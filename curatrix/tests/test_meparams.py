"""Model-driven FreeCAD parameters (task 5.24): parameters from the ME model, cell values,
placements, CK-F3."""
import json
import math

import pytest

from curatrix import meparams, model as modelmod
from test_meassemblies import _prop, _run, fcstd
from helpers import git_init


class M:
    """A tiny model JSON builder in the Pilot's shape (owned relationships, values as expressions)."""

    def __init__(self):
        self.data = []
        self.n = 0

    def el(self, i, payload):
        payload["@id"] = i
        payload.setdefault("ownedRelationship", [])
        self.data.append({"identity": {"@id": i}, "payload": payload})
        return payload

    def own(self, owner, child, kind="FeatureMembership"):
        self.n += 1
        rid = f"{owner['@id']}/r{self.n}"
        self.el(rid, {"@type": kind, "ownedRelatedElement": [{"@id": child["@id"]}]})
        owner["ownedRelationship"].append({"@id": rid})
        return child

    def attr(self, owner, name, value=None, unit=None, tol=None):
        a = self.own(owner, self.el(f"{owner['@id']}::{name}", {"@type": "AttributeUsage", "name": name}))
        if value is not None:
            if unit is None:
                self.own(a, self.el(f"{a['@id']}/v", {"@type": "LiteralRational", "value": value}), "FeatureValue")
            else:
                op = self.own(a, self.el(f"{a['@id']}/v", {"@type": "OperatorExpression", "operator": "["}), "FeatureValue")
                self.own(op, self.el(f"{a['@id']}/v/x", {"@type": "LiteralInteger", "value": value}))
                self.own(op, self.el(f"{a['@id']}/v/u", {"@type": "FeatureReferenceExpression",
                                                          "referent": {"@id": f"lib:SI::{unit}"}}))
        if tol is not None:
            md = self.el(f"{a['@id']}/tol", {"@type": "MetadataUsage", "annotatedElement": [{"@id": a["@id"]}],
                                              "metadataDefinition": {"@id": "lib:XdDomain::ModelMatchTolerance"}})
            self.own(a, md, "OwningMembership")
            self.own(md, self.el(f"{md['@id']}/v", {"@type": "LiteralRational", "value": tol}))
        return a


def canary_model(x=10, length=20, extra=0):
    b = M()
    b.el("lib:XdDomain::Assembly", {"@type": "PartDefinition", "name": "Assembly",
                                    "qualifiedName": "XdDomain::Assembly", "isLibraryElement": True})
    b.el("lib:XdDomain::ModelMatchTolerance", {"@type": "MetadataDefinition", "qualifiedName": "XdDomain::ModelMatchTolerance",
                                     "isLibraryElement": True})
    part = b.el("Me::CanaryPart", {"@type": "PartDefinition", "name": "CanaryPart", "qualifiedName": "Me::CanaryPart",
                                   "declaredShortName": "ME-PART-0001"})
    mount = b.el("Me::CanaryMount", {"@type": "PortDefinition", "name": "CanaryMount", "qualifiedName": "Me::CanaryMount",
                                     "declaredShortName": "ME-PORT-0001"})
    b.attr(mount, "holeSpacing", 12, "millimetre")
    asm = b.el("Me::CanaryAssembly", {"@type": "PartDefinition", "name": "CanaryAssembly",
                                      "qualifiedName": "Me::CanaryAssembly", "declaredShortName": "ME-ASM-0001"})
    sub = b.el("Me::CanaryAssembly/sub", {"@type": "Subclassification", "superclassifier": {"@id": "lib:XdDomain::Assembly"}})
    asm["ownedRelationship"].append({"@id": sub["@id"]})
    pu = b.own(asm, b.el("Me::CanaryAssembly::canaryPart", {"@type": "PartUsage", "name": "canaryPart",
                                                            "type": [{"@id": part["@id"]}]}))
    b.attr(pu, "length", length, "millimetre", tol=0.5)
    mu = b.own(asm, b.el("Me::CanaryAssembly::mount", {"@type": "PortUsage", "name": "mount",
                                                       "type": [{"@id": mount["@id"]}]}))
    b.attr(mu, "x", x, "millimetre")
    b.attr(mu, "yaw", 90, "degree")
    for i in range(extra):
        b.attr(mu, f"p{i}", i)
    return b.data


def test_model_params():
    m = modelmod.Model(canary_model())
    asm = m.get("Me::CanaryAssembly")
    params, findings = meparams.model_params(m, asm)
    assert not findings
    got = {p.alias: (p.text, p.kind, p.tol, p.port) for p in params}
    assert got == {"canaryPart_length": ("20 mm", "length", 0.5, None),
                   "mount_holeSpacing": ("12 mm", "length", 0.001, "ME-PORT-0001"),
                   "mount_x": ("10 mm", "length", 0.001, "ME-PORT-0001"),
                   "mount_yaw": ("90 deg", "angle", 0.001, "ME-PORT-0001")}
    _, findings = meparams.model_params(modelmod.Model(canary_model(extra=7)), asm)
    assert any("at most 10" in f for f in findings), findings


def test_cell_values_and_placements():
    assert meparams.cell_value("12 mm") == (12.0, "length")
    assert meparams.cell_value("=1.5 cm") == (15.0, "length")
    assert meparams.cell_value("90 °") == (90.0, "angle")
    assert meparams.cell_value("3") == (3.0, "number")
    assert meparams.cell_value("'mount_x") is None
    s = math.sqrt(0.5)
    pl = meparams.compose({"Px": 1.0, "Q2": s, "Q3": s}, {"Px": 10.0})      # 90 deg about z, then x = 10
    v = meparams.placement_values(pl)
    assert round(v["x"], 6) == 1.0 and round(v["y"], 6) == 10.0 and round(v["yaw"], 6) == 90.0


def _repo(tmp_path, model):
    root = tmp_path / "ws"
    repo = git_init(root / "r")
    (repo / "checks.yaml").write_text('version: 1\ncad: {freecad: ["assemblies/**/*.FCStd"]}\n'
                                      'model: {files: [model/*.sysml]}\n')
    (repo / "generated").mkdir()
    (repo / "generated/model.json").write_text(json.dumps(model))
    return root, repo


def _skeleton(repo, cells: dict[str, str], lcs_x=10.0, port="ME-PORT-0001"):
    d = repo / "assemblies/canary-assembly"
    s = math.sqrt(0.5)
    cell_xml = "".join(f'<Cell address="B{i}" content="{v}" alias="{a}"/>' for i, (a, v) in enumerate(cells.items(), 1))
    lcs = (f'<Property name="Placement" type="App::PropertyPlacement"><PropertyPlacement Px="{lcs_x}" Py="0" Pz="0" '
           f'Q0="0" Q1="0" Q2="{s}" Q3="{s}"/></Property>')
    fcstd(d / "canary-assembly-skeleton.FCStd", {
        "Params": ("Spreadsheet::Sheet", [f'<Property name="cells" type="Spreadsheet::PropertySheet"><Cells>{cell_xml}'
                                          f'</Cells></Property>']),
        "LCS_mount": ("Part::LocalCoordinateSystem", [lcs, _prop("Port", port, group="Trace")])})
    fcstd(d / "canary-assembly.FCStd", {"Assembly": ("Assembly::AssemblyObject", [_prop("TraceID", "ME-ASM-0001", group="Trace")])})


GOOD = {"canaryPart_length": "20.3 mm", "mount_holeSpacing": "12 mm", "mount_x": "10 mm", "mount_yaw": "90 °"}


def test_f3_freecad_params(tmp_path):
    root, repo = _repo(tmp_path, canary_model())
    _skeleton(repo, GOOD)
    assert _run(root, repo, "CK-F3", "c_freecad_params") == []        # 20.3 within the tolerance 0.5
    # planted: the model moved the mount and changed the length; Params holds an unknown alias
    (repo / "generated/model.json").write_text(json.dumps(canary_model(x=11, length=24)))
    _skeleton(repo, dict(GOOD, stray_alias="1 mm"))
    f = _run(root, repo, "CK-F3", "c_freecad_params")
    assert "assemblies/canary-assembly/canary-assembly-skeleton.FCStd: Params.mount_x = 10 mm, the model has 11 mm (tolerance 0.001 mm)" in f, f
    assert any("Params.canaryPart_length = 20.3 mm, the model has 24 mm" in x for x in f), f
    assert any("LCS_mount.x = 10 mm, the model has 11 mm" in x for x in f), f
    assert any("Params.stray_alias is no attribute" in x for x in f), f


def test_f3_missing_alias_and_lcs(tmp_path):
    root, repo = _repo(tmp_path, canary_model())
    _skeleton(repo, {k: v for k, v in GOOD.items() if k != "mount_x"}, port="ME-PORT-0009")
    f = _run(root, repo, "CK-F3", "c_freecad_params")
    assert any("Params has no alias mount_x" in x and "gen freecad-params" in x for x in f), f
    assert any("Port ME-PORT-0009, which is no port" in x for x in f), f
    assert any("no LCS with Port = ME-PORT-0001 for the port mount" in x for x in f), f


def test_tolerance_in_the_attributes_own_unit():
    b = M()
    b.el("lib:XdDomain::ModelMatchTolerance", {"@type": "MetadataDefinition",
                                               "qualifiedName": "XdDomain::ModelMatchTolerance", "isLibraryElement": True})
    asm = b.el("Me::A", {"@type": "PartDefinition", "name": "A", "qualifiedName": "Me::A"})
    pu = b.own(asm, b.el("Me::A::arm", {"@type": "PartUsage", "name": "arm"}))
    b.attr(pu, "length", 2, "metre", tol=0.001)        # 1 mm
    b.attr(pu, "tilt", 1, "radian", tol=0.01)          # 0.573 deg
    m = modelmod.Model(b.data)
    params, _ = meparams.model_params(m, m.get("Me::A"))
    got = {p.alias: (round(p.value, 4), round(p.tol, 4)) for p in params}
    assert got == {"arm_length": (2000.0, 1.0), "arm_tilt": (57.2958, 0.573)}, got
