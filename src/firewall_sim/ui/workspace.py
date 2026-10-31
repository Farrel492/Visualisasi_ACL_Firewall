"""Penyimpanan workspace otomatis agar pekerjaan tidak hilang saat halaman di-refresh.

Cara kerja:
- Setiap browser mendapat token acak yang ditaruh di URL (?w=<token>). Refresh tetap
  membawa token yang sama, sehingga workspace yang sama dimuat kembali.
- Isi workspace (topologi, rule, riwayat uji, log, tata letak, kabel, sesi CLI) ditulis
  ke data/workspaces/<token>.json setiap kali ada perubahan.
- Berkas lama (lebih dari 30 hari) dibersihkan otomatis.

Modul ini hanya memakai pustaka standar dan storage.json_store untuk ProjectState.
"""

from __future__ import annotations

from datetime import datetime
import json
import os
from pathlib import Path
import re
import secrets
import time
from typing import Any, Dict, List, Optional, Tuple

from firewall_sim.core.analytics import TrafficLogEntry
from firewall_sim.core.models import (
    Decision,
    PacketTest,
    Protocol,
    SecurityEvent,
    SimulationResult,
    TraceStep,
)
from firewall_sim.storage.json_store import load_project, save_project

WORKSPACE_VERSION = 1
MAX_AGE_DAYS = 30
_TOKEN_RE = re.compile(r"^[A-Za-z0-9_-]{6,40}$")


def workspace_dir() -> Path:
    base = os.environ.get("FW_DATA_DIR")
    root = Path(base) if base else Path(__file__).resolve().parents[3] / "data"
    path = root / "workspaces"
    path.mkdir(parents=True, exist_ok=True)
    return path


def new_token() -> str:
    return secrets.token_urlsafe(8)


def is_valid_token(token: Optional[str]) -> bool:
    return bool(token) and bool(_TOKEN_RE.match(token or ""))


def workspace_path(token: str) -> Path:
    return workspace_dir() / f"{token}.json"


def cleanup_old(max_age_days: int = MAX_AGE_DAYS) -> int:
    """Hapus berkas workspace yang tidak disentuh lebih dari max_age_days."""
    removed = 0
    limit = time.time() - max_age_days * 86400
    try:
        for p in workspace_dir().glob("*.json"):
            try:
                if p.stat().st_mtime < limit:
                    p.unlink()
                    removed += 1
            except OSError:
                continue
    except OSError:
        return removed
    return removed


# --------------------------------------------------------------------------- serialisasi


def _dt(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if value else None


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _packet_to_dict(p: PacketTest) -> Dict[str, Any]:
    return {
        "id": p.id,
        "source_device_id": p.source_device_id,
        "destination_device_id": p.destination_device_id,
        "destination_ip": p.destination_ip,
        "protocol": p.protocol.value,
        "src_port": p.src_port,
        "dst_port": p.dst_port,
        "timestamp": _dt(p.timestamp),
        "config_revision": p.config_revision,
    }


def _packet_from_dict(d: Dict[str, Any]) -> PacketTest:
    return PacketTest(
        id=d["id"],
        source_device_id=d["source_device_id"],
        destination_device_id=d.get("destination_device_id"),
        destination_ip=d.get("destination_ip"),
        protocol=Protocol(d.get("protocol", "tcp")),
        src_port=d.get("src_port"),
        dst_port=d.get("dst_port"),
        timestamp=_parse_dt(d.get("timestamp")),
        config_revision=int(d.get("config_revision", 0)),
    )


def _result_to_dict(r: SimulationResult) -> Dict[str, Any]:
    return {
        "test_id": r.test_id,
        "decision": r.decision.value,
        "reason": r.reason,
        "matched_rule_id": r.matched_rule_id,
        "config_revision": r.config_revision,
        "timestamp": _dt(r.timestamp),
        "evaluated_rules": list(r.evaluated_rules),
        "trace": [
            {
                "step_number": s.step_number,
                "device_id": s.device_id,
                "description": s.description,
                "rule_id": s.rule_id,
                "action": s.action,
                "link_id": s.link_id,
            }
            for s in r.trace
        ],
    }


def _result_from_dict(d: Dict[str, Any]) -> SimulationResult:
    return SimulationResult(
        test_id=d["test_id"],
        decision=Decision(d["decision"]),
        reason=d.get("reason", ""),
        matched_rule_id=d.get("matched_rule_id"),
        trace=tuple(
            TraceStep(
                step_number=int(s["step_number"]),
                device_id=s["device_id"],
                description=s.get("description", ""),
                rule_id=s.get("rule_id"),
                action=s.get("action"),
                link_id=s.get("link_id"),
            )
            for s in d.get("trace", [])
        ),
        config_revision=int(d.get("config_revision", 0)),
        timestamp=_parse_dt(d.get("timestamp")) or datetime.now(),
        evaluated_rules=tuple(d.get("evaluated_rules", [])),
    )


def _log_to_dict(e: TrafficLogEntry) -> Dict[str, Any]:
    return {
        "id": e.id,
        "timestamp": _dt(e.timestamp),
        "source_device": e.source_device,
        "destination_target": e.destination_target,
        "protocol": e.protocol.value,
        "src_port": e.src_port,
        "dst_port": e.dst_port,
        "decision": e.decision.value,
        "matched_rule_id": e.matched_rule_id,
        "reason": e.reason,
        "config_revision": e.config_revision,
    }


def _log_from_dict(d: Dict[str, Any]) -> TrafficLogEntry:
    return TrafficLogEntry(
        id=d["id"],
        timestamp=_parse_dt(d.get("timestamp")) or datetime.now(),
        source_device=d["source_device"],
        destination_target=d["destination_target"],
        protocol=Protocol(d.get("protocol", "tcp")),
        src_port=d.get("src_port"),
        dst_port=d.get("dst_port"),
        decision=Decision(d["decision"]),
        matched_rule_id=d.get("matched_rule_id"),
        reason=d.get("reason", ""),
        config_revision=int(d.get("config_revision", 0)),
    )


def _event_to_dict(e: SecurityEvent) -> Dict[str, Any]:
    return {
        "id": e.id,
        "test_id": e.test_id,
        "event_type": e.event_type,
        "severity": e.severity,
        "timestamp": _dt(e.timestamp),
        "message": e.message,
        "device_id": e.device_id,
        "rule_id": e.rule_id,
        "acknowledged": e.acknowledged,
    }


def _event_from_dict(d: Dict[str, Any]) -> SecurityEvent:
    return SecurityEvent(
        id=d["id"],
        test_id=d["test_id"],
        event_type=d["event_type"],
        severity=d["severity"],
        timestamp=_parse_dt(d.get("timestamp")) or datetime.now(),
        message=d.get("message", ""),
        device_id=d.get("device_id"),
        rule_id=d.get("rule_id"),
        acknowledged=bool(d.get("acknowledged", False)),
    )


def snapshot_to_json(snap: Dict[str, Any]) -> str:
    """Ubah snapshot sesi (objek domain) menjadi teks JSON."""
    data = {
        "workspace_version": WORKSPACE_VERSION,
        "saved_at": datetime.now().isoformat(),
        "project": json.loads(save_project(snap["state"])),
        "pairs": [
            {"packet": _packet_to_dict(p), "result": _result_to_dict(r)}
            for p, r in snap.get("pairs", [])
        ],
        "logs": [_log_to_dict(e) for e in snap.get("logs", [])],
        "events": [_event_to_dict(e) for e in snap.get("events", [])],
        "cli_log": [list(x) for x in snap.get("cli_log", [])],
        "layout": snap.get("layout", {}),
        "cables": snap.get("cables", {}),
        "cli_sessions": snap.get("cli_sessions", {}),
    }
    return json.dumps(data, ensure_ascii=False, indent=1)


def snapshot_from_json(text: str) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    """Baca teks JSON menjadi snapshot. Berkas rusak menghasilkan error, bukan crash."""
    try:
        data = json.loads(text)
    except Exception as exc:  # noqa: BLE001
        return None, [f"Berkas workspace rusak: {exc}"]
    if not isinstance(data, dict) or "project" not in data:
        return None, ["Berkas workspace tidak berisi proyek."]

    state, errors = load_project(json.dumps(data["project"]))
    if state is None:
        return None, errors or ["Proyek di workspace tidak valid."]

    try:
        pairs = [
            (_packet_from_dict(x["packet"]), _result_from_dict(x["result"]))
            for x in data.get("pairs", [])
        ]
        logs = [_log_from_dict(x) for x in data.get("logs", [])]
        events = [_event_from_dict(x) for x in data.get("events", [])]
    except Exception as exc:  # noqa: BLE001
        return None, [f"Riwayat workspace tidak terbaca: {exc}"]

    snap = {
        "state": state,
        "pairs": pairs,
        "logs": logs,
        "events": events,
        "cli_log": [tuple(x) for x in data.get("cli_log", [])],
        "layout": data.get("layout", {}),
        "cables": data.get("cables", {}),
        "cli_sessions": data.get("cli_sessions", {}),
    }
    return snap, []


# --------------------------------------------------------------------------- berkas


def write_snapshot(token: str, snap: Dict[str, Any]) -> bool:
    """Tulis atomik: tulis ke berkas sementara lalu ganti, agar tidak setengah tertulis."""
    if not is_valid_token(token):
        return False
    try:
        path = workspace_path(token)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(snapshot_to_json(snap), encoding="utf-8")
        os.replace(tmp, path)
        return True
    except OSError:
        return False


def read_snapshot(token: str) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    if not is_valid_token(token):
        return None, ["Token workspace tidak valid."]
    path = workspace_path(token)
    if not path.exists():
        return None, []
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return None, [f"Workspace tidak dapat dibaca: {exc}"]
    return snapshot_from_json(text)


def delete_workspace(token: str) -> None:
    if is_valid_token(token):
        try:
            workspace_path(token).unlink()
        except OSError:
            pass
