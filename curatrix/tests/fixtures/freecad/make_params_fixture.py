# FreeCADCmd script: the FreeCAD fixture of `curatrix gen freecad-params` with an own part (finding
# 16 of xdmod#69). Run only through curatrix (tests: `newasm.run_script`). Inputs: XD_DIR (an
# empty folder), XD_RESULT. Makes in XD_DIR:
#   fxp-skeleton.FCStd  App::Part Skeleton and the spreadsheet Params (alias plate_length = 10 mm)
#   parts/plate.FCStd   Part::Box whose Length is fxp_skeleton#Params.plate_length
#   fxp.FCStd           Assembly with a link to the skeleton and one to the box: through this link
#                       FreeCAD opens parts/plate.FCStd only partially
import json
import os
import traceback

import FreeCAD as App
import Part  # noqa: F401  (loads the Part types)

res = os.environ.get("XD_RESULT", "")
out = {"ok": False}
try:
    for d in list(App.listDocuments().values()):
        App.closeDocument(d.Name)
    root = os.environ["XD_DIR"]
    os.makedirs(os.path.join(root, "parts"), exist_ok=True)
    sk = App.newDocument("fxp_skeleton")
    part = sk.addObject("App::Part", "Skeleton")
    ps = sk.addObject("Spreadsheet::Sheet", "Params")
    ps.set("A1", "plate_length")
    ps.set("B1", "10 mm")
    ps.setAlias("B1", "plate_length")
    sk.recompute()
    sk.saveAs(os.path.join(root, "fxp-skeleton.FCStd"))
    pd = App.newDocument("plate")
    box = pd.addObject("Part::Box", "Plate")
    pd.saveAs(os.path.join(root, "parts", "plate.FCStd"))      # saved before the cross-document expression
    box.setExpression("Length", "fxp_skeleton#Params.plate_length")
    pd.recompute()
    pd.save()
    top = App.newDocument("fxp")
    asm = top.addObject("Assembly::AssemblyObject", "Assembly")
    top.saveAs(os.path.join(root, "fxp.FCStd"))
    for name, target in (("Skeleton", part), ("PlateLink", box)):
        ln = top.addObject("App::Link", name)
        ln.setLink(target)
        asm.addObject(ln)
    top.recompute()
    top.save()
    out = {"ok": True, "length": box.Length.Value}
    for d in list(App.listDocuments().values()):
        App.closeDocument(d.Name)
except Exception:
    out["error"] = traceback.format_exc()
if res:
    with open(res, "w") as f:
        json.dump(out, f)
