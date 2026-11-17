"""The board document (task 5.21): the plain-Python BOM reader against KiCad (CK-D9), the BOM fields
(CK-F12), the local CAM output of the current commit (CK-D10) and the pcba directives."""
import json
import os
import shutil
import subprocess
import sys
import time

import pytest

from curatrix import bom, cam, checkcfg, checks, ercdrc
from curatrix.ws import Repo, Workspace
from helpers import FIXTURES, git_init

BOM = FIXTURES / "kicad" / "bom"
YAML = 'version: 1\narea: r\ncad: {projects: ["pcba/*/*.kicad_pro"], connectors: generated}\n'
FILES = ("bom.kicad_pro", "bom.kicad_sch", "bom_ch.kicad_sch")


def _repo(tmp_path):
    root = tmp_path / "ws"
    repo = git_init(root / "r")
    (repo / "checks.yaml").write_text(YAML)
    d = repo / "pcba" / "bom"
    d.mkdir(parents=True)
    for f in FILES:
        shutil.copy(BOM / f, d / f)
    _commit(repo)
    return root, repo


def _commit(repo, msg="board"):
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", msg], check=True)


def _run(root, repo, cid, fn):
    ctx = checks.Ctx(Workspace(root), Repo("r", repo, "r"), checkcfg.load(repo / "checks.yaml", root), "local",
                     False, None, root / "out")
    (root / "out").mkdir(exist_ok=True)
    r = checks.Result(cid, cid, level="warning")
    getattr(checks, fn)(ctx, r)
    return r.findings


def test_reader_equals_recorded_kicad_bom():
    """A sheet used twice (R2, R3), a two-unit symbol (U1, one part), DNP (JP1), not in the BOM (H1),
    a value override (R1 in a), DNP per instance (R3 in b), fitted per variant (JP1 in b), a Setting
    per variant (J1): the reader equals KiCad 10.0.8's BOM export (recorded) without and with
    --variant."""
    parts = bom.read(BOM / "bom.kicad_sch")
    assert [p.ref for p in parts] == ["H1", "J1", "JP1", "R1", "R2", "R3", "U1"]
    for v in (None, "a", "b"):
        assert bom.compare(bom.mine(parts, v), bom.from_kicad_csv(BOM / f"bom.{v or 'base'}.csv"), v or "base") == []


def test_table_variants_and_findings():
    parts = bom.read(BOM / "bom.kicad_sch")
    head, rows = bom.table(parts, ["a", "b"])
    assert head[-2:] == ["Variant a", "Variant b"]
    by = {r[0]: r for r in rows}
    assert by["R2, R3"][-2:] == ["2", "1, R3 DNP"]
    assert by["R1"][-2:] == ["1, value 4k7", "1"]
    assert by["JP1"][3] == "Standard: solder bridge" and by["JP1"][-2:] == ["DNP", "1"]
    assert by["J1"][-2:] == ["1, 1-2", "1, 2-3"] and "H1" not in by
    assert bom.collapse(["R1", "R2", "R3", "R4", "R7", "R9", "R10"]) == "R1-R4, R7, R9, R10"
    vt = bom.variants_table(parts, [{"name": "a"}, {"name": "b", "description": "B"}], {"bom": ["b"]}, "bom")
    assert vt == [["a", "", "R1 value 4k7", "J1 1-2", "none"], ["b", "B", "JP1 fitted, R3 DNP", "J1 2-3", "bom/b"]]
    assert bom.variants_table(parts, [{"name": "a"}], None, "bom")[0][4] == "—"


def test_f12_bom_fields(tmp_path):
    """CK-F12 planted: J1 has neither Manufacturer nor MPN; JP1 has a Standard designation instead;
    H1 is not in the BOM."""
    root, repo = _repo(tmp_path)
    f = _run(root, repo, "CK-F12", "c_bom_fields")
    assert len(f) == 1 and "J1 (Conn_01x03) has no Manufacturer and no MPN" in f[0], f
    sch = repo / "pcba" / "bom" / "bom.kicad_sch"
    sch.write_text(sch.read_text().replace('(property "Setting" "1-2"', '(property "Standard" "DIN 1-2"'))
    assert _run(root, repo, "CK-F12", "c_bom_fields") == []


@pytest.mark.tools
def test_d9_against_kicad_cli(tmp_path, monkeypatch):
    """CK-D9 with KiCad: no finding on the fixture (base and both variants); planted: a reader that
    loses a variant's DNP is reported."""
    if shutil.which("kicad-cli") is None:
        pytest.skip("kicad-cli not installed")
    root, repo = _repo(tmp_path)
    assert _run(root, repo, "CK-D9", "c_bom_kicad") == []
    real = bom.resolve

    def buggy(parts, variant):
        out = real(parts, variant)
        for p in out:
            p.dnp = False if variant == "b" and p.ref == "R3" else p.dnp
        return out
    monkeypatch.setattr(bom, "resolve", buggy)
    f = _run(root, repo, "CK-D9", "c_bom_kicad")
    assert f == ["pcba/bom/bom.kicad_sch (variant b): R3 DNP '' here, 'DNP' in KiCad"], f


def _cam(root, repo, version, commit=None):
    top = root / "build" / "r" / "cam" / "bom" / version
    (top / "bom").mkdir(parents=True, exist_ok=True)
    head = commit or subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True,
                                    text=True).stdout.strip()
    (top / "cam.json").write_text(json.dumps({"kind": "board", "project": "bom", "version": f"bom/{version}", "release": False,
                                              "commit": head, "date": "2026-11-17T00:00:00+00:00"}))
    return top


def test_d10_cam_output_of_the_current_commit(tmp_path):
    """CK-D10 planted: no output; output of another commit; a clean run, then an uncommitted change
    (stale); a run on the dirty tree, then a newer change (stale again)."""
    root, repo = _repo(tmp_path)
    f = _run(root, repo, "CK-D10", "c_cam_output")
    assert len(f) == 1 and "no `curatrix cam` output for commit" in f[0] and "curatrix cam r bom" in f[0], f
    _cam(root, repo, "v0.0.0-1-gold-preview", commit="0" * 40)
    assert _run(root, repo, "CK-D10", "c_cam_output")
    _cam(root, repo, "v0.0.0-1-gabc-preview")
    assert _run(root, repo, "CK-D10", "c_cam_output") == []
    sch = repo / "pcba" / "bom" / "bom.kicad_sch"
    sch.write_text(sch.read_text() + "\n")
    f = _run(root, repo, "CK-D10", "c_cam_output")
    assert any("uncommitted changes in the project folder since" in x for x in f), f
    _cam(root, repo, "v0.0.0-1-gabc-dirty-preview")
    assert _run(root, repo, "CK-D10", "c_cam_output") == []
    time.sleep(0.05)
    os.utime(sch, (time.time() + 5, time.time() + 5))
    f = _run(root, repo, "CK-D10", "c_cam_output")
    assert any("a project file changed after the `curatrix cam` run" in x for x in f), f


def test_findings_rows_carry_the_acceptance_state():
    f = [ercdrc.Finding("CK-F4b", "unconnected_items", "error", "Missing connection", ["Pad 1 of J1"], ["u1"]),
         ercdrc.Finding("CK-F4b", "clearance", "error", "Clearance", ["Pad 1 of R1"], ["u2"]),
         ercdrc.Finding("CK-F4b", "silk_overlap", "warning", "Silk", ["R1"], ["u3"])]
    e = ercdrc.Entry(1, "CK-F4b", "unconnected_items", "all", "no routing.", (1, 4), "accepted", "Accepted-by: O in abc")
    rows = ercdrc.evaluate(f, [e], {}).rows
    assert [(r["rule"], r["state"]) for r in rows] == [("unconnected_items", "accepted"), ("clearance", "open"),
                                                      ("silk_overlap", "warning")]
    assert rows[0]["note"] == "no routing (accepted.yaml entry 1; Accepted-by: O in abc)" and rows[0]["items"] == "J1"


@pytest.mark.sphinx
def test_board_document(tmp_path):
    """The pcba directives in a strict Sphinx build: plain-Python sections everywhere; without the CAM
    output of the current commit (CI) one fixed sentence; with it, renderings, schematic, findings."""
    root, repo = _repo(tmp_path)
    pro = repo / "pcba" / "bom" / "bom.kicad_pro"
    pro.write_text(pro.read_text().replace('"TraceID": "EE-PCBA-0001"', '"XD_VERSION": "unversioned"'))
    _commit(repo, "no board need in this document")
    (repo / "generated").mkdir()
    (repo / "generated" / "bom.connectors.json").write_text(json.dumps({"connectors": [
        {"ref": "J1", "port": "-", "value": "Conn_01x03", "footprint": "fp",
         "pins": [{"number": "1", "name": "Pin_1", "net": "/A"}]}]}))
    src = tmp_path / "src"
    shutil.copytree(FIXTURES / "sphinxdoc", src)
    tmpl = (FIXTURES.parents[2] / "templates" / "kicad-pcba" / "doc" / "index.rst").read_text()
    (src / "index.rst").write_text(tmpl.replace("__TITLE_RST__", "Board\n=====").replace("__NAME__", "bom"))
    for d in src.iterdir():
        if d.suffix == ".rst" and d.name != "index.rst":
            d.unlink()

    def build(out):
        r = subprocess.run([sys.executable, "-m", "sphinx", "-W", "--keep-going", "-q", "-b", "html",
                            "-D", f"xd_repo={repo}", "-D", f"xd_cam_dir={root / 'build' / 'r' / 'cam'}",
                            str(src), str(out)], capture_output=True, text=True, timeout=300)
        assert r.returncode == 0, r.stdout + r.stderr
        return (out / "index.html").read_text()

    local = "Made locally with KiCad (curatrix cam) for the current commit; not part of this build."
    html = build(tmp_path / "o1")
    assert html.count(local) == 3                                   # renderings, schematic, findings
    for text in ("R1 value 4k7", "JP1 fitted, R3 DNP", "Variant b", "1, R3 DNP", "Pin_1",
                 "No data yet.", "is not part of this build"):   # no board file: no stackup
        assert text in html, text
    top = _cam(root, repo, "v0.0.0-1-gabc-preview")
    out = top / "bom"
    for v in ("a", "b"):
        for stem in ("render-top", "render-bottom", "render-3d"):
            (out / f"{stem}-{v}.png").write_bytes(b"\x89PNG same")
    (out / "bom.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" id="root-sheet"/>')
    (out / "findings.json").write_text(json.dumps({"erc": [], "drc": [
        {"check": "CK-F4b", "rule": "unconnected_items", "severity": "error", "state": "proposal", "items": "J1",
         "description": "Missing connection", "note": "routing (accepted.yaml entry 1; not committed)"}]}))
    html = build(tmp_path / "o2")
    assert local not in html
    for text in ("bom/v0.0.0-1-gabc-preview", "data:image/png;base64,", "the same renderings as variant a",
                 'id="root-sheet"', "proposed, not accepted", "0 open, 1 proposed, 0 accepted"):
        assert text in html, text
    _cam(root, repo, "v0.0.0-1-gabc-preview", commit="1" * 40)       # the output of another commit: never shown
    assert build(tmp_path / "o3").count(local) == 3


def test_harness_links_use_the_zdocs_intersphinx_name(tmp_path):
    """zdocs names a peer's inventory by its registry prefix, else its ID with `_` (pcba_canary_board)."""
    sys.path.insert(0, str(FIXTURES.parents[2] / "sphinx"))
    from xdmod_sphinx import harness
    repo = tmp_path / "r"
    (repo / "docs").mkdir(parents=True)
    (repo / "checks.yaml").write_text("version: 1\ndocs: {registry: docs/documents.yaml}\n")
    (repo / "docs" / "documents.yaml").write_text("documents:\n  pcba-a-b: {title: A}\n  c: {title: C, prefix: cc}\n")
    assert harness._registry_docs(repo) == {"pcba-a-b": "pcba_a_b", "c": "cc"}
