"""Blender as an optional local renderer (owner decision 2026-11-17; XD-ADR on Blender renderings).

Blender is a system package used through its executable (no ``bpy`` wheel). It is **not pinnable**:
curatrix installs nothing, the distribution updates it, so its output is local only and never
compared or committed. ``tools.yaml`` records the version it was tried with; ``curatrix doctor``
notes a missing Blender and warns on another version, it never fails on it.

Isolation: every call, from curatrix, ``curatrix run -- blender``, ``curatrix launch blender`` or the
``.venv/bin/blender`` shim, gets ``--factory-startup`` (no user preferences, no add-ons, no startup
file) and the user paths under ``<ws>/.xdmod/blender/`` (``env``): Blender's own ``BLENDER_USER_*``
variables, the XDG dirs (Blender's cache, Mesa's shader cache) and ``TMPDIR`` (Blender's session
temp folder). Nothing reaches ``~/.config/blender`` or ``~/.cache/blender``.
"""
from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

NAME = "blender"
# always first on the command line: no user preferences or startup file, no extension network
# access, no Python in .blend files
ARGS = ("--factory-startup", "--offline-mode", "--disable-autoexec")
USE = "blender"
# Blender's Python finds the workspace .venv (VIRTUAL_ENV, or the venv's python3 first on PATH and
# its pyvenv.cfg) and then misses the system numpy that its glTF importer needs. Blender calls run
# without these variables and without .venv/bin on PATH.
UNSET = ("VIRTUAL_ENV", "PYTHONHOME", "PYTHONPATH")


def path_without_venv(ws, path: str) -> str:
    """PATH without the workspace's .venv/bin and any other virtual environment's bin folder (a
    folder next to a pyvenv.cfg), also when reached through a link."""
    import os
    venv = (ws.venv / "bin").resolve()
    keep = []
    for d in path.split(os.pathsep):
        try:
            if d and (Path(d).resolve() == venv or (Path(d).resolve().parent / "pyvenv.cfg").is_file()):
                continue
        except OSError:
            pass
        keep.append(d)
    return os.pathsep.join(keep)


def dirs(ws) -> dict[str, Path]:
    """The user paths of Blender under <ws>/.xdmod/blender/."""
    b = ws.state / "blender"
    u = b / "user"
    return {"BLENDER_USER_RESOURCES": u, "BLENDER_USER_CONFIG": u / "config",
            "BLENDER_USER_SCRIPTS": u / "scripts", "BLENDER_USER_DATAFILES": u / "datafiles",
            "BLENDER_USER_EXTENSIONS": u / "extensions",
            "XDG_CONFIG_HOME": b / "xdg" / "config", "XDG_DATA_HOME": b / "xdg" / "data",
            "XDG_CACHE_HOME": b / "xdg" / "cache", "TMPDIR": b / "tmp"}


def env(ws) -> dict[str, str]:
    """The variables every Blender call gets (folders created)."""
    d = dirs(ws)
    for p in d.values():
        p.mkdir(parents=True, exist_ok=True)
    return {k: str(v) for k, v in d.items()}


def is_blender(cmd: list[str] | None) -> bool:
    return bool(cmd) and Path(cmd[0]).name.lower().startswith(NAME)


def with_args(cmd: list[str]) -> list[str]:
    """``cmd`` with the isolation arguments right after the program (not twice)."""
    rest = [a for a in cmd[1:] if a not in ARGS]
    return [cmd[0], *ARGS, *rest]


def find(ws) -> Path | None:
    """The real Blender binary (not a shim), or None."""
    from curatrix import setup
    return setup.real_tool(ws, NAME)


def version(ws) -> str | None:
    """The Blender version (through the isolated call), or None without Blender."""
    from curatrix import limits
    exe = find(ws)
    if exe is None:
        return None
    r = limits.run([str(exe), "--version"], USE, ws, capture_output=True, text=True)
    m = re.search(r"Blender (\d+\.\d+\.\d+)", (r.stdout or "") + (r.stderr or ""))
    return m.group(1) if m else None


class BlenderError(RuntimeError):
    pass


def run_script(ws, script: Path, env_vars: dict[str, str], result: Path, exe: Path | None = None) -> dict:
    """``blender -b <isolation args> --python-exit-code 1 -P <script>`` under the ``blender``
    limits; inputs by environment variables, success from the result file the script writes."""
    from curatrix import limits
    exe = exe or find(ws)
    if exe is None:
        raise BlenderError("blender not found on PATH")
    result.parent.mkdir(parents=True, exist_ok=True)
    result.unlink(missing_ok=True)
    e = ws.run_env({**env_vars, "XD_RESULT": str(result)})
    r = limits.run([str(exe), "-b", "--python-exit-code", "1", "-P", str(script)], USE, ws,
                   capture_output=True, text=True, env=e)
    tail = (r.stdout + r.stderr)[-1500:]
    if not result.is_file():
        raise BlenderError(f"blender {script.name}: no result file (exit {r.returncode} "
                           f"{limits.explain_rc(r.returncode)}): {tail}")
    out = json.loads(result.read_text())
    if not out.get("ok"):
        raise BlenderError(f"blender {script.name} failed: {out.get('error') or out}")
    return out


def available(ws) -> bool:
    return shutil.which(NAME) is not None and find(ws) is not None
