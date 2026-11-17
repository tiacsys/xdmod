# FreeCAD script of `curatrix cam <repo> <board> --board-model` / `--library` (task 5.29, XD-ADR-0139).
# Run only through curatrix: the FreeCAD GUI binary on Qt's offscreen platform (no window, no display),
# workspace-local FreeCAD config with CompressionLevel 0, limits. Inputs by environment variables:
# XD_STEP, XD_OUT, XD_TRACE_ID, XD_VERSION, XD_VARIANT, XD_BOARD, XD_COMMIT, XD_RESULT.
# Success only by the result file; the script never raises and ends with os._exit (the GUI binary
# would otherwise wait in its event loop).
#
# Why the GUI binary (2026-11-17, finding 17 of tiacsys/xdmod#69): the STEP colours become the view
# providers' ShapeAppearance (GuiDocument.xml). FreeCADCmd has no view providers, so `Import.insert`
# there keeps the structure but no colour, and `FreeCADGui.setupWithoutGUI()` gives none either.
# `ImportGui.insert` in the offscreen GUI binary keeps the per-face colours.
#
# Writes XD_OUT, a new document with
#   App::Part "Board"     the board model to link from an assembly; properties
#                         TraceID (group Trace) = the board's EE-PCBA ID,
#                         Version, Variant, Board, Commit, Source (group Board)
#   Part::Feature per component inside it, named and labelled by the reference designator (R1, J1),
#                         Label2 = the STEP product (the 3D model's name); "PCB" is the board body.
#                         Shape in board coordinates, ShapeAppearance = the STEP colours per face.
# The STEP is imported with instance names (Import parameter UseBaseName off, link groups), then
# flattened: one feature per top-level instance of the STEP (Part.getShape in board coordinates), its
# face colours collected from the solids below it in shape order.
import json
import os
import re
import traceback

res = os.environ.get("XD_RESULT", "")
out = {"ok": False}
grp = had = old = None
try:
    import FreeCAD as App
    import Part
    if not App.GuiUp:
        raise RuntimeError("needs the FreeCAD GUI binary (QT_QPA_PLATFORM=offscreen): FreeCADCmd has no view "
                           "providers, so the STEP colours would be lost")
    import ImportGui
    step, dest = os.environ["XD_STEP"], os.environ["XD_OUT"]
    for d in list(App.listDocuments().values()):              # a fresh start
        App.closeDocument(d.Name)
    if os.path.exists(dest):
        os.remove(dest)
    # instance names (R1, J1) instead of product names; restored below (os._exit saves no config anyway)
    grp = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Import")
    had = "UseBaseName" in grp.GetBools()
    old = grp.GetBool("UseBaseName", True)
    grp.SetBool("UseBaseName", False)
    src = App.newDocument("step")
    ImportGui.insert(step, src.Name, merge=False, useLinkGroup=True)
    src.recompute()
    roots = [o for o in src.Objects if not o.InList and o.TypeId in ("App::LinkGroup", "App::Part", "Part::Feature")]
    if len(roots) != 1:
        raise RuntimeError(f"expected one top object in the STEP import, got {[o.Label for o in roots]}")
    root = roots[0]

    def children(obj):
        """the objects an import object is made of: link group elements, compound links, the link target."""
        if obj.TypeId == "App::Link":
            return [obj.LinkedObject] if obj.LinkedObject else []
        if obj.TypeId == "App::LinkGroup":
            return list(obj.ElementList)
        if obj.TypeId == "Part::Compound2":
            return list(obj.Links)
        return []

    def appearance(obj, nfaces):
        mats = list(obj.ViewObject.ShapeAppearance) if obj is not None and obj.ViewObject else []
        if len(mats) == nfaces:
            return mats
        return [mats[0] if mats else App.Material()] * nfaces

    def solids(obj, depth=0):
        """the Part::Feature leaves below obj in shape order (a compound's faces are its children's in turn)."""
        if obj.TypeId == "Part::Feature":
            return [obj]
        return [x for c in children(obj) for x in solids(c, depth + 1)] if depth < 30 else []

    doc = App.newDocument("board")
    part = doc.addObject("App::Part", "Board")
    part.Label = os.environ["XD_BOARD"]
    part.addProperty("App::PropertyString", "TraceID", "Trace", "EE-PCBA ID of the board (robarm-ee model)")
    part.TraceID = os.environ["XD_TRACE_ID"]
    for name, doc_text in (("Version", "board tag <board>/vX.Y.Z (curatrix cam)"),
                           ("Variant", "KiCad variant of the export, empty for none"),
                           ("Board", "KiCad project name"),
                           ("Commit", "EE repo commit of the export"),
                           ("Source", "how the model was made")):
        part.addProperty("App::PropertyString", name, "Board", doc_text)
    part.Version = os.environ["XD_VERSION"]
    part.Variant = os.environ.get("XD_VARIANT", "")
    part.Board = os.environ["XD_BOARD"]
    part.Commit = os.environ.get("XD_COMMIT", "")
    part.Source = ("kicad-cli pcb export step, FreeCAD ImportGui.insert (offscreen), one feature per "
                   "component with the STEP colours")
    comps, shapes, models, group, linked = [], [], {}, None, 0
    for sub in root.getSubObjects():
        child = root.getSubObject(sub, retType=1)
        leaves = solids(child)
        shape = Part.getShape(root, sub, needSubElement=False, transform=True)   # in board coordinates
        if not leaves or shape.isNull() or not shape.Faces:
            continue
        model = leaves[0].Label                                    # the STEP product of the 3D model
        ref = child.Label
        if ref.startswith("=>") or not ref.strip():               # an unnamed instance: the board body
            ref = "PCB" if model.endswith("_PCB") else model
        mats = [m for leaf in leaves for m in appearance(leaf, len(leaf.Shape.Faces))]
        exact = len(mats) == len(shape.Faces)
        if not exact:                                             # not expected; keep one colour then
            mats = [mats[0] if mats else App.Material()] * len(shape.Faces)
        name = re.sub(r"\W", "_", ref) or "Component"
        # a 3D model used by several components is stored once (a hidden feature in "Models") and the
        # components are links to it; the board file stays small (one BREP per model, not per part)
        key = tuple(leaf.Name for leaf in leaves)
        local = Part.getShape(child, "", needSubElement=False, transform=False)
        mat = root.getSubObject(sub, retType=2, transform=True)[1]
        placed = local.transformed(mat) if not local.isNull() else local
        same = (not placed.isNull() and abs(placed.Volume - shape.Volume) <= 1e-6 * max(1.0, abs(shape.Volume))
                and placed.BoundBox.isInside(shape.BoundBox.Center)
                and max(abs(x - y) for x, y in zip(
                    (placed.BoundBox.XMin, placed.BoundBox.YMin, placed.BoundBox.ZMin,
                     placed.BoundBox.XMax, placed.BoundBox.YMax, placed.BoundBox.ZMax),
                    (shape.BoundBox.XMin, shape.BoundBox.YMin, shape.BoundBox.ZMin,
                     shape.BoundBox.XMax, shape.BoundBox.YMax, shape.BoundBox.ZMax))) < 1e-4)
        if same and len(local.Faces) == len(mats):
            if key not in models:
                if group is None:
                    group = doc.addObject("App::DocumentObjectGroup", "Models")
                    group.Label = "Models"
                m = doc.addObject("Part::Feature", "Model")
                m.Label = model
                m.Shape = local
                group.addObject(m)
                m.ViewObject.ShapeAppearance = mats
                m.Visibility = False
                models[key] = m
            feat = doc.addObject("App::Link", name)
            feat.LinkedObject = models[key]
            feat.Placement = App.Placement(mat)
            feat.Label = ref
            feat.Label2 = model
            part.addObject(feat)
            feat.Visibility = True
            linked += 1
        else:                                                     # placement not recoverable: a copy
            feat = doc.addObject("Part::Feature", name)
            feat.Label = ref
            feat.Label2 = model
            feat.Shape = shape
            part.addObject(feat)
            feat.ViewObject.ShapeAppearance = mats
        shapes.append(shape)
        rgb = sorted({tuple(round(c, 3) for c in m.DiffuseColor[:3]) for m in mats})
        comps.append({"name": feat.Name, "label": ref, "model": model, "solids": len(shape.Solids),
                      "faces": len(shape.Faces), "colours": rgb,
                      "face_colours": exact})
    doc.recompute()
    App.closeDocument(src.Name)
    doc.saveAs(dest)
    whole = Part.makeCompound(shapes) if shapes else Part.Shape()
    bb = whole.BoundBox
    invalid = [o.Name for o in doc.Objects if not o.isValid()] + [c["name"] for c, s in zip(comps, shapes)
                                                                 if not s.isValid()]
    out = {"ok": bool(comps) and not invalid, "valid": not invalid, "components": comps,
           "solids": len(whole.Solids), "shells": len(whole.Shells),
           "bbox_mm": [round(v, 3) for v in (bb.XLength, bb.YLength, bb.ZLength)] if shapes else None,
           "coloured": sum(1 for c in comps if c["colours"]), "models": len(models), "links": linked,
           "invalid": invalid}
    if not comps:
        out["error"] = "the STEP import gave no component"
    App.closeDocument(doc.Name)
except Exception:
    out["error"] = traceback.format_exc()
finally:
    try:
        if grp is not None:
            if had:
                grp.SetBool("UseBaseName", old)
            else:
                grp.RemBool("UseBaseName")
    except Exception:
        pass
    if res:
        with open(res, "w") as f:
            json.dump(out, f)
    os._exit(0)
