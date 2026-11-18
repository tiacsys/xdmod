"""ME design output (task 5.26): `curatrix cam <repo> <asm>`, the drawing sheet, the flat BOM and
CK-F19 (version mark on printed parts)."""
import csv
import json
import shutil
import subprocess
import zipfile

import pytest

from curatrix import blender, cam, checkcfg, checks, mecam
from curatrix.ws import Repo, Workspace
from helpers import FIXTURES, git_init
from test_meassemblies import _assembly, _prop, fcstd

REAL_BLENDER_AVAILABLE = blender.available


@pytest.fixture(autouse=True)
def _no_blender(monkeypatch):
    """Blender is optional and not pinnable: the tests see none unless they ask for it."""
    monkeypatch.setattr(blender, "available", lambda ws: False)


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
             "Standard": "ISO 4762 M3x10, A2"},
            {"file": str(repo.parent / "lib/boards/b/b-v0.1.0.FCStd"), "object": "Board", "label": "b",
             "TraceID": "EE-PCBA-0001", "Board": "b", "Version": "b/v0.1.0"}]
    b = mecam.bom_rows(rows, repo)
    assert [(r["item"], r["kind"], r["qty"], r["name"]) for r in b] == [(1, "board", 1, "b b/v0.1.0"),
                                                                       (2, "fastener", 1, "Screw"),
                                                                       (3, "printed", 2, "A")]
    assert b[2]["file"] == "parts/a.FCStd" and b[0]["file"] == "../lib/boards/b/b-v0.1.0.FCStd"
    mecam._write_csv(tmp_path / "bom.csv", b)
    last = list(csv.DictReader(open(tmp_path / "bom.csv")))[-1]
    assert (last["item"], last["qty"]) == ("total", "4")


def test_sheet_svg_and_pdf():
    """The drawing sheet from TechDraw view SVGs: paths with lines, arcs and curves; a PDF without a tool."""
    view = ('<g><path d=" M 0 0 L 10 0 L 10 5 Z " /><path d="M 0 0 A 5 5 0 0 1 10 0"/>'
            '<path d="M 0 0 C 1 1 2 1 3 0"/><circle cx="5" cy="5" r="2"/></g>')
    ps = mecam._paths(view)
    assert len(ps) == 4 and ps[0] == [(0.0, 0.0), (10.0, 0.0), (10.0, 5.0), (0.0, 0.0)]
    assert abs(min(y for _, y in ps[1]) + 5) < 0.2 or abs(max(y for _, y in ps[1]) - 5) < 0.2   # a half circle
    # TechDraw's own circle form has a blank before the "=" (the canary base plate's top view)
    ps = mecam._paths('<g><circle cx ="-11" cy ="6" r ="4" /><path d ="M 0 0 L 4 0" /></g>')
    assert len(ps) == 2 and ps[0] == [(0.0, 0.0), (4.0, 0.0)] and abs(max(x for x, _ in ps[1]) + 7) < 1e-6
    lines, texts = mecam.sheet({k: view for k in mecam.VIEWS}, {"assembly": "fx", "version": "fx/v1.0.0"}, True)
    assert any(t[3] == "PREVIEW" for t in texts) and any("Version: fx/v1.0.0" == t[3] for t in texts)
    pdf = mecam.sheet_pdf(lines, texts)
    assert pdf.startswith(b"%PDF-1.4") and pdf.rstrip().endswith(b"%%EOF") and b"(PREVIEW) Tj" in pdf
    svg = mecam.sheet_svg(lines, texts)
    assert svg.count("<polyline") == len(lines) and "PREVIEW" in svg
    assert any(t[3] == mecam.NOTE for t in texts) and any(t[3] == "Projection: first angle (ISO 128 method 1)"
                                                         for t in texts)
    assert 'viewBox="-2.000 -7.000' in mecam.wrap_svg(view)


def test_sheet_first_angle_aligned_standard_scale():
    """The sheet: a standard scale; first angle (right view left of the front view, top view below
    it); the front view aligned with the top view (same x) and with the right view (same y)."""
    def rect(w, h):
        return f'<path d="M 0 0 L {w} 0 L {w} {h} L 0 {h} Z"/>'
    views = {"front": rect(20, 5), "top": rect(20, 10), "right": rect(10, 5), "iso": rect(25, 15)}
    lines, texts = mecam.sheet(views, {}, False)
    scale = next(t[3] for t in texts if t[3].startswith("Scale: "))
    assert scale in {f"Scale: {mecam.scale_text(s)}" for s in mecam.STANDARD_SCALES} and scale == "Scale: 10:1", scale
    boxes = {}
    for k in ("right", "front", "top"):                   # the views are drawn in this order after the frame
        pl = lines[1 + len(boxes)]
        boxes[k] = (min(p[0] for p in pl), min(p[1] for p in pl), max(p[0] for p in pl), max(p[1] for p in pl))
    r, f, t = boxes["right"], boxes["front"], boxes["top"]
    assert r[2] < f[0] and t[1] > f[3]                   # first angle
    assert (f[0], f[2]) == (t[0], t[2]) and (f[1], f[3]) == (r[1], r[3])   # aligned
    assert (round(f[2] - f[0], 6), round(r[2] - r[0], 6)) == (200, 100)    # 10:1
    assert mecam.standard_scale(8.24) == 5 and mecam.standard_scale(0.3) == 0.2 and mecam.scale_text(0.2) == "1:5"


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


def _cam_repo(tmp_path, configs=""):
    """A repo with an assembly fx (one link to parts/p.FCStd, Configs on the link when given)."""
    root = tmp_path / "ws"
    repo = git_init(root / "r")
    (repo / "checks.yaml").write_text(CFG)
    fcstd(repo / "parts" / "p.FCStd", {"Box": ("Part::Box", [_prop("TraceID", "ME-PART-0001", group="Trace")])})
    p = _assembly(repo, name="fx", links=(("../../parts/p.FCStd", "Box"),))
    if configs:
        with zipfile.ZipFile(p) as z:
            xml = z.read("Document.xml").decode()
        xml = xml.replace('<Object name="Link0"><Properties>',
                          f'<Object name="Link0"><Properties>{_prop("Configs", configs, group="Trace")}')
        with zipfile.ZipFile(p, "w") as z:
            z.writestr("Document.xml", xml)
    _commit(repo, "fx")
    return root, repo


def _fake_script(edges=1, touch=None, painted=1):
    """A stand-in for cam-asm.py: writes the views and renderings, reports the edges and the painted
    facets, optionally changes a file; and for check-asm.py (the findings of the assembly document,
    task 5.27): no findings."""
    def run_script(ws, script, env, result):
        if "XD_FILES" in env:
            return {"ok": True, "recompute": [], "parts": [], "solids": [], "assemblies": []}
        dest = __import__("pathlib").Path(env["XD_OUT"])
        (dest / "views").mkdir(parents=True, exist_ok=True)
        for v in mecam.VIEWS:
            (dest / "views" / f"{v}.svg").write_text('<path d="M 0 0 L 10 0 L 10 5 Z"/>')
        (dest / "exploded.svg").write_text('<path d="M 0 0 L 10 0"/>')
        (dest / "renderings").mkdir(parents=True, exist_ok=True)
        for v in mecam.VIEWS:
            (dest / "renderings" / f"{v}.png").write_bytes(b"\x89PNG")
        if touch is not None:
            touch.write_bytes(touch.read_bytes() + b"\n")
        return {"edges": {**{v: 4 for v in mecam.VIEWS}, "right": edges, "exploded": 4}, "bom": [],
                "painted": {**{v: 100 for v in mecam.VIEWS}, "iso": painted}}
    return run_script


def test_cam_variants_base(tmp_path, monkeypatch):
    """Configs named on a link give their variant and `base` (only the links without Configs: every
    configuration no link names); without Configs one variant `all`."""
    import curatrix.newasm as newasm
    monkeypatch.setattr(newasm, "run_script", _fake_script())
    for configs, want in (("", ["all"]), ("SYS-CFG-0002", ["SYS-CFG-0002", "base"])):
        root, repo = _cam_repo(tmp_path / (configs or "none"), configs)
        rec = mecam.run(Workspace(root), Repo("r", repo, "r"), checkcfg.load(repo / "checks.yaml", root), "fx",
                        log=lambda *_: None)[0]
        assert rec["variants"] == want, rec["variants"]
        assert all(f"fx/{v}/mass.json" in rec["files"] for v in want)            # task 5.27
        top = Workspace(root).build("r") / "cam" / "fx" / rec["version"].split("/", 1)[1]
        assert json.loads((top / "findings.json").read_text())["rows"] == []


def test_cam_md5_guard_and_empty_view(tmp_path, monkeypatch):
    """Planted: a run that changes a source document fails (md5 before and after); a view without a
    visible edge and a rendering without a painted facet fail the run."""
    import curatrix.newasm as newasm
    root, repo = _cam_repo(tmp_path)
    ws, cfg = Workspace(root), checkcfg.load(repo / "checks.yaml", root)
    monkeypatch.setattr(newasm, "run_script", _fake_script(touch=repo / "parts" / "p.FCStd"))
    with pytest.raises(cam.CamError, match=r"changed the source documents .*parts/p.FCStd"):
        mecam.run(ws, Repo("r", repo, "r"), cfg, "fx", log=lambda *_: None)
    subprocess.run(["git", "-C", str(repo), "checkout", "--", "."], check=True)
    monkeypatch.setattr(newasm, "run_script", _fake_script(edges=0))
    with pytest.raises(cam.CamError, match=r"no visible edge in the view\(s\) right"):
        mecam.run(ws, Repo("r", repo, "r"), cfg, "fx", log=lambda *_: None)
    monkeypatch.setattr(newasm, "run_script", _fake_script(painted=0))
    with pytest.raises(cam.CamError, match=r"no painted facet in the rendering\(s\) iso"):
        mecam.run(ws, Repo("r", repo, "r"), cfg, "fx", log=lambda *_: None)
    monkeypatch.setattr(newasm, "run_script", _fake_script())
    rec = mecam.run(ws, Repo("r", repo, "r"), cfg, "fx", log=lambda *_: None)[0]
    assert rec["sources_unchanged"] and rec["renderings"]["marking"] == "PREVIEW"
    assert rec["renderings"]["method"] == "zbuffer"
    assert rec["per_variant"]["all"]["renderings"]["iso"] == "fx/all/renderings/iso.png"
    assert "fx/all/renderings/front.png" in rec["files"]


def test_cam_renders_with_blender_when_there(tmp_path, monkeypatch):
    """With Blender: cam-asm.py gets XD_SCENE (the glTF for Blender) and draws no renderings itself;
    render-asm.py runs per variant; cam.json says blender, not pinned. --no-blender (use_blender=False)
    and a missing Blender take the z-buffer renderer; a failing Blender stops the run with a hint."""
    import curatrix.newasm as newasm
    root, repo = _cam_repo(tmp_path)
    ws, cfg = Workspace(root), checkcfg.load(repo / "checks.yaml", root)
    seen = {}
    fake = _fake_script()

    def run_script(ws_, script, env, result):
        if "XD_FILES" in env:                     # check-asm.py (findings), not cam-asm.py
            return fake(ws_, script, env, result)
        seen["scene"] = env["XD_SCENE"]
        return {**fake(ws_, script, env, result), "painted": {}}
    calls = []

    def run_blender(ws_, script, env, result, exe=None):
        calls.append((script.name, env))
        return {"ok": True, "pixels": {v: 10 for v in mecam.VIEWS}, "seconds": {v: 1.0 for v in mecam.VIEWS}, "threads": 3,
                "blender": "5.2.3 LTS", "engine": "CYCLES", "device": "CPU", "samples": 32, "seed": 0}
    monkeypatch.setattr(newasm, "run_script", run_script)
    monkeypatch.setattr(blender, "available", lambda ws_: True)
    monkeypatch.setattr(blender, "run_script", run_blender)
    rec = mecam.run(ws, Repo("r", repo, "r"), cfg, "fx", log=lambda *_: None)[0]
    assert seen["scene"].endswith("all.scene.glb")
    assert [c[0] for c in calls] == ["render-asm.py"]
    env = calls[0][1]
    assert env["XD_OUT"].endswith("fx/all/renderings") and json.loads(env["XD_LABEL"])[0] == "fx  variant all"
    assert env["XD_RELEASE"] == "" and env["XD_FONT"].endswith(".ttf")
    r = rec["renderings"]
    assert r["method"] == "blender" and r["pinned"] is False and r["samples"] == 32 and r["marking"] == "PREVIEW"
    assert rec["per_variant"]["all"]["pixels"]["iso"] == 10 and rec["per_variant"]["all"]["painted"] == {}
    assert rec["renderings"]["threads"] == 3 and int(env["XD_THREADS"]) >= 1
    # --no-blender: the z-buffer renderer, no glTF
    monkeypatch.setattr(newasm, "run_script", _fake_script())
    rec = mecam.run(ws, Repo("r", repo, "r"), cfg, "fx", log=lambda *_: None, use_blender=False)[0]
    assert rec["renderings"]["method"] == "zbuffer" and len(calls) == 1
    # Blender fails: the run stops and names the way out
    monkeypatch.setattr(newasm, "run_script", run_script)

    def broken(*a, **k):
        raise blender.BlenderError("blender render-asm.py failed: boom")
    monkeypatch.setattr(blender, "run_script", broken)
    with pytest.raises(cam.CamError, match="boom.*--no-blender"):
        mecam.run(ws, Repo("r", repo, "r"), cfg, "fx", log=lambda *_: None)


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
    assert rec["renderings"]["method"] == "zbuffer"
    assert rec["kind"] == "assembly" and rec["version"].startswith("fx/v0.0.0-1-g") and rec["version"].endswith("-preview")
    assert rec["variants"] == ["SYS-CFG-0002", "base"] and rec["emboss"] == "v0.0.0P" and rec["sources_unchanged"]
    top = ws.build("r") / "cam" / "fx" / rec["version"].split("/", 1)[1]
    files = set(rec["files"])
    for f in ("fx.step", "parts/box-a.stl", "parts/box-a.3mf", "print/pla.ini", "drawing.svg", "drawing.pdf",
              "exploded.svg", "bom.csv", "views/front.svg", "views/iso.svg", "renderings/front.png",
              "renderings/top.png", "renderings/right.png", "renderings/iso.png"):
        assert f"fx/SYS-CFG-0002/{f}" in files, f
    e = rec["per_variant"]["SYS-CFG-0002"]["embossed"]["box-a"]
    assert e["solids"] == 1 and e["valid"] and e["volume_after"] > e["volume_before"]
    assert rec["per_variant"]["SYS-CFG-0002"]["moves"]["B"] == [0, 0, 20]
    assert "PREVIEW" in (top / "fx" / "SYS-CFG-0002" / "drawing.svg").read_text()
    # renderings: real PNGs of the 1600 x 1200 px canvas, painted, more facets with box-b (D) present
    png = (top / "fx" / "SYS-CFG-0002" / "renderings" / "iso.png").read_bytes()
    assert png[:8] == b"\x89PNG\r\n\x1a\n" and int.from_bytes(png[16:20], "big") == 1600
    pv = {v: rec["per_variant"][v]["painted"] for v in rec["variants"]}
    assert all(n > 0 for p in pv.values() for n in p.values()) and pv["SYS-CFG-0002"]["iso"] > pv["base"]["iso"], pv
    sc = rec["per_variant"]["base"]["render_scale"]                  # one scale for front, top and right
    assert sc["front"] == sc["top"] == sc["right"] > 0 and sc["iso"] > 0, sc
    for v, n in (("SYS-CFG-0002", "3"), ("base", "2")):        # D (box-b) only in SYS-CFG-0002
        bom = list(csv.DictReader(open(top / "fx" / v / "bom.csv")))
        assert {(r["id"], r["qty"]) for r in bom if r["item"] != "total"} >= {("ME-PART-0001", "2"), ("ME-PART-0002", n)}
    # the views keep z up: front x by z, top x by y, right y by z (base: x 0..26 with the sheet, y 0..20, z -10..20)
    size = {}
    for v in ("front", "top", "right"):
        b = mecam._bbox(mecam._paths((top / "fx" / "base" / "views" / f"{v}.svg").read_text()))
        size[v] = (round(b[2] - b[0], 1), round(b[3] - b[1], 1))
    assert size == {"front": (26.0, 30.0), "top": (26.0, 20.0), "right": (20.0, 30.0)}, size
    assert json.loads((top / "cam.json").read_text())["kind"] == "assembly"
    assert subprocess.run(["git", "-C", str(repo), "status", "--porcelain"], capture_output=True, text=True).stdout == ""
    rec2, _, why = mecam.current(ws.build("r") / "cam", "fx", repo, repo / "assemblies" / "fx")
    assert rec2 is not None and rec2["version"] == rec["version"], why
    # planted: the printed part without its version mark
    shutil.rmtree(repo / "parts")
    _fixture(tmp_path, repo, {"XD_NO_MARK": "1"})
    with pytest.raises(cam.CamError, match="no version mark"):
        mecam.run(ws, Repo("r", repo, "r"), cfg, "fx", log=lambda *_: None)


@pytest.mark.tools
def test_me_cam_run_blender(tmp_path, monkeypatch):
    """`curatrix cam` on the FreeCAD fixture with Blender (local only: Blender is optional, not
    pinnable, not in CI): FreeCADCmd writes the glTF, Blender renders the four views per variant,
    1600 x 1200 px PNGs, painted, method blender. Blender's user paths stay in the workspace's
    .xdmod/blender (here a temporary workspace)."""
    if shutil.which("FreeCADCmd") is None or shutil.which("blender") is None:
        pytest.skip("FreeCADCmd or blender not installed")
    monkeypatch.setattr(blender, "available", REAL_BLENDER_AVAILABLE)
    root = tmp_path / "ws"
    repo = git_init(root / "r")
    (repo / "checks.yaml").write_text(CFG)
    _fixture(tmp_path, repo)
    (repo / "print").mkdir()
    (repo / "print" / "pla.ini").write_text("layer_height = 0.2\n")
    _commit(repo, "fixture")
    ws = Workspace(root)
    rec = mecam.run(ws, Repo("r", repo, "r"), checkcfg.load(repo / "checks.yaml", root), "fx", log=lambda *_: None)[0]
    assert rec["renderings"]["method"] == "blender" and rec["renderings"]["pinned"] is False
    top = ws.build("r") / "cam" / "fx" / rec["version"].split("/", 1)[1]
    for v in rec["variants"]:
        assert (top / f"{v}.scene.glb").read_bytes()[:4] == b"glTF"
        assert all(n > 1000 for n in rec["per_variant"][v]["pixels"].values()), rec["per_variant"][v]
        assert rec["per_variant"][v]["facets"] > 0
        for view in mecam.VIEWS:
            png = (top / "fx" / v / "renderings" / f"{view}.png").read_bytes()
            assert png[:8] == b"\x89PNG\r\n\x1a\n" and int.from_bytes(png[16:20], "big") == 1600
            assert int.from_bytes(png[20:24], "big") == 1200
    assert (root / ".xdmod" / "blender" / "user").is_dir()
