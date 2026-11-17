# FreeCADCmd script of `curatrix new asm` (task 5.23, XD-ADR-0137). Run only through curatrix
# (workspace-local FreeCAD config, limits). Inputs by environment variables, because FreeCADCmd
# opens extra arguments as files (FreeCAD spike): XD_ASM_DIR, XD_ASM_NAME, XD_ASM_ID,
# XD_ASM_TITLE, XD_RESULT. FreeCADCmd exits 0 when a script raises, so the caller judges success
# by the result file only; the script never raises (a raising script runs twice).
#
# Makes, in XD_ASM_DIR:
#   <name>-skeleton.FCStd  App::Part "Skeleton" with the master sketch "MasterSketch"; the parameter
#                     spreadsheet "Params" (aliases <usage>_<attribute>, written by
#                     `curatrix gen freecad-params`)
#   <name>.FCStd      the top document: Assembly::AssemblyObject "Assembly" with the property
#                     TraceID (group Trace) = the ME-ASM ID of the assembly def, a "Joints" group
#                     and an App::Link "Skeleton" to the skeleton's part
import json
import os
import traceback

import FreeCAD as App

res = os.environ.get("XD_RESULT", "")
out = {"ok": False}
try:
    d, name = os.environ["XD_ASM_DIR"], os.environ["XD_ASM_NAME"]
    tid, title = os.environ["XD_ASM_ID"], os.environ["XD_ASM_TITLE"]
    for doc in list(App.listDocuments().values()):          # a fresh start, also on a second run
        App.closeDocument(doc.Name)

    sk = App.newDocument((name + "-skeleton").replace("-", "_"))
    part = sk.addObject("App::Part", "Skeleton")
    part.Label = "Skeleton"
    sketch = sk.addObject("Sketcher::SketchObject", "MasterSketch")
    sketch.Label = "MasterSketch"
    part.addObject(sketch)
    params = sk.addObject("Spreadsheet::Sheet", "Params")
    params.Label = "Params"
    sk.recompute()
    sk.saveAs(os.path.join(d, name + "-skeleton.FCStd"))

    top = App.newDocument(name.replace("-", "_"))
    asm = top.addObject("Assembly::AssemblyObject", "Assembly")
    asm.Label = title
    asm.addProperty("App::PropertyString", "TraceID", "Trace")
    asm.TraceID = tid
    joints = top.addObject("Assembly::JointGroup", "Joints")
    asm.addObject(joints)
    top.saveAs(os.path.join(d, name + ".FCStd"))              # a cross-document link needs a saved owner
    link = top.addObject("App::Link", "Skeleton")
    link.setLink(part)
    link.Label = "Skeleton"
    asm.addObject(link)
    top.recompute()
    top.save()
    invalid = [f"{doc.Name}#{o.Name}" for doc in (sk, top) for o in doc.Objects if not o.isValid()]
    out = {"ok": not invalid, "invalid": invalid,
           "files": sorted(f for f in os.listdir(d) if f.endswith(".FCStd"))}
    for doc in (top, sk):
        App.closeDocument(doc.Name)
except Exception:
    out["error"] = traceback.format_exc()
if res:
    with open(res, "w") as f:
        json.dump(out, f)
