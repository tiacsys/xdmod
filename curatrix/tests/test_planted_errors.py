"""Every built-in check fails on a planted error (task 5.3, exit criterion 2 of Phase 5).

PLANTED maps each check ID of checks.BUILTIN to the test that plants an error the check must
report: a case in this module, or an existing test elsewhere (by node id). A check without an
entry fails `test_every_check_has_a_planted_error`. Cases marked `tools` need a tool (the Pilot)
and run only locally: `curatrix fixtures` runs every entry, also those, and records the result
(rule, tool versions, date) for the Phase 5 review and every baseline.
"""
import json
import subprocess
import zipfile

import pytest

from curatrix import checkcfg, checks, gen, graph, needs as needsmod
from curatrix.ws import Repo, Workspace
from helpers import git_init

HERE = "curatrix/tests/test_planted_errors.py"

# check ID -> node id (relative to xdmod/) of the test that plants an error it must find
PLANTED = {
    "CK-A6": "curatrix/tests/test_needs_config.py::test_planted_error_fails",
    "CK-A1": f"{HERE}::test_a1_unknown_link",
    "CK-A3": f"{HERE}::test_a3_id_does_not_match_its_type",
    "CK-B1": f"{HERE}::test_b1_requirement_not_refined",
    "CK-B2": f"{HERE}::test_b2_requirement_not_verified",
    "CK-B3": f"{HERE}::test_b3_link_to_retired",
    "CK-B4": "curatrix/tests/test_variants.py::test_planted_errors",
    "CK-B5": f"{HERE}::test_b5_duplicate_id",
    "CK-B6": f"{HERE}::test_b6_stale_evidence",
    "CK-B7": f"{HERE}::test_b7_tombstone",
    "CK-C1": f"{HERE}::test_c1_placeholder",
    "CK-C2": f"{HERE}::test_c2_id_not_in_ledger",
    "CK-D1": f"{HERE}::test_d1_stale_stubs",
    "CK-E1": f"{HERE}::test_e1_pilot_error_through_the_check",
    "CK-D2": f"{HERE}::test_d2_stale_model_json",
    "CK-D3": "curatrix/tests/test_views.py::test_content_change_and_stale_picture",
    "CK-D4": "curatrix/tests/test_cli.py::test_gen_and_check_cad_needs",
    "CK-D6": f"{HERE}::test_d6_code_changed_after_gen",
    "CK-D5": "curatrix/tests/test_provenance.py::test_made_with_another_version_is_reported",
    "CK-E4": f"{HERE}::test_e4_conformance",
    "CK-B8": f"{HERE}::test_b8_variants_across_levels",
    "CK-F6": "curatrix/tests/test_eeprojects.py::test_f6_folder_rule",
    "CK-F7": "curatrix/tests/test_eeprojects.py::test_f7_one_to_one",
    "CK-E2": f"{HERE}::test_e2_value_not_in_sentence",
    "CK-E3": f"{HERE}::test_e3_wrong_ears_pattern",
    "CK-G1": f"{HERE}::test_g1_g2_changed_need_makes_links_suspect",
    "CK-G2": f"{HERE}::test_g1_g2_changed_need_makes_links_suspect",
    "CK-H1": f"{HERE}::test_h1_compressed_fcstd",
    "CK-H2": f"{HERE}::test_h2_build_output",
    "CK-H3": f"{HERE}::test_h3_unpinned_requirement",
    "CK-H4": f"{HERE}::test_h4_missing_trailer",
    "CK-H5": f"{HERE}::test_h5_bootstrap_drift",
    "CK-H6": "curatrix/tests/test_check_runner.py::test_expect_list",
    "CK-H7": "curatrix/tests/test_check_runner.py::test_pr_size_counts_hand_written_lines_only",
}


# control tests: the clean case must pass, or a check that fails on everything would look fine
CONTROLS = ["curatrix/tests/test_needs_config.py::test_sample_builds_strict"]


def test_every_check_has_a_planted_error():
    assert sorted(PLANTED) == sorted(b[0] for b in checks.BUILTIN)


# ------------------------------------------------------------------ helpers
def _ctx(tmp_path, needs=(), yaml_text="version: 1\n", stage="local", owners=None):
    root = tmp_path / "ws"
    repo = git_init(root / "r")
    (repo / "checks.yaml").write_text(yaml_text)
    ws = Workspace(root)
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    ctx = checks.Ctx(ws, Repo("r", repo, "r"), checkcfg.load(repo / "checks.yaml", root), stage, False, None, out)
    ctx.graph = graph.Graph({n["id"]: n for n in needs}, owners or {})
    ctx.graph_findings = graph.check(ctx.graph, stage)
    return ctx


def _run(ctx, cid, fn, level="error"):
    r = checks.Result(cid, cid, level=level)
    fn(ctx, r)
    return r.findings


def _graph_finds(tmp_path, cid, needs, stage="local", owners=None):
    ctx = _ctx(tmp_path, needs, stage=stage, owners=owners)
    return _run(ctx, cid, checks.c_graph)


V = {"status": "valid"}
REQ = {"id": "SYS-REQ-0001", "type": "sys-req", **V, "content": "The arm shall answer within 50 ms."}
SWR = {"id": "SW-REQ-0001", "type": "sw-req", **V, "refines": ["SYS-REQ-0001"]}


def _commit(repo, rel, text, msg=None):
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", msg or rel], check=True)


# ------------------------------------------------------------------ graph rules
def test_a1_unknown_link(tmp_path):
    assert _graph_finds(tmp_path, "CK-A1", [REQ, {**SWR, "refines": ["SYS-REQ-0099"]}])


def test_a3_id_does_not_match_its_type(tmp_path):
    assert _graph_finds(tmp_path, "CK-A3", [REQ, {"id": "SYS-REQ-0002", "type": "sw-req", **V}])


def test_b1_requirement_not_refined(tmp_path):
    assert _graph_finds(tmp_path, "CK-B1", [REQ], stage="full")


def test_b2_requirement_not_verified(tmp_path):
    assert _graph_finds(tmp_path, "CK-B2", [REQ, SWR], stage="full")


def test_b3_link_to_retired(tmp_path):
    assert _graph_finds(tmp_path, "CK-B3", [{**REQ, "status": "retired"}, SWR])


def test_b5_duplicate_id(tmp_path):
    assert _graph_finds(tmp_path, "CK-B5", [REQ, SWR], stage="full",
                        owners={"SYS-REQ-0001": ["a/needs.json", "b/needs.json"]})


def test_b6_stale_evidence(tmp_path, monkeypatch):
    tr = {"id": "TR-INT-STC-0001-aaaaaaaa", "type": "tr", **V, "result_of": ["INT-STC-0001"],
          "shas": ["r=1111111111111111111111111111111111111111"]}
    ctx = _ctx(tmp_path, [tr], stage="full")
    monkeypatch.setattr(Workspace, "repos", property(lambda self: [Repo("r", self.root / "r", "r", "2" * 40)]))
    f = _run(ctx, "CK-B6", checks.c_stale, "report")
    assert f and "TR-INT-STC-0001-aaaaaaaa" in f[0] and "no pinned SHAs" not in f[0], f


def test_b7_tombstone(tmp_path):
    ctx = _ctx(tmp_path, yaml_text="version: 1\ncad: {needs: generated/cad-needs.json}\n")
    rp = gen.retired_path(ctx.cfg)
    rp.parent.mkdir(parents=True)
    rp.write_text(needsmod.dumps(needsmod.doc({"EE-CMP-0001": {"id": "EE-CMP-0001", "type": "ee-cmp",
                                                               "status": "retired", "title": "x"}}, "r")))
    assert _run(ctx, "CK-B7", checks.c_tombstones, "warning")


# ------------------------------------------------------------------ IDs
def test_c1_placeholder(tmp_path):
    ctx = _ctx(tmp_path, yaml_text="version: 1\nids: {ledger: ids.yaml}\n")
    _commit(ctx.repo.path, "docs/x.rst", ".. sys-req:: X\n   :id: SYS-REQ-NEW-a\n")
    assert _run(ctx, "CK-C1", checks.c_placeholders)


def test_c2_id_not_in_ledger(tmp_path):
    ctx = _ctx(tmp_path, yaml_text="version: 1\nids: {ledger: ids.yaml}\n")
    _commit(ctx.repo.path, "ids.yaml", "SYS-REQ:\n  - 1\n")
    _commit(ctx.repo.path, "docs/x.rst", ".. sys-req:: X\n   :id: SYS-REQ-0007\n")
    assert _run(ctx, "CK-C2", checks.c_ledger)


# ------------------------------------------------------------------ generated files
def test_d1_stale_stubs(tmp_path, monkeypatch):
    ctx = _ctx(tmp_path, yaml_text="version: 1\nstubs: {out: model/generated/NeedStubs.sysml, docs: [se-req]}\n")
    nj = tmp_path / "se-req" / "needs.json"
    nj.parent.mkdir()
    nj.write_text(json.dumps(needsmod.doc({"SYS-REQ-0001": {**REQ, "title": "answer"}}, "x")))
    monkeypatch.setattr(gen, "docs_needs_json", lambda ws, cfg, ids=None: [nj])
    stale = ctx.repo.path / "model" / "generated" / "NeedStubs.sysml"
    stale.parent.mkdir(parents=True)
    stale.write_text("package NeedStubs {}\n")                       # the need is missing in it
    f = _run(ctx, "CK-D1", checks.c_stubs)
    assert f and "does not match the needs" in f[0], f


def test_d6_code_changed_after_gen(tmp_path):
    ctx = _ctx(tmp_path, yaml_text="version: 1\ncode: {sources: ['src/*.h'], needs: generated/code-needs.json}\n")
    h = ctx.repo.path / "src" / "a.h"
    h.parent.mkdir()
    h.write_text("/**\n * @xdid{SW-IMPL-0001}\n * Implements SW-DD-0001.\n */\nint a(void);\n")
    o = gen.code_needs(ctx.ws, ctx.cfg)
    o.write()
    assert not _run(ctx, "CK-D6", checks.c_codeneeds)
    h.write_text(h.read_text().replace("SW-DD-0001", "SW-DD-0002"))   # the link changes in the code
    f = _run(ctx, "CK-D6", checks.c_codeneeds)
    assert f and "does not match the code" in f[0], f


@pytest.mark.tools
def test_d2_stale_model_json(tmp_path):
    """Needs the Pilot (local only): a model.json that does not match the model fails CK-D2."""
    from test_tools_live import need_pilot
    need_pilot()
    from curatrix.ws import Workspace as W
    real = W()
    ctx = _ctx(tmp_path, yaml_text="version: 1\nmodel: {files: [model/a.sysml]}\n")
    (ctx.repo.path / "model").mkdir()
    (ctx.repo.path / "model" / "a.sysml").write_text("package A { part def B; }\n")
    ctx.ws = real
    ctx.cfg = checkcfg.load(ctx.repo.path / "checks.yaml", real.root)
    mjson, mneeds, _ = gen.model(real, ctx.cfg)                       # the true outputs ...
    mneeds.write()
    mjson.path.parent.mkdir(parents=True, exist_ok=True)
    mjson.path.write_text("{}\n")                                     # ... and a stale model.json
    f = _run(ctx, "CK-D2", checks.c_model)
    assert any("model.json does not match the model" in x for x in f), f


@pytest.mark.tools
def test_e1_pilot_error_through_the_check(tmp_path):
    """CK-E1 through c_model: a model the Pilot rejects is a finding (not only pilot.run)."""
    from test_tools_live import need_pilot
    need_pilot()
    from curatrix.ws import Workspace as W
    real = W()
    ctx = _ctx(tmp_path, yaml_text="version: 1\nmodel: {files: [model/a.sysml]}\n")
    (ctx.repo.path / "model").mkdir()
    (ctx.repo.path / "model" / "a.sysml").write_text("package A { part x : NoSuchType; }\n")
    ctx.ws = real
    ctx.cfg = checkcfg.load(ctx.repo.path / "checks.yaml", real.root)
    f = _run(ctx, "CK-E1", checks.c_model)
    assert f and any("error" in x.lower() for x in f), f


def test_e4_conformance(tmp_path):
    """CK-E4 through c_conformance (plain Python): a board def that does not redefine an inherited
    system port, read against the upstream model.json named in checks.yaml."""
    from helpers import FIXTURES
    d = FIXTURES / "sysml" / "domain"
    ctx = _ctx(tmp_path, yaml_text="version: 1\nmodel: {files: [model/a.sysml], upstream: up/model.json}\n")
    for src, dst in (("ee-model.json", "generated/model.json"), ("sys-model.json", "up/model.json")):
        (ctx.repo.path / dst).parent.mkdir(parents=True, exist_ok=True)
        (ctx.repo.path / dst).write_text((d / src).read_text())
    f = _run(ctx, "CK-E4", checks.c_conformance)
    assert any("EeBoards::SensorBoard: port bus" in x and "is not redefined" in x for x in f), f
    (ctx.repo.path / "up/model.json").unlink()
    assert any("model.upstream up/model.json" in x for x in _run(ctx, "CK-E4", checks.c_conformance))


def test_b8_variants_across_levels(tmp_path):
    """CK-B8 through c_domain_variants (plain Python): two variants serve one usage in one
    configuration, another usage has none, and a variant is missing in the KiCad project."""
    import json as _json
    from helpers import FIXTURES
    d = FIXTURES / "sysml" / "domain"
    ctx = _ctx(tmp_path, yaml_text="version: 1\nmodel: {files: [model/a.sysml], upstream: up/model.json}\n"
                                   "cad: {kicad: [\"pcba/*/*.kicad_sch\"]}\nvariants: true\n")
    for src, dst in (("ee-model.json", "generated/model.json"), ("sys-model.json", "up/model.json")):
        (ctx.repo.path / dst).parent.mkdir(parents=True, exist_ok=True)
        (ctx.repo.path / dst).write_text((d / src).read_text())
    pro = ctx.repo.path / "pcba" / "ctrl" / "ctrl.kicad_pro"
    pro.parent.mkdir(parents=True)
    (pro.parent / "ctrl.kicad_sch").write_text("(kicad_sch (version 20260306))\n")
    pro.write_text(_json.dumps({"text_variables": {"TraceID": "EE-PCBA-0001"},
                                "schematic": {"variants": [{"name": "std"}]}}))
    f = _run(ctx, "CK-B8", checks.c_domain_variants, "warning")
    assert any("2 variants (a, b) for usage Sys::Arm::servo1 in configuration SYS-CFG-0001" in x for x in f), f
    assert any("no variant for usage Sys::Arm::servo1 in configuration SYS-CFG-0002" in x for x in f), f
    assert any("CtrlFast: variant 'fast' is not in ctrl.kicad_pro" in x for x in f), f
    assert not any("CtrlStd" in x for x in f), f
    assert "| SYS-CFG-0002 | Sys::Arm::ctrlB | EE-PCBA-0001 | fast |" in (ctx.out / "variants-across-levels.md").read_text()


# ------------------------------------------------------------------ requirements
def test_e2_value_not_in_sentence(tmp_path):
    ctx = _ctx(tmp_path, [{**REQ, "max": "40", "unit": "ms"}])
    assert _run(ctx, "CK-E2", checks.c_ears, "warning")


def test_e3_wrong_ears_pattern(tmp_path):
    ctx = _ctx(tmp_path, [{**REQ, "ears": "event"}])
    assert _run(ctx, "CK-E3", checks.c_ears, "warning")


# ------------------------------------------------------------------ change impact
def test_g1_g2_changed_need_makes_links_suspect(tmp_path, monkeypatch):
    ctx = _ctx(tmp_path, [REQ, SWR], stage="pr")
    base = tmp_path / "base" / "needs.json"
    base.parent.mkdir()
    base.write_text(json.dumps(needsmod.doc({"SYS-REQ-0001": REQ, "SW-REQ-0001": SWR}, "x")))
    new = tmp_path / "new" / "needs.json"
    new.parent.mkdir()
    new.write_text(json.dumps(needsmod.doc({"SYS-REQ-0001": {**REQ, "content": "40 ms"}, "SW-REQ-0001": SWR}, "x")))
    monkeypatch.setattr(gen, "docs_needs_json", lambda ws, cfg, ids=None: [new])
    ctx.base = base.parent
    r = checks.Result("CK-G1", "diff", level="report")
    checks.c_diff(ctx, r)
    assert r.status != "skip" and r.findings and "suspect" in r.findings[0], r.findings


# ------------------------------------------------------------------ hygiene
def test_h1_compressed_fcstd(tmp_path):
    ctx = _ctx(tmp_path)
    f = ctx.repo.path / "parts" / "p.FCStd"
    f.parent.mkdir()
    with zipfile.ZipFile(f, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("Document.xml", "<Document>" + "x" * 1000 + "</Document>")
    subprocess.run(["git", "-C", str(ctx.repo.path), "add", "-A"], check=True)
    assert _run(ctx, "CK-H1", checks.c_hygiene_compress)


def test_h2_build_output(tmp_path):
    ctx = _ctx(tmp_path)
    (ctx.repo.path / "build").mkdir()
    (ctx.repo.path / "build" / "x.o").write_text("x")
    assert _run(ctx, "CK-H2", checks.c_hygiene_build)


def test_h3_unpinned_requirement(tmp_path):
    ctx = _ctx(tmp_path)
    (ctx.repo.path / "requirements.txt").write_text("sphinx\n")
    assert _run(ctx, "CK-H3", checks.c_pins, "warning")


def test_h4_missing_trailer(tmp_path):
    ctx = _ctx(tmp_path)
    _commit(ctx.repo.path, "a.txt", "a")
    subprocess.run(["git", "-C", str(ctx.repo.path), "update-ref", "refs/remotes/origin/main", "HEAD"], check=True)
    _commit(ctx.repo.path, "b.txt", "b", "b\n\nGenerated with [Claude Code], trailer forgotten")   # agent commit, no trailer
    assert _run(ctx, "CK-H4", checks.c_trailers, "warning")


def test_h5_bootstrap_drift(tmp_path):
    ctx = _ctx(tmp_path, yaml_text="version: 1\nbootstrap_template: scripts/bootstrap.sh\n")
    (ctx.repo.path / "scripts").mkdir()
    (ctx.repo.path / "scripts" / "bootstrap.sh").write_text("#!/bin/sh\necho drift\n")
    assert _run(ctx, "CK-H5", checks.c_bootstrap, "warning")
