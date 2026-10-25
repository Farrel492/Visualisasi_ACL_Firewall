"""Smoke test for Firewall Simulator package and architectural boundaries."""

import ast
from pathlib import Path
import sys


def test_import_firewall_sim():
    """Memastikan seluruh modul paket firewall_sim dapat diimpor tanpa error."""
    import firewall_sim
    import firewall_sim.core
    import firewall_sim.core.models
    import firewall_sim.core.validation
    import firewall_sim.core.rules
    import firewall_sim.core.simulator
    import firewall_sim.core.alerts
    import firewall_sim.config
    import firewall_sim.config.service
    import firewall_sim.config.cli_parser
    import firewall_sim.storage
    import firewall_sim.scenarios
    import firewall_sim.ui

    assert firewall_sim.__version__ == "0.1.0"


def test_core_does_not_import_streamlit():
    """Aturan arsitektur AGENTS.md:

    Engine (src/firewall_sim/core/) murni Python: tidak boleh mengimpor
    Streamlit atau library UI apa pun.
    Memeriksa AST dari setiap file .py di src/firewall_sim/core/.
    """
    core_dir = Path(__file__).resolve().parent.parent / "src" / "firewall_sim" / "core"
    assert core_dir.exists() and core_dir.is_dir()

    prohibited_modules = {"streamlit", "st", "plotly", "matplotlib"}

    for py_file in core_dir.glob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_name = alias.name.split(".")[0]
                    assert root_name not in prohibited_modules, (
                        f"Pelanggaran arsitektur: File '{py_file.name}' mengimpor library UI '{alias.name}'"
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    root_name = node.module.split(".")[0]
                    assert root_name not in prohibited_modules, (
                        f"Pelanggaran arsitektur: File '{py_file.name}' mengimpor dari library UI '{node.module}'"
                    )
