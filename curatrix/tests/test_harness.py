"""Wiring harnesses (task 5.22): WireViz YAML 1:1 with a cable def (CK-F7), the harness ends
against the pin maps of both ports (CK-F1), plain-Python tables, `curatrix cam` (WireViz)."""
import json
import shutil
import subprocess

import pytest
import yaml

from curatrix import checkcfg, checks, harness, model as modelmod
from curatrix.ws import Repo, Workspace
from helpers import FIXTURES, git_init

DOMAIN = FIXTURES / "sysml" / "domain"
YAML = ('version: 1\ncad: {projects: ["pcba/*/*.kicad_pro"], connectors: generated, harnesses: ["harness/*/*.yml"]}\n'
        "model: {files: [model/*.sysml]}\n")

# ServoCable (EE-HAR-0001) of the domain fixture: X1 mates with ServoHeader (EE-PORT-0001) of a
# board, X2 with ServoPlug (EE-PORT-0010) of the external part ServoMotor.
GOOD = {
    "metadata": {"title": "Servo cable", "TraceID": "EE-HAR-0001"},
    "connectors": {
        "X1": {"type": "JST XH housing", "manufacturer": "JST", "mpn": "XHP-3", "pins": [1, 2, 3],
               "pinlabels": ["SERVO_PWM", "NC", "GND"], "notes": "Port: EE-PORT-0001"},
        "X2": {"type": "JST XH receptacle", "pins": [1, 3], "pinlabels": ["SERVO_PWM", "GND"],
               "notes": "Mates with the servo.\nPort: EE-PORT-0010"},
    },
    "cables": {"W1": {"wirecount": 2, "length": 0.3, "gauge": "0.14 mm2", "colors": ["OG", "BK"],
                      "manufacturer": "Lapp", "mpn": "49900"}},
    "connections": [[{"X1": [1, 3]}, {"W1": [1, 2]}, {"X2": ["SERVO_PWM", "GND"]}]],
}


def _model():
    return modelmod.Model.load(DOMAIN / "ee-model.json")


def _h(data, name="servo-cable"):
    h = harness.Harness(name, FIXTURES, FIXTURES / f"{name}.yml")
    h.data = data
    return h


def test_ports_and_wiring_of_the_good_harness():
    h = _h(GOOD)
    assert harness.port_of(GOOD["connectors"]["X2"]) == "EE-PORT-0010"
    w = harness.wiring(h)
    assert w.unsupported == []
    assert any(set(g) == {("X1", "1"), ("W1", "1"), ("X2", "1")} for g in w.groups)
    assert any(set(g) == {("X1", "3"), ("W1", "2"), ("X2", "3")} for g in w.groups)   # pin label GND -> pin 3
    assert harness.conformance(h, _model(), "h.yml") == []


def test_f1_harness_ends():
    """CK-F1 planted (harness ends): a connector without Port, an unknown Port, a pin label that
    differs from the pin map, a pin of the map missing, a wire joining two nets, an unwired pin
    another end carries, an end the cable def does not have, a mate the reader does not support."""
    m = _model()
    bad = yaml.safe_load(yaml.safe_dump(GOOD))
    bad["connectors"]["X1"]["pinlabels"] = ["SERVO_PWM", "NC", "GNDX"]
    bad["connectors"]["X2"]["pins"] = [1]
    bad["connectors"]["X2"]["pinlabels"] = ["SERVO_PWM"]
    bad["connectors"]["X3"] = {"pins": [1], "notes": "spare"}
    bad["connectors"]["X4"] = {"pins": [1], "notes": "Port: EE-PORT-0077"}
    bad["connectors"]["X5"] = {"pins": [1], "pinlabels": ["DATA"], "notes": "Port: EE-PORT-0002"}
    bad["connections"] = [[{"X1": [1, 3]}, {"W1": [1, 2]}, {"X2": [1, 1]}], ["X1", "-->", "X2"]]
    text = "\n".join(harness.conformance(_h(bad), m, "h.yml"))
    assert "h.yml: connector X3 names no port" in text
    assert "connector X4: Port EE-PORT-0077 is no connector port def" in text
    assert "X1 (EePorts::ServoHeader): pin 3 is labelled 'GNDX', the pin map says 'GND'" in text
    assert "X2 (EeCables::ServoPlug): pin 3 of the pin map is not on the connector" in text
    assert "one conductor joins different nets: GND (X1:3), SERVO_PWM (X1:1 X2:1)" in text
    assert "connection set 2: entry 'X1' (mates, arrows and bare designators are not read)" in text
    assert "X5: Port EE-PORT-0002 is no end of the cable def EeCables::ServoCable" in text
    bad2 = yaml.safe_load(yaml.safe_dump(GOOD))
    bad2["connections"] = [[{"X1": 1}, {"W1": 1}, {"X2": 1}]]
    bad2["connectors"]["X2"]["notes"] = "Port: EE-PORT-0001"
    text = "\n".join(harness.conformance(_h(bad2), m, "h.yml"))
    assert "X1 (EePorts::ServoHeader): pin 3 (GND) is not wired, but another end carries GND" in text
    assert "has 1 end(s) at EePorts::ServoHeader (boardEnd), 2 connector(s) name it (X1, X2)" in text
    assert "has 1 end(s) at EeCables::ServoPlug (servoEnd), 0 connector(s) name it (none)" in text
    # a loop that shorts two signals of one connector (WireViz `loops`)
    bad3 = yaml.safe_load(yaml.safe_dump(GOOD))
    bad3["connectors"]["X1"]["loops"] = [[1, 3]]
    text = "\n".join(harness.conformance(_h(bad3), m, "h.yml"))
    assert "one conductor joins different nets: GND (X1:3 X2:3), SERVO_PWM (X1:1 X2:1)" in text
    bad2["metadata"]["TraceID"] = "EE-HAR-0042"
    assert any("TraceID EE-HAR-0042 names no cable def" in x for x in harness.conformance(_h(bad2), m, "h.yml"))


def test_wires_by_color_and_label():
    """Wires named by a unique color or a wire label are the wire of that number (as in WireViz);
    a name that maps to no wire is reported, never a new conductor."""
    d = yaml.safe_load(yaml.safe_dump(GOOD))
    d["cables"]["W1"]["wirelabels"] = ["PWM", "RET"]
    d["connections"] = [[{"X1": [1, 3]}, {"W1": ["OG", "RET"]}, {"X2": [1, 3]}]]
    assert harness.conformance(_h(d), _model(), "h.yml") == []
    assert [r[2:4] for r in harness.pin_table(_h(d))] == [("W1:1", "OG"), ("W1:2", "BK")]
    d["connections"] = [[{"X1": 1}, {"W1": 1}], [{"W1": "OG"}, {"X2": 1}], [{"X1": 3}, {"W1": "PK"}, {"X2": 3}]]
    w = harness.wiring(_h(d))
    assert any(set(g) == {("X1", "1"), ("W1", "1"), ("X2", "1")} for g in w.groups)
    assert w.unsupported == ["connection set 3: W1 wire 'PK' is no wire number, unique wire label or unique color "
                             "of the cable (color codes are not read)"]


def test_cable_ends_need_ids_and_two_ends():
    data = json.loads((DOMAIN / "ee-model.json").read_text())
    # the cable def keeps one end: a finding, also when the YAML is fine otherwise
    keep = [x for x in data if x["identity"]["@id"] != "EeCables::ServoCable::servoEnd"]
    m = modelmod.Model(keep)
    good = yaml.safe_load(yaml.safe_dump(GOOD))
    text = "\n".join(harness.conformance(_h(good), m, "h.yml"))
    assert "the cable def EeCables::ServoCable has 1 end(s); a cable has at least two" in text


def test_bom_with_part_data_per_wire():
    d = yaml.safe_load(yaml.safe_dump(GOOD))
    d["cables"]["W1"]["mpn"] = ["A1", "A2"]
    assert harness.bom(_h(d))[0][5] == "A1; A2"


def _repo(tmp_path, data=GOOD, name="servo-cable"):
    root = tmp_path / "ws"
    repo = git_init(root / "r")
    (repo / "checks.yaml").write_text(YAML)
    (repo / "generated").mkdir()
    shutil.copy(DOMAIN / "ee-model.json", repo / "generated" / "model.json")
    if data is not None:
        d = repo / "harness" / name
        d.mkdir(parents=True)
        (d / f"{name}.yml").write_text(yaml.safe_dump(data, sort_keys=False))
    return root, repo


def _run(root, repo, cid, fn):
    (root / "out").mkdir(exist_ok=True)
    ctx = checks.Ctx(Workspace(root), Repo("r", repo, "r"), checkcfg.load(repo / "checks.yaml", root), "local",
                     False, None, root / "out")
    r = checks.Result(cid, cid, level="warning")
    getattr(checks, fn)(ctx, r)
    return r.findings


def test_f1_through_the_check(tmp_path):
    root, repo = _repo(tmp_path)
    assert [x for x in _run(root, repo, "CK-F1", "c_connectors_model") if "harness/" in x] == []
    y = repo / "harness/servo-cable/servo-cable.yml"
    y.write_text(y.read_text().replace("Port: EE-PORT-0010", "Port: EE-PORT-0099"))
    assert any(x.startswith("harness/servo-cable/servo-cable.yml: connector X2: Port EE-PORT-0099")
               for x in _run(root, repo, "CK-F1", "c_connectors_model"))


def test_f7_cables_one_to_one(tmp_path):
    """CK-F7 planted (cables): a cable def without harness, a harness without TraceID, one naming
    no cable def, a wrong folder name, two harnesses for one cable def, a second YAML in a folder."""
    root, repo = _repo(tmp_path)
    f7 = [x for x in _run(root, repo, "CK-F7", "c_ee_one_to_one") if "harness" in x or "Cable" in x]
    assert f7 == []
    shutil.rmtree(repo / "harness/servo-cable")
    assert any("EeCables::ServoCable (EE-HAR-0001): no harness; create harness/servo-cable/servo-cable.yml" in x
               for x in _run(root, repo, "CK-F7", "c_ee_one_to_one"))
    for name, tid in (("servo-cable", "EE-HAR-0001"), ("cable2", "EE-HAR-0001"), ("ghost", "EE-HAR-0042"), ("plain", "")):
        d = repo / "harness" / name
        d.mkdir(parents=True)
        (d / f"{name}.yml").write_text(yaml.safe_dump({"metadata": {"TraceID": tid}} if tid else {"connectors": {}}))
    (repo / "harness/servo-cable/extra.yml").write_text("connectors: {}\n")
    text = "\n".join(_run(root, repo, "CK-F7", "c_ee_one_to_one"))
    assert "EE-HAR-0001): 2 harnesses name it" in text
    assert "harness/cable2/cable2.yml: the cable def ServoCable (EE-HAR-0001) gives the folder name harness/servo-cable/" in text
    assert "harness/ghost/ghost.yml: TraceID EE-HAR-0042 names no cable def" in text
    assert "harness/plain/plain.yml: no metadata TraceID" in text
    assert "harness/servo-cable/extra.yml: not the entry point of its folder" in text


def test_cable_def_without_id():
    data = json.loads((DOMAIN / "ee-model.json").read_text())
    for x in data:
        if x["identity"]["@id"] == "EeCables::ServoCable":
            x["payload"].pop("declaredShortName")
    _, f = harness.cable_defs(modelmod.Model(data))
    assert f == ["model EeCables::ServoCable: a cable def (XdDomain::Cable) without an EE-HAR ID (short name)"]


def test_connects_from_the_cable_ends():
    n = modelmod.to_needs(_model(), "ee")[0]["versions"][""]["needs"]
    assert n["EE-HAR-0001"]["connects"] == ["EE-PORT-0001", "EE-PORT-0010"]
    assert "part_of" not in n["EE-PORT-0010"]                     # a port of an external part


def test_tables():
    h = _h(GOOD)
    assert harness.pin_table(h) == [("X1:1", "SERVO_PWM", "W1:1", "OG", "X2:1", "SERVO_PWM"),
                                    ("X1:3", "GND", "W1:2", "BK", "X2:3", "GND")]
    assert harness.bom(h) == [
        ("W1", "Cable, 2 x 0.14 mm2", "0.3", "m", "Lapp", "49900"),
        ("X1", "Connector, JST XH housing, 3 pins", "1", "", "JST", "XHP-3"),
        ("X2", "Connector, JST XH receptacle, 2 pins", "1", "", "", ""),
    ]
    owners = harness.port_owners(_model())
    assert owners["EE-PORT-0010"] == [("external", "ServoMotor", "")]
    assert ("board", "ControllerBoard", "EE-PCBA-0001") in owners["EE-PORT-0001"]


def test_checks_yaml_key(tmp_path):
    root, repo = _repo(tmp_path)
    assert harness.patterns(checkcfg.load(repo / "checks.yaml", root)) == ["harness/*/*.yml"]


@pytest.mark.tools
def test_cam_runs_wireviz(tmp_path):
    """`curatrix cam`: WireViz as a separate process, output under build/, version as the diagram label."""
    if not shutil.which("dot"):
        pytest.skip("Graphviz dot not installed")
    from conftest import WORKSPACE
    root, repo = _repo(tmp_path)
    (root / ".venv" / "bin").mkdir(parents=True)
    (root / ".venv" / "bin" / "wireviz").symlink_to(WORKSPACE / ".venv" / "bin" / "wireviz")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "h"], check=True)
    ws = Workspace(root)
    cfg = checkcfg.load(repo / "checks.yaml", root)
    rec = harness.run(ws, Repo("r", repo, "r"), cfg)[0]
    assert rec["kind"] == "harness"
    assert rec["version"].startswith("servo-cable/v0.0.0-1-g") and rec["version"].endswith("-preview")
    top = ws.build(cfg.area) / "cam" / "servo-cable" / rec["version"].split("/", 1)[1]
    assert {"servo-cable/servo-cable.svg", "servo-cable/servo-cable.png", "servo-cable/servo-cable.bom.tsv"} <= set(rec["files"])
    assert "v0.0.0" in (top / "servo-cable" / "servo-cable.svg").read_text()
    assert "Lapp" in (top / "servo-cable" / "servo-cable.bom.tsv").read_text()
    assert harness.latest(ws, cfg, "servo-cable")["version"] == rec["version"]
    assert not (repo / "harness/servo-cable/servo-cable.svg").exists()


def test_cam_command_names_a_board_or_a_harness(tmp_path, monkeypatch, capsys):
    """One `cam` command: an unknown name and --update-jobset on a harness are refused before
    any tool runs; a name that is both a board and a harness is refused."""
    from curatrix import cli, eeprojects
    root, repo = _repo(tmp_path)
    ws = Workspace(root)
    monkeypatch.setattr(cli, "_ws", lambda: ws)
    monkeypatch.setattr(cli, "_repo", lambda w, n: Repo("r", repo, "r"))
    assert cli.main(["cam", "r", "nope"]) == 1
    assert "no pcba/ project or harness nope" in capsys.readouterr().err
    assert cli.main(["cam", "r", "servo-cable", "--update-jobset"]) == 1
    assert "--update-jobset applies to pcba/ projects only" in capsys.readouterr().err
    pr = eeprojects.Project("servo-cable", "pcba", repo, repo / "x.kicad_pro", repo / "x.kicad_sch")
    monkeypatch.setattr(eeprojects, "discover", lambda cfg: [pr])
    assert cli.main(["cam", "r", "servo-cable"]) == 1
    assert "both a pcba/ project and a harness" in capsys.readouterr().err
