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
    rc = limits.norm_rc(subprocess.run(limits.wrap(cmd, lim), env=ws.run_env(), cwd=os.getcwd()).returncode)
    if rc in (124, 137):
        print(f"curatrix run: {limits.explain_rc(rc)}", file=sys.stderr)
    return rc


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
    print("curatrix work start/done: not implemented yet (plan task 4.4c, D125). Until then create worktrees by hand:\n"
          "  git -C <repo> worktree add ../.worktrees/<branch>/<repo> -b <branch>", file=sys.stderr)
    return 2


def cmd_ci(a):
    from curatrix import ci
    ws = _ws()
    if a.action == "siblings":
        print(f"curatrix ci siblings: branch {a.branch!r}, under check {a.repo} @ {a.sha[:12] or '-'}")
        ci.siblings(ws, a.branch, a.repo, a.sha)
        return 0
    return 2


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
    whats = ["stubs", "model", "cad-needs", "freecad-json"] if a.what == "all" else [a.what]
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
            for sec, key, default in (("model", "needs", "generated/model-needs.json"), ("cad", "needs", "generated/cad-needs.json")):
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
            if provenance.record(ws, cfg, built, "views"):
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

    s = sub.add_parser("gen", help="generated files: stubs, model, cad-needs, freecad-json, tombstones, all; "
                                   "cad-exports (build/<area>/cad, not committed)")
    s.add_argument("what", choices=["stubs", "model", "cad-needs", "freecad-json", "tombstones", "cad-exports", "all"])
    s.add_argument("repo", nargs="?")
    s.add_argument("--check", action="store_true", help="only compare with the committed files")
    s.add_argument("--needs", nargs="+", help="stubs: needs.json files instead of the last docs build")
    s.add_argument("--textconv", metavar="FCSTD", help="freecad-json: print the trace JSON of one file (git textconv)")
    s.add_argument("--shape", action="store_true", help="freecad-json: add the shape part (needs FreeCAD)")
    s.set_defaults(func=cmd_gen)

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

    s = sub.add_parser("work", help="git worktrees for parallel work (not implemented yet, 4.4c)")
    s.add_argument("action", choices=["start", "done"])
    s.add_argument("args", nargs="*")
    s.set_defaults(func=cmd_work)

    s = sub.add_parser("ci", help="CI helpers: `ci siblings` resolves sibling revisions (D127)")
    s.add_argument("action", choices=["siblings"])
    s.add_argument("--branch", required=True, help="the PR's head branch name (push: the branch pushed)")
    s.add_argument("--repo", required=True, help="west name of the repo under check")
    s.add_argument("--sha", default="", help="its PR head commit")
    s.set_defaults(func=cmd_ci)

    s = sub.add_parser("hook", help=argparse.SUPPRESS)
    s.add_argument("name")
    s.add_argument("args", nargs="*")
    s.set_defaults(func=cmd_hook)
    return p


def main(argv: list[str] | None = None) -> int:
    os.environ.setdefault("PYTHONDONTWRITEBYTECODE", "1")
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
        from curatrix import checkcfg, setup, tools
        if isinstance(e, (checkcfg.ConfigError, setup.SetupError, tools.ToolsError)):
            print(f"curatrix: {e}", file=sys.stderr)
            return 1
        raise
