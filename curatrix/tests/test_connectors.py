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
    assert mine[0]["port"] == "EE-PORT-0001" and mine[1]["port"] == "-"
    assert (j1["1"]["net"], j1["1"]["name"], j1["3"]["net"]) == ("/CANARY_A", "Pin_1", "GND")
    assert j1["2"]["net"] == "Net-(J1-Pin_2)"                   # the T without a junction did not join GND


def test_d8_compare_reports_differences():
    """CK-D8 planted: a pin on another net, a missing connector, another Port."""
    mine = conn.connectors(conn.netlist(CONN / "conn.kicad_sch"))
    bad = copy.deepcopy(mine)
    bad[0]["pins"][0]["net"] = "/OTHER"
    bad[0]["port"] = "EE-PORT-0002"
    del bad[1]
    f = conn.compare(bad, conn.from_xml(CONN / "conn.net.xml"), "conn")
    assert any("J1 pin 1: name/net 'Pin_1'/'/OTHER' here, 'Pin_1'/'/CANARY_A' in KiCad" in x for x in f)
    assert any("J1: Port 'EE-PORT-0002' here, 'EE-PORT-0001' in KiCad" in x for x in f)
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
    doc["connectors"][1]["port"] = "EE-PORT-0002"
    doc["connectors"][1]["pins"][0]["net"] = "DATA"
    return doc


def test_pin_maps_from_the_model():
    m = modelmod.Model.load(DOMAIN / "ee-model.json")
    maps, names = conn.pin_maps(m)
    assert maps["EE-PORT-0001"] == {"1": "SERVO_PWM", "3": "GND"} and maps["EE-PORT-0002"] == {"1": "DATA"}
    assert names["EE-PORT-0001"] == "EePorts::ServoHeader"


def test_f1_against_the_model():
    """CK-F1 planted: a net differs from the pin map, a pin of the map is missing, a connector
    without Port, an unknown Port, a port of the board without connector."""
    m = modelmod.Model.load(DOMAIN / "ee-model.json")
    good = _doc_for_controller()
    assert conn.conformance(good, "EE-PCBA-0001", m, "c") == []
    bad = copy.deepcopy(good)
    bad["connectors"][0]["pins"][0]["net"] = "/CANARY_A"
    bad["connectors"][0]["pins"] = bad["connectors"][0]["pins"][:2]
    bad["connectors"][1]["port"] = None
    bad["connectors"].append({"ref": "J9", "port": "EE-PORT-0077", "pins": []})
    text = "\n".join(conn.conformance(bad, "EE-PCBA-0001", m, "c"))
    assert "J1 (EePorts::ServoHeader): pin 1 is on net '/CANARY_A', the pin map says 'SERVO_PWM'" in text
    assert "J1 (EePorts::ServoHeader): pin 3 of the pin map is not on the connector" in text
    assert "J2 has no Port field" in text
    assert "J9: Port EE-PORT-0077 is no connector port def" in text
    assert "1 port(s) of EePorts::BusHeader (bus), 0 connector(s) name it" in text
    assert "names no board def" in conn.conformance(good, "EE-PCBA-0099", m, "c")[0]


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
    assert {"CK-D7", "CK-D8", "CK-F1"} <= set(ids)
    root, repo = _repo(tmp_path / "b", yaml_text='version: 1\ncad: {projects: ["pcba/*/*.kicad_pro"]}\n')
    assert not {"CK-D7", "CK-D8", "CK-F1"} & set(checks.builtin_ids(checkcfg.load(repo / "checks.yaml", root)))
