"""curatrix command line (command-layer.md §3). Run every command from the workspace root (D67);
curatrix finds the root itself, so it also works from a subfolder."""
from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

from curatrix import __version__


def _ws():
    from curatrix.ws import Workspace
    return Workspace()


def _repo(ws, name: str | None):
    if name:
        return ws.repo(name)
    r = ws.repo_of_cwd()
    if r is None:
        raise SystemExit("curatrix: name the repo (or run from inside it)")
    return r


def _integration_repo(ws) -> str:
    """The INT domain repo (`<project>-integration`, repo-layouts.md), which holds the evidence branch."""
    names = [r.name for r in ws.framework_repos if r.name.endswith("-integration")]
    if len(names) != 1:
        raise SystemExit(f"curatrix: name the evidence repo with --repo (integration repos found: {names or 'none'})")
    return names[0]


def _cfg(ws, repo):
    from curatrix import checkcfg
    return checkcfg.load(repo.path / "checks.yaml", ws.root)


# ------------------------------------------------------------------ env / run / doctor
def cmd_env(a):
    ws = _ws()
    e = ws.env()
    path = e.pop("PATH")
    lines = []
    for k, v in sorted(e.items()):
        lines.append(f"set -gx {k} {shlex.quote(v)}" if a.shell == "fish" else f"export {k}={shlex.quote(v)}")
    lines.append(f"set -gx PATH {shlex.quote(path)} $PATH" if a.shell == "fish"
                 else f'export PATH={shlex.quote(path)}:"$PATH"')
    print("\n".join(lines))
    return 0


def cmd_run(a):
    from curatrix import limits
    ws = _ws()
    cmd = a.cmd[1:] if a.cmd and a.cmd[0] == "--" else a.cmd
    if not cmd:
        raise SystemExit("usage: curatrix run [--use USE] [-m MEM] [-t TIME] -- COMMAND ...")
    lim = limits.resolve(a.use, ws, a.memory, a.timeout)
    if a.verbose:
        print(f"curatrix run: {limits.describe(lim)} [{limits.backend()}]", file=sys.stderr)
    env = limits.tool_env(ws, a.use, ws.run_env(), cmd)   # KiCad/FreeCAD: the workspace-local config
    rc = limits.norm_rc(subprocess.run(limits.wrap(cmd, lim), env=env, cwd=os.getcwd()).returncode)
    if rc in (124, 137):
        print(f"curatrix run: {limits.explain_rc(rc)}", file=sys.stderr)
    return rc


def cmd_fixtures(a):
    from curatrix import fixtures
    ok, _ = fixtures.run(_ws())
    return 0 if ok else 1


def cmd_limits(a):
    from curatrix import limits
    ws = _ws()
    t = limits.load_table(ws)
    print(f"backend: {limits.backend()}   (override file: {ws.rel(ws.state / 'limits.yaml')})")
    for use in sorted(t["uses"]):
        lim = limits.resolve(use, ws, table=t)
        print(f"  {use:11} memory {lim.memory:5} timeout {lim.timeout or 'none':5} vmem {lim.vmem or 'none'}")
    return 0


def cmd_doctor(a):
    from curatrix import setup
    return setup.doctor(_ws(), ci=a.ci)


def cmd_bootstrap(a):
    from curatrix import setup
    return setup.bootstrap(_ws(), a.role, adopt=a.adopt, skip_west=a.no_west, run_doctor=not a.no_doctor)


def cmd_update(a):
    from curatrix import setup
    return setup.update(_ws(), adopt=a.adopt)


def cmd_launch(a):
    from curatrix import setup
    return setup.launch(_ws(), a.tool, a.args)


def cmd_work(a):
    from curatrix import work
    ws = _ws()
    try:
        if a.action == "start":
            if not a.args:
                raise SystemExit("usage: curatrix work start <branch> <repo>...")
            work.start(ws, a.args[0], a.args[1:], base=a.base or "main")
        elif a.action == "done":
            if len(a.args) != 1:
                raise SystemExit("usage: curatrix work done <branch> [--force] [--delete-branch]")
            work.done(ws, a.args[0], a.force, a.delete_branch)
        else:
            for m in work.listing(ws):
                print(f"  {m['branch']:30} {', '.join(m['repos']):40} build: {m['build']}")
    except work.WorkError as e:
        print(f"curatrix work: {e}", file=sys.stderr)
        return 1
    return 0


def cmd_ci(a):
    from curatrix import ci
    ws = _ws()
    if a.action == "siblings":
        if not a.branch:
            raise SystemExit("curatrix ci siblings: --branch is required")
        print(f"curatrix ci siblings: branch {a.branch!r}, under check {a.repo} @ {a.sha[:12] or '-'}")
        ci.siblings(ws, a.branch, a.repo, a.sha)
        return 0
    if a.action == "base":
        out = Path(a.out) if a.out else ws.build("ci") / "base"
        return 0 if ci.fetch_base(ws, a.repo, out, a.version) else 1
    return 2


def cmd_evidence(a):
    """Run records and the evidence branch (4.5a, 4.6; D57, D60, D73, D131)."""
    from curatrix import evidence as ev
    ws = _ws()
    if a.action == "validate":
        rec = json.loads(Path(a.target).read_text())
        errs = ev.validate(rec)
        for e in errs:
            print(f"  {e}")
        print(f"{a.target}: {'INVALID' if errs else 'valid'} ({ev.SCHEMA_ID})")
        return 1 if errs else 0
    if a.action == "preview":
        if not a.target or not a.out:
            raise SystemExit("usage: curatrix evidence preview TWISTER_DIR -o FILE [--tests DIR] [--config SYS-CFG-nnnn] "
                             "[--commit-of REPO]")
        out = Path(a.out)
        stamp = ev.stamp_path(out)
        out.unlink(missing_ok=True)              # no old preview may pose as this run's result
        stamp.unlink(missing_ok=True)
        if not (Path(a.target) / "twister.json").is_file():
            print(f"  no Twister output in {a.target}: no preview test results")
            return 0
        try:
            doc = ev.preview_needs(Path(a.target), [Path(d) for d in a.tests] if a.tests else None, a.config,
                                   project=f"{Path(a.target).name}-preview")
        except (ValueError, KeyError, ev.EvidenceError) as e:
            print(f"curatrix evidence preview: {a.target}/twister.json is not a usable Twister report ({e})", file=sys.stderr)
            return 1
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
        stamp.write_text(json.dumps(ev.preview_stamp(Path(a.target), Path(a.commit_of) if a.commit_of else None),
                                    indent=2, sort_keys=True) + "\n")
        n = doc["versions"][""]["needs"]
        print(f"  {len(n)} preview TR need(s) -> {ws.rel(out)} (stamp {ws.rel(stamp)})")
        return 0
    repo = ws.repo(a.repo or _integration_repo(ws))
    url = next((p["url"] for p in ev._west_projects(ws) if p["name"] == repo.name), "") if ws.has_west else ""
    url = url or str(repo.path)
    if a.action == "read":
        ref = a.ref or f"refs/heads/{a.branch}"
        if not a.ref and ev._git(["fetch", "-q", "--no-tags", url, f"+refs/heads/{a.branch}:refs/remotes/xd-evidence/{a.branch}"],
                                 repo.path, ws, check=False).returncode == 0:
            ref = f"refs/remotes/xd-evidence/{a.branch}"
        recs = ev.load_records(repo.path, ref, ws)
        pins = {r.name: r.sha for r in ws.repos if r.sha}
        problems: list[str] = []
        doc = ev.to_needs(recs, pins, project=f"{repo.name}-evidence", problems=problems)
        for pr in problems:
            print(f"  {pr}", file=sys.stderr)
        out = Path(a.out) if a.out else ws.build(repo.name) / "evidence" / "tr-needs.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(doc, indent=2, sort_keys=True) + "\n")
        n = doc["versions"][""]["needs"]
        stale = sum(1 for x in n.values() if "stale" in x["tags"])
        print(f"  {len(recs)} record(s) on {ref}: {len(n)} TR need(s), {stale} stale -> {ws.rel(out)}")
        return 1 if problems else 0
    # record
    if not a.target or not a.config:
        raise SystemExit("usage: curatrix evidence record TWISTER_DIR --config SYS-CFG-nnnn [--kind sim|hil] ...")
    tdir = Path(a.target).resolve()
    overrides = dict(m.split("=", 1) for m in a.map or [])
    rec = ev.make_record(ws, tdir, a.config, a.kind, a.setup, [Path(d) for d in a.tests] if a.tests else None,
                         overrides, a.note or "", check_remote=not a.offline)
    print(f"  run {rec['run_id']}: {rec['kind']} {rec['platform']} {rec['config']}, firmware {rec['firmware']['sha256'][:16]}…, "
          f"{len(rec['results'])} result(s), {sum(1 for r in rec['results'] if r['test_case'])} traced")
    print(f"  evidence rule (D60): {'ok, against ' + rec['evidence']['base'] if rec['evidence']['ok'] else 'FAILED'}")
    for pr in rec["evidence"]["problems"]:
        print(f"    - {pr}")
    if a.dry_run:
        print(json.dumps(rec, indent=2, sort_keys=True))
        errs = ev.validate(rec)
        return 1 if errs else 0
    sha = ev.write(ws, rec, tdir, repo.path, url, a.branch, a.create, a.trailer or "")
    print(f"  push with: git -C {repo.rel} push {url} {a.branch}   ({sha[:12]})")
    return 0


# ------------------------------------------------------------------ docs / check
def cmd_docs(a):
    from curatrix import docs
    ws = _ws()
    if a.target == "full":
        mp = ws.manifest_path
        if mp is None:
            raise SystemExit("curatrix docs full: no west manifest repo")
        repo_dir, area = mp, "full"
    else:
        repo = _repo(ws, a.target)
        from curatrix import checkcfg
        area = checkcfg.load(repo.path / "checks.yaml", ws.root).area if (repo.path / "checks.yaml").exists() else repo.name
        repo_dir = repo.path
    res = docs.build(ws, repo_dir, area)
    print(res.summary or "")
    print(f"docs {area}: {'OK' if res.ok else 'FAILED'} [{res.strict_mode}]  log: {ws.rel(res.log)}")
    idx = docs.index_html(ws, area)
    if idx:
        print(f"open: {ws.rel(idx)}")
        if a.open:
            subprocess.Popen(["xdg-open", str(idx)], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return 0 if res.ok else 1


def cmd_check(a):
    from curatrix import checks
    ws = _ws()
    repo = _repo(ws, a.repo)
    only = [x.strip() for x in a.only.split(",")] if a.only else None
    logf = (lambda *x, **k: print(*x, file=sys.stderr, **k)) if a.json else print
    ok, summary = checks.run(ws, repo, a.stage, a.no_cad, only, Path(a.base) if a.base else None, log=logf)
    if a.json:
        checks.main_json(summary)
    return 0 if ok else 1


def cmd_trace(a):
    """A minimal trace report per SYS-REQ from the needs.json of the last docs build (task 5.10)."""
    from curatrix import trace
    ws = _ws()
    if a.target == "full":
        area = "full"
    else:
        repo = _repo(ws, a.target)
        area = _cfg(ws, repo).area
    files = sorted((ws.build(area) / "docs" / "deploy" / "html").glob("*/needs.json"))
    if not files:
        print(f"curatrix trace: no needs.json in {ws.rel(ws.build(area) / 'docs')}; run `curatrix docs {a.target}` first",
              file=sys.stderr)
        return 1
    out = Path(a.out) if a.out else ws.build(area) / "trace"
    s = trace.write(files, out, a.target, a.canary)
    if not s["canary_configs"]:
        print("  warning: no canary SYS-CFG found (tag `canary` or \"canary\" in the title; or --canary): "
              "nothing is left out of the coverage", file=sys.stderr)
    c = s["coverage"]
    print(f"  {c['requirements']} SYS-REQ (canary excluded: {len(s['canary'])}): {c['refined_or_satisfied']} refined or "
          f"satisfied, {c['with_test_case']} with a test case, {c['passed']} passed")
    print(f"  wrote {ws.rel(out / 'trace.md')}, {ws.rel(out / 'trace.html')}")
    return 0


# ------------------------------------------------------------------ gen
def cmd_gen(a):
    from curatrix import gen
    ws = _ws()
    if a.what == "freecad-json" and a.textconv:
        from curatrix import cad
        sem = cad.freecad_trace(Path(a.textconv), "")
        sem.pop("file", None)
        print(json.dumps(sem, indent=2, sort_keys=True))
        return 0
    repo = _repo(ws, a.repo)
    cfg = _cfg(ws, repo)
    outs, msgs, rc = [], [], 0
    made: list[tuple[str, list[Path], list[Path]]] = []    # (provenance kind, files made, files no longer tool-made)
    whats = ["stubs", "model", "cad-needs", "connectors", "code-needs", "freecad-json"] if a.what == "all" else [a.what]
    for what in whats:
        try:
            if what == "stubs":
                if cfg.section("stubs") is None and a.what == "all":
                    continue
                outs.append(gen.stubs(ws, cfg, [Path(x) for x in a.needs] if a.needs else None))
            elif what == "model":
                if cfg.section("model") is None and a.what == "all":
                    continue
                mjson, mneeds, res = gen.model(ws, cfg)
                print(f"  Pilot: {res.seconds:.1f} s, 0 errors")
                outs += [mjson, mneeds]
                made.append(("model", [mjson.path, mneeds.path], []))
            elif what == "cad-needs":
                if cfg.section("cad") is None and a.what == "all":
                    continue
                outs.append(gen.cad_needs(ws, cfg))
            elif what == "connectors":
                if not (cfg.section("cad") or {}).get("connectors") and a.what == "all":
                    continue
                outs += gen.connectors(ws, cfg)
            elif what == "code-needs":
                if cfg.section("code") is None and a.what == "all":
                    continue
                outs.append(gen.code_needs(ws, cfg))
            elif what == "freecad-params":
                from curatrix import meparams
                ms = cfg.section("model") or {}
                mj = cfg.resolve(ms.get("json", "generated/model.json"))
                if not mj.exists():
                    raise gen.GenError(f"{ws.rel(mj)} missing; run `curatrix gen model {repo.name}`")
                from curatrix import model as modelmod
                errs = meparams.write(ws, cfg, modelmod.Model.load(mj))
                for e in errs:
                    print(f"  error: {e}", file=sys.stderr)
                if errs:
                    rc = 1
                else:
                    print(f"  next: `curatrix gen all {repo.name}` (semantic JSON), `curatrix check {repo.name} --only CK-F3`")
            elif what == "freecad-json":
                fj = gen.freecad_json(ws, cfg, shapes=a.shape)
                outs += fj
                made.append(("freecad-shapes", [o.path for o in fj], []) if a.shape else
                            ("freecad-shapes", [], [o.path for o in fj]))
            elif what == "cad-exports":
                for e in gen.cad_exports(ws, cfg):
                    print(f"  {e}", file=sys.stderr)
                    rc = 1
        except gen.GenError as e:
            print(f"curatrix gen {what}: {e}", file=sys.stderr)
            rc = 1
    gen_needs = [o for o in outs if o.path.name.endswith("needs.json") and o.path.name != "retired-needs.json"]
    if gen_needs or a.what == "tombstones":
        if a.what == "tombstones":
            for sec, key, default in (("model", "needs", "generated/model-needs.json"), ("cad", "needs", "generated/cad-needs.json"),
                                      ("code", "needs", "generated/code-needs.json")):
                s = cfg.section(sec)
                if s is not None:
                    p = cfg.resolve(s.get(key, default))
                    if p.exists():
                        gen_needs.append(gen.Output(p, p.read_text()))
        tomb, tmsgs = gen.tombstones(cfg, gen_needs, gen.last_baseline_date(ws))
        msgs += tmsgs
        if tmsgs or tomb.path.exists():
            outs.append(tomb)
    for o in outs:
        for f in o.findings:
            print(f"  finding: {f}")
        if a.check:
            if o.differs():
                print(f"  OUT OF DATE {ws.rel(o.path)}")
                rc = 1
            else:
                print(f"  up to date  {ws.rel(o.path)}")
        else:
            print(f"  {'wrote' if o.write() else 'unchanged'} {ws.rel(o.path)}")
    if not a.check and rc == 0:
        from curatrix import provenance
        for kind, files, dropped in made:
            if provenance.record(ws, cfg, files, kind, drop=dropped):
                print(f"  wrote {ws.rel(provenance.path(cfg))} ({kind}: {provenance.used(ws, kind) if files else 'plain Python'})")
    for m in msgs:
        print(f"  {m}")
    return rc


# ------------------------------------------------------------------ new
def cmd_new(a):
    from curatrix import newasm, newpcba
    ws = _ws()
    repo = _repo(ws, a.repo)
    try:
        if a.what == "asm":
            newasm.new_asm(ws, repo, _cfg(ws, repo), a.element, freecad=not a.no_freecad)
        else:
            newpcba.new_pcba(ws, repo, _cfg(ws, repo), a.element, kicad=not a.no_kicad)
    except newpcba.NewError as e:
        print(f"curatrix new {a.what}: {e}", file=sys.stderr)
        return 1
    return 0


def cmd_cam(a):
    """Design output of a pcba/ project or a harness (`name`), or of all of them."""
    from curatrix import cam, eeprojects, harness
    ws = _ws()
    repo = _repo(ws, a.repo)
    cfg = _cfg(ws, repo)
    boards = {p.name for p in eeprojects.discover(cfg) if p.kind == "pcba"}
    harnesses = {h.name for h in harness.discover(cfg)} if harness.patterns(cfg) else set()
    try:
        if a.name and a.name in boards and a.name in harnesses:
            raise cam.CamError(f"{a.name} is both a pcba/ project and a harness; rename one (tags <name>/vX.Y.Z "
                               f"must be unique in the repo)")
        if a.name and a.name not in boards | harnesses:
            raise cam.CamError(f"no pcba/ project or harness {a.name} in {repo.name} (checks.yaml cad.projects, "
                               f"cad.harnesses)")
        if a.update_jobset and (a.name in harnesses or not boards):
            raise cam.CamError("--update-jobset applies to pcba/ projects only")
        if boards and (a.name is None or a.name in boards):
            cam.run(ws, repo, cfg, a.name, update=a.update_jobset)
        if harnesses and not a.update_jobset and (a.name is None or a.name in harnesses):
            harness.run(ws, repo, cfg, a.name)
        if not boards and not harnesses:
            raise cam.CamError(f"{repo.name} has no pcba/ project and no harness (checks.yaml cad.projects, "
                               f"cad.harnesses)")
    except (cam.CamError, harness.HarnessError) as e:
        print(f"curatrix cam: {e}", file=sys.stderr)
        return 1
    return 0


# ------------------------------------------------------------------ ids
def _excl(ws, repo_path: Path) -> list[str]:
    from curatrix import checkcfg
    cy = repo_path / "checks.yaml"
    return checkcfg.load(cy, ws.root).ids_exclude if cy.exists() else []


def cmd_ids(a):
    from curatrix import ids
    ws = _ws()
    try:
        if a.action == "new":
            repo = ws.repo(a.repo) if a.repo else None
            lg = ids.find_ledger_for(ws, a.kind, a.repo)
            rp = repo.path if repo else lg.path.parent
            excl = _excl(ws, rp)
            nid = ids.new(lg, a.kind, rp, Path(a.file) if a.file else None, excl)
            print(nid)
        elif a.action == "fix":
            repo = _repo(ws, a.repo)
            lg = ids.Ledger.load(repo.path / "ids.yaml")
            mapping = ids.fix(repo.path, lg, dry_run=a.dry_run, exclude=_excl(ws, repo.path))
            for k, v in mapping.items():
                print(f"  {k} -> {v}")
            print(f"ids fix: {len(mapping)} placeholder(s){' (dry run)' if a.dry_run else ''}")
        elif a.action == "check":
            repo = _repo(ws, a.repo)
            files = ids.source_files(repo.path, _excl(ws, repo.path))
            errs = ids.check_placeholders(files, repo.path) + ids.check_ledger(files, ids.Ledger.load(repo.path / "ids.yaml"), repo.path)
            for e in errs:
                print(f"  {e}")
            print(f"ids check: {'OK' if not errs else f'{len(errs)} problem(s)'}")
            return 1 if errs else 0
    except ids.IdError as e:
        print(f"curatrix ids: {e}", file=sys.stderr)
        return 1
    return 0


# ------------------------------------------------------------------ views / variants / needs-diff
def cmd_views(a):
    from curatrix import model as modelmod, views
    from curatrix.views import render
    ws = _ws()
    if a.action == "normalize" and a.targets and all(t.endswith(".drawio.svg") for t in a.targets):
        errs = render.normalize(ws, [Path(t).resolve() for t in a.targets], ws.build("curatrix") / "views-normalize",
                                check_only=a.check)
        for e in errs:
            print(f"  {e}")
        return 1 if errs else 0
    repo = _repo(ws, a.targets[0] if a.targets else None)
    cfg = _cfg(ws, repo)
    vs = cfg.section("views") or {}
    ms = cfg.section("model") or {}
    mj = cfg.resolve(vs.get("model") or ms.get("json", "generated/model.json"))
    vdir = cfg.resolve(vs.get("dir", "views"))
    if a.action == "build":
        m = modelmod.Model.load(mj)
        errs = render.build(ws, m, vdir, ws.build(cfg.area) / "views", a.view or None)
        if not errs:
            from curatrix import provenance
            built = [vdir / f"{n}.drawio.svg" for n in a.view] if a.view else sorted(vdir.glob("*.drawio.svg"))
            # a full build also drops the records of views that are gone (xdmod#23)
            gone = [] if a.view else [cfg.repo / rel for rel, e in provenance.load(cfg)["files"].items()
                                      if e.get("made_by") == provenance.KINDS["views"][0] and not (cfg.repo / rel).exists()]
            if provenance.record(ws, cfg, built, "views", drop=gone):
                print(f"  wrote {ws.rel(provenance.path(cfg))} (views: {provenance.used(ws, 'views')})")
    elif a.action == "normalize":
        errs = render.normalize(ws, sorted(vdir.glob("*.drawio.svg")), ws.build(cfg.area) / "views" / "_normalize",
                                check_only=a.check)
    else:
        from curatrix import checks
        ok, _ = checks.run(ws, repo, "local", False, ["CK-D3"])
        return 0 if ok else 1
    for e in errs:
        print(f"  {e}")
    return 1 if errs else 0


def cmd_variants(a):
    from curatrix import model as modelmod, variants
    ws = _ws()
    if a.model:
        mj = Path(a.model)
    else:
        repo = _repo(ws, a.repo)
        ms = _cfg(ws, repo).section("model") or {}
        mj = _cfg(ws, repo).resolve(ms.get("json", "generated/model.json"))
    res = variants.check(modelmod.Model.load(mj))
    if a.verbose:
        print("\n".join(res.notes))
    for e in res.errors:
        print(f"ERROR {e}")
    print(res.summary())
    return 0 if res.ok else 1


def cmd_needs_diff(a):
    from curatrix import graph, needs as needsmod

    def load(p):
        p = Path(p)
        files = [p] if p.is_file() else sorted(p.rglob("needs.json")) or sorted(p.rglob("*.json"))
        return needsmod.load_built(files)
    text, n = graph.diff_report(load(a.before), load(a.after), a.before, a.after)
    print(text)
    if a.out:
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        Path(a.out).write_text(text)
    return 1 if n else 0


def cmd_hook(a):
    from curatrix import hook
    if a.name != "pre-commit":
        raise SystemExit(f"unknown hook {a.name}")
    return hook.pre_commit(Path.cwd())


# ------------------------------------------------------------------ parser
def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="curatrix", description="XDMOD workspace command layer (run from the workspace root).")
    p.add_argument("--version", action="version", version=f"curatrix {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True, metavar="COMMAND")

    s = sub.add_parser("env", help="print the workspace environment: eval \"$(curatrix env)\"")
    s.add_argument("--shell", choices=["sh", "fish"], default="sh")
    s.set_defaults(func=cmd_env)

    s = sub.add_parser("run", help="run any command with the workspace env and limits (limits.yaml)")
    s.add_argument("--use", default="script", help="limits.yaml use (default: script)")
    s.add_argument("-m", "--memory", help="memory limit, e.g. 2G (overrides the use)")
    s.add_argument("-t", "--timeout", help="timeout, e.g. 10m or none (overrides the use)")
    s.add_argument("-v", "--verbose", action="store_true")
    s.add_argument("cmd", nargs=argparse.REMAINDER)
    s.set_defaults(func=cmd_run)

    s = sub.add_parser("fixtures", help="run the planted error of every built-in check (also the tool-backed ones) and record the result")
    s.set_defaults(func=cmd_fixtures)

    s = sub.add_parser("limits", help="show the resolved limits table and backend")
    s.set_defaults(func=cmd_limits)

    s = sub.add_parser("doctor", help="check tools, versions (tools.yaml), paths, hooks, west state")
    s.add_argument("--ci", action="store_true",
                   help="CI runner: system tool mismatches are warnings (tools.yaml tools must still match)")
    s.set_defaults(func=cmd_doctor)

    s = sub.add_parser("bootstrap", help="set up the workspace for a role (group filter, venv, tools, hooks)")
    s.add_argument("--role", required=True, help="syseng | ee | ee3d | me | sw | integration | full | ci-full")
    s.add_argument("--adopt", action="store_true", help="stamp tools already in .venv/opt instead of reinstalling")
    s.add_argument("--no-west", action="store_true", help="skip group filter and west update")
    s.add_argument("--no-doctor", action="store_true", help="skip the final doctor run (CI runners have other system tool versions)")
    s.set_defaults(func=cmd_bootstrap)

    s = sub.add_parser("update", help="west update -k, then refresh venv, tools, links, hooks")
    s.add_argument("--adopt", action="store_true")
    s.set_defaults(func=cmd_update)

    s = sub.add_parser("launch", help="start a GUI tool / Claude Code with workspace-local config")
    s.add_argument("tool", choices=["kicad", "freecad", "drawio", "claude"])
    s.add_argument("args", nargs=argparse.REMAINDER)
    s.set_defaults(func=cmd_launch)

    s = sub.add_parser("docs", help="zdocs build of a repo (or `full`) into build/<area>/docs (strict)")
    s.add_argument("target")
    s.add_argument("--open", action="store_true")
    s.set_defaults(func=cmd_docs)

    s = sub.add_parser("check", help="run a repo's checks (checks.yaml) for a stage")
    s.add_argument("repo", nargs="?")
    s.add_argument("--stage", choices=["local", "pr", "full", "baseline"], default="local")
    s.add_argument("--no-cad", action="store_true", help="skip checks that need CAD tools (CI)")
    s.add_argument("--only", help="comma list of check IDs or prefixes, e.g. CK-D,CK-C1")
    s.add_argument("--base", help="folder with the needs.json files to diff against (CK-G1/G2)")
    s.add_argument("--json", action="store_true", help="print the summary JSON on stdout (log on stderr)")
    s.set_defaults(func=cmd_check)

    s = sub.add_parser("gen", help="generated files: stubs, model, cad-needs, code-needs, freecad-json, tombstones, all; "
                                   "freecad-params (model values into the skeletons' Params, FreeCAD); "
                                   "cad-exports (build/<area>/cad, not committed)")
    s.add_argument("what", choices=["stubs", "model", "cad-needs", "connectors", "code-needs", "freecad-json", "freecad-params",
                                    "tombstones", "cad-exports", "all"])
    s.add_argument("repo", nargs="?")
    s.add_argument("--check", action="store_true", help="only compare with the committed files")
    s.add_argument("--needs", nargs="+", help="stubs: needs.json files instead of the last docs build")
    s.add_argument("--textconv", metavar="FCSTD", help="freecad-json: print the trace JSON of one file (git textconv)")
    s.add_argument("--shape", action="store_true", help="freecad-json: add the shape part (needs FreeCAD)")
    s.set_defaults(func=cmd_gen)

    s = sub.add_parser("new", help="scaffolds: `new pcba <BoardDef>` makes the KiCad project, jobset, library tables "
                                   "and the pcba-<name> document of a board def of the EE model; `new asm "
                                   "<AssemblyDef>` the FreeCAD top document, skeleton.FCStd and the asm-<name> "
                                   "document of an assembly def of the ME model")
    s.add_argument("what", choices=["pcba", "asm"])
    s.add_argument("element", help="the board or assembly def (name, qualified name or EE-PCBA / ME-ASM ID) in the "
                                   "repo's model.json")
    s.add_argument("--repo", help="the EE or ME repo (name or path; default: the repo of the current folder)")
    s.add_argument("--no-kicad", action="store_true", help="pcba: do not let KiCad save the new files (tests)")
    s.add_argument("--no-freecad", action="store_true", help="asm: make only the folder and the document (tests)")
    s.set_defaults(func=cmd_new)

    s = sub.add_parser("cam", help="EE design output into build/<area>/cam/<name>/<version>/: a pcba/ project (copy, "
                                   "version, its jobset; local, needs KiCad) or a harness (WireViz diagram and BOM, "
                                   "a separate process)")
    s.add_argument("repo", help="the EE repo")
    s.add_argument("name", nargs="?", help="one pcba/ project or harness (default: all)")
    s.add_argument("--update-jobset", action="store_true",
                   help="write the project's jobset from the shared template and its variants, then stop")
    s.set_defaults(func=cmd_cam)

    s = sub.add_parser("trace", help="trace report per SYS-REQ (refined, satisfied, verified, latest result, gaps) "
                                     "from the last docs build; the canary configuration in its own section")
    s.add_argument("target", help="a repo or `full`")
    s.add_argument("--canary", action="append", help="SYS-CFG ID of the canary configuration (default: the SYS-CFG titled canary)")
    s.add_argument("-o", "--out", help="output folder (default build/<area>/trace)")
    s.set_defaults(func=cmd_trace)

    s = sub.add_parser("ids", help="issue IDs from the ledger, replace placeholders")
    ss = s.add_subparsers(dest="action", required=True)
    x = ss.add_parser("new", help="issue one ID: ids new KIND [FILE]")
    x.add_argument("kind")
    x.add_argument("file", nargs="?")
    x.add_argument("--repo")
    x = ss.add_parser("fix", help="replace every <KIND>-NEW-<tag> placeholder in a repo")
    x.add_argument("repo", nargs="?")
    x.add_argument("--dry-run", action="store_true")
    x = ss.add_parser("check", help="CK-C1 + CK-C2 for a repo")
    x.add_argument("repo", nargs="?")
    s.set_defaults(func=cmd_ids)

    s = sub.add_parser("views", help="views as editable SVG: build | check | normalize")
    s.add_argument("action", choices=["build", "check", "normalize"])
    s.add_argument("targets", nargs="*", help="repo, or .drawio.svg files (normalize)")
    s.add_argument("--view", action="append", help="build only this view (repeatable)")
    s.add_argument("--check", action="store_true", help="normalize: report only")
    s.set_defaults(func=cmd_views)

    s = sub.add_parser("variants", help="variant rules F1, F2, V1-V5 on the model JSON")
    s.add_argument("repo", nargs="?")
    s.add_argument("--model", help="a model JSON (Pilot export or compact) instead of the repo's")
    s.add_argument("-v", "--verbose", action="store_true")
    s.set_defaults(func=cmd_variants)

    s = sub.add_parser("needs-diff", help="change impact between two sets of needs.json (R7)")
    s.add_argument("before")
    s.add_argument("after")
    s.add_argument("-o", "--out")
    s.set_defaults(func=cmd_needs_diff)

    s = sub.add_parser("work", help="git worktrees for parallel work: start <branch> <repos...> | done <branch> | list (D125)")
    s.add_argument("action", choices=["start", "done", "list"])
    s.add_argument("args", nargs="*")
    s.add_argument("--force", action="store_true", help="done: also with uncommitted changes")
    s.add_argument("--delete-branch", action="store_true", help="done: delete the branches if merged")
    s.add_argument("--base", help="start: the parent branch of a stacked PR (default: main)")
    s.set_defaults(func=cmd_work)

    s = sub.add_parser("ci", help="CI helpers: `ci siblings` resolves sibling revisions (D127); `ci base` fetches the published needs as the CK-G1/G2 base")
    s.add_argument("action", choices=["siblings", "base"])
    s.add_argument("-o", "--out", help="base: output folder (default build/ci/base)")
    s.add_argument("--version", default="latest", help="base: the Pages folder (latest = main, vX.Y.Z = a baseline)")
    s.add_argument("--branch", default="", help="siblings: the PR's head branch name (push: the branch pushed)")
    s.add_argument("--repo", required=True, help="west name of the repo under check")
    s.add_argument("--sha", default="", help="its PR head commit")
    s.set_defaults(func=cmd_ci)

    s = sub.add_parser("evidence", help="test run records: record (Twister dir -> evidence branch), read (-> TR needs), "
                                        "preview (Twister dir -> preview TR needs for the docs), validate")
    s.add_argument("action", choices=["record", "read", "preview", "validate"])
    s.add_argument("target", nargs="?", default="", help="record, preview: Twister output dir; validate: record.json")
    s.add_argument("--config", help="record: the SYS-CFG of the run (required); preview: optional")
    s.add_argument("--kind", choices=["sim", "hil"], default="sim", help="hil: on the HIL setup; sim: native_sim/QEMU (never HIL evidence)")
    s.add_argument("--setup", help="record --kind hil: the setup folder hil/<setup>")
    s.add_argument("--tests", action="append", help="record, preview: test source folders for the ZTEST -> test case IDs (default: Twister's testsuite roots)")
    s.add_argument("--map", action="append", help="TEST=ID: test case ID for a Twister test (overrides the source comments)")
    s.add_argument("--note")
    s.add_argument("--repo", help="the repo with the evidence branch (default: the framework repo named <project>-integration)")
    s.add_argument("--branch", default="evidence", help="evidence (default) or a scratch branch for records that are not evidence")
    s.add_argument("--create", action="store_true", help="create the branch as an orphan if it does not exist")
    s.add_argument("--trailer", help="trailer line for the commit (agents: Co-Authored-By: ...)")
    s.add_argument("--dry-run", action="store_true", help="record: print the record, write nothing")
    s.add_argument("--offline", action="store_true", help="record: don't check main/baseline at the remotes (the rule then fails)")
    s.add_argument("--ref", help="read: a git ref instead of the remote branch")
    s.add_argument("--commit-of", help="preview: the repo whose commit the stamp records (the docs show the preview only for that commit)")
    s.add_argument("-o", "--out", help="read: output file (default build/<repo>/evidence/tr-needs.json); preview: output file (required)")
    s.set_defaults(func=cmd_evidence)

    s = sub.add_parser("hook", help=argparse.SUPPRESS)
    s.add_argument("name")
    s.add_argument("args", nargs="*")
    s.set_defaults(func=cmd_hook)
    return p


def _reexec_from_worktree(argv: list[str] | None) -> None:
    """In a worktree set whose xdmod is a worktree (D125), run that xdmod's curatrix, not the
    editable install of the main checkout."""
    if os.environ.get("XD_CURATRIX_REEXEC"):
        return
    try:
        from curatrix.ws import PKG_DIR, find_root
        own = find_root() / "xdmod" / "curatrix" / "src" / "curatrix"
    except Exception:  # noqa: BLE001 - no workspace: the command reports that itself
        return
    if own.is_dir() and own.resolve() != PKG_DIR.resolve():
        env = dict(os.environ, XD_CURATRIX_REEXEC="1")
        env["PYTHONPATH"] = os.pathsep.join(x for x in (str(own.parent), env.get("PYTHONPATH", "")) if x)
        args = sys.argv[1:] if argv is None else argv
        os.execve(sys.executable, [sys.executable, "-m", "curatrix", *args], env)


def main(argv: list[str] | None = None) -> int:
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
    _reexec_from_worktree(argv)
    a = parser().parse_args(argv)
    from curatrix.ws import WorkspaceError
    try:
        return a.func(a) or 0
    except WorkspaceError as e:
        print(f"curatrix: {e}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130
    except Exception as e:  # noqa: BLE001
        from curatrix import checkcfg, evidence, setup, tools
        if isinstance(e, (checkcfg.ConfigError, setup.SetupError, tools.ToolsError, evidence.EvidenceError)):
            print(f"curatrix: {e}", file=sys.stderr)
            return 1
        raise
