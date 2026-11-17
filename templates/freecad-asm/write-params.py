# FreeCADCmd script of `curatrix gen freecad-params` (task 5.24, XD-ADR-0137). Run only through
# curatrix. Inputs by environment variables: XD_TOP (top document), XD_SKELETON (<name>-skeleton.FCStd),
# XD_PARAMS (JSON {alias: "12 mm"}), XD_RESULT. Success only by the result file (FreeCADCmd exits
# 0 when a script raises); the script never raises and is safe to run twice.
#
# Order (FreeCAD spike §1, XD-ADR-0146): open the skeleton, then the top document, so the parts load
# fully through its links; write the values into Params (values only, never rebuild objects: no
# object-ID churn); recompute the documents in dependency order (skeleton, parts, sub-assemblies,
# top: a document after every document it refers to); check every object; save only the documents
# whose values or own shapes changed. A link's shape is the linked part's, so links are left out of
# that comparison (also groups: App::Part, the assembly object): a top document whose links only follow a changed part is not saved (its XLink
# stamps would be the only change). Aliases the model no longer has stay in Params (CK-F3 reports
# them); removing one is a manual step.
import json
import os
import traceback

import FreeCAD as App

res = os.environ.get("XD_RESULT", "")
out = {"ok": False}


def state(doc):
    """What a save would change: placements, shape volumes and bounding boxes, cell contents."""
    s = {}
    for o in doc.Objects:
        e = [str(getattr(o, "Placement", ""))]
        # links and groups (App::Part, the assembly) only show the shapes of what they hold
        sh = None if o.TypeId.startswith(("App::Link", "App::Part", "Assembly::")) else getattr(o, "Shape", None)
        if sh is not None and not sh.isNull():
            bb = sh.BoundBox
            e += [round(sh.Volume, 6)] + [round(x, 6) for x in (bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax)]
        if o.TypeId == "Spreadsheet::Sheet":
            e += [str(o.getContents(c)) for c in sorted(o.getUsedCells())]
        if o.TypeId == "Sketcher::SketchObject":
            e += [round(c.Value, 6) for c in o.Constraints if c.Name]
        s[o.Name] = e
    return s


try:
    for d in list(App.listDocuments().values()):
        App.closeDocument(d.Name)
    want = json.load(open(os.environ["XD_PARAMS"]))
    # the skeleton first: the top links only its part "Skeleton", so through the top FreeCAD loads
    # the skeleton partially (without Params); it depends on no other document
    sk = App.openDocument(os.path.realpath(os.environ["XD_SKELETON"]))
    top = App.openDocument(os.environ["XD_TOP"])
    partial = [d.Name for d in App.listDocuments().values() if getattr(d, "Partial", False)]
    if partial:
        raise RuntimeError(f"partially loaded documents: {partial}")
    # dependency order: a document after every document its objects refer to (links, expressions)
    alld = list(App.listDocuments().values())
    deps = {d.Name: {x.Document.Name for o in d.Objects for x in o.OutList if x.Document is not d} for d in alld}
    docs, left = [], {d.Name: d for d in alld}
    while left:
        ready = sorted(n for n in left if not (deps[n] & set(left)))
        if not ready:
            raise RuntimeError(f"documents refer to each other in a cycle: {sorted(left)}")
        docs += [left.pop(n) for n in ready]
    before = {d.Name: state(d) for d in docs}
    ps = sk.getObject("Params")
    if ps is None:
        raise RuntimeError("skeleton.FCStd has no spreadsheet Params (`curatrix new asm` makes it)")
    changed = []
    used = ps.getUsedCells()
    row = max([int("".join(ch for ch in c if ch.isdigit())) for c in used] or [0]) + 1
    for alias, text in sorted(want.items()):
        cell = ps.getCellFromAlias(alias)
        if cell is None:
            ps.set(f"A{row}", alias)
            cell = f"B{row}"
            ps.set(cell, text)
            ps.setAlias(cell, alias)
            row += 1
            changed.append(alias)
        elif str(ps.getContents(cell)).lstrip("=").strip() != text:
            ps.set(cell, text)
            changed.append(alias)
    for d in docs:
        d.recompute()
    invalid = [f"{d.Name}#{o.Name}: {o.State}" for d in docs for o in d.Objects
               if not o.isValid()]
    saved = []
    if not invalid:
        for d in docs:
            if state(d) != before[d.Name]:
                d.save()
                saved.append(d.FileName)
    out = {"ok": not invalid, "changed": changed, "saved": saved, "invalid": invalid,
           "order": [os.path.basename(d.FileName) for d in docs],
           "values": {a: str(ps.get(ps.getCellFromAlias(a))) for a in sorted(want)}}
    for d in reversed(docs):
        App.closeDocument(d.Name)
except Exception:
    out["error"] = traceback.format_exc()
if res:
    with open(res, "w") as f:
        json.dump(out, f)
