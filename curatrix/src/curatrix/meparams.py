"""Model-driven FreeCAD parameters (task 5.24; ME-6, XD-ADR-0137; check CK-F3).

The parameters of a top-level assembly come from its def in the ME model: every attribute with a
value of a part or port usage the def owns, or of the usage's def (``attribute holeSpacing = 12
[mm];``), is one parameter with the alias ``<usage>_<attribute>`` (``mount_holeSpacing``). At most
ten per assembly (iteration 1); the attributes of a port that redefine an attribute of a ``SYS-IF``
space budget its def specializes (co-design, XD-ADR-0134) are copied from the system model, not
chosen in ME, and do not count. Its placement and every attribute ME adds itself (a seat clearance,
a standoff height) count. Leaving the copies out interprets the ten parameters of XD-ADR-0137;
that is an open owner decision. Ports (``XdDomain::MechanicalPort``) give their placement in the
assembly by the attributes ``x``, ``y``, ``z`` (lengths) and ``yaw``, ``pitch``, ``roll`` (angles,
FreeCAD's order: about z, then y, then x).

* ``curatrix gen freecad-params <repo>`` writes the values into the spreadsheet ``Params`` of
  ``assemblies/<name>/<name>-skeleton.FCStd`` (FreeCADCmd, ``templates/freecad-asm/write-params.py``):
  skeleton, then top document (XD-ADR-0146), values only, recompute in dependency order (skeleton,
  parts, sub-assemblies, top), save the documents whose values or shapes changed.
* CK-F3 (plain Python) compares the aliases in ``Params`` and the placements of the LCS with a
  ``Port`` property with the model, with a tolerance per kind (``DEFAULT_TOL``) or the one of
  ``@XdDomain::ModelMatchTolerance { value = ...; }`` on the attribute, in the attribute's own unit
  (the agreement of a copied number, not a manufacturing tolerance).
"""
from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path

from curatrix import ids as idmod, meassemblies, model as modelmod

MAX_PARAMS = 10
PLACEMENT = ("x", "y", "z", "yaw", "pitch", "roll")
# unit (SysML SI name or FreeCAD / short name) -> (kind, factor to the base unit mm or deg)
UNITS = {"millimetre": ("length", 1.0), "mm": ("length", 1.0), "centimetre": ("length", 10.0), "cm": ("length", 10.0),
         "metre": ("length", 1000.0), "m": ("length", 1000.0), "micrometre": ("length", 0.001), "um": ("length", 0.001),
         "degree": ("angle", 1.0), "deg": ("angle", 1.0), "°": ("angle", 1.0),
         "radian": ("angle", 180.0 / math.pi), "rad": ("angle", 180.0 / math.pi)}
BASE = {"length": "mm", "angle": "deg", "number": ""}
DEFAULT_TOL = {"length": 0.001, "angle": 0.001, "number": 1e-9}     # mm, deg, plain numbers
TOLERANCE_DEF = "XdDomain::ModelMatchTolerance"     # model-to-CAD agreement, not a part tolerance
LCS_TYPES = ("Part::LocalCoordinateSystem", "PartDesign::CoordinateSystem")


@dataclass
class Param:
    alias: str
    usage: str
    attribute: str
    value: float              # in the base unit of its kind
    kind: str                 # length | angle | number
    tol: float                # in the base unit
    port: str | None          # the ME-PORT ID of a port usage
    budget: bool = False      # a copy of a SYS-IF space-budget value (not chosen in ME)

    @property
    def text(self) -> str:
        """The spreadsheet content FreeCAD reads (``12 mm``)."""
        v = f"{self.value:.6f}".rstrip("0").rstrip(".")
        return f"{v} {BASE[self.kind]}".strip()


def _literal(m, el) -> float | None:
    for x in m.walk(el):
        if x.get("@type") in ("LiteralInteger", "LiteralRational", "LiteralReal") and x.get("value") is not None:
            return float(x["value"])
    return None


def _value(m, attr) -> tuple[float, str, float] | None:
    """(value in the base unit, kind, factor of the attribute's own unit to the base unit) of an
    attribute's value expression, or None."""
    for _, x in m.owned(attr):
        t = x.get("@type", "")
        if t.startswith("Literal") and x.get("value") is not None and not isinstance(x["value"], str):
            return float(x["value"]), "number", 1.0
        if t == "OperatorExpression" and x.get("operator") == "[":
            num, unit = None, None
            for y in m.walk(x):
                if y.get("@type") in ("LiteralInteger", "LiteralRational", "LiteralReal") and num is None:
                    num = float(y["value"])
                if y.get("@type") == "FeatureReferenceExpression":
                    ref = (y.get("referent") or {}).get("@id", "")
                    unit = ref.rsplit("::", 1)[-1].strip("'")
            if num is not None and unit in UNITS:
                kind, f = UNITS[unit]
                return num * f, kind, f
            return None
    return None


def _tolerance(m, attr, kind: str, factor: float) -> float:
    """The tolerance in the base unit: the metadata value is in the attribute's own unit."""
    for md in m.metadata(attr):
        d = m.get(md.get("metadataDefinition")) or {}
        if (d.get("qualifiedName") or "") == TOLERANCE_DEF or str((md.get("metadataDefinition") or {}).get("@id", "")).endswith(TOLERANCE_DEF):
            v = _literal(m, md)
            if v is not None:
                return v * factor
    return DEFAULT_TOL[kind]


def _attributes(m, el, seen=None) -> list[dict]:
    """Attribute features of an element, its own first, then those of its defs and supers."""
    seen = seen if seen is not None else set()
    if el is None or el.get("@id") in seen or el.get("isLibraryElement"):
        return []
    seen.add(el["@id"])
    out = [x for _, x in m.owned(el) if x.get("@type") in ("AttributeUsage", "ReferenceUsage") and x.get("name")]
    nxt = m.declared_types(el) if el.get("@type", "").endswith("Usage") else m.supers(el)
    for t in nxt:
        out += _attributes(m, m.port_def(t)[0], seen)
    return out


def _redefines(m, a, budgets: tuple[str, ...], seen=None) -> bool:
    """Whether attribute ``a`` redefines an attribute of one of the defs ``budgets`` (qualified
    names), directly or through redefinitions in between (a usage redefining its def's attribute)."""
    seen = seen if seen is not None else set()
    if not budgets or a is None or a.get("@id") in seen:
        return False
    seen.add(a["@id"])
    for r in m.rels(a, "Redefinition"):
        t = m.get(r.get("redefinedFeature"))
        if t is None:
            continue
        if (t.get("qualifiedName") or "").startswith(tuple(f"{b}::" for b in budgets)):
            return True
        if not t.get("isLibraryElement") and _redefines(m, t, budgets, seen):
            return True
    return False


def model_params(m, asm) -> tuple[list[Param], list[str]]:
    """The parameters of an assembly def (see the module doc) and findings."""
    params, findings, aliases = [], [], set()
    budget = 0                                          # values copied from a SYS-IF budget
    for _, u in m.owned(asm):
        if u.get("@type") not in ("PartUsage", "PortUsage") or not u.get("name"):
            continue
        port, budgets = None, ()
        if u["@type"] == "PortUsage":
            t = next(iter(m.declared_types(u)), None)
            pdef = m.port_def(t)[0] if t else None
            pid = modelmod.element_id(m, pdef) if pdef else None
            port = pid if pid and idmod.kind_of(pid) == "ME-PORT" else None
            budgets = tuple(s["qualifiedName"] for s in (m.supers(pdef) if pdef else [])
                            if s.get("isLibraryElement") and s.get("qualifiedName")
                            and idmod.kind_of(modelmod.element_id(m, s) or "") == "SYS-IF")
        for a in _attributes(m, u):
            alias = f"{u['name']}_{a['name']}"
            if alias in aliases:
                continue                                # redefined closer to the usage
            v = _value(m, a)
            if v is None:
                continue
            aliases.add(alias)
            value, kind, factor = v
            if a["name"] in PLACEMENT and kind != ("angle" if a["name"] in PLACEMENT[3:] else "length"):
                findings.append(f"model {m.qn(a)}: {a['name']} needs a {'angle' if a['name'] in PLACEMENT[3:] else 'length'} "
                                f"with a unit")
            copied = _redefines(m, a, budgets)
            params.append(Param(alias, u["name"], a["name"], value, kind, _tolerance(m, a, kind, factor), port, copied))
            budget += copied
    if len(params) - budget > MAX_PARAMS:
        findings.append(f"model {m.qn(asm)}: {len(params) - budget} parameters (without {budget} values of SYS-IF budgets); "
                        f"at most {MAX_PARAMS} per assembly in iteration 1 (XD-ADR-0137)")
    return sorted(params, key=lambda p: p.alias), findings


def top_assemblies(cfg, m) -> list[tuple[str, dict, Path]]:
    """(ME-ASM ID, def, folder) of every top-level assembly def that has its folder."""
    asms, _ = meassemblies.model_defs(m)
    from curatrix.eeprojects import kebab
    out = []
    for aid, p in sorted(asms.items()):
        folder = cfg.repo / "assemblies" / kebab(p.get("name") or "")
        if folder.is_dir():
            out.append((aid, p, folder))
    return out


# ------------------------------------------------------------------ CK-F3
_CELL = re.compile(r"^\s*=?\s*([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)\s*([^\d\s][^\s]*)?\s*$")


def cell_value(content) -> tuple[float, str] | None:
    """(value in the base unit, kind) of a spreadsheet cell (``12 mm``, ``=90 °``, ``3``)."""
    mt = _CELL.match(str(content or ""))
    if not mt:
        return None
    num, unit = float(mt.group(1)), (mt.group(2) or "")
    if not unit:
        return num, "number"
    if unit not in UNITS:
        return None
    kind, f = UNITS[unit]
    return num * f, kind


def _qmul(a, b):
    w1, x1, y1, z1 = a
    w2, x2, y2, z2 = b
    return (w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
            w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2)


def _rotate(q, v):
    w, x, y, z = _qmul(_qmul(q, (0.0, *v)), (q[0], -q[1], -q[2], -q[3]))
    return (x, y, z)


def compose(outer: dict, inner: dict) -> dict:
    """outer * inner of two FreeCAD placements (Px..Pz, Q0..Q3 with Q3 = w)."""
    qo = (outer.get("Q3", 1.0), outer.get("Q0", 0.0), outer.get("Q1", 0.0), outer.get("Q2", 0.0))
    qi = (inner.get("Q3", 1.0), inner.get("Q0", 0.0), inner.get("Q1", 0.0), inner.get("Q2", 0.0))
    p = _rotate(qo, (inner.get("Px", 0.0), inner.get("Py", 0.0), inner.get("Pz", 0.0)))
    q = _qmul(qo, qi)
    return {"Px": outer.get("Px", 0.0) + p[0], "Py": outer.get("Py", 0.0) + p[1], "Pz": outer.get("Pz", 0.0) + p[2],
            "Q0": q[1], "Q1": q[2], "Q2": q[3], "Q3": q[0]}


def placement_values(pl: dict) -> dict[str, float]:
    """x, y, z (mm) and yaw, pitch, roll (deg, z-y-x as FreeCAD's Rotation.getYawPitchRoll)."""
    x, y, z, w = pl.get("Q0", 0.0), pl.get("Q1", 0.0), pl.get("Q2", 0.0), pl.get("Q3", 1.0)
    yaw = math.degrees(math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z)))
    pitch = math.degrees(math.asin(max(-1.0, min(1.0, 2 * (w * y - z * x)))))
    roll = math.degrees(math.atan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y)))
    return {"x": pl.get("Px", 0.0), "y": pl.get("Py", 0.0), "z": pl.get("Pz", 0.0), "yaw": yaw, "pitch": pitch, "roll": roll}


def _differs(a: float, b: float, kind: str, tol: float) -> bool:
    d = abs(a - b)
    if kind == "angle":
        d = abs((a - b + 180.0) % 360.0 - 180.0)
    return d > tol


def _lcs(cfg, folder: Path, docs: dict) -> list[tuple[str, str, str, dict]]:
    """(document, LCS name, Port, placement in the assembly) of every LCS with a Port in the folder."""
    top_rel = str((folder / f"{folder.name}.FCStd").relative_to(cfg.repo))
    top = docs.get(top_rel)
    out = []
    for rel, d in sorted(docs.items()):
        if not rel.startswith(str(folder.relative_to(cfg.repo)) + "/"):
            continue
        objs = d.sem["objects"]
        for name, o in objs.items():
            port = str((o.get("trace") or {}).get("Port") or "").strip()
            if o.get("type") not in LCS_TYPES or not port or port == "-":
                continue
            pl = o.get("placement") or {}
            # a container (App::Part) that holds the LCS: linked from the top -> the link's
            # placement replaces the container's, else the container's own
            holder = next((n for n, x in objs.items() if any(t.get("object") == name and not t.get("file")
                                                             for t in (x.get("links") or {}).get("Group", []))), None)
            outer = None
            if top is not None and rel != top_rel:
                for _, x in top.sem["objects"].items():
                    for t in (x.get("links") or {}).get("LinkedObject", []):
                        if t.get("file") and meassemblies._resolve(top_rel, t["file"]) == rel and \
                                t.get("object") in (holder, name):
                            outer = x.get("placement") or {}
            if outer is None and holder:
                outer = objs[holder].get("placement") or {}
            out.append((rel, name, port, compose(outer, pl) if outer else pl))
    return out


def check(cfg, m, docs: dict | None = None) -> list[str]:
    """CK-F3: Params aliases and LCS placements of every top-level assembly against the model."""
    docs = meassemblies.documents(cfg) if docs is None else docs
    findings: list[str] = []
    for aid, asm, folder in top_assemblies(cfg, m):
        params, f = model_params(m, asm)
        findings += f
        sk_rel = str((folder / meassemblies.skeleton_name(folder.name)).relative_to(cfg.repo))
        sk = docs.get(sk_rel)
        if sk is None:
            if params:
                findings.append(f"{sk_rel}: missing; the parameters of {asm.get('name')} ({aid}) live in its Params")
            continue
        sheets = sk.sem.get("spreadsheets") or {}
        cells = sheets.get("Params")
        if cells is None:
            if params:
                findings.append(f"{sk_rel}: no spreadsheet Params; `curatrix gen freecad-params {cfg.repo.name}` writes it")
            continue
        aliased = {k: v for k, v in cells.items() if not re.fullmatch(r"[A-Z]+\d+", k)}
        want = {p.alias: p for p in params}
        for alias, p in sorted(want.items()):
            if alias not in aliased:
                findings.append(f"{sk_rel}: Params has no alias {alias} ({m.qn(asm)}::{p.usage}::{p.attribute} = {p.text}); "
                                f"run `curatrix gen freecad-params {cfg.repo.name}`")
                continue
            got = cell_value(aliased[alias])
            if got is None or got[1] != p.kind:
                findings.append(f"{sk_rel}: Params.{alias} = {aliased[alias]!r}, the model has {p.text}")
            elif _differs(got[0], p.value, p.kind, p.tol):
                findings.append(f"{sk_rel}: Params.{alias} = {aliased[alias]}, the model has {p.text} "
                                f"(tolerance {p.tol:g} {BASE[p.kind]})")
        for alias in sorted(set(aliased) - set(want)):
            findings.append(f"{sk_rel}: Params.{alias} is no attribute of the model (aliases are <usage>_<attribute> of "
                            f"{asm.get('name')})")
        # LCS placements
        ports: dict[str, list[str]] = {}
        for p in params:
            if p.port:
                ports.setdefault(p.port, [])
                if p.usage not in ports[p.port]:
                    ports[p.port].append(p.usage)
        found: dict[str, list] = {}
        for rel, name, port, pl in _lcs(cfg, folder, docs):
            usages = ports.get(port)
            if usages is None:
                findings.append(f"{rel}: {name} has Port {port}, which is no port of {asm.get('name')} ({aid}) with a "
                                f"placement or parameters")
                continue
            usage = usages[0] if len(usages) == 1 else next((u for u in usages if name.endswith(u)), None)
            if usage is None:
                findings.append(f"{rel}: {name}: Port {port} is used by {', '.join(usages)}; name the LCS LCS_<usage>")
                continue
            found.setdefault(usage, []).append((rel, name))
            have = placement_values(pl)
            for p in params:
                if p.usage == usage and p.attribute in PLACEMENT and _differs(have[p.attribute], p.value, p.kind, p.tol):
                    findings.append(f"{rel}: {name}.{p.attribute} = {have[p.attribute]:.6g} {BASE[p.kind]}, the model "
                                    f"has {p.text} ({usage}, tolerance {p.tol:g} {BASE[p.kind]})")
        for p in params:
            if p.port and p.attribute in PLACEMENT and p.usage not in found:
                findings.append(f"{folder.relative_to(cfg.repo)}/: no LCS with Port = {p.port} for the port {p.usage} "
                                f"of {asm.get('name')}")
                found[p.usage] = []
        for usage, lst in sorted(found.items()):
            if len(lst) > 1:
                findings.append(f"{folder.relative_to(cfg.repo)}/: {len(lst)} LCS for the port {usage} "
                                f"({', '.join(f'{r}#{n}' for r, n in lst)}); exactly one")
    return findings


# ------------------------------------------------------------------ gen freecad-params
def write(ws, cfg, m, log=print) -> list[str]:
    """Write the model values into Params of every top-level assembly (FreeCADCmd). Returns errors."""
    from curatrix.newasm import run_script
    from curatrix.newpcba import NewError
    errs = []
    script = ws.xdmod / "templates" / "freecad-asm" / "write-params.py"
    for aid, asm, folder in top_assemblies(cfg, m):
        params, f = model_params(m, asm)
        if f:
            errs += f
            continue
        top, sk = folder / f"{folder.name}.FCStd", folder / meassemblies.skeleton_name(folder.name)
        if not (top.is_file() and sk.is_file()):
            errs.append(f"{ws.rel(folder)}: needs {top.name} and {sk.name} (`curatrix new asm`)")
            continue
        out = ws.build(cfg.area) / "freecad-params"
        out.mkdir(parents=True, exist_ok=True)
        pf = out / f"{folder.name}.params.json"
        pf.write_text(json.dumps({p.alias: p.text for p in params}, indent=2, sort_keys=True))
        try:
            res = run_script(ws, script, {"XD_TOP": str(top.resolve()), "XD_SKELETON": str(sk.resolve()),
                                          "XD_PARAMS": str(pf)}, out / f"{folder.name}.result.json")
        except NewError as e:
            errs.append(f"{ws.rel(folder)}: {e}")
            continue
        for saved in res.get("saved") or []:          # backups of the files this run saved only
            sp = Path(saved)
            for bak in sp.parent.glob(f"{sp.stem}.*.FCBak"):
                bak.unlink()
        log(f"  {ws.rel(folder)}: {len(params)} parameter(s); changed: {', '.join(res.get('changed') or []) or 'none'}; "
            f"saved: {', '.join(ws.rel(Path(x)) for x in res.get('saved') or []) or 'nothing'}; "
            f"recompute order: {' -> '.join(res.get('order') or [])}")
    return errs
