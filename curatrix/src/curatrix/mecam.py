"""`curatrix cam <repo> <asm>` for an ME repo: the design output of a top-level assembly (task 5.26;
ME-3, XD-ADR-0143, XD-ADR-0137, XD-ADR-0140) and the version-face rule (CK-F19).

``cam`` runs ``FreeCADCmd`` (``templates/freecad-asm/cam-asm.py``, ``freecad`` limits,
workspace-local config) once per variant into ``build/<area>/cam/<asm>/<version>/<asm>/<variant>/``:

* ``<asm>.step``: the links of the assembly that are there in the variant;
* ``parts/<part>.3mf`` and ``.stl`` per printed part (an object with a ``PrintProfile`` property),
  with the version embossed on its version mark (an LCS with ``Role = version-emboss``,
  ``TextSize``, ``MaxWidth``, optional ``EmbossDepth``) in the pinned font
  (``templates/freecad-asm/fonts/``); the export fails unless the result is exactly one valid
  solid; the print profile ``print/<PrintProfile>.ini`` is copied next to them
  (``print/<profile>.ini``), because a 3MF from FreeCAD carries no slicer settings;
* ``views/front|top|right|iso.svg``: TechDraw views computed in ``FreeCADCmd``, and the drawing
  ``drawing.svg`` and ``drawing.pdf``: a plain-Python view sheet, not a TechDraw page: no
  dimensions, no TechDraw template; front, top and right in first-angle projection, aligned, at one
  standard scale, the iso view, a frame and the title block (assembly, ID, full version, variant,
  date, scale, projection symbol, that note; ``PREVIEW`` unless a release). A full TechDraw page needs the GUI binary, which hangs offscreen when it waits for the
  views (FreeCAD spike §5, again in task 5.26), so this is the fallback of XD-ADR-0137;
* ``exploded.svg``: a TechDraw view of the exploded compound with explosion lines (spike §5
  fallback); the moves come from ``assemblies/<asm>/explode.yaml`` (``{link name: [dx, dy, dz]}``
  in mm), or automatically away from the assembly's centre;
* ``renderings/front|top|right|iso.png`` (task 5.30; method ``zbuffer``, the fallback when Blender
  is not there): shaded renderings, 1600 x 1200 px, without OpenGL (Coin3D offscreen snapshots and
  the Render workbench do not work headless, ``claude/notes/me-renderings-spike.md``). FreeCAD
  tessellates the present parts; ``cam-asm.py`` shades each facet flat (colour by BOM kind) and
  draws it into a numpy z-buffer, with the visible edges on top; FreeCAD's Qt writes the text and
  the PNG. Front, top and right share one scale, iso has its own; the scale (px/mm) is on the
  image and in ``cam.json``. Assembly, variant, full version and view are written on each image,
  and ``PREVIEW`` in red unless a release. A rendering without a drawn facet fails the run. With Blender on the machine (and without ``--no-blender``) the renderings come from
  Blender instead (method ``blender``, owner decision 2026-11-17): ``cam-asm.py`` writes the
  tessellated parts as glTF (``<variant>.scene.glb`` next to ``cam.json``, colour by BOM kind) and
  ``templates/blender/render-asm.py`` renders the same four views with Cycles on the CPU (fixed
  samples and seed, Freestyle edges, same size, names, scales and marking), through the isolated
  call of ``curatrix.blender``. Blender is not pinnable, so ``cam.json`` says which way was taken
  (``renderings.method``: ``blender`` or ``zbuffer``);
* ``bom.csv``: the flat BOM with totals, one row per part (sub-assemblies resolved);
* ``mass.json``: mass and center of gravity (``asmdoc.mass``, task 5.27);
* in the version folder, ``findings.json``: the findings of the ME checks CK-F4c, CK-F16, CK-F17
  for this assembly and the shared documents, with their acceptance state (``accepted.yaml``), for
  the assembly document (task 5.27).

Variants: the ``Configs`` of the links (presence, XD-ADR-0137; only a link's own property, as the ME
checks read it): one output per configuration a link names, and ``base`` with only the links
without ``Configs`` (every configuration no link names); without any ``Configs`` one variant
``all``. The model's configuration list and the parameter rows of a configuration table are not
read yet (the canary has none). A view without a visible edge fails the run.

Version (XD-ADR-0140): ``git describe --match '<asm>/*'`` (``cam.version``), preview unless an exact
tag on main with a clean tree; here "clean" covers the assembly folder and the shared ``parts/``,
``lib/`` and ``print/``. The full version goes into the title block, the short one (``vX.Y.Z``,
``P`` appended for a preview) onto the printed parts. The sources are never saved: their md5 before
and after the run must be equal, else the run fails. ``cam.json`` (``kind: assembly``) records it.
``current()`` gives the run the assembly document may show: the current commit and the same
``cam.tree_state`` of the assembly folder and the shared folders (CK-D10, task 5.27).
"""
from __future__ import annotations

import csv
import datetime as dt
import hashlib
import json
import math
import re
import shutil
from pathlib import Path

import yaml

from curatrix import asmdoc, cad, meassemblies
from curatrix import cam
from curatrix.cam import CamError, _git, version as git_version

SCRIPT = Path("templates") / "freecad-asm" / "cam-asm.py"
FONT = Path("templates") / "freecad-asm" / "fonts" / "DejaVuSansMono-Bold.ttf"
SHARED = ("parts", "lib", "print")
LCS_TYPES = ("Part::LocalCoordinateSystem", "PartDesign::CoordinateSystem")
VIEWS = ("front", "top", "right", "iso")
ALL, BASE = "all", "base"   # variants: no Configs anywhere; only the links without Configs
RENDER_METHOD = "zbuffer"   # FreeCAD tessellation, flat shading, numpy z-buffer; text and PNG by Qt (no OpenGL)
BLENDER_SCRIPT = Path("templates") / "blender" / "render-asm.py"
BLENDER_METHOD = "blender"  # FreeCAD tessellation as glTF, rendered by Blender (Cycles CPU, Freestyle edges)
BOM_COLS = ("item", "id", "name", "kind", "qty", "material", "print_profile", "standard", "manufacturer", "mpn", "file")


# ------------------------------------------------------------------ CK-F19
def version_faces(cfg, docs: dict | None = None) -> list[str]:
    """CK-F19 (XD-ADR-0143): every printed part (an object with a PrintProfile) has a version mark
    in its document: an LCS with Role = version-emboss (plain Python on the .FCStd files)."""
    docs = meassemblies.documents(cfg) if docs is None else docs
    out = []
    for rel, d in sorted(docs.items()):
        objs = d.sem["objects"]
        printed = [n for n, o in objs.items() if str((o.get("values") or {}).get("PrintProfile") or "").strip()]
        if not printed:
            continue
        marks = [n for n, o in objs.items() if o.get("type") in LCS_TYPES
                 and str((o.get("values") or {}).get("Role") or "").strip() == "version-emboss"]
        if not marks:
            out.append(f"{rel}: printed part {', '.join(printed)} has no version mark (an LCS with Role = "
                       f"version-emboss, TextSize, MaxWidth on the face for the version); `curatrix cam` cannot "
                       f"emboss it")
        elif len(marks) > 1:
            out.append(f"{rel}: {len(marks)} version marks ({', '.join(marks)}); exactly one")
    return out


# ------------------------------------------------------------------ version
def version(repo: Path, name: str, folder: Path) -> tuple[str, bool, str]:
    """(full version, release, short version for the parts)."""
    v, release = git_version(repo, name, folder)
    shared = [s for s in SHARED if (repo / s).exists()]
    if shared and _git(repo, "status", "--porcelain", "--", *shared).stdout.strip() and "-dirty" not in v:
        v = v.replace("-preview", "") + "-dirty-preview"
        release = False
    short = v.split("/", 1)[1] if "/" in v else v
    m = re.match(r"v\d+\.\d+\.\d+", short)
    tag = m.group(0) if m else "v0.0.0"
    return v, release, tag if release else f"{tag}P"


# ------------------------------------------------------------------ helpers
def _md5(paths: list[Path]) -> dict[str, str]:
    return {str(p): hashlib.md5(p.read_bytes()).hexdigest() for p in paths}


def variants(doc: meassemblies.Doc) -> list[str]:
    """The variants of a top document: each configuration named in the ``Configs`` of a link (the
    link's own property), and ``base`` for every configuration no link names (only the links
    without ``Configs``); without any ``Configs`` one variant ``all``. The model's configuration
    list is not read yet, so a configuration is known here only when a link names it."""
    cs = set()
    for o in doc.sem["objects"].values():
        if o.get("type") in meassemblies.LINK_TYPES:
            cs |= set(cad._list(str((o.get("trace") or {}).get("Configs") or "")))
    return sorted(cs) + [BASE] if cs else [ALL]


def empty_views(res: dict) -> list[str]:
    """The views of a cam-asm.py result without a visible edge (TechDraw did not compute them)."""
    return sorted(k for k, n in (res.get("edges") or {}).items() if not n)


def empty_renderings(res: dict) -> list[str]:
    """The renderings of a cam-asm.py result without a painted facet (or not made at all)."""
    painted = res.get("painted") or {}
    return sorted(v for v in VIEWS if not painted.get(v))


def bom_rows(rows: list[dict], repo: Path) -> list[dict]:
    """The flat BOM: one row per part with its quantity."""
    out: dict[tuple, dict] = {}
    for r in rows:
        key = (r["file"], r["object"])
        if key not in out:
            kind = ("board" if r.get("TraceID", "").startswith("EE-PCBA") else "printed" if r.get("PrintProfile")
                    else "fastener" if r.get("Standard") else "bought" if r.get("Manufacturer") or r.get("MPN")
                    else "part")
            try:
                f = str(Path(r["file"]).resolve().relative_to(repo.resolve()))
            except ValueError:
                f = r["file"]
            out[key] = {"id": r.get("TraceID", ""), "name": r.get("label", ""), "kind": kind, "qty": 0,
                        "material": r.get("Material", ""), "print_profile": r.get("PrintProfile", ""),
                        "standard": r.get("Standard", ""), "manufacturer": r.get("Manufacturer", ""),
                        "mpn": r.get("MPN", ""), "file": f}
        out[key]["qty"] += 1
    rows_ = sorted(out.values(), key=lambda x: (x["kind"], x["id"], x["name"]))
    for i, r in enumerate(rows_, 1):
        r["item"] = i
    return rows_


def _write_csv(path: Path, rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(BOM_COLS), extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
        w.writerow({"item": "total", "qty": sum(r["qty"] for r in rows)})


# ------------------------------------------------------------------ the drawing sheet (SVG and PDF)
_NUM = r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?"


def _paths(svg: str) -> list[list[tuple]]:
    """The polylines of a TechDraw view SVG: each path as a list of (x, y) points (arcs and curves
    flattened), circles as polygons."""
    out = []
    for d in re.findall(r'<path[^>]*?\sd="([^"]*)"', svg):
        toks = re.findall(r"[MLHVCSQAZmlhvcsqaz]|" + _NUM, d)
        pts, cur, start, cmd, i = [], (0.0, 0.0), (0.0, 0.0), "M", 0

        def num():
            nonlocal i
            v = float(toks[i])
            i += 1
            return v
        while i < len(toks):
            if re.fullmatch(r"[A-Za-z]", toks[i]):
                cmd = toks[i]
                i += 1
                if cmd in "Zz":
                    pts.append(start)
                    cur = start
                continue
            rel = cmd.islower()
            c = cmd.upper()
            ox, oy = cur if rel else (0.0, 0.0)
            if c == "M":
                if len(pts) > 1:
                    out.append(pts)
                cur = (ox + num(), oy + num())
                pts, start = [cur], cur
                cmd = "l" if rel else "L"
            elif c == "L":
                cur = (ox + num(), oy + num())
                pts.append(cur)
            elif c == "H":
                cur = ((ox if rel else 0) + num(), cur[1])
                pts.append(cur)
            elif c == "V":
                cur = (cur[0], (oy if rel else 0) + num())
                pts.append(cur)
            elif c in "CSQ":
                n = {"C": 3, "S": 2, "Q": 2}[c]
                ps = [(ox + num(), oy + num()) for _ in range(n)]
                ctrl = [cur] + ps if c != "S" else [cur, ps[0], ps[0], ps[1]]
                for k in range(1, 9):
                    t = k / 8
                    if len(ctrl) == 4:
                        a, b, cc, dd = ctrl
                        x = (1 - t) ** 3 * a[0] + 3 * (1 - t) ** 2 * t * b[0] + 3 * (1 - t) * t * t * cc[0] + t ** 3 * dd[0]
                        y = (1 - t) ** 3 * a[1] + 3 * (1 - t) ** 2 * t * b[1] + 3 * (1 - t) * t * t * cc[1] + t ** 3 * dd[1]
                    else:
                        a, b, cc = ctrl
                        x = (1 - t) ** 2 * a[0] + 2 * (1 - t) * t * b[0] + t * t * cc[0]
                        y = (1 - t) ** 2 * a[1] + 2 * (1 - t) * t * b[1] + t * t * cc[1]
                    pts.append((x, y))
                cur = ps[-1]
            elif c == "A":
                rx, ry, rot, large, sweep = num(), num(), num(), num(), num()
                end = (ox + num(), oy + num())
                pts += _arc(cur, end, rx, ry, rot, bool(large), bool(sweep))
                cur = end
            else:
                i += 1
        if len(pts) > 1:
            out.append(pts)
    for cx, cy, r in re.findall(r'<circle[^>]*?cx="(' + _NUM + r')"[^>]*?cy="(' + _NUM + r')"[^>]*?r="(' + _NUM + r')"', svg):
        cx, cy, r = float(cx), float(cy), float(r)
        out.append([(cx + r * math.cos(2 * math.pi * k / 32), cy + r * math.sin(2 * math.pi * k / 32)) for k in range(33)])
    return out


def _arc(p0, p1, rx, ry, rot, large, sweep, n=16) -> list[tuple]:
    """Points of an SVG elliptical arc (endpoint parametrization, SVG spec F.6.5)."""
    if rx == 0 or ry == 0 or p0 == p1:
        return [p1]
    phi = math.radians(rot)
    cp, sp = math.cos(phi), math.sin(phi)
    dx, dy = (p0[0] - p1[0]) / 2, (p0[1] - p1[1]) / 2
    x1, y1 = cp * dx + sp * dy, -sp * dx + cp * dy
    rx, ry = abs(rx), abs(ry)
    lam = x1 * x1 / (rx * rx) + y1 * y1 / (ry * ry)
    if lam > 1:
        rx, ry = rx * math.sqrt(lam), ry * math.sqrt(lam)
    num = rx * rx * ry * ry - rx * rx * y1 * y1 - ry * ry * x1 * x1
    den = rx * rx * y1 * y1 + ry * ry * x1 * x1
    co = math.sqrt(max(0.0, num / den)) if den else 0.0
    if large == sweep:
        co = -co
    cxp, cyp = co * rx * y1 / ry, -co * ry * x1 / rx
    cx = cp * cxp - sp * cyp + (p0[0] + p1[0]) / 2
    cy = sp * cxp + cp * cyp + (p0[1] + p1[1]) / 2

    def ang(ux, uy, vx, vy):
        return math.atan2(ux * vy - uy * vx, ux * vx + uy * vy)
    t1 = ang(1, 0, (x1 - cxp) / rx, (y1 - cyp) / ry)
    dt_ = ang((x1 - cxp) / rx, (y1 - cyp) / ry, (-x1 - cxp) / rx, (-y1 - cyp) / ry)
    if not sweep and dt_ > 0:
        dt_ -= 2 * math.pi
    elif sweep and dt_ < 0:
        dt_ += 2 * math.pi
    pts = []
    for k in range(1, n + 1):
        t = t1 + dt_ * k / n
        x, y = rx * math.cos(t), ry * math.sin(t)
        pts.append((cp * x - sp * y + cx, sp * x + cp * y + cy))
    return pts


W, H = 420.0, 297.0                       # A3 landscape, mm
STANDARD_SCALES = (50, 20, 10, 5, 2, 1, 0.5, 0.2, 0.1, 0.05, 0.02, 0.01)   # ISO 5455
MARGIN, GAP = 20.0, 15.0                  # mm: from the frame to the views; between views (labels)
BLOCK_W, BLOCK_H = 185.0, 47.0            # the title block, bottom right
NOTE = "views only, no dimensions; sheet composed by curatrix from FreeCADCmd views (no TechDraw template)"


def standard_scale(fit: float) -> float:
    """The largest standard scale (ISO 5455) that is not larger than ``fit``."""
    return next((s for s in STANDARD_SCALES if s <= fit + 1e-9), STANDARD_SCALES[-1])


def scale_text(s: float) -> str:
    return "1:1" if abs(s - 1) < 1e-9 else f"{s:g}:1" if s > 1 else f"1:{1 / s:g}"


def _bbox(ps) -> tuple[float, float, float, float] | None:
    pts = [p for pl in ps for p in pl]
    if not pts:
        return None
    return min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)


def projection_symbol(x: float, y: float) -> list[list[tuple]]:
    """The first-angle projection symbol (ISO 128-30 / ISO 5456-2) with its top left at (x, y):
    the end view (two circles) left of the side view of the truncated cone."""
    def circle(cx, cy, r):
        return [(cx + r * math.cos(2 * math.pi * k / 32), cy + r * math.sin(2 * math.pi * k / 32)) for k in range(33)]
    cy = y + 5
    return [circle(x + 5, cy, 5), circle(x + 5, cy, 2.5),
            [(x + 13, cy - 5), (x + 23, cy - 2.5), (x + 23, cy + 2.5), (x + 13, cy + 5), (x + 13, cy - 5)]]


def sheet(views: dict[str, str], title: dict[str, str], preview: bool) -> tuple[list[tuple], list[tuple]]:
    """(polylines, texts) of the drawing sheet in mm, y downwards. A plain-Python view sheet, not a
    TechDraw page: frame, the views front, top and right in first-angle projection (ISO 128 method 1:
    top view below the front view, the view from the right left of it), aligned and at one standard
    scale; the iso view in the larger free area, at the same scale or a smaller standard one; no
    dimensions. Title block with the scale, the projection symbol and that note. texts: (x, y, size,
    text, red)."""
    lines: list[list[tuple]] = [[(5, 5), (W - 5, 5), (W - 5, H - 5), (5, H - 5), (5, 5)]]
    texts = []
    polys = {k: _paths(v) for k, v in views.items()}
    box = {k: _bbox(ps) for k, ps in polys.items()}

    def size(k):
        b = box.get(k)
        return (b[2] - b[0], b[3] - b[1]) if b else (0.0, 0.0)
    (fw, fh), (tw, th), (rw, rh) = size("front"), size("top"), size("right")
    bottom = H - 5 - BLOCK_H - 5                          # the views stay above the title block
    aw, ah = W - 2 * MARGIN, bottom - MARGIN
    fit = min((aw - GAP) / max(rw + max(fw, tw), 1e-6), (ah - GAP) / max(max(fh, rh) + th, 1e-6))
    scale = standard_scale(fit)

    def place(k, x0, y0, s):
        """Draw view k at scale s with the top left of its bounding box at (x0, y0)."""
        b = box.get(k)
        if b is None:
            return
        for pl in polys[k]:
            lines.append([(x0 + (x - b[0]) * s, y0 + (y - b[1]) * s) for x, y in pl])
    xr, xf, yf = MARGIN, MARGIN + rw * scale + GAP, MARGIN + 5
    yt = yf + max(fh, rh) * scale + GAP
    place("right", xr, yf, scale)
    place("front", xf, yf, scale)
    place("top", xf, yt, scale)
    texts += [(xr, yf - 2, 3.5, "right", False), (xf, yf - 2, 3.5, "front", False), (xf, yt - 2, 3.5, "top", False)]
    # iso: below the right view, or right of the front and top views, whichever gives the larger scale
    iw, ih = size("iso")
    cands = [(MARGIN, yt, xf - GAP - MARGIN, bottom - yt),
             (xf + max(fw, tw) * scale + GAP, MARGIN + 5, W - MARGIN - (xf + max(fw, tw) * scale + GAP), bottom - MARGIN - 5)]
    best = max(cands, key=lambda c: min(c[2] / max(iw, 1e-6), c[3] / max(ih, 1e-6)) if c[2] > 0 and c[3] > 0 else -1)
    iscale = min(scale, standard_scale(min(best[2] / max(iw, 1e-6), best[3] / max(ih, 1e-6))))
    if best[2] > 0 and best[3] > 0:
        place("iso", best[0], best[1], iscale)
        texts.append((best[0], best[1] - 2, 3.5, "iso" + ("" if iscale == scale else f" ({scale_text(iscale)})"), False))
    # title block, bottom right
    bx, by = W - 5 - BLOCK_W, H - 5 - BLOCK_H
    lines.append([(bx, by), (W - 5, by), (W - 5, H - 5), (bx, H - 5), (bx, by)])
    rows = [("Assembly", title.get("assembly", "")), ("ID", title.get("id", "")), ("Version", title.get("version", "")),
            ("Variant", title.get("variant", "")), ("Date", title.get("date", "")), ("Scale", scale_text(scale)),
            ("Projection", "first angle (ISO 128 method 1)")]
    for i, (k, v) in enumerate(rows):
        texts.append((bx + 2, by + 5 + i * 5, 3, f"{k}: {v}", False))
    texts.append((bx + 2, by + 5 + len(rows) * 5 + 1, 2.2, NOTE, False))
    lines += projection_symbol(W - 5 - 30, by + 26)
    if preview:
        texts.append((bx + 120, by + 12, 8, "PREVIEW", True))
    return lines, texts


def sheet_svg(lines, texts) -> str:
    def esc(s):
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    body = "\n".join('<polyline fill="none" stroke="#000" stroke-width="0.25" points="'
                     + " ".join(f"{x:.3f},{y:.3f}" for x, y in pl) + '"/>' for pl in lines)
    body += "\n" + "\n".join(f'<text x="{x:.2f}" y="{y:.2f}" font-family="DejaVu Sans Mono, monospace" '
                             f'font-size="{s}" fill="{"#c00000" if red else "#000"}">{esc(t)}</text>'
                             for x, y, s, t, red in texts)
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" width="{W}mm" '
            f'height="{H}mm" viewBox="0 0 {W} {H}">\n<rect width="{W}" height="{H}" fill="#fff"/>\n{body}\n</svg>\n')


def sheet_pdf(lines, texts) -> bytes:
    """A one-page vector PDF of the sheet (PDF 1.4, Helvetica; no tool needed)."""
    k = 72 / 25.4                                   # mm -> pt; PDF y upwards
    ops = ["0.25 w 0 0 0 RG"]
    for pl in lines:
        ops.append(" ".join(f"{x * k:.2f} {(H - y) * k:.2f} {'m' if i == 0 else 'l'}" for i, (x, y) in enumerate(pl)) + " S")
    for x, y, s, t, red in texts:
        t = t.encode("latin-1", "replace").decode("latin-1").replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        ops.append(f"{'0.75 0 0' if red else '0 0 0'} rg BT /F1 {s * k:.2f} Tf {x * k:.2f} {(H - y) * k:.2f} Td ({t}) Tj ET")
    stream = "\n".join(ops).encode("latin-1")
    objs = [b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {W * k:.2f} {H * k:.2f}] /Contents 4 0 R "
            f"/Resources << /Font << /F1 5 0 R >> >> >>".encode(),
            b"<< /Length " + str(len(stream)).encode() + b" >>\nstream\n" + stream + b"\nendstream",
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    out, offs = bytearray(b"%PDF-1.4\n"), []
    for i, o in enumerate(objs, 1):
        offs.append(len(out))
        out += f"{i} 0 obj\n".encode() + o + b"\nendobj\n"
    x = len(out)
    out += f"xref\n0 {len(objs) + 1}\n0000000000 65535 f \n".encode()
    out += b"".join(f"{o:010d} 00000 n \n".encode() for o in offs)
    out += f"trailer\n<< /Size {len(objs) + 1} /Root 1 0 R >>\nstartxref\n{x}\n%%EOF\n".encode()
    return bytes(out)


def wrap_svg(fragment: str) -> str:
    """A TechDraw view SVG fragment (viewPartAsSvg) as a standalone SVG with a fitting viewBox."""
    pts = [p for pl in _paths(fragment) for p in pl]
    if pts:
        x0, x1 = min(p[0] for p in pts), max(p[0] for p in pts)
        y0, y1 = min(p[1] for p in pts), max(p[1] for p in pts)
    else:
        x0 = y0 = 0.0
        x1 = y1 = 1.0
    m = 2.0
    w, h = x1 - x0 + 2 * m, y1 - y0 + 2 * m
    return (f'<?xml version="1.0" encoding="UTF-8"?>\n<svg xmlns="http://www.w3.org/2000/svg" width="{w:.2f}mm" '
            f'height="{h:.2f}mm" viewBox="{x0 - m:.3f} {y0 - m:.3f} {w:.3f} {h:.3f}">\n{fragment}\n</svg>\n')


# ------------------------------------------------------------------ the run
def render_method(ws, use_blender: bool = True) -> str:
    """``blender`` when Blender is wanted and on the machine, else ``zbuffer`` (the fallback)."""
    from curatrix import blender
    return BLENDER_METHOD if use_blender and blender.available(ws) else RENDER_METHOD


def run_assembly(ws, repo, cfg, folder: Path, log=print, use_blender: bool = True) -> dict:
    from curatrix.newasm import run_script
    from curatrix.newpcba import NewError
    name = folder.name
    top_doc, sk = folder / f"{name}.FCStd", folder / meassemblies.skeleton_name(name)
    if not (top_doc.is_file() and sk.is_file()):
        raise CamError(f"{ws.rel(folder)}: needs {top_doc.name} and {sk.name} (`curatrix new asm`)")
    docs = meassemblies.documents(cfg)
    warnings = version_faces(cfg, docs)
    for w in warnings:
        log(f"  warn CK-F19 {w}")
    ver, release, short = version(repo.path, name, folder)
    state = cam.tree_state(repo.path, folder, *shared_folders(repo.path))
    tag = ver.split("/", 1)[1] if "/" in ver else ver
    top = ws.build(cfg.area) / "cam" / name / tag
    if top.exists():
        shutil.rmtree(top)
    out = top / name
    out.mkdir(parents=True)
    sources = sorted({p.resolve() for p in cfg.globs((cfg.section("cad") or {}).get("freecad") or [])})
    before = _md5(sources)
    explode_file = folder / "explode.yaml"
    moves = {}
    if explode_file.is_file():
        moves = yaml.safe_load(explode_file.read_text(encoding="utf-8")) or {}
        if not isinstance(moves, dict) or not all(isinstance(v, list) and len(v) == 3 for v in moves.values()):
            raise CamError(f"{ws.rel(explode_file)}: a mapping {{link name: [dx, dy, dz]}} in mm")
    top_rel = str(top_doc.resolve().relative_to(cfg.repo.resolve()))
    vs = variants(docs[top_rel]) if top_rel in docs else [ALL]
    head = _git(repo.path, "rev-parse", "HEAD").stdout.strip()
    date = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    aid = next(iter(docs[top_rel].asm_ids), "") if top_rel in docs else ""
    per, profiles = {}, {}
    method = render_method(ws, use_blender)
    bl_info = {}
    for vname in vs:
        v = "" if vname == ALL else vname
        dest = out / vname
        dest.mkdir(parents=True)
        log(f"  {name} {ver} variant {vname}: FreeCADCmd cam-asm.py")
        glb = top / f"{vname}.scene.glb"
        try:
            res = run_script(ws, ws.xdmod / SCRIPT, {
                "XD_TOP": str(top_doc.resolve()), "XD_SKELETON": str(sk.resolve()), "XD_OUT": str(dest),
                "XD_VARIANT": v, "XD_VERSION": ver, "XD_SHORT": short, "XD_FONT": str(ws.xdmod / FONT),
                "XD_EXPLODE": json.dumps(moves), "XD_SCENE": str(glb) if method == BLENDER_METHOD else "",
                "XD_RELEASE": "1" if release else ""}, top / f"{vname}.result.json")
        except NewError as e:
            raise CamError(f"{name} (variant {vname}): {e}") from None
        if method == BLENDER_METHOD:
            res["painted"], bl_info = render_blender(ws, glb, dest / "renderings", top / f"{vname}.blender.json",
                                                     [f"{name}  variant {v or 'all'}", ver], release, name, vname, log)
            res["render_scale"] = bl_info.get("render_scale") or {}
        if empty_views(res):
            raise CamError(f"{name} (variant {vname}): no visible edge in the view(s) {', '.join(empty_views(res))} "
                           f"(TechDraw did not compute them in FreeCADCmd); an empty view is never written as output")
        if empty_renderings(res):
            raise CamError(f"{name} (variant {vname}): no painted facet in the rendering(s) "
                           f"{', '.join(empty_renderings(res))}; an empty rendering is never written as output")
        for f in ("views/" + x + ".svg" for x in VIEWS):
            (dest / f).write_text(wrap_svg((dest / f).read_text(encoding="utf-8")), encoding="utf-8")
        (dest / "exploded.svg").write_text(wrap_svg((dest / "exploded.svg").read_text(encoding="utf-8")),
                                           encoding="utf-8")
        lines, texts = sheet({k: (dest / "views" / f"{k}.svg").read_text(encoding="utf-8") for k in VIEWS},
                             {"assembly": name, "id": aid, "version": ver, "variant": vname, "date": date[:10]},
                             not release)
        (dest / "drawing.svg").write_text(sheet_svg(lines, texts), encoding="utf-8")
        (dest / "drawing.pdf").write_bytes(sheet_pdf(lines, texts))
        rows = bom_rows(res.get("bom") or [], cfg.repo)
        _write_csv(dest / "bom.csv", rows)
        (dest / "mass.json").write_text(json.dumps(asmdoc.mass(res.get("bom") or []), indent=2) + "\n",
                                        encoding="utf-8")
        for r in rows:
            p = r["print_profile"]
            if not p:
                continue
            src = cfg.repo / "print" / f"{p}.ini"
            if not src.is_file():
                raise CamError(f"{r['file']}: PrintProfile {p!r}, but print/{p}.ini does not exist")
            (dest / "print").mkdir(exist_ok=True)
            shutil.copy2(src, dest / "print" / src.name)
            profiles[p] = f"print/{src.name}"
        per[vname] = {"embossed": res.get("embossed") or {}, "edges": res.get("edges") or {},
                      "moves": res.get("moves") or {}, "bom_rows": len(rows),
                      "renderings": {v: f"{name}/{vname}/renderings/{v}.png" for v in VIEWS},
                      "painted": res.get("painted") or {}, "facets": res.get("facets", 0),
                      "render_scale": res.get("render_scale") or {},
                      **({"render_seconds": bl_info.get("seconds") or {}} if method == BLENDER_METHOD else {})}
    (top / "findings.json").write_text(json.dumps(findings(ws, cfg, folder, top), indent=2) + "\n", encoding="utf-8")
    after = _md5(sources)
    changed = sorted(ws.rel(Path(p)) for p in before if after.get(p) != before[p])
    if changed:
        raise CamError(f"{name}: the CAM run changed the source documents {', '.join(changed)} (it must never save)")
    files = sorted(str(f.relative_to(top)) for f in out.rglob("*") if f.is_file())
    rec = {"kind": "assembly", "project": name, "assembly": aid, "version": ver, "release": release,
           "emboss": short, "commit": head, "tree_state": state, "date": date, "variants": vs,
           "print_profiles": profiles, "sources_unchanged": True,
           "renderings": renderings_rec(method, release, bl_info), "per_variant": per, "warnings": warnings,
           "files": files}
    (top / "cam.json").write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    log(f"  {name}: {len(files)} files in {ws.rel(out)} ({'release' if release else 'preview'}); sources unchanged")
    return rec


def findings(ws, cfg, folder: Path, top: Path) -> dict:
    """The ME check findings of this assembly (CK-F4c, CK-F16, CK-F17; findings of shared documents
    too) with their acceptance state, and the reason CK-F18 skipped, for the assembly document
    (task 5.27; tied to the commit like the rest of the output). One FreeCADCmd run (mechecks)."""
    from curatrix import ercdrc, mechecks
    try:
        res = mechecks.run(ws, cfg, top)
    except mechecks.MeCheckError as e:
        raise CamError(f"{folder.name}: the ME checks failed: {e}") from None
    mine = str(folder.relative_to(cfg.repo))
    entries, _ = mechecks.folder_entries(cfg, ercdrc.Acceptors(cfg.repo))
    rows = []
    for check in mechecks.RULES:
        found = [(f, x) for f, x in mechecks.findings(cfg, res, check) if f in (mine, None)]
        rows += mechecks.evaluate(cfg, check, found, entries).rows
    b = mechecks.boards(res)
    return {"checks": list(mechecks.RULES), "rows": rows,
            "skipped": {"CK-F18": f"board model(s) {', '.join(b)} placed; the space budget is not checked yet"
                        if b else "no board model in the assembly"}}


def render_blender(ws, glb: Path, dest: Path, result: Path, label: list[str], release: bool, name: str,
                   vname: str, log=print) -> tuple[dict, dict]:
    """The four renderings of one variant by Blender: (painted pixels per view, the script's result)."""
    from curatrix import blender
    log(f"  {name} variant {vname}: blender render-asm.py (Cycles CPU)")
    try:
        r = blender.run_script(ws, ws.xdmod / BLENDER_SCRIPT, {
            "XD_SCENE": str(glb), "XD_OUT": str(dest), "XD_LABEL": json.dumps(label),
            "XD_RELEASE": "1" if release else "", "XD_FONT": str(ws.xdmod / FONT)}, result)
    except blender.BlenderError as e:
        raise CamError(f"{name} (variant {vname}): {e}; `curatrix cam --no-blender` uses the renderer "
                       f"without Blender") from None
    return r.get("painted") or {}, r


def renderings_rec(method: str, release: bool, bl_info: dict) -> dict:
    """The ``renderings`` entry of cam.json: which way they were made, and the marking."""
    rec = {"views": list(VIEWS), "method": method,
           "marking": "release" if release else "PREVIEW"}
    if method == BLENDER_METHOD:
        rec.update({k: bl_info.get(k) for k in ("blender", "engine", "device", "samples", "seed")})
        rec["pinned"] = False            # a system package: local output only, never compared
    return rec


def run(ws, repo, cfg, name: str | None = None, log=print, use_blender: bool = True) -> list[dict]:
    folders = [d for d in meassemblies.top_folders(cfg) if name is None or d.name == name]
    if not folders:
        known = ", ".join(d.name for d in meassemblies.top_folders(cfg)) or "none"
        raise CamError(f"no assembly {name or ''} in {repo.name}/assemblies/ (assemblies: {known})".replace("  ", " "))
    return [run_assembly(ws, repo, cfg, d, log, use_blender) for d in folders]


def shared_folders(repo: Path) -> list[Path]:
    return [repo / s for s in SHARED if (repo / s).exists()]


def current(cam_dir: Path, name: str, repo: Path, folder: Path) -> tuple[dict | None, Path | None, str]:
    """(cam.json record, its version folder, why there is none) of the ``curatrix cam`` run of an
    assembly that the assembly document may show: one of the commit ``repo`` is at, from an
    assembly folder and shared ``parts/``, ``lib/``, ``print/`` in exactly the uncommitted state
    they are in now (``cam.tree_state``, the rule of the board document; task 5.27)."""
    head = _git(repo, "rev-parse", "HEAD").stdout.strip()
    state = cam.tree_state(repo, folder, *shared_folders(repo))
    none = f"no `curatrix cam` output of {name} for commit {head[:12]}"
    best, why = None, none
    for f in sorted((cam_dir / name).glob("*/cam.json")):
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if rec.get("kind") != "assembly" or rec.get("commit") != head:
            continue
        if rec.get("tree_state", "") != state:
            why = ("uncommitted changes that differ from those of the `curatrix cam` run" if state
                   else "the `curatrix cam` output of this commit is from a tree with uncommitted changes")
            continue
        if best is None or f.stat().st_mtime > best[0]:
            best = (f.stat().st_mtime, rec, f.parent)
    return (best[1], best[2], "") if best else (None, None, why)
