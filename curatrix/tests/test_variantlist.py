"""`curatrix variants list` (xdmod#69 finding 9, decision Q14) on the canary fixture
(fixtures/canary/README.md), and the rename of the PLEML rules to `curatrix pleml check`."""
import gzip
import json
import shutil
import zipfile

import pytest

from curatrix import cli, model, variantlist
from helpers import FIXTURES, make_ws

CANARY = FIXTURES / "canary"
CFG, USAGE = "SYS-CFG-0001", "RobArmProduct::Canary::CanaryContext::canaryUnit"


def raw(name):
    return json.loads(gzip.decompress((CANARY / name).read_bytes()))


def load(name, drop_client=None):
    """A fixture model; ``drop_client``: leave out the dependencies from that def."""
    data = [x for x in raw(name) if not (drop_client and x["payload"].get("@type") == "Dependency"
                                         and {"@id": drop_client} in (x["payload"].get("client") or []))]
    return model.Model(data)


def board(tmp_path, sch_alt=None, pcb_alt=None):
    """A copy of the canary board; ``sch_alt`` / ``pcb_alt`` replace R1's `alt` block in the
    schematic / on the board."""
    d = tmp_path / "pcba" / "canary-board"
    shutil.copytree(CANARY / "pcba" / "canary-board", d)
    for f, new, old in ((d / "canary-board.kicad_sch", sch_alt, '(name "alt")\n\t\t\t\t\t\t(dnp yes)'),
                        (d / "canary-board.kicad_pcb", pcb_alt, "(name alt)\n\t\t\t(dnp yes)")):
        if new is not None:
            t = f.read_text()
            assert old in t, f
            f.write_text(t.replace(old, new, 1))
    return d / "canary-board.kicad_sch"


@pytest.fixture(scope="module")
def canary():
    return variantlist.listing("ee", load("ee-model.json.gz"), [load("sys-model.json.gz")],
                               [CANARY / "pcba/canary-board/canary-board.kicad_sch"])


@pytest.mark.parametrize("name,model_def,description,differences,serves", [
    ("default", "RobArmEe::Canary::CanaryBoardDefault", "R1 fitted", [], [[CFG, USAGE]]),
    ("alt", "RobArmEe::Canary::CanaryBoardAlt", "R1 not fitted", ["R1 DNP"], []),
])
def test_canary_variants(canary, name, model_def, description, differences, serves):
    v = {e.name: e for e in canary.variants}[name]
    assert (v.owner, v.owner_def, v.kind) == ("EE-PCBA-0001", "RobArmEe::Canary::CanaryBoard", "board")
    assert (v.model_def, v.description, v.differences, v.serves) == (model_def, description, differences, serves)
    assert v.cad_file.endswith("canary-board.kicad_pro")
    assert v.serves_none == (not serves)


def test_canary_order_text_and_json(canary):
    assert [e.name for e in canary.variants] == ["default", "alt"]      # serving variants first
    assert canary.unserved == []
    t = variantlist.text([canary])
    assert "SYS-CFG-0001 canaryUnit" in t and "none (serves no pair)" in t and "R1 DNP" in t
    j = canary.to_json()
    assert [(v["name"], v["serves_none"]) for v in j["variants"]] == [("default", False), ("alt", True)]


@pytest.mark.parametrize("sch_alt,pcb_alt,want", [
    (None, None, ["R1 DNP"]),
    # a variant that changes a part's value (and keeps it fitted, on the board too)
    ('(name "alt")(field (name "Value") (value "4k7"))', "(name alt)", ["R1 value 4k7"]),
    # the schematic and the board disagree
    ('(name "alt")', None, ["R1 fitted (board: DNP)"]),
    (None, "(name alt)", ["R1 DNP (board: fitted)"]),
])
def test_alt_differences(tmp_path, sch_alt, pcb_alt, want):
    L = variantlist.listing("ee", load("ee-model.json.gz"), [load("sys-model.json.gz")],
                            [board(tmp_path, sch_alt, pcb_alt)])
    assert {e.name: e.differences for e in L.variants}["alt"] == want


def test_pair_no_variant_serves():
    """Without default's dependency, no variant serves (SYS-CFG-0001, canaryUnit): listed."""
    L = variantlist.listing("ee", load("ee-model.json.gz", "RobArmEe::Canary::CanaryBoardDefault"),
                            [load("sys-model.json.gz")], [CANARY / "pcba/canary-board/canary-board.kicad_sch"])
    assert L.unserved == [[CFG, USAGE, "EE-PCBA-0001"]]
    assert all(e.serves_none for e in L.variants)
    assert "no variant of EE-PCBA-0001 serves canaryUnit in SYS-CFG-0001" in variantlist.text([L])


@pytest.mark.parametrize("upstream,kicad,want", [
    # no upstream model: the pairs as the dependencies declare them, and a note
    (None, True, {"default": ([[CFG, USAGE]], []), "alt": ([], ["R1 DNP"])}),
    # no KiCad project: the model's variants are listed, marked as not in CAD
    ([], False, {"default": ([[CFG, USAGE]], ["not in CAD"]), "alt": ([], ["not in CAD"])}),
])
def test_missing_levels(upstream, kicad, want):
    roots = [CANARY / "pcba/canary-board/canary-board.kicad_sch"] if kicad else []
    L = variantlist.listing("ee", load("ee-model.json.gz"), upstream, roots)
    assert {e.name: (e.serves, e.differences) for e in L.variants} == want
    assert [e.name for e in L.variants] == ["default", "alt"]          # also without an upstream model
    assert any("no upstream model" in n for n in L.notes)


def test_kicad_only_variant(tmp_path):
    """A variant only KiCad has (no model def) is listed, serving nothing."""
    d = tmp_path / "pcba" / "canary-board"
    shutil.copytree(CANARY / "pcba" / "canary-board", d)
    pro = d / "canary-board.kicad_pro"
    p = json.loads(pro.read_text())
    p["schematic"]["variants"].append({"name": "extra", "description": "new"})
    pro.write_text(json.dumps(p))
    L = variantlist.listing("ee", load("ee-model.json.gz"), [load("sys-model.json.gz")], [d / "canary-board.kicad_sch"])
    e = {e.name: e for e in L.variants}["extra"]
    assert (e.model_def, e.description, e.serves, e.differences) == ("", "new", [], [])
    assert [x.name for x in L.variants] == ["default", "alt", "extra"]


def test_freecad_configuration_rows(tmp_path):
    doc = ('<Document><Objects><Object type="Spreadsheet::Sheet" name="Params"/></Objects><ObjectData>'
           '<Object name="Params"><Properties>'
           '<Property name="Variant" type="App::PropertyEnumeration"><Integer value="0"/></Property>'
           '<Property name="cells" type="Spreadsheet::PropertySheet"><Cells>'
           '<Cell address="A2" content="short"/><Cell address="A3" content="long"/>'
           '<Cell address="B1" content="=.B2" alias="length"/><Cell address="B2" content="=100 mm"/>'
           '<Cell address="B3" content="=180 mm"/>'
           '</Cells></Property></Properties></Object></ObjectData></Document>')
    f = tmp_path / "skeleton.FCStd"
    with zipfile.ZipFile(f, "w") as z:
        z.writestr("Document.xml", doc)
    assert variantlist.freecad_rows(f) == {"short": ["length=100 mm"], "long": ["length=180 mm"]}


# ------------------------------------------------------------------ assemblies
def _fcstd(path, objects):
    """A minimal .FCStd: {object name: (type, [property xml])}."""
    path.parent.mkdir(parents=True, exist_ok=True)
    objs = "".join(f'<Object type="{t}" name="{n}"/>' for n, (t, _) in objects.items())
    data = "".join(f'<Object name="{n}"><Properties>{"".join(ps)}</Properties></Object>'
                   for n, (_, ps) in objects.items())
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("Document.xml", f'<?xml version="1.0"?><Document SchemaVersion="4"><Properties/>'
                                   f'<Objects>{objs}</Objects><ObjectData>{data}</ObjectData></Document>')
    return path


def _s(name, value):
    return f'<Property name="{name}" type="App::PropertyString"><String value="{value}"/></Property>'


SHEET = ('<Property name="Variant" type="App::PropertyEnumeration"><Integer value="0"/></Property>'
         '<Property name="cells" type="Spreadsheet::PropertySheet"><Cells>'
         '<Cell address="A2" content="bench"/><Cell address="A3" content="printed"/>'
         '<Cell address="B1" content="=.B2" alias="height"/><Cell address="B2" content="=40 mm"/>'
         '<Cell address="B3" content="=60 mm"/></Cells></Property>')


@pytest.mark.parametrize("with_table,configs,want_rows,want_note", [
    # a configuration table: one variant per row, its parameters, and the links with Configs
    (True, "SYS-CFG-0002", {"bench": ["height=40 mm", "link Rig absent (Configs SYS-CFG-0002)"],
                            "printed": ["height=60 mm", "link Rig absent (Configs SYS-CFG-0002)"]}, None),
    # no table: no variant, and a note that names the links with Configs
    (False, "SYS-CFG-0002", {}, "ME-ASM-0007: no variant (no DomainVariant def, no configuration table; "
                                "links with Configs: Rig (SYS-CFG-0002))"),
    (False, "", {}, "no link with Configs"),
])
def test_assembly(tmp_path, with_table, configs, want_rows, want_note):
    objs = {"Asm": ("App::Part", [_s("TraceID", "ME-ASM-0007")]),
            "Rig": ("App::Link", [_s("Configs", configs)] if configs else []),
            "Plain": ("App::Link", [])}
    if with_table:
        objs["Params"] = ("Spreadsheet::Sheet", [SHEET])
    f = _fcstd(tmp_path / "assemblies" / "arm" / "arm.FCStd", objs)
    L = variantlist.listing("me", None, None, [], [f])
    assert {e.name: e.differences for e in L.variants} == want_rows
    assert all(e.kind == "assembly" and e.serves_none for e in L.variants)
    if want_note:
        assert any(want_note in n for n in L.notes), L.notes


# ------------------------------------------------------------------ CLI
@pytest.fixture
def ws(tmp_path, monkeypatch):
    root = make_ws(tmp_path, monkeypatch)
    repo = root / "ee"
    shutil.copytree(CANARY / "pcba", repo / "pcba")
    (repo / "generated").mkdir()
    (repo / "generated" / "model.json").write_bytes(gzip.decompress((CANARY / "ee-model.json.gz").read_bytes()))
    (root / "sys" / "generated").mkdir(parents=True)
    (root / "sys" / "generated" / "model.json").write_bytes(gzip.decompress((CANARY / "sys-model.json.gz").read_bytes()))
    (repo / "checks.yaml").write_text(
        "version: 1\nmodel: {files: [model/*.sysml], json: generated/model.json, upstream: '{ws}/sys/generated/model.json'}\n"
        "cad: {projects: ['pcba/*/*.kicad_pro']}\n")
    monkeypatch.chdir(root)
    return root


@pytest.mark.parametrize("argv", [["variants", "list", "ee", "--json"], ["variants", "list", "--json"]])
def test_cli_list(ws, capsys, argv):
    assert cli.main(argv) == 0
    out = json.loads(capsys.readouterr().out)
    assert [r["repo"] for r in out["repos"]] == ["ee"]                 # `sys` has no variants
    assert [(v["name"], v["serves"]) for v in out["repos"][0]["variants"]] == [("default", [[CFG, USAGE]]), ("alt", [])]


@pytest.mark.parametrize("argv,warns", [
    (["pleml", "check", "ee"], False),
    (["variants", "ee"], True),            # the old name, one release
])
def test_pleml_check_and_old_name(ws, capsys, argv, warns):
    assert cli.main(argv) == 0
    o = capsys.readouterr()
    assert "variant-check: OK" in o.out
    assert ("deprecated" in o.err and "curatrix pleml check" in o.err) == warns


def test_old_name_rejects_json(ws):
    with pytest.raises(SystemExit, match="--json belongs to"):
        cli.main(["variants", "ee", "--json"])


def test_list_uses_the_current_repo(ws, monkeypatch, capsys):
    monkeypatch.chdir(ws / "ee" / "pcba")
    assert cli.main(["variants", "list", "--json"]) == 0
    assert [r["repo"] for r in json.loads(capsys.readouterr().out)["repos"]] == ["ee"]
