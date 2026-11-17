"""Memory limits and timeouts for every tool (D71, D117, command-layer.md §6).

`limits.yaml` (next to this package, ``xdmod/curatrix/limits.yaml``) gives a memory limit and a
timeout per *use* (docs, pilot, firefox, gui, ...). ``<ws>/.xdmod/limits.yaml`` overrides it
per use and key.

Backends (``$XD_LIMIT_BACKEND`` forces one):

- ``systemd``: ``systemd-run --user --scope -p MemoryMax=M -p MemorySwapMax=0 -- timeout T cmd``
  (the same as the interim ``xd-limit``). Used when a systemd user session answers.
- ``ulimit``: ``sh -c 'ulimit -v KB; exec timeout T cmd'`` -- GitHub runners have no systemd user
  session; the address-space limit is the fallback (``vmem``, default = memory).
- ``none``: no limits (debugging only).

GUI tools get a memory limit only (``timeout: none``, D117). Exit codes: the command's own;
124 = timeout; 137 = killed (usually out of memory).
"""
from __future__ import annotations

import functools
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import yaml

from curatrix.ws import CURATRIX_DIR, Workspace

DEFAULT_FILE = CURATRIX_DIR / "limits.yaml"
_SIZE = re.compile(r"^(\d+(?:\.\d+)?)([KMGT]?)i?B?$", re.I)


@dataclass(frozen=True)
class Limit:
    use: str
    memory: str
    timeout: str | None          # None = no timeout
    vmem: str | None             # fallback ulimit -v; None = no address-space limit
    java_heap: str | None = None


def size_kib(s: str) -> int:
    m = _SIZE.match(s.strip())
    if not m:
        raise ValueError(f"bad size {s!r} (use e.g. 512M, 4G)")
    n, unit = float(m.group(1)), m.group(2).upper()
    return int(n * {"": 1 / 1024, "K": 1, "M": 1024, "G": 1024**2, "T": 1024**3}[unit])


def load_table(ws: Workspace | None = None, base: Path = DEFAULT_FILE) -> dict:
    data = yaml.safe_load(base.read_text()) or {}
    table = {"defaults": dict(data.get("defaults") or {}), "uses": {k: dict(v or {}) for k, v in (data.get("uses") or {}).items()}}
    if ws is not None:
        ov = ws.state / "limits.yaml"
        if ov.is_file():
            o = yaml.safe_load(ov.read_text()) or {}
            table["defaults"].update(o.get("defaults") or {})
            for k, v in (o.get("uses") or {}).items():
                table["uses"].setdefault(k, {}).update(v or {})
    return table


def resolve(use: str, ws: Workspace | None = None, memory: str | None = None, timeout: str | None = None,
            table: dict | None = None) -> Limit:
    t = table or load_table(ws)
    entry = {**t["defaults"], **t["uses"].get(use, {})}
    if use not in t["uses"] and use != "default":
        raise KeyError(f"unknown limits use {use!r}; known: {', '.join(sorted(t['uses']))}")
    mem = str(memory or entry.get("memory", "1G"))
    to = str(timeout or entry.get("timeout", "5m"))
    vmem = entry.get("vmem", mem)
    size_kib(mem)
    return Limit(use=use, memory=mem, timeout=None if to.lower() == "none" else to,
                 vmem=None if str(vmem).lower() == "none" else str(vmem), java_heap=entry.get("java_heap"))


@functools.cache
def systemd_available() -> bool:
    """True if a systemd user scope can be started (checked once per process)."""
    if not shutil.which("systemd-run"):
        return False
    if not os.environ.get("XDG_RUNTIME_DIR") and not os.environ.get("DBUS_SESSION_BUS_ADDRESS"):
        return False
    try:
        r = subprocess.run(["systemd-run", "--user", "--scope", "--quiet", "--collect", "--", "true"],
                           capture_output=True, timeout=20)
        return r.returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def backend() -> str:
    b = os.environ.get("XD_LIMIT_BACKEND")
    if b:
        if b not in ("systemd", "ulimit", "none"):
            raise ValueError(f"XD_LIMIT_BACKEND must be systemd, ulimit or none, not {b!r}")
        return b
    return "systemd" if systemd_available() else "ulimit"


def wrap(cmd: list[str], lim: Limit, which: str | None = None) -> list[str]:
    """The argv that runs `cmd` under `lim` with the given backend."""
    which = which or backend()
    timeout = ["timeout", "--kill-after=10s", lim.timeout] if lim.timeout else []
    if which == "none":
        return [*timeout, *cmd]
    if which == "systemd":
        return ["systemd-run", "--user", "--scope", "--quiet", "--collect",
                "-p", f"MemoryMax={lim.memory}", "-p", "MemorySwapMax=0", "--", *timeout, *cmd]
    # ulimit fallback: sh sets the address-space limit, then execs timeout + the command.
    ulim = f"ulimit -v {size_kib(lim.vmem)}; " if lim.vmem else ""
    return ["sh", "-c", ulim + 'exec "$@"', "curatrix-limit", *timeout, *cmd]


def describe(lim: Limit) -> str:
    return f"{lim.use}: memory {lim.memory}, timeout {lim.timeout or 'none'}"


def run(cmd: list[str], use: str = "script", ws: Workspace | None = None, *, memory: str | None = None,
        timeout: str | None = None, check: bool = False, env: dict | None = None, **kw) -> subprocess.CompletedProcess:
    """subprocess.run under the limits of `use`. Extra keyword arguments go to subprocess.run."""
    lim = resolve(use, ws, memory, timeout)
    if env is None and ws is not None:
        env = ws.run_env()
    if ws is not None:
        env = tool_env(ws, use, env, cmd)
    if ws is not None and "cwd" not in kw:
        kw["cwd"] = ws.root
    r = subprocess.run(wrap(cmd, lim), env=env, **kw)
    r.returncode = norm_rc(r.returncode)
    if check:
        r.check_returncode()
    return r


def norm_rc(rc: int) -> int:
    """A process killed by a signal (the OOM kill takes the whole scope) -> 128 + signal, like a shell."""
    return 128 - rc if rc < 0 else rc


def explain_rc(rc: int) -> str:
    return {124: "timeout (limit reached)", 137: "killed (memory limit reached?)"}.get(rc, "")


FREECAD_NAMES = ("FreeCAD", "FreeCADCmd", "freecad", "freecadcmd")


def tool_env(ws: Workspace, use: str, env: dict | None, cmd: list[str] | None = None) -> dict | None:
    """The workspace-local config of KiCad and FreeCAD, so a scripted run never writes the user's
    ~/.config (rule 4, D88; task 5.3 incident: a pcbnew run rewrote ~/.config/kicad).

    KiCad's variables (KICAD_CONFIG_HOME, KICAD10_*) only affect KiCad, so every run gets them,
    also `python board.py` that imports pcbnew under `script`. FreeCAD's config lives in the XDG
    dirs, which other tools (git, gh) read too, so they are set only for the `freecad` use or a
    FreeCAD command."""
    from curatrix import setup                      # local import: setup imports limits
    out = dict(env if env is not None else ws.run_env())
    kicad = setup.launch_env(ws, "kicad")
    out.update({k: v for k, v in kicad.items() if k.startswith("KICAD")})
    exe0 = Path(cmd[0]).name if cmd else ""
    if use == "kicad-cli" or exe0.startswith(("kicad", "eeschema", "pcbnew")):
        out["LC_ALL"] = "C.UTF-8"           # KiCad writes numbers with the locale's decimal comma otherwise
    exe = Path(cmd[0]).name if cmd else ""
    if use == "freecad" or exe.startswith(FREECAD_NAMES):
        fc = setup.launch_env(ws, "freecad")
        out.update({k: v for k, v in fc.items() if k.startswith("XDG_")})
    return out
