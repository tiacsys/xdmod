"""Workspace setup: bootstrap, update, doctor, launchers, .claude links, git hooks
(command-layer.md §2, §4, §5; repo-topology.md §4; D69, D86, D88, D93, D100, D113, D117).
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from curatrix import blender, limits, tools
from curatrix.ws import Workspace

# repo-topology.md §4: group filter added to the manifest default (which is minimal, D93).
# me and sw also get the ee group (task 5.14): ME pushes board geometry into the KiCad files,
# SW reads the board pin maps from the EE model.
ROLES = {
    "syseng": [],
    "ee": ["+ee"],
    "ee3d": ["+ee", "+kicad-3d"],
    "me": ["+me", "+freecad-parts", "+ee"],
    "sw": ["+sw", "+ee"],
    "integration": ["+ee", "+me", "+sw", "+integration"],
    "full": ["+ee", "+me", "+sw", "+integration", "+kicad-3d", "+freecad-parts"],
    "ci-full": ["+ee", "+me", "+sw", "+integration"],
}
HOOK_MARK = "# installed by curatrix (D100)"


class SetupError(Exception):
    pass


def say(msg: str) -> None:
    print(msg, flush=True)


def git(args: list[str], cwd: Path, ws: Workspace | None = None, check: bool = True) -> subprocess.CompletedProcess:
    r = limits.run(["git", *args], "git", ws, cwd=cwd, capture_output=True, text=True)
    if check and r.returncode:
        raise SetupError(f"git {' '.join(args)} failed in {cwd}: {r.stderr.strip()}")
    return r


def west(ws: Workspace, *args: str, use: str = "west") -> int:
    say(f"$ west {' '.join(args)}")
    return limits.run([*ws.west(), *args], use, ws).returncode


# ------------------------------------------------------------------ role
def set_role(ws: Workspace, role: str) -> None:
    if role not in ROLES:
        raise SetupError(f"unknown role {role!r}; roles: {', '.join(ROLES)}")
    if not ws.has_west:
        raise SetupError("no west workspace here (run bootstrap.sh / `west init -l <manifest>` first)")
    flt = ",".join(ROLES[role])
    if flt:
        if west(ws, "config", "manifest.group-filter", "--", flt):
            raise SetupError("west config manifest.group-filter failed")
    else:
        west(ws, "config", "-d", "manifest.group-filter")
    if west(ws, "config", "xdmod.role", role):
        raise SetupError("west config xdmod.role failed")


# ------------------------------------------------------------------ venv
def requirement_files(ws: Workspace) -> list[Path]:
    files = []
    if (ws.xdmod / "requirements.txt").is_file():
        files.append(ws.xdmod / "requirements.txt")
    for r in ws.framework_repos:
        f = r.path / "requirements.txt"
        if f.is_file() and f.resolve() not in {x.resolve() for x in files}:
            files.append(f)
    return files


def requirements_hash(files: list[Path]) -> str:
    h = hashlib.sha256()
    for f in files:
        h.update(str(f).encode() + b"\0" + f.read_bytes())
    return h.hexdigest()


def state_file(ws: Workspace) -> Path:
    return ws.state / "state.json"


def load_state(ws: Workspace) -> dict:
    p = state_file(ws)
    return json.loads(p.read_text()) if p.exists() else {}


def save_state(ws: Workspace, st: dict) -> None:
    ws.state.mkdir(parents=True, exist_ok=True)
    state_file(ws).write_text(json.dumps(st, indent=2, sort_keys=True) + "\n")


def install_requirements(ws: Workspace, force: bool = False) -> None:
    files = requirement_files(ws)
    st = load_state(ws)
    h = requirements_hash(files)
    if not force and st.get("requirements_hash") == h:
        say("  pip: requirements unchanged")
        return
    py = ws.venv / "bin" / "python"
    args = []
    for f in files:
        args += ["-r", str(f)]
    if shutil.which("uv"):
        cmd = ["uv", "pip", "install", "-q", "-p", str(py), *args]
    else:
        cmd = [str(py), "-m", "pip", "install", "-q", *args]
    say(f"  pip: installing {', '.join(ws.rel(f) for f in files)}")
    if limits.run(cmd, "install", ws).returncode:
        raise SetupError("installing the pip requirements failed")
    st["requirements_hash"] = h
    save_state(ws, st)


# ------------------------------------------------------------------ CLAUDE.md and .claude (D69, D113)
def copy_launch_claude(ws: Workspace) -> None:
    src = ws.xdmod / "launch" / "CLAUDE.md"
    dst = ws.root / "CLAUDE.md"
    if not src.exists():
        return
    if dst.exists() and dst.read_text() == src.read_text():
        return
    if dst.exists() and not dst.is_symlink():
        shutil.copyfile(dst, ws.state / "CLAUDE.md.previous")
        say(f"  kept the previous CLAUDE.md as {ws.rel(ws.state / 'CLAUDE.md.previous')}")
    shutil.copyfile(src, dst)
    say("  copied xdmod/launch/CLAUDE.md -> CLAUDE.md")


def repo_prefix(name: str) -> str:
    """Short prefix of a repo's skills and commands in .claude/: `xd` for xdmod, else the part after
    the project prefix (`<project>-ee` -> `ee`, `<project>-manifest` -> `manifest`). Project names
    have no dash of their own (repo-layouts.md: `<project>-<domain>`)."""
    return "xd" if name == "xdmod" else name.split("-", 1)[-1]


def assemble_claude(ws: Workspace) -> list[str]:
    """<ws>/.claude/{skills,commands}/<prefix>-<name> -> <repo>/claude/{skills,commands}/<name>.
    Only links curatrix made (pointing into a repo's claude/ folder) are replaced or removed."""
    made = []
    for kind in ("skills", "commands"):
        tdir = ws.root / ".claude" / kind
        tdir.mkdir(parents=True, exist_ok=True)
        wanted: dict[str, Path] = {}
        for r in [x for x in ws.repos if x.is_framework_repo]:
            src = r.path / "claude" / kind
            if not src.is_dir():
                continue
            for item in sorted(src.iterdir()):
                if item.name.startswith(".") or item.name == "README.md":
                    continue
                wanted[f"{repo_prefix(r.name)}-{item.name}"] = item
        for link in tdir.iterdir():
            if link.is_symlink():
                tgt = os.readlink(link)
                if "/claude/" in tgt and link.name not in wanted:
                    link.unlink()
        for name, src in wanted.items():
            link = tdir / name
            rel = os.path.relpath(src, tdir)
            if link.is_symlink() and os.readlink(link) == rel:
                continue
            if link.exists() and not link.is_symlink():
                say(f"  warning: {ws.rel(link)} is not a link; left alone")
                continue
            if link.is_symlink():
                link.unlink()
            link.symlink_to(rel)
            made.append(ws.rel(link))
    return made


# ------------------------------------------------------------------ hooks and diff drivers (D100, D63)
def hook_text(ws: Workspace) -> str:
    return (f"#!/bin/sh\n{HOOK_MARK}: normalizers, ID placeholders, fast checks.\n"
            f'exec "{ws.venv / "bin" / "curatrix"}" hook pre-commit "$@"\n')


def repo_hooks_dir(repo: Path, ws: Workspace | None = None) -> Path:
    """The repo's own hooks folder (<git common dir>/hooks). Never a configured core.hooksPath,
    which may be user-global and shared by every repo on the machine."""
    gd = Path(git(["rev-parse", "--git-common-dir"], repo, ws).stdout.strip())
    return (gd if gd.is_absolute() else repo / gd) / "hooks"


def install_hooks(ws: Workspace) -> list[str]:
    done = []
    for r in ws.framework_repos:
        gd = r.path / ".git"
        if not gd.exists():
            continue
        hooks = repo_hooks_dir(r.path, ws)
        hooks.mkdir(parents=True, exist_ok=True)
        hp = git(["config", "core.hooksPath"], r.path, ws, check=False).stdout.strip()
        if hp:
            say(f"  note: {r.name}: core.hooksPath is set ({hp}); the hook is in {ws.rel(hooks)}, "
                f"so that hooks path must call the repo's own hook")
        h = hooks / "pre-commit"
        if h.exists() and HOOK_MARK not in h.read_text():
            say(f"  warning: {ws.rel(h)} exists and is not ours; left alone")
        else:
            h.write_text(hook_text(ws))
            h.chmod(0o755)
        # FreeCAD textconv (D63, D100): git does not take driver settings from the repo
        git(["config", "diff.fcstd.textconv", f"{ws.venv / 'bin' / 'curatrix'} gen freecad-json --textconv"], r.path, ws)
        git(["config", "diff.fcstd.cachetextconv", "true"], r.path, ws)
        done.append(r.name)
    return done


# ------------------------------------------------------------------ .xdmod (workspace-local state)
FREECAD_USER_CFG = """<?xml version="1.0" encoding="UTF-8" standalone="no" ?>
<FCParameters>
  <FCParamGroup Name="Root">
    <FCParamGroup Name="BaseApp">
      <FCParamGroup Name="Preferences">
        <FCParamGroup Name="Document">
          <FCInt Name="CompressionLevel" Value="0"/>
          <FCBool Name="CreateBackupFiles" Value="0"/>
        </FCParamGroup>
      </FCParamGroup>
    </FCParamGroup>
  </FCParamGroup>
</FCParameters>
"""
KICAD_TABLE = "({kind}\n  (version 7)\n)\n"


def freecad_dirs(ws: Workspace) -> dict[str, Path]:
    b = ws.state / "freecad"
    return {"XDG_CONFIG_HOME": b / "config", "XDG_DATA_HOME": b / "data", "XDG_CACHE_HOME": b / "cache"}


def ensure_freecad_config(ws: Workspace) -> Path:
    """FreeCAD 1.1 reads its user config from $XDG_CONFIG_HOME/FreeCAD/v1-1/user.cfg (verified with
    1.1.4); the launcher points XDG_* into <ws>/.xdmod/freecad and keeps CompressionLevel = 0 (D63) and
    CreateBackupFiles = false (no .FCBak files, FreeCAD spike)."""
    d = freecad_dirs(ws)
    for p in d.values():
        p.mkdir(parents=True, exist_ok=True)
    cfg = d["XDG_CONFIG_HOME"] / "FreeCAD" / "v1-1" / "user.cfg"
    cfg.parent.mkdir(parents=True, exist_ok=True)
    if not cfg.exists():
        cfg.write_text(FREECAD_USER_CFG)
        return cfg
    tree = ET.parse(cfg)
    root = tree.getroot()

    def group(parent, name):
        for g in parent.findall("FCParamGroup"):
            if g.get("Name") == name:
                return g
        return ET.SubElement(parent, "FCParamGroup", {"Name": name})
    g = root
    for name in ("Root", "BaseApp", "Preferences", "Document"):
        g = group(g, name)
    changed = False
    # uncompressed saves (D63); no <name>.<time>.FCBak next to every saved file (FreeCAD spike)
    for tag, name in (("FCInt", "CompressionLevel"), ("FCBool", "CreateBackupFiles")):
        el = next((i for i in g.findall(tag) if i.get("Name") == name), None)
        if el is None:
            ET.SubElement(g, tag, {"Name": name, "Value": "0"})
            changed = True
        elif el.get("Value") != "0":
            el.set("Value", "0")
            changed = True
    if changed:
        tree.write(cfg, encoding="UTF-8", xml_declaration=True)
    return cfg


def ensure_kicad_config(ws: Workspace) -> Path:
    """KICAD_CONFIG_HOME=<ws>/.xdmod/kicad with empty global library tables, so KiCad uses no
    user-global libraries and does not ask on first start (D88)."""
    base = ws.state / "kicad"
    for ver in ("10.0",):
        d = base / ver
        d.mkdir(parents=True, exist_ok=True)
        for f, kind in (("sym-lib-table", "sym_lib_table"), ("fp-lib-table", "fp_lib_table")):
            if not (d / f).exists():
                (d / f).write_text(KICAD_TABLE.format(kind=kind))
    return base


def create_state(ws: Workspace) -> None:
    for d in ("kicad", "freecad", "drawio", "cache"):
        (ws.state / d).mkdir(parents=True, exist_ok=True)
    ensure_kicad_config(ws)
    ensure_freecad_config(ws)
    readme = ws.state / "README"
    if not readme.exists():
        readme.write_text("Workspace-local state of curatrix (command-layer.md §5): tool configs for KiCad,\n"
                          "FreeCAD and drawio, caches, and limits.yaml overrides. Not a repo; not shared.\n")


# ------------------------------------------------------------------ launchers (§4)
def launch_env(ws: Workspace, tool: str) -> dict[str, str]:
    env = ws.run_env()
    if tool == "kicad":
        env["KICAD_CONFIG_HOME"] = str(ensure_kicad_config(ws))
        # KiCad 10 also writes ~/.cache/kicad (3D models) and ~/.local/share/kicad (documents,
        # plugins) unless these are set (KiCad spike, task 5.12)
        for var, sub in (("KICAD_CACHE_HOME", "kicad-cache"), ("KICAD_DOCUMENTS_HOME", "kicad-documents")):
            (ws.state / sub).mkdir(parents=True, exist_ok=True)
            env[var] = str(ws.state / sub)
        for k, sub in (("SYMBOL_DIR", "XD_KICAD_SYMBOLS"), ("FOOTPRINT_DIR", "XD_KICAD_FOOTPRINTS"),
                       ("3DMODEL_DIR", "XD_KICAD_3DMODELS"), ("TEMPLATE_DIR", "XD_KICAD_TEMPLATES")):
            env[f"KICAD10_{k}"] = env[sub]
    elif tool == "freecad":
        ensure_freecad_config(ws)
        env.update({k: str(v) for k, v in freecad_dirs(ws).items()})
    elif tool == "blender":
        env.update(blender.env(ws))
    return env


# ------------------------------------------------------------------ tool shims
# A bare `kicad-cli --version` rewrites ~/.config/kicad/10.0/kicad_common.json (XD-ADR-0145, after
# two agent runs did it). So bootstrap/update write shims with the KiCad and FreeCAD program names
# into .venv/bin, which `curatrix env` puts first on PATH: each sets the workspace-local config that
# `curatrix run` sets (limits.tool_env) and execs the real binary by its absolute path.
KICAD_PROGRAMS = ("kicad-cli", "kicad", "eeschema", "pcbnew", "bitmap2component")
FREECAD_PREFIX = "freecad"           # FreeCAD, FreeCADCmd, freecad, freecadcmd, freecad-thumbnailer, ...
BLENDER = "blender"                  # also gets --factory-startup etc. (blender.ARGS)
SHIM_MARK = "# curatrix tool shim"
WORKTREE_MARKER = ".xdmod-worktree.json"     # work.MARKER (work imports setup)


def main_workspace(ws: Workspace) -> Workspace:
    """A worktree set links the main workspace's .venv, so its shims belong to the main workspace:
    shims written with a set's paths would point into a folder that `curatrix work done` removes."""
    m = ws.root / WORKTREE_MARKER
    if m.is_file():
        main = json.loads(m.read_text()).get("main_workspace")
        if main:
            return Workspace(Path(main))
    return ws


def shim_dir(ws: Workspace) -> Path:
    return ws.venv / "bin"


def is_shim(p: Path) -> bool:
    try:
        with open(p, "rb") as f:
            return SHIM_MARK.encode() in f.read(512)
    except OSError:
        return False


def shim_real(p: Path) -> Path | None:
    """The real binary a shim execs (its `exec` line)."""
    import shlex
    try:
        for line in p.read_text().splitlines():
            if line.startswith("exec "):
                return Path(shlex.split(line)[1])
    except (OSError, ValueError, IndexError):
        pass
    return None


def _path_dirs(ws: Workspace, path: str | None) -> list[Path]:
    """PATH without .venv/bin (also reached through a symlink)."""
    skip = shim_dir(ws).resolve()
    out = []
    for d in (path if path is not None else os.environ.get("PATH", "")).split(os.pathsep):
        if not d:
            continue
        try:
            if Path(d).resolve() == skip:
                continue
        except OSError:
            continue
        out.append(Path(d))
    return out


def _runnable(p: Path) -> bool:
    return p.is_file() and os.access(p, os.X_OK)


def real_tool(ws: Workspace, name: str, path: str | None = None) -> Path | None:
    """The first `name` on PATH that is neither in .venv/bin nor a shim (of any workspace), so a
    shim never execs itself or another shim."""
    for d in _path_dirs(ws, path):
        p = d / name
        if _runnable(p) and not is_shim(p):
            return p.absolute()
    return None


def shim_names(ws: Workspace, path: str | None = None) -> list[str]:
    """The KiCad and FreeCAD programs on this machine, derived from the install folders: next to
    each KiCad program, every `_<name>.kiface` with a `<name>` program (gerbview, pl_editor,
    pcb_calculator, ...); next to each FreeCAD program, every program named freecad* (any case)."""
    names: dict[str, None] = {}
    for d in _path_dirs(ws, path):
        try:
            entries = sorted(d.iterdir())
        except OSError:
            continue
        files = {e.name for e in entries}
        if any(n in files for n in KICAD_PROGRAMS):
            for n in KICAD_PROGRAMS:
                if n in files:
                    names[n] = None
            for f in sorted(files):
                if f.startswith("_") and f.endswith(".kiface") and f[1:-7] in files:
                    names[f[1:-7]] = None
        for f in sorted(files):
            if f.lower().startswith(FREECAD_PREFIX):
                names[f] = None
        if BLENDER in files:
            names[BLENDER] = None
    return [n for n in names if real_tool(ws, n, path)]


def shim_env(ws: Workspace, name: str) -> dict[str, str]:
    """The variables `curatrix run -- <name>` adds for this tool (KICAD*, XDG_*), and LC_ALL only
    for the batch tool kicad-cli: the GUI programs keep the user's locale."""
    env = limits.tool_env(ws, "script", {}, [name])
    if name != "kicad-cli":
        env.pop("LC_ALL", None)
    return dict(sorted(env.items()))


def shim_text(ws: Workspace, name: str, real: Path) -> str:
    import shlex
    q = shlex.quote(str(real))
    lines = ["#!/bin/sh",
             f"{SHIM_MARK} (written by `curatrix bootstrap` / `update`; do not edit)",
             f"# workspace: {ws.root}",
             f"# Runs {real} with the workspace-local config, never ~/.config, ~/.cache or ~/.local.",
             "# It sets no limits: run tools through `curatrix run` (rule 2)."]
    lines += [f"export {k}={shlex.quote(v)}" for k, v in shim_env(ws, name).items()]
    if name == BLENDER:
        lines.append("unset " + " ".join(blender.UNSET))
        # without any .venv/bin (also a worktree set's link to it): Blender's Python would take the venv
        lines.append("PATH=$(printf %s \"$PATH\" | tr : '\\n' | grep -v '/\\.venv/bin/*$' | paste -sd: -); export PATH")
    lines.append(f"[ -x {q} ] || {{ echo {shlex.quote(f'{name}: {real} is gone; run curatrix update')} >&2; exit 127; }}")
    extra = "".join(f" {a}" for a in blender.ARGS) if name == BLENDER else ""
    lines.append(f'exec {q}{extra} "$@"')
    return "\n".join(lines) + "\n"


def write_shims(ws: Workspace, path: str | None = None) -> list[str]:
    """Write a shim for each KiCad/FreeCAD program found on PATH (shim_names) and remove our shims
    of programs that are gone. Always for the main workspace, also when called from a worktree set.
    Touches only <ws>/.venv/bin. Returns the names with a shim."""
    ws = main_workspace(ws)
    d = shim_dir(ws)
    d.mkdir(parents=True, exist_ok=True)
    made = []
    for name in shim_names(ws, path):
        p = d / name
        if os.path.lexists(p) and not is_shim(p):
            say(f"  {p} exists and is not a curatrix shim: left alone")
            continue
        text = shim_text(ws, name, real_tool(ws, name, path))
        if not p.exists() or p.read_text() != text:
            p.write_text(text)
        p.chmod(0o755)
        made.append(name)
    for p in sorted(d.iterdir()):
        if p.name not in made and not p.is_symlink() and is_shim(p):
            p.unlink()
    return made


def shim_rows(ws: Workspace, path: str | None = None) -> list[tuple[str, str, str]]:
    """Doctor rows: a KiCad/FreeCAD name found first on PATH that is not this workspace's shim
    would write ~/.config when called bare; a shim whose real binary is gone fails."""
    rows = []
    path = path if path is not None else os.environ.get("PATH", "")
    d = shim_dir(ws)
    mine = d.resolve()
    shims = sorted(p.name for p in d.iterdir() if not p.is_symlink() and is_shim(p)) if d.is_dir() else []
    for name in shims:
        real = shim_real(d / name)
        if real is None or not _runnable(real):
            rows.append(("warn", f"stale shim .venv/bin/{name}: {real} is gone", "curatrix update"))
    seen = False
    for name in dict.fromkeys([*shim_names(ws, path), *shims]):
        found = shutil.which(name, path=path)
        if not found:
            continue
        seen = True
        fp = Path(found)
        if fp.parent.resolve() == mine and is_shim(fp):
            continue
        own = d / name
        if os.path.lexists(own) and not is_shim(own):
            fix = f"remove or rename .venv/bin/{name}, then curatrix update"
        elif is_shim(own):
            fix = 'eval "$(curatrix env)"'
        else:
            fix = "curatrix update"
        rows.append(("warn", f"{name} on PATH is {found}, not the workspace shim",
                     f"a bare call writes ~/.config; {fix}"))
    if seen and not rows:
        rows.append(("ok", "KiCad/FreeCAD shims first on PATH", ".venv/bin"))
    return rows


def launch(ws: Workspace, tool: str, args: list[str]) -> int:
    """GUI tools: memory limit only, no timeout (D117). Runs from the workspace root (D67)."""
    exe = {"kicad": "kicad", "freecad": "FreeCAD", "blender": "blender", "drawio": "drawio", "claude": "claude"}[tool]
    if tool == "kicad" and args and args[0].endswith(".kicad_sch"):
        exe = "eeschema"
    if tool == "drawio":
        (ws.state / "drawio").mkdir(parents=True, exist_ok=True)
        args = [f"--user-data-dir={ws.state / 'drawio'}", *args]
    if not shutil.which(exe):
        raise SetupError(f"{exe} not found on PATH")
    if tool == "blender":
        args = [*blender.ARGS, *args]
    if tool in ("kicad", "freecad", "blender"):
        # the real binary, not the shim: launch_env is already the workspace config, and the
        # shim's batch LC_ALL would switch the GUI's language
        exe = str(real_tool(ws, exe) or exe)
    env = launch_env(ws, tool)
    use = "claude" if tool == "claude" else "gui"
    lim = limits.resolve(use, ws)
    say(f"curatrix launch {tool}: {limits.describe(lim)}")
    return limits.norm_rc(subprocess.run(limits.wrap([exe, *args], lim), cwd=ws.root, env=env).returncode)


# ------------------------------------------------------------------ doctor (§5, 4.4b)
def kicad_models_row(ws: Workspace, role: str | None, ci: bool = False) -> tuple[str, str, str] | None:
    """A doctor warning when a role that should have the KiCad 3D models (group kicad-3d) lacks
    them: STEP exports and renderings then show bare boards. Roles that leave them out on purpose
    (ee, me, integration, CI) get no warning."""
    if ci or "+kicad-3d" not in ROLES.get(role or "", []):
        return None
    if (ws.root / "libs" / "kicad" / "packages3D").is_dir():
        return None
    return ("warn", "KiCad 3D models (libs/kicad/packages3D) missing", "west update; STEP and renderings show bare boards")



def doctor(ws: Workspace, quiet: bool = False, ci: bool = False) -> int:
    """Exit 1 on any FAIL. `ci`: on a CI runner the system tools come from the runner image, not
    from the pinned local toolchain (D19), so their mismatches are warnings; tools.yaml tools
    (installed by curatrix with sha256) must still match."""
    rows: list[tuple[str, str, str]] = []   # (status, what, detail/fix)

    def add(st, what, detail=""):
        rows.append((st, what, detail))

    add("ok" if sys.version_info >= (3, 12) else "FAIL", f"python {sys.version.split()[0]}", "needs >= 3.12")
    add("ok" if ws.venv.is_dir() else "FAIL", "workspace .venv", "" if ws.venv.is_dir() else "run bootstrap.sh")
    add("ok" if ws.has_west else "warn", "west workspace (.west/)", "" if ws.has_west else "not initialized (west init -l <manifest>)")
    role = ws.role
    add("ok" if role else "warn", f"role: {role or '(none)'}", "" if role else "curatrix bootstrap --role <role>")
    try:
        ts = tools.for_role(tools.load_all(ws), role)
    except tools.ToolsError as e:
        add("FAIL", "tools.yaml", str(e))
        ts = tools.ToolSet()
    for t in ts.tools.values():
        s = tools.stamp_of(ws, t.name)
        if tools.installed_ok(ws, t):
            add("ok", f"{t.name} {t.version}", f".venv/{t.location}")
        elif s and s.get("version") != t.version:
            add("FAIL", f"{t.name}: installed {s.get('version')}, tools.yaml wants {t.version}", "curatrix update")
        else:
            add("FAIL", f"{t.name} {t.version} not installed", "curatrix update (or `curatrix update --adopt`)")
    for st in ts.system.values():
        have = tools.system_version(st, ws)
        if have is None and not st.pinned:
            add("note", f"{st.name} missing", f"optional, not pinnable; tried with {st.version}")
        elif have is None:
            add("warn" if st.optional or ci else "FAIL", f"{st.name} missing", f"system tool, wants {st.version}")
        elif not tools.version_ok(st.version, have):
            add("warn" if ci or not st.pinned else "FAIL", f"{st.name} {have}: tools.yaml wants {st.version}",
                "not pinnable: local output only" if not st.pinned else "runner image (--ci)" if ci else st.source)
        else:
            add("ok", f"{st.name} {have}")
    row = kicad_models_row(ws, role, ci)
    if row:
        add(*row)
    for row in shim_rows(ws):
        add(*row)
    lim_backend = limits.backend()
    add("ok" if lim_backend == "systemd" else "warn", f"limits backend: {lim_backend}",
        "" if lim_backend == "systemd" else "no systemd user session: timeout + ulimit -v fallback")
    if (ws.root / "zephyr").is_dir():
        add("ok", "ZEPHYR_BASE", "zephyr/")
    else:
        add("warn", "zephyr/ missing", "docs builds need Zephyr (west update)")
    zd = ws.root / "tools" / "zdocs"
    add("ok" if zd.is_dir() else "warn", "tools/zdocs", "" if zd.is_dir() else "docs builds need zdocs (west update)")
    cm = ws.root / "CLAUDE.md"
    src = ws.xdmod / "launch" / "CLAUDE.md"
    if src.exists():
        add("ok" if cm.exists() and cm.read_text() == src.read_text() else "warn", "CLAUDE.md (launch copy)",
            "" if cm.exists() and cm.read_text() == src.read_text() else "curatrix update")
    add("ok" if ws.state.is_dir() else "warn", ".xdmod/ state", "" if ws.state.is_dir() else "curatrix bootstrap")
    for r in ws.framework_repos:
        if not (r.path / ".git").exists():
            continue
        try:
            hooks = repo_hooks_dir(r.path, ws)
            ok = (hooks / "pre-commit").exists() and HOOK_MARK in (hooks / "pre-commit").read_text()
        except SetupError:
            ok = False
        add("ok" if ok else "warn", f"{r.name}: pre-commit hook", "" if ok else "curatrix update")
    fails = sum(1 for s, _, _ in rows if s == "FAIL")
    if not quiet:
        for s, what, detail in rows:
            say(f"  {s:4} {what}" + (f"   ({detail})" if detail else ""))
        say(f"doctor: {'OK' if not fails else f'{fails} problem(s)'}")
    return 1 if fails else 0


# ------------------------------------------------------------------ bootstrap / update
def refresh(ws: Workspace, adopt: bool = False, force_pip: bool = False) -> None:
    say("== venv and tools (D19)")
    install_requirements(ws, force=force_pip)
    tools.install_all(ws, ws.role, say, adopt=adopt)
    say("== launch CLAUDE.md and .claude/ (D69, D113)")
    copy_launch_claude(ws)
    made = assemble_claude(ws)
    say(f"  .claude links: {len(made)} new")
    say("== git hooks and diff drivers (D100)")
    say(f"  installed in: {', '.join(install_hooks(ws)) or '(no repos)'}")
    say("== workspace state (.xdmod/)")
    create_state(ws)
    say("== KiCad/FreeCAD/Blender shims in .venv/bin (workspace-local config)")
    say(f"  shims: {', '.join(write_shims(ws)) or '(no KiCad, FreeCAD or Blender found)'}")


def bootstrap(ws: Workspace, role: str, adopt: bool = False, skip_west: bool = False, run_doctor: bool = True) -> int:
    if not skip_west:
        say(f"== role {role}: group filter {','.join(ROLES.get(role, [])) or '(manifest default)'}")
        set_role(ws, role)
        if west(ws, "update"):
            raise SetupError("west update failed")
        ws.__dict__.pop("repos", None)
    refresh(ws, adopt=adopt)
    if not run_doctor:
        return 0
    say("== doctor")
    return doctor(ws)


def update(ws: Workspace, adopt: bool = False) -> int:
    if ws.has_west:
        role = ws.role
        if role in ROLES:            # a role's groups may change (task 5.14: me and sw get +ee)
            say(f"== role {role}: group filter {','.join(ROLES[role]) or '(manifest default)'}")
            set_role(ws, role)
        if west(ws, "update", "-k"):
            raise SetupError("west update -k failed")
        ws.__dict__.pop("repos", None)
    refresh(ws, adopt=adopt)
    return doctor(ws, quiet=True)
