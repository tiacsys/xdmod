"""The board library (task 5.29, XD-ADR-0139): FreeCAD models of tagged board versions.

``curatrix cam <ee-repo> <board> --board-model`` exports a ``pcba/`` project as a FreeCAD model, locally
and for any version (previews too):

1. copy the project into ``build/<area>/board-model/<board>/<version>/project/`` and write the
   version into the copy's ``XD_VERSION`` and the board name into ``XD_BOARD`` (as ``curatrix cam``
   does, XD-ADR-0142);
2. ``kicad-cli pcb export step --no-dnp --subst-models --user-origin X0xY0mm [--variant V]`` per
   variant of the project (board body and components, no tracks, pads or zones), with the origin at
   the lower-left corner of the ``Edge.Cuts`` outline (``board_frame``);
3. the FreeCAD GUI binary on Qt's offscreen platform (no window) runs
   ``xdmod/templates/freecad-pcba/import-step.py``: ``ImportGui.insert`` keeps the STEP's structure and
   colours (finding 17 of xdmod#69; ``FreeCADCmd`` has no view providers and loses the colours).
   One ``App::Part`` ``Board`` with ``TraceID`` (group Trace) = the project's ``TraceID`` text
   variable (its ``EE-PCBA``) and ``Version``, ``Variant``, ``Board``, ``Commit``, ``Source`` (group
   Board) and ``Thickness``; the model sits in the **board frame** of the co-design budget
   (XD-ADR-0134): origin at the lower-left corner of the outline seen from the top, x right, y up,
   z = 0 on the top face (the import moves it down by the board thickness), so an assembly places it
   with the seat's LCS as it is. Inside ``Board`` one object per component, named by its reference designator (``R1``, ``J1``;
   ``PCB`` = the board body): an ``App::Link`` to the component's 3D model, which is stored once per
   model in the hidden group ``Models`` with the STEP colours per face (``ShapeAppearance`` in
   ``GuiDocument.xml``); saved with the workspace FreeCAD config (CompressionLevel 0, uncompressed);
4. findings: compressed entries, a file above the size limit (5 MB to start), an invalid shape, a file
   without colours (``board_colours`` reads them back in plain Python; not part of CK-F20).

``--library`` does the same for a **release** only (an exact tag ``<board>/vX.Y.Z`` on main and a
clean project folder; anything else is refused before KiCad runs) and copies the files into
``boards/<board>/<board>-<vX.Y.Z>[-<variant>].FCStd`` of the board library: the repo whose
checks.yaml has a ``board_library`` section, which must be a checkout on a branch other than main
(a worktree set). Existing files are never overwritten. Then the EE agent commits and opens the PR.

Checks (plain Python, also in CI):

* CK-F20 (in the library, section ``board_library``): every ``.FCStd`` sits at
  ``boards/<board>/<board>-vX.Y.Z[-<variant>].FCStd``; its ``Board`` object carries an ``EE-PCBA``
  TraceID, ``Version`` = ``<board>/vX.Y.Z`` and the variant of the name; the tag exists in the
  source repo, names the same ``EE-PCBA`` in the project's ``TraceID`` at the tag, and ``Commit`` is
  the tag's commit; ``Board`` = the folder name; at most ``max_mb`` per file. The tag must be a
  release tag ``<board>/vX.Y.Z`` on the source repo's main (``origin/main``, in CI
  ``xd-ci/main``), and on its ``origin`` remote when it has one (a local, unpushed tag is a
  finding; an unreachable origin too, when the library has files; CI's west clones have no origin
  and fetched the remote's tags). Against the PR base (``XD_BASE_REF``, CI: the PR base), files
  under ``boards/`` may only be added: a changed or deleted board version is a finding.
* CK-F21 (in an ME repo, ``cad.board_library``): an ME FreeCAD file that links a board model of the
  library gets a note when the library has a newer version of that board and variant, or when the
  linked file is not in the library (XD-ADR-0139: moving to a new version is an ME change). Only
  links to ``boards/<board>/<file>`` count; other links into the library are ignored, and the linked
  object name (``Board``) is not checked yet.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import shutil
import struct
import subprocess
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from curatrix import cad

DEFAULT_MAX_MB = 5.0
VERSION_RE = re.compile(r"^v(\d+)\.(\d+)\.(\d+)$")
TAG_RE = re.compile(r"^(?P<board>[^/]+)/(?P<v>v\d+\.\d+\.\d+)$")
OBJECT = "Board"
SKIP_COPY = shutil.ignore_patterns("*.kicad_prl", "*-backups", "fp-info-cache", "_autosave-*", "*.lck")


class BoardLibError(Exception):
    pass


# ------------------------------------------------------------------ board frame
def board_frame(pcb: Path) -> tuple[float, float, float]:
    """(x, y, thickness) of a board's frame in KiCad coordinates (mm, y down): the lower-left corner
    of the ``Edge.Cuts`` outline seen from the top (smallest x, largest y) and ``general.thickness``
    (KiCad's default 1.6 mm without one). The board frame of the co-design budget (XD-ADR-0134): x
    right, y up, z = 0 on the top face."""
    root = cad.sexpr(pcb.read_text(encoding="utf-8"))
    xs, ys = [], []
    for item in root[1:]:
        if not (isinstance(item, list) and item and str(item[0]).startswith("gr_")):
            continue
        if not any(isinstance(c, list) and c[:2] == ["layer", "Edge.Cuts"] for c in item[1:]):
            continue
        kids = {c[0]: c for c in item[1:] if isinstance(c, list) and c}
        pts = [kids[k][1:3] for k in ("start", "end", "mid", "center") if k in kids]
        pts += [c[1:3] for c in (kids.get("pts") or [])[1:] if isinstance(c, list) and c and c[0] == "xy"]
        pts = [(float(a), float(b)) for a, b in pts]
        if item[0] == "gr_circle" and "center" in kids and "end" in kids:
            (cx, cy), (ex, ey) = (float(v) for v in kids["center"][1:3]), (float(v) for v in kids["end"][1:3])
            r = ((ex - cx) ** 2 + (ey - cy) ** 2) ** 0.5
            pts += [(cx - r, cy - r), (cx + r, cy + r)]
        xs += [a for a, _ in pts]
        ys += [b for _, b in pts]
    if not xs:
        raise BoardLibError(f"{pcb.name}: no outline on Edge.Cuts, so the board has no frame")
    general = next((c for c in root[1:] if isinstance(c, list) and c and c[0] == "general"), [])
    thick = next((float(c[1]) for c in general[1:] if isinstance(c, list) and c[:1] == ["thickness"]), 1.6)
    return min(xs), max(ys), thick


# ------------------------------------------------------------------ names
def file_name(board: str, short: str, variant: str | None) -> str:
    return f"{board}-{short}" + (f"-{variant}" if variant else "") + ".FCStd"


def parse_name(board: str, name: str) -> tuple[str, str | None] | None:
    """(vX.Y.Z, variant or None) of ``<board>-vX.Y.Z[-<variant>].FCStd``, None if the name does not fit."""
    m = re.fullmatch(re.escape(board) + r"-(v\d+\.\d+\.\d+)(?:-(.+))?\.FCStd", name)
    return (m.group(1), m.group(2)) if m else None


def vkey(short: str) -> tuple[int, int, int]:
    m = VERSION_RE.match(short)
    return tuple(int(x) for x in m.groups()) if m else (-1, -1, -1)


def board_props(fcstd: Path) -> dict:
    """TraceID, Version, Variant, Board, Commit of the library object ``Board`` (plain Python)."""
    sem = cad.freecad_trace(fcstd, fcstd.name)
    o = sem["objects"].get(OBJECT) or {}
    vals = o.get("values") or {}
    out = {k: vals.get(k) for k in ("Version", "Variant", "Board", "Commit") if vals.get(k) is not None}
    tid = (o.get("trace") or {}).get("TraceID")
    if tid:
        out["TraceID"] = tid
    out["_found"] = bool(o)
    return out


# PropertyMaterialList (version 3) file: uint32 count, then per material 4 packed colours (ambient, diffuse,
# specular, emissive) and 2 floats (shininess, transparency), 24 bytes; after all of them 12 more bytes
# per material (image and name data, not read here)
MATERIAL_BYTES = 24
MATERIAL_VERSION = "3"


def _rgb(packed: int) -> tuple[float, float, float]:
    """FreeCAD's packed colour 0xRRGGBBAA -> (r, g, b) in 0..1, rounded to 3 places."""
    return tuple(round(((packed >> sh) & 0xFF) / 255, 3) for sh in (24, 16, 8))


def board_colours(fcstd: Path) -> dict[str, list[tuple[float, float, float]]]:
    """Plain Python: object name -> the distinct diffuse colours of its faces (``ShapeAppearance`` of the
    view provider in ``GuiDocument.xml``, a binary material list per object). Objects without a
    ``ShapeAppearance`` (groups, links, parts) are left out; a file without ``GuiDocument.xml`` (saved by
    ``FreeCADCmd``) gives ``{}``. Another material list version than 3 raises ``ValueError``. Only ``Part::Feature`` objects count (not the datum axes and planes)."""
    out: dict = {}
    with zipfile.ZipFile(fcstd) as z:
        names = set(z.namelist())
        if "GuiDocument.xml" not in names:
            return {}
        doc = ET.fromstring(z.read("Document.xml"))
        features = {o.get("name") for o in doc.iter("Object") if o.get("type") == "Part::Feature"}
        root = ET.fromstring(z.read("GuiDocument.xml"))
        for vp in root.iter("ViewProvider"):
            if vp.get("name") not in features:
                continue
            ml = next((p.find("MaterialList") for p in vp.iter("Property") if p.get("name") == "ShapeAppearance"),
                      None)
            f = ml.get("file") if ml is not None else None
            if not f or f not in names:
                continue
            if ml.get("version") != MATERIAL_VERSION:
                raise ValueError(f"{fcstd.name}: {vp.get('name')}: material list version {ml.get('version')!r}, "
                                 f"only {MATERIAL_VERSION} is known (FreeCAD 1.1); update board_colours")
            data = z.read(f)
            if len(data) < 4:
                continue
            (n,) = struct.unpack_from("<I", data, 0)
            cols = []
            for i in range(n):
                off = 4 + i * MATERIAL_BYTES + 4                   # the diffuse colour, after the ambient one
                if off + 4 > len(data):
                    break
                c = _rgb(struct.unpack_from("<I", data, off)[0])
                if c not in cols:
                    cols.append(c)
            out[vp.get("name")] = cols
    return out


# ------------------------------------------------------------------ git
def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=60)


# ------------------------------------------------------------------ export
def release_version(repo: Path, pr) -> tuple[str, bool]:
    """``cam.version``, but a release only with an exact release tag ``<board>/vX.Y.Z`` (TAG_RE): a
    tag with a suffix (``-rc1``) is a preview; when HEAD has both, the release tag wins."""
    from curatrix import cam
    ver, release = cam.version(repo, pr.name, pr.folder)
    if release and not _is_release_tag(ver, pr.name):
        exact = [t for t in _git(repo, "tag", "--points-at", "HEAD", "--list", f"{pr.name}/v*").stdout.split()
                 if _is_release_tag(t, pr.name)]
        if exact:
            return sorted(exact, key=lambda t: vkey(t.split("/", 1)[1]))[-1], True
        return ver + "-preview", False
    return ver, release


def _is_release_tag(tag: str, board: str) -> bool:
    m = TAG_RE.match(tag)
    return bool(m) and m["board"] == board


def export(ws, repo, cfg, pr, release_only: bool = False, log=print) -> dict:
    """Export one pcba/ project as FreeCAD board models into build/; returns the record."""
    from curatrix import cam, domvariants, limits, newasm, newpcba
    ver, release = release_version(repo.path, pr)
    if release_only and not release:
        raise BoardLibError(
            f"{pr.name}: {ver} is not a tagged board version (an exact release tag {pr.name}/vX.Y.Z, no suffix, "
            f"on main and a clean project folder); the board library takes only tagged versions (XD-ADR-0139), and only the owner "
            f"makes the tags (XD-ADR-0140). Use --board-model for a local preview")
    tid = (pr.variables().get("TraceID") or "").strip()
    if not tid:
        raise BoardLibError(f"{ws.rel(pr.pro)}: no TraceID text variable (the EE-PCBA ID of the board, CK-F7)")
    short = ver.split("/", 1)[1] if "/" in ver else ver
    top = ws.build(cfg.area) / "board-model" / pr.name / short
    if top.exists():
        shutil.rmtree(top)
    copy_dir = top / "project"
    shutil.copytree(pr.folder, copy_dir, ignore=SKIP_COPY)
    pro = copy_dir / pr.pro.name
    cam.set_variables(pro, short, pr.name)
    pcb = copy_dir / f"{pr.name}.kicad_pcb"
    if not pcb.is_file():
        raise BoardLibError(f"{pr.name}: no {pcb.name}; a board model needs the layout")
    tmp = top / "tmp"
    tmp.mkdir(parents=True)
    env = dict(ws.run_env(), TMPDIR=str(tmp))
    head = _git(repo.path, "rev-parse", "HEAD").stdout.strip()
    max_mb = DEFAULT_MAX_MB
    fx, fy, thick = board_frame(pcb)       # the model in the board frame: the seat's LCS places it as is
    files, findings = [], []
    for variant in domvariants.kicad_variants(pr.pro) or [None]:
        step = top / (file_name(pr.name, short, variant)[:-len(".FCStd")] + ".step")
        argv = ["kicad-cli", "pcb", "export", "step", "--no-dnp", "--subst-models", "-f", "-o", str(step),
                "--user-origin", f"{fx:g}x{fy:g}mm"]
        argv += ["--variant", variant] if variant else []
        log(f"  {pr.name} {ver}{' variant ' + variant if variant else ''}: kicad-cli pcb export step")
        p = limits.run([*argv, str(pcb)], "kicad-cli", ws, env=env, capture_output=True, text=True)
        (top / (step.stem + ".kicad-cli.log")).write_text(p.stdout + p.stderr, encoding="utf-8")
        if p.returncode or not step.is_file():
            raise BoardLibError(f"{pr.name}: kicad-cli pcb export step: exit {p.returncode} "
                                f"{limits.explain_rc(p.returncode)}: {(p.stdout + p.stderr)[-400:]}")
        fc = top / file_name(pr.name, short, variant)
        try:
            res = newasm.run_script(ws, ws.xdmod / "templates" / "freecad-pcba" / "import-step.py",
                                    {"XD_STEP": str(step.resolve()), "XD_OUT": str(fc.resolve()), "XD_TRACE_ID": tid,
                                     "XD_VERSION": ver, "XD_VARIANT": variant or "", "XD_BOARD": pr.name,
                                     "XD_COMMIT": head, "XD_THICKNESS": f"{thick:g}"},
                                    top / (step.stem + ".result.json"), exe="FreeCAD")
        except newpcba.NewError as e:
            raise BoardLibError(f"{pr.name}: FreeCAD import: {e}") from e
        for bak in top.glob("*.FCBak"):
            bak.unlink()
        mb = fc.stat().st_size / 1e6
        f = file_findings(fc, max_mb)
        try:                                         # export only: CK-F20 does not ask for colours
            colours = board_colours(fc)
        except (ValueError, zipfile.BadZipFile, ET.ParseError) as e:
            colours, f = {"?": []}, f + [f"colours not readable: {e}"]
        if not colours:
            f.append("no colours (no ShapeAppearance in GuiDocument.xml): not imported by the FreeCAD GUI binary "
                     "(import-step.py, offscreen)")
        if res.get("uncoloured_faces"):
            f.append(f"one colour only for {', '.join(res['uncoloured_faces'])}: the STEP colours did not match the "
                     f"faces (import-step.py)")
        findings += [f"{fc.name}: {x}" for x in f]
        comps = res.get("components") or []
        files.append({"file": fc.name, "variant": variant, "step": step.name, "mb": round(mb, 3),
                      "solids": res.get("solids"), "bbox_mm": res.get("bbox_mm"), "bbox_min_mm": res.get("bbox_min_mm"),
                      "components": [{k: c.get(k) for k in ("label", "model", "colours")} for c in comps],
                      "models": res.get("models")})
        log(f"    {ws.rel(fc)}: {mb:.2f} MB, {len(comps)} components ({res.get('models')} models), "
            f"{res.get('solids')} solids, bbox {res.get('bbox_mm')} mm from {res.get('bbox_min_mm')} (board frame)")
    shutil.rmtree(tmp, ignore_errors=True)
    rec = {"kind": "board-model", "project": pr.name, "version": ver, "release": release, "commit": head,
           "frame": {"origin_kicad_mm": [fx, fy], "thickness_mm": thick},
           "trace_id": tid, "date": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "files": files, "findings": findings, "folder": ws.rel(top)}
    (top / "board-model.json").write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    for x in findings:
        log(f"  finding: {x}")
    return rec


def file_findings(fc: Path, max_mb: float) -> list[str]:
    out = []
    mb = fc.stat().st_size / 1e6
    if mb > max_mb:
        out.append(f"{mb:.2f} MB, above the limit of {max_mb:g} MB per file (XD-ADR-0139); simplify the 3D models "
                   f"or ask the owner")
    bad = cad.freecad_compressed(fc)
    if bad:
        out.append(f"saved compressed ({', '.join(bad[:3])} ...); FreeCAD must run with the workspace config")
    return out


# ------------------------------------------------------------------ into the library
def find_library(ws) -> Path:
    from curatrix import checkcfg
    hits = []
    for r in ws.repos:
        cy = r.path / "checks.yaml"
        if r.is_framework_repo and cy.is_file():
            try:
                if checkcfg.load(cy, ws.root).section("board_library") is not None:
                    hits.append(r.path)
            except Exception:                       # a broken checks.yaml elsewhere is not our concern here
                continue
    if len(hits) != 1:
        raise BoardLibError(f"{'no' if not hits else 'more than one'} repo with a board_library section in its "
                            f"checks.yaml in this workspace" + (f": {', '.join(ws.rel(h) for h in hits)}" if hits else
                                                                 "") + "; name the library checkout with --into")
    return hits[0]


def add_to_library(ws, repo, cfg, pr, dest: Path | None = None, log=print) -> list[Path]:
    """Export a tagged board version and copy its files into the library checkout ``dest``."""
    from curatrix import checkcfg
    _, release = release_version(repo.path, pr)
    if not release:                                  # refuse before KiCad runs
        export(ws, repo, cfg, pr, release_only=True, log=log)
    lib = (dest or find_library(ws)).resolve()
    cy = lib / "checks.yaml"
    if not cy.is_file() or checkcfg.load(cy, ws.root).section("board_library") is None:
        raise BoardLibError(f"{ws.rel(lib)} is not a board library (no board_library section in its checks.yaml)")
    branch = _git(lib, "symbolic-ref", "-q", "--short", "HEAD").stdout.strip()
    if not branch or branch == "main":
        raise BoardLibError(f"{ws.rel(lib)} is {'on main' if branch else 'detached'}; the library gets a board version "
                            f"by a pull request: put it on a branch (curatrix work start <branch> <library repo>)")
    rec = export(ws, repo, cfg, pr, release_only=True, log=log)
    big = [x for x in rec["findings"] if "above the limit" in x or "compressed" in x]
    if big:
        raise BoardLibError(f"{pr.name}: not added to the library: " + "; ".join(big))
    folder = lib / "boards" / pr.name
    src = ws.root / rec["folder"]
    targets = [folder / f["file"] for f in rec["files"]]
    there = [t for t in targets if t.exists()]
    if there:
        raise BoardLibError(f"{', '.join(ws.rel(t) for t in there)} exist; a board version is written once and never "
                            f"replaced (XD-ADR-0139)")
    folder.mkdir(parents=True, exist_ok=True)
    for f, t in zip(rec["files"], targets):
        shutil.copyfile(src / f["file"], t)
        log(f"  wrote {ws.rel(t)} ({f['mb']:.2f} MB)")
    log(f"next: commit in {ws.rel(lib)} on {branch}, run `curatrix check {lib.name} --stage local`, open the PR "
        f"(name the tag {rec['version']})")
    return targets


# ------------------------------------------------------------------ CK-F20
def _tag_on_main(src: Path, tag: str) -> bool:
    main = next((r for r in ("origin/main", "refs/remotes/xd-ci/main", "main")
                 if _git(src, "rev-parse", "--verify", "-q", r).returncode == 0), None)
    return bool(main) and _git(src, "merge-base", "--is-ancestor", tag, main).returncode == 0


def _remote_tags(src: Path) -> dict[str, str] | None | bool:
    """tag -> commit on the source repo's origin; False for a west clone in CI (no origin: its tags
    were fetched from the remote, so every local tag is a remote one); None if origin cannot be reached."""
    if "origin" not in _git(src, "remote").stdout.split():
        return False
    p = _git(src, "ls-remote", "--tags", "origin")
    if p.returncode:
        return None
    out = {}
    for ln in p.stdout.splitlines():
        sha, _, ref = ln.partition("\t")
        name = ref.removeprefix("refs/tags/")
        if name.endswith("^{}"):
            out[name[:-3]] = sha                     # the commit of an annotated tag
        else:
            out.setdefault(name, sha)
    return out


def changed_files(repo: Path, base: str | None) -> list[str]:
    """board files changed or deleted against the merge base with ``base`` (committed or not)."""
    if not base:
        return []
    mb = _git(repo, "merge-base", base, "HEAD").stdout.strip()
    if not mb:
        return []
    p = _git(repo, "diff", "--name-status", "--no-renames", mb, "--", "boards")
    return [f"{ln.split(chr(9))[1]}: {'changed' if ln[0] == 'M' else 'deleted'} against {base}; a board version is "
            f"never replaced or removed by a PR (XD-ADR-0139); a new version is a new file"
            for ln in p.stdout.splitlines() if ln[:1] in "MDT" and ln.endswith(".FCStd")]


def library_findings(ws, cfg, base: str | None = None) -> list[str]:
    """CK-F20 on the library repo."""
    s = cfg.section("board_library") or {}
    max_mb = float(s.get("max_mb") or DEFAULT_MAX_MB)
    src = cfg.resolve(s["source"]) if s.get("source") else None
    out = []
    if src is None or not (src / ".git").exists():
        out.append(f"board_library.source {s.get('source')!r} is not a git checkout in this workspace: the board tags "
                   f"cannot be checked")
        src = None
    repo = cfg.repo
    tags = set(_git(src, "tag", "-l").stdout.split()) if src else set()
    out += changed_files(repo, base)
    files = [f for f in sorted(repo.rglob("*.FCStd")) if not f.relative_to(repo).as_posix().startswith(".git/")]
    remote = _remote_tags(src) if src and files else False
    if src is not None and remote is None:
        out.append(f"{ws.rel(src)}: its origin cannot be reached, so the board tags cannot be checked as pushed tags")
    for fc in files:
        rel = fc.relative_to(repo).as_posix()
        parts = rel.split("/")
        parsed = parse_name(parts[1], parts[2]) if len(parts) == 3 and parts[0] == "boards" else None
        if parsed is None:
            out.append(f"{rel}: not boards/<board>/<board>-vX.Y.Z[-<variant>].FCStd")
            continue
        board, (short, variant) = parts[1], parsed
        tag = f"{board}/{short}"
        out += [f"{rel}: {x}" for x in file_findings(fc, max_mb)]
        try:
            p = board_props(fc)
        except Exception as e:                       # not a zip, no Document.xml, bad XML
            out.append(f"{rel}: not readable as a FreeCAD file ({e})")
            continue
        if not p["_found"]:
            out.append(f"{rel}: no object {OBJECT!r} (the model must come from `curatrix cam <ee-repo> {board} "
                       f"--library`)")
            continue
        tid = p.get("TraceID") or ""
        from curatrix import ids as idmod
        if idmod.kind_of(tid) != "EE-PCBA":
            out.append(f"{rel}: TraceID {tid or '(none)'} is not an EE-PCBA ID")
        if p.get("Version") != tag:
            out.append(f"{rel}: Version {p.get('Version')!r} does not match the file name ({tag})")
        if p.get("Board") != board:
            out.append(f"{rel}: Board {p.get('Board')!r} is not the folder name {board!r}")
        if (p.get("Variant") or None) != variant:
            out.append(f"{rel}: Variant {p.get('Variant')!r} does not match the file name ({variant or 'none'})")
        if src is None:
            continue
        if tag not in tags:
            out.append(f"{rel}: no tag {tag} in {ws.rel(src)}; only tagged board versions go into the library "
                       f"(XD-ADR-0139)")
            continue
        commit = _git(src, "rev-parse", f"{tag}^{{commit}}").stdout.strip()
        if not p.get("Commit"):
            out.append(f"{rel}: no Commit property (the commit of tag {tag})")
        elif p["Commit"] != commit:
            out.append(f"{rel}: Commit {p['Commit'][:12]} is not the commit of tag {tag} ({commit[:12]})")
        if not _tag_on_main(src, tag):
            out.append(f"{rel}: tag {tag} is not on main of {ws.rel(src)}")
        if isinstance(remote, dict) and remote.get(tag) != commit:
            out.append(f"{rel}: tag {tag} is not on the origin of {ws.rel(src)} (a local tag; only the owner's pushed "
                       f"tags count, XD-ADR-0140)")
        pro = next((f for f in _git(src, "ls-tree", "-r", "--name-only", tag).stdout.splitlines()
                    if f.endswith(f"/{board}/{board}.kicad_pro")), None)
        if pro is None:
            out.append(f"{rel}: tag {tag} has no KiCad project {board}/{board}.kicad_pro")
            continue
        try:
            tv = json.loads(_git(src, "show", f"{tag}:{pro}").stdout).get("text_variables") or {}
        except ValueError:
            tv = {}
        if not tv.get("TraceID"):
            out.append(f"{rel}: the project {pro} at {tag} has no TraceID text variable")
        elif tv["TraceID"] != tid:
            out.append(f"{rel}: TraceID {tid}, but the project at {tag} is {tv['TraceID']}")
    return out


# ------------------------------------------------------------------ CK-F21
def library_versions(lib: Path) -> dict[tuple[str, str | None], list[str]]:
    """(board, variant) -> versions vX.Y.Z in the library, oldest first."""
    out: dict = {}
    for fc in sorted((lib / "boards").glob("*/*.FCStd")):
        parsed = parse_name(fc.parent.name, fc.name)
        if parsed:
            out.setdefault((fc.parent.name, parsed[1]), []).append(parsed[0])
    return {k: sorted(v, key=vkey) for k, v in out.items()}


def newer_findings(ws, cfg) -> list[str]:
    """CK-F21 on an ME repo: links into the board library that are not the newest version."""
    lib_s = (cfg.section("cad") or {}).get("board_library")
    lib = cfg.resolve(lib_s).resolve()
    if not (lib / "boards").is_dir():
        return [f"cad.board_library {lib_s!r}: no boards/ folder there (is the library in this workspace?)"]
    versions = library_versions(lib)
    out = []
    for fc in cfg.globs((cfg.section("cad") or {}).get("freecad") or []):
        rel = fc.relative_to(cfg.repo).as_posix()
        try:
            sem = cad.freecad_trace(fc, rel)
        except Exception:
            continue                                 # CK-D4 reports unreadable files
        seen = set()
        for o in sem["objects"].values():
            for targets in (o.get("links") or {}).values():
                for t in targets:
                    f = t.get("file") or ""
                    if not f:
                        continue
                    target = (fc.parent / f).resolve()
                    try:
                        inner = target.relative_to(lib / "boards").as_posix().split("/")
                    except ValueError:
                        continue
                    if target in seen:
                        continue
                    seen.add(target)
                    parsed = parse_name(inner[0], inner[1]) if len(inner) == 2 else None
                    if parsed is None or not target.is_file():
                        out.append(f"{rel}: links {f}, which is not a board version in the library")
                        continue
                    have = versions.get((inner[0], parsed[1])) or []
                    newest = have[-1] if have else parsed[0]
                    if vkey(newest) > vkey(parsed[0]):
                        out.append(f"{rel}: links {inner[0]} {parsed[0]}" + (f" (variant {parsed[1]})" if parsed[1]
                                                                            else "") +
                                   f"; the library has {newest}. Moving to it is an ME change (XD-ADR-0139)")
    return out
