"""Topologi 2D: layar interaktif (gambar perangkat, seret untuk memindahkan, kabel Fa/Se)."""

from __future__ import annotations

from dataclasses import replace
import re

import streamlit as st

from firewall_sim.config.service import AddDevice, AddLink, RemoveDevice, RemoveLink
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
    reset_layout,
    set_cable,
    set_selected_device,
)
from firewall_sim.ui.widgets import apply_component_event, topology_view

ADDABLE_TYPES = [DeviceType.PC, DeviceType.SERVER, DeviceType.SWITCH]


def _peer_text(state, iface_id: str) -> str:
    for link in state.links:
        other = None
        if link.interface_a == iface_id:
            other = link.interface_b
        elif link.interface_b == iface_id:
            other = link.interface_a
        if other:
            dev = topo.find_device_of_interface(state, other)
            iface = state.get_interface(other)
            if dev and iface:
                return f"{dev.name} {iface.name}"
    return "tidak terhubung"


def _unique_id(state, base: str) -> str:
    existing = {d.id for d in state.devices}
    slug = re.sub(r"[^a-z0-9_]+", "_", base.strip().lower()).strip("_") or "perangkat"
    candidate, n = slug, 2
    while candidate in existing:
        candidate = f"{slug}_{n}"
        n += 1
    return candidate


def _form_add_device(state) -> None:
    with st.form("form_add_dev", border=False):
        name = st.text_input("Nama perangkat", placeholder="misal: PC C", key="input_add_dev_name")
        dtype = st.selectbox(
            "Jenis perangkat",
            ADDABLE_TYPES,
            format_func=topo.type_label,
            key="sel_add_dev_type",
        )
        ip = gw = ""
        if dtype in (DeviceType.PC, DeviceType.SERVER):
            ip = st.text_input(
                "Alamat IP (CIDR)",
                value="192.168.1.30/24" if dtype == DeviceType.PC else "10.0.0.20/24",
                key="input_add_dev_ip",
            )
            gw = st.text_input(
                "Default gateway",
                value="192.168.1.1" if dtype == DeviceType.PC else "10.0.0.1",
                key="input_add_dev_gw",
            )
        if st.form_submit_button("Tambah perangkat", type="primary", width="stretch"):
            if not name.strip():
                st.error("Nama perangkat tidak boleh kosong.")
                return
            dev_id = _unique_id(state, name)
            ifaces = topo.default_interfaces(dev_id, dtype)
            if dtype in (DeviceType.PC, DeviceType.SERVER) and ip.strip():
                ifaces = (replace(ifaces[0], ipv4_cidr=ip.strip()),) + ifaces[1:]
            ok, errors = apply_command(
                AddDevice(
                    name=name.strip(),
                    type=dtype,
                    device_id=dev_id,
                    interfaces=ifaces,
                    default_gateway=gw.strip() or None,
                )
            )
            if ok:
                st.toast(f"Perangkat {name.strip()} ditambahkan.")
                st.rerun()
            else:
                render_error_box(errors)


def _form_add_link(state) -> None:
    cable = st.radio(
        "Jenis kabel",
        [topo.CABLE_FA, topo.CABLE_SE],
        format_func=lambda c: topo.CABLE_LABELS[c],
        key="sel_cable_kind",
    )
    candidates = [d for d in state.devices if topo.free_interfaces(state, d.id, cable)]
    if len(candidates) < 2:
        st.info(
            "Belum ada dua perangkat dengan port "
            + ("FastEthernet (Fa)" if cable == topo.CABLE_FA else "Serial (Se)")
            + " yang bebas. Putuskan link lain atau tambahkan perangkat lebih dulu.",
            icon=":material/info:",
        )
        return
    names = {d.id: d.name for d in candidates}
    dev_a = st.selectbox("Perangkat pertama", list(names), format_func=names.get, key="sel_link_dev_a")
    others = [d for d in candidates if d.id != dev_a]
    dev_b = st.selectbox(
        "Perangkat kedua", [d.id for d in others], format_func=names.get, key="sel_link_dev_b"
    )
    ports_a = topo.free_interfaces(state, dev_a, cable)
    ports_b = topo.free_interfaces(state, dev_b, cable)
    port_a = st.selectbox("Port pertama", [p.id for p in ports_a],
                          format_func=lambda i: state.get_interface(i).name, key="sel_link_port_a")
    port_b = st.selectbox("Port kedua", [p.id for p in ports_b],
                          format_func=lambda i: state.get_interface(i).name, key="sel_link_port_b")
    if st.button("Hubungkan dengan kabel", type="primary", width="stretch", key="btn_add_link"):
        ok, errors = apply_command(AddLink(interface_a=port_a, interface_b=port_b))
        if ok:
            for link in get_state().links:
                if {link.interface_a, link.interface_b} == {port_a, port_b}:
                    set_cable(link.id, cable)
            st.toast("Kabel terpasang.")
            st.rerun()
        else:
            render_error_box(errors)


def _form_delete(state) -> None:
    deletable = [d for d in state.devices if d.type != DeviceType.ROUTER]
    if deletable:
        dev_id = st.selectbox(
            "Perangkat yang dihapus",
            [d.id for d in deletable],
            format_func=lambda x: state.get_device(x).name,
            key="sel_del_dev",
        )
        st.caption("Link yang terhubung ke perangkat ini ikut diputus.")
        if st.button("Hapus perangkat", width="stretch", key="btn_del_dev"):
            ok, errors = apply_command(RemoveDevice(device_id=dev_id))
            if ok:
                if get_selected_device() == dev_id:
                    set_selected_device(None)
                st.toast("Perangkat dihapus.")
                st.rerun()
            else:
                render_error_box(errors)
    else:
        st.caption("Router firewall tunggal tidak dapat dihapus.")
    st.divider()
    if state.links:
        cables = get_cables()
        link_id = st.selectbox(
            "Link yang diputus",
            [l.id for l in state.links],
            format_func=lambda lid: topo.link_description(state, next(l for l in state.links if l.id == lid), cables),
            key="sel_del_link",
        )
        if st.button("Putuskan link", width="stretch", key="btn_del_link"):
            ok, errors = apply_command(RemoveLink(link_id=link_id))
            if ok:
                st.toast("Link diputus.")
                st.rerun()
            else:
                render_error_box(errors)
    else:
        st.caption("Belum ada link.")


def _inspector(state) -> None:
    names = {d.id: f"{d.name} ({topo.type_label(d.type)})" for d in state.devices}
    selected = get_selected_device()
    if selected not in names:
        selected = state.devices[0].id
    if st.session_state.get("sel_inspect_dev") != selected:
        st.session_state["sel_inspect_dev"] = selected
    dev_id = st.selectbox("Perangkat terpilih", list(names), format_func=names.get, key="sel_inspect_dev")
    if dev_id != get_selected_device():
        set_selected_device(dev_id)
    dev = state.get_device(dev_id)
    cols = st.columns(3)
    cols[0].metric("Nama", dev.name)
    cols[1].metric("Jenis", topo.type_label(dev.type))
    cols[2].metric("Default gateway", dev.default_gateway or "belum diatur")
    used = topo.linked_interface_ids(state)
    rows = [
        {
            "Port": i.name,
            "Alamat IP": i.ipv4_cidr or "-",
            "Status": "aktif" if i.enabled else "nonaktif",
            "Terhubung ke": _peer_text(state, i.id),
        }
        for i in dev.interfaces
        if dev.type != DeviceType.SWITCH or i.id in used
    ]
    if dev.type == DeviceType.SWITCH:
        st.caption(f"{len(used & {i.id for i in dev.interfaces})} dari {len(dev.interfaces)} port terpakai (hanya port terpakai yang ditampilkan).")
    st.dataframe(rows, hide_index=True, width="stretch")


def render_network_page() -> None:
    render_simulation_banner()
    page_header(
        title="Topologi 2D",
        description="Seret perangkat untuk mengatur tata letak; posisi tersimpan otomatis.",
    )
    render_workflow_rail("network")

    state = get_state()
    if not state.devices:
        empty_state(
            message="Topologi masih kosong. Muat demo atau tambahkan perangkat pertama.",
            action_label="Kembali ke Mulai di Sini",
            target_page_or_callback="start_here",
            key="empty_network_btn",
            icon=":material/hub:",
        )
        return

    layout = topo.resolve_layout(state, get_layout())
    payload = topo.component_payload(state, layout, get_cables(), None, get_selected_device(), True)

    col_main, col_side = st.columns([2.4, 1.0], gap="medium")
    with col_main:
        event = topology_view(payload, key="network_topology", intro=True)
        if apply_component_event(event, "network_topology"):
            st.rerun()
        _inspector(state)

    with col_side:
        with st.container(border=True):
            st.markdown("**Kelola topologi**")
            with st.expander("Tambah perangkat", expanded=False):
                _form_add_device(state)
            with st.expander("Hubungkan dengan kabel", expanded=False):
                _form_add_link(state)
            with st.expander("Hapus perangkat atau link", expanded=False):
                _form_delete(state)
            if st.button("Reset posisi perangkat", width="stretch", key="btn_reset_layout"):
                reset_layout()
                st.toast("Posisi perangkat dikembalikan.")
                st.rerun()
        st.caption(
            "Port Fa untuk FastEthernet, Se untuk Serial. Switch punya 24 port Fa; "
            "satu port hanya dapat dipakai satu kabel."
        )
        next_steps([
            ("Konfigurasi IP dan Gateway", "device_config"),
            ("Atur Kebijakan Firewall", "firewall_rules"),
            ("Uji Simulasi Paket", "packet_sim"),
        ])

    render_flow_next("firewall_rules", "Aturan Firewall", "Lanjutkan ke konfigurasi aturan firewall.")
