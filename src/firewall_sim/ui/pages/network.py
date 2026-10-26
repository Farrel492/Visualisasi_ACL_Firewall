"""Network 2D visualization and topology management page."""

from __future__ import annotations

import math
import re
from typing import Dict, Tuple
import plotly.graph_objects as go
import streamlit as st

from firewall_sim.config.service import (
    AddDevice,
    AddLink,
    RemoveDevice,
    RemoveLink,
    RenameDevice,
)
from firewall_sim.core.models import Device, DeviceType, Interface, ProjectState
from firewall_sim.ui.components import (
    empty_state,
    next_steps,
    page_header,
    render_error_box,
    render_flow_next,
    render_simulation_banner,
    render_workflow_rail,
)
from firewall_sim.ui.state import apply_command, get_state
from firewall_sim.ui.theme import (
    COLOR_ALLOW,
    COLOR_AMBER,
    COLOR_BASE,
    COLOR_MUTED,
    COLOR_PRIMARY,
    COLOR_SURFACE,
)


def _calculate_layered_layout(state: ProjectState) -> Dict[str, Tuple[float, float]]:
    """Menghitung koordinat 2D deterministik berlapis:
    PC di kiri, Switch di tengah-kiri, Router di tengah, Server di kanan.
    """
    positions: Dict[str, Tuple[float, float]] = {}

    routers = [d for d in state.devices if d.type == DeviceType.ROUTER]
    switches = [d for d in state.devices if d.type == DeviceType.SWITCH]
    pcs = [d for d in state.devices if d.type == DeviceType.PC]
    servers = [d for d in state.devices if d.type == DeviceType.SERVER]

    # Router di posisi pusat (0.0, 0.0)
    for idx, r in enumerate(routers):
        positions[r.id] = (0.0, float(idx * 2.0))

    # PC di kolom kiri (-4.0)
    for idx, pc in enumerate(pcs):
        y_offset = (idx - (len(pcs) - 1) / 2.0) * 2.2
        positions[pc.id] = (-4.5, y_offset)

    # Switch di antara PC dan Router (-2.2)
    for idx, sw in enumerate(switches):
        y_offset = (idx - (len(switches) - 1) / 2.0) * 2.2
        positions[sw.id] = (-2.0, y_offset)

    # Server di kolom kanan (+3.5)
    for idx, srv in enumerate(servers):
        y_offset = (idx - (len(servers) - 1) / 2.0) * 2.2
        positions[srv.id] = (3.5, y_offset)

    # Fallback untuk perangkat lain yang belum terpetakan
    for d in state.devices:
        if d.id not in positions:
            positions[d.id] = (0.0, -3.0)

    return positions


def render_network_page() -> None:
    """Merender halaman workspace topologi 2D."""
    render_simulation_banner()
    page_header(
        title="Topologi 2D",
        description="Visualisasi interaktif keterhubungan perangkat serta konfigurasi antarmuka L2/L3.",
    )
    render_workflow_rail("network")

    state = get_state()

    if not state.devices:
        empty_state(
            message="Topologi jaringan saat ini masih kosong. Silakan muat skenario lab atau tambahkan perangkat pertama Anda.",
            action_label="Kembali ke Mulai di Sini",
            target_page_or_callback="start_here",
            key="empty_network_btn",
            icon=":material/hub:",
        )
        return

    col_main, col_side = st.columns([2.2, 1.0])

    with col_main:
        # Legenda Chip di atas grafik
        st.markdown(
            f"""
            <div style="display:flex;gap:12px;margin-bottom:10px;flex-wrap:wrap;">
                <span class="fw-chip" style="background:#DC262622;border:1px solid #DC2626;padding:3px 10px;border-radius:16px;font-size:0.85rem;color:#F87171;">
                    ◆ <b>Router Firewall</b> (Tengah)
                </span>
                <span class="fw-chip" style="background:#3B82F622;border:1px solid #3B82F6;padding:3px 10px;border-radius:16px;font-size:0.85rem;color:#60A5FA;">
                    ■ <b>L2 Switch</b>
                </span>
                <span class="fw-chip" style="background:#16A34A22;border:1px solid #16A34A;padding:3px 10px;border-radius:16px;font-size:0.85rem;color:#4ADE80;">
                    ● <b>Host PC</b> (Kiri)
                </span>
                <span class="fw-chip" style="background:#8B5CF622;border:1px solid #8B5CF6;padding:3px 10px;border-radius:16px;font-size:0.85rem;color:#C084FC;">
                    ⬡ <b>Web Server</b> (Kanan)
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        positions = _calculate_layered_layout(state)

        # 1. Visualisasi Topologi 2D dengan SVG custom
        from firewall_sim.ui.svg_topology import build_svg_html_component
        # Tidak ada highlight jalur pada halaman jaringan standar
        svg_html = build_svg_html_component(state)
        # Render HTML SVG dalam komponen Streamlit (ukuran responsif)
        st.components.v1.html(svg_html, height=540, scrolling=True)


        # Inspector Perangkat Terpilih
        with st.container(border=True):
            st.markdown("#### :material/search: Inspector Perangkat Terpilih")
            dev_names = {d.id: f"{d.name} ({d.type.value.upper()})" for d in state.devices}
            sel_dev_id = st.selectbox(
                "Pilih perangkat:",
                options=list(dev_names.keys()),
                format_func=lambda x: dev_names[x],
                key="sel_inspect_dev",
            )
            sel_dev = state.get_device(sel_dev_id)
            if sel_dev:
                ci1, ci2, ci3 = st.columns(3)
                ci1.metric(label="Nama Perangkat", value=sel_dev.name)
                ci2.metric(label="Tipe", value=sel_dev.type.value.upper())
                ci3.metric(label="Default Gateway", value=sel_dev.default_gateway or "None")

                st.markdown("**Antarmuka (Interfaces):**")
                if sel_dev.interfaces:
                    for iface in sel_dev.interfaces:
                        st_icon = ":material/check_circle:" if iface.enabled else ":material/cancel:"
                        st_text = "Up" if iface.enabled else "Down"
                        ip_text = iface.ipv4_cidr or "Tidak ada IP (Layer 2 Switch Port)"
                        st.markdown(f"- {st_icon} **{iface.name}** (`{iface.id}`): `{ip_text}` — Status: *{st_text}*")
                else:
                    st.caption("Perangkat ini belum memiliki interface.")

    with col_side:
        # Panel Aksi Topologi
        with st.container(border=True):
            st.markdown("#### :material/tune: Kelola Topologi")

            DEV_TYPE_LABELS = {
                DeviceType.PC: "PC",
                DeviceType.SERVER: "Server",
                DeviceType.SWITCH: "Switch",
            }

            # Form Tambah Perangkat
            with st.expander(":material/add_circle: Tambah Perangkat Baru"):
                with st.form("form_add_dev"):
                    new_dev_name = st.text_input("Nama Perangkat", placeholder="misal: PC C", key="input_add_dev_name")
                    new_dev_type = st.selectbox(
                        "Tipe",
                        [DeviceType.PC, DeviceType.SERVER, DeviceType.SWITCH],
                        format_func=lambda t: DEV_TYPE_LABELS.get(t, t.value),
                        key="sel_add_dev_type",
                    )
                    new_ip = ""
                    new_gw = ""
                    if new_dev_type in (DeviceType.PC, DeviceType.SERVER):
                        default_ip = "192.168.1.30/24" if new_dev_type == DeviceType.PC else "10.0.0.20/24"
                        default_gw = "192.168.1.1" if new_dev_type == DeviceType.PC else "10.0.0.1"
                        new_ip = st.text_input("Alamat IPv4/CIDR", value=default_ip, key="input_add_dev_ip")
                        new_gw = st.text_input("Default Gateway", value=default_gw, key="input_add_dev_gw")

                    if st.form_submit_button("Simpan Perangkat", type="primary", use_container_width=True):
                        if not new_dev_name.strip():
                            st.error("Nama perangkat tidak boleh kosong.")
                        else:
                            dev_slug = re.sub(r"[^a-z0-9_]+", "_", new_dev_name.strip().lower()).strip("_")
                            if not dev_slug:
                                dev_slug = f"dev_{len(state.devices)+1}"

                            if new_dev_type in (DeviceType.PC, DeviceType.SERVER):
                                iface = Interface(
                                    id=f"if_{dev_slug}",
                                    device_id=dev_slug,
                                    name="eth0",
                                    ipv4_cidr=new_ip.strip() or None,
                                    enabled=True,
                                )
                                cmd = AddDevice(
                                    name=new_dev_name.strip(),
                                    type=new_dev_type,
                                    device_id=dev_slug,
                                    interfaces=(iface,),
                                    default_gateway=new_gw.strip() or None,
                                )
                            else:
                                cmd = AddDevice(
                                    name=new_dev_name.strip(),
                                    type=new_dev_type,
                                    device_id=dev_slug,
                                )

                            success, errors = apply_command(cmd)
                            if success:
                                st.toast(f"Perangkat '{new_dev_name}' berhasil ditambahkan!")
                                st.rerun()
                            else:
                                render_error_box(errors)

            # Form Hubungkan Dua Interface
            with st.expander(":material/cable: Hubungkan Link Jaringan"):
                all_ifaces = [(i.id, f"{d.name} -> {i.name} ({i.id})") for d in state.devices for i in d.interfaces]
                connected_ids = {l.interface_a for l in state.links} | {l.interface_b for l in state.links}
                avail_ifaces = [item for item in all_ifaces if item[0] not in connected_ids]

                if len(avail_ifaces) >= 2:
                    with st.form("form_add_link"):
                        if_a = st.selectbox(
                            "Interface A",
                            options=[x[0] for x in avail_ifaces],
                            format_func=lambda x: next((y[1] for y in avail_ifaces if y[0] == x), x),
                            key="sel_link_a",
                        )
                        other_avail = [x for x in avail_ifaces if x[0] != if_a]
                        if_b = st.selectbox(
                            "Interface B",
                            options=[x[0] for x in other_avail],
                            format_func=lambda x: next((y[1] for y in other_avail if y[0] == x), x),
                            key="sel_link_b",
                        )
                        if st.form_submit_button("Hubungkan Link", type="primary", use_container_width=True):
                            success, errors = apply_command(AddLink(interface_a=if_a, interface_b=if_b))
                            if success:
                                st.toast("Kabel link jaringan berhasil dihubungkan!")
                                st.rerun()
                            else:
                                render_error_box(errors)
                else:
                    st.info(
                        "Semua port terpakai; putuskan link lain atau tambah Switch untuk menghubungkan perangkat.",
                        icon=":material/info:",
                    )

            # Form Hapus Perangkat
            with st.expander(":material/delete: Hapus Perangkat"):
                deletable_devices = [d for d in state.devices if d.type != DeviceType.ROUTER]
                if deletable_devices:
                    with st.form("form_del_dev"):
                        del_id = st.selectbox(
                            "Pilih Perangkat untuk Dihapus:",
                            options=[d.id for d in deletable_devices],
                            format_func=lambda x: state.get_device(x).name if state.get_device(x) else x,
                            key="sel_del_dev",
                        )
                        st.caption("Menghapus perangkat akan otomatis memutus link yang terhubung dengannya.")
                        if st.form_submit_button("Hapus Perangkat", use_container_width=True):
                            success, errors = apply_command(RemoveDevice(device_id=del_id))
                            if success:
                                st.toast("Perangkat berhasil dihapus!")
                                st.rerun()
                            else:
                                render_error_box(errors)
                else:
                    st.caption("Tidak ada perangkat yang dapat dihapus (Router firewall tunggal dilindungi).")

            # Form Hapus Link
            with st.expander(":material/link_off: Hapus Link"):
                if state.links:
                    iface_to_dev = {iface.id: dev for dev in state.devices for iface in dev.interfaces}
                    def _format_link_option(link_id: str) -> str:
                        lk = next((l for l in state.links if l.id == link_id), None)
                        if not lk:
                            return link_id
                        dev_a = iface_to_dev.get(lk.interface_a)
                        dev_b = iface_to_dev.get(lk.interface_b)
                        na = dev_a.name if dev_a else lk.interface_a
                        nb = dev_b.name if dev_b else lk.interface_b
                        return f"{lk.id}: {na} ({lk.interface_a}) <-> {nb} ({lk.interface_b})"

                    with st.form("form_del_link"):
                        sel_link_del = st.selectbox(
                            "Pilih Link:",
                            options=[l.id for l in state.links],
                            format_func=_format_link_option,
                            key="sel_del_link",
                        )
                        if st.form_submit_button("Putus Link", use_container_width=True):
                            success, errors = apply_command(RemoveLink(link_id=sel_link_del))
                            if success:
                                st.toast("Link jaringan berhasil diputus!")
                                st.rerun()
                            else:
                                render_error_box(errors)
                else:
                    st.caption("Tidak ada link aktif saat ini.")

        # Langkah Berikutnya
        next_steps([
            ("Konfigurasi IP & Gateway", "device_config"),
            ("Atur Kebijakan Firewall", "firewall_rules"),
            ("Uji Simulasi Paket", "packet_sim"),
        ])

    render_flow_next("firewall_rules", "Aturan Firewall", "Lanjutkan ke konfigurasi aturan firewall.")

