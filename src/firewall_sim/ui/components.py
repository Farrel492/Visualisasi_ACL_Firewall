"""Shared UI presentation components and design system helpers."""

from __future__ import annotations

from typing import Callable, List, Optional, Union
import streamlit as st

from firewall_sim.core.models import Decision
from firewall_sim.core.validation import validate_topology
from firewall_sim.ui.state import get_state, get_ui_mode, init_session_state
from firewall_sim.ui.theme import (
    COLOR_ALLOW,
    COLOR_AMBER,
    COLOR_DENY,
    COLOR_MUTED,
    COLOR_SURFACE,
    SPACING_MD,
    inject_theme_css,
)

GLOSSARY = {
    "chain": "Jalur traversal paket (INPUT: menuju router, FORWARD: melintasi router, OUTPUT: keluar dari router).",
    "ACCEPT": "Paket diizinkan lewat oleh aturan firewall atau default policy.",
    "DROP": "Paket ditolak dan dibuang diam-diam oleh firewall.",
    "NO_ROUTE": "Rute tidak ditemukan / gateway tidak dapat menjangkau subnet tujuan.",
    "INVALID_CONFIG": "Konfigurasi topologi atau parameter paket tidak valid.",
    "UNSUPPORTED_CASE": "Skenario belum didukung dalam simulasi saat ini.",
    "config_revision": "Nomor revisi konfigurasi atomik yang bertambah di setiap mutasi topologi/rule.",
    "default policy": "Aksi cadangan (fallback) per chain jika tidak ada rule yang cocok (first-match).",
    "first matching terminal action wins": "Aturan dievaluasi berurutan dari atas ke bawah; aturan pertama yang cocok langsung menentukan keputusan.",
}


def render_simulation_banner() -> None:
    """Menampilkan banner ringkas satu baris bahwa seluruh aktivitas adalah simulasi virtual."""
    col1, col2 = st.columns([5, 1])
    with col1:
        st.info(
            "Mode simulasi: tidak ada koneksi ke jaringan nyata.",
            icon=":material/info:",
        )
    with col2:
        with st.popover("Apa artinya?"):
            st.markdown(
                "Seluruh perangkat, interface, paket, dan aturan firewall dalam lab ini "
                "berjalan murni dalam memori simulasi Python. Tidak ada perangkat fisik, "
                "sistem operasi host, atau kartu jaringan nyata yang terpengaruh."
            )


def render_error_box(errors: List[str]) -> None:
    """Render a formatted error box with a list of messages."""
    if errors:
        with st.container(border=True):
            st.error("Terjadi kesalahan pada konfigurasi:")
            for err in errors:
                st.markdown(f"- {err}")


def page_header(title: str, description: Optional[str] = None) -> None:
    """Standard page header with navigation-matching title and 1-sentence purpose description."""
    init_session_state()
    st.markdown(inject_theme_css(), unsafe_allow_html=True)
    st.title(title)
    if description:
        st.caption(description)


def render_workflow_rail(current_page: str) -> None:
    """Merender bilah alur kerja horizontal 5 langkah yang memandu pengguna:
    1. Build (network) -> 2. Configure (firewall_rules) -> 3. Simulate (packet_sim) -> 4. Visualize (viz3d) -> 5. Analyze (traffic_logs).
    """
    steps = [
        ("network", "1", "Build", "Topologi"),
        ("firewall_rules", "2", "Configure", "Aturan"),
        ("packet_sim", "3", "Simulate", "Uji Paket"),
        ("viz3d", "4", "Visualize", "3D Replay"),
        ("traffic_logs", "5", "Analyze", "Log & Audit"),
    ]
    items_html = []
    for page_id, num, eng_name, id_name in steps:
        is_active = (current_page == page_id)
        active_cls = " active" if is_active else ""
        items_html.append(
            f"<div class='fw-step-item{active_cls}'>"
            f"<span class='fw-step-num'>{num}</span>"
            f"<span><strong>{eng_name}</strong> <span style='opacity:0.7;'>({id_name})</span></span>"
            f"</div>"
        )
    sep = "<span class='fw-step-arrow' style='padding:0 0.25rem;'>&rarr;</span>"
    rail_html = f"<div class='fw-workflow-rail'>{''.join([f'{item}{sep}' if i < len(items_html)-1 else item for i, item in enumerate(items_html)])}</div>"
    st.markdown(rail_html, unsafe_allow_html=True)


def render_flow_next(next_page_id: str, next_label: str, hint: Optional[str] = None) -> None:
    """Menampilkan tombol navigasi alur kerja berikutnya di akhir konten halaman."""
    st.markdown("---")
    c_info, c_btn = st.columns([3, 1.2])
    with c_info:
        if hint:
            st.caption(f":material/arrow_forward: **Langkah Berikutnya:** {hint}")
    with c_btn:
        if st.button(f"Lanjut: {next_label}", icon=":material/navigate_next:", type="primary", use_container_width=True, key=f"btn_flow_next_{next_page_id}"):
            st.session_state["nav_page"] = next_page_id
            st.rerun()



def card(content: str, *, icon: str = "", background: str = COLOR_SURFACE) -> None:
    """Render a card container with optional icon and background colour."""
    icon_html = f"<span class='fw-card-icon'>{icon}</span> " if icon else ""
    st.markdown(
        f"""
        <div class="fw-card" style='background:{background}; padding:{SPACING_MD}; border-radius:0.75rem; border:1px solid #334155; margin-bottom:0.75rem;'>
            {icon_html}{content}
        </div>
        """,
        unsafe_allow_html=True,
    )


def status_badge(decision: Union[str, Decision], render: bool = False) -> str:
    """Return an accessible text+icon badge for a simulation Decision.

    If render=True, also renders the native st.badge directly.
    """
    val = decision.value if isinstance(decision, Decision) else str(decision).upper()

    color_map = {
        "ACCEPT": ("green", ":material/check_circle:", COLOR_ALLOW, "ACCEPT (Lolos)"),
        "DROP": ("red", ":material/cancel:", COLOR_DENY, "DROP (Ditolak)"),
        "NO_ROUTE": ("orange", ":material/alt_route:", COLOR_AMBER, "NO_ROUTE (Rute Kosong)"),
        "INVALID_CONFIG": ("orange", ":material/error:", COLOR_AMBER, "INVALID_CONFIG (Konfigurasi Salah)"),
        "UNSUPPORTED_CASE": ("gray", ":material/help:", COLOR_MUTED, "UNSUPPORTED (Kasus Belum Didukung)"),
    }

    badge_color, badge_icon, hex_color, full_text = color_map.get(
        val, ("gray", ":material/info:", COLOR_MUTED, f"{val}")
    )

    if render:
        st.badge(val, icon=badge_icon, color=badge_color)

    return f"<span class='fw-badge' style='display:inline-block;padding:2px 8px;border-radius:6px;background:{hex_color}22;color:{hex_color};font-weight:600;border:1px solid {hex_color}55;'>{full_text}</span>"


def metric_row(label: str, value: str, icon: Optional[str] = None) -> None:
    """Render a metric row (label + value) using Streamlit metric."""
    label_text = f"{icon} {label}" if icon else label
    st.metric(label=label_text, value=value, border=True)


def empty_state(
    message: str,
    action_label: str,
    target_page_or_callback: Union[str, Callable],
    key: Optional[str] = None,
    icon: str = ":material/inbox:",
) -> None:
    """Show an empty state container with an icon, message, and action button."""
    with st.container(border=True):
        st.markdown(f"### {icon}")
        st.write(message)
        btn_key = key or f"empty_btn_{action_label.lower().replace(' ', '_')}"
        if st.button(action_label, key=btn_key, type="primary"):
            if callable(target_page_or_callback):
                target_page_or_callback()
            else:
                st.session_state["nav_page"] = target_page_or_callback
                st.rerun()


def next_steps(steps: List[tuple[str, str]]) -> None:
    """Render a list of next-step navigation buttons."""
    with st.container(border=True):
        st.markdown("#### :material/arrow_forward: Langkah Berikutnya")
        for label, page in steps:
            clean_key = f"next_{page}_{label.lower().replace(' ', '_')}"
            if st.button(label, key=clean_key, use_container_width=True):
                st.session_state["nav_page"] = page
                st.rerun()


def tooltip(text: str, hover: Optional[str] = None) -> None:
    """Render an inline glossary tooltip."""
    explanation = hover or GLOSSARY.get(text, hover) or ""
    if explanation:
        st.caption(f":material/info: **{text}**: {explanation}")
    else:
        st.caption(f":material/info: {text}")
