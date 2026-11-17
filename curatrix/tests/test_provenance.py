import pytest
"""Tool provenance of generated files (4.4b): record on generation, CK-D5 against the pins."""
import json

from curatrix import checkcfg, provenance, tools
from curatrix.ws import Workspace
from helpers import make_ws

TOOLS = """tools:
  - {name: jdk, version: "21.0.13+9", kind: file, url: "https://x/jdk", sha256: "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa", location: opt/jdk}
  - {name: sysml-pilot, version: "0.63.1", kind: file, url: "https://x/p", sha256: "bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb", location: opt/p}
system: []
"""


def setup_ws(tmp_path, monkeypatch, pilot="0.63.1"):
    root = make_ws(tmp_path, monkeypatch)
    (root / "xdmod").mkdir()
    (root / "xdmod" / "tools.yaml").write_text(TOOLS)
    repo = root / "robarm-syseng"
    (repo / "generated").mkdir(parents=True)
    (repo / "checks.yaml").write_text("version: 1\nmodel: {files: [model/a.sysml]}\n")
    for f in ("model.json", "model-needs.json"):
        (repo / "generated" / f).write_text("{}\n")
    ws = Workspace(root)
    for name, v in (("jdk", "21.0.13+9"), ("sysml-pilot", pilot)):
        t = tools.Tool(name=name, version=v, kind="file", url="u", sha256="c" * 64, location=f"opt/{name}")
        tools.write_stamp(ws, t)
    return ws, checkcfg.load(repo / "checks.yaml", root)


def files(cfg):
    return [cfg.repo / "generated" / "model.json", cfg.repo / "generated" / "model-needs.json"]


def test_record_and_check(tmp_path, monkeypatch):
    ws, cfg = setup_ws(tmp_path, monkeypatch)
    assert len(provenance.check(ws, cfg, files(cfg), "model")) == 2          # nothing recorded yet
    assert provenance.record(ws, cfg, files(cfg), "model")
    doc = json.loads(provenance.path(cfg).read_text())
    assert doc["files"]["generated/model.json"] == {
        "made_by": "curatrix gen model", "tools": {"jdk": "21.0.13+9", "sysml-pilot": "0.63.1"}}
    assert provenance.check(ws, cfg, files(cfg), "model") == []
    assert not provenance.record(ws, cfg, files(cfg), "model")               # stable: unchanged


def test_made_with_another_version_is_reported(tmp_path, monkeypatch):
    ws, cfg = setup_ws(tmp_path, monkeypatch, pilot="0.62.0")                # e.g. an old workspace
    provenance.record(ws, cfg, files(cfg), "model")
    f = provenance.check(ws, cfg, files(cfg), "model")
    assert len(f) == 2 and "sysml-pilot 0.62.0 (tools.yaml: 0.63.1)" in f[0]


def test_drop_and_check_runner(tmp_path, monkeypatch):
    ws, cfg = setup_ws(tmp_path, monkeypatch)
    provenance.record(ws, cfg, files(cfg), "model")
    provenance.record(ws, cfg, [], "model", drop=[files(cfg)[1]])
    assert list(provenance.load(cfg)["files"]) == ["generated/model.json"]
    from curatrix import checks
    assert checks.enabled(cfg, "provenance")
    lv = [b for b in checks.BUILTIN if b[0] == "CK-D5"][0][2]
    assert lv["pr"] == "warning" and lv["baseline"] == "error"


def test_minimum_versions():
    from curatrix import tools
    assert tools.version_ok(">=2.43", "2.56.1") and tools.version_ok(">=22", "22.23.4")
    assert not tools.version_ok(">=3.28", "3.27.9") and not tools.version_ok(">=2.43", None)
    assert tools.version_ok(">=2.43", "2.43.0") and not tools.version_ok(">=1", "")


def test_stale_records_are_reported(tmp_path, monkeypatch):
    ws, cfg = setup_ws(tmp_path, monkeypatch)
    (cfg.repo / "views").mkdir(exist_ok=True)
    gone = cfg.repo / "views" / "old.drawio.svg"
    gone.write_text("x")
    provenance.record(ws, cfg, [gone], "views", versions={"elkjs": "1"})
    gone.unlink()
    assert any("views/old.drawio.svg" in f for f in provenance.stale(cfg))
    provenance.record(ws, cfg, [], "views", drop=[gone])
    assert not any("views/old.drawio.svg" in f for f in provenance.stale(cfg))


def test_leading_version_and_merge_of_minimums(tmp_path):
    from curatrix import tools
    assert not tools.version_ok(">=2.43.5", "2.43 (20190901.0435)")
    assert tools.version_ok(">=4.5.0", "4.5.0-rc1") and tools.version_ok(">=22", "v22.23.4")
    assert tools._stricter(">=2.43", "2.56.1") == "2.56.1" and tools._stricter(">=3", ">=2") == ">=3"
    assert tools._stricter(">=3", "2.9") is None and tools._stricter("1.0", "1.1") is None
    assert tools._stricter(">=10.0", "10.0.*") == "10.0.*"
    a, b = tmp_path / "a.yaml", tmp_path / "b.yaml"
    a.write_text("system: [{name: git, version: '>=2.43'}]\n")
    b.write_text("system: [{name: git, version: '2.56.1'}]\n")
    assert tools.merge([tools.parse(a), tools.parse(b)]).system["git"].version == "2.56.1"
    b.write_text("system: [{name: git, version: '2.40.0'}]\n")
    with pytest.raises(tools.ToolsError):
        tools.merge([tools.parse(a), tools.parse(b)])
    b.write_text("system: [{name: git, version: '>=abc'}]\n")
    with pytest.raises(tools.ToolsError, match="minimum"):
        tools.parse(b)


def test_pinned_ignores_the_role(tmp_path, monkeypatch):
    """CI with a role that does not install a tool still compares its records (xdmod#23)."""
    ws, cfg = setup_ws(tmp_path, monkeypatch)
    from curatrix import tools
    full = tools.load_all(ws)
    monkeypatch.setattr(type(ws), "role", property(lambda self: "nobody-has-this-role"))
    assert provenance.pinned(ws, "model") == {n: full.tools[n].version if n in full.tools else full.system[n].version
                                              for n in provenance.KINDS["model"][1] if n in full.tools or n in full.system}
