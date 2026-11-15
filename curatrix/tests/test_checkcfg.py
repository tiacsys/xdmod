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
bootstrap_template: scripts/bootstrap.sh
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
    assert cfg.section("bootstrap_template") == {"path": "scripts/bootstrap.sh"}
    assert cfg.bootstrap_copy == tmp_path / "ws" / "repo" / "scripts" / "bootstrap.sh"


@pytest.mark.parametrize("value,expect", [(True, "scripts/bootstrap.sh"), ("tools/boot.sh", "tools/boot.sh")])
def test_bootstrap_template_forms(tmp_path, value, expect):
    """CK-H5 accepts the path the README documents, and `true` for the default (regression:
    a string crashed section() with `dict(str)`)."""
    p = tmp_path / "checks.yaml"
    p.write_text(yaml.safe_dump({"bootstrap_template": value}))
    cfg = checkcfg.load(p, tmp_path)
    assert cfg.section("bootstrap_template") is not None
    assert cfg.bootstrap_copy == tmp_path / expect


def test_bootstrap_template_check_runs(tmp_path):
    """The CK-H5 implementation reads the path and compares it with the template."""
    from curatrix import checks
    ws = tmp_path
    (ws / "xdmod" / "templates").mkdir(parents=True)
    (ws / "xdmod" / "templates" / "bootstrap.sh").write_text("#!/bin/sh\n")
    (ws / "m" / "scripts").mkdir(parents=True)
    (ws / "m" / "scripts" / "bootstrap.sh").write_text("#!/bin/sh\necho drift\n")
    (ws / "m" / "checks.yaml").write_text("bootstrap_template: scripts/bootstrap.sh\n")
    cfg = checkcfg.load(ws / "m" / "checks.yaml", ws)
    assert checks.enabled(cfg, "bootstrap_template")
    assert cfg.bootstrap_copy.read_text().endswith("drift\n")


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
    ({"bootstrap_template": ["a"]}, "bootstrap_template must be a path"),
    ({"requirements": "yes"}, "requirements must be true or false"),
])
def test_invalid(tmp_path, bad, msg):
    p = tmp_path / "checks.yaml"
    p.write_text(yaml.safe_dump(bad))
    with pytest.raises(checkcfg.ConfigError, match=msg):
        checkcfg.load(p, tmp_path)
