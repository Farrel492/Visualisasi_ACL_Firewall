"""Komponen SVG 2D interaktif untuk topologi jaringan.

Menghasilkan HTML+SVG standalone tanpa CDN eksternal. Semua ikon perangkat
digambar secara prosedural (polyline/rect/path SVG) — tidak ada library eksternal.

ATURAN:
- Tidak mengimpor Streamlit atau library UI.
- Murni Python + svg string generation.
- Tidak ada CDN/external asset; semua inline.
"""

from __future__ import annotations

import html as _html
from typing import Dict, List, Optional, Tuple

from firewall_sim.core.models import Device, DeviceType, Link, ProjectState


# ──────────────────────────────────────────────────────────────────────────
# Koordinat Layout
# ──────────────────────────────────────────────────────────────────────────

def _layout_positions(state: ProjectState) -> Dict[str, Tuple[float, float]]:
    """Menghitung posisi pixel untuk setiap perangkat dalam grid berlapis.

    Tata letak (x, y) dalam koordinat SVG (asal kiri-atas):
    - PC    : kolom kiri     (x≈110)
    - Switch: kolom tengah-kiri (x≈300)
    - Router: kolom tengah   (x≈500)
    - Server: kolom kanan    (x≈680)
    """
    positions: Dict[str, Tuple[float, float]] = {}

    W_COL = {"pc": 110.0, "switch": 290.0, "router": 490.0, "server": 670.0}
    CENTER_Y = 250.0
    SPACING_Y = 130.0

    groups: Dict[str, List[Device]] = {"pc": [], "switch": [], "router": [], "server": []}
    for dev in state.devices:
        key = dev.type.value
        if key in groups:
            groups[key].append(dev)

    for group_key, devs in groups.items():
        x = W_COL[group_key]
        n = len(devs)
        for idx, dev in enumerate(devs):
            y = CENTER_Y + (idx - (n - 1) / 2.0) * SPACING_Y
            positions[dev.id] = (x, y)

    return positions


# ──────────────────────────────────────────────────────────────────────────
# Gambar Ikon SVG Perangkat
# ──────────────────────────────────────────────────────────────────────────

def _icon_pc(cx: float, cy: float, color: str = "#22C55E") -> str:
    """Monitor PC + base stand — gambar prosedural SVG."""
    x, y = cx - 22, cy - 22
    return (
        # Monitor body
        f'<rect x="{x}" y="{y}" width="44" height="30" rx="3" ry="3" '
        f'fill="{color}" fill-opacity="0.18" stroke="{color}" stroke-width="1.8"/>'
        # Layar monitor
        f'<rect x="{x+3}" y="{y+3}" width="38" height="21" rx="2" ry="2" '
        f'fill="#0F172A" stroke="none"/>'
        # Stand neck
        f'<rect x="{cx-3}" y="{y+30}" width="6" height="7" rx="1" fill="{color}" fill-opacity="0.5"/>'
        # Stand base
        f'<rect x="{cx-12}" y="{y+36}" width="24" height="5" rx="2" fill="{color}" fill-opacity="0.5"/>'
        # Power LED
        f'<circle cx="{cx}" cy="{y+27}" r="2" fill="{color}"/>'
    )


def _icon_switch(cx: float, cy: float, color: str = "#3B82F6") -> str:
    """Rack switch dengan port row — gambar prosedural SVG."""
    x, y = cx - 28, cy - 14
    ports_html = ""
    for i in range(6):
        px = x + 6 + i * 8
        py = y + 7
        ports_html += (
            f'<rect x="{px}" y="{py}" width="5" height="5" rx="1" '
            f'fill="{color}" fill-opacity="{0.9 if i < 4 else 0.3}"/>'
        )
    return (
        f'<rect x="{x}" y="{y}" width="56" height="20" rx="3" ry="3" fill="{color}" fill-opacity="0.18" stroke="{color}" stroke-width="1.8"/>'
        f'<circle cx="{x+4}" cy="{y+10}" r="3" fill="{color}"/>'
        + ports_html
        + f'<text x="{cx}" y="{y+34}" text-anchor="middle" font-size="9" fill="{color}" font-family="monospace">SW</text>'
    )












def _icon_router_firewall(cx: float, cy: float, color: str = "#EF4444") -> str:
    """Router/Firewall dengan ikon shield prosedural."""
    # Shield outline
    shield_path = (
        f"M{cx},{cy-24} "
        f"L{cx-18},{cy-14} "
        f"L{cx-18},{cy+2} "
        f"Q{cx-18},{cy+18} {cx},{cy+24} "
        f"Q{cx+18},{cy+18} {cx+18},{cy+2} "
        f"L{cx+18},{cy-14} Z"
    )
    # Kunci/check di tengah shield
    check_path = (
        f"M{cx-7},{cy+2} L{cx-2},{cy+8} L{cx+9},{cy-6}"
    )
    return (
        f'<path d="{shield_path}" fill="{color}" fill-opacity="0.2" stroke="{color}" stroke-width="2.2"/>'
        f'<path d="{check_path}" fill="none" stroke="{color}" stroke-width="2.5" '
        f'stroke-linecap="round" stroke-linejoin="round"/>'
    )


def _icon_server(cx: float, cy: float, color: str = "#A855F7") -> str:
    """Server rack unit dengan drive bay baris."""
    x, y = cx - 20, cy - 28
    drive_bays = ""
    for row in range(3):
        by = y + 3 + row * 13
        for col in range(3):
            bx = x + 5 + col * 12
            drive_bays += (
                f'<rect x="{bx}" y="{by}" width="9" height="8" rx="1" '
                f'fill="{color}" fill-opacity="{0.7 if row < 2 else 0.3}"/>'
            )
    return (
        # Chassis badan
        f'<rect x="{x}" y="{y}" width="40" height="48" rx="3" ry="3" '
        f'fill="{color}" fill-opacity="0.15" stroke="{color}" stroke-width="1.8"/>'
        # Power button
        f'<circle cx="{x+35}" cy="{y+6}" r="3.5" fill="{color}"/>'
        # LED status
        f'<circle cx="{x+35}" cy="{y+14}" r="2.5" fill="#10B981" fill-opacity="0.9"/>'
        + drive_bays
    )


_ICON_FN = {
    DeviceType.PC: _icon_pc,
    DeviceType.SWITCH: _icon_switch,
    DeviceType.ROUTER: _icon_router_firewall,
    DeviceType.SERVER: _icon_server,
}
_ICON_COLORS = {
    DeviceType.PC: "#22C55E",
    DeviceType.SWITCH: "#3B82F6",
    DeviceType.ROUTER: "#EF4444",
    DeviceType.SERVER: "#A855F7",
}


# ──────────────────────────────────────────────────────────────────────────
# Membangun HTML SVG Komponen
# ──────────────────────────────────────────────────────────────────────────

def _e(text: str) -> str:
    return _html.escape(str(text))


def build_svg_topology(
    state: ProjectState,
    highlight_path: Optional[List[str]] = None,
    highlight_color: str = "#22C55E",
    width: int = 800,
    height: int = 480,
) -> str:
    """Menghasilkan HTML/SVG topologi interaktif lengkap sebagai string.

    Args:
        state: ProjectState saat ini.
        highlight_path: Daftar device_id yang termasuk dalam jalur simulasi terakhir.
        highlight_color: Warna highlight jalur (hijau = ACCEPT, merah = DROP).
        width, height: Dimensi SVG.

    Returns:
        String HTML siap dimasukkan ke st.components.v1.html.
    """
    positions = _layout_positions(state)

    iface_to_dev: Dict[str, Device] = {}
    for dev in state.devices:
        for iface in dev.interfaces:
            iface_to_dev[iface.id] = dev

    # ── Edge Lines ─────────────────────────────────────────────────────────
    edge_svgs: list[str] = []
    for link in state.links:
        dev_a = iface_to_dev.get(link.interface_a)
        dev_b = iface_to_dev.get(link.interface_b)
        if not (dev_a and dev_b and dev_a.id in positions and dev_b.id in positions):
            continue
        x1, y1 = positions[dev_a.id]
        x2, y2 = positions[dev_b.id]

        # Tentukan warna edge berdasarkan highlight
        on_path = (
            highlight_path
            and dev_a.id in highlight_path
            and dev_b.id in highlight_path
        )
        line_color = highlight_color if on_path else "#334155"
        line_width = 3 if on_path else 2
        line_dash = "" if on_path else 'stroke-dasharray="6,3"'

        edge_svgs.append(
            f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" '
            f'stroke="{line_color}" stroke-width="{line_width}" '
            f'stroke-opacity="0.7" {line_dash}/>'
        )

    # ── Node Icons + Labels ────────────────────────────────────────────────
    node_svgs: list[str] = []
    for dev in state.devices:
        if dev.id not in positions:
            continue
        cx, cy = positions[dev.id]
        color = _ICON_COLORS.get(dev.type, "#94A3B8")

        # Highlight ring jika berada di jalur simulasi
        is_on_path = highlight_path and dev.id in highlight_path
        if is_on_path:
            node_svgs.append(
                f'<circle cx="{cx}" cy="{cy}" r="36" '
                f'fill="{highlight_color}" fill-opacity="0.12" '
                f'stroke="{highlight_color}" stroke-width="2" stroke-opacity="0.6"/>'
            )

        # Gambar ikon perangkat
        icon_fn = _ICON_FN.get(dev.type)
        if icon_fn:
            node_svgs.append(icon_fn(cx, cy, color))

        # Nama Perangkat
        node_svgs.append(
            f'<text x="{cx}" y="{cy + 46}" text-anchor="middle" '
            f'font-size="11" font-weight="600" fill="#E2E8F0" '
            f'font-family="ui-sans-serif,system-ui,sans-serif">{_e(dev.name)}</text>'
        )
        # IP primer (jika ada)
        ip_list = [i.ipv4_cidr for i in dev.interfaces if i.ipv4_cidr]
        if ip_list:
            node_svgs.append(
                f'<text x="{cx}" y="{cy + 58}" text-anchor="middle" '
                f'font-size="9.5" fill="#64748B" '
                f'font-family="ui-monospace,Menlo,Consolas,monospace">{_e(ip_list[0])}</text>'
            )

        # Tooltip area transparan (untuk hover native SVG title)
        ifaces_detail = "; ".join([
            f"{i.name}: {i.ipv4_cidr or 'L2'}" for i in dev.interfaces
        ])
        tooltip_text = _e(f"{dev.name} ({dev.type.value.upper()}) | GW: {dev.default_gateway or '-'} | {ifaces_detail}")
        node_svgs.append(
            f'<circle cx="{cx}" cy="{cy}" r="34" fill="transparent" stroke="none">'
            f'<title>{tooltip_text}</title>'
            f'</circle>'
        )

    # ── Legenda ─────────────────────────────────────────────────────────────
    legend_items = [
        ("#EF4444", "Router Firewall"),
        ("#3B82F6", "L2 Switch"),
        ("#22C55E", "Host PC"),
        ("#A855F7", "Server"),
    ]
    legend_x, legend_y = 12, height - 36
    legend_svgs: list[str] = []
    lx = legend_x
    for lcolor, llabel in legend_items:
        legend_svgs.append(
            f'<circle cx="{lx + 6}" cy="{legend_y + 6}" r="5" fill="{lcolor}" fill-opacity="0.8"/>'
            f'<text x="{lx + 15}" y="{legend_y + 10}" font-size="10" fill="#94A3B8">{llabel}</text>'
        )
        lx += 110

    # ── Himpunan SVG lengkap ─────────────────────────────────────────────────
    all_edges = "\n".join(edge_svgs)
    all_nodes = "\n".join(node_svgs)
    all_legend = "\n".join(legend_svgs)

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg"
         width="{width}" height="{height}"
         viewBox="0 0 {width} {height}"
         style="background:#0F172A;border-radius:0.75rem;border:1px solid #334155;display:block;max-width:100%;">

    <!-- Grid background subtle -->
    <defs>
        <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#1E293B" stroke-width="0.5"/>
        </pattern>
    </defs>
    <rect width="{width}" height="{height}" fill="url(#grid)" rx="0.75rem"/>

    <!-- Edges / Links -->
    {all_edges}

    <!-- Device nodes -->
    {all_nodes}

    <!-- Legenda -->
    {all_legend}
</svg>"""
    return svg


def build_svg_html_component(
    state: ProjectState,
    highlight_path: Optional[List[str]] = None,
    highlight_color: str = "#22C55E",
    width: int = 800,
    height: int = 480,
) -> str:
    """Menghasilkan halaman HTML lengkap untuk st.components.v1.html."""
    svg_content = build_svg_topology(
        state,
        highlight_path=highlight_path,
        highlight_color=highlight_color,
        width=width,
        height=height,
    )
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ background: transparent; }}
.fw-svg-wrap {{ width:100%; overflow-x:auto; }}
</style>
</head>
<body>
<div class="fw-svg-wrap">
{svg_content}
</div>
</body>
</html>"""
