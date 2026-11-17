"""ERC and DRC (task 5.19): CK-F4a, CK-F4b with KiCad; CK-F8 severities and CK-F9 acceptance in
plain Python (XD-ADR-0126, XD-ADR-0144)."""
import json
import shutil
import subprocess

import pytest

from curatrix import checkcfg, checks, ercdrc
from curatrix.ws import Repo, Workspace
from helpers import FIXTURES, git_init

DRC = FIXTURES / "kicad" / "drc"
TEMPLATE = FIXTURES.parents[2] / "templates" / "kicad-pcba" / "pcba.kicad_pro"
YAML = 'version: 1\ncad: {projects: ["pcba/*/*.kicad_pro"]}\n'
AGENT = "\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n"
UNROUTED = ("version: 1\naccepted:\n  - check: CK-F4b\n    rule: unconnected_items\n    items: all\n"
            "    reason: routing is not done in iteration 1 (XD-ADR-0144)\n")


def _repo(tmp_path, files=("drc.kicad_pro", "drc.kicad_sch", "drc.kicad_pcb")):
    root = tmp_path / "ws"
    repo = git_init(root / "r")
    (repo / "checks.yaml").write_text(YAML)
    d = repo / "pcba" / "drc"
    d.mkdir(parents=True)
    for f in files:
        shutil.copy(DRC / f, d / f)
    _commit(repo, "the board")
    return root, repo


def _commit(repo, msg, *paths):
    subprocess.run(["git", "-C", str(repo), "add", *(paths or ["-A"])], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", msg], check=True)


def _run(root, repo, cid, fn, stage="local"):
    ctx = checks.Ctx(Workspace(root), Repo("r", repo, "r"), checkcfg.load(repo / "checks.yaml", root), stage,
                     False, None, root / "out")
    (root / "out").mkdir(exist_ok=True)
    r = checks.Result(cid, cid, level="warning")
    getattr(checks, fn)(ctx, r)
    return r.findings


# ------------------------------------------------------------------ plain Python
def test_report_reader_and_designators(tmp_path):
    rep = tmp_path / "drc.json"
    rep.write_text(json.dumps({
        "violations": [{"type": "clearance", "severity": "error", "description": "Clearance violation",
                        "items": [{"description": "Pad 1 [/A] of R1 on F.Cu", "uuid": "u1"},
                                  {"description": "Track [/B] on F.Cu, length 2 mm", "uuid": "u2"}]}],
        "unconnected_items": [{"type": "unconnected_items", "severity": "error", "description": "Missing connection",
                               "excluded": True, "comment": "later",
                               "items": [{"description": "PTH pad 1 [/A] of J1", "uuid": "u3"},
                                         {"description": "Pad 1 [/A] of R1 on F.Cu", "uuid": "u4"}]}],
        "schematic_parity": [{"type": "footprint_symbol_field_mismatch", "severity": "warning",
                              "description": "x", "items": [{"description": "Footprint JP12", "uuid": "u5"}]}]}))
    f = ercdrc.read_report(rep, "CK-F4b")
    assert [x.refs for x in f] == [["R1"], ["J1", "R1"], ["JP12"]]
    assert (f[1].excluded, f[1].comment, f[1].uuids) == (True, "later", ["u3", "u4"])
    erc = tmp_path / "erc.json"
    erc.write_text(json.dumps({"sheets": [{"path": "/", "violations": [
        {"type": "pin_not_connected", "severity": "error", "description": "Pin not connected",
         "items": [{"description": "Symbol R1 Pin 2 [Passive, Line]", "uuid": "u6"}]}]}]}))
    assert ercdrc.read_report(erc, "CK-F4a")[0].refs == ["R1"]


def _f(rule="unconnected_items", sev="error", refs=("J1", "R1"), uuids=("a", "b"), excluded=False, check="CK-F4b"):
    return ercdrc.Finding(check, rule, sev, "d", [f"Pad 1 of {r}" for r in refs], list(uuids), excluded)


def test_evaluate_entries_exclusions_phantoms():
    acc = ercdrc.Entry(1, "CK-F4b", "unconnected_items", "all", "r", (3, 6), "accepted", "Accepted-by: O in abc")
    o = ercdrc.evaluate([_f(), _f(uuids=("c", "d")), _f(sev="warning", rule="silk_overlap")], [acc], {})
    assert o.problems == [] and acc.hits == 2 and len(o.listed) == 3
    prop = ercdrc.Entry(1, "CK-F4b", "clearance", ["R1"], "r", (3, 6), "proposed", "commit x is an agent commit")
    o = ercdrc.evaluate([_f("clearance", refs=("R1",)), _f("clearance", refs=("R1", "R2"))], [prop], {})
    assert any("entry 1 (CK-F4b clearance: R1) is a proposal" in p and "covers 1 error" in p for p in o.problems)
    assert any(p.startswith("error: clearance") and "R1, R2" in p for p in o.problems)
    # KiCad exclusions: accepted, a proposal, a stale one of a rule switched off, an ERC phantom
    excl = {"unconnected_items|1|2|F.Cu|4|a|b": (True, "Accepted-by: O in abc"),
            "unconnected_items|1|2|F.Cu|4|c|d": (False, "commit def has no `Accepted-by:` trailer")}
    o = ercdrc.evaluate([_f(excluded=True), _f(uuids=("c", "d"), excluded=True)], [], excl)
    assert len(o.problems) == 1 and "exclusion is a proposal (commit def has no" in o.problems[0]
    o = ercdrc.evaluate([_f("label_dangling", sev="", excluded=True, check="CK-F4a")], [], {})
    assert "stale KiCad exclusion" in o.problems[0]
    phantom = [_f("label_dangling", excluded=True, check="CK-F4a"), _f("label_dangling", check="CK-F4a")]
    o = ercdrc.evaluate(phantom, [], {})
    assert len(o.problems) == 1 and o.problems[0].startswith("error: label_dangling")


def test_f9_acceptance(tmp_path):
    """CK-F9 planted: a malformed entry, an entry from an agent commit, from a human commit without
    `Accepted-by:`, from an acceptance commit that changes another file, an uncommitted one: all
    proposals; only a human commit with `Accepted-by:` and nothing else accepts."""
    root, repo = _repo(tmp_path)
    acc = repo / "pcba" / "drc" / "accepted.yaml"
    acc.write_text(UNROUTED)
    assert any("entry 1 (CK-F4b unconnected_items: all): proposal, not accepted (not committed)" in x
               for x in _run(root, repo, "CK-F9", "c_acceptance"))
    _commit(repo, "propose the unrouted nets" + AGENT)
    assert any("is an agent commit" in x for x in _run(root, repo, "CK-F9", "c_acceptance"))
    acc.write_text(UNROUTED.replace("iteration 1", "iteration one"))
    _commit(repo, "reword")
    assert any("has no `Accepted-by:` trailer" in x for x in _run(root, repo, "CK-F9", "c_acceptance"))
    acc.write_text(UNROUTED)
    (repo / "README.md").write_text("x\n")
    _commit(repo, "accept\n\nAccepted-by: Owner")
    assert any("also changes README.md" in x for x in _run(root, repo, "CK-F9", "c_acceptance"))
    acc.write_text(UNROUTED.replace("iteration 1", "iteration 1 (owner)"))
    _commit(repo, "accept\n\nAccepted-by: Owner")
    assert _run(root, repo, "CK-F9", "c_acceptance") == []
    acc.write_text(UNROUTED + "  - check: CK-F4b\n    rule: clearance\n    items: [{x: 1, y: 2}]\n")
    f = _run(root, repo, "CK-F9", "c_acceptance")
    assert any("entry 2: items must be `all` or a list of designators" in x and "reason is missing" in x for x in f), f


def test_f9_kicad_exclusion_commit(tmp_path):
    """A KiCad exclusion counts only from an acceptance commit that changes nothing but exclusions."""
    root, repo = _repo(tmp_path)
    pro = repo / "pcba" / "drc" / "drc.kicad_pro"
    d = json.loads(pro.read_text())
    d["board"]["design_settings"]["drc_exclusions"] = [["unconnected_items|1|2|F.Cu|4|a|b", "later"]]
    pro.write_text(json.dumps(d, indent=2) + "\n")
    _commit(repo, "exclude" + AGENT)
    assert any("DRC exclusion unconnected_items (later): proposal" in x and "agent commit" in x
               for x in _run(root, repo, "CK-F9", "c_acceptance"))
    d["board"]["design_settings"]["drc_exclusions"] = [["unconnected_items|1|2|F.Cu|4|a|b", "later"],
                                                       ["clearance|5|6|c|d", "ok"]]
    d["text_variables"]["XD_VERSION"] = "v1"
    pro.write_text(json.dumps(d, indent=2) + "\n")
    _commit(repo, "accept\n\nAccepted-by: Owner")
    assert any("beyond its ERC/DRC exclusions" in x for x in _run(root, repo, "CK-F9", "c_acceptance"))
    d["text_variables"]["XD_VERSION"] = "unversioned"
    pro.write_text(json.dumps(d, indent=2) + "\n")
    _commit(repo, "back")
    d["board"]["design_settings"]["drc_exclusions"].append(["clearance|7|8|e|f", "fine"])
    pro.write_text(json.dumps(d, indent=2) + "\n")
    _commit(repo, "accept\n\nAccepted-by: Owner")
    f = _run(root, repo, "CK-F9", "c_acceptance")
    assert not any("clearance|7" in x or "(fine)" in x for x in f), f


def test_f8_severities(tmp_path):
    """CK-F8 planted: a rule switched to `ignore` in the .kicad_pro and a custom rule lowered to a
    warning; an accepted entry clears one; a project without an `erc` section counts as the template."""
    root, repo = _repo(tmp_path)
    assert _run(root, repo, "CK-F8", "c_severities") == []
    pro = repo / "pcba" / "drc" / "drc.kicad_pro"
    d = json.loads(pro.read_text())
    d["board"]["design_settings"]["rule_severities"]["unconnected_items"] = "ignore"
    del d["erc"]
    pro.write_text(json.dumps(d, indent=2) + "\n")
    (pro.with_suffix(".kicad_dru")).write_text('(version 1)\n(rule "near"\n\t(constraint clearance (min 0.1mm))'
                                               '\n\t(severity warning))\n')
    f = _run(root, repo, "CK-F8", "c_severities")
    assert any("DRC rule unconnected_items: 'ignore', the template has 'error'" in x for x in f), f
    assert any("custom rule 'near' in drc.kicad_dru: severity warning" in x for x in f), f
    assert not any("ERC rule" in x for x in f)
    _commit(repo, "lower")
    (pro.parent / "accepted.yaml").write_text("version: 1\naccepted:\n  - check: CK-F8\n    rule: dru:near\n"
                                              "    items: all\n    reason: a test\n")
    _commit(repo, "accept\n\nAccepted-by: Owner")
    f = _run(root, repo, "CK-F8", "c_severities")
    assert len(f) == 1 and "unconnected_items" in f[0], f


def test_template_severities_are_complete():
    """The template holds every ERC and DRC severity (CK-F8 compares against it)."""
    erc, drc = ercdrc.severities(TEMPLATE)
    assert len(erc) > 40 and len(drc) > 50 and drc["unconnected_items"] == "error"


# ------------------------------------------------------------------ with KiCad
def _kicad():
    if shutil.which("kicad-cli") is None:
        pytest.skip("kicad-cli not installed")


@pytest.mark.tools
def test_f4b_unrouted_board(tmp_path):
    """CK-F4b planted: a placed, unrouted board reports one unconnected_items error per missing
    connection (2); one proposed entry covers both and is still reported; accepted by a human
    commit with `Accepted-by:`, the check passes."""
    _kicad()
    root, repo = _repo(tmp_path)
    f = _run(root, repo, "CK-F4b", "c_drc")
    assert len([x for x in f if "error: unconnected_items" in x]) == 2, f
    (repo / "pcba" / "drc" / "accepted.yaml").write_text(UNROUTED)
    _commit(repo, "propose" + AGENT)
    f = _run(root, repo, "CK-F4b", "c_drc")
    assert len(f) == 1 and "is a proposal, not accepted (commit" in f[0] and "covers 2 errors" in f[0], f
    _commit_accept(repo)
    assert _run(root, repo, "CK-F4b", "c_drc") == []
    rep = (root / "out" / "erc-drc" / "drc.txt").read_text()
    assert rep.count("accepted (accepted.yaml entry 1") == 2


def _commit_accept(repo):
    acc = repo / "pcba" / "drc" / "accepted.yaml"
    acc.write_text(UNROUTED.replace("(XD-ADR-0144)", "(XD-ADR-0144), accepted"))
    _commit(repo, "accept the unrouted nets\n\nAccepted-by: Owner")


LABEL = ('\t(label "DANGLING"\n\t\t(at 50.8 50.8 0)\n\t\t(effects\n\t\t\t(font\n\t\t\t\t(size 1.27 1.27)\n'
         '\t\t\t)\n\t\t\t(justify left bottom)\n\t\t)\n\t\t(uuid "0e0e0e0e-0000-4000-8000-000000000001")\n\t)\n')


@pytest.mark.tools
def test_f4a_erc(tmp_path):
    """CK-F4a planted: the clean fixture passes; a dangling label is an error."""
    _kicad()
    root, repo = _repo(tmp_path)
    assert _run(root, repo, "CK-F4a", "c_erc") == []
    sch = repo / "pcba" / "drc" / "drc.kicad_sch"
    text = sch.read_text()
    pos = text.index("\t(symbol\n\t\t(lib_id")
    sch.write_text(text[:pos] + LABEL + text[pos:])
    f = _run(root, repo, "CK-F4a", "c_erc")
    assert any("error: label_dangling" in x for x in f), f
