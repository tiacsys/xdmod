import json

from curatrix import model
from helpers import FIXTURES

PROBE = FIXTURES / "sysml" / "probe-model.json"


def load():
    return model.Model.load(PROBE)


def test_compact_is_stable_and_idempotent():
    data = json.loads(PROBE.read_text())
    again = model.compact(data, {"XdTrace", "NeedStubs"})
    assert model.dumps(again) == PROBE.read_text()
    ids = [x["identity"]["@id"] for x in data]
    assert ids == sorted(ids) and "Probe::LogicalJoint" in ids


def test_metadata_and_inheritance():
    m = load()
    follow = next(p for p in m.user() if p.get("qualifiedName") == "Probe::Follow")
    ctrl = next(p for p in m.user() if p.get("qualifiedName") == "Probe::JointController")
    joint = next(p for p in m.user() if p.get("qualifiedName") == "Probe::LogicalJoint")
    assert m.inherited_meta(follow, "XdTrace::Trace", "layer") == "functional"   # own
    assert m.inherited_meta(joint, "XdTrace::Trace", "layer") == "logical"       # from the package
    assert m.inherited_meta(ctrl, "XdTrace::Trace", "status") == "draft"


def test_to_needs():
    doc, findings = model.to_needs(load(), "probe", {"Probe": "model/Probe.sysml"})
    assert findings == []
    n = doc["versions"][""]["needs"]
    assert sorted(n) == ["SYS-EL-0001", "SYS-EL-0002", "SYS-EL-0003", "SYS-UC-0001"]     # views are not needs
    assert n["SYS-EL-0001"]["realizes"] == ["SYS-UC-0001"]                  # dependency, by kinds
    assert n["SYS-EL-0002"]["realizes"] == ["SYS-EL-0001"]                  # allocate f to c: target realizes
    assert n["SYS-EL-0002"]["satisfies"] == ["SYS-REQ-0001"]                # satisfy ... by usage -> its def (D128)
    assert n["SYS-EL-0002"]["status"] == "draft" and n["SYS-EL-0002"]["layer"] == "logical"
    assert n["SYS-EL-0003"]["instances"] == ["Probe::arm::joint1", "Probe::arm::joint2"]
    assert n["SYS-UC-0001"]["type"] == "sys-uc" and "layer" not in n["SYS-UC-0001"]
    assert n["SYS-EL-0001"]["source_file"] == "model/Probe.sysml"


def test_top_packages(tmp_path):
    f = tmp_path / "a.sysml"
    f.write_text("library package XdTrace {\n}\npackage <'P'> 'My Pkg' { }\nstandard library package S;\n")
    assert model.top_packages([f]) == {"XdTrace", "My Pkg", "S"}


def test_top_packages_ignores_nested(tmp_path):
    f = tmp_path / "b.sysml"
    f.write_text("package Outer {\n    package Inner {\n    }\n    private package Hidden;\n}\n")
    assert model.top_packages([f]) == {"Outer"}
