"""ME checks (task 5.25): CK-F4c recompute, CK-F16 solids, CK-F17 collisions, CK-F18 space budget,
accepted findings in assemblies/<name>/accepted.yaml (CK-F9, XD-ADR-0126)."""
import json
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
    assert f == ["error: overlap (error): assemblies/fx/fx.FCStd: A and B overlap by 500 mm³ (tolerance 0.001 mm³) "
                 "[A, B]"], f                                # in every variant: one finding, no variant label
    res["assemblies"][0]["overlaps"][1]["volume"] = 0.5            # joined, but beyond the joint tolerance
    f = _run(root, repo, "c_collisions").findings
    assert any("(variant SYS-CFG-0002): B and C overlap by 0.5 mm³ (tolerance 0.1 mm³, joined)" in x for x in f), f
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


SEAT = {"ME-PORT-0009": {"budget": "SYS-IF-0001", "missing": [],
                         "values": {"width": 20.0, "depth": 10.0, "heightAbove": 10.0, "heightBelow": 3.0}}}


def test_f18_space_budget(tmp_path, monkeypatch):
    """CK-F18 planted (plain Python on the FreeCAD result): a skip without a board; a board out of
    its box (beyond the tolerance only), a part in the box, a fastener through the board and a board
    at no seat are findings; a part in the box can be accepted (rule space)."""
    root, repo = _repo(tmp_path)
    res = _result(repo, [])
    monkeypatch.setattr(mechecks, "run", lambda ws, cfg, out: res)
    r = _run(root, repo, "c_space_budget")
    assert r.status == "skip" and "no board model" in r.findings[0], r
    res["assemblies"][0]["children"].append({"name": "Board", "kind": "board", "configs": "", "id": "EE-PCBA-0001"})
    res["seats"] = SEAT
    res["assemblies"][0]["budgets"] = [
        {"board": "Board", "seat": "LCS_seat", "port": "ME-PORT-0009", "placement": [0, 40, 20],
         "bbox": [0.0, -0.005, -3.005, 20.0, 10.0, 12.0],
         "intrusions": [{"name": "A", "volume": 100.0, "z": [-3.0, -2.0]}, {"name": "B", "volume": 0.0005, "z": [0, 0]}],
         "fasteners": [{"name": "ScrewBad", "volume": 11.3097}]},
        {"board": "Board2", "seat": "", "port": "", "placement": [0, 70, 20], "intrusions": [], "fasteners": []}]
    f = _run(root, repo, "c_space_budget").findings
    assert f == [
        "error: space (error): assemblies/fx/fx.FCStd: Board and the fastener ScrewBad overlap by 11.31 mm³ (tolerance "
        "0.001 mm³): the fastener misses the board's hole [ScrewBad]",
        "error: space (error): assemblies/fx/fx.FCStd: Board reaches 2 mm above heightAbove of the space budget "
        "SYS-IF-0001 at LCS_seat (ME-PORT-0009; board z 12.000 mm, budget 10 mm, tolerance 0.01 mm) [Board]",
        "error: space (error): assemblies/fx/fx.FCStd: A reaches into the space budget SYS-IF-0001 of Board at LCS_seat "
        "(ME-PORT-0009) by 100 mm³, z -3 to -2 mm in the board frame (tolerance 0.001 mm³) [A]",
        "error: space (error): assemblies/fx/fx.FCStd: Board2 is not placed at a board seat (an LCS with Port = an "
        "ME-PORT that specializes a SYS-IF budget: ME-PORT-0009); the link sits at [0, 70, 20] [Board2]"], f
    rows = mechecks.evaluate(checkcfg.load(repo / "checks.yaml", root), "CK-F18",
                             mechecks.findings(checkcfg.load(repo / "checks.yaml", root), res, "CK-F18"), {}).rows
    assert len(rows) == 4 and rows[2]["items"] == "A", rows            # the assembly document's table
    (repo / "assemblies" / "fx" / "accepted.yaml").write_text(
        "version: 1\naccepted:\n  - check: CK-F18\n    rule: space\n    items: [A]\n"
        "    reason: the stand-off under the board (planted)\n")
    _commit(repo, "accept the stand-off\n\nAccepted-by: Owner")
    f = _run(root, repo, "c_space_budget").findings
    assert len(f) == 3 and not any("A reaches" in x for x in f), f
    res["seats"] = {"ME-PORT-0009": {"budget": "SYS-IF-0001", "missing": ["heightBelow"], "values": {}}}
    f = _run(root, repo, "c_space_budget").findings
    assert any("the budget SYS-IF-0001 has no value for heightBelow" in x for x in f), f


def test_f18_seats_from_the_model(tmp_path):
    """The seats: ME port defs that specialize a SYS-IF budget of the upstream model; the budget's
    defaults, overridden by the values the seat restates; a missing value is named."""
    from test_meparams import M
    root, repo = _repo(tmp_path)
    up = M()
    sp = up.el("Sys::BoardSpace", {"@type": "PortDefinition", "name": "BoardSpace", "qualifiedName": "Sys::BoardSpace",
                                   "declaredShortName": "SYS-IF-0001"})
    for n, v in (("width", 30), ("depth", 20), ("heightAbove", 10)):
        up.attr(sp, n, v, "millimetre")
    me = M()
    me.el("lib:Sys::BoardSpace", {"@type": "PortDefinition", "name": "BoardSpace", "qualifiedName": "Sys::BoardSpace",
                                  "declaredShortName": "SYS-IF-0001", "isLibraryElement": True})
    seat = me.el("Me::BoardSeat", {"@type": "PortDefinition", "name": "BoardSeat", "qualifiedName": "Me::BoardSeat",
                                   "declaredShortName": "ME-PORT-0002"})
    sub = me.el("Me::BoardSeat/sub", {"@type": "Subclassification", "superclassifier": {"@id": "lib:Sys::BoardSpace"}})
    seat["ownedRelationship"].append({"@id": sub["@id"]})
    me.attr(seat, "width", 25, "millimetre")
    me.el("Me::Other", {"@type": "PortDefinition", "name": "Other", "qualifiedName": "Me::Other",
                        "declaredShortName": "ME-PORT-0001"})
    (repo / "generated").mkdir()
    (repo / "generated" / "model.json").write_text(json.dumps(me.data))
    (repo / "up.json").write_text(json.dumps(up.data))
    (repo / "checks.yaml").write_text("version: 1\n" + CFG + "model: {files: [model/*.sysml], upstream: up.json}\n")
    cfg = checkcfg.load(repo / "checks.yaml", root)
    assert mechecks.seats(cfg) == {"ME-PORT-0002": {"budget": "SYS-IF-0001", "missing": ["heightBelow"],
                                                    "values": {"width": 25.0, "depth": 20.0, "heightAbove": 10.0}}}


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
    built, a face with an ME-PART TraceID, three overlaps (A-B in every variant, the joined pair
    B-C beyond the joint tolerance, C-D only in variant SYS-CFG-0002); E touches two parts without
    a joint, the library screw through A and B is left out; nothing is saved."""
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
        "error: overlap (error): assemblies/fx/fx.FCStd (variant SYS-CFG-0002): C and D overlap by 400 mm³ "
        "(tolerance 0.001 mm³) [C, D]",
        "error: overlap (error): assemblies/fx/fx.FCStd: A and B overlap by 500 mm³ (tolerance 0.001 mm³) [A, B]",
        "error: overlap (error): assemblies/fx/fx.FCStd: B and C overlap by 100 mm³ (tolerance 0.1 mm³, joined) "
        "[B, C]"], f                         # E touches A and B without a joint: no finding
    assert _run(root, repo, "c_space_budget").status == "skip"
    assert subprocess.run(["git", "-C", str(repo), "status", "--porcelain"], capture_output=True,
                          text=True).stdout == ""                     # the check saved nothing


@pytest.mark.tools
def test_f18_space_budget_freecad(tmp_path, monkeypatch):
    """CK-F18 planted in the FreeCAD fixture (XD_BOARD=1): a board 2 mm above heightAbove, a part
    1 mm into the box below the board, a screw through the board body (the one through the hole
    passes), a second board at no seat."""
    if shutil.which("FreeCADCmd") is None:
        pytest.skip("FreeCADCmd not installed")
    root, repo = _repo(tmp_path)
    _fixture(tmp_path, repo, {"XD_BOARD": "1"})
    _commit(repo, "fixture")
    mechecks._CACHE.clear()
    monkeypatch.setattr(mechecks, "seats", lambda cfg: SEAT)
    f = _run(root, repo, "c_space_budget").findings
    assert f == [
        "error: space (error): assemblies/fx/fx.FCStd: Board and the fastener ScrewBad overlap by 11.31 mm³ (tolerance "
        "0.001 mm³): the fastener misses the board's hole [ScrewBad]",
        "error: space (error): assemblies/fx/fx.FCStd: Board reaches 2 mm above heightAbove of the space budget "
        "SYS-IF-0001 at LCS_seat (ME-PORT-0009; board z 12.000 mm, budget 10 mm, tolerance 0.01 mm) [Board]",
        "error: space (error): assemblies/fx/fx.FCStd: F reaches into the space budget SYS-IF-0001 of Board at LCS_seat "
        "(ME-PORT-0009) by 100 mm³, z -3 to -2 mm in the board frame (tolerance 0.001 mm³) [F]",
        "error: space (error): assemblies/fx/fx.FCStd: Board2 is not placed at a board seat (an LCS with Port = an "
        "ME-PORT that specializes a SYS-IF budget: ME-PORT-0009); the link sits at [0.0, 70.0, 20.0] [Board2]"], f
