"""tools.yaml: pinned non-pip tools, their installer, and the version checks of `doctor` (D19).

Every repo (xdmod included) may have a ``tools.yaml`` at its root. curatrix merges the files of
all active repos; one tool name with two different versions is an error. Format (see
``xdmod/curatrix/README.md``)::

    tools:                      # installed into <ws>/.venv/<location> with sha256 checks
      - name: jdk
        version: "21.0.13+9"
        kind: tarball           # tarball | zip | conda | file | npm
        url: https://...
        sha256: d7f5...         # required for every kind except npm
        location: opt/jdk       # relative to <ws>/.venv
        strip: 1                # tarball: leading path components to drop (default 1)
        subdir: share/...       # conda / zip: copy only this folder of the package
        links: {jshell: bin/jshell}   # symlinks <ws>/.venv/bin/<name> -> <location>/<path>
        env: {JAVA_HOME: "{location}"}  # exported by `curatrix env`
        roles: [sw]             # optional: install only for these roles
    system:                     # used from the machine (D19); `doctor` fails on a mismatch
      - name: kicad-cli
        version: "10.0.8"       # exact; "any"; or a prefix wildcard like "10.0.*"
        cmd: [kicad-cli, --version]   # default [<name>, --version]
        regex: '(\\d+\\.\\d+\\.\\d+)'  # default: the first x.y[.z] in the output
        optional: true          # missing = warning (a wrong version is still an error)
        roles: [ee]

An installed tool leaves a stamp ``<ws>/.venv/opt/.xd-stamps/<name>.json`` with name, version,
sha256. `doctor` compares the stamps with tools.yaml.
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

KINDS = ("tarball", "zip", "conda", "file", "npm")
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
    links: dict = field(default_factory=dict)
    env: dict = field(default_factory=dict)
    roles: list = field(default_factory=list)
    source: str = ""          # which tools.yaml

    def __post_init__(self):
        if self.kind not in KINDS:
            raise ToolsError(f"{self.source}: tool {self.name}: kind must be one of {KINDS}")
        if self.kind != "npm" and not re.fullmatch(r"[0-9a-f]{64}", self.sha256 or ""):
            raise ToolsError(f"{self.source}: tool {self.name}: sha256 (64 hex digits) is required")
        if self.kind != "npm" and not self.url:
            raise ToolsError(f"{self.source}: tool {self.name}: url is required")


@dataclass
class SystemTool:
    name: str
    version: str
    cmd: list = field(default_factory=list)
    regex: str = ""
    optional: bool = False
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
        ts.system[s["name"]] = SystemTool(source=str(path), **s)
    return ts


def merge(sets: list[ToolSet]) -> ToolSet:
    out = ToolSet()
    for ts in sets:
        for kind, target in (("tools", out.tools), ("system", out.system)):
            for name, t in getattr(ts, kind).items():
                old = target.get(name)
                if old and old.version != t.version and "any" not in (old.version, t.version):
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
def version_ok(want: str, have: str | None) -> bool:
    if have is None:
        return False
    if want in ("any", ""):
        return True
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


def installed_ok(ws: Workspace, t: Tool) -> bool:
    s = stamp_of(ws, t.name)
    return bool(s) and s.get("version") == t.version and s.get("sha256", "") == t.sha256 \
        and (ws.venv / t.location).exists()


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
    sp.write_text(json.dumps({"name": t.name, "version": t.version, "sha256": t.sha256, "source": t.source},
                             indent=2) + "\n")


def install(ws: Workspace, t: Tool, log=print, adopt: bool = False) -> None:
    """Install one tool unless its stamp matches. `adopt`: a tool already on disk without a
    stamp (a workspace set up before curatrix) is taken as is and only stamped."""
    if installed_ok(ws, t):
        log(f"  ok       {t.name} {t.version}")
        return
    loc = ws.venv / t.location
    if adopt and loc.exists() and stamp_of(ws, t.name) is None:
        log(f"  adopt    {t.name} {t.version} (already in .venv/{t.location}; stamped, not re-installed)")
        write_stamp(ws, t)
        return
    log(f"  install  {t.name} {t.version} -> .venv/{t.location}")
    if t.kind == "npm":
        prefix = loc
        prefix.mkdir(parents=True, exist_ok=True)
        r = limits.run(["npm", "--prefix", str(prefix), "install", "--no-audit", "--no-fund", "--save-exact",
                        f"{t.package or t.name}@{t.version}"], "install", ws, capture_output=True, text=True)
        if r.returncode:
            raise ToolsError(f"{t.name}: npm install failed:\n{r.stdout}{r.stderr}")
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
                    content = td
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
