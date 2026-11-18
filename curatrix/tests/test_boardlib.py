"""The board library (task 5.29, XD-ADR-0139): CK-F20 on the library, CK-F21 on an ME repo, the release
guard of `curatrix cam --library`, the checks.yaml keys. Plain Python; the FreeCAD files are minimal
zips like those of `curatrix cam --board-model`."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from curatrix import boardlib, checkcfg, checks
from curatrix.ws import Repo, Workspace
from helpers import FIXTURES, git_init
from test_meassemblies import _prop, fcstd

TID = "EE-PCBA-0001"


def board_file(path, version, variant="", tid=TID, commit="", board=None):
    board = path.parent.name if board is None else board
    props = [_prop("TraceID", tid, group="Trace"), _prop("Version", version, group="Board"),
             _prop("Board", board, group="Board"),
             _prop("Variant", variant, group="Board"), _prop("Commit", commit, group="Board")]
    return fcstd(path, {"Board": ("App::Part", props), "Shape": ("Part::Feature", [])})


def _git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


def ee_repo(root, tags=("canary/v0.1.0",), tid=TID):
    ee = git_init(root / "ee")
    pro = ee / "pcba" / "canary" / "canary.kicad_pro"
    pro.parent.mkdir(parents=True)
    tv = {"TraceID": tid, "XD_VERSION": "unversioned"} if tid else {"XD_VERSION": "unversioned"}
    pro.write_text(json.dumps({"text_variables": tv}))
    _git(ee, "add", "-A")
    _git(ee, "commit", "-qm", "board")
    _git(ee, "branch", "-M", "main")
    for t in tags:
        _git(ee, "tag", t)
    return ee, _git(ee, "rev-parse", "HEAD")


def _ctx(root, name, yaml_text):
    repo = git_init(root / name)
    (repo / "checks.yaml").write_text(yaml_text)
    out = root / "out"
    out.mkdir(exist_ok=True)
    return checks.Ctx(Workspace(root), Repo(name, repo, name), checkcfg.load(repo / "checks.yaml", root), "local",
                      False, None, out)


def _run(ctx, fn):
    r = checks.Result("x", "x")
    fn(ctx, r)
    return r.findings


LIB = 'board_library: {source: "{ws}/ee", max_mb: 5}\n'


def test_f20_board_library(tmp_path):
    root = tmp_path / "ws"
    ee, sha = ee_repo(root)
    ctx = _ctx(root, "lib", LIB)
    lib = ctx.repo.path
    board_file(lib / "boards/canary/canary-v0.1.0-default.FCStd", "canary/v0.1.0", "default", commit=sha)
    assert _run(ctx, checks.c_board_library) == []
    # planted: no tag, a wrong name, a wrong version property, a foreign ID, a wrong commit
    board_file(lib / "boards/canary/canary-v0.2.0.FCStd", "canary/v0.2.0")
    board_file(lib / "boards/canary/board.FCStd", "canary/v0.1.0")
    board_file(lib / "boards/canary/canary-v0.1.0-alt.FCStd", "canary/v0.0.9", "alt")
    board_file(lib / "boards/canary/canary-v0.1.0-x.FCStd", "canary/v0.1.0", "x", tid="ME-PART-0001", commit="0" * 40)
    board_file(lib / "boards/canary/canary-v0.1.0-y.FCStd", "canary/v0.1.0", "y", board="other")
    f = "\n".join(_run(ctx, checks.c_board_library))
    assert "canary-v0.2.0.FCStd: no tag canary/v0.2.0" in f
    assert "board.FCStd: not boards/<board>/<board>-vX.Y.Z" in f
    assert "canary-v0.1.0-alt.FCStd: Version 'canary/v0.0.9' does not match" in f
    assert "canary-v0.1.0-x.FCStd: TraceID ME-PART-0001 is not an EE-PCBA ID" in f
    assert "canary-v0.1.0-x.FCStd: Commit 000000000000 is not the commit of tag" in f
    assert "TraceID ME-PART-0001, but the project at canary/v0.1.0 is EE-PCBA-0001" in f
    assert "canary-v0.1.0-y.FCStd: no Commit property" in f
    assert "canary-v0.1.0-y.FCStd: Board 'other' is not the folder name 'canary'" in f
    assert "default" not in f


def test_f20_size_and_missing_source(tmp_path):
    root = tmp_path / "ws"
    ctx = _ctx(root, "lib", 'board_library: {source: "{ws}/nowhere", max_mb: 0.000001}\n')
    board_file(ctx.repo.path / "boards/canary/canary-v0.1.0.FCStd", "canary/v0.1.0")
    f = "\n".join(_run(ctx, checks.c_board_library))
    assert "is not a git checkout in this workspace" in f
    assert "above the limit of 1e-06 MB" in f


def test_f21_newer_board_version(tmp_path):
    root = tmp_path / "ws"
    lib = root / "lib" / "boards" / "canary"
    for v in ("v0.1.0", "v0.2.0", "v0.10.0"):
        board_file(lib / f"canary-{v}-default.FCStd", f"canary/{v}", "default")
    board_file(lib / "canary-v0.1.0-alt.FCStd", "canary/v0.1.0", "alt")
    ctx = _ctx(root, "me", 'cad: {freecad: ["assemblies/**/*.FCStd"], board_library: "{ws}/lib"}\n')
    rel = "../../../lib/boards/canary/"

    def asm(name, target):
        fcstd(ctx.repo.path / f"assemblies/{name}/{name}.FCStd", {
            "Assembly": ("Assembly::AssemblyObject", []),
            "Board": ("App::Link", [_prop("LinkedObject", (rel + target, "Board"), "App::PropertyXLink")])})

    asm("newest", "canary-v0.10.0-default.FCStd")
    asm("alt", "canary-v0.1.0-alt.FCStd")
    assert _run(ctx, checks.c_board_versions) == []
    asm("old", "canary-v0.2.0-default.FCStd")
    asm("gone", "canary-v0.3.0-default.FCStd")
    f = "\n".join(_run(ctx, checks.c_board_versions))
    assert "assemblies/old/old.FCStd: links canary v0.2.0 (variant default); the library has v0.10.0" in f
    assert "assemblies/gone/gone.FCStd: links ../../../lib/boards/canary/canary-v0.3.0-default.FCStd, which is not" in f
    assert "newest" not in f and "alt.FCStd" not in f


def test_names_and_versions():
    assert boardlib.parse_name("canary-board", "canary-board-v1.2.3-no-led.FCStd") == ("v1.2.3", "no-led")
    assert boardlib.parse_name("canary-board", "canary-board-v1.2.3.FCStd") == ("v1.2.3", None)
    assert boardlib.parse_name("canary-board", "canary-v1.2.3.FCStd") is None
    assert boardlib.file_name("b", "v1.0.0", None) == "b-v1.0.0.FCStd"
    assert boardlib.vkey("v0.10.0") > boardlib.vkey("v0.9.9")


def test_checks_yaml_keys(tmp_path):
    assert checkcfg.validate({"board_library": {"source": "{ws}/ee", "max_mb": 5}}, tmp_path) == []
    assert checkcfg.validate({"cad": {"board_library": "{ws}/lib"}}, tmp_path) == []
    errs = "\n".join(checkcfg.validate({"board_library": {"max_mb": -1}, "cad": {"board_library": ["x"]}}, tmp_path))
    assert "board_library.source" in errs and "max_mb must be a positive number" in errs
    assert "cad.board_library must be a path" in errs


class _Pr:
    def __init__(self, folder):
        self.name, self.folder, self.pro = folder.name, folder, folder / f"{folder.name}.kicad_pro"

    def variables(self):
        return json.loads(self.pro.read_text())["text_variables"]


def test_library_refuses_untagged_versions(tmp_path, monkeypatch):
    """`curatrix cam --library` refuses a preview before KiCad runs (no kicad-cli call)."""
    monkeypatch.delenv("XD_BASE_REF", raising=False)
    root = tmp_path / "ws"
    ee, _ = ee_repo(root, tags=())
    ws = Workspace(root)
    cfg = type("C", (), {"area": "ee"})()
    pr = _Pr(ee / "pcba" / "canary")
    monkeypatch.setattr(boardlib.shutil, "copytree", lambda *a, **k: pytest.fail("exported a preview"))
    with pytest.raises(boardlib.BoardLibError, match="is not a tagged board version"):
        boardlib.add_to_library(ws, Repo("ee", ee, "ee"), cfg, pr, dest=tmp_path / "lib")
    _git(ee, "tag", "canary/v0.1.0")
    (pr.folder / "canary.kicad_sch").write_text("dirty")       # a tag, but uncommitted changes
    with pytest.raises(boardlib.BoardLibError, match="-dirty-preview is not a tagged board version"):
        boardlib.add_to_library(ws, Repo("ee", ee, "ee"), cfg, pr, dest=tmp_path / "lib")


def test_f20_tag_on_main_pushed_and_project_id(tmp_path):
    root = tmp_path / "ws"
    ee, sha = ee_repo(root, tags=(), tid="")
    _git(ee, "tag", "canary/v0.1.0")                       # a project without TraceID at the tag
    _git(ee, "checkout", "-qb", "side")
    _commit = (ee / "side.txt")
    _commit.write_text("x")
    _git(ee, "add", "-A")
    _git(ee, "commit", "-qm", "side")
    _git(ee, "tag", "canary/v0.2.0")                       # a tag that is not on main
    side = _git(ee, "rev-parse", "HEAD")
    ctx = _ctx(root, "lib", LIB)
    lib = ctx.repo.path / "boards/canary"
    board_file(lib / "canary-v0.1.0.FCStd", "canary/v0.1.0", commit=sha)
    board_file(lib / "canary-v0.2.0.FCStd", "canary/v0.2.0", commit=side)
    f = "\n".join(_run(ctx, checks.c_board_library))
    assert "canary-v0.1.0.FCStd: the project pcba/canary/canary.kicad_pro at canary/v0.1.0 has no TraceID" in f
    assert "canary-v0.2.0.FCStd: tag canary/v0.2.0 is not on main" in f
    assert "canary-v0.1.0.FCStd: tag canary/v0.1.0 is not on main" not in f
    # an origin without the tag: a local, unpushed tag
    bare = tmp_path / "remote.git"
    subprocess.run(["git", "clone", "-q", "--bare", "--no-tags", str(ee), str(bare)], check=True)
    _git(bare, "tag", "-d", "canary/v0.1.0") if "canary/v0.1.0" in _git(bare, "tag") else None
    _git(ee, "remote", "add", "origin", str(bare))
    f = "\n".join(_run(ctx, checks.c_board_library))
    assert "canary-v0.1.0.FCStd: tag canary/v0.1.0 is not on the origin" in f
    _git(ee, "push", "-q", "origin", "canary/v0.1.0")
    assert "canary-v0.1.0.FCStd: tag canary/v0.1.0 is not on the origin" not in "\n".join(
        _run(ctx, checks.c_board_library))


def test_f20_board_files_are_only_added(tmp_path, monkeypatch):
    root = tmp_path / "ws"
    ee, sha = ee_repo(root)
    ctx = _ctx(root, "lib", LIB)
    lib = ctx.repo.path
    fc = board_file(lib / "boards/canary/canary-v0.1.0.FCStd", "canary/v0.1.0", commit=sha)
    _git(lib, "add", "-A")
    _git(lib, "commit", "-qm", "v0.1.0")
    _git(lib, "branch", "-M", "main")
    _git(lib, "checkout", "-qb", "pr")
    monkeypatch.setenv("XD_BASE_REF", "main")
    assert _run(ctx, checks.c_board_library) == []
    board_file(fc, "canary/v0.1.0", commit=sha, tid="EE-PCBA-0002")   # a re-export over the old file
    f = "\n".join(_run(ctx, checks.c_board_library))
    assert "boards/canary/canary-v0.1.0.FCStd: changed against main; a board version is never replaced" in f


def _lib_checkout(root, branch="board/canary", section=True):
    lib = git_init(root / "lib")
    (lib / "checks.yaml").write_text(LIB if section else "version: 1\n")
    _git(lib, "add", "-A")
    _git(lib, "commit", "-qm", "skeleton")
    _git(lib, "branch", "-M", "main")
    if branch:
        _git(lib, "checkout", "-qb", branch)
    return lib


def _fake_export(ws, files):
    def export(ws_, repo, cfg, pr, release_only=False, log=print):
        folder = ws.root / "build" / "bm"
        folder.mkdir(parents=True, exist_ok=True)
        for f in files:
            (folder / f).write_text("model")
        return {"files": [{"file": f, "mb": 0.0} for f in files], "findings": [], "folder": "build/bm",
                "version": "canary/v0.1.0"}
    return export


def test_library_targets(tmp_path, monkeypatch):
    """--library writes only into a board library on a branch, and never over an existing file."""
    monkeypatch.delenv("XD_BASE_REF", raising=False)
    root = tmp_path / "ws"
    ee, _ = ee_repo(root)
    ws = Workspace(root)
    cfg = type("C", (), {"area": "ee"})()
    pr, repo = _Pr(ee / "pcba" / "canary"), Repo("ee", ee, "ee")
    monkeypatch.setattr(boardlib, "export", _fake_export(ws, ["canary-v0.1.0.FCStd"]))
    lib = _lib_checkout(root)
    on_main = _lib_checkout(tmp_path / "m", branch=None)
    with pytest.raises(boardlib.BoardLibError, match="is on main"):
        boardlib.add_to_library(ws, repo, cfg, pr, dest=on_main)
    _git(on_main, "checkout", "-q", "--detach")
    with pytest.raises(boardlib.BoardLibError, match="is detached"):
        boardlib.add_to_library(ws, repo, cfg, pr, dest=on_main)
    with pytest.raises(boardlib.BoardLibError, match="is not a board library"):
        boardlib.add_to_library(ws, repo, cfg, pr, dest=_lib_checkout(tmp_path / "x", section=False))
    out = boardlib.add_to_library(ws, repo, cfg, pr, dest=lib, log=lambda *_: None)
    assert out == [lib.resolve() / "boards/canary/canary-v0.1.0.FCStd"]
    with pytest.raises(boardlib.BoardLibError, match="exist; a board version is written once"):
        boardlib.add_to_library(ws, repo, cfg, pr, dest=lib, log=lambda *_: None)


def test_library_refuses_suffixed_tags(tmp_path, monkeypatch):
    monkeypatch.delenv("XD_BASE_REF", raising=False)
    root = tmp_path / "ws"
    ee, _ = ee_repo(root, tags=("canary/v1.0.0-rc1",))
    monkeypatch.setattr(boardlib.shutil, "copytree", lambda *a, **k: pytest.fail("exported a pre-release"))
    with pytest.raises(boardlib.BoardLibError, match="canary/v1.0.0-rc1-preview is not a tagged board version"):
        boardlib.add_to_library(Workspace(root), Repo("ee", ee, "ee"), type("C", (), {"area": "ee"})(),
                                _Pr(ee / "pcba" / "canary"), dest=tmp_path / "lib")


def test_release_version_takes_only_exact_release_tags(tmp_path):
    root = tmp_path / "ws"
    ee, _ = ee_repo(root, tags=("canary/v1.0.0-rc1",))
    pr = _Pr(ee / "pcba" / "canary")
    assert boardlib.release_version(ee, pr) == ("canary/v1.0.0-rc1-preview", False)
    _git(ee, "tag", "canary/v1.0.0")                       # the release on the same commit wins
    assert boardlib.release_version(ee, pr) == ("canary/v1.0.0", True)


# ------------------------------------------------------------------ the coloured board model (finding 17, xdmod#69)
def _materials(*rgbs):
    """A PropertyMaterialList file as FreeCAD 1.1 writes it: count, 24 bytes per material, 12 more each."""
    import struct

    def packed(rgb):
        r, g, b = (round(c * 255) for c in rgb)
        return (r << 24) | (g << 16) | (b << 8) | 0xFF
    data = struct.pack("<I", len(rgbs))
    for rgb in rgbs:
        data += struct.pack("<IIIIff", packed((0.333, 0.333, 0.333)), packed(rgb), packed((0.533, 0.533, 0.533)),
                            0xFF, 0.9, 0.0)
    return data + b"\0" * 12 * len(rgbs)


def coloured_board_file(path, version, commit="", colours=None):
    """The layout of import-step.py: Board (App::Part) with links named by designator, the models in
    a hidden group, their face colours in GuiDocument.xml."""
    import zipfile
    board_file(path, version, commit=commit)
    colours = colours if colours is not None else {"Model": [(0.824, 0.82, 0.78), (0.082, 0.086, 0.094)],
                                                   "Model001": [(0.314, 0.486, 0.412)]}
    objs = {"Board": "App::Part", "X_Axis": "App::Line", "R1": "App::Link", "PCB": "App::Link",
            "Models": "App::DocumentObjectGroup", **{m: "Part::Feature" for m in colours}}
    with zipfile.ZipFile(path) as z:
        doc = z.read("Document.xml").decode()
    doc = doc.replace("<Objects>", "<Objects>" + "".join(f'<Object type="{t}" name="{n}"/>' for n, t in objs.items()
                                                           if n not in ("Board",)))
    files = {"ShapeAppearance": _materials((0.8, 0.2, 0.2))}          # the X axis: not a component colour
    vps = ['<ViewProvider name="X_Axis"><Properties><Property name="ShapeAppearance" '
           'type="App::PropertyMaterialList"><MaterialList file="ShapeAppearance" version="3"/></Property>'
           '</Properties></ViewProvider>', '<ViewProvider name="R1"><Properties/></ViewProvider>']
    for i, (m, rgbs) in enumerate(colours.items(), 1):
        files[f"ShapeAppearance{i}"] = _materials(*rgbs)
        vps.append(f'<ViewProvider name="{m}"><Properties><Property name="ShapeAppearance" '
                   f'type="App::PropertyMaterialList"><MaterialList file="ShapeAppearance{i}" version="3"/>'
                   f'</Property></Properties></ViewProvider>')
    gui = f'<?xml version="1.0"?><Document SchemaVersion="1"><ViewProviderData>{"".join(vps)}</ViewProviderData></Document>'
    with zipfile.ZipFile(path, "w", zipfile.ZIP_STORED) as z:
        z.writestr("Document.xml", doc)
        z.writestr("GuiDocument.xml", gui)
        for n, data in files.items():
            z.writestr(n, data)
    return path


def test_board_colours(tmp_path):
    fc = coloured_board_file(tmp_path / "canary-v0.1.0.FCStd", "canary/v0.1.0")
    assert boardlib.board_colours(fc) == {"Model": [(0.824, 0.82, 0.78), (0.082, 0.086, 0.094)],
                                          "Model001": [(0.314, 0.486, 0.412)]}
    # a model saved by FreeCADCmd (the old Part.Shape.read import) has no GuiDocument.xml: no colours
    assert boardlib.board_colours(board_file(tmp_path / "old.FCStd", "canary/v0.1.0")) == {}
    # the trace properties sit on Board as before
    assert boardlib.board_props(fc)["Version"] == "canary/v0.1.0"


def test_f20_accepts_the_coloured_layout(tmp_path):
    root = tmp_path / "ws"
    ee, sha = ee_repo(root)
    ctx = _ctx(root, "lib", LIB)
    coloured_board_file(ctx.repo.path / "boards/canary/canary-v0.1.0.FCStd", "canary/v0.1.0", commit=sha)
    assert _run(ctx, checks.c_board_library) == []
    # CK-F20 does not ask for colours: an old single-compound file stays valid
    board_file(ctx.repo.path / "boards/canary/canary-v0.1.0-alt.FCStd", "canary/v0.1.0", "alt", commit=sha)
    assert _run(ctx, checks.c_board_library) == []


def test_board_colours_refuses_unknown_material_versions(tmp_path):
    import zipfile
    fc = coloured_board_file(tmp_path / "canary-v0.1.0.FCStd", "canary/v0.1.0")
    with zipfile.ZipFile(fc) as z:
        entries = {n: z.read(n) for n in z.namelist()}
    entries["GuiDocument.xml"] = entries["GuiDocument.xml"].replace(b'file="ShapeAppearance1" version="3"',
                                                                    b'file="ShapeAppearance1" version="4"')
    with zipfile.ZipFile(fc, "w", zipfile.ZIP_STORED) as z:
        for n, data in entries.items():
            z.writestr(n, data)
    with pytest.raises(ValueError, match="material list version '4'"):
        boardlib.board_colours(fc)


# a board outline 30 x 20 mm with its lower-left corner at (88, 112) and a mounting hole; 1.2 mm thick
PCB = """(kicad_pcb (general (thickness 1.2))
  (gr_line (start 88 92) (end 88 112) (layer "Edge.Cuts"))
  (gr_line (start 88 112) (end 118 112) (layer "Edge.Cuts"))
  (gr_rect (start 100 92) (end 118 100) (layer "Edge.Cuts"))
  (gr_circle (center 92 108) (end 90.4 108) (layer "Edge.Cuts"))
  (gr_line (start 0 0) (end 200 200) (layer "F.SilkS"))
)"""


def test_board_frame(tmp_path):
    pcb = tmp_path / "b.kicad_pcb"
    pcb.write_text(PCB)
    assert boardlib.board_frame(pcb) == (88.0, 112.0, 1.2)
    pcb.write_text(PCB.replace("(general (thickness 1.2))", ""))
    assert boardlib.board_frame(pcb)[2] == 1.6                       # KiCad's default
    pcb.write_text('(kicad_pcb (gr_line (start 0 0) (end 9 9) (layer "F.SilkS")))')
    with pytest.raises(boardlib.BoardLibError, match="no outline on Edge.Cuts"):
        boardlib.board_frame(pcb)


def _stub_export(tmp_path, monkeypatch, write, result):
    """export() with kicad-cli and FreeCAD stubbed: `write(path)` makes the board file the import would."""
    from curatrix import limits, newasm
    root = tmp_path / "ws"
    ee, _ = ee_repo(root)
    (ee / "pcba" / "canary" / "canary.kicad_pcb").write_text(PCB)
    ws = Workspace(root)

    def kicad(argv, use, ws_, **kw):
        assert argv[argv.index("--user-origin") + 1] == "88x112mm"
        out = argv[argv.index("-o") + 1]
        open(out, "w").write("ISO-10303-21;")
        return subprocess.CompletedProcess(argv, 0, "", "")

    def freecad(ws_, script, env, res, use="freecad", exe="FreeCADCmd"):
        assert exe == "FreeCAD" and script.name == "import-step.py"
        assert env["XD_THICKNESS"] == "1.2"
        write(Path(env["XD_OUT"]))
        return result
    monkeypatch.setattr(limits, "run", kicad)
    monkeypatch.setattr(newasm, "run_script", freecad)
    return boardlib.export(ws, Repo("ee", ee, "ee"), type("C", (), {"area": "ee"})(), _Pr(ee / "pcba" / "canary"),
                           log=lambda *_: None)


RESULT = {"ok": True, "solids": 2, "bbox_mm": [30.0, 20.0, 2.0], "models": 2, "links": 2, "copies": 0,
          "components": [{"name": "R1", "label": "R1", "model": "R_0603", "colours": [[0.824, 0.82, 0.78]],
                          "face_colours": True},
                         {"name": "PCB", "label": "PCB", "model": "canary_PCB", "colours": [[0.314, 0.486, 0.412]],
                          "face_colours": True}]}


def test_export_records_components_and_colours(tmp_path, monkeypatch):
    rec = _stub_export(tmp_path, monkeypatch, lambda p: coloured_board_file(p, "canary/v0.1.0"), RESULT)
    assert rec["findings"] == []
    f = rec["files"][0]
    assert f["models"] == 2 and [c["label"] for c in f["components"]] == ["R1", "PCB"]
    assert f["components"][1] == {"label": "PCB", "model": "canary_PCB", "colours": [[0.314, 0.486, 0.412]]}
    saved = json.loads((tmp_path / "ws" / rec["folder"] / "board-model.json").read_text())
    assert saved["files"][0]["components"] == f["components"]


def test_export_reports_missing_colours(tmp_path, monkeypatch):
    # planted: a file as FreeCADCmd saves it (no GuiDocument.xml), and a component whose colours did not fit
    res = dict(RESULT, uncoloured_faces=["R1"])
    rec = _stub_export(tmp_path, monkeypatch, lambda p: board_file(p, "canary/v0.1.0"), res)
    f = "\n".join(rec["findings"])
    assert "no colours (no ShapeAppearance in GuiDocument.xml)" in f
    assert "one colour only for R1" in f


@pytest.mark.tools
def test_import_step_pins_the_import_settings(tmp_path):
    """The real import (FreeCAD GUI binary, offscreen) in a FreeCAD config with hostile import
    preferences (ImportMode 2 stalled it until the time limit; review of #75): it still gives one
    link per component, named by the instance name, and the models with colours."""
    from curatrix import newasm
    if shutil.which("FreeCAD") is None or shutil.which("FreeCADCmd") is None:
        pytest.skip("FreeCAD not installed")
    ws = Workspace(tmp_path / "ws")
    step, out = tmp_path / "board.step", tmp_path / "board.FCStd"
    pre = newasm.run_script(ws, FIXTURES / "freecad" / "hostile_import_prefs.py", {"XD_STEP": str(step)},
                            tmp_path / "pre.result.json")
    assert pre["import_mode"] == 2
    res = newasm.run_script(ws, Path(boardlib.__file__).resolve().parents[3] / "templates" / "freecad-pcba" /
                            "import-step.py",
                            {"XD_STEP": str(step), "XD_OUT": str(out), "XD_TRACE_ID": TID, "XD_VERSION": "canary/v0.1.0",
                             "XD_VARIANT": "", "XD_BOARD": "canary", "XD_COMMIT": "", "XD_THICKNESS": "1.6"},
                            tmp_path / "import.result.json", exe="FreeCAD")
    assert sorted(c["label"] for c in res["components"]) == ["PCB", "R1", "R2"], res
    assert res["links"] == 3 and res["models"] == 3 and res["solids"] == 3
    assert boardlib.board_props(out)["Version"] == "canary/v0.1.0"
    assert res["bbox_min_mm"][2] <= -1.6 + 1e-6          # board frame: z = 0 on the top face
    assert len(boardlib.board_colours(out)) == 3
