"""`curatrix cam <repo> [<project>]`: the EE design output (task 5.20; XD-ADR-0142, XD-ADR-0140) and
the plain-Python jobset and version-variable rules (CK-F10, CK-F11).

``cam`` copies a ``pcba/`` project into ``build/<area>/cam/<project>/<version>/project/``, writes the
version into the copy's ``.kicad_pro`` text variable ``XD_VERSION`` (the version only, without the
``<project>/`` tag prefix) and the board name into ``XD_BOARD``, and runs the project's jobset
there (``kicad-cli jobset run``) with ``XD_CAM_OUT`` = the version folder, so the outputs land in
``build/<area>/cam/<project>/<version>/<project>/``. Then:

* single exports where a job cannot do it: the schematic SVG per variant (the SVG job names its
  files after the sheets, so variant jobs would overwrite each other);
* plain Python: ``stackup.csv`` from the ``.kicad_pcb`` and ``design-rules.csv`` from the
  ``.kicad_pro`` and ``.kicad_dru`` (KiCad exports neither);
* ERC and DRC (``kicad-cli``, as CK-F4a/b) into ``erc-drc/`` and ``findings.json``: every finding
  with its acceptance state, for the board document (task 5.21; the checks do not read it);
* ``cam.json`` in the version folder: version, commit, jobs, files.

``current(cam_dir, project, repo, folder)`` finds the output the board document may show: the run
of the commit the repo is at, never an older one (task 5.21).

Guards: the jobset must pass the hard rules of CK-F10 (no Execute Command job, no Copy Files,
output folder or job file name outside ``${XD_CAM_OUT}``, it parses, no job without a variant after
a variant job, every variant job names one variant of the project); the number of jobs KiCad reports as succeeded must equal
the number of jobs in the jobset (one job KiCad cannot parse drops all jobs, with exit code 0).

Version (XD-ADR-0142): ``git describe --tags --match '<project>/*'``; without a tag
``<project>/v0.0.0-<n>-g<sha>``. Only an exact tag on a commit of ``main``, with a clean project
folder, is a release; anything else gets ``-dirty`` (uncommitted changes in the project folder) and
``-preview``. ``-dirty`` looks only at the project folder: the libraries and 3D models come from
other repos (``libs/``) and can change the STEP model and the renderings without a mark.

Frames and silkscreen (CK-F11; owner decision Q13 of tiacsys/xdmod#69, correcting XD-ADR-0142): the
title block of every sheet and of the board has title ``${XD_BOARD}`` and rev ``${XD_VERSION}``; the
board has the two silkscreen lines ``${XD_BOARD}`` and ``${XD_VERSION}``. ``XD_VERSION`` holds the
version without the tag prefix (``v0.1.0``, ``v0.1.0-3-gabc1234-preview``). A release version fits
the Rev field; a preview version is longer than the field and KiCad cuts it off at the frame (open
point for the owner: a comment line with the full version); the committed values are
``unversioned`` and the project name.

Jobset template (``xdmod/templates/kicad-pcba/pcba.kicad_jobset``): the jobs without a variant come
first, then the variant-dependent ones. A project with variants has, instead of each
variant-dependent template job, one job per variant: id ``<template id>-<variant>``, settings equal
to the template job except the variant and the file name. KiCad keeps the variant of the last job
for the following ones, so a job without a variant after a variant job would silently export that
variant (found in task 5.20).
"""
from __future__ import annotations

import copy
import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
from pathlib import Path

from curatrix import cad

VARIANT_KEY = {"sch_export_plot_pdf": "variant_names", "sch_export_bom": "variant_names",
               "pcb_export_pos": "variant", "pcb_export_3d": "variant", "pcb_render": "variant"}
ALL_VARIANT_KEYS = ("variant", "variant_name", "variant_names")
FILE_KEYS = ("output_filename", "output_dir")
FORBIDDEN = {
    "special_execute": "an Execute Command job (XD-ADR-0142)",
    "pcb_export_stats": "a statistics job (KiCad cannot parse it in a jobset and then runs 0 jobs, KiCad spike §2.4)",
    "sch_erc": "an ERC job (ERC is CK-F4a, not part of the CAM run)",
    "pcb_drc": "a DRC job (DRC is CK-F4b, not part of the CAM run)",
}
HARD = ("special_execute", "special_copyfiles", "output", "jobfile", "parse", "order", "variant")
BOM_DELIMITERS = ("field_delimiter", "string_delimiter", "ref_delimiter", "ref_range_delimiter")
TEMPLATE = Path("templates") / "kicad-pcba" / "pcba.kicad_jobset"
VAR = "${XD_VERSION}"
BOARD_VAR = "${XD_BOARD}"


# ------------------------------------------------------------------ jobset
def job_variants(job: dict) -> list[str]:
    s = job.get("settings") or {}
    out = []
    for k in ALL_VARIANT_KEYS:
        v = s.get(k)
        out += [v] if isinstance(v, str) and v else [x for x in v or [] if isinstance(x, str) and x] \
            if isinstance(v, list) else []
    return out


def template(ws, name: str) -> dict:
    return json.loads((ws.xdmod / TEMPLATE).read_text(encoding="utf-8").replace("__NAME__", name))


def _variant_file(fn: str, v: str) -> str:
    if fn.endswith("/"):
        return f"{fn[:-1]}-{v}/"
    stem, dot, ext = fn.rpartition(".")
    return f"{stem}-{v}.{ext}" if dot and stem else f"{fn}-{v}"


def expected(ws, name: str, variants: list[str]) -> dict:
    """The project's jobset: the template, with one job per variant for each variant-dependent job."""
    t = template(ws, name)
    if not variants:
        return t
    fixed = [j for j in t["jobs"] if j["type"] not in VARIANT_KEY]
    per = []
    for j in t["jobs"]:
        if j["type"] not in VARIANT_KEY:
            continue
        for v in variants:
            k = copy.deepcopy(j)
            k["id"] = f"{j['id']}-{v}"
            k["description"] = f"{j.get('description') or j['id']} ({v})"
            for f in FILE_KEYS:
                if f in k["settings"]:
                    k["settings"][f] = _variant_file(k["settings"][f], v)
            key = VARIANT_KEY[j["type"]]
            k["settings"][key] = [v] if key == "variant_names" else v
            per.append(k)
    t["jobs"] = fixed + per
    return t


def dumps(js: dict) -> str:
    return json.dumps(js, indent=2) + "\n"


def _strip(settings: dict) -> dict:
    return {k: v for k, v in settings.items() if k not in ALL_VARIANT_KEYS + FILE_KEYS}


def _inside(path: str) -> bool:
    p = path.replace("\\", "/")
    return not (p.startswith("/") or re.match(r"^[A-Za-z]:", p) or ".." in p.split("/") or "$" in p)


def jobset_findings(ws, pr, variants: list[str]) -> list[tuple[str, str]]:
    """CK-F10: (kind, text) per finding; kinds in HARD stop `curatrix cam`."""
    js_path = pr.folder / f"{pr.name}.kicad_jobset"
    if not js_path.is_file():
        return [("missing", f"no jobset {pr.name}.kicad_jobset; write it with "
                            f"`curatrix cam <repo> {pr.name} --update-jobset`")]
    try:
        js = json.loads(js_path.read_text(encoding="utf-8"))
        jobs = js["jobs"]
        assert isinstance(jobs, list) and all(isinstance(j, dict) and j.get("type") for j in jobs)
    except (ValueError, KeyError, AssertionError, TypeError):
        return [("parse", f"{js_path.name}: not a KiCad jobset (JSON with a `jobs` list)")]
    out: list[tuple[str, str]] = []
    ids = [j.get("id") for j in jobs]
    for i in sorted({i for i in ids if ids.count(i) > 1}):
        out.append(("ids", f"job id {i!r} appears {ids.count(i)} times"))
    seen_variant = None
    for j in jobs:
        jid, typ, s = j.get("id"), j["type"], j.get("settings") or {}
        if typ in FORBIDDEN:
            out.append((typ if typ in HARD else "type", f"job {jid!r}: {FORBIDDEN[typ]}; remove it"))
        if typ == "special_copyfiles":
            dest = str(s.get("dest") or "")
            if not _inside(dest):
                out.append(("special_copyfiles", f"job {jid!r}: Copy Files to {dest!r}, outside the output folder"))
        for k in FILE_KEYS:
            if k in s and not _inside(str(s[k])):
                out.append(("jobfile", f"job {jid!r}: {k} {s[k]!r} leaves the output folder ${{XD_CAM_OUT}} (D46); "
                                       f"use a relative name"))
        if typ == "sch_export_bom":
            miss = [k for k in BOM_DELIMITERS if not s.get(k)]
            if miss:
                out.append(("bom", f"job {jid!r}: BOM without {', '.join(miss)} (KiCad writes a CSV without "
                                   f"separators, KiCad spike §2.4)"))
        vs = job_variants(j)
        for v in vs:
            if v not in variants:
                out.append(("variant", f"job {jid!r} names variant {v!r}, which the project does not have "
                                       f"(schematic.variants: {', '.join(variants) or 'none'})"))
        if vs:
            seen_variant = seen_variant or jid
        elif seen_variant and typ not in ("special_copyfiles",):
            out.append(("order", f"job {jid!r} has no variant but comes after the variant job {seen_variant!r}: KiCad "
                                 f"would export it with that variant; put the jobs without a variant first"))
        if variants and typ in VARIANT_KEY and len(vs) != 1:
            out.append(("variant", f"job {jid!r}: in a project with variants each {typ} job names exactly one variant"))
    for o in js.get("outputs") or []:
        path = str((o.get("settings") or {}).get("output_path") or "")
        if not path.startswith("${XD_CAM_OUT}") or not _inside(path[len("${XD_CAM_OUT}"):].lstrip("/")):
            out.append(("output", f"output {o.get('id')!r}: {path!r} is not under ${{XD_CAM_OUT}} (output only under "
                                  f"build/, D46)"))
    # the shared template: every job there, variant jobs equal to their template job
    by_id = {j.get("id"): j for j in jobs}
    for t in template(ws, pr.name)["jobs"]:
        wanted = [(f"{t['id']}-{v}", v) for v in variants] if variants and t["type"] in VARIANT_KEY else [(t["id"], None)]
        for jid, v in wanted:
            j = by_id.get(jid)
            if j is None:
                out.append(("template", f"job {jid!r} of the shared template is missing"
                                        + (f" (variant {v})" if v else "")))
                continue
            if j["type"] != t["type"] or _strip(j.get("settings") or {}) != _strip(t["settings"]):
                out.append(("template", f"job {jid!r} differs from the template job {t['id']!r} in more than its "
                                        f"variant and file name"))
            elif job_variants(j) != ([v] if v else []):
                out.append(("variant", f"job {jid!r} names {job_variants(j) or 'no variant'}, not {v!r}"))
    return out


# ------------------------------------------------------------------ version variable (CK-F11)
def _kids(node, name):
    return [c for c in node[1:] if isinstance(c, list) and c and c[0] == name]


def _title_block(root) -> tuple[str, str]:
    """(title, rev) of a title block."""
    tb = next(iter(_kids(root, "title_block")), None)
    if tb is None:
        return "", ""
    first = lambda k: next((c[1] for c in _kids(tb, k) if len(c) > 1 and isinstance(c[1], str)), "")  # noqa: E731
    return first("title"), first("rev")


def _silk_texts(root) -> list[str]:
    out = []
    for t in _kids(root, "gr_text"):
        layer = next((c[1] for c in _kids(t, "layer") if len(c) > 1), "")
        if isinstance(t[1], str) and str(layer).endswith("SilkS"):
            out.append(t[1])
    return out


# a long preview version, to test that the silkscreen version line fits (CK-F11); the board line
# is tested with the board name. KiCad's stroke
# font is about 0.87 x the character width per character (measured with KiCad 10.0.8)
LONG_VERSION = "v0.1.0-12-gabc1234-dirty-preview"
CHAR_ADVANCE = 0.87


def _outline_box(root) -> tuple[float, float, float, float] | None:
    """(xmin, ymin, xmax, ymax) of the Edge.Cuts drawings of a board (circles are holes, left out)."""
    pts = []
    for kind in ("gr_line", "gr_rect", "gr_arc", "gr_poly"):
        for g in _kids(root, kind):
            if next((c[1] for c in _kids(g, "layer") if len(c) > 1), "") != "Edge.Cuts":
                continue
            for k in ("start", "end", "mid"):
                pts += [(float(c[1]), float(c[2])) for c in _kids(g, k) if len(c) > 2]
            for pl in _kids(g, "pts"):
                pts += [(float(c[1]), float(c[2])) for c in _kids(pl, "xy") if len(c) > 2]
    if not pts:
        return None
    return min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)


def _obstacles(root) -> list[tuple[str, float, float, float]]:
    """(what, x, y, radius) of the holes (Edge.Cuts circles) and of every footprint pad (its
    bounding circle; pad positions rotate with the footprint) of a board."""
    import math
    out = []
    for c in _kids(root, "gr_circle"):
        if next((k[1] for k in _kids(c, "layer") if len(k) > 1), "") != "Edge.Cuts":
            continue
        ctr, end = next(iter(_kids(c, "center")), None), next(iter(_kids(c, "end")), None)
        if ctr and end:
            cx, cy = float(ctr[1]), float(ctr[2])
            out.append(("the hole", cx, cy, math.hypot(float(end[1]) - cx, float(end[2]) - cy)))
    for fp in _kids(root, "footprint"):
        at = next(iter(_kids(fp, "at")), None)
        if not at or len(at) < 3:
            continue
        fx, fy = float(at[1]), float(at[2])
        a = math.radians(float(at[3]) if len(at) > 3 else 0.0)
        ref = next((pr[2] for pr in _kids(fp, "property") if len(pr) > 2 and pr[1] == "Reference"), "?")
        for pad in _kids(fp, "pad"):
            pa, ps = next(iter(_kids(pad, "at")), None), next(iter(_kids(pad, "size")), None)
            if not pa or len(pa) < 3:
                continue
            px, py = float(pa[1]), float(pa[2])
            r = max(float(ps[1]), float(ps[2])) / 2 if ps and len(ps) > 2 else 0.5
            out.append((f"pad {pad[1]} of {ref}", fx + px * math.cos(a) + py * math.sin(a),
                        fy - px * math.sin(a) + py * math.cos(a), r))
    return out


def _silk_line_findings(root, board: str) -> list[str]:
    """Findings for the silkscreen lines with ${XD_BOARD} (filled with the board name) and
    ${XD_VERSION} (filled with LONG_VERSION): each line, estimated from its font size, stays inside
    the outline's bounding box and off holes and pads. Horizontal texts only; an estimate, not
    KiCad's text layout."""
    box = _outline_box(root)
    if box is None:
        return []
    obstacles = _obstacles(root)
    out = []
    for t in _kids(root, "gr_text"):
        layer = next((c[1] for c in _kids(t, "layer") if len(c) > 1), "")
        if not (isinstance(t[1], str) and (VAR in t[1] or BOARD_VAR in t[1]) and str(layer).endswith("SilkS")):
            continue
        at = next(iter(_kids(t, "at")), None)
        eff = next(iter(_kids(t, "effects")), [])
        font = next(iter(_kids(eff, "font")), []) if eff else []
        size = next(iter(_kids(font, "size")), None) if font else None
        if at is None or size is None or len(at) < 3 or len(size) < 3:
            continue
        if (float(at[3]) % 180 if len(at) > 3 else 0.0):
            continue
        h, w = float(size[1]), float(size[2])
        just = [x for j in (_kids(eff, "justify") if eff else []) for x in j[1:]]
        if str(layer).startswith("B."):
            just = ["right" if x == "left" else "left" if x == "right" else x for x in just]
        lines = t[1].split("\n")
        pitch = 1.6 * h
        for k, ln in enumerate(lines):
            if VAR not in ln and BOARD_VAR not in ln:
                continue
            what = VAR if VAR in ln else BOARD_VAR
            filled = ln.replace(VAR, LONG_VERSION).replace(BOARD_VAR, board)
            width = CHAR_ADVANCE * w * len(filled)
            x = float(at[1])
            y = float(at[2]) + (k - (len(lines) - 1) / 2) * pitch
            x0 = x if "left" in just else x - width if "right" in just else x - width / 2
            y0, y1 = y - h / 2 - 0.15, y + h / 2 + 0.15
            name = f"the silkscreen line with {what} ({filled!r}, about {width:.1f} mm from x {x0:.1f} mm)"
            if x0 < box[0] or x0 + width > box[2] or y0 < box[1] or y1 > box[3]:
                out.append(f"{name} would run past the board outline (x {box[0]:g} to {box[2]:g}, y {box[1]:g} to "
                           f"{box[3]:g} mm); move it or make its characters smaller")
                continue
            for o, cx, cy, r in obstacles:
                if x0 < cx + r and x0 + width > cx - r and y0 < cy + r and y1 > cy - r:
                    out.append(f"{name} would cross {o} at ({cx:g}, {cy:g}); move it")
                    break
    return out


def version_findings(pr) -> list[str]:
    """CK-F11: title ``${XD_BOARD}`` and rev ``${XD_VERSION}`` in the title block of every sheet
    and of the board; the board's silkscreen shows both, each on its own line; the committed values
    are ``unversioned`` and the project name."""
    out = []
    vs = pr.variables()
    if vs.get("XD_VERSION") != "unversioned":
        out.append(f"{pr.pro.name}: text variable XD_VERSION is {vs.get('XD_VERSION')!r}; the committed value is "
                   f"'unversioned' (curatrix cam writes the version into its copy)")
    if vs.get("XD_BOARD") != pr.name:
        out.append(f"{pr.pro.name}: text variable XD_BOARD is {vs.get('XD_BOARD')!r}; it is the board name {pr.name!r} "
                   f"(the project name)")
    for f in sorted(pr.folder.glob("*.kicad_sch")) + sorted(pr.folder.glob("*.kicad_pcb")):
        root = cad.sexpr(f.read_text(encoding="utf-8"))
        title, rev = _title_block(root)
        if BOARD_VAR not in title:
            out.append(f"{f.name}: the title-block title is {title!r}; it is {BOARD_VAR}")
        if VAR not in rev:
            out.append(f"{f.name}: the title-block Rev is {rev!r}; it is {VAR}")
        if f.suffix == ".kicad_pcb":
            lines = [ln for t in _silk_texts(root) for ln in t.split("\n")]
            for var in (BOARD_VAR, VAR):
                if not any(var in ln for ln in lines):
                    out.append(f"{f.name}: no silkscreen text (F.SilkS or B.SilkS) with {var}")
            out += [f"{f.name}: {x}" for x in _silk_line_findings(root, pr.name)]
            if any(BOARD_VAR in ln and VAR in ln for ln in lines):
                out.append(f"{f.name}: {BOARD_VAR} and {VAR} on one silkscreen line; put them on two lines (name, "
                           f"then version), sized to fit inside the board outline")
    return out


# ------------------------------------------------------------------ version (XD-ADR-0140, XD-ADR-0142)
def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=60)


def version(repo: Path, project: str, folder: Path, main: str | None = None) -> tuple[str, bool]:
    """(version, is_release) of a project: `git describe --match '<project>/*'`, marked as preview
    unless an exact tag on main with a clean project folder."""
    d = _git(repo, "describe", "--tags", "--match", f"{project}/*")
    exact = _git(repo, "describe", "--tags", "--exact-match", "--match", f"{project}/*").returncode == 0
    if d.returncode == 0:
        v = d.stdout.strip()
    else:
        n = _git(repo, "rev-list", "--count", "HEAD").stdout.strip() or "0"
        sha = _git(repo, "rev-parse", "--short=7", "HEAD").stdout.strip() or "0000000"
        v = f"{project}/v0.0.0-{n}-g{sha}"
    rel = str(folder.resolve().relative_to(repo.resolve()))
    dirty = bool(_git(repo, "status", "--porcelain", "--", rel).stdout.strip())
    if main is None:
        main = next((r for r in ("origin/main", "main")
                     if _git(repo, "rev-parse", "--verify", "-q", r).returncode == 0), None)
    on_main = bool(main) and _git(repo, "merge-base", "--is-ancestor", "HEAD", main).returncode == 0
    release = exact and on_main and not dirty
    if not release:
        v += ("-dirty" if dirty else "") + "-preview"
    return v, release


# ------------------------------------------------------------------ stackup and design rules
STACKUP_COLS = ("layer", "type", "material", "thickness_mm", "epsilon_r", "loss_tangent", "color")


def stackup(pcb: Path) -> tuple[list[dict], str]:
    """(rows, source) of a board's stackup: Board Setup's `(setup (stackup ...))`, or KiCad's
    default for a board without one (copper 35 um, the rest FR4, `general.thickness`)."""
    root = cad.sexpr(pcb.read_text(encoding="utf-8"))
    setup = next(iter(_kids(root, "setup")), [])
    st = next(iter(_kids(setup, "stackup")), None) if setup else None
    if st is not None:
        rows = []
        for layer in _kids(st, "layer"):
            row = {"layer": layer[1]}
            for c in layer[2:]:
                if isinstance(c, list) and len(c) > 1 and c[0] in ("type", "material", "thickness", "epsilon_r",
                                                                   "loss_tangent", "color"):
                    row["thickness_mm" if c[0] == "thickness" else c[0]] = c[1]
            rows.append(row)
        return rows, "Board Setup stackup"
    general = next(iter(_kids(root, "general")), [])
    thick = float(next((c[1] for c in _kids(general, "thickness")), 1.6))
    layers = next(iter(_kids(root, "layers")), [])
    copper = [lay[1] for lay in layers[1:] if isinstance(lay, list) and len(lay) > 2 and lay[1].endswith(".Cu")]
    copper = copper or ["F.Cu", "B.Cu"]
    order = ["F.Cu"] + [c for c in copper if c not in ("F.Cu", "B.Cu")] + ["B.Cu"]
    cu, mask = 0.035, 0.01             # KiCad's defaults; the board thickness includes both masks (.gbrjob)
    diel = round((thick - cu * len(order) - 2 * mask) / max(1, len(order) - 1), 4)
    rows = [{"layer": "F.SilkS", "type": "Top Silk Screen"}, {"layer": "F.Mask", "type": "Top Solder Mask",
                                                               "thickness_mm": "0.01"}]
    for i, c in enumerate(order):
        rows.append({"layer": c, "type": "copper", "thickness_mm": f"{cu}"})
        if i < len(order) - 1:
            core = len(order) == 2 or i % 2 == 1          # 2 layers: one core; more: prepreg outside, core inside
            rows.append({"layer": f"dielectric {i + 1}", "type": "core" if core else "prepreg", "material": "FR4",
                         "thickness_mm": f"{diel}", "epsilon_r": "4.5", "loss_tangent": "0.02"})
    rows += [{"layer": "B.Mask", "type": "Bottom Solder Mask", "thickness_mm": "0.01"},
             {"layer": "B.SilkS", "type": "Bottom Silk Screen"}]
    note = "" if len(order) == 2 else "; dielectrics split evenly, an approximation of KiCad's default"
    return rows, (f"KiCad default ({len(order)} copper layers, board thickness {thick} mm; no stackup in Board "
                  f"Setup{note})")


UNITLESS = {"min_resolved_spokes", "max_error_count"}


def _sx(node) -> str:
    if isinstance(node, list):
        return "(" + " ".join(_sx(c) for c in node) + ")"
    return f'"{node}"' if (not node or re.search(r'[\s()"]', node)) else node


def design_rules(pro: Path) -> list[dict]:
    """Rows (scope, rule, value) from the .kicad_pro design settings, the net classes and the
    custom rules of the .kicad_dru (KiCad exports none of them)."""
    d = json.loads(pro.read_text(encoding="utf-8"))
    rows = []
    rules = ((d.get("board") or {}).get("design_settings") or {}).get("rules") or {}
    for k in sorted(rules):
        v = rules[k]
        unit = "" if isinstance(v, bool) or k in UNITLESS else "mm"
        rows.append({"scope": "board", "rule": k, "value": json.dumps(v) if isinstance(v, bool) else v, "unit": unit})
    for c in (d.get("net_settings") or {}).get("classes") or []:
        for k in sorted(c):
            if k in ("name", "pcb_color", "schematic_color", "wire_width", "bus_width", "line_style", "priority",
                     "tuning_profile"):
                continue
            if isinstance(c[k], (int, float)) and not isinstance(c[k], bool):
                rows.append({"scope": f"net class {c.get('name')}", "rule": k, "value": c[k], "unit": "mm"})
    dru = pro.with_suffix(".kicad_dru")
    if dru.is_file():
        root = cad.sexpr("(dru " + dru.read_text(encoding="utf-8") + ")")
        for r in root[1:]:
            if isinstance(r, list) and r and r[0] == "rule":
                rows.append({"scope": "custom rule", "rule": r[1],
                             "value": " ".join(_sx(c) for c in r[2:]), "unit": ""})
    return rows


def _csv(path: Path, cols, rows) -> None:
    import csv
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(cols), extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


# ------------------------------------------------------------------ the output of the current commit
def tree_state(repo: Path, folder: Path, *more: Path) -> str:
    """A hash of the uncommitted state of a project folder (and of ``more`` folders, e.g. the shared
    ``parts/``, ``lib/``, ``print/`` of an ME repo): ``git status`` of the folders and the content
    of every changed or untracked file ("" for a clean tree). A file that is reverted or deleted
    later changes it too (task 5.21; assemblies: task 5.27)."""
    rels = [str(f.resolve().relative_to(repo.resolve())) for f in (folder, *more)]
    status = _git(repo, "status", "--porcelain", "--untracked-files=all", "--", *rels).stdout
    if not status.strip():
        return ""
    h = hashlib.sha256(status.encode())
    for ln in sorted(status.splitlines()):
        f = repo / ln[3:].split(" -> ")[-1].strip('"')
        h.update(f"\0{ln}\0".encode())
        h.update(f.read_bytes() if f.is_file() else b"<missing>")
    return h.hexdigest()


def current(cam_dir: Path, project: str, repo: Path, folder: Path) -> tuple[dict | None, Path | None, str]:
    """(cam.json record, its version folder, why there is none) of the ``curatrix cam`` run the
    board document may show: one of the commit ``repo`` is at, from a project folder in exactly
    the uncommitted state it is in now (``tree_state``). Anything else is stale and never shown
    (task 5.21)."""
    head = _git(repo, "rev-parse", "HEAD").stdout.strip()
    try:
        state = tree_state(repo, folder)
    except ValueError:
        return None, None, f"{folder} is not in {repo}"
    none = f"no `curatrix cam` output for commit {head[:12]}"
    best, why = None, none
    for f in sorted((cam_dir / project).glob("*/cam.json")):
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if rec.get("kind", "board") != "board" or rec.get("commit") != head:
            continue
        if rec.get("tree_state", "") != state:
            why = ("the project folder has uncommitted changes that differ from those of the `curatrix cam` run"
                   if state else "the `curatrix cam` output of this commit is from a tree with uncommitted changes")
            continue
        if best is None or f.stat().st_mtime > best[0]:
            best = (f.stat().st_mtime, rec, f.parent)
    return (best[1], best[2], "") if best else (None, None, why)


# ------------------------------------------------------------------ the run
class CamError(Exception):
    pass


def set_variables(pro: Path, version: str, board: str) -> None:
    """Write XD_VERSION (the version without the ``<board>/`` tag prefix) and XD_BOARD into the
    text variables of a project COPY (never the committed file)."""
    d = json.loads(pro.read_text(encoding="utf-8"))
    d.setdefault("text_variables", {}).update(XD_VERSION=version, XD_BOARD=board)
    pro.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")


SKIP_COPY = shutil.ignore_patterns("*.kicad_prl", "*-backups", "fp-info-cache", "_autosave-*", "*.lck")
JOBS_RE = re.compile(r"(\d+) jobs? succeeded, (\d+) jobs? failed")


def update_jobset(ws, pr, log=print) -> Path:
    from curatrix import domvariants
    p = pr.folder / f"{pr.name}.kicad_jobset"
    p.write_text(dumps(expected(ws, pr.name, domvariants.kicad_variants(pr.pro))), encoding="utf-8")
    log(f"  wrote {ws.rel(p)} from the shared template and the variants of {pr.pro.name}")
    return p


def run_project(ws, repo, cfg, pr, log=print) -> dict:
    from curatrix import domvariants, limits
    variants = domvariants.kicad_variants(pr.pro)
    found = jobset_findings(ws, pr, variants)
    hard = [t for k, t in found if k in HARD or k == "missing"]
    if hard:
        raise CamError(f"{pr.name}: the jobset breaks the CAM rules (CK-F10): " + "; ".join(hard))
    for _, t in found:
        log(f"  warn CK-F10 {pr.name}: {t}")
    for t in version_findings(pr):
        log(f"  warn CK-F11 {pr.name}: {t}")
    ver, release = version(repo.path, pr.name, pr.folder)
    state = tree_state(repo.path, pr.folder)        # the state that is copied, before KiCad runs
    short = ver.split("/", 1)[1] if "/" in ver else ver
    top = ws.build(cfg.area) / "cam" / pr.name / short
    if top.exists():
        shutil.rmtree(top)
    copy_dir = top / "project"
    shutil.copytree(pr.folder, copy_dir, ignore=SKIP_COPY)
    pro = copy_dir / pr.pro.name
    set_variables(pro, short, pr.name)
    tmp = ws.build(cfg.area) / "cam" / "tmp"
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    env = dict(ws.run_env(), XD_CAM_OUT=str(top), TMPDIR=str(tmp))
    js = copy_dir / f"{pr.name}.kicad_jobset"
    n_jobs = len(json.loads(js.read_text(encoding="utf-8"))["jobs"])
    log(f"  {pr.name} {ver}: kicad-cli jobset run ({n_jobs} jobs) in {ws.rel(copy_dir)}")
    p = limits.run(["kicad-cli", "jobset", "run", "-f", str(js), str(pro)], "kicad-cli", ws, env=env,
                   capture_output=True, text=True)
    text = re.sub(r"\x1b\[[0-9;]*m", "", p.stdout + p.stderr)
    (top / "jobset.log").write_text(text, encoding="utf-8")
    m = JOBS_RE.search(text)
    ok_jobs, failed = (int(m.group(1)), int(m.group(2))) if m else (0, 0)
    if p.returncode or ok_jobs != n_jobs or failed:
        raise CamError(f"{pr.name}: kicad-cli jobset run: exit {p.returncode} {limits.explain_rc(p.returncode)}; "
                       f"{ok_jobs} of {n_jobs} jobs succeeded, {failed} failed (a job KiCad cannot parse drops all "
                       f"jobs); log: {ws.rel(top / 'jobset.log')}")
    out = top / pr.name
    out.mkdir(parents=True, exist_ok=True)
    singles = []
    for v in variants:                   # the SVG job names files after the sheets: one folder per variant
        dest = out / f"schematic-svg-{v}"
        argv = ["kicad-cli", "sch", "export", "svg", "--variant", v, "-o", str(dest), str(copy_dir / pr.sch.name)]
        r = limits.run(argv, "kicad-cli", ws, env=env, capture_output=True, text=True)
        if r.returncode:
            raise CamError(f"{pr.name}: {' '.join(argv[:4])} --variant {v}: exit {r.returncode} "
                           f"{limits.explain_rc(r.returncode)} {(r.stdout + r.stderr)[-300:]}")
        singles.append(f"sch export svg --variant {v}")
    pcb = copy_dir / f"{pr.name}.kicad_pcb"
    rows, source = stackup(pcb) if pcb.is_file() else ([], "no board")
    _csv(out / "stackup.csv", STACKUP_COLS, rows)
    _csv(out / "design-rules.csv", ("scope", "rule", "value", "unit"), design_rules(pro))
    from curatrix import ercdrc
    try:                                 # ERC/DRC findings with their acceptance, for the board document
        found_rows = ercdrc.document_rows(ws, cfg, pr, out / "erc-drc", ercdrc.Acceptors(repo.path))
    except RuntimeError as e:
        raise CamError(str(e)) from None
    (out / "findings.json").write_text(json.dumps(found_rows, indent=2) + "\n", encoding="utf-8")
    singles += ["sch erc", "pcb drc"][:len(found_rows)]
    shutil.rmtree(tmp, ignore_errors=True)
    files = sorted(str(f.relative_to(top)) for f in out.rglob("*") if f.is_file())
    head = _git(repo.path, "rev-parse", "HEAD").stdout.strip()
    rec = {"kind": "board", "project": pr.name, "version": ver, "release": release, "commit": head,
           "tree_state": state,
           "date": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "jobs": n_jobs, "single_exports": singles, "variants": variants, "stackup": source,
           "warnings": [t for _, t in found] + version_findings(pr), "files": files}
    (top / "cam.json").write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    log(f"  {pr.name}: {len(files)} files in {ws.rel(out)} ({'release' if release else 'preview'})")
    return rec


def run(ws, repo, cfg, project: str | None = None, update: bool = False, log=print) -> list[dict]:
    from curatrix import eeprojects
    prs = [p for p in eeprojects.discover(cfg) if p.kind == "pcba" and (project is None or p.name == project)]
    if not prs:
        raise CamError(f"no pcba/ project {project or ''} in {repo.name} (checks.yaml cad.projects)".replace("  ", " "))
    if update:
        for pr in prs:
            update_jobset(ws, pr, log)
        return []
    return [run_project(ws, repo, cfg, pr, log) for pr in prs]
