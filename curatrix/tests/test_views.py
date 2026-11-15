import base64
import urllib.parse
import zlib

import pytest

from curatrix import model, views
from helpers import FIXTURES

SVG = FIXTURES / "sphinxdoc" / "views" / "jointView.drawio.svg"


def probe():
    return model.Model.load(FIXTURES / "sysml" / "probe-model.json")


def expected():
    m = probe()
    (v,) = views.discover(m)
    return v, views.to_mxfile(views.graph(m, v))


def test_discover_and_graph():
    v, _ = expected()
    assert (v.name, v.short_id, v.kind, v.root) == ("jointView", "SYS-VIEW-0001", "interconnection", "Probe::LogicalJoint")
    g = views.graph(probe(), v)
    ids = {n["id"]: n for n in g["nodes"]}
    assert ids["Probe::LogicalJoint::ctrl"]["trace_id"] == "SYS-EL-0002"      # from its definition (D128)
    assert ids["Probe::LogicalJoint::sensor"]["trace_id"] == ""
    assert [p["side"] for p in ids["Probe::LogicalJoint::ctrl"]["ports"]] == ["WEST"]   # conjugated port
    assert g["edges"][0]["src"] == "Probe::LogicalJoint::sensor.angleOut"


def test_committed_view_passes_the_content_check():
    _, exp = expected()
    assert views.check_file(SVG, exp) == []


def test_content_change_and_stale_picture(tmp_path):
    _, exp = expected()
    bad = tmp_path / "jointView.drawio.svg"
    bad.write_text(SVG.read_text().replace("ctrl : JointController", "ctrl : Renamed"))
    errs = views.check_file(bad, exp)
    assert any("stale" in e for e in errs) and any("changed Probe::LogicalJoint::ctrl" in e for e in errs)


def test_geometry_is_not_content(tmp_path):
    _, exp = expected()
    content, _, text = views.read_svg(SVG)
    moved = content.replace('x="', 'x="1', 1)
    assert views.content_of(moved) == views.content_of(content)


def test_compressed_diagram_is_rejected_and_decompressed(tmp_path):
    _, exp = expected()
    content, _, _ = views.read_svg(SVG)
    import xml.etree.ElementTree as ET
    root = ET.fromstring(content)
    dia = root.find("diagram")
    model_xml = ET.tostring(dia.find("mxGraphModel"), encoding="unicode")
    co = zlib.compressobj(9, zlib.DEFLATED, -15)
    packed = base64.b64encode(co.compress(urllib.parse.quote(model_xml).encode()) + co.flush()).decode()
    dia.remove(dia.find("mxGraphModel"))
    dia.text = packed
    comp = ET.tostring(root, encoding="unicode")
    assert views.is_compressed(comp)
    assert views.content_of(comp) == views.content_of(content)            # normalize decompresses
    assert views.normalize_xml(comp) == views.normalize_xml(content)


def test_geometry_errors():
    import xml.etree.ElementTree as ET
    content, _, _ = views.read_svg(SVG)
    assert views.geometry_errors(content) == []
    root = ET.fromstring(content)
    obj = next(o for o in root.iter("object") if o.get("id") == "Probe::LogicalJoint::ctrl")
    obj.find("mxCell/mxGeometry").set("x", "5000")
    assert any("outside its parent" in e for e in views.geometry_errors(ET.tostring(root, encoding="unicode")))


def test_normalize_is_idempotent_and_drops_editor_attributes():
    _, exp = expected()
    edited = exp.replace('<mxfile host="xdmod-curatrix">', '<mxfile host="Electron" modified="2026-11-15T00:00:00Z" agent="x" version="31.7.0">')
    assert views.normalize_xml(edited) == exp
    assert views.diagram_hash(edited) == views.diagram_hash(exp)


def test_unknown_or_unimplemented_kind():
    v, _ = expected()
    v.kind = "allocation"
    with pytest.raises(views.ViewError, match="not implemented"):
        views.graph(probe(), v)
    v.kind = "bogus"
    with pytest.raises(views.ViewError, match="unknown kind"):
        views.graph(probe(), v)


def test_view_not_in_model():
    assert any("no view of this name" in e for e in views.check_file(SVG, None))
