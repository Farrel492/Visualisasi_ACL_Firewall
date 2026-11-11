"""Konsol CLI bergaya Cisco IOS (router/switch) dan Windows (PC/server).

Modul ini murni: tidak memakai Streamlit. Mutasi konfigurasi dan pengujian paket disuntikkan lewat
callback, sehingga seluruh perilakunya dapat diuji tanpa UI.

Mode sesi IOS:
    user        Nama>
    priv        Nama#           (setelah `enable`)
    config      Nama(config)#   (setelah `configure terminal`)
    config-if   Nama(config-if)# (setelah `interface fa0/0`)
Perangkat PC/server memakai prompt `C:\\>` dengan perintah ipconfig dan ping.
"""

from __future__ import annotations

from dataclasses import dataclass
import ipaddress
import re
from typing import Callable, List, Optional, Sequence, Tuple

from firewall_sim.config.service import (
    ConfigCommand,
    RenameDevice,
    SetGateway,
    SetInterfaceEnabled,
    SetInterfaceIP,
)
from firewall_sim.core.models import Decision, Device, DeviceType, Interface, ProjectState

Line = Tuple[str, str]  # (jenis, teks); jenis: out | ok | err | info

MODE_USER, MODE_PRIV, MODE_CONFIG, MODE_CONFIG_IF = "user", "priv", "config", "config-if"


@dataclass
class CliSession:
    device_id: str
    mode: str = MODE_USER
    iface_id: Optional[str] = None


@dataclass(frozen=True)
class PingOutcome:
    decision: Decision
    detail: str  # penjelasan singkat, mis. "aturan #2, chain FORWARD" atau "kebijakan default"


GetState = Callable[[], ProjectState]
ApplyCmd = Callable[[ConfigCommand], Tuple[bool, List[str]]]
RunPing = Callable[[str, Optional[str], Optional[str]], Optional[PingOutcome]]
Legacy = Callable[[str], Tuple[str, List[str]]]


# --------------------------------------------------------------------------- tabel perintah
# (kata-kata perintah, nama handler, bantuan, contoh penggunaan)
_Entry = Tuple[Tuple[str, ...], str, str, str]

_USER: List[_Entry] = [
    (("enable",), "enable", "Masuk mode privileged", "enable"),
    (("ping",), "ping", "Uji konektivitas (ICMP) ke perangkat atau IP", "ping 10.0.0.10"),
    (("show", "ip", "interface", "brief"), "show_ip_brief", "Ringkasan interface dan IP", "show ip interface brief"),
    (("exit",), "exit", "Keluar dari sesi", "exit"),
]
_PRIV: List[_Entry] = [
    (("configure", "terminal"), "conf_t", "Masuk mode konfigurasi", "configure terminal"),
    (("disable",), "disable", "Kembali ke mode user", "disable"),
    (("ping",), "ping", "Uji konektivitas (ICMP) ke perangkat atau IP", "ping 10.0.0.10"),
    (("show", "running-config"), "show_run", "Tampilkan konfigurasi aktif", "show running-config"),
    (("show", "ip", "interface", "brief"), "show_ip_brief", "Ringkasan interface dan IP", "show ip interface brief"),
    (("show", "interfaces"), "show_interfaces", "Detail interface perangkat", "show interfaces"),
    (("show", "rules"), "legacy", "Daftar aturan firewall", "show rules"),
    (("show", "policy"), "legacy", "Default policy tiap chain", "show policy"),
    (("show", "links"), "legacy", "Daftar link", "show links"),
    (("show", "revision"), "legacy", "Nomor revisi konfigurasi", "show revision"),
    (("show", "audit"), "legacy", "Riwayat perubahan konfigurasi", "show audit"),
    (("test",), "legacy", "Uji paket: test <asal> <tujuan> <tcp|udp|icmp> [port]", "test pc_a server tcp 80"),
    (("exit",), "exit", "Kembali ke mode user", "exit"),
]
_CONFIG: List[_Entry] = [
    (("hostname",), "hostname", "Ganti nama perangkat", "hostname R1"),
    (("interface",), "interface", "Masuk konfigurasi sebuah interface", "interface fa0/0"),
    (("rule",), "legacy", "Kelola rule: rule add chain=forward proto=tcp dport=80 action=accept", "rule add chain=forward proto=tcp dport=80 action=accept"),
    (("policy",), "legacy", "Default policy: policy forward drop", "policy forward drop"),
    (("access-list",), "legacy", "ACL gaya Cisco: access-list permit tcp any any eq 80", "access-list permit tcp any any eq 80"),
    (("ping",), "ping", "Uji konektivitas (ICMP)", "ping 10.0.0.10"),
    (("exit",), "exit", "Kembali ke mode privileged", "exit"),
    (("end",), "end", "Kembali ke mode privileged", "end"),
]
_CONFIG_IF: List[_Entry] = [
    (("ip", "address"), "ip_address", "Atur alamat IP: ip address <ip> <netmask>", "ip address 192.168.1.1 255.255.255.0"),
    (("no", "ip", "address"), "no_ip_address", "Hapus alamat IP", "no ip address"),
    (("shutdown",), "shutdown", "Nonaktifkan interface", "shutdown"),
    (("no", "shutdown"), "no_shutdown", "Aktifkan interface", "no shutdown"),
    (("interface",), "interface", "Pindah ke interface lain", "interface fa0/1"),
    (("exit",), "exit", "Kembali ke mode konfigurasi", "exit"),
    (("end",), "end", "Kembali ke mode privileged", "end"),
]
_HOST: List[_Entry] = [
    (("ipconfig", "set"), "host_set", "Atur IP: ipconfig set <ip> <netmask> <gateway>", "ipconfig set 192.168.1.10 255.255.255.0 192.168.1.1"),
    (("ipconfig",), "ipconfig", "Tampilkan konfigurasi IP", "ipconfig"),
    (("ping",), "ping", "Uji konektivitas (ICMP) ke perangkat atau IP", "ping 10.0.0.10"),
    (("exit",), "exit", "Tutup sesi", "exit"),
]
_TABLES = {MODE_USER: _USER, MODE_PRIV: _PRIV, MODE_CONFIG: _CONFIG, MODE_CONFIG_IF: _CONFIG_IF}


# --------------------------------------------------------------------------- fungsi bantu murni


def hostname_of(dev: Device) -> str:
    return re.sub(r"\s+", "-", dev.name.strip()) or dev.id


def is_host(dev: Device) -> bool:
    return dev.type in (DeviceType.PC, DeviceType.SERVER)


def prompt_for(state: ProjectState, session: CliSession) -> str:
    dev = state.get_device(session.device_id)
    if dev is None:
        return ">"
    if is_host(dev):
        return "C:\\>"
    host = hostname_of(dev)
    return {
        MODE_USER: f"{host}>",
        MODE_PRIV: f"{host}#",
        MODE_CONFIG: f"{host}(config)#",
        MODE_CONFIG_IF: f"{host}(config-if)#",
    }.get(session.mode, f"{host}>")


def _norm_iface(name: str) -> str:
    n = re.sub(r"\s+", "", name.lower())
    n = n.replace("fastethernet", "fa").replace("ethernet", "fa").replace("serial", "se")
    return n


def find_interface(dev: Device, token: str) -> Optional[Interface]:
    want = _norm_iface(token)
    for iface in dev.interfaces:
        if _norm_iface(iface.name) == want:
            return iface
    return None


def netmask_to_prefix(mask: str) -> Optional[int]:
    mask = mask.strip()
    if mask.startswith("/"):
        mask = mask[1:]
    if mask.isdigit():
        n = int(mask)
        return n if 1 <= n <= 32 else None
    try:
        return ipaddress.IPv4Network(f"0.0.0.0/{mask}").prefixlen
    except ValueError:
        return None


def prefix_to_netmask(prefix: int) -> str:
    return str(ipaddress.IPv4Network(f"0.0.0.0/{prefix}").netmask)


def _match(tokens: Sequence[str], table: List[_Entry]):
    """Cocokkan token dengan tabel; singkatan unik diperbolehkan (conf t, sh run, int fa0/0)."""
    low = [t.lower() for t in tokens]
    scored = []
    for entry in table:
        words = entry[0]
        if len(low) < len(words):
            continue
        if all(w.startswith(t) for w, t in zip(words, low)):
            exact = sum(1 for w, t in zip(words, low) if w == t)
            scored.append((len(words), exact, entry))
    if not scored:
        return None, "unknown"
    best_len = max(s[0] for s in scored)
    scored = [s for s in scored if s[0] == best_len]
    best_exact = max(s[1] for s in scored)
    scored = [s for s in scored if s[1] == best_exact]
    if len(scored) > 1:
        return None, "ambiguous"
    return scored[0][2], ""


# --------------------------------------------------------------------------- inti CLI


class IosCli:
    def __init__(self, get_state: GetState, apply_cmd: ApplyCmd, run_ping: RunPing, legacy: Legacy):
        self._state = get_state
        self._apply = apply_cmd
        self._ping = run_ping
        self._legacy = legacy

    # ------------------------------------------------------------------ publik
    def prompt(self, session: CliSession) -> str:
        return prompt_for(self._state(), session)

    def help_lines(self, session: CliSession) -> List[Line]:
        state = self._state()
        dev = state.get_device(session.device_id)
        table = _HOST if dev and is_host(dev) else _TABLES[session.mode]
        lines: List[Line] = [("info", "Perintah yang tersedia pada mode ini (singkatan unik diperbolehkan, mis. conf t, sh run):")]
        for words, _h, desc, _usage in table:
            lines.append(("out", f"  {' '.join(words):<26}{desc}"))
        lines.append(("out", "  ?                         Tampilkan bantuan ini"))
        return lines

    def quick_commands(self, session: CliSession) -> List[str]:
        """Perintah contoh yang valid pada mode sesi sekarang (untuk chip klik-jalankan)."""
        state = self._state()
        dev = state.get_device(session.device_id)
        if dev is None:
            return []
        if is_host(dev):
            other = next((d for d in state.devices if d.id != dev.id and is_host(d) and _first_ip(d)), None)
            cmds = ["ipconfig"]
            if other:
                cmds.append(f"ping {_first_ip(other)}")
            return cmds
        first_if = dev.interfaces[0].name.lower() if dev.interfaces else "fa0/0"
        if session.mode == MODE_USER:
            return ["enable", "show ip interface brief", "?"]
        if session.mode == MODE_PRIV:
            cmds = ["configure terminal", "show running-config", "show ip interface brief"]
            if dev.type == DeviceType.ROUTER:
                cmds += ["show rules", "test pc_a server tcp 80"]
            return cmds + ["?"]
        if session.mode == MODE_CONFIG:
            cmds = [f"interface {first_if}"]
            if dev.type == DeviceType.ROUTER:
                cmds += ["rule add chain=forward proto=tcp dport=443 action=accept", "policy forward drop"]
            return cmds + ["end", "?"]
        if dev.type == DeviceType.SWITCH:
            return ["no shutdown", "shutdown", "exit", "?"]
        return ["ip address 192.168.1.1 255.255.255.0", "no shutdown", "shutdown", "exit", "?"]

    def execute(self, session: CliSession, line: str) -> List[Line]:
        raw = line.strip()
        if not raw or raw.startswith("#"):
            return []
        if raw in ("?", "help"):
            return self.help_lines(session)
        state = self._state()
        dev = state.get_device(session.device_id)
        if dev is None:
            return [("err", "% Perangkat tidak ditemukan. Pilih perangkat lain.")]
        table = _HOST if is_host(dev) else _TABLES[session.mode]
        tokens = raw.split()
        entry, problem = _match(tokens, table)
        if entry is None:
            if problem == "ambiguous":
                return [("err", f"% Perintah ambigu: '{raw}'. Tulis lebih lengkap atau ketik ? untuk bantuan.")]
            return [("err", f"% Perintah tidak dikenali: '{raw}'. Ketik ? untuk daftar perintah.")]
        words, handler, _desc, usage = entry
        args = tokens[len(words):]
        fn = getattr(self, f"_h_{handler}")
        return fn(session, dev, raw, words, args, usage)

    # ------------------------------------------------------------------ handler mode
    def _h_enable(self, s, dev, raw, words, args, usage):
        s.mode = MODE_PRIV
        return []

    def _h_disable(self, s, dev, raw, words, args, usage):
        s.mode = MODE_USER
        return []

    def _h_conf_t(self, s, dev, raw, words, args, usage):
        s.mode = MODE_CONFIG
        return [("info", "Masukkan perintah konfigurasi satu per satu. Akhiri dengan 'end' atau 'exit'.")]

    def _h_exit(self, s, dev, raw, words, args, usage):
        if is_host(dev) or s.mode == MODE_USER:
            return [("info", "Sesi ditutup (simulasi). Ketik perintah lagi untuk melanjutkan.")]
        s.mode = {MODE_PRIV: MODE_USER, MODE_CONFIG: MODE_PRIV, MODE_CONFIG_IF: MODE_CONFIG}[s.mode]
        s.iface_id = None if s.mode != MODE_CONFIG_IF else s.iface_id
        return []

    def _h_end(self, s, dev, raw, words, args, usage):
        s.mode = MODE_PRIV
        s.iface_id = None
        return []

    # ------------------------------------------------------------------ konfigurasi
    def _h_hostname(self, s, dev, raw, words, args, usage):
        if not args:
            return [("err", f"% Perintah belum lengkap. Contoh: {usage}")]
        ok, errors = self._apply(RenameDevice(device_id=dev.id, new_name=" ".join(args)))
        return [("ok", f"Nama perangkat menjadi '{' '.join(args)}'.")] if ok else [("err", f"% {e}") for e in errors]

    def _h_interface(self, s, dev, raw, words, args, usage):
        if not args:
            return [("err", f"% Perintah belum lengkap. Contoh: {usage}")]
        if len(args) > 1 and s.mode == MODE_CONFIG:  # bentuk lama: interface <perangkat> <if> ip address ...
            return self._h_legacy(s, dev, raw, words, args, usage)
        iface = find_interface(dev, " ".join(args))
        if iface is None:
            names = ", ".join(i.name for i in dev.interfaces[:8]) + (" ..." if len(dev.interfaces) > 8 else "")
            return [("err", f"% Interface tidak ditemukan: {' '.join(args)}. Interface yang ada: {names}")]
        s.mode, s.iface_id = MODE_CONFIG_IF, iface.id
        return []

    def _current_iface(self, s, dev) -> Optional[Interface]:
        return next((i for i in dev.interfaces if i.id == s.iface_id), None)

    def _h_ip_address(self, s, dev, raw, words, args, usage):
        iface = self._current_iface(s, dev)
        if iface is None:
            return [("err", "% Pilih interface lebih dulu (interface fa0/0).")]
        if dev.type == DeviceType.SWITCH:
            return [("err", "% Switch Layer 2 tidak memakai alamat IP pada interface.")]
        if not args:
            return [("err", f"% Perintah belum lengkap. Contoh: {usage}")]
        if len(args) == 1 and "/" in args[0]:
            ip_txt, mask_txt = args[0].split("/", 1)
        elif len(args) >= 2:
            ip_txt, mask_txt = args[0], args[1]
        else:
            return [("err", f"% Perintah belum lengkap (butuh netmask). Contoh: {usage}")]
        try:
            ipaddress.IPv4Address(ip_txt)
        except ValueError:
            return [("err", f"% Alamat IP tidak valid: {ip_txt}")]
        prefix = netmask_to_prefix(mask_txt)
        if prefix is None:
            return [("err", f"% Netmask tidak valid: {mask_txt}. Contoh: 255.255.255.0")]
        ok, errors = self._apply(SetInterfaceIP(device_id=dev.id, interface_id=iface.id, ipv4_cidr=f"{ip_txt}/{prefix}"))
        return [("ok", f"{iface.name}: {ip_txt}/{prefix}")] if ok else [("err", f"% {e}") for e in errors]

    def _h_no_ip_address(self, s, dev, raw, words, args, usage):
        iface = self._current_iface(s, dev)
        if iface is None:
            return [("err", "% Pilih interface lebih dulu (interface fa0/0).")]
        ok, errors = self._apply(SetInterfaceIP(device_id=dev.id, interface_id=iface.id, ipv4_cidr=None))
        return [("ok", f"{iface.name}: alamat IP dihapus")] if ok else [("err", f"% {e}") for e in errors]

    def _set_enabled(self, s, dev, enabled: bool):
        iface = self._current_iface(s, dev)
        if iface is None:
            return [("err", "% Pilih interface lebih dulu (interface fa0/0).")]
        ok, errors = self._apply(SetInterfaceEnabled(interface_id=iface.id, enabled=enabled))
        if not ok:
            return [("err", f"% {e}") for e in errors]
        return [("ok", f"{iface.name}: {'aktif (no shutdown)' if enabled else 'nonaktif (shutdown)'}")]

    def _h_shutdown(self, s, dev, raw, words, args, usage):
        return self._set_enabled(s, dev, False)

    def _h_no_shutdown(self, s, dev, raw, words, args, usage):
        return self._set_enabled(s, dev, True)

    def _h_legacy(self, s, dev, raw, words, args, usage):
        """Perintah lama (rule, policy, access-list, test, show rules/...) didelegasikan ke parser yang ada."""
        out, errors = self._legacy(raw)
        lines: List[Line] = [("out", t) for t in out.splitlines()] if out else []
        lines += [("err", f"% {e}") for e in errors]
        return lines

    # ------------------------------------------------------------------ tampilan
    def _h_show_ip_brief(self, s, dev, raw, words, args, usage):
        state = self._state()
        used = {i for l in state.links for i in (l.interface_a, l.interface_b)}
        lines: List[Line] = [("info", f"{'Interface':<12}{'IP-Address':<20}{'Status':<24}Protocol")]
        for iface in dev.interfaces:
            status = "up" if iface.enabled else "administratively down"
            proto = "up" if iface.enabled and iface.id in used else "down"
            lines.append(("out", f"{iface.name:<12}{(iface.ipv4_cidr or 'unassigned'):<20}{status:<24}{proto}"))
        return lines

    def _h_show_interfaces(self, s, dev, raw, words, args, usage):
        state = self._state()
        lines: List[Line] = []
        for iface in dev.interfaces:
            peer = "tidak terhubung"
            for link in state.links:
                other = link.interface_b if link.interface_a == iface.id else link.interface_a if link.interface_b == iface.id else None
                if other:
                    od = next((d for d in state.devices for i in d.interfaces if i.id == other), None)
                    oi = state.get_interface(other)
                    if od and oi:
                        peer = f"{od.name} {oi.name}"
            lines.append(("out", f"{iface.name} is {'up' if iface.enabled else 'administratively down'}"))
            lines.append(("out", f"  Internet address is {iface.ipv4_cidr or 'belum diatur'}"))
            lines.append(("out", f"  Terhubung ke: {peer}"))
        return lines

    def _h_show_run(self, s, dev, raw, words, args, usage):
        state = self._state()
        lines: List[Line] = [("out", "Building configuration..."), ("out", ""), ("out", "!"), ("out", f"hostname {hostname_of(dev)}"), ("out", "!")]
        for iface in dev.interfaces:
            if dev.type == DeviceType.SWITCH and not iface.ipv4_cidr and iface.enabled:
                continue
            lines.append(("out", f"interface {iface.name}"))
            if iface.ipv4_cidr:
                net = ipaddress.ip_interface(iface.ipv4_cidr)
                lines.append(("out", f" ip address {net.ip} {prefix_to_netmask(net.network.prefixlen)}"))
            else:
                lines.append(("out", " no ip address"))
            lines.append(("out", " no shutdown" if iface.enabled else " shutdown"))
            lines.append(("out", "!"))
        if dev.default_gateway:
            lines.append(("out", f"ip default-gateway {dev.default_gateway}"))
            lines.append(("out", "!"))
        if dev.type == DeviceType.ROUTER:
            for chain, action in state.default_policies:
                lines.append(("out", f"policy {chain.value} {action.value}"))
            for r in sorted(state.rules, key=lambda x: x.order):
                flag = "" if r.enabled else "  ! nonaktif"
                port = f" dport {r.dst_port}" if r.dst_port else ""
                lines.append(("out", f"rule {r.order} {r.chain.value} {r.action.value} {r.protocol.value} src {r.src_cidr or 'any'} dst {r.dst_cidr or 'any'}{port}{flag}"))
            lines.append(("out", "!"))
        lines.append(("out", "end"))
        return lines

    # ------------------------------------------------------------------ host
    def _h_ipconfig(self, s, dev, raw, words, args, usage):
        lines: List[Line] = [("out", "Konfigurasi IP Windows"), ("out", "")]
        for iface in dev.interfaces:
            lines.append(("out", f"Ethernet adapter {iface.name}:"))
            if iface.ipv4_cidr:
                net = ipaddress.ip_interface(iface.ipv4_cidr)
                lines.append(("out", f"   IPv4 Address. . . . . . : {net.ip}"))
                lines.append(("out", f"   Subnet Mask . . . . . . : {prefix_to_netmask(net.network.prefixlen)}"))
            else:
                lines.append(("out", "   IPv4 Address. . . . . . : (belum diatur)"))
            lines.append(("out", f"   Default Gateway . . . . : {dev.default_gateway or '(belum diatur)'}"))
            lines.append(("out", ""))
        return lines

    def _h_host_set(self, s, dev, raw, words, args, usage):
        if len(args) < 3:
            return [("err", f"% Perintah belum lengkap. Contoh: {usage}")]
        ip_txt, mask_txt, gw = args[0], args[1], args[2]
        try:
            ipaddress.IPv4Address(ip_txt)
            ipaddress.IPv4Address(gw)
        except ValueError:
            return [("err", "% Alamat IP atau gateway tidak valid.")]
        prefix = netmask_to_prefix(mask_txt)
        if prefix is None:
            return [("err", f"% Netmask tidak valid: {mask_txt}")]
        if not dev.interfaces:
            return [("err", "% Perangkat tidak punya interface.")]
        ok1, e1 = self._apply(SetInterfaceIP(device_id=dev.id, interface_id=dev.interfaces[0].id, ipv4_cidr=f"{ip_txt}/{prefix}"))
        if not ok1:
            return [("err", f"% {e}") for e in e1]
        ok2, e2 = self._apply(SetGateway(device_id=dev.id, default_gateway=gw))
        if not ok2:
            return [("err", f"% {e}") for e in e2]
        return [("ok", f"IP {ip_txt}/{prefix}, gateway {gw} disimpan.")]

    # ------------------------------------------------------------------ ping
    def _resolve(self, token: str):
        state = self._state()
        key = token.strip().lower()
        for d in state.devices:
            if key in (d.id.lower(), d.name.lower(), hostname_of(d).lower()):
                ip = _first_ip(d)
                return d.id, ip, ip or d.name
        try:
            ipaddress.IPv4Address(token)
        except ValueError:
            return None, None, None
        for d in state.devices:
            for i in d.interfaces:
                if i.ipv4_cidr and str(ipaddress.ip_interface(i.ipv4_cidr).ip) == token:
                    return d.id, token, token
        return None, token, token

    def _h_ping(self, s, dev, raw, words, args, usage):
        if not args:
            return [("err", f"% Perintah belum lengkap. Contoh: {usage}")]
        dst_id, dst_ip, shown = self._resolve(args[0])
        if shown is None:
            return [("err", f"% Tujuan tidak dikenal: {args[0]}. Gunakan nama perangkat atau alamat IP.")]
        outcome = self._ping(dev.id, dst_id, dst_ip)
        if outcome is None:
            return [("err", "% Uji ping tidak dapat dijalankan.")]
        return self._ping_lines(dev, shown, outcome)

    def _ping_lines(self, dev: Device, shown: str, o: PingOutcome) -> List[Line]:
        ok, drop = o.decision == Decision.ACCEPT, o.decision == Decision.DROP
        if not is_host(dev):  # gaya Cisco
            marks = "!!!!!" if ok else ("....." if drop else "UUUUU")
            rate = 100 if ok else 0
            lines: List[Line] = [
                ("out", f"Sending 5, 100-byte ICMP Echos to {shown}, timeout is 2 seconds:"),
                ("ok" if ok else "err", marks),
                ("out", f"Success rate is {rate} percent ({5 if ok else 0}/5)"),
            ]
        else:  # gaya Windows
            lines = [("out", f"Pinging {shown} with 32 bytes of data:")]
            for _ in range(4):
                if ok:
                    lines.append(("out", f"Reply from {shown}: bytes=32 time<1ms TTL=127"))
                elif drop:
                    lines.append(("err", "Request timed out."))
                else:
                    lines.append(("err", "Destination host unreachable."))
            got = 4 if ok else 0
            lines += [("out", ""), ("out", f"Ping statistics for {shown}:"),
                      ("out", f"    Packets: Sent = 4, Received = {got}, Lost = {4 - got} ({0 if ok else 100}% loss)")]
        if drop:
            lines.append(("info", f"% Paket ditolak firewall (DROP): {o.detail}."))
        elif not ok:
            lines.append(("info", f"% Tidak sampai ke tujuan ({o.decision.value}): {o.detail}"))
            if not is_host(dev):
                lines.append(("info", "% Catatan: paket yang berasal dari router sendiri (chain OUTPUT) belum didukung simulator. Coba ping dari PC atau Server."))
        return lines


def _first_ip(dev: Device) -> Optional[str]:
    for i in dev.interfaces:
        if i.ipv4_cidr:
            return str(ipaddress.ip_interface(i.ipv4_cidr).ip)
    return None
