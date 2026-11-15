"""Generated, committed files ("generate, commit, check", spike lesson 2).

Each generator computes the file content in memory. `curatrix gen` writes it; `curatrix check`
compares it with the committed file (CK-D1, CK-D2, CK-D4). All paths come from checks.yaml.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from curatrix import cad, model as modelmod, needs as needsmod, pilot, stubs as stubsmod
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
    res = pilot.run(ws, [*libs, *files], export, raw, tmpdir=tmp)
    (tmp / "pilot.log").write_text(res.log + "\n")
    if not res.ok:
        raise GenError(f"the Pilot reported {res.errors} error(s); see {ws.rel(tmp / 'pilot.log')}:\n{res.log[-3000:]}")
    data = json.loads(raw.read_text())
    compact = modelmod.compact(data, modelmod.top_packages(libs))
    mjson = Output(cfg.resolve(s.get("json", "generated/model.json")), modelmod.dumps(compact), log=res.log)
    m = modelmod.Model(compact)
    doc, findings = modelmod.to_needs(m, f"{cfg.repo.name}-model", modelmod.source_map(files, cfg.repo))
    nout = Output(cfg.resolve(s.get("needs", "generated/model-needs.json")), needsmod.dumps(doc), findings)
    return mjson, nout, res


def model_needs_from_json(cfg: ChecksConfig) -> Output:
    """model-needs.json from the committed model.json (no Java needed)."""
    s = cfg.section("model") or {}
    mj = cfg.resolve(s.get("json", "generated/model.json"))
    m = modelmod.Model.load(mj)
    files = cfg.globs(s.get("files") or [])
    doc, findings = modelmod.to_needs(m, f"{cfg.repo.name}-model", modelmod.source_map(files, cfg.repo))
    return Output(cfg.resolve(s.get("needs", "generated/model-needs.json")), needsmod.dumps(doc), findings)


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

    for sch in cfg.globs(s.get("kicad") or []):
        add(*cad.kicad_needs(cad.kicad_items(sch, cfg.repo)))
    for fc in cfg.globs(s.get("freecad") or []):
        add(*cad.freecad_needs(fc, str(fc.resolve().relative_to(cfg.repo.resolve()))))
    return Output(cfg.resolve(s.get("needs", "generated/cad-needs.json")),
                  needsmod.dumps(needsmod.doc(needs, f"{cfg.repo.name}-cad")), findings)


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
    for sch in cfg.globs(s.get("kicad") or []):
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
    """Compare old and new generated needs files; keep tombstones for deleted, unretired needs."""
    rp = retired_path(cfg)
    current = needsmod.load(rp) if rp.exists() else {}
    msgs: list[str] = []
    new_all: dict[str, dict] = {}
    for o in generated:
        old = needsmod.load(o.path) if o.path.exists() else {}
        new = needsmod.needs_of(json.loads(o.text))
        new_all.update(new)
        current, m = needsmod.update_tombstones(old, new, current)
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
