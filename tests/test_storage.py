"""Unit tests for JSON storage persistence (save and load)."""

from datetime import datetime
import pytest

from firewall_sim.config.service import AddRule, update_config
from firewall_sim.core.models import (
    Action,
    Chain,
    FirewallRule,
    ProjectState,
    Protocol,
)
from firewall_sim.storage.json_store import load_project, save_project


def test_round_trip_project_persistence(sample_topology: ProjectState):
    """Pengujian round-trip: save_project lalu load_project menghasilkan state yang identik."""
    # Tambah rule dan update config revision
    rule = FirewallRule(
        id="r_persist_1",
        order=1,
        enabled=True,
        chain=Chain.FORWARD,
        dst_cidr="10.0.0.10/32",
        protocol=Protocol.TCP,
        dst_port="80",
        action=Action.ACCEPT,
        comment="Roundtrip rule",
    )
    state, err = update_config(sample_topology, AddRule(rule=rule, source="TEST"))
    assert not err

    json_str = save_project(state)
    assert "schema_version" in json_str
    assert "r_persist_1" in json_str

    loaded_state, errors = load_project(json_str)
    assert not errors
    assert loaded_state is not None

    # Verifikasi integritas kesetaraan data
    assert loaded_state.config_revision == state.config_revision
    assert len(loaded_state.devices) == len(state.devices)
    assert len(loaded_state.links) == len(state.links)
    assert len(loaded_state.rules) == len(state.rules)
    assert loaded_state.default_policies == state.default_policies

    # Cek detail rule
    r_loaded = loaded_state.rules[0]
    assert r_loaded.id == rule.id
    assert r_loaded.action == rule.action
    assert r_loaded.dst_port == rule.dst_port
    assert r_loaded.comment == rule.comment


def test_load_invalid_or_corrupt_json(sample_topology: ProjectState):
    """Pengujian error handling saat memuat JSON rusak atau struktur tidak valid."""
    # JSON rusak sintaks
    s1, err1 = load_project("{invalid json: broken")
    assert s1 is None
    assert len(err1) > 0
    assert "rusak" in err1[0].lower() or "tidak valid" in err1[0].lower()

    # Berkas kosong
    s2, err2 = load_project("")
    assert s2 is None
    assert len(err2) > 0

    # JSON valid tapi tanpa schema_version
    s3, err3 = load_project('{"devices": []}')
    assert s3 is None
    assert any("schema_version" in e for e in err3)


def test_load_violates_topology_validation():
    """Pengujian penolakan muat jika data JSON melanggar aturan validasi topologi (misal tanpa router)."""
    corrupt_topology_json = """
    {
      "schema_version": "1.0",
      "config_revision": 1,
      "devices": [],
      "links": [],
      "rules": []
    }
    """
    state, errors = load_project(corrupt_topology_json)
    assert state is None
    assert len(errors) > 0
    assert any("INVALID_ROUTER_COUNT" in e for e in errors)
