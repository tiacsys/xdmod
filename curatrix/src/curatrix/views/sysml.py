"""SysML v2 standard views as view graphs: general, actionflow, statetransition, usecases.

The graphs use the SysML v2 graphical notation where drawio has a matching shape:

* definitions are rectangles with sharp corners, usages have rounded corners, reference usages a
  dashed border; the header shows the keyword (``«item def»``), the short name in angle brackets
  and the name; compartments list the features that are not drawn as edges;
* specialization: hollow triangle at the general end; composite feature: filled diamond at the
  owner; reference feature: hollow diamond at the owner and an open arrow at the type;
  dependency: dashed line with an open arrow;
* action flow: actions are rounded boxes with their parameters as pins on the border, start is a
  filled circle, done a bull's eye, decide a diamond; successions are open arrows, flows filled
  arrows from an out pin to an in pin, guards in brackets;
* state transition: states are rounded boxes, the entry is a filled circle, transitions are open
  arrows labelled ``trigger [guard]``;
* use cases: use cases are ellipses inside the subject, actors are stick figures, «include» is a
  dashed arrow.

Graph format (shared with ``views.__init__``): nodes ``{id, label, sysml_kind, parent, trace_id,
layer, configs, ports, shape, w, h, body, tooltip}``, edges ``{id, src, dst, sysml_kind, label,
rel}``. ``body`` (compartment text) becomes a child cell ``<id>#body``. Node IDs are qualified
names, so the output is stable and readable in diffs.
"""
from __future__ import annotations

from curatrix.model import Model

GENERAL_KINDS = ("specialization", "composition", "reference", "dependency")

KEYWORD = {
    "Package": "package", "LibraryPackage": "library package",
    "PartDefinition": "part def", "PartUsage": "part",
    "ItemDefinition": "item def", "ItemUsage": "item",
    "AttributeDefinition": "attribute def", "AttributeUsage": "attribute",
    "EnumerationDefinition": "enum def", "EnumerationUsage": "enum",
    "PortDefinition": "port def", "PortUsage": "port",
    "ActionDefinition": "action def", "ActionUsage": "action",
    "StateDefinition": "state def", "StateUsage": "state",
    "ConnectionDefinition": "connection def", "ConnectionUsage": "connection",
    "InterfaceDefinition": "interface def", "InterfaceUsage": "interface",
    "RequirementDefinition": "requirement def", "RequirementUsage": "requirement",
    "UseCaseDefinition": "use case def", "UseCaseUsage": "use case",
    "ViewDefinition": "view def", "ViewUsage": "view",
    "MetadataDefinition": "metadata def", "OccurrenceDefinition": "occurrence def",
    "ConstraintDefinition": "constraint def", "CalculationDefinition": "calc def",
}
SKIP_OWNED = {"MetadataUsage", "Documentation", "Comment", "Multiplicity", "MultiplicityRange", "TextualRepresentation"}
CHAR_W = 6.6          # average character width at font size 11 (Helvetica), for box sizes
LINE_H = 15


class GraphError(Exception):
    pass


# ------------------------------------------------------------------ small model helpers
def name(p: dict | None) -> str:
    if not p:
        return ""
    return p.get("declaredName") or p.get("name") or ""


def is_def(p: dict) -> bool:
    return p.get("@type", "").endswith("Definition")


def keyword(p: dict) -> str:
    kw = KEYWORD.get(p.get("@type", ""), p.get("@type", "").replace("Usage", "").replace("Definition", " def").lower())
    if p.get("isAbstract") and p.get("@type") != "Package":
        kw = "abstract " + kw
    return kw


def header(p: dict, with_keyword: bool = True) -> str:
    sn = p.get("declaredShortName")
    title = (f"<{sn}> " if sn else "") + name(p)
    return f"«{keyword(p)}»\n{title}" if with_keyword else title


def doc_of(m: Model, p: dict) -> str:
    for _, x in m.owned(p):
        if x.get("@type") == "Documentation" and x.get("body"):
            return " ".join(str(x["body"]).split())
    return ""


def see_of(m: Model, p: dict) -> str:
    return str(m.trace_meta(p, "XdTrace::See").get("needId") or "")


def owned_of(m: Model, p: dict, *types: str) -> list[dict]:
    return [x for _, x in m.owned(p) if not types or x.get("@type") in types]


def related(m: Model, p: dict, *rel_types: str) -> list[dict]:
    """Targets of p's owned relationships of the given types (e.g. Subclassification)."""
    out = []
    for r in p.get("ownedRelationship", []) or []:
        rel = m.get(r)
        if rel and rel.get("@type") in rel_types:
            t = m.get(rel.get("general")) or m.get((rel.get("target") or [None])[0])
            if t:
                out.append(t)
    return out


def literal(m: Model, x: dict | None) -> str:
    if not x:
        return ""
    t = x.get("@type", "")
    if t == "LiteralInfinity":
        return "*"
    if t.startswith("Literal"):
        v = x.get("value")
        return str(v).lower() if isinstance(v, bool) else str(v)
    if t == "FeatureReferenceExpression":
        if m.get(x.get("referent")):
            return name(m.get(x.get("referent")))
        for _, y in m.owned(x):
            if y.get("@type") != "ParameterMembership":
                return name(m.get(y.get("referent"))) or name(y)
        return name(m.get(x.get("referent")))
    if t == "OperatorExpression":
        args = []
        for rel, y in m.owned(x):
            if rel.get("@type") == "ParameterMembership":      # an argument: x = <expression>
                args.append(literal(m, y))
        args = [a for a in args if a]
        op = x.get("operator") or ""
        if len(args) == 1:
            return f"{op} {args[0]}"
        return f" {op} ".join(args)
    for rel, y in m.owned(x):          # a feature with a bound value (e.g. an argument wrapper)
        if rel.get("@type") == "FeatureValue":
            return literal(m, y)
    return name(x)


def multiplicity(m: Model, f: dict) -> str:
    for _, x in m.owned(f):
        if x.get("@type") == "MultiplicityRange":
            lo, hi = literal(m, m.get(x.get("lowerBound"))), literal(m, m.get(x.get("upperBound")))
            if lo and hi:
                return f"[{lo}..{hi}]"
            return f"[{hi or lo}]"
    return ""


def value_of(m: Model, f: dict) -> str:
    """The bound value of a feature (``= Domain::SYS``), as text."""
    for rel, x in m.owned(f):
        if rel.get("@type") != "FeatureValue":
            continue
        t = x.get("@type", "")
        if t.endswith("Expression") or t.startswith("Literal"):
            return literal(m, x)
    return ""


def type_names(m: Model, f: dict) -> str:
    return ", ".join(name(t) for t in m.types_of(f) if name(t))


def link_name(m: Model, f: dict) -> str:
    """The name a reference feature stands for: the redefined or subsetted feature's name if it
    is declared in a general type (a link type), else its own name."""
    for rel_type in ("Redefinition", "Subsetting"):
        for g in related(m, f, rel_type):
            if name(g):
                return name(g)
    return name(f)


def features(m: Model, d: dict) -> list[dict]:
    """Owned, named (or redefining) usages of a definition or usage."""
    out = []
    for _, x in m.owned(d):
        t = x.get("@type", "")
        if t in SKIP_OWNED or not t.endswith("Usage") or t in ("ViewUsage",):
            continue
        if name(x) or related(m, x, "Redefinition"):
            out.append(x)
    return out


def size_for(lines: list[str], min_w: float = 130, pad_w: float = 24, pad_h: float = 12) -> tuple[float, float]:
    w = max([len(s) for s in lines] or [0]) * CHAR_W + pad_w
    return max(min_w, round(w)), round(len(lines) * LINE_H + pad_h)


def node(nid, label, kind, parent="1", shape="def", trace_id="", w=None, h=None, sections=None, tooltip="", ports=None):
    """sections: [(compartment title, [entries])], drawn below the header."""
    lines = label.split("\n")
    sections = sections or []
    header_h = round(len(lines) * LINE_H + 10)
    entries = [e for _, es in sections for e in es] + [t for t, _ in sections]
    bw, _ = size_for(lines + entries)
    bh = header_h + sum(2 + 13 + 13 * len(es) + 4 + 6 for _, es in sections) + (4 if sections else 0)
    return {"id": nid, "label": label, "sysml_kind": kind, "parent": parent, "trace_id": trace_id, "layer": "",
            "configs": "", "ports": ports or [], "shape": shape, "w": w or bw, "h": h or max(bh, round(len(lines) * LINE_H + 16)),
            "body": "\n".join(e for _, es in sections for e in es), "sections": sections,
            "header_h": header_h, "tooltip": tooltip}


def edge(src, dst, rel, kind, label="", eid=None):
    return {"id": eid or f"{src}->{dst}:{rel}:{label}", "src": src, "dst": dst, "sysml_kind": kind,
            "label": label, "rel": rel}


# ------------------------------------------------------------------ general view
def general(m: Model, v, opts: dict) -> dict:
    show = {s.strip() for s in (opts.get("show") or ",".join(GENERAL_KINDS)).split(",") if s.strip()}
    # compartments: "all" (features), "root" (features of abstract types), "doc", "none"; a list
    # such as "root,doc" combines them
    comp = {c.strip() for c in (opts.get("compartments") or "all").lower().split(",") if c.strip()}
    # between = "P1, P2": a view of the relations between two (or more) packages. Only edges
    # whose ends lie in different packages of the list are drawn, and only elements with such an
    # edge are shown.
    between = [b.strip() for b in (opts.get("between") or "").split(",") if b.strip()]
    if not v.exposed:
        raise GraphError(f"view {v.name}: a general view needs `expose` (no element exposed)")
    els = [m.get(x) for x in sorted(v.exposed)]
    els = [p for p in els if p and not p.get("isLibraryElement") and p.get("@type") != "ViewUsage"
           and (p.get("@type", "").endswith(("Definition", "Usage")) or p.get("@type") == "Package")]
    shown = {p["@id"] for p in els}
    g = {"nodes": [], "edges": []}

    def required_in_total(owner: dict, link: str) -> bool:
        """A link split into one feature per target type (subsetting) can still be required as a
        whole: the owner redefines the general link feature with a lower bound >= 1."""
        for f in features(m, owner):
            if related(m, f, "Redefinition") and link_name(m, f) == link:
                lo = multiplicity(m, f).strip("[]").split("..")[0]
                if lo not in ("", "0", "*"):
                    return True
        return False

    for p in sorted(els, key=lambda p: p.get("qualifiedName") or p["@id"]):
        pid = p["qualifiedName"] if p.get("qualifiedName") else p["@id"]
        sections = {}
        for f in features(m, p):
            ft = f.get("@type", "")
            types = [t for t in m.types_of(f)]
            to_shown = [t for t in types if t["@id"] in shown]
            is_ref = bool(f.get("isReference")) and ft != "AttributeUsage" and ft != "PortUsage"
            rel = "reference" if is_ref else "composition"
            if to_shown and not f.get("isAbstract") and rel in show and ft not in ("AttributeUsage", "PortUsage"):
                for t in to_shown:
                    lbl = (link_name(m, f) if is_ref else name(f)) + (" " + multiplicity(m, f) if multiplicity(m, f) else "")
                    if is_ref and not related(m, f, "Redefinition") and link_name(m, f) != name(f) \
                            and required_in_total(p, link_name(m, f)):
                        lbl += " (>= 1 in total)"
                    g["edges"].append(edge(pid, t["qualifiedName"], rel, "ReferenceUsage" if is_ref else ft, lbl,
                                           eid=f"{pid}->{t['qualifiedName']}:{name(f) or link_name(m, f)}"))
                continue
            if to_shown and not f.get("isAbstract"):
                continue          # an edge kind the view hides: not listed either
            redef = [name(x) for x in related(m, f, "Redefinition")]
            fname = name(f) or (redef[0] if redef else "")
            if ft == "AttributeUsage":
                val = value_of(m, f)
                tn = type_names(m, f)
                line = f"{fname} = {val}" if val else f"{fname}" + (f" : {tn}" if tn else "")
                sec = "attributes"
            elif ft == "PortUsage":
                line, sec = f"{fname} : {type_names(m, f)}", "ports"
            else:
                sec = "references" if is_ref else ("parts" if ft == "PartUsage" else "items" if ft == "ItemUsage" else "features")
                tn = type_names(m, f)
                line = fname + (f" : {tn}" if tn else "")
            mult = multiplicity(m, f)
            sections.setdefault(sec, []).append(line + (f" {mult}" if mult else ""))
        with_body = "all" in comp or ("root" in comp and p.get("isAbstract"))
        secs = [(s, sections[s]) for s in ("attributes", "ports", "parts", "items", "references", "features")
                if with_body and sections.get(s)]
        if "doc" in comp and doc_of(m, p):
            secs.insert(0, ("doc", _wrap_words(doc_of(m, p), 36)))
        shape = "package" if p.get("@type") == "Package" else ("def" if is_def(p) else
                                                                 "ref" if p.get("isReference") else "usage")
        n = node(pid, header(p), p["@type"], shape=shape, trace_id=see_of(m, p), sections=secs, tooltip=doc_of(m, p))
        n["_generals"] = [(gen.get("qualifiedName") or gen["@id"], name(gen)) for gen in related(m, p, "Subclassification")]
        g["nodes"].append(n)
        if "specialization" in show:
            for gen in related(m, p, "Subclassification"):
                if gen["@id"] in shown:
                    g["edges"].append(edge(pid, gen["qualifiedName"], "specialization", "Subclassification"))
    if "dependency" in show:
        for d in m.of_type("Dependency"):
            for c in d.get("client", []) or []:
                for s in d.get("supplier", []) or []:
                    c_, s_ = m.get(c), m.get(s)
                    if c_ and s_ and c_["@id"] in shown and s_["@id"] in shown:
                        g["edges"].append(edge(c_["qualifiedName"], s_["qualifiedName"], "dependency", "Dependency"))
    ids = {n["id"] for n in g["nodes"]}
    g["edges"] = [e for e in g["edges"] if e["src"] in ids and e["dst"] in ids]
    if between:
        def pkg(qn: str) -> str | None:
            hits = [b for b in between if qn.startswith(b + "::")]
            return max(hits, key=len) if hits else None
        g["edges"] = [e for e in g["edges"] if pkg(e["src"]) and pkg(e["dst"]) and pkg(e["src"]) != pkg(e["dst"])]
        used = {e[k] for e in g["edges"] for k in ("src", "dst")}
        g["nodes"] = [n for n in g["nodes"] if n["id"] in used]
        if not g["nodes"]:
            raise GraphError(f"view {v.name}: no relations between {', '.join(between)}")
    # a general type that is not drawn (box and triangle) is named in the header in the textual
    # notation, `:> General`, so the category of each type stays visible
    drawn = {(e["src"], e["dst"]) for e in g["edges"] if e["rel"] == "specialization"}
    for n in g["nodes"]:
        hidden = [gname for gid, gname in n.pop("_generals") if (n["id"], gid) not in drawn]
        if hidden:
            lines = n["label"].split("\n") + [f":> {', '.join(hidden)}"]
            grown = node(n["id"], "\n".join(lines), n["sysml_kind"], shape=n["shape"], sections=n["sections"])
            n.update({k: grown[k] for k in ("label", "w", "h", "header_h")})
    return g


def _wrap_words(text: str, cols: int) -> list[str]:
    import textwrap
    return textwrap.wrap(text, cols) or [text]


# ------------------------------------------------------------------ action flow view
def _guard_label(m: Model, t: dict) -> str:
    owned = [x for _, x in m.owned(t)]
    # the guard expression is the member named `guard`; fall back to the first expression
    owned.sort(key=lambda x: 0 if name(x) == "guard" else 1)
    for x in owned:
        if x.get("@type") in ("SuccessionAsUsage", "ReferenceUsage") or x.get("@type") in SKIP_OWNED:
            continue
        if x.get("@type", "").endswith("Expression") or x.get("@type", "").startswith("Literal"):
            s = literal(m, x)
            return f"[{s}]" if s else ""
    return ""


def _trigger_label(m: Model, t: dict) -> str:
    for _, x in m.owned(t):
        if x.get("@type") == "AcceptActionUsage":
            for _, y in m.owned(x):
                if name(y) == "payload":
                    return type_names(m, y)
    return ""


def _effective(m: Model, ref: str, root: dict, special: dict) -> str | None:
    """Node id for a succession/transition end: a user action/state/control node, or start/done/entry."""
    p = m.get(ref)
    if p is None:
        if isinstance(ref, str) and ref.endswith("::start"):
            return special.setdefault("start", f"{root['qualifiedName']}::start")
        if isinstance(ref, str) and ref.endswith("::done"):
            return special.setdefault("done", f"{root['qualifiedName']}::done")
        return None
    if p.get("isLibraryElement"):
        n = name(p)
        if n in ("start", "done"):
            return special.setdefault(n, f"{root['qualifiedName']}::{n}")
        return None
    if name(p) == "entryAction":
        return special.setdefault("start", f"{root['qualifiedName']}::entry")
    return p.get("qualifiedName") or p["@id"]


def _pin_side(direction: str, out: bool) -> str:
    return {"RIGHT": ("WEST", "EAST"), "LEFT": ("EAST", "WEST"), "DOWN": ("NORTH", "SOUTH"),
            "UP": ("SOUTH", "NORTH")}[direction][1 if out else 0]


def behaviour(m: Model, v, opts: dict, kind: str) -> dict:
    root = _find(m, v.root)
    direction = (opts.get("direction") or "DOWN").upper()
    rid = root["qualifiedName"]
    g = {"nodes": [], "edges": []}
    special: dict[str, str] = {}
    members = owned_of(m, root)
    action_types = ("ActionUsage", "AcceptActionUsage", "SendActionUsage", "PerformActionUsage")
    control = {"DecisionNode": "decision", "MergeNode": "decision", "ForkNode": "bar", "JoinNode": "bar"}
    ids = set()
    for x in members:
        t = x.get("@type", "")
        xid = x.get("qualifiedName") or x["@id"]
        if kind == "actionflow" and t in action_types and name(x) != "entryAction":
            pins = []
            for f in features(m, x):
                if f.get("direction") in ("in", "out", "inout"):
                    pins.append({"id": f"{xid}.{name(f)}", "label": name(f), "item": type_names(m, f),
                                 "side": _pin_side(direction, f.get("direction") == "out")})
            tn = type_names(m, x)
            label = f"«action»\n{name(x)}" + (f" : {tn}" if tn else "")
            n = node(xid, label, t, shape="action", trace_id=see_of(m, x), tooltip=doc_of(m, x), ports=pins)
            if pins and direction in ("RIGHT", "LEFT"):
                # room for the pin names inside the border, left and right of the action name
                side_w = {s: max([len(p["label"]) for p in pins if p["side"] == s] or [0]) * CHAR_W for s in ("WEST", "EAST")}
                n["w"] = max(n["w"], round(n["w"] + 2 * max(side_w.values()) + 12))
                n["h"] = max(n["h"], 18 + 22 * max([sum(1 for p in pins if p["side"] == s) for s in ("WEST", "EAST")] + [1]))
            elif pins:
                # pin names inside the border, in a row above and below the action name
                row_w = max(sum(len(p["label"]) * CHAR_W * 0.85 + 18 for p in pins if p["side"] == s)
                            for s in ("NORTH", "SOUTH"))
                n["w"] = max(n["w"], round(row_w + 16))
                n["h"] = n["h"] + 2 * 14
            g["nodes"].append(n)
            ids.add(xid)
        elif kind == "statetransition" and t == "StateUsage":
            body = doc_of(m, x)
            g["nodes"].append(node(xid, name(x), t, shape="state", trace_id=see_of(m, x), tooltip=body, w=None))
            ids.add(xid)
        elif t in control:
            g["nodes"].append(node(xid, "", t, shape=control[t], w=36 if control[t] == "decision" else 8,
                                   h=36 if control[t] == "decision" else 60, tooltip=name(x)))
            ids.add(xid)
    for x in members:
        t = x.get("@type", "")
        if t not in ("SuccessionAsUsage", "TransitionUsage", "FlowUsage", "SuccessionFlowUsage"):
            continue
        if t == "FlowUsage" or t == "SuccessionFlowUsage":
            ends = []
            for _, e in m.owned(x):
                if e.get("@type") != "FlowEnd":
                    continue
                act = related(m, e, "ReferenceSubsetting")
                pin = [name(y) for _, y in m.owned(e) if name(y)]
                if act and pin:
                    ends.append(f"{act[0].get('qualifiedName')}.{pin[0]}")
            if len(ends) == 2:
                item = type_names(m, [y for _, y in m.owned([e for _, e in m.owned(x) if e.get("@type") == "FlowEnd"][0]) if name(y)][0])
                # an out pin that feeds several actions names its item once
                if any(e["rel"] == "flow" and e["src"] == ends[0] and e["label"] == item for e in g["edges"]):
                    item = ""
                g["edges"].append(edge(ends[0], ends[1], "flow", t, item, eid=f"flow({ends[0]}->{ends[1]})"))
            continue
        src = x.get("source")
        dst = x.get("target")
        src = src[0] if isinstance(src, list) else src
        dst = dst[0] if isinstance(dst, list) else dst
        s, d = _effective(m, src, root, special), _effective(m, dst, root, special)
        if not s or not d:
            continue
        if t == "TransitionUsage":
            trig, guard = _trigger_label(m, x), _guard_label(m, x)
            label = " ".join(p for p in (trig, guard) if p)
            if not label and (m.get(src) or {}).get("@type") == "DecisionNode":
                label = "[else]"
        else:
            label = ""
        g["edges"].append(edge(s, d, "transition" if t == "TransitionUsage" else "succession", t, label,
                               eid=f"{s}->{d}" + (f":{label}" if label else "")))
    if "start" in special:
        g["nodes"].insert(0, node(special["start"], "", "start" if kind == "actionflow" else "entry", shape="initial", w=22, h=22))
    if "done" in special:
        g["nodes"].append(node(special["done"], "", "done", shape="final", w=26, h=26))
    known = {n["id"] for n in g["nodes"]} | {p["id"] for n in g["nodes"] for p in n["ports"]}
    seen, edges = set(), []
    for e in g["edges"]:
        if e["src"] in known and e["dst"] in known and e["id"] not in seen:
            seen.add(e["id"])
            edges.append(e)
    g["edges"] = edges
    # node order = first mention in the flow statements (they are written in flow order), so that
    # ELK's model-order cycle breaking turns only the real loops backwards
    rank: dict[str, int] = {}
    for e in edges:
        for end in (e["src"], e["dst"]):
            rank.setdefault(end.rsplit(".", 1)[0] if end not in known - {p["id"] for n in g["nodes"] for p in n["ports"]} else end, len(rank))
    g["nodes"].sort(key=lambda n: rank.get(n["id"], len(rank)))
    if kind == "statetransition":   # the state machine as a frame around its states
        frame = node(rid, f"«state def»\n{name(root)}", root["@type"], shape="frame", trace_id=see_of(m, root),
                     tooltip=doc_of(m, root))
        for n in g["nodes"]:
            n["parent"] = rid
        g["nodes"].insert(0, frame)
    return g


# ------------------------------------------------------------------ use case view
def usecases(m: Model, v, opts: dict) -> dict:
    root = _find(m, v.root)
    ucs = [x for x in m.walk(root) if x.get("@type") == "UseCaseDefinition" and not x.get("isLibraryElement")]
    if not ucs:
        raise GraphError(f"view {v.name}: no use case definitions under {v.root}")
    g = {"nodes": [], "edges": []}
    subjects: dict[str, dict] = {}      # subject type -> a subject usage (one frame per type)
    subject_of: dict[str, str] = {}     # use case -> subject frame id
    actors: dict[str, dict] = {}
    for uc in sorted(ucs, key=lambda u: u["qualifiedName"]):
        uid = uc["qualifiedName"]
        for r in uc.get("ownedRelationship", []) or []:
            rel = m.get(r) or {}
            for x in (m.get(y) for y in rel.get("ownedRelatedElement", []) or []):
                if not x:
                    continue
                if rel.get("@type") == "SubjectMembership":
                    st = (m.types_of(x) or [x])[0]
                    sid_ = st.get("qualifiedName") or st["@id"]
                    subjects.setdefault(sid_, x)
                    subject_of[uid] = sid_
                elif rel.get("@type") == "ActorMembership":
                    for t in m.types_of(x) or [x]:
                        aid = t.get("qualifiedName") or t["@id"]
                        actors.setdefault(aid, t)
                        g["edges"].append(edge(aid, uid, "association", "ActorMembership", "",
                                               eid=f"{aid}--{uid}"))
                elif x.get("@type") == "IncludeUseCaseUsage":
                    for t in m.types_of(x):
                        g["edges"].append(edge(uid, t["qualifiedName"], "include", "IncludeUseCaseUsage", "«include»"))
    no_subject = f"{root.get('qualifiedName')}::(no subject)"
    for sid, subj in sorted(subjects.items()):
        g["nodes"].append(node(sid, f"«subject»\n{name(subj)} : {type_names(m, subj)}", "SubjectMembership",
                               shape="subject", w=10, h=10))
    if any(uc["qualifiedName"] not in subject_of for uc in ucs):
        g["nodes"].append(node(no_subject, "«subject»\n(none)", "SubjectMembership", shape="subject", w=10, h=10))
    for uc in sorted(ucs, key=lambda u: u["qualifiedName"]):
        sid = subject_of.get(uc["qualifiedName"], no_subject)
        lab = f"«use case def»\n{name(uc)}"
        w, h = size_for(lab.split("\n"), min_w=150)
        g["nodes"].append(node(uc["qualifiedName"], lab, "UseCaseDefinition", parent=sid, shape="usecase",
                               trace_id=see_of(m, uc), w=round(w * 1.25), h=max(56, round(h * 1.3)), tooltip=doc_of(m, uc)))
    for aid, t in sorted(actors.items()):
        g["nodes"].append(node(aid, name(t), t.get("@type", "PartDefinition"), shape="actor", w=40, h=56,
                               trace_id=see_of(m, t), tooltip=doc_of(m, t)))
    return g


def _find(m: Model, qname: str | None) -> dict:
    if not qname:
        raise GraphError("@XdView needs root")
    for p in m.e.values():
        if p.get("qualifiedName") == qname and not p.get("isLibraryElement"):
            return p
    raise GraphError(f"root {qname!r} not found in the model")


def build(m: Model, v, opts: dict) -> dict:
    if v.kind == "general":
        g = general(m, v, opts)
    elif v.kind in ("actionflow", "statetransition"):
        g = behaviour(m, v, opts, v.kind)
    elif v.kind == "usecases":
        g = usecases(m, v, opts)
    else:
        raise GraphError(f"view {v.name}: kind {v.kind!r} is not a SysML standard view here")
    g.update({"view": v.name, "kind": v.kind, "short_id": v.short_id or "", "root": v.root or "",
              "direction": (opts.get("direction") or "DOWN").upper()})
    return g
