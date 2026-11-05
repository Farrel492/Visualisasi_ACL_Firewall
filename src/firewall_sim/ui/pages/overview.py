"""Overview dashboard page."""

from __future__ import annotations

import streamlit as st

from firewall_sim.core.analytics import summarize_traffic
from firewall_sim.core.models import Decision
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
from firewall_sim.ui.theme import get_decision_badge, COLOR_ALLOW, COLOR_DENY, COLOR_MUTED


# ── helper untuk keputusan ──────────────────────────────────────────────────

_DECISION_LABEL: dict[Decision, str] = {
    Decision.ACCEPT: "ACCEPT",
    Decision.DROP: "DROP",
    Decision.NO_ROUTE: "NO_ROUTE",
    Decision.INVALID_CONFIG: "INVALID",
    Decision.UNSUPPORTED_CASE: "UNSUPPORTED",
}


def _device_name(state, device_id: str) -> str:
    """Nama perangkat untuk ditampilkan; bila tidak ditemukan, tampilkan teks aslinya (mis. alamat IP)."""
    dev = state.get_device(device_id) if device_id else None
    return dev.name if dev else (device_id or "-")


def _decision_color(decision: Decision) -> str:
    if decision == Decision.ACCEPT:
        return COLOR_ALLOW
    if decision == Decision.DROP:
        return COLOR_DENY
    return COLOR_MUTED


def _led_dot(decision: Decision) -> str:
    """Buat lingkaran berwarna kecil sebagai LED indikator keputusan."""
    color = _decision_color(decision)
    return (
        f'<span style="display:inline-block;width:10px;height:10px;' 
        f'border-radius:50%;background:{color};margin-right:5px;vertical-align:middle;"></span>'
    )


# ── dialog ──────────────────────────────────────────────────────────────────

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


# ── helpers status strip ─────────────────────────────────────────────────────

def _compute_strip_data(state) -> dict:
    """Hitung data untuk strip status satu baris."""
    val_errors = validate_topology(state)
    return {
        "revision": state.config_revision,
        "devices": len(state.devices),
        "rules": len(state.rules),
        "links": len(state.links),
        "valid": len(val_errors) == 0,
        "val_count": len(val_errors),
    }


# ── render utama ─────────────────────────────────────────────────────────────

def render_overview_page() -> None:
    """Merender halaman ringkasan sistem, status topologi, dan persistensi proyek."""
    render_simulation_banner()
    page_header(
        title="Dasbor",
        description="Ringkasan kondisi topologi jaringan virtual, kepatuhan validasi, serta metrik pengujian terakhir.",
    )

    state = get_state()
    strip = _compute_strip_data(state)
    scenario_name = dict(state.scenario_metadata).get("name", "Custom Scenario")

    # ── Strip Status ────────────────────────────────────────────────────────
    val_color = COLOR_ALLOW if strip["valid"] else COLOR_DENY
    val_text = "Valid" if strip["valid"] else f"{strip['val_count']} isu"
    strip_html = (
        '<div style="font-family:var(--fw-mono, \'IBM Plex Mono\', monospace);font-size:0.82rem;padding:8px 12px;' 
        'background:#F4F5F6;border:1px solid #C2C9D0;border-radius:6px;' 
        'display:flex;gap:24px;align-items:center;flex-wrap:wrap;">' 
        f'<span><b>Revisi</b>&nbsp;#{strip["revision"]}</span>' 
        f'<span><b>Perangkat</b>&nbsp;{strip["devices"]}</span>' 
        f'<span><b>Rule</b>&nbsp;{strip["rules"]}</span>' 
        f'<span><b>Link</b>&nbsp;{strip["links"]}</span>' 
        f'<span><b>Validasi</b>&nbsp;<span style="color:{val_color};font-weight:600;">{val_text}</span></span>' 
        f'<span style="color:#5E6A75">{scenario_name}</span>' 
        '</div>'
    )
    st.html(strip_html)

    col_main, col_side = st.columns([2.2, 1.0])

    with col_main:
        # Validasi Topologi
        with st.container(border=True):
            st.markdown("#### Status Validasi Topologi")
            val_errors = validate_topology(state)
            if val_errors:
                st.error(f"Terdeteksi {len(val_errors)} isu validasi konfigurasi:", icon=":material/warning:")
                for err in val_errors:
                    st.markdown(f"- **[{err.code}]** {err.message}")
            else:
                st.success(
                    "Topologi valid: Memenuhi seluruh aturan integritas jaringan dan kriteria router tunggal MVP.",
                    icon=":material/check_circle:",
                )

        # Default Policy per Chain — teks penuh, tidak terpotong
        with st.container(border=True):
            st.markdown("#### Kebijakan Default per Chain")
            p_cols = st.columns(3)
            for idx, (chain, action) in enumerate(state.default_policies):
                act = action.value.upper()
                color = COLOR_ALLOW if act == "ACCEPT" else COLOR_DENY
                chain_label = chain.value.upper()
                badge_html = (
                    f'<div style="border:1px solid #C2C9D0;border-radius:6px;' 
                    f'padding:10px 12px;background:#F4F5F6;">' 
                    f'<div style="font-size:0.78rem;color:#5E6A75;margin-bottom:4px;">Chain {chain_label}</div>' 
                    f'<div style="font-size:1rem;font-weight:700;color:{color};">{act}</div>' 
                    f'</div>'
                )
                with p_cols[idx]:
                    st.html(badge_html)

        # Tabel Uji Terbaru (5 entri terakhir)
        with st.container(border=True):
            st.markdown("#### Uji Paket Terbaru")
            logs = get_traffic_logs()
            summary = summarize_traffic(logs)

            # Baris ringkasan satu baris
            total = summary["total"]
            accepted = summary["ACCEPT"]
            dropped = summary["DROP"]
            no_route = summary["NO_ROUTE"]
            st.caption(
                f"Total: **{total}** uji  |  ACCEPT: **{accepted}**  |  DROP: **{dropped}**  |  NO_ROUTE: **{no_route}**"
            )

            if logs:
                recent = logs[:5]
                rows = []
                for entry in recent:
                    waktu = entry.timestamp.strftime("%H:%M:%S") if hasattr(entry.timestamp, "strftime") else str(entry.timestamp)
                    keputusan = _DECISION_LABEL.get(entry.decision, str(entry.decision))
                    rows.append({
                        "Waktu": waktu,
                        "Sumber": _device_name(state, entry.source_device),
                        "Tujuan": _device_name(state, entry.destination_target),
                        "Protokol": entry.protocol or "-",
                        "Keputusan": keputusan,
                    })
                st.dataframe(
                    rows,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Keputusan": st.column_config.TextColumn("Keputusan"),
                    },
                )
            else:
                st.info("Belum ada pengujian simulasi paket yang dijalankan.")

        # Riwayat Audit Log Konfigurasi (5 terakhir)
        if state.audit_log:
            with st.container(border=True):
                st.markdown("#### 5 Revisi Konfigurasi Terakhir")
                recent_logs = list(reversed(state.audit_log[-5:]))
                for entry in recent_logs:
                    stamp = entry.timestamp.strftime("%H:%M:%S")
                    st.caption(f"`{stamp}`  **{entry.source}**  {entry.summary or 'Pembaruan konfigurasi'}")

    with col_side:
        # Kontrol Manajemen Proyek (Proyek baru, Ekspor, Impor)
        with st.container(border=True):
            st.markdown("#### Manajemen Proyek")

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
