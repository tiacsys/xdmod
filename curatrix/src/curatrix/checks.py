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
    ("CK-A4", "no orphans (R3)", _lv({s: "error" for s in ALL}), "docs", False, "c_graph"),
    ("CK-A5", "HIL results carry firmware hash and SHAs (R5)", _lv({s: "error" for s in ALL}), "docs", False, "c_graph"),
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
    ("CK-E2", "requirement values agree with the sentence", _lv({"local": "error", "pr": "error", "baseline": "error"}), "requirements", False, "c_ears"),
    ("CK-E3", "EARS pattern matches the sentence", _lv({"local": "warning", "pr": "warning", "baseline": "warning"}), "requirements", False, "c_ears"),
    ("CK-G1", "needs-diff against the base (change impact)", _lv({"pr": "report", "full": "report"}), "docs", False, "c_diff"),
    ("CK-G2", "suspect links against the last baseline (R7)", _lv({"full": "report", "baseline": "error"}), "docs", False, "c_diff"),
    ("CK-H1", ".FCStd uncompressed; drawio uncompressed", _lv({"local": "error", "pr": "error", "baseline": "error"}), None, False, "c_hygiene_compress"),
    ("CK-H2", "no build output inside the repo", _lv({"local": "error", "pr": "error"}), None, False, "c_hygiene_build"),
    ("CK-H3", "pins in requirements.txt / tools.yaml", _lv({"pr": "warning", "local": "warning"}), None, False, "c_pins"),
    ("CK-H4", "commit trailers on agent commits", _lv({"pr": "warning"}), None, False, "c_trailers"),
    ("CK-H5", "scripts/bootstrap.sh matches the xdmod template", _lv({s: "warning" for s in ALL}), "bootstrap_template", False, "c_bootstrap"),
]


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


def c_cadneeds(ctx: Ctx, r: Result):
    o = gen.cad_needs(ctx.ws, ctx.cfg)
    r.findings = o.findings + _compare(o, "the CAD files", ctx.ws, f"curatrix gen cad-needs {ctx.repo.name}")


EARS_START = {"ubiquitous": r"^(the|a|an|each|every)\b", "event": r"^when\b", "state": r"^while\b",
              "optional": r"^where\b", "unwanted": r"^if\b"}


def c_ears(ctx: Ctx, r: Result):
    _graph(ctx)
    for nid, n in sorted((ctx.graph.needs if ctx.graph else {}).items()):
        if n.get("is_external") or n.get("type") not in graph.REQ_TYPES or n.get("status") == "retired":
            continue
        text = re.sub(r"\s+", " ", (n.get("content") or "")).strip()
        if r.id == "CK-E2":
            unit = n.get("unit")
            for f in ("min", "max", "nominal"):
                v = n.get(f)
                if v in (None, ""):
                    continue
                num = f"{float(v):g}"
                pat = re.escape(num) + (r"\s*" + re.escape(unit) if unit else "")
                if not re.search(r"(?<![\d.])" + pat + r"(?![\w])", text):
                    r.findings.append(f"{nid}: {f} = {num}{' ' + unit if unit else ''} does not appear in the sentence")
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
        out = subprocess.run(["git", "-C", str(ctx.repo.path), "ls-files", "-co", "--exclude-standard"],
                             capture_output=True, text=True, timeout=60).stdout.splitlines()
    except (OSError, subprocess.SubprocessError):
        out = []
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
    except (OSError, subprocess.SubprocessError):
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
    log(f"curatrix check {repo.name} --stage {stage}{' --no-cad' if no_cad else ''}: {len(items)} check(s)")
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
               "checks": [asdict(r) for r in results]}
    (out / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    log(f"{'CHECK PASSED' if ok else 'CHECK FAILED'} ({repo.name}, stage {stage}); summary: {ws.rel(out / 'summary.json')}")
    return ok, summary


def main_json(summary: dict) -> None:
    json.dump(summary, sys.stdout, indent=2)
    sys.stdout.write("\n")
