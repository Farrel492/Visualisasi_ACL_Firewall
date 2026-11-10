"""Log Trafik: riwayat setiap paket virtual yang dievaluasi, dengan filter dan penjelasan keputusan."""

from __future__ import annotations

import streamlit as st

from firewall_sim.core.analytics import filter_traffic, summarize_traffic
from firewall_sim.core.models import Decision
from firewall_sim.ui.components import (
    empty_state,
    next_steps,
    page_header,
    render_flow_next,
    render_simulation_banner,
    render_workflow_rail,
)
from firewall_sim.ui.labels import device_name, friendly_text, rule_label
from firewall_sim.ui.state import clear_traffic_logs, get_state, get_traffic_logs


@st.dialog("Kosongkan log trafik")
def _dialog_clear_traffic_logs():
    st.write("Semua catatan log trafik akan dihapus. Riwayat uji di Simulasi Paket tidak ikut terhapus.")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Ya, kosongkan", type="primary", key="btn_confirm_clear_logs", width="stretch"):
            clear_traffic_logs()
            st.toast("Log trafik dikosongkan.")
            st.rerun()
    with c2:
        if st.button("Batal", key="btn_cancel_clear_logs", width="stretch"):
            st.rerun()


def summary_strip_html(summary: dict) -> str:
    return (
        '<div class="fw-strip" translate="no">'
        f"<span><b>Total</b> {summary['total']}</span>"
        f'<span><i class="fw-led ok"></i><b>ACCEPT</b> {summary["ACCEPT"]}</span>'
        f'<span><i class="fw-led deny"></i><b>DROP</b> {summary["DROP"]}</span>'
        f'<span><i class="fw-led amber"></i><b>NO_ROUTE</b> {summary["NO_ROUTE"]}</span>'
        "</div>"
    )


def log_rows(state, logs):
    rows = []
    for log in logs:
        dest = device_name(state, log.destination_target)
        port = f":{log.dst_port}" if log.dst_port else ""
        rev = f"#{log.config_revision}" + (" (usang)" if log.config_revision != state.config_revision else "")
        rows.append(
            {
                "Waktu": log.timestamp.strftime("%H:%M:%S"),
                "Sumber": device_name(state, log.source_device),
                "Tujuan": f"{dest}{port}",
                "Protokol": log.protocol.value.upper(),
                "Keputusan": log.decision.value,
                "Penentu": rule_label(state, log.matched_rule_id),
                "Revisi": rev,
                "Alasan": friendly_text(state, log.reason),
            }
        )
    return rows


def render_traffic_logs_page() -> None:
    render_simulation_banner()
    page_header(
        title="Log Trafik",
        description="Catatan setiap paket virtual yang dievaluasi, lengkap dengan keputusan dan penentunya.",
    )
    render_workflow_rail("traffic_logs")

    state = get_state()
    logs = get_traffic_logs()
    summary = summarize_traffic(logs)
    st.markdown(summary_strip_html(summary), unsafe_allow_html=True)

    if not logs:
        empty_state(
            message="Belum ada catatan log. Kirim paket uji di Simulasi Paket untuk mengisi log.",
            action_label="Mulai Uji Paket",
            target_page_or_callback="packet_sim",
            key="empty_logs_btn",
            icon=":material/list_alt:",
        )
        return

    col_main, col_side = st.columns([2.6, 1.0], gap="medium")
    with col_main:
        c_f1, c_f2, c_f3 = st.columns([1, 1.6, 1])
        with c_f1:
            sel_dec_label = st.selectbox(
                "Keputusan", ["Semua", "ACCEPT", "DROP", "NO_ROUTE"], key="sel_log_dec"
            )
        with c_f2:
            search = st.text_input("Cari host atau alamat IP", placeholder="misal: PC A atau 192.168.1.10", key="input_log_search")
        with c_f3:
            st.markdown("&nbsp;", unsafe_allow_html=True)
            if st.button("Kosongkan log", icon=":material/delete:", key="btn_clear_logs", width="stretch"):
                _dialog_clear_traffic_logs()

        sel_dec = None if sel_dec_label == "Semua" else Decision(sel_dec_label)
        # pencarian boleh memakai nama perangkat: ubah nama menjadi ID sebelum difilter
        needle = (search or "").strip()
        by_name = {d.name.lower(): d.id for d in state.devices}
        if needle.lower() in by_name:
            needle = by_name[needle.lower()]
        filtered = filter_traffic(logs, decision=sel_dec, ip_or_device=needle)

        st.caption(f"Menampilkan {len(filtered)} dari {len(logs)} catatan.")
        if not filtered:
            st.info("Tidak ada catatan yang cocok dengan filter.")
        else:
            st.dataframe(log_rows(state, filtered), hide_index=True, width="stretch")

    with col_side:
        pct_allow = round(summary["ACCEPT"] / summary["total"] * 100) if summary["total"] else 0
        pct_deny = round(summary["DROP"] / summary["total"] * 100) if summary["total"] else 0
        st.caption(f"Lolos {pct_allow}%, ditolak {pct_deny}% dari {summary['total']} uji.")
        next_steps([
            ("Buka Pusat Peringatan", "alerts"),
            ("Lihat Replay 3D", "viz3d"),
            ("Jalankan Uji Paket Lain", "packet_sim"),
        ])

    render_flow_next("alerts", "Pusat Peringatan", "Periksa event penolakan dan tandai yang sudah ditinjau.")
