"""The XDMOD self-model (xdmod/model, compiled into xdmod/generated/model.json) and its views.

* The need types and link types in package XdmodNeeds must match needs/needs_config.toml, so the
  diagrams of the trace model can never drift from what sphinx-needs enforces.
* The SysML standard views (general, actionflow, statetransition, usecases) are built from the
  self-model, and the committed views/*.drawio.svg pass the content check (CK-D3).
"""
import tomllib
from pathlib import Path

import pytest

from curatrix import model, views
from curatrix.views import sysml

XDMOD = Path(__file__).resolve().parents[2]
MODEL = XDMOD / "generated" / "model.json"


@pytest.fixture(scope="module")
def m():
    return model.Model.load(MODEL)


def _model_trace(m):
    """{directive: {link: (set of target directives, min 1?)}} from package XdmodNeeds."""
    defs = {p["@id"]: p for p in m.of_type("ItemDefinition")
            if not p.get("isLibraryElement") and p.get("qualifiedName", "").startswith("XdmodNeeds::")}

    def directive(d):
        return d.get("declaredShortName")

    def ancestors(d):
        out, todo = [], [d]
        while todo:
            cur = todo.pop()
            out.append(cur)
            todo += [g for g in sysml.related(m, cur, "Subclassification") if g["@id"] in defs]
        return out

    result = {}
    for d in defs.values():
        if not directive(d) or d.get("isAbstract"):
            continue
        links: dict[str, list] = {}
        mins: dict[str, bool] = {}
        # walk from the most general to the most specific type: specific features win
        for t in reversed(ancestors(d)):
            for f in sysml.features(m, t):
                if f.get("@type") != "ItemUsage" or not f.get("isReference"):
                    continue
                link = sysml.link_name(m, f)
                targets = [directive(x) for x in m.types_of(f) if directive(x)]
                lower = sysml.multiplicity(m, f).strip("[]").split("..")[0]
                redefines = bool(sysml.related(m, f, "Redefinition"))
                if redefines:
                    mins[link] = lower not in ("", "0", "*")
                    if targets:
                        links[link] = targets            # a redefinition replaces the targets
                elif not f.get("isAbstract"):            # a subsetting feature adds a target type
                    links.setdefault(link, [])
                    links[link] = [*links[link], *targets]
        result[directive(d)] = {k: (set(v), mins.get(k, False)) for k, v in links.items() if v}
    return result


def _config_trace():
    cfg = tomllib.loads((XDMOD / "needs" / "needs_config.toml").read_text())["needs"]
    out = {}
    for t in cfg["types"]:
        out[t["directive"]] = {k: (set(v["target_types"]), (v.get("schema") or {}).get("minItems", 0) >= 1)
                               for k, v in (t.get("links") or {}).items()}
    return out


def test_need_types_match_needs_config(m):
    model_trace, config_trace = _model_trace(m), _config_trace()
    assert sorted(model_trace) == sorted(config_trace)


@pytest.mark.parametrize("directive", sorted(_config_trace()))
def test_link_types_match_needs_config(m, directive):
    assert _model_trace(m)[directive] == _config_trace()[directive]


def test_every_view_builds_and_its_file_passes_the_content_check(m):
    vs = views.discover(m)
    assert {v.kind for v in vs} >= {"general", "actionflow", "statetransition", "usecases", "interconnection"}
    for v in vs:
        f = XDMOD / "views" / views.file_name(v)
        assert f.exists(), f"{f.name} missing: run `curatrix views build xdmod`"
        assert views.check_file(f, views.to_mxfile(views.graph(m, v))) == [], v.name


def _view(m, name):
    (v,) = [v for v in views.discover(m) if v.name == name]
    return views.graph(m, v)


def test_general_view_trace_links_point_from_concrete_to_abstract(m):
    g = _view(m, "traceSystem")
    edges = {(e["src"].split("::")[-1], e["dst"].split("::")[-1], e["label"]) for e in g["edges"]}
    assert ("SystemRequirement", "StakeholderNeed", "refines [1..*]") in edges
    # one reference per target type, named after the link type; at least one link is required
    assert ("IntegrationTestCase", "Interface", "verifies [0..*] (>= 1 in total)") in edges
    labels = {n["label"] for n in g["nodes"]}
    assert "«item def»\n<sys-req> SystemRequirement" in labels
    assert not any("Software" in n["id"] for n in g["nodes"])                 # expose only what is asked


def test_general_view_compartments_and_values(m):
    g = _view(m, "workspaceRepos")
    sys_repo = next(n for n in g["nodes"] if n["id"].endswith("::SysEngRepo"))
    assert ("attributes", ["domain = SYS"]) in sys_repo["sections"]
    assert sys_repo["trace_id"] == "XD-ADR-0001"                            # @See links the box to its decision
    assert any(e["rel"] == "specialization" and e["dst"].endswith("::Repository") for e in g["edges"])
    assert any(e["rel"] == "composition" and e["label"] == "syseng" for e in g["edges"])


def test_action_flow_guards_pins_and_flows(m):
    g = _view(m, "changeProcess")
    labels = sorted(e["label"] for e in g["edges"] if e["label"])
    assert labels == ["[approved]", "[ciPasses]", *["[else]"] * 5, "[linksSuspect]", "[localChecksPass]",
                      "[reviewClean]"]
    assert {n["shape"] for n in g["nodes"]} >= {"initial", "final", "decision", "action"}
    g = _view(m, "buildAndCheck")
    flows = [e for e in g["edges"] if e["rel"] == "flow"]
    assert any(e["src"].endswith("'gen model (Pilot)'.modelJson") and e["label"] == "ModelJson" for e in flows)


def test_state_transition_triggers_and_guards(m):
    g = _view(m, "evidenceStatus")
    labels = {e["label"] for e in g["edges"]}
    assert {"[fromMainOrBaseline]", "[not fromMainOrBaseline]", "PinsChanged", "PinsMatch"} <= labels
    assert g["nodes"][0]["shape"] == "frame" and all(n["parent"] == g["nodes"][0]["id"] for n in g["nodes"][1:])


def test_use_case_view_dedupes_actors(m):
    g = _view(m, "rolesAndUseCases")
    actors = [n for n in g["nodes"] if n["shape"] == "actor"]
    assert len(actors) == len({n["id"] for n in actors}) == 7
    assert sum(1 for e in g["edges"] if e["rel"] == "include") == 3
