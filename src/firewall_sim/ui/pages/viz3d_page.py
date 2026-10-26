"""3D Topology Visualization and Packet Replay page using Plotly Scatter3d."""

from __future__ import annotations

import plotly.graph_objects as go
import streamlit as st

from firewall_sim.core.models import Decision, DeviceType
from firewall_sim.ui.components import (
    empty_state,
    next_steps,
    page_header,
    render_flow_next,
    render_simulation_banner,
    render_workflow_rail,
)
from firewall_sim.ui.state import get_simulation_history, get_state
from firewall_sim.ui.theme import COLOR_MUTED, get_decision_badge
from firewall_sim.ui.viz3d import build_replay_frames, calculate_3d_positions


def render_viz3d_page() -> None:
    """Merender panggung visualisasi 3D dengan replay paket per langkah."""
    render_simulation_banner()
    page_header(
        title="Visualisasi 3D",
        description="Amati topologi jaringan secara 3D dan putar ulang jalannya paket virtual langkah demi langkah.",
    )
    render_workflow_rail("viz3d")

    state = get_state()
    history = get_simulation_history()
    positions = calculate_3d_positions(state)

    if not positions:
        with st.container(key="viz3d_empty_dev_container"):
            empty_state(
                message="Belum ada perangkat dalam topologi. Buat perangkat di Topologi 2D terlebih dahulu.",
                action_label="Buka Topologi 2D",
                target_page_or_callback="network",
                key="empty_viz3d_dev_btn",
                icon=":material/view_in_ar:",
            )
        return

    if not history:
        with st.container(key="viz3d_empty_hist_container"):
            empty_state(
                message="Belum ada pengujian simulasi paket untuk direplay di panggung 3D. Jalankan simulasi paket virtual terlebih dahulu.",
                action_label="Buka Simulasi Paket",
                target_page_or_callback="packet_sim",
                key="empty_viz3d_hist_btn",
                icon=":material/send:",
            )
        return

    # Pemilihan Sesi Uji (Default Otomatis: Uji Terbaru / index 0)
    test_options = {
        idx: f"Test #{item.test_id} — {get_decision_badge(item.decision)} ({item.timestamp.strftime('%H:%M:%S')})"
        for idx, item in enumerate(history)
    }
    sel_idx = st.selectbox(
        "Pilih Sesi Pengujian untuk Direplay (Default Otomatis: Terbaru):",
        options=list(test_options.keys()),
        index=0,
        format_func=lambda x: test_options[x],
        key="sel_viz3d_test",
    )
    selected_res = history[sel_idx]

    # Bangun frames replay
    frames = build_replay_frames(selected_res, positions)
    total_frames = len(frames)
    step_key = f"replay_step_{selected_res.test_id}"
    if step_key not in st.session_state:
        st.session_state[step_key] = 0

    curr_step = st.session_state[step_key]
    if curr_step >= total_frames:
        curr_step = max(0, total_frames - 1)
        st.session_state[step_key] = curr_step

    col_graph, col_panel = st.columns([2.2, 1.0])

    with col_graph:
        # Legenda Chip di atas panggung 3D
        st.markdown(
            """
            <div style="display:flex;gap:10px;margin-bottom:8px;flex-wrap:wrap;">
                <span class="fw-chip" style="background:#DC262622;border:1px solid #DC2626;padding:2px 8px;border-radius:12px;font-size:0.8rem;color:#F87171;">
                    ◆ <b>Router Firewall</b> (Z=0)
                </span>
                <span class="fw-chip" style="background:#3B82F622;border:1px solid #3B82F6;padding:2px 8px;border-radius:12px;font-size:0.8rem;color:#60A5FA;">
                    ■ <b>Switch L2</b> (Z=1)
                </span>
                <span class="fw-chip" style="background:#16A34A22;border:1px solid #16A34A;padding:2px 8px;border-radius:12px;font-size:0.8rem;color:#4ADE80;">
                    ● <b>Host PC</b> (Z=2)
                </span>
                <span class="fw-chip" style="background:#8B5CF622;border:1px solid #8B5CF6;padding:2px 8px;border-radius:12px;font-size:0.8rem;color:#C084FC;">
                    ⬡ <b>Web Server</b> (Z=2)
                </span>
                <span class="fw-chip" style="background:#F59E0B22;border:1px solid #F59E0B;padding:2px 8px;border-radius:12px;font-size:0.8rem;color:#FBBF24;">
                    ● <b>Posisi Paket Aktif</b>
                </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Kontrol Replay Langkah-demi-Langkah
        if total_frames > 1:
            with st.container(border=True):
                cn1, cn2, cn3 = st.columns([1, 4, 1])
                with cn1:
                    if st.button("Mundur", icon=":material/arrow_back:", disabled=(curr_step <= 0), key=f"prev_{step_key}", use_container_width=True):
                        st.session_state[step_key] = max(0, curr_step - 1)
                        st.rerun()

                with cn3:
                    if st.button("Maju", icon=":material/arrow_forward:", disabled=(curr_step >= total_frames - 1), key=f"next_{step_key}", use_container_width=True):
                        st.session_state[step_key] = min(total_frames - 1, curr_step + 1)
                        st.rerun()

                with cn2:
                    slider_val = st.slider(
                        "Navigasi Langkah:",
                        min_value=0,
                        max_value=total_frames - 1,
                        value=curr_step,
                        format=f"Langkah %d dari {total_frames - 1}",
                        key=f"slider_{step_key}",
                    )
                    if slider_val != curr_step:
                        st.session_state[step_key] = slider_val
                        curr_step = slider_val

        active_frame = frames[curr_step] if frames else None

        # Konstruksi Scatter3d
        edge_x, edge_y, edge_z = [], [], []
        iface_to_dev = {}
        for dev in state.devices:
            for iface in dev.interfaces:
                iface_to_dev[iface.id] = dev

        for link in state.links:
            dev_a = iface_to_dev.get(link.interface_a)
            dev_b = iface_to_dev.get(link.interface_b)
            if dev_a and dev_b and dev_a.id in positions and dev_b.id in positions:
                pt_a = positions[dev_a.id]
                pt_b = positions[dev_b.id]
                edge_x.extend([pt_a.x, pt_b.x, None])
                edge_y.extend([pt_a.y, pt_b.y, None])
                edge_z.extend([pt_a.z, pt_b.z, None])

        edge_trace = go.Scatter3d(
            x=edge_x,
            y=edge_y,
            z=edge_z,
            mode="lines",
            line=dict(color="#475569", width=4),
            hoverinfo="none",
        )

        dev_x, dev_y, dev_z = [], [], []
        dev_colors, dev_symbols, dev_labels = [], [], []

        type_palette = {
            DeviceType.ROUTER: ("#DC2626", "diamond"),
            DeviceType.SWITCH: ("#3B82F6", "square"),
            DeviceType.PC: ("#16A34A", "circle"),
            DeviceType.SERVER: ("#8B5CF6", "square"),
        }

        for dev in state.devices:
            if dev.id in positions:
                pt = positions[dev.id]
                dev_x.append(pt.x)
                dev_y.append(pt.y)
                dev_z.append(pt.z)

                col, sym = type_palette.get(dev.type, (COLOR_MUTED, "circle"))
                dev_colors.append(col)
                dev_symbols.append(sym)
                dev_labels.append(f"{dev.name} ({dev.type.value.upper()})")

        node_trace = go.Scatter3d(
            x=dev_x,
            y=dev_y,
            z=dev_z,
            mode="markers+text",
            hoverinfo="text",
            text=dev_labels,
            textposition="top center",
            textfont=dict(color="#F8FAFC", size=11),
            marker=dict(
                size=14,
                color=dev_colors,
                symbol=dev_symbols,
                opacity=0.9,
                line=dict(color="#FFFFFF", width=1),
            ),
        )

        plot_data = [edge_trace, node_trace]

        # Jalur Traversal Replay (Aktif)
        if active_frame:
            # Garis jejak paket hingga langkah ini
            path_x = [pt.x for pt in active_frame.path_so_far]
            path_y = [pt.y for pt in active_frame.path_so_far]
            path_z = [pt.z for pt in active_frame.path_so_far]

            plot_data.append(
                go.Scatter3d(
                    x=path_x,
                    y=path_y,
                    z=path_z,
                    mode="lines",
                    line=dict(color="#F59E0B", width=6),
                    hoverinfo="none",
                )
            )

            # Posisi penanda paket aktif
            pkt_color = (
                "#16A34A" if selected_res.decision == Decision.ACCEPT and curr_step == total_frames - 1
                else "#DC2626" if selected_res.decision == Decision.DROP and curr_step == total_frames - 1
                else "#F59E0B"
            )
            plot_data.append(
                go.Scatter3d(
                    x=[active_frame.position.x],
                    y=[active_frame.position.y],
                    z=[active_frame.position.z],
                    mode="markers+text",
                    text=[f"Paket (#{curr_step})"],
                    textposition="bottom center",
                    textfont=dict(color="#FDE047", size=12),
                    marker=dict(size=18, color=pkt_color, symbol="circle"),
                    hoverinfo="text",
                    hovertext=[f"Langkah {curr_step}: {active_frame.description}"],
                )
            )

        fig = go.Figure(
            data=plot_data,
            layout=go.Layout(
                margin=dict(l=0, r=0, b=0, t=0),
                paper_bgcolor="rgba(0,0,0,0)",
                scene=dict(
                    xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title=""),
                    yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title=""),
                    zaxis=dict(showgrid=False, zeroline=False, showticklabels=False, title=""),
                    bgcolor="rgba(0,0,0,0)",
                ),
                height=540,
                showlegend=False,
            ),
        )

        with st.container(border=True):
            st.caption("Tahan klik kiri & geser mouse untuk rotasi/orbit kamera; scroll untuk zoom in/out.")
            st.plotly_chart(fig, use_container_width=True)

    with col_panel:
        # Panel Keputusan di Samping Grafik (2:1 Layout)
        with st.container(border=True):
            st.markdown("#### :material/info: Keputusan Simulasi")
            st.markdown(f"**Uji:** `Test #{selected_res.test_id}`")
            st.markdown(f"**Status:** {get_decision_badge(selected_res.decision)}")
            st.markdown(f"**Alasan:** {selected_res.reason}")
            if selected_res.matched_rule_id:
                st.markdown(f"**Rule Cocok:** `{selected_res.matched_rule_id}`")

            if selected_res.decision == Decision.DROP:
                st.warning(
                    "**Paket DROP**: Paket dihentikan dan dibuang di router. Replay tidak meneruskan paket ke subnet tujuan.",
                    icon=":material/cancel:",
                )

        # Penjelasan Langkah Saat Ini
        with st.container(border=True):
            st.markdown("#### :material/step: Penjelasan Langkah Aktif")
            if active_frame:
                st.markdown(f"**Langkah #{curr_step} dari {total_frames - 1}**")
                st.markdown(f"**Lokasi:** `{active_frame.device_id}`")
                st.info(active_frame.description)
            else:
                st.caption("Tidak ada frame langkah.")

        # Langkah Berikutnya
        next_steps([
            ("Buka Log Trafik Detail", "traffic_logs"),
            ("Periksa Alert Keamanan", "alerts"),
            ("Jalankan Uji Paket Lain", "packet_sim"),
        ])

    render_flow_next("traffic_logs", "Log Trafik", "Analisis riwayat dan statistik paket yang disimulasikan.")

