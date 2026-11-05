"""Aturan Firewall: kebijakan default per chain dan daftar aturan berurutan (first match wins)."""

from __future__ import annotations

import html
import ipaddress
from typing import List, Optional

import streamlit as st

from firewall_sim.config.service import (
    AddRule,
    MoveRule,
    RemoveRule,
    SetDefaultPolicy,
    ToggleRule,
)
from firewall_sim.core.models import Action, Chain, FirewallRule, Protocol, ProjectState
from firewall_sim.ui import topo
from firewall_sim.ui.components import (
    empty_state,
    next_steps,
    page_header,
    render_error_box,
    render_flow_next,
    render_simulation_banner,
    render_workflow_rail,
)
from firewall_sim.ui.state import apply_command, get_cables, get_layout, get_selected_device, get_state
from firewall_sim.ui.widgets import apply_component_event, topology_view

_CHAINS = [Chain.FORWARD, Chain.INPUT, Chain.OUTPUT]
_ANY = "__any__"
_MANUAL = "__manual__"


# --------------------------------------------------------------------------- fungsi bantu murni


def endpoint_label(state: ProjectState, cidr: Optional[str]) -> str:
    """Teks yang ramah pembaca untuk sumber/tujuan rule: nama perangkat bila /32 cocok dengan IP perangkat."""
    if not cidr:
        return "semua"
    try:
        net = ipaddress.ip_network(cidr, strict=False)
    except ValueError:
        return cidr
    if net.prefixlen == 32:
        for dev in state.devices:
            for iface in dev.interfaces:
                if iface.ipv4_cidr and ipaddress.ip_interface(iface.ipv4_cidr).ip == net.network_address:
                    return f"{dev.name} ({net.network_address})"
        return str(net.network_address)
    return f"{cidr} (subnet)"


def port_label(rule: FirewallRule) -> str:
    return rule.dst_port if rule.dst_port else "semua"


def rule_summary(state: ProjectState, rule: FirewallRule) -> str:
    proto = rule.protocol.value
    port = f"/{rule.dst_port}" if rule.dst_port else ""
    return (
        f"#{rule.order}  {rule.action.value.upper()}  "
        f"{endpoint_label(state, rule.src_cidr)} ke {endpoint_label(state, rule.dst_cidr)}  {proto}{port}"
    )


def endpoint_options(state: ProjectState) -> List[tuple]:
    """Pilihan sumber/tujuan: semua, setiap perangkat ber-IP (sebagai /32), atau CIDR manual."""
    options = [(_ANY, "Semua (any)")]
    for dev in state.devices:
        ips = [i.ipv4_cidr for i in dev.interfaces if i.ipv4_cidr]
        if ips:
            ip = str(ipaddress.ip_interface(ips[0]).ip)
            options.append((f"{ip}/32", f"{dev.name} ({ip})"))
    options.append((_MANUAL, "CIDR manual"))
    return options


def table_html(state: ProjectState, rules: List[FirewallRule]) -> str:
    rows = []
    for r in rules:
        on = r.enabled
        status = (
            '<span class="fw-led ok"></span>aktif' if on else '<span class="fw-led off"></span>nonaktif'
        )
        action_cls = "fw-act-accept" if r.action == Action.ACCEPT else "fw-act-drop"
        cls = "" if on else ' class="fw-row-off"'
        rows.append(
            f"<tr{cls}><td>{r.order}</td><td>{status}</td>"
            f"<td>{html.escape(endpoint_label(state, r.src_cidr))}</td>"
            f"<td>{html.escape(endpoint_label(state, r.dst_cidr))}</td>"
            f"<td>{r.protocol.value}</td><td>{html.escape(port_label(r))}</td>"
            f'<td class="{action_cls}">{r.action.value.upper()}</td>'
            f"<td>{html.escape(r.comment or '')}</td></tr>"
        )
    return (
        '<div class="fw-rule-wrap" translate="no"><table class="fw-rule-table"><thead><tr>'
        "<th>No</th><th>Status</th><th>Sumber</th><th>Tujuan</th><th>Protokol</th><th>Port</th>"
        "<th>Aksi</th><th>Catatan</th></tr></thead><tbody>" + "".join(rows) + "</tbody></table></div>"
    )


def swap_with_neighbor(state: ProjectState, rule: FirewallRule, delta: int) -> bool:
    """Tukar nomor urut rule dengan tetangganya di chain yang sama (delta -1 = naik, +1 = turun).

    MoveRule hanya mengganti nomor, jadi menukar dua rule memakai dua perintah agar nomor tetap unik.
    """
    chain_rules = sorted([x for x in state.rules if x.chain == rule.chain], key=lambda x: x.order)
    idx = next((i for i, x in enumerate(chain_rules) if x.id == rule.id), None)
    if idx is None or not 0 <= idx + delta < len(chain_rules):
        return False
    other = chain_rules[idx + delta]
    mine, theirs = rule.order, other.order
    ok1, errors1 = apply_command(MoveRule(rule_id=rule.id, new_order=theirs))
    if not ok1:
        render_error_box(errors1)
        return False
    ok2, errors2 = apply_command(MoveRule(rule_id=other.id, new_order=mine))
    if not ok2:
        render_error_box(errors2)
        return False
    return True


# --------------------------------------------------------------------------- dialog hapus


@st.dialog("Hapus aturan")
def _confirm_delete(rule_id: str, summary: str) -> None:
    st.write(f"Hapus aturan **{summary}**? Tindakan ini tidak dapat dibatalkan.")
    c1, c2 = st.columns(2)
    if c1.button("Hapus aturan", type="primary", key="dlg_rule_del_yes", width="stretch"):
        ok, errors = apply_command(RemoveRule(rule_id=rule_id))
        if ok:
            st.toast("Aturan dihapus.")
            st.rerun()
        else:
            render_error_box(errors)
    if c2.button("Batal", key="dlg_rule_del_no", width="stretch"):
        st.rerun()


# --------------------------------------------------------------------------- bagian halaman


def _policy_row(state: ProjectState) -> None:
    st.markdown("**Kebijakan default per chain**")
    st.caption("Berlaku jika tidak ada rule yang cocok sampai akhir chain.")
    cols = st.columns(3)
    for col, chain in zip(cols, _CHAINS):
        cur = state.get_default_policy(chain)
        with col:
            st.markdown(f'<span class="fw-code-pill" translate="no">{chain.value.upper()}</span>', unsafe_allow_html=True)
            choice = st.selectbox(
                f"Kebijakan {chain.value.upper()}",
                [Action.ACCEPT, Action.DROP],
                index=0 if cur == Action.ACCEPT else 1,
                format_func=lambda a: a.value.upper(),
                key=f"sel_pol_{chain.value}",
                label_visibility="collapsed",
            )
            if st.button("Simpan", key=f"btn_pol_{chain.value}", disabled=(choice == cur), width="stretch"):
                ok, errors = apply_command(SetDefaultPolicy(chain=chain, action=choice))
                if ok:
                    st.toast(f"Kebijakan {chain.value.upper()} menjadi {choice.value.upper()}.")
                    st.rerun()
                else:
                    render_error_box(errors)


def _chain_tab(state: ProjectState, chain: Chain) -> None:
    rules = sorted([r for r in state.rules if r.chain == chain], key=lambda x: x.order)
    if not rules:
        st.caption(
            f"Belum ada aturan di chain {chain.value.upper()}. "
            f"Semua paket langsung memakai kebijakan default ({state.get_default_policy(chain).value.upper()})."
        )
        return
    st.markdown(table_html(state, rules), unsafe_allow_html=True)
    by_id = {r.id: r for r in rules}
    chosen = st.selectbox(
        "Pilih aturan untuk dikelola",
        list(by_id),
        format_func=lambda rid: rule_summary(state, by_id[rid]),
        key=f"sel_manage_{chain.value}",
    )
    r = by_id[chosen]
    b1, b2, b3, b4 = st.columns(4)
    with b1:
        first = rules[0].id == r.id
        if st.button("Naik", icon=":material/arrow_upward:", key=f"up_{chain.value}", disabled=first, width="stretch"):
            if swap_with_neighbor(state, r, -1):
                st.rerun()
    with b2:
        last = rules[-1].id == r.id
        if st.button("Turun", icon=":material/arrow_downward:", key=f"down_{chain.value}", disabled=last, width="stretch"):
            if swap_with_neighbor(state, r, +1):
                st.rerun()
    with b3:
        label = "Matikan" if r.enabled else "Aktifkan"
        if st.button(label, key=f"toggle_{chain.value}", width="stretch"):
            apply_command(ToggleRule(rule_id=r.id))
            st.rerun()
    with b4:
        if st.button("Hapus", icon=":material/delete:", key=f"delete_{chain.value}", width="stretch"):
            _confirm_delete(r.id, rule_summary(state, r))


def _endpoint_input(state: ProjectState, label: str, key: str) -> Optional[str]:
    opts = endpoint_options(state)
    values = [v for v, _ in opts]
    labels = dict(opts)
    picked = st.selectbox(label, values, format_func=labels.get, key=f"sel_{key}")
    if picked == _ANY:
        return None
    if picked == _MANUAL:
        manual = st.text_input(f"{label} (CIDR)", placeholder="misal: 192.168.1.0/24", key=f"input_{key}_manual")
        return manual.strip() or None
    return picked


def _add_rule_form(state: ProjectState) -> None:
    st.markdown("**Tambah aturan**")
    st.caption("Aturan baru ditaruh paling bawah; geser dengan Naik/Turun agar urutannya tepat.")
    c1, c2, c3 = st.columns(3)
    with c1:
        chain = st.selectbox("Chain", _CHAINS, format_func=lambda c: c.value.upper(), key="sel_rule_chain")
        action = st.selectbox("Aksi", [Action.ACCEPT, Action.DROP], format_func=lambda a: a.value.upper(), key="sel_rule_action")
    with c2:
        src = _endpoint_input(state, "Sumber", "rule_src")
        dst = _endpoint_input(state, "Tujuan", "rule_dst")
    with c3:
        proto = st.selectbox(
            "Protokol",
            [Protocol.TCP, Protocol.UDP, Protocol.ICMP, Protocol.ANY],
            format_func=lambda p: p.value.upper(),
            key="sel_rule_proto",
        )
        dport = st.text_input("Port tujuan", placeholder="misal: 80 atau 1000-2000", key="input_rule_dport")
    comment = st.text_input("Catatan (opsional)", placeholder="misal: Izinkan web HTTP", key="input_rule_comment")
    if st.button("Tambah aturan", type="primary", key="btn_add_rule"):
        n = len(state.rules) + 1
        rule_id = f"rule_{n}"
        while any(x.id == rule_id for x in state.rules):
            n += 1
            rule_id = f"rule_{n}"
        new_rule = FirewallRule(
            id=rule_id,
            order=max([x.order for x in state.rules], default=0) + 1,
            enabled=True,
            chain=chain,
            src_cidr=src,
            dst_cidr=dst,
            protocol=proto,
            src_port=None,
            dst_port=dport.strip() or None,
            action=action,
            comment=comment.strip(),
        )
        ok, errors = apply_command(AddRule(rule=new_rule))
        if ok:
            st.toast("Aturan ditambahkan.")
            st.rerun()
        else:
            render_error_box(errors)


def render_firewall_rules_page() -> None:
    render_simulation_banner()
    page_header(
        title="Aturan Firewall",
        description="Rule dievaluasi dari atas ke bawah; rule pertama yang cocok menang.",
    )
    render_workflow_rail("firewall_rules")

    state = get_state()
    col_main, col_side = st.columns([2.2, 1.0], gap="medium")

    with col_main:
        _policy_row(state)
        st.divider()
        chains_tabs = st.tabs([f"{c.value.upper()} ({len([r for r in state.rules if r.chain == c])})" for c in _CHAINS])
        for tab, chain in zip(chains_tabs, _CHAINS):
            with tab:
                _chain_tab(state, chain)
        st.divider()
        _add_rule_form(state)

    with col_side:
        if state.devices:
            layout = topo.resolve_layout(state, get_layout())
            payload = topo.component_payload(state, layout, get_cables(), None, get_selected_device(), editable=False)
            event = topology_view(payload, key="rules_topology")
            if apply_component_event(event, "rules_topology"):
                st.rerun()
        with st.expander("Konsep penting", expanded=False):
            st.markdown(
                "- **Urutan**: rule bernomor kecil dievaluasi lebih dulu.\n"
                "- **First match wins**: begitu cocok, keputusan diambil dan evaluasi berhenti.\n"
                "- **FORWARD**: paket yang melintasi router antar subnet.\n"
                "- **INPUT**: paket yang menuju router sendiri.\n"
                "- **Default policy**: berlaku jika tidak ada rule yang cocok.\n"
                "- Aturan nonaktif dilewati."
            )
        next_steps([
            ("Jalankan Uji Paket", "packet_sim"),
            ("Lihat Jalur di 3D", "viz3d"),
            ("Buka Log Trafik", "traffic_logs"),
        ])

    render_flow_next("packet_sim", "Simulasi Paket", "Uji aturan firewall ini dengan mengirimkan paket virtual.")
