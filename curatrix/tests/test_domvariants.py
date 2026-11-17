"""Variants across levels (XD-ADR-0136, CK-B8): model reader, computed table, CAD and Zephyr sides.
The fixture is curatrix/tests/fixtures/sysml/domain/c_variants.sysml (Pilot output in ee-model.json)."""
import json
import zipfile

from helpers import FIXTURES

from curatrix import domvariants as dv
from curatrix import model

DOMAIN = FIXTURES / "sysml" / "domain"


def models():
    return model.Model.load(DOMAIN / "ee-model.json"), [model.Model.load(DOMAIN / "sys-model.json")]


def project(tmp_path, name, trace_id, variants):
    d = tmp_path / "pcba" / name
    d.mkdir(parents=True)
    (d / f"{name}.kicad_sch").write_text("(kicad_sch (version 20260306))\n")
    (d / f"{name}.kicad_pro").write_text(json.dumps({"text_variables": {"TraceID": trace_id},
                                                      "schematic": {"variants": [{"name": v} for v in variants]}}))
    return d / f"{name}.kicad_sch"


def test_variants_from_the_model():
    vs, findings = dv.variants(models()[0])
    by = {v.qn: v for v in vs}
    std = by["EeVariants::CtrlStd"]
    assert (std.name, std.owner) == ("std", "EE-PCBA-0001")
    # two dependencies: their pairs are not crossed ((Full, ctrlB) is CtrlFast's only)
    assert std.pairs == {("SYS-CFG-0001", "Sys::Arm::ctrlA"), ("SYS-CFG-0001", "Sys::Arm::ctrlB"),
                         ("SYS-CFG-0002", "Sys::Arm::ctrlA")}
    assert findings == ["EeVariants::ServoC: no variantName"]


def test_table_is_computed_per_configuration_and_usage():
    m, up = models()
    _, rows = dv.check(m, up)
    t = {(r.config, r.usage, r.owner): r.variants for r in rows}
    assert t[("SYS-CFG-0002", "Sys::Arm::ctrlB", "EE-PCBA-0001")] == ["fast"]
    assert t[("SYS-CFG-0001", "Sys::Arm::servo1", "EE-PCBA-0006")] == ["a", "b"]
    assert t[("SYS-CFG-0002", "Sys::Arm::servo1", "EE-PCBA-0006")] == []     # Servo: in every configuration
    assert "| SYS-CFG-0001 | Sys::Arm::ctrlA | EE-PCBA-0001 | std |" in dv.table_markdown(rows)


def test_planted_errors_and_clean_board(tmp_path):
    m, up = models()
    roots = [project(tmp_path, "controller-board", "EE-PCBA-0001", ["std", "fast"]),
             project(tmp_path, "servo-board", "EE-PCBA-0006", ["a", "b"])]
    f, _ = dv.check(m, up, roots)
    assert not [x for x in f if "Ctrl" in x or "ControllerBoard" in x], f        # the clean board
    for e in ("EeBoards::ServoBoard: 3 variants; at most 2",
              "EeVariants::ServoC: no variantName",
              "EeVariants::ServoC: Sys::Arm::ctrlA is not a usage of a system def that EE-PCBA-0006 realizes",
              "EeBoards::ServoBoard: 2 variants (a, b) for usage Sys::Arm::servo1 in configuration SYS-CFG-0001",
              "EeBoards::ServoBoard: no variant for usage Sys::Arm::servo1 in configuration SYS-CFG-0002"):
        assert any(x.startswith(e) for x in f), (e, f)


def test_variant_missing_in_kicad(tmp_path):
    m, up = models()
    f, _ = dv.check(m, up, [project(tmp_path, "controller-board", "EE-PCBA-0001", ["std"])])
    assert any(x.startswith("EeVariants::CtrlFast: variant 'fast' is not in controller-board.kicad_pro") for x in f), f
    f, _ = dv.check(m, up, [])
    assert any("no KiCad project names EE-PCBA-0001" in x for x in f), f


def test_zephyr_board_variants_by_name(tmp_path):
    m, up = models()
    roots = [project(tmp_path, "controller-board", "EE-PCBA-0001", ["std", "fast"])]
    b = tmp_path / "boards" / "acme" / "controller_board"
    b.mkdir(parents=True)
    (b / "board.yml").write_text("board:\n  name: controller_board\n  vendor: acme\n  socs:\n"
                                 "    - name: stm32g474xx\n      variants:\n        - name: fast\n        - name: turbo\n")
    f, _ = dv.check(m, up, roots, zephyr_roots=[tmp_path / "boards"])
    zf = [x for x in f if x.startswith("Zephyr")]
    assert zf == ["Zephyr board controller_board: variant 'turbo' is no variant of EeBoards::ControllerBoard (fast, std)"]


def test_freecad_configuration_table(tmp_path):
    doc = ('<Document><Objects><Object type="Spreadsheet::Sheet" name="Params"/></Objects><ObjectData>'
           '<Object name="Params"><Properties>'
           '<Property name="Variant" type="App::PropertyEnumeration"><Integer value="0"/></Property>'
           '<Property name="cells" type="Spreadsheet::PropertySheet"><Cells>'
           '<Cell address="A2" content="short"/><Cell address="A3" content="long"/>'
           '<Cell address="B1" content="=.B2" alias="length"/><Cell address="B2" content="=100 mm"/>'
           '</Cells></Property></Properties></Object></ObjectData></Document>')
    f = tmp_path / "skeleton.FCStd"
    with zipfile.ZipFile(f, "w") as z:
        z.writestr("Document.xml", doc)
    assert dv.freecad_variants(f) == ["short", "long"]


def test_pairs_per_realized_def():
    """ComboBoard2 realizes Controller (Basic, Full) and Driver (Basic only): drv1 needs a variant
    in Basic, not in Full (no cross product over the realized defs)."""
    m, up = models()
    f, rows = dv.check(m, up)
    t = {(r.config, r.usage) for r in rows if r.owner == "EE-PCBA-0005"}
    assert ("SYS-CFG-0001", "Sys::Arm::drv1") in t and ("SYS-CFG-0002", "Sys::Arm::drv1") not in t
    assert not [x for x in f if "ComboX" in x and "KiCad" not in x], f


def test_dependency_without_configuration_is_a_finding():
    m, up = models()
    f, _ = dv.check(m, up)
    assert "EeVariants::ServoA: a dependency names usages but no configuration (SYS-CFG)" in f, f


def test_upstream_without_configurations_is_a_finding():
    m, _ = models()
    data = json.loads((DOMAIN / "sys-model.json").read_text())
    for x in data:
        if str(x["payload"].get("declaredShortName", "")).startswith("SYS-CFG-"):
            del x["payload"]["declaredShortName"]
    f, rows = dv.check(m, [model.Model(data)])
    assert rows == [] and any(x.startswith("the upstream model has no configuration") for x in f), f


def test_unused_variant_is_checked_against_kicad(tmp_path):
    """A variant that serves no pair is not reported as unused, but it must be in KiCad."""
    data = json.loads((DOMAIN / "ee-model.json").read_text())
    data = [x for x in data if not (x["payload"].get("@type") == "Dependency" and
                                    x["payload"].get("client") == [{"@id": "EeVariants::CtrlFast"}])]
    m, up = model.Model(data), models()[1]
    f, _ = dv.check(m, up, [project(tmp_path, "controller-board", "EE-PCBA-0001", ["std"])])
    assert any(x.startswith("EeVariants::CtrlFast: variant 'fast' is not in") for x in f), f


def test_two_projects_for_one_board(tmp_path):
    m, up = models()
    roots = [project(tmp_path, "a-board", "EE-PCBA-0001", ["std", "fast"]),
             project(tmp_path, "b-board", "EE-PCBA-0001", ["std", "fast"])]
    f, _ = dv.check(m, up, roots)
    assert any("more than one KiCad project names EE-PCBA-0001" in x for x in f), f
