"""Test run records and the evidence branch (tasks 4.5a, 4.6; D57, D60, D73, D131; R5, R5a).

A **run record** (schema ``data/run-record.schema.json``, README "Evidence") describes one
Twister run: the firmware hash, the SHAs of every west project, the configuration (``SYS-CFG``),
the results, and whether the evidence rule held. Records live on the orphan branch ``evidence``
of the integration repo (``<project>-integration``) as ``runs/<YYYY>/<run id>/record.json`` (+ the Twister reports), never on
``main``.

``record``  build a record from a Twister output dir and the workspace state.
``write``   commit it onto the evidence branch through a git worktree under ``build/evidence/``
            (the repo's own checkout and its ``main`` are never touched). It refuses a record whose
            evidence rule failed, unless it goes to another (scratch) branch.
``preview`` turn a local Twister output dir straight into preview ``TR`` needs for the docs build
            of the same run (no record, no evidence rule: previews never count, D60).
``read``    turn the records of a branch into ``TR`` needs (sphinx-needs import format) for the
            docs; a record whose SHAs differ from the current pins is tagged ``stale`` (D131).

Evidence rule (D60): every west project at its manifest pin with a clean tree, and the commits of
xdmod, the manifest and every framework repo (a project with a ``checks.yaml``) on ``main`` (or, for the manifest, a ``baseline/*`` tag).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

from curatrix import limits
# test case kinds from needs_config.toml (task 5.2) and the ZTEST variants: one reader with
# `curatrix gen code-needs` (code.py)
from curatrix.code import TC_RE, ZTEST_RE, mask
from curatrix.ws import Workspace, is_framework_path

SCHEMA_FILE = Path(__file__).resolve().parent / "data" / "run-record.schema.json"
SCHEMA_ID = "xdmod-run-record/1"
REPORTS = ("twister.json", "twister_report.xml")
VERDICT = {"passed": "passed", "failed": "failed", "skipped": "skipped", "error": "error",
           "blocked": "error", "filtered": "skipped", "not run": "skipped"}


class EvidenceError(Exception):
    pass


def _git(args, cwd: Path, ws: Workspace | None = None, check: bool = True, **kw) -> subprocess.CompletedProcess:
    cmd = ["git", *args]
    r = (limits.run(cmd, "git", ws, cwd=cwd, capture_output=True, text=True, **kw) if ws is not None
         else subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, **kw))
    if check and r.returncode:
        raise EvidenceError(f"git {' '.join(args)} ({cwd}) failed: {r.stderr.strip()}")
    return r


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------ test case IDs (D80)
def test_case_map(src_dirs: list[Path]) -> dict[str, str]:
    """`<ztest suite>.<test name without test_>` -> test case ID, from the comment right above
    each ZTEST(...) in the C sources of the test folders."""
    out = {}
    for d in src_dirs:
        for f in sorted(Path(d).rglob("*.c")):
            for m in ZTEST_RE.finditer(mask(f.read_text(errors="replace"))):
                ids = TC_RE.findall(m.group("c").split("/*")[-1])
                if ids:
                    name = m.group("name")
                    out[f"{m.group('suite')}.{name[5:] if name.startswith('test_') else name}"] = ids[0]
    return out


def _tc_for(identifier: str, suite: str, mapping: dict[str, str]) -> str | None:
    """twister identifier `<yaml scenario>.<ztest suite>.<test>`: match on the last two parts."""
    if identifier in mapping:
        return mapping[identifier]
    rest = identifier[len(suite) + 1:] if identifier.startswith(suite + ".") else identifier
    return mapping.get(rest)


# ------------------------------------------------------------------ twister output
def parse_twister(outdir: Path) -> dict:
    p = Path(outdir) / "twister.json"
    if not p.is_file():
        raise EvidenceError(f"{p} not found (not a Twister output dir)")
    return json.loads(p.read_text())


def find_firmware(outdir: Path, suite: dict) -> Path:
    plat = suite.get("platform", "").replace("/", "_")
    cands = [p for name in ("zephyr.bin", "zephyr.exe")
             for p in sorted(Path(outdir).rglob(f"{suite['name']}/zephyr/{name}")) if plat in str(p)]
    if not cands:
        raise EvidenceError(f"no zephyr.bin / zephyr.exe for {suite['name']} ({suite.get('platform')}) in {outdir}")
    return cands[0]


# ------------------------------------------------------------------ workspace state (D60)
def _west_projects(ws: Workspace) -> list[dict]:
    out = subprocess.run([*ws.west(), "list", "-f", "{name}|{path}|{url}|{sha}"], cwd=ws.root,
                         capture_output=True, text=True, check=True, timeout=120).stdout
    res = []
    for line in out.splitlines():
        name, path, url, sha = (line.split("|") + ["", "", "", ""])[:4]
        res.append({"name": name, "path": ws.root / path, "url": url, "pin": sha})
    return res


def _on_main_or_baseline(path: Path, url: str, sha: str, ws, manifest: bool) -> str | None:
    """'main' if sha is in the remote main, 'baseline/vX.Y.Z' if it is a baseline tag (manifest)."""
    if manifest:
        tags = _git(["ls-remote", "--tags", url, "refs/tags/baseline/*"], path, ws, check=False).stdout
        for line in tags.splitlines():
            obj, ref = line.split("\t")
            if ref.endswith("^{}") and obj == sha:
                return ref[len("refs/tags/"):-3]
            if not ref.endswith("^{}") and obj == sha:
                return ref[len("refs/tags/"):]
    if _git(["fetch", "-q", "--no-tags", "--filter=blob:none", url, "+refs/heads/main:refs/remotes/xd-evidence/main"],
            path, ws, check=False).returncode:
        if _git(["rev-parse", "-q", "--verify", "refs/remotes/xd-evidence/main"], path, ws, check=False).returncode:
            return None
    ok = _git(["merge-base", "--is-ancestor", sha, "refs/remotes/xd-evidence/main"], path, ws, check=False).returncode == 0
    return "main" if ok else None


def workspace_state(ws: Workspace, check_remote: bool = True) -> tuple[dict, dict, list[str], str]:
    """(manifest entry, {name: repo entry}, problems, base) for the run record."""
    manifest, repos, problems, base = None, {}, [], "main"
    for p in _west_projects(ws):
        path, name = p["path"], p["name"]
        if not (path / ".git").exists():
            continue
        head = _git(["rev-parse", "HEAD"], path, ws).stdout.strip()
        clean = _git(["status", "--porcelain"], path, ws).stdout.strip() == ""
        is_manifest = name == "manifest"
        url = p["url"]
        if is_manifest:
            name = path.name
            url = _git(["config", "--get", "remote.origin.url"], path, ws, check=False).stdout.strip()
        e = {"sha": head, "pin": head if is_manifest else p["pin"], "clean": clean}
        if not clean:
            problems.append(f"{name}: tree not clean")
        if not is_manifest and head != p["pin"]:
            problems.append(f"{name}: HEAD {head[:12]} is not the manifest pin {p['pin'][:12]}")
        if check_remote and (is_manifest or is_framework_path(path, name)):
            on = _on_main_or_baseline(path, url, head, ws, is_manifest) if url else None
            e["on"] = on
            if on is None:
                problems.append(f"{name}: {head[:12]} is not on main" + (" or a baseline tag" if is_manifest else ""))
            elif is_manifest and on.startswith("baseline/"):
                base = on
        elif is_manifest or is_framework_path(path, name):
            problems.append(f"{name}: main/baseline not checked (offline)")
        if is_manifest:
            manifest = e
        else:
            repos[name] = e
    if manifest is None:
        raise EvidenceError("no manifest repo in `west list`")
    return manifest, dict(sorted(repos.items())), problems, base


# ------------------------------------------------------------------ the record
def make_record(ws: Workspace, twister_dir: Path, config: str, kind: str = "sim", setup: str | None = None,
                test_dirs: list[Path] | None = None, overrides: dict[str, str] | None = None,
                note: str = "", check_remote: bool = True, now: dt.datetime | None = None) -> dict:
    tw = parse_twister(twister_dir)
    suites = [s for s in tw.get("testsuites", []) if s.get("status") not in ("filtered",)]
    if not suites:
        raise EvidenceError(f"{twister_dir}: no test suites that ran")
    platforms = sorted({s.get("platform", "") for s in suites})
    if len(platforms) != 1:
        raise EvidenceError(f"one platform per record, got {platforms}")
    fw = {find_firmware(twister_dir, s) for s in suites}
    if len(fw) != 1:
        raise EvidenceError("one firmware image per record; run Twister for one test scenario, or record "
                            f"each separately (images: {', '.join(sorted(str(f) for f in fw))})")
    fw_path = fw.pop()
    roots = tw.get("environment", {}).get("options", {}).get("testsuite_root", [])
    mapping = test_case_map(test_dirs or [Path(r) for r in roots])
    mapping.update(overrides or {})
    results = []
    for s in suites:
        for tc in s.get("testcases", []):
            d = tc.get("execution_time")
            results.append({"test": tc["identifier"], "suite": s["name"],
                            "test_case": _tc_for(tc["identifier"], s["name"], mapping),
                            "status": tc.get("status", "not run"),
                            "duration": float(d) if d not in (None, "") else None})
    manifest, repos, problems, base = workspace_state(ws, check_remote)
    now = (now or dt.datetime.now(dt.timezone.utc)).replace(microsecond=0)
    fw_sha = sha256_file(fw_path)
    created = now.isoformat().replace("+00:00", "Z")
    run_id = now.strftime("%Y%m%dT%H%M%SZ") + "-" + hashlib.sha256(
        (fw_sha + manifest["sha"] + created).encode()).hexdigest()[:8]
    who = _git(["config", "user.name"], ws.root, ws, check=False).stdout.strip() or "unknown"
    rec = {
        "schema": SCHEMA_ID, "run_id": run_id, "kind": kind, "created": created, "recorded_by": who,
        "config": config, "setup": setup, "platform": platforms[0],
        "firmware": {"file": str(fw_path.resolve().relative_to(Path(twister_dir).resolve())), "sha256": fw_sha},
        "workspace": {"manifest": manifest, "repos": repos},
        "evidence": {"ok": not problems, "base": base, "problems": problems},
        "results": results,
        "tool": {"name": "twister", "zephyr_version": tw.get("environment", {}).get("zephyr_version", ""),
                 "files": {f: sha256_file(Path(twister_dir) / f) for f in REPORTS if (Path(twister_dir) / f).is_file()}},
    }
    if note:
        rec["note"] = note
    return rec


def validate(rec: dict) -> list[str]:
    """Schema errors (jsonschema), plus the rules a schema can't say."""
    errs = []
    try:
        import jsonschema
        v = jsonschema.Draft202012Validator(json.loads(SCHEMA_FILE.read_text()))
        errs += [f"{'/'.join(str(x) for x in e.absolute_path) or '(record)'}: {e.message}" for e in v.iter_errors(rec)]
    except ImportError:
        errs.append("jsonschema is not installed (xdmod/requirements.txt)")
    if not errs and rec["kind"] == "hil" and not rec.get("setup"):
        errs.append("setup: a hil record names its HIL setup (hil/<setup>)")
    if not errs and rec["evidence"]["ok"] != (not rec["evidence"]["problems"]):
        errs.append("evidence.ok must be true exactly when there are no problems")
    return errs


def record_path(rec: dict) -> str:
    return f"runs/{rec['run_id'][:4]}/{rec['run_id']}"


# ------------------------------------------------------------------ writer
def write(ws: Workspace, rec: dict, twister_dir: Path, repo: Path, url: str, branch: str = "evidence",
          create: bool = False, trailer: str = "", log=print) -> str:
    """Commit `rec` (+ Twister reports) onto `branch` of `repo` through a worktree in build/.
    Returns the new commit SHA. The branch is updated locally; pushing is the caller's step."""
    errs = validate(rec)
    if errs:
        raise EvidenceError("invalid run record:\n  " + "\n  ".join(errs))
    if branch == "evidence" and not rec["evidence"]["ok"]:
        raise EvidenceError("the evidence rule failed (D60), so this run is a preview and is not kept:\n  "
                            + "\n  ".join(rec["evidence"]["problems"]) + "\n(write it to a scratch branch with --branch)")
    wt = ws.build("evidence") / f"wt-{re.sub(r'[^A-Za-z0-9_.-]+', '-', branch)}"
    if wt.exists():
        _git(["worktree", "remove", "--force", str(wt)], repo, ws, check=False)
        shutil.rmtree(wt, ignore_errors=True)
    _git(["worktree", "prune"], repo, ws, check=False)
    remote = _git(["fetch", "-q", "--no-tags", url, f"+refs/heads/{branch}:refs/remotes/xd-evidence/{branch}"],
                  repo, ws, check=False).returncode == 0
    local = _git(["rev-parse", "-q", "--verify", f"refs/heads/{branch}"], repo, ws, check=False).returncode == 0
    wt.parent.mkdir(parents=True, exist_ok=True)
    if remote:
        rref = f"refs/remotes/xd-evidence/{branch}"
        if not local:
            _git(["branch", branch, rref], repo, ws)
        elif _git(["merge-base", "--is-ancestor", f"refs/heads/{branch}", rref], repo, ws, check=False).returncode == 0:
            _git(["branch", "-f", branch, rref], repo, ws)            # local is behind: fast-forward, nothing lost
        _git(["worktree", "add", "-q", str(wt), branch], repo, ws)
        if local and _git(["merge-base", "--is-ancestor", rref, "HEAD"], wt, ws, check=False).returncode:
            # diverged: local records not pushed yet + new remote records. Never drop local ones:
            # replay them onto the remote head (records are new files only, so this can't conflict).
            r = _git(["rebase", "-q",
                      "--committer-date-is-author-date", rref], wt, ws, check=False)
            if r.returncode:
                _git(["rebase", "--abort"], wt, ws, check=False)
                _git(["worktree", "remove", "--force", str(wt)], repo, ws, check=False)
                raise EvidenceError(f"local branch {branch} and {url} diverged and the local records don't replay "
                                    f"cleanly ({r.stderr.strip()}); nothing was changed. Resolve by hand, then push")
            log(f"  replayed unpushed local records of {branch} onto the remote head")
    elif local:
        _git(["worktree", "add", "-q", str(wt), branch], repo, ws)
    elif create:
        _git(["worktree", "add", "-q", "--orphan", "-b", branch, str(wt)], repo, ws)
    else:
        raise EvidenceError(f"branch {branch!r} exists neither at {url} nor locally (use --create for a new orphan branch)")
    try:
        if _git(["symbolic-ref", "--short", "HEAD"], wt, ws).stdout.strip() != branch:
            raise EvidenceError(f"worktree {wt} is not on {branch}")
        d = wt / record_path(rec)
        d.mkdir(parents=True, exist_ok=False)
        (d / "record.json").write_text(json.dumps(rec, indent=2, sort_keys=True) + "\n")
        for f in REPORTS:
            if (Path(twister_dir) / f).is_file():
                shutil.copyfile(Path(twister_dir) / f, d / f)
        _git(["add", "--", record_path(rec)], wt, ws)
        n_tc = sum(1 for r in rec["results"] if r["test_case"])
        msg = (f"run {rec['run_id']}: {rec['kind']} {rec['platform']} {rec['config']}, "
               f"{len(rec['results'])} result(s), {n_tc} traced\n\n"
               f"firmware sha256 {rec['firmware']['sha256']}\nmanifest {rec['workspace']['manifest']['sha']}\n")
        if trailer:
            msg += f"\n{trailer}\n"
        _git(["commit", "-q", "-m", msg], wt, ws)
        sha = _git(["rev-parse", "HEAD"], wt, ws).stdout.strip()
        log(f"  committed {record_path(rec)} on {branch} ({sha[:12]}) in {ws.rel(repo)}")
        return sha
    finally:
        _git(["worktree", "remove", "--force", str(wt)], repo, ws, check=False)


# ------------------------------------------------------------------ reader
def load_records(repo: Path, ref: str, ws: Workspace | None = None) -> list[dict]:
    files = _git(["ls-tree", "-r", "--name-only", ref, "--", "runs"], repo, ws, check=False).stdout.split()
    out = []
    for f in sorted(files):
        if f.endswith("/record.json"):
            out.append(json.loads(_git(["show", f"{ref}:{f}"], repo, ws).stdout))
    return out


def shas_of(rec: dict) -> list[str]:
    ws = rec["workspace"]
    return [f"{n}={e['sha']}" for n, e in sorted(ws["repos"].items())]


def stale_reasons(rec: dict, pins: dict[str, str]) -> list[str]:
    """D131: the recorded SHAs must equal the current pins (west name -> SHA)."""
    out = []
    for n, e in rec["workspace"]["repos"].items():
        pin = pins.get(n)
        if pin and pin != e["sha"]:
            out.append(f"{n} {e['sha'][:12]} != pin {pin[:12]}")
    return out


def test_suffix(run_id: str, test: str) -> str:
    """The 8 hex digits of a TR ID: unique per run and Twister test."""
    return hashlib.sha256(f"{run_id}\0{test}".encode()).hexdigest()[:8]


def to_needs(records: list[dict], pins: dict[str, str] | None = None, project: str = "evidence",
             problems: list[str] | None = None) -> dict:
    """TR needs (import format) from run records; untraced results make no need. Records that
    fail the schema are skipped and reported in `problems`."""
    needs = {}
    for rec in records:
        errs = validate(rec)
        if errs:
            if problems is not None:
                problems.append(f"{rec.get('run_id', '?')}: invalid record, skipped: {'; '.join(errs[:3])}")
            continue
        if not rec.get("evidence", {}).get("ok"):
            continue                                   # previews never count (D60)
        stale = stale_reasons(rec, pins) if pins else []
        for r in rec["results"]:
            tc = r.get("test_case")
            if not tc:
                continue
            # one TR per Twister test, also when several tests trace to the same test case:
            # the suffix hashes run and test, so a later pass can't overwrite an earlier fail
            nid = f"TR-{tc}-{test_suffix(rec['run_id'], r['test'])}"
            verdict = VERDICT.get(r["status"], "error")
            n = {"id": nid, "type": "tr", "title": f"{tc} {verdict} ({rec['platform']}, {rec['config']})",
                 "content": (f"Run ``{rec['run_id']}`` ({rec['kind']}), test ``{r['test']}``, recorded "
                             f"{rec['created']} by {rec['recorded_by']} against {rec['evidence']['base']}."
                             + (f" **Stale** (D131): {'; '.join(stale)}." if stale else "")),
                 "status": "valid", "result_of": [tc], "method": "hil" if rec["kind"] == "hil" else "test",
                 "config": rec["config"], "firmware_sha256": rec["firmware"]["sha256"], "shas": shas_of(rec),
                 "verdict": verdict, "run_id": rec["run_id"], "tags": ["stale"] if stale else []}
            needs[nid] = n
    return {"created": "", "current_version": "", "project": project,
            "versions": {"": {"needs": {k: needs[k] for k in sorted(needs)}}}}


# ------------------------------------------------------------------ preview (task 5.10)
def preview_needs(twister_dir: Path, test_dirs: list[Path] | None = None, config: str | None = None,
                  project: str = "preview") -> dict:
    """Preview TR needs (import format) from a local Twister output dir, for the docs build of the
    same check run. Unlike a record it takes every suite and platform, needs no firmware hash and
    no workspace state. The IDs are stable for a test (suffix of "preview" and the Twister test),
    the needs carry the tag ``preview``. Untraced results make no need."""
    tw = parse_twister(twister_dir)
    roots = tw.get("environment", {}).get("options", {}).get("testsuite_root", [])
    mapping = test_case_map(test_dirs or [Path(r) for r in roots])
    when = tw.get("environment", {}).get("run_date", "")
    day = when[:10]
    needs = {}
    for suite in tw.get("testsuites", []):
        if suite.get("status") == "filtered":
            continue
        plat = suite.get("platform", "")
        for tc in suite.get("testcases", []):
            tcid = _tc_for(tc["identifier"], suite["name"], mapping)
            if not tcid:
                continue
            verdict = VERDICT.get(tc.get("status", "not run"), "error")
            nid = f"TR-{tcid}-{test_suffix('preview', tc['identifier'] + '@' + plat)}"
            n = {"id": nid, "type": "tr", "title": f"{tcid} {verdict} ({plat}, local preview{', ' + day if day else ''})",
                 "content": (f"Local Twister run{(' of ' + when) if when else ''}, test ``{tc['identifier']}`` on "
                             f"``{plat}``. A preview from this build, not evidence (D60): published results "
                             f"come from the evidence branch."),
                 "status": "valid", "result_of": [tcid], "method": "test", "verdict": verdict, "tags": ["preview"]}
            if config:
                n["config"] = config
            needs[nid] = n
    return {"created": "", "current_version": "", "project": project,
            "versions": {"": {"needs": {k: needs[k] for k in sorted(needs)}}}}


def stamp_path(needs_file: Path) -> Path:
    """The run stamp next to a preview needs file: ``tr-needs.json`` -> ``tr-needs.stamp.json``."""
    return needs_file.with_name(needs_file.stem + ".stamp.json")


def preview_stamp(twister_dir: Path, repo: Path | None) -> dict:
    """When the previewed run happened and which commit of the repo it tested. The docs show a
    preview only while the repo is still at that commit (``xd-needimport :stamp:``)."""
    tw = parse_twister(twister_dir)
    st = {"run_date": tw.get("environment", {}).get("run_date", ""), "commit": "", "dirty": False}
    if repo is not None:
        st["commit"] = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True,
                                      text=True).stdout.strip()
        st["dirty"] = bool(subprocess.run(["git", "-C", str(repo), "status", "--porcelain"], capture_output=True,
                                          text=True).stdout.strip())
    return st
