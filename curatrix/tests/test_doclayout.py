"""CK-A7, the document layout (tiacsys/xdmod#69 Q8, finding 15)."""
from curatrix import checkcfg, checks, doclayout

REG = """groups:
  - id: g
    title: G
documents:
  ee-req:
    group: g
    builders: [html]
  pcba-a:
    group: g
    doc_dir: pcbas/pcba-a
    builders: [html]
  harnesses:
    group: g
    builders: [html]
  # upstream
  se-req:
    group: g
    doc_dir: ../../s/docs/se-req
    builders: [html]
"""


def _repo(tmp_path, reg=REG, folders=("ee-req", "pcbas/pcba-a", "harnesses")):
    repo = tmp_path / "r"
    (repo / "docs").mkdir(parents=True)
    (repo / "docs/documents.yaml").write_text(reg)
    for f in folders:
        (repo / "docs" / f).mkdir(parents=True)
        (repo / "docs" / f / "conf.py").write_text("")
    (repo / "harness/cab").mkdir(parents=True)
    (repo / "harness/cab/cab.yml").write_text("connectors: {}\n")
    (repo / "checks.yaml").write_text("version: 1\ndocs: {registry: docs/documents.yaml}\n"
                                      "cad: {harnesses: [\"harness/*/*.yml\"]}\n")
    return checkcfg.load(repo / "checks.yaml", tmp_path)


def test_good_layout(tmp_path):
    cfg = _repo(tmp_path)
    assert doclayout.findings(cfg) == []
    assert checks.enabled(cfg, "docs+deliverables")


def test_planted_errors(tmp_path):
    """A board document outside docs/pcbas/, an unregistered document folder, a missing folder, a
    harness-<cable> document and no harnesses document."""
    reg = REG.replace("    doc_dir: pcbas/pcba-a\n", "").replace("  harnesses:", "  harness-cab:") + \
        "  ee-test-spec:\n    group: g\n    builders: [html]\n"
    cfg = _repo(tmp_path, reg, folders=("ee-req", "pcba-a", "harness-cab", "fw/old"))
    f = doclayout.findings(cfg)
    assert any("pcba-a: in r/docs/pcba-a/, not in r/docs/pcbas/pcba-a/" in x for x in f), f
    assert any("r/docs/fw/old/conf.py: a document folder that no entry" in x for x in f), f
    assert any("ee-test-spec: r/docs/ee-test-spec/conf.py missing" in x for x in f), f
    assert any("harness-cab: one document `harnesses`" in x for x in f), f
    assert any("no `harnesses` document" in x for x in f), f
    assert len(f) == 5, f
