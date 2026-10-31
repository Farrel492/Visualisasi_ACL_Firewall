"""Helper topologi untuk UI: tata letak, penamaan interface gaya Cisco, jenis kabel.

Semua fungsi murni (tanpa Streamlit) agar mudah diuji.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from firewall_sim.core.models import (
    Device,
    DeviceType,
    Interface,
    Link,
    ProjectState,
    SimulationResult,
)

CANVAS_W = 1000
CANVAS_H = 560

CABLE_FA = "fa"
CABLE_SE = "se"
CABLE_LABELS = {
    CABLE_FA: "FastEthernet (kabel straight/cross)",
    CABLE_SE: "Serial (kabel DCE/DTE)",
}
CABLE_SHORT = {CABLE_FA: "Fa", CABLE_SE: "Se"}

TYPE_LABELS = {
    DeviceType.PC: "PC",
    DeviceType.SERVER: "Server",
    DeviceType.ROUTER: "Router firewall",
    DeviceType.SWITCH: "Switch 24 port",
}

_TIER_X = {
    DeviceType.PC: 120.0,
    DeviceType.SWITCH: 350.0,
    DeviceType.ROUTER: 590.0,
    DeviceType.SERVER: 860.0,
}


def type_label(dtype: DeviceType) -> str:
    return TYPE_LABELS.get(dtype, dtype.value)


# --------------------------------------------------------------------------- interface


def default_interfaces(dev_id: str, dtype: DeviceType) -> Tuple[Interface, ...]:
    """Interface bawaan perangkat baru, bernama seperti perangkat Cisco."""
    if dtype == DeviceType.SWITCH:
        return tuple(
            Interface(id=f"if_{dev_id}_p{n}", device_id=dev_id, name=f"Fa0/{n}", ipv4_cidr=None)
            for n in range(1, 25)
        )
    if dtype == DeviceType.ROUTER:
        return (
            Interface(id=f"if_{dev_id}_fa00", device_id=dev_id, name="Fa0/0"),
            Interface(id=f"if_{dev_id}_fa01", device_id=dev_id, name="Fa0/1"),
            Interface(id=f"if_{dev_id}_se00", device_id=dev_id, name="Se0/0"),
            Interface(id=f"if_{dev_id}_se01", device_id=dev_id, name="Se0/1"),
        )
    return (Interface(id=f"if_{dev_id}_fa0", device_id=dev_id, name="Fa0"),)


def interface_kind(iface: Interface) -> str:
    """Jenis port dari namanya: 'se' untuk Serial, selain itu 'fa'."""
    name = iface.name.lower()
    if name.startswith("se") or name.startswith("serial"):
        return CABLE_SE
    return CABLE_FA


def linked_interface_ids(state: ProjectState) -> set:
    ids = set()
    for link in state.links:
        ids.add(link.interface_a)
        ids.add(link.interface_b)
    return ids


def free_interfaces(state: ProjectState, device_id: str, kind: Optional[str] = None) -> List[Interface]:
    dev = state.get_device(device_id)
    if dev is None:
        return []
    used = linked_interface_ids(state)
    out = []
    for iface in dev.interfaces:
        if iface.id in used:
            continue
        if kind and interface_kind(iface) != kind:
            continue
        out.append(iface)
    return out


def iface_label(iface: Interface) -> str:
    return iface.name


def find_device_of_interface(state: ProjectState, iface_id: str) -> Optional[Device]:
    for dev in state.devices:
        for iface in dev.interfaces:
            if iface.id == iface_id:
                return dev
    return None


def link_kind(state: ProjectState, link: Link, cables: Dict[str, str]) -> str:
    """Jenis kabel sebuah link: dari metadata, atau diturunkan dari nama interface."""
    if link.id in cables:
        return cables[link.id]
    ia = state.get_interface(link.interface_a)
    if ia is not None:
        return interface_kind(ia)
    return CABLE_FA


def link_description(state: ProjectState, link: Link, cables: Dict[str, str]) -> str:
    ia = state.get_interface(link.interface_a)
    ib = state.get_interface(link.interface_b)
    da = find_device_of_interface(state, link.interface_a)
    db = find_device_of_interface(state, link.interface_b)
    if not (ia and ib and da and db):
        return link.id
    kind = CABLE_SHORT[link_kind(state, link, cables)]
    return f"{da.name} {ia.name}  ke  {db.name} {ib.name}  ({kind})"


# --------------------------------------------------------------------------- layout


def resolve_layout(state: ProjectState, saved: Dict[str, List[float]]) -> Dict[str, List[float]]:
    """Posisi (x, y) tiap perangkat pada kanvas logis 1000x560.

    Posisi yang sudah disimpan pengguna dipakai apa adanya. Perangkat tanpa posisi
    ditempatkan per tingkat: PC di kiri, switch, router, lalu server di kanan.
    """
    layout: Dict[str, List[float]] = {}
    for dev in state.devices:
        if dev.id in saved:
            x, y = saved[dev.id][0], saved[dev.id][1]
            layout[dev.id] = [min(max(float(x), 50.0), CANVAS_W - 50.0), min(max(float(y), 60.0), CANVAS_H - 60.0)]

    tiers: Dict[DeviceType, List[Device]] = {}
    for dev in state.devices:
        tiers.setdefault(dev.type, []).append(dev)

    for dtype, devs in tiers.items():
        pending = [d for d in devs if d.id not in layout]
        if not pending:
            continue
        taken_y = [layout[d.id][1] for d in devs if d.id in layout]
        count = len(devs)
        step = (CANVAS_H - 160.0) / max(count - 1, 1) if count > 1 else 0.0
        for idx, dev in enumerate(devs):
            if dev.id in layout:
                continue
            y = CANVAS_H / 2.0 if count == 1 else 80.0 + step * idx
            while any(abs(y - t) < 70.0 for t in taken_y):
                y += 80.0
                if y > CANVAS_H - 70.0:
                    y = 80.0 + (len(taken_y) % 5) * 15.0
                    break
            taken_y.append(y)
            layout[dev.id] = [_TIER_X.get(dtype, 500.0), round(y, 1)]
    return layout


# --------------------------------------------------------------------------- data komponen


def path_from_result(result: Optional[SimulationResult]) -> List[str]:
    """Urutan perangkat yang dilalui paket (tanpa duplikat berurutan)."""
    if result is None:
        return []
    path: List[str] = []
    for step in result.trace:
        if not path or path[-1] != step.device_id:
            path.append(step.device_id)
    return path


def component_payload(
    state: ProjectState,
    layout: Dict[str, List[float]],
    cables: Dict[str, str],
    result: Optional[SimulationResult] = None,
    selected: Optional[str] = None,
    editable: bool = True,
) -> Dict[str, Any]:
    """Data JSON untuk komponen topologi 2D dan scene 3D."""
    used = linked_interface_ids(state)
    devices = []
    for dev in state.devices:
        pos = layout.get(dev.id, [CANVAS_W / 2, CANVAS_H / 2])
        ips = [i.ipv4_cidr for i in dev.interfaces if i.ipv4_cidr]
        devices.append(
            {
                "id": dev.id,
                "name": dev.name,
                "type": dev.type.value,
                "x": pos[0],
                "y": pos[1],
                "ip": ips[0] if ips else "",
                "ports_used": len([i for i in dev.interfaces if i.id in used]),
                "ports_total": len(dev.interfaces),
            }
        )
    links = []
    for link in state.links:
        da = find_device_of_interface(state, link.interface_a)
        db = find_device_of_interface(state, link.interface_b)
        ia = state.get_interface(link.interface_a)
        ib = state.get_interface(link.interface_b)
        if not (da and db and ia and ib):
            continue
        links.append(
            {
                "id": link.id,
                "a": da.id,
                "b": db.id,
                "a_if": ia.name,
                "b_if": ib.name,
                "kind": link_kind(state, link, cables),
                "enabled": link.enabled,
            }
        )
    replay = None
    if result is not None:
        replay = {
            "test_id": result.test_id,
            "decision": result.decision.value,
            "path": path_from_result(result),
            "reason": result.reason,
            "steps": [
                {"device": s.device_id, "text": s.description, "action": s.action} for s in result.trace
            ],
        }
    return {
        "devices": devices,
        "links": links,
        "replay": replay,
        "selected": selected,
        "editable": editable,
        "revision": state.config_revision,
        "canvas": [CANVAS_W, CANVAS_H],
    }
