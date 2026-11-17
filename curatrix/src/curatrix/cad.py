"""CAD readers in plain Python (no KiCad or FreeCAD needed) and CAD-derived needs (D29, D110, D128, D130).

Trace fields (id-scheme.md §5), the same names in both tools:

    TraceID     the need ID (EE-CMP, ME-PART); on a KiCad project or a FreeCAD top document the
                ID of its domain def (EE-PCBA, ME-ASM), a reference only (XD-ADR-0128)
    Realizes    comma list of IDs  -> realizes
    Satisfies   comma list         -> satisfies
    Conforms    comma list         -> conforms
    PartOf      comma list         -> part_of
    Status      draft | valid | retired (D130; default valid)
    Configs     comma list of SYS-CFG IDs (D103)

KiCad: hidden symbol fields and sheet fields in ``.kicad_sch`` (hierarchical sheets are
followed); the PCBA itself from ``text_variables`` of the ``.kicad_pro`` (TraceID, Realizes, ...).
A sheet file used several times carries one ID; its usages are listed in ``instances`` (D128).
The XML netlist of ``kicad-cli sch export netlist --format kicadxml`` can be read instead.

FreeCAD: object properties in ``Document.xml`` inside the ``.FCStd`` zip.
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from curatrix import ids as idmod

# kinds the domain model owns (XD-ADR-0128): a CAD file names them, it does not make the need
MODEL_OWNED = ("EE-PCBA", "EE-PORT", "EE-HAR", "ME-ASM", "ME-PORT")
LINK_FIELDS = {"Realizes": "realizes", "Satisfies": "satisfies", "Conforms": "conforms", "PartOf": "part_of"}
TRACE_FIELDS = ("TraceID", *LINK_FIELDS, "Status", "Configs", "Port")
# `Port` on a FreeCAD LCS (or a KiCad connector) names the ME-PORT / EE-PORT of the domain model
# it implements: a reference, never a need (XD-ADR-0128, XD-ADR-0133)


def _list(v: str | None) -> list[str]:
    return [x.strip() for x in re.split(r"[,\s]+", v or "") if x.strip()]


def trace_need(fields: dict[str, str], title: str, content: str, source: str,
               refs: list | None = None) -> tuple[dict | None, list[str]]:
    """A need from trace fields, or (None, findings) if there is no (valid) TraceID. A TraceID of a
    model-owned kind is a reference: no need; it goes into `refs` as (ID, source), and link fields
    next to it are findings, since nothing reads them (XD-ADR-0128)."""
    tid = (fields.get("TraceID") or "").strip()
    if not tid:
        return None, []
    kind = idmod.kind_of(tid)
    if kind is None:
        return None, [f"{source}: TraceID {tid!r} is not a valid ID"]
    if kind in MODEL_OWNED:
        if refs is not None:
            refs.append((tid, source))
        unread = [f for f in (*LINK_FIELDS, "Status", "Configs") if (fields.get(f) or "").strip()]
        return None, [f"{source}: {tid} is owned by the domain model; {', '.join(unread)} next to it "
                      f"{'is' if len(unread) == 1 else 'are'} not read (links come from the model): remove "
                      f"{'it' if len(unread) == 1 else 'them'}"] if unread else []
    n = {"id": tid, "type": idmod.directive_of(kind), "title": title, "content": content,
         "status": (fields.get("Status") or "valid").strip() or "valid", "source_file": source}
    findings = []
    if n["status"] not in ("draft", "valid", "retired"):
        findings.append(f"{source}: {tid}: Status {n['status']!r} is not draft, valid or retired")
    for f, link in LINK_FIELDS.items():
        vals = _list(fields.get(f))
        bad = [v for v in vals if not idmod.valid_id(v)]
        if bad:
            findings.append(f"{source}: {tid}: {f} holds invalid IDs {bad}")
        if vals:
            n[link] = sorted(set(vals) - set(bad))
    cfgs = _list(fields.get("Configs"))
    if cfgs:
        n["configs"] = sorted(cfgs)
    return n, findings


# ------------------------------------------------------------------ KiCad
def sexpr(text: str):
    """Parse a KiCad S-expression file into nested lists of str (atoms and strings)."""
    tok = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+')
    stack: list[list] = [[]]
    for m in tok.finditer(text):
        t = m.group(0)
        if t == "(":
            stack.append([])
        elif t == ")":
            done = stack.pop()
            stack[-1].append(done)
        elif t.startswith('"'):
            stack[-1].append(re.sub(r'\\(.)', lambda m: "\n" if m.group(1) == "n" else m.group(1), t[1:-1]))
        else:
            stack[-1].append(t)
    return stack[0][0] if stack[0] else []


def _children(node, name):
    return [c for c in node[1:] if isinstance(c, list) and c and c[0] == name]


def _props(node) -> dict[str, str]:
    return {c[1]: c[2] for c in _children(node, "property") if len(c) >= 3}


@dataclass
class KicadItem:
    kind: str                 # symbol | sheet | project
    fields: dict
    sheet_path: str           # e.g. /joint1/ (instance path through the hierarchy)
    file: str                 # schematic file (relative to the repo)
    ref: str = ""
    value: str = ""
    footprint: str = ""
    instances: list = field(default_factory=list)


def kicad_items(root_sch: Path, repo: Path) -> list[KicadItem]:
    """Symbols and sheets with their fields, through the sheet hierarchy (root first)."""
    out: list[KicadItem] = []

    def uuid_of(node) -> str:
        u = _children(node, "uuid")
        return u[0][1] if u and len(u[0]) > 1 else ""

    def instance_ref(sym, upath: str) -> str | None:
        for inst in _children(sym, "instances"):
            for proj in _children(inst, "project"):
                for p in _children(proj, "path"):
                    if len(p) > 1 and p[1] == upath:
                        r = _children(p, "reference")
                        if r and len(r[0]) > 1:
                            return r[0][1]
        return None

    def visit(sch: Path, path: str, upath: str | None, depth: int):
        if depth > 20:
            return
        tree = sexpr(sch.read_text(encoding="utf-8"))
        if upath is None:
            upath = "/" + uuid_of(tree)
        rel = str(sch.resolve().relative_to(repo.resolve())) if repo.resolve() in sch.resolve().parents else str(sch)
        for s in _children(tree, "symbol"):
            if not _children(s, "lib_id"):
                continue
            p = _props(s)
            ref = instance_ref(s, upath) or p.get("Reference", "")
            out.append(KicadItem("symbol", p, path, rel, ref=ref, value=p.get("Value", ""),
                                 footprint=p.get("Footprint", "")))
        for sh in _children(tree, "sheet"):
            p = _props(sh)
            name = p.get("Sheetname") or p.get("Sheet name", "")
            sub = p.get("Sheetfile") or p.get("Sheet file", "")
            out.append(KicadItem("sheet", p, path + name + "/", str(Path(rel).parent / sub) if sub else rel,
                                 value=Path(sub).stem if sub else name))
            if sub and (sch.parent / sub).is_file():
                visit(sch.parent / sub, path + name + "/", upath + "/" + uuid_of(sh), depth + 1)

    visit(root_sch, "/", None, 0)
    pro = root_sch.with_suffix(".kicad_pro")
    if pro.is_file():
        tv = (json.loads(pro.read_text()).get("text_variables") or {})
        if tv.get("TraceID"):
            out.insert(0, KicadItem("project", dict(tv), "/", str(pro.resolve().relative_to(repo.resolve()))
                                    if repo.resolve() in pro.resolve().parents else str(pro),
                                    value=pro.stem))
    return out


def kicad_netlist_items(netlist: Path, source: str) -> list[KicadItem]:
    """Components of a kicad-cli XML netlist (`--format kicadxml`), with their fields."""
    out = []
    for comp in ET.parse(netlist).getroot().iter("comp"):
        f = {x.get("name"): (x.text or "") for x in comp.iter("field")}
        sp = comp.find("sheetpath")
        out.append(KicadItem("symbol", f, sp.get("names") if sp is not None else "/", source,
                             ref=comp.get("ref", ""), value=comp.findtext("value") or "",
                             footprint=comp.findtext("footprint") or ""))
    return out


def kicad_needs(items: list[KicadItem], refs: list | None = None) -> tuple[dict[str, dict], list[str]]:
    needs: dict[str, dict] = {}
    findings: list[str] = []
    for it in items:
        if it.kind == "project":
            title, content = it.value, f"KiCad project ``{it.file}``."
        elif it.kind == "sheet":
            title, content = it.value, f"KiCad sheet file ``{it.file}`` (hierarchical sheet)."
        else:
            title = it.value or it.ref
            content = (f"KiCad symbol ``{it.ref}`` ({it.value}, footprint ``{it.footprint or '-'}``) "
                       f"in ``{it.file}``.")
        n, f = trace_need(it.fields, title, content, it.file, refs)
        findings += f
        if n is None:
            continue
        inst = f"{it.sheet_path}{it.ref}" if it.kind == "symbol" else it.sheet_path
        old = needs.get(n["id"])
        if old is None:
            n["instances"] = [inst]
            needs[n["id"]] = n
            continue
        # the same ID again: fine for a sheet file / symbol used several times (D128) if the
        # trace fields agree; otherwise two things claim one ID
        if {k: v for k, v in old.items() if k not in ("instances", "content")} != \
           {k: v for k, v in n.items() if k not in ("instances", "content")}:
            findings.append(f"{it.file}: {n['id']} is used by different items with different trace fields")
        old["instances"].append(inst)
    for n in needs.values():
        n["instances"] = sorted(set(n["instances"]))
        if len(n["instances"]) <= 1:
            del n["instances"]
    return needs, findings


# ------------------------------------------------------------------ FreeCAD
_NOISE_DOC = {"CreationDate", "LastModifiedDate", "LastModifiedBy", "CreatedBy", "Uid", "FileName",
              "TransientDir", "Id", "Tip", "TipName", "Material", "Meta", "UnitSystem", "UseHasher",
              "License", "LicenseURL", "Comment", "Company", "ShowHidden"}


def _prop_value(p: ET.Element):
    for child in p:
        tag = child.tag
        if tag in ("String", "Bool", "Integer", "Float", "Uuid"):
            v = child.get("value")
            if tag == "Float":
                try:
                    return round(float(v), 6)
                except (TypeError, ValueError):
                    return v
            return v
        if tag == "PropertyPlacement":
            a = child.attrib
            return {k: round(float(a[k]), 6) for k in ("Px", "Py", "Pz", "Q0", "Q1", "Q2", "Q3") if k in a}
        if tag == "Link":
            return child.get("value")
        if tag == "LinkList":
            return [x.get("value") for x in child.findall("Link")]
        if tag == "Cells":
            return {c.get("alias") or c.get("address"): c.get("content", "").lstrip("=")
                    for c in child.findall("Cell")}
    return None


def _xlinks(p: ET.Element) -> list[dict]:
    """Targets of a link property (``App::PropertyLink*``, ``App::PropertyXLink*``) as
    ``{file, object, sub}``: ``file`` is relative to the linking document ("" = the same
    document); the ``stamp`` (the other file's save time) is noise and left out."""
    out = []
    for x in p.iter():
        if x.tag == "XLink" and x.get("name"):
            e = {"file": x.get("file") or "", "object": x.get("name")}
            subs = [s.get("value") for s in x.findall("Sub") if s.get("value")] or \
                   ([x.get("sub")] if x.get("sub") else [])
            if subs:
                e["sub"] = subs
            out.append(e)
        elif x.tag == "Link" and (x.get("value") or x.get("obj")):
            # PropertyLink(List) writes value=, PropertyLinkSubList obj= and sub=
            e = {"file": "", "object": x.get("value") or x.get("obj")}
            if x.get("sub"):
                e["sub"] = [x.get("sub")]
            out.append(e)
        elif x.tag == "LinkSub" and x.get("value"):
            e = {"file": "", "object": x.get("value")}
            subs = [s.get("value") for s in x.findall("Sub") if s.get("value")]
            if subs:
                e["sub"] = subs
            out.append(e)
    return out


def _expressions(p: ET.Element) -> dict[str, str]:
    return {e.get("path"): e.get("expression") for e in p.iter("Expression") if e.get("path")}


def _constraints(p: ET.Element) -> dict[str, float]:
    """Named sketch constraints ``{name: value}`` (dimensions of a master sketch)."""
    out = {}
    for c in p.iter("Constrain"):
        if c.get("Name"):
            try:
                out[c.get("Name")] = round(float(c.get("Value")), 6)
            except (TypeError, ValueError):
                out[c.get("Name")] = c.get("Value")
    return out


def freecad_document(fcstd: Path) -> ET.Element:
    with zipfile.ZipFile(fcstd) as z:
        return ET.fromstring(z.read("Document.xml"))


def freecad_trace(fcstd: Path, source: str) -> dict:
    """The plain-Python ("trace") part of the semantic JSON: objects with type, label, trace
    properties, placement and plain values; spreadsheets with aliases and values. No noise
    (dates, UUIDs, object ids, temp paths)."""
    root = freecad_document(fcstd)
    types = {o.get("name"): o.get("type") for o in root.iter("Object") if o.get("type")}
    objects = {}
    sheets = {}
    data = root.find("ObjectData")
    for o in (data if data is not None else []):
        name = o.get("name")
        props = {}
        links, exprs, constraints = {}, {}, {}
        for p in o.iter("Property"):
            pname = p.get("name")
            ptype = p.get("type") or ""
            props[pname] = (ptype, _prop_value(p), p.get("group"))
            if ptype.startswith(("App::PropertyLink", "App::PropertyXLink")):
                tg = _xlinks(p)
                if tg:
                    links[pname] = tg
            elif pname == "ExpressionEngine":
                exprs = _expressions(p)
            elif pname == "Constraints" and ptype == "Sketcher::PropertyConstraintList":
                constraints = _constraints(p)
        t = types.get(name, "")
        if t == "Spreadsheet::Sheet":
            sheets[props.get("Label", (None, name))[1] or name] = props.get("cells", (None, {}))[1] or {}
            continue
        entry = {"type": t, "label": props.get("Label", (None, name))[1]}
        trace = {k: props[k][1] for k in TRACE_FIELDS if k in props and props[k][1] not in (None, "")}
        if trace:
            entry["trace"] = trace
        if "Placement" in props:
            entry["placement"] = props["Placement"][1]
        if links:
            entry["links"] = links
        if exprs:
            entry["expressions"] = exprs
        if constraints:
            entry["constraints"] = constraints
        values = {}
        for k, (ptype, v, _grp) in sorted(props.items()):
            if k in TRACE_FIELDS or k in ("Label", "Label2", "Placement", "Visibility") or v is None:
                continue
            if ptype and ptype.startswith(("App::PropertyLength", "App::PropertyDistance", "App::PropertyAngle",
                                           "App::PropertyFloat", "App::PropertyInteger", "App::PropertyBool",
                                           "App::PropertyString", "App::PropertyQuantity")) \
                    and k not in ("AttacherType", "MapPathParameter", "MapReversed", "_ElementMapVersion"):
                values[k] = v
        if values:
            entry["values"] = values
        objects[name] = entry
    meta = {}
    props_el = root.find("Properties")
    for p in (props_el if props_el is not None else []):
        if p.tag == "Property" and p.get("name") not in _NOISE_DOC:
            v = _prop_value(p)
            if v not in (None, ""):
                meta[p.get("name")] = v
    return {"file": source, "document": meta, "objects": dict(sorted(objects.items())),
            "spreadsheets": dict(sorted(sheets.items()))}


def freecad_needs(fcstd: Path, source: str, refs: list | None = None) -> tuple[dict[str, dict], list[str]]:
    sem = freecad_trace(fcstd, source)
    needs, findings = {}, []
    for name, o in sem["objects"].items():
        tr = o.get("trace") or {}
        port = str(tr.get("Port") or "").strip()
        if port and port != "-":
            if idmod.kind_of(port) != "ME-PORT":
                findings.append(f"{source}: {name}: Port {port!r} is not an ME-PORT ID")
            elif refs is not None:
                refs.append((port, source))
        n, f = trace_need({k: str(v) for k, v in tr.items()}, o.get("label") or name,
                          f"FreeCAD object ``{name}`` ({o.get('type')}) in ``{source}``.", source, refs)
        findings += f
        if n is None:
            continue
        if n["id"] in needs:
            findings.append(f"{source}: TraceID {n['id']} is on more than one object")
            continue
        needs[n["id"]] = n
    return needs, findings


SHAPE_SCRIPT = r'''
import json, sys
import FreeCAD
doc = FreeCAD.openDocument(sys.argv[-2])
out = {}
for o in doc.Objects:
    s = getattr(o, "Shape", None)
    if s is None or s.isNull():
        continue
    bb = s.BoundBox
    out[o.Name] = {"volume": round(s.Volume, 3), "solids": len(s.Solids),
                   "bbox": [round(x, 3) for x in (bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax)]}
open(sys.argv[-1], "w").write(json.dumps(out, sort_keys=True))
FreeCAD.closeDocument(doc.Name)
'''


def freecad_shapes(ws, fcstd: Path, tmp: Path) -> dict:
    """The shape part (needs FreeCAD, local only): volume, bounding box, number of solids."""
    from curatrix import limits
    tmp.mkdir(parents=True, exist_ok=True)
    script = tmp / "xd_shapes.py"
    script.write_text(SHAPE_SCRIPT)
    out = tmp / (fcstd.stem + ".shapes.json")
    env = None
    if ws is not None:
        env = ws.run_env({"QT_QPA_PLATFORM": "offscreen"})
    r = limits.run(["FreeCADCmd", str(script), str(fcstd.resolve()), str(out)], "freecad", ws,
                   capture_output=True, text=True, env=env)
    if r.returncode or not out.exists():
        raise RuntimeError(f"FreeCADCmd failed ({r.returncode}): {r.stdout[-500:]}{r.stderr[-500:]}")
    return json.loads(out.read_text())


def freecad_compressed(fcstd: Path) -> list[str]:
    """CK-H1: entries stored with real compression (CompressionLevel 0 stores them at ~100 %)."""
    bad = []
    with zipfile.ZipFile(fcstd) as z:
        for i in z.infolist():
            if i.file_size > 256 and i.compress_size < i.file_size * 0.95:
                bad.append(f"{i.filename} ({i.compress_size}/{i.file_size} bytes)")
    return bad
