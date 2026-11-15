"""`curatrix docs <repo|full>`: the zdocs build of a repo's registry (D25, D35, D64c).

Output: build/<area>/docs/ (cmake binary dir); HTML, needs.json and objects.inv per document under
build/<area>/docs/deploy/html/<doc-id>/ (doc-architecture.md §5). `full` builds the manifest repo's
registry into build/full/.

Strict (D64c): with a zdocs that knows ZDOCS_STRICT (zdocs PR #36) curatrix passes
-DZDOCS_STRICT=ON; otherwise -W --keep-going and `ninja -k 0`, so every document reports.
"""
from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

from curatrix import limits


@dataclass
class DocsResult:
    ok: bool
    area: str
    build_dir: Path
    log: Path
    summary: str
    strict_mode: str


def zdocs_dir(ws) -> Path | None:
    for p in (ws.root / "tools" / "zdocs",):
        if (p / "cmake").is_dir():
            return p
    return None


def supports_strict(ws) -> bool:
    z = zdocs_dir(ws)
    if not z:
        return False
    return any("ZDOCS_STRICT" in f.read_text(errors="replace") for f in (z / "cmake").glob("*.cmake"))


def build(ws, repo_dir: Path, area: str, log=print) -> DocsResult:
    src = repo_dir / "docs"
    out = ws.build(area) / "docs"
    out.mkdir(parents=True, exist_ok=True)
    logf = ws.build(area) / "docs-build.log"
    if not (src / "CMakeLists.txt").is_file():
        return DocsResult(False, area, out, logf, f"{ws.rel(src)}/CMakeLists.txt not found", "-")
    strict = supports_strict(ws)
    mode = "ZDOCS_STRICT=ON" if strict else "-W --keep-going, ninja -k 0"
    cfg_cmd = ["cmake", "-S", str(src), "-B", str(out), "-GNinja", f"-DUSER_CACHE_DIR={ws.build(area) / 'cache'}"]
    cfg_cmd += ["-DZDOCS_STRICT=ON"] if strict else ["-DZDOCS_SPHINXOPTS_EXTRA=-W;--keep-going"]
    with open(logf, "w") as fh:
        fh.write(f"$ {' '.join(cfg_cmd)}\n")
        fh.flush()
        r = limits.run(cfg_cmd, "docs", ws, stdout=fh, stderr=subprocess.STDOUT)
        if r.returncode:
            return DocsResult(False, area, out, logf, f"cmake configure failed ({r.returncode}); see {ws.rel(logf)}", mode)
        bcmd = ["cmake", "--build", str(out), "--", "-k", "0"]
        fh.write(f"\n$ {' '.join(bcmd)}\n")
        fh.flush()
        r = limits.run(bcmd, "docs", ws, stdout=fh, stderr=subprocess.STDOUT)
    text = logf.read_text(errors="replace")
    lines = [ln.replace(str(ws.root) + "/", "") for ln in text.splitlines()
             if re.search(r"WARNING|ERROR|error:|doccheck|FAILED: ", ln) and not ln.startswith("cd ")]
    summary = "\n".join(lines[-60:])
    if r.returncode in (124, 137):
        summary += f"\n[curatrix] docs build stopped: {limits.explain_rc(r.returncode)}"
    return DocsResult(r.returncode == 0, area, out, logf, summary, mode)


def index_html(ws, area: str) -> Path | None:
    html = ws.build(area) / "docs" / "deploy" / "html"
    for cand in (html / "index.html", *sorted(html.glob("*/index.html"))):
        if cand.exists():
            return cand
    return None
