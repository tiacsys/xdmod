"""ME design output (task 5.26): `curatrix cam <repo> <asm>`, the drawing sheet, the flat BOM and
CK-F19 (version mark on printed parts)."""
import csv
import json
import shutil
import subprocess

import pytest

from curatrix import cam, checkcfg, checks, mecam
from curatrix.ws import Repo, Workspace
from helpers import FIXTURES, git_init
from test_meassemblies import _prop, fcstd

CFG = 'version: 1\ncad: {freecad: ["parts/*.FCStd", "assemblies/**/*.FCStd", "lib/**/*.FCStd"]}\n'


def _commit(repo, msg):
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", msg], check=True)


def _run(root, repo, fn):
    ctx = checks.Ctx(Workspace(root), Repo("r", repo, "r"), checkcfg.load(repo / "checks.yaml", root), "local",
                     False, None, root / "out")
    (root / "out").mkdir(exist_ok=True)
    r = checks.Result("X", "X", level="warning")
    getattr(checks, fn)(ctx, r)
    return r.findings


# ------------------------------------------------------------------ plain Python
def test_f19_version_face(tmp_path):
    """CK-F19 planted: a printed part (PrintProfile) without an LCS with Role = version-emboss."""
    root = tmp_path / "ws"
    repo = git_init(root / "r")
    (repo / "checks.yaml").write_text(CFG)
    fcstd(repo / "parts" / "p.FCStd", {"Box": ("Part::Box", [_prop("TraceID", "ME-PART-0001", group="Trace"),
                                                             _prop("PrintProfile", "pla", group="BOM")])})
    fcstd(repo / "parts" / "q.FCStd", {"Box": ("Part::Box", [_prop("TraceID", "ME-PART-0002", group="Trace")])})
    f = _run(root, repo, "c_version_face")
    assert len(f) == 1 and f[0].startswith("parts/p.FCStd: printed part Box has no version mark"), f
    fcstd(repo / "parts" / "p.FCStd", {"Box": ("Part::Box", [_prop("TraceID", "ME-PART-0001", group="Trace"),
                                                             _prop("PrintProfile", "pla", group="BOM")]),
                                       "VersionMark": ("Part::LocalCoordinateSystem",
                                                       [_prop("Role", "version-emboss", group="Version")])})
    assert _run(root, repo, "c_version_face") == []


def test_bom_rows_and_totals(tmp_path):
    repo = tmp_path
    rows = [{"file": str(repo / "parts/a.FCStd"), "object": "Box", "label": "A", "TraceID": "ME-PART-0001",
             "PrintProfile": "pla", "Material": "PLA"},
            {"file": str(repo / "parts/a.FCStd"), "object": "Box", "label": "A", "TraceID": "ME-PART-0001",
             "PrintProfile": "pla", "Material": "PLA"},
            {"file": str(repo / "lib/screw.FCStd"), "object": "Screw", "label": "Screw", "TraceID": "ME-PART-0005",
             "Standard": "ISO 4762 M3x10, A2"}]
    b = mecam.bom_rows(rows, repo)
    assert [(r["item"], r["kind"], r["qty"], r["file"]) for r in b] == [(1, "fastener", 1, "lib/screw.FCStd"),
                                                                       (2, "printed", 2, "parts/a.FCStd")]
    mecam._write_csv(tmp_path / "bom.csv", b)
    last = list(csv.DictReader(open(tmp_path / "bom.csv")))[-1]
    assert (last["item"], last["qty"]) == ("total", "3")


def test_sheet_svg_and_pdf():
    """The drawing sheet from TechDraw view SVGs: paths with lines, arcs and curves; a PDF without a tool."""
    view = ('<g><path d=" M 0 0 L 10 0 L 10 5 Z " /><path d="M 0 0 A 5 5 0 0 1 10 0"/>'
            '<path d="M 0 0 C 1 1 2 1 3 0"/><circle cx="5" cy="5" r="2"/></g>')
    ps = mecam._paths(view)
    assert len(ps) == 4 and ps[0] == [(0.0, 0.0), (10.0, 0.0), (10.0, 5.0), (0.0, 0.0)]
    assert abs(min(y for _, y in ps[1]) + 5) < 0.2 or abs(max(y for _, y in ps[1]) - 5) < 0.2   # a half circle
    lines, texts = mecam.sheet({k: view for k in mecam.VIEWS}, {"assembly": "fx", "version": "fx/v1.0.0"}, True)
    assert any(t[3] == "PREVIEW" for t in texts) and any("Version: fx/v1.0.0" == t[3] for t in texts)
    pdf = mecam.sheet_pdf(lines, texts)
    assert pdf.startswith(b"%PDF-1.4") and pdf.rstrip().endswith(b"%%EOF") and b"(PREVIEW) Tj" in pdf
    svg = mecam.sheet_svg(lines, texts)
    assert svg.count("<polyline") == len(lines) and "PREVIEW" in svg
    assert 'viewBox="-2.000 -7.000' in mecam.wrap_svg(view)


def test_short_version(tmp_path):
    repo = git_init(tmp_path / "r")
    (repo / "assemblies" / "fx").mkdir(parents=True)
    (repo / "assemblies" / "fx" / "a.txt").write_text("a")
    _commit(repo, "a")
    subprocess.run(["git", "-C", str(repo), "tag", "fx/v1.2.0"], check=True)
    subprocess.run(["git", "-C", str(repo), "branch", "-M", "main"], check=True)
    v, rel, short = mecam.version(repo, "fx", repo / "assemblies" / "fx")
    assert (v, rel, short) == ("fx/v1.2.0", True, "v1.2.0")
    (repo / "parts").mkdir()
    (repo / "parts" / "p.txt").write_text("p")                     # a shared folder changes: a preview
    v, rel, short = mecam.version(repo, "fx", repo / "assemblies" / "fx")
    assert (v, rel, short) == ("fx/v1.2.0-dirty-preview", False, "v1.2.0P")


# ------------------------------------------------------------------ with FreeCAD
def _fixture(tmp_path, repo, extra=None):
    from curatrix.newasm import run_script
    run_script(Workspace(tmp_path / "ws"), FIXTURES / "freecad" / "make_me_fixture.py",
               {"XD_DIR": str(repo), **(extra or {})}, tmp_path / "fixture.result.json")
    for bak in repo.rglob("*.FCBak"):
        bak.unlink()


@pytest.mark.tools
def test_me_cam_run(tmp_path):
    """`curatrix cam` on the FreeCAD fixture: per variant STEP, 3MF and STL of the printed part with
    the version embossed (one valid solid), print profile, views, drawing SVG and PDF, exploded view,
    BOM; preview marking; output only under build/; the sources unchanged. Planted: a printed part
    without a version mark stops the run."""
    if shutil.which("FreeCADCmd") is None:
        pytest.skip("FreeCADCmd not installed")
    root = tmp_path / "ws"
    repo = git_init(root / "r")
    (repo / "checks.yaml").write_text(CFG)
    _fixture(tmp_path, repo)
    (repo / "print").mkdir()
    (repo / "print" / "pla.ini").write_text("layer_height = 0.2\n")
    (repo / "assemblies" / "fx" / "explode.yaml").write_text("A: [0, 0, 0]\nB: [0, 0, 20]\n")
    _commit(repo, "fixture")
    ws = Workspace(root)
    cfg = checkcfg.load(repo / "checks.yaml", root)
    rec = mecam.run(ws, Repo("r", repo, "r"), cfg, "fx", log=lambda *_: None)[0]
    assert rec["kind"] == "assembly" and rec["version"].startswith("fx/v0.0.0-1-g") and rec["version"].endswith("-preview")
    assert rec["variants"] == ["SYS-CFG-0002"] and rec["emboss"] == "v0.0.0P" and rec["sources_unchanged"]
    top = ws.build("r") / "cam" / "fx" / rec["version"].split("/", 1)[1]
    files = set(rec["files"])
    for f in ("fx.step", "parts/box-a.stl", "parts/box-a.3mf", "print/pla.ini", "drawing.svg", "drawing.pdf",
              "exploded.svg", "bom.csv", "views/front.svg", "views/iso.svg"):
        assert f"fx/SYS-CFG-0002/{f}" in files, f
    e = rec["per_variant"]["SYS-CFG-0002"]["embossed"]["box-a"]
    assert e["solids"] == 1 and e["valid"] and e["volume_after"] > e["volume_before"]
    assert rec["per_variant"]["SYS-CFG-0002"]["moves"]["B"] == [0, 0, 20]
    assert "PREVIEW" in (top / "fx" / "SYS-CFG-0002" / "drawing.svg").read_text()
    bom = list(csv.DictReader(open(top / "fx" / "SYS-CFG-0002" / "bom.csv")))
    assert {(r["id"], r["qty"]) for r in bom if r["item"] != "total"} >= {("ME-PART-0001", "2"), ("ME-PART-0002", "2")}
    assert json.loads((top / "cam.json").read_text())["kind"] == "assembly"
    assert subprocess.run(["git", "-C", str(repo), "status", "--porcelain"], capture_output=True, text=True).stdout == ""
    rec2, _, why = mecam.current(ws.build("r") / "cam", "fx", repo, repo / "assemblies" / "fx")
    assert rec2 is not None and rec2["version"] == rec["version"], why
    # planted: the printed part without its version mark
    shutil.rmtree(repo / "parts")
    _fixture(tmp_path, repo, {"XD_NO_MARK": "1"})
    with pytest.raises(cam.CamError, match="no version mark"):
        mecam.run(ws, Repo("r", repo, "r"), cfg, "fx", log=lambda *_: None)
