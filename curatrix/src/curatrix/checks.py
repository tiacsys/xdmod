"""`curatrix check <repo> --stage local|pr|full|baseline [--no-cad] [--only ...] [--json]` (checks.md §3).

Runs the built-in checks a repo's checks.yaml switches on, plus its `commands`, for one stage.
Writes logs to build/<area>/checks/ and a summary JSON (build/<area>/checks/summary.json) for
agents and CI comments, and prints the command that reproduces each failure.

Status of a check: pass | fail (error level: the stage fails) | warn | report | skip.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from curatrix import cad, checkcfg, docs as docsmod, gen, graph, ids as idmod, limits, model as modelmod
from curatrix import needs as needsmod, variants as varmod, views as viewsmod

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
    ("CK-D5", "generated files record the pinned tool versions (provenance.json)",
     _lv({"local": "warning", "pr": "warning", "full": "warning", "baseline": "error"}), "provenance", False, "c_provenance"),
    ("CK-E2", "requirement values agree with the sentence", _lv({"local": "warning", "pr": "warning", "baseline": "warning"}), "requirements", False, "c_ears"),
    ("CK-E3", "EARS pattern matches the sentence", _lv({"local": "warning", "pr": "warning", "baseline": "warning"}), "requirements", False, "c_ears"),
    ("CK-G1", "needs-diff against the base (change impact)", _lv({"pr": "report", "full": "report"}), "docs", False, "c_diff"),
    ("CK-G2", "suspect links against the last baseline (R7)", _lv({"full": "report", "baseline": "error"}), "docs", False, "c_diff"),
    ("CK-H1", ".FCStd uncompressed; drawio uncompressed", _lv({"local": "error", "pr": "error", "baseline": "error"}), None, False, "c_hygiene_compress"),
    ("CK-H2", "no build output inside the repo", _lv({"local": "error", "pr": "error"}), None, False, "c_hygiene_build"),
    ("CK-H3", "pins in requirements.txt / tools.yaml", _lv({"pr": "warning", "local": "warning"}), None, False, "c_pins"),
    ("CK-H4", "commit trailers on agent commits", _lv({"pr": "warning"}), None, False, "c_trailers"),
    ("CK-H5", "scripts/bootstrap.sh matches the xdmod template", _lv({s: "warning" for s in ALL}), "bootstrap_template", False, "c_bootstrap"),
    ("CK-H6", "checks.yaml lists exactly the checks the repo runs (expect:)", _lv({s: "error" for s in ALL}), None, False, "c_expect"),
    ("CK-H7", "PR size: hand-written lines and files against the base", _lv({"local": "warning", "pr": "warning"}), None, False, "c_pr_size"),
]

# Why a built-in check is off for a repo: the checks.yaml key it needs.
NEED_TEXT = {"model.variants": "model.variants: true", "generated": "a model or cad section",
             "requirements": "requirements: true and a docs section", "provenance": "a model section or cad.freecad_json",
             "views": "views and model sections"}


def enabled(cfg: checkcfg.ChecksConfig, need: str | None) -> bool:
    if need is None:
        return True
    if need == "model.variants":
        s = cfg.section("model")
        return bool(s and s.get("variants"))
    if need == "generated":
        return any(cfg.section(x) for x in ("model", "cad"))
    if need == "requirements":
        return bool(cfg.raw.get("requirements")) and cfg.section("docs") is not None
    if need == "provenance":
        return cfg.section("model") is not None or bool((cfg.section("cad") or {}).get("freecad_json"))
    if need == "views":
        return cfg.section("views") is not None and cfg.section("model") is not None
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


def c_cadneeds(ctx: Ctx, r: Result):
    o = gen.cad_needs(ctx.ws, ctx.cfg)
    r.findings = o.findings + _compare(o, "the CAD files", ctx.ws, f"curatrix gen cad-needs {ctx.repo.name}")


EARS_START = {"ubiquitous": r"^(the|a|an|each|every)\b", "event": r"^when\b", "state": r"^while\b",
              "optional": r"^where\b", "unwanted": r"^if\b"}


# CK-E2: numbers in a sentence. Thousands separators (1,000 / 1 000 / 1'000), decimals, a sign,
# and "a ± b". Compared as numbers, so 2000000 matches "2,000,000 Hz" and 2e+06.
_NUM = r"[-+−]?(?:\d{1,3}(?:[,' \u202f]\d{3})+(?![\d])|\d+)(?:\.\d+)?"
NUMBER = re.compile(r"(?<![\w.])" + _NUM + r"(?![\d])")
PLUSMINUS = re.compile(r"(?<![\w.])(" + _NUM + r")\s*(?:°|[A-Za-zµ%]+)?\s*(?:±|\+/-)\s*(" + _NUM + r")")
# unit symbol -> names that may stand in the sentence instead (singular stems; plurals match too)
UNIT_NAMES = {"ms": ["millisecond"], "s": ["second"], "us": ["microsecond"], "µs": ["microsecond"],
              "min": ["minute"], "h": ["hour"], "Hz": ["hertz"], "kHz": ["kilohertz"], "MHz": ["megahertz"],
              "g": ["gram"], "kg": ["kilogram"], "mm": ["millimetre", "millimeter"], "cm": ["centimetre", "centimeter"],
              "m": ["metre", "meter"], "°": ["degree", "deg"], "deg": ["degree", "°"], "V": ["volt"], "mV": ["millivolt"],
              "A": ["ampere", "amp"], "mA": ["milliampere", "milliamp"], "W": ["watt"], "N": ["newton"],
              "Nm": ["newton metre", "newton meter", "N·m", "N m"], "N·m": ["newton metre", "newton meter", "Nm"],
              "%": ["percent", "per cent"], "rpm": ["revolutions per minute"], "bit": ["bit"], "B": ["byte"]}


def numbers_in(text: str) -> list[float]:
    """Every number in a sentence, plus a+b and a-b for each "a ± b"."""
    out = [float(m.group(0).replace("−", "-").replace(",", "").replace("'", "").replace(" ", "").replace("\u202f", ""))
           for m in NUMBER.finditer(text)]
    for m in PLUSMINUS.finditer(text):
        a, b = (float(re.sub(r"[,' \u202f]", "", x).replace("−", "-")) for x in (m.group(1), m.group(2)))
        out += [a + b, a - b]
    return out


def unit_in(unit: str, text: str) -> bool:
    for u in [unit, *UNIT_NAMES.get(unit, [])]:
        if u in ("°", "%"):
            if u in text:
                return True
        elif re.search(r"(?<![A-Za-z])" + re.escape(u) + r"(?:e?s)?(?![A-Za-z])", text, re.I if len(u) > 3 else 0):
            return True
    return False


def ears_value_findings(nid: str, n: dict, text: str) -> list[str]:
    """CK-E2 for one requirement: each of min/max/nominal occurs as a number in the sentence (any
    order, any format), and the unit occurs once, as symbol or name."""
    out = []
    nums = numbers_in(text)
    unit = n.get("unit")
    for f in ("min", "max", "nominal"):
        v = n.get(f)
        if v in (None, ""):
            continue
        try:
            x = float(v)
        except (TypeError, ValueError):
            out.append(f"{nid}: {f} = {v!r} is not a number")
            continue
        if not any(abs(x - y) <= 1e-9 * max(1.0, abs(x)) for y in nums):
            out.append(f"{nid}: {f} = {x:g} does not appear as a number in the sentence")
    if unit and any(n.get(f) not in (None, "") for f in ("min", "max", "nominal")) and not unit_in(unit, text):
        out.append(f"{nid}: unit {unit!r} does not appear in the sentence (as symbol or name)")
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


def c_trailers(ctx: Ctx, r: Result):
    base = "origin/main"
    try:
        out = subprocess.run(["git", "-C", str(ctx.repo.path), "log", "--format=%H%x00%B%x01", f"{base}..HEAD"],
                             capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        r.findings = [f"git log failed: {e}"]
        return
    if out.returncode:
        r.status = "skip"
        r.findings = [f"no {base} to compare with"]
        return
    for rec in out.stdout.split("\x01"):
        if not rec.strip():
            continue
        sha, _, body = rec.strip().partition("\x00")
        if "Co-Authored-By:" not in body:
            r.findings.append(f"{sha[:10]}: no Co-Authored-By trailer (fine for a human commit; agents must add it, D51)")


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
    for c in cfg.commands:
        selected = only and any(c.id == o or c.id.startswith(o) for o in only)
        if (stage in c.stages and not only) or selected:
            items.append((c.id, c.name, c.level, c.cad, "c_command", c))
    return items


def run(ws, repo, stage: str = "local", no_cad: bool = False, only: list[str] | None = None,
        base: Path | None = None, log=print) -> tuple[bool, dict]:
    cfg = checkcfg.load(repo.path / "checks.yaml", ws.root)
    out = ws.build(cfg.area) / "checks"
    out.mkdir(parents=True, exist_ok=True)
    ctx = Ctx(ws, repo, cfg, stage, no_cad, base, out)
    items = plan(cfg, stage, no_cad, only)
    results: list[Result] = []
    need_docs = any(fn in ("c_graph", "c_stale", "c_stubs", "c_ears", "c_diff") for _, _, _, _, fn, _ in items)
    if need_docs and not any(i[0] == "CK-A6" for i in items) and cfg.section("docs") is not None \
            and not gen.docs_needs_json(ws, cfg):
        items.insert(0, next((cid, n, lv.get(stage, "error"), c, fn, None)
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
