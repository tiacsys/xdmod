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


def test_top_packages_skips_nested_packages_comments_and_strings(tmp_path):
    f = tmp_path / "a.sysml"
    f.write_text("package A {\n    public package Inner { part def X; }\n    // package C {\n"
                 "    doc /* package D { */\n    attribute s = \"package E {\";\n}\npackage B;\n")
    assert model.top_packages([f]) == {"A", "B"}


DOMAIN = FIXTURES / "sysml" / "domain"      # made by test_tools_live.py::test_domain_model_fixture_is_fresh


def domain():
    return model.Model.load(DOMAIN / "ee-model.json"), model.Model.load(DOMAIN / "sys-model.json")


def test_domain_needs_links_from_specialization():
    doc, findings = model.to_needs(domain()[0], "ee")
    n = doc["versions"][""]["needs"]
    assert findings == []
    assert n["EE-PCBA-0001"]["realizes"] == ["SYS-EL-0001"] and n["EE-PCBA-0001"]["type"] == "ee-pcba"
    assert n["EE-PCBA-0002"]["realizes"] == ["SYS-EL-0003"]                      # super in a nested package
    assert n["EE-PCBA-0004"]["realizes"] == ["SYS-EL-0001", "SYS-EL-0002"]      # multiple specialization
    assert n["EE-PORT-0001"]["conforms"] == ["SYS-IF-0002"]
    # part_of also through a conjugated port (`~ServoHeader` on ServoBoard)
    assert n["EE-PORT-0001"]["part_of"] == ["EE-PCBA-0001", "EE-PCBA-0004", "EE-PCBA-0005", "EE-PCBA-0006", "EE-PCBA-0007"]
    assert "realizes" not in n["EE-PORT-0009"]                                   # no link type: CK-E4 says so


def test_conformance_planted_errors():
    d, u = domain()
    f = model.conformance(d, [u])
    expect = [
        "EeBoards::ComboBoard: port servoOut (from Sys::Driver) is not redefined",
        "EeBoards::ComboBoard: inherits port name 'servoOut' more than once",
        "EeBoards::ControllerBoardW: port servoOut (from EeBoards::ControllerBoard) is redefined by "
        "EeBoards::ControllerBoardW::servoOut with Sys::ServoIf, which does not specialize EePorts::ServoHeader",
        "EeBoards::FlatServoBoard: port servoIn (from Sys::Servo) is redefined by EeBoards::FlatServoBoard::servoIn "
        "with EePorts::ServoHeader, which does not match the conjugation of ~Sys::ServoIf",
        "EeBoards::NoIdBoard: specializes SYS-EL-0002 (Sys::Driver) but has no ID of its own",
        "EeBoards::OddBoard: EE-PORT-0009 specializes SYS-EL-0002, but there is no trace link from EE-PORT to SYS-EL",
        "EeBoards::SensorBoard: port bus (from Sys::Detail::Sensor) is not redefined",
        "EeBoards::WrongBoard: port servoOut (from Sys::Controller) is redefined by EeBoards::WrongBoard::servoOut "
        "with EePorts::BusHeader, which does not specialize Sys::ServoIf",
    ]
    assert len(f) == len(expect) and all(x.startswith(e) for x, e in zip(f, expect)), f
    # clean: the good board, its variant without own redefinitions, one port redefining both
    # supers' `servoOut`, `~ServoHeader` for `~ServoIf`, and the signal ports of the port defs
    # (Pin :> ElSignal, no ID needed)
    assert not [x for x in f if x.startswith(("EeBoards::ControllerBoard:", "EeBoards::ControllerBoardB",
                                              "EeBoards::ComboBoard2", "EeBoards::ServoBoard", "EePorts::"))]


def test_configs_from_the_upstream_configuration():
    d, u = domain()
    n = model.add_configs(model.to_needs(d, "ee")[0], [u])["versions"][""]["needs"]
    assert n["EE-PCBA-0001"]["configs"] == ["SYS-CFG-0001", "SYS-CFG-0002"]   # Basic and Full configure Controller
    assert n["EE-PCBA-0004"]["configs"] == ["SYS-CFG-0001", "SYS-CFG-0002"]   # Controller or Driver
    assert "configs" not in n["EE-PCBA-0006"]                   # realizes Servo, configured by none: in every one
    assert "configs" not in n["EE-PORT-0001"]


def test_conformance_without_upstream_finds_nothing():
    assert model.conformance(domain()[0], []) == []
