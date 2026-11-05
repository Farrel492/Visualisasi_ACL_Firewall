"""Konfigurasi Perangkat: IP interface, status port, dan default gateway, dengan topologi di sampingnya."""

from __future__ import annotations

import ipaddress

import streamlit as st

from firewall_sim.config.service import SetGateway, SetInterfaceEnabled, SetInterfaceIP
from firewall_sim.core.models import DeviceType
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
from firewall_sim.ui.state import (
    apply_command,
    get_cables,
    get_layout,
    get_selected_device,
    get_state,
    set_selected_device,
)
from firewall_sim.ui.widgets import apply_component_event, topology_view


def _validate_ipv4_cidr_inline(cidr_str: str) -> tuple[bool, str]:
    """Validasi format IPv4 CIDR secara inline dalam Bahasa Indonesia."""
    if not cidr_str or not cidr_str.strip():
        return True, ""  # kosong = hapus alamat
    try:
        network = ipaddress.IPv4Network(cidr_str.strip(), strict=False)
        if network.prefixlen == 0 or network.prefixlen > 32:
            return False, "Prefix subnet mask harus bernilai antara /1 hingga /32."
        if "/" not in cidr_str:
            return False, "Tambahkan prefix subnet, misalnya /24. Contoh: 192.168.1.10/24"
        return True, ""
    except ValueError:
        return False, "Format IPv4 CIDR tidak valid. Contoh yang benar: 192.168.1.10/24"


def _validate_ipv4_address_inline(ip_str: str) -> tuple[bool, str]:
    """Validasi alamat IPv4 tunggal secara inline dalam Bahasa Indonesia."""
    if not ip_str or not ip_str.strip():
        return True, ""
    try:
        ipaddress.IPv4Address(ip_str.strip())
        return True, ""
    except ValueError:
        return False, "Alamat IP gateway tidak valid. Contoh yang benar: 192.168.1.1"


def _peer_text(state, iface_id: str) -> str:
    for link in state.links:
        other = link.interface_b if link.interface_a == iface_id else link.interface_a if link.interface_b == iface_id else None
        if other:
            dev = topo.find_device_of_interface(state, other)
            iface = state.get_interface(other)
            if dev and iface:
                return f"{dev.name} {iface.name}"
    return "tidak terhubung"


def _on_pick_device() -> None:
    set_selected_device(st.session_state.get("sel_config_dev"))


def _gateway_form(dev) -> None:
    with st.form(f"form_gw_{dev.id}", border=True):
        st.markdown("**Default gateway**")
        cur = dev.default_gateway or ""
        st.caption(f"Saat ini: {cur or 'belum diatur'}")
        new = st.text_input("Gateway baru", value=cur, placeholder="misal: 192.168.1.1", key=f"input_gw_{dev.id}")
        if st.form_submit_button("Simpan gateway", type="primary"):
            cleaned = new.strip() or None
            ok_fmt, msg = _validate_ipv4_address_inline(cleaned or "")
            if not ok_fmt:
                st.error(msg)
            else:
                ok, errors = apply_command(SetGateway(device_id=dev.id, default_gateway=cleaned))
                if ok:
                    st.toast(f"Gateway {dev.name} disimpan.")
                    st.rerun()
                else:
                    render_error_box(errors)


def _interface_rows(state, dev) -> None:
    used = topo.linked_interface_ids(state)
    ifaces = [i for i in dev.interfaces if dev.type != DeviceType.SWITCH or i.id in used]
    if dev.type == DeviceType.SWITCH:
        st.caption(
            f"Switch Layer 2 tidak memakai alamat IP. {len(ifaces)} dari {len(dev.interfaces)} port terpakai."
        )
    if not ifaces:
        st.info("Belum ada port yang terpakai pada perangkat ini.")
        return
    for iface in ifaces:
        with st.container(border=True):
            top = st.columns([1.2, 2.2, 1.4])
            top[0].markdown(f"**{iface.name}**")
            top[1].caption(f"Terhubung ke: {_peer_text(state, iface.id)}")
            top[2].markdown(f"Status: **{'aktif' if iface.enabled else 'nonaktif'}**")
            if dev.type != DeviceType.SWITCH:
                with st.form(f"form_ip_{iface.id}", border=False):
                    cur = iface.ipv4_cidr or ""
                    c_ip, c_btn = st.columns([3, 1.2])
                    new = c_ip.text_input(
                        f"Alamat IP {iface.name} (saat ini: {cur or 'belum ada'})",
                        value=cur,
                        placeholder="misal: 192.168.1.10/24",
                        key=f"input_ip_{iface.id}",
                    )
                    c_btn.markdown("&nbsp;", unsafe_allow_html=True)
                    if c_btn.form_submit_button("Simpan IP", type="primary", width="stretch"):
                        cleaned = new.strip() or None
                        ok_fmt, msg = _validate_ipv4_cidr_inline(cleaned or "")
                        if not ok_fmt:
                            st.error(msg)
                        else:
                            ok, errors = apply_command(
                                SetInterfaceIP(device_id=dev.id, interface_id=iface.id, ipv4_cidr=cleaned)
                            )
                            if ok:
                                st.toast(f"Alamat {iface.name} disimpan.")
                                st.rerun()
                            else:
                                render_error_box(errors)
            label = "Nonaktifkan port" if iface.enabled else "Aktifkan port"
            if st.button(label, key=f"btn_st_{iface.id}", width="content"):
                ok, errors = apply_command(SetInterfaceEnabled(interface_id=iface.id, enabled=not iface.enabled))
                if ok:
                    st.toast(f"Status {iface.name} diubah.")
                    st.rerun()
                else:
                    render_error_box(errors)


def render_device_config_page() -> None:
    render_simulation_banner()
    page_header(
        title="Konfigurasi Perangkat",
        description="Atur alamat IP, status port, dan default gateway. Klik perangkat di topologi untuk memilihnya.",
    )
    render_workflow_rail("device_config")

    state = get_state()
    if not state.devices:
        empty_state(
            message="Belum ada perangkat dalam topologi untuk dikonfigurasi.",
            action_label="Buat Perangkat di Topologi 2D",
            target_page_or_callback="network",
            key="empty_device_config_btn",
            icon=":material/settings:",
        )
        return

    names = {d.id: f"{d.name} ({topo.type_label(d.type)})" for d in state.devices}
    selected = get_selected_device()
    if selected not in names:
        selected = state.devices[0].id
        set_selected_device(selected)
    st.session_state["sel_config_dev"] = selected  # sinkronkan dengan klik di topologi

    col_main, col_side = st.columns([1.5, 1.0], gap="medium")
    with col_main:
        dev_id = st.selectbox(
            "Perangkat yang dikonfigurasi",
            list(names),
            format_func=names.get,
            key="sel_config_dev",
            on_change=_on_pick_device,
        )
        dev = state.get_device(dev_id)
        if dev is None:
            return
        used = topo.linked_interface_ids(state)
        n_used = len([i for i in dev.interfaces if i.id in used])
        st.caption(f"{topo.type_label(dev.type)}, {n_used} dari {len(dev.interfaces)} port terpakai.")
        if dev.type in (DeviceType.PC, DeviceType.SERVER):
            _gateway_form(dev)
        _interface_rows(state, dev)

    with col_side:
        layout = topo.resolve_layout(state, get_layout())
        payload = topo.component_payload(state, layout, get_cables(), None, selected, editable=False)
        event = topology_view(payload, key="config_topology")
        if apply_component_event(event, "config_topology"):
            st.rerun()
        with st.expander("Panduan konfigurasi", expanded=False):
            st.markdown(
                "- **IPv4 CIDR**: alamat wajib disertai prefix, misalnya `/24`.\n"
                "- **Gateway**: harus satu subnet dengan alamat host.\n"
                "- **Switch**: Layer 2, tanpa alamat IP.\n"
                "- **Port nonaktif**: paket tidak dapat melewatinya."
            )
        next_steps([
            ("Tinjau Topologi 2D", "network"),
            ("Atur Aturan Firewall", "firewall_rules"),
            ("Jalankan Uji Paket", "packet_sim"),
        ])

    render_flow_next("firewall_rules", "Aturan Firewall", "Lanjutkan ke konfigurasi aturan firewall.")
