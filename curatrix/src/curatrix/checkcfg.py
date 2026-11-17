"""checks.yaml: what `curatrix check <repo>` runs for a repo (schema version 1).

Every key is optional; a section that is absent switches its checks off. Full reference:
``xdmod/curatrix/README.md`` ("checks.yaml"). Paths are relative to the repo unless they start
with ``{ws}/`` (the workspace root).

    version: 1
    area: myproj-syseng              # build/<area>/ (default: the repo name)
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
      upstream: ["{ws}/myproj-syseng/generated/model.json"]   # CK-E4 conformance (domain models)
    variants:                        # CK-B8 variants across levels (domain repos; needs model.upstream)
      zephyr: ["{ws}/myproj-sw/boards"]   # optional: Zephyr board roots; board variants by name
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
    code:                            # CK-D6 (plain Python): @xdid code units, test cases above ZTEST
      sources: ["app/src/**/*.[ch]"]
      tests: ["tests/**/*.c"]
      needs: generated/code-needs.json
    requirements: true               # CK-E2, CK-E3 on the repo's own requirements
    bootstrap_template: scripts/bootstrap.sh   # CK-H5 (the manifest repo)
    pr_size: {lines: 600, files: 15}  # CK-H7 PR size warning (these are the defaults)
    expect: [CK-A6, CK-A1, CK-C1]    # CK-H6: exactly the checks this repo runs (built-in + commands)
    commands:                        # repo-specific checks
      - id: CK-F1
        name: KiCad netlist vs. interface pin maps
        run: ["{python}", "tests/check_pinmap.py", "-o", "{build}/pinmap.xml"]
        use: script
        stages: [local, baseline]
        cad: true
        level: error
      - id: CK-F5b
        name: unit tests (Twister)
        run: ["{python}", "{ws}/zephyr/scripts/twister", "-T", "{repo}/tests", "-O", "{build}/twister"]
        before_docs: true            # runs before CK-A6, so the docs build sees this run's results
"""
from __future__ import annotations

import glob
from dataclasses import dataclass, field
from pathlib import Path

import yaml

STAGES = ("local", "pr", "full", "baseline")
LEVELS = ("error", "warning", "report")
TOP_KEYS = {"version", "area", "docs", "ids", "model", "stubs", "views", "cad", "code", "requirements", "variants",
            "bootstrap_template", "commands", "expect", "pr_size"}
SECTION_KEYS = {
    "docs": {"registry"},
    "ids": {"ledger", "exclude"},
    "model": {"libraries", "files", "export", "json", "needs", "variants", "upstream"},
    "stubs": {"out", "docs", "package"},
    "views": {"dir", "model"},
    "cad": {"kicad", "freecad", "needs", "freecad_json"},
    "code": {"sources", "tests", "needs"},
    "variants": {"zephyr"},
}
COMMAND_KEYS = {"id", "name", "run", "use", "stages", "cad", "level", "cwd", "before_docs"}


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
    before_docs: bool = False   # run before the docs build (CK-A6), e.g. tests whose results the docs show


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
        """The section as a mapping, None if it is off. A scalar key (``requirements: true``,
        ``bootstrap_template: scripts/bootstrap.sh``) gives ``{}`` or ``{"path": <value>}``."""
        v = self.raw.get(name)
        if v is None or v is False:
            return None
        if v is True:
            return {}
        if isinstance(v, str):
            return {"path": v}
        return dict(v)

    @property
    def bootstrap_copy(self) -> Path:
        """CK-H5: the repo's copy of xdmod/templates/bootstrap.sh (``true`` = the default path)."""
        v = self.raw.get("bootstrap_template")
        return self.resolve(v if isinstance(v, str) else "scripts/bootstrap.sh")

    @property
    def expect(self) -> list[str] | None:
        """CK-H6: the check IDs the repo expects to run, None if the key is missing."""
        v = self.raw.get("expect")
        return list(v) if v is not None else None

    @property
    def pr_size(self) -> tuple[int, int]:
        """CK-H7: (lines, files) above which a PR gets a size warning."""
        v = self.raw.get("pr_size") or {}
        return int(v.get("lines", 600)), int(v.get("files", 15))

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
        for k in ("files", "libraries", "export", "docs", "kicad", "freecad", "exclude", "sources", "tests", "zephyr"):
            if k in v and not (isinstance(v[k], list) and all(isinstance(x, str) for x in v[k])):
                errs.append(f"{path}: {sec}.{k} must be a list of strings")
    for k in ("requirements",):
        if k in raw and not isinstance(raw[k], bool):
            errs.append(f"{path}: {k} must be true or false")
    bt = raw.get("bootstrap_template")
    if bt is not None and not isinstance(bt, (bool, str)):
        errs.append(f"{path}: bootstrap_template must be a path (string) or true/false")
    ex = raw.get("expect")
    if ex is not None and not (isinstance(ex, list) and all(isinstance(x, str) for x in ex)):
        errs.append(f"{path}: expect must be a list of check IDs")
    elif ex is not None and len(set(ex)) != len(ex):
        errs.append(f"{path}: expect lists a check twice")
    ps = raw.get("pr_size")
    if ps is not None:
        if not isinstance(ps, dict) or set(ps) - {"lines", "files"} or \
                not all(isinstance(v, int) and not isinstance(v, bool) and v > 0 for v in ps.values()):
            errs.append(f"{path}: pr_size must be a mapping with positive integers `lines` and `files`")
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
        if "before_docs" in c and not isinstance(c["before_docs"], bool):
            errs.append(f"{where}: before_docs must be true or false")
        if c.get("level", "error") not in LEVELS:
            errs.append(f"{where}: level must be one of {LEVELS}")
    return errs


def load(path: Path, ws_root: Path) -> ChecksConfig:
    """Read and validate a checks.yaml. A missing file is an error: a renamed or deleted
    checks.yaml must not turn a repo's checks green (P4-4)."""
    if not path.is_file():
        raise ConfigError(f"{path}: missing. Every repo that `curatrix check` runs on needs a checks.yaml "
                          f"(format: xdmod/curatrix/README.md, \"checks.yaml\")")
    raw = yaml.safe_load(path.read_text()) or {}
    errs = validate(raw, path)
    if errs:
        raise ConfigError("\n".join(errs))
    return ChecksConfig(path=path, repo=path.parent, ws=ws_root, raw=raw)
