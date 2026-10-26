"""Security Alert Center page."""

from __future__ import annotations

import streamlit as st

from firewall_sim.ui.components import (
    empty_state,
    next_steps,
    page_header,
    render_simulation_banner,
)
from firewall_sim.ui.state import (
    KEY_ALERT_HIGHLIGHT,
    get_security_events,
)


def render_alerts_page() -> None:
    """Merender dasbor Pusat Peringatan Keamanan."""
    render_simulation_banner()
    page_header(
        title="Pusat Peringatan",
        description="Pemantauan event penolakan paket firewall virtual dan peninjauan insiden kebijakan keamanan.",
    )

    # Catatan Permanen Sesuai AGENTS.md & PRD Bagian 11/12
    st.warning(
        "**CATATAN KEBIJAKAN KEAMANAN**: Penolakan paket (DROP) merupakan perilaku normal "
        "dari kebijakan filter firewall dan **BUKAN OTOMATIS BERARTI SERANGAN / ANCAMAN (ATTACK)**.",
        icon=":material/policy:",
    )

    events = get_security_events()

    col_main, col_side = st.columns([2.2, 1.0])

    with col_main:
        # Toggle Konfigurasi Alert
        with st.container(border=True):
            highlight_active = st.session_state.get(KEY_ALERT_HIGHLIGHT, True)
            new_highlight = st.toggle(
                "Aktifkan penandaan otomatis setiap penolakan (DROP) sebagai alert keamanan",
                value=highlight_active,
                key="tgl_alert_highlight",
            )
            if new_highlight != highlight_active:
                st.session_state[KEY_ALERT_HIGHLIGHT] = new_highlight
                st.rerun()

        # Daftar Peringatan
        st.markdown(f"#### :material/notifications: Daftar Event Peringatan ({len(events)} tercatat)")

        if not events:
            empty_state(
                message="Tidak ada event penolakan atau alert keamanan yang tercatat saat ini. Event akan otomatis terbentuk setiap kali ada paket simulasi yang ditolak (DROP).",
                action_label="Jalankan Simulasi Paket",
                target_page_or_callback="packet_sim",
                key="empty_alerts_btn",
                icon=":material/security:",
            )
        else:
            for idx, ev in enumerate(events):
                sev_icon = ":material/warning:" if ev.severity == "warning" else ":material/info:"
                with st.expander(
                    f"{sev_icon} [{ev.severity.upper()}] Event #{ev.id} — {ev.timestamp.strftime('%H:%M:%S')}",
                    expanded=(idx == 0),
                ):
                    c1, c2 = st.columns(2)
                    with c1:
                        st.markdown(f"**Tipe Event:** `{ev.event_type}`")
                        st.markdown(f"**Perangkat Pengevaluasi:** `{ev.device_id or 'Router Firewall'}`")
                        st.markdown(f"**Rule Pemicu:** `{ev.rule_id or 'Default Policy DROP'}`")
                    with c2:
                        st.markdown(f"**Tingkat Keparahan:** `{ev.severity.upper()}`")
                        st.markdown(f"**Waktu Deteksi:** {ev.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
                        st.markdown(f"**Status Tinjauan:** `{'Sudah Ditinjau' if ev.acknowledged else 'Perlu Perhatian'}`")

                    st.markdown(f"**Rincian Pesan:**\n\n{ev.message}")

    with col_side:
        # Informasi Kebijakan & Langkah Berikutnya
        with st.container(border=True):
            st.markdown("#### :material/policy: Prinsip Audit Firewall")
            st.markdown(
                "- Setiap event DROP dikelompokkan sebagai audit trail keamanan.\n"
                "- Penolakan port tidak resmi adalah bagian dari prinsip *least privilege*.\n"
                "- Tidak ada penuduhan otomatis serangan siber tanpa korelasi anomali lanjutan (fitur P2)."
            )

        next_steps([
            ("Tinjau Log Trafik", "traffic_logs"),
            ("Periksa Aturan Firewall", "firewall_rules"),
            ("Jalankan Uji Paket Lain", "packet_sim"),
        ])
