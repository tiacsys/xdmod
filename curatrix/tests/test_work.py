"""curatrix work start/done (D125, 4.4c) in a real west workspace made of local repos.

Proves that from the set (1) `west topdir` / `west list` -- and so `west build` and Zephyr's module
discovery -- see the set's repos, (2) registry paths `../../<repo>/...` stay inside the set in both
directions (a repo of the change read by a repo outside it, and the reverse), also when resolved
physically, (3) curatrix finds the set root from a symlinked folder, (4) builds go to
build/wt-<branch>/, (5) the main checkouts stay untouched.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from curatrix import work
from curatrix.ws import Workspace, find_root

WEST = Path(sys.executable).parent / "west"
REAL_ZEPHYR = Path(__file__).resolve().parents[3] / "zephyr"
REG = "documents:\n  {doc}: {{doc_dir: ../../{up}/docs/{doc}}}\n"


def git(cwd, *args):
    return subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@x", *args], cwd=cwd, check=True,
                          capture_output=True, text=True).stdout.strip()


def make_repo(path: Path, files: dict[str, str]) -> Path:
    path.mkdir(parents=True)
    git(path, "init", "-q", "-b", "main")
    for f, text in files.items():
        (path / f).parent.mkdir(parents=True, exist_ok=True)
        (path / f).write_text(text)
    git(path, "add", ".")
    git(path, "commit", "-q", "-m", "init")
    return path


@pytest.fixture
def ws(tmp_path, monkeypatch):
    if not WEST.exists():
        pytest.skip("west not installed in this venv")
    src = tmp_path / "src"
    # syseng reads ee's docs (../../robarm-ee), ee reads syseng's (../../robarm-syseng)
    make_repo(src / "robarm-syseng", {"docs/se-req/index.rst": "Requirements (main)\n", "checks.yaml": "version: 1\n",
                                      "docs/documents.yaml": REG.format(doc="ee-design", up="robarm-ee")})
    make_repo(src / "robarm-ee", {"docs/documents.yaml": REG.format(doc="se-req", up="robarm-syseng"),
                                  "docs/ee-design/index.rst": "EE design (main)\n",
                                  "checks.yaml": "version: 1\n", "zephyr/module.yml": "name: robarm-ee\nbuild:\n  cmake: .\n",
                                  "CMakeLists.txt": "# module\n"})
    root = tmp_path / "ws"
    projects = "\n".join(f"    - name: {n}\n      url: file://{src / n}\n      revision: main" for n in ("robarm-syseng", "robarm-ee"))
    make_repo(root / "robarm-manifest", {"west.yml": f"manifest:\n  self:\n    path: robarm-manifest\n  projects:\n{projects}\n",
                                         "checks.yaml": "version: 1\n"})
    (root / ".venv" / "bin").mkdir(parents=True)
    (root / ".venv" / "bin" / "west").symlink_to(WEST)
    (root / "build").mkdir()
    (root / "zephyr" / "scripts").mkdir(parents=True)      # stands for a shared, linked tree
    # = `west init -l robarm-manifest` (which refuses to run inside the real workspace around build/)
    (root / ".west").mkdir()
    (root / ".west" / "config").write_text("[manifest]\npath = robarm-manifest\nfile = west.yml\n")
    subprocess.run([str(WEST), "update"], cwd=root, check=True, capture_output=True)
    for n in ("robarm-syseng", "robarm-ee"):       # like a bootstrapped workspace: an origin remote
        if "origin" not in git(root / n, "remote").split():
            git(root / n, "remote", "add", "origin", str(src / n))
        git(root / n, "fetch", "-q", "origin")
    monkeypatch.delenv("XD_WORKSPACE", raising=False)
    monkeypatch.chdir(root)
    return Workspace(root)


def west_in(cwd, *args):
    return subprocess.run([str(WEST), *args], cwd=cwd, check=True, capture_output=True, text=True,
                          env={k: v for k, v in os.environ.items() if k != "ZEPHYR_BASE"}).stdout.strip()


def physical(p: Path) -> str:
    return os.path.realpath(p)


def test_worktree_set_is_seen_by_west_registries_and_builds(ws, monkeypatch):
    head_before = git(ws.root / "robarm-ee", "rev-parse", "HEAD")
    w = work.start(ws, "feat/x", ["robarm-syseng"], log=lambda *_: None)    # change syseng only
    assert w == ws.root / ".worktrees" / "feat" / "x"
    assert git(w / "robarm-syseng", "rev-parse", "--abbrev-ref", "HEAD") == "feat/x"
    # repos outside the change are detached worktrees inside the set, not symlinks
    for rel in ("robarm-ee", "robarm-manifest"):
        assert (w / rel / ".git").is_file() and not (w / rel).is_symlink()
        assert git(w / rel, "rev-parse", "HEAD") == git(ws.root / rel, "rev-parse", "HEAD")
    assert (w / "zephyr").is_symlink() and (w / ".venv").is_symlink()
    assert (w / ".west").is_dir() and not (w / ".west").is_symlink()
    # (1) west sees the set
    assert west_in(w, "topdir") == str(w)
    paths = dict(line.split() for line in west_in(w, "list", "-f", "{name} {abspath}").splitlines())
    assert paths["robarm-ee"] == str(w / "robarm-ee") and paths["robarm-syseng"] == str(w / "robarm-syseng")
    assert west_in(w / "robarm-ee", "topdir") == str(w)                        # also from a repo outside the change
    assert west_in(ws.root, "list", "-f", "{abspath}", "robarm-ee") == str(ws.root / "robarm-ee")
    # (2) ../../ paths, resolved PHYSICALLY: a repo outside the change reads the changed repo of the set
    (w / "robarm-syseng/docs/se-req/index.rst").write_text("Requirements (branch)\n")
    p = w / "robarm-ee" / "docs" / "../../robarm-syseng/docs/se-req/index.rst"
    assert Path(physical(p)).read_text() == "Requirements (branch)\n"
    assert physical(p).startswith(physical(w))
    # ... and the changed repo reads a repo outside the change inside the set too
    q = w / "robarm-syseng" / "docs" / "../../robarm-ee/docs/ee-design/index.rst"
    assert physical(q).startswith(physical(w)) and Path(physical(q)).read_text() == "EE design (main)\n"
    assert (ws.root / "robarm-syseng/docs/se-req/index.rst").read_text() == "Requirements (main)\n"
    # (3) curatrix finds the set root from a repo and from a symlinked folder of the set
    for sub in (w / "robarm-ee" / "docs", w / "zephyr" / "scripts"):
        monkeypatch.chdir(sub)
        monkeypatch.setenv("PWD", str(sub))
        assert find_root() == w
    monkeypatch.chdir(ws.root)
    monkeypatch.setenv("PWD", str(ws.root))
    # (4) builds: build/wt-<branch>/<area>
    assert (w / "build").resolve() == (ws.root / "build" / "wt-feat-x").resolve()
    assert Workspace(w).build("robarm-ee").resolve() == (ws.root / "build" / "wt-feat-x" / "robarm-ee").resolve()
    # (5) the main checkout is untouched
    assert git(ws.root / "robarm-ee", "rev-parse", "HEAD") == head_before
    # adding a repo to the change moves its detached worktree onto the branch
    work.start(ws, "feat/x", ["robarm-ee"], log=lambda *_: None)
    assert git(w / "robarm-ee", "rev-parse", "--abbrev-ref", "HEAD") == "feat/x"
    assert [m["repos"] for m in work.listing(ws)] == [["robarm-ee", "robarm-syseng"]]
    # done: refused while dirty, then removed (branches kept)
    with pytest.raises(work.WorkError, match="uncommitted"):
        work.done(ws, "feat/x", log=lambda *_: None)
    git(w / "robarm-syseng", "checkout", "--", ".")
    work.done(ws, "feat/x", log=lambda *_: None)
    assert not (ws.root / ".worktrees" / "feat").exists()
    assert git(ws.root / "robarm-ee", "branch", "--list", "feat/x") != ""
    for rel in ("robarm-ee", "robarm-syseng", "robarm-manifest"):
        assert ".worktrees" not in git(ws.root / rel, "worktree", "list")


@pytest.mark.skipif(not (REAL_ZEPHYR / "scripts" / "zephyr_module.py").is_file(), reason="no Zephyr tree")
def test_zephyr_module_discovery_sees_the_worktree(ws, tmp_path):
    w = work.start(ws, "feat/mod", ["robarm-syseng"], log=lambda *_: None)
    out = tmp_path / "modules.cmake"
    r = subprocess.run([sys.executable, str(REAL_ZEPHYR / "scripts" / "zephyr_module.py"), "--zephyr-base", str(REAL_ZEPHYR),
                        "--cmake-out", str(out)], cwd=w, capture_output=True, text=True,
                       env={k: v for k, v in os.environ.items() if k != "ZEPHYR_BASE"})
    assert r.returncode == 0, r.stderr
    assert f'"robarm-ee":"{w / "robarm-ee"}"' in out.read_text()            # a repo outside the change, too


def test_names_rerun_and_half_done_start(ws, monkeypatch):
    with pytest.raises(work.WorkError, match="bad branch"):
        work.start(ws, "../x", ["robarm-ee"])
    w = work.start(ws, "feat/y", ["robarm-ee"], log=lambda *_: None)
    with pytest.raises(work.WorkError, match="main workspace root"):
        work.start(Workspace(w), "feat/z", ["robarm-ee"])
    with pytest.raises(work.WorkError, match="nest"):
        work.start(ws, "feat", ["robarm-ee"])
    with pytest.raises(work.WorkError, match="build folder"):
        work.start(ws, "feat-y", ["robarm-ee"])
    work.start(ws, "feat/y", ["robarm-ee"], log=lambda *_: None)            # a rerun is fine
    work.done(ws, "feat/y", log=lambda *_: None)
    # a start that fails half-way (here: a repo of the set can't be added) leaves a marker,
    # so `done` can clean up
    blocker = ws.root / ".worktrees" / "feat" / "h" / "robarm-syseng"
    blocker.mkdir(parents=True)
    (blocker / "junk").write_text("x")
    with pytest.raises(work.WorkError, match="not a worktree"):
        work.start(ws, "feat/h", ["robarm-ee"], log=lambda *_: None)
    assert (ws.root / ".worktrees/feat/h" / work.MARKER).is_file()
    (blocker / "junk").unlink()
    blocker.rmdir()
    work.start(ws, "feat/h", ["robarm-ee"], log=lambda *_: None)            # repeated: completes
    work.done(ws, "feat/h", log=lambda *_: None)
    assert not (ws.root / ".worktrees" / "feat").exists()
