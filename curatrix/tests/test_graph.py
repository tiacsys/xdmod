from curatrix import graph


def g(*ns):
    return graph.Graph({n["id"]: n for n in ns})


def rules(fs):
    return sorted({f.rule for f in fs})


BASE = [
    {"id": "SYS-NEED-0001", "type": "sys-need", "status": "valid"},
    {"id": "SYS-REQ-0001", "type": "sys-req", "status": "valid", "refines": ["SYS-NEED-0001"]},
    {"id": "SYS-EL-0001", "type": "sys-el", "status": "valid", "layer": "logical", "satisfies": ["SYS-REQ-0001"]},
    {"id": "INT-STC-0001", "type": "int-stc", "status": "valid", "verifies": ["SYS-REQ-0001"]},
]


def test_clean_graph():
    assert graph.check(g(*BASE), "full") == []


def test_r1_r2_and_draft_does_not_count():
    ns = [dict(n) for n in BASE]
    ns[2]["status"] = "draft"
    ns[3]["status"] = "draft"
    fs = graph.check(g(*ns), "full")
    assert rules(fs) == ["CK-B1", "CK-B2"]
    assert {f.level for f in fs if f.rule == "CK-B2"} == {"warning"}


def test_r3_orphans_and_r4_grace():
    ns = [*BASE,
          {"id": "EE-CMP-0001", "type": "ee-cmp", "status": "valid"},
          {"id": "SYS-REQ-0002", "type": "sys-req", "status": "retired"},
          {"id": "SYS-EL-0002", "type": "sys-el", "status": "valid", "layer": "product", "satisfies": ["SYS-REQ-0002"]}]
    fs = graph.check(g(*ns), "pr")
    assert rules(fs) == ["CK-A4", "CK-B3"]
    assert [f.level for f in fs if f.rule == "CK-B3"] == ["warning"]
    assert [f.level for f in graph.check(g(*ns), "baseline") if f.rule == "CK-B3"] == ["error"]


def test_unknown_links_ids_and_hil():
    ns = [*BASE,
          {"id": "SW-REQ-0001", "type": "sw-req", "status": "valid", "refines": ["SYS-REQ-0099"]},
          {"id": "SW-REQ-0002", "type": "ee-req", "status": "valid", "derived": True},
          {"id": "TR-INT-STC-0001-3f9a1c2e", "type": "tr", "status": "valid", "method": "hil", "result_of": ["INT-STC-0001"]}]
    assert rules(graph.check(g(*ns), "local")) == ["CK-A1", "CK-A3", "CK-A5", "CK-B2"]


def test_duplicates_and_stale_evidence():
    gr = g(*BASE, {"id": "TR-INT-STC-0001-3f9a1c2e", "type": "tr", "status": "valid",
                   "result_of": ["INT-STC-0001"], "shas": ["robarm-sw=abc1234"]})
    gr.owners = {"SYS-REQ-0001": ["a/needs.json", "b/needs.json"]}
    assert "CK-B5" in rules(graph.check(gr, "full"))
    assert graph.stale_evidence(gr, {"robarm-sw": "abc1234ffff"}) == []
    assert rules(graph.stale_evidence(gr, {"robarm-sw": "999"})) == ["CK-B6"]


def test_needs_diff_suspects():
    old = {n["id"]: n for n in BASE}
    new = {k: dict(v) for k, v in old.items()}
    new["SYS-REQ-0001"]["content"] = "now 40 ms"
    changes, impact, n = graph.needs_diff(old, new)
    assert any("CHANGED `SYS-REQ-0001`" in c for c in changes)
    assert n == 2 and all("SUSPECT (direct)" in i for i in impact)       # SYS-EL and INT-STC
    new2 = {k: v for k, v in new.items() if k != "SYS-NEED-0001"}
    _, impact2, _ = graph.needs_diff(old, new2)
    assert any("DANGLING `SYS-REQ-0001`" in i for i in impact2)
    assert any("SUSPECT (transitive)" in i for i in impact2)
