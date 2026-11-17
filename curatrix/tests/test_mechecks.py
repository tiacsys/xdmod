"""ME checks (task 5.25): CK-F4c recompute, CK-F16 solids, CK-F17 collisions, CK-F18 space budget,
accepted findings in assemblies/<name>/accepted.yaml (CK-F9, XD-ADR-0126)."""
import shutil
import subprocess

import pytest

from curatrix import checkcfg, checks, mechecks
from curatrix.ws import Repo, Workspace
from helpers import FIXTURES, git_init

AGENT = "\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n"
CFG = 'cad: {freecad: ["parts/*.FCStd", "assemblies/**/*.FCStd", "lib/**/*.FCStd"]}\n'


def _repo(tmp_path):
    root = tmp_path / "ws"
    repo = git_init(root / "r")
    (repo / "checks.yaml").write_text("version: 1\n" + CFG)
    (repo / "assemblies" / "fx").mkdir(parents=True)
    (repo / "assemblies" / "fx" / "README.md").write_text("fx\n")
    _commit(repo, "init")
    return root, repo


def _commit(repo, msg):
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", msg], check=True)


def _run(root, repo, fn, cid="X"):
    ctx = checks.Ctx(Workspace(root), Repo("r", repo, "r"), checkcfg.load(repo / "checks.yaml", root), "local",
                     False, None, root / "out")
    (root / "out").mkdir(exist_ok=True)
    r = checks.Result(cid, cid, level="warning")
    getattr(checks, fn)(ctx, r)
    return r


def _result(repo, overlaps, joined=(), kids=None, recompute=(), solids=()):
    doc = str(repo / "assemblies" / "fx" / "fx.FCStd")
    kids = kids or [{"name": n, "kind": "part", "configs": c, "id": "ME-PART-0001"}
                    for n, c in (("A", ""), ("B", ""), ("C", "SYS-CFG-0002"))]
    return {"ok": True, "recompute": list(recompute), "solids": list(solids), "parts": [],
            "assemblies": [{"doc": doc, "object": "Assembly", "id": "ME-ASM-0001", "children": kids,
                            "joined": [list(j) for j in joined], "overlaps": overlaps}]}


ACCEPT = """version: 1
accepted:
  - check: CK-F17
    rule: overlap
    items: [A, B]
    reason: the press fit of the canary insert (planted)
"""


def test_f17_collisions_and_acceptance(tmp_path, monkeypatch):
    """CK-F17 planted (plain Python on the FreeCAD result): an overlap above the tolerance is a
    finding per variant; a joined pair within its tolerance is not; a proposal from an agent commit
    still fails; a human commit with Accepted-by accepts it; an unused entry is reported."""
    root, repo = _repo(tmp_path)
    res = _result(repo, [{"a": "A", "b": "B", "volume": 500.0}, {"a": "B", "b": "C", "volume": 0.05},
                         {"a": "A", "b": "C", "volume": 0.0005}], joined=[("B", "C")])
    monkeypatch.setattr(mechecks, "run", lambda ws, cfg, out: res)
    f = _run(root, repo, "c_collisions").findings
    assert f == ["error: overlap (error): assemblies/fx/fx.FCStd (variant SYS-CFG-0002): A and B overlap by 500 mm³ "
                 "(tolerance 0.001 mm³) [A, B]"], f
    res["assemblies"][0]["overlaps"][1]["volume"] = 0.5            # joined, but beyond the joint tolerance
    f = _run(root, repo, "c_collisions").findings
    assert any("B and C overlap by 0.5 mm³ (tolerance 0.1 mm³, joined)" in x for x in f), f
    res["assemblies"][0]["overlaps"].pop(1)
    (repo / "assemblies" / "fx" / "accepted.yaml").write_text(ACCEPT)
    _commit(repo, "propose" + AGENT)
    f = _run(root, repo, "c_collisions").findings
    assert len(f) == 1 and "is a proposal, not accepted (commit" in f[0] and "agent commit" in f[0], f
    assert any("proposal, not accepted" in x for x in _run(root, repo, "c_acceptance").findings)
    (repo / "assemblies" / "fx" / "accepted.yaml").write_text(ACCEPT.replace("(planted)", "(planted), ok"))
    _commit(repo, "accept the press fit\n\nAccepted-by: Owner")
    assert _run(root, repo, "c_collisions").findings == []
    assert _run(root, repo, "c_acceptance").findings == []
    res["assemblies"][0]["overlaps"] = []
    f = _run(root, repo, "c_collisions").findings
    assert f == ["assemblies/fx/accepted.yaml entry 1 (CK-F17 overlap: A, B) matches no CK-F17 finding; remove it"], f


def test_f18_space_budget(tmp_path, monkeypatch):
    """CK-F18: without a board model a skip with its reason; planted: a board model is reported
    as not checked until the co-design task gives the budget its form."""
    root, repo = _repo(tmp_path)
    res = _result(repo, [])
    monkeypatch.setattr(mechecks, "run", lambda ws, cfg, out: res)
    r = _run(root, repo, "c_space_budget")
    assert r.status == "skip" and "no board model" in r.findings[0], r
    res["assemblies"][0]["children"].append({"name": "Board", "kind": "board", "configs": "", "id": "EE-PCBA-0001"})
    r = _run(root, repo, "c_space_budget")
    assert r.status != "skip" and r.findings == [
        "error: space-budget (error): assemblies/fx/fx.FCStd: board model Board (EE-PCBA-0001): its SYS-IF space "
        "budget is not checked yet; the budget's form comes from the co-design task 5.28 [Board]"], r.findings


def test_recompute_and_solids_shared_documents(tmp_path, monkeypatch):
    """CK-F4c / CK-F16 findings of a shared part (parts/) can be accepted in any assembly folder;
    the items are <document stem>#<object>."""
    root, repo = _repo(tmp_path)
    res = _result(repo, [], recompute=[{"doc": str(repo / "parts" / "broken.FCStd"), "object": "Fillet",
                                        "type": "Part::Fillet", "state": ["Invalid"]}],
                  solids=[{"doc": str(repo / "parts" / "sheet.FCStd"), "object": "Sheet", "id": "ME-PART-0004",
                           "problem": "no solid (shape type Face)"}])
    monkeypatch.setattr(mechecks, "run", lambda ws, cfg, out: res)
    assert _run(root, repo, "c_recompute").findings == [
        "error: recompute (error): parts/broken.FCStd: Fillet (Part::Fillet) does not recompute: Invalid [broken#Fillet]"]
    assert _run(root, repo, "c_solids").findings == [
        "error: solid (error): parts/sheet.FCStd: Sheet (ME-PART-0004): no solid (shape type Face) [sheet#Sheet]"]
    (repo / "assemblies" / "fx" / "accepted.yaml").write_text(
        "version: 1\naccepted:\n  - check: CK-F16\n    rule: solid\n    items: [sheet#Sheet]\n    reason: a sheet\n")
    _commit(repo, "accept\n\nAccepted-by: Owner")
    assert _run(root, repo, "c_solids").findings == []


# ------------------------------------------------------------------ with FreeCAD
def _fixture(tmp_path, repo, extra=None):
    from curatrix.newasm import run_script
    run_script(Workspace(tmp_path / "ws"), FIXTURES / "freecad" / "make_me_fixture.py",
               {"XD_DIR": str(repo), **(extra or {})}, tmp_path / "fixture.result.json")
    for bak in repo.rglob("*.FCBak"):
        bak.unlink()


@pytest.mark.tools
def test_me_checks_freecad(tmp_path):
    """CK-F4c, CK-F16, CK-F17 planted in a FreeCAD fixture (FreeCADCmd): a fillet that cannot be
    built, a face with an ME-PART TraceID, two overlaps (one only in variant SYS-CFG-0002); the
    joined pair touches, the library screw through both is left out; nothing is saved."""
    if shutil.which("FreeCADCmd") is None:
        pytest.skip("FreeCADCmd not installed")
    root, repo = _repo(tmp_path)
    _fixture(tmp_path, repo)
    _commit(repo, "fixture")
    mechecks._CACHE.clear()
    assert _run(root, repo, "c_recompute").findings == [
        "error: recompute (error): parts/broken.FCStd: Fillet (Part::Fillet) does not recompute: Touched, Invalid "
        "[broken#Fillet]"]
    assert _run(root, repo, "c_solids").findings == [
        "error: solid (error): parts/sheet.FCStd: Sheet (ME-PART-0004): no solid (shape type Face) [sheet#Sheet]"]
    f = _run(root, repo, "c_collisions").findings
    assert sorted(f) == [
        "error: overlap (error): assemblies/fx/fx.FCStd (variant SYS-CFG-0002): A and B overlap by 500 mm³ "
        "(tolerance 0.001 mm³) [A, B]",
        "error: overlap (error): assemblies/fx/fx.FCStd (variant SYS-CFG-0002): C and D overlap by 500 mm³ "
        "(tolerance 0.001 mm³) [C, D]"], f
    assert _run(root, repo, "c_space_budget").status == "skip"
    assert subprocess.run(["git", "-C", str(repo), "status", "--porcelain"], capture_output=True,
                          text=True).stdout == ""                     # the check saved nothing
