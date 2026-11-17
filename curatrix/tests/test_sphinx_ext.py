"""xdmod_sphinx in a plain strict Sphinx build (no zdocs)."""
import re
import shutil
import subprocess
import sys

import pytest

from helpers import FIXTURES

pytestmark = pytest.mark.sphinx


def build(tmp_path, extra="", env=None, defines=()):
    src = tmp_path / "src"
    shutil.copytree(FIXTURES / "sphinxdoc", src)
    if extra:
        with open(src / "index.rst", "a") as f:
            f.write("\n" + extra)
    out = tmp_path / "out"
    r = subprocess.run([sys.executable, "-m", "sphinx", "-W", "--keep-going", "-q", "-b", "html",
                        *[x for d in defines for x in ("-D", d)], str(src), str(out)],
                       capture_output=True, text=True, timeout=300, env=env)
    return r.returncode, r.stdout + r.stderr, out


def test_build(tmp_path):
    rc, log, out = build(tmp_path)
    assert rc == 0, log
    html = (out / "index.html").read_text()
    assert 'href="#SYS-EL-0002"' in html                  # need:<ID> resolved to the need's page
    assert "need:SYS-EL" not in html and "mxfile" not in html
    assert "built locally" in html                         # CAD directive without the export: notice, no warning
    assert "link_length" in html and "80 mm" in html       # freecad-params, plain Python
    assert "1 chain(s)" in html or "chain(s)" in html
    # the SVG viewer (xdmod#69 Q16): the view is a zoom figure, the vendored files are in _static, no CDN
    assert '<figure class="sysml-view xd-zoom">' in html
    for f in ("svg-pan-zoom/svg-pan-zoom.min.js", "svg-pan-zoom/LICENSE", "xd-svgview.js", "xd-svgview.css"):
        assert (out / "_static" / f).is_file(), f
    assert re.search(r'<script src="_static/svg-pan-zoom/svg-pan-zoom.min.js', html)
    assert re.search(r'<script src="_static/xd-svgview.js', html)
    assert not re.search(r'<script src="https?:', html)


def test_vendored_files_match_the_record():
    """Each vendored file is the one vendor.yaml records (version, sha256), with its licence file."""
    import hashlib
    import yaml
    ext = FIXTURES.parents[2] / "sphinx" / "xdmod_sphinx"
    rec = yaml.safe_load((ext / "vendor.yaml").read_text())
    spz = rec["svg-pan-zoom"]
    assert spz["license"] == "BSD-2-Clause" and "svg-pan-zoom/LICENSE" in spz["files"]
    for path, f in spz["files"].items():
        assert hashlib.sha256((ext / "static" / path).read_bytes()).hexdigest() == f["sha256"], path
    head = (ext / "static" / "svg-pan-zoom" / "svg-pan-zoom.min.js").read_text().splitlines()[0]
    assert head == f"// svg-pan-zoom v{spz['version']}"


def test_unknown_need_in_view_fails_strict(tmp_path):
    src_svg = (FIXTURES / "sphinxdoc" / "views" / "jointView.drawio.svg").read_text()
    rc, log, _ = build(tmp_path, extra=".. sysml-view:: /views/other.drawio.svg\n")
    assert rc != 0                                          # missing file
    (tmp_path / "src2").mkdir()
    shutil.rmtree(tmp_path / "src")
    rc, log, _ = build(tmp_path, extra="")
    assert rc == 0
    bad = src_svg.replace("need:SYS-EL-0002", "need:SYS-EL-0999")
    src = tmp_path / "src"
    (src / "views" / "jointView.drawio.svg").write_text(bad)
    r = subprocess.run([sys.executable, "-m", "sphinx", "-W", "-q", "-b", "html", str(src), str(tmp_path / "o2")],
                       capture_output=True, text=True, timeout=300)
    assert r.returncode != 0 and "SYS-EL-0999" in (r.stdout + r.stderr)


def test_cad_export_is_shown_when_present(tmp_path):
    import os
    cad = tmp_path / "cad" / "board"
    cad.mkdir(parents=True)
    (cad / "board.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" id="kicad-board"><rect/></svg>')
    env = dict(os.environ, XD_CAD_DIR=str(tmp_path / "cad"))
    rc, log, out = build(tmp_path, env=env)
    assert rc == 0, log
    html = (out / "index.html").read_text()
    assert 'id="kicad-board"' in html and "built locally" not in html
    assert '<figure class="xd-cad xd-zoom">' in html


def test_needimport_missing_prints_the_sentence(tmp_path):
    rc, log, out = build(tmp_path, ".. xd-needimport:: /build/preview.json\n   :missing: No local test run yet.\n")
    assert rc == 0, log
    assert "No local test run yet." in (out / "index.html").read_text()


def test_needimport_missing_without_text_prints_a_default(tmp_path):
    rc, log, out = build(tmp_path, ".. xd-needimport:: /build/preview.json\n   :missing:\n")
    assert rc == 0, log
    assert "No results: the file is not there in this build." in (out / "index.html").read_text()


def test_needimport_stamp_shows_only_the_run_of_this_commit(tmp_path):
    """A stamped preview is shown with its date and commit only while the repo is at that commit;
    an older run shows the :missing: sentence (task 5.10, review of xdmod#43)."""
    import json
    from helpers import git_init
    repo = git_init(tmp_path / "repo")
    (repo / "a").write_text("a")
    subprocess.run(["git", "-C", str(repo), "add", "a"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "a"], check=True)
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    tr = {"SYS-EL-0099": {"id": "SYS-EL-0099", "type": "sys-el", "title": "imported", "status": "valid",
                          "layer": "logical"}}            # any need type: the test is about the stamp
    doc = {"created": "", "current_version": "", "project": "p", "versions": {"": {"needs": tr}}}
    extra = ".. xd-needimport:: /prev/tr-needs.json\n   :stamp:\n   :missing: No local run.\n"
    for commit, shown in ((head, True), ("0" * 40, False)):
        d = tmp_path / str(shown)
        d.mkdir()
        src_extra = d / "prev"
        src_extra.mkdir()
        (src_extra / "tr-needs.json").write_text(json.dumps(doc))
        (src_extra / "tr-needs.stamp.json").write_text(json.dumps({"run_date": "2026-11-17T10:00:00",
                                                                    "commit": commit, "dirty": False}))
        src = d / "src"
        shutil.copytree(FIXTURES / "sphinxdoc", src)
        shutil.copytree(src_extra, src / "prev")
        with open(src / "index.rst", "a") as f:
            f.write("\n" + extra)
        out = d / "out"
        r = subprocess.run([sys.executable, "-m", "sphinx", "-W", "--keep-going", "-q", "-b", "html",
                            "-D", f"xd_repo={repo}", str(src), str(out)], capture_output=True, text=True, timeout=300)
        assert r.returncode == 0, r.stdout + r.stderr
        page = (out / "index.html").read_text()
        assert ("SYS-EL-0099" in page) is shown
        assert (f"commit {head[:12]}" in page) is shown and ("No local run." in page) is not shown


def test_harness_document_directives(tmp_path):
    """The harness-<name> directives (task 5.22): ends, wires and BOM in plain Python; the diagram
    from the local cam output, a notice without it (CI)."""
    import json
    import os
    import yaml
    from test_harness import GOOD
    data = yaml.safe_load(yaml.safe_dump(GOOD))
    data["metadata"].pop("TraceID")                         # no need targets in this plain build
    for c in data["connectors"].values():
        c["notes"] = "portName: -"
    h = tmp_path / "harness" / "servo-cable"
    h.mkdir(parents=True)
    (h / "servo-cable.yml").write_text(yaml.safe_dump(data))
    text = "".join(f".. xd-harness-{d}:: servo-cable\n\n" for d in ("ends", "diagram", "wires", "bom"))
    env = dict(os.environ, XD_CAM_DIR=str(tmp_path / "cam"))
    rc, log, out = build(tmp_path, text, env=env)
    assert rc == 0, log
    html = (out / "index.html").read_text()
    assert "WireViz diagram of servo-cable: built locally" in html
    assert "SERVO_PWM" in html and "W1:2" in html and "XHP-3" in html and "Lapp" in html
    v = tmp_path / "cam" / "servo-cable" / "v0.1.0"
    (v / "servo-cable").mkdir(parents=True)
    (v / "servo-cable" / "servo-cable.svg").write_text('<svg xmlns="http://www.w3.org/2000/svg" id="wv"><rect/></svg>')
    (v / "cam.json").write_text(json.dumps({"kind": "harness", "version": "servo-cable/v0.1.0", "release": True}))
    # a second build into the same output shows it
    r = subprocess.run([sys.executable, "-m", "sphinx", "-W", "--keep-going", "-q", "-b", "html",
                        str(tmp_path / "src"), str(out)], capture_output=True, text=True, timeout=300, env=env)
    assert r.returncode == 0, r.stdout + r.stderr
    html = (out / "index.html").read_text()
    assert 'id="wv"' in html and "servo-cable/v0.1.0" in html


def test_harness_diagram_documents_are_always_outdated():
    """A document with xd-harness-diagram is re-read on every build, so a later `curatrix cam`
    run shows up without a clean build (the plain test build above re-reads anyway)."""
    import types
    sys.path.insert(0, str(FIXTURES.parents[2] / "sphinx"))
    from xdmod_sphinx import harness as hd
    env = types.SimpleNamespace(xd_harness_docs={"harness", "gone"}, found_docs={"harness", "index"})
    assert hd._outdated(None, env, set(), set(), set()) == ["harness"]
    hd._purge(None, env, "harness")
    assert env.xd_harness_docs == {"gone"}


def test_assembly_document_directives(tmp_path):
    """The asm-<name> directives (task 5.27): overview, materials, sub-assembly chapters and the
    indented BOM in plain Python; drawings, mass, renderings and findings only from the cam output
    of the current commit, a fixed sentence without it (CI); renderings: a placeholder until the
    output has renderings/<view>.png."""
    import json
    import os
    from test_asmdoc import _setup
    root, repo, cfg, a = _setup(tmp_path / "w")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "asm"], check=True)
    needs = "".join(f".. me-asm:: {t}\n   :id: {i}\n   :status: valid\n   :realizes: SYS-EL-0002\n\n"
                    for t, i in (("Top", "ME-ASM-0001"), ("Arm", "ME-ASM-0002")))
    needs += "".join(f".. me-part:: P{i}\n   :id: ME-PART-000{i}\n   :status: valid\n   :realizes: SYS-EL-0002\n\n"
                     for i in (2, 3, 4))
    text = needs + "".join(f".. xd-asm-{d}:: top\n\n" for d in (
        "overview", "drawing", "exploded", "renderings", "mass", "materials", "findings", "subassemblies", "bom"))
    env = dict(os.environ, XD_CAM_DIR=str(tmp_path / "cam"))
    rc, log, out = build(tmp_path, text, env=env, defines=[f"xd_repo={repo}"])
    assert rc == 0, log
    html = (out / "index.html").read_text()
    assert "Made locally with FreeCAD (curatrix cam)" in html
    assert "Sub-assembly arm (ME-ASM-0002)" in html and "Used 2 times in top" in html
    assert "ISO 4762 M3x10, A2" in html and "canary-board canary-board/v0.1.0" in html and "pcba-canary-board" in html
    assert "· ISO 4762 M3x10, A2" in html                                   # indented one level below the arm
    assert "Made for the top-level assembly only" in html and "has no parameters of its own" in html
    assert 'href="#ME-PART-0002"' in html
    head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    v = tmp_path / "cam" / "top" / "v0.1.0"
    for var in ("SYS-CFG-0002", "base"):
        (v / "top" / var).mkdir(parents=True)
        (v / "top" / var / "drawing.svg").write_text(f'<svg xmlns="http://www.w3.org/2000/svg" id="d-{var}"/>')
        (v / "top" / var / "mass.json").write_text(json.dumps({"total_g": 3.5, "cog_mm": [1, 2, 3], "complete": True,
                                                               "missing": [], "parts": [
            {"path": "Arm1/L", "id": "ME-PART-0003", "name": "link", "material": "PETG", "volume_mm3": 1000.0,
             "mass_g": 1.27, "source": "material PETG", "com_mm": [4, 0, 0]},
            {"path": "B1", "id": "ME-PART-0002", "name": "bracket", "material": "PLA", "volume_mm3": 1000.0,
             "mass_g": 1.24, "source": "material PLA", "com_mm": [0, 0, 0]}]}))
    (v / "findings.json").write_text(json.dumps({"checks": ["CK-F17"], "rows": [
        {"check": "CK-F17", "rule": "overlap", "severity": "error", "state": "proposal", "items": "B1, Plate",
         "description": "assemblies/top/top.FCStd: B1 and Plate overlap by 2 mm³", "note": "on purpose"}],
        "skipped": {"CK-F18": "no board model"}}))
    (v / "cam.json").write_text(json.dumps({"kind": "assembly", "project": "top", "commit": head,
                                            "version": "top/v0.1.0", "variants": ["SYS-CFG-0002", "base"]}))
    shutil.rmtree(out)
    rc, log, out = build(tmp_path / "again", text, env=env, defines=[f"xd_repo={repo}"])
    assert rc == 0, log
    html = (out / "index.html").read_text()
    assert 'id="d-base"' in html and "top/v0.1.0" in html
    assert "mass 3.5 g" in html and "(1, 2, 3) mm" in html and "mass 1.27 g" in html   # the arm's own mass
    assert "proposed, not accepted" in html and "B1 and Plate overlap" in html
    assert "has no renderings" in html
    import struct
    import zlib

    def png(path):                                         # a real 1 x 1 PNG
        def chunk(t, d):
            return struct.pack(">I", len(d)) + t + d + struct.pack(">I", zlib.crc32(t + d))
        path.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0))
                         + chunk(b"IDAT", zlib.compress(b"\x00\xff\x00\x00")) + chunk(b"IEND", b""))
    (v / "top" / "base" / "renderings").mkdir(parents=True)
    for name in ("right", "front", "extra"):              # task 5.30: the list in cam.json counts, in its order
        png(v / "top" / "base" / "renderings" / f"{name}.png")
    rec = json.loads((v / "cam.json").read_text())
    rec["per_variant"] = {"base": {"renderings": {x: f"top/base/renderings/{x}.png" for x in ("front", "right")}}}
    rec["renderings"] = {"views": ["front", "top", "right", "iso"]}
    (v / "cam.json").write_text(json.dumps(rec))
    shutil.rmtree(out)
    rc, log, out = build(tmp_path / "third", text, env=env, defines=[f"xd_repo={repo}"])
    assert rc == 0, log
    html = (out / "index.html").read_text()
    imgs = re.findall(r'<img alt="Variant base, (\w+)"', html)
    assert imgs == ["front", "right"], imgs
    assert (out / "_images" / "front.png").is_file()
    sys.path.insert(0, str(FIXTURES.parents[2] / "sphinx"))
    from xdmod_sphinx import asm
    assert [f.stem for f in asm._renderings({}, v / "top" / "base", "base")] == ["front", "right", "extra"]
