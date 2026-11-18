"""The KiCad MCP server as a curated tool (xdmod#69 finding 19, owner decisions Q1, Q3)."""
import json
import os
from pathlib import Path

import pytest

from curatrix import cli, kicadmcp, tools
from curatrix.ws import Workspace
from helpers import make_ws

XDMOD = Path(__file__).resolve().parents[2]


def _tool(**kw):
    base = dict(name="x", version="1", kind="tarball", url="https://e/x.tar.gz", sha256="0" * 64,
                location="opt/x", source="t")
    base.update(kw)
    return tools.Tool(**base)


def test_pin():
    t = tools.parse(XDMOD / "tools.yaml").tools[kicadmcp.TOOL]
    assert t.kind == "tarball" and t.location == "opt/kicad-mcp" and t.licence == "MIT"
    assert t.url.startswith("https://github.com/tiacsys/KiCAD-MCP-Server/releases/download/v2.9.0-xd.")
    assert t.python_venv == {"requirements": "requirements.lock.txt", "system_modules": ["pcbnew", "_pcbnew"]}


@pytest.mark.parametrize("pv, kind", [
    ({"requirements": "r.txt"}, "zip"),                          # only for tarballs
    ({"requirements": "../r.txt"}, "tarball"),                   # outside the tool
    ({"requirements": "r.txt", "extra": 1}, "tarball"),          # unknown key
    ({"system_modules": ["pcbnew"]}, "tarball"),                 # requirements missing
])
def test_python_venv_validation(pv, kind):
    with pytest.raises(tools.ToolsError, match="python_venv"):
        _tool(kind=kind, python_venv=pv)


def test_install_python_venv(tmp_path, monkeypatch):
    """A separate venv, pip --require-hashes with the pip cache under .xdmod, the system modules
    linked in through a .pth file; nothing below HOME."""
    ws = Workspace(make_ws(tmp_path, monkeypatch))
    monkeypatch.setenv("HOME", str(tmp_path / "home"))
    site = tmp_path / "usr-site"
    site.mkdir()
    (site / "pcbnew.py").write_text("")
    (site / "_pcbnew.so").write_text("")
    monkeypatch.setattr(tools, "base_python", lambda: (Path("/usr/bin/python3.14"), site))
    calls = []

    def run(cmd, use="script", ws=None, env=None, **kw):
        calls.append((cmd, env))
        if cmd[1:3] == ["-m", "venv"]:
            (Path(cmd[-1]) / "bin").mkdir(parents=True, exist_ok=True)
            (Path(cmd[-1]) / "bin" / "python").write_text("")
            (Path(cmd[-1]) / "lib" / "python3.14" / "site-packages").mkdir(parents=True, exist_ok=True)
        return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()
    monkeypatch.setattr(tools.limits, "run", run)
    t = _tool(name="kicad-mcp", python_venv={"requirements": "requirements.lock.txt",
                                             "system_modules": ["pcbnew", "_pcbnew"]})
    loc = t.path(ws)
    loc.mkdir(parents=True)
    with pytest.raises(tools.ToolsError, match="not in the tool"):
        tools.install_python_venv(ws, t, loc, log=lambda *_: None)
    (loc / "requirements.lock.txt").write_text("x==1 \\\n    --hash=sha256:00\n")
    tools.install_python_venv(ws, t, loc, log=lambda *_: None)
    venv_cmd, pip = calls[0][0], calls[1]
    assert venv_cmd[0] == "/usr/bin/python3.14" and venv_cmd[-1] == str(loc / "venv")
    assert "--require-hashes" in pip[0] and "--no-deps" in pip[0]
    assert pip[1]["PIP_CACHE_DIR"] == str(ws.state / "cache" / "pip")
    assert (loc / "sysmods" / "pcbnew.py").resolve() == site / "pcbnew.py"
    assert (loc / "sysmods" / "_pcbnew.so").is_symlink()
    pth = loc / "venv" / "lib" / "python3.14" / "site-packages" / "xd-system-modules.pth"
    assert pth.read_text().strip() == str(loc / "sysmods")
    (site / "pcbnew.py").unlink()
    (site / "_pcbnew.so").unlink()
    with pytest.raises(tools.ToolsError, match="system module pcbnew not found"):
        tools.install_python_venv(ws, t, loc, log=lambda *_: None)
    assert not (tmp_path / "home").exists()


def test_installed_ok_needs_the_venv(tmp_path, monkeypatch):
    ws = Workspace(make_ws(tmp_path, monkeypatch))
    t = _tool(name="kicad-mcp", python_venv={"requirements": "r.txt"})
    t.path(ws).mkdir(parents=True)
    tools.write_stamp(ws, t)
    assert not tools.installed_ok(ws, t)
    tools.venv_python(ws, t).parent.mkdir(parents=True)
    tools.venv_python(ws, t).write_text("")
    assert tools.installed_ok(ws, t)


def test_server_env(tmp_path, monkeypatch):
    ws = Workspace(make_ws(tmp_path, monkeypatch))
    monkeypatch.setenv("PYTHONPATH", "/somewhere")
    t = tools.parse(XDMOD / "tools.yaml").tools[kicadmcp.TOOL]
    env = kicadmcp.server_env(ws, t)
    assert env["KICAD_MCP_STRICT_PATHS"] == "1" and env["KICAD_MCP_OPERATING_MODE"] == "readonly"
    assert env["KICAD_MCP_TOOLBOXES"] == "core,schematic,board,drc"
    assert "PYTHONPATH" not in env and "KICAD_GUI_DRIVER_AUTOINSTALL" not in env
    assert env["KICAD_PYTHON"] == str(ws.venv / "opt/kicad-mcp/venv/bin/python")
    assert env["KICAD_CLI"] == str(ws.venv / "bin/kicad-cli")
    for k in ("HOME", "KICAD_CONFIG_HOME", "KICAD_DOCUMENTS_HOME", "KICAD_CACHE_HOME", "KICAD_MCP_HOME",
              "KICAD_MCP_LOG_DIR", "XDG_CONFIG_HOME", "XDG_CACHE_HOME", "XDG_DATA_HOME", "TMPDIR",
              "KICAD10_3RD_PARTY"):
        p = Path(env[k])
        assert p.is_absolute() and ws.root in p.parents, k        # everything inside the workspace
    assert env["KICAD10_3RD_PARTY"].endswith("kicad-documents/kicad/10.0/3rdparty")
    assert kicadmcp.server_env(ws, t, "write")["KICAD_MCP_OPERATING_MODE"] == "write"
    with pytest.raises(ValueError):
        kicadmcp.server_env(ws, t, "anything")


def test_ensure_writes_only_the_mcp_entry(tmp_path, monkeypatch):
    ws = Workspace(make_ws(tmp_path, monkeypatch))
    (ws.root / ".mcp.json").write_text(json.dumps({"mcpServers": {"other": {"command": "x"}}}))
    kicadmcp.ensure(ws, "ee", log=lambda *_: None)
    mcp = json.loads((ws.root / ".mcp.json").read_text())["mcpServers"]
    assert set(mcp) == {"other", "kicad"}
    assert mcp["kicad"] == {"command": str(ws.venv / "bin" / "curatrix"), "args": ["mcp-server", "kicad"],
                            "env": {"XD_WORKSPACE": str(ws.root)}}
    assert not (ws.root / ".claude" / "settings.local.json").exists()   # the owner approves it
    ws2 = Workspace(make_ws(tmp_path / "b"))
    kicadmcp.ensure(ws2, "sw", log=lambda *_: None)                     # role without the tool
    assert not (ws2.root / ".mcp.json").exists()


def test_doctor_rows_without_install(tmp_path, monkeypatch):
    ws = Workspace(make_ws(tmp_path, monkeypatch))
    assert kicadmcp.doctor_rows(ws, "ee") == []          # tools.yaml's row already says "not installed"
    assert kicadmcp.doctor_rows(ws, "sw") == []


def test_user_dir_snapshot(tmp_path):
    home = tmp_path / "home"
    (home / ".config" / "kicad" / "10.0").mkdir(parents=True)
    before = kicadmcp.snapshot_user_dirs(home)
    assert before[".kicad-mcp"] == ("missing",)
    assert kicadmcp.diff_snapshots(before, kicadmcp.snapshot_user_dirs(home)) == []
    (home / ".kicad-mcp" / "logs").mkdir(parents=True)              # planted: the server wrote below HOME
    f = home / ".config" / "kicad" / "10.0" / "kicad_common.json"
    f.write_text("{}")
    changed = kicadmcp.diff_snapshots(before, kicadmcp.snapshot_user_dirs(home))
    assert ".kicad-mcp" in changed and ".config/kicad/10.0/kicad_common.json" in changed


def test_cli_has_mcp_server_kicad():
    a = cli.parser().parse_args(["mcp-server", "kicad"])
    assert a.server == "kicad" and a.mode == "readonly" and a.func is cli.cmd_mcp_server
    assert cli.parser().parse_args(["mcp-server", "kicad", "--mode", "write"]).mode == "write"
    with pytest.raises(SystemExit):
        cli.parser().parse_args(["mcp-server", "kicad", "--mode", "anything"])


def test_mcp_limit_is_memory_only():
    from curatrix import limits
    lim = limits.resolve("mcp-kicad")
    assert lim.timeout is None and lim.memory


def test_handshake_against_a_fake_server(tmp_path, monkeypatch):
    """The handshake speaks MCP over stdio and waits for the worker's READY line on stderr."""
    ws = Workspace(make_ws(tmp_path, monkeypatch))
    fake = tmp_path / "fake.py"
    fake.write_text(
        "import sys, json\n"
        "for line in sys.stdin:\n"
        "    m = json.loads(line)\n"
        "    if m.get('id') == 1:\n"
        "        print(json.dumps({'jsonrpc':'2.0','id':1,'result':{}}), flush=True)\n"
        "    elif m.get('id') == 2:\n"
        "        print(json.dumps({'jsonrpc':'2.0','id':2,'result':{'tools':[{'name':'a'},{'name':'b'}]}}), flush=True)\n"
        "        print('[x] [INFO] Python process is ready.', file=sys.stderr, flush=True)\n")
    t = tools.parse(XDMOD / "tools.yaml").tools[kicadmcp.TOOL]
    import sys
    monkeypatch.setattr(kicadmcp, "command", lambda ws, t: [sys.executable, str(fake)])
    monkeypatch.setattr(kicadmcp.limits, "wrap", lambda cmd, lim: cmd)
    ok, detail = kicadmcp.handshake(ws, t, timeout=30)
    assert ok, detail
    assert "2 tools" in detail
    fake.write_text("import sys\nprint('KICAD_MCP_STRICT_PATHS is set, but: X', file=sys.stderr, flush=True)\n"
                    "sys.stdin.read()\n")
    ok, detail = kicadmcp.handshake(ws, t, timeout=10)
    assert not ok and "KICAD_MCP_STRICT_PATHS" in detail
    assert os.environ.get("XD_WORKSPACE") == str(ws.root)
