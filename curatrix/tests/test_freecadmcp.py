"""The FreeCAD MCP server as a curated tool (xdmod#69 finding 18, owner decision Q1)."""
import json
import stat

from curatrix import freecadmcp, setup, tools
from curatrix.ws import Workspace
from helpers import make_ws

XDMOD = __import__("pathlib").Path(__file__).resolve().parents[2]


def test_pins_agree():
    t = tools.parse(XDMOD / "tools.yaml").tools[freecadmcp.ADDON]
    req = (XDMOD / "requirements.txt").read_text()
    assert f"{freecadmcp.PIP}=={t.version}" in req
    assert t.location == ".xdmod/freecad/data/FreeCAD/v1-1/Mod/FreeCADMCP" and t.subdir == "addon/FreeCADMCP"
    assert t.licence == "MIT"


def test_ensure_token_settings_and_mcp_entry(tmp_path, monkeypatch):
    ws = Workspace(make_ws(tmp_path, monkeypatch))
    (ws.root / ".claude").mkdir()
    (ws.root / ".claude" / "settings.local.json").write_text(json.dumps({"permissions": {"allow": ["Bash(ls)"]},
                                                                        "disabledMcpjsonServers": ["freecad"]}))
    (ws.root / ".mcp.json").write_text(json.dumps({"mcpServers": {"other": {"command": "x"}}}))
    freecadmcp.ensure(ws, "me", log=lambda *_: None)
    tok = freecadmcp.read_token(ws)
    assert len(tok) > 30 and stat.S_IMODE(freecadmcp.token_path(ws).stat().st_mode) == 0o600
    s = freecadmcp.read_settings(ws)
    assert s == {"remote_enabled": False, "allowed_ips": "127.0.0.1", "auth_token": tok, "auto_start_rpc": False}
    mcp = json.loads((ws.root / ".mcp.json").read_text())["mcpServers"]
    assert set(mcp) == {"other", "freecad"}
    assert mcp["freecad"]["env"] == {"FREECAD_MCP_TOKEN": "${XD_FREECAD_MCP_TOKEN}"}
    assert mcp["freecad"]["command"].endswith(".venv/bin/freecad-mcp") and "--use freecad" in mcp["freecad"]["args"][1]
    loc = json.loads((ws.root / ".claude" / "settings.local.json").read_text())
    assert loc["enabledMcpjsonServers"] == ["freecad"] and loc["disabledMcpjsonServers"] == []
    assert loc["permissions"] == {"allow": ["Bash(ls)"]}
    assert ws.env()["XD_FREECAD_MCP_TOKEN"] == tok
    freecadmcp.ensure(ws, "me", log=lambda *_: None)          # idempotent: same token
    assert freecadmcp.read_token(ws) == tok
    # a role without the addon: nothing
    ws2 = Workspace(make_ws(tmp_path / "b"))
    freecadmcp.ensure(ws2, "sw", log=lambda *_: None)
    assert not freecadmcp.token_path(ws2).exists() and not (ws2.root / ".mcp.json").exists()


def test_launch_mcp_only_for_that_run(tmp_path, monkeypatch):
    ws = Workspace(make_ws(tmp_path, monkeypatch))
    freecadmcp.ensure(ws, "me", log=lambda *_: None)
    env = freecadmcp.launch_env(ws, {"HOME": str(tmp_path)}, mcp=True)
    assert freecadmcp.read_settings(ws)["auto_start_rpc"] is True
    assert env["HOME"] == str(ws.state / "stepup" / "home")
    freecadmcp.after_launch(ws, True)
    assert freecadmcp.read_settings(ws)["auto_start_rpc"] is False
    s = freecadmcp.read_settings(ws)
    s["auto_start_rpc"] = True                                   # switched on in the GUI
    freecadmcp.settings_path(ws).write_text(json.dumps(s))
    env = freecadmcp.launch_env(ws, {"HOME": str(tmp_path)}, mcp=False)
    assert env["HOME"] == str(tmp_path) and freecadmcp.read_settings(ws)["auto_start_rpc"] is False


def test_launch_strips_mcp_flag(tmp_path, monkeypatch):
    ws = Workspace(make_ws(tmp_path, monkeypatch))
    freecadmcp.ensure(ws, "me", log=lambda *_: None)
    seen = {}

    monkeypatch.setattr(setup.limits, "wrap", lambda cmd, lim: cmd)

    def run(cmd, cwd, env):
        seen.update(cmd=cmd, env=env, auto=freecadmcp.read_settings(ws)["auto_start_rpc"])
        return type("R", (), {"returncode": 0})()
    monkeypatch.setattr(setup.subprocess, "run", run)
    monkeypatch.setattr(setup.shutil, "which", lambda exe: "/usr/bin/" + exe)
    monkeypatch.setattr(setup, "real_tool", lambda ws, exe: None)
    assert setup.launch(ws, "freecad", ["--mcp", "a.FCStd"]) == 0
    assert "--mcp" not in seen["cmd"] and "a.FCStd" in seen["cmd"] and seen["auto"] is True
    assert seen["env"]["HOME"].endswith(".xdmod/stepup/home")
    assert freecadmcp.read_settings(ws)["auto_start_rpc"] is False


def test_doctor_rows(tmp_path, monkeypatch):
    ws = Workspace(make_ws(tmp_path, monkeypatch))
    monkeypatch.setattr(freecadmcp, "pip_version", lambda: "0.1.32")
    monkeypatch.setattr(freecadmcp.Path, "home", lambda: tmp_path / "home")
    rows = freecadmcp.doctor_rows(ws, "me")
    assert any(st == "FAIL" and "settings missing" in w for st, w, _ in rows)
    freecadmcp.ensure(ws, "me", log=lambda *_: None)
    rows = freecadmcp.doctor_rows(ws, "me")
    assert [st for st, _, _ in rows] == ["ok"]
    s = freecadmcp.read_settings(ws)
    s["remote_enabled"] = True                                   # planted: remote access switched on
    freecadmcp.settings_path(ws).write_text(json.dumps(s))
    assert any(st == "FAIL" and "remote_enabled" in w for st, w, _ in freecadmcp.doctor_rows(ws, "me"))
    monkeypatch.setattr(freecadmcp, "pip_version", lambda: "0.1.31")
    assert any(st == "FAIL" and "differs" in w for st, w, _ in freecadmcp.doctor_rows(ws, "me"))
    user = tmp_path / "home" / ".local/share/FreeCAD/v1-1/Mod/FreeCADMCP"
    user.mkdir(parents=True)
    assert any(st == "warn" and "user-global" in w for st, w, _ in freecadmcp.doctor_rows(ws, "me"))
    assert freecadmcp.doctor_rows(ws, "sw") == []
