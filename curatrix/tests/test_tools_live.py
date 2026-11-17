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


def test_pilot_loads_libraries_as_one_set(tmp_path):
    """Library files that refer to each other resolve when loaded as one set (SYSMOD case)."""
    need_pilot()
    d = FIXTURES / "sysml" / "libset"
    for order in ([d / "LibA.sysml", d / "LibB.sysml"], [d / "LibB.sysml", d / "LibA.sysml"]):
        r = pilot.run(WS, [d / "UsesLibs.sysml"], [], None, tmpdir=tmp_path, libraries=[XDTRACE, *order])
        assert r.ok, r.log
    # one file at a time (the old way) fails for one of the two orders
    r = pilot.run(WS, [d / "LibA.sysml", d / "LibB.sysml", d / "UsesLibs.sysml"], [], None, tmpdir=tmp_path)
    assert not r.ok


def test_pilot_library_set_errors_name_file_and_line(tmp_path):
    need_pilot()
    d = FIXTURES / "sysml" / "libset"
    r = pilot.run(WS, [], [], None, tmpdir=tmp_path, libraries=[d / "LibA.sysml", d / "LibB.sysml", d / "BadLib.sysml"])
    assert not r.ok and r.errors == 1
    assert f"{(d / 'BadLib.sysml').resolve()} line : 3" in r.log, r.log


DOMAIN = FIXTURES / "sysml" / "domain"


def domain_models(tmp_path) -> tuple[str, str]:
    """The compact JSON of the fixture system model and of the domain model read against it, as
    `curatrix gen model` makes them (libraries as one set, the repo's files as one set). Rewrite
    the committed fixtures with XD_REGEN=1."""
    import os
    libs = sorted((XDTRACE.parent).glob("*.sysml"))
    out = {}
    for name, lib, files in (("sys", libs, [DOMAIN / "Sys.sysml"]),
                             ("ee", libs + [DOMAIN / "Sys.sysml"], [DOMAIN / "a_boards.sysml", DOMAIN / "b_ports.sysml", DOMAIN / "c_variants.sysml",
                                                            DOMAIN / "d_cables.sysml"])):
        raw = tmp_path / f"{name}.json"
        r = pilot.run(WS, files, sorted(model.top_packages(files)), raw, tmpdir=tmp_path, libraries=lib, one_set=True)
        assert r.ok, r.log
        out[name] = model.dumps(model.compact(json.loads(raw.read_text()), model.top_packages(lib)))
        if os.environ.get("XD_REGEN"):
            (DOMAIN / f"{name}-model.json").write_text(out[name])
    return out["sys"], out["ee"]


def test_domain_model_fixture_is_fresh(tmp_path):
    """The Pilot reads the domain files as one set (a forward import works), the system model's
    nested package is no export target, and the committed fixture JSON is what the Pilot makes."""
    need_pilot()
    s, e = domain_models(tmp_path)
    assert s == (DOMAIN / "sys-model.json").read_text()
    assert e == (DOMAIN / "ee-model.json").read_text()


def test_pilot_files_in_name_order_fail_without_one_set(tmp_path):
    need_pilot()
    libs = sorted((XDTRACE.parent).glob("*.sysml")) + [DOMAIN / "Sys.sysml"]
    r = pilot.run(WS, [DOMAIN / "a_boards.sysml", DOMAIN / "b_ports.sysml"], [], None, tmpdir=tmp_path, libraries=libs)
    assert not r.ok and "EePorts" in r.log


def test_pilot_export_error_is_an_error(tmp_path):
    """An export the Pilot cannot resolve (e.g. a nested package by its simple name) returns an
    `ERROR:` string; it counts as an error and is never written into the JSON (model spike §3)."""
    need_pilot()
    out = tmp_path / "x.json"
    r = pilot.run(WS, [DOMAIN / "Sys.sysml"], ["Sys", "Detail"], out, tmpdir=tmp_path, libraries=[XDTRACE])
    assert not r.ok and r.errors == 1 and "EXPORT Detail: ERROR:" in r.log and not out.exists()
