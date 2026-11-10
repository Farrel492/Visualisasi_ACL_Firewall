"""Pusat Peringatan: event penolakan paket (DROP) yang perlu ditinjau."""

from __future__ import annotations

import streamlit as st

from firewall_sim.ui.components import (
    empty_state,
    next_steps,
    page_header,
    render_flow_next,
    render_simulation_banner,
    render_workflow_rail,
)
from firewall_sim.ui.labels import device_name, friendly_text, rule_label
from firewall_sim.ui.state import (
    KEY_ALERT_HIGHLIGHT,
    acknowledge_security_events,
    clear_security_events,
    get_security_events,
    get_state,
)


@st.dialog("Kosongkan peringatan")
def _dialog_clear_alerts():
    st.write("Semua catatan peringatan akan dihapus. Log trafik tidak ikut terhapus.")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Ya, kosongkan", type="primary", key="btn_confirm_clear_alerts", width="stretch"):
            clear_security_events()
            st.toast("Daftar peringatan dikosongkan.")
            st.rerun()
    with c2:
        if st.button("Batal", key="btn_cancel_clear_alerts", width="stretch"):
            st.rerun()


def strip_html(events) -> str:
    waiting = sum(1 for e in events if not e.acknowledged)
    return (
        '<div class="fw-strip" translate="no">'
        f"<span><b>Peringatan</b> {len(events)}</span>"
        f'<span><i class="fw-led amber"></i><b>Perlu ditinjau</b> {waiting}</span>'
        f'<span><i class="fw-led ok"></i><b>Sudah ditinjau</b> {len(events) - waiting}</span>'
        "</div>"
    )


def event_rows(state, events):
    rows = []
    for ev in events:
        rows.append(
            {
                "Waktu": ev.timestamp.strftime("%H:%M:%S"),
                "Tingkat": ev.severity.upper(),
                "Perangkat": device_name(state, ev.device_id) if ev.device_id else "Router Firewall",
                "Penentu": rule_label(state, ev.rule_id) if ev.rule_id else "kebijakan default",
                "Pesan": friendly_text(state, ev.message),
                "Status": "sudah ditinjau" if ev.acknowledged else "perlu ditinjau",
            }
        )
    return rows


def render_alerts_page() -> None:
    render_simulation_banner()
    page_header(
        title="Pusat Peringatan",
        description="Event penolakan paket (DROP) dari simulasi, untuk ditinjau satu per satu.",
    )
    render_workflow_rail("alerts")

    # Catatan wajib (PRD bagian 11/12): DROP bukan otomatis serangan.
    st.warning(
        "**CATATAN KEBIJAKAN KEAMANAN**: Penolakan paket (DROP) merupakan perilaku normal "
        "dari kebijakan filter firewall dan **BUKAN OTOMATIS BERARTI SERANGAN / ANCAMAN (ATTACK)**.",
        icon=":material/policy:",
    )

    state = get_state()
    events = get_security_events()
    st.markdown(strip_html(events), unsafe_allow_html=True)

    col_main, col_side = st.columns([2.6, 1.0], gap="medium")
    with col_main:
        highlight_active = st.session_state.get(KEY_ALERT_HIGHLIGHT, True)
        new_highlight = st.toggle(
            "Tandai setiap penolakan (DROP) sebagai peringatan",
            value=highlight_active,
            key="tgl_alert_highlight",
            help="Jika dimatikan, uji berikutnya tidak lagi membuat peringatan baru.",
        )
        if new_highlight != highlight_active:
            st.session_state[KEY_ALERT_HIGHLIGHT] = new_highlight
            st.rerun()

        if not events:
            empty_state(
                message="Belum ada peringatan. Peringatan muncul otomatis setiap ada paket yang ditolak (DROP).",
                action_label="Jalankan Simulasi Paket",
                target_page_or_callback="packet_sim",
                key="empty_alerts_btn",
                icon=":material/security:",
            )
        else:
            st.dataframe(event_rows(state, events), hide_index=True, width="stretch")
            idx_labels = {
                i: f"Peringatan {len(events) - i}  {e.timestamp.strftime('%H:%M:%S')}  {'ditinjau' if e.acknowledged else 'perlu ditinjau'}"
                for i, e in enumerate(events)
            }
            picked = st.selectbox(
                "Pilih peringatan",
                list(idx_labels),
                format_func=idx_labels.get,
                key="sel_alert_pick",
            )
            ev = events[picked]
            st.caption(friendly_text(state, ev.message))
            b1, b2, b3 = st.columns(3)
            with b1:
                if st.button("Tandai sudah ditinjau", key="btn_ack_one", disabled=ev.acknowledged, width="stretch"):
                    acknowledge_security_events([ev.id])
                    st.toast("Peringatan ditandai sudah ditinjau.")
                    st.rerun()
            with b2:
                if st.button("Tandai semua ditinjau", key="btn_ack_all", disabled=all(e.acknowledged for e in events), width="stretch"):
                    acknowledge_security_events(None)
                    st.toast("Semua peringatan ditandai sudah ditinjau.")
                    st.rerun()
            with b3:
                if st.button("Kosongkan peringatan", icon=":material/delete:", key="btn_clear_alerts", width="stretch"):
                    _dialog_clear_alerts()

    with col_side:
        with st.expander("Prinsip audit firewall", expanded=False):
            st.markdown(
                "- Setiap event DROP dicatat sebagai jejak audit.\n"
                "- Penolakan port yang tidak diizinkan adalah bagian dari prinsip *least privilege*.\n"
                "- Tidak ada penuduhan serangan otomatis tanpa korelasi anomali lanjutan (fitur P2)."
            )
        next_steps([
            ("Tinjau Log Trafik", "traffic_logs"),
            ("Periksa Aturan Firewall", "firewall_rules"),
            ("Jalankan Uji Paket Lain", "packet_sim"),
        ])

    render_flow_next("traffic_logs", "Log Trafik", "Lihat seluruh riwayat paket yang dievaluasi.")
