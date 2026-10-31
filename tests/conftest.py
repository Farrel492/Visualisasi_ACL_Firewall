"""Pytest fixtures for Firewall Simulator tests."""

import pytest

from firewall_sim.core.models import ProjectState
from firewall_sim.scenarios.presets import default_lab


@pytest.fixture
def sample_topology() -> ProjectState:
    """Fixture topologi standar memanggil default_lab dari presets."""
    return default_lab()


@pytest.fixture(autouse=True)
def _isolated_workspace_dir(tmp_path, monkeypatch):
    """Workspace tersimpan selama tes ditulis ke folder sementara, bukan ke data/ proyek."""
    monkeypatch.setenv("FW_DATA_DIR", str(tmp_path / "data"))
