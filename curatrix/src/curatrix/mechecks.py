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
  object with an ``ME-ASM`` ``TraceID``), per variant: a link with ``Configs`` is there only in the
  configurations it names. The skeleton link and library fasteners (a link to an object in ``lib/``
  with a ``Standard`` property, the standard designation) are left out. Common volume above
  ``OVERLAP_TOL`` is a finding; parts joined by an assembly joint (``Reference1`` and
  ``Reference2`` of a joint name both links) may touch and get ``JOINED_TOL``, the numerical noise of
  a boolean on coincident faces. Touching faces give no volume, so touching is free for every pair.
* **CK-F18** each board model (a link whose target carries an ``EE-PCBA`` ``TraceID``) inside its
  ``SYS-IF`` space budget. The budget's form comes from the co-design task 5.28; until then a board
  model is reported as not checked, and an assembly without a board model is a skip with its reason.

Every error can be accepted in ``assemblies/<name>/accepted.yaml``, in the format and with the
acceptor rule of ``ercdrc`` (XD-ADR-0126, CK-F9): ``check`` CK-F4c | CK-F16 | CK-F17 | CK-F18,
``rule`` recompute | solid | overlap | space-budget, ``items`` the part names (CK-F17: the two link
names; CK-F4c and CK-F16: ``<document stem>#<object>``; CK-F18: the board link), never positions.
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
RULES = {"CK-F4c": "recompute", "CK-F16": "solid", "CK-F17": "overlap", "CK-F18": "space-budget"}
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


def run(ws, cfg, out: Path) -> dict:
    """The FreeCAD result of the repo (cached per set of files and their modification times)."""
    fs = files(cfg)
    key = (str(cfg.repo.resolve()), tuple((str(f), f.stat().st_mtime_ns) for f in fs))
    if key in _CACHE:
        return _CACHE[key]
    if not fs:
        res = {"ok": True, "recompute": [], "parts": [], "solids": [], "assemblies": []}
    else:
        from curatrix.newasm import run_script
        from curatrix.newpcba import NewError
        lib = (cfg.repo / "lib").resolve()
        try:
            res = run_script(ws, ws.xdmod / SCRIPT, {"XD_FILES": json.dumps([str(f) for f in fs]), "XD_LIB": str(lib)},
                             out / "me-checks.result.json")
        except NewError as e:
            raise MeCheckError(str(e)) from None
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
            configs = sorted({c for k in kids.values() for c in meassemblies.cad._list(k.get("configs") or "")}) or [""]
            joined = {tuple(sorted(j)) for j in a.get("joined") or []}
            for o in a.get("overlaps") or []:
                pair = tuple(sorted((o["a"], o["b"])))
                tol = JOINED_TOL if pair in joined else OVERLAP_TOL
                if o["volume"] <= tol:
                    continue
                for c in configs:
                    here = [n for n in pair if _present(kids.get(n), c)]
                    if len(here) < 2:
                        continue
                    where = f" (variant {c})" if c else ""
                    j = ", joined" if pair in joined else ""
                    out.append((_folder(cfg, rel), _finding(
                        check, f"{rel}{where}: {pair[0]} and {pair[1]} overlap by {o['volume']:.4g} mm³ "
                               f"(tolerance {tol:g} mm³{j})", list(pair))))
    elif check == "CK-F18":
        for a in res.get("assemblies") or []:
            rel = _rel(cfg, a["doc"])
            for k in a.get("children") or []:
                if k.get("kind") == "board":
                    out.append((_folder(cfg, rel), _finding(
                        check, f"{rel}: board model {k['name']} ({k.get('id')}): its SYS-IF space budget is not "
                               f"checked yet; the budget's form comes from the co-design task 5.28", [k["name"]])))
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
    for folder, es in sorted(mine.items()):
        for e in es:
            if not e.hits:
                total.problems.append(f"{folder}/{ercdrc.ACCEPTED} {e.label()} matches no {check} finding; remove it")
    return total
