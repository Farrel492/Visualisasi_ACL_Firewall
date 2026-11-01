"""Overview dashboard page."""

from __future__ import annotations

import streamlit as st

from firewall_sim.core.analytics import summarize_traffic
from firewall_sim.core.validation import validate_topology
from firewall_sim.storage.json_store import load_project, save_project
from firewall_sim.ui.components import (
    next_steps,
    page_header,
    render_error_box,
    render_flow_next,
    render_simulation_banner,
)
from firewall_sim.ui.state import (
    clear_simulation_data,
    new_workspace,
    get_security_events,
    get_state,
    get_traffic_logs,
    reset_to_preset,
    set_project_state,
)
from firewall_sim.ui.theme import get_decision_badge



@st.dialog("Mulai Proyek Baru")
def _dialog_new_project():
    st.write("Sesi kerja baru yang bersih akan dibuat. Proyek sebelumnya tetap tersimpan di riwayat arsip.")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Ya, buat proyek baru", type="primary", key="btn_confirm_new_project", use_container_width=True):
            new_workspace()
            st.toast("Proyek baru berhasil dibuat.")
            st.rerun()
    with c2:
        if st.button("Batal", key="btn_cancel_new_project", use_container_width=True):
            st.rerun()


def render_overview_page() -> None:
    """Merender halaman ringkasan sistem, status topologi, dan persistensi proyek."""
    render_simulation_banner()
    page_header(
        title="Dasbor",
        description="Ringkasan kondisi topologi jaringan virtual, kepatuhan validasi, serta metrik pengujian terakhir.",
    )

    state = get_state()
    scenario_name = dict(state.scenario_metadata).get("name", "Custom Scenario")

    # 4 KPI Utama Ringkasan Sistem
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Skenario Aktif", scenario_name, border=True)
    k2.metric("Config Revision", f"Rev #{state.config_revision}", border=True)
    k3.metric("Total Perangkat", f"{len(state.devices)} unit", border=True)
    k4.metric("Keterhubungan & Rule", f"{len(state.links)} link / {len(state.rules)} rule", border=True)

    col_main, col_side = st.columns([2.2, 1.0])

    with col_main:
        # Validasi Topologi
        with st.container(border=True):
            st.markdown("#### :material/verified_user: Status Validasi Topologi (MVP Rules)")
            val_errors = validate_topology(state)
            if val_errors:
                st.error(f"Terdeteksi {len(val_errors)} isu validasi konfigurasi:", icon=":material/warning:")
                for err in val_errors:
                    st.markdown(f"- **[{err.code}]** {err.message}")
            else:
                st.success("Topologi valid: Memenuhi seluruh aturan integritas jaringan dan kriteria router tunggal MVP.", icon=":material/check_circle:")

        # Default Policy per Chain
        with st.container(border=True):
            st.markdown("#### :material/policy: Kebijakan Default Aktif")
            p_cols = st.columns(3)
            for idx, (chain, action) in enumerate(state.default_policies):
                act_badge = "ACCEPT" if action.value.lower() == "accept" else "DROP"
                with p_cols[idx]:
                    st.metric(f"Chain {chain.value.upper()}", act_badge, border=True)

        # Aktivitas Log & Alert Terakhir
        with st.container(border=True):
            st.markdown("#### :material/query_stats: Aktivitas Uji Terakhir")
            logs = get_traffic_logs()
            summary = summarize_traffic(logs)

            m_c1, m_c2, m_c3, m_c4 = st.columns(4)
            m_c1.metric("Total Uji", summary["total"], border=True)
            m_c2.metric("Lolos", summary["ACCEPT"], border=True)
            m_c3.metric("Ditolak", summary["DROP"], border=True)
            m_c4.metric("No Route", summary["NO_ROUTE"], border=True)

            if logs:
                st.caption(f"Uji terakhir: {get_decision_badge(logs[0].decision)} — {logs[0].source_device} -> {logs[0].destination_target}")
            else:
                st.info("Belum ada pengujian simulasi paket yang dijalankan.")

        # Riwayat Audit Log Konfigurasi (5 terakhir)
        if state.audit_log:
            with st.container(border=True):
                st.markdown("#### :material/history: 5 Revisi Konfigurasi Terakhir")
                recent_logs = list(reversed(state.audit_log[-5:]))
                for entry in recent_logs:
                    stamp = entry.timestamp.strftime("%H:%M:%S")
                    st.caption(f"`{stamp}`  **{entry.source}**  {entry.summary or 'Pembaruan konfigurasi'}")

    with col_side:
        # Kontrol Manajemen Proyek (Proyek baru, Ekspor, Impor)
        with st.container(border=True):
            st.markdown("#### :material/folder: Manajemen Proyek")

            if st.button("Proyek baru", icon=":material/note_add:", use_container_width=True, key="btn_new_project"):
                _dialog_new_project()

            json_export = save_project(state)
            st.download_button(
                label="Ekspor proyek (JSON)",
                icon=":material/download:",
                data=json_export,
                file_name=f"firewall_project_rev{state.config_revision}.json",
                mime="application/json",
                use_container_width=True,
                key="btn_download_json",
            )

            with st.expander("Impor proyek"):
                uploaded_file = st.file_uploader("Pilih berkas JSON proyek", type=["json"], key="json_uploader")
                if uploaded_file is not None:
                    content = uploaded_file.getvalue().decode("utf-8")
                    loaded_state, errors = load_project(content)
                    if loaded_state:
                        set_project_state(loaded_state)
                        st.toast("Proyek berhasil diimpor dari JSON!")
                        st.rerun()
                    else:
                        render_error_box(errors)

            with st.expander(":material/restart_alt: Reset Topologi"):
                if st.button("Reset ke Default Lab", icon=":material/restart_alt:", use_container_width=True, key="btn_reset_default"):
                    reset_to_preset("default")
                    clear_simulation_data()
                    st.toast("Topologi direset ke 'Default Lab'!")
                    st.rerun()

                if st.button("Reset ke Proyek Kosong", icon=":material/delete:", use_container_width=True, key="btn_reset_empty"):
                    reset_to_preset("empty")
                    clear_simulation_data()
                    st.toast("Topologi direset ke 'Proyek Kosong'!")
                    st.rerun()

        next_steps([
            ("Buka Topologi 2D", "network"),
            ("Atur Firewall Rules", "firewall_rules"),
            ("Simulasi Paket", "packet_sim"),
            ("Analisis Log Trafik", "traffic_logs"),
        ])

    render_flow_next("network", "Topologi 2D", "Mulai meninjau atau menyusun perangkat jaringan.")

