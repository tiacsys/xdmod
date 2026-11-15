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


def pytest_configure(config):
    config.addinivalue_line("markers", "sphinx: runs sphinx-build (slow, a few seconds)")
    config.addinivalue_line("markers", "tools: needs external tools (node, firefox, java)")
    if not config.option.basetemp and (WORKSPACE / "build").is_dir():
        config.option.basetemp = str(WORKSPACE / "build" / "xdmod-dev" / "pytest")
