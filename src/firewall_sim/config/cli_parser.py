"""Restricted CLI command parser (Cisco/Packet Tracer inspired subset).

ATURAN ARSITEKTUR & KEAMANAN:
- Menggunakan parser deterministik berbasis modul standar shlex.
- DILARANG menggunakan eval, exec, os.system, subprocess, atau shell execution.
- Semua mutasi state dialirkan melalui config/service.py dengan source='CLI'.
- Perintah tidak dikenal atau argumen salah mengembalikan pesan error yang jelas
  beserta saran 'help', dan state awal tetap utuh.
"""

from __future__ import annotations

from datetime import datetime
import ipaddress
import shlex
from typing import List, Optional, Tuple

from firewall_sim.config.service import (
    AddRule,
    MoveRule,
    RemoveRule,
    SetDefaultPolicy,
    SetGateway,
    SetInterfaceEnabled,
    SetInterfaceIP,
    ToggleRule,
    update_config,
)
from firewall_sim.core.models import (
    Action,
    Chain,
    FirewallRule,
    PacketTest,
    ProjectState,
    Protocol,
)
from firewall_sim.core.simulator import simulate_packet


HELP_TEXT = """=== Panduan Perintah CLI Firewall Simulator ===
Perintah yang didukung:
1. help
   Menampilkan panduan ini.

2. show <target>
   Target:
   - running-config : Menampilkan konfigurasi menyeluruh.
   - interfaces     : Menampilkan seluruh interface, IP, dan status.
   - rules [chain]  : Menampilkan tabel firewall rules (opsional filter chain).
   - policy         : Menampilkan default policy setiap chain.
   - audit          : Menampilkan riwayat log audit perubahan konfigurasi.
   - revision       : Menampilkan nomor config_revision saat ini.
   - links          : Menampilkan daftar link antar-interface.

3. interface <device> <ifname> ip address <ip> <prefix|netmask>
   Contoh: interface pc_a eth0 ip address 192.168.1.50 24
           interface router eth0 ip address 192.168.1.1 255.255.255.0

4. interface <device> <ifname> <shutdown | no shutdown>
   Mengaktifkan atau menonaktifkan interface.

5. gateway <host> <ip>
   Mengatur default gateway pada perangkat host.

6. rule add chain=<input|forward|output> [src=<cidr|any>] [dst=<cidr|any>] [proto=<tcp|udp|icmp|any>] [sport=<p|a-b>] [dport=<p|a-b>] action=<accept|drop> [comment="..."]
   Menambahkan firewall rule kanonik.

7. rule remove <id> | rule enable <id> | rule disable <id> | rule move <id> <order>
   Manajemen rule firewall.

8. policy <input|forward|output> <accept|drop>
   Mengatur default policy pada chain tertentu.

9. access-list <permit|deny> <proto> <src|any> <dst|any> [eq <port>]
   Translasi ACL Cisco-style ke FirewallRule kanonik pada chain forward.

10. test <src_device> <dst_device_or_ip> <tcp|udp|icmp> [port]
    Menjalankan simulasi paket virtual dan menampilkan trace keputusan.
"""


def _normalize_prefix(val: str) -> Optional[int]:
    """Mengonversi nilai prefix (mis. '24', '/24') atau netmask (mis. '255.255.255.0') ke integer prefix length."""
    val = val.strip().lstrip("/")
    if val.isdigit():
        p = int(val)
        if 0 <= p <= 32:
            return p
        return None
    try:
        net = ipaddress.IPv4Network(f"0.0.0.0/{val}", strict=False)
        return net.prefixlen
    except ValueError:
        return None


def _find_device_and_interface(state: ProjectState, dev_identifier: str, if_identifier: str):
    """Mencari objek Device dan Interface berdasarkan ID atau Nama."""
    dev = state.get_device(dev_identifier)
    if not dev:
        for d in state.devices:
            if d.name.lower() == dev_identifier.lower():
                dev = d
                break
    if not dev:
        return None, None

    iface = None
    for i in dev.interfaces:
        if i.id.lower() == if_identifier.lower() or i.name.lower() == if_identifier.lower():
            iface = i
            break
    return dev, iface


def parse_and_execute(
    state: ProjectState,
    line: str,
    now: Optional[datetime] = None,
) -> Tuple[ProjectState, str, List[str]]:
    """Mem-parse satu baris perintah CLI dan mengeksekusinya secara deterministik dan aman."""
    raw_line = line.strip()
    if not raw_line or raw_line.startswith("#"):
        return state, "", []

    try:
        tokens = shlex.split(raw_line)
    except ValueError as e:
        return state, "", [f"Sintaks quote error: {e}. Ketik 'help' untuk panduan."]

    if not tokens:
        return state, "", []

    cmd = tokens[0].lower()
    ts = now or datetime.now()

    # 1. HELP
    if cmd == "help":
        return state, HELP_TEXT, []

    # 2. SHOW
    if cmd == "show":
        if len(tokens) < 2:
            return state, "", ["Perintah show memerlukan target. Ketik 'help' untuk daftar target."]
        target = tokens[1].lower()

        if target == "running-config":
            lines = [
                f"! Config Revision: {state.config_revision}",
                f"! Default Policies: {', '.join(f'{c.value.upper()}={a.value.upper()}' for c, a in state.default_policies)}",
                "! Devices:",
            ]
            for d in state.devices:
                lines.append(f"device {d.id} ({d.name}, {d.type.value})")
                if d.default_gateway:
                    lines.append(f"  gateway {d.default_gateway}")
                for i in d.interfaces:
                    st_str = "up" if i.enabled else "down"
                    ip_str = i.ipv4_cidr or "unassigned"
                    lines.append(f"  interface {i.name} (id={i.id}, ip={ip_str}, {st_str})")
            lines.append("! Links:")
            for l in state.links:
                lines.append(f"link {l.id}: {l.interface_a} <-> {l.interface_b} ({'up' if l.enabled else 'down'})")
            lines.append("! Rules:")
            for r in sorted(state.rules, key=lambda x: x.order):
                lines.append(
                    f"rule {r.id} order {r.order} chain {r.chain.value.upper()} "
                    f"proto {r.protocol.value.upper()} src={r.src_cidr or 'any'} dst={r.dst_cidr or 'any'} "
                    f"dport={r.dst_port or 'any'} action {r.action.value.upper()} ({'enabled' if r.enabled else 'disabled'})"
                )
            return state, "\n".join(lines), []

        elif target == "interfaces":
            lines = ["DEVICE      INTERFACE   IP ADDRESS        STATUS"]
            lines.append("-" * 50)
            for d in state.devices:
                for i in d.interfaces:
                    ip_s = i.ipv4_cidr or "unassigned"
                    st_s = "up" if i.enabled else "down"
                    lines.append(f"{d.name:<11} {i.name:<11} {ip_s:<17} {st_s}")
            return state, "\n".join(lines), []

        elif target == "rules":
            chain_filter = tokens[2].lower() if len(tokens) > 2 else None
            rules = sorted(state.rules, key=lambda x: x.order)
            if chain_filter:
                rules = [r for r in rules if r.chain.value.lower() == chain_filter]
            lines = ["ORDER ID             CHAIN   PROTO  SRC              DST              DPORT  ACTION  STATUS"]
            lines.append("-" * 88)
            for r in rules:
                lines.append(
                    f"{r.order:<5} {r.id:<14} {r.chain.value.upper():<7} {r.protocol.value.upper():<6} "
                    f"{(r.src_cidr or 'any'):<16} {(r.dst_cidr or 'any'):<16} "
                    f"{(r.dst_port or 'any'):<6} {r.action.value.upper():<7} {'enabled' if r.enabled else 'disabled'}"
                )
            return state, "\n".join(lines), []

        elif target == "policy":
            lines = [f"{c.value.upper()}: {a.value.upper()}" for c, a in state.default_policies]
            return state, "\n".join(lines), []

        elif target == "audit":
            lines = ["TIMESTAMP            SOURCE  SUMMARY"]
            lines.append("-" * 60)
            for a in state.audit_log:
                ts_str = a.timestamp.strftime("%Y-%m-%d %H:%M:%S")
                lines.append(f"{ts_str}  {a.source:<7} {a.summary}")
            return state, "\n".join(lines), []

        elif target == "revision":
            return state, f"Current Config Revision: {state.config_revision}", []

        elif target == "links":
            lines = ["LINK ID              INTERFACE A          INTERFACE B          STATUS"]
            lines.append("-" * 68)
            for l in state.links:
                lines.append(f"{l.id:<20} {l.interface_a:<20} {l.interface_b:<20} {'up' if l.enabled else 'down'}")
            return state, "\n".join(lines), []

        else:
            return state, "", [f"Target show '{target}' tidak dikenal. Ketik 'help' untuk daftar target."]

    # 3. INTERFACE
    if cmd == "interface":
        if len(tokens) < 4:
            return state, "", ["Format perintah interface salah. Ketik 'help' untuk panduan."]
        dev_id_arg = tokens[1]
        if_name_arg = tokens[2]
        action_arg = tokens[3].lower()

        dev, iface = _find_device_and_interface(state, dev_id_arg, if_name_arg)
        if not dev:
            return state, "", [f"Perangkat '{dev_id_arg}' tidak ditemukan."]
        if not iface:
            return state, "", [f"Interface '{if_name_arg}' tidak ditemukan pada '{dev.name}'."]

        if action_arg == "ip":
            # interface <dev> <if> ip address <ip> <prefix|netmask>
            if len(tokens) < 6 or tokens[4].lower() != "address":
                return state, "", ["Format salah. Gunakan: interface <dev> <if> ip address <ip> <prefix|netmask>"]
            ip_val = tokens[5]
            if len(tokens) < 7:
                return state, "", ["Prefix atau subnet mask wajib disertakan (contoh: 24 atau 255.255.255.0)."]
            prefix_val = _normalize_prefix(tokens[6])
            if prefix_val is None:
                return state, "", [f"Subnet mask atau prefix '{tokens[6]}' tidak valid."]
            cidr = f"{ip_val}/{prefix_val}"
            new_state, errors = update_config(
                state,
                SetInterfaceIP(device_id=dev.id, interface_id=iface.id, ipv4_cidr=cidr, source="CLI", timestamp=ts),
            )
            if errors:
                return state, "", errors
            return new_state, f"IP interface '{iface.name}' pada '{dev.name}' diubah menjadi '{cidr}'.", []

        elif action_arg == "shutdown":
            new_state, errors = update_config(
                state,
                SetInterfaceEnabled(interface_id=iface.id, enabled=False, source="CLI", timestamp=ts),
            )
            if errors:
                return state, "", errors
            return new_state, f"Interface '{iface.name}' pada '{dev.name}' dinonaktifkan (shutdown).", []

        elif action_arg == "no" and len(tokens) >= 5 and tokens[4].lower() == "shutdown":
            new_state, errors = update_config(
                state,
                SetInterfaceEnabled(interface_id=iface.id, enabled=True, source="CLI", timestamp=ts),
            )
            if errors:
                return state, "", errors
            return new_state, f"Interface '{iface.name}' pada '{dev.name}' diaktifkan (no shutdown).", []

        else:
            return state, "", [f"Aksi interface '{action_arg}' tidak dikenal. Ketik 'help' untuk panduan."]

    # 4. GATEWAY
    if cmd == "gateway":
        if len(tokens) < 3:
            return state, "", ["Gunakan: gateway <host> <ip>"]
        host_arg = tokens[1]
        gw_ip = tokens[2]
        dev = state.get_device(host_arg)
        if not dev:
            for d in state.devices:
                if d.name.lower() == host_arg.lower():
                    dev = d
                    break
        if not dev:
            return state, "", [f"Perangkat '{host_arg}' tidak ditemukan."]

        new_state, errors = update_config(
            state,
            SetGateway(device_id=dev.id, default_gateway=gw_ip, source="CLI", timestamp=ts),
        )
        if errors:
            return state, "", errors
        return new_state, f"Default gateway '{dev.name}' diatur ke '{gw_ip}'.", []

    # 5. RULE
    if cmd == "rule":
        if len(tokens) < 2:
            return state, "", ["Gunakan: rule add | rule remove | rule enable | rule disable | rule move"]
        subcmd = tokens[1].lower()

        if subcmd == "add":
            kv_pairs = {}
            for token in tokens[2:]:
                if "=" in token:
                    k, v = token.split("=", 1)
                    kv_pairs[k.lower().strip()] = v.strip()

            if "chain" not in kv_pairs or "action" not in kv_pairs:
                return state, "", ["Argumen 'chain=' dan 'action=' wajib disertakan pada rule add."]

            try:
                chain = Chain(kv_pairs["chain"].lower())
            except ValueError:
                return state, "", [f"Chain '{kv_pairs['chain']}' tidak valid (pilihan: input, forward, output)."]

            try:
                action = Action(kv_pairs["action"].lower())
            except ValueError:
                return state, "", [f"Action '{kv_pairs['action']}' tidak valid (pilihan: accept, drop)."]

            proto = Protocol.ANY
            if "proto" in kv_pairs:
                try:
                    proto = Protocol(kv_pairs["proto"].lower())
                except ValueError:
                    return state, "", [f"Protocol '{kv_pairs['proto']}' tidak valid (pilihan: any, tcp, udp, icmp)."]

            src_cidr = kv_pairs.get("src")
            if src_cidr and src_cidr.lower() in ("any", "0.0.0.0/0"):
                src_cidr = None

            dst_cidr = kv_pairs.get("dst")
            if dst_cidr and dst_cidr.lower() in ("any", "0.0.0.0/0"):
                dst_cidr = None

            sport = kv_pairs.get("sport")
            dport = kv_pairs.get("dport")
            comment = kv_pairs.get("comment", "")

            # ID deterministik
            rule_id = f"rule_{len(state.rules) + 1}"
            idx = 2
            while any(r.id == rule_id for r in state.rules):
                rule_id = f"rule_{len(state.rules) + idx}"
                idx += 1

            new_order = max([r.order for r in state.rules], default=0) + 1
            rule = FirewallRule(
                id=rule_id,
                order=new_order,
                enabled=True,
                chain=chain,
                src_cidr=src_cidr,
                dst_cidr=dst_cidr,
                protocol=proto,
                src_port=sport,
                dst_port=dport,
                action=action,
                comment=comment,
            )

            new_state, errors = update_config(state, AddRule(rule=rule, source="CLI", timestamp=ts))
            if errors:
                return state, "", errors
            return new_state, f"Firewall rule '{rule_id}' berhasil ditambahkan pada order {new_order}.", []

        elif subcmd == "remove":
            if len(tokens) < 3:
                return state, "", ["Gunakan: rule remove <rule_id>"]
            rule_id = tokens[2]
            new_state, errors = update_config(state, RemoveRule(rule_id=rule_id, source="CLI", timestamp=ts))
            if errors:
                return state, "", errors
            return new_state, f"Firewall rule '{rule_id}' berhasil dihapus.", []

        elif subcmd in ("enable", "disable"):
            if len(tokens) < 3:
                return state, "", [f"Gunakan: rule {subcmd} <rule_id>"]
            rule_id = tokens[2]
            target_rule = next((r for r in state.rules if r.id == rule_id), None)
            if not target_rule:
                return state, "", [f"Rule '{rule_id}' tidak ditemukan."]

            desired = (subcmd == "enable")
            if target_rule.enabled != desired:
                new_state, errors = update_config(state, ToggleRule(rule_id=rule_id, source="CLI", timestamp=ts))
                if errors:
                    return state, "", errors
                return new_state, f"Rule '{rule_id}' berhasil di-{subcmd}.", []
            else:
                return state, f"Rule '{rule_id}' sudah dalam status {subcmd}.", []

        elif subcmd == "move":
            if len(tokens) < 4:
                return state, "", ["Gunakan: rule move <rule_id> <new_order>"]
            rule_id = tokens[2]
            try:
                new_order = int(tokens[3])
            except ValueError:
                return state, "", [f"Nilai order '{tokens[3]}' harus berupa angka integer."]
            new_state, errors = update_config(state, MoveRule(rule_id=rule_id, new_order=new_order, source="CLI", timestamp=ts))
            if errors:
                return state, "", errors
            return new_state, f"Rule '{rule_id}' dipindahkan ke urutan order {new_order}.", []

        else:
            return state, "", [f"Subperintah rule '{subcmd}' tidak dikenal. Ketik 'help' untuk panduan."]

    # 6. POLICY
    if cmd == "policy":
        if len(tokens) < 3:
            return state, "", ["Gunakan: policy <chain> <accept|drop>"]
        try:
            chain = Chain(tokens[1].lower())
        except ValueError:
            return state, "", [f"Chain '{tokens[1]}' tidak valid (pilihan: input, forward, output)."]
        try:
            action = Action(tokens[2].lower())
        except ValueError:
            return state, "", [f"Action '{tokens[2]}' tidak valid (pilihan: accept, drop)."]

        new_state, errors = update_config(state, SetDefaultPolicy(chain=chain, action=action, source="CLI", timestamp=ts))
        if errors:
            return state, "", errors
        return new_state, f"Default policy chain {chain.value.upper()} diubah menjadi {action.value.upper()}.", []

    # 7. ACCESS-LIST (Cisco-style subset translation)
    if cmd == "access-list":
        # access-list <permit|deny> <proto> <src|any> <dst|any> [eq <port>]
        if len(tokens) < 5:
            return state, "", ["Gunakan: access-list <permit|deny> <proto> <src|any> <dst|any> [eq <port>]"]
        act_token = tokens[1].lower()
        if act_token == "permit":
            action = Action.ACCEPT
        elif act_token == "deny":
            action = Action.DROP
        else:
            return state, "", [f"Action access-list '{act_token}' tidak valid (pilihan: permit, deny)."]

        try:
            proto = Protocol(tokens[2].lower())
        except ValueError:
            return state, "", [f"Protocol '{tokens[2]}' tidak valid (pilihan: tcp, udp, icmp, any)."]

        src_token = tokens[3].lower()
        src_cidr = None if src_token in ("any", "0.0.0.0/0") else tokens[3]
        if src_cidr and "/" not in src_cidr:
            src_cidr = f"{src_cidr}/32"

        dst_token = tokens[4].lower()
        dst_cidr = None if dst_token in ("any", "0.0.0.0/0") else tokens[4]
        if dst_cidr and "/" not in dst_cidr:
            dst_cidr = f"{dst_cidr}/32"

        dport = None
        if len(tokens) >= 7 and tokens[5].lower() == "eq":
            dport = tokens[6]

        rule_id = f"acl_{len(state.rules) + 1}"
        new_order = max([r.order for r in state.rules], default=0) + 1

        rule = FirewallRule(
            id=rule_id,
            order=new_order,
            enabled=True,
            chain=Chain.FORWARD,
            src_cidr=src_cidr,
            dst_cidr=dst_cidr,
            protocol=proto,
            dst_port=dport,
            action=action,
            comment=f"Translated from CLI: {raw_line}",
        )

        new_state, errors = update_config(state, AddRule(rule=rule, source="CLI", timestamp=ts))
        if errors:
            return state, "", errors

        note = (
            f"[CATATAN] access-list diterjemahkan ke aturan kanonik chain FORWARD (Rule ID: {rule_id}); "
            "implicit deny Cisco TIDAK diterapkan, gunakan 'policy forward drop'."
        )
        return new_state, note, []

    # 8. TEST (Packet simulation CLI)
    if cmd == "test":
        # test <src_device> <dst_device_or_ip> <tcp|udp|icmp> [port]
        if len(tokens) < 4:
            return state, "", ["Gunakan: test <src_device> <dst_device_or_ip> <tcp|udp|icmp> [port]"]
        src_dev_arg = tokens[1]
        dst_arg = tokens[2]
        proto_str = tokens[3].lower()

        try:
            proto = Protocol(proto_str)
        except ValueError:
            return state, "", [f"Protocol '{proto_str}' tidak valid (pilihan: tcp, udp, icmp, any)."]

        port_val = None
        if len(tokens) >= 5:
            try:
                port_val = int(tokens[4])
            except ValueError:
                return state, "", [f"Port '{tokens[4]}' harus berupa angka integer."]

        # Cek apakah dst adalah device ID atau nama atau IP
        dst_dev_id = None
        dst_ip = None
        target_dev = state.get_device(dst_arg)
        if not target_dev:
            for d in state.devices:
                if d.name.lower() == dst_arg.lower():
                    target_dev = d
                    break

        if target_dev:
            dst_dev_id = target_dev.id
        else:
            dst_ip = dst_arg

        src_dev = state.get_device(src_dev_arg)
        if not src_dev:
            for d in state.devices:
                if d.name.lower() == src_dev_arg.lower():
                    src_dev = d
                    break
        if not src_dev:
            return state, "", [f"Perangkat sumber '{src_dev_arg}' tidak ditemukan."]

        pkt = PacketTest(
            id=f"cli_test_{int(ts.timestamp() * 1000)}",
            source_device_id=src_dev.id,
            destination_device_id=dst_dev_id,
            destination_ip=dst_ip,
            protocol=proto,
            dst_port=port_val,
            timestamp=ts,
            config_revision=state.config_revision,
        )

        res = simulate_packet(state, pkt, now=ts)

        out_lines = [
            f"=== Hasil Simulasi Paket ({pkt.id}) ===",
            f"Keputusan : {res.decision.value}",
            f"Alasan    : {res.reason}",
            f"Rule ID   : {res.matched_rule_id or 'None'}",
            f"Revisi    : {res.config_revision}",
            "Trace Langkah:",
        ]
        for step in res.trace:
            act_str = f" [{step.action}]" if step.action else ""
            out_lines.append(f"  {step.step_number}. {step.device_id}: {step.description}{act_str}")

        return state, "\n".join(out_lines), []

    # Perintah tidak dikenal
    return state, "", [
        f"Perintah tidak dikenal: '{cmd}'. Ketik 'help' untuk daftar perintah yang didukung."
    ]
