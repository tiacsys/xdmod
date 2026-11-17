"""`curatrix cam <repo> [<project>]`: the EE design output (task 5.20; XD-ADR-0142, XD-ADR-0140) and
the plain-Python jobset and version-variable rules (CK-F10, CK-F11).

``cam`` copies a ``pcba/`` project into ``build/<area>/cam/<project>/<version>/project/``, writes the
version into the copy's ``.kicad_pro`` text variable ``XD_VERSION`` and runs the project's jobset
there (``kicad-cli jobset run``) with ``XD_CAM_OUT`` = the version folder, so the outputs land in
``build/<area>/cam/<project>/<version>/<project>/``. Then:

* single exports where a job cannot do it: the schematic SVG per variant (the SVG job names its
  files after the sheets, so variant jobs would overwrite each other);
* plain Python: ``stackup.csv`` from the ``.kicad_pcb`` and ``design-rules.csv`` from the
  ``.kicad_pro`` and ``.kicad_dru`` (KiCad exports neither);
* ``cam.json`` in the version folder: version, commit, jobs, files.

Guards: the jobset must pass the hard rules of CK-F10 (no Execute Command job, no Copy Files,
output folder or job file name outside ``${XD_CAM_OUT}``, it parses, no job without a variant after
a variant job, every variant job names one variant of the project); the number of jobs KiCad reports as succeeded must equal
the number of jobs in the jobset (one job KiCad cannot parse drops all jobs, with exit code 0).

Version (XD-ADR-0142): ``git describe --tags --match '<project>/*'``; without a tag
``<project>/v0.0.0-<n>-g<sha>``. Only an exact tag on a commit of ``main``, with a clean project
folder, is a release; anything else gets ``-dirty`` (uncommitted changes in the project folder) and
``-preview``. ``-dirty`` looks only at the project folder: the libraries and 3D models come from
other repos (``libs/``) and can change the STEP model and the renderings without a mark. The full version goes into a title-block comment line and a silkscreen text; the
title-block ``Rev`` field stays empty, because KiCad cuts long values off there (KiCad spike §2.1).

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


def _title_block(root) -> tuple[list[str], str]:
    """(comment texts, rev) of a title block."""
    tb = next(iter(_kids(root, "title_block")), None)
    if tb is None:
        return [], ""
    comments = [c[2] for c in _kids(tb, "comment") if len(c) > 2 and isinstance(c[2], str)]
    rev = next((c[1] for c in _kids(tb, "rev") if len(c) > 1 and isinstance(c[1], str)), "")
    return comments, rev


def _silk_texts(root) -> list[str]:
    out = []
    for t in _kids(root, "gr_text"):
        layer = next((c[1] for c in _kids(t, "layer") if len(c) > 1), "")
        if isinstance(t[1], str) and str(layer).endswith("SilkS"):
            out.append(t[1])
    return out


def version_findings(pr) -> list[str]:
    """CK-F11: XD_VERSION in a title-block comment of every sheet and of the board, in a silkscreen
    text, not in the Rev field; the committed value is `unversioned`."""
    out = []
    val = pr.variables().get("XD_VERSION")
    if val != "unversioned":
        out.append(f"{pr.pro.name}: text variable XD_VERSION is {val!r}; the committed value is 'unversioned' "
                   f"(curatrix cam writes the version into its copy)")
    for f in sorted(pr.folder.glob("*.kicad_sch")) + sorted(pr.folder.glob("*.kicad_pcb")):
        root = cad.sexpr(f.read_text(encoding="utf-8"))
        comments, rev = _title_block(root)
        if not any(VAR in c for c in comments):
            out.append(f"{f.name}: no title-block comment line with {VAR} (for example comment 2 \"Version {VAR}\")")
        if VAR in rev:
            out.append(f"{f.name}: {VAR} in the title-block Rev field, which cuts long versions off; use a comment line")
        if f.suffix == ".kicad_pcb" and not any(VAR in t for t in _silk_texts(root)):
            out.append(f"{f.name}: no silkscreen text (F.SilkS or B.SilkS) with {VAR}")
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


# ------------------------------------------------------------------ the run
class CamError(Exception):
    pass


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
    short = ver.split("/", 1)[1] if "/" in ver else ver
    top = ws.build(cfg.area) / "cam" / pr.name / short
    if top.exists():
        shutil.rmtree(top)
    copy_dir = top / "project"
    shutil.copytree(pr.folder, copy_dir, ignore=SKIP_COPY)
    pro = copy_dir / pr.pro.name
    d = json.loads(pro.read_text(encoding="utf-8"))
    d.setdefault("text_variables", {})["XD_VERSION"] = ver
    pro.write_text(json.dumps(d, indent=2) + "\n", encoding="utf-8")
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
    shutil.rmtree(tmp, ignore_errors=True)
    files = sorted(str(f.relative_to(top)) for f in out.rglob("*") if f.is_file())
    head = _git(repo.path, "rev-parse", "HEAD").stdout.strip()
    rec = {"kind": "board", "project": pr.name, "version": ver, "release": release, "commit": head,
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
