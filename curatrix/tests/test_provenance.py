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
