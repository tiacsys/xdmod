"""`curatrix check <repo> --stage local|pr|full|baseline [--no-cad] [--only ...] [--json]` (checks.md §3).

Runs the built-in checks a repo's checks.yaml switches on, plus its `commands`, for one stage.
Writes logs to build/<area>/checks/ and a summary JSON (build/<area>/checks/summary.json) for
agents and CI comments, and prints the command that reproduces each failure.

Status of a check: pass | fail (error level: the stage fails) | warn | report | skip.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from curatrix import cad, checkcfg, docs as docsmod, gen, graph, ids as idmod, limits, model as modelmod
from curatrix import domvariants, needs as needsmod, variants as varmod, views as viewsmod

ALL = ("local", "pr", "full", "baseline")


@dataclass
class Result:
    id: str
    name: str
    status: str = "pass"
    level: str = "error"
    findings: list[str] = field(default_factory=list)
    log: str = ""
    repro: str = ""
    seconds: float = 0.0


@dataclass
class Ctx:
    ws: object
    repo: object
    cfg: checkcfg.ChecksConfig
    stage: str
    no_cad: bool
    base: Path | None
    out: Path
    results: dict = field(default_factory=dict)
    graph: graph.Graph | None = None
    graph_findings: list | None = None

    def repro(self, cid: str) -> str:
        extra = " --no-cad" if self.no_cad else ""
        return f"curatrix check {self.repo.name} --stage {self.stage}{extra} --only {cid}"


# ------------------------------------------------------------------ built-in checks
# id -> (name, {stage: level}, section needed, cad, function name)
def _lv(levels: dict[str, str]) -> dict[str, str]:
    return levels


BUILTIN = [
    ("CK-A6", "docs build strict (zdocs, sphinx-needs schema: CK-A1-A3)", _lv({s: "error" for s in ALL}), "docs", False, "c_docs"),
    ("CK-A1", "links: unknown IDs (own graph check)", _lv({s: "error" for s in ALL}), "docs", False, "c_graph"),
    ("CK-A3", "IDs match the scheme and their need type", _lv({s: "error" for s in ALL}), "docs", False, "c_graph"),
    ("CK-B1", "every SYS-REQ refined or satisfied (R1)", _lv({"full": "error", "baseline": "error"}), "docs", False, "c_graph"),
    ("CK-B2", "every requirement verified (R2)", _lv({"full": "warning", "baseline": "warning"}), "docs", False, "c_graph"),
    ("CK-B3", "no links to retired needs (R4, grace until baseline)",
     _lv({"local": "warning", "pr": "warning", "full": "warning", "baseline": "error"}), "docs", False, "c_graph"),
    ("CK-B4", "variant rules F1, F2, V1-V5", _lv({s: "error" for s in ALL}), "model.variants", False, "c_variants"),
    ("CK-B8", "variants across levels: one variant per configuration and usage, in the model and in CAD",
     _lv({"local": "warning", "pr": "warning", "full": "warning"}), "variants", False, "c_domain_variants"),
    ("CK-B5", "no duplicate IDs across documents", _lv({"full": "error", "baseline": "error"}), "docs", False, "c_graph"),
    ("CK-B6", "stale evidence (R5a)", _lv({"full": "report", "baseline": "report"}), "docs", False, "c_stale"),
    ("CK-B7", "tombstones of deleted generated needs", _lv({"local": "warning", "pr": "warning"}), "generated", False, "c_tombstones"),
    ("CK-C1", "no placeholder IDs", _lv({s: "error" for s in ALL}), "ids", False, "c_placeholders"),
    ("CK-C2", "IDs in the sources are in the ledger", _lv({"local": "error", "pr": "error", "baseline": "error"}), "ids", False, "c_ledger"),
    ("CK-D1", "SysML stubs match the needs", _lv({"local": "error", "pr": "error", "baseline": "error"}), "stubs", False, "c_stubs"),
    ("CK-E1", "the Pilot parses the model (0 errors)", _lv({"local": "error", "pr": "error", "baseline": "error"}), "model", False, "c_model"),
    ("CK-D2", "model.json and model-needs.json match the model", _lv({"local": "error", "pr": "error", "baseline": "error"}), "model", False, "c_model"),
    ("CK-D3", "views match the model (content), fresh, uncompressed", _lv({"local": "error", "pr": "error", "baseline": "error"}), "views", False, "c_views"),
    ("CK-D4", "cad-needs.json matches the CAD files", _lv({"local": "error", "pr": "error", "baseline": "error"}), "cad", False, "c_cadneeds"),
    ("CK-D6", "code-needs.json matches the code (@xdid blocks, ZTEST comments)", _lv({"local": "error", "pr": "error", "baseline": "error"}), "code", False, "c_codeneeds"),
    ("CK-D5", "generated files record the pinned tool versions (provenance.json)",
     _lv({"local": "warning", "pr": "warning", "full": "warning", "baseline": "error"}), "provenance", False, "c_provenance"),
    ("CK-E4", "domain model conforms to its upstream model (ports, link types)",
     _lv({"local": "warning", "pr": "warning"}), "model.upstream", False, "c_conformance"),
    ("CK-E2", "requirement values agree with the sentence", _lv({"local": "warning", "pr": "warning", "baseline": "warning"}), "requirements", False, "c_ears"),
    ("CK-E3", "EARS pattern matches the sentence", _lv({"local": "warning", "pr": "warning", "baseline": "warning"}), "requirements", False, "c_ears"),
    ("CK-G1", "needs-diff against the base (change impact)", _lv({"pr": "report", "full": "report"}), "docs", False, "c_diff"),
    ("CK-G2", "suspect links against the last baseline (R7)", _lv({"full": "report", "baseline": "error"}), "docs", False, "c_diff"),
    ("CK-F6", "KiCad projects: one per folder, named like it; no KiCad files elsewhere",
     _lv({"local": "warning", "pr": "warning", "baseline": "warning"}), "cad.projects", False, "c_ee_projects"),
    ("CK-F7", "KiCad projects and harnesses 1:1 with the board and cable defs of the EE model",
     _lv({"local": "warning", "pr": "warning", "baseline": "warning"}), "cad.projects+model", False, "c_ee_one_to_one"),
    ("CK-D7", "connectors.json files match the KiCad schematics", _lv({"local": "warning", "pr": "warning"}),
     "cad.connectors", False, "c_connectors_fresh"),
    ("CK-D8", "connector extraction equals KiCad's XML netlist", _lv({"local": "warning", "baseline": "warning"}),
     "cad.connectors", True, "c_connectors_netlist"),
    ("CK-F1", "connectors and harness ends match the pin maps of the EE model (Port, pin numbers, net names)",
     _lv({"local": "warning", "pr": "warning", "baseline": "warning"}), "cad.connectors+model", False, "c_connectors_model"),
    ("CK-F4a", "KiCad ERC per project: errors excluded or accepted (Accepted-by)",
     _lv({"local": "warning", "baseline": "warning"}), "cad.projects", True, "c_erc"),
    ("CK-F4b", "KiCad DRC per board: errors excluded or accepted (Accepted-by); unrouted nets in one entry",
     _lv({"local": "warning", "baseline": "warning"}), "cad.projects", True, "c_drc"),
    ("CK-F8", "ERC and DRC severities equal the new-pcba template",
     _lv({"local": "warning", "pr": "warning", "baseline": "warning"}), "cad.projects", False, "c_severities"),
    ("CK-F9", "accepted.yaml well formed; entries and KiCad exclusions accepted by a human (Accepted-by)",
     _lv({"local": "warning", "pr": "warning", "baseline": "warning"}), "cad.acceptance", False, "c_acceptance"),
    ("CK-F10", "jobset rules: no Execute Command, outputs under ${XD_CAM_OUT}, variant jobs = template jobs",
     _lv({"local": "warning", "pr": "warning"}), "cad.projects", False, "c_jobset"),
    ("CK-F11", "XD_VERSION in a title-block comment of every sheet and board and in a silkscreen text",
     _lv({"local": "warning", "pr": "warning"}), "cad.projects", False, "c_version_variable"),
    ("CK-F14", "FreeCAD assemblies 1:1 with the assembly defs of the ME model; skeleton; no reference to a top document",
     _lv({"local": "warning", "pr": "warning", "baseline": "warning"}), "cad.freecad+model", False, "c_me_one_to_one"),
    ("CK-F15", "FreeCAD links per part or sub-assembly equal the usages (ME model and system model)",
     _lv({"local": "warning", "pr": "warning", "baseline": "warning"}), "cad.freecad+model", False, "c_link_counts"),
    ("CK-F3", "FreeCAD Params aliases and LCS placements equal the ME model (tolerance per kind)",
     _lv({"local": "warning", "pr": "warning", "baseline": "warning"}), "cad.freecad+model", False, "c_freecad_params"),
    ("CK-F12", "every BOM part has Manufacturer and MPN, or a Standard designation",
     _lv({"local": "warning", "pr": "warning"}), "cad.projects", False, "c_bom_fields"),
    ("CK-D9", "the plain-Python BOM equals kicad-cli sch export bom, every board and variant",
     _lv({"local": "warning", "baseline": "warning"}), "cad.projects", True, "c_bom_kicad"),
    ("CK-D10", "the local curatrix cam output of the current commit exists for every board",
     _lv({"local": "warning", "baseline": "warning"}), "cad.projects", True, "c_cam_output"),
    ("CK-F4c", "FreeCAD documents recompute without errors (FreeCADCmd); errors accepted (Accepted-by)",
     _lv({"local": "warning", "baseline": "warning"}), "cad.freecad", True, "c_recompute"),
    ("CK-F16", "every part shape (ME-PART) is valid solids (FreeCADCmd)",
     _lv({"local": "warning", "baseline": "warning"}), "cad.freecad", True, "c_solids"),
    ("CK-F17", "no overlap between direct children of an assembly, per variant; joined may touch; fasteners left out",
     _lv({"local": "warning", "baseline": "warning"}), "cad.freecad", True, "c_collisions"),
    ("CK-F18", "board models inside their space budget (a skip with its reason until task 5.28)",
     _lv({"local": "warning", "baseline": "warning"}), "cad.freecad", True, "c_space_budget"),
    ("CK-F19", "every printed part (PrintProfile) has a version mark (LCS with Role = version-emboss)",
     _lv({"local": "warning", "pr": "warning"}), "cad.freecad", False, "c_version_face"),
    ("CK-H1", ".FCStd uncompressed; drawio uncompressed", _lv({"local": "error", "pr": "error", "baseline": "error"}), None, False, "c_hygiene_compress"),
    ("CK-H2", "no build output inside the repo", _lv({"local": "error", "pr": "error"}), None, False, "c_hygiene_build"),
    ("CK-H3", "pins in requirements.txt / tools.yaml", _lv({"pr": "warning", "local": "warning"}), None, False, "c_pins"),
    ("CK-H4", "commit trailers on agent commits", _lv({"pr": "warning"}), None, False, "c_trailers"),
    ("CK-H5", "scripts/bootstrap.sh matches the xdmod template", _lv({s: "warning" for s in ALL}), "bootstrap_template", False, "c_bootstrap"),
    ("CK-H6", "checks.yaml lists exactly the checks the repo runs (expect:)", _lv({s: "error" for s in ALL}), None, False, "c_expect"),
    ("CK-H7", "PR size: hand-written lines and files against the base", _lv({"local": "warning", "pr": "warning"}), None, False, "c_pr_size"),
]

# Why a built-in check is off for a repo: the checks.yaml key it needs.
NEED_TEXT = {"model.variants": "model.variants: true", "model.upstream": "model.upstream", "generated": "a model, cad or code section",
             "requirements": "requirements: true and a docs section", "provenance": "a model section or cad.freecad_json",
             "views": "views and model sections",
             "variants": "a variants section (domain repos, with model.upstream)",
             "cad.projects": "cad.projects", "cad.projects+model": "cad.projects and a model section",
             "cad.connectors": "cad.projects and cad.connectors",
             "cad.connectors+model": "cad.projects, cad.connectors and a model section",
             "cad.freecad+model": "cad.freecad and a model section", "cad.freecad": "cad.freecad",
             "cad.acceptance": "cad.projects or cad.freecad"}


def enabled(cfg: checkcfg.ChecksConfig, need: str | None) -> bool:
    if need is None:
        return True
    if need == "model.variants":
        s = cfg.section("model")
        return bool(s and s.get("variants"))
    if need == "model.upstream":
        return bool((cfg.section("model") or {}).get("upstream"))
    if need == "generated":
        return any(cfg.section(x) for x in ("model", "cad", "code"))
    if need == "requirements":
        return bool(cfg.raw.get("requirements")) and cfg.section("docs") is not None
    if need == "provenance":
        return cfg.section("model") is not None or bool((cfg.section("cad") or {}).get("freecad_json"))
    if need == "views":
        return cfg.section("views") is not None and cfg.section("model") is not None
    if need == "cad.projects":
        return bool((cfg.section("cad") or {}).get("projects"))
    if need in ("cad.connectors", "cad.connectors+model"):
        c = cfg.section("cad") or {}
        return bool(c.get("projects") and c.get("connectors")) and (need == "cad.connectors" or cfg.section("model") is not None)
    if need == "cad.freecad":
        return bool((cfg.section("cad") or {}).get("freecad"))
    if need == "cad.acceptance":
        c = cfg.section("cad") or {}
        return bool(c.get("projects") or c.get("freecad"))
    if need == "cad.freecad+model":
        return bool((cfg.section("cad") or {}).get("freecad")) and cfg.section("model") is not None
    if need == "cad.projects+model":
        return bool((cfg.section("cad") or {}).get("projects")) and cfg.section("model") is not None
    return cfg.section(need) is not None


# ---------------------------------------------------------------- implementations
def c_docs(ctx: Ctx, r: Result):
    res = docsmod.build(ctx.ws, ctx.repo.path, ctx.cfg.area)
    r.log = ctx.ws.rel(res.log)
    if not res.ok:
        r.findings = [f"strict mode: {res.strict_mode}", res.summary or "docs build failed"]


def _graph(ctx: Ctx):
    if ctx.graph_findings is None:
        files = gen.docs_needs_json(ctx.ws, ctx.cfg)
        ctx.graph = graph.load(files) if files else graph.Graph({})
        ctx.graph_findings = graph.check(ctx.graph, ctx.stage) if files else []
        if not files:
            ctx.graph_findings = [graph.Finding("CK-A1", "error", "-", "no needs.json in the docs build (run CK-A6 first)")]
    return ctx.graph_findings


def c_graph(ctx: Ctx, r: Result):
    fs = [f for f in _graph(ctx) if f.rule == r.id]
    r.findings = [str(f) for f in fs]


def c_stale(ctx: Ctx, r: Result):
    _graph(ctx)
    pins = {x.name: x.sha for x in ctx.ws.repos if x.sha}
    if not pins:
        r.level = "error"             # a report would let the stage pass without judging evidence
        r.findings = ["no pinned SHAs: `west list` gave none (no west workspace, or it failed); "
                      "stale evidence cannot be judged"]
        return
    r.findings = [str(f) for f in graph.stale_evidence(ctx.graph, pins)]


def c_variants(ctx: Ctx, r: Result):
    s = ctx.cfg.section("model") or {}
    mj = ctx.cfg.resolve(s.get("json", "generated/model.json"))
    if not mj.exists():
        r.findings = [f"{ctx.ws.rel(mj)} missing; run `curatrix gen model {ctx.repo.name}`"]
        return
    res = varmod.check(modelmod.Model.load(mj))
    r.findings = list(res.errors)
    (ctx.out / "variants.log").write_text("\n".join(res.notes + res.errors + [res.summary()]) + "\n")
    r.log = ctx.ws.rel(ctx.out / "variants.log")


def c_tombstones(ctx: Ctx, r: Result):
    rp = gen.retired_path(ctx.cfg)
    if rp.exists():
        r.findings = [f"tombstone {nid} ({t.get('title')}), retired on {t.get('retired_on')}: kept until the next baseline"
                      for nid, t in sorted(needsmod.load(rp).items())]


def c_placeholders(ctx: Ctx, r: Result):
    r.findings = idmod.check_placeholders(idmod.source_files(ctx.repo.path, ctx.cfg.ids_exclude), ctx.repo.path)


def c_ledger(ctx: Ctx, r: Result):
    lp = ctx.cfg.ledger
    if not lp.exists():
        r.findings = [f"{ctx.ws.rel(lp)} missing"]
        return
    r.findings = idmod.check_ledger(idmod.source_files(ctx.repo.path, ctx.cfg.ids_exclude), idmod.Ledger.load(lp), ctx.repo.path)


def _compare(o: gen.Output, what: str, ws, fix_cmd: str) -> list[str]:
    if not o.path.exists():
        return [f"{ws.rel(o.path)} missing; run `{fix_cmd}`"]
    if o.differs():
        return [f"{ws.rel(o.path)} does not match {what}; run `{fix_cmd}` and commit"]
    return []


def c_stubs(ctx: Ctx, r: Result):
    try:
        o = gen.stubs(ctx.ws, ctx.cfg)
    except gen.GenError as e:
        r.findings = [str(e)]
        return
    r.findings = _compare(o, "the needs", ctx.ws, f"curatrix gen stubs {ctx.repo.name}")


def c_model(ctx: Ctx, r: Result):
    key = "_model"
    if key not in ctx.results:
        try:
            ctx.results[key] = gen.model(ctx.ws, ctx.cfg)
        except (gen.GenError, FileNotFoundError) as e:
            ctx.results[key] = e
    res = ctx.results[key]
    r.log = ctx.ws.rel(ctx.ws.build(ctx.cfg.area) / "model" / "pilot.log")
    if isinstance(res, Exception):
        r.findings = [str(res)]
        return
    mjson, mneeds, _ = res
    if r.id == "CK-E1":
        return
    fix = f"curatrix gen model {ctx.repo.name}"
    r.findings = _compare(mjson, "the model", ctx.ws, fix) + _compare(mneeds, "the model", ctx.ws, fix) + mneeds.findings


def c_conformance(ctx: Ctx, r: Result):
    """CK-E4 (XD-ADR-0132): on the committed model.json and the upstream ones, no Java."""
    s = ctx.cfg.section("model") or {}
    mj = ctx.cfg.resolve(s.get("json", "generated/model.json"))
    if not mj.exists():
        r.findings = [f"{ctx.ws.rel(mj)} missing; run `curatrix gen model {ctx.repo.name}`"]
        return
    ups, r.findings = gen.upstream_models(ctx.cfg)
    if not r.findings:
        r.findings = modelmod.conformance(modelmod.Model.load(mj), ups)


def c_domain_variants(ctx: Ctx, r: Result):
    """CK-B8 (XD-ADR-0136): the domain variants against the upstream model and the CAD files,
    plain Python. The computed table "configuration -> variant per usage" goes into the log."""
    s = ctx.cfg.section("model") or {}
    mj = ctx.cfg.resolve(s.get("json", "generated/model.json"))
    if not mj.exists():
        r.findings = [f"{ctx.ws.rel(mj)} missing; run `curatrix gen model {ctx.repo.name}`"]
        return
    if not s.get("upstream"):
        r.findings = ["CK-B8 needs model.upstream: the published system model the variants serve"]
        return
    ups, r.findings = gen.upstream_models(ctx.cfg)
    if r.findings:
        return
    c = ctx.cfg.section("cad") or {}
    v = ctx.cfg.section("variants") or {}
    z = v.get("zephyr") or []
    from curatrix import eeprojects
    kicad = eeprojects.root_sheets(ctx.cfg)     # cad.kicad and the root sheets of cad.projects
    freecad = ctx.cfg.globs(c.get("freecad") or [])
    r.findings, rows = domvariants.check(modelmod.Model.load(mj), ups, kicad, freecad,
                                         ctx.cfg.globs([z] if isinstance(z, str) else z))
    log = ctx.out / "variants-across-levels.md"
    log.write_text("# Configuration -> variant per usage (computed, CK-B8)\n\n" + domvariants.table_markdown(rows)
                   + ("\n## Findings\n\n" + "\n".join(f"- {f}" for f in r.findings) + "\n" if r.findings else ""))
    r.log = ctx.ws.rel(log)


def c_views(ctx: Ctx, r: Result):
    s = ctx.cfg.section("views") or {}
    ms = ctx.cfg.section("model") or {}
    mj = ctx.cfg.resolve(s.get("model") or ms.get("json", "generated/model.json"))
    vdir = ctx.cfg.resolve(s.get("dir", "views"))
    if not mj.exists():
        r.findings = [f"{ctx.ws.rel(mj)} missing; run `curatrix gen model {ctx.repo.name}`"]
        return
    m = modelmod.Model.load(mj)
    expected = {}
    for v in viewsmod.discover(m):
        try:
            expected[viewsmod.file_name(v)] = viewsmod.to_mxfile(viewsmod.graph(m, v))
        except viewsmod.ViewError as e:
            r.findings.append(str(e))
    files = sorted(vdir.glob("*.drawio.svg")) if vdir.is_dir() else []
    for name in sorted(set(expected) - {f.name for f in files}):
        r.findings.append(f"{name}: view missing; run `curatrix views build {ctx.repo.name}`")
    for f in files:
        r.findings += viewsmod.check_file(f, expected.get(f.name))


def c_provenance(ctx: Ctx, r: Result):
    from curatrix import provenance
    cfg = ctx.cfg
    ms = cfg.section("model")
    if ms is not None:
        r.findings += provenance.check(ctx.ws, cfg, [cfg.resolve(ms.get("json", "generated/model.json")),
                                                     cfg.resolve(ms.get("needs", "generated/model-needs.json"))], "model")
        vs = cfg.section("views")
        if vs is not None:
            vdir = cfg.resolve(vs.get("dir", "views"))
            r.findings += provenance.check(ctx.ws, cfg, sorted(vdir.glob("*.drawio.svg")) if vdir.is_dir() else [], "views")
    # FreeCAD JSON with shapes: only files that have a record (without --shape it is plain Python)
    doc = provenance.load(cfg)
    shaped = [cfg.repo / f for f, e in doc["files"].items() if e.get("made_by") == provenance.KINDS["freecad-shapes"][0]]
    r.findings += provenance.check(ctx.ws, cfg, shaped, "freecad-shapes")
    r.findings += provenance.stale(cfg)


def c_cadneeds(ctx: Ctx, r: Result):
    o = gen.cad_needs(ctx.ws, ctx.cfg)
    r.findings = o.findings + _compare(o, "the CAD files", ctx.ws, f"curatrix gen cad-needs {ctx.repo.name}")


def c_ee_projects(ctx: Ctx, r: Result):
    """CK-F6 (task 5.17): the folder rule of the KiCad projects."""
    from curatrix import eeprojects
    r.findings = eeprojects.folder_findings(ctx.cfg)


def c_ee_one_to_one(ctx: Ctx, r: Result):
    """CK-F7 (XD-ADR-0128, XD-ADR-0135): board defs of the committed model.json <-> pcba/ projects."""
    from curatrix import eeprojects
    s = ctx.cfg.section("model") or {}
    mj = ctx.cfg.resolve(s.get("json", "generated/model.json"))
    if not mj.exists():
        r.findings = [f"{ctx.ws.rel(mj)} missing; run `curatrix gen model {ctx.repo.name}`"]
        return
    m = modelmod.Model.load(mj)
    r.findings = eeprojects.one_to_one(ctx.cfg, m)
    from curatrix import harness
    if harness.patterns(ctx.cfg):        # cable defs <-> harness/<name>/ (task 5.22)
        r.findings += harness.one_to_one(ctx.cfg, m)


def _model_or_finding(ctx: Ctx, r: Result):
    s = ctx.cfg.section("model") or {}
    mj = ctx.cfg.resolve(s.get("json", "generated/model.json"))
    if not mj.exists():
        r.findings = [f"{ctx.ws.rel(mj)} missing; run `curatrix gen model {ctx.repo.name}`"]
        return None
    return modelmod.Model.load(mj)


def c_me_one_to_one(ctx: Ctx, r: Result):
    """CK-F14 (XD-ADR-0128, XD-ADR-0137): assembly defs of the committed model.json <-> FreeCAD documents."""
    from curatrix import meassemblies
    m = _model_or_finding(ctx, r)
    if m is not None:
        ups, missing = gen.upstream_models(ctx.cfg)
        r.findings = missing + meassemblies.one_to_one(ctx.cfg, m, upstream=ups)


def c_link_counts(ctx: Ctx, r: Result):
    """CK-F15 (XD-ADR-0138): FreeCAD links vs the usages of the ME model and of the upstream system model."""
    from curatrix import meassemblies
    m = _model_or_finding(ctx, r)
    if m is not None:
        ups, missing = gen.upstream_models(ctx.cfg)
        r.findings = missing + meassemblies.link_counts(ctx.cfg, m, ups)


def c_freecad_params(ctx: Ctx, r: Result):
    """CK-F3 (XD-ADR-0137): skeleton Params and LCS with Port against the committed model.json."""
    from curatrix import meparams
    m = _model_or_finding(ctx, r)
    if m is not None:
        r.findings = meparams.check(ctx.cfg, m)


def c_connectors_fresh(ctx: Ctx, r: Result):
    """CK-D7 (task 5.18): regenerate generated/<project>.connectors.json and compare (plain Python)."""
    fix = f"curatrix gen connectors {ctx.repo.name}"
    for o in gen.connectors(ctx.ws, ctx.cfg):
        r.findings += o.findings + _compare(o, "the KiCad schematic", ctx.ws, fix)
    r.findings += gen.stale_connectors(ctx.cfg)


def c_connectors_netlist(ctx: Ctx, r: Result):
    """CK-D8 (P5-15): the plain-Python extraction against `kicad-cli sch export netlist --format kicadxml`."""
    from curatrix import connectors as conn, eeprojects
    out = ctx.out / "netlists"
    out.mkdir(parents=True, exist_ok=True)
    for pr in eeprojects.discover(ctx.cfg):
        if not pr.sch.is_file():
            continue
        xml = out / f"{pr.name}.net.xml"
        argv = ["kicad-cli", "sch", "export", "netlist", "--format", "kicadxml", "-o", str(xml), str(pr.sch)]
        p = limits.run(argv, "kicad-cli", ctx.ws, capture_output=True, text=True)
        if p.returncode or not xml.is_file():
            r.level = "error"
            r.findings.append(f"{pr.name}: kicad-cli sch export netlist failed (exit {p.returncode} "
                              f"{limits.explain_rc(p.returncode)}): {(p.stdout + p.stderr)[-300:]}")
            continue
        mine = conn.connectors(conn.netlist(pr.sch))
        r.findings += conn.compare(mine, conn.from_xml(xml), ctx.ws.rel(pr.sch))
    r.log = ctx.ws.rel(out)


def c_connectors_model(ctx: Ctx, r: Result):
    """CK-F1 (task 5.18): the committed connectors.json of every pcba/ project against the pin maps
    of the committed model.json (plain Python)."""
    from curatrix import connectors as conn, eeprojects
    s = ctx.cfg.section("model") or {}
    mj = ctx.cfg.resolve(s.get("json", "generated/model.json"))
    if not mj.exists():
        r.findings = [f"{ctx.ws.rel(mj)} missing; run `curatrix gen model {ctx.repo.name}`"]
        return
    m = modelmod.Model.load(mj)
    for pr in eeprojects.discover(ctx.cfg):
        if pr.kind != "pcba":
            continue
        f = gen.connectors_path(ctx.cfg, pr.name)
        if not f.is_file():
            r.findings.append(f"{ctx.ws.rel(f)} missing; run `curatrix gen connectors {ctx.repo.name}`")
            continue
        r.findings += conn.conformance(json.loads(f.read_text()), (pr.variables().get("TraceID") or "").strip(), m,
                                       str(pr.sch.relative_to(ctx.repo.path)))
    from curatrix import harness
    for h in harness.discover(ctx.cfg):  # harness ends against the ports of both sides (task 5.22)
        r.findings += harness.conformance(h, m, str(h.yml.relative_to(ctx.repo.path)))


def _erc_drc(ctx: Ctx, r: Result, kind: str):
    """CK-F4a (kind erc, every project) / CK-F4b (drc, every pcba/ board): kicad-cli JSON, evaluated
    against the KiCad exclusions and accepted.yaml (XD-ADR-0126). Warnings go to the report only."""
    from curatrix import eeprojects, ercdrc
    out = ctx.out / "erc-drc"
    acc = ercdrc.Acceptors(ctx.repo.path)
    lines: list[str] = []
    for pr in eeprojects.discover(ctx.cfg):
        if not pr.sch.is_file() or (kind == "drc" and (pr.kind != "pcba" or not pr.pro.with_suffix(".kicad_pcb").is_file())):
            continue
        problems, listed, err = ercdrc.check_project(ctx.ws, ctx.cfg, pr, kind, out, acc)
        if err:
            r.level = "error"
            r.findings.append(err)
            continue
        r.findings += problems
        lines += problems + [f"{pr.name}: {x}" for x in listed]
    out.mkdir(parents=True, exist_ok=True)
    rep = out / f"{kind}.txt"
    rep.write_text("".join(f"{x}\n" for x in lines) or "no findings\n")
    r.log = ctx.ws.rel(rep)


def c_erc(ctx: Ctx, r: Result):
    _erc_drc(ctx, r, "erc")


def c_drc(ctx: Ctx, r: Result):
    _erc_drc(ctx, r, "drc")


def c_severities(ctx: Ctx, r: Result):
    """CK-F8 (XD-ADR-0126): ERC/DRC severities of each project equal the new-pcba template's."""
    from curatrix import eeprojects, ercdrc
    tmpl = ctx.ws.xdmod / "templates" / "kicad-pcba" / "pcba.kicad_pro"
    acc = ercdrc.Acceptors(ctx.repo.path)
    for pr in eeprojects.discover(ctx.cfg):
        entries, _ = ercdrc.project_entries(ctx.cfg, pr, acc)
        rel = pr.pro.relative_to(ctx.repo.path)
        for rule, text in ercdrc.severity_diffs(pr.pro, tmpl):
            e = next((e for e in entries if e.check == "CK-F8" and e.rule == rule), None)
            if e is None:
                r.findings.append(f"{rel}: {text}; set it back or accept it in {ercdrc.ACCEPTED} (check: CK-F8, rule: {rule})")
            elif e.status != "accepted":
                r.findings.append(f"{rel}: {text}; {ercdrc.ACCEPTED} {e.label()} is a proposal ({e.why})")
        diffs = {rule for rule, _ in ercdrc.severity_diffs(pr.pro, tmpl)}
        r.findings += [f"{(pr.folder / ercdrc.ACCEPTED).relative_to(ctx.repo.path)} {e.label()} matches no severity "
                       f"difference; remove it" for e in entries if e.check == "CK-F8" and e.rule not in diffs]


def c_acceptance(ctx: Ctx, r: Result):
    """CK-F9 (XD-ADR-0126): accepted.yaml entries and KiCad exclusions; accepted only by a human
    commit with `Accepted-by:`, no agent mark and nothing else changed; else a proposal."""
    from curatrix import eeprojects, ercdrc
    acc = ercdrc.Acceptors(ctx.repo.path)
    for pr in eeprojects.discover(ctx.cfg):
        entries, errs = ercdrc.project_entries(ctx.cfg, pr, acc)
        r.findings += errs
        rel = (pr.folder / ercdrc.ACCEPTED).relative_to(ctx.repo.path)
        r.findings += [f"{rel} {e.label()}: proposal, not accepted ({e.why})" for e in entries if e.status != "accepted"]
        rel_pro = str(pr.pro.relative_to(ctx.repo.path))
        for kind, key, comment in ercdrc.exclusions(pr.pro):
            ok, why = acc.exclusion(rel_pro, key)
            if not ok:
                r.findings.append(f"{rel_pro}: {kind.upper()} exclusion {key.split('|', 1)[0]} ({comment or 'no comment'}): "
                                  f"proposal, not accepted ({why})")
    if (ctx.cfg.section("cad") or {}).get("freecad"):          # ME: assemblies/<name>/accepted.yaml (task 5.25)
        from curatrix import mechecks
        per, errs = mechecks.folder_entries(ctx.cfg, acc)
        r.findings += errs
        for folder, entries in sorted(per.items()):
            r.findings += [f"{folder}/{ercdrc.ACCEPTED} {e.label()}: proposal, not accepted ({e.why})"
                           for e in entries if e.status != "accepted"]


def _me(ctx: Ctx, r: Result, check: str):
    """CK-F4c, CK-F16, CK-F17, CK-F18 (task 5.25, XD-ADR-0126): one FreeCADCmd run for all four
    (mechecks), findings against assemblies/<name>/accepted.yaml; a report per check."""
    from curatrix import ercdrc, mechecks
    out = ctx.out / "me-checks"
    out.mkdir(parents=True, exist_ok=True)
    try:
        res = mechecks.run(ctx.ws, ctx.cfg, out)
    except mechecks.MeCheckError as e:
        r.level = "error"
        r.findings = [str(e)]
        return
    if check == "CK-F18":            # a skip with its reason until task 5.28 gives the budget its form
        b = mechecks.boards(res)
        r.status = "skip"
        r.findings = [f"board model(s) {', '.join(b)} placed, but the SYS-IF space budget has no form yet (co-design "
                      f"task 5.28): not checked" if b else
                      "no board model in any assembly (a link to an object with an EE-PCBA TraceID): nothing to check"]
        return
    entries, _ = mechecks.folder_entries(ctx.cfg, ercdrc.Acceptors(ctx.repo.path))   # format: CK-F9
    o = mechecks.evaluate(ctx.cfg, check, mechecks.findings(ctx.cfg, res, check), entries)
    r.findings = o.problems
    rep = out / f"{check}.txt"
    rep.write_text("".join(f"{x}\n" for x in o.problems + o.listed) or "no findings\n")
    r.log = ctx.ws.rel(rep)


def c_recompute(ctx: Ctx, r: Result):
    _me(ctx, r, "CK-F4c")


def c_solids(ctx: Ctx, r: Result):
    _me(ctx, r, "CK-F16")


def c_collisions(ctx: Ctx, r: Result):
    _me(ctx, r, "CK-F17")


def c_space_budget(ctx: Ctx, r: Result):
    _me(ctx, r, "CK-F18")


def c_version_face(ctx: Ctx, r: Result):
    """CK-F19 (XD-ADR-0143): every printed part has its version mark (plain Python)."""
    from curatrix import mecam
    r.findings = mecam.version_faces(ctx.cfg)


def c_jobset(ctx: Ctx, r: Result):
    """CK-F10 (XD-ADR-0142): the jobset of every pcba/ project against the CAM rules and the shared
    template (plain Python)."""
    from curatrix import cam, domvariants, eeprojects
    for pr in eeprojects.discover(ctx.cfg):
        if pr.kind == "pcba":
            r.findings += [f"{pr.folder.relative_to(ctx.repo.path)}: {t}"
                           for _, t in cam.jobset_findings(ctx.ws, pr, domvariants.kicad_variants(pr.pro))]


def c_version_variable(ctx: Ctx, r: Result):
    """CK-F11 (XD-ADR-0142): the version variable in the frames and on the silkscreen (plain Python)."""
    from curatrix import cam, eeprojects
    for pr in eeprojects.discover(ctx.cfg):
        if pr.kind == "pcba":
            r.findings += [f"{pr.folder.relative_to(ctx.repo.path)}/{t}" for t in cam.version_findings(pr)]


def _boards(ctx: Ctx):
    from curatrix import eeprojects
    return [pr for pr in eeprojects.discover(ctx.cfg) if pr.kind == "pcba" and pr.sch.is_file()]


def c_bom_fields(ctx: Ctx, r: Result):
    """CK-F12 (XD-ADR-0129): Manufacturer and MPN on every BOM part of every board (plain Python)."""
    from curatrix import bom
    for pr in _boards(ctx):
        r.findings += bom.field_findings(bom.read(pr.sch), domvariants.kicad_variants(pr.pro),
                                         str(pr.sch.relative_to(ctx.repo.path)))


def c_bom_kicad(ctx: Ctx, r: Result):
    """CK-D9 (P5-15): the plain-Python BOM reader against `kicad-cli sch export bom [--variant]`."""
    from curatrix import bom
    out = ctx.out / "bom"
    out.mkdir(parents=True, exist_ok=True)
    for pr in _boards(ctx):
        parts = bom.read(pr.sch)
        for v in [None, *domvariants.kicad_variants(pr.pro)]:
            csv_ = out / f"{pr.name}.{v or 'base'}.csv"
            csv_.unlink(missing_ok=True)
            p = limits.run(bom.kicad_argv(pr.sch, csv_, v), "kicad-cli", ctx.ws, capture_output=True, text=True)
            if p.returncode or not csv_.is_file():
                r.level = "error"
                r.findings.append(f"{pr.name}: kicad-cli sch export bom{' --variant ' + v if v else ''} failed (exit "
                                  f"{p.returncode} {limits.explain_rc(p.returncode)}): {(p.stdout + p.stderr)[-300:]}")
                continue
            r.findings += bom.compare(bom.mine(parts, v), bom.from_kicad_csv(csv_),
                                      f"{pr.sch.relative_to(ctx.repo.path)} ({'variant ' + v if v else 'base'})")
    r.log = ctx.ws.rel(out)


def c_cam_output(ctx: Ctx, r: Result):
    """CK-D10 (XD-ADR-0129): the board document's local output (`curatrix cam`) is there for the
    commit the repo is at; never in CI."""
    from curatrix import cam
    for pr in _boards(ctx):
        rec, _, why = cam.current(ctx.ws.build(ctx.cfg.area) / "cam", pr.name, ctx.repo.path, pr.folder)
        if rec is None:
            r.findings.append(f"{pr.name}: {why}; the board document shows no renderings, schematic or ERC/DRC "
                              f"findings; run `curatrix cam {ctx.repo.name} {pr.name}`")


def c_codeneeds(ctx: Ctx, r: Result):
    o = gen.code_needs(ctx.ws, ctx.cfg)
    r.findings = o.findings + _compare(o, "the code", ctx.ws, f"curatrix gen code-needs {ctx.repo.name}")


EARS_START = {"ubiquitous": r"^(the|a|an|each|every)\b", "event": r"^when\b", "state": r"^while\b",
              "optional": r"^where\b", "unwanted": r"^if\b"}


# CK-E2: numbers in a sentence. Thousands separators (1,000 / 1 000 / 1'000), decimals, a sign,
# ranges and "a ± b". Compared as numbers, so 2000000 matches "2,000,000 Hz". Digits inside IDs
# (SYS-REQ-0012) are not numbers. The unit must stand right after the value, or after the next
# number of a range ("between 0.5 and 2.5 ms", "10–20 Hz").
_NUM = r"[-+−]?(?:\d{1,3}(?:[,'  ]\d{3})+(?![\d])|\d+)(?:\.\d+)?"
NUMBER = re.compile(r"(?<![\w.])(?<![A-Za-z]-)" + _NUM + r"(?![\d])")
PLUSMINUS = re.compile(r"(?:(?<![\w.])(" + _NUM + r")\s*(?:°[A-Z]?|[A-Za-zµ%]+)?\s*)?(?:±|\+/-)\s*(" + _NUM + r")")
RANGE_TO_NEXT = re.compile(r"\s*(?:°[A-Z]?|[A-Za-zµ%]+)?\s*(?:and|to|or|–|—|-|\.\.\.?)\s*")
# unit symbol -> names that may stand in the sentence instead (a name may be plural)
UNIT_NAMES = {"ms": ["millisecond"], "s": ["second"], "us": ["µs", "microsecond"], "µs": ["microsecond"],
              "min": ["minute"], "h": ["hour"], "Hz": ["hertz"], "kHz": ["kilohertz"], "MHz": ["megahertz"],
              "g": ["gram"], "kg": ["kilogram"], "mm": ["millimetre", "millimeter"], "cm": ["centimetre", "centimeter"],
              "m": ["metre", "meter"], "°": ["degree"], "deg": ["degree", "°"], "°C": ["degrees Celsius", "degree Celsius"],
              "K": ["kelvin"], "V": ["volt"], "mV": ["millivolt"], "A": ["ampere", "amp"], "mA": ["milliampere", "milliamp"],
              "W": ["watt"], "N": ["newton"], "Nm": ["newton metre", "newton meter", "N·m", "N m"],
              "N·m": ["newton metre", "newton meter", "Nm"], "%": ["percent", "per cent"],
              "rpm": ["revolutions per minute"], "bit": ["bit"], "B": ["byte"]}


def _norm(text: str) -> str:
    return text.replace("μ", "µ")                 # Greek mu -> micro sign


def _num(s: str) -> float:
    return float(re.sub(r"[,'  ]", "", s).replace("−", "-"))


def numbers_in(text: str) -> list[float]:
    """Every number in a sentence, plus a+b and a-b for each "a ± b" (and +b, -b for a bare "± b")."""
    text = _norm(text)
    out = [_num(m.group(0)) for m in NUMBER.finditer(text)]
    for m in PLUSMINUS.finditer(text):
        b = _num(m.group(2))
        if m.group(1):
            a = _num(m.group(1))
            out += [a + b, a - b]
        else:
            out += [b, -b]
    return out


def unit_at(unit: str, text: str, pos: int) -> bool:
    """The unit (symbol, or a name, plural allowed for names) stands at text[pos:] after spaces."""
    rest = _norm(text[pos:]).lstrip()
    for i, u in enumerate([unit, *UNIT_NAMES.get(unit, [])]):
        u = _norm(u)
        name = i > 0 and u.replace(" ", "").isalpha() and len(u) > 2
        tail = r"(?:e?s)?" if name else ""
        if re.match(re.escape(u) + tail + r"(?![A-Za-z])", rest, re.I if name else 0):
            return True
    return False


def _value_with_unit(x: float, unit: str | None, text: str) -> bool:
    text = _norm(text)
    same = lambda y: abs(x - y) <= 1e-9 * max(1.0, abs(x))  # noqa: E731
    for m in NUMBER.finditer(text):
        if not same(_num(m.group(0))):
            continue
        if not unit or unit_at(unit, text, m.end()):
            return True
        r = RANGE_TO_NEXT.match(text, m.end())          # unit after the next number of a range
        if r:
            n2 = NUMBER.match(text, r.end())
            if n2 and unit_at(unit, text, n2.end()):
                return True
    for m in PLUSMINUS.finditer(text):                  # a ± b: the unit after a or after b
        b = _num(m.group(2))
        vals = [_num(m.group(1)) + b, _num(m.group(1)) - b] if m.group(1) else [b, -b]
        if any(same(v) for v in vals) and (not unit or unit_at(unit, text, m.end())
                                           or (m.group(1) and unit_at(unit, text, m.start(1) + len(m.group(1))))):
            return True
    return False


def ears_value_findings(nid: str, n: dict, text: str) -> list[str]:
    """CK-E2 for one requirement: each of min/max/nominal occurs as a number in the sentence (any
    order, any format), with its unit (symbol or name) right after it or after the end of its range."""
    out = []
    unit = n.get("unit") or None
    for f in ("min", "max", "nominal"):
        v = n.get(f)
        if v in (None, ""):
            continue
        try:
            x = float(v)
        except (TypeError, ValueError):
            out.append(f"{nid}: {f} = {v!r} is not a number")
            continue
        if _value_with_unit(x, unit, text):
            continue
        if any(abs(x - y) <= 1e-9 * max(1.0, abs(x)) for y in numbers_in(text)):
            out.append(f"{nid}: {f} = {x:g} is in the sentence, but not followed by its unit {unit!r}")
        else:
            out.append(f"{nid}: {f} = {x:g} does not appear as a number in the sentence")
    return out


def c_ears(ctx: Ctx, r: Result):
    _graph(ctx)
    for nid, n in sorted((ctx.graph.needs if ctx.graph else {}).items()):
        if n.get("is_external") or n.get("type") not in graph.REQ_TYPES or n.get("status") == "retired":
            continue
        text = re.sub(r"\s+", " ", (n.get("content") or "")).strip()
        if r.id == "CK-E2":
            r.findings += ears_value_findings(nid, n, text)
        else:
            e = n.get("ears")
            if not e:
                continue
            if "shall" not in text.lower():
                r.findings.append(f"{nid}: no 'shall' in the requirement sentence")
            pat = EARS_START.get(e)
            if pat and not re.search(pat, text.lower()):
                r.findings.append(f"{nid}: ears={e} but the sentence does not start like that pattern")


def c_diff(ctx: Ctx, r: Result):
    if ctx.base is None:
        r.status = "skip"
        r.findings = ["no base given (--base DIR with the needs.json files of main / the last baseline)"]
        return
    _graph(ctx)
    old = needsmod.load_built(sorted(Path(ctx.base).rglob("needs.json")) or sorted(Path(ctx.base).rglob("*.json")))
    new = needsmod.load_built(gen.docs_needs_json(ctx.ws, ctx.cfg))
    text, n = graph.diff_report(old, new, str(ctx.base), ctx.ws.rel(ctx.ws.build(ctx.cfg.area) / "docs"))
    rep = ctx.out / "needs-diff.md"
    rep.write_text(text)
    r.log = ctx.ws.rel(rep)
    if n:
        r.findings = [f"{n} suspect or dangling link(s); see {ctx.ws.rel(rep)}"]


def c_hygiene_compress(ctx: Ctx, r: Result):
    for f in idmod.source_files(ctx.repo.path):
        if f.suffix == ".FCStd":
            bad = cad.freecad_compressed(f)
            if bad:
                r.findings.append(f"{f.relative_to(ctx.repo.path)}: compressed entries {bad[:3]}; save with "
                                  f"CompressionLevel 0 (`curatrix launch freecad`)")
        elif f.name.endswith(".drawio.svg") or f.suffix == ".drawio":
            try:
                text = f.read_text()
                content = viewsmod.read_svg(f)[0] if f.suffix == ".svg" else text
                if content and viewsmod.is_compressed(content):
                    r.findings.append(f"{f.relative_to(ctx.repo.path)}: compressed diagram; run `curatrix views normalize`")
            except Exception as e:  # noqa: BLE001
                r.findings.append(f"{f.relative_to(ctx.repo.path)}: unreadable ({e})")


BUILD_PATTERNS = re.compile(r"(^|/)(build|_build|__pycache__|\.pytest_cache)/|\.pyc$|(^|/)deploy/html/")


def c_hygiene_build(ctx: Ctx, r: Result):
    try:
        p = subprocess.run(["git", "-C", str(ctx.repo.path), "ls-files", "-co", "--exclude-standard"],
                           capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        r.findings = [f"git ls-files failed: {e}"]
        return
    if p.returncode:
        r.findings = [f"git ls-files failed (exit {p.returncode}): {p.stderr.strip()[:200]}"]
        return
    out = p.stdout.splitlines()
    r.findings = [f"{f}: build output inside the repo (outputs go to build/<area>/, D46)" for f in out if BUILD_PATTERNS.search(f)]


def c_pins(ctx: Ctx, r: Result):
    req = ctx.repo.path / "requirements.txt"
    if req.exists():
        for i, ln in enumerate(req.read_text().splitlines(), 1):
            s = ln.split("#")[0].strip()
            if s and not s.startswith("-") and "==" not in s and "@" not in s:
                r.findings.append(f"requirements.txt:{i}: {s!r} is not pinned (==)")
    tf = ctx.repo.path / "tools.yaml"
    if tf.exists():
        from curatrix import tools
        try:
            tools.parse(tf)
        except Exception as e:  # noqa: BLE001
            r.findings.append(f"tools.yaml: {e}")


AGENT_TRAILER = re.compile(r"^Co-Authored-By: .+ <noreply@anthropic\.com>\s*$", re.M | re.I)
# an agent commit names Claude Code or anthropic.com (a human message that mentions "Claude" is not one)
AGENT_MARK = re.compile(r"Claude Code|anthropic\.com|Co-Authored-By: Claude", re.I)


def c_trailers(ctx: Ctx, r: Result):
    """CK-H4: agent commits since the PR base carry the agent trailer (D51). Agents commit under the
    owner's identity, so a commit is an agent commit when its message names Claude or anthropic.com;
    human commits are not asked for a trailer (task 5.7)."""
    base = _base_ref(ctx.repo.path)
    if base is None:
        r.status = "skip"
        r.findings = ["no base branch to compare with (set XD_BASE_REF)"]
        return
    try:
        out = subprocess.run(["git", "-C", str(ctx.repo.path), "log", "--format=%H%x00%B%x01", f"{base}..HEAD"],
                             capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        r.findings = [f"git log failed: {e}"]
        return
    if out.returncode:
        r.findings = [f"git log {base}..HEAD failed: {out.stderr.strip()[:200]}"]
        return
    for rec in out.stdout.split("\x01"):
        if not rec.strip():
            continue
        sha, _, body = rec.strip().partition("\x00")
        if AGENT_MARK.search(body) and not AGENT_TRAILER.search(body):
            r.findings.append(f"{sha[:10]}: an agent commit without the trailer "
                              f"`Co-Authored-By: <agent> <noreply@anthropic.com>` (D51)")


def c_bootstrap(ctx: Ctx, r: Result):
    copy = ctx.cfg.bootstrap_copy
    tmpl = ctx.ws.xdmod / "templates" / "bootstrap.sh"
    if not copy.exists():
        r.findings = [f"{ctx.ws.rel(copy)} missing (copy {ctx.ws.rel(tmpl)})"]
    elif copy.read_text() != tmpl.read_text():
        r.findings = [f"{ctx.ws.rel(copy)} differs from {ctx.ws.rel(tmpl)} (D118); copy the template again"]


def builtin_ids(cfg: checkcfg.ChecksConfig) -> list[str]:
    """The built-in checks a repo's checks.yaml switches on, in any stage."""
    return [cid for cid, _, _, need, _, _ in BUILTIN if enabled(cfg, need)]


def off_checks(cfg: checkcfg.ChecksConfig) -> list[tuple[str, str]]:
    """(check id, why it is off) for every built-in check this checks.yaml switches off."""
    return [(cid, f"needs {NEED_TEXT.get(need, f'a {need} section')}") for cid, _, _, need, _, _ in BUILTIN
            if not enabled(cfg, need)]


def c_expect(ctx: Ctx, r: Result):
    want = ctx.cfg.expect
    have = set(builtin_ids(ctx.cfg)) | {c.id for c in ctx.cfg.commands}
    if want is None:
        r.findings = ["checks.yaml has no `expect:` list; add the IDs this repo runs: " + ", ".join(sorted(have))]
        return
    known = {b[0] for b in BUILTIN} | {c.id for c in ctx.cfg.commands}
    for cid in sorted(set(want) - known):
        r.findings.append(f"{cid}: expected, but no such check (built-in or in `commands`)")
    off = dict(off_checks(ctx.cfg))
    for cid in sorted((set(want) & known) - have):
        r.findings.append(f"{cid}: expected, but off: it {off.get(cid, 'is not configured')} in checks.yaml")
    for cid in sorted(have - set(want)):
        r.findings.append(f"{cid}: runs, but is not in `expect:` (add it, so that losing it later is an error)")


GENERATED = ("generated/", "model/generated/", "views/")


def _base_ref(path: Path) -> str | None:
    """The ref a PR is measured against: XD_BASE_REF if set; in CI the base that `curatrix ci
    siblings` fetched (refs/remotes/xd-ci/base; west clones have no `origin`); else the PR's base
    branch (GITHUB_BASE_REF) or main, on the first remote that has it, or locally."""
    import os
    if os.environ.get("XD_BASE_REF"):
        cands = [os.environ["XD_BASE_REF"]]
    else:
        branch = os.environ.get("GITHUB_BASE_REF") or "main"
        remotes = subprocess.run(["git", "-C", str(path), "remote"], capture_output=True, text=True,
                                 timeout=30).stdout.split()
        cands = ["refs/remotes/xd-ci/base", *[f"{rm}/{branch}" for rm in ["origin", *remotes]], branch]
    for ref in cands:
        if subprocess.run(["git", "-C", str(path), "rev-parse", "-q", "--verify", f"{ref}^{{commit}}"],
                          capture_output=True, timeout=30).returncode == 0:
            return ref
    return None


def is_generated(rel: str, cfg: checkcfg.ChecksConfig) -> bool:
    """A committed generated file (written by `curatrix gen` / `views build`), not counted as hand-written."""
    if rel.startswith(GENERATED) or rel.endswith(".drawio.svg"):
        return True
    outs = []
    for sec, keys in (("model", ("json", "needs")), ("stubs", ("out",)), ("cad", ("needs", "freecad_json")),
                      ("views", ("dir",))):
        v = cfg.section(sec) or {}
        outs += [str(v[k]).rstrip("/") for k in keys if v.get(k)]
    return any(rel == o or rel.startswith(o + "/") for o in outs)


def c_pr_size(ctx: Ctx, r: Result):
    base = _base_ref(ctx.repo.path)
    if base is None:
        r.status = "skip"
        r.findings = ["no base branch to compare with (set XD_BASE_REF)"]
        return
    p = subprocess.run(["git", "-C", str(ctx.repo.path), "diff", "--numstat", "--no-renames", f"{base}...HEAD"],
                       capture_output=True, text=True, timeout=60)
    if p.returncode:
        r.findings = [f"git diff against {base} failed: {p.stderr.strip()[:200]}"]
        return
    lines = files = 0
    for ln in p.stdout.splitlines():
        add, rm, rel = (ln.split("\t") + ["", "", ""])[:3]
        if is_generated(rel, ctx.cfg) or add == "-":
            continue
        files += 1
        lines += int(add) + int(rm)
    max_lines, max_files = ctx.cfg.pr_size
    if lines > max_lines or files > max_files:
        r.findings = [f"{lines} hand-written lines in {files} files against {base} (limits {max_lines} / {max_files}): "
                      f"one SYSMOD step or one tool feature per PR; consider a stack of smaller PRs"]


def c_command(ctx: Ctx, r: Result, cmd: checkcfg.Command):
    subst = {"{ws}": str(ctx.ws.root), "{repo}": str(ctx.repo.path), "{build}": str(ctx.out),
             "{area}": ctx.cfg.area, "{python}": str(ctx.ws.venv / "bin" / "python")}

    def sub(s):
        for k, v in subst.items():
            s = s.replace(k, v)
        return s
    argv = [sub(a) for a in cmd.run]
    logf = ctx.out / f"{cmd.id}.log"
    with open(logf, "w") as fh:
        fh.write(f"$ {' '.join(argv)}\n")
        fh.flush()
        p = limits.run(argv, cmd.use, ctx.ws, cwd=sub(cmd.cwd), stdout=fh, stderr=subprocess.STDOUT)
    r.log = ctx.ws.rel(logf)
    if p.returncode:
        tail = logf.read_text(errors="replace").splitlines()[-15:]
        r.findings = [f"exit {p.returncode} {limits.explain_rc(p.returncode)}".strip(), *tail]


# ------------------------------------------------------------------ runner
def plan(cfg: checkcfg.ChecksConfig, stage: str, no_cad: bool, only: list[str] | None):
    items = []
    for cid, name, levels, need, is_cad, fn in BUILTIN:
        if not enabled(cfg, need):
            continue
        selected = only and any(cid == o or cid.startswith(o) for o in only)
        if stage not in levels and not selected:
            continue
        if only and not selected:
            continue
        items.append((cid, name, levels.get(stage, "error"), is_cad, fn, None))
    first = []          # commands with before_docs: true run before every built-in check
    for c in cfg.commands:
        selected = only and any(c.id == o or c.id.startswith(o) for o in only)
        if (stage in c.stages and not only) or selected:
            (first if c.before_docs else items).append((c.id, c.name, c.level, c.cad, "c_command", c))
    return first + items


def run(ws, repo, stage: str = "local", no_cad: bool = False, only: list[str] | None = None,
        base: Path | None = None, log=print) -> tuple[bool, dict]:
    cfg = checkcfg.load(repo.path / "checks.yaml", ws.root)
    out = ws.build(cfg.area) / "checks"
    out.mkdir(parents=True, exist_ok=True)
    # outputs that belong to one check run (e.g. preview test results for the docs): never left
    # over from an earlier run, so a docs build in this run cannot show an old result
    shutil.rmtree(out / "preview", ignore_errors=True)
    ctx = Ctx(ws, repo, cfg, stage, no_cad, base, out)
    items = plan(cfg, stage, no_cad, only)
    results: list[Result] = []
    need_docs = any(fn in ("c_graph", "c_stale", "c_stubs", "c_ears", "c_diff") for _, _, _, _, fn, _ in items)
    if need_docs and not any(i[0] == "CK-A6" for i in items) and cfg.section("docs") is not None \
            and not gen.docs_needs_json(ws, cfg):
        pos = sum(1 for i in items if i[5] is not None and i[5].before_docs)
        items.insert(pos, next((cid, n, lv.get(stage, "error"), c, fn, None)
                             for cid, n, lv, need, c, fn in BUILTIN if cid == "CK-A6"))
    if not items:
        (out / "summary.json").write_text(json.dumps({"repo": repo.name, "area": cfg.area, "stage": stage,
                                                      "ok": False, "checks": [], "error": "empty plan"}, indent=2) + "\n")
        raise checkcfg.ConfigError(f"{repo.name}: no check runs at stage {stage}"
                                   f"{' with --only ' + ','.join(only) if only else ''}; an empty plan never passes")
    off = off_checks(cfg)
    log(f"curatrix check {repo.name} --stage {stage}{' --no-cad' if no_cad else ''}: {len(items)} check(s)")
    if off and not only:
        log("  off for this repo: " + "; ".join(f"{cid} ({why})" for cid, why in off))
    for cid, name, level, is_cad, fn, cmd in items:
        r = Result(cid, name, level=level, repro=ctx.repro(cid))
        t0 = time.time()
        if is_cad and no_cad:
            r.status = "skip"
            r.findings = ["needs CAD tools (--no-cad)"]
        else:
            try:
                if cmd is not None:
                    c_command(ctx, r, cmd)
                else:
                    globals()[fn](ctx, r)
            except Exception as e:  # noqa: BLE001 - one broken check must not hide the others
                r.findings = [f"internal error: {type(e).__name__}: {e}"]
                r.level = "error"
            if r.status != "skip":
                r.status = "pass" if not r.findings else {"error": "fail", "warning": "warn", "report": "report"}[r.level]
        if r.status == "skip" and stage == "baseline" and r.level == "error":
            r.status = "fail"              # a baseline must not pass on a check that did not run
            r.findings.append("skipped at the baseline stage: an error-level check must run here")
        r.seconds = round(time.time() - t0, 1)
        results.append(r)
        mark = {"pass": "ok  ", "fail": "FAIL", "warn": "warn", "report": "info", "skip": "skip"}[r.status]
        log(f"  {mark} {cid:6} {name} ({r.seconds} s)")
        for f in r.findings[:25]:
            log(f"         {f}")
        if len(r.findings) > 25:
            log(f"         ... {len(r.findings) - 25} more (see {ws.rel(out / 'summary.json')})")
        if r.status == "fail":
            log(f"         reproduce: {r.repro}" + (f"   log: {r.log}" if r.log else ""))
    ok = not any(r.status == "fail" for r in results)
    summary = {"repo": repo.name, "area": cfg.area, "stage": stage, "no_cad": no_cad, "ok": ok,
               "checks": [asdict(r) for r in results], "off": [{"id": c, "why": w} for c, w in off]}
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    log(f"{'CHECK PASSED' if ok else 'CHECK FAILED'} ({repo.name}, stage {stage}); summary: {ws.rel(out / 'summary.json')}")
    return ok, summary


def main_json(summary: dict) -> None:
    json.dump(summary, sys.stdout, indent=2)
    sys.stdout.write("\n")
