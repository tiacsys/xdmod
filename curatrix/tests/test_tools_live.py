"""Tests that need the installed tools: the Pilot (Java), node + elkjs, headless Firefox.
Run with `-m tools`; skipped when a tool is missing."""
import json
import shutil
from pathlib import Path

import pytest

from curatrix import model, pilot, stubs, views
from curatrix.views import render
from curatrix.ws import Workspace
from helpers import FIXTURES

pytestmark = pytest.mark.tools
WS = Workspace(Path(__file__).resolve().parents[3])
XDTRACE = Path(__file__).resolve().parents[2] / "sysml" / "XdTrace.sysml"


def need_pilot():
    jshell, _, jar = pilot.paths(WS)
    if not (jshell.exists() and jar.exists()):
        pytest.skip("Pilot not installed")


def test_pilot_parses_library_stubs_and_probe(tmp_path):
    need_pilot()
    n = {"SYS-NEED-0002": {"id": "SYS-NEED-0002", "type": "sys-need", "title": "Mirror", "status": "valid"},
         "SYS-REQ-0001": {"id": "SYS-REQ-0001", "type": "sys-req", "title": "Latency", "status": "valid",
                          "refines": ["SYS-NEED-0002"], "max": 50, "unit": "ms", "ears": "event"}}
    st = tmp_path / "NeedStubs.sysml"
    st.write_text(stubs.generate(n))
    out = tmp_path / "export.json"
    r = pilot.run(WS, [XDTRACE, st, FIXTURES / "sysml" / "Probe.sysml"], ["Probe"], out, tmpdir=tmp_path)
    assert r.ok, r.log
    doc, findings = model.to_needs(model.Model(model.compact(json.loads(out.read_text()), {"XdTrace"})), "p")
    assert findings == [] and doc["versions"][""]["needs"]["SYS-EL-0002"]["satisfies"] == ["SYS-REQ-0001"]


def test_pilot_reports_errors(tmp_path):
    need_pilot()
    bad = tmp_path / "Bad.sysml"
    bad.write_text("package Bad { part x : NoSuchType; }\n")
    r = pilot.run(WS, [XDTRACE, bad], [], None, tmpdir=tmp_path)
    assert not r.ok and r.errors == 1 and "NoSuchType" in r.log


def test_views_build_is_byte_stable(tmp_path):
    if not (shutil.which("node") and shutil.which("firefox") and (WS.opt / "node/node_modules/elkjs").exists()):
        pytest.skip("node, elkjs or firefox missing")
    m = model.Model.load(FIXTURES / "sysml" / "probe-model.json")
    vd = tmp_path / "views"
    assert render.build(WS, m, vd, tmp_path / "out", log=lambda *_: None) == []
    f = vd / "jointView.drawio.svg"
    first = f.read_text()
    render.build(WS, m, vd, tmp_path / "out", log=lambda *_: None)
    assert f.read_text() == first
    (v,) = views.discover(m)
    assert views.check_file(f, views.to_mxfile(views.graph(m, v))) == []
    assert render.normalize(WS, [f], tmp_path / "norm", check_only=True, log=lambda *_: None) == []
