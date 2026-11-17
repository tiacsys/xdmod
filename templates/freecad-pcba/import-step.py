# FreeCADCmd script of `curatrix cam <repo> <board> --board-model` (task 5.29, XD-ADR-0139). Run only
# through curatrix (workspace-local FreeCAD config with CompressionLevel 0, limits). Inputs by
# environment variables, because FreeCADCmd opens extra arguments as files (FreeCAD spike):
# XD_STEP, XD_OUT, XD_TRACE_ID, XD_VERSION, XD_VARIANT, XD_BOARD, XD_COMMIT, XD_RESULT.
# FreeCADCmd exits 0 when a script raises, so the caller judges success by the result file only;
# the script never raises (a raising script runs twice).
#
# Writes XD_OUT, a new document with
#   App::Part "Board"     the board model to link from an assembly; properties
#                         TraceID (group Trace) = the board's EE-PCBA ID,
#                         Version, Variant, Board, Commit, Source (group Board)
#   Part::Feature "Shape" inside it: the STEP shape (one compound: board body and components)
# The STEP is read as one shape (Part.Shape.read), so the colours of the STEP are not kept.
import json
import os
import traceback

import FreeCAD as App
import Part

res = os.environ.get("XD_RESULT", "")
out = {"ok": False}
try:
    step, dest = os.environ["XD_STEP"], os.environ["XD_OUT"]
    for doc in list(App.listDocuments().values()):          # a fresh start, also on a second run
        App.closeDocument(doc.Name)
    if os.path.exists(dest):
        os.remove(dest)
    shape = Part.Shape()
    shape.read(step)
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
    part.Source = "kicad-cli pcb export step, FreeCAD Part.Shape.read"
    feat = doc.addObject("Part::Feature", "Shape")
    feat.Label = "Shape"
    feat.Shape = shape
    part.addObject(feat)
    doc.recompute()
    doc.saveAs(dest)
    bb = shape.BoundBox
    out = {"ok": shape.isValid() and not shape.isNull(), "valid": shape.isValid(),
           "solids": len(shape.Solids), "shells": len(shape.Shells),
           "bbox_mm": [round(v, 3) for v in (bb.XLength, bb.YLength, bb.ZLength)],
           "invalid": [o.Name for o in doc.Objects if not o.isValid()]}
    if out["invalid"]:
        out["ok"] = False
    App.closeDocument(doc.Name)
except Exception:
    out["error"] = traceback.format_exc()
if res:
    with open(res, "w") as f:
        json.dump(out, f)
