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


def test_ls_remote_failure_is_an_error_not_no_branch(tmp_path, upstream):
    p = clone(tmp_path, upstream, upstream["pin"])
    p.url = f"file://{tmp_path / 'does-not-exist'}"
    with pytest.raises(RuntimeError, match="ls-remote"):
        ci.resolve_one(p, "feat/x", "robarm-sw", "")


def test_tags_are_fetched(tmp_path, upstream):
    git(Path(upstream["url"]), "-c", "user.name=t", "-c", "user.email=t@x", "tag", "-a", "-m", "b", "baseline/v0.1.0", upstream["pin"])
    p = clone(tmp_path, upstream, upstream["pin"])
    ci.resolve_one(p, "feat/other", "robarm-sw", "")
    assert git(p.path, "describe", "--tags", upstream["pin"]) == "baseline/v0.1.0"


def test_stacked_pr_sibling_uses_the_base_branch(tmp_path, upstream, monkeypatch):
    """A stacked PR (head feat/y on base feat/x): a sibling without feat/y takes feat/x (task 5.7)."""
    monkeypatch.setenv("GITHUB_BASE_REF", "feat/x")
    p = clone(tmp_path, upstream, upstream["pin"], "robarm-sw")
    r = ci.resolve_one(p, "feat/y", "robarm-ee", "")
    assert r.rule == "base" and r.sha == upstream["feat"]


def test_fetch_base_from_published_needs(tmp_path):
    from curatrix.ws import Repo, Workspace
    pages = tmp_path / "pages" / "latest" / "doc-a"
    pages.mkdir(parents=True)
    (pages / "needs.json").write_text('{"versions": {}}')
    root = tmp_path / "ws"
    repo = root / "r"
    (repo / "docs").mkdir(parents=True)
    (repo / "checks.yaml").write_text("version: 1\ndocs: {registry: docs/documents.yaml}\n")
    (repo / "docs" / "documents.yaml").write_text(
        f"base_url: file://{tmp_path / 'pages'}/\ndocuments:\n  doc-a: {{}}\n  doc-b: {{}}\n")
    ws = Workspace(root)
    ws.__dict__["repos"] = [Repo("r", repo, "r")]
    out = tmp_path / "base"
    assert ci.fetch_base(ws, "r", out, log=lambda *_: None) == 1
    assert (out / "doc-a" / "needs.json").exists() and not (out / "doc-b").exists()
