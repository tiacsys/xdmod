"""Layout (elkjs graph) and drawio XML for the SysML standard views of ``views.sysml``.

The drawio file is normalized the same way as the other views (``views.normalize_xml``):
uncompressed, ``html=0`` labels, one ``<object>`` per cell with ``sysml_kind``, ``trace_id`` and
``link``. Edges follow the ELK route exactly: the exit and entry points and the bend points are
written into the cell, so drawio does not re-route them.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET

PIN = 10
LINE = 13
FONT = "fontFamily=Helvetica;fontSize=11;"
BASE = "html=0;" + FONT + "strokeColor=#333333;"
NODE_STYLE = {
    "def": BASE + "rounded=0;fillColor=#FFFFFF;",
    "usage": BASE + "rounded=1;arcSize=12;fillColor=#FFFFFF;",
    "ref": BASE + "rounded=1;arcSize=12;dashed=1;fillColor=#FFFFFF;",
    "package": BASE + "shape=folder;tabWidth=80;tabHeight=16;tabPosition=left;verticalAlign=top;spacingTop=18;fillColor=#FFFFFF;",
    "action": BASE + "rounded=1;arcSize=30;fillColor=#FFFFFF;",
    "state": BASE + "rounded=1;arcSize=40;fillColor=#FFFFFF;",
    "initial": "ellipse;html=0;aspect=fixed;fillColor=#000000;strokeColor=#000000;",
    "final": "ellipse;shape=endState;html=0;aspect=fixed;fillColor=#000000;strokeColor=#000000;",
    "decision": "rhombus;html=0;fillColor=#FFFFFF;strokeColor=#333333;",
    "bar": "rounded=0;html=0;fillColor=#000000;strokeColor=#000000;",
    "frame": BASE + "rounded=0;container=1;collapsible=0;verticalAlign=top;align=left;spacingLeft=8;fillColor=none;",
    "subject": BASE + "rounded=0;container=1;collapsible=0;verticalAlign=top;align=left;spacingLeft=8;fillColor=#FAFAFA;",
    "usecase": BASE + "ellipse;fillColor=#FFFFFF;",
    "actor": "shape=umlActor;html=0;verticalLabelPosition=bottom;verticalAlign=top;outlineConnect=0;"
             + FONT + "fillColor=#FFFFFF;strokeColor=#333333;",
}
BODY_STYLE = "text;html=0;align=left;verticalAlign=top;spacingLeft=6;spacingTop=0;fontFamily=Helvetica;fontSize=10;"
TITLE_STYLE = "text;html=0;align=center;verticalAlign=top;spacingTop=0;fontFamily=Helvetica;fontSize=10;fontStyle=2;"
SWIMLANE = "swimlane;startSize={hh};horizontal=1;fontStyle={fs};collapsible=0;swimlaneLine=1;"
PIN_STYLE = {
    "WEST": "labelPosition=right;align=left;verticalLabelPosition=middle;verticalAlign=middle;",
    "EAST": "labelPosition=left;align=right;verticalLabelPosition=middle;verticalAlign=middle;",
    "NORTH": "labelPosition=center;align=center;verticalLabelPosition=bottom;verticalAlign=top;",
    "SOUTH": "labelPosition=center;align=center;verticalLabelPosition=top;verticalAlign=bottom;",
}
EDGE_BASE = "html=0;rounded=0;endSize=10;startSize=14;fontFamily=Helvetica;fontSize=10;labelBackgroundColor=#FFFFFF;strokeColor=#333333;"
EDGE_STYLE = {
    "specialization": "endArrow=block;endFill=0;endSize=14;",
    "composition": "startArrow=diamondThin;startFill=1;endArrow=none;",
    "reference": "startArrow=diamondThin;startFill=0;endArrow=open;",
    "dependency": "dashed=1;endArrow=open;",
    "succession": "endArrow=open;",
    "flow": "endArrow=block;endFill=1;endSize=8;strokeWidth=1.5;",
    "transition": "endArrow=open;",
    "include": "dashed=1;endArrow=open;",
    "association": "endArrow=none;",
    "connection": "endArrow=none;",
}
LEGEND = {
    "general": "Legend (SysML v2 general view): sharp box = definition, rounded box = usage, dashed = reference usage; "
               "«keyword» and <short name> above the name; lists inside a box = compartments. "
               "Hollow triangle = specialization (points to the general type); filled diamond = composite feature; "
               "hollow diamond with open arrow = reference feature, held by the diamond end and labelled with the "
               "link type and multiplicity. A box with a need ID links to its page.",
    "actionflow": "Legend (SysML v2 action flow view): rounded box = action (name : its action definition, here the "
                  "kind of task, which says who may do it); small squares = "
                  "parameters (in on the entry side, out on the exit side); filled circle = start, bull's eye = done, "
                  "diamond = decide; open arrow = succession with [guard]; thick filled arrow = flow of an item.",
    "statetransition": "Legend (SysML v2 state transition view): frame = state definition; rounded box = state; "
                       "filled circle = entry; arrow = transition labelled with its trigger (accepted item) "
                       "and [guard].",
    "interconnection": "Legend (SysML v2 interconnection view): frame = the part (definition or usage) whose inside is "
                       "shown; rounded box = part usage (name : definition; colour = layer: blue functional, green "
                       "logical, yellow product); small squares = ports, conjugated (~) ports on the left; lines = "
                       "connections and interfaces between ports; thick arrow = flow. A box with a need ID links to its page.",
    "usecases": "Legend (SysML v2 use cases): stick figure = actor (its part definition); ellipse = use case "
                "definition; frame = subject; line = the actor takes part; dashed «include» arrow = included use case.",
}
LEGEND_ID = "xd-legend"


def to_elk(g: dict) -> dict:
    direction = g.get("direction", "DOWN")
    children_of: dict[str, list[dict]] = {}
    for n in g["nodes"]:
        children_of.setdefault(n["parent"], []).append(n)

    def port(p):
        return {"id": p["id"], "width": PIN, "height": PIN,
                "layoutOptions": {"elk.port.side": p["side"], "elk.port.borderOffset": f"-{PIN // 2}"}}

    def box(n):
        el = {"id": n["id"], "width": n["w"], "height": n["h"], "ports": [port(p) for p in n["ports"]],
              "layoutOptions": {"elk.portConstraints": "FIXED_SIDE"}}
        if n["shape"] in ("def", "usage", "ref", "action", "state", "package"):
            # boxes grow so that edge ends (and their labels) keep their distance
            el["layoutOptions"].update({"elk.nodeSize.constraints": "PORTS MINIMUM_SIZE",
                                        "elk.nodeSize.minimum": f"({n['w']},{n['h']})"})
        kids = children_of.get(n["id"])
        if kids:
            el.pop("width"), el.pop("height")
            el["children"] = [box(k) for k in kids]
            el["layoutOptions"].update({"elk.padding": f"[top={n['header_h'] + 14},left=24,bottom=20,right=24]",
                                        "elk.direction": direction})
        return el

    edges = []
    for e in g["edges"]:
        rev = e["rel"] == "specialization"     # general above / before specific
        s, d = (e["dst"], e["src"]) if rev else (e["src"], e["dst"])
        ee = {"id": e["id"], "sources": [s], "targets": [d]}
        if e["label"]:
            # end labels need no label layer: reference and part ends are named at the type end
            # (HEAD), guards, triggers and items at the start of the line (TAIL)
            place = {"reference": "HEAD", "composition": "HEAD", "flow": "TAIL"}.get(e["rel"], "CENTER")
            if rev:
                place = {"HEAD": "TAIL", "TAIL": "HEAD"}.get(place, place)
            ee["labels"] = [{"text": e["label"], "width": round(len(e["label"]) * 6.0 + 8), "height": 14,
                             "layoutOptions": {"elk.edgeLabels.placement": place}}]
        edges.append(ee)
    return {"id": "root", "children": [box(n) for n in children_of.get("1", [])], "edges": edges,
            "layoutOptions": {"elk.algorithm": "layered", "elk.direction": direction,
                              "elk.edgeRouting": "ORTHOGONAL", "elk.hierarchyHandling": "INCLUDE_CHILDREN",
                              "elk.json.shapeCoords": "ROOT", "elk.json.edgeCoords": "ROOT",
                              "elk.spacing.nodeNode": "28", "elk.layered.spacing.nodeNodeBetweenLayers": "56",
                              "elk.spacing.edgeNode": "14", "elk.spacing.edgeEdge": "10", "elk.spacing.portPort": "18",
                              "elk.spacing.edgeLabel": "4", "elk.edgeLabels.placement": "CENTER",
                              "elk.layered.considerModelOrder.strategy": "NODES_AND_EDGES",
                              # NETWORK_SIMPLEX gives straighter lines, but elkjs 0.12 fails with it
                              # on some nested graphs ("NEdge must have a source and target")
                              **({"elk.layered.nodePlacement.strategy": "NETWORK_SIMPLEX"}
                                 if set(children_of) <= {"1"} else {}),
                              **({"elk.layered.cycleBreaking.strategy": "MODEL_ORDER"}
                                 if g["kind"] in ("actionflow", "statetransition") else {}),
                              **({"elk.spacing.nodeNode": "44"} if g["kind"] == "usecases" else {})}}


def positions(laid: dict) -> dict:
    out: dict[str, dict] = {}

    def rec(n):
        for c in n.get("children", []) or []:
            out[c["id"]] = {k: c.get(k, 0) for k in ("x", "y", "width", "height")}
            for p in c.get("ports", []) or []:
                out[p["id"]] = {k: p.get(k, 0) for k in ("x", "y", "width", "height")}
            rec(c)
        for e in n.get("edges", []) or []:
            sec = (e.get("sections") or [{}])[0]
            pts = []
            if sec:
                pts = [(sec["startPoint"]["x"], sec["startPoint"]["y"])]
                pts += [(b["x"], b["y"]) for b in sec.get("bendPoints", []) or []]
                pts += [(sec["endPoint"]["x"], sec["endPoint"]["y"])]
            lab = (e.get("labels") or [None])[0]
            out[e["id"]] = {"points": pts, "label": ({k: lab.get(k, 0) for k in ("x", "y", "width", "height")}
                                                    if lab else None)}
    rec(laid)
    return out


def _wrap(text: str, cols: int) -> str:
    import textwrap
    return "\n".join(textwrap.wrap(text, max(40, cols)))


def _f(v) -> str:
    return str(round(float(v)))


def _midpoint(pts):
    import math
    segs = list(zip(pts, pts[1:]))
    total = sum(math.dist(a, b) for a, b in segs)
    if not segs or total == 0:
        return pts[0] if pts else (0, 0)
    half = total / 2
    for a, b in segs:
        d = math.dist(a, b)
        if half <= d and d:
            t = half / d
            return (a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
        half -= d
    return pts[-1]


def to_mxfile(g: dict, pos: dict | None, normalize) -> str:
    pos = pos or {}
    mx = ET.Element("mxfile", {"host": "xdmod-curatrix"})
    dia = ET.SubElement(mx, "diagram", {"id": "view:" + g["view"], "name": g["view"]})
    gm = ET.SubElement(dia, "mxGraphModel", {"grid": "1", "gridSize": "10", "page": "0"})
    root = ET.SubElement(gm, "root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})
    absb: dict[str, dict] = {}
    kind_of = {}

    def cell(cid, label, style, parent, attrs, geom=None, edge=None, tooltip=""):
        obj = ET.SubElement(root, "object", {"id": cid, "label": label})
        for k, v in attrs.items():
            if v:
                obj.set(k, v)
        if tooltip:
            obj.set("tooltip", tooltip)
        c = ET.SubElement(obj, "mxCell", {"style": style, "parent": parent})
        if edge:
            c.set("edge", "1"); c.set("source", edge[0]); c.set("target", edge[1])
            gmt = ET.SubElement(c, "mxGeometry", {"relative": "1", "as": "geometry"})
            if edge[2]:
                arr = ET.SubElement(gmt, "Array", {"as": "points"})
                for px, py in edge[2]:
                    ET.SubElement(arr, "mxPoint", {"x": _f(px), "y": _f(py)})
            if edge[3]:
                ET.SubElement(gmt, "mxPoint", {"x": _f(edge[3][0]), "y": _f(edge[3][1]), "as": "offset"})
        else:
            c.set("vertex", "1")
            x, y, w, h = geom
            ET.SubElement(c, "mxGeometry", {"x": _f(x), "y": _f(y), "width": _f(w), "height": _f(h), "as": "geometry"})

    def geom(nid, parent, w, h):
        b = pos.get(nid) or {"x": 0, "y": 0, "width": w, "height": h}
        b = {"x": b["x"], "y": b["y"], "width": b.get("width") or w, "height": b.get("height") or h}
        absb[nid] = b
        pb = absb.get(parent, {"x": 0, "y": 0})
        return (b["x"] - pb["x"], b["y"] - pb["y"], b["width"], b["height"])

    def attrs(n, kind=None):
        return {"sysml_kind": kind or n["sysml_kind"], "trace_id": n.get("trace_id", ""), "layer": n.get("layer", ""),
                "configs": n.get("configs", ""), "link": f"need:{n['trace_id']}" if n.get("trace_id") else ""}

    for n in g["nodes"]:
        kind_of[n["id"]] = n["shape"]
        style = NODE_STYLE[n["shape"]]
        italic = n["label"].startswith("«abstract")
        if n.get("body"):
            style = style + SWIMLANE.format(hh=n["header_h"], fs=2 if italic else 0)
        elif italic:
            style += "fontStyle=2;"
        if n["shape"] in ("def", "usage", "ref", "action") and not n.get("body"):
            style += "verticalAlign=middle;"
        if n["shape"] in ("initial", "final", "decision", "bar"):
            style += "noLabel=1;"
        if n.get("fill"):
            style += f"fillColor={n['fill']};"
        x, y, w, h = geom(n["id"], n["parent"], n["w"], n["h"])
        cell(n["id"], n["label"], style, n["parent"], attrs(n), (x, y, w, h), tooltip=n.get("tooltip", ""))
        if n.get("body"):
            y0 = n["header_h"]
            for i, (title, entries) in enumerate(n["sections"]):
                tid, bid = f"{n['id']}#{title}", f"{n['id']}#{title}.body"
                cell(tid, title, TITLE_STYLE + ("strokeColor=none;" if i == 0 else "strokeColor=none;"), n["id"],
                     {"sysml_kind": "compartment"}, (0, y0 + 2, w, LINE))
                bh = LINE * len(entries) + 4
                cell(bid, "\n".join(entries), BODY_STYLE, n["id"], {"sysml_kind": "compartment"}, (0, y0 + 2 + LINE, w, bh))
                y0 += LINE + bh + 6
                if i + 1 < len(n["sections"]):   # separator line between compartments
                    cell(f"{n['id']}#{title}.sep", "", "line;html=0;strokeColor=#333333;strokeWidth=1;", n["id"],
                         {"sysml_kind": "separator"}, (0, y0 - 3, w, 1))
        for p in n["ports"]:
            px, py, pw, ph = geom(p["id"], n["id"], PIN, PIN)
            cell(p["id"], p["label"], BASE + "rounded=0;fillColor=#FFFFFF;fontSize=9;" + PIN_STYLE[p["side"]],
                 n["id"], {"sysml_kind": p.get("kind", "pin")}, (px, py, pw, ph))
    for e in g["edges"]:
        info = pos.get(e["id"]) or {}
        pts = list(info.get("points") or [])
        if e["rel"] == "specialization":
            pts.reverse()
        style = EDGE_BASE + EDGE_STYLE[e["rel"]]
        bends = pts[1:-1]
        if len(pts) >= 2:
            for end, (px, py), key in (("src", pts[0], "exit"), ("dst", pts[-1], "entry")):
                b = absb.get(e[end])
                if b and kind_of.get(e[end]) not in (None, "actor") and b["width"] and b["height"]:
                    rx = min(1, max(0, (px - b["x"]) / b["width"]))
                    ry = min(1, max(0, (py - b["y"]) / b["height"]))
                    style += f"{key}X={rx:.3f};{key}Y={ry:.3f};{key}Dx=0;{key}Dy=0;{key}Perimeter=0;"
        offset = None
        lab = info.get("label")
        if e["label"] and lab and pts:
            mx_, my_ = _midpoint(pts)
            offset = (lab["x"] + lab["width"] / 2 - mx_, lab["y"] + lab["height"] / 2 - my_)
        cell(e["id"], e["label"], style, "1", {"sysml_kind": e["sysml_kind"]}, edge=(e["src"], e["dst"], bends, offset))
    tops = [b for k, b in absb.items() if "#" not in k]
    route_y = [y for v in pos.values() if isinstance(v, dict) for _, y in (v.get("points") or [])]
    bottom = max([b["y"] + b["height"] for b in tops] + route_y or [0])
    left = min([b["x"] for b in tops] or [0])
    # the legend text is content: its line breaks must not depend on the layout
    text = _wrap(LEGEND.get(g["kind"], "Legend"), 120)
    width = round(max(len(s) for s in text.split("\n")) * 4.9 + 16)
    cell(LEGEND_ID, text, "text;html=0;align=left;verticalAlign=top;fontFamily=Helvetica;fontSize=9;fillColor=#FFFFFF;"
         "strokeColor=#999999;spacing=4;", "1", {"sysml_kind": "legend"},
         (left, bottom + 24, width, 12 + 12 * (text.count("\n") + 1)))
    return normalize(ET.tostring(mx, encoding="unicode"))
