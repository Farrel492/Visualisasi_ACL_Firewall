"""Configuration service: Single source of truth for ProjectState mutation.

ATURAN ARSITEKTUR:
- Menjadi satu-satunya pintu gerbang (single point of entry) untuk perubahan konfigurasi.
- State tidak pernah dimutasi di tempat (in-place); setiap perubahan yang valid
  mengembalikan objek ProjectState baru yang immutable.
- Setiap perubahan yang valid menaikkan 'config_revision' +1 dan mencatat AuditEntry.
- Perubahan tidak valid mengembalikan state asli secara utuh beserta daftar pesan error.
- Validasi topologi/skema dijalankan sebelum perubahan di-commit.
- Pembuatan ID perangkat/interface/link harus deterministik tanpa modul random/uuid.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import re
from typing import List, Optional, Tuple, Union

from firewall_sim.core.models import (
    Action,
    AuditEntry,
    Chain,
    Device,
    DeviceType,
    FirewallRule,
    Interface,
    Link,
    ProjectState,
)
from firewall_sim.core.validation import validate_topology


# Base & Command Dataclasses
@dataclass(frozen=True)
class ConfigCommand:
    source: str = "TEST"  # "GUI", "CLI", "TEST"
    timestamp: Optional[datetime] = None


@dataclass(frozen=True)
class SetInterfaceIP(ConfigCommand):
    device_id: str = ""
    interface_id: str = ""
    ipv4_cidr: Optional[str] = None


@dataclass(frozen=True)
class SetInterfaceEnabled(ConfigCommand):
    interface_id: str = ""
    enabled: bool = True


@dataclass(frozen=True)
class SetGateway(ConfigCommand):
    device_id: str = ""
    default_gateway: Optional[str] = None


@dataclass(frozen=True)
class AddRule(ConfigCommand):
    rule: Optional[FirewallRule] = None


@dataclass(frozen=True)
class RemoveRule(ConfigCommand):
    rule_id: str = ""


@dataclass(frozen=True)
class ToggleRule(ConfigCommand):
    rule_id: str = ""


@dataclass(frozen=True)
class MoveRule(ConfigCommand):
    rule_id: str = ""
    new_order: int = 1


@dataclass(frozen=True)
class SetDefaultPolicy(ConfigCommand):
    chain: Chain = Chain.FORWARD
    action: Action = Action.ACCEPT


@dataclass(frozen=True)
class AddDevice(ConfigCommand):
    name: str = ""
    type: DeviceType = DeviceType.PC
    device_id: Optional[str] = None
    interfaces: Tuple[Interface, ...] = ()
    default_gateway: Optional[str] = None


@dataclass(frozen=True)
class RemoveDevice(ConfigCommand):
    device_id: str = ""


@dataclass(frozen=True)
class RenameDevice(ConfigCommand):
    device_id: str = ""
    new_name: str = ""


@dataclass(frozen=True)
class AddLink(ConfigCommand):
    interface_a: str = ""
    interface_b: str = ""
    link_id: Optional[str] = None
    enabled: bool = True


@dataclass(frozen=True)
class RemoveLink(ConfigCommand):
    link_id: str = ""


def _generate_deterministic_slug(name: str, existing_ids: List[str]) -> str:
    """Menghasilkan ID deterministik berbasis nama tanpa modul acak."""
    base = re.sub(r"[^a-zA-Z0-9_]", "_", name.lower().strip())
    base = re.sub(r"_+", "_", base).strip("_") or "dev"
    cand = base
    idx = 2
    while cand in existing_ids:
        cand = f"{base}_{idx}"
        idx += 1
    return cand


def update_config(
    state: ProjectState,
    command: ConfigCommand,
) -> Tuple[ProjectState, List[str]]:
    """Menerapkan command konfigurasi terhadap ProjectState secara atomik dan aman."""
    now_dt = command.timestamp or datetime.now()
    src = command.source or "TEST"

    new_devices = list(state.devices)
    new_links = list(state.links)
    new_rules = list(state.rules)
    new_default_policies = list(state.default_policies)
    summary = ""

    # 1. Handler Per Command
    if isinstance(command, SetInterfaceIP):
        target_dev_idx = None
        for i, d in enumerate(new_devices):
            if d.id == command.device_id:
                target_dev_idx = i
                break

        if target_dev_idx is None:
            return state, [f"Perangkat dengan ID '{command.device_id}' tidak ditemukan."]

        dev = new_devices[target_dev_idx]
        target_if_idx = None
        for j, iface in enumerate(dev.interfaces):
            if iface.id == command.interface_id:
                target_if_idx = j
                break

        if target_if_idx is None:
            return state, [f"Interface dengan ID '{command.interface_id}' tidak ditemukan pada '{dev.name}'."]

        old_if = dev.interfaces[target_if_idx]
        updated_if = Interface(
            id=old_if.id,
            device_id=old_if.device_id,
            name=old_if.name,
            ipv4_cidr=command.ipv4_cidr,
            enabled=old_if.enabled,
        )
        updated_if_list = list(dev.interfaces)
        updated_if_list[target_if_idx] = updated_if
        new_devices[target_dev_idx] = Device(
            id=dev.id,
            name=dev.name,
            type=dev.type,
            interfaces=tuple(updated_if_list),
            default_gateway=dev.default_gateway,
        )
        summary = f"Ubah IP interface '{old_if.name}' pada '{dev.name}' menjadi '{command.ipv4_cidr}'"

    elif isinstance(command, SetInterfaceEnabled):
        found = False
        for i, dev in enumerate(new_devices):
            for j, iface in enumerate(dev.interfaces):
                if iface.id == command.interface_id:
                    updated_if = Interface(
                        id=iface.id,
                        device_id=iface.device_id,
                        name=iface.name,
                        ipv4_cidr=iface.ipv4_cidr,
                        enabled=command.enabled,
                    )
                    updated_if_list = list(dev.interfaces)
                    updated_if_list[j] = updated_if
                    new_devices[i] = Device(
                        id=dev.id,
                        name=dev.name,
                        type=dev.type,
                        interfaces=tuple(updated_if_list),
                        default_gateway=dev.default_gateway,
                    )
                    found = True
                    summary = f"Set status interface '{iface.name}' menjadi {'aktif' if command.enabled else 'nonaktif'}"
                    break
            if found:
                break
        if not found:
            return state, [f"Interface ID '{command.interface_id}' tidak ditemukan."]

    elif isinstance(command, SetGateway):
        target_dev_idx = None
        for i, d in enumerate(new_devices):
            if d.id == command.device_id:
                target_dev_idx = i
                break
        if target_dev_idx is None:
            return state, [f"Perangkat dengan ID '{command.device_id}' tidak ditemukan."]

        dev = new_devices[target_dev_idx]
        new_devices[target_dev_idx] = Device(
            id=dev.id,
            name=dev.name,
            type=dev.type,
            interfaces=dev.interfaces,
            default_gateway=command.default_gateway,
        )
        summary = f"Set default gateway '{dev.name}' menjadi '{command.default_gateway}'"

    elif isinstance(command, AddRule):
        if not command.rule:
            return state, ["Rule tidak boleh kosong."]
        if any(r.id == command.rule.id for r in new_rules):
            return state, [f"Rule ID '{command.rule.id}' sudah ada."]
        new_rules.append(command.rule)
        summary = f"Tambah firewall rule '{command.rule.id}' ({command.rule.chain.value.upper()} {command.rule.action.value.upper()})"

    elif isinstance(command, RemoveRule):
        orig_count = len(new_rules)
        new_rules = [r for r in new_rules if r.id != command.rule_id]
        if len(new_rules) == orig_count:
            return state, [f"Rule ID '{command.rule_id}' tidak ditemukan."]
        summary = f"Hapus firewall rule '{command.rule_id}'"

    elif isinstance(command, ToggleRule):
        found = False
        for i, r in enumerate(new_rules):
            if r.id == command.rule_id:
                new_rules[i] = FirewallRule(
                    id=r.id,
                    order=r.order,
                    enabled=not r.enabled,
                    chain=r.chain,
                    src_cidr=r.src_cidr,
                    dst_cidr=r.dst_cidr,
                    protocol=r.protocol,
                    src_port=r.src_port,
                    dst_port=r.dst_port,
                    action=r.action,
                    comment=r.comment,
                    counter=r.counter,
                )
                found = True
                status_str = "aktif" if new_rules[i].enabled else "nonaktif"
                summary = f"Toggle firewall rule '{r.id}' menjadi {status_str}"
                break
        if not found:
            return state, [f"Rule ID '{command.rule_id}' tidak ditemukan."]

    elif isinstance(command, MoveRule):
        found = False
        for i, r in enumerate(new_rules):
            if r.id == command.rule_id:
                new_rules[i] = FirewallRule(
                    id=r.id,
                    order=command.new_order,
                    enabled=r.enabled,
                    chain=r.chain,
                    src_cidr=r.src_cidr,
                    dst_cidr=r.dst_cidr,
                    protocol=r.protocol,
                    src_port=r.src_port,
                    dst_port=r.dst_port,
                    action=r.action,
                    comment=r.comment,
                    counter=r.counter,
                )
                found = True
                summary = f"Pindahkan urutan rule '{r.id}' ke order {command.new_order}"
                break
        if not found:
            return state, [f"Rule ID '{command.rule_id}' tidak ditemukan."]

    elif isinstance(command, SetDefaultPolicy):
        updated_policies = []
        for c, a in new_default_policies:
            if c == command.chain:
                updated_policies.append((command.chain, command.action))
            else:
                updated_policies.append((c, a))
        new_default_policies = updated_policies
        summary = f"Ubah default policy chain {command.chain.value.upper()} menjadi {command.action.value.upper()}"

    elif isinstance(command, AddDevice):
        if not command.name.strip():
            return state, ["Nama perangkat tidak boleh kosong."]
        existing_ids = [d.id for d in new_devices]
        dev_id = command.device_id or _generate_deterministic_slug(command.name, existing_ids)
        if dev_id in existing_ids:
            return state, [f"Perangkat dengan ID '{dev_id}' sudah ada."]

        # Interface default jika tidak disediakan
        iface_list = list(command.interfaces)
        if not iface_list:
            if command.type == DeviceType.SWITCH:
                for p in range(1, 5):
                    iface_list.append(
                        Interface(
                            id=f"if_{dev_id}_p{p}",
                            device_id=dev_id,
                            name=f"port{p}",
                            ipv4_cidr=None,
                            enabled=True,
                        )
                    )
            elif command.type in (DeviceType.PC, DeviceType.SERVER):
                iface_list.append(
                    Interface(
                        id=f"if_{dev_id}_eth0",
                        device_id=dev_id,
                        name="eth0",
                        ipv4_cidr=None,
                        enabled=True,
                    )
                )
            elif command.type == DeviceType.ROUTER:
                iface_list.append(
                    Interface(
                        id=f"if_{dev_id}_eth0",
                        device_id=dev_id,
                        name="eth0",
                        ipv4_cidr=None,
                        enabled=True,
                    )
                )

        new_dev = Device(
            id=dev_id,
            name=command.name.strip(),
            type=command.type,
            interfaces=tuple(iface_list),
            default_gateway=command.default_gateway,
        )
        new_devices.append(new_dev)
        summary = f"Tambah perangkat '{new_dev.name}' ({new_dev.type.value.upper()})"

    elif isinstance(command, RemoveDevice):
        target_dev = state.get_device(command.device_id)
        if not target_dev:
            return state, [f"Perangkat dengan ID '{command.device_id}' tidak ditemukan."]

        # Aturan A1: Tolak jika menghapus satu-satunya router
        if target_dev.type == DeviceType.ROUTER:
            router_count = sum(1 for d in new_devices if d.type == DeviceType.ROUTER)
            if router_count <= 1:
                return state, ["Tidak dapat menghapus satu-satunya router/firewall pada topologi."]

        dev_iface_ids = {i.id for i in target_dev.interfaces}
        # Hapus device
        new_devices = [d for d in new_devices if d.id != command.device_id]
        # Hapus link terkait
        new_links = [
            l for l in new_links
            if l.interface_a not in dev_iface_ids and l.interface_b not in dev_iface_ids
        ]
        summary = f"Hapus perangkat '{target_dev.name}' dan seluruh link terkait"

    elif isinstance(command, RenameDevice):
        if not command.new_name.strip():
            return state, ["Nama baru perangkat tidak boleh kosong."]
        found = False
        for i, dev in enumerate(new_devices):
            if dev.id == command.device_id:
                new_devices[i] = Device(
                    id=dev.id,
                    name=command.new_name.strip(),
                    type=dev.type,
                    interfaces=dev.interfaces,
                    default_gateway=dev.default_gateway,
                )
                found = True
                summary = f"Ganti nama perangkat '{dev.name}' menjadi '{command.new_name.strip()}'"
                break
        if not found:
            return state, [f"Perangkat dengan ID '{command.device_id}' tidak ditemukan."]

    elif isinstance(command, AddLink):
        if command.interface_a == command.interface_b:
            return state, ["Link tidak boleh menghubungkan interface ke dirinya sendiri."]
        all_ifaces = {i.id: i for d in new_devices for i in d.interfaces}
        if command.interface_a not in all_ifaces:
            return state, [f"Interface '{command.interface_a}' tidak ditemukan."]
        if command.interface_b not in all_ifaces:
            return state, [f"Interface '{command.interface_b}' tidak ditemukan."]

        # Cek interface apakah sudah terhubung link lain
        for l in new_links:
            if command.interface_a in (l.interface_a, l.interface_b):
                return state, [f"Interface '{command.interface_a}' sudah terhubung pada link '{l.id}'."]
            if command.interface_b in (l.interface_a, l.interface_b):
                return state, [f"Interface '{command.interface_b}' sudah terhubung pada link '{l.id}'."]

        link_id = command.link_id or f"link_{command.interface_a}_{command.interface_b}"
        new_link = Link(
            id=link_id,
            interface_a=command.interface_a,
            interface_b=command.interface_b,
            enabled=command.enabled,
        )
        new_links.append(new_link)
        summary = f"Tambah link '{new_link.id}' antara '{command.interface_a}' dan '{command.interface_b}'"

    elif isinstance(command, RemoveLink):
        orig_count = len(new_links)
        new_links = [l for l in new_links if l.id != command.link_id]
        if len(new_links) == orig_count:
            return state, [f"Link ID '{command.link_id}' tidak ditemukan."]
        summary = f"Hapus link '{command.link_id}'"

    else:
        return state, [f"Tipe command tidak dikenali: '{type(command).__name__}'."]

    # 2. Bangun State Kandidat Sementara
    candidate_state = ProjectState(
        devices=tuple(new_devices),
        links=tuple(new_links),
        rules=tuple(new_rules),
        config_revision=state.config_revision + 1,
        default_policies=tuple(new_default_policies),
        scenario_metadata=state.scenario_metadata,
        audit_log=state.audit_log + (
            AuditEntry(
                timestamp=now_dt,
                source=src,
                summary=summary,
            ),
        ),
    )

    # 3. Jalankan Validasi Topologi Terhadap State Kandidat
    val_errors = validate_topology(candidate_state)
    if val_errors:
        err_msgs = [f"[{e.code}] {e.message}" for e in val_errors]
        return state, err_msgs

    return candidate_state, []
