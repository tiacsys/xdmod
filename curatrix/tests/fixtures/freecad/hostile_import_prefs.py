# FreeCADCmd script for test_boardlib.py (finding 17 of xdmod#69, review of #75): sets import
# preferences that break or stall the board-model import if import-step.py did not pin them
# (ImportMode 2 stalls the offscreen GUI binary until the time limit), saves them into the
# (test-local) FreeCAD config, and writes a small assembly STEP to import. Inputs: XD_STEP (the STEP
# to write), XD_RESULT. Run only through curatrix (newasm.run_script).
import json
import os
import traceback

out = {"ok": False}
try:
    import FreeCAD as App
    import Import
    import Part
    g = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Import")
    g.SetInt("ImportMode", 2)
    for name, value in (("UseBaseName", True), ("UseLinkGroup", False), ("ReduceObjects", True),
                        ("ExpandCompound", True), ("ReadShowDialogImport", True)):
        g.SetBool(name, value)
    App.ParamGet("User parameter:BaseApp/Preferences/Mod/Import/hSTEP").SetBool("ReadShowDialogImport", True)
    App.saveParameter()
    doc = App.newDocument("hostile")
    top = doc.addObject("App::Part", "Assembly")
    for i, x in enumerate((0, 20), 1):
        b = doc.addObject("Part::Feature", f"R{i}")
        b.Shape = Part.makeBox(10, 5, 3, App.Vector(x, 0, 0))
        top.addObject(b)
    pcb = doc.addObject("Part::Feature", "PCB")
    pcb.Shape = Part.makeBox(40, 20, 1.6, App.Vector(-5, -5, -1.6))
    top.addObject(pcb)
    doc.recompute()
    Import.export([top], os.environ["XD_STEP"])
    out = {"ok": os.path.isfile(os.environ["XD_STEP"]), "import_mode": g.GetInt("ImportMode")}
except Exception:
    out["error"] = traceback.format_exc()
with open(os.environ["XD_RESULT"], "w") as f:
    json.dump(out, f)
