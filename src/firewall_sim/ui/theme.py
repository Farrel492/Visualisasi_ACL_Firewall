"""UI theme tokens and badge helpers for Firewall Simulator.

Design system tokens: colors, spacing, typography.
"""

from __future__ import annotations

from firewall_sim.core.models import Decision

# Palet PRD Bagian 11 & Spesifikasi Visual
COLOR_BASE = "#E6E9EC"
COLOR_SURFACE = "#F4F5F6"
COLOR_SIDEBAR = "#1E252B"
COLOR_BORDER = "#C2C9D0"
COLOR_TEXT = "#18222B"
COLOR_PRIMARY = "#16808D"
COLOR_ALLOW = "#1F7A45"
COLOR_DENY = "#B8322A"
COLOR_WARNING = "#9A6208"
COLOR_AMBER = "#9A6208"
COLOR_MUTED = "#5E6A75"

# Radius tokens
RADIUS_BASE = "6px"
RADIUS_BUTTON = "6px"

# Spacing tokens (rem units) for consistent layout
SPACING_XS = "0.25rem"
SPACING_SM = "0.5rem"
SPACING_MD = "1rem"
SPACING_LG = "1.5rem"
SPACING_XL = "2rem"

# Typography defaults (system font stack via .streamlit/config.toml)
FONT_FAMILY = "IBM Plex Sans, sans-serif"
FONT_SIZE_BASE = "1rem"
FONT_SIZE_SM = "0.875rem"
FONT_SIZE_LG = "1.125rem"

def get_decision_badge(decision: Decision) -> str:
    """Return a textual badge for a simulation Decision without emojis.
    The badge includes text and description satisfying accessibility requirements.
    """
    if decision == Decision.ACCEPT:
        return "ACCEPT: lolos kebijakan"
    if decision == Decision.DROP:
        return "DROP: ditolak firewall"
    if decision == Decision.NO_ROUTE:
        return "NO_ROUTE: rute tidak ditemukan"
    if decision == Decision.INVALID_CONFIG:
        return "INVALID_CONFIG: konfigurasi tidak valid"
    if decision == Decision.UNSUPPORTED_CASE:
        return "UNSUPPORTED_CASE: kasus belum didukung"
    return decision.value


def inject_theme_css() -> str:
    """CSS desain "meja lab jaringan": area kerja terang + layar instrumen gelap.

    Hanya menyentuh elemen buatan sendiri (.fw-*) dan class otomatis dari key Streamlit (.st-key-*).
    Tidak menyentuh .st-emotion-cache atau data-testid.
    """
    import streamlit as st  # impor lokal agar modul tetap ringan saat diuji

    rail_open = bool(st.session_state.get("fw_sim_rail_open", True))
    rail_w = "248px" if rail_open else "64px"
    return """
<style>
:root {
  --fw-rail-w: __RAIL_W__;
  --fw-bench: #E6E9EC; --fw-panel: #F4F5F6; --fw-ink: #18222B; --fw-mute: #5E6A75; --fw-line: #C2C9D0;
  --fw-accent: #16808D; --fw-screen: #1E252B; --fw-screen-line: #33404A; --fw-screen-text: #E7ECEF;
  --fw-led-ok: #2FA35B; --fw-led-deny: #CF3B31; --fw-led-amber: #D9902A;
  --fw-ok-text: #1F7A45; --fw-deny-text: #B8322A; --fw-amber-text: #8A5A0B;
  --fw-r-data: 2px; --fw-r-control: 6px; --fw-r-screen: 10px;
  --fw-mono: "IBM Plex Mono", ui-monospace, Consolas, monospace;
}

/* ---------- rail navigasi (fixed, tetap tampil saat diciutkan) ---------- */
.st-key-fw_rail {
  position: fixed; top: 0; left: 0; bottom: 0; width: var(--fw-rail-w); z-index: 60;
  background: var(--fw-screen); border-radius: 0; padding: 18px 10px; overflow-y: auto; overflow-x: hidden;
}
.st-key-fw_rail, .st-key-fw_rail p, .st-key-fw_rail label, .st-key-fw_rail span, .st-key-fw_rail button { color: var(--fw-screen-text); }
.st-key-fw_rail button {
  justify-content: flex-start; background: transparent; border: 0; box-shadow: none;
  border-radius: var(--fw-r-control); min-height: 38px; padding: 0 10px;
}
.st-key-fw_rail button div { justify-content: flex-start; width: 100%; }
.st-key-fw_rail button p { text-align: left; width: 100%; font-weight: 500; font-size: 0.92rem; }
.st-key-fw_rail button:hover { background: #2A343C; }
[class*="st-key-navitem_"][class*="_on"] button { background: var(--fw-accent) !important; }
[class*="st-key-navitem_"][class*="_on"] button:hover { background: var(--fw-accent) !important; }
.st-key-fw_main { padding-left: calc(var(--fw-rail-w) - 52px); margin-top: -2.5rem; box-sizing: border-box; }
.fw-brand { display: flex; align-items: center; gap: 10px; padding: 2px 6px 12px; }
.fw-brand b { font: 600 17px/1.15 "IBM Plex Sans", sans-serif; color: var(--fw-screen-text); }
.fw-brand small { display: block; font: 400 11.5px "IBM Plex Sans", sans-serif; color: #93A1AC; margin-top: 2px; }
.fw-rail-cap { font: 600 11px "IBM Plex Sans", sans-serif; color: #93A1AC; margin: 14px 0 4px 10px; }
.fw-rail-status { margin: 12px 4px 4px; padding: 10px; border-top: 1px solid var(--fw-screen-line); font: 400 12.5px/1.6 "IBM Plex Sans", sans-serif; color: #B6C2CB; }
.fw-rail-status b { color: var(--fw-screen-text); font-weight: 600; }
.fw-led { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; vertical-align: middle; }
.fw-led.ok { background: var(--fw-led-ok); } .fw-led.deny { background: var(--fw-led-deny); } .fw-led.amber { background: var(--fw-led-amber); }
@media (max-width: 900px) {
  .st-key-fw_rail { position: static; width: 100%; margin-bottom: 12px; }
  .st-key-fw_main { padding-left: 0; }
}

/* ---------- jalur kerja 5 langkah: baris teks yang tenang ---------- */
.fw-workflow-rail { display: flex; flex-wrap: wrap; gap: 4px 18px; padding: 0 0 12px; margin-bottom: 14px; border-bottom: 1px solid var(--fw-line); font-size: 0.84rem; color: var(--fw-mute); }
.fw-step-item { display: flex; align-items: center; gap: 6px; padding: 2px 0; border-bottom: 2px solid transparent; }
.fw-step-item.active { color: var(--fw-ink); font-weight: 600; border-bottom-color: var(--fw-accent); }
.fw-step-num { font-family: var(--fw-mono); font-size: 0.78rem; opacity: .8; }
.fw-step-arrow { display: none; }

/* ---------- elemen buatan sendiri ---------- */
.fw-card { background: var(--fw-panel); border: 1px solid var(--fw-line); border-radius: var(--fw-r-control); padding: 1rem; margin-bottom: 0.75rem; }
.fw-badge { display: inline-flex; align-items: center; gap: 0.25rem; font-family: var(--fw-mono); font-size: 0.8rem; }
.fw-code-pill { font-family: var(--fw-mono); background: #DDE2E6; border: 1px solid var(--fw-line); padding: 0.05rem 0.4rem; border-radius: var(--fw-r-data); font-size: 0.82rem; color: var(--fw-ink); }
.fw-chip { display: inline-flex; align-items: center; gap: 6px; font-size: 0.8rem; color: var(--fw-ink); background: var(--fw-panel); border: 1px solid var(--fw-line); border-radius: var(--fw-r-control); padding: 2px 8px; }

/* ---------- konsol CLI: layar instrumen ---------- */
.fw-terminal-window { background: var(--fw-screen); border: 1px solid #141A1F; border-radius: var(--fw-r-screen); overflow: hidden; margin-bottom: 1rem; }
.fw-terminal-bar { background: #181E23; padding: 0.4rem 0.75rem; display: flex; align-items: center; justify-content: space-between; border-bottom: 1px solid var(--fw-screen-line); font-family: var(--fw-mono); font-size: 0.75rem; color: #93A1AC; }
.fw-terminal-dots { display: flex; gap: 0.35rem; }
.fw-terminal-dot { width: 0.6rem; height: 0.6rem; border-radius: 50%; display: inline-block; background: #55626D; }
.fw-terminal-body { padding: 0.85rem 1rem; font-family: var(--fw-mono); font-size: 0.85rem; line-height: 1.5; height: 400px; overflow-y: auto; display: flex; flex-direction: column-reverse; }
.fw-term-inner { width: 100%; }
.fw-cursor { display: inline-block; width: 0.55em; height: 1.05em; background: #5CCB86; vertical-align: text-bottom; animation: fw-blink 1.1s steps(1) infinite; }
@keyframes fw-blink { 50% { opacity: 0; } }
@media (prefers-reduced-motion: reduce) { .fw-cursor { animation: none; } }
.fw-term-line { margin: 0.2rem 0; white-space: pre-wrap; word-break: break-all; color: var(--fw-screen-text); }
.fw-term-prompt { color: #3FB6C4; font-weight: 500; } .fw-term-cmd { color: #F2F5F7; }
.fw-term-ok { color: #5CCB86; } .fw-term-err { color: #F2766C; } .fw-term-dim { color: #7F8E99; }

/* ---------- tabel aturan (gaya listing konfigurasi) ---------- */
.fw-rule-wrap { overflow-x: auto; margin: 4px 0 12px; border: 1px solid var(--fw-line); border-radius: var(--fw-r-data); background: var(--fw-panel); }
.fw-rule-table { width: 100%; border-collapse: collapse; font-family: var(--fw-mono); font-size: 0.82rem; color: var(--fw-ink); }
.fw-rule-table th { text-align: left; font: 600 0.74rem "IBM Plex Sans", sans-serif; color: var(--fw-mute); padding: 7px 10px; border-bottom: 1px solid var(--fw-line); background: #ECEFF1; }
.fw-rule-table td { padding: 7px 10px; border-bottom: 1px solid #DDE1E5; white-space: nowrap; }
.fw-rule-table tr:last-child td { border-bottom: 0; }
.fw-row-off td { color: var(--fw-mute); text-decoration: line-through; text-decoration-color: #9AA5AE; }
.fw-act-accept { color: var(--fw-ok-text); font-weight: 500; } .fw-act-drop { color: var(--fw-deny-text); font-weight: 500; }
.fw-led.off { background: #9AA5AE; }

/* ---------- kartu hasil uji paket ---------- */
.fw-result { background: var(--fw-panel); border: 1px solid var(--fw-line); border-left: 5px solid var(--c, var(--fw-accent)); border-radius: var(--fw-r-control); padding: 14px 18px; margin: 6px 0 10px; }
.fw-result-meta { font: 400 0.78rem var(--fw-mono); color: var(--fw-mute); }
.fw-result-title { font: 600 1.3rem/1.35 "IBM Plex Sans", sans-serif; color: var(--fw-ink); margin: 2px 0 6px; }
.fw-result-verdict { font: 400 0.95rem "IBM Plex Sans", sans-serif; color: var(--fw-ink); }
.fw-result-verdict b { font-family: var(--fw-mono); font-weight: 500; }
.fw-result-reason { margin-top: 6px; font-size: 0.88rem; color: var(--fw-mute); }

/* ---------- strip ringkasan satu baris ---------- */
.fw-strip { display: flex; flex-wrap: wrap; gap: 6px 26px; align-items: center; padding: 10px 14px; margin: 0 0 14px; background: var(--fw-panel); border: 1px solid var(--fw-line); border-radius: var(--fw-r-control); font: 400 0.9rem var(--fw-mono); color: var(--fw-ink); }
.fw-strip b { font-weight: 500; margin-right: 6px; }
.fw-strip .fw-led { display: inline-block; }

/* ---------- animasi masuk per halaman (sekali, singkat) ---------- */
@keyframes fw-rise { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: none; } }
@keyframes fw-fade { from { opacity: 0; } to { opacity: 1; } }
@keyframes fw-from-left { from { opacity: 0; transform: translateX(-16px); } to { opacity: 1; transform: none; } }
@keyframes fw-from-right { from { opacity: 0; transform: translateX(16px); } to { opacity: 1; transform: none; } }
@keyframes fw-reveal { from { clip-path: inset(0 100% 0 0); opacity: .4; } to { clip-path: inset(0 0 0 0); opacity: 1; } }
@keyframes fw-drop { from { opacity: 0; transform: translateY(-12px); } to { opacity: 1; transform: none; } }
@keyframes fw-zoom { from { opacity: 0; transform: scale(.975); } to { opacity: 1; transform: none; } }
.st-key-fw_page_start_here { animation: fw-rise .45s ease-out both; }
.st-key-fw_page_overview { animation: fw-zoom .4s ease-out both; }
.st-key-fw_page_network { animation: fw-reveal .6s ease-out both; }
.st-key-fw_page_device_config { animation: fw-from-right .4s ease-out both; }
.st-key-fw_page_firewall_rules { animation: fw-rise .5s ease-out both; }
.st-key-fw_page_packet_sim { animation: fw-from-left .4s ease-out both; }
.st-key-fw_page_viz3d { animation: fw-fade .6s ease-out both; }
.st-key-fw_page_traffic_logs { animation: fw-rise .35s ease-out both; }
.st-key-fw_page_alerts { animation: fw-drop .4s ease-out both; }
.st-key-fw_page_learning_lab { animation: fw-rise .5s ease-out both; }
.st-key-fw_page_cli_console { animation: fw-fade .5s ease-out both; }
@media (prefers-reduced-motion: reduce) {
  [class*="st-key-fw_page_"] { animation: none !important; }
}
</style>
""".replace("__RAIL_W__", rail_w)
