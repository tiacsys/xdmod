"""The KiCad MCP server as a curated tool (xdmod#69 finding 19, owner decisions Q1, Q3).

mixelpixx/KiCAD-MCP-Server (MIT) through the fork tiacsys/KiCAD-MCP-Server: tools.yaml
``kicad-mcp`` installs the fork's release asset (built ``dist/``, production ``node_modules``,
``python/``, hashed ``requirements.lock.txt`` without pymupdf) into ``.venv/opt/kicad-mcp`` and its
Python worker's own venv (``python_venv``: kipy, sexpdata, kicad-skip, ...; the system KiCad's
SWIG ``pcbnew`` linked in). Research: build/research-kicad-mcp/report.md §6.

What curatrix adds:

* ``curatrix mcp-server kicad`` starts the server over stdio (memory limit only, use ``mcp-kicad``) with the
  environment of ``server_env``: the workspace KiCad config of ``curatrix launch kicad``, the
  fork's ``KICAD_MCP_STRICT_PATHS=1`` (no fallback below ``$HOME``; the worker refuses to start
  without its folders), its own folders under ``.xdmod/kicad-mcp/``, logs under
  ``build/kicad-mcp/logs``, operating mode ``readonly`` unless ``--mode write`` is given, and the
  toolboxes core + schematic + board + drc open (no library registration, part search or GUI
  driver unless a client opens them; readonly hides every writing tool anyway).
* ``ensure`` (bootstrap / update) writes the ``kicad`` server into ``<ws>/.mcp.json`` (other
  servers are kept). Approving it is left to the owner (Claude Code asks once per project).
* ``doctor_rows``: the worker venv (kipy, sexpdata, skip; no pymupdf), ``pcbnew.Version()``
  against the pinned KiCad, an MCP handshake (initialize + tools/list, then the Python worker's
  READY) and that the user's KiCad and kicad-mcp folders did not change during it.
"""
from __future__ import annotations

import json
import os
import select
import shutil
import subprocess
import time
from pathlib import Path

from curatrix import limits, tools
from curatrix.ws import Workspace

TOOL = "kicad-mcp"
SERVER = "kicad"                          # the name in .mcp.json
MODES = ("readonly", "write", "manufacturing")
TOOLBOXES = "core,schematic,board,drc"
KICAD_VERSION = "10.0"                    # the KiCad of tools.yaml (kicad-cli 10.0.x)
SMOKE_TIMEOUT = 90                        # s: initialize + tools/list + the worker's READY

# The user's folders that KiCad and the server would write without the workspace config.
USER_DIRS = (".config/kicad", ".local/share/kicad", ".cache/kicad", ".kicad-mcp",
             ".config/kicad-mcp", ".cache/kicad-mcp", ".local/share/kicad-mcp")
UNSET = ("PYTHONPATH", "PYTHONHOME", "VIRTUAL_ENV", "KICAD_GUI_DRIVER_AUTOINSTALL")


def tool(ws: Workspace, role: str | None) -> tools.Tool | None:
    try:
        return tools.for_role(tools.load_all(ws), role).tools.get(TOOL)
    except tools.ToolsError:
        return None


def home(ws: Workspace) -> Path:
    return ws.state / "kicad-mcp"


def build_dir(ws: Workspace) -> Path:
    return ws.root / "build" / "kicad-mcp"


def server_env(ws: Workspace, t: tools.Tool, mode: str = "readonly") -> dict[str, str]:
    """The environment of the server (research report §6.6). Every path is absolute."""
    from curatrix import setup                      # setup imports this module
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}, not {mode!r}")
    env = setup.launch_env(ws, "kicad")             # KICAD_CONFIG_HOME, _CACHE_, _DOCUMENTS_, KICAD10_*_DIR
    for k in UNSET:
        env.pop(k, None)
    third = Path(env["KICAD_DOCUMENTS_HOME"]) / "kicad" / KICAD_VERSION / "3rdparty"
    h, b = home(ws), build_dir(ws)
    # HOME too: child processes (kicad-cli, Java for Freerouting) follow the environment, not
    # the server's strict mode (fork review of #4, N3); same rule as freecadmcp.serve.
    dirs = {"HOME": h / "home", "KICAD10_3RD_PARTY": third, "KICAD_MCP_HOME": h,
            "KICAD_MCP_LOG_DIR": b / "logs",
            "XDG_CONFIG_HOME": h / "config", "XDG_CACHE_HOME": h / "cache", "XDG_DATA_HOME": h / "data",
            "TMPDIR": b / "tmp"}
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    env.update({k: str(v) for k, v in dirs.items()})
    env.update({
        "KICAD_CLI": str(ws.venv / "bin" / "kicad-cli"),          # the shim: workspace config
        "KICAD_PYTHON": str(tools.venv_python(ws, t)),
        "KICAD_BACKEND": "auto",
        "KICAD_MCP_STRICT_PATHS": "1",
        "KICAD_MCP_OPERATING_MODE": mode,
        "KICAD_MCP_TOOLBOXES": TOOLBOXES,
        "LC_ALL": "C.UTF-8",
    })
    return env


def command(ws: Workspace, t: tools.Tool) -> list[str]:
    node = shutil.which("node") or "node"
    return [node, str(t.path(ws) / "dist" / "index.js")]


def run(ws: Workspace, mode: str = "readonly") -> int:
    """`curatrix mcp-server kicad`: the server on this process's stdin/stdout (nothing else may write to
    stdout). Memory limit only (use `mcp`): a session runs as long as the client does."""
    t = tool(ws, ws.role) or tool(ws, None)
    if t is None:
        raise SystemExit(f"curatrix mcp-server kicad: {TOOL} is not in tools.yaml")
    if not tools.installed_ok(ws, t):
        raise SystemExit(f"curatrix mcp-server kicad: {TOOL} {t.version} is not installed (curatrix update)")
    lim = limits.resolve("mcp-kicad", ws)
    return limits.norm_rc(subprocess.run(limits.wrap(command(ws, t), lim), cwd=ws.root,
                                         env=server_env(ws, t, mode)).returncode)


# ------------------------------------------------------------------ .mcp.json
def mcp_entry(ws: Workspace) -> dict:
    from curatrix import setup
    main = setup.main_workspace(ws)
    return {"command": str(main.venv / "bin" / "curatrix"), "args": ["mcp-server", SERVER],
            "env": {"XD_WORKSPACE": str(main.root)}}


def write_mcp_config(ws: Workspace) -> bool:
    """The `kicad` server in <ws>/.mcp.json; other servers are kept. No approval is written."""
    from curatrix import freecadmcp

    def server(d):
        d.setdefault("mcpServers", {})[SERVER] = mcp_entry(ws)
    return freecadmcp._merge_json(ws.root / ".mcp.json", server)


def ensure(ws: Workspace, role: str | None, log=print) -> None:
    """bootstrap / update: the server's folders and the .mcp.json entry, for the roles that
    install the tool."""
    t = tool(ws, role)
    if t is None:
        return
    for d in (home(ws), build_dir(ws) / "logs"):
        d.mkdir(parents=True, exist_ok=True)
    made = write_mcp_config(ws)
    log(f"  KiCad MCP: server '{SERVER}' in .mcp.json" + (" (written)" if made else "")
        + f"; `curatrix mcp-server kicad` (readonly, toolboxes {TOOLBOXES}, strict paths)")


# ------------------------------------------------------------------ doctor
def snapshot_user_dirs(home_dir: Path | None = None, limit: int = 20000) -> dict[str, tuple]:
    """Path -> (mtime_ns, size) of everything below the user folders of USER_DIRS, plus the
    folders themselves (missing ones as None)."""
    base = home_dir or Path.home()
    snap: dict[str, tuple] = {}
    for rel in USER_DIRS:
        root = base / rel
        if not root.exists():
            snap[rel] = ("missing",)
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            for name in [*dirnames, *filenames, "."]:
                p = Path(dirpath) / name if name != "." else Path(dirpath)
                try:
                    st = p.lstat()
                except OSError:
                    continue
                snap[str(p.relative_to(base))] = (st.st_mtime_ns, st.st_size)
                if len(snap) >= limit:
                    return snap
    return snap


def diff_snapshots(before: dict, after: dict) -> list[str]:
    return sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))


def _send(proc: subprocess.Popen, msg: dict) -> None:
    proc.stdin.write((json.dumps(msg) + "\n").encode())
    proc.stdin.flush()


def handshake(ws: Workspace, t: tools.Tool, timeout: float = SMOKE_TIMEOUT) -> tuple[bool, str]:
    """Start the server as .mcp.json does, send initialize and tools/list, and wait until the
    Python worker reported READY (strict mode makes it exit without its folders). Returns
    (ok, detail)."""
    lim = limits.resolve("mcp-kicad", ws)
    proc = subprocess.Popen(limits.wrap(command(ws, t), lim), cwd=ws.root, env=server_env(ws, t),
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out, err = b"", b""
    tools_n, ready, failed = None, False, ""
    deadline = time.monotonic() + timeout
    try:
        _send(proc, {"jsonrpc": "2.0", "id": 1, "method": "initialize",
                     "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                                "clientInfo": {"name": "curatrix-doctor", "version": "1"}}})
        sent_list = False
        while time.monotonic() < deadline and not (tools_n is not None and ready) and not failed:
            r, _, _ = select.select([proc.stdout, proc.stderr], [], [], 1.0)
            for f in r:
                chunk = os.read(f.fileno(), 65536)
                if not chunk:
                    failed = failed or f"server exited (rc {proc.poll()})"
                    continue
                if f is proc.stdout:
                    out += chunk
                else:
                    err += chunk
            while b"\n" in out:
                line, out = out.split(b"\n", 1)
                try:
                    msg = json.loads(line)
                except ValueError:
                    continue
                if msg.get("id") == 1 and not sent_list:
                    _send(proc, {"jsonrpc": "2.0", "method": "notifications/initialized"})
                    _send(proc, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
                    sent_list = True
                elif msg.get("id") == 2:
                    tools_n = len((msg.get("result") or {}).get("tools") or [])
            text = err.decode(errors="replace")
            if "Python process is ready" in text:
                ready = True
            if "KICAD_MCP_STRICT_PATHS is set, but" in text or "Python process exited" in text:
                failed = failed or text[text.find("KICAD_MCP_STRICT") if "KICAD_MCP_STRICT" in text
                                        else text.find("Python process exited"):][:300].strip()
    finally:
        try:
            proc.stdin.close()
        except OSError:
            pass
        try:
            proc.wait(timeout=15)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
    if failed:
        return False, failed
    if tools_n is None:
        return False, f"no tools/list answer within {timeout:.0f} s"
    if not ready:
        return False, f"{tools_n} tools listed, but the Python worker was not ready within {timeout:.0f} s"
    return True, f"initialize + tools/list ({tools_n} tools, readonly), Python worker ready"


def _venv_check(ws: Workspace, t: tools.Tool, code: str) -> subprocess.CompletedProcess:
    return limits.run([str(tools.venv_python(ws, t)), "-I", "-c", code], "kicad-cli", ws,
                      env=server_env(ws, t), capture_output=True, text=True, timeout=180)


def doctor_rows(ws: Workspace, role: str | None, smoke: bool = True) -> list[tuple[str, str, str]]:
    t = tool(ws, role)
    if t is None or not tools.installed_ok(ws, t):
        return []                                     # the tools.yaml row already says so
    rows: list[tuple[str, str, str]] = []
    # -I: the venv's own site-packages and the .pth with pcbnew, nothing from the environment
    r = _venv_check(ws, t, "import kipy, sexpdata, skip, importlib.util as u;"
                           "print(bool(u.find_spec('pymupdf') or u.find_spec('fitz')))")
    if r.returncode:
        rows.append(("FAIL", "kicad-mcp worker venv: import kipy, sexpdata, skip failed",
                     (r.stderr.strip().splitlines() or ["?"])[-1] + "; curatrix update"))
    elif r.stdout.strip() == "True":
        rows.append(("warn", "kicad-mcp worker venv has pymupdf (AGPL-3.0)", "curatrix update (the lock leaves it out)"))
    else:
        rows.append(("ok", "kicad-mcp worker venv: kipy, sexpdata, skip; no pymupdf",
                     ws.rel(tools.venv_python(ws, t).parent.parent)))
    want = (tools.load_all(ws).system.get("kicad-cli") or tools.SystemTool("kicad-cli", "any")).version
    r = _venv_check(ws, t, "import pcbnew; print(pcbnew.Version())")
    have = r.stdout.strip().splitlines()[-1] if r.returncode == 0 and r.stdout.strip() else None
    if have is None:
        rows.append(("FAIL", "kicad-mcp worker: import pcbnew failed",
                     (r.stderr.strip().splitlines() or ["?"])[-1] + "; system KiCad installed? curatrix update"))
    elif not tools.version_ok(want, tools._VERSION.search(have).group(1) if tools._VERSION.search(have) else have):
        rows.append(("FAIL", f"kicad-mcp worker: pcbnew {have}, tools.yaml wants KiCad {want}", "curatrix update"))
    else:
        rows.append(("ok", f"kicad-mcp worker: pcbnew {have}"))
    if smoke and have is not None:
        before = snapshot_user_dirs()
        ok, detail = handshake(ws, t)
        changed = diff_snapshots(before, snapshot_user_dirs())
        rows.append(("ok" if ok else "FAIL", "kicad-mcp MCP handshake", detail))
        if changed:
            rows.append(("FAIL", f"kicad-mcp changed user folders during the handshake: {', '.join(changed[:5])}"
                         + (" ..." if len(changed) > 5 else ""), "report it; the server must stay workspace-local"))
        else:
            rows.append(("ok", "kicad-mcp left ~/.config/kicad, ~/.local/share/kicad, ~/.cache/kicad, "
                         "~/.kicad-mcp unchanged"))
    mj = ws.root / ".mcp.json"
    try:
        have_entry = (json.loads(mj.read_text()).get("mcpServers") or {}).get(SERVER) if mj.is_file() else None
    except ValueError:
        have_entry = None
    if have_entry is None:
        rows.append(("warn", f"no '{SERVER}' server in .mcp.json", "curatrix update"))
    elif have_entry != mcp_entry(ws):
        rows.append(("warn", f"'{SERVER}' server in .mcp.json differs from curatrix's", "curatrix update"))
    return rows
