"""FreeCAD checks of an ME repo (task 5.25; ME-7, XD-ADR-0126, XD-ADR-0137; checks CK-F4c, CK-F16,
CK-F17, CK-F18). One ``FreeCADCmd`` run (``templates/freecad-asm/check-asm.py``, under the
``freecad`` limits and the workspace-local config) opens every FreeCAD document of the repo
(checks.yaml ``cad.freecad``; per assembly the skeleton first, then the top document, so the parts
load fully through its links), recomputes everything without saving and reports:

* **CK-F4c** objects that are not valid after the recompute. The exploded-view objects of the
  Assembly workbench are left out: their Python proxy cannot load in ``FreeCADCmd`` (FreeCAD spike
  §5), which is no design error.
* **CK-F16** objects with an ``ME-PART`` ``TraceID`` whose shape is not valid solids (Part check:
  valid, at least one solid, every solid valid with a volume, no face or shell outside the solids).
* **CK-F17** overlaps between the direct children of an assembly (the links in the group of each
  object with an ``ME-ASM`` ``TraceID``), per variant: a link with its own ``Configs`` is there only
  in the configurations it names (an overlap of two parts that are in every variant is one finding
  without a variant). The skeleton link and library fasteners (a link to an object in ``lib/``
  with a ``Standard`` property, the standard designation) are left out. Common volume above
  ``OVERLAP_TOL`` is a finding; parts joined by an assembly joint (``Reference1`` and
  ``Reference2`` of a joint name both links) may touch and get ``JOINED_TOL``, the numerical noise of
  a boolean on coincident faces. Touching faces give no volume, so touching is free for every pair.
* **CK-F18** each board model (a link whose target carries an ``EE-PCBA`` ``TraceID``, e.g. a board of
  the board library, XD-ADR-0139) inside its ``SYS-IF`` space budget (XD-ADR-0134). The seats are
  the ME port defs (``ME-PORT``) that specialize a ``SYS-IF`` budget of the upstream model; the
  budget's box is ``width`` x ``depth`` in the board frame (origin at the lower-left corner of the
  outline seen from the top, z = 0 on the top face), from ``-heightBelow`` to ``heightAbove``,
  with the values the seat restates or else the budget's defaults. Findings (rule ``space``):
  a board link not placed at a seat LCS (an LCS with ``Port`` = a seat, reached through the
  skeleton link); a board that reaches out of the box by more than ``BOX_TOL``; a part (not a
  fastener, not a board) with a common volume above ``OVERLAP_TOL`` with the box (a stand-off
  under the board, a wall too close); a library fastener with a common volume above
  ``OVERLAP_TOL`` with the board (a screw that misses the board's hole). Fasteners may pass
  through the box (they hold the board through the budget's holes); board versus part collisions
  are CK-F17's. Without a board model the check is a skip with its reason. The items of an
  ``accepted.yaml`` entry: the board link for its own findings (box, seat), the part or fastener
  link for the others.

Every error can be accepted in ``assemblies/<name>/accepted.yaml``, in the format and with the
acceptor rule of ``ercdrc`` (XD-ADR-0126, CK-F9): ``check`` CK-F4c | CK-F16 | CK-F17, ``rule``
recompute | solid | overlap, ``items`` the part names (CK-F17: the two link names; CK-F4c and
CK-F16: ``<document stem>#<object>``), never positions.
A finding of a document inside ``assemblies/<name>/`` is accepted there; a finding of a shared
document (``parts/``, ``lib/``) in the ``accepted.yaml`` of any assembly. Agents never write
``Accepted-by:``.
"""
from __future__ import annotations

import json
from pathlib import Path

from curatrix import ercdrc, meassemblies

SCRIPT = Path("templates") / "freecad-asm" / "check-asm.py"
OVERLAP_TOL = 1e-3          # mm^3
JOINED_TOL = 0.1            # mm^3, parts joined by an assembly joint
RULES = {"CK-F4c": "recompute", "CK-F16": "solid", "CK-F17": "overlap", "CK-F18": "space"}
BOX_TOL = 0.01              # mm, a board beyond its budget box; KiCad's STEP seats components 5 um off the top face
BOX = ("width", "depth", "heightAbove", "heightBelow")
_CACHE: dict[tuple, dict] = {}


class MeCheckError(Exception):
    pass


def files(cfg) -> list[Path]:
    """Every FreeCAD document of the repo, each assembly's skeleton and top document first."""
    docs = sorted({p.resolve() for p in cfg.globs((cfg.section("cad") or {}).get("freecad") or [])})
    first = []
    for d in meassemblies.top_folders(cfg):
        for f in (d / meassemblies.skeleton_name(d.name), d / f"{d.name}.FCStd"):
            if f.is_file():
                first.append(f.resolve())
    return first + [p for p in docs if p not in first]


def seats(cfg) -> dict[str, dict]:
    """{ME-PORT: {budget, values: {width, depth, heightAbove, heightBelow}, missing}} of every seat:
    an ME port def that specializes a ``SYS-IF`` space budget of the upstream model (co-design,
    XD-ADR-0134). A value the seat restates wins over the budget's default."""
    from curatrix import gen, ids as idmod, meparams, model as modelmod
    mj = cfg.resolve((cfg.section("model") or {}).get("json", "generated/model.json"))
    if not (cfg.section("model") and mj.is_file()):
        return {}
    m = modelmod.Model.load(mj)
    ups, _ = gen.upstream_models(cfg)
    joined = modelmod.Joined(m, ups)
    out = {}
    for pdef in m.user():
        if pdef.get("@type") != "PortDefinition":
            continue
        pid = modelmod.element_id(m, pdef) or ""
        if idmod.kind_of(pid) != "ME-PORT":
            continue
        for s in m.supers(pdef):
            sid = modelmod.element_id(m, s) or ""
            if idmod.kind_of(sid) != "SYS-IF":
                continue
            um, full = joined.full(s)
            values = {}
            for mm, el in ((um, full), (m, pdef)):          # the budget's defaults, then the seat's own values
                if el is None:
                    continue
                for a in meparams._attributes(mm, el):
                    v = meparams._value(mm, a) if a.get("name") in BOX else None
                    if v is not None and v[1] == "length":
                        values[a["name"]] = v[0]
            out[pid] = {"budget": sid, "values": values, "missing": [k for k in BOX if k not in values]}
            break
    return out


def run(ws, cfg, out: Path) -> dict:
    """The FreeCAD result of the repo (cached per set of files and their modification times)."""
    fs = files(cfg)
    st = seats(cfg)
    key = (str(cfg.repo.resolve()), tuple((str(f), f.stat().st_mtime_ns) for f in fs), json.dumps(st, sort_keys=True))
    if key in _CACHE:
        return _CACHE[key]
    if not fs:
        res = {"ok": True, "recompute": [], "parts": [], "solids": [], "assemblies": []}
    else:
        from curatrix.newasm import run_script
        from curatrix.newpcba import NewError
        lib = (cfg.repo / "lib").resolve()
        try:
            res = run_script(ws, ws.xdmod / SCRIPT, {"XD_FILES": json.dumps([str(f) for f in fs]), "XD_LIB": str(lib),
                                                     "XD_SEATS": json.dumps({k: v["values"] for k, v in st.items()
                                                                             if not v["missing"]})},
                             out / "me-checks.result.json")
        except NewError as e:
            raise MeCheckError(str(e)) from None
        res["seats"] = st
    _CACHE[key] = res
    return res


def _rel(cfg, p: str) -> str:
    try:
        return str(Path(p).resolve().relative_to(cfg.repo.resolve()))
    except ValueError:
        return p


def _folder(cfg, rel: str) -> str | None:
    """The assembly folder (``assemblies/<name>``) of a repo-relative path, or None."""
    parts = Path(rel).parts
    return "/".join(parts[:2]) if len(parts) > 2 and parts[0] == "assemblies" else None


def _finding(check: str, text: str, names: list[str]) -> ercdrc.Finding:
    return ercdrc.Finding(check, RULES[check], "error", text, [], [], names=names)


def findings(cfg, res: dict, check: str) -> list[tuple[str | None, ercdrc.Finding]]:
    """(assembly folder or None for a shared document, finding) of one check."""
    out = []
    if check == "CK-F4c":
        for x in res.get("recompute") or []:
            rel = _rel(cfg, x["doc"])
            name = f"{Path(rel).stem}#{x['object']}"
            out.append((_folder(cfg, rel), _finding(check, f"{rel}: {x['object']} ({x['type']}) does not recompute: "
                                                           f"{', '.join(x.get('state') or [])}", [name])))
    elif check == "CK-F16":
        for x in res.get("solids") or []:
            rel = _rel(cfg, x["doc"])
            name = f"{Path(rel).stem}#{x['object']}"
            out.append((_folder(cfg, rel), _finding(check, f"{rel}: {x['object']} ({x['id']}): {x['problem']}", [name])))
    elif check == "CK-F17":
        for a in res.get("assemblies") or []:
            rel = _rel(cfg, a["doc"])
            kids = {k["name"]: k for k in a.get("children") or []}
            configs = sorted({c for k in kids.values() for c in meassemblies.cad._list(k.get("configs") or "")})
            joined = {tuple(sorted(j)) for j in a.get("joined") or []}
            for o in a.get("overlaps") or []:
                pair = tuple(sorted((o["a"], o["b"])))
                tol = JOINED_TOL if pair in joined else OVERLAP_TOL
                if o["volume"] <= tol:
                    continue
                if all(not meassemblies.cad._list(kids.get(n, {}).get("configs") or "") for n in pair):
                    where = [""]                   # both parts are in every variant: one finding
                else:
                    where = [c for c in configs if all(_present(kids.get(n), c) for n in pair)]
                j = ", joined" if pair in joined else ""
                for c in where:
                    label = f" (variant {c})" if c else ""
                    out.append((_folder(cfg, rel), _finding(
                        check, f"{rel}{label}: {pair[0]} and {pair[1]} overlap by {o['volume']:.4g} mm³ "
                               f"(tolerance {tol:g} mm³{j})", list(pair))))
    elif check == "CK-F18":
        out += _space_findings(cfg, res)
    return out


def _space_findings(cfg, res: dict) -> list[tuple[str | None, ercdrc.Finding]]:
    """CK-F18 findings (see the module doc)."""
    out = []
    st = res.get("seats") or {}
    sides = (("x", 0, "left of the outline (x < 0)", None), ("y", 1, "below the outline (y < 0)", None),
             ("z", 2, "below heightBelow", "heightBelow"), ("x", 3, "beyond width", "width"),
             ("y", 4, "beyond depth", "depth"), ("z", 5, "above heightAbove", "heightAbove"))
    for a in res.get("assemblies") or []:
        rel = _rel(cfg, a["doc"])
        folder = _folder(cfg, rel)
        for b in a.get("budgets") or []:
            board = b["board"]

            def add(text, names, _board=board):     # items: the board, or the part / fastener alone (an
                # entry's items must cover all of a finding's, so [board, part] would also accept the board's own)
                out.append((folder, _finding("CK-F18", f"{rel}: {text}", names or [_board])))
            for f in b.get("fasteners") or []:
                if f["volume"] > OVERLAP_TOL:
                    add(f"{board} and the fastener {f['name']} overlap by {f['volume']:.4g} mm³ (tolerance "
                        f"{OVERLAP_TOL:g} mm³): the fastener misses the board's hole", [f["name"]])
            if not b.get("seat"):
                add(f"{board} is not placed at a board seat (an LCS with Port = an ME-PORT that specializes a SYS-IF "
                    f"budget: {', '.join(sorted(st)) or 'none in the model'}); the link sits at {b.get('placement')}", [])
                continue
            seat = st.get(b["port"]) or {}
            if seat.get("missing"):
                add(f"{board} at {b['seat']} ({b['port']}): the budget {seat.get('budget')} has no value for "
                    f"{', '.join(seat['missing'])}", [])
                continue
            v = seat["values"]
            lim = {"width": v["width"], "depth": v["depth"], "heightAbove": v["heightAbove"],
                   "heightBelow": -v["heightBelow"]}
            bb = b.get("bbox") or []
            for axis, i, what, key in sides if bb else ():
                edge = lim[key] if key else 0.0
                over = (edge - bb[i]) if i < 3 else (bb[i] - edge)
                if over > BOX_TOL:
                    add(f"{board} reaches {over:.3g} mm {what} of the space budget {seat['budget']} at {b['seat']} "
                        f"({b['port']}; board {axis} {bb[i]:.3f} mm, budget {edge:g} mm, tolerance {BOX_TOL:g} mm)", [])
            for x in b.get("intrusions") or []:
                if x["volume"] > OVERLAP_TOL:
                    add(f"{x['name']} reaches into the space budget {seat['budget']} of {board} at {b['seat']} "
                        f"({b['port']}) by {x['volume']:.4g} mm³, z {x['z'][0]:.3g} to {x['z'][1]:.3g} mm in the "
                        f"board frame (tolerance {OVERLAP_TOL:g} mm³)", [x["name"]])
    return out


def _present(kid: dict | None, config: str) -> bool:
    if kid is None:
        return False
    cs = meassemblies.cad._list(kid.get("configs") or "")
    return not config or not cs or config in cs


def boards(res: dict) -> list[str]:
    return [k["name"] for a in res.get("assemblies") or [] for k in a.get("children") or [] if k.get("kind") == "board"]


def folder_entries(cfg, acc: ercdrc.Acceptors) -> tuple[dict[str, list[ercdrc.Entry]], list[str]]:
    """accepted.yaml entries per assembly folder, and format findings."""
    out, errs = {}, []
    for d in meassemblies.top_folders(cfg):
        entries, e = ercdrc.folder_entries(cfg, d, acc)
        out[str(d.relative_to(cfg.repo))] = entries
        errs += e
    return out, errs


def evaluate(cfg, check: str, found: list[tuple[str | None, ercdrc.Finding]],
             entries: dict[str, list[ercdrc.Entry]]) -> ercdrc.Outcome:
    """The errors of one check that no accepted entry covers, and the entries that match nothing."""
    total = ercdrc.Outcome()
    mine = {k: [e for e in v if e.check == check] for k, v in entries.items()}
    by_folder: dict[str | None, list[ercdrc.Finding]] = {}
    for folder, f in found:
        by_folder.setdefault(folder, []).append(f)
    for folder, fs in by_folder.items():
        pool = mine.get(folder, []) if folder else [e for v in mine.values() for e in v]
        o = ercdrc.evaluate(fs, pool, {})
        total.problems += o.problems
        total.listed += o.listed
        total.rows += o.rows                      # the assembly document's findings table (findings.json)
    for folder, es in sorted(mine.items()):
        for e in es:
            if not e.hits:
                total.problems.append(f"{folder}/{ercdrc.ACCEPTED} {e.label()} matches no {check} finding; remove it")
    return total
