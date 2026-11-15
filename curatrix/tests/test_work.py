"""curatrix work start/done (D125, 4.4c) in a real west workspace made of local repos.

Proves that from the worktree root (1) `west topdir` / `west list` -- and so `west build` and
Zephyr's module discovery -- see the worktree repos, (2) registry paths `../../<repo>/...`
resolve to the worktree when that repo is part of the change and to the main checkout otherwise,
(3) builds go to build/<branch>/, (4) the main checkouts stay untouched.
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from curatrix import work
from curatrix.ws import Workspace

WEST = Path(sys.executable).parent / "west"
REAL_ZEPHYR = Path(__file__).resolve().parents[3] / "zephyr"


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
    make_repo(src / "robarm-syseng", {"docs/se-req/index.rst": "Requirements (main)\n", "checks.yaml": "version: 1\n"})
    make_repo(src / "robarm-ee", {"docs/documents.yaml": "documents:\n  se-req: {doc_dir: ../../robarm-syseng/docs/se-req}\n",
                                  "checks.yaml": "version: 1\n", "zephyr/module.yml": "name: robarm-ee\nbuild:\n  cmake: .\n",
                                  "CMakeLists.txt": "# module\n"})
    root = tmp_path / "ws"
    projects = "\n".join(f"    - name: {n}\n      url: file://{src / n}\n      revision: main" for n in ("robarm-syseng", "robarm-ee"))
    make_repo(root / "robarm-manifest", {"west.yml": f"manifest:\n  self:\n    path: robarm-manifest\n  projects:\n{projects}\n"})
    (root / ".venv" / "bin").mkdir(parents=True)
    (root / ".venv" / "bin" / "west").symlink_to(WEST)
    (root / "build").mkdir()
    (root / "zephyr").mkdir()                      # stands for a shared, linked tree
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


def test_worktree_set_is_seen_by_west_registries_and_builds(ws):
    head_before = git(ws.root / "robarm-ee", "rev-parse", "HEAD")
    w = work.start(ws, "feat/x", ["robarm-ee"], log=lambda *_: None)
    assert w == ws.root / ".worktrees" / "feat" / "x"
    assert git(w / "robarm-ee", "rev-parse", "--abbrev-ref", "HEAD") == "feat/x"
    assert (w / "robarm-syseng").is_symlink() and (w / "zephyr").is_symlink() and (w / ".venv").is_symlink()
    assert (w / ".west").is_dir() and not (w / ".west").is_symlink()
    # (1) west, and with it `west build` and Zephyr's module discovery, sees the worktree
    assert west_in(w, "topdir") == str(w)
    paths = dict(line.split() for line in west_in(w, "list", "-f", "{name} {abspath}").splitlines())
    assert paths["robarm-ee"] == str(w / "robarm-ee")
    assert west_in(ws.root, "list", "-f", "{abspath}", "robarm-ee") == str(ws.root / "robarm-ee")
    # curatrix's own view from the worktree root
    wws = Workspace(w)
    assert wws.repo("robarm-ee").path == w / "robarm-ee"
    # (2) ../../ registry paths: other repos through the symlink to main, the worktree's own repo inside
    reg = w / "robarm-ee" / "docs"
    assert (reg / "../../robarm-syseng/docs/se-req/index.rst").read_text() == "Requirements (main)\n"
    work.start(ws, "feat/x", ["robarm-syseng"], log=lambda *_: None)          # add a repo to the set
    (w / "robarm-syseng" / "docs/se-req/index.rst").write_text("Requirements (branch)\n")
    assert (reg / "../../robarm-syseng/docs/se-req/index.rst").read_text() == "Requirements (branch)\n"
    assert (ws.root / "robarm-syseng/docs/se-req/index.rst").read_text() == "Requirements (main)\n"
    # (3) builds: build/<branch>/<area>
    assert (w / "build").resolve() == (ws.root / "build" / "feat-x").resolve()
    assert wws.build("robarm-ee").resolve() == (ws.root / "build" / "feat-x" / "robarm-ee").resolve()
    # (4) the main checkout is untouched
    assert git(ws.root / "robarm-ee", "rev-parse", "HEAD") == head_before
    assert [m["repos"] for m in work.listing(ws)] == [["robarm-ee", "robarm-syseng"]]
    # done: refused while dirty, then removed (branches kept unless merged and asked for)
    with pytest.raises(work.WorkError, match="uncommitted"):
        work.done(ws, "feat/x", log=lambda *_: None)
    git(w / "robarm-syseng", "checkout", "--", ".")
    work.done(ws, "feat/x", log=lambda *_: None)
    assert not (ws.root / ".worktrees" / "feat").exists()
    assert git(ws.root / "robarm-ee", "branch", "--list", "feat/x") != ""
    assert "feat/x" not in git(ws.root / "robarm-ee", "worktree", "list")


@pytest.mark.skipif(not (REAL_ZEPHYR / "scripts" / "zephyr_module.py").is_file(), reason="no Zephyr tree")
def test_zephyr_module_discovery_sees_the_worktree(ws, tmp_path):
    w = work.start(ws, "feat/mod", ["robarm-ee"], log=lambda *_: None)
    out = tmp_path / "modules.cmake"
    r = subprocess.run([sys.executable, str(REAL_ZEPHYR / "scripts" / "zephyr_module.py"), "--zephyr-base", str(REAL_ZEPHYR),
                    "--cmake-out", str(out)], cwd=w, capture_output=True, text=True,
                   env={k: v for k, v in os.environ.items() if k != "ZEPHYR_BASE"})
    assert r.returncode == 0, r.stderr
    assert f'"robarm-ee":"{w / "robarm-ee"}"' in out.read_text()


def test_bad_names_and_nested_runs(ws):
    with pytest.raises(work.WorkError, match="bad branch"):
        work.start(ws, "../x", ["robarm-ee"])
    w = work.start(ws, "feat/y", ["robarm-ee"], log=lambda *_: None)
    with pytest.raises(work.WorkError, match="main workspace root"):
        work.start(Workspace(w), "feat/z", ["robarm-ee"])
    work.done(ws, "feat/y", log=lambda *_: None)
