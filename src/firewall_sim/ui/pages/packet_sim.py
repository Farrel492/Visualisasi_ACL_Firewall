"""Packet Simulation and Path Traversal UI page."""

from __future__ import annotations

from datetime import datetime
import streamlit as st

from firewall_sim.core.models import (
    Decision,
    DeviceType,
    PacketTest,
    Protocol,
)
from firewall_sim.core.simulator import simulate_packet
from firewall_sim.ui.components import (
    empty_state,
    next_steps,
    page_header,
    render_flow_next,
    render_simulation_banner,
    render_workflow_rail,
)
from firewall_sim.ui.state import (
    add_simulation_run,
    get_simulation_history,
    get_state,
    is_learning,
)
from firewall_sim.ui.theme import (
    COLOR_ALLOW,
    COLOR_AMBER,
    COLOR_DENY,
    COLOR_MUTED,
    get_decision_badge,
)


def render_packet_sim_page() -> None:
    """Merender halaman simulasi paket dan penelusuran jalur jaringan virtual."""
    render_simulation_banner()
    page_header(
        title="Simulasi Paket",
        description="Kirim paket virtual untuk menguji evaluasi firewall secara nyata dan menelusuri rute L2/L3.",
    )
    render_workflow_rail("packet_sim")

    state = get_state()
    history = get_simulation_history()

    col_main, col_side = st.columns([2.2, 1.0])

    with col_main:
        # Tombol Uji Cepat (3 Skenario Umum dari Topologi Aktif)
        with st.container(border=True):
            st.markdown("#### :material/bolt: Uji Cepat (Preset Topologi)")
            qc1, qc2, qc3 = st.columns(3)

            with qc1:
                if st.button("PC A -> Server :80 (HTTP)", icon=":material/public:", key="btn_quick_pca_web", use_container_width=True):
                    pkt = PacketTest(
                        id=f"test_quick_web_{int(datetime.now().timestamp() * 1000)}",
                        source_device_id="pc_a",
                        destination_device_id="server",
                        destination_ip="10.0.0.10",
                        protocol=Protocol.TCP,
                        src_port=49152,
                        dst_port=80,
                        timestamp=datetime.now(),
                        config_revision=state.config_revision,
                    )
                    res = simulate_packet(state, pkt)
                    add_simulation_run(pkt, res)
                    st.toast("Uji PC A -> Server port 80 berhasil dijalankan!")
                    st.rerun()

            with qc2:
                if st.button("PC B -> Server :80 (HTTP)", icon=":material/block:", key="btn_quick_pcb_web", use_container_width=True):
                    pkt = PacketTest(
                        id=f"test_quick_pcb_{int(datetime.now().timestamp() * 1000)}",
                        source_device_id="pc_b",
                        destination_device_id="server",
                        destination_ip="10.0.0.10",
                        protocol=Protocol.TCP,
                        src_port=49153,
                        dst_port=80,
                        timestamp=datetime.now(),
                        config_revision=state.config_revision,
                    )
                    res = simulate_packet(state, pkt)
                    add_simulation_run(pkt, res)
                    st.toast("Uji PC B -> Server port 80 berhasil dijalankan!")
                    st.rerun()

            with qc3:
                if st.button("PC A -> PC B (ICMP Ping)", icon=":material/sync:", key="btn_quick_pca_pcb", use_container_width=True):
                    pkt = PacketTest(
                        id=f"test_quick_ping_{int(datetime.now().timestamp() * 1000)}",
                        source_device_id="pc_a",
                        destination_device_id="pc_b",
                        destination_ip="192.168.1.11",
                        protocol=Protocol.ICMP,
                        src_port=None,
                        dst_port=None,
                        timestamp=datetime.now(),
                        config_revision=state.config_revision,
                    )
                    res = simulate_packet(state, pkt)
                    add_simulation_run(pkt, res)
                    st.toast("Uji PC A -> PC B ICMP Ping berhasil dijalankan!")
                    st.rerun()

        # Form Generator Paket Kustom
        with st.container(border=True):
            st.markdown("#### :material/send: Generator Paket Kustom")
            with st.form("form_packet_test"):
                col1, col2 = st.columns(2)
                with col1:
                    src_hosts = [d for d in state.devices if d.type != DeviceType.SWITCH]
                    src_dev_id = st.selectbox(
                        "Perangkat Sumber (Source):",
                        options=[d.id for d in src_hosts],
                        format_func=lambda x: f"{state.get_device(x).name} ({x})" if state.get_device(x) else x,
                        key="sel_pkt_src",
                    )

                    dst_mode = st.radio("Metode Tujuan:", ["Pilih Perangkat", "Alamat IP Manual"], horizontal=True, key="rad_pkt_dst_mode")
                    dst_dev_id = None
                    dst_custom_ip = None

                    if dst_mode == "Pilih Perangkat":
                        other_devices = [d for d in state.devices if d.id != src_dev_id and d.type != DeviceType.SWITCH]
                        if other_devices:
                            dst_dev_id = st.selectbox(
                                "Perangkat Tujuan (Destination):",
                                options=[d.id for d in other_devices],
                                format_func=lambda x: f"{state.get_device(x).name} ({x})",
                                key="sel_pkt_dst",
                            )
                        else:
                            st.caption("Tidak ada perangkat tujuan lain.")
                    else:
                        dst_custom_ip = st.text_input("IP Tujuan Manual:", placeholder="misal: 10.0.0.10", key="input_pkt_custom_ip")

                with col2:
                    proto_choice = st.selectbox(
                        "Protokol:",
                        [Protocol.TCP, Protocol.UDP, Protocol.ICMP],
                        format_func=lambda p: p.value.upper(),
                        key="sel_pkt_proto",
                    )
                    src_port_val = st.number_input("Port Sumber (Ephemeral):", min_value=1024, max_value=65535, value=49152, key="input_pkt_sport")
                    dst_port_val = st.number_input("Port Tujuan:", min_value=1, max_value=65535, value=80, disabled=(proto_choice == Protocol.ICMP), key="input_pkt_dport")

                if st.form_submit_button("Jalankan Simulasi Paket", icon=":material/send:", type="primary", use_container_width=True):
                    pkt = PacketTest(
                        id=f"test_{int(datetime.now().timestamp() * 1000)}",
                        source_device_id=src_dev_id,
                        destination_device_id=dst_dev_id,
                        destination_ip=dst_custom_ip.strip() if dst_custom_ip else None,
                        protocol=proto_choice,
                        src_port=int(src_port_val),
                        dst_port=int(dst_port_val) if proto_choice != Protocol.ICMP else None,
                        timestamp=datetime.now(),
                        config_revision=state.config_revision,
                    )
                    res = simulate_packet(state, pkt)
                    add_simulation_run(pkt, res)
                    st.toast("Simulasi paket virtual berhasil dieksekusi!")
                    st.rerun()

        # Riwayat dan Kartu Hasil Evaluasi
        st.markdown("#### :material/history: Riwayat Hasil Evaluasi Simulasi")
        if not history:
            empty_state(
                message="Belum ada pengujian simulasi paket yang dijalankan. Klik salah satu tombol 'Uji Cepat' di atas untuk memulai.",
                action_label="Jalankan Uji Cepat Sekarang",
                target_page_or_callback=lambda: None,
                key="empty_packet_sim_btn",
                icon=":material/send:",
            )
        else:
            for idx, item in enumerate(history):
                is_latest = (idx == 0)

                # Warna border kiri sesuai keputusan
                border_color = (
                    COLOR_ALLOW if item.decision == Decision.ACCEPT
                    else COLOR_DENY if item.decision == Decision.DROP
                    else COLOR_AMBER
                )

                rule_tag = f" oleh rule #{item.matched_rule_id}" if item.matched_rule_id else " oleh default policy"
                headline = f"Hasil Uji #{item.test_id}: {item.decision.value}{rule_tag}"

                with st.container(border=True):
                    # Header Kartu Hasil Beraksen
                    st.markdown(
                        f"""
                        <div style="border-left: 5px solid {border_color}; padding-left: 12px; margin-bottom: 8px;">
                            <h4 style="margin:0 0 4px 0; color:#F8FAFC;">{headline}</h4>
                            <span style="color:#94A3B8; font-size:0.875rem;">Waktu: {item.timestamp.strftime('%H:%M:%S')} &bull; Revisi Uji: #{item.config_revision}</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    # Pelabelan jika revisi konfigurasi telah berubah
                    if item.config_revision != state.config_revision:
                        st.warning(
                            f"**Konfigurasi sudah berubah**: Pengujian ini dilakukan pada Revisi #{item.config_revision}, "
                            f"sedangkan konfigurasi aktif saat ini adalah Revisi #{state.config_revision}.",
                            icon=":material/warning:",
                        )

                    c_b1, c_b2 = st.columns([3, 1])
                    with c_b1:
                        st.markdown(f"**Alasan Engine:** {item.reason}")
                        if item.matched_rule_id:
                            st.markdown(f"**ID Aturan yang Cocok:** `{item.matched_rule_id}`")

                    with c_b2:
                        st.markdown(f"**Badge:**\n\n{get_decision_badge(item.decision)}")

                    if item.decision == Decision.ACCEPT:
                        st.info(
                            "**Catatan Kebijakan**: ACCEPT = lolos kebijakan simulasi firewall, bukan bukti service/daemon port pada tujuan aktif.",
                            icon=":material/info:",
                        )

                    # Trace Langkah Bernomor
                    with st.expander(f"Tampilkan Jejak Traversal ({len(item.trace)} langkah)", expanded=is_latest):
                        if item.trace:
                            for step in item.trace:
                                act_lbl = f" -> **[{step.action}]**" if step.action else ""
                                st.markdown(f"{step.step_number}. `{step.device_id}`: {step.description}{act_lbl}")
                        else:
                            st.caption("Tidak ada langkah traversal.")

                    # Tombol Tindak Lanjut: Lihat di 3D dan Lihat di Log
                    col_act1, col_act2, _ = st.columns([1.5, 1.5, 3])
                    with col_act1:
                        if st.button("Lihat di 3D", icon=":material/view_in_ar:", key=f"btn_3d_{item.test_id}", use_container_width=True):
                            st.session_state["nav_page"] = "viz3d"
                            st.rerun()
                    with col_act2:
                        if st.button("Lihat di Log", icon=":material/list_alt:", key=f"btn_log_{item.test_id}", use_container_width=True):
                            st.session_state["nav_page"] = "traffic_logs"
                            st.rerun()

    with col_side:
        # Panel Panduan Edukatif (Learning Mode)
        if is_learning():
            with st.container(border=True):
                st.markdown("#### :material/school: Konsep Traversal Paket")
                st.markdown(
                    "- **Same-Subnet Bypass**: Paket antar-host dalam subnet yang sama langsung diteruskan via Switch L2 tanpa menyentuh firewall.\n"
                    "- **Routing ke Gateway**: Jika subnet berbeda, host mengirim paket ke router gateway-nya.\n"
                    "- **Chain FORWARD**: Paket yang melintasi router dievaluasi terhadap aturan forward.\n"
                    "- **DROP Berhenti di Router**: Jika keputusan DROP, paket dimusnahkan di router dan tidak sampai ke subnet tujuan."
                )

        # Langkah Berikutnya
        next_steps([
            ("Putar Visualisasi 3D", "viz3d"),
            ("Tinjau Log Trafik", "traffic_logs"),
            ("Periksa Pusat Peringatan", "alerts"),
            ("Kembali ke Aturan Firewall", "firewall_rules"),
        ])

    render_flow_next("viz3d", "Visualisasi 3D", "Lihat animasi perjalanan paket dalam 3D.")

