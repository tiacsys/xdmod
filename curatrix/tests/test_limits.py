import subprocess
import sys

import pytest

from curatrix import limits
from curatrix.ws import Workspace


def test_size_kib():
    assert limits.size_kib("1G") == 1024 * 1024
    assert limits.size_kib("512M") == 512 * 1024
    assert limits.size_kib("2GiB") == 2 * 1024 * 1024
    with pytest.raises(ValueError):
        limits.size_kib("lots")


def test_default_table_has_the_agreed_values():
    t = limits.load_table()
    for use, mem, to in [("docs", "4G", "15m"), ("pilot", "4G", "10m"), ("kicad-cli", "2G", "5m"),
                         ("freecad", "4G", "10m"), ("firefox", "2G", "5m"), ("west-build", "4G", "20m"),
                         ("tests", "4G", "30m"), ("script", "1G", "5m")]:
        lim = limits.resolve(use, table=t)
        assert (lim.memory, lim.timeout) == (mem, to), use
    gui = limits.resolve("gui", table=t)
    assert gui.memory == "8G" and gui.timeout is None          # D117: memory only
    assert limits.resolve("pilot", table=t).java_heap == "3g"
    with pytest.raises(KeyError):
        limits.resolve("nope", table=t)


def test_workspace_override(tmp_path):
    (tmp_path / ".xdmod").mkdir()
    (tmp_path / ".xdmod" / "limits.yaml").write_text("uses:\n  docs: {memory: 6G}\n  extra: {memory: 3G, timeout: 1h}\n")
    ws = Workspace(tmp_path)
    assert limits.resolve("docs", ws).memory == "6G"
    assert limits.resolve("docs", ws).timeout == "15m"          # merged per key
    assert limits.resolve("extra", ws).timeout == "1h"


def test_wrap_backends():
    lim = limits.Limit("x", "2G", "5m", "2G")
    s = limits.wrap(["echo", "hi"], lim, "systemd")
    assert s[:2] == ["systemd-run", "--user"] and "MemoryMax=2G" in s and "MemorySwapMax=0" in s
    assert s[-5:] == ["timeout", "--kill-after=10s", "5m", "echo", "hi"]
    u = limits.wrap(["echo", "hi"], lim, "ulimit")
    assert u[0:2] == ["sh", "-c"] and f"ulimit -v {2 * 1024 * 1024}" in u[2]
    gui = limits.wrap(["kicad"], limits.Limit("gui", "8G", None, None), "systemd")
    assert "timeout" not in gui
    assert limits.wrap(["a"], limits.Limit("x", "1G", None, None), "ulimit")[2] == 'exec "$@"'


def test_ulimit_fallback_runs(monkeypatch):
    """The GitHub-runner fallback: timeout and address-space limit without systemd."""
    monkeypatch.setenv("XD_LIMIT_BACKEND", "ulimit")
    r = limits.run([sys.executable, "-c", "print('ok')"], "script", memory="1G", capture_output=True, text=True)
    assert r.returncode == 0 and r.stdout.strip() == "ok"
    r = limits.run(["sleep", "5"], "script", timeout="1s")
    assert r.returncode == 124
    r = limits.run([sys.executable, "-c", "x = b'x' * 600_000_000"], "script", memory="300M", capture_output=True)
    assert r.returncode != 0


def test_norm_rc():
    assert limits.norm_rc(-9) == 137 and limits.norm_rc(3) == 3
