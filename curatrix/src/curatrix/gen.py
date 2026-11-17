"""Generated, committed files ("generate, commit, check", spike lesson 2).

Each generator computes the file content in memory. `curatrix gen` writes it; `curatrix check`
compares it with the committed file (CK-D1, CK-D2, CK-D4). All paths come from checks.yaml.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from curatrix import cad, code as codemod, model as modelmod, needs as needsmod, pilot, stubs as stubsmod
from curatrix.checkcfg import ChecksConfig


class GenError(Exception):
    pass


@dataclass
class Output:
    path: Path
    text: str
    findings: list[str] = field(default_factory=list)
    log: str = ""

    def differs(self) -> bool:
        return not self.path.exists() or self.path.read_text(encoding="utf-8") != self.text

    def write(self) -> bool:
        changed = self.differs()
        if changed:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(self.text, encoding="utf-8")
        return changed


def docs_needs_json(ws, cfg: ChecksConfig, doc_ids: list[str] | None = None) -> list[Path]:
    """needs.json files of this repo's last docs build (build/<area>/docs/deploy/html/<doc>/)."""
    base = ws.build(cfg.area) / "docs" / "deploy" / "html"
    if doc_ids:
        return [base / d / "needs.json" for d in doc_ids]
    return sorted(base.glob("*/needs.json"))


# ------------------------------------------------------------------ stubs (CK-D1)
def stubs(ws, cfg: ChecksConfig, needs_files: list[Path] | None = None) -> Output:
    s = cfg.section("stubs")
    if s is None:
        raise GenError("checks.yaml has no stubs section")
    files = needs_files or docs_needs_json(ws, cfg, s["docs"])
    missing = [str(f) for f in files if not f.exists()]
    if missing:
        raise GenError(f"needs.json not found ({', '.join(missing)}); run `curatrix docs {cfg.repo.name}` first")
    all_needs = needsmod.load_built(files, own_only=True)
    text = stubsmod.generate(all_needs, s.get("package", stubsmod.PACKAGE),
                             source=", ".join(f"{d}/needs.json" for d in s["docs"]))
    return Output(cfg.resolve(s.get("out", "model/generated/NeedStubs.sysml")), text)


# ------------------------------------------------------------------ model (CK-E1, CK-D2)
def model_files(ws, cfg: ChecksConfig) -> tuple[list[Path], list[Path]]:
    s = cfg.section("model") or {}
    libs = sorted((ws.xdmod / "sysml").glob("*.sysml")) + cfg.globs(s.get("libraries") or [])
    files = cfg.globs(s.get("files") or [])
    lib_set = {p.resolve() for p in libs}
    return libs, [f for f in files if f.resolve() not in lib_set]


def model(ws, cfg: ChecksConfig) -> tuple[Output, Output, pilot.PilotResult]:
    """Run the Pilot; return (model.json, model-needs.json, pilot result)."""
    s = cfg.section("model")
    if s is None:
        raise GenError("checks.yaml has no model section")
    libs, files = model_files(ws, cfg)
    if not files:
        raise GenError("model.files matches no file")
    export = s.get("export") or sorted(modelmod.top_packages(files))
    tmp = ws.build(cfg.area) / "model"
    tmp.mkdir(parents=True, exist_ok=True)
    raw = tmp / "pilot-export.json"
    # the libraries as one set, then the repo's own files as one set (their order does not matter, XD-ADR-0130)
    res = pilot.run(ws, files, export, raw, tmpdir=tmp, libraries=libs, one_set=True)
    (tmp / "pilot.log").write_text(res.log + "\n")
    if not res.ok:
        raise GenError(f"the Pilot reported {res.errors} error(s); see {ws.rel(tmp / 'pilot.log')}:\n{res.log[-3000:]}")
    data = json.loads(raw.read_text())
    compact = modelmod.compact(data, modelmod.top_packages(libs))
    mjson = Output(cfg.resolve(s.get("json", "generated/model.json")), modelmod.dumps(compact), log=res.log)
    m = modelmod.Model(compact)
    doc, findings = modelmod.to_needs(m, f"{cfg.repo.name}-model", modelmod.source_map(files, cfg.repo))
    modelmod.add_configs(doc, upstream_models(cfg)[0])
    nout = Output(cfg.resolve(s.get("needs", "generated/model-needs.json")), needsmod.dumps(doc), findings)
    return mjson, nout, res


def model_needs_from_json(cfg: ChecksConfig) -> Output:
    """model-needs.json from the committed model.json (no Java needed)."""
    s = cfg.section("model") or {}
    mj = cfg.resolve(s.get("json", "generated/model.json"))
    m = modelmod.Model.load(mj)
    files = cfg.globs(s.get("files") or [])
    doc, findings = modelmod.to_needs(m, f"{cfg.repo.name}-model", modelmod.source_map(files, cfg.repo))
    modelmod.add_configs(doc, upstream_models(cfg)[0])
    return Output(cfg.resolve(s.get("needs", "generated/model-needs.json")), needsmod.dumps(doc), findings)


def upstream_models(cfg: ChecksConfig) -> tuple[list, list[str]]:
    """The upstream models of a domain model (``model.upstream``: the upstream repos' committed
    ``generated/model.json``, XD-ADR-0130), and findings for the missing ones."""
    s = cfg.section("model") or {}
    ups = s.get("upstream") or []
    out, findings = [], []
    for u in [ups] if isinstance(ups, str) else ups:
        p = cfg.resolve(u)
        if p.is_file():
            out.append(modelmod.Model.load(p))
        else:
            findings.append(f"model.upstream {u}: {p} not found (west update, or `curatrix gen model` in the upstream repo)")
    return out, findings


# ------------------------------------------------------------------ CAD needs (CK-D4), plain Python
def cad_needs(ws, cfg: ChecksConfig) -> Output:
    s = cfg.section("cad")
    if s is None:
        raise GenError("checks.yaml has no cad section")
    needs: dict[str, dict] = {}
    findings: list[str] = []

    def add(ns, fs):
        findings.extend(fs)
        for nid, n in ns.items():
            if nid in needs:
                findings.append(f"{n.get('source_file')}: {nid} is also defined in {needs[nid].get('source_file')}")
                continue
            needs[nid] = n

    refs: list[tuple[str, str]] = []
    from curatrix import eeprojects
    for sch in eeprojects.root_sheets(cfg):
        add(*cad.kicad_needs(cad.kicad_items(sch, cfg.repo), refs))
    for fc in cfg.globs(s.get("freecad") or []):
        add(*cad.freecad_needs(fc, str(fc.resolve().relative_to(cfg.repo.resolve())), refs))
    # a model-owned ID in a CAD file must be a need of the repo's model (XD-ADR-0128)
    ms = cfg.section("model")
    mp = cfg.resolve((ms or {}).get("needs", "generated/model-needs.json")) if ms is not None else None
    owned = needsmod.load(mp) if mp is not None and mp.exists() else {}
    for rid, src in refs:
        if rid not in owned:
            findings.append(f"{src}: TraceID {rid} is not a need of the model"
                            + ("" if ms is not None else " (the repo has no model section)")
                            + f"; add the def to the model and run `curatrix gen model {cfg.repo.name}`")
    return Output(cfg.resolve(s.get("needs", "generated/cad-needs.json")),
                  needsmod.dumps(needsmod.doc(needs, f"{cfg.repo.name}-cad")), findings)


# ------------------------------------------------------------------ connectors (CK-D7), plain Python
def connectors_path(cfg: ChecksConfig, project: str) -> Path:
    return cfg.resolve((cfg.section("cad") or {}).get("connectors") or "generated") / f"{project}.connectors.json"


def connectors(ws, cfg: ChecksConfig) -> list[Output]:
    """generated/<project>.connectors.json for every KiCad project (cad.projects): the connector
    pin tables, read from the schematic in plain Python (task 5.18)."""
    from curatrix import connectors as conn, eeprojects
    if not (cfg.section("cad") or {}).get("connectors"):
        raise GenError("checks.yaml has no cad.connectors (the folder of <project>.connectors.json)")
    outs = []
    for pr in eeprojects.discover(cfg):
        if not pr.sch.is_file():
            continue
        outs.append(Output(connectors_path(cfg, pr.name), conn.dumps(conn.document(pr.name, pr.sch, cfg.repo))))
    return outs


def stale_connectors(cfg: ChecksConfig) -> list[str]:
    """connectors.json files of projects that no longer exist."""
    from curatrix import eeprojects
    d = cfg.resolve((cfg.section("cad") or {}).get("connectors") or "generated")
    names = {pr.name for pr in eeprojects.discover(cfg)}
    return [f"{f.relative_to(cfg.repo)}: no project {f.name.removesuffix('.connectors.json')} any more; delete it"
            for f in sorted(d.glob("*.connectors.json")) if f.name.removesuffix(".connectors.json") not in names]


# ------------------------------------------------------------------ code needs (CK-D6), plain Python
def code_needs(ws, cfg: ChecksConfig) -> Output:
    """SW-IMPL needs from @xdid Doxygen blocks, test case needs from the comments above ZTEST."""
    s = cfg.section("code")
    if s is None:
        raise GenError("checks.yaml has no code section")
    needs: dict[str, dict] = {}
    findings: list[str] = []
    for key, reader in (("sources", codemod.code_units), ("tests", codemod.test_cases)):
        for f in cfg.globs(s.get(key) or []):
            if not f.is_file():
                continue
            ns, fs = reader(f, str(f.resolve().relative_to(cfg.repo.resolve())))
            findings += fs
            for nid, n in ns.items():
                if nid in needs:
                    findings.append(f"{n['source_file']}: {nid} is also defined in {needs[nid]['source_file']}")
                    continue
                needs[nid] = n
    return Output(cfg.resolve(s.get("needs", "generated/code-needs.json")),
                  needsmod.dumps(needsmod.doc(needs, f"{cfg.repo.name}-code")), findings)


def freecad_json(ws, cfg: ChecksConfig, shapes: bool = False) -> list[Output]:
    s = cfg.section("cad") or {}
    outdir = s.get("freecad_json")
    if not outdir:
        return []
    outs = []
    for fc in cfg.globs(s.get("freecad") or []):
        rel = str(fc.resolve().relative_to(cfg.repo.resolve()))
        sem = cad.freecad_trace(fc, rel)
        if shapes:
            sem["shapes"] = cad.freecad_shapes(ws, fc, ws.build(cfg.area) / "freecad")
        outs.append(Output(cfg.resolve(outdir) / (rel + ".json"), json.dumps(sem, indent=2, sort_keys=True) + "\n"))
    return outs


def cad_exports(ws, cfg: ChecksConfig, log=print) -> list[str]:
    """CAD pictures and tables for the docs (local only, needs the CAD tools; not committed):
    build/<area>/cad/<schematic stem>/<sheet>.svg and bom.csv from kicad-cli. The kicad-sheet /
    kicad-bom directives show them; without them the directives show a notice (D56).
    FreeCAD TechDraw exports are not implemented yet."""
    from curatrix import limits
    s = cfg.section("cad") or {}
    out = ws.build(cfg.area) / "cad"
    errs = []
    rev = subprocess.run(["git", "-C", str(cfg.repo), "describe", "--always", "--dirty"],
                         capture_output=True, text=True).stdout.strip() or "unknown"
    from curatrix import eeprojects
    for sch in eeprojects.root_sheets(cfg):
        d = out / sch.stem
        d.mkdir(parents=True, exist_ok=True)
        for argv in (["kicad-cli", "sch", "export", "svg", "-D", f"GIT_REV={rev}", "-o", str(d), str(sch)],
                     ["kicad-cli", "sch", "export", "bom", "-o", str(d / "bom.csv"), str(sch)]):
            r = limits.run(argv, "kicad-cli", ws, capture_output=True, text=True)
            if r.returncode:
                errs.append(f"{' '.join(argv[:4])} {ws.rel(sch)}: exit {r.returncode} {r.stderr[-300:]}")
        log(f"  exported {ws.rel(sch)} -> {ws.rel(d)}")
    return errs


# ------------------------------------------------------------------ tombstones (D130, CK-B7)
def retired_path(cfg: ChecksConfig) -> Path:
    return cfg.repo / "generated" / "retired-needs.json"


def tombstones(cfg: ChecksConfig, generated: list[Output], baseline_date: str | None = None) -> tuple[Output, list[str]]:
    """Compare old and new generated needs files; keep tombstones for deleted, unretired needs.
    A need that moved to another generated file of the repo (EE-PCBA from cad-needs.json to
    model-needs.json, XD-ADR-0128) is not deleted. The other files are read from disk, so the
    order of `gen cad-needs` and `gen model` does not matter: a tombstone written while
    model-needs.json was stale is removed by the next `gen model` (the need is back), and
    `gen all` makes both in one run."""
    rp = retired_path(cfg)
    current = needsmod.load(rp) if rp.exists() else {}
    msgs: list[str] = []
    new_all: dict[str, dict] = {}
    done = {o.path.resolve() for o in generated}
    for sec, default in (("model", "generated/model-needs.json"), ("cad", "generated/cad-needs.json"),
                         ("code", "generated/code-needs.json")):
        if cfg.section(sec) is not None:
            other = cfg.resolve((cfg.section(sec) or {}).get("needs", default))
            if other.resolve() not in done and other.exists():
                new_all.update(needsmod.load(other))
    for o in generated:
        new_all.update(needsmod.needs_of(json.loads(o.text)))
    for o in generated:
        old = needsmod.load(o.path) if o.path.exists() else {}
        current, m = needsmod.update_tombstones(old, new_all, current)
        msgs += m
    current = {k: v for k, v in current.items() if k not in new_all}
    current, m = needsmod.prune_tombstones(current, baseline_date)
    msgs += m
    return Output(rp, needsmod.dumps(needsmod.doc(current, f"{cfg.repo.name}-retired"))), msgs


def last_baseline_date(ws) -> str | None:
    """Date of the newest baseline/* tag of the manifest repo (ISO), if any."""
    mp = ws.manifest_path
    if not mp or not (mp / ".git").exists():
        return None
    try:
        out = subprocess.run(["git", "-C", str(mp), "for-each-ref", "--sort=-creatordate", "--count=1",
                              "--format=%(creatordate:short)", "refs/tags/baseline/"],
                             capture_output=True, text=True, timeout=30).stdout.strip()
        return out or None
    except (OSError, subprocess.SubprocessError):
        return None
