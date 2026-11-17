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


def _git(*a, cwd=None):
    import subprocess
    env = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@x", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@x",
           "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1", "PATH": "/usr/bin:/bin"}
    return subprocess.run(["git", *a], cwd=cwd, env=env, check=True, capture_output=True, text=True).stdout.strip()


def _upstream(tmp_path):
    up = tmp_path / "upstream"
    (up / "addon" / "Mod").mkdir(parents=True)
    (up / "tool.py").write_text("V = 1\n")
    (up / "addon" / "Mod" / "Init.py").write_text("# addon\n")
    _git("init", "-q", "-b", "main", str(up))
    _git("add", "-A", cwd=up)
    _git("commit", "-q", "-m", "one", cwd=up)
    first = _git("rev-parse", "HEAD", cwd=up)
    (up / "tool.py").write_text("V = 2\n")
    _git("commit", "-q", "-am", "two", cwd=up)
    return up, first


def test_git_tool_pinned_by_commit_into_state(tmp_path):
    up, first = _upstream(tmp_path)
    ws = Workspace(tmp_path / "ws")
    (ws.root / ".venv").mkdir(parents=True)
    t = tools.Tool(name="addon", version="1", kind="git", url=up.as_uri(), commit=first,
                   location=".xdmod/addon/tool", env={"XD_ADDON": "{location}"})
    assert t.path(ws) == ws.root / ".xdmod/addon/tool" and t.shown() == ".xdmod/addon/tool"
    tools.install(ws, t, log=lambda *_: None)
    assert (ws.root / ".xdmod/addon/tool/tool.py").read_text() == "V = 1\n"     # the pinned commit, not main
    assert not (ws.root / ".xdmod/addon/tool/.git").exists()
    assert tools.installed_ok(ws, t) and tools.stamp_of(ws, "addon")["commit"] == first
    sub = tools.Tool(name="sub", version="1", kind="git", url=up.as_uri(), commit=first,
                     subdir="addon/Mod", location=".xdmod/Mod/Addon")
    tools.install(ws, sub, log=lambda *_: None)
    assert sorted(p.name for p in (ws.root / ".xdmod/Mod/Addon").iterdir()) == ["Init.py"]
    bad = tools.Tool(name="bad", version="1", kind="git", url=up.as_uri(), commit="0" * 40, location=".xdmod/bad")
    with pytest.raises(tools.ToolsError, match="fetch|did not give"):
        tools.install(ws, bad, log=lambda *_: None)


def test_git_tool_adopts_a_checkout_at_the_pin(tmp_path):
    up, first = _upstream(tmp_path)
    ws = Workspace(tmp_path / "ws")
    (ws.root / ".venv").mkdir(parents=True)
    loc = ws.root / ".xdmod/stepup/tool"
    _git("clone", "-q", str(up), str(loc))
    _git("checkout", "-q", first, cwd=loc)
    t = tools.Tool(name="tool", version="1", kind="git", url="https://example.invalid/x", commit=first,
                   location=".xdmod/stepup/tool")
    msgs = []
    tools.install(ws, t, log=msgs.append)                    # no network: the checkout is at the pin
    assert "adopt" in msgs[0] and (loc / ".git").exists() and tools.installed_ok(ws, t)
    _git("checkout", "-q", "main", cwd=loc)                   # moved by hand: no longer ok
    assert not tools.installed_ok(ws, t)


@pytest.mark.parametrize("extra,match", [("kind: git, commit: abc", "40 hex"),
                                         ("kind: git, commit: " + "a" * 40 + ", sha256: " + "b" * 64, "not sha256"),
                                         ("kind: file, sha256: " + "b" * 64 + ", commit: " + "a" * 40, "only for kind git"),
                                         ("kind: file, sha256: " + "b" * 64 + ", subdir: x", "subdir"),
                                         ("kind: git, commit: " + "a" * 40 + ", location: ../x", "location")])
def test_git_tool_fields(tmp_path, extra, match):
    p = tmp_path / "t.yaml"
    loc = "" if "location" in extra else ", location: .xdmod/x"
    p.write_text(f"tools:\n  - {{name: x, version: '1', url: 'file:///x'{loc}, {extra}}}\n")
    with pytest.raises(tools.ToolsError, match=match):
        tools.parse(p)


def test_stepup_is_a_curated_tool():
    t = tools.parse(XDMOD / "tools.yaml").tools["stepup"]
    assert t.kind == "git" and t.commit == "3db98be23aae40413eab041f19de5ab2e168157e"
    assert t.location == ".xdmod/stepup/kicadStepUpMod" and "no LICENSE" in t.licence
    assert t.env["XD_STEPUP"] == "{location}"
