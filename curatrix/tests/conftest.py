"""Shared pytest setup for curatrix.

Temporary files go to <workspace>/build/xdmod-dev/pytest (workspace rule: build output only
under build/<area>/), unless --basetemp is given. The workspace is the folder above xdmod/.
"""
import os
from pathlib import Path

XDMOD = Path(__file__).resolve().parents[2]
WORKSPACE = XDMOD.parent
os.environ.setdefault("XD_NEEDS_CONFIG", str(XDMOD / "needs" / "needs_config.toml"))
os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
os.environ.setdefault("XD_XDMOD", str(XDMOD))


import pytest  # noqa: E402


@pytest.fixture(autouse=True)
def _no_ci_base(monkeypatch):
    """Tests do not see the caller's base branch: a stacked PR's CI sets GITHUB_BASE_REF to the
    parent branch, which the tests' temporary repos lack (CK-H4, CK-H7, ci siblings). A test that
    wants a base sets it itself."""
    monkeypatch.delenv("GITHUB_BASE_REF", raising=False)
    monkeypatch.delenv("XD_BASE_REF", raising=False)


def pytest_configure(config):
    config.addinivalue_line("markers", "sphinx: runs sphinx-build (slow, a few seconds)")
    config.addinivalue_line("markers", "tools: needs external tools (node, firefox, java)")
    if not config.option.basetemp and (WORKSPACE / "build").is_dir():
        base = WORKSPACE / "build" / "xdmod-dev"
        base.mkdir(parents=True, exist_ok=True)       # pytest creates only the last level
        config.option.basetemp = str(base / "pytest")
