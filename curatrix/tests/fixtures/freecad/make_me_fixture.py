# FreeCADCmd script: the FreeCAD fixture of the ME checks and the ME design output (tasks 5.25,
# 5.26). Run only through curatrix (tests: `newasm.run_script`). Inputs: XD_DIR (an empty folder),
# XD_RESULT; XD_NO_MARK=1 leaves out the version mark of the printed part (planted for `cam`).
# Makes in XD_DIR a small ME repo layout:
#   parts/box-a.FCStd    Part::Box 10x10x10 (ME-PART-0001), printed (PrintProfile pla, Material PLA),
#                        version mark: LCS VersionMark (Role version-emboss) on the top face
#   parts/box-b.FCStd    Part::Box 10x10x10 (ME-PART-0002)
#   parts/broken.FCStd   Part::Box (ME-PART-0003) and a Part::Fillet with a radius too large (recompute error)
#   parts/sheet.FCStd    Part::Plane with an ME-PART TraceID (a face, not a solid)
#   lib/screw.FCStd      Part::Cylinder with Standard = "ISO 4762 M3x10" (a library fastener)
#   assemblies/fx/fx.FCStd  Assembly (ME-ASM-0001) with links: A at 0, B overlapping A by 5 mm
#                (500 mm^3), C (box-a again) touching B and joined to it, Screw through A and B (a
#                fastener, left out), Sheet (a face inside C, no volume), D (box-b, Configs
#                SYS-CFG-0002) overlapping C by 500 mm^3
#   assemblies/fx/fx-skeleton.FCStd  the skeleton (linked, never checked for overlaps)
import json
import os
import traceback

import FreeCAD as App
import Part  # noqa: F401  (loads the Part types)

res = os.environ.get("XD_RESULT", "")
out = {"ok": False}


def trace(o, tid):
    o.addProperty("App::PropertyString", "TraceID", "Trace")
    o.TraceID = tid


def doc(path, name):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    d = App.newDocument(name)
    return d


try:
    for d in list(App.listDocuments().values()):
        App.closeDocument(d.Name)
    root = os.environ["XD_DIR"]
    made = {}
    for name, tid in (("box-a", "ME-PART-0001"), ("box-b", "ME-PART-0002")):
        d = doc(f"{root}/parts/{name}.FCStd", name.replace("-", "_"))
        b = d.addObject("Part::Box", "Box")
        b.Length = b.Width = b.Height = 10
        trace(b, tid)
        if name == "box-a":                # a printed part, with its version mark on the top face
            b.addProperty("App::PropertyString", "PrintProfile", "BOM")
            b.PrintProfile = "pla"
            b.addProperty("App::PropertyString", "Material", "BOM")
            b.Material = "PLA"
        if name == "box-a" and not os.environ.get("XD_NO_MARK"):
            m = d.addObject("Part::LocalCoordinateSystem", "VersionMark")
            m.Placement = App.Placement(App.Vector(1, 3, 10), App.Rotation())
            m.addProperty("App::PropertyString", "Role", "Version")
            m.Role = "version-emboss"
            m.addProperty("App::PropertyLength", "TextSize", "Version")
            m.TextSize = 3
            m.addProperty("App::PropertyLength", "MaxWidth", "Version")
            m.MaxWidth = 8
        d.recompute()
        d.saveAs(f"{root}/parts/{name}.FCStd")
        made[name] = (d, b)
    d = doc(f"{root}/parts/broken.FCStd", "broken")
    b = d.addObject("Part::Box", "Body")
    trace(b, "ME-PART-0003")
    f = d.addObject("Part::Fillet", "Fillet")
    f.Base = b
    f.Edges = [(1, 50.0, 50.0)]
    d.recompute()
    d.saveAs(f"{root}/parts/broken.FCStd")
    d = doc(f"{root}/parts/sheet.FCStd", "sheet")
    p = d.addObject("Part::Plane", "Sheet")
    p.Length = p.Width = 10
    trace(p, "ME-PART-0004")
    d.recompute()
    d.saveAs(f"{root}/parts/sheet.FCStd")
    made["sheet"] = (d, p)
    d = doc(f"{root}/lib/screw.FCStd", "screw")
    s = d.addObject("Part::Cylinder", "Screw")
    s.Radius, s.Height = 1.5, 30
    trace(s, "ME-PART-0005")
    s.addProperty("App::PropertyString", "Standard", "BOM")
    s.Standard = "ISO 4762 M3x10, A2"
    d.recompute()
    d.saveAs(f"{root}/lib/screw.FCStd")
    made["screw"] = (d, s)

    sk = doc(f"{root}/assemblies/fx/fx-skeleton.FCStd", "fx_skeleton")
    skp = sk.addObject("App::Part", "Skeleton")
    sk.addObject("Spreadsheet::Sheet", "Params")
    sk.recompute()
    sk.saveAs(f"{root}/assemblies/fx/fx-skeleton.FCStd")
    top = doc(f"{root}/assemblies/fx/fx.FCStd", "fx")
    asm = top.addObject("Assembly::AssemblyObject", "Assembly")
    trace(asm, "ME-ASM-0001")
    joints = top.addObject("Assembly::JointGroup", "Joints")
    asm.addObject(joints)
    top.saveAs(f"{root}/assemblies/fx/fx.FCStd")

    def link(name, target, pos, configs=""):
        lk = top.addObject("App::Link", name)
        lk.setLink(target)
        lk.Placement = App.Placement(App.Vector(*pos), App.Rotation())
        if configs:
            lk.addProperty("App::PropertyString", "Configs", "Trace")
            lk.Configs = configs
        asm.addObject(lk)
        return lk
    link("Skeleton", skp, (0, 0, 0))
    a = link("A", made["box-a"][1], (0, 0, 0))
    b = link("B", made["box-b"][1], (5, 0, 0))            # 5 x 10 x 10 = 500 mm^3 into A
    c = link("C", made["box-a"][1], (15, 0, 0))           # touches B (x = 15), joined to it
    link("Screw", made["screw"][1], (5, 5, -10))           # through A and B: a fastener, left out
    link("Sheet", made["sheet"][1], (16, 0, 5))           # a face inside C: no volume, no overlap
    link("D", made["box-b"][1], (20, 0, 0), "SYS-CFG-0002")   # into C, only in SYS-CFG-0002
    j = top.addObject("App::FeaturePython", "Joint")
    j.addProperty("App::PropertyXLinkSubHidden", "Reference1", "Joint")
    j.addProperty("App::PropertyXLinkSubHidden", "Reference2", "Joint")
    j.Reference1 = (asm, ["B.Face2"])
    j.Reference2 = (asm, ["C.Face1"])
    joints.addObject(j)
    top.recompute()
    top.save()
    out = {"ok": True, "files": sorted(os.path.relpath(os.path.join(p, f), root)
                                       for p, _, fs in os.walk(root) for f in fs if f.endswith(".FCStd"))}
    for d in list(App.listDocuments().values()):
        App.closeDocument(d.Name)
except Exception:
    out["error"] = traceback.format_exc()
if res:
    with open(res, "w") as f:
        json.dump(out, f)
