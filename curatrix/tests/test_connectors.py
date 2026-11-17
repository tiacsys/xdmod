"""Connector pin tables (task 5.18): plain-Python nets vs. KiCad's netlist (CK-D8), the
committed connectors.json (CK-D7), and the pin maps of the EE model (CK-F1)."""
import copy
import json
import shutil

import pytest

from curatrix import checkcfg, checks, connectors as conn, gen, model as modelmod
from curatrix.ws import Repo, Workspace
from helpers import FIXTURES, git_init

CONN = FIXTURES / "kicad" / "conn"
DOMAIN = FIXTURES / "sysml" / "domain"
YAML = ('version: 1\ncad: {projects: ["pcba/*/*.kicad_pro"], connectors: generated}\n'
        "model: {files: [model/*.sysml]}\n")


def _repo(tmp_path, yaml_text=YAML):
    root = tmp_path / "ws"
    repo = git_init(root / "r")
    (repo / "checks.yaml").write_text(yaml_text)
    d = repo / "pcba" / "conn"
    d.mkdir(parents=True)
    for f in ("conn.kicad_pro", "conn.kicad_sch"):
        shutil.copy(CONN / f, d / f)
    (repo / "generated").mkdir()
    shutil.copy(DOMAIN / "ee-model.json", repo / "generated" / "model.json")
    return root, repo


def _run(root, repo, cid, fn):
    ctx = checks.Ctx(Workspace(root), Repo("r", repo, "r"), checkcfg.load(repo / "checks.yaml", root), "local",
                     False, None, root / "out")
    (root / "out").mkdir(exist_ok=True)
    r = checks.Result(cid, cid, level="warning")
    getattr(checks, fn)(ctx, r)
    return r.findings


def test_extraction_equals_kicad_netlist():
    """Rotated (90, 180, 270) and mirrored symbols, labels, power, a T without junction: the
    plain-Python nets equal those of KiCad 10's XML netlist (recorded in conn.net.xml)."""
    mine = conn.connectors(conn.netlist(CONN / "conn.kicad_sch"))
    assert conn.compare(mine, conn.from_xml(CONN / "conn.net.xml"), "conn") == []
    j1 = {p["number"]: p for p in mine[0]["pins"]}
    assert (mine[0]["portName"], mine[0]["portType"], mine[0]["portTypeID"]) == ("servoOut", "ServoHeader", "EE-PORT-0001")
    assert mine[1]["portName"] == "-" and mine[1]["portTypeID"] is None and "Port" not in mine[1]
    assert (j1["1"]["net"], j1["1"]["name"], j1["3"]["net"]) == ("/CANARY_A", "Pin_1", "GND")
    assert j1["2"]["net"] == "Net-(J1-Pin_2)"                   # the T without a junction did not join GND


HIER = FIXTURES / "kicad" / "hier"


def test_hierarchy_power_flags_and_lib_name_equal_kicad():
    """A sheet used twice (sheet pins, hierarchical labels, a local label inside the sheet), a
    PWR_FLAG on GND (it joins nothing), a global label on the GND net (it names the net over the
    power symbol), and a connector placed with lib_name: every pin's net equals KiCad's netlist."""
    import xml.etree.ElementTree as ET
    nl = conn.netlist(HIER / "hier.kicad_sch")
    kicad = {(n2.get("ref"), n2.get("pin")): n.get("name")
             for n in ET.parse(HIER / "hier.net.xml").getroot().iter("net") for n2 in n.iter("node")}
    assert nl.nets == kicad and nl.findings == []
    assert kicad[("J1", "1")] == "/ch1/MID" and kicad[("J1", "3")] == "ZZZ"
    j1 = conn.connectors(nl)[0]
    assert j1["ref"] == "J1" and len(j1["pins"]) == 3          # pins found through lib_name
    assert conn.compare(conn.connectors(nl), conn.from_xml(HIER / "hier.net.xml"), "hier") == []


def test_buses_are_reported(tmp_path):
    """A bus is not read: the extraction says so instead of writing a silently wrong table."""
    sch = tmp_path / "b.kicad_sch"
    sch.write_text((CONN / "conn.kicad_sch").read_text().replace(
        "(sheet_instances", '(bus (pts (xy 10 10) (xy 20 10)) (stroke (width 0) (type default)) (uuid "b"))\n\t(sheet_instances', 1))
    doc = conn.document("b", sch, tmp_path)
    assert any("buses are not read yet" in u for u in doc["unsupported"])
    assert doc["inputs"] == ["b.kicad_sch"]


def test_d8_compare_reports_differences():
    """CK-D8 planted: a pin on another net, a missing connector, another portName and portTypeID."""
    mine = conn.connectors(conn.netlist(CONN / "conn.kicad_sch"))
    bad = copy.deepcopy(mine)
    bad[0]["pins"][0]["net"] = "/OTHER"
    bad[0]["portName"] = "bus"
    bad[0]["portTypeID"] = "EE-PORT-0002"
    del bad[1]
    f = conn.compare(bad, conn.from_xml(CONN / "conn.net.xml"), "conn")
    assert any("J1 pin 1: name/net 'Pin_1'/'/OTHER' here, 'Pin_1'/'/CANARY_A' in KiCad" in x for x in f)
    assert any("J1: portName 'bus' here, 'servoOut' in KiCad" in x for x in f)
    assert any("J1: portTypeID 'EE-PORT-0002' here, 'EE-PORT-0001' in KiCad" in x for x in f)
    assert any("J2 is in KiCad's netlist, not in the extraction" in x for x in f)


@pytest.mark.tools
def test_d8_against_kicad_cli(tmp_path, monkeypatch):
    """CK-D8 with KiCad: the check runs kicad-cli and finds nothing on the fixture; planted: an
    extraction that puts a pin on another net (a reader bug) is reported."""
    if shutil.which("kicad-cli") is None:
        pytest.skip("kicad-cli not installed")
    root, repo = _repo(tmp_path)
    assert _run(root, repo, "CK-D8", "c_connectors_netlist") == []
    real = conn.connectors

    def buggy(nl):
        out = real(nl)
        out[0]["pins"][1]["net"] = "GND"
        return out
    monkeypatch.setattr(conn, "connectors", buggy)
    f = _run(root, repo, "CK-D8", "c_connectors_netlist")
    assert any("J1 pin 2: name/net 'Pin_2'/'GND' here, 'Pin_2'/'Net-(J1-Pin_2)' in KiCad" in x for x in f), f


def test_d7_fresh(tmp_path):
    """CK-D7 planted: missing, then stale after a label changed; a file of a removed project."""
    root, repo = _repo(tmp_path)
    assert any("missing; run `curatrix gen connectors r`" in x for x in _run(root, repo, "CK-D7", "c_connectors_fresh"))
    cfg = checkcfg.load(repo / "checks.yaml", root)
    for o in gen.connectors(Workspace(root), cfg):
        o.write()
    assert _run(root, repo, "CK-D7", "c_connectors_fresh") == []
    doc = json.loads((repo / "generated/conn.connectors.json").read_text())
    assert doc["project"] == "conn" and doc["root_sheet"] == "pcba/conn/conn.kicad_sch"
    assert list(doc["inputs"]) == ["pcba/conn/conn.kicad_sch"]
    sch = repo / "pcba/conn/conn.kicad_sch"
    sch.write_text(sch.read_text().replace('(label "CANARY_A"', '(label "CANARY_X"'))
    assert any("does not match the KiCad schematic" in x for x in _run(root, repo, "CK-D7", "c_connectors_fresh"))
    (repo / "generated/old.connectors.json").write_text("{}")
    assert any("old.connectors.json: no project old" in x for x in _run(root, repo, "CK-D7", "c_connectors_fresh"))


def _doc_for_controller():
    """The fixture's connectors renamed to fit ControllerBoard (EE-PCBA-0001) of the domain
    fixture: J1 = ServoHeader (pin 1 SERVO_PWM, pin 3 GND), J2 = BusHeader (pin 1 DATA)."""
    doc = {"connectors": conn.connectors(conn.netlist(CONN / "conn.kicad_sch"))}
    doc["connectors"][0]["pins"][0]["net"] = "/SERVO_PWM"
    doc["connectors"][0]["pins"][1]["net"] = "unconnected-(J1-Pin_2-Pad2)"     # not in the pin map
    doc["connectors"][1].update(portName="bus", portType="BusHeader", portTypeID="EE-PORT-0002")
    doc["connectors"][1]["pins"][0]["net"] = "DATA"
    return doc


def test_pin_maps_from_the_model():
    m = modelmod.Model.load(DOMAIN / "ee-model.json")
    maps, names = conn.pin_maps(m)
    assert maps["EE-PORT-0001"] == {"1": "SERVO_PWM", "3": "GND"} and maps["EE-PORT-0002"] == {"1": "DATA"}
    assert names["EE-PORT-0001"] == "EePorts::ServoHeader"


def test_f1_against_the_model():
    """CK-F1 planted: a net differs from the pin map, a pin of the map is missing, a connector
    without portName, a portName that is no port of the board, a wrong portType and portTypeID, the
    old Port field, a port of the board without connector, a port named twice."""
    m = modelmod.Model.load(DOMAIN / "ee-model.json")
    good = _doc_for_controller()
    assert conn.conformance(good, "EE-PCBA-0001", m, "c") == []
    bad = copy.deepcopy(good)
    bad["connectors"][0]["pins"][0]["net"] = "/CANARY_A"
    bad["connectors"][0]["pins"][1]["net"] = "/EXTRA"
    bad["connectors"][0]["pins"] = bad["connectors"][0]["pins"][:2]
    bad["connectors"][1].update(portName=None, portType=None, portTypeID=None)
    bad["connectors"].append({"ref": "J9", "portName": "j9", "pins": []})
    bad["connectors"].append({"ref": "J8", "portName": "servoOut", "portType": "BusHeader", "portTypeID": "EE-PORT-0002",
                              "pins": [{"number": "1", "name": "", "net": "SERVO_PWM"}, {"number": "3", "name": "", "net": "GND"}]})
    bad["connectors"].append({"ref": "J7", "Port": "EE-PORT-0001", "portName": None, "pins": []})
    text = "\n".join(conn.conformance(bad, "EE-PCBA-0001", m, "c"))
    assert "J1 (EePorts::ServoHeader): pin 1 is on net '/CANARY_A', the pin map says 'SERVO_PWM'" in text
    assert "J1 (EePorts::ServoHeader): pin 3 of the pin map is not on the connector" in text
    assert "J1 (EePorts::ServoHeader): pin 2 is on net '/EXTRA', but the pin map has no pin 2" in text
    assert "J2 has no portName field" in text
    assert "J9: portName 'j9' is no port of the def (ports: bus, servoOut)" in text
    assert "J8: portType is 'BusHeader', the port servoOut is typed by ServoHeader (EE-PORT-0001): portType = ServoHeader" in text
    assert "J8: portTypeID is 'EE-PORT-0002'" in text
    assert "J7 has the old field Port = 'EE-PORT-0001'; replace it by portName" in text
    assert "the port bus (BusHeader) of the board def EeBoards::ControllerBoard is named by 0 connector(s) (none)" in text
    assert "the port servoOut (ServoHeader) of the board def EeBoards::ControllerBoard is named by 2 connector(s) (J1, J8)" in text
    assert "names no board def" in conn.conformance(good, "EE-PCBA-0099", m, "c")[0]


def test_f22_port_and_connector_names():
    """CK-F22 planted: a designator-like port name and one that is not lowerCamelCase in the model;
    a connector with a portName and a J designator. Pins and signals inside port defs do not count."""
    m = modelmod.Model.load(DOMAIN / "ee-model.json")
    assert conn.port_name_findings(m) == []
    data = json.loads((DOMAIN / "ee-model.json").read_text())
    for x in data:
        if x["identity"]["@id"] == "EeCables::ServoMotor::plug":
            x["payload"]["name"] = "j1"
        if x["identity"]["@id"] == "EeCables::ServoCable::boardEnd":
            x["payload"]["name"] = "Board_End"
    text = "\n".join(conn.port_name_findings(modelmod.Model(data)))
    assert "model EeCables::ServoMotor::plug: the port name 'j1' looks like a reference designator" in text
    assert "the port name 'Board_End' is not lowerCamelCase" in text
    assert "pwm" not in text and "gnd" not in text
    assert conn.designator_findings({"connectors": [{"ref": "X1", "portName": "servoOut"}, {"ref": "R1"}]}, "c") == []
    assert conn.designator_findings({"connectors": [{"ref": "J1", "portName": "-"}]}, "c") == [
        "c: J1 has a portName but no X designator; connectors are X1, X2, ... (set the reference prefix to X)"]
    for name in ("j1", "p3", "x2", "cn1", "JP2"):
        assert conn.DESIGNATOR_LIKE.match(name)
    for name in ("canaryLink", "servoBase", "bus", "plug", "boardEnd"):
        assert not conn.DESIGNATOR_LIKE.match(name)


def test_f22_through_the_check(tmp_path):
    root, repo = _repo(tmp_path)
    (repo / "generated/conn.connectors.json").write_text(json.dumps(_doc_for_controller()))
    f = _run(root, repo, "CK-F22", "c_port_names")
    assert f == ["pcba/conn/conn.kicad_sch: J1 has a portName but no X designator; connectors are X1, X2, ... "
                 "(set the reference prefix to X)",
                 "pcba/conn/conn.kicad_sch: J2 has a portName but no X designator; connectors are X1, X2, ... "
                 "(set the reference prefix to X)"]


def test_f1_through_the_check(tmp_path):
    root, repo = _repo(tmp_path)
    assert any("conn.connectors.json missing" in x for x in _run(root, repo, "CK-F1", "c_connectors_model"))
    (repo / "generated/conn.connectors.json").write_text(json.dumps(_doc_for_controller()))
    assert _run(root, repo, "CK-F1", "c_connectors_model") == []
    d = _doc_for_controller()
    d["connectors"][0]["pins"][2]["net"] = "GNDX"
    (repo / "generated/conn.connectors.json").write_text(json.dumps(d))
    assert any("pin 3 is on net 'GNDX', the pin map says 'GND'" in x for x in _run(root, repo, "CK-F1", "c_connectors_model"))


def test_strip_root():
    assert conn.strip_root("/X") == "X" and conn.strip_root("/sub/X") == "/sub/X" and conn.strip_root("GND") == "GND"


def test_checks_switch_on(tmp_path):
    root, repo = _repo(tmp_path)
    ids = checks.builtin_ids(checkcfg.load(repo / "checks.yaml", root))
    assert {"CK-D7", "CK-D8", "CK-F1", "CK-F22"} <= set(ids)
    root, repo = _repo(tmp_path / "b", yaml_text='version: 1\ncad: {projects: ["pcba/*/*.kicad_pro"]}\n')
    assert not {"CK-D7", "CK-D8", "CK-F1", "CK-F22"} & set(checks.builtin_ids(checkcfg.load(repo / "checks.yaml", root)))
