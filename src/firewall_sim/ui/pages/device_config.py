"""Device Configuration UI page."""

from __future__ import annotations

import ipaddress
import streamlit as st

from firewall_sim.config.service import (
    SetGateway,
    SetInterfaceEnabled,
    SetInterfaceIP,
)
from firewall_sim.core.models import DeviceType
from firewall_sim.ui.components import (
    empty_state,
    next_steps,
    page_header,
    render_error_box,
    render_simulation_banner,
)
from firewall_sim.ui.state import apply_command, get_state, get_ui_mode


def _validate_ipv4_cidr_inline(cidr_str: str) -> tuple[bool, str]:
    """Validasi format IPv4 CIDR secara inline dalam Bahasa Indonesia."""
    if not cidr_str or not cidr_str.strip():
        return True, ""  # Boleh kosong jika port L2 atau dihapus
    try:
        network = ipaddress.IPv4Network(cidr_str.strip(), strict=False)
        if network.prefixlen == 0 or network.prefixlen > 32:
            return False, "Prefix subnet mask harus bernilai antara /1 hingga /32."
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


def render_device_config_page() -> None:
    """Merender halaman konfigurasi perangkat, interface, dan gateway."""
    render_simulation_banner()
    page_header(
        title="Konfigurasi Perangkat & Interface",
        description="Atur penetapan alamat IP interface, status aktif/nonaktif, dan default gateway host.",
    )

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

    col_main, col_side = st.columns([2.2, 1.0])

    with col_main:
        dev_options = {d.id: f"{d.name} ({d.type.value.upper()})" for d in state.devices}
        selected_id = st.selectbox(
            "Pilih Perangkat untuk Dikonfigurasi:",
            options=list(dev_options.keys()),
            format_func=lambda x: dev_options[x],
            key="sel_config_dev",
        )
        dev = state.get_device(selected_id)
        if not dev:
            return

        with st.container(border=True):
            st.markdown(f"### :material/memory: Perangkat: **{dev.name}** (`{dev.type.value.upper()}`)")

            # Ringkasan Nilai Saat Ini vs Nilai Baru
            c_sum1, c_sum2, c_sum3 = st.columns(3)
            c_sum1.metric("ID Perangkat", dev.id)
            c_sum2.metric("Jumlah Interface", len(dev.interfaces))
            c_sum3.metric("Gateway Saat Ini", dev.default_gateway or "Belum Diatur")

        # 1. Konfigurasi Default Gateway (khusus Host: PC dan Server)
        if dev.type in (DeviceType.PC, DeviceType.SERVER):
            with st.container(border=True):
                st.markdown("#### :material/router: Konfigurasi Default Gateway")
                st.caption(
                    "Setiap host (PC/Server) memerlukan default gateway yang mengarah ke interface router pada subnet yang sama."
                )

                with st.form(f"form_gw_{dev.id}"):
                    curr_gw = dev.default_gateway or ""
                    st.markdown(f"**Nilai Gateway Saat Ini:** `{curr_gw or '(Kosong / Tidak Ada)'}`")

                    new_gw = st.text_input(
                        "Alamat IPv4 Gateway Baru:",
                        value=curr_gw,
                        placeholder="misal: 192.168.1.1",
                        key=f"input_gw_{dev.id}",
                    )

                    btn_sub_gw = st.form_submit_button("Simpan Gateway", type="primary")
                    if btn_sub_gw:
                        cleaned_gw = new_gw.strip() or None
                        is_valid_format, err_msg = _validate_ipv4_address_inline(cleaned_gw or "")
                        if not is_valid_format:
                            st.error(f"Validasi Gagal: {err_msg}")
                        else:
                            success, errors = apply_command(
                                SetGateway(device_id=dev.id, default_gateway=cleaned_gw)
                            )
                            if success:
                                st.toast(f"Gateway untuk '{dev.name}' berhasil diperbarui!")
                                st.rerun()
                            else:
                                render_error_box(errors)

        # 2. Konfigurasi Interface
        with st.container(border=True):
            st.markdown("#### :material/settings_ethernet: Daftar Antarmuka (Interfaces)")
            if not dev.interfaces:
                st.info("Perangkat ini belum memiliki interface.")
            else:
                for iface in dev.interfaces:
                    with st.expander(f"Antarmuka: {iface.name} ({iface.id})", expanded=True):
                        col_ip, col_st = st.columns([2.5, 1.5])

                        with col_ip:
                            if dev.type == DeviceType.SWITCH:
                                st.info("Interface switch Layer 2 murni tidak memerlukan alamat IP.")
                            else:
                                with st.form(f"form_ip_{iface.id}"):
                                    curr_ip = iface.ipv4_cidr or ""
                                    st.markdown(f"**Alamat IP Saat Ini:** `{curr_ip or '(Belum Ditetapkan)'}`")

                                    new_ip = st.text_input(
                                        "Alamat IPv4 CIDR Baru:",
                                        value=curr_ip,
                                        placeholder="misal: 192.168.1.10/24",
                                        key=f"input_ip_{iface.id}",
                                    )

                                    if st.form_submit_button("Simpan Alamat IP", type="primary"):
                                        cleaned_ip = new_ip.strip() or None
                                        is_valid_format, err_msg = _validate_ipv4_cidr_inline(cleaned_ip or "")
                                        if not is_valid_format:
                                            st.error(f"Validasi Gagal: {err_msg}")
                                        else:
                                            success, errors = apply_command(
                                                SetInterfaceIP(
                                                    device_id=dev.id,
                                                    interface_id=iface.id,
                                                    ipv4_cidr=cleaned_ip,
                                                )
                                            )
                                            if success:
                                                st.toast(f"Alamat IP interface '{iface.name}' berhasil disimpan!")
                                                st.rerun()
                                            else:
                                                render_error_box(errors)

                        with col_st:
                            st.markdown("**Status Antarmuka**")
                            st_badge = "🟢 Aktif (Up)" if iface.enabled else "🔴 Nonaktif (Down)"
                            st.markdown(f"Kondisi: **{st_badge}**")

                            toggle_label = "Nonaktifkan Interface" if iface.enabled else "Aktifkan Interface"
                            btn_style = "secondary" if iface.enabled else "primary"
                            if st.button(toggle_label, key=f"btn_st_{iface.id}", type=btn_style, use_container_width=True):
                                success, errors = apply_command(
                                    SetInterfaceEnabled(interface_id=iface.id, enabled=not iface.enabled)
                                )
                                if success:
                                    st.toast(f"Status interface '{iface.name}' berhasil diubah!")
                                    st.rerun()
                                else:
                                    render_error_box(errors)

    with col_side:
        # Panel Panduan Edukasi
        if get_ui_mode() == "Learning":
            with st.container(border=True):
                st.markdown("#### :material/school: Panduan Konfigurasi")
                st.markdown(
                    "- **IPv4 CIDR**: Alamat IP wajib disertai prefix subnet mask (misal `/24` untuk `255.255.255.0`).\n"
                    "- **Subnet Gateway**: IP gateway host harus satu subnet dengan IP interface host tersebut.\n"
                    "- **Switch L2**: Switch menghubungkan perangkat pada collision domain/subnet yang sama tanpa IP L3.\n"
                    "- **Status Up/Down**: Paket tidak dapat melewati interface yang berada dalam status Down."
                )

        # Langkah Berikutnya
        next_steps([
            ("Tinjau Topologi 2D", "network"),
            ("Atur Aturan Firewall", "firewall_rules"),
            ("Jalankan Uji Paket", "packet_sim"),
        ])
