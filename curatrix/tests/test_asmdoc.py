"""The assembly document (task 5.27): structure, indented BOM, CK-F12 for ME parts, materials,
mass and center of gravity, CK-D10 for assemblies."""
import json
import subprocess

from curatrix import asmdoc, checkcfg, checks, meassemblies
from curatrix.ws import Repo, Workspace
from helpers import git_init
from test_meassemblies import _prop, fcstd

CFG = 'version: 1\ncad: {freecad: ["parts/*.FCStd", "assemblies/**/*.FCStd", "lib/**/*.FCStd"]}\n'


def _group(*names):
    links = "".join(f'<Link value="{n}"/>' for n in names)
    return f'<Property name="Group" type="App::PropertyLinkList"><LinkList count="{len(names)}">{links}</LinkList></Property>'


def _link(file, obj, configs=""):
    ps = [_prop("LinkedObject", (file, obj), "App::PropertyXLink")]
    if configs:
        ps.append(_prop("Configs", configs, group="Trace"))
    return ("App::Link", ps)


def _asm(tid, label, *kids):
    return ("Assembly::AssemblyObject", [_prop("Label", label), _prop("TraceID", tid, group="Trace"), _group(*kids)])


def _setup(tmp_path, ext=True):
    """Top assembly ``top``: the skeleton, two printed brackets (one only in config SYS-CFG-0002),
    two links to the sub-assembly ``arm`` (a printed link and four screws), a library bearing
    without MPN, an own plate without Material, a board model of the board library outside the
    repo (``ext``) and a link to a missing board model."""
    root = tmp_path / "ws"
    repo = git_init(root / "r")
    (repo / "checks.yaml").write_text(CFG)
    a = repo / "assemblies" / "top"
    fcstd(a / "top-skeleton.FCStd", {"Skeleton": ("App::Part", [])})
    fcstd(a / "top.FCStd", {
        "Assembly": _asm("ME-ASM-0001", "top", "Skeleton", "B1", "B2", "Arm1", "Arm2", "Bearing", "Plate", "Board", "Gone"),
        "Skeleton": _link("top-skeleton.FCStd", "Skeleton"),
        "B1": _link("../../parts/bracket.FCStd", "Body"),
        "B2": _link("../../parts/bracket.FCStd", "Body", "SYS-CFG-0002"),
        "Arm1": _link("arm.FCStd", "Assembly"), "Arm2": _link("arm.FCStd", "Assembly"),
        "Bearing": _link("../../lib/bearing.FCStd", "Bearing"),
        "Plate": _link("parts/plate.FCStd", "Plate"),
        "Board": _link("../../../lib/boards/canary-board/canary-board-v0.1.0.FCStd", "Board"),
        "Gone": _link("../../../lib/boards/old/old-v0.1.0.FCStd", "Board")})
    fcstd(a / "arm.FCStd", {"Assembly": _asm("ME-ASM-0002", "arm", "L", "S1", "S2", "S3", "S4"),
                            "L": _link("parts/link.FCStd", "Body"),
                            **{f"S{i}": _link("../../lib/screw.FCStd", "Screw") for i in range(1, 5)}})
    fcstd(a / "parts" / "link.FCStd", {"Body": ("Part::Box", [_prop("Label", "link"), _prop("TraceID", "ME-PART-0003", group="Trace"),
                                                              _prop("Material", "PETG"), _prop("PrintProfile", "petg")])})
    fcstd(a / "parts" / "plate.FCStd", {"Plate": ("Part::Box", [_prop("Label", "plate"), _prop("TraceID", "ME-PART-0004", group="Trace")])})
    fcstd(repo / "parts" / "bracket.FCStd", {"Body": ("Part::Box", [
        _prop("Label", "bracket"), _prop("TraceID", "ME-PART-0002", group="Trace"), _prop("Material", "PLA"), _prop("PrintProfile", "pla")])})
    fcstd(repo / "lib" / "screw.FCStd", {"Screw": ("Part::Feature", [_prop("Standard", "ISO 4762 M3x10, A2"),
                                                                    _prop("Material", "A2")])})
    fcstd(repo / "lib" / "bearing.FCStd", {"Bearing": ("Part::Feature", [_prop("Label", "bearing"), _prop("Manufacturer", "SKF")])})
    if ext:
        fcstd(root / "lib" / "boards" / "canary-board" / "canary-board-v0.1.0.FCStd", {"Board": ("App::Part", [
            _prop("TraceID", "EE-PCBA-0001", group="Trace"), _prop("Version", "canary-board/v0.1.0", group="Board"),
            _prop("Board", "canary-board", group="Board")])})
    cfg = checkcfg.load(repo / "checks.yaml", root)
    return root, repo, cfg, a


def test_tree_and_indented_bom(tmp_path):
    _, repo, cfg, a = _setup(tmp_path)
    t = asmdoc.tree(cfg, a)
    assert t.id == "ME-ASM-0001" and [c.link for c in t.children][0] == "B1"
    assert "Skeleton" not in [c.link for c in t.children]
    assert asmdoc.variants(t) == ["SYS-CFG-0002", "base"]
    rows = asmdoc.indented_bom(t)
    got = [(r["pos"], r["level"], r["kind"], r["designation"], r["qty"]) for r in rows]
    assert got == [
        ("1", 0, "assembly", "arm", {"SYS-CFG-0002": 2, "base": 2}),
        ("1.1", 1, "printed", "link", {"SYS-CFG-0002": 1, "base": 1}),
        ("1.2", 1, "fastener", "ISO 4762 M3x10, A2", {"SYS-CFG-0002": 4, "base": 4}),
        ("2", 0, "printed", "bracket", {"SYS-CFG-0002": 2, "base": 1}),
        ("3", 0, "part", "plate", {"SYS-CFG-0002": 1, "base": 1}),
        ("4", 0, "bought", "bearing", {"SYS-CFG-0002": 1, "base": 1}),
        ("5", 0, "board", "canary-board canary-board/v0.1.0", {"SYS-CFG-0002": 1, "base": 1}),
        ("6", 0, "unresolved", "Gone", {"SYS-CFG-0002": 1, "base": 1})], got
    board = next(r for r in rows if r["kind"] == "board")
    assert board["document"] == "pcba-canary-board" and board["id"] == "EE-PCBA-0001"
    subs = asmdoc.sub_assemblies(t)
    assert [(p, n.id) for p, n in subs] == [("Arm1", "ME-ASM-0002")]
    assert asmdoc.uses(t, subs[0][1]) == ["Arm1", "Arm2"]


def test_f12_me_bom_fields(tmp_path):
    """CK-F12 planted for ME: a bought library part without MPN, an own part without Material, a
    link to a board model that is not there; standard fasteners and boards need nothing."""
    root, repo, cfg, a = _setup(tmp_path)
    ctx = checks.Ctx(Workspace(root), Repo("r", repo, "r"), cfg, "local", False, None, root / "out")
    r = checks.Result("CK-F12", "CK-F12", level="warning")
    checks.c_bom_fields(ctx, r)
    f = r.findings
    assert len(f) == 3, f
    assert f[0].startswith("lib/bearing.FCStd#Bearing (bearing): a bought part without MPN")
    assert f[1].startswith("assemblies/top/parts/plate.FCStd#Plate (plate): an own part without a Material")
    assert "the link Gone points to an object that is not there" in f[2]


def test_materials(tmp_path):
    _, _, cfg, a = _setup(tmp_path)
    rows = asmdoc.materials(asmdoc.tree(cfg, a), {"pla": 1.24, "a2": 7.9})
    assert [(r["material"], r["density"], r["parts"], r["print_profiles"]) for r in rows] == [
        ("A2", 7.9, ["ISO 4762 M3x10, A2"], []), ("PETG", None, ["link"], ["petg"]),
        ("PLA", 1.24, ["bracket"], ["pla"]), ("", None, ["bearing", "plate"], [])]


def test_mass_and_center_of_gravity():
    rows = [{"path": "A", "label": "a", "Material": "PLA", "volume": 1000.0, "com": [0, 0, 0]},
            {"path": "Arm1/B", "label": "b", "Material": "steel", "Mass": "0.01 kg", "volume": 1.0, "com": [10, 0, 0]},
            {"path": "Arm1/C", "label": "c", "Material": "x", "Density": "2 g/cm^3", "volume": 500.0, "com": [0, 4, 0]},
            {"path": "D", "label": "d", "Material": "unknown", "volume": 5.0, "com": [1, 1, 1]}]
    m = asmdoc.mass(rows, {"pla": 1.24})
    assert [p["mass_g"] for p in m["parts"]] == [1.24, 10.0, 1.0, None]
    assert [p["source"] for p in m["parts"]] == ["material PLA", "Mass property", "Density property",
                                                "no density for Material 'unknown' (data/materials.yaml)"]
    assert m["total_g"] == 12.24 and not m["complete"] and m["missing"] == ["D"]
    assert m["cog_mm"] == [round(100 / 12.24, 3), round(4 / 12.24, 3), 0.0]
    bad = asmdoc.mass([{"path": "E", "Mass": "5", "volume": 1.0, "com": [0, 0, 0]},
                       {"path": "F", "Density": "90 g/cm^3", "volume": 1.0, "com": [0, 0, 0]},
                       {"path": "G", "Density": "1.2", "volume": 1.0, "com": [0, 0, 0]}], {})
    assert [p["mass_g"] for p in bad["parts"]] == [None, None, None] and bad["missing"] == ["E", "F", "G"]
    assert [p["source"] for p in bad["parts"]] == ["Mass '5' needs a unit (g, kg, mg)",
                                                    "Density '90 g/cm^3' is 90 g/cm³, outside 0.01..25",
                                                    "Density '1.2' needs a unit (g/cm^3, kg/m^3)"]
    assert m["parts"][3]["source"] == "no density for Material 'unknown' (data/materials.yaml)"
    s = asmdoc.sub_mass(m, "Arm1")
    assert s["total_g"] == 11.0 and s["cog_mm"] == [round(100 / 11, 3), round(4 / 11, 3), 0.0] and s["complete"]


def test_d10_assembly_output(tmp_path):
    """CK-D10 planted for ME: no cam output of the current commit; a clean run, then an uncommitted
    change in the assembly folder (stale); a run on that dirty tree, then a shared part deleted
    (stale, also without any file time); the same tree_state hash as the board document."""
    from curatrix import cam, mecam
    root, repo, cfg, a = _setup(tmp_path, ext=False)
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", "asm"], check=True)
    ctx = checks.Ctx(Workspace(root), Repo("r", repo, "r"), cfg, "local", False, None, root / "out")

    def run():
        r = checks.Result("CK-D10", "CK-D10", level="warning")
        checks.c_cam_output(ctx, r)
        return r.findings
    f = run()
    assert len(f) == 1 and f[0].startswith("top: no `curatrix cam` output of top for commit"), f
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()

    def cam_json(n):
        top = root / "build" / "r" / "cam" / "top" / f"v0.0.0-1-gabc{n}-preview"
        top.mkdir(parents=True)
        (top / "cam.json").write_text(json.dumps({
            "kind": "assembly", "project": "top", "commit": head, "version": f"top/v0.0.0-1-gabc{n}-preview",
            "variants": ["all"], "tree_state": cam.tree_state(repo, a, *mecam.shared_folders(repo))}))
    cam_json(1)
    assert run() == []
    (a / "top.FCStd").write_bytes((a / "top.FCStd").read_bytes() + b"\0")     # uncommitted change
    stale = "uncommitted changes that differ from those of the `curatrix cam` run"
    assert any(stale in x for x in run())
    cam_json(2)
    assert run() == []
    (repo / "lib" / "bearing.FCStd").unlink()                                     # a shared part deleted
    assert any(stale in x for x in run())
    subprocess.run(["git", "-C", str(repo), "checkout", "--", "."], check=True)   # clean: only a clean run counts
    assert run() == []
    assert meassemblies.top_folders(cfg) == [a]
