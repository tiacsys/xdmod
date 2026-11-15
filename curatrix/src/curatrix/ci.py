"""CI helpers for the reusable workflow (`.github/workflows/curatrix-check.yml`).

``curatrix ci siblings``: PR CI sibling resolution (repo-topology.md §7, D52, D127). For every
active ``xdmod`` / ``robarm-*`` project of the west workspace, check out, in this order:

1. the branch with the PR's head branch name, if the project's remote has one;
2. the project's ``main``, if the manifest pin is an ancestor of it (so changes merged upstream
   but not yet bumped are seen);
3. the manifest pin.

The repo under check is checked out at the PR head SHA. The manifest repo itself is checked out
by the workflow (``actions/checkout``) and is left alone. On a push to ``main`` rule 1 is skipped
(every repo has a ``main``; rule 2 already says when it may be used).

West clones have no ``origin`` remote, so every fetch goes to the project URL from
``west list``. Fetches are blobless (``--filter=blob:none``) and unshallow a ``--depth=1``
clone, because the ancestor test needs the history of ``main``.
"""
from __future__ import annotations

import json
import os
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from curatrix import limits
from curatrix.ws import Workspace

PREFIXES = ("xdmod", "robarm-")


@dataclass
class Project:
    name: str
    path: Path
    url: str
    pin: str


@dataclass
class Resolution:
    name: str
    path: str
    rule: str            # "head" | "branch" | "main" | "pin"
    sha: str
    pin: str
    detail: str = ""


def _git(args: list[str], cwd: Path, ws: Workspace | None, check: bool = True) -> subprocess.CompletedProcess:
    cmd = ["git", *args]
    if ws is not None:
        r = limits.run(cmd, "git", ws, cwd=cwd, capture_output=True, text=True)
    else:  # tests without a workspace
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if check and r.returncode:
        raise RuntimeError(f"git {' '.join(args)} in {cwd} failed ({r.returncode}): {r.stderr.strip()}")
    return r


def _is_shallow(path: Path, ws) -> bool:
    return _git(["rev-parse", "--is-shallow-repository"], path, ws).stdout.strip() == "true"


def _fetch(p: Project, refspecs: list[str], ws) -> None:
    args = ["fetch", "-q", "--filter=blob:none"]
    if _is_shallow(p.path, ws):
        args.append("--unshallow")
    # full history and the tags (D64 g), e.g. for `git describe`
    _git([*args, p.url, *refspecs, "+refs/tags/*:refs/tags/*"], p.path, ws)


def remote_has_branch(p: Project, branch: str, ws) -> bool:
    """True/False; any other ls-remote failure (network, auth, bad URL) raises, so it is never
    mistaken for "no such branch"."""
    r = _git(["ls-remote", "--exit-code", "--heads", p.url, f"refs/heads/{branch}"], p.path, ws, check=False)
    if r.returncode == 0:
        return True
    if r.returncode == 2:
        return False
    raise RuntimeError(f"git ls-remote {p.url} failed ({r.returncode}): {r.stderr.strip()}")


def resolve_one(p: Project, branch: str, under_check: str, head_sha: str, ws=None, checkout: bool = True) -> Resolution:
    """Apply D127 to one project (fetches, then checks out unless `checkout` is False)."""
    if p.name == under_check:
        if head_sha:
            _fetch(p, [head_sha], ws)
        target, rule, detail = head_sha, "head", "the repo under check, at the PR head"
    else:
        refs = ["+refs/heads/main:refs/remotes/xd-ci/main"]
        has_branch = bool(branch) and branch != "main" and remote_has_branch(p, branch, ws)
        if has_branch:
            refs.append(f"+refs/heads/{branch}:refs/remotes/xd-ci/branch")
        _fetch(p, refs, ws)
        if has_branch:
            target, rule, detail = "refs/remotes/xd-ci/branch", "branch", f"branch {branch}"
        elif _git(["merge-base", "--is-ancestor", p.pin, "refs/remotes/xd-ci/main"], p.path, ws, check=False).returncode == 0:
            target, rule, detail = "refs/remotes/xd-ci/main", "main", "main (the pin is an ancestor)"
        else:
            target, rule, detail = p.pin, "pin", "manifest pin (not an ancestor of main)"
    sha = _git(["rev-parse", f"{target}^{{commit}}"], p.path, ws).stdout.strip()
    if checkout:
        _git(["checkout", "-q", "--detach", sha], p.path, ws)
    return Resolution(p.name, str(p.path), rule, sha, p.pin, detail)


def projects(ws: Workspace) -> list[Project]:
    """Active xdmod/robarm-* projects from `west list` (the manifest repo excluded)."""
    out = subprocess.run([*ws.west(), "list", "-f", "{name}|{path}|{url}|{sha}"], cwd=ws.root,
                         capture_output=True, text=True, check=True, timeout=120).stdout
    res = []
    for line in out.splitlines():
        name, path, url, sha = (line.split("|") + ["", "", "", ""])[:4]
        if name == "manifest" or not name.startswith(PREFIXES):
            continue
        res.append(Project(name, ws.root / path, url, sha))
    return res


def siblings(ws: Workspace, branch: str, under_check: str, head_sha: str, log=print,
             out: Path | None = None) -> list[Resolution]:
    res = []
    for p in projects(ws):
        r = resolve_one(p, branch, under_check, head_sha, ws)
        log(f"  {r.name:20} {r.rule:6} {r.sha[:12]}  {r.detail}")
        res.append(r)
    out = out or ws.build("ci") / "siblings.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({"branch": branch, "under_check": under_check, "head_sha": head_sha,
                               "repos": [asdict(r) for r in res]}, indent=2) + "\n")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as f:
            f.write(f"### Sibling revisions (D127), branch `{branch}`\n\n| repo | rule | commit | pin |\n|---|---|---|---|\n")
            for r in res:
                f.write(f"| {r.name} | {r.rule} | `{r.sha[:12]}` | `{r.pin[:12]}` |\n")
    return res
