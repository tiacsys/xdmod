"""Views between a domain model and the system model (views/domain.py): allocation, variants;
the context alias and the decomposition drawing. Fixture: the EE domain model of
fixtures/sysml/domain (see test_model.py)."""
import pytest

from curatrix import model, views
from helpers import FIXTURES


@pytest.fixture(scope="module")
def m():
    return model.Model.load(FIXTURES / "sysml" / "domain" / "ee-model.json")


def view(kind, root, **opts):
    return views.ViewDef(name="v", short_id=None, kind=kind, root=root, layer=None, qualified_name="v", opts=opts)


def short(x):
    return x.split("::")[-1]


def test_allocation_draws_exactly_the_derived_trace_links(m):
    """The view = the needs: every realizes/conforms/part_of/connects link of a need in scope
    is one edge, labelled with the link type, from the concrete to the abstract element."""
    g = views.graph(m, view("allocation", "EeBoards"))
    needs = model.to_needs(m)[0]["versions"][""]["needs"]
    qn = {n["id"]: n for n in g["nodes"]}
    own = {n["trace_id"] for n in g["nodes"] if n["id"].startswith("EeBoards::")}
    assert own == {k for k, n in needs.items() if n["qualified_name"].startswith("EeBoards::")}
    drawn = {(qn[e["src"]]["trace_id"], e["sysml_kind"], qn[e["dst"]]["trace_id"]) for e in g["edges"]}
    want = {(s, link, t) for s in own for link in ("realizes", "conforms", "part_of", "connects")
            for t in needs[s].get(link, [])}
    assert drawn == want and want
    assert ("EE-PCBA-0004", "realizes", "SYS-EL-0002") in drawn                  # multiple specialization
    assert {e["label"] for e in g["edges"]} <= {"«realizes»", "«conforms»", "«part of»", "«connects»"}
    up = [n for n in g["nodes"] if n["trace_id"].startswith("SYS-")]
    assert up and all(n["fill"] == "#EEEEEE" for n in up)                          # the system model is grey
    assert g["direction"] == "UP"


def test_allocation_of_ports_and_cables(m):
    g = views.graph(m, view("allocation", "EeCables"))
    edges = {(short(e["src"]), e["sysml_kind"], short(e["dst"])) for e in g["edges"]}
    assert ("ServoCable", "connects", "ServoHeader") in edges and ("ServoCable", "connects", "ServoPlug") in edges


def test_allocation_planted_errors(m):
    with pytest.raises(views.ViewError, match="no definition with a trace ID"):
        views.graph(m, view("allocation", "EeVariants"))
    # planted: a committed view that lost a realizes line fails CK-D3
    xml = views.to_mxfile(views.graph(m, view("allocation", "EeBoards")))
    g = views.graph(m, view("allocation", "EeBoards"))
    g["edges"] = [e for e in g["edges"] if not (short(e["src"]) == "ControllerBoard" and e["sysml_kind"] == "realizes")]
    d = views.diff_content(views.content_of(xml), views.content_of(views.to_mxfile(g)))
    assert any(x.startswith("missing in the file: EeBoards::ControllerBoard->") and x.endswith(":realizes") for x in d), d


def test_variants_view(m):
    g = views.graph(m, view("variants", "EeBoards::ControllerBoard"))
    nodes = {short(n["id"]): n for n in g["nodes"]}
    assert {"CtrlStd", "CtrlFast", "ControllerBoard", "Basic", "Full"} <= set(nodes)
    assert ("attributes", ["variantName = std"]) in nodes["CtrlStd"]["sections"]
    edges = {(short(e["src"]), e["rel"], short(e["dst"])) for e in g["edges"]}
    assert ("CtrlStd", "specialization", "ControllerBoard") in edges
    assert ("CtrlFast", "allocation", "Full") in edges and ("CtrlFast", "allocation", "ctrlB") in edges
    assert nodes["ctrlB"]["shape"] == "usage"
    with pytest.raises(views.ViewError, match="has no variants"):
        views.graph(m, view("variants", "EeBoards::SensorBoard"))


def test_context_is_an_interconnection_with_its_own_legend(m):
    ctx = views.graph(m, view("context", "EeBoards::ControllerBoard"))
    ic = views.graph(m, view("interconnection", "EeBoards::ControllerBoard"))
    assert ctx["kind"] == "context" and [n["id"] for n in ctx["nodes"]] == [n["id"] for n in ic["nodes"]]
    assert "system context" in views.to_mxfile(ctx)


def test_decomposition_is_drawn_in_sysml_notation(m):
    g = views.graph(m, view("decomposition", "EeBoards::ControllerBoard"))
    assert g["draw"] and g["nodes"][0]["shape"] == "def"
    assert g["nodes"][0]["label"] == "«part def»\n<EE-PCBA-0001> ControllerBoard"


def test_turning_keeps_the_content(m):
    for kind, root in (("allocation", "EeBoards"), ("variants", "EeBoards::ControllerBoard")):
        bare = views.content_of(views.to_mxfile(views.graph(m, view(kind, root))))
        turned = views.content_of(views.to_mxfile(views.graph(m, view(kind, root, direction="RIGHT"))))
        assert bare == turned, kind
