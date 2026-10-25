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
    """Menampilkan banner permanen bahwa seluruh aktivitas adalah simulasi virtual."""
    st.warning(
        "⚠️ **SIMULASI VIRTUAL**: Seluruh paket, aturan firewall, dan perangkat dalam aplikasi ini "
        "adalah simulasi virtual. Tidak ada koneksi atau modifikasi terhadap perangkat jaringan nyata."
    )


def render_error_box(errors: List[str]) -> None:
    """Render a formatted error box with a list of messages."""
    if errors:
        with st.container(border=True):
            st.error("Terjadi kesalahan pada konfigurasi:")
            for err in errors:
                st.markdown(f"- {err}")


def page_header(title: str, description: Optional[str] = None) -> None:
    """Standard page header with title, one-line purpose description, and status badges."""
    init_session_state()
    state = get_state()
    mode = get_ui_mode()
    validation_errors = validate_topology(state)
    is_valid = (len(validation_errors) == 0)

    col1, col2 = st.columns([3, 2])
    with col1:
        st.title(title)
        if description:
            st.caption(description)

    with col2:
        c1, c2, c3 = st.columns(3)
        with c1:
            st.badge(f"Rev #{state.config_revision}", icon=":material/tag:", color="blue")
        with c2:
            mode_icon = ":material/school:" if mode == "Learning" else ":material/work:"
            st.badge(f"{mode}", icon=mode_icon, color="gray")
        with c3:
            if is_valid:
                st.badge("Valid", icon=":material/check_circle:", color="green")
            else:
                st.badge("Warning", icon=":material/warning:", color="orange")


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
        "ACCEPT": ("green", ":material/check_circle:", COLOR_ALLOW, "🟢 ACCEPT (Lolos)"),
        "DROP": ("red", ":material/cancel:", COLOR_DENY, "🔴 DROP (Ditolak)"),
        "NO_ROUTE": ("orange", ":material/alt_route:", COLOR_AMBER, "⚠️ NO_ROUTE (Rute Kosong)"),
        "INVALID_CONFIG": ("orange", ":material/error:", COLOR_AMBER, "❌ INVALID_CONFIG (Konfigurasi Salah)"),
        "UNSUPPORTED_CASE": ("gray", ":material/help:", COLOR_MUTED, "❓ UNSUPPORTED (Kasus Belum Didukung)"),
    }

    badge_color, badge_icon, hex_color, full_text = color_map.get(
        val, ("gray", ":material/info:", COLOR_MUTED, f"ℹ️ {val}")
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
