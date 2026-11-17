"""The board library (task 5.29, XD-ADR-0139): CK-F20 on the library, CK-F21 on an ME repo, the release
guard of `curatrix cam --library`, the checks.yaml keys. Plain Python; the FreeCAD files are minimal
zips like those of `curatrix cam --board-model`."""
import json
import subprocess

import pytest

from curatrix import boardlib, checkcfg, checks
from curatrix.ws import Repo, Workspace
from helpers import git_init
from test_meassemblies import _prop, fcstd

TID = "EE-PCBA-0001"


def board_file(path, version, variant="", tid=TID, commit=""):
    props = [_prop("TraceID", tid, group="Trace"), _prop("Version", version, group="Board"),
             _prop("Variant", variant, group="Board"), _prop("Commit", commit, group="Board")]
    return fcstd(path, {"Board": ("App::Part", props), "Shape": ("Part::Feature", [])})


def _git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


def ee_repo(root, tags=("canary/v0.1.0",), tid=TID):
    ee = git_init(root / "ee")
    pro = ee / "pcba" / "canary" / "canary.kicad_pro"
    pro.parent.mkdir(parents=True)
    pro.write_text(json.dumps({"text_variables": {"TraceID": tid, "XD_VERSION": "unversioned"}}))
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
    f = "\n".join(_run(ctx, checks.c_board_library))
    assert "canary-v0.2.0.FCStd: no tag canary/v0.2.0" in f
    assert "board.FCStd: not boards/<board>/<board>-vX.Y.Z" in f
    assert "canary-v0.1.0-alt.FCStd: Version 'canary/v0.0.9' does not match" in f
    assert "canary-v0.1.0-x.FCStd: TraceID ME-PART-0001 is not an EE-PCBA ID" in f
    assert "canary-v0.1.0-x.FCStd: Commit 000000000000 is not the commit of tag" in f
    assert "TraceID ME-PART-0001, but the project at canary/v0.1.0 is EE-PCBA-0001" in f
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
