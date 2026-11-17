"""Variants across levels (XD-ADR-0136, task 5.16). Check CK-B8.

A board or assembly variant is a def in the domain model that specializes the board or assembly
def and ``XdDomain::DomainVariant``; ``variantName`` is its name in KiCad (``.kicad_pro``
``schematic.variants``) or FreeCAD (a row of the configuration table). A dependency from the
variant names the configurations (``SYS-CFG``) and the system usages it serves::

    part def JointBoardAlt :> JointBoard, DomainVariant { :>> variantName = "alt"; }
    dependency from JointBoardAlt to MyConfigs::proto, MyProduct::Arm::joint1;

From these, ``table()`` computes "configuration -> variant per usage" (nobody writes it), and
``check()`` compares it with the published system model (the upstream ``model.json``):

* every pair (configuration, usage) of a board or assembly that has variants gets exactly one
  variant. The pairs are built per system def the board realizes: the usages of that def times
  the configurations that configure it (all configurations if none does, as in ``configs``), and
  the union over the defs;
* a variant serves only such pairs, and every dependency names both kinds;
* at most two variants per board or assembly (iteration 1); every variant has a unique name;
* every variant (also one that serves no pair yet) exists in the board's KiCad project or the
  assembly's FreeCAD documents;
* Zephyr board variants (``board.yml`` under the board roots in ``variants.zephyr``) map to
  board variants by name; the Zephyr board name is the KiCad project name, lower case, with ``-``
  as ``_``; a nested variant counts by its last part; a Zephyr board without such a project is
  ignored.

A variant that serves no pair is not reported as unused (iteration 2). Plain Python, no CAD tools.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from curatrix import cad
from curatrix import ids as idmod
from curatrix import model as modelmod

VARIANT_DEF = "XdDomain::DomainVariant"
OWNER_KINDS = ("EE-PCBA", "ME-ASM")
MAX_VARIANTS = 2


@dataclass
class Variant:
    qn: str
    name: str | None
    owner: str                      # ID of the board or assembly def
    owner_qn: str
    configs: list[str] = field(default_factory=list)       # SYS-CFG IDs
    usages: list[str] = field(default_factory=list)        # qualified names of system usages
    pairs: set = field(default_factory=set)                # (SYS-CFG, usage): per dependency
    other: list[str] = field(default_factory=list)         # named elements that are neither
    no_usage: bool = False                                 # a dependency with configurations only
    no_config: bool = False                                # a dependency with usages only


@dataclass
class Row:
    config: str
    usage: str
    owner: str
    variants: list[str]


def _variant_name(m: modelmod.Model, p: dict) -> str | None:
    for _, f in m.owned(p):
        if f.get("name") == "variantName":
            for _, v in m.owned(f):
                if v.get("@type", "").startswith("Literal") and v.get("value") not in (None, ""):
                    return str(v["value"])
    return None


def variants(m: modelmod.Model) -> tuple[list[Variant], list[str]]:
    """The variants of the domain model and findings (a variant without a board or assembly def)."""
    out, findings = [], []
    by_qn: dict[str, Variant] = {}
    for p in m.user():
        if not p.get("@type", "").endswith("Definition"):
            continue
        sups = m.supers(p)
        if not any(s.get("qualifiedName") == VARIANT_DEF for s in sups):
            continue
        owners = [s for s in sups if idmod.kind_of(modelmod.element_id(m, s) or "") in OWNER_KINDS]
        if len(owners) != 1:
            findings.append(f"{m.qn(p)}: a variant specializes exactly one board or assembly def "
                            f"({' or '.join(OWNER_KINDS)}), not {len(owners)}")
            continue
        v = Variant(m.qn(p), _variant_name(m, p), modelmod.element_id(m, owners[0]), m.qn(owners[0]))
        if not v.name:
            findings.append(f"{v.qn}: no variantName")
        out.append(v)
        by_qn[v.qn] = v
    for dep in m.of_type("Dependency"):
        if dep.get("isLibraryElement"):
            continue
        for c in dep.get("client", []) or []:
            v = by_qn.get(m.qn(m.get(c)))
            if not v:
                continue
            cfgs, uses = [], []
            for s in dep.get("supplier", []) or []:
                t = m.get(s)
                tid = modelmod.element_id(m, t) if t else None
                if tid and idmod.kind_of(tid) == "SYS-CFG":
                    cfgs.append(tid)
                elif t and t.get("@type", "").endswith("Usage"):
                    uses.append(m.qn(t))
                else:
                    v.other.append(m.qn(t) or str(s))
            v.configs += [c for c in cfgs if c not in v.configs]
            v.usages += [u for u in uses if u not in v.usages]
            v.pairs |= {(c, u) for c in cfgs for u in uses}
            v.no_usage |= bool(cfgs and not uses)
            v.no_config |= bool(uses and not cfgs)
    return sorted(out, key=lambda v: (v.owner, v.qn)), findings


def _required(m: modelmod.Model, upstream: list[modelmod.Model]) -> tuple[dict[str, set], set[str]]:
    """(board or assembly ID -> the (configuration, usage) pairs it must serve, all configurations
    of the upstream model). Pairs per realized system def, then the union (not a cross product
    over the defs)."""
    configures: dict[str, set[str]] = {}
    all_cfgs: set[str] = set()
    usages_of: dict[str, set[str]] = {}
    for um in upstream:
        for nid, n in modelmod.needs_doc_needs(modelmod.to_needs(um)[0]).items():
            if idmod.kind_of(nid) == "SYS-CFG":
                all_cfgs.add(nid)
                for el in n.get("configures", []):
                    configures.setdefault(el, set()).add(nid)
        for u in um.user():
            if u.get("@type", "").endswith("Usage") and u.get("qualifiedName"):
                for t in um.types_of(u):
                    tid = modelmod.element_id(um, t)
                    if tid:
                        usages_of.setdefault(tid, set()).add(u["qualifiedName"])
    out: dict[str, set] = {}
    for _p, sid, _sup, tid in modelmod.specializations(m):
        if idmod.kind_of(sid) not in OWNER_KINDS:
            continue
        out.setdefault(sid, set()).update((c, u) for c in (configures.get(tid) or all_cfgs)
                                          for u in usages_of.get(tid, set()))
    return out, all_cfgs


def table(vs: list[Variant], required: dict[str, set]) -> list[Row]:
    """The computed table "configuration -> variant per usage", for every board or assembly that
    has variants: one row per (configuration, usage), with the variants that serve it."""
    rows = []
    for owner in sorted({v.owner for v in vs}):
        mine = [v for v in vs if v.owner == owner]
        for c, u in sorted(required.get(owner, set())):
            rows.append(Row(c, u, owner, sorted(v.name or v.qn for v in mine if (c, u) in v.pairs)))
    return rows


def table_markdown(rows: list[Row]) -> str:
    if not rows:
        return "No board or assembly has variants.\n"
    lines = ["| Configuration | Usage | Board / assembly | Variant |", "|---|---|---|---|"]
    for r in rows:
        lines.append(f"| {r.config} | {r.usage} | {r.owner} | {', '.join(r.variants) or '(none)'} |")
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------ CAD side, plain Python
def kicad_variants(pro: Path) -> list[str]:
    """Variant names of a KiCad project (``schematic.variants``, KiCad 10)."""
    d = json.loads(pro.read_text(encoding="utf-8"))
    return [v.get("name") for v in ((d.get("schematic") or {}).get("variants") or []) if v.get("name")]


def kicad_projects(roots: list[Path]) -> dict[str, list[Path]]:
    """TraceID (the EE-PCBA a project names) -> its .kicad_pro files, from root schematics."""
    out: dict[str, Path] = {}
    for sch in roots:
        pro = sch.with_suffix(".kicad_pro")
        if pro.is_file():
            tid = (json.loads(pro.read_text(encoding="utf-8")).get("text_variables") or {}).get("TraceID")
            if tid:
                out.setdefault(tid, []).append(pro)
    return out


_CELL_A = re.compile(r"^A(\d+)$")


def freecad_variants(fcstd: Path) -> list[str]:
    """Variant names of the configuration tables in a FreeCAD document: column A from row 2 of
    every spreadsheet with a ``Variant`` property (FreeCAD spike §3)."""
    root = cad.freecad_document(fcstd)
    types = {o.get("name"): o.get("type") for o in root.iter("Object") if o.get("type")}
    data = root.find("ObjectData")
    names = []
    for o in (data if data is not None else []):
        if types.get(o.get("name")) != "Spreadsheet::Sheet":
            continue
        if not any(p.get("name") == "Variant" for p in o.iter("Property")):
            continue
        rows = []
        for c in o.iter("Cell"):
            mm = _CELL_A.match(c.get("address") or "")
            if mm and int(mm.group(1)) >= 2 and (c.get("content") or "").strip():
                rows.append((int(mm.group(1)), c.get("content").strip()))
        names += [n for _, n in sorted(rows)]
    return names


def freecad_documents(files: list[Path]) -> dict[str, list[Path]]:
    """TraceID of an object -> the documents of its folder (top document and skeleton)."""
    out: dict[str, list[Path]] = {}
    for f in files:
        try:
            sem = cad.freecad_trace(f, str(f))
        except Exception:  # noqa: BLE001 - a broken document is CK-D4's finding
            continue
        for o in sem["objects"].values():
            tid = (o.get("trace") or {}).get("TraceID")
            if tid:
                out.setdefault(tid, sorted(set(f.parent.glob("*.FCStd"))))
    return out


def zephyr_boards(roots: list[Path]) -> dict[str, list[str]]:
    """Zephyr board name -> its variant names (HWMv2 ``board.yml``: ``board`` or ``boards``, variants
    per SoC, nested variants as ``outer/inner``)."""
    out: dict[str, list[str]] = {}

    def names(vs, prefix=""):
        for v in vs or []:
            n = prefix + str(v.get("name"))
            yield n
            yield from names(v.get("variants"), n + "/")

    for root in roots:
        for f in sorted(root.glob("**/board.yml")):
            d = yaml.safe_load(f.read_text(encoding="utf-8")) or {}
            for b in ([d["board"]] if "board" in d else []) + list(d.get("boards") or []):
                vs = []
                for soc in b.get("socs") or []:
                    vs += list(names(soc.get("variants")))
                out[str(b.get("name"))] = vs
    return out


# ------------------------------------------------------------------ the check
def check(m: modelmod.Model, upstream: list[modelmod.Model], kicad_roots: list[Path] = (),
          freecad_files: list[Path] = (), zephyr_roots: list[Path] = ()) -> tuple[list[str], list[Row]]:
    """CK-B8 findings and the computed table."""
    vs, findings = variants(m)
    required, all_cfgs = _required(m, upstream)
    rows = table(vs, required)
    projects = kicad_projects(list(kicad_roots))
    fc_docs = freecad_documents(list(freecad_files)) if freecad_files else {}
    zboards = zephyr_boards(list(zephyr_roots))
    if vs and not all_cfgs:
        findings.append("the upstream model has no configuration (SYS-CFG), so no variant can be checked "
                        "against one; give the system model its configurations")

    for owner in sorted({v.owner for v in vs}):
        mine = [v for v in vs if v.owner == owner]
        oqn = mine[0].owner_qn
        if len(mine) > MAX_VARIANTS:
            findings.append(f"{oqn}: {len(mine)} variants; at most {MAX_VARIANTS} per board or assembly in iteration 1")
        seen: dict[str, str] = {}
        for v in mine:
            if v.name and v.name in seen:
                findings.append(f"{v.qn}: variant name {v.name!r} is also used by {seen[v.name]}")
            seen.setdefault(v.name or "", v.qn)
        pairs = required.get(owner, set())
        cfgs, uses = {c for c, _ in pairs}, {u for _, u in pairs}
        pros = projects.get(owner, [])
        if len(pros) > 1:
            findings.append(f"{oqn}: more than one KiCad project names {owner}: {', '.join(p.name for p in pros)}")
        for v in mine:
            for o in v.other:
                findings.append(f"{v.qn}: names {o}, which is neither a configuration (SYS-CFG) nor a usage")
            if v.no_usage:
                findings.append(f"{v.qn}: a dependency names configurations but no usage of the system model")
            if v.no_config:
                findings.append(f"{v.qn}: a dependency names usages but no configuration (SYS-CFG)")
            for c in v.configs:
                if c not in cfgs:
                    findings.append(f"{v.qn}: configuration {c} does not configure what {owner} realizes")
            for u in v.usages:
                if u not in uses:
                    findings.append(f"{v.qn}: {u} is not a usage of a system def that {owner} realizes")
            for c, u in sorted(v.pairs):
                if c in cfgs and u in uses and (c, u) not in pairs:
                    findings.append(f"{v.qn}: serves {u} in {c}, but that configuration does not configure "
                                    f"the system def of that usage")
            # every named variant exists in CAD, also one that serves no pair yet
            if not v.name:
                continue
            kind = idmod.kind_of(owner)
            if kind == "EE-PCBA":
                if not pros:
                    findings.append(f"{v.qn}: no KiCad project names {owner} (TraceID), so variant {v.name!r} is not there")
                else:
                    have = kicad_variants(pros[0])
                    if v.name not in have:
                        findings.append(f"{v.qn}: variant {v.name!r} is not in {pros[0].name} schematic.variants "
                                        f"({', '.join(have) or 'none'})")
            elif kind == "ME-ASM":
                docs = fc_docs.get(owner)
                if not docs:
                    findings.append(f"{v.qn}: no FreeCAD document names {owner} (TraceID), so variant {v.name!r} is not there")
                else:
                    have = [n for d in docs for n in freecad_variants(d)]
                    if v.name not in have:
                        findings.append(f"{v.qn}: variant {v.name!r} is not a row of a configuration table in "
                                        f"{', '.join(d.name for d in docs)} ({', '.join(have) or 'none'})")
        for r in rows:
            if r.owner == owner and len(r.variants) != 1:
                what = "no variant" if not r.variants else f"{len(r.variants)} variants ({', '.join(r.variants)})"
                findings.append(f"{oqn}: {what} for usage {r.usage} in configuration {r.config}; exactly one expected")
        # Zephyr board variants map to board variants by name
        if pros:
            zname = pros[0].stem.replace("-", "_").lower()
            names = {v.name for v in mine if v.name}
            for zv in zboards.get(zname, []):
                if zv.split("/")[-1] not in names:
                    findings.append(f"Zephyr board {zname}: variant {zv!r} is no variant of {oqn} "
                                    f"({', '.join(sorted(names))})")
    return findings, rows
