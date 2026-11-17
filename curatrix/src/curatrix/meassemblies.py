"""FreeCAD assemblies of an ME repo: the folder rule, the 1:1 with the ME model and the link counts
(task 5.23; XD-ADR-0128, XD-ADR-0137, XD-ADR-0138; checks CK-F14, CK-F15). Plain Python, no FreeCAD:
it reads ``Document.xml`` of the ``.FCStd`` files (``cad.freecad_trace``).

Layout (XD-ADR-0137, file name of the skeleton as proposed in XD-ADR-0146): each top-level
assembly is a folder ``assemblies/<name>/`` with its top document ``<name>.FCStd`` and the skeleton
``<name>-skeleton.FCStd`` (a name unique in the repo, because FreeCAD names a document after its
file and cross-document expressions name the document); its own parts and sub-assembly documents
sit in the folder too, shared parts in ``parts/``.

The 1:1 (CK-F14): an assembly def of the ME model (a def that specializes ``XdDomain::Assembly``
directly, with an ``ME-ASM`` short name) has exactly one FreeCAD document with an object whose
``TraceID`` is that ID, named after the def (``CanaryAssembly`` -> ``canary-assembly.FCStd``); a
top-level def (one that no assembly def uses, neither in the ME model nor through the system
model's usages, XD-ADR-0138) has its folder. No document refers to a top
document except through the assembly's own links (no document cycles).

The link counts (CK-F15): in the document of an assembly def, the FreeCAD links (``App::Link``)
to each part or sub-assembly equal its usages: the usages in the ME model (``part x : T;``, with
multiplicity) for internal elements, and the usages of the system model for the system blocks the
assembly realizes, counted for the ME def that realizes each used block. A link names what it
links by the ``TraceID`` of its target object (``ME-PART`` or ``ME-ASM``); links to the skeleton
are not counted. Per configuration: a link with ``Configs`` counts only for those configurations;
the model usages are not filtered by configuration yet. A system usage of a block that no ME def
realizes is not counted (it may be an EE or SW block); a usage the ME model repeats from the system
model, a block realized by two ME defs and a multiplicity that is not one number are findings.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from curatrix import cad, ids as idmod
from curatrix.eeprojects import kebab

ASSEMBLY_DEF = "XdDomain::Assembly"
VARIANT_DEF = "XdDomain::DomainVariant"
SKELETON_SUFFIX = "-skeleton.FCStd"


def skeleton_name(asm_folder: str) -> str:
    """``canary-assembly`` -> ``canary-assembly-skeleton.FCStd``."""
    return asm_folder + SKELETON_SUFFIX
LINK_TYPES = ("App::Link", "App::LinkElement")
UNREAD_FIELDS = ("Realizes", "Conforms", "Satisfies", "PartOf")


@dataclass
class Doc:
    rel: str                                   # path relative to the repo
    sem: dict                                  # cad.freecad_trace
    ids: dict[str, str] = field(default_factory=dict)    # object name -> TraceID

    @property
    def asm_ids(self) -> list[str]:
        return sorted({t for t in self.ids.values() if idmod.kind_of(t) == "ME-ASM"})


def documents(cfg) -> dict[str, Doc]:
    """Every FreeCAD document of the repo (checks.yaml ``cad.freecad``), by repo-relative path."""
    out = {}
    s = cfg.section("cad") or {}
    for fc in cfg.globs(s.get("freecad") or []):
        rel = str(fc.resolve().relative_to(cfg.repo.resolve()))
        sem = cad.freecad_trace(fc, rel)
        d = Doc(rel, sem)
        for name, o in sem["objects"].items():
            tid = str((o.get("trace") or {}).get("TraceID") or "").strip()
            if tid:
                d.ids[name] = tid
        out[rel] = d
    return out


def top_folders(cfg) -> list[Path]:
    root = cfg.repo / "assemblies"
    return sorted(d for d in root.iterdir() if d.is_dir()) if root.is_dir() else []


# ------------------------------------------------------------------ the ME model side
def model_defs(m) -> tuple[dict[str, dict], list[str]]:
    """(assembly defs by ME-ASM ID, findings) of an ME model."""
    asms, findings = {}, []
    for p in m.user():
        if p.get("@type") != "PartDefinition":
            continue
        sup = {s.get("qualifiedName") or "" for s in m.supers(p)}
        if ASSEMBLY_DEF not in sup or VARIANT_DEF in sup:
            continue
        sid = p.get("declaredShortName") or ""
        if idmod.kind_of(sid) != "ME-ASM":
            findings.append(f"model {m.qn(p)}: an assembly def ({ASSEMBLY_DEF}) without an ME-ASM ID (short name)")
            continue
        asms[sid] = p
    return asms, findings


def _multiplicity(m, u) -> int | None:
    """The multiplicity of a usage: ``[n]`` or ``[n..n]`` gives n, none gives 1; a range or ``*``
    gives None (no fixed number of links)."""
    for _, x in m.owned(u):
        if x.get("@type") == "MultiplicityRange":
            bounds = [v for _, v in m.owned(x)]
            vals = [v.get("value") for v in bounds if v.get("@type") == "LiteralInteger"]
            if len(vals) != len(bounds) or not vals or len(set(vals)) != 1:
                return None
            return int(vals[0])
    return 1


def usages(m, p) -> list[tuple[str, dict, int | None]]:
    """(usage name, its definition, multiplicity) of the part usages a def owns directly."""
    out = []
    for _, u in m.owned(p):
        if u.get("@type") != "PartUsage":
            continue
        types = m.declared_types(u) or [x for x in (m.get(d) for d in u.get("definition") or []) if x]
        for t in types[:1]:
            out.append((u.get("name") or "", t, _multiplicity(m, u)))
    return out


def realizers(m) -> tuple[dict[str, str], list[str]]:
    """System def qualified name -> the ID of the ME def that specializes it (domain variants left
    out), and findings for a system def realized by more than one ME def."""
    from curatrix import model as modelmod
    out: dict[str, list[str]] = {}
    for p in m.user():
        pid = modelmod.element_id(m, p)
        if not pid or p.get("@type") != "PartDefinition":
            continue
        sups = m.supers(p)
        if any(s.get("qualifiedName") == VARIANT_DEF for s in sups):
            continue
        for s in sups:
            q = s.get("qualifiedName") or ""
            if s.get("isLibraryElement") and q and not q.startswith("XdDomain::"):
                out.setdefault(q, []).append(pid)
    findings = [f"model: the system block {q} is realized by {len(ids)} ME defs ({', '.join(sorted(ids))}); "
                f"exactly one (XD-ADR-0130)" for q, ids in sorted(out.items()) if len(set(ids)) > 1]
    return {q: sorted(ids)[0] for q, ids in out.items()}, findings


def system_usages(m, upstream: list, asm: dict, realizer: dict[str, str]) -> list[tuple[str, str, int | None]]:
    """(usage qualified name, ME ID realizing its block, multiplicity) of the usages that syseng owns
    inside the system blocks `asm` realizes; usages of blocks no ME def realizes are left out."""
    out = []
    for s in m.supers(asm):
        qn = s.get("qualifiedName") or ""
        for up in upstream:
            sp = next((x for x in up.user() if x.get("qualifiedName") == qn), None)
            if sp is None:
                continue
            for name, t, n in usages(up, sp):
                tq = t.get("qualifiedName") or ""
                if tq in realizer:
                    out.append((f"{qn}::{name}", realizer[tq], n))
    return out


def expected_counts(m, upstream: list, asm: dict) -> tuple[dict[str, int], list[str]]:
    """ID -> expected number of links in the document of `asm` (XD-ADR-0138), and findings."""
    from curatrix import model as modelmod
    want: dict[str, int] = {}
    realizer, findings = realizers(m)
    sys_uses = system_usages(m, upstream, asm, realizer)
    sys_ids = {tid for _, tid, _ in sys_uses}
    for name, t, n in usages(m, asm):
        tid = modelmod.element_id(m, t)
        where = f"model {m.qn(asm)}::{name}"
        if tid is None:
            findings.append(f"{where}: its def {m.qn(t)} has no ME-PART or ME-ASM ID, so its FreeCAD links cannot be counted")
            continue
        if tid in sys_ids:
            findings.append(f"{where}: repeats a usage the system model owns ({tid}); the domain model refers to it and "
                            f"does not repeat it (XD-ADR-0138)")
            continue
        if n is None:
            findings.append(f"{where}: the multiplicity is not one number; the number of FreeCAD links cannot be checked")
            continue
        want[tid] = want.get(tid, 0) + n
    for qn, tid, n in sys_uses:
        if n is None:
            findings.append(f"system model {qn}: the multiplicity is not one number; the number of FreeCAD links "
                            f"cannot be checked")
            continue
        want[tid] = want.get(tid, 0) + n
    return want, findings


# ------------------------------------------------------------------ CK-F14
def _resolve(src_rel: str, file: str) -> str:
    """A link's target file (relative to the linking document) as a repo-relative path."""
    parts: list[str] = []
    for x in (PurePosixPath(src_rel).parent / file).parts:
        if x == "..":
            if parts:
                parts.pop()
        elif x != ".":
            parts.append(x)
    return "/".join(parts)


def xlinks(doc: Doc) -> list[tuple[str, str, str, str]]:
    """(object, property, target file (repo-relative), target object) of every link to another file."""
    out = []
    for name, o in doc.sem["objects"].items():
        for prop, targets in (o.get("links") or {}).items():
            for t in targets:
                if t.get("file"):
                    out.append((name, prop, _resolve(doc.rel, t["file"]), t.get("object") or ""))
    return out


def one_to_one(cfg, m, docs: dict[str, Doc] | None = None, upstream: list | None = None) -> list[str]:
    """CK-F14 (XD-ADR-0128, XD-ADR-0137)."""
    asms, findings = model_defs(m)
    docs = documents(cfg) if docs is None else docs
    # a def used by an assembly def, in the ME model or through the system model, is a sub-assembly
    used_as_sub = {t["@id"] for p in asms.values() for _, t, _ in usages(m, p)}
    realizer, _ = realizers(m)
    by_id_el = {aid: p["@id"] for aid, p in asms.items()}
    for p in asms.values():
        for _, tid, _ in system_usages(m, upstream or [], p, realizer):
            if tid in by_id_el:
                used_as_sub.add(by_id_el[tid])
    tops = set()
    for d in top_folders(cfg):
        rel = d.relative_to(cfg.repo)
        top = d / f"{d.name}.FCStd"
        if not top.is_file():
            findings.append(f"{rel}/: an assembly folder without its top document {d.name}.FCStd")
        else:
            tops.add(str(top.relative_to(cfg.repo)))
        if not (d / skeleton_name(d.name)).is_file():
            findings.append(f"{rel}/: no {skeleton_name(d.name)} (parameters and master sketch, XD-ADR-0137); "
                            f"`curatrix new asm` makes it")
    by_id: dict[str, list[str]] = {}
    for rel, d in sorted(docs.items()):
        ids = d.asm_ids
        objs = [n for n, t in d.ids.items() if idmod.kind_of(t) == "ME-ASM"]
        for n in objs:
            tr = d.sem["objects"][n].get("trace") or {}
            unread = [f for f in UNREAD_FIELDS if str(tr.get(f) or "").strip()]
            if unread:
                findings.append(f"{rel}: {n} has {', '.join(unread)} next to its ME-ASM TraceID: links come from "
                                f"the model (XD-ADR-0128); remove {'it' if len(unread) == 1 else 'them'}")
        if len(objs) > 1:
            findings.append(f"{rel}: {len(objs)} objects carry an ME-ASM TraceID ({', '.join(sorted(objs))}); "
                            f"a document names exactly one assembly def")
        if rel in tops and not ids:
            findings.append(f"{rel}: a top document without an ME-ASM TraceID; set TraceID on its assembly object "
                            f"to the ID of its assembly def")
        for tid in ids:
            if tid not in asms:
                findings.append(f"{rel}: TraceID {tid} names no assembly def of the ME model ({ASSEMBLY_DEF})")
                continue
            by_id.setdefault(tid, []).append(rel)
            want = kebab(asms[tid].get("name") or "")
            if Path(rel).stem != want:
                findings.append(f"{rel}: the assembly def {asms[tid].get('name')} ({tid}) gives the file name "
                                f"{want}.FCStd")
            if asms[tid]["@id"] not in used_as_sub and rel != f"assemblies/{want}/{want}.FCStd":
                findings.append(f"{rel}: {tid} is a top-level assembly; its document is assemblies/{want}/{want}.FCStd")
    for aid, p in sorted(asms.items()):
        found = by_id.get(aid, [])
        if not found:
            findings.append(f"model {m.qn(p)} ({aid}): no FreeCAD document; create it with "
                            f"`curatrix new asm {p.get('name')} --repo {cfg.repo.name}`")
        elif len(found) > 1:
            findings.append(f"model {m.qn(p)} ({aid}): {len(found)} documents name it ({', '.join(found)}); exactly one")
    # no references to a top document from outside it (document cycles, XD-ADR-0137)
    for rel, d in sorted(docs.items()):
        for obj, prop, target, _ in xlinks(d):
            if target in tops and target != rel:
                findings.append(f"{rel}: {obj}.{prop} refers to the top document {target}; parts and sub-assemblies "
                                f"refer only to the skeleton (XD-ADR-0137)")
    return findings


# ------------------------------------------------------------------ CK-F15
def link_counts(cfg, m, upstream: list, docs: dict[str, Doc] | None = None) -> list[str]:
    """CK-F15 (XD-ADR-0138): FreeCAD links per part or sub-assembly vs the usages, per configuration."""
    asms, findings = model_defs(m)
    docs = documents(cfg) if docs is None else docs
    for rel, d in sorted(docs.items()):
        ids = [t for t in d.asm_ids if t in asms]
        if len(ids) != 1:
            continue                                  # CK-F14 reports it
        aid = ids[0]
        want, f = expected_counts(m, upstream, asms[aid])
        findings += [f"{rel}: {x}" for x in f]
        have: list[tuple[str, list[str]]] = []        # (target ID, configs) per link
        for name, o in d.sem["objects"].items():
            if o.get("type") not in LINK_TYPES:
                continue
            targets = (o.get("links") or {}).get("LinkedObject") or []
            if not targets:
                findings.append(f"{rel}: link {name} has no target")
                continue
            t = targets[0]
            tfile = _resolve(rel, t["file"]) if t.get("file") else rel
            if PurePosixPath(tfile).name.endswith(SKELETON_SUFFIX):
                continue
            target = docs.get(tfile)
            if target is None:
                findings.append(f"{rel}: link {name} points to {tfile}, which is not a FreeCAD file of the repo")
                continue
            tid = target.ids.get(t.get("object") or "")
            if not tid:
                findings.append(f"{rel}: link {name} points to {tfile}#{t.get('object')}, which has no TraceID")
                continue
            cfgs = cad._list(str((o.get("trace") or {}).get("Configs") or ""))
            have.append((tid, cfgs))
        configs = sorted({c for _, cs in have for c in cs}) or [""]
        for c in configs:
            got: dict[str, int] = {}
            for tid, cs in have:
                if not cs or not c or c in cs:
                    got[tid] = got.get(tid, 0) + 1
            where = f"{rel}" + (f" ({c})" if c else "")
            for tid in sorted(set(want) | set(got)):
                if want.get(tid, 0) != got.get(tid, 0):
                    findings.append(f"{where}: {got.get(tid, 0)} FreeCAD link(s) to {tid}, the model has "
                                    f"{want.get(tid, 0)} usage(s) in {asms[aid].get('name')} ({aid})")
    return findings
