"""The SysML standard views (views/sysml.py, views/draw.py) on a small synthetic model.

The fixture fixtures/sysml/views-probe-model.json is the compact Pilot export of
fixtures/sysml/views-probe.sysml (``pilot.run`` on that file with the xdmod SysML library, then
``model.compact``; the same steps as ``curatrix gen model``). Rebuild it when the .sysml changes.
"""
from pathlib import Path

import pytest

from curatrix import model, views
from curatrix.ws import Workspace
from helpers import FIXTURES

XDMOD = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def m():
    return model.Model.load(FIXTURES / "sysml" / "views-probe-model.json")


def graph(m, name):
    (v,) = [v for v in views.discover(m) if v.name == name]
    return views.graph(m, v)


def test_general_view_labels_edges_and_compartments(m):
    g = graph(m, "vGeneral")
    nodes = {n["id"].split("::")[-1]: n for n in g["nodes"]}
    assert nodes["C"]["label"] == "«item def»\n<c-t> C"
    assert nodes["N"]["label"] == "«abstract item def»\nN"
    assert nodes["C"]["trace_id"] == "XD-ADR-0004"                         # @See
    assert ("attributes", ["size = 3"]) in nodes["C"]["sections"]
    edges = {(e["src"].split("::")[-1], e["dst"].split("::")[-1], e["rel"], e["label"]) for e in g["edges"]}
    # one reference per target type, named after the link type; the owner requires >= 1 in total
    assert ("C", "A", "reference", "link [0..*] (>= 1 in total)") in edges
    assert ("C", "B", "reference", "link [0..*] (>= 1 in total)") in edges
    assert ("C", "A", "composition", "part1") in edges
    assert ("C", "N", "specialization", "") in edges
    assert not any(e[0] == "N" and e[2] == "reference" for e in edges)      # abstract features are listed, not drawn


def test_action_flow(m):
    g = graph(m, "vFlow")
    shapes = {n["id"].split("::")[-1]: n["shape"] for n in g["nodes"]}
    assert shapes["start"] == "initial" and shapes["done"] == "final" and shapes["produce"] == "action"
    assert "decision" in shapes.values()
    flows = [e for e in g["edges"] if e["rel"] == "flow"]
    assert [(f["src"].split("::")[-1], f["dst"].split("::")[-1], f["label"]) for f in flows] == \
        [("produce.a", "consume.a", "A")]
    assert sorted(e["label"] for e in g["edges"] if e["label"] and e["rel"] != "flow") == ["[else]", "[ok]"]
    # node order follows the flow, so ELK's model-order cycle breaking keeps forward edges forward
    order = [n["id"].split("::")[-1] for n in g["nodes"]]
    assert order.index("produce") < order.index("consume") < order.index("done")


def test_state_transition(m):
    g = graph(m, "vLife")
    assert g["nodes"][0]["shape"] == "frame"
    labels = {e["label"] for e in g["edges"]}
    assert {"Go", "[not flag]"} <= labels
    assert any(n["shape"] == "initial" for n in g["nodes"])


def test_use_cases_one_frame_per_subject_type(m):
    g = graph(m, "vUc")
    frames = {n["id"].split("::")[-1]: n for n in g["nodes"] if n["shape"] == "subject"}
    assert sorted(frames) == ["Ws1", "Ws2"]
    parent = {n["id"].split("::")[-1]: n["parent"].split("::")[-1] for n in g["nodes"] if n["shape"] == "usecase"}
    assert parent == {"U1": "Ws1", "U2": "Ws2", "U3": "Ws1"}
    actors = [n for n in g["nodes"] if n["shape"] == "actor"]
    assert [a["label"] for a in actors] == ["Person"]                     # deduplicated by type
    assert [e["label"] for e in g["edges"] if e["rel"] == "include"] == ["«include»"]


def test_content_has_no_geometry_in_it(m):
    """CK-D3 compares content only: fake, very different layouts must give the same content."""
    for v in views.discover(m):
        g = views.graph(m, v)
        bare = views.content_of(views.to_mxfile(g))
        ids = [n["id"] for n in g["nodes"]] + [p["id"] for n in g["nodes"] for p in n["ports"]]
        fake = {i: {"x": 37 * k, "y": 911 - 13 * k, "width": 400, "height": 300} for k, i in enumerate(ids)}
        fake.update({e["id"]: {"points": [(1, 2), (3, 4), (500, 600)], "bends": [(3, 4)],
                               "label": {"x": 9, "y": 9, "width": 50, "height": 14}} for e in g["edges"]})
        assert views.content_of(views.to_mxfile(g, fake)) == bare, v.name


@pytest.mark.tools
def test_content_is_the_same_with_the_real_layout(m):
    """The same property with the real ELK layout, for the fixture and for every xdmod view."""
    ws = Workspace(Path(__file__).resolve().parents[3])
    if not (ws.opt / "node").exists():
        pytest.skip("node not installed")
    for mm in (m, model.Model.load(XDMOD / "generated" / "model.json")):
        for v in views.discover(mm):
            g = views.graph(mm, v)
            laid = views.positions(views.run_elk(ws, views.to_elk(g)))
            assert views.content_of(views.to_mxfile(g, laid)) == views.content_of(views.to_mxfile(g)), v.name


def test_legend_placement_and_turning_keep_the_content(m):
    """The layout may turn a view and move its legend to fit a page; CK-D3 content stays the same."""
    for v in views.discover(m):
        g = views.graph(m, v)
        bare = views.content_of(views.to_mxfile(g))
        for side in ("below-narrow", "right"):
            g["legend"] = side
            assert views.content_of(views.to_mxfile(g)) == bare, (v.name, side)
        if v.kind in ("general", "actionflow", "statetransition", "usecases"):
            other = views.PERPENDICULAR[g["direction"]]
            turned = views.ViewDef(**{**v.__dict__, "opts": {**v.opts, "direction": other}})
            assert views.content_of(views.to_mxfile(views.graph(m, turned))) == bare, v.name


def test_canvas_ratio_counts_boxes_and_routes():
    xml = ('<mxfile><diagram><mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>'
           '<object id="a" label=""><mxCell vertex="1" parent="1"><mxGeometry x="0" y="0" width="100" height="100" as="geometry"/></mxCell></object>'
           '<object id="e" label=""><mxCell edge="1" parent="1" source="a" target="a"><mxGeometry relative="1" as="geometry">'
           '<Array as="points"><mxPoint x="300" y="50"/></Array><mxPoint x="900" y="900" as="offset"/></mxGeometry></mxCell></object>'
           '</root></mxGraphModel></diagram></mxfile>')
    assert views.canvas_ratio(xml) == 3.0                     # the label offset is not a route point
    assert views.ratio_error(1.33) == 0 and views.ratio_error(3.0) > 0


def test_turned_interconnection_keeps_the_content():
    m = model.Model.load(FIXTURES / "sysml" / "probe-model.json")
    for v in views.discover(m):
        bare = views.content_of(views.to_mxfile(views.graph(m, v)))
        for d in ("DOWN", "RIGHT"):
            turned = views.ViewDef(**{**v.__dict__, "opts": {**v.opts, "direction": d}})
            g = views.graph(m, turned)
            g["wrap"] = True
            assert views.content_of(views.to_mxfile(g)) == bare, (v.name, d)


def test_interconnection_show_with_an_unknown_port_is_an_error():
    m = model.Model.load(FIXTURES / "sysml" / "probe-model.json")
    (v,) = views.discover(m)
    bad = views.ViewDef(**{**v.__dict__, "opts": {**v.opts, "show": "noSuchPort"}})
    with pytest.raises(views.ViewError, match="noSuchPort"):
        views.graph(m, bad)
