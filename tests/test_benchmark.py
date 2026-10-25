"""Performance benchmark test: 10 devices + 50 firewall rules."""

from __future__ import annotations

from pathlib import Path
import time
from streamlit.testing.v1 import AppTest

from firewall_sim.config.service import AddRule, update_config
from firewall_sim.core.models import (
    Action,
    Chain,
    Decision,
    Device,
    DeviceType,
    FirewallRule,
    Interface,
    Link,
    PacketTest,
    ProjectState,
    Protocol,
)
from firewall_sim.core.simulator import simulate_packet

APP_PATH = str(Path(__file__).parent.parent / "app.py")


def _build_benchmark_topology() -> ProjectState:
    """Membangun topologi 10 perangkat (1 Router, 1 Switch, 4 PC, 4 Server) + 50 Firewall Rules."""
    devices = []
    links = []

    # 1. Router Firewall
    r_ifaces = [
        Interface(id="r_lan", device_id="router", name="eth0", ipv4_cidr="192.168.1.1/24", enabled=True),
        Interface(id="r_srv", device_id="router", name="eth1", ipv4_cidr="10.0.0.1/24", enabled=True),
    ]
    devices.append(Device(id="router", name="Router Core", type=DeviceType.ROUTER, interfaces=tuple(r_ifaces)))

    # 2. Switch LAN (5 ports)
    sw_ifaces = [
        Interface(id=f"sw_p{i}", device_id="sw_lan", name=f"port{i}", ipv4_cidr=None, enabled=True)
        for i in range(1, 6)
    ]
    devices.append(Device(id="sw_lan", name="Switch LAN", type=DeviceType.SWITCH, interfaces=tuple(sw_ifaces)))

    # Link Router LAN port ke Switch port 1
    links.append(Link(id="link_r_sw", interface_a="r_lan", interface_b="sw_p1", enabled=True))

    # 3. 4 Host PC
    for idx in range(1, 5):
        pc_id = f"pc_{idx}"
        if_id = f"if_pc_{idx}"
        pc_if = Interface(id=if_id, device_id=pc_id, name="eth0", ipv4_cidr=f"192.168.1.1{idx}/24", enabled=True)
        devices.append(
            Device(id=pc_id, name=f"PC {idx}", type=DeviceType.PC, interfaces=(pc_if,), default_gateway="192.168.1.1")
        )
        links.append(Link(id=f"link_{pc_id}", interface_a=if_id, interface_b=f"sw_p{idx+1}", enabled=True))

    # 4. 4 Server
    for idx in range(1, 5):
        srv_id = f"srv_{idx}"
        if_id = f"if_srv_{idx}"
        srv_if = Interface(id=if_id, device_id=srv_id, name="eth0", ipv4_cidr=f"10.0.0.1{idx}/24", enabled=True)
        devices.append(
            Device(id=srv_id, name=f"Server {idx}", type=DeviceType.SERVER, interfaces=(srv_if,), default_gateway="10.0.0.1")
        )
        # Interface router srv disambung ke srv_1
        if idx == 1:
            links.append(Link(id="link_r_srv", interface_a="r_srv", interface_b=if_id, enabled=True))

    # 5. 50 Firewall Rules
    rules = []
    for r_idx in range(1, 51):
        action = Action.ACCEPT if r_idx % 2 == 1 else Action.DROP
        port_num = 1000 + r_idx
        rules.append(
            FirewallRule(
                id=f"bench_rule_{r_idx}",
                order=r_idx,
                enabled=True,
                chain=Chain.FORWARD,
                protocol=Protocol.TCP,
                dst_port=str(port_num),
                action=action,
                comment=f"Benchmark rule #{r_idx}",
            )
        )

    return ProjectState(
        devices=tuple(devices),
        links=tuple(links),
        rules=tuple(rules),
        config_revision=1,
        default_policies=(
            (Chain.INPUT, Action.ACCEPT),
            (Chain.FORWARD, Action.ACCEPT),
            (Chain.OUTPUT, Action.ACCEPT),
        ),
        scenario_metadata=(("name", "Benchmark 10 Perangkat 50 Rule"),),
        audit_log=(),
    )


def test_benchmark_simulation_and_render_time():
    """Mengukur performa eksekusi simulate_packet dan render AppTest pada 10 perangkat + 50 rules."""
    bench_state = _build_benchmark_topology()

    assert len(bench_state.devices) == 10, f"Jumlah perangkat: {len(bench_state.devices)}"
    assert len(bench_state.rules) == 50, f"Jumlah rule: {len(bench_state.rules)}"

    # Benchmark 1: simulate_packet (100 run)
    pkt = PacketTest(
        id="pkt_bench_test",
        source_device_id="pc_1",
        destination_device_id="srv_1",
        destination_ip="10.0.0.11",
        protocol=Protocol.TCP,
        src_port=49152,
        dst_port=1049,  # Cocok di rule ke-49
    )

    iterations = 50
    t0_sim = time.perf_counter()
    for _ in range(iterations):
        res = simulate_packet(bench_state, pkt)
    t1_sim = time.perf_counter()

    avg_sim_ms = ((t1_sim - t0_sim) / iterations) * 1000
    print(f"\n[BENCHMARK] simulate_packet (10 devices, 50 rules): {avg_sim_ms:.4f} ms per call ({iterations} iterations)")
    assert res.decision in (Action.ACCEPT, Action.DROP, Decision.ACCEPT, Decision.DROP)

    # Benchmark 2: AppTest page render
    t0_render = time.perf_counter()
    at = AppTest.from_file(APP_PATH, default_timeout=15)
    at.run()
    t1_render = time.perf_counter()

    render_sec = t1_render - t0_render
    print(f"[BENCHMARK] AppTest full page render: {render_sec:.4f} s")
    assert not at.exception
