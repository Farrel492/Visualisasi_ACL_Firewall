"""Firewall Rules management page."""

from __future__ import annotations

import streamlit as st

from firewall_sim.config.service import (
    AddRule,
    MoveRule,
    RemoveRule,
    SetDefaultPolicy,
    ToggleRule,
)
from firewall_sim.core.models import (
    Action,
    Chain,
    FirewallRule,
    Protocol,
)
from firewall_sim.ui.components import (
    empty_state,
    next_steps,
    page_header,
    render_error_box,
    render_flow_next,
    render_simulation_banner,
    render_workflow_rail,
)
from firewall_sim.ui.state import apply_command, get_state, is_learning


def render_firewall_rules_page() -> None:
    """Merender halaman manajemen aturan firewall dan kebijakan default."""
    render_simulation_banner()
    page_header(
        title="Aturan Firewall",
        description="Definisikan kebijakan filter paket berbasis urutan (first matching terminal action wins) dan default policy per chain.",
    )
    render_workflow_rail("firewall_rules")

    state = get_state()

    col_main, col_side = st.columns([2.2, 1.0])

    with col_main:
        # 1. Banner Default Policy Per Chain
        with st.container(border=True):
            st.markdown("#### :material/policy: Kebijakan Default (Default Policy per Chain)")
            st.caption(
                "Kebijakan default menentukan tindakan yang diambil jika tidak ada satupun aturan yang cocok hingga akhir chain."
            )

            pol_cols = st.columns(3)
            for idx, chain in enumerate([Chain.FORWARD, Chain.INPUT, Chain.OUTPUT]):
                curr_act = state.get_default_policy(chain)
                with pol_cols[idx]:
                    chain_label = f"Chain `{chain.value.upper()}`"
                    with st.form(f"form_pol_{chain.value}"):
                        st.markdown(f"**{chain_label}**")
                        act_choice = st.selectbox(
                            "Aksi Bawaan:",
                            [Action.ACCEPT, Action.DROP],
                            format_func=lambda a: a.value.upper(),
                            index=0 if curr_act == Action.ACCEPT else 1,
                            key=f"sel_pol_{chain.value}",
                        )
                        if st.form_submit_button("Simpan Policy", use_container_width=True):
                            success, errors = apply_command(
                                SetDefaultPolicy(chain=chain, action=act_choice)
                            )
                            if success:
                                st.toast(f"Policy {chain.value.upper()} diubah ke {act_choice.value.upper()}!")
                                st.rerun()
                            else:
                                render_error_box(errors)

        # Penjelasan Prinsip First Match Wins
        st.info(
            "**Prinsip Evaluasi**: Dievaluasi dari atas ke bawah; rule pertama yang cocok menang (*first matching rule wins*). Aturan yang nonaktif akan dilewati.",
            icon=":material/info:",
        )

        # 2. Daftar Aturan Firewall per Chain
        with st.container(border=True):
            st.markdown("#### :material/table_rows: Daftar Aturan Firewall (Ordered Rules)")

            chains = [Chain.FORWARD, Chain.INPUT, Chain.OUTPUT]
            tabs = st.tabs([f"Chain {c.value.upper()} ({len([r for r in state.rules if r.chain == c])} Rule)" for c in chains])

            for tab_idx, chain in enumerate(chains):
                with tabs[tab_idx]:
                    chain_rules = sorted(
                        [r for r in state.rules if r.chain == chain],
                        key=lambda x: x.order,
                    )

                    if not chain_rules:
                        st.caption(
                            f"Belum ada aturan pada chain {chain.value.upper()}. Seluruh paket akan langsung dievaluasi oleh Default Policy ({state.get_default_policy(chain).value.upper()})."
                        )
                    else:
                        for r in chain_rules:
                            with st.container(border=True):
                                c_ord, c_info, c_act, c_btn = st.columns([0.8, 3.5, 1.8, 2.5])

                                with c_ord:
                                    st.markdown(f"### #{r.order}")
                                    st.caption(f"`{r.id}`")

                                with c_info:
                                    src_str = r.src_cidr or "Semua (any)"
                                    dst_str = r.dst_cidr or "Semua (any)"
                                    port_str = f"Port Tujuan: `{r.dst_port}`" if r.dst_port else "Semua Port"
                                    proto_str = f"Protokol: `{r.protocol.value.upper()}`"
                                    comment_str = f"<br><i>Catatan: {r.comment}</i>" if r.comment else ""

                                    st.markdown(
                                        f"**{src_str}** &rarr; **{dst_str}**<br>"
                                        f"<small>{proto_str} | {port_str}{comment_str}</small>",
                                        unsafe_allow_html=True,
                                    )

                                with c_act:
                                    if r.action == Action.ACCEPT:
                                        st.badge("ACCEPT", icon=":material/check_circle:", color="green")
                                    else:
                                        st.badge("DROP", icon=":material/cancel:", color="red")

                                    # Status Teks Eksplisit
                                    if r.enabled:
                                        st.caption("Status: **Aktif**")
                                    else:
                                        st.caption("Status: **Nonaktif** (dilewati)")

                                with c_btn:
                                    cb1, cb2 = st.columns(2)
                                    with cb1:
                                        toggle_label = "Matikan" if r.enabled else "Aktifkan"
                                        if st.button(toggle_label, key=f"tgl_{r.id}", use_container_width=True):
                                            apply_command(ToggleRule(rule_id=r.id))
                                            st.rerun()

                                        if st.button("Hapus", key=f"del_{r.id}", use_container_width=True):
                                            apply_command(RemoveRule(rule_id=r.id))
                                            st.rerun()

                                    with cb2:
                                        # Tombol Naik / Turun
                                        if st.button("Naik", icon=":material/arrow_upward:", key=f"up_{r.id}", disabled=(r.order <= 1), use_container_width=True):
                                            apply_command(MoveRule(rule_id=r.id, new_order=r.order - 1))
                                            st.rerun()

                                        if st.button("Turun", icon=":material/arrow_downward:", key=f"down_{r.id}", use_container_width=True):
                                            apply_command(MoveRule(rule_id=r.id, new_order=r.order + 1))
                                            st.rerun()

        # 3. Form Tambah Rule Baru
        with st.container(border=True):
            st.markdown("#### :material/add_moderator: Tambah Aturan Firewall Baru")
            with st.form("form_add_rule"):
                col_c1, col_c2, col_c3 = st.columns(3)
                with col_c1:
                    r_chain = st.selectbox(
                        "Pilih Chain",
                        [Chain.FORWARD, Chain.INPUT, Chain.OUTPUT],
                        format_func=lambda c: c.value.upper(),
                        key="sel_rule_chain",
                    )
                    r_action = st.selectbox(
                        "Aksi Firewall",
                        [Action.ACCEPT, Action.DROP],
                        format_func=lambda a: a.value.upper(),
                        key="sel_rule_action",
                    )
                    r_proto = st.selectbox(
                        "Protokol",
                        [Protocol.TCP, Protocol.UDP, Protocol.ICMP, Protocol.ANY],
                        format_func=lambda p: p.value.upper(),
                        key="sel_rule_proto",
                    )

                with col_c2:
                    r_src = st.text_input("Source IP / CIDR", placeholder="misal: 192.168.1.10/32 atau kosongkan", key="input_rule_src")
                    r_dst = st.text_input("Destination IP / CIDR", placeholder="misal: 10.0.0.10/32 atau kosongkan", key="input_rule_dst")
                    r_dport = st.text_input("Port Tujuan (TCP/UDP)", placeholder="misal: 80 atau 1000-2000", key="input_rule_dport")

                with col_c3:
                    r_sport = st.text_input("Port Sumber (opsional)", placeholder="misal: 49152 atau kosongkan", key="input_rule_sport")
                    r_comment = st.text_input("Komentar / Keterangan", placeholder="misal: Izinkan Web HTTP", key="input_rule_comment")
                    default_order = max([x.order for x in state.rules], default=0) + 1
                    r_order_val = st.number_input("Nomor Urutan (Order)", min_value=1, value=default_order, key="input_rule_order")

                if st.form_submit_button("Simpan Aturan", type="primary", use_container_width=True):
                    rule_id = f"rule_{len(state.rules) + 1}"
                    idx = 2
                    while any(x.id == rule_id for x in state.rules):
                        rule_id = f"rule_{len(state.rules) + idx}"
                        idx += 1

                    new_rule = FirewallRule(
                        id=rule_id,
                        order=int(r_order_val),
                        enabled=True,
                        chain=r_chain,
                        src_cidr=r_src.strip() or None,
                        dst_cidr=r_dst.strip() or None,
                        protocol=r_proto,
                        src_port=r_sport.strip() or None,
                        dst_port=r_dport.strip() or None,
                        action=r_action,
                        comment=r_comment.strip(),
                    )
                    success, errors = apply_command(AddRule(rule=new_rule))
                    if success:
                        st.toast(f"Aturan '{rule_id}' berhasil ditambahkan!")
                        st.rerun()
                    else:
                        render_error_box(errors)

    with col_side:
        # Panduan Edukasi (Khusus Learning Mode)
        if is_learning():
            with st.container(border=True):
                st.markdown("#### :material/school: Konsep Penting")
                st.markdown(
                    "- **Rule Ordering**: Firewall mengevaluasi nomor order terendah lebih dulu.\n"
                    "- **First Match Wins**: Begitu kriteria paket cocok, keputusan langsung diambil dan evaluasi selesai.\n"
                    "- **Chain FORWARD**: Untuk paket yang melintasi router antar subnet.\n"
                    "- **Chain INPUT**: Untuk paket menuju interface router sendiri.\n"
                    "- **Default Policy**: Berlaku jika sampai akhir chain tidak ada rule yang cocok."
                )

        # Langkah Berikutnya
        next_steps([
            ("Simulasi Pengujian Paket", "packet_sim"),
            ("Pantau Visualisasi 3D", "viz3d"),
            ("Analisis Log Trafik", "traffic_logs"),
        ])

    render_flow_next("packet_sim", "Simulasi Paket", "Uji aturan firewall ini dengan mengirimkan paket virtual.")

