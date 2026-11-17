"""tools.yaml: pinned non-pip tools, their installer, and the version checks of `doctor` (D19).

Every repo (xdmod included) may have a ``tools.yaml`` at its root. curatrix merges the files of
all active repos; one tool name with two different versions is an error. Format (see
``xdmod/curatrix/README.md``)::

    tools:                      # installed into <ws>/.venv/<location> with sha256 checks
      - name: jdk
        version: "21.0.13+9"
        kind: tarball           # tarball | zip | conda | file | npm | git
        url: https://...
        sha256: d7f5...         # required for every kind except npm and git
        commit: 3db9...         # git only, instead of sha256: the full commit hash (40 hex digits)
        location: opt/jdk       # relative to <ws>/.venv; `.xdmod/...` = relative to the workspace root
        strip: 1                # tarball: leading path components to drop (default 1)
        subdir: share/...       # tarball / zip / conda / git: copy only this folder
        licence: MIT            # optional: the licence, and any gap in it (shown by `doctor`)
        links: {jshell: bin/jshell}   # symlinks <ws>/.venv/bin/<name> -> <location>/<path>
        env: {JAVA_HOME: "{location}"}  # exported by `curatrix env`
        roles: [sw]             # optional: install only for these roles
    system:                     # used from the machine (D19); `doctor` fails on a mismatch
      - name: kicad-cli
        version: "10.0.8"       # exact; "any"; a prefix wildcard like "10.0.*"; or a minimum ">=10.0"
        cmd: [kicad-cli, --version]   # default [<name>, --version]
        regex: '(\\d+\\.\\d+\\.\\d+)'  # default: the first x.y[.z] in the output
        optional: true          # missing = warning (a wrong version is still an error)
        roles: [ee]

An installed tool leaves a stamp ``<ws>/.venv/opt/.xd-stamps/<name>.json`` with name, version,
sha256 (or commit). `doctor` compares the stamps with tools.yaml.

``kind: git`` pins by commit, which is content-addressed: curatrix fetches exactly that commit into
a bare cache repo (``<ws>/.xdmod/cache/git/<name>.git``), checks that the fetched object is that
commit, and extracts its tree (``git archive``) into the location. No checkout, no remote in the
location. A location that is already a git checkout at the pinned commit (made by hand before the
tool was curated) is adopted and stamped, not replaced.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from curatrix import limits
from curatrix.ws import Workspace

KINDS = ("tarball", "zip", "conda", "file", "npm", "git")
STATE_PREFIX = ".xdmod/"       # a location under the workspace state instead of .venv
_VERSION = re.compile(r"(\d+\.\d+(?:\.\d+)?)")


class ToolsError(Exception):
    pass


@dataclass
class Tool:
    name: str
    version: str
    kind: str
    location: str
    url: str = ""
    sha256: str = ""
    strip: int = 1
    subdir: str = ""
    package: str = ""
    commit: str = ""          # kind git: the pinned commit (instead of sha256)
    licence: str = ""         # the licence and any gap in it (doctor shows it)
    links: dict = field(default_factory=dict)
    env: dict = field(default_factory=dict)
    roles: list = field(default_factory=list)
    source: str = ""          # which tools.yaml

    def __post_init__(self):
        if self.kind not in KINDS:
            raise ToolsError(f"{self.source}: tool {self.name}: kind must be one of {KINDS}")
        if self.kind == "git":
            if not re.fullmatch(r"[0-9a-f]{40}", self.commit or ""):
                raise ToolsError(f"{self.source}: tool {self.name}: kind git needs commit (the full hash, 40 hex digits)")
            if self.sha256:
                raise ToolsError(f"{self.source}: tool {self.name}: kind git is pinned by commit, not sha256")
        elif self.commit:
            raise ToolsError(f"{self.source}: tool {self.name}: commit is only for kind git")
        elif self.kind != "npm" and not re.fullmatch(r"[0-9a-f]{64}", self.sha256 or ""):
            raise ToolsError(f"{self.source}: tool {self.name}: sha256 (64 hex digits) is required")
        if self.kind != "npm" and not self.url:
            raise ToolsError(f"{self.source}: tool {self.name}: url is required")
        if self.subdir and self.kind not in ("tarball", "zip", "conda", "git"):
            raise ToolsError(f"{self.source}: tool {self.name}: subdir is not supported for kind {self.kind}")
        loc = Path(self.location)
        if loc.is_absolute() or ".." in loc.parts or self.location.rstrip("/") == STATE_PREFIX.rstrip("/"):
            raise ToolsError(f"{self.source}: tool {self.name}: location must be a folder below .venv or .xdmod/")

    def path(self, ws: Workspace) -> Path:
        """Where the tool is installed: <ws>/.venv/<location>, or <ws>/.xdmod/... for a state location."""
        if self.location.startswith(STATE_PREFIX):
            return ws.state / self.location[len(STATE_PREFIX):]
        return ws.venv / self.location

    def shown(self) -> str:
        """The location as the workspace-relative path people see."""
        return self.location if self.location.startswith(STATE_PREFIX) else f".venv/{self.location}"

    @property
    def pin(self) -> str:
        return self.commit[:12] if self.kind == "git" else self.version


@dataclass
class SystemTool:
    name: str
    version: str
    cmd: list = field(default_factory=list)
    regex: str = ""
    optional: bool = False
    pinned: bool = True              # false: a version the tool was tried with (doctor: warn, never FAIL)
    roles: list = field(default_factory=list)
    source: str = ""

    def argv(self) -> list[str]:
        return list(self.cmd) if self.cmd else [self.name, "--version"]


@dataclass
class ToolSet:
    tools: dict[str, Tool] = field(default_factory=dict)
    system: dict[str, SystemTool] = field(default_factory=dict)


def parse(path: Path) -> ToolSet:
    data = yaml.safe_load(path.read_text()) or {}
    ts = ToolSet()
    for t in data.get("tools") or []:
        t = dict(t)
        t["version"] = str(t.get("version", ""))
        ts.tools[t["name"]] = Tool(source=str(path), **t)
    for s in data.get("system") or []:
        s = dict(s)
        s["version"] = str(s.get("version", "any"))
        if s["version"].startswith(">=") and not re.fullmatch(r">=\d+(?:\.\d+)*", s["version"]):
            raise ToolsError(f"{path}: {s['name']}: a minimum version is >= followed by numbers, not {s['version']!r}")
        ts.system[s["name"]] = SystemTool(source=str(path), **s)
    return ts


def merge(sets: list[ToolSet]) -> ToolSet:
    out = ToolSet()
    for ts in sets:
        for kind, target in (("tools", out.tools), ("system", out.system)):
            for name, t in getattr(ts, kind).items():
                old = target.get(name)
                if old and old.version != t.version and "any" not in (old.version, t.version):
                    keep = _stricter(old.version, t.version)
                    if keep is not None:              # a minimum and a pin that meets it: keep the stricter
                        target[name] = t if keep == t.version else old
                        continue
                    raise ToolsError(f"tool {name}: version {old.version} ({old.source}) "
                                     f"conflicts with {t.version} ({t.source})")
                if not old or old.version == "any":
                    target[name] = t
    return out


def load_all(ws: Workspace) -> ToolSet:
    files = []
    seen = set()
    for r in [*ws.framework_repos]:
        f = r.path / "tools.yaml"
        if f.is_file() and f.resolve() not in seen:
            seen.add(f.resolve())
            files.append(f)
    xf = ws.xdmod / "tools.yaml"
    if xf.is_file() and xf.resolve() not in seen:
        files.insert(0, xf)
    return merge([parse(f) for f in files])


def for_role(ts: ToolSet, role: str | None) -> ToolSet:
    keep = lambda t: not t.roles or (role in t.roles)  # noqa: E731
    return ToolSet({k: v for k, v in ts.tools.items() if keep(v)}, {k: v for k, v in ts.system.items() if keep(v)})


# ------------------------------------------------------------------ version checks
def _vtuple(v: str) -> tuple[int, ...]:
    """The leading version of a string: "v22.23.4" -> (22, 23, 4); "4.5.0-rc1" -> (4, 5, 0)."""
    m = re.search(r"\d+(?:\.\d+)*", v or "")
    return tuple(int(x) for x in m.group(0).split(".")[:4]) if m else ()


def _stricter(a: str, b: str) -> str | None:
    """Of two pins of the same tool where at least one is a minimum, the stricter one, if they agree;
    None if they conflict (an exact pin below a minimum)."""
    if a.startswith(">=") and b.startswith(">="):
        return a if _vtuple(a[2:]) >= _vtuple(b[2:]) else b
    lo, other = (a, b) if a.startswith(">=") else (b, a) if b.startswith(">=") else (None, None)
    if lo is None:
        return None
    base = other[:-2] if other.endswith(".*") else other
    return other if _vtuple(base) >= _vtuple(lo[2:]) else None


def version_ok(want: str, have: str | None) -> bool:
    """`want`: an exact version, "any", a prefix wildcard ("10.0.*") or a minimum (">=2.43")."""
    if have is None:
        return False
    if want in ("any", ""):
        return True
    if want.startswith(">="):
        return bool(_vtuple(have)) and _vtuple(have) >= _vtuple(want[2:])
    if want.endswith(".*"):
        return have == want[:-2] or have.startswith(want[:-1])
    return have == want


def system_version(st: SystemTool, ws: Workspace | None = None) -> str | None:
    """The installed version, or None if the tool is missing."""
    argv = st.argv()
    if not shutil.which(argv[0]) and not Path(argv[0]).exists():
        return None
    try:
        r = limits.run(argv, "script", ws, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return None
    out = (r.stdout or "") + (r.stderr or "")
    m = re.search(st.regex, out) if st.regex else _VERSION.search(out)
    return m.group(1) if m else out.strip().splitlines()[0] if out.strip() else ""


def stamp_path(ws: Workspace, name: str) -> Path:
    return ws.opt / ".xd-stamps" / f"{name}.json"


def stamp_of(ws: Workspace, name: str) -> dict | None:
    p = stamp_path(ws, name)
    return json.loads(p.read_text()) if p.is_file() else None


def git_head(path: Path, ws: Workspace | None = None) -> str | None:
    """The commit of a git checkout whose top folder is `path`, else None."""
    if not (path / ".git").exists():
        return None
    r = limits.run(["git", "-C", str(path), "rev-parse", "HEAD"], "git", ws, capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def installed_ok(ws: Workspace, t: Tool) -> bool:
    s = stamp_of(ws, t.name)
    if not (s and s.get("version") == t.version and s.get("sha256", "") == t.sha256
            and s.get("commit", "") == t.commit and t.path(ws).exists()):
        return False
    if t.kind == "git":                      # an adopted checkout must still be at the pin
        head = git_head(t.path(ws), ws)
        return head is None or head == t.commit
    return True


# ------------------------------------------------------------------ installer
def _cache(ws: Workspace) -> Path:
    c = ws.state / "cache" / "downloads"
    c.mkdir(parents=True, exist_ok=True)
    return c


def sha256_of(path: Path) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def fetch(ws: Workspace, t: Tool) -> Path:
    dst = _cache(ws) / f"{t.sha256[:16]}-{Path(t.url.split('?')[0]).name or t.name}"
    if not dst.exists() or sha256_of(dst) != t.sha256:
        tmp = dst.with_suffix(dst.suffix + ".part")
        r = limits.run(["curl", "-fsSL", "-o", str(tmp), t.url], "install", ws)
        if r.returncode:
            raise ToolsError(f"{t.name}: download failed ({t.url})")
        got = sha256_of(tmp)
        if got != t.sha256:
            tmp.unlink()
            raise ToolsError(f"{t.name}: sha256 mismatch for {t.url}: got {got}, want {t.sha256}")
        tmp.rename(dst)
    return dst


def write_stamp(ws: Workspace, t: Tool) -> None:
    sp = stamp_path(ws, t.name)
    sp.parent.mkdir(parents=True, exist_ok=True)
    data = {"name": t.name, "version": t.version, "sha256": t.sha256, "source": t.source}
    if t.commit:
        data["commit"] = t.commit
    sp.write_text(json.dumps(data, indent=2) + "\n")


def fetch_git(ws: Workspace, t: Tool, into: Path) -> None:
    """Exactly the pinned commit into a bare cache repo; its tree (or subdir) extracted into `into`."""
    cache = ws.state / "cache" / "git" / f"{t.name}.git"
    run = lambda *a: limits.run(["git", *a], "install", ws, capture_output=True, text=True)  # noqa: E731
    if not (cache / "HEAD").exists():
        cache.mkdir(parents=True, exist_ok=True)
        if run("init", "--bare", "-q", str(cache)).returncode:
            raise ToolsError(f"{t.name}: git init of the cache failed")
    have = run("-C", str(cache), "rev-parse", "--verify", "--quiet", f"{t.commit}^{{commit}}")
    if have.returncode or have.stdout.strip() != t.commit:
        r = run("-C", str(cache), "fetch", "--quiet", "--depth", "1", t.url, t.commit)
        if r.returncode:
            raise ToolsError(f"{t.name}: git fetch of {t.commit} from {t.url} failed: {r.stderr.strip()}")
        have = run("-C", str(cache), "rev-parse", "--verify", "--quiet", f"{t.commit}^{{commit}}")
        if have.returncode or have.stdout.strip() != t.commit:
            raise ToolsError(f"{t.name}: {t.url} did not give commit {t.commit}")
    tar = into.parent / f"{t.name}.tar"
    args = ["-C", str(cache), "archive", "--format=tar", "-o", str(tar), t.commit]
    if t.subdir:
        args.append(t.subdir.strip("/"))
    r = run(*args)
    if r.returncode:
        raise ToolsError(f"{t.name}: git archive failed: {r.stderr.strip()}")
    into.mkdir(parents=True, exist_ok=True)
    strip = len(Path(t.subdir.strip("/")).parts) if t.subdir else 0
    if limits.run(["tar", "-xf", str(tar), "-C", str(into), f"--strip-components={strip}"], "install", ws).returncode:
        raise ToolsError(f"{t.name}: unpacking failed")
    tar.unlink()


def install(ws: Workspace, t: Tool, log=print, adopt: bool = False) -> None:
    """Install one tool unless its stamp matches. `adopt`: a tool already on disk without a
    stamp (a workspace set up before curatrix) is taken as is and only stamped."""
    if installed_ok(ws, t):
        log(f"  ok       {t.name} {t.version}")
        return
    loc = t.path(ws)
    if adopt and loc.exists() and stamp_of(ws, t.name) is None and t.kind != "git":
        log(f"  adopt    {t.name} {t.version} (already in {t.shown()}; stamped, not re-installed)")
        write_stamp(ws, t)
        return
    if t.kind == "git" and not t.subdir and git_head(loc, ws) == t.commit:
        log(f"  adopt    {t.name} {t.version} (a git checkout at {t.commit[:12]} in {t.shown()}; stamped)")
        write_stamp(ws, t)
        return
    log(f"  install  {t.name} {t.version} -> {t.shown()}")
    if t.kind == "npm":
        prefix = loc
        prefix.mkdir(parents=True, exist_ok=True)
        r = limits.run(["npm", "--prefix", str(prefix), "install", "--no-audit", "--no-fund", "--save-exact",
                        f"{t.package or t.name}@{t.version}"], "install", ws, capture_output=True, text=True)
        if r.returncode:
            raise ToolsError(f"{t.name}: npm install failed:\n{r.stdout}{r.stderr}")
    elif t.kind == "git":
        with tempfile.TemporaryDirectory(dir=_cache(ws).parent) as td:
            content = Path(td) / "tree"
            fetch_git(ws, t, content)
            if loc.exists():
                shutil.rmtree(loc)
            loc.parent.mkdir(parents=True, exist_ok=True)
            shutil.copytree(content, loc, symlinks=True)
    else:
        src = fetch(ws, t)
        if t.kind == "file":
            loc.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, loc)
        else:
            with tempfile.TemporaryDirectory(dir=ws.state / "cache") as td:
                td = Path(td)
                if t.kind == "tarball":
                    r = limits.run(["tar", "-xf", str(src), "-C", str(td), f"--strip-components={t.strip}"], "install", ws)
                    if r.returncode:
                        raise ToolsError(f"{t.name}: unpacking failed")
                    content = td / t.subdir if t.subdir else td
                elif t.kind == "zip":
                    with zipfile.ZipFile(src) as z:
                        z.extractall(td)
                    content = td / t.subdir if t.subdir else td
                else:  # conda: a zip with pkg-*.tar.zst inside
                    with zipfile.ZipFile(src) as z:
                        z.extractall(td / "conda")
                    pkg = next((td / "conda").glob("pkg-*.tar.zst"))
                    (td / "pkg").mkdir()
                    r = limits.run(["tar", "--zstd", "-xf", str(pkg), "-C", str(td / "pkg")], "install", ws)
                    if r.returncode:
                        raise ToolsError(f"{t.name}: unpacking failed")
                    content = td / "pkg" / t.subdir if t.subdir else td / "pkg"
                if loc.exists():
                    shutil.rmtree(loc)
                loc.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(content, loc, symlinks=True)
    for name, rel in (t.links or {}).items():
        link = ws.venv / "bin" / name
        if link.is_symlink() or link.exists():
            link.unlink()
        link.symlink_to(loc / rel)
    write_stamp(ws, t)


def install_all(ws: Workspace, role: str | None, log=print, adopt: bool = False) -> None:
    ts = for_role(load_all(ws), role)
    for t in ts.tools.values():
        install(ws, t, log, adopt=adopt)
