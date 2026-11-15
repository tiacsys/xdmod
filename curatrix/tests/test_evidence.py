"""Run records (4.5a), the evidence branch writer and the TR reader (4.6)."""
import copy
import json
import subprocess
from pathlib import Path

import pytest

from curatrix import evidence as ev
from curatrix.ws import Workspace
from helpers import make_ws

SHA = "a" * 40


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def record(ok=True, kind="sim", tc="SW-TC-0007", sha=SHA):
    problems = [] if ok else ["robarm-sw: tree not clean"]
    repo = {"sha": sha, "pin": sha, "clean": ok, "on": "main"}
    return {
        "schema": ev.SCHEMA_ID, "run_id": "20261115T010203Z-0123abcd", "kind": kind,
        "created": "2026-11-15T01:02:03Z", "recorded_by": "tester", "config": "SYS-CFG-0001",
        "setup": "bench1" if kind == "hil" else None, "platform": "native_sim/native",
        "firmware": {"file": "x/zephyr/zephyr.exe", "sha256": "f" * 64},
        "workspace": {"manifest": dict(repo), "repos": {"robarm-sw": dict(repo), "zephyr": {"sha": "b" * 40, "pin": "b" * 40, "clean": True}}},
        "evidence": {"ok": ok, "base": "main", "problems": problems},
        "results": [{"test": "robarm.joint.joint.limits", "suite": "robarm.joint", "test_case": tc, "status": "passed", "duration": 0.1},
                    {"test": "robarm.joint.joint.smoke", "suite": "robarm.joint", "test_case": None, "status": "passed", "duration": None}],
        "tool": {"name": "twister", "zephyr_version": "v4.4.2", "files": {}},
    }


def test_schema_accepts_and_rejects():
    assert ev.validate(record()) == []
    bad = record()
    bad["firmware"]["sha256"] = "xyz"
    assert any("firmware/sha256" in e for e in ev.validate(bad))
    bad = record()
    bad["unknown"] = 1
    assert ev.validate(bad)
    bad = record(kind="hil")
    bad["setup"] = None
    assert any("setup" in e for e in ev.validate(bad))
    bad = record()
    bad["evidence"]["problems"] = ["x"]
    assert any("evidence.ok" in e for e in ev.validate(bad))


def test_test_case_ids_from_ztest_comments(tmp_path):
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "main.c").write_text(
        "/** @brief limits.\n * Verifies SW-REQ-0001. Test case: SW-TC-0007 */\nZTEST(joint, test_limits)\n{\n}\n"
        "/** no id here */\nZTEST(joint, test_smoke) {}\n"
        "/* SW-TC-0009 */\nZTEST_F(joint, test_fixture) {}\n")
    m = ev.test_case_map([tmp_path])
    assert m == {"joint.limits": "SW-TC-0007", "joint.fixture": "SW-TC-0009"}
    assert ev._tc_for("robarm.joint.joint.limits", "robarm.joint", m) == "SW-TC-0007"
    assert ev._tc_for("robarm.joint.joint.smoke", "robarm.joint", m) is None


def test_reader_makes_tr_needs_and_marks_stale():
    doc = ev.to_needs([record(), record(ok=False, tc="SW-TC-0008")], pins={"robarm-sw": SHA, "zephyr": "b" * 40})
    n = doc["versions"][""]["needs"]
    assert list(n) == ["TR-SW-TC-0007-0123abcd"]                       # previews and untraced results: no TR
    tr = n["TR-SW-TC-0007-0123abcd"]
    assert tr["result_of"] == ["SW-TC-0007"] and tr["method"] == "test" and tr["verdict"] == "passed"
    assert tr["shas"] == [f"robarm-sw={SHA}", f"zephyr={'b' * 40}"] and tr["tags"] == []
    from curatrix import ids
    assert ids.ID_RE.match("TR-SW-TC-0007-0123abcd")
    n2 = ev.to_needs([record(kind="hil")], pins={"robarm-sw": "c" * 40})["versions"][""]["needs"]
    tr2 = n2["TR-SW-TC-0007-0123abcd"]
    assert tr2["method"] == "hil" and tr2["tags"] == ["stale"] and "Stale" in tr2["content"]


@pytest.fixture
def integration(tmp_path, monkeypatch):
    """robarm-integration with main, and a bare 'remote' it was cloned from."""
    root = make_ws(tmp_path, monkeypatch)
    remote = tmp_path / "remote.git"
    git(tmp_path, "init", "-q", "--bare", "-b", "main", str(remote))
    repo = root / "robarm-integration"
    repo.mkdir()
    git(repo, "init", "-q", "-b", "main")
    (repo / "README.md").write_text("main\n")
    git(repo, "add", ".")
    git(repo, "-c", "user.name=t", "-c", "user.email=t@x", "commit", "-q", "-m", "main")
    git(repo, "push", "-q", str(remote), "main")
    git(repo, "config", "user.name", "t")
    git(repo, "config", "user.email", "t@x")
    tw = tmp_path / "twister"
    tw.mkdir()
    (tw / "twister.json").write_text("{}\n")
    return Workspace(root), repo, f"file://{remote}", tw


def test_writer_creates_orphan_branch_and_never_touches_main(integration):
    ws, repo, url, tw = integration
    main_before = git(repo, "rev-parse", "HEAD")
    with pytest.raises(ev.EvidenceError, match="neither"):
        ev.write(ws, record(), tw, repo, url, "evidence")
    sha = ev.write(ws, record(), tw, repo, url, "evidence", create=True, trailer="Co-Authored-By: x <x@y>", log=lambda *_: None)
    assert git(repo, "rev-parse", "HEAD") == main_before and git(repo, "rev-parse", "--abbrev-ref", "HEAD") == "main"
    assert git(repo, "status", "--porcelain") == ""
    assert git(repo, "rev-list", "--count", "evidence") == "1"                       # orphan: no main history
    files = git(repo, "ls-tree", "-r", "--name-only", "evidence").split()
    assert files == ["runs/2026/20261115T010203Z-0123abcd/record.json", "runs/2026/20261115T010203Z-0123abcd/twister.json"]
    assert "Co-Authored-By: x <x@y>" in git(repo, "log", "-1", "--format=%B", sha)
    assert ev.load_records(repo, "evidence")[0]["run_id"] == "20261115T010203Z-0123abcd"
    assert not (ws.build("evidence") / "wt-evidence").exists()                        # worktree removed
    # a second record on the same branch, after the branch was pushed
    git(repo, "push", "-q", url, "evidence")
    r2 = copy.deepcopy(record())
    r2["run_id"] = "20261115T020000Z-89abcdef"
    ev.write(ws, r2, tw, repo, url, "evidence", log=lambda *_: None)
    assert len(ev.load_records(repo, "evidence")) == 2


def test_writer_refuses_previews_on_the_evidence_branch(integration):
    ws, repo, url, tw = integration
    with pytest.raises(ev.EvidenceError, match="D60"):
        ev.write(ws, record(ok=False), tw, repo, url, "evidence", create=True)
    ev.write(ws, record(ok=False), tw, repo, url, "scratch/preview", create=True, log=lambda *_: None)  # scratch: allowed
    assert ev.to_needs(ev.load_records(repo, "scratch/preview"))["versions"][""]["needs"] == {}
