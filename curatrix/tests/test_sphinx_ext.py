"""xdmod_sphinx in a plain strict Sphinx build (no zdocs)."""
import shutil
import subprocess
import sys

import pytest

from helpers import FIXTURES

pytestmark = pytest.mark.sphinx


def build(tmp_path, extra="", env=None):
    src = tmp_path / "src"
    shutil.copytree(FIXTURES / "sphinxdoc", src)
    if extra:
        with open(src / "index.rst", "a") as f:
            f.write("\n" + extra)
    out = tmp_path / "out"
    r = subprocess.run([sys.executable, "-m", "sphinx", "-W", "--keep-going", "-q", "-b", "html", str(src), str(out)],
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
