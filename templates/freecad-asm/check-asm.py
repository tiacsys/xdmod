# FreeCADCmd script of the ME checks CK-F4c, CK-F16, CK-F17 and CK-F18 (tasks 5.25, 5.28). Run only
# through curatrix (`curatrix check`): workspace-local FreeCAD config, limits. Inputs by
# environment variables, because FreeCADCmd opens extra arguments as files (FreeCAD spike):
#   XD_FILES   JSON list of the documents to open, in this order (per assembly the skeleton, then the
#              top document, so the parts load fully through its links; then every other document)
#   XD_LIB     the repo's lib/ folder (library fasteners live there)
#   XD_SEATS   JSON {ME-PORT: {width, depth, heightAbove, heightBelow, [mountZoneDiameter,
#              hole<n>X, hole<n>Y]}} of the board seats (CK-F18): the ME seat ports that specialize a
#              SYS-IF space budget, with the budget's values (a seat may lack some: then only the seat
#              is reported, without bbox and intrusions). With mountZoneDiameter, a cylinder of that
#              diameter around each hole, through the whole box height, is cut from the box first
#   XD_RESULT  the result file (JSON)
# FreeCADCmd exits 0 when a script raises, so the caller judges success by the result file only; the
# script never raises and is safe to run twice. It never saves a document.
#
# Result:
#   recompute: [{doc, object, type, state}]       objects that are not valid after a recompute
#   solids:    [{doc, object, id, problem}]        objects with an ME-PART TraceID whose shape is not
#                                                  valid solids
#   parts:     [{doc, object, id}]                 every object with an ME-PART TraceID (checked)
#   assemblies: [{doc, object, id, children: [{name, label, file, object, id, kind, configs}],
#                 joined: [[a, b]], overlaps: [{a, b, volume}]}]
#              children are the direct links of the assembly object (Group), without the skeleton;
#              kind: part | fastener (a lib/ object with a Standard property) | board (an EE-PCBA
#              TraceID); overlaps: common volume of each pair of non-fastener children (mm^3)
#   budgets:   per assembly, one entry per board child (CK-F18): {board, seat (the LCS whose
#              placement in the assembly equals the board link's, or ""), port, placement,
#              bbox (the board's bounding box in the seat frame: xmin, ymin, zmin, xmax, ymax, zmax),
#              zones: the number of mounting zones cut from the box,
#              intrusions: [{name, volume, z}] the non-fastener parts inside the budget box
#              (common volume in mm^3, its z range in the seat frame), fasteners: [{name, volume}]
#              common volume of the board with each fastener}
import json
import os
import traceback

import FreeCAD as App

res = os.environ.get("XD_RESULT", "")
out = {"ok": False}
TOL = 1e-6          # report every overlap above this; the caller applies the check's tolerances


def tid(o):
    return str(getattr(o, "TraceID", "") or "").strip() if "TraceID" in o.PropertiesList else ""


def kind_of(i):
    parts = i.split("-")
    return "-".join(parts[:2]) if len(parts) >= 3 else ""


def exploded_proxy(o):
    """An object of the Assembly workbench's exploded view: its Python proxy cannot load in
    FreeCADCmd (CommandCreateView imports QtCore), so its error is not a design error."""
    if not o.TypeId.startswith(("App::FeaturePython", "Part::FeaturePython", "Assembly::")):
        return False
    t = str(getattr(o, "Type", "") or "") + o.Name + o.TypeId
    return getattr(o, "Proxy", 1) is None and ("Explode" in t or "ViewGroup" in t or "View" in o.TypeId)


def solid_problem(sh):
    if sh is None or sh.isNull():
        return "no shape"
    if not sh.isValid():
        return "the shape is not valid (Part check)"
    if not sh.Solids:
        return f"no solid (shape type {sh.ShapeType})"
    bad = [i for i, s in enumerate(sh.Solids) if not s.isValid() or s.Volume <= 0]
    if bad:
        return f"solid(s) {bad} not valid or without volume"
    free = len(sh.Shells) - sum(len(s.Shells) for s in sh.Solids)
    if free > 0 or len(sh.Faces) != sum(len(s.Faces) for s in sh.Solids):
        return "faces or shells outside the solids"
    return ""


def rel(path):
    return os.path.realpath(path)


def seat_places(d, skels, seats):
    """(LCS name, ME-PORT, placement in the assembly) of every seat LCS reached through the
    skeleton link(s) of the assembly: the link's placement replaces its target container's, so an
    LCS inside the linked App::Part is at link * LCS, any other at link * its global placement."""
    out = []
    for c in d.Objects:
        if not c.TypeId.startswith("App::Link") or c.Name not in skels:
            continue
        t = c.getLinkedObject(True)
        if t is None or not (t.Document.FileName or "").endswith("-skeleton.FCStd"):
            continue
        for o in t.Document.Objects:
            port = str(getattr(o, "Port", "") or "").strip() if "Port" in o.PropertiesList else ""
            if port not in seats:
                continue
            inside = o.getParentGeoFeatureGroup() == t
            out.append((o.Name, port, c.Placement.multiply(o.Placement if inside else o.getGlobalPlacement())))
    return out


def same_place(a, b):
    return (a.Base - b.Base).Length < 1e-4 and a.Rotation.isSame(b.Rotation, 1e-6)


def budget_of(d, kids, skels, seats, board):
    """CK-F18 data of one board child (see the header)."""
    import Part
    lk = d.getObject(board["name"])
    pl = lk.Placement
    hit = next(((n, p, sp) for n, p, sp in seat_places(d, skels, seats) if same_place(sp, pl)), None)
    e = {"board": board["name"], "seat": hit[0] if hit else "", "port": hit[1] if hit else "",
         "placement": [round(v, 6) for v in (pl.Base.x, pl.Base.y, pl.Base.z)], "intrusions": [], "fasteners": []}
    sh = lk.Shape
    for k in kids:
        if k["kind"] == "fastener":
            f = d.getObject(k["name"]).Shape
            if not f.isNull() and not sh.isNull() and f.BoundBox.intersect(sh.BoundBox):
                v = sh.common(f).Volume
                if v > TOL:
                    e["fasteners"].append({"name": k["name"], "volume": round(v, 6)})
    if not hit:
        return e
    seat = hit[2]
    b = seats[hit[1]]
    if any(k not in b for k in ("width", "depth", "heightAbove", "heightBelow")):
        return e                            # the caller names the missing value; no box to check
    loc = sh.transformed(seat.inverse().toMatrix())
    bb = loc.BoundBox
    e["bbox"] = [round(v, 6) for v in (bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax)]
    h = b["heightAbove"] + b["heightBelow"]
    box = Part.makeBox(b["width"], b["depth"], h, App.Vector(0, 0, -b["heightBelow"]))
    holes = sorted({k[:-1] for k in b if k.startswith("hole") and k[-1:] in "XY" and k[4:-1].isdigit()})
    zone = b.get("mountZoneDiameter") or 0
    e["zones"] = 0
    for n in holes if zone > 0 else ():
        if n + "X" in b and n + "Y" in b:   # the zone: a cylinder through the whole box height, 1 mm beyond it
            box = box.cut(Part.makeCylinder(zone / 2, h + 2, App.Vector(b[n + "X"], b[n + "Y"], -b["heightBelow"] - 1)))
            e["zones"] += 1
    for k in kids:
        if k["kind"] != "part":
            continue
        o = d.getObject(k["name"]).Shape
        if o.isNull():
            continue
        lo = o.transformed(seat.inverse().toMatrix())
        if not lo.BoundBox.intersect(box.BoundBox):
            continue
        c = box.common(lo)
        if c.Volume > TOL:
            e["intrusions"].append({"name": k["name"], "volume": round(c.Volume, 6),
                                    "z": [round(c.BoundBox.ZMin, 6), round(c.BoundBox.ZMax, 6)]})
    return e


try:
    for d in list(App.listDocuments().values()):
        App.closeDocument(d.Name)
    files = json.loads(os.environ["XD_FILES"])
    lib = rel(os.environ.get("XD_LIB", "")) + os.sep if os.environ.get("XD_LIB") else None
    seats = json.loads(os.environ.get("XD_SEATS") or "{}")
    for f in files:
        if not any(rel(d.FileName) == rel(f) for d in App.listDocuments().values()):
            App.openDocument(f)
    partial = [d.Name for d in App.listDocuments().values() if getattr(d, "Partial", False)]
    for n in partial:                       # load it fully (a document opened only through a link)
        App.getDocument(n).restore()
    alld = list(App.listDocuments().values())
    deps = {d.Name: {x.Document.Name for o in d.Objects for x in o.OutList if x.Document is not d} for d in alld}
    docs, left = [], {d.Name: d for d in alld}
    cycle = []
    while left:
        ready = sorted(n for n in left if not (deps[n] & set(left)))
        if not ready:
            cycle = sorted(left)
            ready = cycle
        docs += [left.pop(n) for n in ready]
    for d in docs:
        for o in d.Objects:
            o.touch()
        d.recompute()
    recompute = []
    for d in docs:
        for o in d.Objects:
            if not o.isValid() and not exploded_proxy(o):
                recompute.append({"doc": rel(d.FileName), "object": o.Name, "type": o.TypeId,
                                  "state": [str(s) for s in o.State]})
    parts, solids = [], []
    for d in docs:
        for o in d.Objects:
            i = tid(o)
            if kind_of(i) != "ME-PART":
                continue
            parts.append({"doc": rel(d.FileName), "object": o.Name, "id": i})
            p = solid_problem(getattr(o, "Shape", None))
            if p:
                solids.append({"doc": rel(d.FileName), "object": o.Name, "id": i, "problem": p})
    asms = []
    for d in docs:
        for a in d.Objects:
            if kind_of(tid(a)) != "ME-ASM":
                continue
            kids, skels = [], []
            for c in getattr(a, "Group", []) or []:
                if not c.TypeId.startswith("App::Link"):
                    continue
                t = c.getLinkedObject(True)
                tf = rel(t.Document.FileName) if t is not None and t.Document.FileName else ""
                if tf.endswith("-skeleton.FCStd"):
                    skels.append(c.Name)
                    continue
                k = "part"
                if t is not None and lib and tf.startswith(lib) and str(getattr(t, "Standard", "") or "").strip():
                    k = "fastener"
                if t is not None and kind_of(tid(t)) == "EE-PCBA":
                    k = "board"
                kids.append({"name": c.Name, "label": c.Label, "file": tf, "object": t.Name if t else "",
                             "id": tid(t) if t is not None else "", "kind": k,
                             # the link's own Configs only: an App::Link passes unknown
                             # attributes on to its target (the same rule as `curatrix cam`)
                             "configs": str(c.Configs or "") if "Configs" in c.PropertiesList else ""})
            names = {k["name"] for k in kids}
            joined = []
            for j in d.Objects:
                if "Reference1" not in j.PropertiesList or "Reference2" not in j.PropertiesList:
                    continue
                ends = []
                for p in ("Reference1", "Reference2"):
                    v = getattr(j, p)
                    obj, subs = (v[0], v[1]) if isinstance(v, (tuple, list)) and v else (v, [])
                    subs = [subs] if isinstance(subs, str) else list(subs or [])
                    hit = None
                    if obj is not None and obj.Name in names:
                        hit = obj.Name
                    for s in subs:
                        for x in s.split("."):
                            if x in names:
                                hit = hit or x
                    ends.append(hit)
                if all(ends) and ends[0] != ends[1]:
                    joined.append(sorted(ends))
            overlaps = []
            solid = {k["name"]: d.getObject(k["name"]).Shape for k in kids if k["kind"] != "fastener"}
            ns = sorted(solid)
            for x in range(len(ns)):
                for y in range(x + 1, len(ns)):
                    a_, b_ = solid[ns[x]], solid[ns[y]]
                    if a_.isNull() or b_.isNull() or not a_.BoundBox.intersect(b_.BoundBox):
                        continue
                    v = a_.common(b_).Volume
                    if v > TOL:
                        overlaps.append({"a": ns[x], "b": ns[y], "volume": round(v, 6)})
            asms.append({"doc": rel(d.FileName), "object": a.Name, "id": tid(a), "children": kids,
                         "joined": sorted(joined), "overlaps": overlaps,
                         "budgets": [budget_of(d, kids, skels, seats, k) for k in kids if k["kind"] == "board"],
                         "bbox": {k["name"]: [round(v, 6) for v in (lambda b: (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax))(d.getObject(k["name"]).Shape.BoundBox)]
                                  for k in kids if k["kind"] == "board"}})
    out = {"ok": True, "order": [rel(d.FileName) for d in docs], "cycle": cycle, "recompute": recompute,
           "parts": parts, "solids": solids, "assemblies": asms}
    for d in reversed(docs):
        App.closeDocument(d.Name)
except Exception:
    out["error"] = traceback.format_exc()
if res:
    with open(res, "w") as f:
        json.dump(out, f, indent=1)
