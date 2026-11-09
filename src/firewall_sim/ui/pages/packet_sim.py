"""Simulasi Paket: kirim paket virtual dan pahami KENAPA ia diterima atau ditolak."""

from __future__ import annotations

import html
import ipaddress
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import streamlit as st

from firewall_sim.core.models import (
    Decision,
    DeviceType,
    PacketTest,
    ProjectState,
    Protocol,
    SimulationResult,
)
from firewall_sim.core.simulator import simulate_packet
from firewall_sim.ui import topo
from firewall_sim.ui.components import (
    empty_state,
    next_steps,
    page_header,
    render_flow_next,
    render_simulation_banner,
    render_workflow_rail,
)
from firewall_sim.ui.pages.firewall_rules import rule_summary
from firewall_sim.ui.state import (
    add_simulation_run,
    clear_test_history,
    get_cables,
    get_layout,
    get_selected_device,
    get_simulation_pairs,
    get_state,
    set_nav_page,
)
from firewall_sim.ui.widgets import apply_component_event, topology_view

_LEGACY_KEYS = {
    ("pc_a", "server", Protocol.TCP): "btn_quick_pca_web",
    ("pc_b", "server", Protocol.TCP): "btn_quick_pcb_web",
    ("pc_a", "pc_b", Protocol.ICMP): "btn_quick_pca_pcb",
}
_DECISION_CLASS = {
    Decision.ACCEPT: ("ok", "var(--fw-led-ok)", "var(--fw-ok-text)"),
    Decision.DROP: ("deny", "var(--fw-led-deny)", "var(--fw-deny-text)"),
}
_AMBER = ("amber", "var(--fw-led-amber)", "var(--fw-amber-text)")


# --------------------------------------------------------------------------- fungsi bantu murni


def device_ip(state: ProjectState, device_id: str) -> Optional[str]:
    dev = state.get_device(device_id)
    if dev is None:
        return None
    for iface in dev.interfaces:
        if iface.ipv4_cidr:
            return str(ipaddress.ip_interface(iface.ipv4_cidr).ip)
    return None


def device_name(state: ProjectState, device_id: Optional[str]) -> str:
    dev = state.get_device(device_id) if device_id else None
    return dev.name if dev else (device_id or "-")


def quick_presets(state: ProjectState) -> List[Dict[str, Any]]:
    """Tiga uji umum yang dibangun dari topologi aktif (bukan nama perangkat yang dikunci)."""
    pcs = [d for d in state.devices if d.type == DeviceType.PC and device_ip(state, d.id)]
    servers = [d for d in state.devices if d.type == DeviceType.SERVER and device_ip(state, d.id)]
    presets: List[Dict[str, Any]] = []
    if servers:
        for pc in pcs[:2]:
            presets.append(
                {"src": pc.id, "dst": servers[0].id, "proto": Protocol.TCP, "dport": 80,
                 "label": f"{pc.name} ke {servers[0].name}, HTTP 80"}
            )
    if len(pcs) >= 2:
        presets.append(
            {"src": pcs[0].id, "dst": pcs[1].id, "proto": Protocol.ICMP, "dport": None,
             "label": f"{pcs[0].name} ping {pcs[1].name}"}
        )
    elif pcs and servers:
        presets.append(
            {"src": pcs[0].id, "dst": servers[0].id, "proto": Protocol.ICMP, "dport": None,
             "label": f"{pcs[0].name} ping {servers[0].name}"}
        )
    for p in presets:
        p["key"] = _LEGACY_KEYS.get((p["src"], p["dst"], p["proto"]), f"btn_quick_{p['src']}_{p['dst']}_{p['proto'].value}")
    return presets


def run_packet(
    state: ProjectState,
    src_id: str,
    dst_id: Optional[str],
    dst_ip: Optional[str],
    proto: Protocol,
    dport: Optional[int],
    sport: int = 49152,
) -> SimulationResult:
    pkt = PacketTest(
        id=f"test_{time.time_ns() // 1000}",
        source_device_id=src_id,
        destination_device_id=dst_id,
        destination_ip=dst_ip or (device_ip(state, dst_id) if dst_id else None),
        protocol=proto,
        src_port=sport if proto != Protocol.ICMP else None,
        dst_port=dport if proto != Protocol.ICMP else None,
        timestamp=datetime.now(),
        config_revision=state.config_revision,
    )
    res = simulate_packet(state, pkt)
    add_simulation_run(pkt, res)
    return res


def target_text(state: ProjectState, packet: PacketTest) -> str:
    dst = device_name(state, packet.destination_device_id) if packet.destination_device_id else (packet.destination_ip or "-")
    proto = packet.protocol.value.upper()
    port = f"/{packet.dst_port}" if packet.dst_port else ""
    return f"{device_name(state, packet.source_device_id)} ke {dst}  {proto}{port}"


def rule_text(state: ProjectState, result: SimulationResult) -> str:
    """Penjelasan singkat penentu keputusan: nomor aturan + chain, atau kebijakan default."""
    if not result.matched_rule_id:
        return "kebijakan default (tidak ada aturan yang cocok)"
    rule = next((r for r in state.rules if r.id == result.matched_rule_id), None)
    if rule is None:
        return "aturan yang sudah dihapus"
    return f"aturan #{rule.order}, chain {rule.chain.value.upper()}"


def friendly_text(state: ProjectState, raw: str) -> str:
    """Teks dari engine tanpa ID internal: "rule ID 'x' (order 2)" menjadi "aturan #2", ID perangkat menjadi namanya."""
    text = re.sub(r"rule ID '[^']*' \(order (\d+)\)", r"aturan #\1", raw)
    for dev in state.devices:  # ID perangkat yang terselip di teks diganti namanya
        text = re.sub(rf"\b{re.escape(dev.id)}\b", dev.name, text)
    return text


def friendly_reason(state: ProjectState, result: SimulationResult) -> str:
    return friendly_text(state, result.reason)


def verdict_style(decision: Decision):
    return _DECISION_CLASS.get(decision, _AMBER)


def result_card_html(state: ProjectState, packet: PacketTest, result: SimulationResult) -> str:
    led, color, text_color = verdict_style(result.decision)
    return (
        f'<div class="fw-result" style="--c:{color}" translate="no">'
        f'<div class="fw-result-meta">{result.timestamp.strftime("%H:%M:%S")}</div>'
        f'<div class="fw-result-title">{html.escape(target_text(state, packet))}</div>'
        f'<div class="fw-result-verdict"><span class="fw-led {led}"></span>'
        f'<b style="color:{text_color}">{result.decision.value}</b> oleh {html.escape(rule_text(state, result))}</div>'
        f'<div class="fw-result-reason">{html.escape(friendly_reason(state, result))}</div></div>'
    )


def history_rows(state: ProjectState, pairs) -> List[Dict[str, str]]:
    rows = []
    for pkt, res in pairs:
        dst = device_name(state, pkt.destination_device_id) if pkt.destination_device_id else (pkt.destination_ip or "-")
        proto = pkt.protocol.value.upper() + (f"/{pkt.dst_port}" if pkt.dst_port else "")
        rows.append(
            {
                "Waktu": res.timestamp.strftime("%H:%M:%S"),
                "Sumber": device_name(state, pkt.source_device_id),
                "Tujuan": dst,
                "Protokol": proto,
                "Keputusan": res.decision.value,
                "Penentu": rule_text(state, res),
            }
        )
    return rows


# --------------------------------------------------------------------------- dialog


@st.dialog("Hapus riwayat uji")
def _dialog_clear_history() -> None:
    st.write("Hapus semua hasil uji paket? Log trafik dan peringatan tidak ikut terhapus.")
    c1, c2 = st.columns(2)
    if c1.button("Hapus riwayat", type="primary", key="dlg_hist_yes", width="stretch"):
        clear_test_history()
        st.toast("Riwayat uji dihapus.")
        st.rerun()
    if c2.button("Batal", key="dlg_hist_no", width="stretch"):
        st.rerun()


# --------------------------------------------------------------------------- bagian halaman


def _quick_tests(state: ProjectState) -> None:
    presets = quick_presets(state)
    st.markdown("**Uji cepat**")
    if not presets:
        st.caption("Tambahkan PC dan Server ber-IP di Topologi 2D untuk mendapat uji cepat.")
        return
    cols = st.columns(len(presets))
    for col, p in zip(cols, presets):
        with col:
            if st.button(p["label"], key=p["key"], width="stretch"):
                run_packet(state, p["src"], p["dst"], None, p["proto"], p["dport"])
                st.toast("Uji paket dijalankan.")
                st.rerun()


def _custom_packet(state: ProjectState, expanded: bool) -> None:
    hosts = [d for d in state.devices if d.type != DeviceType.SWITCH]
    names = {d.id: f"{d.name} ({device_ip(state, d.id) or 'tanpa IP'})" for d in hosts}
    with st.expander("Paket kustom", expanded=expanded):
        c1, c2 = st.columns(2)
        with c1:
            src = st.selectbox("Sumber", list(names), format_func=names.get, key="sel_pkt_src")
            mode = st.radio("Tujuan", ["Pilih perangkat", "Alamat IP manual"], horizontal=True, key="rad_pkt_dst_mode")
            dst_id: Optional[str] = None
            dst_ip: Optional[str] = None
            if mode == "Pilih perangkat":
                others = [d for d in hosts if d.id != src]
                if others:
                    dst_id = st.selectbox("Perangkat tujuan", [d.id for d in others], format_func=names.get, key="sel_pkt_dst")
                else:
                    st.caption("Tidak ada perangkat tujuan lain.")
            else:
                dst_ip = st.text_input("IP tujuan", placeholder="misal: 10.0.0.10", key="input_pkt_custom_ip").strip() or None
        with c2:
            proto = st.selectbox("Protokol", [Protocol.TCP, Protocol.UDP, Protocol.ICMP], format_func=lambda p: p.value.upper(), key="sel_pkt_proto")
            sport = st.number_input("Port sumber", min_value=1024, max_value=65535, value=49152, key="input_pkt_sport")
            dport = st.number_input("Port tujuan", min_value=1, max_value=65535, value=80, disabled=(proto == Protocol.ICMP), key="input_pkt_dport")
        if st.button("Jalankan uji paket", type="primary", key="btn_run_custom_packet"):
            if mode == "Alamat IP manual" and not dst_ip:
                st.error("Isi IP tujuan terlebih dahulu.")
            elif mode == "Pilih perangkat" and not dst_id:
                st.error("Pilih perangkat tujuan.")
            else:
                run_packet(state, src, dst_id, dst_ip, proto, int(dport), int(sport))
                st.toast("Uji paket dijalankan.")
                st.rerun()


def _trace_list(state: ProjectState, result: SimulationResult) -> None:
    items = []
    for i, step in enumerate(result.trace, start=1):
        items.append(f"{i}. **{device_name(state, step.device_id)}**: {friendly_text(state, step.description)}")
    st.markdown("\n".join(items) if items else "Tidak ada jejak langkah.")


def _result_section(state: ProjectState, pairs) -> None:
    options = list(range(len(pairs)))
    idx = st.selectbox(
        "Hasil yang ditampilkan",
        options,
        format_func=lambda i: f"Uji {len(pairs) - i}  {pairs[i][1].timestamp.strftime('%H:%M:%S')}  {target_text(state, pairs[i][0])}  {pairs[i][1].decision.value}",
        key="sel_pkt_result",
        label_visibility="collapsed",
    )
    pkt, res = pairs[idx]
    st.markdown(result_card_html(state, pkt, res), unsafe_allow_html=True)
    if res.config_revision != state.config_revision:
        st.warning(
            f"Konfigurasi sudah berubah: uji ini dijalankan pada revisi {res.config_revision}, sekarang revisi {state.config_revision}.",
            icon=":material/history:",
        )
    if res.decision == Decision.ACCEPT:
        st.caption("ACCEPT berarti lolos kebijakan simulasi, bukan bukti bahwa layanan di tujuan aktif.")
    rule = next((r for r in state.rules if r.id == res.matched_rule_id), None)
    if rule is not None:
        st.caption(f"Aturan penentu: {rule_summary(state, rule)}")

    layout = topo.resolve_layout(state, get_layout())
    payload = topo.component_payload(state, layout, get_cables(), res, get_selected_device(), editable=False)
    event = topology_view(payload, key="packet_topology")
    if apply_component_event(event, "packet_topology"):
        st.rerun()

    with st.expander("Langkah jalur paket", expanded=True):
        _trace_list(state, res)

    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("Lihat di 3D", icon=":material/view_in_ar:", key="btn_pkt_view_3d", width="stretch"):
            st.session_state["sel_viz3d_test"] = idx
            set_nav_page("viz3d")
            st.rerun()
    with b2:
        if st.button("Lihat di Log", icon=":material/list_alt:", key="btn_pkt_view_log", width="stretch"):
            set_nav_page("traffic_logs")
            st.rerun()
    with b3:
        if st.button("Hapus riwayat", icon=":material/delete:", key="btn_pkt_clear", width="stretch"):
            _dialog_clear_history()


def render_packet_sim_page() -> None:
    render_simulation_banner()
    page_header(
        title="Simulasi Paket",
        description="Kirim paket virtual dan lihat keputusan firewall beserta alasannya.",
    )
    render_workflow_rail("packet_sim")

    state = get_state()
    pairs = get_simulation_pairs()

    if not state.devices:
        empty_state(
            message="Belum ada perangkat dalam topologi untuk diuji.",
            action_label="Buka Topologi 2D",
            target_page_or_callback="network",
            key="empty_packet_sim_btn",
            icon=":material/send:",
        )
        return

    col_main, col_side = st.columns([2.3, 1.0], gap="medium")
    with col_main:
        _quick_tests(state)
        _custom_packet(state, expanded=not pairs)
        st.divider()
        if not pairs:
            empty_state(
                message="Belum ada hasil uji. Jalankan uji cepat di atas, atau atur aturan firewall terlebih dahulu.",
                action_label="Atur Aturan Firewall",
                target_page_or_callback="firewall_rules",
                key="empty_packet_sim_btn",
                icon=":material/send:",
            )
        else:
            _result_section(state, pairs)
            st.markdown("**Riwayat uji**")
            st.dataframe(history_rows(state, pairs), hide_index=True, width="stretch")

    with col_side:
        with st.expander("Konsep penting", expanded=False):
            st.markdown(
                "- **Satu subnet**: paket antar-host dalam subnet yang sama tidak lewat firewall.\n"
                "- **Antar subnet**: paket melewati router dan dievaluasi di chain FORWARD.\n"
                "- **First match wins**: aturan pertama yang cocok menentukan keputusan.\n"
                "- **DROP**: paket berhenti di router dan tidak sampai ke tujuan.\n"
                "- **NO_ROUTE**: tidak ada jalur; firewall belum sempat memutuskan."
            )
        next_steps([
            ("Putar Jalur di 3D", "viz3d"),
            ("Buka Log Trafik", "traffic_logs"),
            ("Kembali ke Aturan Firewall", "firewall_rules"),
        ])

    render_flow_next("viz3d", "Visualisasi 3D", "Putar ulang jalur paket langkah demi langkah di panggung 3D.")
