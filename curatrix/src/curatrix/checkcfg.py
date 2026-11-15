"""checks.yaml: what `curatrix check <repo>` runs for a repo (schema version 1).

Every key is optional; a section that is absent switches its checks off. Full reference:
``xdmod/curatrix/README.md`` ("checks.yaml"). Paths are relative to the repo unless they start
with ``{ws}/`` (the workspace root).

    version: 1
    area: robarm-syseng              # build/<area>/ (default: the repo name)
    docs:                            # CK-A6 strict zdocs build; its needs.json feed the graph checks
      registry: docs/documents.yaml
    ids:                             # CK-C1, CK-C2
      ledger: ids.yaml
      exclude: ["docs/examples/**"]  # paths whose IDs/placeholders are examples, not sources
    model:                           # CK-E1, CK-D2 (SysML via the Pilot), CK-B4 (variants)
      libraries: ["{ws}/libs/pleml/PLEML.sysml"]   # loaded first; xdmod/sysml/*.sysml always is
      files: [model/generated/NeedStubs.sysml, "model/*.sysml"]
      export: [RobArm]               # default: every top-level package of `files`
      json: generated/model.json
      needs: generated/model-needs.json
      variants: true
    stubs:                           # CK-D1
      out: model/generated/NeedStubs.sysml
      docs: [se-req]
      package: NeedStubs
    views:                           # CK-D3
      dir: views
    cad:                             # CK-D4 (plain Python, no CAD tools), CK-H1
      kicad: ["pcba/*/*.kicad_sch"]
      freecad: ["parts/*.FCStd", "assemblies/**/*.FCStd"]
      needs: generated/cad-needs.json
      freecad_json: generated/freecad
    requirements: true               # CK-E2, CK-E3 on the repo's own requirements
    bootstrap_template: scripts/bootstrap.sh   # CK-H5 (robarm-manifest)
    commands:                        # repo-specific checks
      - id: CK-F1
        name: KiCad netlist vs. interface pin maps
        run: ["{python}", "tests/check_pinmap.py", "-o", "{build}/pinmap.xml"]
        use: script
        stages: [local, baseline]
        cad: true
        level: error
"""
from __future__ import annotations

import glob
from dataclasses import dataclass, field
from pathlib import Path

import yaml

STAGES = ("local", "pr", "full", "baseline")
LEVELS = ("error", "warning", "report")
TOP_KEYS = {"version", "area", "docs", "ids", "model", "stubs", "views", "cad", "requirements",
            "bootstrap_template", "commands"}
SECTION_KEYS = {
    "docs": {"registry"},
    "ids": {"ledger", "exclude"},
    "model": {"libraries", "files", "export", "json", "needs", "variants"},
    "stubs": {"out", "docs", "package"},
    "views": {"dir", "model"},
    "cad": {"kicad", "freecad", "needs", "freecad_json"},
}
COMMAND_KEYS = {"id", "name", "run", "use", "stages", "cad", "level", "cwd"}


class ConfigError(Exception):
    pass


@dataclass
class Command:
    id: str
    name: str
    run: list[str]
    use: str = "script"
    stages: list[str] = field(default_factory=lambda: list(STAGES))
    cad: bool = False
    level: str = "error"
    cwd: str = "{repo}"


@dataclass
class ChecksConfig:
    path: Path
    repo: Path
    ws: Path
    raw: dict

    def resolve(self, p: str) -> Path:
        if p.startswith("{ws}/"):
            return self.ws / p[5:]
        return self.repo / p

    def globs(self, patterns: list[str]) -> list[Path]:
        out, seen = [], set()
        for pat in patterns:
            base = self.resolve(pat)
            hits = sorted(Path(x) for x in glob.glob(str(base), recursive=True)) if any(c in pat for c in "*?[") else [base]
            for h in hits:
                if h.resolve() not in seen:
                    seen.add(h.resolve())
                    out.append(h)
        return out

    def section(self, name: str) -> dict | None:
        v = self.raw.get(name)
        if v is None or v is False:
            return None
        return {} if v is True else dict(v)

    @property
    def area(self) -> str:
        return self.raw.get("area") or self.repo.name

    @property
    def commands(self) -> list[Command]:
        return [Command(**c) for c in self.raw.get("commands") or []]

    # convenient accessors with defaults
    @property
    def docs_registry(self) -> Path | None:
        s = self.section("docs")
        return self.resolve(s.get("registry", "docs/documents.yaml")) if s is not None else None

    @property
    def ids_exclude(self) -> list[str]:
        return list((self.section("ids") or {}).get("exclude") or [])

    @property
    def ledger(self) -> Path:
        s = self.section("ids") or {}
        return self.resolve(s.get("ledger", "ids.yaml"))


def validate(raw: dict, path: Path) -> list[str]:
    errs = []
    if not isinstance(raw, dict):
        return [f"{path}: must be a mapping"]
    if raw.get("version", 1) != 1:
        errs.append(f"{path}: version must be 1")
    for k in raw:
        if k not in TOP_KEYS:
            errs.append(f"{path}: unknown key {k!r} (known: {', '.join(sorted(TOP_KEYS))})")
    for sec, keys in SECTION_KEYS.items():
        v = raw.get(sec)
        if v is None or isinstance(v, bool):
            continue
        if not isinstance(v, dict):
            errs.append(f"{path}: {sec} must be a mapping or true/false")
            continue
        for k in v:
            if k not in keys:
                errs.append(f"{path}: {sec}: unknown key {k!r} (known: {', '.join(sorted(keys))})")
        for k in ("files", "libraries", "export", "docs", "kicad", "freecad", "exclude"):
            if k in v and not (isinstance(v[k], list) and all(isinstance(x, str) for x in v[k])):
                errs.append(f"{path}: {sec}.{k} must be a list of strings")
    if "model" in raw and isinstance(raw["model"], dict) and not raw["model"].get("files"):
        errs.append(f"{path}: model.files is required")
    if "stubs" in raw and isinstance(raw["stubs"], dict) and not raw["stubs"].get("docs"):
        errs.append(f"{path}: stubs.docs (the doc ids whose needs feed the stubs) is required")
    seen = set()
    for i, c in enumerate(raw.get("commands") or []):
        where = f"{path}: commands[{i}]"
        if not isinstance(c, dict):
            errs.append(f"{where} must be a mapping")
            continue
        for k in c:
            if k not in COMMAND_KEYS:
                errs.append(f"{where}: unknown key {k!r}")
        for k in ("id", "name", "run"):
            if k not in c:
                errs.append(f"{where}: {k} is required")
        if "run" in c and not (isinstance(c["run"], list) and c["run"] and all(isinstance(x, str) for x in c["run"])):
            errs.append(f"{where}: run must be a non-empty list of strings (argv, no shell)")
        if c.get("id") in seen:
            errs.append(f"{where}: duplicate id {c.get('id')}")
        seen.add(c.get("id"))
        for s in c.get("stages", []):
            if s not in STAGES:
                errs.append(f"{where}: unknown stage {s!r}")
        if c.get("level", "error") not in LEVELS:
            errs.append(f"{where}: level must be one of {LEVELS}")
    return errs


def load(path: Path, ws_root: Path) -> ChecksConfig:
    raw = yaml.safe_load(path.read_text()) if path.is_file() else {}
    raw = raw or {}
    errs = validate(raw, path)
    if errs:
        raise ConfigError("\n".join(errs))
    return ChecksConfig(path=path, repo=path.parent, ws=ws_root, raw=raw)
