"""Packet simulation engine and path traversal.

ATURAN ARSITEKTUR:
- Murni Python standard library (tanpa Streamlit / UI).
- Menghasilkan SimulationResult yang immutable.
- Hasil dibedakan secara ketat: ACCEPT, DROP, NO_ROUTE, INVALID_CONFIG, UNSUPPORTED_CASE.
- NO_ROUTE tidak boleh dilaporkan sebagai DROP.
- Trace mencatat seluruh langkah traversal dan evaluasi rule.
- Hasil selalu mencatat config_revision state saat simulasi dijalankan.
"""

from __future__ import annotations

from collections import deque
from datetime import datetime
import ipaddress
from typing import Callable, Dict, List, Optional, Set, Tuple, Union

from firewall_sim.core.models import (
    Action,
    Chain,
    Decision,
    Device,
    DeviceType,
    Interface,
    Link,
    PacketTest,
    ProjectState,
    SimulationResult,
    TraceStep,
)
from firewall_sim.core.rules import evaluate_chain
from firewall_sim.core.validation import validate_topology


def _get_l2_path(
    state: ProjectState,
    start_iface_id: str,
    target_iface_id: str,
) -> Optional[List[Tuple[Optional[str], str, str]]]:
    """Mencari jalur L2 antara dua interface menggunakan BFS.

    Returns:
        List of tuples (link_id, from_iface_id, to_iface_id) jika ditemukan jalur,
        atau None jika tidak terjangkau.
    """
    if start_iface_id == target_iface_id:
        return []

    # Map interface ke device
    iface_to_dev: Dict[str, Device] = {}
    iface_obj: Dict[str, Interface] = {}
    for dev in state.devices:
        for iface in dev.interfaces:
            iface_to_dev[iface.id] = dev
            iface_obj[iface.id] = iface

    start_if = iface_obj.get(start_iface_id)
    target_if = iface_obj.get(target_iface_id)
    if not start_if or not target_if or not start_if.enabled or not target_if.enabled:
        return None

    # Bangun adjacency list untuk L2
    # Edge type:
    # 1. Link antar-interface (hanya jika link & kedua interface enabled)
    # 2. Internal switch bridge antar semua interface di switch yang sama (hanya jika switch & interface enabled)
    adj: Dict[str, List[Tuple[str, Optional[str]]]] = {if_id: [] for if_id in iface_obj}

    for link in state.links:
        if link.enabled:
            if_a = iface_obj.get(link.interface_a)
            if_b = iface_obj.get(link.interface_b)
            if if_a and if_b and if_a.enabled and if_b.enabled:
                adj[link.interface_a].append((link.interface_b, link.id))
                adj[link.interface_b].append((link.interface_a, link.id))

    for dev in state.devices:
        if dev.type == DeviceType.SWITCH:
            enabled_switch_ifaces = [i.id for i in dev.interfaces if i.enabled]
            for i1 in enabled_switch_ifaces:
                for i2 in enabled_switch_ifaces:
                    if i1 != i2:
                        adj[i1].append((i2, None))  # internal bridge (tanpa link external)

    # BFS
    queue = deque([[start_iface_id]])
    visited: Set[str] = {start_iface_id}
    parent_edge: Dict[Tuple[str, str], Optional[str]] = {}

    found_path = False
    final_node_path: List[str] = []

    while queue:
        curr_path = queue.popleft()
        curr_node = curr_path[-1]

        if curr_node == target_iface_id:
            found_path = True
            final_node_path = curr_path
            break

        for neighbor, link_id in adj.get(curr_node, []):
            if neighbor not in visited:
                visited.add(neighbor)
                parent_edge[(curr_node, neighbor)] = link_id
                queue.append(curr_path + [neighbor])

    if not found_path:
        return None

    # Rekonstruksi rute
    route_edges: List[Tuple[Optional[str], str, str]] = []
    for i in range(len(final_node_path) - 1):
        u = final_node_path[i]
        v = final_node_path[i + 1]
        l_id = parent_edge.get((u, v))
        route_edges.append((l_id, u, v))

    return route_edges


def simulate_packet(
    state: ProjectState,
    packet: PacketTest,
    now: Optional[Union[datetime, Callable[[], datetime]]] = None,
) -> SimulationResult:
    """Menjalankan simulasi traversal paket virtual terhadap ProjectState."""
    # 1. Resolve deterministik timestamp
    if now is None:
        ts = datetime.now()
    elif callable(now):
        ts = now()
    else:
        ts = now

    # 2. Validasi State
    validation_errors = validate_topology(state)
    if validation_errors:
        err_msgs = "; ".join(f"[{e.code}] {e.message}" for e in validation_errors)
        return SimulationResult(
            test_id=packet.id,
            decision=Decision.INVALID_CONFIG,
            reason=f"Konfigurasi topologi tidak valid: {err_msgs}",
            matched_rule_id=None,
            trace=(),
            config_revision=state.config_revision,
            timestamp=ts,
            evaluated_rules=(),
        )

    # 3. Cari Host Sumber
    src_dev = state.get_device(packet.source_device_id)
    if not src_dev:
        return SimulationResult(
            test_id=packet.id,
            decision=Decision.INVALID_CONFIG,
            reason=f"Perangkat sumber dengan ID '{packet.source_device_id}' tidak ditemukan.",
            matched_rule_id=None,
            trace=(),
            config_revision=state.config_revision,
            timestamp=ts,
            evaluated_rules=(),
        )

    # Larangan/Backlog: Sumber = Router (Chain OUTPUT)
    if src_dev.type == DeviceType.ROUTER:
        return SimulationResult(
            test_id=packet.id,
            decision=Decision.UNSUPPORTED_CASE,
            reason="Paket yang bersumber langsung dari router (chain output) belum didukung pada tahap MVP (backlog).",
            matched_rule_id=None,
            trace=(),
            config_revision=state.config_revision,
            timestamp=ts,
            evaluated_rules=(),
        )

    src_iface = src_dev.interfaces[0]
    if not src_iface.enabled:
        return SimulationResult(
            test_id=packet.id,
            decision=Decision.NO_ROUTE,
            reason=f"Interface '{src_iface.name}' pada perangkat sumber '{src_dev.name}' dalam keadaan nonaktif (down).",
            matched_rule_id=None,
            trace=(
                TraceStep(
                    step_number=1,
                    device_id=src_dev.id,
                    description=f"Interface {src_iface.name} nonaktif.",
                ),
            ),
            config_revision=state.config_revision,
            timestamp=ts,
            evaluated_rules=(),
        )

    src_ip = str(ipaddress.IPv4Interface(src_iface.ipv4_cidr).ip)
    src_net = ipaddress.IPv4Interface(src_iface.ipv4_cidr).network

    # 4. Tentukan Tujuan
    dst_dev: Optional[Device] = None
    dst_ip_str: str = ""
    dst_iface: Optional[Interface] = None

    if packet.destination_device_id:
        dst_dev = state.get_device(packet.destination_device_id)
        if not dst_dev:
            return SimulationResult(
                test_id=packet.id,
                decision=Decision.INVALID_CONFIG,
                reason=f"Perangkat tujuan dengan ID '{packet.destination_device_id}' tidak ditemukan.",
                matched_rule_id=None,
                trace=(),
                config_revision=state.config_revision,
                timestamp=ts,
                evaluated_rules=(),
            )
        if dst_dev.interfaces and dst_dev.interfaces[0].ipv4_cidr:
            dst_iface = dst_dev.interfaces[0]
            dst_ip_str = str(ipaddress.IPv4Interface(dst_iface.ipv4_cidr).ip)
        else:
            return SimulationResult(
                test_id=packet.id,
                decision=Decision.INVALID_CONFIG,
                reason=f"Perangkat tujuan '{dst_dev.name}' tidak memiliki interface dengan IP valid.",
                matched_rule_id=None,
                trace=(),
                config_revision=state.config_revision,
                timestamp=ts,
                evaluated_rules=(),
            )
    elif packet.destination_ip:
        dst_ip_str = packet.destination_ip
        # Cari apakah ada device di state yang memegang IP ini
        for d in state.devices:
            for iface in d.interfaces:
                if iface.ipv4_cidr:
                    if str(ipaddress.IPv4Interface(iface.ipv4_cidr).ip) == dst_ip_str:
                        dst_dev = d
                        dst_iface = iface
                        break
            if dst_dev:
                break
    else:
        return SimulationResult(
            test_id=packet.id,
            decision=Decision.INVALID_CONFIG,
            reason="Parameter tujuan (destination_device_id atau destination_ip) harus disediakan.",
            matched_rule_id=None,
            trace=(),
            config_revision=state.config_revision,
            timestamp=ts,
            evaluated_rules=(),
        )

    try:
        dst_addr = ipaddress.IPv4Address(dst_ip_str)
    except ValueError:
        return SimulationResult(
            test_id=packet.id,
            decision=Decision.INVALID_CONFIG,
            reason=f"Alamat IP tujuan '{dst_ip_str}' tidak valid.",
            matched_rule_id=None,
            trace=(),
            config_revision=state.config_revision,
            timestamp=ts,
            evaluated_rules=(),
        )

    # 5. Cek apakah tujuan adalah IP Router itu sendiri (Chain INPUT)
    routers = [d for d in state.devices if d.type == DeviceType.ROUTER]
    router = routers[0]

    router_dst_iface: Optional[Interface] = None
    for r_iface in router.interfaces:
        if r_iface.ipv4_cidr:
            if str(ipaddress.IPv4Interface(r_iface.ipv4_cidr).ip) == dst_ip_str:
                router_dst_iface = r_iface
                break

    if router_dst_iface is not None:
        # Tujuan adalah interface router -> Evaluasi Chain INPUT
        # Cek apakah router interface tersebut se-subnet dengan sumber
        r_dst_net = ipaddress.IPv4Interface(router_dst_iface.ipv4_cidr).network
        trace_steps: List[TraceStep] = [
            TraceStep(
                step_number=1,
                device_id=src_dev.id,
                description=f"Paket diinisiasi dari {src_dev.name} ({src_ip}) menuju IP router {dst_ip_str}.",
            )
        ]
        step_idx = 2

        if dst_addr in src_net:
            # Satu subnet dengan sumber -> L2 langsung ke router_dst_iface
            l2_to_router = _get_l2_path(state, src_iface.id, router_dst_iface.id)
            if l2_to_router is None:
                return SimulationResult(
                    test_id=packet.id,
                    decision=Decision.NO_ROUTE,
                    reason=f"Interface router '{router_dst_iface.name}' ({dst_ip_str}) tidak terjangkau secara L2 dari '{src_dev.name}'.",
                    matched_rule_id=None,
                    trace=tuple(trace_steps),
                    config_revision=state.config_revision,
                    timestamp=ts,
                    evaluated_rules=(),
                )
            for link_id, u, v in l2_to_router:
                u_iface = state.get_interface(u)
                v_iface = state.get_interface(v)
                desc = f"L2 hop: {u_iface.name if u_iface else u} -> {v_iface.name if v_iface else v}"
                if link_id:
                    desc += f" (Link {link_id})"
                dev_id = u_iface.device_id if u_iface else src_dev.id
                trace_steps.append(
                    TraceStep(
                        step_number=step_idx,
                        device_id=dev_id,
                        description=desc,
                        link_id=link_id,
                    )
                )
                step_idx += 1
        else:
            # Berbeda subnet -> Kirim via default gateway
            if not src_dev.default_gateway:
                return SimulationResult(
                    test_id=packet.id,
                    decision=Decision.NO_ROUTE,
                    reason=f"Host sumber '{src_dev.name}' tidak memiliki default gateway.",
                    matched_rule_id=None,
                    trace=tuple(trace_steps),
                    config_revision=state.config_revision,
                    timestamp=ts,
                    evaluated_rules=(),
                )
            gw_ip_str = src_dev.default_gateway
            router_gw_iface = None
            for r_if in router.interfaces:
                if r_if.ipv4_cidr and str(ipaddress.IPv4Interface(r_if.ipv4_cidr).ip) == gw_ip_str:
                    router_gw_iface = r_if
                    break
            if not router_gw_iface:
                return SimulationResult(
                    test_id=packet.id,
                    decision=Decision.NO_ROUTE,
                    reason=f"Gateway host '{gw_ip_str}' bukan merupakan IP interface router '{router.name}'.",
                    matched_rule_id=None,
                    trace=tuple(trace_steps),
                    config_revision=state.config_revision,
                    timestamp=ts,
                    evaluated_rules=(),
                )
            l2_to_router = _get_l2_path(state, src_iface.id, router_gw_iface.id)
            if l2_to_router is None:
                return SimulationResult(
                    test_id=packet.id,
                    decision=Decision.NO_ROUTE,
                    reason=f"Gateway '{gw_ip_str}' pada router '{router.name}' tidak terjangkau secara L2 dari '{src_dev.name}'.",
                    matched_rule_id=None,
                    trace=tuple(trace_steps),
                    config_revision=state.config_revision,
                    timestamp=ts,
                    evaluated_rules=(),
                )
            for link_id, u, v in l2_to_router:
                u_iface = state.get_interface(u)
                v_iface = state.get_interface(v)
                desc = f"L2 hop: {u_iface.name if u_iface else u} -> {v_iface.name if v_iface else v}"
                if link_id:
                    desc += f" (Link {link_id})"
                dev_id = u_iface.device_id if u_iface else src_dev.id
                trace_steps.append(
                    TraceStep(
                        step_number=step_idx,
                        device_id=dev_id,
                        description=desc,
                        link_id=link_id,
                    )
                )
                step_idx += 1

        trace_steps.append(
            TraceStep(
                step_number=step_idx,
                device_id=router.id,
                description=f"Paket tiba di interface router: {router_dst_iface.name}.",
            )
        )
        step_idx += 1

        # Evaluasi chain INPUT
        default_pol = state.get_default_policy(Chain.INPUT)
        rule_res = evaluate_chain(
            state.rules,
            Chain.INPUT,
            src_ip,
            dst_ip_str,
            packet,
            default_policy=default_pol,
        )

        trace_steps.append(
            TraceStep(
                step_number=step_idx,
                device_id=router.id,
                description=f"Evaluasi firewall chain INPUT: {rule_res.reason}.",
                rule_id=rule_res.matched_rule.id if rule_res.matched_rule else None,
                action=rule_res.action.value.upper(),
            )
        )

        if rule_res.action == Action.DROP:
            return SimulationResult(
                test_id=packet.id,
                decision=Decision.DROP,
                reason=rule_res.reason,
                matched_rule_id=rule_res.matched_rule.id if rule_res.matched_rule else None,
                trace=tuple(trace_steps),
                config_revision=state.config_revision,
                timestamp=ts,
                evaluated_rules=rule_res.evaluated_rule_ids,
            )
        else:
            return SimulationResult(
                test_id=packet.id,
                decision=Decision.ACCEPT,
                reason=rule_res.reason,
                matched_rule_id=rule_res.matched_rule.id if rule_res.matched_rule else None,
                trace=tuple(trace_steps),
                config_revision=state.config_revision,
                timestamp=ts,
                evaluated_rules=rule_res.evaluated_rule_ids,
            )

    # 6. Cek Komunikasi Sama Subnet Antar Host (Same-Subnet L2 Direct)
    if dst_addr in src_net:
        if not dst_iface:
            return SimulationResult(
                test_id=packet.id,
                decision=Decision.NO_ROUTE,
                reason=f"IP tujuan '{dst_ip_str}' berada di subnet yang sama namun perangkat pemilik IP tidak ditemukan.",
                matched_rule_id=None,
                trace=(),
                config_revision=state.config_revision,
                timestamp=ts,
                evaluated_rules=(),
            )

        l2_path = _get_l2_path(state, src_iface.id, dst_iface.id)
        if l2_path is None:
            return SimulationResult(
                test_id=packet.id,
                decision=Decision.NO_ROUTE,
                reason=f"Host tujuan '{dst_dev.name if dst_dev else dst_ip_str}' berada di subnet yang sama ({src_net}), tetapi tidak ada jalur L2 aktif.",
                matched_rule_id=None,
                trace=(
                    TraceStep(
                        step_number=1,
                        device_id=src_dev.id,
                        description=f"Paket keluar dari {src_dev.name} menuju {dst_ip_str} (same-subnet).",
                    ),
                    TraceStep(
                        step_number=2,
                        device_id=src_dev.id,
                        description="Jalur L2 terputus atau tidak terhubung.",
                    ),
                ),
                config_revision=state.config_revision,
                timestamp=ts,
                evaluated_rules=(),
            )

        # Berhasil L2 direct tanpa melewati firewall
        trace_steps: List[TraceStep] = [
            TraceStep(
                step_number=1,
                device_id=src_dev.id,
                description=f"Paket diinisiasi dari {src_dev.name} ({src_ip}) menuju {dst_ip_str}.",
            )
        ]
        step_idx = 2
        for link_id, u, v in l2_path:
            u_iface = state.get_interface(u)
            v_iface = state.get_interface(v)
            desc = f"L2 hop via interface {u_iface.name if u_iface else u} -> {v_iface.name if v_iface else v}"
            if link_id:
                desc += f" (Link {link_id})"
            dev_id = u_iface.device_id if u_iface else src_dev.id
            trace_steps.append(
                TraceStep(
                    step_number=step_idx,
                    device_id=dev_id,
                    description=desc,
                    link_id=link_id,
                )
            )
            step_idx += 1

        trace_steps.append(
            TraceStep(
                step_number=step_idx,
                device_id=dst_dev.id if dst_dev else "unknown",
                description=f"Paket tiba di tujuan {dst_dev.name if dst_dev else dst_ip_str}.",
                action="ACCEPT",
            )
        )

        return SimulationResult(
            test_id=packet.id,
            decision=Decision.ACCEPT,
            reason="Komunikasi dalam subnet yang sama melalui L2; paket tidak melewati firewall.",
            matched_rule_id=None,
            trace=tuple(trace_steps),
            config_revision=state.config_revision,
            timestamp=ts,
            evaluated_rules=(),
        )

    # 7. Komunikasi Berbeda Subnet Melalui Router -> Chain FORWARD
    router = routers[0]

    # Validasi gateway pada host sumber
    if not src_dev.default_gateway:
        return SimulationResult(
            test_id=packet.id,
            decision=Decision.NO_ROUTE,
            reason=f"Host sumber '{src_dev.name}' tidak memiliki default gateway yang dikonfigurasi.",
            matched_rule_id=None,
            trace=(),
            config_revision=state.config_revision,
            timestamp=ts,
            evaluated_rules=(),
        )

    gw_ip_str = src_dev.default_gateway

    # Cari interface router yang memiliki IP gateway tersebut
    router_in_iface: Optional[Interface] = None
    for r_iface in router.interfaces:
        if r_iface.ipv4_cidr:
            if str(ipaddress.IPv4Interface(r_iface.ipv4_cidr).ip) == gw_ip_str:
                router_in_iface = r_iface
                break

    if not router_in_iface:
        return SimulationResult(
            test_id=packet.id,
            decision=Decision.NO_ROUTE,
            reason=f"Gateway host '{gw_ip_str}' bukan merupakan IP interface router/firewall '{router.name}'.",
            matched_rule_id=None,
            trace=(),
            config_revision=state.config_revision,
            timestamp=ts,
            evaluated_rules=(),
        )

    # Cek L2 dari host sumber ke router_in_iface
    l2_to_router = _get_l2_path(state, src_iface.id, router_in_iface.id)
    if l2_to_router is None:
        return SimulationResult(
            test_id=packet.id,
            decision=Decision.NO_ROUTE,
            reason=f"Gateway '{gw_ip_str}' pada router '{router.name}' tidak terjangkau secara L2 dari '{src_dev.name}'.",
            matched_rule_id=None,
            trace=(
                TraceStep(
                    step_number=1,
                    device_id=src_dev.id,
                    description=f"Paket dikirim menuju gateway {gw_ip_str}.",
                ),
                TraceStep(
                    step_number=2,
                    device_id=src_dev.id,
                    description="Jalur L2 menuju gateway terputus.",
                ),
            ),
            config_revision=state.config_revision,
            timestamp=ts,
            evaluated_rules=(),
        )

    trace_steps: List[TraceStep] = [
        TraceStep(
            step_number=1,
            device_id=src_dev.id,
            description=f"Paket diinisiasi dari {src_dev.name} ({src_ip}) menuju {dst_ip_str} via gateway {gw_ip_str}.",
        )
    ]
    step_idx = 2
    for link_id, u, v in l2_to_router:
        u_iface = state.get_interface(u)
        v_iface = state.get_interface(v)
        desc = f"L2 hop: {u_iface.name if u_iface else u} -> {v_iface.name if v_iface else v}"
        if link_id:
            desc += f" (Link {link_id})"
        dev_id = u_iface.device_id if u_iface else src_dev.id
        trace_steps.append(
            TraceStep(
                step_number=step_idx,
                device_id=dev_id,
                description=desc,
                link_id=link_id,
            )
        )
        step_idx += 1

    trace_steps.append(
        TraceStep(
            step_number=step_idx,
            device_id=router.id,
            description=f"Paket tiba di interface incoming router: {router_in_iface.name}.",
        )
    )
    step_idx += 1

    # 8. Komunikasi Melalui Router ke Subnet Lain (Chain FORWARD)
    # Temukan interface router yang meng-handle subnet tujuan
    router_out_iface: Optional[Interface] = None
    for r_iface in router.interfaces:
        if r_iface.ipv4_cidr:
            r_net = ipaddress.IPv4Interface(r_iface.ipv4_cidr).network
            if dst_addr in r_net:
                router_out_iface = r_iface
                break

    if not router_out_iface:
        return SimulationResult(
            test_id=packet.id,
            decision=Decision.NO_ROUTE,
            reason=f"Router '{router.name}' tidak memiliki rute / interface connected menuju subnet IP '{dst_ip_str}'.",
            matched_rule_id=None,
            trace=tuple(trace_steps),
            config_revision=state.config_revision,
            timestamp=ts,
            evaluated_rules=(),
        )

    if not router_out_iface.enabled:
        return SimulationResult(
            test_id=packet.id,
            decision=Decision.NO_ROUTE,
            reason=f"Interface keluar router '{router_out_iface.name}' dalam keadaan down.",
            matched_rule_id=None,
            trace=tuple(trace_steps),
            config_revision=state.config_revision,
            timestamp=ts,
            evaluated_rules=(),
        )

    # Cek keterjangkauan L2 dari router_out_iface ke interface tujuan (jika tujuan ada di topologi)
    l2_from_router: Optional[List[Tuple[Optional[str], str, str]]] = None
    if dst_iface:
        l2_from_router = _get_l2_path(state, router_out_iface.id, dst_iface.id)
        if l2_from_router is None:
            return SimulationResult(
                test_id=packet.id,
                decision=Decision.NO_ROUTE,
                reason=f"Host tujuan '{dst_dev.name if dst_dev else dst_ip_str}' tidak terjangkau secara L2 dari interface router '{router_out_iface.name}'.",
                matched_rule_id=None,
                trace=tuple(trace_steps),
                config_revision=state.config_revision,
                timestamp=ts,
                evaluated_rules=(),
            )

    # Evaluasi Chain FORWARD
    default_pol = state.get_default_policy(Chain.FORWARD)
    rule_res = evaluate_chain(
        state.rules,
        Chain.FORWARD,
        src_ip,
        dst_ip_str,
        packet,
        default_policy=default_pol,
    )

    trace_steps.append(
        TraceStep(
            step_number=step_idx,
            device_id=router.id,
            description=f"Evaluasi firewall chain FORWARD: {rule_res.reason}.",
            rule_id=rule_res.matched_rule.id if rule_res.matched_rule else None,
            action=rule_res.action.value.upper(),
        )
    )
    step_idx += 1

    # Jika DROP, paket dihentikan di router (tidak dilanjutkan)
    if rule_res.action == Action.DROP:
        return SimulationResult(
            test_id=packet.id,
            decision=Decision.DROP,
            reason=rule_res.reason,
            matched_rule_id=rule_res.matched_rule.id if rule_res.matched_rule else None,
            trace=tuple(trace_steps),
            config_revision=state.config_revision,
            timestamp=ts,
            evaluated_rules=rule_res.evaluated_rule_ids,
        )

    # Jika ACCEPT, lanjutkan paket ke host tujuan via L2
    if l2_from_router is not None:
        for link_id, u, v in l2_from_router:
            u_iface = state.get_interface(u)
            v_iface = state.get_interface(v)
            desc = f"L2 egress hop: {u_iface.name if u_iface else u} -> {v_iface.name if v_iface else v}"
            if link_id:
                desc += f" (Link {link_id})"
            dev_id = u_iface.device_id if u_iface else router.id
            trace_steps.append(
                TraceStep(
                    step_number=step_idx,
                    device_id=dev_id,
                    description=desc,
                    link_id=link_id,
                )
            )
            step_idx += 1

    trace_steps.append(
        TraceStep(
            step_number=step_idx,
            device_id=dst_dev.id if dst_dev else "unknown",
            description=f"Paket diterima dengan sukses di tujuan {dst_dev.name if dst_dev else dst_ip_str}.",
            action="ACCEPT",
        )
    )

    return SimulationResult(
        test_id=packet.id,
        decision=Decision.ACCEPT,
        reason=rule_res.reason,
        matched_rule_id=rule_res.matched_rule.id if rule_res.matched_rule else None,
        trace=tuple(trace_steps),
        config_revision=state.config_revision,
        timestamp=ts,
        evaluated_rules=rule_res.evaluated_rule_ids,
    )
