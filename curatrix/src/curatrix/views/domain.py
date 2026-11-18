"""Views between a domain model and the system model it refines: ``allocation`` and ``variants``.

``allocation`` (views.md §2): the elements of a domain model (boards, harnesses, assemblies, their
ports) and the system elements and interfaces they realize or conform to. The links are the trace
links curatrix derives for the needs (``model.to_needs``): ``D :> S`` across the repo boundary
(XD-ADR-0132), ``dependency from D to S`` and ``allocate``, with the link type by the kind pair
(``model.LINK_BY_KINDS``). So the view shows exactly the links of the generated needs. A port def
that is part of a board or assembly is drawn with a «part of» line to it.

``variants`` (XD-ADR-0136, D102): a domain def and its variants (defs that specialize it and
``XdDomain::DomainVariant``), each with its ``variantName`` and documentation, and the
configurations and system usages each variant serves (``dependency from Variant to ...``).

Root: a package (every element with a trace ID inside it) or one definition. Domain elements are
white boxes, elements of the upstream (system) model grey. No package frames: lines across frames
route badly in ELK. Edges point from the concrete element to the abstract one (the trace rule, D5).
"""
from __future__ import annotations

from curatrix.model import Model, element_id, to_needs
from curatrix.views.sysml import KEYWORD, GraphError, doc_of, edge, features, header, name, node, value_of, _wrap_words

# links drawn from a domain need, in this order; `configs` and `instances` are no lines
LINKS = ("realizes", "conforms", "satisfies", "part_of", "connects")
LABEL = {"part_of": "«part of»"}
UPSTREAM_FILL = "#EEEEEE"


def _scope(m: Model, root: dict) -> list[dict]:
    """The own definitions with a trace ID of the view."""
    rq = root.get("qualifiedName") or ""
    if root.get("@type", "").endswith("Package"):
        return [p for p in m.user() if p.get("@type", "").endswith("Definition") and element_id(m, p)
                and (p.get("qualifiedName") or "").startswith(rq + "::")]
    return [root]


def _upstream(m: Model, t: dict) -> bool:
    """An element of the upstream (system) model: a library element in the compact JSON, or a
    trace ID without an element (a placeholder). Colour by origin, not by the view's scope."""
    return bool(t.get("isLibraryElement")) or not t.get("@type")


def _target_node(m: Model, t: dict) -> dict:
    q = t["qualifiedName"]
    if t.get("@type", "").endswith("Usage"):
        label = f"«{KEYWORD.get(t['@type'], 'usage')}»\n{q.split('::', 1)[-1]}"
        shape = "usage"
    else:
        label, shape = (header(t) if t.get("@type") else q), "def"
    n = node(q, label, t.get("@type") or "need", shape=shape, trace_id=element_id(m, t) or t.get("declaredShortName") or "")
    if _upstream(m, t):
        n["fill"] = UPSTREAM_FILL
    return n


def allocation(m: Model, v, opts: dict, root: dict) -> dict:
    els = _scope(m, root)
    doc, _ = to_needs(m)
    needs = doc["versions"][""]["needs"]
    by_id: dict[str, dict] = {}
    for p in m.e.values():
        tid = element_id(m, p)
        if tid and tid not in by_id and p.get("qualifiedName"):
            by_id[tid] = p
    # only elements that are needs (a CAD-owned kind such as ME-PART is a reference, XD-ADR-0128)
    own = {element_id(m, p): p for p in els if element_id(m, p) in needs}
    if not own:
        raise GraphError(f"no definition with a trace ID (a need) in {root.get('qualifiedName')}")
    g = {"nodes": [], "edges": []}
    upstream: dict[str, dict] = {}          # trace ID -> upstream element (or a placeholder)
    for sid in sorted(own):
        p = own[sid]
        g["nodes"].append(node(p["qualifiedName"], header(p), p["@type"], shape="def", trace_id=sid, tooltip=doc_of(m, p)))
    for sid in sorted(own):
        n = needs.get(sid) or {}
        src = own[sid]["qualifiedName"]
        for link in LINKS:
            for tid in n.get(link, []):
                if tid in own:
                    dst = own[tid]["qualifiedName"]
                else:
                    upstream[tid] = by_id.get(tid) or {"qualifiedName": tid, "@type": "", "declaredShortName": tid}
                    dst = upstream[tid]["qualifiedName"]
                g["edges"].append(edge(src, dst, "allocation", link, LABEL.get(link, f"«{link}»"),
                                       eid=f"{src}->{dst}:{link}"))
    for t in sorted(upstream.values(), key=lambda t: t["qualifiedName"]):
        g["nodes"].append(_target_node(m, t))
    g["direction"] = (opts.get("direction") or "UP").upper()
    return g


def _is_variant(m: Model, p: dict) -> bool:
    seen, todo = set(), [p]
    while todo:
        x = todo.pop()
        if x["@id"] in seen:
            continue
        seen.add(x["@id"])
        if x.get("qualifiedName") == "XdDomain::DomainVariant":
            return True
        todo += m.supers(x)
    return False


def variants(m: Model, v, opts: dict, root: dict) -> dict:
    if not root.get("@type", "").endswith("Definition"):
        raise GraphError("the root of a variants view is a definition")
    rid = root["qualifiedName"]
    g = {"nodes": [node(rid, header(root), root["@type"], shape="def", trace_id=element_id(m, root) or "",
                        tooltip=doc_of(m, root))], "edges": []}
    vs = sorted((p for p in m.user() if p.get("@type", "").endswith("Definition")
                 and any(s["@id"] == root["@id"] for s in m.supers(p)) and _is_variant(m, p)),
                key=lambda p: p["qualifiedName"])
    if not vs:
        raise GraphError(f"{rid} has no variants (defs that specialize it and XdDomain::DomainVariant)")
    upstream: dict[str, dict] = {}
    for p in vs:
        pid = p["qualifiedName"]
        attrs = [f"{name(f) or 'variantName'} = {value_of(m, f)}" for f in features(m, p) if value_of(m, f)]
        secs = [("attributes", attrs)] if attrs else []
        if doc_of(m, p):
            secs.insert(0, ("doc", _wrap_words(doc_of(m, p), 36)))
        g["nodes"].append(node(pid, header(p), p["@type"], shape="def", sections=secs, tooltip=doc_of(m, p)))
        g["edges"].append(edge(pid, rid, "specialization", "Subclassification"))
        for d in m.of_type("Dependency"):
            if d.get("isLibraryElement") or not any((m.get(c) or {}).get("@id") == p["@id"] for c in d.get("client") or []):
                continue
            for s in d.get("supplier") or []:
                t = m.get(s)
                if t and t.get("qualifiedName"):
                    upstream[t["qualifiedName"]] = t
                    g["edges"].append(edge(pid, t["qualifiedName"], "allocation", "Dependency", "«serves»",
                                           eid=f"{pid}->{t['qualifiedName']}:serves"))
    for q in sorted(upstream):
        g["nodes"].append(_target_node(m, upstream[q]))
    g["direction"] = (opts.get("direction") or "UP").upper()
    return g
