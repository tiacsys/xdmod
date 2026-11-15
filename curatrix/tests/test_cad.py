import json
import zipfile

from curatrix import cad
from helpers import FIXTURES

KI = FIXTURES / "kicad"


def test_sexpr():
    t = cad.sexpr('(a "b c" (d "e\\"f") g)')
    assert t == ["a", "b c", ["d", 'e"f'], "g"]


def test_kicad_schematic_needs_plain_python():
    needs, findings = cad.kicad_needs(cad.kicad_items(KI / "board.kicad_sch", KI))
    assert findings == []
    assert sorted(needs) == ["EE-CMP-0001", "EE-CMP-0002", "EE-CMP-0003", "EE-PCBA-0001"]
    pcba = needs["EE-PCBA-0001"]                      # from the project's text variables
    assert pcba["type"] == "ee-pcba" and pcba["realizes"] == ["SYS-EL-0003"]
    c1 = needs["EE-CMP-0001"]
    assert c1["satisfies"] == ["EE-REQ-0001", "EE-REQ-0002"] and c1["part_of"] == ["EE-PCBA-0001"]
    sheet = needs["EE-CMP-0002"]                      # one sheet file, two usages (D128)
    assert sheet["status"] == "draft" and sheet["instances"] == ["/joint1/", "/joint2/"]
    assert sheet["title"] == "joint"
    c3 = needs["EE-CMP-0003"]                         # symbol in the reused sheet: per-instance refs
    assert c3["instances"] == ["/joint1/R2", "/joint2/R3"] and c3["configs"] == ["SYS-CFG-0001"]
    assert "R9" not in json.dumps(needs)              # no TraceID: not a need


def test_kicad_netlist_reader_agrees():
    items = cad.kicad_netlist_items(KI / "board.net.xml", "board.kicad_sch")
    needs, _ = cad.kicad_needs(items)
    plain, _ = cad.kicad_needs(cad.kicad_items(KI / "board.kicad_sch", KI))
    assert needs["EE-CMP-0003"]["instances"] == plain["EE-CMP-0003"]["instances"]
    assert needs["EE-CMP-0001"]["satisfies"] == plain["EE-CMP-0001"]["satisfies"]


def test_trace_fields_validation():
    n, f = cad.trace_need({"TraceID": "EE-CMP-1", "Realizes": "SYS-EL-0001"}, "t", "c", "x")
    assert n is None and "not a valid ID" in f[0]
    n, f = cad.trace_need({"TraceID": "EE-CMP-0001", "Realizes": "SYS-EL-0001, bogus", "Status": "gone"}, "t", "c", "x")
    assert n["realizes"] == ["SYS-EL-0001"] and len(f) == 2


def test_freecad_trace_and_needs():
    fc = FIXTURES / "freecad" / "part.FCStd"
    sem = cad.freecad_trace(fc, "parts/part.FCStd")
    assert sem["spreadsheets"] == {"Params": {"link_length": "80 mm"}}
    box = sem["objects"]["Box"]
    assert box["trace"]["TraceID"] == "ME-PART-0001" and box["values"]["Length"] == 10.0
    assert "CreationDate" not in json.dumps(sem) and "Uid" not in sem["document"]   # no noise
    needs, findings = cad.freecad_needs(fc, "parts/part.FCStd")
    assert findings == [] and needs["ME-PART-0001"]["realizes"] == ["SYS-EL-0003"]
    assert needs["ME-PART-0001"]["type"] == "me-part"


def test_freecad_compression_detection(tmp_path):
    fc = FIXTURES / "freecad" / "part.FCStd"
    assert cad.freecad_compressed(fc) == []          # saved with CompressionLevel 0
    bad = tmp_path / "bad.FCStd"
    with zipfile.ZipFile(fc) as src, zipfile.ZipFile(bad, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as dst:
        for i in src.infolist():
            dst.writestr(i.filename, src.read(i.filename))
    assert cad.freecad_compressed(bad)
