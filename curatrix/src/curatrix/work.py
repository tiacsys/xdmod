"""Git worktrees for parallel work (D125, workflow.md §4, task 4.4c).

``curatrix work start <branch> <repos...>`` makes ``<ws>/.worktrees/<branch>/`` look like a
workspace root of its own:

- each named repo is a **git worktree** on ``<branch>`` (new from the repo's ``main``, or the
  existing local/remote branch);
- every other top-level entry of the workspace (other repos, ``zephyr/``, ``modules/``,
  ``tools/``, ``libs/``, ``.venv``, ``.xdmod``, ``CLAUDE.md``, ``.claude``) is a **relative
  symlink** to the main checkout, so shared parts are not duplicated;
- ``.west/`` is a real folder with a copy of the west config. West finds its topdir from the
  current directory, so ``west list`` -- and with it Zephyr's module discovery
  (``zephyr_module.py``), ``west build`` and the docs build (``west topdir``) -- sees the
  worktree repos, not the main checkouts. Registry paths like ``../../robarm-syseng/docs/se-req``
  resolve inside ``.worktrees/<branch>/`` too: to the worktree if that repo is part of the
  change, else through the symlink to the main checkout;
- ``build`` is a symlink to ``<ws>/build/<branch>/``, so builds go to ``build/<branch>/<area>/``.

Work from the worktree root: ``cd .worktrees/<branch>`` (or ``XD_WORKSPACE=.worktrees/<branch>``)
and run curatrix as usual. If xdmod itself is one of the worktree repos, curatrix runs its own
code from the worktree (cli.main re-executes itself). Never run ``west update`` / ``curatrix
update`` there: it would move the worktrees to the pins.

``curatrix work done <branch>`` removes the worktrees (refused for uncommitted changes unless
``--force``), the symlinks and the folder; the branches stay (``--delete-branch`` deletes them if
they are merged into ``main``).
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from curatrix.ws import Workspace

MARKER = ".xdmod-worktree.json"
NOT_LINKED = {".worktrees", ".west", "build", ".git"}


class WorkError(Exception):
    pass


def _git(args, cwd, check=True) -> subprocess.CompletedProcess:
    r = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, timeout=600)
    if check and r.returncode:
        raise WorkError(f"git {' '.join(args)} ({cwd}) failed: {r.stderr.strip()}")
    return r


def slug(branch: str) -> str:
    """Folder-safe branch name for build/<branch>/ (feat/x -> feat-x)."""
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", branch).strip("-")


def root_of(ws: Workspace, branch: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9._/-]+", branch) or ".." in branch.split("/"):
        raise WorkError(f"bad branch name {branch!r}")
    return ws.root / ".worktrees" / branch


def _rel_link(link: Path, target: Path) -> None:
    link.symlink_to(os.path.relpath(target, link.parent))


def _start_point(repo: Path, branch: str) -> list[str]:
    """`git worktree add` arguments after the path: existing local branch, else the remote
    branch, else a new branch from main."""
    if _git(["rev-parse", "-q", "--verify", f"refs/heads/{branch}"], repo, check=False).returncode == 0:
        return [branch]
    remotes = _git(["remote"], repo).stdout.split()
    if "origin" in remotes:
        _git(["fetch", "-q", "origin"], repo, check=False)
        if _git(["rev-parse", "-q", "--verify", f"refs/remotes/origin/{branch}"], repo, check=False).returncode == 0:
            return ["--track", "-b", branch, f"origin/{branch}"]
        if _git(["rev-parse", "-q", "--verify", "refs/remotes/origin/main"], repo, check=False).returncode == 0:
            return ["--no-track", "-b", branch, "origin/main"]
    base = "main" if _git(["rev-parse", "-q", "--verify", "refs/heads/main"], repo, check=False).returncode == 0 else "HEAD"
    return ["-b", branch, base]


def start(ws: Workspace, branch: str, repos: list[str], log=print) -> Path:
    if ws.root.parent.name == ".worktrees" or (ws.root / MARKER).exists():
        raise WorkError("run `curatrix work start` from the main workspace root, not from a worktree")
    if not repos:
        raise WorkError("name at least one repo")
    if not (ws.root / ".west" / "config").is_file():
        raise WorkError(f"{ws.root} is not a west workspace (no .west/config)")
    wroot = root_of(ws, branch)
    chosen = []
    for name in repos:
        r = ws.repo(name)
        if "/" in r.rel:
            raise WorkError(f"{name}: only top-level repos can be worktrees (it is at {r.rel})")
        chosen.append(r)
    existing = json.loads((wroot / MARKER).read_text()) if (wroot / MARKER).is_file() else None
    wroot.mkdir(parents=True, exist_ok=True)
    have = set(existing["repos"]) if existing else set()
    for r in chosen:
        dst = wroot / r.rel
        if r.rel in have and dst.exists():
            log(f"  {r.rel}: worktree exists")
            continue
        if dst.is_symlink():
            dst.unlink()                       # a repo added to an existing worktree set
        _git(["worktree", "add", "-q", str(dst), *_start_point(r.path, branch)], r.path)
        log(f"  {r.rel}: worktree on {branch} -> {ws.rel(dst)}")
        have.add(r.rel)
    # .west: own folder, copied config (west's topdir is where .west/ is)
    wd = wroot / ".west"
    wd.mkdir(exist_ok=True)
    shutil.copyfile(ws.root / ".west" / "config", wd / "config")
    # build -> <ws>/build/<branch>/
    b = ws.build(slug(branch))
    b.mkdir(parents=True, exist_ok=True)
    if not (wroot / "build").is_symlink():
        _rel_link(wroot / "build", b)
    # everything else: symlinks to the main checkout
    for entry in sorted(ws.root.iterdir()):
        if entry.name in NOT_LINKED or entry.name in have:
            continue
        link = wroot / entry.name
        if link.is_symlink() or link.exists():
            continue
        _rel_link(link, entry)
    (wroot / MARKER).write_text(json.dumps({
        "branch": branch, "repos": sorted(have), "main_workspace": str(ws.root),
        "build": ws.rel(b), "created": (existing or {}).get("created") or dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
    }, indent=2) + "\n")
    log(f"worktree set {ws.rel(wroot)} (builds: {ws.rel(b)}). Work there: cd {ws.rel(wroot)}")
    return wroot


def done(ws: Workspace, branch: str, force: bool = False, delete_branch: bool = False, log=print) -> None:
    main_root = ws.root
    if (main_root / MARKER).is_file():         # called from inside the worktree set
        main_root = Path(json.loads((main_root / MARKER).read_text())["main_workspace"])
    wroot = main_root / ".worktrees" / branch
    meta_file = wroot / MARKER
    if not meta_file.is_file():
        raise WorkError(f"no worktree set {wroot} (curatrix work start {branch} ...)")
    meta = json.loads(meta_file.read_text())
    dirty = []
    for rel in meta["repos"]:
        d = wroot / rel
        if d.is_dir() and _git(["status", "--porcelain"], d).stdout.strip():
            dirty.append(rel)
    if dirty and not force:
        raise WorkError(f"uncommitted changes in {', '.join(dirty)} (commit, or --force to drop them)")
    for rel in meta["repos"]:
        repo = main_root / rel
        d = wroot / rel
        if d.exists():
            _git(["worktree", "remove", *(["--force"] if force else []), str(d)], repo)
        _git(["worktree", "prune"], repo, check=False)
        log(f"  {rel}: worktree removed")
        if delete_branch:
            r = _git(["branch", "-d", branch], repo, check=False)
            log(f"  {rel}: branch {branch} " + ("deleted" if r.returncode == 0 else f"kept ({r.stderr.strip()})"))
    for entry in list(wroot.iterdir()):
        if entry.is_symlink():
            entry.unlink()
    shutil.rmtree(wroot / ".west", ignore_errors=True)
    meta_file.unlink()
    try:
        wroot.rmdir()
        p = wroot.parent
        while p != main_root / ".worktrees" and not any(p.iterdir()):   # feat/x -> remove feat/
            p.rmdir()
            p = p.parent
    except OSError as e:
        raise WorkError(f"{wroot} not empty after removing the worktrees: {e}") from e
    log(f"worktree set {branch} removed (build output stays in build/{slug(branch)}/)")


def listing(ws: Workspace) -> list[dict]:
    base = ws.root / ".worktrees"
    return [json.loads(m.read_text()) for m in sorted(base.rglob(MARKER))] if base.is_dir() else []
