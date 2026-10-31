"""Pembungkus komponen front-end buatan sendiri (topologi 2D dan scene 3D).

Komponen berupa halaman HTML lokal (tanpa CDN) yang berbicara dengan Streamlit lewat
protokol postMessage standar. Nilai balik dibedakan dengan 'nonce' agar tidak diproses dua kali.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

import streamlit.components.v1 as components

_FRONTEND = Path(__file__).resolve().parent / "frontend"

_topology = components.declare_component("fw_topology", path=str(_FRONTEND / "topology"))
_scene3d = components.declare_component("fw_scene3d", path=str(_FRONTEND / "scene3d"))


def topology_view(payload: Dict[str, Any], key: str, intro: bool = False) -> Optional[Dict[str, Any]]:
    """Tampilkan topologi 2D interaktif. Mengembalikan event terakhir dari komponen (atau None)."""
    return _topology(data=payload, intro=intro, key=key, default=None)


def scene3d_view(payload: Dict[str, Any], key: str) -> Optional[Dict[str, Any]]:
    """Tampilkan scene 3D (Three.js). Kontrol replay ada di dalam komponen, tanpa rerun."""
    return _scene3d(data=payload, key=key, default=None)


def apply_component_event(event: Optional[Dict[str, Any]], key: str) -> bool:
    """Terapkan event komponen (geser perangkat / pilih perangkat) tepat satu kali.

    Mengembalikan True bila ada perubahan yang perlu ditampilkan ulang (st.rerun).
    Event dibedakan dengan 'nonce' agar tidak diproses ulang pada rerun berikutnya.
    """
    import streamlit as st

    from firewall_sim.ui import state as ui_state

    if not event or not isinstance(event, dict):
        return False
    nonce_key = f"fw_sim_nonce_{key}"
    if st.session_state.get(nonce_key) == event.get("nonce"):
        return False
    st.session_state[nonce_key] = event.get("nonce")
    kind = event.get("type")
    if kind == "layout":
        ui_state.set_layout(event.get("positions", {}))
        if event.get("selected"):
            ui_state.set_selected_device(event["selected"])
        return True
    if kind == "select":
        ui_state.set_selected_device(event.get("id"))
        return True
    return False
