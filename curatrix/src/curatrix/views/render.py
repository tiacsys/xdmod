"""Rendering views to .drawio.svg (needs node, elkjs, Firefox and the drawio viewer: local only)."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from curatrix import limits
from curatrix.model import Model
from curatrix.views import (ViewError, compose, discover, file_name, graph, normalize_xml, positions, read_svg,
                            run_elk, to_elk, to_mxfile, HERE)


def firefox() -> str:
    return shutil.which("firefox") or "/usr/bin/firefox"


def render_batch(ws, items: list[tuple[str, str]], work: Path) -> list[str]:
    """[(name, mxfile_xml)] -> [svg] with one headless Firefox start."""
    work.mkdir(parents=True, exist_ok=True)
    args = []
    for i, (name, xml) in enumerate(items):
        src, dst = work / f"{i}.xml", work / f"{i}.svg"
        src.write_text(xml)
        if dst.exists():
            dst.unlink()
        args += [str(src), str(dst)]
    viewer = ws.opt / "drawio-viewer" / "viewer-static.min.js"
    if not viewer.exists():
        raise ViewError(f"drawio viewer missing ({viewer}); run `curatrix update`")
    r = limits.run(["node", str(HERE / "render_svg.mjs"), str(ws.opt / "node"), str(viewer), firefox(),
                    str(work / "ffprofile"), *args], "firefox", ws, capture_output=True, text=True)
    if r.returncode:
        raise ViewError(f"SVG render failed ({r.returncode} {limits.explain_rc(r.returncode)}): {r.stderr[-1500:]}")
    return [(work / f"{i}.svg").read_text() for i in range(len(items))]


def build(ws, model: Model, views_dir: Path, out_dir: Path, only: list[str] | None = None, log=print) -> list[str]:
    """Generate every view of the model into views_dir; the graph JSON goes to out_dir (for agents)."""
    errors = []
    todo = []
    for v in discover(model):
        if only and v.name not in only:
            continue
        try:
            g = graph(model, v)
        except ViewError as e:
            errors.append(str(e))
            continue
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / f"{v.name}.json").write_text(json.dumps(g, indent=1, sort_keys=True) + "\n")
        laid = run_elk(ws, to_elk(g))
        todo.append((v, to_mxfile(g, positions(laid))))
    if todo:
        svgs = render_batch(ws, [(v.name, x) for v, x in todo], out_dir / "_render")
        views_dir.mkdir(parents=True, exist_ok=True)
        for (v, xml), svg in zip(todo, svgs):
            dst = views_dir / file_name(v)
            text = compose(svg, xml, v.name)
            changed = not dst.exists() or dst.read_text() != text
            dst.write_text(text)
            log(f"  {'wrote' if changed else 'unchanged'} {ws.rel(dst)}")
    return errors


def normalize(ws, files: list[Path], work: Path, check_only: bool = False, log=print) -> list[str]:
    """Rewrite editor-saved .drawio.svg files into the normalized form (decompressed, editor
    attributes dropped, cells sorted, picture re-rendered, hash set)."""
    errs, todo = [], []
    for f in files:
        content, _, _ = read_svg(f)
        if content is None:
            errs.append(f"{f}: no embedded diagram")
            continue
        todo.append((f, normalize_xml(content)))
    if not todo:
        return errs
    svgs = render_batch(ws, [(f.stem, x) for f, x in todo], work)
    for (f, xml), svg in zip(todo, svgs):
        name = f.name[: -len(".drawio.svg")] if f.name.endswith(".drawio.svg") else f.stem
        text = compose(svg, xml, name)
        if f.read_text() != text:
            if check_only:
                errs.append(f"{f}: not normalized")
            else:
                f.write_text(text)
                log(f"  normalized {ws.rel(f)}")
    return errs
