"""The ``asm-<name>`` assembly document (task 5.27; ME-4, ME-8, XD-ADR-0129): what its directives
(``xdmod/sphinx/xdmod_sphinx/asm.py``) read, in plain Python, and the mass and center of gravity
that ``curatrix cam`` computes from the ``FreeCADCmd`` result.

Plain Python on the committed ``.FCStd`` files (``Document.xml``, ``cad.freecad_trace``) and the
committed ``model.json``, so CI shows it:

* ``tree``: the assembly structure from the top document's assembly object (the object with the
  ``ME-ASM`` ``TraceID``): each ``App::Link`` in its group is a node; a link to an object with an
  ``ME-ASM`` ``TraceID`` is a sub-assembly and is walked into; links to the skeleton are left out.
  A link may point outside the repo (a board model of the board library): its file is read when it
  is there, else the node is ``unresolved``.
* ``indented_bom``: one row per distinct child of each assembly, with its quantity per parent and per
  variant (the links' own ``Configs``, as ``curatrix cam`` and the ME checks read them; XD-ADR-0137).
  A standard fastener (an object with a ``Standard`` property) is named by its standard designation
  (``ISO 4762 M3x10, A2``); a board (``EE-PCBA``) or harness (``EE-HAR``) is one line with its
  version and its ``pcba-<name>`` / ``harnesses`` document, never its components (owner, ME-8).
* ``bom_field_findings`` (CK-F12 for ME): a library part (``lib/``) that is not a standard fastener
  names ``Manufacturer`` and ``MPN``; an own part (``parts/``, ``assemblies/``) names its ``Material``.
* ``materials``, ``parameters``, ``interfaces``: the tables of the document.

Local only (``FreeCADCmd`` in ``curatrix cam``): ``mass`` turns the volume and center of mass of
every present part (in the frame of the top-level assembly) into masses and the center of gravity.
The mass of a part is its ``Mass`` property (``12 g``, ``0.012 kg``) if it has one, else its volume
times the density of its ``Density`` property (``1.24 g/cm^3``) or of its ``Material`` in
``data/materials.yaml``. Both properties need a unit, and a density outside 0.01..25 g/cm³ is
refused; a part without a usable value has no mass (the reason is shown) and the total is marked
incomplete.
Printed parts count as solid: the infill of the print profile is not applied (an upper bound).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

import yaml

from curatrix import cad, ids as idmod, meassemblies

MATERIALS = Path(__file__).parent / "data" / "materials.yaml"
ALL, BASE = "all", "base"                    # the variant names of mecam
KINDS = ("assembly", "printed", "part", "fastener", "bought", "board", "harness", "unresolved")


@dataclass
class Node:
    link: str                                # link name in the parent ("" for the top-level assembly)
    label: str
    id: str                                  # TraceID of the linked object
    kind: str                                # one of KINDS
    file: str                                # the target document, repo-relative (or as resolved on disk)
    object: str
    configs: list[str] = field(default_factory=list)
    values: dict = field(default_factory=dict)
    children: list["Node"] = field(default_factory=list)

    @property
    def designation(self) -> str:
        v = self.values
        if self.kind == "fastener":
            return str(v.get("Standard"))
        if self.kind == "board":
            name = v.get("Board") or self.label
            return f"{name} {v.get('Version')}" if v.get("Version") else str(name)
        if self.kind == "harness":
            return f"{self.label} {v.get('Version')}" if v.get("Version") else self.label
        return self.label

    def document(self) -> str:
        """The zdocs document of a board or harness line (``pcba-<name>``; ``harnesses``, the one
        document of every cable, tiacsys/xdmod#69 finding 15)."""
        from curatrix.eeprojects import kebab
        if self.kind == "board":
            return f"pcba-{kebab(str(self.values.get('Board') or self.label))}"
        if self.kind == "harness":
            return "harnesses"
        return ""

    def walk(self, path: str = ""):
        """(link path in the top-level frame, node) of this node and every node below it."""
        here = f"{path}/{self.link}" if path and self.link else (self.link or path)
        yield here, self
        for c in self.children:
            yield from c.walk(here)


def kind_of(tid: str, values: dict, rel: str) -> str:
    k = idmod.kind_of(tid) if tid else None
    if k == "ME-ASM":
        return "assembly"
    if k == "EE-PCBA":
        return "board"
    if k == "EE-HAR":
        return "harness"
    if str(values.get("Standard") or "").strip():
        return "fastener"
    if str(values.get("PrintProfile") or "").strip():
        return "printed"
    if values.get("Manufacturer") or values.get("MPN") or rel.startswith("lib/"):
        return "bought"
    return "part"


class _Reader:
    """Documents by path: the repo's (``meassemblies.documents``) and, read on demand, others."""

    def __init__(self, cfg, docs):
        self.cfg = cfg
        self.docs = docs
        self.extra: dict[str, dict | None] = {}

    def resolve(self, src_rel: str, file: str) -> str:
        p = (self.cfg.repo / PurePosixPath(src_rel).parent / file).resolve()
        try:
            return str(p.relative_to(self.cfg.repo.resolve()))
        except ValueError:
            return str(p)

    def sem(self, rel: str) -> dict | None:
        if rel in self.docs:
            return self.docs[rel].sem
        if rel not in self.extra:
            p = Path(rel) if Path(rel).is_absolute() else self.cfg.repo / rel
            self.extra[rel] = cad.freecad_trace(p, rel) if p.is_file() else None
        return self.extra[rel]


def _asm_object(sem: dict) -> str | None:
    return next((n for n, o in sem["objects"].items()
                 if idmod.kind_of(str((o.get("trace") or {}).get("TraceID") or "")) == "ME-ASM"), None)


def _children(rd: _Reader, rel: str, sem: dict, obj: str, seen: tuple) -> list[Node]:
    out = []
    objs = sem["objects"]
    for t in ((objs.get(obj) or {}).get("links") or {}).get("Group") or []:
        if t.get("file"):
            continue
        name = t.get("object") or ""
        o = objs.get(name) or {}
        if o.get("type") not in meassemblies.LINK_TYPES:
            continue
        cfgs = cad._list(str((o.get("trace") or {}).get("Configs") or ""))
        tg = ((o.get("links") or {}).get("LinkedObject") or [{}])[0]
        trel = rd.resolve(rel, tg["file"]) if tg.get("file") else rel
        if PurePosixPath(trel).name.endswith(meassemblies.SKELETON_SUFFIX):
            continue
        tsem = rd.sem(trel)
        tobj = (tsem or {}).get("objects", {}).get(tg.get("object") or "")
        if tobj is None:
            out.append(Node(name, o.get("label") or name, "", "unresolved", trel, tg.get("object") or "", cfgs))
            continue
        tid = str((tobj.get("trace") or {}).get("TraceID") or "").strip()
        vals = dict(tobj.get("values") or {})
        n = Node(name, tobj.get("label") or tg.get("object") or name, tid, kind_of(tid, vals, trel), trel,
                 tg.get("object") or "", cfgs, vals)
        if n.kind == "assembly" and (trel, n.object) not in seen:
            n.children = _children(rd, trel, tsem, n.object, seen + ((trel, n.object),))
        out.append(n)
    return out


def tree(cfg, folder: Path, docs: dict | None = None) -> Node | None:
    """The structure of the top-level assembly in ``folder``, or None without its top document."""
    docs = meassemblies.documents(cfg) if docs is None else docs
    rel = str((folder / f"{folder.name}.FCStd").resolve().relative_to(cfg.repo.resolve()))
    if rel not in docs:
        return None
    sem = docs[rel].sem
    obj = _asm_object(sem)
    if obj is None:
        return None
    o = sem["objects"][obj]
    root = Node("", o.get("label") or folder.name, str(o["trace"]["TraceID"]), "assembly", rel, obj)
    root.children = _children(_Reader(cfg, docs), rel, sem, obj, ((rel, obj),))
    return root


def sub_assemblies(root: Node) -> list[tuple[str, Node]]:
    """(link path, node) of every sub-assembly, each distinct document once (its first use)."""
    out, seen = [], set()
    for path, n in root.walk():
        if n is not root and n.kind == "assembly" and (n.file, n.object) not in seen:
            seen.add((n.file, n.object))
            out.append((path, n))
    return out


def find(root: Node, asm_id: str) -> tuple[str, Node] | None:
    return next(((p, n) for p, n in root.walk() if n.kind == "assembly" and n.id == asm_id), None)


def uses(root: Node, node: Node) -> list[str]:
    """Link paths of every use of the document of ``node`` in the tree."""
    return [p for p, n in root.walk() if n is not root and (n.file, n.object) == (node.file, node.object)]


# ------------------------------------------------------------------ variants and the indented BOM
def variants(root: Node) -> list[str]:
    """As ``mecam.variants``: every configuration a link names, and ``base``; else ``all``."""
    cs = {c for _, n in root.walk() for c in n.configs}
    return sorted(cs) + [BASE] if cs else [ALL]


def present(n: Node, variant: str) -> bool:
    if variant == BASE:
        return not n.configs
    return variant == ALL or not n.configs or variant in n.configs


def indented_bom(root: Node, vs: list[str] | None = None) -> list[dict]:
    """One row per distinct child (same document and object) of each assembly, along the structure:
    ``pos`` (``1``, ``1.2``), ``level``, ``qty`` {variant: number per parent}, and the part fields."""
    vs = vs or variants(root)
    rows: list[dict] = []

    def level(node: Node, prefix: str, depth: int):
        groups: dict[tuple, list[Node]] = {}
        for c in node.children:
            groups.setdefault((c.file, c.object, c.kind), []).append(c)
        order = sorted(groups.values(), key=lambda g: (g[0].kind != "assembly", KINDS.index(g[0].kind),
                                                       g[0].id, g[0].designation))
        for i, g in enumerate(order, 1):
            n = g[0]
            pos = f"{prefix}{i}"
            v = n.values
            rows.append({"pos": pos, "level": depth, "id": n.id, "designation": n.designation, "kind": n.kind,
                         "qty": {x: sum(present(c, x) for c in g) for x in vs},
                         "material": str(v.get("Material") or ""), "print_profile": str(v.get("PrintProfile") or ""),
                         "manufacturer": str(v.get("Manufacturer") or ""), "mpn": str(v.get("MPN") or ""),
                         "file": n.file, "document": n.document(), "links": [c.link for c in g]})
            if n.kind == "assembly":
                level(n, pos + ".", depth + 1)
    level(root, "", 0)
    return rows


def bom_field_findings(root: Node) -> list[str]:
    """CK-F12 for an ME repo (XD-RULE-0058, owner ME-8): a library part that is not a standard
    fastener names Manufacturer and MPN; an own part names its Material. Boards and harnesses are
    one line each; their parts are in the EE BOM."""
    out, seen = [], set()
    for _, n in root.walk():
        if n is root or (n.file, n.object) in seen:
            continue
        seen.add((n.file, n.object))
        where = f"{n.file}#{n.object}"
        if n.kind == "bought":
            miss = [f for f in ("Manufacturer", "MPN") if not str(n.values.get(f) or "").strip()]
            if miss:
                out.append(f"{where} ({n.label}): a bought part without {' and '.join(miss)}; add the "
                           f"propert{'ies' if len(miss) > 1 else 'y'}, or a Standard property with the standard "
                           f"designation if it is a standard fastener (ISO 4762 M3x10, A2)")
        elif n.kind in ("part", "printed") and not str(n.values.get("Material") or "").strip():
            out.append(f"{where} ({n.label}): an own part without a Material property (the materials table and "
                       f"the mass need it)")
        elif n.kind == "unresolved":
            out.append(f"{where}: the link {n.link} points to an object that is not there; the BOM cannot name it")
    return out


# ------------------------------------------------------------------ materials
def densities() -> dict[str, float]:
    """Material name (lower case) -> density in g/cm³."""
    d = yaml.safe_load(MATERIALS.read_text(encoding="utf-8")) or {}
    return {str(k).lower(): float(v) for k, v in (d.get("densities") or {}).items()}


def materials(root: Node, dens: dict[str, float] | None = None) -> list[dict]:
    """One row per material of the parts below ``root`` (each distinct part once)."""
    dens = densities() if dens is None else dens
    rows: dict[str, dict] = {}
    seen = set()
    for _, n in root.walk():
        if n.kind in ("assembly", "board", "harness", "unresolved") or (n.file, n.object) in seen:
            continue
        seen.add((n.file, n.object))
        mat = str(n.values.get("Material") or "")
        r = rows.setdefault(mat, {"material": mat, "parts": [], "print_profiles": set(),
                                  "density": dens.get(mat.lower())})
        r["parts"].append(n.designation)
        if n.values.get("PrintProfile"):
            r["print_profiles"].add(str(n.values["PrintProfile"]))
    return [{**r, "print_profiles": sorted(r["print_profiles"])} for _, r in sorted(rows.items(), key=lambda x: (not x[0], x[0]))]


# ------------------------------------------------------------------ mass and center of gravity (local)
_QTY = re.compile(r"^\s*([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)\s*([^\d\s].*)?$")
MASS_UNITS = {"g": 1.0, "kg": 1000.0, "mg": 0.001}          # a unit is required
DENSITY_RANGE = (0.01, 25.0)                     # g/cm³: plausible solids (aerogel .. osmium)
DENSITY_UNITS = {"g/cm^3": 1.0, "g/cm³": 1.0, "g/cm3": 1.0, "kg/m^3": 0.001, "kg/m³": 0.001, "kg/m3": 0.001,
                 "kg/mm^3": 1e6}


def quantity(text, units: dict[str, float]) -> float | None:
    m = _QTY.match(str(text or ""))
    if not m or (m.group(2) or "").strip() not in units:
        return None
    return float(m.group(1)) * units[(m.group(2) or "").strip()]


def mass(rows: list[dict], dens: dict[str, float] | None = None) -> dict:
    """Mass and center of gravity from the ``cam-asm.py`` rows (one per present part instance, with
    ``volume`` in mm³ and ``com`` [x, y, z] in mm in the frame of the top-level assembly)."""
    dens = densities() if dens is None else dens
    parts, missing = [], []
    total, mx, my, mz = 0.0, 0.0, 0.0, 0.0
    for r in rows:
        g, src, problem = None, "", ""
        if r.get("Mass"):
            g, src = quantity(r["Mass"], MASS_UNITS), "Mass property"
            if g is None:
                problem = f"Mass {r['Mass']!r} needs a unit (g, kg, mg)"
        elif r.get("Density"):
            d, src = quantity(r["Density"], DENSITY_UNITS), "Density property"
            if d is None:
                problem = f"Density {r['Density']!r} needs a unit (g/cm^3, kg/m^3)"
            elif not DENSITY_RANGE[0] <= d <= DENSITY_RANGE[1]:
                problem, d = f"Density {r['Density']!r} is {d:g} g/cm³, outside {DENSITY_RANGE[0]:g}..{DENSITY_RANGE[1]:g}", None
            vol = r.get("volume")
            g = vol / 1000.0 * d if d is not None and vol is not None else None
        else:
            d = dens.get(str(r.get("Material") or "").lower())
            src = f"material {r.get('Material')}"
            if d is None:
                problem = f"no density for Material {r.get('Material')!r} (data/materials.yaml)" if r.get("Material") \
                    else "no Material, Mass or Density"
            vol = r.get("volume")
            g = vol / 1000.0 * d if d is not None and vol is not None else None
        name = r.get("label") or r.get("object") or ""
        com = r.get("com")
        p = {"path": r.get("path", ""), "id": r.get("TraceID", ""), "name": name, "material": r.get("Material", ""),
             "volume_mm3": r.get("volume"), "mass_g": None if g is None else round(g, 4),
             "source": src if g is not None else problem, "com_mm": com}
        parts.append(p)
        if g is None or com is None:
            missing.append(p["path"] or name)
            continue
        total += g
        mx, my, mz = mx + g * com[0], my + g * com[1], mz + g * com[2]
    cog = [round(mx / total, 3), round(my / total, 3), round(mz / total, 3)] if total > 0 else None
    return {"total_g": round(total, 4), "cog_mm": cog, "complete": not missing, "missing": missing, "parts": parts}


def sub_mass(m: dict, prefix: str) -> dict:
    """The mass of one use of a sub-assembly: the parts whose link path starts with ``prefix/``."""
    rows = [p for p in m.get("parts") or [] if p["path"].startswith(prefix + "/")]
    total = sum(p["mass_g"] for p in rows if p["mass_g"] is not None and p["com_mm"] is not None)
    cog = None
    if total > 0:
        cog = [round(sum(p["mass_g"] * p["com_mm"][i] for p in rows if p["mass_g"] is not None and p["com_mm"])
                     / total, 3) for i in range(3)]
    missing = [p["path"] for p in rows if p["mass_g"] is None or p["com_mm"] is None]
    return {"total_g": round(total, 4), "cog_mm": cog, "complete": not missing, "missing": missing, "parts": rows}


# ------------------------------------------------------------------ parameters and interfaces (model)
def parameters(m, asm: dict, sk_sem: dict | None) -> list[dict]:
    """The parameters of a top-level assembly def: model value, the value in the skeleton's Params."""
    from curatrix import meparams
    params, _ = meparams.model_params(m, asm)
    cells = ((sk_sem or {}).get("spreadsheets") or {}).get("Params") or {}
    return [{"alias": p.alias, "usage": p.usage, "attribute": p.attribute, "model": p.text,
             "params": str(cells.get(p.alias, "")), "port": p.port or "", "budget": p.budget,
             "tolerance": f"{p.tol:g} {meparams.BASE[p.kind]}".strip()} for p in params]


def interfaces(cfg, m, asm: dict, folder: Path | None, docs: dict) -> list[dict]:
    """The ports of an assembly def: port def and its ID, the SYS-IF it conforms to, placement in the
    model, the LCS that implements it (top-level assemblies) and the other attribute values."""
    from curatrix import meparams, model as modelmod
    lcs = {}
    if folder is not None:
        for rel, name, port, pl in meparams._lcs(cfg, folder, docs):
            lcs.setdefault(port, []).append((rel, name, meparams.placement_values(pl)))
    out = []
    for _, u in m.owned(asm):
        if u.get("@type") != "PortUsage" or not u.get("name"):
            continue
        t = next(iter(m.declared_types(u)), None)
        pdef = m.port_def(t)[0] if t else None
        pid = modelmod.element_id(m, pdef) if pdef else None
        conforms = sorted({modelmod.element_id(m, s) for s in (m.supers(pdef) if pdef else [])
                           if idmod.kind_of(modelmod.element_id(m, s) or "") == "SYS-IF"})
        vals, seen = {}, set()
        for a in meparams._attributes(m, u):
            if a["name"] in seen:
                continue
            seen.add(a["name"])
            v = meparams._value(m, a)
            if v is not None:
                vals[a["name"]] = f"{v[0]:.6f}".rstrip("0").rstrip(".") + (f" {meparams.BASE[v[1]]}" if meparams.BASE[v[1]] else "")
        place = {k: vals.pop(k) for k in meparams.PLACEMENT if k in vals}
        out.append({"usage": u["name"], "port_def": (pdef or {}).get("name") or "", "id": pid or "",
                    "conforms": conforms, "placement": place, "values": vals,
                    "lcs": [(rel, name) for rel, name, _ in lcs.get(pid or "", [])]})
    return out
