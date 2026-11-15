"""Views as editable SVG (D94, D96, views.md; checks CK-D3). Port of the spike renderer.

Pipeline (views.md §4)::

    model JSON --view graph--> build/<area>/views/<view>.json            (for agents)
               --elkjs-->      positions
               --drawio XML--> normalized <mxfile> (uncompressed, html=0, stable cell IDs)
               --headless Firefox + pinned drawio viewer--> SVG picture
               ==> <repo>/views/<view>.drawio.svg                         (committed)

The committed ``.drawio.svg`` is the SVG picture with the diagram in its ``content`` attribute
(what drawio desktop opens and saves), plus ``data-xdmod-hash="sha256:<hex>"``: the hash of the
normalized embedded diagram at the time the picture was rendered. ``check`` needs no browser: it
regenerates the view content from the model JSON and compares labels, parents, edge ends, kinds,
links, layers and configs (never geometry, D64a); it rejects compressed diagrams and geometry
errors, and compares the stored hash with the embedded diagram (picture freshness).

View definitions are SysML ``view``s with ``@XdView { kind = "..."; root = "..."; }`` (D94).
Implemented kinds: ``interconnection`` and ``decomposition`` (here), and the SysML v2 standard
views ``general``, ``actionflow``, ``statetransition`` and ``usecases`` (``views/sysml.py`` builds
the graph, ``views/draw.py`` lays it out and writes drawio). The others are reported as not
implemented.
"""
from __future__ import annotations

import base64
import hashlib
import html
import json
import re
import urllib.parse
import xml.etree.ElementTree as ET
import zlib
from dataclasses import dataclass, field
from pathlib import Path

from curatrix.model import Model, element_id

HERE = Path(__file__).resolve().parent
SYSML_KINDS = ("general", "actionflow", "statetransition", "usecases")
IMPLEMENTED = ("interconnection", "decomposition", *SYSML_KINDS)
KNOWN = ("context", "usecases", "decomposition", "interconnection", "allocation", "variants", *SYSML_KINDS[:3])
HASH_ATTR = "data-xdmod-hash"
PORT = 12
LAYER_FILL = {"context": "#F5F5F5", "functional": "#DAE8FC", "logical": "#D5E8D4", "product": "#FFF2CC", None: "#FFFFFF"}


@dataclass
class ViewDef:
    name: str
    short_id: str | None
    kind: str
    root: str | None
    layer: str | None
    qualified_name: str
    exposed: set = field(default_factory=set)
    opts: dict = field(default_factory=dict)    # direction, show, compartments, between


class ViewError(Exception):
    pass


# ------------------------------------------------------------------ view definitions
def discover(m: Model) -> list[ViewDef]:
    out = []
    for v in m.of_type("ViewUsage", "ViewDefinition"):
        if v.get("isLibraryElement"):
            continue
        meta = m.trace_meta(v, "XdTrace::XdView")
        if not meta:
            continue
        opts = {k: str(meta[k]) for k in ("direction", "show", "compartments", "between") if meta.get(k)}
        if opts.get("direction", "").endswith("!"):     # "RIGHT!": the layout may not turn the view
            opts["direction"], opts["fixed"] = opts["direction"][:-1], "1"
        out.append(ViewDef(name=v.get("declaredName") or v.get("name") or v["@id"],
                           short_id=v.get("declaredShortName"), kind=str(meta.get("kind", "")),
                           root=meta.get("root"), layer=meta.get("layer"), qualified_name=v.get("qualifiedName", ""),
                           exposed={x["@id"] for x in (v.get("exposedElement") or []) if isinstance(x, dict)},
                           opts=opts))
    return sorted(out, key=lambda v: v.name)


def file_name(v: ViewDef) -> str:
    return re.sub(r"[^A-Za-z0-9_.-]+", "-", v.name) + ".drawio.svg"


# ------------------------------------------------------------------ view graphs
def _layer_of(m: Model, p: dict) -> str | None:
    return m.inherited_meta(p, "XdTrace::Trace", "layer")


def _trace_of(m: Model, p: dict) -> tuple[str | None, dict | None]:
    """(trace ID, the element that carries it): the element itself, else its definition (D128)."""
    tid = element_id(m, p)
    if tid:
        return tid, p
    for t in m.types_of(p):
        tid = element_id(m, t)
        if tid:
            return tid, t
    return None, None


def _label(m: Model, u: dict) -> str:
    tn = ", ".join(t.get("name") or "" for t in m.types_of(u) if t.get("name"))
    name = u.get("name") or u.get("declaredName") or ""
    return f"{name} : {tn}" if tn else name


def _node(m: Model, p: dict, nid: str, label: str, kind: str, parent: str, ports=None) -> dict:
    tid, carrier = _trace_of(m, p)
    lay = _layer_of(m, carrier or p) if (carrier or p) else None
    return {"id": nid, "label": label, "sysml_kind": kind, "parent": parent, "trace_id": tid or "",
            "layer": lay or "", "configs": "", "ports": ports or []}


def _ports(m: Model, u: dict) -> list[dict]:
    seen, out = set(), []
    for f in (u.get("feature") or []) + (u.get("ownedFeature") or []):
        pu = m.get(f)
        if not pu or pu.get("@type") != "PortUsage" or not pu.get("name") or pu["name"] in seen:
            continue
        seen.add(pu["name"])
        conj = any((m.get(t) or {}).get("@type") == "ConjugatedPortDefinition" for t in pu.get("type", []) or [])
        out.append({"id": f"{u['qualifiedName']}.{pu['name']}", "label": pu["name"], "side": "WEST" if conj else "EAST",
                    "kind": "PortUsage"})
    return sorted(out, key=lambda p: p["id"])


def _find(m: Model, qname: str) -> dict:
    for p in m.e.values():
        if p.get("qualifiedName") == qname and not p.get("isLibraryElement"):
            return p
    raise ViewError(f"root {qname!r} not found in the model")


def graph(m: Model, v: ViewDef) -> dict:
    if v.kind not in KNOWN:
        raise ViewError(f"view {v.name}: unknown kind {v.kind!r} (known: {', '.join(KNOWN)})")
    if v.kind not in IMPLEMENTED:
        raise ViewError(f"view {v.name}: kind {v.kind!r} is not implemented yet (iteration 1: {', '.join(IMPLEMENTED)})")
    if v.kind in SYSML_KINDS:
        from curatrix.views import sysml
        try:
            return sysml.build(m, v, v.opts)
        except sysml.GraphError as e:
            raise ViewError(f"view {v.name}: {e}") from None
    if not v.root:
        raise ViewError(f"view {v.name}: @XdView needs root")
    root = _find(m, v.root)
    g = {"view": v.name, "kind": v.kind, "short_id": v.short_id or "", "root": v.root, "nodes": [], "edges": []}
    rid = root["qualifiedName"]
    g["nodes"].append(_node(m, root, rid, root.get("name") or rid, root["@type"], "1"))
    if v.kind == "interconnection":
        parts = []
        for ref in (root.get("ownedPart") or []) or [x["@id"] for _, x in m.owned(root) if x.get("@type") == "PartUsage"]:
            u = m.get(ref)
            if u and u.get("name") and u.get("@type") == "PartUsage":
                parts.append(u)
        if v.exposed and any(p["@id"] in v.exposed for p in parts):
            parts = [p for p in parts if p["@id"] in v.exposed]
        for u in sorted(parts, key=lambda u: u["qualifiedName"]):
            g["nodes"].append(_node(m, u, u["qualifiedName"], _label(m, u), "PartUsage", rid, _ports(m, u)))
        for c in m.of_type("ConnectionUsage", "InterfaceUsage", "FlowConnectionUsage"):
            if (m.get(c.get("owningType")) or {}).get("qualifiedName") != rid:
                continue
            ends = []
            for f in c.get("relatedFeature", []) or []:
                fe = m.get(f) or {}
                chain = [(m.get(x) or {}).get("name") for x in fe.get("chainingFeature", []) or []]
                if not chain:
                    chain = [fe.get("name")]
                ends.append(f"{rid}::{chain[0]}" + ("." + ".".join(chain[1:]) if len(chain) > 1 else ""))
            if len(ends) == 2:
                cid = f"{rid}::connect({ends[0].split('::')[-1]}->{ends[1].split('::')[-1]})"
                g["edges"].append({"id": cid, "src": ends[0], "dst": ends[1], "sysml_kind": c["@type"], "label": ""})
        if v.opts.get("show"):     # only these ports, their connections, and the parts that have them
            keep = {x.strip() for x in v.opts["show"].split(",") if x.strip()}
            unknown = keep - {p["label"] for n in g["nodes"][1:] for p in n["ports"]}
            if unknown:
                raise ViewError(f"view {v.name}: show names ports that no part has: {', '.join(sorted(unknown))}")
            for n in g["nodes"][1:]:
                n["ports"] = [p for p in n["ports"] if p["label"] in keep]
            pids = {p["id"] for n in g["nodes"] for p in n["ports"]}
            g["edges"] = [e for e in g["edges"] if e["src"] in pids and e["dst"] in pids]
            g["nodes"] = g["nodes"][:1] + [n for n in g["nodes"][1:] if n["ports"]]
        _as_drawn(g, root, v)
    else:  # decomposition: definition -> part usages -> their definitions, as a tree
        def rec(p, pid, depth):
            if depth > 4:
                return
            kids = [m.get(r) for r in (p.get("ownedPart") or [])] or [x for _, x in m.owned(p) if x.get("@type") == "PartUsage"]
            for u in sorted((k for k in kids if k and k.get("name")), key=lambda k: k.get("qualifiedName", "")):
                uid = u["qualifiedName"]
                g["nodes"].append(_node(m, u, uid, _label(m, u), "PartUsage", "1"))
                g["edges"].append({"id": f"{pid}->{uid}", "src": pid, "dst": uid, "sysml_kind": "composition", "label": ""})
                for t in m.types_of(u):
                    if not t.get("isLibraryElement"):
                        rec(t, uid, depth + 1)
        g["nodes"][0]["parent"] = "1"
        rec(root, rid, 0)
    return g


def _as_drawn(g: dict, root: dict, v: ViewDef) -> None:
    """Interconnection graphs are drawn by views/draw.py: a frame for the root, rounded part
    usages with their ports, plain lines for connections and interfaces (SysML v2 notation)."""
    from curatrix.views.sysml import keyword, node as snode, size_for
    g["draw"] = True
    g["direction"] = (v.opts.get("direction") or "RIGHT").upper()
    first = g["nodes"][0]
    frame = snode(first["id"], f"«{keyword(root)}»\n{first['label']}", first["sysml_kind"], shape="frame",
                  trace_id=first["trace_id"])
    frame.update({k: first[k] for k in ("layer", "configs")})
    out = [frame]
    vertical = g["direction"] in ("DOWN", "UP")
    for n in g["nodes"][1:]:
        sides = {s: [p for p in n["ports"] if p["side"] == s] for s in ("WEST", "EAST")}
        w, _ = size_for([n["label"]], min_w=150)
        if vertical:   # conjugated ports on the entry side (top for DOWN), the others on the exit side
            flip = {"WEST": "NORTH", "EAST": "SOUTH"} if g["direction"] == "DOWN" else {"WEST": "SOUTH", "EAST": "NORTH"}
            ports = [{**p, "side": flip[p["side"]]} for p in n["ports"]]
            per = max([sum(len(p["label"]) * 6.6 + 24 for p in sides[s]) for s in sides] + [0])
            w, h = round(max(w + 16, per + 16)), 64
        else:
            ports = n["ports"]
            pw = {s: max([len(p["label"]) for p in sides[s]] or [0]) * 6.6 for s in sides}
            w, h = round(w + 2 * max(pw.values()) + 16), max(56, 30 + 22 * max(len(sides["WEST"]), len(sides["EAST"])))
        d = snode(n["id"], n["label"], n["sysml_kind"], parent=n["parent"], shape="usage", trace_id=n["trace_id"],
                  w=w, h=h, ports=ports)
        d.update({k: n[k] for k in ("layer", "configs")})
        d["fill"] = LAYER_FILL.get(n["layer"] or None, "#FFFFFF")
        out.append(d)
    g["nodes"] = out
    for e in g["edges"]:
        e["rel"] = "flow" if e["sysml_kind"] == "FlowConnectionUsage" else "connection"


# ------------------------------------------------------------------ layout (elkjs)
def to_elk(g: dict) -> dict:
    if g["kind"] in SYSML_KINDS or g.get("draw"):
        from curatrix.views import draw
        return draw.to_elk(g)

    def port(p):
        return {"id": p["id"], "width": PORT, "height": PORT,
                "layoutOptions": {"elk.port.side": p["side"], "elk.port.borderOffset": "-6"}}

    def box(n, w=170, h=70):
        return {"id": n["id"], "width": w, "height": h, "labels": [{"text": n["label"], "width": w - 20, "height": 16}],
                "ports": [port(p) for p in n["ports"]],
                "layoutOptions": {"elk.portConstraints": "FIXED_SIDE", "elk.nodeSize.constraints": "MINIMUM_SIZE",
                                  "elk.nodeSize.minimum": f"({w},{h})"}}

    if g["kind"] == "interconnection":
        rid = g["nodes"][0]["id"]
        outer = {"id": rid, "labels": [{"text": g["nodes"][0]["label"], "width": 160, "height": 16}],
                 "ports": [], "children": [box(n) for n in g["nodes"][1:]],
                 "edges": [{"id": e["id"], "sources": [e["src"]], "targets": [e["dst"]]} for e in g["edges"]],
                 "layoutOptions": {"elk.algorithm": "layered", "elk.direction": "RIGHT", "elk.edgeRouting": "ORTHOGONAL",
                                   "elk.portConstraints": "FIXED_SIDE",
                                   "elk.padding": "[top=40,left=40,bottom=30,right=40]", "elk.spacing.nodeNode": "40",
                                   "elk.layered.spacing.nodeNodeBetweenLayers": "60"}}
        return {"id": "root", "children": [outer],
                "layoutOptions": {"elk.algorithm": "layered", "elk.hierarchyHandling": "INCLUDE_CHILDREN",
                                  "elk.json.shapeCoords": "ROOT", "elk.json.edgeCoords": "ROOT"}}
    return {"id": "root", "children": [box(n, 190, 50) for n in g["nodes"]],
            "edges": [{"id": e["id"], "sources": [e["src"]], "targets": [e["dst"]]} for e in g["edges"]],
            "layoutOptions": {"elk.algorithm": "layered", "elk.direction": "DOWN", "elk.edgeRouting": "ORTHOGONAL",
                              "elk.json.shapeCoords": "ROOT", "elk.json.edgeCoords": "ROOT",
                              "elk.spacing.nodeNode": "30", "elk.layered.spacing.nodeNodeBetweenLayers": "50"}}


def run_elk(ws, elk_graph: dict) -> dict:
    from curatrix import limits
    r = limits.run(["node", str(HERE / "elk_layout.mjs"), str(ws.opt / "node")], "elk", ws,
                   input=json.dumps(elk_graph), capture_output=True, text=True)
    if r.returncode:
        raise ViewError(f"elkjs layout failed ({r.returncode} {limits.explain_rc(r.returncode)}): {r.stderr[-800:]}")
    return json.loads(r.stdout)


def positions(laid: dict) -> dict[str, dict]:
    """id -> absolute box (x, y, width, height); edges: route points (start, bends, end), bends
    and label box, from ELK root coordinates."""
    from curatrix.views import draw
    out = draw.positions(laid)
    for v in out.values():
        if "points" in v:
            v["bends"] = v["points"][1:-1]
    return out


# ------------------------------------------------------------------ canvas ratio
# A diagram must fit a page: its canvas is between 9:16 (portrait) and 16:9 (landscape), so
# 4:3 and 16:9 pages in either orientation take it without large empty margins.
RATIO_MIN, RATIO_MAX = 9 / 16, 16 / 9
PERPENDICULAR = {"RIGHT": "DOWN", "LEFT": "UP", "DOWN": "RIGHT", "UP": "LEFT"}


def canvas_ratio(mxfile_xml: str) -> float:
    """Width / height of the drawing: top-level boxes (with the legend) and edge routes."""
    root = ET.fromstring(mxfile_xml)
    xs, ys = [], []
    for obj in root.iter("object"):
        c = obj.find("mxCell")
        g = c.find("mxGeometry") if c is not None else None
        if g is None:
            continue
        if c.get("vertex") == "1" and c.get("parent") == "1":
            x, y = float(g.get("x", 0)), float(g.get("y", 0))
            xs += [x, x + float(g.get("width", 0))]
            ys += [y, y + float(g.get("height", 0))]
        elif c.get("edge") == "1" and c.get("parent") == "1":
            for pt in g.iter("mxPoint"):
                if pt.get("as") != "offset":
                    xs.append(float(pt.get("x", 0))); ys.append(float(pt.get("y", 0)))
    if not xs:
        return 1.0
    return max(1.0, max(xs) - min(xs)) / max(1.0, max(ys) - min(ys))


def ratio_error(r: float) -> float:
    """0 inside [RATIO_MIN, RATIO_MAX], else how far outside (log scale)."""
    import math
    return max(0.0, math.log(r / RATIO_MAX), math.log(RATIO_MIN / r))


def layout(ws, m: Model, v: ViewDef, log=lambda *_: None) -> tuple[dict, str, float]:
    """Lay out a view so that its canvas ratio fits a page. Tries, in this order: the view as
    declared; the perpendicular direction (unless the view fixes it with ``direction = "RIGHT!"``);
    with layer wrapping; both. The legend goes below (wide or narrow) or to the right. The first try within
    [RATIO_MIN, RATIO_MAX] wins, else the closest. Returns (graph, mxfile, ratio).
    Only geometry changes between the tries: the content (CK-D3) is the same."""
    fixed = bool(v.opts.get("fixed"))
    tries = [{}]
    turn = v.kind in ("general", "actionflow", "statetransition", "usecases", "interconnection") and not fixed
    if turn:
        other = PERPENDICULAR.get(graph(m, v).get("direction", "DOWN"), "RIGHT")
        tries.append({"direction": other})
    tries.append({"wrap": True})
    if turn:
        tries.append({"direction": other, "wrap": True})
    best = None
    for t in tries:
        vv = v
        if "direction" in t:
            vv = ViewDef(**{**v.__dict__, "opts": {**v.opts, "direction": t["direction"]}})
        g = graph(m, vv)
        if t.get("wrap"):
            g["wrap"] = True
        pos = positions(run_elk(ws, to_elk(g)))
        for legend in ("below", "below-narrow", "right"):
            g["legend"] = legend
            xml = to_mxfile(g, pos)
            r = canvas_ratio(xml)
            score = (ratio_error(r), tries.index(t), ("below", "below-narrow", "right").index(legend))
            if best is None or score < best[0]:
                best = (score, g, xml, r)
            if ratio_error(r) == 0:
                log(f"  {v.name}: {t or 'as declared'}, legend {legend}, ratio {r:.2f}")
                return g, xml, r
    log(f"  {v.name}: no layout within {RATIO_MIN:.2f}..{RATIO_MAX:.2f}; best ratio {best[3]:.2f}")
    return best[1], best[2], best[3]


# ------------------------------------------------------------------ drawio XML
STYLE = {
    "outer": "rounded=0;html=0;container=1;collapsible=0;verticalAlign=top;align=left;spacingLeft=6;fontStyle=1;fillColor={fill};",
    "part": "rounded=1;arcSize=6;html=0;container=1;collapsible=0;verticalAlign=top;whiteSpace=wrap;fillColor={fill};",
    "port": "rounded=0;html=0;fillColor=#FFFFFF;fontSize=9;labelPosition={lp};align={al};verticalLabelPosition=middle;verticalAlign=middle;",
    "edge": "endArrow=open;html=0;rounded=0;edgeStyle=orthogonalEdgeStyle;",
    "composition": "endArrow=none;startArrow=diamondThin;startFill=1;html=0;rounded=0;edgeStyle=orthogonalEdgeStyle;",
    "legend": "text;html=0;align=left;verticalAlign=top;fontSize=9;fillColor=#FFFFFF;strokeColor=#999999;spacing=4;whiteSpace=wrap;",
}
LEGEND = {
    "interconnection": "Legend: boxes = part usages (colour = layer: blue functional, green logical, yellow product); "
                       "small squares = ports (left: conjugated ~, right: normal); lines = connections. "
                       "A part with a trace ID links to its need.",
    "decomposition": "Legend: boxes = part definitions/usages (colour = layer: blue functional, green logical, yellow product); "
                     "diamond lines = composition (parent owns child). A box with a trace ID links to its need.",
}
LEGEND_ID = "xd-legend"


def _fmt(v) -> str:
    return str(round(float(v)))


def _cell(root, cid, label, style, parent, geom=None, edge=None, attrs=None):
    obj = ET.SubElement(root, "object", {"id": cid, "label": label})
    for k, val in (attrs or {}).items():
        if val:
            obj.set(k, val)
    c = ET.SubElement(obj, "mxCell", {"style": style, "parent": parent})
    if edge:
        c.set("edge", "1"); c.set("source", edge[0]); c.set("target", edge[1])
        gm = ET.SubElement(c, "mxGeometry", {"relative": "1", "as": "geometry"})
        if edge[2]:
            arr = ET.SubElement(gm, "Array", {"as": "points"})
            for px, py in edge[2]:
                ET.SubElement(arr, "mxPoint", {"x": _fmt(px), "y": _fmt(py)})
    else:
        c.set("vertex", "1")
        x, y, w, h = geom or (0, 0, 10, 10)
        ET.SubElement(c, "mxGeometry", {"x": _fmt(x), "y": _fmt(y), "width": _fmt(w), "height": _fmt(h), "as": "geometry"})


def to_mxfile(g: dict, pos: dict | None = None) -> str:
    """Normalized, uncompressed drawio XML for a view graph (pos=None: dummy geometry, content only)."""
    if g["kind"] in SYSML_KINDS or g.get("draw"):
        from curatrix.views import draw
        return draw.to_mxfile(g, pos, normalize_xml)
    pos = pos or {}
    mx = ET.Element("mxfile", {"host": "xdmod-curatrix"})
    dia = ET.SubElement(mx, "diagram", {"id": "view:" + g["view"], "name": g["view"]})
    gm = ET.SubElement(dia, "mxGraphModel", {"grid": "1", "gridSize": "10", "page": "0"})
    root = ET.SubElement(gm, "root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})
    abs_of = {}

    def geom(nid, parent):
        b = pos.get(nid) or {"x": 0, "y": 0, "width": 170, "height": 70}
        abs_of[nid] = b
        pb = abs_of.get(parent, {"x": 0, "y": 0})
        return (b["x"] - pb["x"], b["y"] - pb["y"], b["width"], b["height"])

    def attrs(n):
        return {"sysml_kind": n["sysml_kind"], "trace_id": n["trace_id"], "layer": n["layer"],
                "configs": n["configs"], "link": f"need:{n['trace_id']}" if n["trace_id"] else ""}

    nodes = g["nodes"]
    first = nodes[0]
    for n in nodes:
        is_outer = g["kind"] == "interconnection" and n is first
        st = (STYLE["outer"] if is_outer else STYLE["part"]).format(fill=LAYER_FILL.get(n["layer"] or None, "#FFFFFF"))
        _cell(root, n["id"], n["label"], st, n["parent"], geom(n["id"], n["parent"]), attrs=attrs(n))
        for p in n["ports"]:
            west = p["side"] == "WEST"
            _cell(root, p["id"], p["label"], STYLE["port"].format(lp="right" if west else "left", al="left" if west else "right"),
                  n["id"], geom(p["id"], n["id"]), attrs={"sysml_kind": "PortUsage"})
    for e in g["edges"]:
        st = STYLE["composition"] if e["sysml_kind"] == "composition" else STYLE["edge"]
        _cell(root, e["id"], e.get("label", ""), st, "1", edge=(e["src"], e["dst"], (pos.get(e["id"]) or {}).get("bends")),
              attrs={"sysml_kind": e["sysml_kind"]})
    # legend below everything
    bottom = max([b["y"] + b.get("height", 0) for b in abs_of.values()] or [0])
    left = min([b["x"] for b in abs_of.values()] or [0])
    _cell(root, LEGEND_ID, LEGEND.get(g["kind"], "Legend"), STYLE["legend"], "1",
          (left, bottom + 20, 520, 48), attrs={"sysml_kind": "legend"})
    return normalize_xml(ET.tostring(mx, encoding="unicode"))


# ------------------------------------------------------------------ normalizing and the editable SVG
EDITOR_ATTRS_MXFILE = {"host", "modified", "agent", "etag", "version", "type", "compressed", "pages", "scale", "border"}
KEEP_MODEL_ATTRS = {"grid", "gridSize", "page"}


def decompress(text: str) -> str:
    """drawio's compressed diagram: base64(deflate-raw(urlencode(xml)))."""
    raw = zlib.decompress(base64.b64decode(text), -15)
    return urllib.parse.unquote(raw.decode("utf-8"))


def is_compressed(mxfile_xml: str) -> bool:
    root = ET.fromstring(mxfile_xml)
    for d in root.iter("diagram"):
        if d.find("mxGraphModel") is None and (d.text or "").strip():
            return True
    return False


def normalize_xml(mxfile_xml: str) -> str:
    """Decompress, drop editor attributes, sort cells (structure first, then vertices by depth and
    ID, then edges by ID), indent. Same input content -> same bytes."""
    root = ET.fromstring(mxfile_xml)
    if root.tag != "mxfile":
        raise ViewError("not a drawio <mxfile>")
    for a in list(root.attrib):
        if a in EDITOR_ATTRS_MXFILE:
            del root.attrib[a]
    root.set("host", "xdmod-curatrix")
    for d in root.findall("diagram"):
        if d.find("mxGraphModel") is None and (d.text or "").strip():
            model = ET.fromstring(decompress(d.text.strip()))
            d.text = None
            d.append(model)
        gm = d.find("mxGraphModel")
        for a in list(gm.attrib):
            if a not in KEEP_MODEL_ATTRS:
                del gm.attrib[a]
        r = gm.find("root")
        cells = list(r)
        parent_of = {}
        for c in cells:
            cell = c if c.tag == "mxCell" else c.find("mxCell")
            parent_of[c.get("id")] = cell.get("parent") if cell is not None else None

        def depth(cid, seen=()):
            p = parent_of.get(cid)
            return 0 if not p or p in seen else 1 + depth(p, (*seen, cid))

        def key(c):
            cid = c.get("id")
            cell = c if c.tag == "mxCell" else c.find("mxCell")
            is_edge = cell is not None and cell.get("edge") == "1"
            return (0 if cid in ("0", "1") else 2 if is_edge else 1, cid if cid in ("0", "1") else "", depth(cid), cid)
        for c in cells:
            r.remove(c)
        for c in sorted(cells, key=key):
            r.append(c)
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode") + "\n"


def diagram_hash(mxfile_xml: str) -> str:
    return "sha256:" + hashlib.sha256(normalize_xml(mxfile_xml).encode("utf-8")).hexdigest()


def compose(svg: str, mxfile_xml: str, view_name: str) -> str:
    """The committed .drawio.svg: picture + embedded diagram + hash; random SVG IDs pinned."""
    svg = re.sub(r"^<\?xml[^>]*>\s*", "", svg.strip())
    rid = re.search(r'id="(ge-svg-[^"]+)"', svg)
    stable = "xd-view-" + re.sub(r"[^A-Za-z0-9_-]+", "-", view_name)
    if rid:
        svg = svg.replace(rid.group(1), stable)
    norm = normalize_xml(mxfile_xml)
    head_end = svg.index(">")
    attrs = f' content="{html.escape(norm, quote=True)}" {HASH_ATTR}="{diagram_hash(norm)}"'
    if svg[head_end - 1] == "/":
        head_end -= 1
    return svg[:head_end] + attrs + svg[head_end:] + "\n"


def read_svg(path: Path) -> tuple[str | None, str | None, str]:
    """(embedded mxfile XML or None, stored hash or None, svg text)."""
    text = path.read_text(encoding="utf-8")
    try:
        root = ET.fromstring(text)
    except ET.ParseError as e:
        raise ViewError(f"{path}: not well-formed SVG: {e}")
    content = root.get("content")
    return content, root.get(HASH_ATTR), text


# ------------------------------------------------------------------ content comparison (no browser)
def content_of(mxfile_xml: str) -> dict[str, tuple]:
    out = {}
    root = ET.fromstring(normalize_xml(mxfile_xml))
    for obj in root.iter("object"):
        c = obj.find("mxCell")
        if c is None:
            continue
        label = obj.get("label") or ""
        if obj.get("sysml_kind") == "legend":     # where the legend breaks its lines is layout
            label = " ".join(label.split())
        out[obj.get("id")] = (label, c.get("parent"), c.get("source"), c.get("target"),
                              obj.get("sysml_kind") or "", obj.get("link") or "", obj.get("trace_id") or "",
                              obj.get("layer") or "", obj.get("configs") or "")
    return out


FIELDS = ("label", "parent", "source", "target", "kind", "link", "trace_id", "layer", "configs")


def diff_content(expected: dict, actual: dict) -> list[str]:
    out = [f"missing in the file: {k}" for k in sorted(expected.keys() - actual.keys())]
    out += [f"not in the model: {k}" for k in sorted(actual.keys() - expected.keys())]
    for k in sorted(expected.keys() & actual.keys()):
        if expected[k] != actual[k]:
            ch = [f"{f}: {a!r} -> {e!r}" for f, e, a in zip(FIELDS, expected[k], actual[k]) if e != a]
            out.append(f"changed {k}: " + "; ".join(ch))
    return out


def geometry_errors(mxfile_xml: str) -> list[str]:
    """Children outside their parent (ports may sit on the border), negative or empty sizes."""
    root = ET.fromstring(normalize_xml(mxfile_xml))
    boxes, kinds = {}, {}
    for obj in root.iter("object"):
        c = obj.find("mxCell")
        if c is None or c.get("vertex") != "1":
            continue
        g = c.find("mxGeometry")
        if g is None:
            continue
        try:
            b = tuple(float(g.get(k, 0)) for k in ("x", "y", "width", "height"))
        except ValueError:
            return [f"{obj.get('id')}: geometry is not numeric"]
        boxes[obj.get("id")] = (b, c.get("parent"))
        kinds[obj.get("id")] = obj.get("sysml_kind")
    errs = []
    for cid, ((x, y, w, h), parent) in boxes.items():
        if w <= 0 or h <= 0:
            errs.append(f"{cid}: width/height must be > 0")
        if parent in boxes:
            pw, ph = boxes[parent][0][2], boxes[parent][0][3]
            tol = PORT if kinds.get(cid) in ("PortUsage", "pin") else 1
            if x < -tol or y < -tol or x + w > pw + tol or y + h > ph + tol:
                errs.append(f"{cid}: lies outside its parent {parent}")
    return errs


def check_file(path: Path, expected_xml: str | None) -> list[str]:
    """CK-D3 for one committed view. expected_xml=None: no such view in the model."""
    errs = []
    content, stored, _ = read_svg(path)
    if content is None:
        return [f"{path.name}: no embedded drawio diagram (content attribute); not an editable SVG"]
    if is_compressed(content):
        errs.append(f"{path.name}: the embedded diagram is compressed; run `curatrix views normalize {path}`")
    if expected_xml is None:
        return errs + [f"{path.name}: no view of this name in the model (delete the file or add the view)"]
    if stored is None:
        errs.append(f"{path.name}: no {HASH_ATTR}; render it with `curatrix views build` / `views normalize`")
    elif stored != diagram_hash(content):
        errs.append(f"{path.name}: picture is stale (hash differs from the embedded diagram); run `curatrix views normalize {path}`")
    errs += [f"{path.name}: {d}" for d in diff_content(content_of(expected_xml), content_of(content))]
    errs += [f"{path.name}: {d}" for d in geometry_errors(content)]
    return errs
