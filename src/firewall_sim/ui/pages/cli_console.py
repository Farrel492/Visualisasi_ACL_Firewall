"""CLI Console UI page — Terminal bergaya nyata untuk konfigurasi interaktif."""

from __future__ import annotations

import html as _html
import streamlit as st

from firewall_sim.config.cli_parser import parse_and_execute
from firewall_sim.ui.components import (
    next_steps,
    page_header,
    render_simulation_banner,
)
from firewall_sim.ui.state import (
    clear_simulation_data,
    get_cli_history,
    get_state,
    init_session_state,
    record_cli_interaction,
    set_state_from_cli,
)
from firewall_sim.ui.theme import inject_theme_css


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_HOSTNAME = "fw-lab"


def _escape(text: str) -> str:
    """HTML-escape teks agar aman diinjeksikan ke dalam innerHTML."""
    return _html.escape(str(text))


def _build_terminal_html(history: list[tuple[str, str, list[str]]]) -> str:
    """Membangun HTML terminal dari riwayat CLI sesi.

    Setiap entri menghasilkan:
      - Baris prompt: fw-lab> <perintah>
      - Baris output (ok): hijau
      - Baris error (err): merah
      Baris kosong pemisah di antara entri.
    """
    lines_html: list[str] = []

    if not history:
        lines_html.append(
            "<div class='fw-term-line fw-term-dim'>"
            f"Sesi terminal dimulai. Ketik perintah atau klik chip di bawah."
            "</div>"
        )
    else:
        for cmd, out, errs in history:
            lines_html.append(
                f"<div class='fw-term-line'>"
                f"<span class='fw-term-prompt'>{_escape(_HOSTNAME)}&gt;</span>"
                f" <span class='fw-term-cmd'>{_escape(cmd)}</span>"
                f"</div>"
            )
            if out and out.strip():
                for line in out.splitlines():
                    lines_html.append(
                        f"<div class='fw-term-line fw-term-ok'>{_escape(line)}</div>"
                    )
            if errs:
                for err in errs:
                    lines_html.append(
                        f"<div class='fw-term-line fw-term-err'>% Error: {_escape(err)}</div>"
                    )
            lines_html.append("<div class='fw-term-line'>&nbsp;</div>")

    return "\n".join(lines_html)


def _render_terminal_window(history: list[tuple[str, str, list[str]]]) -> None:
    """Merender jendela terminal HTML bergaya macOS."""
    body_html = _build_terminal_html(history)
    terminal_html = f"""
    <div class="fw-terminal-window">
        <div class="fw-terminal-bar">
            <div class="fw-terminal-dots">
                <span class="fw-terminal-dot close"></span>
                <span class="fw-terminal-dot min"></span>
                <span class="fw-terminal-dot max"></span>
            </div>
            <span style="flex:1;text-align:center;letter-spacing:0.04em;">{_HOSTNAME} — Firewall Simulator CLI</span>
            <span style="width:3.5rem;"></span>
        </div>
        <div class="fw-terminal-body" id="fw-term-body">
            {body_html}
        </div>
    </div>
    <script>
    (function() {{
        var el = document.getElementById('fw-term-body');
        if (el) {{ el.scrollTop = el.scrollHeight; }}
    }})();
    </script>
    """
    st.markdown(terminal_html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Chip perintah cepat
# ---------------------------------------------------------------------------

_QUICK_CMDS: list[tuple[str, str]] = [
    ("help", ":material/help:"),
    ("show running-config", ":material/settings:"),
    ("show interfaces", ":material/hub:"),
    ("show rules", ":material/shield:"),
    ("test source=pc_a destination=server proto=tcp dport=80", ":material/send:"),
    ("test source=pc_b destination=server proto=tcp dport=22", ":material/send:"),
]


# ---------------------------------------------------------------------------
# Render halaman
# ---------------------------------------------------------------------------

def render_cli_console_page() -> None:
    """Merender konsol terminal perintah CLI bergaya nyata."""
    render_simulation_banner()
    page_header(
        title="Konsol CLI",
        description="Prompt interaktif bergaya terminal untuk konfigurasi firewall — sintaks aman tanpa eksekusi subproses sistem.",
    )

    init_session_state()
    state = get_state()
    history = get_cli_history()

    # Injeksi CSS terminal (sudah dilakukan oleh page_header via inject_theme_css)

    col_main, col_side = st.columns([2.5, 1.0])

    with col_main:
        # Panel Utama: Jendela Terminal
        _render_terminal_window(history)

        # Form Input Perintah (submit = Kirim atau Enter)
        prefill_cmd = st.session_state.pop("cli_prefill", "")
        with st.form("form_cli_input", clear_on_submit=True):
            cli_input = st.text_input(
                f"{_HOSTNAME}>",
                value=prefill_cmd,
                placeholder="Contoh: show rules  |  test source=pc_a destination=server proto=tcp dport=80",
                key="cli_cmd_input",
                label_visibility="visible",
            )
            c_sub1, c_sub2, c_sub3 = st.columns([1.2, 1.2, 3])
            with c_sub1:
                submitted = st.form_submit_button(
                    "Kirim",
                    icon=":material/send:",
                    type="primary",
                    use_container_width=True,
                )
            with c_sub2:
                clear_btn = st.form_submit_button(
                    "Bersihkan",
                    icon=":material/clear_all:",
                    use_container_width=True,
                )

            if submitted and cli_input.strip():
                new_state, out_text, errors = parse_and_execute(state, cli_input.strip())
                record_cli_interaction(cli_input.strip(), out_text, errors)
                if not errors:
                    set_state_from_cli(new_state)
                st.rerun()

            if clear_btn:
                # Hanya bersihkan log CLI, bukan simulation data
                st.session_state["fw_sim_cli_log"] = []
                st.rerun()

    with col_side:
        # Chip Perintah Cepat
        with st.container(border=True):
            st.markdown("#### :material/bolt: Perintah Cepat")
            st.caption("Klik chip untuk langsung mengeksekusi:")
            for cmd_str, icon in _QUICK_CMDS:
                label = cmd_str if len(cmd_str) <= 28 else cmd_str[:25] + "..."
                chip_key = f"chip_{cmd_str[:36].replace(' ', '_').replace('=', '_')}"
                if st.button(label, icon=icon, key=chip_key, use_container_width=True):
                    new_state, out_text, errors = parse_and_execute(state, cmd_str)
                    record_cli_interaction(cmd_str, out_text, errors)
                    if not errors:
                        set_state_from_cli(new_state)
                    st.rerun()

        # Referensi Perintah (Learning Mode tersimpulkan tanpa is_learning)
        with st.expander(":material/menu_book: Referensi Sintaks"):
            st.markdown(
                "| Perintah | Keterangan |\n"
                "|----------|------------|\n"
                "| `help` | Daftar lengkap perintah |\n"
                "| `show running-config` | Konfigurasi aktif |\n"
                "| `show interfaces` | Daftar antarmuka |\n"
                "| `show rules` | Daftar aturan firewall |\n"
                "| `rule add chain=forward proto=tcp dport=80 action=accept` | Tambah rule |\n"
                "| `policy forward drop` | Ubah default policy |\n"
                "| `test source=<id> destination=<ip> proto=tcp dport=80` | Simulasi paket |\n"
                "| `interface eth0 ip 10.0.0.1/24` | Atur IP interface |\n"
                "| `gateway 192.168.1.1` | Atur gateway host |"
            )

        next_steps([
            ("Tinjau Topologi 2D", "network"),
            ("Periksa Aturan Firewall", "firewall_rules"),
            ("Buka Log Trafik", "traffic_logs"),
        ])
