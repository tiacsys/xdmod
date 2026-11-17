"""The minimal trace report (task 5.10): rows per SYS-REQ, gaps, the canary in its own section."""
import json

from curatrix import cli, graph, needs as needsmod, trace


def N(nid, typ, **kw):
    return {"id": nid, "type": typ, "title": nid.lower(), "status": "valid", **kw}


NEEDS = [
    N("SYS-CFG-0001", "sys-cfg", title="canary", configures=["SYS-EL-0001"]),
    N("SYS-REQ-0001", "sys-req", configs=["SYS-CFG-0001"]),
    N("SW-REQ-0001", "sw-req", refines=["SYS-REQ-0001"]),
    N("SW-TC-0001", "sw-tc", verifies=["SW-REQ-0001"]),
    N("TR-SW-TC-0001-0000aaaa", "tr", result_of=["SW-TC-0001"], verdict="failed", content="Run ``20261101T000000Z-1``", tags=[]),
    N("TR-SW-TC-0001-0000bbbb", "tr", result_of=["SW-TC-0001"], verdict="passed", content="Run ``20261115T000000Z-2``", tags=[]),
    N("TR-SW-TC-0001-0000cccc", "tr", result_of=["SW-TC-0001"], verdict="failed", content="Local", tags=["preview"]),
    N("SYS-REQ-0002", "sys-req"),
    N("SYS-EL-0002", "sys-el", satisfies=["SYS-REQ-0002"]),
    N("SYS-REQ-0003", "sys-req"),
    N("SYS-REQ-0004", "sys-req", status="retired"),
]


def _graph():
    return graph.Graph({n["id"]: n for n in NEEDS})


def test_rows_and_gaps():
    rows = {r["id"]: r for r in trace.rows(_graph())}
    assert "SYS-REQ-0004" not in rows                                   # retired: no row
    r1 = rows["SYS-REQ-0001"]
    assert r1["refined_by"] == ["SW-REQ-0001"] and r1["verified_by"] == ["SW-TC-0001"]   # through the refinement
    assert r1["results"]["SW-TC-0001"]["id"] == "TR-SW-TC-0001-0000bbbb"      # newest evidence beats the preview
    assert r1["gaps"] == []
    assert rows["SYS-REQ-0002"]["satisfied_by"] == ["SYS-EL-0002"] and rows["SYS-REQ-0002"]["gaps"] == ["no test case"]
    assert rows["SYS-REQ-0003"]["gaps"] == ["not refined or satisfied", "no test case"]


def test_canary_has_its_own_section_and_is_not_counted():
    md, page, s = trace.report(_graph(), "t")
    assert s["canary_configs"] == ["SYS-CFG-0001"] and s["canary"] == ["SYS-REQ-0001"]
    assert s["coverage"] == {"requirements": 2, "refined_or_satisfied": 1, "with_test_case": 0, "passed": 0}
    main, canary = md.split("## Configuration canary")
    assert "SYS-REQ-0001" not in main and "SYS-REQ-0001" in canary and "SYS-REQ-0003" in main
    assert "<table>" in page


def test_cli_from_a_docs_build(tmp_path, monkeypatch):
    from helpers import git_init, make_ws
    root = make_ws(tmp_path, monkeypatch)
    repo = git_init(root / "r")
    (repo / "checks.yaml").write_text("version: 1\n")
    nj = root / "build" / "r" / "docs" / "deploy" / "html" / "se-req" / "needs.json"
    assert cli.main(["trace", "r"]) == 1                                 # no docs build yet
    nj.parent.mkdir(parents=True)
    nj.write_text(json.dumps(needsmod.doc({n["id"]: n for n in NEEDS}, "x")))
    monkeypatch.chdir(root)
    assert cli.main(["trace", "r"]) == 0
    out = root / "build" / "r" / "trace"
    assert (out / "trace.md").exists() and (out / "trace.html").exists()
    assert json.loads((out / "trace.json").read_text())["canary"] == ["SYS-REQ-0001"]
