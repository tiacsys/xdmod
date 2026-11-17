# FreeCADCmd script of `curatrix cam <repo> <asm>` (task 5.26; XD-ADR-0137, XD-ADR-0143). Run only
# through curatrix: workspace-local FreeCAD config, limits. Inputs by environment variables
# (FreeCADCmd opens extra arguments as files, FreeCAD spike):
#   XD_TOP, XD_SKELETON  the top document and its skeleton (opened skeleton first, XD-ADR-0146)
#   XD_OUT               the output folder of this variant (fresh, made by curatrix)
#   XD_VARIANT           the variant: links whose own Configs do not name it are left out; "" = all
#                        links; "base" = only the links without Configs (every configuration that
#                        no link names)
#   XD_VERSION           the full version (drawing title block); XD_SHORT the short one (embossed)
#   XD_FONT              the pinned font file for the emboss
#   XD_EXPLODE           JSON {link name: [dx, dy, dz]} of the exploded view, or {} (automatic)
#   XD_RESULT            the result file
# FreeCADCmd exits 0 when a script raises: the caller judges success by the result file. The script
# never raises and never saves a document (curatrix checks the md5 of the sources before and after).
#
# Writes into XD_OUT: <asm>.step (the present links of the assembly), parts/<part>.stl and .3mf per
# printed part (an object with a PrintProfile property; embossed with XD_SHORT on its version mark,
# an LCS with Role = version-emboss, TextSize, MaxWidth, optional EmbossDepth), views/<view>.svg
# (TechDraw views front, top, right, iso of the assembly), exploded.svg (TechDraw view of the
# exploded compound with explosion lines). The result lists the BOM rows (one per present leaf link)
# and the files.
import json
import os
import traceback

import FreeCAD as App

res = os.environ.get("XD_RESULT", "")
out = {"ok": False}
LCS_TYPES = ("Part::LocalCoordinateSystem", "PartDesign::CoordinateSystem")
BOM_PROPS = ("TraceID", "PrintProfile", "Material", "Standard", "Manufacturer", "MPN")
# view: (Direction, the view normal towards the viewer; XDirection, the model direction that points
# right in the view). Up is Direction x XDirection: +z for front, right and iso, +y for top.
VIEWS = {"front": ((0, -1, 0), (1, 0, 0)), "top": ((0, 0, 1), (1, 0, 0)), "right": ((1, 0, 0), (0, 1, 0)),
         "iso": ((1, -1, 1), (1, 1, 0))}


def prop(o, name):
    return str(getattr(o, name, "") or "").strip() if o is not None and name in o.PropertiesList else ""


def present(link, variant):
    cfgs = [c.strip() for c in prop(link, "Configs").replace(";", ",").split(",") if c.strip()]
    if variant == "base":
        return not cfgs
    return not variant or not cfgs or variant in cfgs


def is_asm(o):
    return o is not None and prop(o, "TraceID").startswith("ME-ASM-")


def walk(asm, variant, path, rows, placement):
    """BOM rows of the present leaf links below an assembly object (sub-assemblies recursively)."""
    for c in getattr(asm, "Group", []) or []:
        if not c.TypeId.startswith("App::Link") or not present(c, variant):
            continue
        t = c.getLinkedObject(True)
        f = t.Document.FileName if t is not None else ""
        if f.endswith("-skeleton.FCStd"):
            continue
        pl = placement.multiply(c.Placement)
        if is_asm(t):
            walk(t, variant, path + [c.Name], rows, pl)
            continue
        rows.append({"path": "/".join(path + [c.Name]), "file": f, "object": t.Name if t else "",
                     "label": t.Label if t else c.Label, **{p: prop(t, p) for p in BOM_PROPS}, "_obj": t, "_pl": pl})


def view_svg(shape, view, name, d):
    """A TechDraw view of a shape as SVG (FreeCAD spike §5: a page with a template is needed, the
    view computes in a thread, so wait for its edges; no GUI, no event loop)."""
    import TechDraw
    import time
    page = d.getObject("XdPage")
    if page is None:
        page = d.addObject("TechDraw::DrawPage", "XdPage")
        tpl = d.addObject("TechDraw::DrawSVGTemplate", "XdTemplate")
        tpl.Template = App.getResourceDir() + "Mod/TechDraw/Templates/Default_Template_A4_Landscape.svg"
        page.Template = tpl
    holder = d.addObject("Part::Feature", f"XdSrc_{name}")
    holder.Shape = shape
    v = d.addObject("TechDraw::DrawViewPart", f"XdView_{name}")
    page.addView(v)
    v.Source = [holder]
    v.Direction = App.Vector(*view[0])
    v.XDirection = App.Vector(*view[1])
    d.recompute()
    for _ in range(120):
        if v.getVisibleEdges():
            break
        time.sleep(0.25)
    edges = len(v.getVisibleEdges())
    return TechDraw.viewPartAsSvg(v), edges


def emboss(part, text, font):
    """(shape, info) of a part with the text embossed on its version mark, or (None, why). The mark
    is the LCS with Role = version-emboss of the part's document, not tied to one object: one mark per
    document (CK-F19), so one printed part per document."""
    import Draft
    import Part
    mark = next((o for o in part.Document.Objects if o.TypeId in LCS_TYPES and prop(o, "Role") == "version-emboss"),
                None)
    if mark is None:
        return None, "no version mark (LCS with Role = version-emboss)"
    size = float(getattr(mark, "TextSize", 3) or 3)
    maxw = float(getattr(mark, "MaxWidth", 0) or 0)
    depth = float(getattr(mark, "EmbossDepth", 0.6) or 0.6)
    base = part.Shape.copy()
    for _ in range(6):
        ss = Draft.make_shapestring(String=text, FontFile=font, Size=size, Tracking=0)
        ss.Document.recompute()
        w = ss.Shape.BoundBox.XLength
        if not maxw or w <= maxw:
            break
        size *= maxw / w * 0.98
        ss.Document.removeObject(ss.Name)
    txt = ss.Shape.copy()
    ss.Document.removeObject(ss.Name)
    gp = mark.getGlobalPlacement() if hasattr(mark, "getGlobalPlacement") else mark.Placement
    txt.Placement = gp.multiply(txt.Placement)
    z = gp.Rotation.multVec(App.Vector(0, 0, 1))
    solid = txt.extrude(z * depth)
    result = base.fuse(solid).removeSplitter()
    info = {"text": text, "size": round(size, 3), "depth": depth, "width": round(w, 3),
            "solids": len(result.Solids), "valid": result.isValid(),
            "volume_before": round(base.Volume, 4), "volume_after": round(result.Volume, 4)}
    if len(result.Solids) != 1 or not result.isValid() or result.Volume <= base.Volume:
        return None, f"the embossed part is not exactly one valid solid: {info}"
    return result, info


try:
    import Import
    import Mesh
    import MeshPart
    import Part
    for d in list(App.listDocuments().values()):
        App.closeDocument(d.Name)
    App.openDocument(os.environ["XD_SKELETON"])
    top = App.openDocument(os.environ["XD_TOP"])
    for d in list(App.listDocuments().values()):
        if getattr(d, "Partial", False):
            d.restore()
    for d in App.listDocuments().values():
        d.recompute()
    variant = os.environ.get("XD_VARIANT", "")
    dest = os.environ["XD_OUT"]
    name = os.path.splitext(os.path.basename(os.environ["XD_TOP"]))[0]
    asm = next(o for o in top.Objects if is_asm(o) and o.TypeId == "Assembly::AssemblyObject")
    rows = []
    walk(asm, variant, [], rows, App.Placement())
    files, warnings, embossed = [], [], {}
    kids = [c for c in asm.Group if c.TypeId.startswith("App::Link") and present(c, variant)
            and not (c.getLinkedObject(True) and c.getLinkedObject(True).Document.FileName.endswith("-skeleton.FCStd"))]
    # STEP of the assembly (the present links, with their structure)
    step = os.path.join(dest, f"{name}.step")
    Import.export(kids, step)
    files.append(step)
    # printed parts: 3MF and STL, embossed
    os.makedirs(os.path.join(dest, "parts"), exist_ok=True)
    done = set()
    for r in rows:
        t = r["_obj"]
        key = (r["file"], r["object"])
        if not r["PrintProfile"] or key in done:
            continue
        done.add(key)
        stem = os.path.splitext(os.path.basename(r["file"]))[0]
        shape, info = emboss(t, os.environ["XD_SHORT"], os.environ["XD_FONT"])
        if shape is None:
            raise RuntimeError(f"{os.path.basename(r['file'])}#{t.Name}: {info}")
        embossed[stem] = info
        mesh = MeshPart.meshFromShape(Shape=shape, LinearDeflection=0.02, AngularDeflection=0.1, Relative=False)
        for ext in ("stl", "3mf"):
            p = os.path.join(dest, "parts", f"{stem}.{ext}")
            mesh.write(p)
            files.append(p)
    # views of the assembly and the exploded view
    shapes = [c.Shape.copy() for c in kids]
    comp = Part.makeCompound(shapes)
    os.makedirs(os.path.join(dest, "views"), exist_ok=True)
    edges = {}
    for v, view in VIEWS.items():
        svg, n = view_svg(comp, view, v, top)
        edges[v] = n
        p = os.path.join(dest, "views", f"{v}.svg")
        with open(p, "w") as f:
            f.write(svg)
        files.append(p)
    moves = json.loads(os.environ.get("XD_EXPLODE") or "{}")
    cb = comp.BoundBox
    center = cb.Center
    exploded, lines, used = [], [], {}
    for c, s in zip(kids, shapes):
        if moves:
            mv = App.Vector(*moves.get(c.Name, (0, 0, 0)))
        else:                               # automatic: away from the assembly's centre
            dv = s.BoundBox.Center - center
            mv = dv * 1.0 if dv.Length > 1e-6 else App.Vector(0, 0, 0)
        used[c.Name] = [round(x, 4) for x in (mv.x, mv.y, mv.z)]
        m = s.copy()
        m.translate(mv)
        exploded.append(m)
        if mv.Length > 1e-6:
            lines.append(Part.makeLine(s.BoundBox.Center, s.BoundBox.Center + mv))
    svg, n = view_svg(Part.makeCompound(exploded + lines), VIEWS["iso"], "exploded", top)
    p = os.path.join(dest, "exploded.svg")
    with open(p, "w") as f:
        f.write(svg)
    files.append(p)
    edges["exploded"] = n
    out = {"ok": True, "files": [os.path.relpath(f, dest) for f in files], "edges": edges, "embossed": embossed,
           "moves": used, "bbox": [round(x, 4) for x in (cb.XMin, cb.YMin, cb.ZMin, cb.XMax, cb.YMax, cb.ZMax)],
           "bom": [{k: v for k, v in r.items() if not k.startswith("_")} for r in rows], "warnings": warnings}
    for d in list(App.listDocuments().values()):
        App.closeDocument(d.Name)
except Exception:
    out["error"] = traceback.format_exc()
if res:
    with open(res, "w") as f:
        json.dump(out, f, indent=1)
