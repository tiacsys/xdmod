"""SysML model JSON: compaction, queries, and model -> needs (D22, D29, D42, D65, D128-D130).

The Pilot's JSON export (a list of ``{"identity": {"@id"}, "payload": {...}}``) is large (MBs
for a small model: every derived property, every referenced library element) and its element
IDs are not stable. ``compact()`` turns it into the committed ``generated/model.json``:

* every non-library element, with the payload keys in ``KEEP`` only;
* library elements that are referenced, as stubs (``@type``, names, ``qualifiedName``);
* stable IDs: the qualified name where it is unique, else ``<owner id>/<index>``;
* sorted, so a regeneration of an unchanged model is byte-identical.

The compact file has the same shape as the Pilot export, so every reader here (views,
variants, needs) works on both.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

from curatrix import ids as idmod
from curatrix import tracemodel

# Payload keys kept for non-library elements (what our readers use).
KEEP = {
    "@type", "name", "declaredName", "declaredShortName", "shortName", "qualifiedName", "isLibraryElement",
    "owner", "owningNamespace", "owningType", "owningRelationship", "ownedRelationship", "ownedRelatedElement",
    "relatedElement", "source", "target", "client", "supplier", "type", "definition", "ownedPart",
    "metadataDefinition", "annotatedElement", "annotatingElement", "ownedAnnotation",
    "satisfiedRequirement", "satisfyingFeature", "chainingFeature", "relatedFeature", "connectorEnd",
    "value", "exposedElement", "referent", "redefinedFeature", "subsettedFeature", "superclassifier",
    "subclassifier", "specific", "general", "typedFeature", "membershipOwningNamespace", "ownedVariantUsage",
    "memberElement", "memberName", "importedMembership", "importedNamespace", "isVariation", "isVariant",
    "isComposite", "isAbstract", "isConjugated", "direction", "operator", "originalPortDefinition",
    "conjugatedPortDefinition", "featureWithValue", "lowerBound", "upperBound", "bound", "body",
    "ownedFeature", "ownedMember", "feature", "isReference", "isEnd", "documentation",
}
STUB_KEYS = ("@type", "name", "declaredName", "declaredShortName", "qualifiedName")

# need kinds generated from a model (trace-model.md §2): the system model's and the domain
# models' (XD-ADR-0128, XD-ADR-0133)
MODEL_KINDS = ("SYS-EL", "SYS-IF", "SYS-UC", "SYS-CFG", "SYS-FEAT", "EE-PCBA", "EE-PORT", "EE-HAR", "ME-ASM", "ME-PORT")
# (source kind, target kind) -> link type, for `dependency from S to T`, `allocate T to S` and,
# across the repo boundary, `S :> T` (XD-ADR-0132)
LINK_BY_KINDS = {
    ("SYS-UC", "SYS-NEED"): "addresses",
    ("SYS-EL", "SYS-UC"): "realizes",
    ("SYS-EL", "SYS-EL"): "realizes",
    ("SYS-EL", "SYS-REQ"): "satisfies",
    ("SYS-CFG", "SYS-EL"): "configures",
    ("EE-PCBA", "SYS-EL"): "realizes",
    ("EE-HAR", "SYS-EL"): "realizes",
    ("ME-ASM", "SYS-EL"): "realizes",
    ("EE-PORT", "SYS-IF"): "conforms",
    ("ME-PORT", "SYS-IF"): "conforms",
}
# a port need is `part_of` the domain defs of these kinds that own a port typed by it (XD-ADR-0133)
PART_OF_KINDS = {"EE-PORT": ("EE-PCBA",), "ME-PORT": ("ME-ASM",)}
LINK_KEYS = ("satisfies", "realizes", "addresses", "configures", "conforms", "part_of")
LAYERS = tracemodel.field_enum("layer")          # from needs_config.toml (task 5.2)
STATUSES = tracemodel.field_enum("status")


def _ref(r):
    return r.get("@id") if isinstance(r, dict) else None


class Model:
    """Read access to a Pilot-format model JSON (full or compact)."""

    def __init__(self, data: list[dict]):
        self.e: dict[str, dict] = {x["identity"]["@id"]: x["payload"] for x in data}
        self._meta: dict[str, list[dict]] | None = None

    @classmethod
    def load(cls, path: Path) -> "Model":
        return cls(json.loads(Path(path).read_text()))

    def get(self, ref) -> dict | None:
        if isinstance(ref, dict):
            ref = ref.get("@id")
        return self.e.get(ref) if ref else None

    def id_of(self, p: dict) -> str:
        return p["@id"]

    def of_type(self, *types: str) -> list[dict]:
        return [p for p in self.e.values() if p.get("@type") in types]

    def user(self) -> list[dict]:
        return [p for p in self.e.values() if not p.get("isLibraryElement")]

    @staticmethod
    def qn(p: dict | None) -> str:
        if not p:
            return ""
        return p.get("qualifiedName") or p.get("name") or p.get("@type", "")

    def owned(self, p: dict):
        """(relationship, element) for every element owned through p's owned relationships."""
        for r in p.get("ownedRelationship", []) or []:
            rel = self.get(r)
            if not rel:
                continue
            for x in rel.get("ownedRelatedElement", []) or []:
                el = self.get(x)
                if el:
                    yield rel, el

    def walk(self, p: dict):
        yield p
        for _, x in self.owned(p):
            yield from self.walk(x)

    def owner(self, p: dict) -> dict | None:
        o = self.get(p.get("owner")) or self.get(p.get("owningNamespace"))
        if o is None and p.get("owningRelationship"):
            rel = self.get(p["owningRelationship"])
            o = self.get(rel.get("owner")) if rel else None
        return o

    # ---------------------------------------------------------------- metadata (@Trace, @XdView, @NeedRef)
    def metadata(self, p: dict) -> list[dict]:
        if self._meta is None:
            self._meta = defaultdict(list)
            for m in self.of_type("MetadataUsage"):
                for a in m.get("annotatedElement", []) or []:
                    if _ref(a):
                        self._meta[_ref(a)].append(m)
        return self._meta.get(p["@id"], [])

    def meta_name(self, m: dict) -> str:
        return self.qn(self.get(m.get("metadataDefinition")))

    def meta_attrs(self, m: dict) -> dict[str, object]:
        """Attribute values of a metadata usage: {name: literal value}."""
        out = {}
        for _, f in self.owned(m):
            if not f.get("name"):
                continue
            for _, v in self.owned(f):
                if "value" in v and v.get("@type", "").startswith("Literal"):
                    out[f["name"]] = v["value"]
        return out

    def trace_meta(self, p: dict, name: str) -> dict:
        """Merged attributes of all metadata usages of `name` (e.g. 'XdTrace::Trace') on p."""
        out: dict[str, object] = {}
        for m in self.metadata(p):
            if self.meta_name(m) == name:
                out.update(self.meta_attrs(m))
        return out

    def inherited_meta(self, p: dict, name: str, attr: str):
        """attr from p's own metadata, else from the nearest owner that has it (packages)."""
        seen = set()
        cur = p
        while cur is not None and cur["@id"] not in seen:
            seen.add(cur["@id"])
            v = self.trace_meta(cur, name).get(attr)
            if v not in (None, ""):
                return v
            cur = self.owner(cur)
        return None

    def types_of(self, p: dict) -> list[dict]:
        return [t for t in (self.get(x) for x in p.get("type", []) or []) if t]

    def rels(self, p: dict, typ: str):
        """p's owned relationships of @type `typ`."""
        for r in p.get("ownedRelationship", []) or []:
            rel = self.get(r)
            if rel and rel.get("@type") == typ:
                yield rel

    def supers(self, p: dict) -> list[dict]:
        """Direct superclassifiers (``:>`` of a definition)."""
        return [x for x in (self.get(r.get("superclassifier") or r.get("general"))
                            for r in self.rels(p, "Subclassification")) if x]


# ------------------------------------------------------------------ compaction
_PKG = re.compile(r"(?<![\w:])(?:standard\s+)?(?:library\s+)?package\s+(?:<'?[^>]*'?>\s*)?('[^']+'|\w+)")
_BLANK = re.compile(r"//[^\n]*|/\*.*?\*/|\"(?:\\.|[^\"\\])*\"", re.S)


def top_packages(files: list[Path]) -> set[str]:
    """Top-level package names declared in the files (for library files: they become stubs).
    Nested packages are not top-level: the brace depth of the declaration must be 0 (comments,
    doc texts and strings are blanked first). The Pilot cannot export a nested package by its
    simple name, and its top package exports it anyway (model spike)."""
    out = set()
    for f in files:
        text = _BLANK.sub(lambda m: re.sub(r"[^\n]", " ", m.group(0)), Path(f).read_text())
        depth, pos = 0, 0
        for m in _PKG.finditer(text):
            seg = text[pos:m.start()]
            depth += seg.count("{") - seg.count("}")
            pos = m.start()
            if depth == 0:
                out.add(m.group(1).strip("'"))
    return out


def compact(data: list[dict], library_packages: set[str] = frozenset()) -> list[dict]:
    E = {x["identity"]["@id"]: x["payload"] for x in data}

    def is_lib(p):
        if p.get("isLibraryElement"):
            return True
        q = p.get("qualifiedName") or ""
        return bool(q) and q.split("::")[0].strip("'") in library_packages

    # ownership: parent -> ordered children (relationships and related elements)
    children: dict[str, list[str]] = defaultdict(list)
    has_parent = set()
    for i, p in E.items():
        for r in p.get("ownedRelationship", []) or []:
            if _ref(r) in E:
                children[i].append(_ref(r)); has_parent.add(_ref(r))
        for r in p.get("ownedRelatedElement", []) or []:
            if _ref(r) in E:
                children[i].append(_ref(r)); has_parent.add(_ref(r))
    roots = sorted((i for i in E if i not in has_parent and not is_lib(E[i])),
                   key=lambda i: (E[i].get("qualifiedName") or "", E[i].get("@type", ""), i))
    qn_count = defaultdict(int)
    for p in E.values():
        if p.get("qualifiedName"):
            qn_count[p["qualifiedName"]] += 1

    new_id: dict[str, str] = {}
    keep: list[str] = []

    def assign(i, path):
        p = E[i]
        q = p.get("qualifiedName")
        nid = q if q and qn_count[q] == 1 else path
        if nid in new_id.values():
            nid = path
        new_id[i] = nid
        keep.append(i)
        for k, c in enumerate(children.get(i, [])):
            if c not in new_id and not E[c].get("isLibraryElement"):
                assign(c, f"{nid}/{k}")

    for n, r in enumerate(roots):
        if r not in new_id:
            assign(r, E[r].get("qualifiedName") or f"root{n}")

    # referenced elements outside the kept set become stubs
    def refs(v):
        if isinstance(v, dict) and "@id" in v:
            yield v["@id"]
        elif isinstance(v, list):
            for x in v:
                yield from refs(x)

    # Referenced library elements become stubs, but only named ones: unnamed library elements
    # (memberships, relationships) carry nothing our readers use, and only their random Pilot IDs
    # would tell them apart, so references to them are dropped.
    stubs = set()
    for i in keep:
        for k, v in E[i].items():
            if k in KEEP:
                for r in refs(v):
                    if r not in new_id and r in E and E[r].get("qualifiedName"):
                        stubs.add(r)
    for s in sorted(stubs, key=lambda s: (E[s].get("qualifiedName") or "", E[s].get("@type", ""), s)):
        base = f"lib:{E[s]['qualifiedName']}"
        nid, n = base, 1
        while nid in new_id.values():
            n += 1
            nid = f"{base}#{n}"
        new_id[s] = nid

    def remap(v):
        if isinstance(v, dict) and set(v) == {"@id"}:
            return {"@id": new_id[v["@id"]]} if v["@id"] in new_id else None
        if isinstance(v, list):
            return [x for x in (remap(x) for x in v) if x is not None]
        return v

    out = []
    for i in keep:
        p = {k: rv for k, v in E[i].items() if k in KEEP for rv in (remap(v),) if rv not in (None, [], "")}
        p["@id"] = new_id[i]
        if E[i].get("isLibraryElement"):
            p["isLibraryElement"] = True
        out.append({"identity": {"@id": new_id[i]}, "payload": p})
    for s in stubs:
        p = {k: E[s][k] for k in STUB_KEYS if E[s].get(k) not in (None, "")}
        p["@id"] = new_id[s]
        p["isLibraryElement"] = True
        out.append({"identity": {"@id": new_id[s]}, "payload": p})
    out.sort(key=lambda x: x["identity"]["@id"])
    return out


def dumps(data) -> str:
    return json.dumps(data, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


# ------------------------------------------------------------------ model -> needs
def element_id(m: Model, p: dict) -> str | None:
    """The trace ID an element carries: its short name, or a stub's NeedRef needId."""
    nr = m.trace_meta(p, "XdTrace::NeedRef").get("needId")
    if nr:
        return str(nr)
    sid = p.get("declaredShortName") or p.get("shortName")
    return sid if sid and idmod.valid_id(sid) else None


def ids_for_end(m: Model, p: dict | None) -> list[str]:
    """IDs an end of a trace relation stands for: its own ID, else its definitions' IDs (D128)."""
    if not p:
        return []
    own = element_id(m, p)
    if own:
        return [own]
    out = []
    for t in m.types_of(p):
        tid = element_id(m, t)
        if tid:
            out.append(tid)
    # a feature chain (e.g. `satisfy x by a.b`): the last feature of the chain
    if not out:
        last = [m.get(c) for c in (p.get("chainingFeature") or [])]
        if last and last[-1]:
            out = ids_for_end(m, last[-1])
    return sorted(set(out))


def to_needs(m: Model, project: str = "model", source_of: dict[str, str] | None = None) -> tuple[dict, list[str]]:
    """Model -> needs.json (sphinx-needs import format) and a list of findings (errors).

    * Every non-library element whose short name is an ID of a model kind (SYS-EL, SYS-IF,
      SYS-UC, SYS-CFG, SYS-FEAT) becomes a need (D129: give an element an ID when its first
      trace link appears).
    * `satisfy <req> by <x>`        -> x satisfies req
    * `dependency from S to T`       -> S <link> T, link by kinds (LINK_BY_KINDS)
    * `allocate T to S`              -> S <link> T (the concrete side holds the link, D36)
    * @XdTrace::Trace { status; layer; } on the element or an owning package (D85, D130).
    * `instances`: usages typed by a definition need (D128).
    """
    source_of = source_of or {}
    needs: dict[str, dict] = {}
    findings: list[str] = []
    by_def_usages: dict[str, list[str]] = defaultdict(list)
    for u in m.user():
        if u.get("@type", "").endswith("Usage") and u.get("qualifiedName"):
            for t in m.types_of(u):
                by_def_usages[t["@id"]].append(u["qualifiedName"])

    for p in m.user():
        sid = p.get("declaredShortName")
        if not sid or m.trace_meta(p, "XdTrace::NeedRef"):
            continue
        kind = idmod.kind_of(sid)
        if kind is None:
            if re.match(rf"^(?:{'|'.join(idmod.DOMAINS)})-[A-Z]+-", sid):
                findings.append(f"{m.qn(p)}: short name {sid!r} is not a valid ID")
            continue
        if kind in idmod.RESERVED_KINDS:
            continue
        if kind not in MODEL_KINDS:
            findings.append(f"{m.qn(p)}: kind {kind} cannot be generated from the model (only {', '.join(MODEL_KINDS)})")
            continue
        if sid in needs:
            findings.append(f"{m.qn(p)}: ID {sid} is used twice (also {needs[sid]['qualified_name']})")
            continue
        status = m.inherited_meta(p, "XdTrace::Trace", "status") or "valid"
        if status not in STATUSES:
            findings.append(f"{m.qn(p)}: status {status!r} not in {STATUSES}")
        n = {
            "id": sid, "type": idmod.directive_of(kind),
            "title": p.get("declaredName") or p.get("name") or sid,
            "content": f"SysML ``{p['@type']}`` ``{p.get('qualifiedName')}``.",
            "qualified_name": p.get("qualifiedName") or "", "sysml_kind": p["@type"], "status": status,
        }
        if kind == "SYS-EL":
            layer = m.inherited_meta(p, "XdTrace::Trace", "layer")
            if layer is None:
                findings.append(f"{m.qn(p)}: {sid} has no layer (@XdTrace::Trace {{ layer = ...; }} on it or its package)")
            elif layer not in LAYERS:
                findings.append(f"{m.qn(p)}: layer {layer!r} not in {LAYERS}")
            else:
                n["layer"] = layer
        inst = sorted(set(by_def_usages.get(p["@id"], [])))
        if inst:
            n["instances"] = inst
        root = (p.get("qualifiedName") or "").split("::")[0].strip("'")
        if root in source_of:
            n["source_file"] = source_of[root]
        needs[sid] = n

    def add_link(src_ids, link, dst_ids, where):
        for s in src_ids:
            if s not in needs:
                continue
            for d in dst_ids:
                needs[s].setdefault(link, [])
                if d not in needs[s][link]:
                    needs[s][link].append(d)

    for s in m.of_type("SatisfyRequirementUsage"):
        if s.get("isLibraryElement"):
            continue
        reqs = ids_for_end(m, m.get(s.get("satisfiedRequirement")))
        by = ids_for_end(m, m.get(s.get("satisfyingFeature")))
        add_link(by, "satisfies", reqs, m.qn(s))

    def relate(src_el, dst_el, where):
        src_ids, dst_ids = ids_for_end(m, src_el), ids_for_end(m, dst_el)
        for s in src_ids:
            for d in dst_ids:
                link = LINK_BY_KINDS.get((idmod.kind_of(s), idmod.kind_of(d)))
                if link is None:
                    if s in needs:
                        findings.append(f"{where}: no trace link from {idmod.kind_of(s)} to {idmod.kind_of(d)} ({s} -> {d})")
                    continue
                add_link([s], link, [d], where)

    for dep in m.of_type("Dependency"):
        if dep.get("isLibraryElement"):
            continue
        if any(m.meta_name(x).startswith("PLEML::") for x in m.metadata(dep)) or dep.get("ownedAnnotation"):
            continue  # PLEML feature bindings are variant data, not trace links
        for c in dep.get("client", []) or []:
            for sup in dep.get("supplier", []) or []:
                relate(m.get(c), m.get(sup), "dependency")
    for a in m.of_type("AllocationUsage"):
        if a.get("isLibraryElement"):
            continue
        srcs = [m.get(x) for x in (a.get("source") or [])]
        tgts = [m.get(x) for x in (a.get("target") or [])]
        for s in srcs:
            for t in tgts:
                relate(t, s, f"allocation {m.qn(s)} -> {m.qn(t)}")  # target realizes source

    # across the repo boundary: `D :> S` with S an upstream (library) element with an ID (XD-ADR-0132).
    # Pairs without a link type are CK-E4 findings (conformance()), not CK-D2 ones.
    for p, sid, sup, tid in specializations(m):
        link = LINK_BY_KINDS.get((idmod.kind_of(sid), idmod.kind_of(tid)))
        if link:
            add_link([sid], link, [tid], m.qn(p))
    # a port need is part of the domain defs that own a port typed by it (XD-ADR-0133)
    for p in m.user():
        oid = element_id(m, p)
        if not oid or oid not in needs or p.get("@type") not in ("PartDefinition", "PortDefinition"):
            continue
        for f in owned_ports(m, p):
            for t in m.types_of(f):
                tid = element_id(m, t)
                if tid in needs and idmod.kind_of(oid) in PART_OF_KINDS.get(idmod.kind_of(tid), ()):
                    add_link([tid], "part_of", [oid], m.qn(f))

    for n in needs.values():
        for k in LINK_KEYS:
            if k in n:
                n[k] = sorted(n[k])
    doc = needs_doc(needs, project)
    return doc, findings


def owned_ports(m: Model, p: dict):
    """Ports declared in p (``port x : T;``, ``port :>> x : T;``)."""
    for kind in ("FeatureMembership", "OwningMembership"):
        for r in m.rels(p, kind):
            for x in r.get("ownedRelatedElement", []) or []:
                f = m.get(x)
                if f and f.get("@type") == "PortUsage":
                    yield f


def specializations(m: Model):
    """(def, its ID, upstream super, the super's ID) for every own definition with an ID that
    specializes an upstream element with an ID (a library stub in the compact JSON)."""
    for p in m.user():
        sid = p.get("declaredShortName")
        if not sid or not idmod.valid_id(sid) or not p.get("@type", "").endswith("Definition"):
            continue
        for sup in m.supers(p):
            tid = element_id(m, sup)
            if sup.get("isLibraryElement") and tid:
                yield p, sid, sup, tid


# ------------------------------------------------------------------ conformance (CK-E4, XD-ADR-0132)
class Joined:
    """A domain model and its upstream models as one: a stub ``lib:<qn>`` of the domain JSON
    resolves to the full upstream element of that qualified name (the stubs keep no features
    and no types, model spike §2)."""

    def __init__(self, domain: Model, upstream: list[Model]):
        self.d = domain
        self.up: dict[str, tuple[Model, dict]] = {}
        for um in upstream:
            for p in um.user():
                q = p.get("qualifiedName")
                if q and q not in self.up:
                    self.up[q] = (um, p)

    def upstream(self, p: dict | None) -> bool:
        return bool(p) and p.get("qualifiedName") in self.up and \
            (p.get("isLibraryElement") or p is self.up[p["qualifiedName"]][1])

    def full(self, p: dict | None) -> tuple[Model, dict | None]:
        """(the model that holds p's full payload, that payload)."""
        if p and p.get("isLibraryElement") and p.get("qualifiedName") in self.up:
            return self.up[p["qualifiedName"]]
        if p and p.get("qualifiedName") in self.up and p is self.up[p["qualifiedName"]][1]:
            return self.up[p["qualifiedName"]]
        return self.d, p

    def by_qn(self, q: str) -> dict | None:
        if q in self.up:
            return self.up[q][1]
        return next((p for p in self.d.user() if p.get("qualifiedName") == q), None)

    def supers(self, p: dict) -> list[dict]:
        m, f = self.full(p)
        return [self.full(s)[1] or s for s in m.supers(f)] if f else []

    def all_supers(self, p: dict) -> list[dict]:
        """All superclassifiers, breadth-first (most specific first)."""
        seen, queue, out = {p.get("qualifiedName")}, list(self.supers(p)), []
        while queue:
            s = queue.pop(0)
            if s.get("qualifiedName") not in seen:
                seen.add(s.get("qualifiedName"))
                out.append(s)
                queue += self.supers(s)
        return out

    def specializes(self, t: dict, general: dict) -> bool:
        g = general.get("qualifiedName")
        return t.get("qualifiedName") == g or any(s.get("qualifiedName") == g for s in self.all_supers(t))

    def ports(self, p: dict) -> list[dict]:
        m, f = self.full(p)
        return list(owned_ports(m, f)) if f else []

    def redefined(self, f: dict) -> list[str]:
        m, g = self.full(f)
        out = []
        for r in m.rels(g, "Redefinition"):
            t = m.get(r.get("redefinedFeature"))
            if t and t.get("qualifiedName"):
                out.append(t["qualifiedName"])
        return out

    def type_of(self, f: dict) -> dict | None:
        m, g = self.full(f)
        t = next(iter(m.types_of(g)), None)
        return self.full(t)[1] if t else None


def conformance(domain: Model, upstream: list[Model]) -> list[str]:
    """CK-E4 (XD-ADR-0132). For every own part or port def that specializes an upstream def:

    * every port it inherits from an upstream def is redefined somewhere in the chain between
      the two, and the most specific redefinition's def specializes the inherited port's def
      (inside port defs the same holds for the signal ports);
    * a port name inherited from more than one upstream port is redefined by one port that
      redefines all of them;
    * a specialization between two IDs has a link type (LINK_BY_KINDS);
    * a def without an ID of its own that specializes an upstream element is a finding, except
      below the port level (a port def used only inside port defs)."""
    j = Joined(domain, upstream)
    findings: list[str] = []
    used_in_part = set()
    for p in domain.user():
        if p.get("@type") == "PartDefinition":
            for f in owned_ports(domain, p):
                used_in_part.update(t.get("qualifiedName") for t in domain.types_of(f))
    defs = [p for p in domain.user() if p.get("@type") in ("PartDefinition", "PortDefinition")]
    for d in sorted(defs, key=lambda p: p.get("qualifiedName") or ""):
        dq, did = d.get("qualifiedName") or d["@id"], element_id(domain, d)
        chain = [d] + j.all_supers(d)
        if not any(j.upstream(s) for s in chain[1:]):
            continue
        for s in (s for s in domain.supers(d) if j.upstream(s)):
            sid = element_id(domain, s)
            if did and sid:
                pair = (idmod.kind_of(did), idmod.kind_of(sid))
                if pair not in LINK_BY_KINDS:
                    findings.append(f"{dq}: {did} specializes {sid}, but there is no trace link from {pair[0]} to {pair[1]}")
            elif sid and not (d.get("@type") == "PortDefinition" and dq not in used_in_part):
                findings.append(f"{dq}: specializes {sid} ({s.get('qualifiedName')}) but has no ID of its own")
        ports = [(o, f) for o in chain for f in j.ports(o)]

        def closure(f, seen=None):
            seen = seen if seen is not None else set()
            for q in j.redefined(f):
                if q not in seen:
                    seen.add(q)
                    g = j.by_qn(q)
                    if g:
                        closure(g, seen)
            return seen

        closures = [(f, closure(f)) for _, f in ports]
        names: dict[str, list[tuple[str, str | None]]] = defaultdict(list)
        for o, p in ports:
            if not j.upstream(o):
                continue
            q = p.get("qualifiedName")
            where = f"{dq}: port {p.get('name')} (from {o.get('qualifiedName')})"
            r = next((f for f, c in closures if q in c), None)
            names[p.get("name")].append((q, r and r.get("qualifiedName")))
            if r is None:
                findings.append(f"{where} is not redefined")
                continue
            want, got = j.type_of(p), j.type_of(r)
            if want and got and not j.specializes(got, want):
                findings.append(f"{where} is redefined by {r.get('qualifiedName')} with {got.get('qualifiedName')}, "
                                f"which does not specialize {want.get('qualifiedName')}")
        for n, qs in sorted(names.items()):
            if len(qs) > 1 and (None in [r for _, r in qs] or len({r for _, r in qs}) != 1):
                findings.append(f"{dq}: inherits port name {n!r} more than once ({', '.join(q for q, _ in qs)}); "
                                f"redefine all of them in one port (port :>> A::{n}, B::{n} : X;)")
    return findings


def needs_doc(needs: dict[str, dict], project: str) -> dict:
    """sphinx-needs import format (what `needimport` reads)."""
    return {"created": "", "current_version": "", "project": project,
            "versions": {"": {"needs": dict(sorted(needs.items()))}}}


def source_map(files: list[Path], root: Path) -> dict[str, str]:
    """top-level package name -> file (relative to `root`), for `source_file`."""
    out = {}
    for f in files:
        for name in top_packages([f]):
            try:
                out[name] = str(Path(f).resolve().relative_to(root.resolve()))
            except ValueError:
                out[name] = str(f)
    return out
