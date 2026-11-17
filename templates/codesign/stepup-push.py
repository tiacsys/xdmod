# The co-design push (XD-ADR-0134, task 5.28): KiCad StepUp writes the sketch BoardOutline of an
# assembly skeleton (outline and mounting holes, in the board frame) into the Edge.Cuts layer of a
# COPY of a .kicad_pcb. FreeCAD GUI binary offscreen (StepUp imports FreeCADGui), HOME sandboxed for
# this process only (StepUp writes ~/ksu-config.ini). Steps and run line:
# docs/xdmod-manual/howto/co-design-change.rst. Inputs by environment variables:
#   XD_STEPUP   the StepUp clone, pinned by commit (.xdmod/stepup/kicadStepUpMod)
#   XD_BOARD    the .kicad_pcb COPY to push into (never a repo file)
#   XD_SKELETON the skeleton .FCStd (a copy is fine); XD_SKETCH the sketch (default BoardOutline)
#   XD_RESULT   JSON result file; success only by this file (the script never raises)
# The board frame origin lands on KiCad's grid origin if the board sets one, else on the lower-left
# corner of the existing Edge.Cuts outline, so a push keeps the board where EE placed it. Afterwards:
# kicad-cli pcb upgrade --force on the copy (re-save by KiCad 10), DRC, then copy it back.
import json, os, re, sys, traceback
import FreeCAD as App, Part

res = os.environ["XD_RESULT"]
out = {"ok": False, "log": []}


def say(*a):
    out["log"].append(" ".join(str(x) for x in a))


def anchor(text):
    m = re.search(r"\(grid_origin\s+([-\d.]+)\s+([-\d.]+)\)", text)
    if m and (float(m.group(1)), float(m.group(2))) != (0.0, 0.0):
        return float(m.group(1)), float(m.group(2)), "grid_origin"
    xs, ys = [], []
    for blk in re.finditer(r"\(gr_(?:rect|line)\s+\(start ([-\d.]+) ([-\d.]+)\)\s+\(end ([-\d.]+) ([-\d.]+)\)(.*?)\(layer \"Edge\.Cuts\"\)",
                           text, re.S):
        if "(gr_" in blk.group(5):
            continue
        xs += [float(blk.group(1)), float(blk.group(3))]
        ys += [float(blk.group(2)), float(blk.group(4))]
    if not xs:
        raise RuntimeError("no grid origin and no Edge.Cuts outline: cannot place the board frame")
    return min(xs), max(ys), "outline lower-left"


try:
    sys.path.insert(0, os.environ["XD_STEPUP"])
    say("GuiUp", App.GuiUp, "HOME", os.environ.get("HOME"), "UserConfig", App.getUserConfigDir())
    import kicadStepUptools as ksu
    out["stepup_version"] = getattr(ksu, "___ver___", "?")
    # modal dialogs block an offscreen run: replace them by logging
    for name in ("say_warning", "say_error", "say_info"):
        if hasattr(ksu, name):
            setattr(ksu, name, (lambda n: lambda msg, *a, **k: say(n + ":", re.sub("<[^>]+>", " ", str(msg))))(name))
    from PySide import QtGui
    for cls in (QtGui.QDialog, QtGui.QMessageBox):          # any modal exec_ returns at once
        cls.exec_ = lambda self, *a, **k: (say("exec_ of", type(self).__name__), 0)[1]
    for name in ("information", "warning", "critical", "question"):
        setattr(QtGui.QMessageBox, name, staticmethod((lambda n: lambda *a, **k: say("QMessageBox." + n + ":", a[2] if len(a) > 2 else a))(name)))

    board = os.environ["XD_BOARD"]
    text = open(board, encoding="utf-8").read()
    ax, ay, how = anchor(text)
    out["anchor"] = [ax, ay, how]
    # geometry in the board frame
    skp = os.environ.get("XD_SKELETON")
    if not skp:
        raise RuntimeError("XD_SKELETON is not set")
    sdoc = App.openDocument(skp)
    sdoc.recompute()
    src = sdoc.getObject(os.environ.get("XD_SKETCH", "BoardOutline"))
    if src is None:
        raise RuntimeError(f"no sketch {os.environ.get('XD_SKETCH', 'BoardOutline')} in {skp}")
    geo = [g.copy() for i, g in enumerate(src.Geometry) if not src.getConstruction(i)]
    out["source"] = f"{os.path.basename(skp)}#{src.Name}"
    out["frame_geometry"] = [type(g).__name__ for g in geo]
    # board frame -> KiCad page: StepUp writes (x, -y) (grid origin 0,0), so shift by (ax, -ay)
    doc = App.newDocument("push")
    sk = doc.addObject("Sketcher::SketchObject", "PCB_Sketch")
    shift = App.Matrix(); shift.move(App.Vector(ax, -ay, 0))
    for g in geo:
        g.transform(shift)
        sk.addGeometry(g)
    doc.recompute()
    # export_pcb reads the sketch from the GUI selection and times itself (globals of the GUI command)
    import FreeCADGui as Gui
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(sk)
    ksu.start_time = ksu.current_milli_time()
    ksu.export_pcb(board, "Edge.Cuts", "PCB_Sketch")
    say("export_pcb done")
    new = open(board, encoding="utf-8").read()
    out["edge_items"] = re.findall(r"\(gr_(?:line|circle|arc|rect)[^\n]*Edge\.Cuts[^\n]*", new)
    out["pushed"] = new != text
    out["ok"] = True
except Exception:
    out["error"] = traceback.format_exc()
finally:
    with open(res, "w") as f:
        json.dump(out, f, indent=1)
    os._exit(0)
