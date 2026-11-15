"""Tool provenance of committed generated files (task 4.4b, D19).

Generated files that depend on an external tool record the versions that made them in
``<repo>/generated/provenance.json`` (committed, sorted, stable)::

    {"files": {"generated/model.json": {"made_by": "curatrix gen model",
                                        "tools": {"jdk": "21.0.13+9", "sysml-pilot": "0.63.1"}},
               "views/jointView.drawio.svg": {"made_by": "curatrix views build",
                                              "tools": {"drawio-viewer": "32.6.1", ...}}},
     "version": 1}

Files made by curatrix alone (stubs, cad-needs, tombstones, plain-Python FreeCAD JSON) have no
entry: their content is checked directly (CK-D1, CK-D4).

The writer records the versions it actually used (tools.yaml stamps, system tool versions). The
check (CK-D5) compares the record with the pins in tools.yaml, so it needs no tools and runs in
CI: a file made with another version than the pinned one (a rolling distro, an old workspace) is
reported until it is regenerated with the pinned toolchain.
"""
from __future__ import annotations

import json
from pathlib import Path

from curatrix import tools as toolsmod
from curatrix.checkcfg import ChecksConfig

REL = "generated/provenance.json"

# which tools make which kind of generated file
KINDS = {
    "model": ("curatrix gen model", ["jdk", "sysml-pilot"]),
    "views": ("curatrix views build", ["elkjs", "drawio-viewer", "firefox"]),
    "freecad-shapes": ("curatrix gen freecad-json --shape", ["FreeCADCmd"]),
}


def path(cfg: ChecksConfig) -> Path:
    return cfg.repo / REL


def load(cfg: ChecksConfig) -> dict:
    p = path(cfg)
    doc = json.loads(p.read_text()) if p.is_file() else {}
    doc.setdefault("version", 1)
    doc.setdefault("files", {})
    return doc


def dumps(doc: dict) -> str:
    return json.dumps({"files": dict(sorted(doc["files"].items())), "version": doc.get("version", 1)},
                      indent=2, sort_keys=True) + "\n"


def _toolset(ws):
    return toolsmod.for_role(toolsmod.load_all(ws), ws.role)


def used(ws, kind: str) -> dict[str, str]:
    """Versions of the tools of `kind` as installed now (stamp / system --version)."""
    ts = _toolset(ws)
    out = {}
    for name in KINDS[kind][1]:
        if name in ts.tools:
            s = toolsmod.stamp_of(ws, name)
            out[name] = (s or {}).get("version") or "unknown"
        elif name in ts.system:
            out[name] = toolsmod.system_version(ts.system[name], ws) or "missing"
    return dict(sorted(out.items()))


def pinned(ws, kind: str) -> dict[str, str]:
    ts = _toolset(ws)
    out = {}
    for name in KINDS[kind][1]:
        if name in ts.tools:
            out[name] = ts.tools[name].version
        elif name in ts.system:
            out[name] = ts.system[name].version
    return dict(sorted(out.items()))


def record(ws, cfg: ChecksConfig, files: list[Path], kind: str, versions: dict[str, str] | None = None,
           drop: list[Path] | None = None) -> bool:
    """Record that `files` were just made by `kind` with `versions` (default: the installed tools).
    `drop`: files that no longer exist. Returns True if provenance.json changed."""
    versions = used(ws, kind) if versions is None else versions
    doc = load(cfg)
    for f in files:
        doc["files"][_rel(cfg, f)] = {"made_by": KINDS[kind][0], "tools": dict(sorted(versions.items()))}
    for f in drop or []:
        doc["files"].pop(_rel(cfg, f), None)
    text = dumps(doc)
    p = path(cfg)
    if p.is_file() and p.read_text() == text:
        return False
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    return True


def _rel(cfg: ChecksConfig, f: Path) -> str:
    return str(Path(f).resolve().relative_to(cfg.repo.resolve()))


def check(ws, cfg: ChecksConfig, files: list[Path], kind: str) -> list[str]:
    """CK-D5: each of `files` has a record, and the record matches the pins in tools.yaml."""
    doc = load(cfg)
    want = pinned(ws, kind)
    fix = KINDS[kind][0] + f" {cfg.repo.name}"
    out = []
    for f in files:
        if not Path(f).exists():
            continue
        rel = _rel(cfg, f)
        e = doc["files"].get(rel)
        if e is None:
            out.append(f"{rel}: no tool versions recorded in {REL}; run `{fix}` and commit")
            continue
        have = e.get("tools", {})
        bad = [f"{n} {have.get(n, 'unrecorded')} (tools.yaml: {v})" for n, v in want.items()
               if not toolsmod.version_ok(v, have.get(n))]
        if bad:
            out.append(f"{rel}: made with {', '.join(bad)}; run `{fix}` with the pinned tools and commit")
    return out
