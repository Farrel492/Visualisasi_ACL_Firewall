"""Topology and configuration validation module.

ATURAN ARSITEKTUR:
- Murni Python standard library (menggunakan modul ipaddress).
- Validasi menghasilkan daftar error yang jelas dalam Bahasa Indonesia disertai kode error.
"""

from __future__ import annotations

from dataclasses import dataclass
import ipaddress
from typing import List, Set

from firewall_sim.core.models import DeviceType, ProjectState


@dataclass(frozen=True)
class ValidationError:
    code: str
    message: str


def validate_topology(state: ProjectState) -> List[ValidationError]:
    """Memvalidasi konfigurasi topologi jaringan pada ProjectState.

    Kriteria MVP:
    1. Tepat 1 router dalam topologi.
    2. Host (PC/Server) memiliki tepat 1 interface dengan IPv4/CIDR valid dan gateway.
    3. Gateway host harus berada di subnet yang sama dengan host tersebut.
    4. Switch adalah perangkat L2: interface-nya tidak boleh memiliki IP.
    5. Seluruh ID dan nama perangkat harus unik.
    6. Interface link harus valid, menghubungkan 2 interface berbeda, dan interface tidak digunakan ganda.
    7. Tidak ada IP duplikat di subnet yang sama.
    """
    errors: List[ValidationError] = []

    # 1. Validasi Jumlah Router
    routers = [d for d in state.devices if d.type == DeviceType.ROUTER]
    if len(routers) != 1:
        errors.append(
            ValidationError(
                code="INVALID_ROUTER_COUNT",
                message=f"Topologi MVP harus memiliki tepat 1 router/firewall, ditemukan: {len(routers)}.",
            )
        )

    # 2. Keunikan ID & Nama Perangkat
    seen_device_ids: Set[str] = set()
    seen_device_names: Set[str] = set()
    seen_iface_ids: Set[str] = set()
    all_interfaces = {}

    for dev in state.devices:
        if dev.id in seen_device_ids:
            errors.append(
                ValidationError(
                    code="DUPLICATE_DEVICE_ID",
                    message=f"ID perangkat duplikat ditemukan: '{dev.id}'.",
                )
            )
        seen_device_ids.add(dev.id)

        if dev.name in seen_device_names:
            errors.append(
                ValidationError(
                    code="DUPLICATE_DEVICE_NAME",
                    message=f"Nama perangkat duplikat ditemukan: '{dev.name}'.",
                )
            )
        seen_device_names.add(dev.name)

        # Cek interface perangkat
        for iface in dev.interfaces:
            if iface.id in seen_iface_ids:
                errors.append(
                    ValidationError(
                        code="DUPLICATE_INTERFACE_ID",
                        message=f"ID interface duplikat ditemukan: '{iface.id}'.",
                    )
                )
            seen_iface_ids.add(iface.id)
            all_interfaces[iface.id] = (dev, iface)

            # Validasi tipe perangkat vs IP interface
            if dev.type == DeviceType.SWITCH:
                if iface.ipv4_cidr is not None:
                    errors.append(
                        ValidationError(
                            code="SWITCH_INTERFACE_HAS_IP",
                            message=f"Interface switch '{iface.name}' pada '{dev.name}' tidak boleh memiliki IP (hanya L2).",
                        )
                    )
            elif dev.type in (DeviceType.PC, DeviceType.SERVER):
                if iface.ipv4_cidr is None:
                    errors.append(
                        ValidationError(
                            code="HOST_MISSING_IP",
                            message=f"Host '{dev.name}' wajib memiliki IP pada interface '{iface.name}'.",
                        )
                    )

        if dev.type in (DeviceType.PC, DeviceType.SERVER):
            if len(dev.interfaces) != 1:
                errors.append(
                    ValidationError(
                        code="HOST_INTERFACE_COUNT",
                        message=f"Host '{dev.name}' harus memiliki tepat 1 interface, ditemukan: {len(dev.interfaces)}.",
                    )
                )

            # Validasi Default Gateway untuk Host
            if not dev.default_gateway:
                errors.append(
                    ValidationError(
                        code="HOST_MISSING_GATEWAY",
                        message=f"Host '{dev.name}' wajib memiliki default gateway.",
                    )
                )
            else:
                try:
                    gw_ip = ipaddress.IPv4Address(dev.default_gateway)
                    # Cek apakah gateway berada di subnet yang sama dengan interface host
                    if dev.interfaces and dev.interfaces[0].ipv4_cidr:
                        try:
                            iface_net = ipaddress.IPv4Interface(dev.interfaces[0].ipv4_cidr).network
                            if gw_ip not in iface_net:
                                errors.append(
                                    ValidationError(
                                        code="GATEWAY_NOT_IN_SUBNET",
                                        message=(
                                            f"Gateway '{dev.default_gateway}' pada host '{dev.name}' "
                                            f"tidak berada dalam subnet interface '{dev.interfaces[0].ipv4_cidr}'."
                                        ),
                                    )
                                )
                        except ValueError:
                            pass  # error invalid ip interface akan dicatat terpisah di bawah
                except ValueError:
                    errors.append(
                        ValidationError(
                            code="INVALID_GATEWAY_IP",
                            message=f"Alamat default gateway '{dev.default_gateway}' pada '{dev.name}' tidak valid.",
                        )
                    )

        elif dev.type == DeviceType.ROUTER:
            if len(dev.interfaces) < 1:
                errors.append(
                    ValidationError(
                        code="ROUTER_NO_INTERFACE",
                        message=f"Router '{dev.name}' harus memiliki minimal 1 interface ber-IP.",
                    )
                )

    # 3. Validasi Format IP dan Deteksi IP Duplikat
    assigned_ips = {}  # ip_address -> (device_name, network)
    for dev, iface in all_interfaces.values():
        if iface.ipv4_cidr:
            try:
                ip_if = ipaddress.IPv4Interface(iface.ipv4_cidr)
                ip_addr = ip_if.ip
                net = ip_if.network

                if ip_addr in assigned_ips:
                    prev_dev, prev_net = assigned_ips[ip_addr]
                    if net == prev_net:
                        errors.append(
                            ValidationError(
                                code="DUPLICATE_IP_IN_SUBNET",
                                message=(
                                    f"Alamat IP duplikat '{ip_addr}' pada subnet yang sama ({net}) "
                                    f"antara '{prev_dev}' dan '{dev.name}'."
                                ),
                            )
                        )
                else:
                    assigned_ips[ip_addr] = (dev.name, net)
            except ValueError:
                errors.append(
                    ValidationError(
                        code="INVALID_IPV4_CIDR",
                        message=f"Format IPv4 CIDR tidak valid '{iface.ipv4_cidr}' pada interface '{iface.name}' ({dev.name}).",
                    )
                )

    # 4. Validasi Link
    seen_link_ids: Set[str] = set()
    connected_interfaces: Set[str] = set()

    for link in state.links:
        if link.id in seen_link_ids:
            errors.append(
                ValidationError(
                    code="DUPLICATE_LINK_ID",
                    message=f"ID link duplikat ditemukan: '{link.id}'.",
                )
            )
        seen_link_ids.add(link.id)

        if link.interface_a == link.interface_b:
            errors.append(
                ValidationError(
                    code="LINK_SELF_LOOP",
                    message=f"Link '{link.id}' tidak boleh menghubungkan interface ke dirinya sendiri.",
                )
            )

        if link.interface_a not in all_interfaces:
            errors.append(
                ValidationError(
                    code="LINK_INVALID_INTERFACE",
                    message=f"Link '{link.id}' merujuk interface_a yang tidak ada: '{link.interface_a}'.",
                )
            )
        if link.interface_b not in all_interfaces:
            errors.append(
                ValidationError(
                    code="LINK_INVALID_INTERFACE",
                    message=f"Link '{link.id}' merujuk interface_b yang tidak ada: '{link.interface_b}'.",
                )
            )

        # Cek interface tidak boleh terhubung ke lebih dari 1 link aktif
        for iface_id in (link.interface_a, link.interface_b):
            if iface_id in connected_interfaces:
                errors.append(
                    ValidationError(
                        code="INTERFACE_MULTIPLE_LINKS",
                        message=f"Interface '{iface_id}' terhubung ke lebih dari 1 link.",
                    )
                )
            connected_interfaces.add(iface_id)

    return errors
