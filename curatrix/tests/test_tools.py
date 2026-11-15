import hashlib
from pathlib import Path

import pytest

from curatrix import tools
from curatrix.ws import Workspace

XDMOD = Path(__file__).resolve().parents[2]


def test_xdmod_tools_yaml_parses():
    ts = tools.parse(XDMOD / "tools.yaml")
    assert ts.tools["jdk"].version == "21.0.13+9" and ts.tools["sysml-pilot"].version == "0.63.1"
    assert ts.tools["elkjs"].kind == "npm" and ts.tools["drawio-viewer"].kind == "file"
    assert ts.tools["jdk"].env == {"JAVA_HOME": "{location}"}
    assert "firefox" in ts.system and ts.system["kicad-cli"].optional


def test_merge_conflict(tmp_path):
    a, b = tmp_path / "a.yaml", tmp_path / "b.yaml"
    a.write_text("system:\n  - {name: cmake, version: '4.5.0'}\n")
    b.write_text("system:\n  - {name: cmake, version: '4.4.0'}\n")
    with pytest.raises(tools.ToolsError, match="conflicts"):
        tools.merge([tools.parse(a), tools.parse(b)])
    b.write_text("system:\n  - {name: cmake, version: any}\n")
    assert tools.merge([tools.parse(a), tools.parse(b)]).system["cmake"].version == "4.5.0"


def test_sha256_required(tmp_path):
    p = tmp_path / "t.yaml"
    p.write_text("tools:\n  - {name: x, version: '1', kind: file, url: 'file:///x', location: opt/x}\n")
    with pytest.raises(tools.ToolsError, match="sha256"):
        tools.parse(p)


@pytest.mark.parametrize("want,have,ok", [("4.5.0", "4.5.0", True), ("4.5.0", "4.5.1", False),
                                          ("3.14.*", "3.14.10", True), ("3.14.*", "3.13.1", False),
                                          ("any", "1", True), ("1.0", None, False)])
def test_version_ok(want, have, ok):
    assert tools.version_ok(want, have) is ok


def test_install_file_tool_with_sha_and_stamp(tmp_path):
    ws_root = tmp_path / "ws"
    (ws_root / ".venv" / "bin").mkdir(parents=True)
    src = tmp_path / "payload.js"
    src.write_text("// payload\n")
    sha = hashlib.sha256(src.read_bytes()).hexdigest()
    ws = Workspace(ws_root)
    t = tools.Tool(name="viewer", version="1.0", kind="file", url=src.as_uri(), sha256=sha,
                   location="opt/viewer/v.js", links={"viewer.js": ""})
    t.links = {}
    tools.install(ws, t, log=lambda *_: None)
    assert (ws_root / ".venv/opt/viewer/v.js").read_text() == "// payload\n"
    assert tools.installed_ok(ws, t)
    bad = tools.Tool(name="bad", version="1.0", kind="file", url=src.as_uri(), sha256="0" * 64, location="opt/bad")
    with pytest.raises(tools.ToolsError, match="sha256 mismatch"):
        tools.install(ws, bad, log=lambda *_: None)
    # a newer version in tools.yaml is not ok until installed
    t2 = tools.Tool(name="viewer", version="2.0", kind="file", url=src.as_uri(), sha256=sha, location="opt/viewer/v.js")
    assert not tools.installed_ok(ws, t2)


def test_adopt(tmp_path):
    ws = Workspace(tmp_path)
    (tmp_path / ".venv/opt/jdk").mkdir(parents=True)
    t = tools.Tool(name="jdk", version="21", kind="tarball", url="file:///nonexistent", sha256="1" * 64, location="opt/jdk")
    tools.install(ws, t, log=lambda *_: None, adopt=True)
    assert tools.installed_ok(ws, t)
