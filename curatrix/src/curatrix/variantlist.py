"""``curatrix variants list``: every board and assembly variant of a repo, across levels
(finding 9 of xdmod#69, owner decision Q14). Plain Python, no CAD tools.

A variant is listed when any level has it:

* the domain model: a def that specializes a board or assembly def and ``XdDomain::DomainVariant``
  (``variantName``), ``domvariants.variants``;
* KiCad: a ``.kicad_pro`` ``schematic.variants`` entry of the project whose ``TraceID`` names the
  board (with its description);
* FreeCAD: a row of a configuration table (a spreadsheet with a ``Variant`` property) in the
  documents of the assembly's folder.

For each one: the differences (a board: the parts the variant fits differently from the base
schematic, from the instances in the schematic, ``bom.differences``; where the ``.kicad_pcb``
fits a part differently in that variant (its footprint's own ``(variant .. (dnp ..))`` or
``(attr .. dnp)``), the difference says so: ``R1 DNP (board: fitted)``; an assembly: the parameters
of its configuration-table row and, where links carry ``Configs``, the links it has or lacks) and
the (configuration, usage) pairs it serves. The pairs come from the dependencies CK-B8 reads and
the table ``domvariants.table`` computes against the upstream model; a variant that serves no pair
is listed and marked. Pairs that no variant serves are listed too. Order per board or assembly:
serving variants first, then by the first configuration served, then in CAD order.
"""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from curatrix import bom, cad, domvariants
from curatrix import ids as idmod
from curatrix import model as modelmod

KINDS = {"EE-PCBA": "board", "ME-ASM": "assembly"}


@dataclass
class Listed:
    owner: str                                  # the board's EE-PCBA or the assembly's ME-ASM
    owner_def: str                              # qualified name of its def ("" without a model def)
    kind: str                                   # board | assembly
    name: str                                   # the variant name (variantName = KiCad / FreeCAD name)
    model_def: str = ""                         # the DomainVariant def ("" if the model has none)
    cad_file: str = ""                          # .kicad_pro or .FCStd that has it ("" if none)
    description: str = ""                       # KiCad variant description
    differences: list[str] = field(default_factory=list)
    configs: list[str] = field(default_factory=list)      # from the model's dependencies
    usages: list[str] = field(default_factory=list)
    serves: list[list[str]] = field(default_factory=list)  # [configuration, usage] pairs

    @property
    def serves_none(self) -> bool:
        return not self.serves


@dataclass
class Listing:
    repo: str
    variants: list[Listed] = field(default_factory=list)
    unserved: list[list[str]] = field(default_factory=list)  # [configuration, usage, owner]: no variant
    notes: list[str] = field(default_factory=list)

    def to_json(self) -> dict:
        return {"repo": self.repo,
                "variants": [{**asdict(v), "serves_none": v.serves_none} for v in self.variants],
                "unserved": self.unserved, "notes": self.notes}


# ------------------------------------------------------------------ FreeCAD
_CELL = re.compile(r"^([A-Z]+)(\d+)$")


def freecad_rows(fcstd: Path) -> dict[str, list[str]]:
    """Variant name -> ``param=value`` of its row, for every configuration table of a document
    (a spreadsheet with a ``Variant`` property: names in column A from row 2, parameter names in
    row 1 by alias or content)."""
    root = cad.freecad_document(fcstd)
    types = {o.get("name"): o.get("type") for o in root.iter("Object") if o.get("type")}
    data = root.find("ObjectData")
    out: dict[str, list[str]] = {}
    for o in (data if data is not None else []):
        if types.get(o.get("name")) != "Spreadsheet::Sheet":
            continue
        if not any(p.get("name") == "Variant" for p in o.iter("Property")):
            continue
        cells: dict[tuple[str, int], tuple[str, str]] = {}
        for c in o.iter("Cell"):
            m = _CELL.match(c.get("address") or "")
            if m:
                cells[(m.group(1), int(m.group(2)))] = ((c.get("content") or "").strip(), c.get("alias") or "")
        cols = sorted({col for col, _ in cells if col != "A"}, key=lambda s: (len(s), s))
        for (col, row), (content, _) in sorted(cells.items(), key=lambda kv: kv[0][1]):
            if col != "A" or row < 2 or not content:
                continue
            params = []
            for c in cols:
                head = cells.get((c, 1), ("", ""))
                val = cells.get((c, row), ("", ""))[0]
                if val:
                    params.append(f"{head[1] or head[0].lstrip('=') or c}={val.lstrip('=')}")
            out.setdefault(content, params)
    return out


# ------------------------------------------------------------------ KiCad board
def board_fitted(pcb: Path) -> dict[str, tuple[bool, dict[str, bool]]]:
    """Reference -> (fitted in the base board, {variant: fitted}) from the footprints of a
    ``.kicad_pcb``: ``(attr ... dnp)`` and the footprint's own ``(variant (name ..) (dnp ..))``."""
    tree = cad.sexpr(pcb.read_text(encoding="utf-8"))
    out = {}
    for fp in cad._children(tree, "footprint"):
        ref = cad._props(fp).get("Reference", "")
        if not ref or ref.startswith("#"):
            continue
        attr = cad._children(fp, "attr")
        base = not (attr and "dnp" in attr[0][1:])
        per = {v: not o["dnp"] for v, o in bom._variant_overrides(fp).items() if "dnp" in o}
        out[ref] = (base, per)
    return out


def board_mismatches(parts: list[bom.Part], board: dict, variant: str) -> dict[str, str]:
    """Reference -> ``fitted`` / ``DNP`` on the board, where the board differs from the
    schematic in ``variant`` (parts in the BOM that the board has)."""
    out = {}
    for p in bom.resolve(parts, variant):
        if not p.in_bom or p.ref not in board:
            continue
        base, per = board[p.ref]
        on_board = per.get(variant, base)
        if on_board != (not p.dnp):
            out[p.ref] = "fitted" if on_board else "DNP"
    return out


def _links_with_configs(docs: list[Path]) -> list[tuple[str, list[str]]]:
    """(link name, its own Configs) of every link in the documents that has ``Configs``."""
    from curatrix import meassemblies
    out = []
    for d in docs:
        try:
            sem = cad.freecad_trace(d, str(d))
        except Exception:  # noqa: BLE001 - a broken document is CK-D4's finding
            continue
        for name, o in sorted(sem["objects"].items()):
            if o.get("type") in meassemblies.LINK_TYPES:
                cs = cad._list(str((o.get("trace") or {}).get("Configs") or ""))
                if cs:
                    out.append((name, cs))
    return out


# ------------------------------------------------------------------ the listing
def listing(repo: str, m: modelmod.Model | None, upstream: list[modelmod.Model] | None,
            kicad_roots: list[Path] = (), freecad_files: list[Path] = (), rel=str) -> Listing:
    """Every board and assembly variant of one repo. ``m``: the repo's domain model (None: none);
    ``upstream``: the published system models (None or []: serves are taken as declared);
    ``rel``: path -> text for the output."""
    out = Listing(repo)
    vs, findings = domvariants.variants(m) if m is not None else ([], [])
    out.notes += findings
    defs: dict[str, str] = {}
    if m is not None:
        for p in m.user():
            if p.get("@type", "").endswith("Definition"):
                eid = modelmod.element_id(m, p)
                if eid and idmod.kind_of(eid) in KINDS:
                    defs.setdefault(eid, m.qn(p))
    rows = []
    if upstream:
        required, _ = domvariants.required_pairs(m, upstream) if m is not None else ({}, set())
        rows = domvariants.table(vs, required)
    elif vs:
        out.notes.append("no upstream model (model.upstream): the pairs are listed as the dependencies "
                         "declare them, not checked against the system model")

    projects = domvariants.kicad_projects(list(kicad_roots))
    fc_docs = {k: v for k, v in domvariants.freecad_documents(list(freecad_files)).items()
               if idmod.kind_of(k) == "ME-ASM"} if freecad_files else {}

    cad_order: list[tuple[str, str]] = []
    owners = sorted({v.owner for v in vs} | {t for t in projects if idmod.kind_of(t) == "EE-PCBA"} | set(fc_docs))
    for owner in owners:
        kind = KINDS.get(idmod.kind_of(owner), "")
        mine = {v.name or v.qn: v for v in vs if v.owner == owner}
        cad_names: dict[str, tuple[str, str]] = {}     # name -> (file, description)
        diffs: dict[str, list[str]] = {}
        links: list[tuple[str, list[str]]] = []
        if kind == "board" and projects.get(owner):
            pro = projects[owner][0]
            d = json.loads(pro.read_text(encoding="utf-8"))
            sch = pro.with_suffix(".kicad_sch")
            parts = bom.read(sch) if sch.is_file() else []
            pcb = pro.with_suffix(".kicad_pcb")
            board = board_fitted(pcb) if pcb.is_file() else {}
            for kv in ((d.get("schematic") or {}).get("variants") or []):
                if kv.get("name"):
                    cad_names.setdefault(kv["name"], (rel(pro), kv.get("description") or ""))
                    ds = bom.differences(parts, kv["name"])
                    for ref, state in board_mismatches(parts, board, kv["name"]).items():
                        i = next((k for k, x in enumerate(ds) if x in (f"{ref} DNP", f"{ref} fitted")), None)
                        sch_state = "DNP" if state == "fitted" else "fitted"
                        note = f"{ref} {sch_state} (board: {state})"
                        if i is None:
                            ds.append(note)
                        else:
                            ds[i] = note
                    diffs[kv["name"]] = ds
        elif kind == "assembly" and fc_docs.get(owner):
            for doc in fc_docs[owner]:
                for name, params in freecad_rows(doc).items():
                    cad_names.setdefault(name, (rel(doc), ""))
                    diffs.setdefault(name, list(params))
            links = _links_with_configs(fc_docs[owner])
        if not mine and not cad_names:
            if kind == "assembly":
                what = (f"links with Configs: {', '.join(f'{n} ({chr(44).join(cs)})' for n, cs in links)}"
                        if links else "no link with Configs")
                out.notes.append(f"{(owner + ' ' + _short(defs.get(owner, ''))).strip()}: no variant (no DomainVariant def, "
                                 f"no configuration table; {what})")
            continue
        cad_order += [(owner, n) for n in cad_names]
        for name in list(mine) + [n for n in cad_names if n not in mine]:
            v = mine.get(name)
            f, desc = cad_names.get(name, ("", ""))
            e = Listed(owner, (v.owner_qn if v else "") or defs.get(owner, ""), kind, name,
                       model_def=v.qn if v else "", cad_file=f, description=desc)
            e.differences = list(diffs.get(name, []))
            if v:
                e.configs, e.usages = list(v.configs), list(v.usages)
                if upstream:
                    e.serves = [[r.config, r.usage] for r in rows if r.owner == owner and name in r.variants]
                else:
                    e.serves = [list(p) for p in sorted(v.pairs)]
            for ln, cs in links:
                has = bool(set(cs) & set(e.configs))
                e.differences.append(f"link {ln} {'present' if has else 'absent'} (Configs {', '.join(cs)})")
            if not f and name in mine:
                e.differences.insert(0, "not in CAD")
            out.variants.append(e)
    # serving variants first, then by the first configuration they serve, then in CAD order
    # (.kicad_pro / configuration table); model.json is sorted by name, so it has no order of its own
    pos = {(e.owner, e.name): i for i, e in enumerate(out.variants)}
    cad_pos = {k: i for i, k in enumerate(cad_order)}
    out.variants.sort(key=lambda e: (e.owner, e.serves_none, min((c for c, _ in e.serves), default="~"),
                                     cad_pos.get((e.owner, e.name), len(cad_pos)), pos[(e.owner, e.name)]))
    out.unserved = [[r.config, r.usage, r.owner] for r in rows if not r.variants]
    return out


def for_repo(ws, repo, cfg) -> Listing:
    """The listing of a repo from its checks.yaml (model, model.upstream, cad sections)."""
    from curatrix import eeprojects, gen
    s = cfg.section("model") or {}
    m = ups = None
    notes = []
    if s:
        mj = cfg.resolve(s.get("json", "generated/model.json"))
        if mj.is_file():
            m = modelmod.Model.load(mj)
            if s.get("upstream"):
                ups, notes = gen.upstream_models(cfg)
        else:
            notes.append(f"{ws.rel(mj)} missing; run `curatrix gen model {repo.name}`")
    c = cfg.section("cad") or {}
    kicad = eeprojects.root_sheets(cfg) if c else []
    freecad = cfg.globs(c.get("freecad") or []) if c else []
    out = listing(repo.name, m, ups, kicad, freecad, rel=lambda p: str(Path(p).resolve().relative_to(repo.path.resolve()))
                  if Path(p).resolve().is_relative_to(repo.path.resolve()) else ws.rel(p))
    out.notes = notes + out.notes
    return out


# ------------------------------------------------------------------ text
def _short(qn: str) -> str:
    return qn.rsplit("::", 1)[-1] if qn else ""


def text(listings: list[Listing]) -> str:
    """Plain-text tables, one per repo."""
    if not listings:
        return "No repo has board or assembly variants.\n"
    lines = []
    head = ("Board / assembly", "Variant", "Model def", "KiCad / FreeCAD", "Differences", "Serves")
    for L in listings:
        lines.append(f"{L.repo}")
        if not L.variants:
            lines.append("  no board or assembly variants")
        rows = []
        for e in L.variants:
            owner = f"{e.owner} {_short(e.owner_def)}".strip()
            cadcell = (e.cad_file or "(not in CAD)") + (f' "{e.description}"' if e.description else "")
            serves = "; ".join(f"{c} {_short(u)}" for c, u in e.serves) or "none (serves no pair)"
            rows.append((owner, e.name, _short(e.model_def) or "(none)", cadcell,
                         ", ".join(e.differences) or "none", serves))
        if rows:
            w = [max(len(r[i]) for r in [head, *rows]) for i in range(len(head))]
            fmt = "  " + "  ".join(f"{{:<{x}}}" for x in w[:-1]) + "  {}"
            lines.append(fmt.format(*head).rstrip())
            lines += [fmt.format(*r).rstrip() for r in rows]
        for c, u, o in L.unserved:
            lines.append(f"  no variant of {o} serves {_short(u)} in {c}")
        lines += [f"  note: {n}" for n in L.notes]
        lines.append("")
    return "\n".join(lines)
