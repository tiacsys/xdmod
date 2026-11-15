"""D127 sibling resolution on local git repos (no network, no west)."""
import subprocess
from pathlib import Path

import pytest

from curatrix import ci


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def commit(repo: Path, msg: str) -> str:
    (repo / "f.txt").write_text(msg + "\n")
    git(repo, "add", "f.txt")
    git(repo, "-c", "user.name=t", "-c", "user.email=t@x", "commit", "-q", "-m", msg)
    return git(repo, "rev-parse", "HEAD")


@pytest.fixture
def upstream(tmp_path):
    """An 'upstream' repo with main: pin -> merged; a side commit not on main; branch feat/x."""
    up = tmp_path / "up"
    up.mkdir()
    git(up, "init", "-q", "-b", "main")
    pin = commit(up, "pin")
    git(up, "checkout", "-q", "-b", "side")
    side = commit(up, "side")                      # rewritten history: not an ancestor of main
    git(up, "checkout", "-q", "main")
    merged = commit(up, "merged after the pin")
    git(up, "checkout", "-q", "-b", "feat/x")
    feat = commit(up, "feature")
    git(up, "checkout", "-q", "main")
    return {"url": str(up), "pin": pin, "side": side, "main": merged, "feat": feat}


def clone(tmp_path, up, sha, name="robarm-ee"):
    """Like west: a clone without an `origin` remote, detached at the pin (depth 1)."""
    d = tmp_path / name
    d.mkdir()
    git(d, "init", "-q")
    git(d, "fetch", "-q", "--depth=1", f"file://{up['url']}", sha)
    git(d, "checkout", "-q", "--detach", sha)
    return ci.Project(name, d, f"file://{up['url']}", sha)


def test_same_name_branch_wins(tmp_path, upstream):
    p = clone(tmp_path, upstream, upstream["pin"])
    r = ci.resolve_one(p, "feat/x", "robarm-sw", "")
    assert (r.rule, r.sha) == ("branch", upstream["feat"])
    assert git(p.path, "rev-parse", "HEAD") == upstream["feat"]


def test_main_when_pin_is_ancestor(tmp_path, upstream):
    p = clone(tmp_path, upstream, upstream["pin"])
    r = ci.resolve_one(p, "feat/other", "robarm-sw", "")
    assert (r.rule, r.sha) == ("main", upstream["main"])


def test_pin_when_not_an_ancestor(tmp_path, upstream):
    p = clone(tmp_path, upstream, upstream["side"])
    r = ci.resolve_one(p, "feat/other", "robarm-sw", "")
    assert (r.rule, r.sha) == ("pin", upstream["side"])
    assert git(p.path, "rev-parse", "HEAD") == upstream["side"]


def test_push_to_main_skips_rule_1(tmp_path, upstream):
    p = clone(tmp_path, upstream, upstream["side"])
    r = ci.resolve_one(p, "main", "robarm-sw", "")
    assert r.rule == "pin"                          # a `main` branch exists, but the pin is not in it


def test_repo_under_check_at_head(tmp_path, upstream):
    p = clone(tmp_path, upstream, upstream["pin"])
    r = ci.resolve_one(p, "feat/x", "robarm-ee", upstream["feat"])
    assert (r.rule, r.sha) == ("head", upstream["feat"])
    assert git(p.path, "rev-parse", "HEAD") == upstream["feat"]
