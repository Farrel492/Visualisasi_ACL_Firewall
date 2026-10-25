"""CLI Console UI page."""

from __future__ import annotations

import streamlit as st

from firewall_sim.config.cli_parser import parse_and_execute
from firewall_sim.ui.components import (
    next_steps,
    page_header,
    render_simulation_banner,
)
from firewall_sim.ui.state import (
    get_cli_history,
    get_state,
    record_cli_interaction,
    set_state_from_cli,
)


def render_cli_console_page() -> None:
    """Merender konsol terminal perintah CLI."""
    render_simulation_banner()
    page_header(
        title="Konsol Terminal CLI",
        description="Prompt konfigurasi interaktif terinspirasi sintaks Cisco/Packet Tracer dengan parser aman (tanpa subproses sistem).",
    )

    state = get_state()

    col_main, col_side = st.columns([2.2, 1.0])

    with col_main:
        # Form Input Perintah
        with st.container(border=True):
            st.markdown("#### :material/terminal: Terminal Prompt")

            # Inisialisasi default command jika dipilih dari shortcut
            prefill_cmd = st.session_state.pop("cli_prefill", "")

            with st.form("form_cli_input", clear_on_submit=True):
                cli_input = st.text_input(
                    "Masukkan Perintah (ketik 'help' untuk daftar lengkap):",
                    value=prefill_cmd,
                    placeholder="misal: show running-config, rule add chain=forward proto=tcp dport=80 action=accept",
                    key="cli_cmd_input",
                )
                c_sub1, c_sub2 = st.columns([1, 4])
                with c_sub1:
                    submitted = st.form_submit_button("Kirim Perintah", type="primary", use_container_width=True)

                if submitted and cli_input.strip():
                    new_state, out_text, errors = parse_and_execute(state, cli_input.strip())
                    record_cli_interaction(cli_input.strip(), out_text, errors)
                    if not errors:
                        set_state_from_cli(new_state)
                    st.rerun()

        # Riwayat Output Terminal
        with st.container(border=True):
            st.markdown("#### :material/history_edu: Output Sesi Terminal")
            history = get_cli_history()

            if not history:
                st.caption("Belum ada interaksi CLI. Masukkan perintah atau gunakan tombol contoh di panel kanan.")
            else:
                terminal_lines = []
                for cmd_line, output, errors in history:
                    terminal_lines.append(f"FirewallSim# {cmd_line}")
                    if output:
                        terminal_lines.append(output)
                    if errors:
                        for err in errors:
                            terminal_lines.append(f"% Error: {err}")
                    terminal_lines.append("")

                st.code("\n".join(terminal_lines), language="shell")

    with col_side:
        # Contoh Perintah Klik-untuk-Isi & Bantuan
        with st.container(border=True):
            st.markdown("#### :material/play_circle: Contoh Perintah Cepat")
            st.caption("Klik salah satu contoh untuk langsung mengeksekusi:")

            quick_cmds = [
                ("show running-config", "Lihat Konfigurasi Aktif"),
                ("help", "Bantuan Sintaks"),
                ("show interfaces", "Daftar Interface"),
                ("show rules", "Daftar Aturan Firewall"),
                ("test source=pc_a destination=server proto=tcp dport=80", "Uji Paket PC A ➔ Server :80"),
            ]

            for cmd_str, desc in quick_cmds:
                if st.button(f"👉 {cmd_str}", key=f"cmd_quick_{cmd_str.replace(' ', '_')[:24]}", use_container_width=True):
                    new_state, out_text, errors = parse_and_execute(state, cmd_str)
                    record_cli_interaction(cmd_str, out_text, errors)
                    if not errors:
                        set_state_from_cli(new_state)
                    st.rerun()

        next_steps([
            ("Tinjau Topologi 2D", "network"),
            ("Periksa Aturan Firewall", "firewall_rules"),
            ("Buka Log Trafik", "traffic_logs"),
        ])
