"""`curatrix hook pre-commit`: fast checks on the staged files (D100; checks.md "pre-commit").

* CK-C1  placeholder IDs (warning: `curatrix ids fix` replaces them; PR CI rejects them)
* CK-H1  .FCStd saved compressed (error); drawio diagram compressed (error)
* CK-D3  .drawio.svg whose picture is stale against its embedded diagram (error: run
         `curatrix views normalize <file>`, which re-renders it; needs Firefox)
* .FCStd changed while its semantic JSON (cad.freecad_json in checks.yaml) did not (warning,
  "save without change", freecad-storage.md §5)
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from curatrix import cad, ids as idmod, views as viewsmod


def staged(repo: Path) -> list[Path]:
    out = subprocess.run(["git", "-C", str(repo), "diff", "--cached", "--name-only", "--diff-filter=ACM"],
                         capture_output=True, text=True, timeout=60).stdout.splitlines()
    return [repo / f for f in out]


def pre_commit(repo: Path) -> int:
    files = staged(repo)
    errors, warnings = [], []
    text_files = [f for f in files if f.suffix in idmod.TEXT_SUFFIXES and f.name not in idmod.SKIP_NAMES]
    warnings += idmod.check_placeholders(text_files, repo)
    for f in files:
        rel = f.relative_to(repo)
        if f.suffix == ".FCStd":
            bad = cad.freecad_compressed(f)
            if bad:
                errors.append(f"{rel}: saved compressed ({bad[0]} ...); save with CompressionLevel 0 "
                              f"(open it with `curatrix launch freecad`)")
        if f.name.endswith(".drawio.svg"):
            try:
                content, stored, _ = viewsmod.read_svg(f)
            except viewsmod.ViewError as e:
                errors.append(str(e))
                continue
            if content is None:
                errors.append(f"{rel}: no embedded diagram")
            elif viewsmod.is_compressed(content):
                errors.append(f"{rel}: compressed diagram; run `curatrix views normalize {rel}`")
            elif stored != viewsmod.diagram_hash(content):
                errors.append(f"{rel}: not normalized / picture stale; run `curatrix views normalize {rel}`")
    fc = [f for f in files if f.suffix == ".FCStd"]
    if fc:
        gen_json = {f.relative_to(repo).as_posix() for f in files if f.suffix == ".json"}
        for f in fc:
            rel = f.relative_to(repo).as_posix()
            if not any(g.endswith(rel + ".json") for g in gen_json):
                warnings.append(f"{rel} changed but its semantic JSON is not staged "
                                f"(`curatrix gen freecad-json`; a save without change? freecad-storage.md §5)")
    for w in warnings:
        print(f"curatrix pre-commit: warning: {w}")
    for e in errors:
        print(f"curatrix pre-commit: ERROR: {e}")
    return 1 if errors else 0
