"""Git worktrees for parallel work (D125, workflow.md §4, task 4.4c).

``curatrix work start <branch> <repos...>`` makes ``<ws>/.worktrees/<branch>/`` a workspace root
of its own:

- **every** framework repo (xdmod, the manifest, every robarm-* repo: the active west projects
  with a ``checks.yaml``, plus xdmod) is a **git worktree** there. The named repos are on
  ``<branch>`` (new from the repo's ``main``, or the existing local/remote branch); all others are
  **detached at the main checkout's HEAD** (read-only by convention). That way every path between
  our repos stays inside the set, also when it is resolved physically: a registry path
  ``../../robarm-syseng/docs/se-req`` from any repo of the set reaches the set's robarm-syseng,
  whichever repos the change touches;
- third-party trees and shared state (``zephyr/``, ``modules/``, ``tools/``, ``libs/``, ``.venv``,
  ``.xdmod``, ``CLAUDE.md``, ``.claude``) are **relative symlinks** to the main checkout (not
  duplicated; nothing in them refers to our repos by relative path);
- ``.west/`` is a real folder with a copy of the west config. West finds its topdir from the
  current directory, so ``west list`` -- and with it Zephyr's module discovery
  (``zephyr_module.py``), ``west build`` and the docs build (``west topdir``) -- see the set;
- ``build`` is a symlink to ``<ws>/build/wt-<branch>/`` (``wt-`` keeps branch builds apart from
  the repo areas ``build/<repo>/``), so builds go to ``build/wt-<branch>/<area>/``.

Work from the set root (``cd .worktrees/<branch>``) or from a repo inside it. curatrix finds the
set root also from a symlinked folder (``ws.find_root`` follows the logical ``$PWD``); other tools
(west) find it only from real folders of the set. If xdmod is on the branch, curatrix runs its own
code from the set (cli.main re-executes itself). Never run ``west update`` / ``curatrix update``
in a set: it would move the worktrees to the pins.

``curatrix work done <branch>`` removes all worktrees of the set (refused for uncommitted changes
unless ``--force``), the symlinks and the folder; branches stay (``--delete-branch`` deletes them
if merged). A ``start`` that failed half-way can be repeated or undone with ``done``: the marker
file is written first.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
import shutil
from pathlib import Path

from curatrix import limits
from curatrix.ws import Workspace

MARKER = ".xdmod-worktree.json"
NOT_LINKED = {".worktrees", ".west", "build", ".git"}


class WorkError(Exception):
    pass


def _git(args, cwd, ws: Workspace, check=True):
    r = limits.run(["git", *args], "git", ws, cwd=cwd, capture_output=True, text=True)
    if check and r.returncode:
        raise WorkError(f"git {' '.join(args)} ({cwd}) failed: {r.stderr.strip()}")
    return r


def slug(branch: str) -> str:
    """Folder name of the branch's build area: build/wt-<slug>/ (feat/x -> wt-feat-x)."""
    return "wt-" + re.sub(r"[^A-Za-z0-9_.-]+", "-", branch).strip("-")


def root_of(ws: Workspace, branch: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9._/-]+", branch) or ".." in branch.split("/") or branch.startswith("/"):
        raise WorkError(f"bad branch name {branch!r}")
    return ws.root / ".worktrees" / branch


def _rel_link(link: Path, target: Path) -> None:
    link.symlink_to(os.path.relpath(target, link.parent))


def _is_worktree(d: Path) -> bool:
    return (d / ".git").is_file()


def framework_repos(ws: Workspace):
    """Repos that become worktrees: active projects with a checks.yaml, and xdmod."""
    return [r for r in ws.repos if r.is_framework_repo and "/" not in r.rel and (r.path / ".git").exists()]


def _start_point(repo: Path, branch: str, ws) -> list[str]:
    """`git worktree add` arguments after the path: existing local branch, else the remote
    branch, else a new branch from main."""
    if _git(["rev-parse", "-q", "--verify", f"refs/heads/{branch}"], repo, ws, check=False).returncode == 0:
        return [branch]
    if "origin" in _git(["remote"], repo, ws).stdout.split():
        _git(["fetch", "-q", "origin"], repo, ws, check=False)
        if _git(["rev-parse", "-q", "--verify", f"refs/remotes/origin/{branch}"], repo, ws, check=False).returncode == 0:
            return ["--track", "-b", branch, f"origin/{branch}"]
        if _git(["rev-parse", "-q", "--verify", "refs/remotes/origin/main"], repo, ws, check=False).returncode == 0:
            return ["--no-track", "-b", branch, "origin/main"]
    base = "main" if _git(["rev-parse", "-q", "--verify", "refs/heads/main"], repo, ws, check=False).returncode == 0 else "HEAD"
    return ["-b", branch, base]


def _check_names(ws: Workspace, branch: str) -> None:
    for m in listing(ws):
        other = m["branch"]
        if other != branch and (other.startswith(branch + "/") or branch.startswith(other + "/")):
            raise WorkError(f"{branch!r} and the existing set {other!r} would nest in .worktrees/")
        if other != branch and slug(other) == slug(branch):
            raise WorkError(f"{branch!r} and the existing set {other!r} share the build folder build/{slug(branch)}/")


def _write_marker(wroot: Path, meta: dict) -> None:
    (wroot / MARKER).write_text(json.dumps(meta, indent=2, sort_keys=True) + "\n")


def start(ws: Workspace, branch: str, repos: list[str], log=print) -> Path:
    if ws.root.parent.name == ".worktrees" or (ws.root / MARKER).exists() or ".worktrees" in ws.root.parts:
        raise WorkError("run `curatrix work start` from the main workspace root, not from a worktree set")
    if not repos:
        raise WorkError("name at least one repo")
    if not (ws.root / ".west" / "config").is_file():
        raise WorkError(f"{ws.root} is not a west workspace (no .west/config)")
    wroot = root_of(ws, branch)
    _check_names(ws, branch)
    fw = {r.rel: r for r in framework_repos(ws)}
    on_branch = []
    for name in repos:
        r = ws.repo(name)
        if r.rel not in fw:
            raise WorkError(f"{name}: not a top-level framework repo (xdmod, the manifest, robarm-*)")
        on_branch.append(r.rel)
    meta = json.loads((wroot / MARKER).read_text()) if (wroot / MARKER).is_file() else {
        "branch": branch, "main_workspace": str(ws.root), "build": ws.rel(ws.build(slug(branch))),
        "created": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "repos": [], "detached": []}
    meta["repos"] = sorted(set(meta["repos"]) | set(on_branch))
    meta["detached"] = sorted(set(fw) - set(meta["repos"]))
    wroot.mkdir(parents=True, exist_ok=True)
    _write_marker(wroot, meta)                 # first: a failed start can be repeated or undone
    for rel, r in sorted(fw.items()):
        dst = wroot / rel
        want_branch = rel in meta["repos"]
        if dst.is_symlink():
            dst.unlink()
        if _is_worktree(dst):
            cur = _git(["symbolic-ref", "-q", "--short", "HEAD"], dst, ws, check=False).stdout.strip()
            if not want_branch or cur == branch:
                continue
            if _git(["status", "--porcelain"], dst, ws).stdout.strip():
                raise WorkError(f"{ws.rel(dst)} has changes; cannot put it on {branch}")
            _git(["worktree", "remove", str(dst)], r.path, ws)     # detached -> on the branch
        elif dst.exists():
            raise WorkError(f"{ws.rel(dst)} exists and is not a worktree")
        if want_branch:
            _git(["worktree", "add", "-q", str(dst), *_start_point(r.path, branch, ws)], r.path, ws)
            log(f"  {rel}: worktree on {branch}")
        else:
            head = _git(["rev-parse", "HEAD"], r.path, ws).stdout.strip()
            _git(["worktree", "add", "-q", "--detach", str(dst), head], r.path, ws)
            log(f"  {rel}: worktree detached at {head[:12]} (main checkout's HEAD)")
    wd = wroot / ".west"
    wd.mkdir(exist_ok=True)
    shutil.copyfile(ws.root / ".west" / "config", wd / "config")
    b = ws.build(slug(branch))
    b.mkdir(parents=True, exist_ok=True)
    if not (wroot / "build").is_symlink():
        _rel_link(wroot / "build", b)
    for entry in sorted(ws.root.iterdir()):
        if entry.name in NOT_LINKED or entry.name in fw:
            continue
        link = wroot / entry.name
        if link.is_symlink() or link.exists():
            continue
        _rel_link(link, entry)
    log(f"worktree set {ws.rel(wroot)}: on {branch}: {', '.join(meta['repos'])}; builds: {ws.rel(b)}. "
        f"Work there: cd {ws.rel(wroot)}")
    return wroot


def done(ws: Workspace, branch: str, force: bool = False, delete_branch: bool = False, log=print) -> None:
    main_root = ws.root
    if (main_root / MARKER).is_file():         # called from inside the worktree set
        main_root = Path(json.loads((main_root / MARKER).read_text())["main_workspace"])
    mws = Workspace(main_root)
    wroot = main_root / ".worktrees" / branch
    meta_file = wroot / MARKER
    if not meta_file.is_file():
        raise WorkError(f"no worktree set {wroot} (curatrix work start {branch} ...)")
    meta = json.loads(meta_file.read_text())
    all_rel = sorted(set(meta.get("repos", [])) | set(meta.get("detached", [])))
    dirty = [rel for rel in all_rel if _is_worktree(wroot / rel)
             and _git(["status", "--porcelain"], wroot / rel, mws).stdout.strip()]
    if dirty and not force:
        raise WorkError(f"uncommitted changes in {', '.join(dirty)} (commit, or --force to drop them)")
    for rel in all_rel:
        repo, d = main_root / rel, wroot / rel
        if _is_worktree(d):
            _git(["worktree", "remove", *(["--force"] if force else []), str(d)], repo, mws)
        _git(["worktree", "prune"], repo, mws, check=False)
        if delete_branch and rel in meta.get("repos", []):
            r = _git(["branch", "-d", branch], repo, mws, check=False)
            log(f"  {rel}: branch {branch} " + ("deleted" if r.returncode == 0 else f"kept ({r.stderr.strip()})"))
    log(f"  worktrees removed: {', '.join(all_rel)}")
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
    log(f"worktree set {branch} removed (build output stays in {meta.get('build', 'build/' + slug(branch))}/)")


def listing(ws: Workspace) -> list[dict]:
    base = ws.root / ".worktrees"
    if not base.is_dir():
        return []
    out = []
    for dirpath, dirnames, filenames in os.walk(base):   # don't descend into the worktrees
        if MARKER in filenames:
            out.append(json.loads((Path(dirpath) / MARKER).read_text()))
            dirnames[:] = []
        else:
            dirnames[:] = [d for d in dirnames if not (Path(dirpath) / d / ".git").exists()]
    return sorted(out, key=lambda m: m["branch"])
