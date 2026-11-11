"""Konsol CLI: terminal gaya Cisco IOS (router/switch) dan Windows (PC/server)."""

from __future__ import annotations

import html as _html
from typing import List, Tuple

import streamlit as st

from firewall_sim.config.cli_parser import parse_and_execute
from firewall_sim.config.ios_cli import (
    CliSession,
    IosCli,
    PingOutcome,
    hostname_of,
    is_host,
)
from firewall_sim.core.models import DeviceType, Protocol
from firewall_sim.ui.components import (
    empty_state,
    next_steps,
    page_header,
    render_simulation_banner,
)
from firewall_sim.ui.pages.packet_sim import friendly_reason, rule_text, run_packet
from firewall_sim.ui.state import (
    apply_command,
    clear_cli_history,
    get_cli_history,
    get_state,
    init_session_state,
    record_cli_entry,
    set_state_from_cli,
)

KEY_SESSION = "fw_sim_cli_session"
_MODE_LABEL = {"user": "user", "priv": "privileged", "config": "config", "config-if": "config-if"}


# --------------------------------------------------------------------------- penyambung ke state


def make_cli() -> IosCli:
    def apply(cmd):
        return apply_command(cmd, source="CLI")

    def ping(src_id, dst_id, dst_ip):
        state = get_state()
        res = run_packet(state, src_id, dst_id, dst_ip, Protocol.ICMP, None)
        detail = rule_text(get_state(), res) if res.decision.value in ("ACCEPT", "DROP") else friendly_reason(get_state(), res)
        return PingOutcome(res.decision, detail)

    def legacy(line):
        new_state, out, errors = parse_and_execute(get_state(), line)
        if not errors:
            set_state_from_cli(new_state)
        return out, errors

    return IosCli(get_state, apply, ping, legacy)


def default_device_id(state) -> str:
    router = next((d for d in state.devices if d.type == DeviceType.ROUTER), None)
    return (router or state.devices[0]).id


def get_session(state) -> CliSession:
    raw = st.session_state.get(KEY_SESSION)
    if raw and state.get_device(raw.get("device_id")):
        return CliSession(raw["device_id"], raw.get("mode", "user"), raw.get("iface_id"))
    session = CliSession(default_device_id(state))
    save_session(session)
    return session


def save_session(session: CliSession) -> None:
    st.session_state[KEY_SESSION] = {"device_id": session.device_id, "mode": session.mode, "iface_id": session.iface_id}


def run_command(cli: IosCli, session: CliSession, command: str) -> None:
    prompt = cli.prompt(session)
    lines = cli.execute(session, command)
    state = get_state()
    dev = state.get_device(session.device_id)
    record_cli_entry(prompt, command, lines, dev.name if dev else "")
    save_session(session)


# --------------------------------------------------------------------------- tampilan terminal


def _entry_lines(entry) -> Tuple[str, str, List[List[str]]]:
    """Ubah entri riwayat (format baru atau format lama) menjadi (prompt, perintah, baris)."""
    if isinstance(entry, dict):
        return entry.get("p", ""), entry.get("c", ""), entry.get("l", [])
    command, output, errors = entry
    lines = [["out", t] for t in str(output).splitlines()] + [["err", f"% {e}"] for e in errors]
    return "fw-lab>", command, lines


def terminal_html(history, title: str, intro: List[str]) -> str:
    cls = {"out": "fw-term-line", "ok": "fw-term-line fw-term-ok", "err": "fw-term-line fw-term-err", "info": "fw-term-line fw-term-dim"}
    body: List[str] = []
    if not history:
        body += [f'<div class="fw-term-line fw-term-dim">{_html.escape(t)}</div>' for t in intro]
    for entry in history[-80:]:
        prompt, command, lines = _entry_lines(entry)
        body.append(
            f'<div class="fw-term-line"><span class="fw-term-prompt">{_html.escape(prompt)}</span> '
            f'<span class="fw-term-cmd">{_html.escape(command)}</span></div>'
        )
        for kind, text in lines:
            body.append(f'<div class="{cls.get(kind, "fw-term-line")}">{_html.escape(text) or "&nbsp;"}</div>')
    body.append('<div class="fw-term-line"><span class="fw-cursor"></span></div>')
    return (
        '<div class="fw-terminal-window" translate="no"><div class="fw-terminal-bar">'
        '<div class="fw-terminal-dots"><span class="fw-terminal-dot"></span><span class="fw-terminal-dot"></span>'
        f'<span class="fw-terminal-dot"></span></div><span>{_html.escape(title)}</span><span></span></div>'
        f'<div class="fw-terminal-body"><div class="fw-term-inner">{"".join(body)}</div></div></div>'
    )


@st.dialog("Bersihkan layar terminal")
def _dialog_clear_cli():
    st.write("Seluruh riwayat terminal akan dihapus. Konfigurasi perangkat tidak berubah.")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Ya, bersihkan", type="primary", key="btn_confirm_clear_cli", width="stretch"):
            clear_cli_history()
            st.rerun()
    with c2:
        if st.button("Batal", key="btn_cancel_clear_cli", width="stretch"):
            st.rerun()


# --------------------------------------------------------------------------- halaman


def render_cli_console_page() -> None:
    render_simulation_banner()
    page_header(
        title="Konsol CLI",
        description="Konfigurasi perangkat lewat perintah, seperti di Cisco IOS (router, switch) atau Windows (PC, server).",
    )
    init_session_state()
    state = get_state()
    if not state.devices:
        empty_state(
            message="Belum ada perangkat untuk dikonfigurasi lewat CLI.",
            action_label="Buka Topologi 2D",
            target_page_or_callback="network",
            key="empty_cli_btn",
            icon=":material/terminal:",
        )
        return

    cli = make_cli()
    session = get_session(state)
    names = {d.id: f"{d.name} ({'host' if is_host(d) else 'IOS'})" for d in state.devices}

    col_main, col_side = st.columns([2.5, 1.0], gap="medium")
    with col_main:
        picked = st.selectbox(
            "Perangkat yang dikonfigurasi",
            list(names),
            index=list(names).index(session.device_id),
            format_func=names.get,
            key="sel_cli_device",
        )
        if picked != session.device_id:
            session = CliSession(picked)
            save_session(session)
            st.rerun()

        dev = state.get_device(session.device_id)
        mode_text = "Windows" if is_host(dev) else f"IOS, mode {_MODE_LABEL[session.mode]}"
        intro = [
            "Firewall Simulator CLI (simulasi). Tidak ada perintah sistem yang dijalankan.",
            f"Perangkat: {dev.name}. Ketik ? untuk bantuan."
            + ("" if is_host(dev) else " Mulai dengan 'enable', lalu 'configure terminal'."),
        ]
        st.markdown(terminal_html(get_cli_history(), f"{hostname_of(dev)}  ({mode_text})", intro), unsafe_allow_html=True)

        with st.form("form_cli_input", clear_on_submit=True):
            cli_input = st.text_input(
                cli.prompt(session),
                placeholder="ketik perintah, mis. enable  atau  ?",
                key="cli_cmd_input",
            )
            c1, c2, _ = st.columns([1.2, 1.4, 2.8])
            with c1:
                submitted = st.form_submit_button("Kirim", icon=":material/send:", type="primary", width="stretch")
            with c2:
                clear_btn = st.form_submit_button("Bersihkan layar", icon=":material/clear_all:", width="stretch")
            if submitted and cli_input.strip():
                run_command(cli, session, cli_input.strip())
                st.rerun()
        if clear_btn:
            _dialog_clear_cli()

    with col_side:
        with st.container(border=True):
            st.markdown("**Perintah cepat**")
            st.caption("Klik untuk langsung menjalankan perintah yang valid pada mode ini.")
            for i, cmd in enumerate(cli.quick_commands(session)):
                if st.button(cmd, key=f"chip_cli_{i}", width="stretch"):
                    run_command(cli, session, cmd)
                    st.rerun()
        with st.expander("Contoh alur konfigurasi", expanded=False):
            st.markdown(
                "Router (IOS):\n"
                "```\nenable\nconfigure terminal\ninterface fa0/1\nip address 10.0.0.1 255.255.255.0\n"
                "no shutdown\nexit\nrule add chain=forward proto=tcp dport=80 action=accept\nend\nshow running-config\n```\n"
                "PC atau Server (Windows):\n"
                "```\nipconfig\nipconfig set 192.168.1.10 255.255.255.0 192.168.1.1\nping 10.0.0.10\n```"
            )
        next_steps([
            ("Tinjau Topologi 2D", "network"),
            ("Periksa Aturan Firewall", "firewall_rules"),
            ("Buka Log Trafik", "traffic_logs"),
        ])
