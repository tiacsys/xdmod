"""The workspace: root discovery, repos, paths (command-layer.md §1, §5; repo-topology.md §2).

The workspace root is the west topdir (D67, D68). curatrix finds it itself, so commands also
work from a subfolder:

1. ``$XD_WORKSPACE`` if set;
2. inside a worktree set (D125): the set root on the logical ``$PWD``, also from a symlinked
   folder of the set (``.worktrees/<branch>/zephyr``);
3. the nearest folder upward from the current directory that holds ``.west/``;
4. the folder above the xdmod checkout this package was installed from (editable install,
   ``<ws>/xdmod/curatrix/src/curatrix``). This keeps curatrix usable before ``west init``.
"""
from __future__ import annotations

import configparser
import functools
import os
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

PKG_DIR = Path(__file__).resolve().parent
CURATRIX_DIR = PKG_DIR.parents[1]          # xdmod/curatrix
XDMOD_DIR = CURATRIX_DIR.parent            # xdmod


class WorkspaceError(Exception):
    pass


@dataclass
class Repo:
    """A west project (or a top-level folder, before west init)."""

    name: str
    path: Path            # absolute
    rel: str              # relative to the workspace root
    sha: str = ""
    groups: list[str] = field(default_factory=list)

    @property
    def checks_file(self) -> Path:
        return self.path / "checks.yaml"

    @property
    def is_framework_repo(self) -> bool:
        """A repo that uses XDMOD (has a checks.yaml) or is xdmod itself."""
        return is_framework_path(self.path, self.name)


def is_framework_path(path: Path, name: str) -> bool:
    """A west project that uses XDMOD (a checks.yaml at its top) or is xdmod itself. XDMOD never
    knows the example project's repo names (D66, D111, P4-16)."""
    return (Path(path) / "checks.yaml").is_file() or name == "xdmod"


def find_root(start: Path | None = None) -> Path:
    env = os.environ.get("XD_WORKSPACE")
    if env:
        return Path(env).resolve()
    here = (start or Path.cwd()).resolve()
    if start is None:
        # In a worktree set (D125) shared folders are symlinks to the main checkout, so the
        # physical cwd of e.g. `.worktrees/b/zephyr` is the main zephyr. The logical $PWD still
        # says which set we are in: prefer the set root on it.
        lp = os.environ.get("PWD")
        if lp and os.path.isabs(lp) and Path(lp).resolve() == here:
            for p in (Path(lp), *Path(lp).parents):
                if (p / ".xdmod-worktree.json").is_file() and (p / ".west").is_dir():
                    return p.resolve()
    for p in (here, *here.parents):
        if (p / ".west").is_dir():
            return p
    if (XDMOD_DIR / "curatrix").is_dir():
        return XDMOD_DIR.parent
    raise WorkspaceError("not inside an XDMOD workspace (no .west/ found and XD_WORKSPACE unset)")


class Workspace:
    def __init__(self, root: Path | None = None):
        self.root = (root or find_root()).resolve()

    # ---------------------------------------------------------------- paths
    @property
    def venv(self) -> Path:
        return self.root / ".venv"

    @property
    def opt(self) -> Path:
        return self.venv / "opt"

    @property
    def state(self) -> Path:
        """<ws>/.xdmod: workspace-local configs, caches and limit overrides (not a repo)."""
        return self.root / ".xdmod"

    @property
    def xdmod(self) -> Path:
        p = self.root / "xdmod"
        return p if p.is_dir() else XDMOD_DIR

    def build(self, area: str) -> Path:
        """<ws>/build/<area>/ (D46). <area> = repo name, `full`, a branch, or a named step."""
        return self.root / "build" / area

    def rel(self, p: Path | str) -> str:
        p = Path(p).resolve()
        try:
            return str(p.relative_to(self.root))
        except ValueError:
            return str(p)

    @property
    def has_west(self) -> bool:
        return (self.root / ".west").is_dir()

    # ---------------------------------------------------------------- west
    def west_config(self) -> configparser.ConfigParser:
        cp = configparser.ConfigParser()
        cp.read(self.root / ".west" / "config")
        return cp

    @property
    def role(self) -> str | None:
        cp = self.west_config()
        return cp.get("xdmod", "role", fallback=None)

    @property
    def manifest_path(self) -> Path | None:
        cp = self.west_config()
        p = cp.get("manifest", "path", fallback=None)
        return self.root / p if p else None

    def west(self) -> list[str]:
        w = self.venv / "bin" / "west"
        return [str(w)] if w.exists() else ["west"]

    @functools.cached_property
    def repos(self) -> list[Repo]:
        """Active projects. With west: `west list` (active only, manifest repo included).
        Without west: every top-level folder that has a checks.yaml, plus xdmod."""
        if self.has_west:
            try:
                out = subprocess.run(
                    [*self.west(), "list", "-f", "{name}|{path}|{sha}|{groups}"],
                    cwd=self.root, capture_output=True, text=True, check=True, timeout=120,
                ).stdout
                repos = []
                for line in out.splitlines():
                    name, path, sha, groups = (line.split("|") + ["", "", "", ""])[:4]
                    if name == "manifest":
                        mp = self.manifest_path
                        if mp is None:
                            continue
                        name, path = mp.name, self.rel(mp)
                    repos.append(Repo(name, self.root / path, path, sha if sha != "N/A" else "",
                                      [g for g in groups.split(",") if g]))
                return repos
            except (subprocess.SubprocessError, OSError) as e:
                # not silent (P4-4): the folder scan below has no SHAs, which CK-B6 then reports
                print(f"curatrix: warning: `west list` failed ({e}); using a folder scan without pinned SHAs",
                      file=sys.stderr)
        repos = []
        for d in sorted(self.root.iterdir()):
            if d.is_dir() and not d.name.startswith(".") and ((d / "checks.yaml").is_file() or d.name == "xdmod"):
                repos.append(Repo(d.name, d, d.name))
        return repos

    def repo(self, name: str) -> Repo:
        """A repo by west name, path, or `.` / a path inside it."""
        for r in self.repos:
            if name in (r.name, r.rel):
                return r
        p = Path(name).resolve()
        for r in self.repos:
            if p == r.path or r.path in p.parents:
                return r
        if (self.root / name).is_dir():
            d = self.root / name
            return Repo(d.name, d, self.rel(d))
        raise WorkspaceError(f"unknown repo {name!r} (active: {', '.join(r.name for r in self.repos)})")

    def repo_of_cwd(self) -> Repo | None:
        cwd = Path.cwd().resolve()
        for r in self.repos:
            if cwd == r.path or r.path in cwd.parents:
                return r
        return None

    @property
    def framework_repos(self) -> list[Repo]:
        return [r for r in self.repos if r.is_framework_repo]

    # ---------------------------------------------------------------- environment (curatrix env)
    def env(self) -> dict[str, str]:
        """Workspace environment (command-layer.md §5). Values only; PATH is prepended."""
        from curatrix import tools  # local import: tools imports ws

        e: dict[str, str] = {
            "XD_WORKSPACE": str(self.root),
            "PYTHONDONTWRITEBYTECODE": "1",
            "VIRTUAL_ENV": str(self.venv),
        }
        zephyr = self.root / "zephyr"
        if zephyr.is_dir():
            e["ZEPHYR_BASE"] = str(zephyr)
        jdk = self.opt / "jdk"
        if jdk.is_dir():
            e["JAVA_HOME"] = str(jdk)
        libs = self.root / "libs"
        e["XD_KICAD_SYMBOLS"] = str(libs / "kicad" / "symbols")
        e["XD_KICAD_FOOTPRINTS"] = str(libs / "kicad" / "footprints")
        e["XD_KICAD_3DMODELS"] = str(libs / "kicad" / "packages3D")
        e["XD_KICAD_TEMPLATES"] = str(libs / "kicad" / "templates")
        # output folder of a KiCad jobset from the template (task 5.17; D46: output only under build/);
        # `curatrix cam` (task 5.20) sets its own per run
        e["XD_CAM_OUT"] = os.environ.get("XD_CAM_OUT") or str(self.root / "build" / "cam")
        e["XD_FREECAD_PARTS"] = str(libs / "freecad")
        e["XD_SYSMOD_LIB"] = str(libs / "sysmod-sysmlv2")
        e["XD_PLEML_LIB"] = str(libs / "pleml")
        # tool-specific variables from tools.yaml (`env:` of each tool), e.g. ZEPHYR_SDK_INSTALL_DIR
        try:
            for t in tools.load_all(self).tools.values():
                for k, v in (t.env or {}).items():
                    e[k] = v.replace("{location}", str(self.venv / t.location)).replace("{venv}", str(self.venv))
        except Exception:  # noqa: BLE001 - env must work even with a broken tools.yaml
            pass
        path_parts = [str(self.venv / "bin")]
        if (self.opt / "node" / "node_modules" / ".bin").is_dir():
            path_parts.append(str(self.opt / "node" / "node_modules" / ".bin"))
        e["PATH"] = os.pathsep.join(path_parts)
        return e

    def run_env(self, extra: dict[str, str] | None = None) -> dict[str, str]:
        """os.environ + the workspace env (PATH prepended)."""
        env = dict(os.environ)
        we = self.env()
        path = we.pop("PATH")
        env.update(we)
        env["PATH"] = path + os.pathsep + env.get("PATH", "")
        if extra:
            env.update(extra)
        return env
