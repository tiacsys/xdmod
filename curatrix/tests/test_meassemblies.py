"""FreeCAD assemblies of an ME repo (task 5.23): the semantic-JSON additions, CK-F14 (1:1 with the
ME model, skeleton, no reference to a top document), CK-F15 (link counts), `curatrix new asm`."""
import json
import zipfile

import pytest

from curatrix import cad, checkcfg, checks, meassemblies, model as modelmod, newasm
from curatrix.ws import Repo, Workspace
from helpers import git_init

CFG = 'cad: {freecad: ["parts/*.FCStd", "assemblies/**/*.FCStd"]}\nmodel: {files: [model/*.sysml], upstream: up.json}\n'


def _prop(name, value, ptype="App::PropertyString", group=None):
    g = f' group="{group}"' if group else ""
    if ptype == "App::PropertyXLink":
        file, obj = value
        inner = f'<XLink file="{file}" stamp="2026-11-17T00:00:00+01:00" name="{obj}"/>'
    else:
        inner = f'<String value="{value}"/>'
    return f'<Property name="{name}" type="{ptype}"{g}>{inner}</Property>'


def fcstd(path, objects: dict[str, tuple[str, list[str]]]):
    """A minimal .FCStd: {object name: (type, [property xml])}."""
    path.parent.mkdir(parents=True, exist_ok=True)
    objs = "".join(f'<Object type="{t}" name="{n}"/>' for n, (t, _) in objects.items())
    data = "".join(f'<Object name="{n}"><Properties>{"".join(ps)}</Properties></Object>'
                   for n, (_, ps) in objects.items())
    xml = (f'<?xml version="1.0"?><Document SchemaVersion="4"><Properties/><Objects>{objs}</Objects>'
           f'<ObjectData>{data}</ObjectData></Document>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_STORED) as z:
        z.writestr("Document.xml", xml)
    return path


def _rel(i, kind, src, rel_id=None):
    return {"identity": {"@id": rel_id or f"{src}/r{i}"}, "payload": {"@type": kind}}


def _model(defs, upstream=False):
    """A tiny model JSON. defs: {name: (short ID, [supers], [(usage, def name, multiplicity)])}."""
    pkg = "Up" if upstream else "Me"
    data = [{"identity": {"@id": pkg}, "payload": {"@type": "Package", "name": pkg, "qualifiedName": pkg}}]
    libs = sorted({s for _, sups, _ in defs.values() for s in sups if "::" in s})
    for s in libs:
        data.append({"identity": {"@id": f"lib:{s}"}, "payload": {
            "@type": "PartDefinition", "name": s.split("::")[-1], "qualifiedName": s, "isLibraryElement": True}})
    for name, (sid, sups, uses) in defs.items():
        qn = f"{pkg}::{name}"
        rels = []
        for i, s in enumerate(sups):
            target = f"lib:{s}" if "::" in s else f"{pkg}::{s}"
            rid = f"{qn}/sub{i}"
            rels.append({"@id": rid})
            data.append({"identity": {"@id": rid}, "payload": {
                "@type": "Subclassification", "superclassifier": {"@id": target}, "subclassifier": {"@id": qn}}})
        for i, (u, t, n) in enumerate(uses):
            rid, uid = f"{qn}/m{i}", f"{qn}::{u}"
            rels.append({"@id": rid})
            data.append({"identity": {"@id": rid}, "payload": {"@type": "FeatureMembership",
                                                               "ownedRelatedElement": [{"@id": uid}]}})
            up = {"@type": "PartUsage", "name": u, "qualifiedName": uid, "type": [{"@id": f"{pkg}::{t}"}],
                  "ownedRelationship": []}
            if n != 1:
                up["ownedRelationship"] = [{"@id": f"{uid}/mr"}]
                data.append({"identity": {"@id": f"{uid}/mr"}, "payload": {
                    "@type": "OwningMembership", "ownedRelatedElement": [{"@id": f"{uid}/mult"}]}})
                data.append({"identity": {"@id": f"{uid}/mult"}, "payload": {
                    "@type": "MultiplicityRange", "ownedRelationship": [{"@id": f"{uid}/mb"}]}})
                data.append({"identity": {"@id": f"{uid}/mb"}, "payload": {
                    "@type": "OwningMembership", "ownedRelatedElement": [{"@id": f"{uid}/lit"}]}})
                data.append({"identity": {"@id": f"{uid}/lit"}, "payload": {"@type": "LiteralInteger", "value": n}})
            data.append({"identity": {"@id": uid}, "payload": up})
        p = {"@type": "PartDefinition", "name": name, "qualifiedName": qn, "ownedRelationship": rels}
        if sid:
            p["declaredShortName"] = sid
        data.append({"identity": {"@id": qn}, "payload": p})
    for x in data:
        x["payload"]["@id"] = x["identity"]["@id"]
    return data


ME = {"CanaryPart": ("ME-PART-0001", [], []),
      "Gripper": ("ME-ASM-0002", ["XdDomain::Assembly"], []),
      "CanaryAssembly": ("ME-ASM-0001", ["Up::Unit", "XdDomain::Assembly"],
                         [("canaryPart", "CanaryPart", 1)])}
UP = {"Finger": ("SYS-EL-0002", [], []),
      "Unit": ("SYS-EL-0001", [], [("finger", "Finger", 2)])}


def _repo(tmp_path, me=ME, up=UP):
    root = tmp_path / "ws"
    repo = git_init(root / "r")
    (repo / "checks.yaml").write_text("version: 1\n" + CFG)
    (repo / "generated").mkdir()
    (repo / "generated/model.json").write_text(json.dumps(_model(me)))
    (repo / "up.json").write_text(json.dumps(_model(up, upstream=True)))
    fcstd(repo / "parts/canary-part.FCStd", {"CanaryBlock": ("Part::Box", [_prop("TraceID", "ME-PART-0001", group="Trace")])})
    return root, repo


def _assembly(repo, name="canary-assembly", tid="ME-ASM-0001", links=(("../../parts/canary-part.FCStd", "CanaryBlock"),),
              skeleton=True):
    d = repo / "assemblies" / name
    if skeleton:
        fcstd(d / f"{name}-skeleton.FCStd", {"Skeleton": ("App::Part", [])})
    objs = {"Assembly": ("Assembly::AssemblyObject", [_prop("TraceID", tid, group="Trace")] if tid else []),
            "Skeleton": ("App::Link", [_prop("LinkedObject", (f"{name}-skeleton.FCStd", "Skeleton"), "App::PropertyXLink")])}
    for i, (f, o) in enumerate(links):
        objs[f"Link{i}"] = ("App::Link", [_prop("LinkedObject", (f, o), "App::PropertyXLink")])
    return fcstd(d / f"{name}.FCStd", objs)


def _run(root, repo, cid, fn):
    (root / "out").mkdir(exist_ok=True)
    ctx = checks.Ctx(Workspace(root), Repo("r", repo, "r"), checkcfg.load(repo / "checks.yaml", root), "local",
                     False, None, root / "out")
    r = checks.Result(cid, cid, level="warning")
    getattr(checks, fn)(ctx, r)
    return r.findings


def test_semantic_json_links_expressions_constraints_port(tmp_path):
    f = fcstd(tmp_path / "a.FCStd", {
        "L": ("App::Link", [_prop("LinkedObject", ("../parts/p.FCStd", "Body"), "App::PropertyXLink")]),
        "LCS": ("Part::LocalCoordinateSystem", [_prop("Port", "ME-PORT-0001", group="Trace")])})
    sem = cad.freecad_trace(f, "a.FCStd")
    assert sem["objects"]["L"]["links"] == {"LinkedObject": [{"file": "../parts/p.FCStd", "object": "Body"}]}
    assert sem["objects"]["LCS"]["trace"] == {"Port": "ME-PORT-0001"}
    xml = ('<Document><ObjectData><Object name="S"><Properties>'
           '<Property name="Constraints" type="Sketcher::PropertyConstraintList"><ConstraintList count="2">'
           '<Constrain Name="partLength" Type="6" Value="24.0"/><Constrain Name="" Type="1" Value="0"/>'
           '</ConstraintList></Property>'
           '<Property name="ExpressionEngine" type="App::PropertyExpressionEngine"><ExpressionEngine count="1">'
           '<Expression path=".Constraints.partLength" expression="Params.canaryPart_length"/></ExpressionEngine>'
           '</Property></Properties></Object></ObjectData><Objects><Object type="Sketcher::SketchObject" name="S"/>'
           '</Objects></Document>')
    g = tmp_path / "s.FCStd"
    with zipfile.ZipFile(g, "w") as z:
        z.writestr("Document.xml", xml)
    s = cad.freecad_trace(g, "s.FCStd")["objects"]["S"]
    assert s["constraints"] == {"partLength": 24.0}
    assert s["expressions"] == {".Constraints.partLength": "Params.canaryPart_length"}


def test_port_is_a_reference(tmp_path):
    f = fcstd(tmp_path / "a.FCStd", {"LCS": ("Part::LocalCoordinateSystem", [_prop("Port", "ME-PORT-0001", group="Trace")]),
                                     "Bad": ("Part::LocalCoordinateSystem", [_prop("Port", "EE-PORT-0001", group="Trace")])})
    refs = []
    needs, findings = cad.freecad_needs(f, "a.FCStd", refs)
    assert needs == {} and refs == [("ME-PORT-0001", "a.FCStd")]
    assert any("not an ME-PORT" in x for x in findings)


def test_model_counts_with_multiplicity_and_upstream(tmp_path):
    me = dict(ME, FingerAsm=("ME-ASM-0003", ["Up::Finger", "XdDomain::Assembly"], []),
              CanaryAssembly=("ME-ASM-0001", ["Up::Unit", "XdDomain::Assembly"], [("canaryPart", "CanaryPart", 3)]))
    m = modelmod.Model(_model(me))
    up = modelmod.Model(_model(UP, upstream=True))
    asms, _ = meassemblies.model_defs(m)
    want, findings = meassemblies.expected_counts(m, [up], asms["ME-ASM-0001"])
    assert want == {"ME-PART-0001": 3, "ME-ASM-0003": 2} and not findings


def test_f14_one_to_one(tmp_path):
    root, repo = _repo(tmp_path)
    _assembly(repo)
    _assembly(repo, "gripper", "ME-ASM-0002", links=())
    assert _run(root, repo, "CK-F14", "c_me_one_to_one") == []
    # planted: a top document without TraceID, a folder without a skeleton, a def without a
    # document, a part that refers to the top document
    _assembly(repo, "gripper", "", links=(), skeleton=False)
    (repo / "assemblies/gripper/gripper-skeleton.FCStd").unlink()
    fcstd(repo / "parts/bad.FCStd", {"B": ("PartDesign::SubShapeBinder", [
        _prop("Support", ("../assemblies/canary-assembly/canary-assembly.FCStd", "Assembly"), "App::PropertyXLink")])})
    f = _run(root, repo, "CK-F14", "c_me_one_to_one")
    assert any("without an ME-ASM TraceID" in x for x in f), f
    assert any("no gripper-skeleton.FCStd" in x for x in f), f
    assert any("Gripper (ME-ASM-0002): no FreeCAD document" in x and "curatrix new asm Gripper" in x for x in f), f
    assert any("parts/bad.FCStd: B.Support refers to the top document" in x for x in f), f


def test_f14_wrong_name_and_unknown_id(tmp_path):
    root, repo = _repo(tmp_path, me={k: v for k, v in ME.items() if k != "Gripper"})
    _assembly(repo, "canary", "ME-ASM-0001")
    _assembly(repo, "other", "ME-ASM-0009", links=())
    f = _run(root, repo, "CK-F14", "c_me_one_to_one")
    assert any("gives the file name canary-assembly.FCStd" in x for x in f), f
    assert any("ME-ASM-0009 names no assembly def" in x for x in f), f


def test_f15_link_counts(tmp_path):
    root, repo = _repo(tmp_path, me={k: v for k, v in ME.items() if k != "Gripper"})
    _assembly(repo)
    assert _run(root, repo, "CK-F15", "c_link_counts") == []
    # planted: a second link to the part, which the model uses once
    _assembly(repo, links=(("../../parts/canary-part.FCStd", "CanaryBlock"),) * 2)
    f = _run(root, repo, "CK-F15", "c_link_counts")
    assert f == ["assemblies/canary-assembly/canary-assembly.FCStd: 2 FreeCAD link(s) to ME-PART-0001, the model has "
                 "1 usage(s) in CanaryAssembly (ME-ASM-0001)"], f


def test_f15_counts_per_configuration(tmp_path):
    root, repo = _repo(tmp_path, me={k: v for k, v in ME.items() if k != "Gripper"})
    p = _assembly(repo, links=(("../../parts/canary-part.FCStd", "CanaryBlock"),) * 2)
    # tag the two links with different configurations: one per configuration, as the model says
    with zipfile.ZipFile(p) as z:
        xml = z.read("Document.xml").decode()
    for i, c in enumerate(("SYS-CFG-0001", "SYS-CFG-0002")):
        xml = xml.replace(f'<Object name="Link{i}"><Properties>',
                          f'<Object name="Link{i}"><Properties>{_prop("Configs", c, group="Trace")}')
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("Document.xml", xml)
    assert _run(root, repo, "CK-F15", "c_link_counts") == []


def test_f15_link_targets(tmp_path):
    root, repo = _repo(tmp_path, me={k: v for k, v in ME.items() if k != "Gripper"})
    fcstd(repo / "parts/plain.FCStd", {"Box": ("Part::Box", [])})
    _assembly(repo, links=(("../../parts/canary-part.FCStd", "CanaryBlock"), ("../../parts/plain.FCStd", "Box"),
                           ("../../parts/missing.FCStd", "X")))
    f = _run(root, repo, "CK-F15", "c_link_counts")
    assert any("plain.FCStd#Box, which has no TraceID" in x for x in f), f
    assert any("missing.FCStd, which is not a FreeCAD file" in x for x in f), f


def test_f15_board_library_links_do_not_count(tmp_path):
    """A link to a board model of the board library (cad.board_library) is an EE block: not counted,
    not a finding (CK-F18 and CK-F21 check it); the same link without the section is a finding."""
    root, repo = _repo(tmp_path, me={k: v for k, v in ME.items() if k != "Gripper"})
    lib = root / "lib-repo" / "boards" / "b"
    fcstd(lib / "b-v0.1.0.FCStd", {"Board": ("App::Part", [_prop("TraceID", "EE-PCBA-0001", group="Trace")])})
    _assembly(repo, links=(("../../parts/canary-part.FCStd", "CanaryBlock"),
                           ("../../../lib-repo/boards/b/b-v0.1.0.FCStd", "Board")))
    f = _run(root, repo, "CK-F15", "c_link_counts")
    assert any("b-v0.1.0.FCStd, which is not a FreeCAD file of the repo" in x for x in f), f
    (repo / "checks.yaml").write_text("version: 1\n" + CFG.replace(
        '"assemblies/**/*.FCStd"]', '"assemblies/**/*.FCStd"], board_library: "{ws}/lib-repo"'))
    assert _run(root, repo, "CK-F15", "c_link_counts") == []


def test_new_asm_without_freecad(tmp_path):
    root, repo = _repo(tmp_path)
    (repo / "docs").mkdir()
    (repo / "docs/documents.yaml").write_text("documents:\n  me-design:\n    title: ME\n    group: g-me\n")
    (repo / "checks.yaml").write_text("version: 1\n" + CFG + "docs: {registry: docs/documents.yaml}\n")
    xd = root / "xdmod"
    import shutil
    shutil.copytree(meassemblies.__file__.rsplit("/curatrix/src/", 1)[0] + "/templates", xd / "templates")
    ws = Workspace(root)
    cfg = checkcfg.load(repo / "checks.yaml", root)
    folder = newasm.new_asm(ws, Repo("r", repo, "r"), cfg, "CanaryAssembly", freecad=False, log=lambda *_: None)
    assert folder == repo / "assemblies/canary-assembly"
    idx = (repo / "docs/asm-canary-assembly/index.rst").read_text()
    assert "ME-ASM-0001" in idx and "Canary Assembly (asm-canary-assembly)" in idx
    assert "asm-canary-assembly:" in (repo / "docs/documents.yaml").read_text()
    with pytest.raises(newasm.NewError, match="exists"):
        newasm.new_asm(ws, Repo("r", repo, "r"), cfg, "CanaryAssembly", freecad=False, log=lambda *_: None)
    with pytest.raises(newasm.NewError, match="no assembly def 'Nope'"):
        newasm.new_asm(ws, Repo("r", repo, "r"), cfg, "Nope", freecad=False, log=lambda *_: None)


def test_cad_owned_short_name_is_a_reference():
    doc, findings = modelmod.to_needs(modelmod.Model(_model(ME)))
    needs = doc["versions"][""]["needs"]
    assert "ME-PART-0001" not in needs and "ME-ASM-0001" in needs and not findings, findings


def _model_range(me, up, lo, hi):
    """canary model with the multiplicity of canaryPart replaced by [lo..hi] (hi None = *)."""
    data = _model(me)
    for x in data:
        if x["identity"]["@id"].endswith("canaryPart/lit"):
            x["payload"]["value"] = lo
            mb = [y for y in data if y["identity"]["@id"].endswith("canaryPart/mult")][0]
            if hi is None:
                data.append({"identity": {"@id": "inf"}, "payload": {"@id": "inf", "@type": "LiteralInfinity"}})
            else:
                data.append({"identity": {"@id": "hi"}, "payload": {"@id": "hi", "@type": "LiteralInteger", "value": hi}})
            data.append({"identity": {"@id": "mb2"}, "payload": {"@id": "mb2", "@type": "OwningMembership",
                                                                "ownedRelatedElement": [{"@id": "inf" if hi is None else "hi"}]}})
            mb["payload"]["ownedRelationship"].append({"@id": "mb2"})
    return data


def test_f15_model_findings():
    up = modelmod.Model(_model(UP, upstream=True))
    # the ME model repeats the system-owned usage of Finger
    me = dict(ME, FingerAsm=("ME-ASM-0003", ["Up::Finger", "XdDomain::Assembly"], []),
              CanaryAssembly=("ME-ASM-0001", ["Up::Unit", "XdDomain::Assembly"],
                              [("canaryPart", "CanaryPart", 1), ("finger", "FingerAsm", 2)]))
    m = modelmod.Model(_model(me))
    want, f = meassemblies.expected_counts(m, [up], meassemblies.model_defs(m)[0]["ME-ASM-0001"])
    assert want == {"ME-PART-0001": 1, "ME-ASM-0003": 2}, want
    assert any("repeats a usage the system model owns (ME-ASM-0003)" in x for x in f), f
    # two ME defs realize Finger
    me2 = dict(me, CanaryAssembly=ME["CanaryAssembly"], FingerAsm=("ME-ASM-0003", ["Up::Finger", "XdDomain::Assembly"], []),
               OtherFinger=("ME-ASM-0004", ["Up::Finger", "XdDomain::Assembly"], []))
    m2 = modelmod.Model(_model(me2))
    _, f = meassemblies.expected_counts(m2, [up], meassemblies.model_defs(m2)[0]["ME-ASM-0001"])
    assert any("Up::Finger is realized by 2 ME defs" in x for x in f), f
    # multiplicity ranges
    for lo, hi in ((0, 2), (1, None)):
        me3 = dict(ME, CanaryAssembly=("ME-ASM-0001", ["Up::Unit", "XdDomain::Assembly"], [("canaryPart", "CanaryPart", 3)]))
        m3 = modelmod.Model(_model_range(me3, UP, lo, hi))
        want, f = meassemblies.expected_counts(m3, [up], meassemblies.model_defs(m3)[0]["ME-ASM-0001"])
        assert "ME-PART-0001" not in want and any("not one number" in x for x in f), (lo, hi, f)


def test_f14_sub_assembly_used_by_the_system_model(tmp_path):
    me = dict(ME, FingerAsm=("ME-ASM-0003", ["Up::Finger", "XdDomain::Assembly"], []))
    root, repo = _repo(tmp_path, me=me)
    _assembly(repo)
    _assembly(repo, "gripper", "ME-ASM-0002", links=())
    fcstd(repo / "assemblies/canary-assembly/finger-asm.FCStd",
          {"Assembly": ("Assembly::AssemblyObject", [_prop("TraceID", "ME-ASM-0003", group="Trace")])})
    f = _run(root, repo, "CK-F14", "c_me_one_to_one")
    assert f == [], f
