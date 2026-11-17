"""The check runner passes only if it checked something (task 5.1, P4-4, XD-ADR "Checks that bite")."""
import subprocess

import pytest

from curatrix import checkcfg, checks
from curatrix.ws import Repo, Workspace
from helpers import git_init


def _repo(tmp_path, yaml_text):
    root = tmp_path / "ws"
    repo = git_init(root / "r")
    (repo / "checks.yaml").write_text(yaml_text)
    return Workspace(root), Repo("r", repo, "r")


def _run(ws, repo, **kw):
    lines = []
    ok, summary = checks.run(ws, repo, log=lines.append, **kw)
    return ok, {c["id"]: c for c in summary["checks"]}, summary, lines


def test_missing_checks_yaml_fails(tmp_path):
    ws, repo = _repo(tmp_path, "")
    (repo.path / "checks.yaml").unlink()
    with pytest.raises(checkcfg.ConfigError, match="missing"):
        checks.run(ws, repo, log=lambda *_: None)


def test_empty_plan_fails(tmp_path):
    """--stage full with no section that runs at full plans nothing: that is an error, not a pass."""
    ws, repo = _repo(tmp_path, "version: 1\nexpect: [CK-H1, CK-H2, CK-H3, CK-H4, CK-H6, CK-H7]\n")
    with pytest.raises(checkcfg.ConfigError, match="no check runs"):
        checks.run(ws, repo, stage="baseline", only=["CK-XX"], log=lambda *_: None)


def test_expect_list(tmp_path):
    ws, repo = _repo(tmp_path, "version: 1\nexpect: [CK-H1, CK-H2, CK-H3, CK-A6, CK-ZZ]\n")
    ok, res, summary, lines = _run(ws, repo, only=["CK-H6"])
    f = "\n".join(res["CK-H6"]["findings"])
    assert not ok
    assert "CK-ZZ: expected, but no such check" in f
    assert "CK-A6: expected, but off: it needs a docs section" in f
    assert "CK-H4: runs, but is not in `expect:`" in f
    assert any(o["id"] == "CK-A6" for o in summary["off"])


def test_no_expect_list_fails_and_names_the_ids(tmp_path):
    ws, repo = _repo(tmp_path, "version: 1\n")
    ok, res, _, _ = _run(ws, repo, only=["CK-H6"])
    assert not ok and "add the IDs this repo runs: CK-H1, CK-H2" in res["CK-H6"]["findings"][0]


def test_off_checks_are_printed(tmp_path):
    ws, repo = _repo(tmp_path, "version: 1\nexpect: [CK-H1, CK-H2, CK-H3, CK-H4, CK-H6, CK-H7]\n")
    _, _, _, lines = _run(ws, repo)
    off = next(ln for ln in lines if "off for this repo" in ln)
    assert "CK-A6 (needs a docs section)" in off and "CK-B4 (needs model.variants: true)" in off


def test_skipped_error_check_fails_at_baseline(tmp_path):
    """A CAD command skipped with --no-cad is fine for a PR, never for a baseline."""
    y = ("version: 1\nexpect: [CK-H1, CK-H6, X1]\ncommands:\n  - {id: X1, name: x, run: [\"true\"], cad: true}\n")
    ws, repo = _repo(tmp_path, y)
    ok, res, _, _ = _run(ws, repo, stage="pr", no_cad=True, only=["X1"])
    assert ok and res["X1"]["status"] == "skip"
    ok, res, _, _ = _run(ws, repo, stage="baseline", no_cad=True, only=["X1"])
    assert not ok and res["X1"]["status"] == "fail" and "baseline" in res["X1"]["findings"][-1]


def test_hygiene_build_reports_git_failure(tmp_path):
    ws, repo = _repo(tmp_path, "version: 1\n")
    subprocess.run(["rm", "-rf", str(repo.path / ".git")], check=True)
    ok, res, _, _ = _run(ws, repo, only=["CK-H2"])
    assert not ok and "git ls-files failed" in res["CK-H2"]["findings"][0]


def _commit(repo, rel, text):
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", rel], check=True)


def test_pr_size_counts_hand_written_lines_only(tmp_path, monkeypatch):
    y = "version: 1\npr_size: {lines: 10, files: 3}\ncad: {needs: generated/cad-needs.json}\n"
    ws, repo = _repo(tmp_path, y)
    _commit(repo.path, "checks.yaml", y)
    subprocess.run(["git", "-C", str(repo.path), "branch", "base"], check=True)
    monkeypatch.setenv("XD_BASE_REF", "base")
    _commit(repo.path, "generated/cad-needs.json", "x\n" * 500)          # generated: not counted
    _commit(repo.path, "views/a.drawio.svg", "x\n" * 500)
    _commit(repo.path, "src/a.py", "x\n" * 5)
    ok, res, _, _ = _run(ws, repo, only=["CK-H7"])
    assert res["CK-H7"]["status"] == "pass"
    _commit(repo.path, "src/b.py", "x\n" * 20)
    ok, res, _, _ = _run(ws, repo, only=["CK-H7"])
    assert res["CK-H7"]["status"] == "warn" and "25 hand-written lines in 2 files" in res["CK-H7"]["findings"][0]
    assert ok                                                          # a warning never fails the run


def test_is_generated_uses_the_config(tmp_path):
    (tmp_path / "checks.yaml").write_text("cad: {needs: out/cad.json, freecad_json: out/fc}\n")
    cfg = checkcfg.load(tmp_path / "checks.yaml", tmp_path)
    assert checks.is_generated("out/cad.json", cfg) and checks.is_generated("out/fc/a.FCStd.json", cfg)
    assert checks.is_generated("model/generated/NeedStubs.sysml", cfg)
    assert not checks.is_generated("out/other.json", cfg) and not checks.is_generated("src/x.py", cfg)
