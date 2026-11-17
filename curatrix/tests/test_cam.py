"""EE design output (task 5.20): `curatrix cam`, the jobset rules (CK-F10) and the version
variable (CK-F11) (XD-ADR-0142, XD-ADR-0140)."""
import copy
import csv
import json
import shutil
import subprocess

import pytest

from curatrix import cam, checkcfg, checks, eeprojects
from curatrix.ws import Repo, Workspace
from helpers import FIXTURES, git_init

DRC = FIXTURES / "kicad" / "drc"
YAML = 'version: 1\ncad: {projects: ["pcba/*/*.kicad_pro"]}\n'


def _repo(tmp_path, jobset=True):
    root = tmp_path / "ws"
    repo = git_init(root / "r")
    (repo / "checks.yaml").write_text(YAML)
    d = repo / "pcba" / "drc"
    d.mkdir(parents=True)
    for f in ("drc.kicad_pro", "drc.kicad_sch", "drc.kicad_pcb"):
        shutil.copy(DRC / f, d / f)
    if jobset:
        (d / "drc.kicad_jobset").write_text(cam.dumps(cam.expected(Workspace(root), "drc", ["default", "alt"])))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "board")
    _git(repo, "branch", "-M", "main")
    return root, repo


def _git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, text=True).stdout


def _run(root, repo, cid, fn):
    ctx = checks.Ctx(Workspace(root), Repo("r", repo, "r"), checkcfg.load(repo / "checks.yaml", root), "local",
                     False, None, root / "out")
    (root / "out").mkdir(exist_ok=True)
    r = checks.Result(cid, cid, level="warning")
    getattr(checks, fn)(ctx, r)
    return r.findings


def _project(repo):
    cfg = checkcfg.load(repo / "checks.yaml", repo.parent)
    return eeprojects.discover(cfg)[0]


# ------------------------------------------------------------------ CK-F10
def test_template_and_expected_jobset(tmp_path):
    """The shared template has every EE-3 output, BOM delimiters, no ERC/DRC/statistics/execute job,
    jobs without a variant first, output under ${XD_CAM_OUT}; per variant one job per
    variant-dependent output."""
    ws = Workspace(tmp_path)
    t = cam.template(ws, "b")
    types = [j["type"] for j in t["jobs"]]
    for want in ("pcb_export_gerbers", "pcb_export_drill", "pcb_export_pos", "sch_export_netlist", "pcb_export_3d",
                 "sch_export_plot_pdf", "sch_export_plot_svg", "sch_export_bom"):
        assert want in types
    renders = [j["settings"] for j in t["jobs"] if j["type"] == "pcb_render"]
    assert sorted((s["side"], s["perspective"]) for s in renders) == [("bottom", False), ("top", False), ("top", True)]
    assert not set(types) & set(cam.FORBIDDEN)
    first_var = next(i for i, j in enumerate(t["jobs"]) if j["type"] in cam.VARIANT_KEY)
    assert all(j["type"] in cam.VARIANT_KEY for j in t["jobs"][first_var:])
    assert [o["settings"]["output_path"] for o in t["outputs"]] == ["${XD_CAM_OUT}/b"]
    e = cam.expected(ws, "b", ["v1", "v2"])
    ids = [j["id"] for j in e["jobs"]]
    assert "bom" not in ids and {"bom-v1", "bom-v2", "render-3d-v2", "pos-v1"} <= set(ids)
    bom2 = next(j for j in e["jobs"] if j["id"] == "bom-v2")["settings"]
    assert (bom2["output_filename"], bom2["variant_names"]) == ("bom-v2.csv", ["v2"])


def test_f10_jobset(tmp_path):
    """CK-F10 planted: an Execute Command job, Copy Files outside the output, a statistics job, a
    BOM without delimiters, a variant job that differs from its template job, a variant the project
    lacks, a job without a variant after a variant job, an output outside ${XD_CAM_OUT}, a missing
    template job."""
    root, repo = _repo(tmp_path)
    assert _run(root, repo, "CK-F10", "c_jobset") == []
    p = repo / "pcba" / "drc" / "drc.kicad_jobset"
    js = json.loads(p.read_text())
    good = copy.deepcopy(js)
    by = {j["id"]: j for j in js["jobs"]}
    by["bom-alt"]["settings"]["fields_ordered"] = ["Reference", "Value"]
    del by["bom-default"]["settings"]["field_delimiter"]
    by["pos-alt"]["settings"]["variant"] = "gone"
    js["jobs"] = [j for j in js["jobs"] if j["id"] != "render-3d-default"]
    js["jobs"] += [{"id": "x", "type": "special_execute", "settings": {"command": "rm -rf /"}},
                   {"id": "c", "type": "special_copyfiles", "settings": {"source": "*.kicad_pcb", "dest": "../../.."}},
                   {"id": "s", "type": "pcb_export_stats", "settings": {"output_format": "json"}},
                   {"id": "late", "type": "sch_export_netlist", "settings": {"output_filename": "n.xml", "format": "xml"}}]
    js["outputs"][0]["settings"]["output_path"] = "../out"
    p.write_text(json.dumps(js))
    f = "\n".join(_run(root, repo, "CK-F10", "c_jobset"))
    for want in ("job 'x': an Execute Command job", "job 'c': Copy Files to '../../..', outside the output folder",
                 "job 's': a statistics job", "job 'bom-default': BOM without field_delimiter",
                 "job 'bom-alt' differs from the template job 'bom'", "job 'pos-alt' names variant 'gone'",
                 "job 'late' has no variant but comes after the variant job",
                 "output 'out': '../out' is not under ${XD_CAM_OUT}",
                 "job 'render-3d-default' of the shared template is missing (variant default)"):
        assert want in f, (want, f)
    kinds = {k for k, _ in cam.jobset_findings(Workspace(root), _project(repo), ["default", "alt"])}
    assert {"special_execute", "special_copyfiles", "output"} <= kinds      # these stop `curatrix cam`
    p.write_text(json.dumps(good))
    assert _run(root, repo, "CK-F10", "c_jobset") == []
    p.write_text('{"jobs": 3}')
    assert any("not a KiCad jobset" in x for x in _run(root, repo, "CK-F10", "c_jobset"))


# ------------------------------------------------------------------ CK-F11
def test_f11_version_variable(tmp_path):
    """CK-F11 planted: no comment line with ${XD_VERSION} in the schematic, the variable in the Rev
    field, no silkscreen text on the board, a committed version other than `unversioned`."""
    root, repo = _repo(tmp_path)
    d = repo / "pcba" / "drc"
    sch = d / "drc.kicad_sch"
    sch.write_text(sch.read_text().replace('(comment 1 "Canary trace chain', '(comment 2 "Version ${XD_VERSION}")\n'
                                           '\t\t(comment 1 "Canary trace chain', 1))
    assert _run(root, repo, "CK-F11", "c_version_variable") == []
    sch.write_text(sch.read_text().replace('(comment 2 "Version ${XD_VERSION}")', '(rev "${XD_VERSION}")'))
    pcb = d / "drc.kicad_pcb"
    pcb.write_text(pcb.read_text().replace('(gr_text "${XD_VERSION}"', '(gr_text "v"'))
    pro = d / "drc.kicad_pro"
    pd = json.loads(pro.read_text())
    pd["text_variables"]["XD_VERSION"] = "drc/v1.0.0"
    pro.write_text(json.dumps(pd))
    f = "\n".join(_run(root, repo, "CK-F11", "c_version_variable"))
    for want in ("drc.kicad_sch: no title-block comment line with ${XD_VERSION}",
                 "drc.kicad_sch: ${XD_VERSION} in the title-block Rev field",
                 "drc.kicad_pcb: no silkscreen text (F.SilkS or B.SilkS) with ${XD_VERSION}",
                 "text variable XD_VERSION is 'drc/v1.0.0'"):
        assert want in f, (want, f)


# ------------------------------------------------------------------ version, stackup, design rules
def test_version(tmp_path):
    """No tag: v0.0.0-<n>-g<sha>-preview; an exact tag on main with a clean folder: the tag; a dirty
    project folder: -dirty-preview; a tag on a branch that is not on main: -preview."""
    root, repo = _repo(tmp_path)
    folder = repo / "pcba" / "drc"
    sha = _git(repo, "rev-parse", "--short=7", "HEAD").strip()
    assert cam.version(repo, "drc", folder) == (f"drc/v0.0.0-1-g{sha}-preview", False)
    _git(repo, "tag", "drc/v0.1.0")
    _git(repo, "tag", "other/v9.0.0")
    assert cam.version(repo, "drc", folder) == ("drc/v0.1.0", True)
    (folder / "drc.kicad_pro").write_text((folder / "drc.kicad_pro").read_text() + " ")
    assert cam.version(repo, "drc", folder) == ("drc/v0.1.0-dirty-preview", False)
    _git(repo, "checkout", "-q", "--", ".")
    _git(repo, "checkout", "-q", "-b", "feat")
    (repo / "x.txt").write_text("x")
    _git(repo, "add", "x.txt")
    _git(repo, "commit", "-q", "-m", "x")
    _git(repo, "tag", "drc/v0.2.0")
    assert cam.version(repo, "drc", folder) == ("drc/v0.2.0-preview", False)


def test_stackup_and_design_rules(tmp_path):
    """A board without a stackup gets KiCad's default (2 copper layers, the board thickness); a
    Board Setup stackup is read as it is; design rules from .kicad_pro, net classes and .kicad_dru."""
    rows, source = cam.stackup(DRC / "drc.kicad_pcb")
    assert source.startswith("KiCad default (2 copper layers, board thickness 1.6 mm")
    assert [r["layer"] for r in rows if r.get("type") == "copper"] == ["F.Cu", "B.Cu"]
    assert next(r for r in rows if r["layer"] == "dielectric 1")["thickness_mm"] == "1.53"
    pcb = tmp_path / "s.kicad_pcb"
    pcb.write_text('(kicad_pcb (setup (stackup (layer "F.Cu" (type "copper") (thickness 0.035))\n'
                   '(layer "dielectric 1" (type "core") (thickness 1.51) (material "FR4") (epsilon_r 4.5))\n'
                   '(layer "B.Cu" (type "copper") (thickness 0.035)) (copper_finish "ENIG"))))')
    rows, source = cam.stackup(pcb)
    assert source == "Board Setup stackup" and rows[1] == {"layer": "dielectric 1", "type": "core",
                                                           "thickness_mm": "1.51", "material": "FR4", "epsilon_r": "4.5"}
    pro = tmp_path / "p.kicad_pro"
    shutil.copy(DRC / "drc.kicad_pro", pro)
    pro.with_suffix(".kicad_dru").write_text('(version 1)\n(rule "hv"\n\t(constraint clearance (min 1.5mm))\n'
                                             '\t(condition "A.NetClass == \'HV\'"))\n')
    dr = cam.design_rules(pro)
    assert {"scope": "board", "rule": "min_clearance", "value": 0.0} in dr
    assert any(r["scope"] == "net class Default" and r["rule"] == "clearance" for r in dr)
    assert {"scope": "custom rule", "rule": "hv",
            "value": "(constraint clearance (min 1.5mm)) (condition \"A.NetClass == 'HV'\")"} in dr


# ------------------------------------------------------------------ with KiCad
@pytest.mark.tools
def test_cam_run(tmp_path):
    """`curatrix cam` on the fixture board (two variants): every output under build/, the version in
    the copy (preview), the copy's source untouched; planted: a jobset with a job KiCad cannot parse
    (0 jobs run, exit 0) fails the run; an Execute Command job stops it before KiCad runs."""
    if shutil.which("kicad-cli") is None:
        pytest.skip("kicad-cli not installed")
    root, repo = _repo(tmp_path)
    ws = Workspace(root)
    cfg = checkcfg.load(repo / "checks.yaml", root)
    rec = cam.run(ws, Repo("r", repo, "r"), cfg)[0]
    assert rec["version"].startswith("drc/v0.0.0-1-g") and rec["version"].endswith("-preview")
    top = ws.build("r") / "cam" / "drc" / rec["version"].split("/", 1)[1]
    out = top / "drc"
    files = set(rec["files"])
    for f in ("drc/bom-default.csv", "drc/bom-alt.csv", "drc/pos-alt-all-pos.csv", "drc/netlist.xml",
              "drc/drc-schematic-default.pdf", "drc/drc.svg", "drc/drc-alt.step", "drc/render-top-alt.png",
              "drc/render-bottom-default.png", "drc/render-3d-alt.png", "drc/gerbers/drc-F_Cu.gtl",
              "drc/gerbers/drc.drl", "drc/stackup.csv", "drc/design-rules.csv",
              "drc/schematic-svg-alt/drc.svg", "drc/schematic-svg-default/drc.svg"):
        assert f in files, f
    boms = {v: (out / f"bom-{v}.csv").read_text() for v in ("default", "alt")}
    r1 = {v: next(ln for ln in b.splitlines() if ln.startswith('"R1"')) for v, b in boms.items()}
    assert '"DNP"' not in r1["default"] and '"DNP"' in r1["alt"]
    assert rec["version"] in (out / "netlist.xml").read_text()          # the project variable reached KiCad
    assert json.loads((top / "project" / "drc.kicad_pro").read_text())["text_variables"]["XD_VERSION"] == rec["version"]
    assert json.loads((repo / "pcba/drc/drc.kicad_pro").read_text())["text_variables"]["XD_VERSION"] == "unversioned"
    assert list(csv.DictReader(open(out / "stackup.csv")))[2]["layer"] == "F.Cu"
    assert not (ws.build("r") / "cam" / "tmp").exists()
    # planted: one job KiCad cannot parse -> it runs none and exits 0; cam must fail
    p = repo / "pcba" / "drc" / "drc.kicad_jobset"
    js = json.loads(p.read_text())
    js["jobs"].insert(0, {"id": "stats", "type": "pcb_export_stats", "settings": {"output_format": "json"}})
    p.write_text(json.dumps(js))
    with pytest.raises(cam.CamError, match=r"0 of 1[0-9] jobs succeeded"):
        cam.run(ws, Repo("r", repo, "r"), cfg)
    js["jobs"][0] = {"id": "x", "type": "special_execute", "settings": {"command": "true"}}
    p.write_text(json.dumps(js))
    with pytest.raises(cam.CamError, match="Execute Command"):
        cam.run(ws, Repo("r", repo, "r"), cfg)
