import pytest
import yaml

from curatrix import checkcfg

FULL = """
version: 1
area: robarm-syseng
docs: {registry: docs/documents.yaml}
ids: {ledger: ids.yaml, exclude: ["docs/examples/**"]}
model:
  libraries: ["{ws}/libs/pleml/PLEML.sysml"]
  files: [model/generated/NeedStubs.sysml, "model/*.sysml"]
  export: [RobArm]
  json: generated/model.json
  needs: generated/model-needs.json
  variants: true
stubs: {out: model/generated/NeedStubs.sysml, docs: [se-req], package: NeedStubs}
views: {dir: views}
cad: {kicad: ["pcba/*/*.kicad_sch"], freecad: ["parts/*.FCStd"], needs: generated/cad-needs.json}
requirements: true
commands:
  - id: CK-F1
    name: pin maps
    run: ["{python}", "tests/check_pinmap.py"]
    stages: [local, baseline]
    cad: true
"""


def test_full_example_is_valid(tmp_path):
    (tmp_path / "ws" / "repo" / "model").mkdir(parents=True)
    p = tmp_path / "ws" / "repo" / "checks.yaml"
    p.write_text(FULL)
    (tmp_path / "ws" / "repo" / "model" / "a.sysml").write_text("")
    (tmp_path / "ws" / "repo" / "model" / "b.sysml").write_text("")
    cfg = checkcfg.load(p, tmp_path / "ws")
    assert cfg.area == "robarm-syseng"
    assert cfg.resolve("{ws}/libs/x") == tmp_path / "ws" / "libs" / "x"
    assert [f.name for f in cfg.globs(["model/b.sysml", "model/*.sysml"])] == ["b.sysml", "a.sysml"]
    assert cfg.commands[0].cad and cfg.commands[0].use == "script"
    assert cfg.ids_exclude == ["docs/examples/**"]
    assert cfg.section("requirements") == {}


def test_defaults_without_file(tmp_path):
    cfg = checkcfg.load(tmp_path / "checks.yaml", tmp_path)
    assert cfg.area == tmp_path.name and cfg.section("docs") is None and cfg.commands == []


@pytest.mark.parametrize("bad,msg", [
    ({"vers": 1}, "unknown key"),
    ({"version": 2}, "version"),
    ({"model": {"files": ["a"], "colour": 1}}, "unknown key 'colour'"),
    ({"model": {"export": ["X"]}}, "model.files is required"),
    ({"stubs": {"out": "x"}}, "stubs.docs"),
    ({"commands": [{"id": "X", "name": "x", "run": "echo hi"}]}, "run must be a non-empty list"),
    ({"commands": [{"id": "X", "name": "x", "run": ["a"], "stages": ["nightly"]}]}, "unknown stage"),
    ({"commands": [{"id": "X", "name": "x", "run": ["a"]}, {"id": "X", "name": "y", "run": ["b"]}]}, "duplicate id"),
    ({"commands": [{"id": "X", "name": "x", "run": ["a"], "level": "fatal"}]}, "level"),
])
def test_invalid(tmp_path, bad, msg):
    p = tmp_path / "checks.yaml"
    p.write_text(yaml.safe_dump(bad))
    with pytest.raises(checkcfg.ConfigError, match=msg):
        checkcfg.load(p, tmp_path)
