"""KiCad projects of an EE repo: discovery, the folder rule and the 1:1 with the EE model
(task 5.17; XD-ADR-0128, XD-ADR-0135; checks CK-F6, CK-F7). Plain Python, no KiCad.

A project is found by its ``.kicad_pro`` (checks.yaml ``cad.projects``, e.g.
``["pcba/*/*.kicad_pro", "proto/*/*.kicad_pro"]``); its root sheet is the ``.kicad_sch`` of the
same name. Each project sits in its own folder ``<kind>/<name>/`` with ``<name>.kicad_pro``.

The 1:1 (CK-F7): each board def of the EE model (a def that specializes ``XdDomain::Pcba``
directly) has exactly one ``pcba/`` project whose text variable ``TraceID`` is the def's
``EE-PCBA`` ID, in the folder named after the def (``JointController`` -> ``joint-controller``);
every ``pcba/`` project names exactly one board def; external parts (``XdDomain::ExternalPart``)
have no project.
"""
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from curatrix import ids as idmod

# files that belong to a KiCad project (library files in lib/ are not project files)
PROJECT_SUFFIXES = (".kicad_pro", ".kicad_sch", ".kicad_pcb", ".kicad_prl", ".kicad_jobset", ".kicad_dru")
PROJECT_NAMES = ("sym-lib-table", "fp-lib-table")
PCBA_DEF = "XdDomain::Pcba"
EXTERNAL_DEF = "XdDomain::ExternalPart"
VARIANT_DEF = "XdDomain::DomainVariant"      # a board variant specializes its board def (XD-ADR-0136)
UNREAD_FIELDS = ("Realizes", "Conforms", "Satisfies", "PartOf", "Configs", "Status")


@dataclass
class Project:
    name: str            # folder name = file stem
    kind: str            # the folder above: pcba | proto | ...
    folder: Path
    pro: Path
    sch: Path            # the root sheet

    def variables(self) -> dict:
        try:
            return json.loads(self.pro.read_text(encoding="utf-8")).get("text_variables") or {}
        except (OSError, ValueError):
            return {}


def kebab(name: str) -> str:
    """Folder name of a model element: ``JointController`` -> ``joint-controller``."""
    s = re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", "-", name)
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def patterns(cfg) -> list[str]:
    return list((cfg.section("cad") or {}).get("projects") or [])


def discover(cfg) -> list[Project]:
    """The projects of a repo, by its ``cad.projects`` globs (sorted)."""
    out = []
    for pro in cfg.globs(patterns(cfg)):
        if pro.is_file():
            out.append(Project(pro.stem, pro.parent.parent.name, pro.parent, pro, pro.with_suffix(".kicad_sch")))
    return out


def root_sheets(cfg) -> list[Path]:
    """Root schematics to read: ``cad.kicad`` globs plus the root sheets of ``cad.projects``."""
    s = cfg.section("cad") or {}
    seen, out = set(), []
    for p in [*cfg.globs(s.get("kicad") or []), *(pr.sch for pr in discover(cfg) if pr.sch.is_file())]:
        if p.resolve() not in seen:
            seen.add(p.resolve())
            out.append(p)
    return out


def _repo_files(repo: Path, ws=None) -> list[str]:
    from curatrix import limits
    try:
        p = limits.run(["git", "-C", str(repo), "ls-files", "-co", "--exclude-standard"], "git", ws,
                       capture_output=True, text=True)
        if p.returncode == 0:
            return p.stdout.splitlines()
    except (OSError, subprocess.SubprocessError):
        pass
    return [str(f.relative_to(repo)) for f in repo.rglob("*") if f.is_file() and ".git" not in f.parts]


def is_project_file(rel: str) -> bool:
    name = rel.rsplit("/", 1)[-1]
    return name.endswith(PROJECT_SUFFIXES) or name in PROJECT_NAMES


def folder_findings(cfg) -> list[str]:
    """CK-F6: one ``.kicad_pro`` per project folder, named like the folder, with its root sheet;
    no KiCad project files outside these folders."""
    repo = cfg.repo
    findings: list[str] = []
    good: list[Path] = []
    pats = patterns(cfg)
    if not pats:
        return ["checks.yaml cad.projects is empty: name the project globs, e.g. pcba/*/*.kicad_pro"]
    folders: set[Path] = set()
    for pat in pats:
        parent = str(Path(pat).parent)                    # pcba/*
        for d in cfg.globs([parent]):
            if d.is_dir():
                folders.add(d.resolve())
    for d in sorted(folders):
        rel = d.relative_to(repo.resolve())
        pros = sorted(d.glob("*.kicad_pro"))
        if not pros:
            findings.append(f"{rel}/: a project folder without a .kicad_pro (expected {rel}/{d.name}.kicad_pro)")
            continue
        if len(pros) > 1:
            findings.append(f"{rel}/: {len(pros)} projects ({', '.join(p.name for p in pros)}); one project per folder")
        named = [p for p in pros if p.stem == d.name]
        for p in pros:
            if p.stem != d.name:
                findings.append(f"{rel}/{p.name}: the project file is named after its folder: {d.name}.kicad_pro")
        if named:
            if not named[0].with_suffix(".kicad_sch").is_file():
                findings.append(f"{rel}/{d.name}.kicad_pro: its root sheet {d.name}.kicad_sch is missing")
            if len(pros) == 1:
                good.append(d)
    for rel in sorted(_repo_files(repo)):
        if not is_project_file(rel):
            continue
        p = (repo / rel).resolve()
        if not any(g == p.parent or g in p.parents for g in good):
            findings.append(f"{rel}: a KiCad project file outside a project folder ({', '.join(pats)})")
    return findings


# ------------------------------------------------------------------ the EE model side
def _direct_supers(m, p) -> set[str]:
    return {s.get("qualifiedName") or "" for s in m.supers(p)}


def model_defs(m) -> tuple[dict[str, dict], dict[str, dict], list[str]]:
    """(board defs by ID, external part defs by ID, findings) of an EE model."""
    boards, externals, findings = {}, {}, []
    for p in m.user():
        if p.get("@type") != "PartDefinition":
            continue
        sup = _direct_supers(m, p)
        if VARIANT_DEF in sup:          # defensive: a variant specializes its board def, not Pcba directly
            continue
        for qn, into in ((PCBA_DEF, boards), (EXTERNAL_DEF, externals)):
            if qn not in sup:
                continue
            sid = p.get("declaredShortName") or ""
            if qn == PCBA_DEF and idmod.kind_of(sid) != "EE-PCBA":
                findings.append(f"model {m.qn(p)}: a board def ({PCBA_DEF}) without an EE-PCBA ID (short name)")
                continue
            into[sid or m.qn(p)] = p
    return boards, externals, findings


def one_to_one(cfg, m) -> list[str]:
    """CK-F7: board defs <-> pcba/ projects (XD-ADR-0128); external parts have none (XD-ADR-0135)."""
    boards, externals, findings = model_defs(m)
    by_id: dict[str, list[Project]] = {}
    for pr in discover(cfg):
        rel = pr.pro.resolve().relative_to(cfg.repo.resolve())
        tv = pr.variables()
        tid = (tv.get("TraceID") or "").strip()
        for f in UNREAD_FIELDS:
            if (tv.get(f) or "").strip():
                findings.append(f"{rel}: text variable {f} on a project: links come from the model "
                                f"(XD-ADR-0128); remove it")
        if pr.kind != "pcba":
            continue                     # proto/: 1:1 with a prototype block, not yet in the EE model
        if not tid:
            findings.append(f"{rel}: no TraceID text variable; set it to the EE-PCBA ID of its board def")
            continue
        if tid in externals:
            findings.append(f"{rel}: TraceID {tid} is an external part ({m.qn(externals[tid])}); external parts have "
                            f"no KiCad project (XD-ADR-0135)")
            continue
        if tid not in boards:
            findings.append(f"{rel}: TraceID {tid} names no board def of the EE model ({PCBA_DEF})")
            continue
        by_id.setdefault(tid, []).append(pr)
        want = kebab(boards[tid].get("name") or "")
        if want and pr.name != want:
            findings.append(f"{rel}: the board def {boards[tid].get('name')} ({tid}) gives the folder name "
                            f"pcba/{want}/")
    for bid, p in sorted(boards.items()):
        prs = by_id.get(bid, [])
        if not prs:
            findings.append(f"model {m.qn(p)} ({bid}): no KiCad project; create it with "
                            f"`curatrix new pcba {p.get('name')} --repo {cfg.repo.name}`")
        elif len(prs) > 1:
            findings.append(f"model {m.qn(p)} ({bid}): {len(prs)} projects name it "
                            f"({', '.join(str(x.pro.relative_to(cfg.repo)) for x in prs)}); exactly one")
    return findings
