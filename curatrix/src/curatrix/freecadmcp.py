"""The FreeCAD MCP server as a curated tool (xdmod#69 finding 18, owner decision Q1).

neka-nat/freecad-mcp (MIT) has two halves at the same version:

* the addon ``FreeCADMCP`` (tools.yaml ``freecad-mcp-addon``), installed into the workspace
  FreeCAD's ``Mod/`` (``.xdmod/freecad/data/FreeCAD/v1-1/Mod/``): an XML-RPC server inside the
  FreeCAD GUI on 127.0.0.1:9875 that runs agent code on the GUI thread;
* the MCP server ``freecad-mcp`` (requirements.txt), started by Claude Code over stdio from the
  workspace ``.mcp.json``.

What curatrix adds (``ensure``, run by bootstrap/update):

* a token file ``.xdmod/freecad/mcp-token`` (0600, made once); never in an environment that
  ``curatrix env`` prints: ``curatrix mcp-server freecad`` (the command in ``.mcp.json``) reads it
  when Claude Code starts the server and passes it as ``FREECAD_MCP_TOKEN``;
* the addon's settings ``freecad_mcp_settings.json`` in FreeCAD's user data folder: remote access off,
  allowed IPs 127.0.0.1, the token, auto-start off;
* the ``freecad`` entry of ``<ws>/.mcp.json`` (other servers are kept). No approval is written:
  Claude Code asks each person once per workspace (owner decision 2026-11-18, tiacsys/xdmod#69).
  curatrix never touches ``.claude/settings.local.json``: Claude Code stores the person's answer there.

``curatrix mcp-server freecad`` runs ``freecad-mcp`` under the ``mcp`` limits with ``HOME`` and the
XDG folders under ``.xdmod/freecad-mcp/``: freecad-mcp 0.1.32 writes its headless scripts to
``~/.cache/freecad-mcp/headless`` (``Path.home()``), which must never be the user's home.

``curatrix launch freecad --mcp`` switches auto-start on for that run only, so the port is open
only while such a session runs, and sets ``HOME`` to ``.xdmod/stepup/home`` (StepUp, driven through
the MCP server, writes ``~/ksu-config.ini``). It is switched off again when FreeCAD exits or the
launcher gets SIGTERM/SIGHUP/SIGINT; and every launch (with or without ``--mcp``) writes it first,
so a run that was killed hard (SIGKILL) leaves it on only until the next launch or update.
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
    """The server in .mcp.json: the curatrix wrapper (token from the file, HOME under .xdmod/)."""
    return {"command": str(ws.venv / "bin" / "curatrix"), "args": ["mcp-server", SERVER],
            "env": {"XD_WORKSPACE": str(ws.root)}}


def server_home(ws: Workspace) -> Path:
    return ws.state / "freecad-mcp"


def server_command(ws: Workspace) -> tuple[list[str], dict]:
    """argv and environment of the MCP server: freecad-mcp with headless runs through
    `curatrix run --use freecad -- FreeCADCmd`, HOME and XDG_* under .xdmod/freecad-mcp/, the token."""
    tok = read_token(ws)
    if not tok:
        raise tools.ToolsError(f"no token in {ws.rel(token_path(ws))}: run curatrix update")
    exe = ws.venv / "bin" / "freecad-mcp"
    if not exe.exists():
        raise tools.ToolsError(f"{ws.rel(exe)} missing: run curatrix update")
    env = ws.run_env()
    base = server_home(ws)
    for k, sub in (("HOME", "home"), ("XDG_CACHE_HOME", "cache"), ("XDG_CONFIG_HOME", "config"),
                   ("XDG_DATA_HOME", "data")):
        (base / sub).mkdir(parents=True, exist_ok=True)
        env[k] = str(base / sub)
    env["FREECAD_MCP_TOKEN"] = tok
    argv = [str(exe), "--freecadcmd", f"{ws.venv / 'bin' / 'curatrix'} run --use freecad -- FreeCADCmd"]
    return argv, env


def serve(ws: Workspace) -> int:
    """`curatrix mcp-server freecad`: exec the MCP server (stdio stays Claude Code's pipe)."""
    from curatrix import limits
    argv, env = server_command(ws)
    cmd = limits.wrap(argv, limits.resolve("mcp", ws))
    os.chdir(ws.root)
    os.execvpe(cmd[0], cmd, env)
    return 1                                  # not reached


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
    """The `freecad` server in <ws>/.mcp.json; everything else is kept. No approval (owner decision
    2026-11-18): Claude Code asks each person once and stores the answer in
    <ws>/.claude/settings.local.json, which curatrix never touches (it cannot tell an old curatrix
    entry from the person's own answer)."""
    made = []

    def server(d):
        d.setdefault("mcpServers", {})[SERVER] = mcp_entry(ws)
    if _merge_json(ws.root / ".mcp.json", server):
        made.append(ws.rel(ws.root / ".mcp.json"))
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
    uc = Path.home() / ".cache" / "freecad-mcp"
    if uc.exists():
        rows.append(("warn", f"{uc} exists: freecad-mcp ran with your HOME",
                     "start it only through .mcp.json (curatrix mcp-server freecad); remove the folder"))
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
