"""The document layout of a repo (CK-A7; owner decision Q8 and finding 15 of tiacsys/xdmod#69).

A repo's own documents sit in the folder of its docs registry (``docs/``): the V-model documents
directly (``docs/ee-req/``, ``docs/ee-design/``, ...), the per-deliverable documents in one sub-folder
per kind: ``docs/pcbas/pcba-<board>/``, ``docs/assemblies/asm-<assembly>/``,
``docs/firmware/fw-<name>/``, ``docs/protos/proto-<setup>/`` (``newpcba.SUBFOLDERS``). The registry entry of a document in a
sub-folder names it with ``doc_dir: pcbas/pcba-<board>``; its deploy path stays ``html/<id>/``.
Every cable of a repo is in one document ``harnesses`` (no ``harness-<cable>`` documents).

``findings(cfg)`` reports, in plain Python:

* an own registry entry whose folder is missing, or has no ``conf.py`` (Sphinx) or ``Doxyfile.in``
  (Doxygen): zdocs would fail;
* a folder below ``docs/`` with a ``conf.py`` that no registry entry names: it is never built;
* a per-deliverable document outside its sub-folder;
* a ``harness-<cable>`` document, and harnesses (``cad.harnesses``) without a ``harnesses`` document.
"""
from __future__ import annotations

from pathlib import Path

import yaml

from curatrix.newpcba import SUBFOLDERS, doc_folder, is_own


def findings(cfg) -> list[str]:
    reg = cfg.docs_registry
    if reg is None:
        return []
    if not reg.is_file():
        return [f"{_rel(cfg, reg)} missing (checks.yaml docs.registry)"]
    try:
        docs = (yaml.safe_load(reg.read_text(encoding="utf-8")) or {}).get("documents") or {}
    except yaml.YAMLError as e:
        return [f"{_rel(cfg, reg)}: not YAML ({str(e).splitlines()[0]})"]
    base = reg.parent
    out: list[str] = []
    own_dirs: dict[Path, str] = {}
    for did, e in docs.items():
        if not is_own(e):
            continue
        kind = (e or {}).get("kind", "sphinx")
        if kind not in ("sphinx", "doxygen"):
            continue
        rel = str((e or {}).get("doc_dir") or did)
        folder = (base / rel).resolve()
        own_dirs[folder] = did
        marker = "conf.py" if kind == "sphinx" else "Doxyfile.in"
        if not (folder / marker).is_file():
            out.append(f"{did}: {_rel(cfg, folder)}/{marker} missing (registry entry without its document)")
        want = doc_folder(did)
        if rel.rstrip("/") != want:
            sub = want.split("/", 1)[0]
            out.append(f"{did}: in {_rel(cfg, folder)}/, not in {_rel(cfg, base / want)}/: per-deliverable "
                       f"documents sit in docs/{sub}/ (doc_dir: {want}; tiacsys/xdmod#69 Q8)"
                       if "/" in want else
                       f"{did}: doc_dir {rel} for a document that belongs directly in {_rel(cfg, base)}/{did}/")
        if did.startswith("harness-"):
            out.append(f"{did}: one document `harnesses` holds every cable of the repo (xd-harnesses; "
                       f"tiacsys/xdmod#69 finding 15), not one document per cable")
    for conf in sorted(base.rglob("conf.py")):
        d = conf.parent.resolve()
        if d in own_dirs or any(o in d.parents for o in own_dirs):
            continue
        out.append(f"{_rel(cfg, conf)}: a document folder that no entry of {_rel(cfg, reg)} names: never built")
    from curatrix import harness
    if harness.patterns(cfg) and harness.discover(cfg) and "harnesses" not in docs:
        out.append(f"{len(harness.discover(cfg))} harness(es) and no `harnesses` document in {_rel(cfg, reg)} "
                   f"(one document for every cable, `.. xd-harnesses::`)")
    return out


def _rel(cfg, p: Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(cfg.repo.resolve().parent))
    except ValueError:
        return str(p)


__all__ = ["findings", "SUBFOLDERS"]
