"""JSON storage service for Firewall Simulator project state persistence.

ATURAN ARSITEKTUR:
- Murni Python standard library (menggunakan modul json).
- Menyimpan skema versi eksplisit (schema_version).
- Load memvalidasi struktur data dan validate_topology.
- File korup atau tidak valid mengembalikan pesan error yang jelas dan tidak merusak state aktif.
"""

from __future__ import annotations

from datetime import datetime
import json
from typing import Any, Dict, List, Optional, Tuple

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
    Protocol,
)
from firewall_sim.core.validation import validate_topology

CURRENT_SCHEMA_VERSION = "1.0"


def save_project(state: ProjectState) -> str:
    """Mengonversi ProjectState ke format JSON string terstruktur."""
    data: Dict[str, Any] = {
        "schema_version": CURRENT_SCHEMA_VERSION,
        "config_revision": state.config_revision,
        "scenario_metadata": list(state.scenario_metadata),
        "default_policies": [[c.value, a.value] for c, a in state.default_policies],
        "devices": [
            {
                "id": d.id,
                "name": d.name,
                "type": d.type.value,
                "default_gateway": d.default_gateway,
                "interfaces": [
                    {
                        "id": i.id,
                        "device_id": i.device_id,
                        "name": i.name,
                        "ipv4_cidr": i.ipv4_cidr,
                        "enabled": i.enabled,
                    }
                    for i in d.interfaces
                ],
            }
            for d in state.devices
        ],
        "links": [
            {
                "id": l.id,
                "interface_a": l.interface_a,
                "interface_b": l.interface_b,
                "enabled": l.enabled,
            }
            for l in state.links
        ],
        "rules": [
            {
                "id": r.id,
                "order": r.order,
                "enabled": r.enabled,
                "chain": r.chain.value,
                "src_cidr": r.src_cidr,
                "dst_cidr": r.dst_cidr,
                "protocol": r.protocol.value,
                "src_port": r.src_port,
                "dst_port": r.dst_port,
                "action": r.action.value,
                "comment": r.comment,
                "counter": r.counter,
            }
            for r in state.rules
        ],
        "audit_log": [
            {
                "timestamp": a.timestamp.isoformat(),
                "source": a.source,
                "summary": a.summary,
            }
            for a in state.audit_log
        ],
    }
    return json.dumps(data, indent=2)


def load_project(text: str) -> Tuple[Optional[ProjectState], List[str]]:
    """Mem-parse string JSON dan memuatnya ke dalam instance ProjectState yang divalidasi.

    Returns:
        (state, errors): state bernilai None jika terjadi error validasi atau parsing.
    """
    if not text.strip():
        return None, ["File JSON kosong."]

    try:
        data = json.loads(text)
    except Exception as e:
        return None, [f"Format JSON tidak valid / rusak: {e}"]

    if not isinstance(data, dict):
        return None, ["Struktur data JSON harus berupa objek dictionary."]

    schema_ver = data.get("schema_version")
    if not schema_ver:
        return None, ["Field 'schema_version' tidak ditemukan pada berkas JSON."]

    try:
        config_revision = int(data.get("config_revision", 1))

        # Metadata
        raw_meta = data.get("scenario_metadata", [])
        scenario_metadata = tuple((str(k), str(v)) for k, v in raw_meta)

        # Default policies
        raw_policies = data.get("default_policies", [])
        policies: List[Tuple[Chain, Action]] = []
        for item in raw_policies:
            policies.append((Chain(item[0]), Action(item[1])))
        if not policies:
            policies = [
                (Chain.INPUT, Action.ACCEPT),
                (Chain.FORWARD, Action.ACCEPT),
                (Chain.OUTPUT, Action.ACCEPT),
            ]

        # Devices & Interfaces
        devices: List[Device] = []
        for d in data.get("devices", []):
            ifaces: List[Interface] = []
            for i in d.get("interfaces", []):
                ifaces.append(
                    Interface(
                        id=str(i["id"]),
                        device_id=str(i.get("device_id", d["id"])),
                        name=str(i["name"]),
                        ipv4_cidr=str(i["ipv4_cidr"]) if i.get("ipv4_cidr") else None,
                        enabled=bool(i.get("enabled", True)),
                    )
                )
            devices.append(
                Device(
                    id=str(d["id"]),
                    name=str(d["name"]),
                    type=DeviceType(d["type"]),
                    interfaces=tuple(ifaces),
                    default_gateway=str(d["default_gateway"]) if d.get("default_gateway") else None,
                )
            )

        # Links
        links: List[Link] = []
        for l in data.get("links", []):
            links.append(
                Link(
                    id=str(l["id"]),
                    interface_a=str(l["interface_a"]),
                    interface_b=str(l["interface_b"]),
                    enabled=bool(l.get("enabled", True)),
                )
            )

        # Rules
        rules: List[FirewallRule] = []
        for r in data.get("rules", []):
            rules.append(
                FirewallRule(
                    id=str(r["id"]),
                    order=int(r["order"]),
                    enabled=bool(r.get("enabled", True)),
                    chain=Chain(r["chain"]),
                    src_cidr=str(r["src_cidr"]) if r.get("src_cidr") else None,
                    dst_cidr=str(r["dst_cidr"]) if r.get("dst_cidr") else None,
                    protocol=Protocol(r.get("protocol", "any")),
                    src_port=str(r["src_port"]) if r.get("src_port") else None,
                    dst_port=str(r["dst_port"]) if r.get("dst_port") else None,
                    action=Action(r["action"]),
                    comment=str(r.get("comment", "")),
                    counter=int(r.get("counter", 0)),
                )
            )

        # Audit log
        audit_log: List[AuditEntry] = []
        for a in data.get("audit_log", []):
            try:
                dt = datetime.fromisoformat(a["timestamp"])
            except Exception:
                dt = datetime.now()
            audit_log.append(
                AuditEntry(
                    timestamp=dt,
                    source=str(a.get("source", "IMPORT")),
                    summary=str(a.get("summary", "")),
                )
            )

        candidate_state = ProjectState(
            devices=tuple(devices),
            links=tuple(links),
            rules=tuple(rules),
            config_revision=config_revision,
            default_policies=tuple(policies),
            scenario_metadata=scenario_metadata,
            audit_log=tuple(audit_log),
        )

        # Validasi topologi hasil parsing
        val_errors = validate_topology(candidate_state)
        if val_errors:
            err_msgs = [f"[{e.code}] {e.message}" for e in val_errors]
            return None, err_msgs

        return candidate_state, []

    except Exception as e:
        return None, [f"Gagal memetakan konfigurasi proyek: {e}"]
