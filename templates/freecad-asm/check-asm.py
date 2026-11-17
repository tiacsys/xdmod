# FreeCADCmd script of the ME checks CK-F4c, CK-F16, CK-F17 and CK-F18 (task 5.25). Run only
# through curatrix (`curatrix check`): workspace-local FreeCAD config, limits. Inputs by
# environment variables, because FreeCADCmd opens extra arguments as files (FreeCAD spike):
#   XD_FILES   JSON list of the documents to open, in this order (per assembly the skeleton, then the
#              top document, so the parts load fully through its links; then every other document)
#   XD_LIB     the repo's lib/ folder (library fasteners live there)
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


try:
    for d in list(App.listDocuments().values()):
        App.closeDocument(d.Name)
    files = json.loads(os.environ["XD_FILES"])
    lib = rel(os.environ.get("XD_LIB", "")) + os.sep if os.environ.get("XD_LIB") else None
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
            kids = []
            for c in getattr(a, "Group", []) or []:
                if not c.TypeId.startswith("App::Link"):
                    continue
                t = c.getLinkedObject(True)
                tf = rel(t.Document.FileName) if t is not None and t.Document.FileName else ""
                if tf.endswith("-skeleton.FCStd"):
                    continue
                k = "part"
                if t is not None and lib and tf.startswith(lib) and str(getattr(t, "Standard", "") or "").strip():
                    k = "fastener"
                if t is not None and kind_of(tid(t)) == "EE-PCBA":
                    k = "board"
                kids.append({"name": c.Name, "label": c.Label, "file": tf, "object": t.Name if t else "",
                             "id": tid(t) if t is not None else "", "kind": k,
                             "configs": str(getattr(c, "Configs", "") or "")})
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
