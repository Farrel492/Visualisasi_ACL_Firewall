"""Traffic Logs dashboard page."""

from __future__ import annotations

import streamlit as st

from firewall_sim.core.analytics import filter_traffic, summarize_traffic
from firewall_sim.core.models import Decision
from firewall_sim.ui.components import (
    empty_state,
    next_steps,
    page_header,
    render_simulation_banner,
)
from firewall_sim.ui.state import get_traffic_logs
from firewall_sim.ui.theme import get_decision_badge


def render_traffic_logs_page() -> None:
    """Merender dasbor log analisis lalu lintas paket virtual."""
    render_simulation_banner()
    page_header(
        title="Log Trafik & Monitoring",
        description="Pencatatan riwayat seluruh paket virtual yang dievaluasi dalam simulator jaringan.",
    )

    logs = get_traffic_logs()
    summary = summarize_traffic(logs)

    # 1. Baris KPI Metrik Agregasi
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Pengujian", summary["total"], border=True)
    m2.metric("🟢 Lolos (ACCEPT)", summary["ACCEPT"], border=True)
    m3.metric("🔴 Ditolak (DROP)", summary["DROP"], border=True)
    m4.metric("⚠️ Rute Hilang (NO_ROUTE)", summary["NO_ROUTE"], border=True)

    if not logs:
        empty_state(
            message="Belum ada catatan log trafik jaringan. Kirim paket pengujian pada menu Simulasi Paket untuk mengisi log.",
            action_label="Mulai Uji Paket",
            target_page_or_callback="packet_sim",
            key="empty_logs_btn",
            icon=":material/list_alt:",
        )
        return

    col_main, col_side = st.columns([2.2, 1.0])

    with col_main:
        # Filter Bar Log
        with st.container(border=True):
            st.markdown("#### :material/filter_alt: Filter Catatan Log")
            c_f1, c_f2 = st.columns([1, 2])
            with c_f1:
                dec_options = ["Semua Keputusan", "ACCEPT", "DROP", "NO_ROUTE"]
                sel_dec_label = st.selectbox("Status Keputusan:", dec_options, key="sel_log_dec")
                sel_dec = None
                if sel_dec_label != "Semua Keputusan":
                    sel_dec = Decision(sel_dec_label)

            with c_f2:
                search_ip = st.text_input("Pencarian Host / Alamat IP:", placeholder="misal: 192.168.1.10 atau pc_a", key="input_log_search")

        filtered_logs = filter_traffic(logs, decision=sel_dec, ip_or_device=search_ip)

        st.caption(f"Menampilkan **{len(filtered_logs)}** dari total **{len(logs)}** catatan log virtual.")

        # Tabel Log Terformat
        if not filtered_logs:
            st.info("Tidak ada catatan log yang cocok dengan kriteria pencarian.")
        else:
            table_data = []
            for log in filtered_logs:
                port_s = f":{log.dst_port}" if log.dst_port else ""
                table_data.append(
                    {
                        "Waktu": log.timestamp.strftime("%H:%M:%S"),
                        "ID Uji": log.id,
                        "Sumber": log.source_device,
                        "Tujuan": f"{log.destination_target}{port_s}",
                        "Protokol": log.protocol.value.upper(),
                        "Keputusan": get_decision_badge(log.decision),
                        "Rule Cocok": log.matched_rule_id or "—",
                        "Revisi": f"Rev #{log.config_revision}",
                        "Alasan": log.reason,
                    }
                )

            st.dataframe(
                table_data,
                hide_index=True,
                use_container_width=True,
                column_config={
                    "Waktu": st.column_config.TextColumn("Waktu"),
                    "ID Uji": st.column_config.TextColumn("ID Uji"),
                    "Sumber": st.column_config.TextColumn("Perangkat Sumber"),
                    "Tujuan": st.column_config.TextColumn("Target Tujuan"),
                    "Protokol": st.column_config.TextColumn("Protokol"),
                    "Keputusan": st.column_config.TextColumn("Keputusan Firewall"),
                    "Rule Cocok": st.column_config.TextColumn("Rule Pemicu"),
                    "Revisi": st.column_config.TextColumn("Revisi Konfigurasi"),
                    "Alasan": st.column_config.TextColumn("Alasan Keputusan"),
                },
            )

    with col_side:
        # Panel Informasi & Langkah Berikutnya
        with st.container(border=True):
            st.markdown("#### :material/insights: Analisis Cepat")
            pct_allow = round((summary["ACCEPT"] / summary["total"] * 100) if summary["total"] else 0, 1)
            pct_deny = round((summary["DROP"] / summary["total"] * 100) if summary["total"] else 0, 1)
            st.markdown(
                f"- **Rasio Lolos**: `{pct_allow}%`\n"
                f"- **Rasio Blokir**: `{pct_deny}%`\n"
                f"- **Status Log**: Penyimpanan in-memory stabil."
            )

        next_steps([
            ("Buka Pusat Peringatan", "alerts"),
            ("Lihat Replay 3D", "viz3d"),
            ("Jalankan Uji Paket Lain", "packet_sim"),
        ])
