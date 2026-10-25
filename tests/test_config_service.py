"""Unit tests for extended ConfigService commands (Device & Link management)."""

import pytest

from firewall_sim.config.service import (
    AddDevice,
    AddLink,
    RemoveDevice,
    RemoveLink,
    RenameDevice,
    update_config,
)
from firewall_sim.core.models import DeviceType, ProjectState


def test_add_device_deterministic_and_validation(sample_topology: ProjectState):
    """Menambah perangkat PC baru dengan ID deterministik."""
    state, err = update_config(
        sample_topology,
        AddDevice(name="PC C", type=DeviceType.PC, default_gateway="192.168.1.1"),
    )
    # Validasi topologi mewajibkan host memiliki IP pada interface
    # Karena interface default belum punya IP, validasi gagal dan state asli tetap utuh
    assert len(err) > 0
    assert state == sample_topology


def test_rename_device_success(sample_topology: ProjectState):
    """Mengganti nama perangkat berhasil dan menaikkan config_revision."""
    old_rev = sample_topology.config_revision
    state, err = update_config(
        sample_topology,
        RenameDevice(device_id="pc_a", new_name="PC Workstation 1"),
    )
    assert not err
    assert state.config_revision == old_rev + 1
    dev = state.get_device("pc_a")
    assert dev is not None
    assert dev.name == "PC Workstation 1"
    assert any("PC Workstation 1" in a.summary for a in state.audit_log)


def test_cannot_remove_sole_router(sample_topology: ProjectState):
    """Menolak penghapusan jika router adalah satu-satunya router dalam topologi."""
    state, err = update_config(
        sample_topology,
        RemoveDevice(device_id="router"),
    )
    assert len(err) > 0
    assert "satu-satunya router" in err[0].lower()
    assert state == sample_topology


def test_remove_device_cascades_links(sample_topology: ProjectState):
    """Menghapus host (mis. PC B) berhasil dan otomatis menghapus link terkait."""
    assert any(l.id == "link_pcb_sw" for l in sample_topology.links)

    state, err = update_config(
        sample_topology,
        RemoveDevice(device_id="pc_b"),
    )
    assert not err
    assert state.get_device("pc_b") is None
    # Link ke PC B harus ikut terhapus
    assert not any(l.id == "link_pcb_sw" for l in state.links)
    assert not any("pc_b" in l.id for l in state.links)


def test_add_and_remove_link(sample_topology: ProjectState):
    """Menghapus dan menambahkan link antar-interface."""
    # Hapus link PC A
    state1, err1 = update_config(sample_topology, RemoveLink(link_id="link_pca_sw"))
    assert not err1
    assert not any(l.id == "link_pca_sw" for l in state1.links)

    # Tambahkan kembali link PC A
    state2, err2 = update_config(
        state1,
        AddLink(interface_a="if_pc_a", interface_b="sw_p1", link_id="link_pca_sw"),
    )
    assert not err2
    assert any(l.id == "link_pca_sw" for l in state2.links)


def test_add_link_self_loop_rejected(sample_topology: ProjectState):
    """Menolak link yang menghubungkan interface ke dirinya sendiri."""
    state, err = update_config(
        sample_topology,
        AddLink(interface_a="if_pc_a", interface_b="if_pc_a"),
    )
    assert len(err) > 0
    assert state == sample_topology
