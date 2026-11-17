"""Table-driven tests for check functions that had none (task 5.4, P4-8): c_ears (CK-E2, CK-E3),
c_diff (CK-G1; CK-G2 is the same function), c_trailers (CK-H4), c_pins (CK-H3), c_hygiene_build (CK-H2)."""
import json
import subprocess

import pytest

from curatrix import checkcfg, checks, graph, needs as needsmod
from curatrix.ws import Repo, Workspace
from helpers import git_init


# ------------------------------------------------------------------ CK-E2
@pytest.mark.parametrize("sentence,fields,ok", [
    # the false errors of the Phase 4 review (P4-8)
    ("The joint shall move between 0.5 and 2.5 ms.", {"min": "0.5", "max": "2.5", "unit": "ms"}, True),
    ("The arm shall answer within 50 milliseconds.", {"max": "50", "unit": "ms"}, True),
    ("The arm shall carry a payload of 1,000 g.", {"max": "1000", "unit": "g"}, True),
    ("The bus shall run at least 2000000 Hz.", {"min": "2000000", "unit": "Hz"}, True),
    ("The bus shall run at least 2,000,000 Hz.", {"min": "2e6", "unit": "Hz"}, True),
    ("The joint shall reach 90° ± 2°.", {"nominal": "90", "max": "92", "min": "88", "unit": "°"}, True),
    ("The joint shall reach 90 degrees.", {"nominal": "90", "unit": "°"}, True),
    ("The motor shall turn at 12 000 rpm.", {"max": "12000", "unit": "rpm"}, True),
    ("When cold, the arm shall start at -10 °C.", {"min": "-10", "unit": "°C"}, True),
    # real errors
    ("The arm shall answer within 50 ms.", {"max": "40", "unit": "ms"}, False),
    ("The arm shall answer within 50 ms.", {"max": "50", "unit": "s"}, False),
    ("The arm shall answer quickly.", {"max": "50", "unit": "ms"}, False),
    ("The arm shall answer within 50 ms.", {"max": "fast"}, False),
    ("The arm shall answer within 150 ms.", {"max": "50", "unit": "ms"}, False),
    ("The arm shall answer within 1.5 ms.", {"max": "5", "unit": "ms"}, False),
    # forms an engineer writes (review of xdmod#31)
    ("The bus shall run at 10–20 Hz.", {"min": "10", "max": "20", "unit": "Hz"}, True),
    ("The bus shall run at 10 to 20 kHz.", {"min": "10", "max": "20", "unit": "kHz"}, True),
    ("The arm shall answer in ≤ 5 ms.", {"max": "5", "unit": "ms"}, True),
    ("The arm shall answer in 5 ms or less.", {"max": "5", "unit": "ms"}, True),
    ("The arm shall answer within 50ms.", {"max": "50", "unit": "ms"}, True),
    ("The board shall run from 12V.", {"nominal": "12", "unit": "V"}, True),
    ("The part shall be flat to ±0.5 mm.", {"min": "-0.5", "max": "0.5", "unit": "mm"}, True),
    ("The arm shall work at 20 °C ± 2 °C.", {"nominal": "20", "min": "18", "max": "22", "unit": "°C"}, True),
    ("The timer shall tick every 10 µs.", {"max": "10", "unit": "us"}, True),
    ("The timer shall tick every 10 \u03bcs.", {"max": "10", "unit": "µs"}, True),
    ("The arm shall answer within 5 milliseconds.", {"max": "5", "unit": "ms"}, True),
    # false passes the review found
    ("The arm shall stop in 5 ms, the tool in 3 s.", {"max": "3", "unit": "ms"}, False),
    ("A gripper shall close within 5 s.", {"max": "5", "unit": "A"}, False),
    ("The arm shall lift 5 kg in 2 m.", {"max": "5", "unit": "m"}, False),
    ("The arm shall weigh 5 ms.", {"max": "5", "unit": "m"}, False),
    ("Per SYS-REQ-0012 the arm shall answer in 3 ms.", {"max": "12", "unit": "ms"}, False),
    ("The arm shall answer in 15 ms or 5.5 ms.", {"max": "5", "unit": "ms"}, False),
])
def test_ck_e2(sentence, fields, ok):
    findings = checks.ears_value_findings("SYS-REQ-0001", fields, sentence)
    assert (findings == []) is ok, findings


def test_ck_e2_without_values_or_unit():
    assert checks.ears_value_findings("X", {}, "The arm shall be red.") == []
    assert checks.ears_value_findings("X", {"unit": "ms"}, "The arm shall be red.") == []   # no value: no unit check
    assert checks.ears_value_findings("X", {"max": "3"}, "It shall hold 3 poses.") == []


# ------------------------------------------------------------------ c_ears via the graph (E2 + E3)
def _ctx(tmp_path, needs, stage="local"):
    root = tmp_path / "ws"
    repo = git_init(root / "r")
    (repo / "checks.yaml").write_text("version: 1\n")
    ws = Workspace(root)
    ctx = checks.Ctx(ws, Repo("r", repo, "r"), checkcfg.load(repo / "checks.yaml", root), stage, False, None,
                     tmp_path / "out")
    (tmp_path / "out").mkdir()
    ctx.graph, ctx.graph_findings = graph.Graph({n["id"]: n for n in needs}), []
    return ctx


@pytest.mark.parametrize("ears,content,finding", [
    ("event", "When the pose is stored, the arm shall beep.", None),
    ("event", "The arm shall beep.", "does not start like that pattern"),
    ("state", "While powered, the arm shall hold.", None),
    ("unwanted", "If a joint stalls, the arm shall stop.", None),
    ("ubiquitous", "The arm will beep.", "no 'shall'"),
    ("optional", "Where a camera is fitted, the arm shall track.", None),
])
def test_ck_e3(tmp_path, ears, content, finding):
    ctx = _ctx(tmp_path, [{"id": "SYS-REQ-0001", "type": "sys-req", "status": "valid", "ears": ears, "content": content}])
    r = checks.Result("CK-E3", "ears", level="warning")
    checks.c_ears(ctx, r)
    assert (r.findings == []) if finding is None else (finding in "\n".join(r.findings))


def test_c_ears_skips_external_retired_and_non_requirements(tmp_path):
    bad = {"max": "1", "unit": "ms", "content": "no number"}
    ctx = _ctx(tmp_path, [
        {"id": "SYS-REQ-0001", "type": "sys-req", "status": "retired", **bad},
        {"id": "SYS-REQ-0002", "type": "sys-req", "status": "valid", "is_external": True, **bad},
        {"id": "SYS-EL-0001", "type": "sys-el", "status": "valid", **bad},
        {"id": "SW-REQ-0001", "type": "sw-req", "status": "valid", **bad}])
    r = checks.Result("CK-E2", "values", level="warning")
    checks.c_ears(ctx, r)
    assert [f.split(":")[0] for f in r.findings] == ["SW-REQ-0001"]


# ------------------------------------------------------------------ CK-G1 / CK-G2
def _needs_file(path, needs):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(needsmod.doc({n["id"]: n for n in needs}, "x")))
    return path


def test_c_diff_skips_without_base_and_reports_changes(tmp_path, monkeypatch):
    req = {"id": "SYS-REQ-0001", "type": "sys-req", "status": "valid", "title": "t", "content": "50 ms"}
    sw = {"id": "SW-REQ-0001", "type": "sw-req", "status": "valid", "title": "s", "content": "x", "refines": ["SYS-REQ-0001"]}
    ctx = _ctx(tmp_path, [req, sw], stage="pr")
    r = checks.Result("CK-G1", "diff", level="report")
    checks.c_diff(ctx, r)
    assert r.status == "skip"
    base = tmp_path / "base"
    _needs_file(base / "needs.json", [req, sw])
    new = _needs_file(tmp_path / "new" / "needs.json", [{**req, "content": "40 ms"}, sw])
    monkeypatch.setattr(checks.gen, "docs_needs_json", lambda ws, cfg: [new])
    ctx.base = base
    r = checks.Result("CK-G1", "diff", level="report")
    checks.c_diff(ctx, r)
    assert r.findings and "suspect" in r.findings[0]
    assert "SW-REQ-0001" in (ctx.out / "needs-diff.md").read_text()


# ------------------------------------------------------------------ CK-H4, CK-H3, CK-H2
def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


def test_c_trailers(tmp_path, monkeypatch):
    """CK-H4 asks agent commits (they name Claude) for the trailer; human commits pass."""
    ctx = _ctx(tmp_path, [])
    repo = ctx.repo.path
    monkeypatch.setenv("XD_BASE_REF", "nope")
    r = checks.Result("CK-H4", "trailers", level="warning")
    checks.c_trailers(ctx, r)
    assert r.status == "skip"                                   # no base
    _git(repo, "commit", "-q", "--allow-empty", "-m", "init")
    _git(repo, "branch", "base")
    monkeypatch.setenv("XD_BASE_REF", "base")
    _git(repo, "commit", "-q", "--allow-empty", "-m", "agent\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>")
    _git(repo, "commit", "-q", "--allow-empty", "-m", "a human commit that asks Claude for help")
    _git(repo, "commit", "-q", "--allow-empty", "-m", "agent\n\nCo-authored-by: Claude <noreply@anthropic.com>")
    _git(repo, "commit", "-q", "--allow-empty", "-m", "agent\n\nGenerated with [Claude Code], trailer forgotten")
    r = checks.Result("CK-H4", "trailers", level="warning")
    checks.c_trailers(ctx, r)
    assert len(r.findings) == 1 and "agent commit without the trailer" in r.findings[0]


def _has(repo, ref):
    return subprocess.run(["git", "-C", str(repo), "rev-parse", "-q", "--verify", ref], capture_output=True).returncode == 0


@pytest.mark.parametrize("req,tools,n", [
    ("pyyaml==6.0.3\n# comment\n-r other.txt\nfoo @ git+https://x\n", None, 0),
    ("pyyaml>=6\nsphinx\n", None, 2),
    ("", "tools: []\n", 0),
    ("", "tools: 3\n", 1),
])
def test_c_pins(tmp_path, req, tools, n):
    ctx = _ctx(tmp_path, [])
    (ctx.repo.path / "requirements.txt").write_text(req)
    if tools is not None:
        (ctx.repo.path / "tools.yaml").write_text(tools)
    r = checks.Result("CK-H3", "pins", level="warning")
    checks.c_pins(ctx, r)
    assert len(r.findings) == n, r.findings


@pytest.mark.parametrize("path,flagged", [
    ("build/out.txt", True), ("docs/_build/index.html", True), ("src/__pycache__/a.pyc", True),
    ("deploy/html/index.html", True), ("src/a.py", False), ("docs/building.rst", False),
])
def test_c_hygiene_build(tmp_path, path, flagged):
    ctx = _ctx(tmp_path, [])
    f = ctx.repo.path / path
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("x")
    r = checks.Result("CK-H2", "build", level="error")
    checks.c_hygiene_build(ctx, r)
    assert bool(r.findings) is flagged, r.findings
