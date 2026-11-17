"""The FreeCAD MCP server as a curated tool (xdmod#69 finding 18, owner decision Q1).

neka-nat/freecad-mcp (MIT) has two halves at the same version:

* the addon ``FreeCADMCP`` (tools.yaml ``freecad-mcp-addon``), installed into the workspace
  FreeCAD's ``Mod/`` (``.xdmod/freecad/data/FreeCAD/v1-1/Mod/``): an XML-RPC server inside the
  FreeCAD GUI on 127.0.0.1:9875 that runs agent code on the GUI thread;
* the MCP server ``freecad-mcp`` (requirements.txt), started by Claude Code over stdio from the
  workspace ``.mcp.json``.

What curatrix adds (``ensure``, run by bootstrap/update):

* a token file ``.xdmod/freecad/mcp-token`` (0600, made once); ``curatrix env`` exports it as
  ``XD_FREECAD_MCP_TOKEN``, and ``.mcp.json`` passes it to the MCP server as ``FREECAD_MCP_TOKEN``;
* the addon's settings ``freecad_mcp_settings.json`` in FreeCAD's user data folder: remote access off,
  allowed IPs 127.0.0.1, the token, auto-start off;
* the ``freecad`` entry of ``<ws>/.mcp.json`` (other servers are kept) and its approval in
  ``<ws>/.claude/settings.local.json`` (``enabledMcpjsonServers``).

``curatrix launch freecad --mcp`` switches auto-start on for that run only, so the port is open
only while such a session runs, and sets ``HOME`` to ``.xdmod/stepup/home`` (StepUp, driven through
the MCP server, writes ``~/ksu-config.ini``). Without ``--mcp`` auto-start is switched off first.
"""
from __future__ import annotations

import json
import os
import secrets
from pathlib import Path

from curatrix import tools
from curatrix.ws import Workspace

ADDON = "freecad-mcp-addon"
PIP = "freecad-mcp"
SERVER = "freecad"                       # the name in .mcp.json
TOKEN_VAR = "XD_FREECAD_MCP_TOKEN"
SETTINGS = "freecad_mcp_settings.json"
SAFE = {"remote_enabled": False, "allowed_ips": "127.0.0.1"}


def token_path(ws: Workspace) -> Path:
    return ws.state / "freecad" / "mcp-token"


def user_data(ws: Workspace) -> Path:
    """FreeCAD 1.1's user app data folder under the launcher's XDG_DATA_HOME."""
    return ws.state / "freecad" / "data" / "FreeCAD" / "v1-1"


def settings_path(ws: Workspace) -> Path:
    return user_data(ws) / SETTINGS


def addon_tool(ws: Workspace, role: str | None) -> tools.Tool | None:
    try:
        return tools.for_role(tools.load_all(ws), role).tools.get(ADDON)
    except tools.ToolsError:
        return None


def read_token(ws: Workspace) -> str:
    p = token_path(ws)
    try:
        return p.read_text().strip() if p.is_file() else ""
    except OSError:
        return ""


def ensure_token(ws: Workspace) -> str:
    tok = read_token(ws)
    if tok:
        return tok
    p = token_path(ws)
    p.parent.mkdir(parents=True, exist_ok=True)
    tok = secrets.token_urlsafe(32)
    fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "w") as f:
        f.write(tok + "\n")
    return tok


def read_settings(ws: Workspace) -> dict | None:
    p = settings_path(ws)
    try:
        return json.loads(p.read_text()) if p.is_file() else None
    except (OSError, ValueError):
        return None


def write_settings(ws: Workspace, auto_start: bool = False) -> dict:
    """The addon settings with remote access off, loopback only, the token, and `auto_start`."""
    s = read_settings(ws) or {}
    s.update(SAFE, auth_token=ensure_token(ws), auto_start_rpc=bool(auto_start))
    p = settings_path(ws)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(s, indent=2) + "\n")
    os.chmod(tmp, 0o600)
    tmp.replace(p)
    return s


def mcp_entry(ws: Workspace) -> dict:
    v = ws.venv / "bin"
    return {"command": str(v / "freecad-mcp"),
            # execute_code_headless: FreeCADCmd under the freecad limits and the workspace config
            "args": ["--freecadcmd", f"{v / 'curatrix'} run --use freecad -- FreeCADCmd"],
            "env": {"FREECAD_MCP_TOKEN": "${" + TOKEN_VAR + "}"}}


def _merge_json(p: Path, change) -> bool:
    try:
        d = json.loads(p.read_text()) if p.is_file() else {}
    except ValueError:
        raise tools.ToolsError(f"{p} is not valid JSON; fix it, then curatrix update") from None
    before = json.dumps(d, sort_keys=True)
    change(d)
    if json.dumps(d, sort_keys=True) == before:
        return False
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, indent=2) + "\n")
    return True


def write_mcp_config(ws: Workspace) -> list[str]:
    """The `freecad` server in <ws>/.mcp.json and its approval in <ws>/.claude/settings.local.json;
    everything else in both files is kept."""
    made = []

    def server(d):
        d.setdefault("mcpServers", {})[SERVER] = mcp_entry(ws)

    def enable(d):
        on = d.setdefault("enabledMcpjsonServers", [])
        if SERVER not in on:
            on.append(SERVER)
        off = d.get("disabledMcpjsonServers")
        if isinstance(off, list) and SERVER in off:
            off.remove(SERVER)
    for p, fn in ((ws.root / ".mcp.json", server), (ws.root / ".claude" / "settings.local.json", enable)):
        if _merge_json(p, fn):
            made.append(ws.rel(p))
    return made


def ensure(ws: Workspace, role: str | None, log=print) -> None:
    """bootstrap / update: token, safe addon settings (auto-start off), MCP entry; only for the
    roles that install the addon."""
    if addon_tool(ws, role) is None:
        return
    write_settings(ws, auto_start=False)
    made = write_mcp_config(ws)
    log(f"  FreeCAD MCP: token {ws.rel(token_path(ws))}, settings (remote off, loopback, token), "
        f"MCP server '{SERVER}'" + (f" (wrote {', '.join(made)})" if made else ""))


def env(ws: Workspace) -> dict[str, str]:
    """For `curatrix env`: the token, if there is one."""
    tok = read_token(ws)
    return {TOKEN_VAR: tok} if tok else {}


def pip_version() -> str | None:
    from importlib import metadata
    try:
        return metadata.version(PIP)
    except metadata.PackageNotFoundError:
        return None


def addon_version(path: Path) -> str | None:
    import re
    p = path / "package.xml"
    if not p.is_file():
        return None
    m = re.search(r"<version>\s*([^<\s]+)\s*</version>", p.read_text(encoding="utf-8", errors="replace"))
    return m.group(1) if m else None


def doctor_rows(ws: Workspace, role: str | None) -> list[tuple[str, str, str]]:
    t = addon_tool(ws, role)
    if t is None:
        return []
    rows = []
    have = addon_version(t.path(ws))
    if have is not None and have != t.version:
        rows.append(("FAIL", f"FreeCAD MCP addon package.xml says {have}, tools.yaml {t.version}", "curatrix update"))
    pv = pip_version()
    if pv is None:
        rows.append(("FAIL", f"pip package {PIP} missing (tools.yaml addon {t.version})", "curatrix update"))
    elif pv != t.version:
        rows.append(("FAIL", f"pip {PIP} {pv} differs from the addon {t.version}", "pin both to one version"))
    s = read_settings(ws)
    tok = read_token(ws)
    if s is None:
        rows.append(("FAIL", f"FreeCAD MCP settings missing ({ws.rel(settings_path(ws))})", "curatrix update"))
    else:
        bad = [k for k, v in SAFE.items() if s.get(k) != v]
        if bad or not s.get("auth_token") or s.get("auth_token") != tok:
            what = ", ".join(bad + ([] if s.get("auth_token") and s.get("auth_token") == tok else ["token"]))
            rows.append(("FAIL", f"FreeCAD MCP settings unsafe or stale: {what}", "curatrix update"))
        elif s.get("auto_start_rpc"):
            rows.append(("warn", "FreeCAD MCP auto-start is on (a FreeCAD without --mcp opens port 9875)",
                         "curatrix launch freecad (switches it off) or curatrix update"))
        else:
            rows.append(("ok", f"FreeCAD MCP {t.version}: remote off, loopback, token", ws.rel(settings_path(ws))))
    mj = ws.root / ".mcp.json"
    try:
        has = SERVER in (json.loads(mj.read_text()).get("mcpServers") or {}) if mj.is_file() else False
    except ValueError:
        has = False
    if not has:
        rows.append(("warn", f"no '{SERVER}' server in .mcp.json", "curatrix update"))
    for d in sorted((Path.home() / ".local" / "share" / "FreeCAD").glob("*/Mod/FreeCADMCP")):
        rows.append(("warn", f"a user-global FreeCAD MCP addon: {d}", "remove it; the workspace has its own"))
    return rows


def launch_env(ws: Workspace, env: dict, mcp: bool) -> dict:
    """`launch freecad`: auto-start on only with --mcp; with --mcp HOME = .xdmod/stepup/home."""
    if read_settings(ws) is not None or mcp:
        write_settings(ws, auto_start=mcp)
    if mcp:
        home = ws.state / "stepup" / "home"
        home.mkdir(parents=True, exist_ok=True)
        real_home = env.get("HOME") or str(Path.home())
        xa = Path(real_home) / ".Xauthority"
        if "XAUTHORITY" not in env and xa.is_file():
            env["XAUTHORITY"] = str(xa)          # X11 looks for ~/.Xauthority otherwise
        env["HOME"] = str(home)
    return env


def after_launch(ws: Workspace, mcp: bool) -> None:
    if mcp:
        write_settings(ws, auto_start=False)
