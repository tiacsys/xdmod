"""The bill of materials of a KiCad project in plain Python (task 5.21; XD-ADR-0129, XD-ADR-0136;
checks CK-F12, CK-D9).

``read(root_sch)`` walks the sheet hierarchy (a sheet used twice gives its symbols twice, with the
references of each instance) and returns one ``Part`` per reference: multi-unit symbols are one
part. Power symbols (``#`` references, ``(power)`` library symbols) are left out. Each part keeps
the flags ``in_bom`` and ``dnp`` of its symbol and, per KiCad 10 assembly variant, the overrides
stored at its instance (``(variant (name ..) (dnp ..) (in_bom ..) (field (name ..) (value ..)))``).

``resolve(parts, variant)`` gives the parts as one variant sees them (``None`` = the base
schematic, which is what KiCad exports without ``--variant``). On top of that:

* ``table(parts, variants)``: the board document's BOM, grouped by value, footprint, Manufacturer
  and MPN (equal in every variant), references collapsed (``R1-R4, R7``), one column per variant
  (quantity fitted, ``DNP``, a value override, the shunt ``Setting``);
* ``variants_table(...)``: the variants of the board (name, description, what is fitted
  differently from the base schematic, the ``Setting`` of each part that has one, the Zephyr board
  variant of the same name);
* ``field_findings(parts)`` (CK-F12): every BOM part has ``Manufacturer`` and ``MPN``, or a
  ``Standard`` field with its standard designation instead;
* ``from_kicad_csv`` / ``compare`` (CK-D9): the reader against ``kicad-cli sch export bom
  --variant`` (one line per reference, ``KICAD_FIELDS``).
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path

from curatrix.cad import _children, _props, sexpr

MANUFACTURER, MPN, STANDARD, SETTING = "Manufacturer", "MPN", "Standard", "Setting"
# what CK-D9 asks kicad-cli for (no grouping: one line per reference)
KICAD_FIELDS = ("Reference", "Value", "Footprint", "DNP", MANUFACTURER, MPN, SETTING)


@dataclass
class Part:
    ref: str
    value: str
    footprint: str
    fields: dict                                   # every property of the symbol
    in_bom: bool = True
    dnp: bool = False
    sheet: str = "/"
    overrides: dict = field(default_factory=dict)  # variant -> {"dnp": bool, "in_bom": bool, "fields": {..}}

    def get(self, name: str) -> str:
        return (self.fields.get(name) or "").strip()


def _flag(node, name: str, default: bool) -> bool:
    c = _children(node, name)
    return (c[0][1] == "yes") if c and len(c[0]) > 1 else default


def _variant_overrides(path_node) -> dict:
    out = {}
    for v in _children(path_node, "variant"):
        name = next((c[1] for c in _children(v, "name") if len(c) > 1), None)
        if not name:
            continue
        o: dict = {"fields": {}}
        for k in ("dnp", "in_bom"):
            if _children(v, k):
                o[k] = _flag(v, k, False)
        for f in _children(v, "field"):
            n = next((c[1] for c in _children(f, "name") if len(c) > 1), None)
            val = next((c[1] for c in _children(f, "value") if len(c) > 1), "")
            if n:
                o["fields"][n] = val
        out[name] = o
    return out


def read(root_sch: Path) -> list[Part]:
    """One Part per reference, through the sheet hierarchy, sorted by reference."""
    parts: dict[str, Part] = {}

    def uuid_of(node) -> str:
        u = _children(node, "uuid")
        return u[0][1] if u and len(u[0]) > 1 else ""

    def visit(sch: Path, sheet: str, inst: str | None, depth: int):
        if depth > 20:
            return
        tree = sexpr(sch.read_text(encoding="utf-8"))
        if inst is None:
            inst = "/" + uuid_of(tree)
        libs = {s[1]: s for s in (_children(tree, "lib_symbols")[0][1:] if _children(tree, "lib_symbols") else [])
                if isinstance(s, list) and len(s) > 1}
        for s in _children(tree, "symbol"):
            lid = _children(s, "lib_id")
            if not lid:
                continue
            ln = _children(s, "lib_name")
            lib = libs.get(ln[0][1]) if ln and len(ln[0]) > 1 else None
            lib = lib or libs.get(lid[0][1])
            props = _props(s)
            ref, over = props.get("Reference", ""), {}
            for ins in _children(s, "instances"):
                for proj in _children(ins, "project"):
                    for p in _children(proj, "path"):
                        if len(p) > 1 and p[1] == inst:
                            r = _children(p, "reference")
                            ref = r[0][1] if r and len(r[0]) > 1 else ref
                            over = _variant_overrides(p)
            if not ref or ref.startswith("#") or (lib is not None and _children(lib, "power")):
                continue
            part = parts.get(ref)
            if part is None:                       # the first unit of a multi-unit symbol
                parts[ref] = Part(ref, props.get("Value", ""), props.get("Footprint", ""), props,
                                  _flag(s, "in_bom", True), _flag(s, "dnp", False), sheet, over)
            else:                                  # further units: DNP on any unit marks the part (as KiCad)
                part.dnp = part.dnp or _flag(s, "dnp", False)
                for v, o in over.items():
                    mine = part.overrides.setdefault(v, {"fields": {}})
                    mine["fields"].update(o.get("fields") or {})
                    mine.update({k: o[k] for k in ("dnp", "in_bom") if k in o})
        for sh in _children(tree, "sheet"):
            p = _props(sh)
            sub = p.get("Sheetfile") or p.get("Sheet file", "")
            name = p.get("Sheetname") or p.get("Sheet name", "")
            if sub and (sch.parent / sub).is_file():
                visit(sch.parent / sub, sheet + name + "/", inst + "/" + uuid_of(sh), depth + 1)

    visit(root_sch, "/", None, 0)
    return sorted(parts.values(), key=lambda p: ref_key(p.ref))


def ref_key(ref: str):
    m = re.match(r"^(.*?)(\d+)$", ref)
    return (m.group(1), int(m.group(2))) if m else (ref, -1)


def resolve(parts: list[Part], variant: str | None) -> list[Part]:
    """The parts as ``variant`` sees them (None: the base schematic)."""
    out = []
    for p in parts:
        o = p.overrides.get(variant) if variant else None
        if not o:
            out.append(p)
            continue
        fields = {**p.fields, **(o.get("fields") or {})}
        out.append(Part(p.ref, fields.get("Value", ""), fields.get("Footprint", ""), fields,
                        o.get("in_bom", p.in_bom), o.get("dnp", p.dnp), p.sheet, {}))
    return out


def collapse(refs: list[str]) -> str:
    """``R1, R2, R3, R4, R7`` -> ``R1-R4, R7``."""
    out, run = [], []
    for r in sorted(refs, key=ref_key):
        k = ref_key(r)
        if run and k[0] == ref_key(run[-1])[0] and k[1] == ref_key(run[-1])[1] + 1:
            run.append(r)
            continue
        if run:
            out.append(run[0] if len(run) < 3 else f"{run[0]}-{run[-1]}")
            out += run[1:2] if len(run) == 2 else []
        run = [r]
    if run:
        out.append(run[0] if len(run) < 3 else f"{run[0]}-{run[-1]}")
        out += run[1:2] if len(run) == 2 else []
    return ", ".join(out)


def bom_parts(parts: list[Part], variants: list[str]) -> list[Part]:
    """The parts in the BOM of the base or of any variant."""
    seen = {p.ref for v in [None, *variants] for p in resolve(parts, v) if p.in_bom}
    return [p for p in parts if p.ref in seen]


def table(parts: list[Part], variants: list[str]) -> tuple[list[str], list[list[str]]]:
    """(head, rows) of the board document's BOM: one column per variant (or ``Qty`` without
    variants). A group's parts agree in value, footprint, Manufacturer and MPN in every variant."""
    views = {v: {p.ref: p for p in resolve(parts, v)} for v in [None, *variants]}
    groups: dict[tuple, list[str]] = {}
    for p in bom_parts(parts, variants):
        key = tuple((views[v][p.ref].value, views[v][p.ref].footprint, views[v][p.ref].get(MANUFACTURER),
                     views[v][p.ref].get(MPN)) for v in [None, *variants])
        groups.setdefault(key, []).append(p.ref)
    head = ["References", "Value", "Footprint", MANUFACTURER, MPN] + ([f"Variant {v}" for v in variants] or ["Qty"])
    rows = []
    for key, refs in sorted(groups.items(), key=lambda kv: ref_key(kv[1][0])):
        base = views[None][refs[0]]
        row = [collapse(refs), base.value, base.footprint,
               base.get(MANUFACTURER) or (f"{STANDARD}: {base.get(STANDARD)}" if base.get(STANDARD) else ""),
               base.get(MPN)]
        for v in variants or [None]:
            ps = [views[v][r] for r in refs]
            fitted = [p for p in ps if p.in_bom and not p.dnp]
            out_ = [p for p in ps if not p.in_bom]
            cell = str(len(fitted)) if fitted else ("not in BOM" if len(out_) == len(ps) else "DNP")
            if fitted and len(fitted) < len(ps):
                dnp = [p.ref for p in ps if p.in_bom and p.dnp]
                cell += (", " + collapse(dnp) + " DNP" if dnp else "") + \
                    (", " + collapse([p.ref for p in out_]) + " not in BOM" if out_ else "")
            if v:                                  # the variant's own part, where it is not the base's
                mine = views[v][refs[0]]
                for label, a_, b_ in (("value", mine.value, base.value), ("footprint", mine.footprint, base.footprint),
                                      (MANUFACTURER, mine.get(MANUFACTURER), base.get(MANUFACTURER)),
                                      (MPN, mine.get(MPN), base.get(MPN))):
                    if a_ != b_:
                        cell += f", {label} {a_ or '(none)'}"
            settings = sorted({p.get(SETTING) for p in ps if p.get(SETTING)})
            if settings:
                cell += ", " + "/".join(settings)
            row.append(cell)
        rows.append(row)
    return head, rows


def differences(parts: list[Part], variant: str) -> list[str]:
    """What ``variant`` fits differently from the base schematic: ``R1 DNP``, ``JP1 fitted``,
    ``R2 value 4k7`` (``Setting`` is listed on its own)."""
    out = []
    base = {p.ref: p for p in parts}
    for p in resolve(parts, variant):
        b = base[p.ref]
        if (b.in_bom and not b.dnp) != (p.in_bom and not p.dnp):
            out.append(f"{p.ref} {'fitted' if p.in_bom and not p.dnp else 'DNP'}")
        for k in sorted(set(p.fields) | set(b.fields)):
            if k not in (SETTING, "Reference") and p.fields.get(k, "") != b.fields.get(k, ""):
                out.append(f"{p.ref} {k.lower() if k in ('Value', 'Footprint') else k} {p.fields.get(k, '')}")
    return out


def settings(parts: list[Part], variant: str | None) -> list[str]:
    """``J2 2-3`` for every part with a ``Setting`` field in ``variant``."""
    return [f"{p.ref} {p.get(SETTING)}" for p in resolve(parts, variant) if p.get(SETTING)]


def variants_table(parts: list[Part], variants: list[dict], zephyr: dict[str, list[str]] | None,
                   zboard: str) -> list[list[str]]:
    """Rows (variant, description, fitted differences, jumper settings, Zephyr board variant).
    ``variants``: the .kicad_pro ``schematic.variants``; ``zephyr``: Zephyr board -> variant
    names (None: no Zephyr board roots configured); ``zboard``: the board's Zephyr name."""
    rows = []
    for v in variants:
        name = v.get("name") or ""
        if zephyr is None or zboard not in zephyr:
            z = "—"
        else:
            z = next((f"{zboard}/{x}" for x in zephyr[zboard] if x.split("/")[-1] == name), "none")
        rows.append([name, v.get("description") or "", ", ".join(differences(parts, name)) or "none",
                     ", ".join(settings(parts, name)) or "—", z])
    return rows


def field_findings(parts: list[Part], variants: list[str], where: str) -> list[str]:
    """CK-F12: Manufacturer and MPN on every BOM part, or a Standard designation instead, as the
    base schematic and every variant see it; a variant that changes the value or footprint of a
    part keeps no MPN of the base (it must name its own)."""
    out = []
    base = {p.ref: p for p in parts}
    seen: dict[str, list[str]] = {}                # ref -> fields already reported missing
    for v in [None, *variants]:
        tag = f" (variant {v})" if v else ""
        for p in resolve(parts, v):
            if not p.in_bom or p.get(STANDARD):
                continue
            miss = [f for f in (MANUFACTURER, MPN) if not p.get(f)]
            if miss and seen.get(p.ref) != miss:
                seen[p.ref] = miss
                out.append(f"{where}: {p.ref} ({p.value}){tag} has no {' and no '.join(miss)}; add the field(s), "
                           f"or a field {STANDARD} with the part's standard designation")
                continue
            if miss:
                continue
            b = base[p.ref]
            if v and (p.value, p.footprint) != (b.value, b.footprint) and p.get(MPN) == b.get(MPN):
                out.append(f"{where}: {p.ref}{tag} is {p.value} ({p.footprint}) but keeps the MPN {b.get(MPN)} of the "
                           f"base ({b.value}); override MPN in the variant too")
    return list(dict.fromkeys(out))


# ------------------------------------------------------------------ CK-D9: against KiCad's BOM export
def kicad_argv(sch: Path, out: Path, variant: str | None) -> list[str]:
    return (["kicad-cli", "sch", "export", "bom", "--fields", ",".join(KICAD_FIELDS), "--labels",
             ",".join(KICAD_FIELDS), "--group-by", "", "--ref-range-delimiter", "", "-o", str(out)]
            + (["--variant", variant] if variant else []) + [str(sch)])


def from_kicad_csv(path: Path) -> dict[str, dict]:
    """Reference -> {field: value} of an ungrouped kicad-cli BOM (``kicad_argv``)."""
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    out = {}
    for r in rows:
        for ref in (r.get("Reference") or "").split(","):
            if ref.strip():
                out[ref.strip()] = {k: (v or "").strip() for k, v in r.items() if k != "Reference"}
    return out


def mine(parts: list[Part], variant: str | None) -> dict[str, dict]:
    """The reader's view in the shape of ``from_kicad_csv``."""
    return {p.ref: {"Value": p.value, "Footprint": p.footprint, "DNP": "DNP" if p.dnp else "",
                    MANUFACTURER: p.get(MANUFACTURER), MPN: p.get(MPN), SETTING: p.get(SETTING)}
            for p in resolve(parts, variant) if p.in_bom}


def compare(ours: dict[str, dict], kicad: dict[str, dict], where: str) -> list[str]:
    out = []
    for ref in sorted(set(ours) | set(kicad), key=ref_key):
        if ref not in kicad:
            out.append(f"{where}: {ref} is in the reader's BOM, not in KiCad's")
        elif ref not in ours:
            out.append(f"{where}: {ref} is in KiCad's BOM, not in the reader's")
        else:
            for k in KICAD_FIELDS[1:]:
                a, b = ours[ref].get(k, ""), kicad[ref].get(k, "")
                if a != b:
                    out.append(f"{where}: {ref} {k} {a!r} here, {b!r} in KiCad")
    return out
