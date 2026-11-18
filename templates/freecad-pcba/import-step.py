# FreeCAD script of `curatrix cam <repo> <board> --board-model` / `--library` (task 5.29, XD-ADR-0139).
# Run only through curatrix: the FreeCAD GUI binary on Qt's offscreen platform (no window, no display),
# workspace-local FreeCAD config with CompressionLevel 0, limits. Inputs by environment variables:
# XD_STEP, XD_OUT, XD_TRACE_ID, XD_VERSION, XD_VARIANT, XD_BOARD, XD_COMMIT, XD_THICKNESS, XD_RESULT.
# The STEP comes with its origin at the lower-left corner of the outline (kicad-cli --user-origin) and
# z = 0 on the board's bottom face; the import moves it down by XD_THICKNESS (the board thickness of
# the .kicad_pcb), so the model sits in the board frame of the co-design budget (XD-ADR-0134): z = 0
# on the top face.
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
#                         Version, Variant, Board, Commit, Source, Thickness (group Board)
#   App::Link per component inside it, named and labelled by the reference designator (R1, J1;
#                         "PCB" is the board body), Label2 = the STEP product (the 3D model's name),
#                         placed in board coordinates, pointing to its model
#   group "Models"        (hidden) one Part::Feature per 3D model, stored once however many components
#                         use it, ShapeAppearance = the STEP colours per face
# A component whose placement cannot be recovered becomes a Part::Feature copy in board coordinates
# inside Board instead of a link (not seen on KiCad STEPs; counted as "copies" in the result).
# The STEP is imported with instance names (UseBaseName off, link groups, import mode 0: every setting
# the flattening relies on is pinned here and restored, so a changed workspace preference, e.g.
# ImportMode 2, which stalls offscreen, cannot break it), then flattened: one object per top-level
# instance of the STEP, its face colours collected from the solids below it in shape order.
import json
import os
import re
import traceback

res = os.environ.get("XD_RESULT", "")
out = {"ok": False}
saved = []                                  # (group, kind, name, had, old): restored in finally
# the import settings this script relies on (FreeCAD 1.1: Mod/Import, STEP reader in Mod/Import/hSTEP)
PINNED = {"User parameter:BaseApp/Preferences/Mod/Import": {
              "UseBaseName": False, "UseLinkGroup": True, "ExpandCompound": False, "ExpandShapeContent": False,
              "ReduceObjects": False, "ImportHiddenObject": True, "ShowProgress": False,
              "ReadShapeCompoundMode": False, "ReadShowDialogImport": False, "ImportMode": 0},
          "User parameter:BaseApp/Preferences/Mod/Import/hSTEP": {
              "ReadShapeCompoundMode": False, "ReadShowDialogImport": False}}


def pin(App):
    for path, values in PINNED.items():
        g = App.ParamGet(path)
        for name, value in values.items():
            kind = "Bool" if isinstance(value, bool) else "Int"
            had = name in getattr(g, f"Get{kind}s")()
            saved.append((g, kind, name, had, getattr(g, f"Get{kind}")(name)))
            getattr(g, f"Set{kind}")(name, value)


def unpin():
    for g, kind, name, had, old in reversed(saved):
        if had:
            getattr(g, f"Set{kind}")(name, old)
        else:
            getattr(g, f"Rem{kind}")(name)
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
    pin(App)                            # restored below (os._exit saves no config anyway)
    src = App.newDocument("step")
    ImportGui.insert(step, src.Name, importHidden=True, merge=False, useLinkGroup=True, mode=0)
    src.recompute()
    roots = [o for o in src.Objects if not o.InList and o.TypeId in ("App::LinkGroup", "App::Part", "Part::Feature")]
    if len(roots) != 1:
        raise RuntimeError(f"expected one top object in the STEP import, got {[o.Label for o in roots]}")
    root = roots[0]
    if not os.environ.get("XD_THICKNESS"):
        raise RuntimeError("XD_THICKNESS missing: without the board thickness the model would keep z = 0 on its "
                           "bottom face instead of the top face (board frame)")
    thick = float(os.environ["XD_THICKNESS"])
    # into the board frame: z = 0 on the top face; every placement below is taken with transform=True,
    # so it includes this one
    root.Placement = App.Placement(App.Vector(0, 0, -thick), App.Rotation()).multiply(root.Placement)
    src.recompute()

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
    part.addProperty("App::PropertyLength", "Thickness", "Board", "board thickness (KiCad general.thickness); "
                     "the model's z = 0 is the top face (board frame)")
    part.Thickness = thick
    part.Source = ("kicad-cli pcb export step, FreeCAD ImportGui.insert (offscreen); one link per component "
                   "to its 3D model in Models, with the STEP colours")
    comps, shapes, models, group, linked, copies = [], [], {}, None, 0, 0
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
            copies += 1
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
           "bbox_min_mm": [round(v, 3) for v in (bb.XMin, bb.YMin, bb.ZMin)] if shapes else None,
           "coloured": sum(1 for c in comps if c["colours"]), "models": len(models), "links": linked,
           "copies": copies, "uncoloured_faces": [c["label"] for c in comps if not c["face_colours"]],
           "invalid": invalid}
    if not comps:
        out["error"] = "the STEP import gave no component"
    App.closeDocument(doc.Name)
except Exception:
    out["error"] = traceback.format_exc()
finally:
    try:
        unpin()
    except Exception:
        pass
    try:
        # os._exit skips FreeCAD's cleanup, which would remove its session lock file in the cache. Remove
        # every FreeCAD_<n>.lock that no running FreeCAD holds (fcntl locks never conflict within one
        # process, so ours counts as free; another live session's lock is busy and stays).
        import fcntl
        import glob
        for lock in glob.glob(os.path.join(App.getUserCachePath(), "FreeCAD_*.lock")):
            with open(lock, "a") as fh:
                try:
                    fcntl.lockf(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except OSError:
                    continue
            os.remove(lock)
    except Exception:
        pass
    if res:
        with open(res, "w") as f:
            json.dump(out, f)
    os._exit(0)
