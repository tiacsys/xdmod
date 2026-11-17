"""curatrix end to end in a temporary workspace (no west): gen, check, ids, tombstones."""
import json
import shutil

import pytest

from curatrix import cli
from helpers import FIXTURES, git_init, make_ws


@pytest.fixture
def ws(tmp_path, monkeypatch):
    root = make_ws(tmp_path, monkeypatch)
    repo = git_init(root / "robarm-ee")
    shutil.copytree(FIXTURES / "kicad", repo / "pcba" / "board")
    (repo / "ids.yaml").write_text("EE-CMP:\n  - 1\n  - 2\n  - 3\nEE-PCBA:\n  - 1\nEE-REQ:\n  - 1\n  - 2\n")
    (repo / "checks.yaml").write_text(
        "version: 1\nids: {ledger: ids.yaml}\n"
        "cad: {kicad: ['pcba/*/board.kicad_sch'], freecad: [], needs: generated/cad-needs.json}\n"
        "commands:\n  - {id: CK-X1, name: echo, run: ['{python}', '-c', 'print(42)'], stages: [local]}\n"
        "expect: [CK-B7, CK-C1, CK-C2, CK-D4, CK-H1, CK-H2, CK-H3, CK-H4, CK-H6, CK-H7, CK-X1]\n")
    monkeypatch.chdir(root)
    return root


def run(*args):
    return cli.main(list(args))


def summary(root, repo="robarm-ee"):
    return {c["id"]: c for c in json.loads((root / "build" / repo / "checks" / "summary.json").read_text())["checks"]}


def test_gen_and_check_cad_needs(ws, capsys):
    assert run("check", "robarm-ee", "--only", "CK-D4") == 1                  # not generated yet
    assert run("gen", "cad-needs", "robarm-ee") == 0
    n = json.loads((ws / "robarm-ee/generated/cad-needs.json").read_text())["versions"][""]["needs"]
    assert sorted(n) == ["EE-CMP-0001", "EE-CMP-0002", "EE-CMP-0003"]           # EE-PCBA: the model's
    assert run("check", "robarm-ee", "--stage", "local") == 0
    s = summary(ws)
    assert s["CK-D4"]["status"] == "pass" and s["CK-C1"]["status"] == "pass" and s["CK-X1"]["status"] == "pass"
    assert "CK-B1" not in s                                                    # not a local-stage check
    # CK-D4 is plain Python, so PR CI (no CAD tools, D56) runs it too (task 4.4a)
    assert run("check", "robarm-ee", "--stage", "pr", "--no-cad") == 0
    assert summary(ws)["CK-D4"]["status"] == "pass"
    # delete a traced symbol's TraceID: CK-D4 fails, regenerating leaves a tombstone (D130)
    sch = ws / "robarm-ee/pcba/board/board.kicad_sch"
    sch.write_text(sch.read_text().replace('"TraceID" "EE-CMP-0001"', '"TraceID" ""'))
    assert run("check", "robarm-ee", "--only", "CK-D4") == 1
    assert run("gen", "cad-needs", "robarm-ee") == 0
    tomb = json.loads((ws / "robarm-ee/generated/retired-needs.json").read_text())["versions"][""]["needs"]
    assert list(tomb) == ["EE-CMP-0001"] and tomb["EE-CMP-0001"]["status"] == "retired"
    assert run("check", "robarm-ee", "--stage", "local") == 0                  # CK-B7 is a warning
    assert summary(ws)["CK-B7"]["status"] == "warn"


def test_need_moved_to_another_generated_file_is_no_tombstone(ws):
    """EE-PCBA moves from cad-needs.json to model-needs.json (XD-ADR-0128): no tombstone."""
    from curatrix import checkcfg, gen, needs as needsmod
    repo = ws / "robarm-ee"
    old = {"EE-PCBA-0001": {"id": "EE-PCBA-0001", "type": "ee-pcba", "title": "b", "status": "valid"}}
    needsmod.write(repo / "generated/cad-needs.json", old, "x")
    needsmod.write(repo / "generated/model-needs.json", old, "x")
    (repo / "checks.yaml").write_text((repo / "checks.yaml").read_text() + "model: {files: [model/a.sysml]}\n")
    cfg = checkcfg.load(repo / "checks.yaml", ws)
    tomb, msgs = gen.tombstones(cfg, [gen.cad_needs(None, cfg)])
    assert needsmod.needs_of(json.loads(tomb.text)) == {} and msgs == []


def test_ids_and_placeholders(ws, capsys):
    rst = ws / "robarm-ee/req.rst"
    rst.write_text(".. ee-req:: X\n   :id: EE-REQ-NEW-a\n")
    assert run("check", "robarm-ee", "--only", "CK-C1") == 1
    assert run("ids", "fix", "robarm-ee") == 0
    assert ":id: EE-REQ-0003" in rst.read_text()
    capsys.readouterr()
    assert run("ids", "new", "EE-REQ") == 0
    assert capsys.readouterr().out.strip() == "EE-REQ-0004"
    rst.write_text(rst.read_text() + "\nSee EE-CMP-0042.\n")
    assert run("ids", "check", "robarm-ee") == 1                               # CK-C2: not in the ledger


def test_json_output_and_work_needs_west(ws, capsys):
    capsys.readouterr()
    assert run("check", "robarm-ee", "--only", "CK-C2", "--json") == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] and out["checks"][0]["id"] == "CK-C2" and out["checks"][0]["repro"].startswith("curatrix check")
    assert run("work", "start", "feat/x", "robarm-ee") == 1                  # no west workspace here
    assert "not a west workspace" in capsys.readouterr().err
    assert not (ws / ".worktrees").exists()


def test_env(ws, capsys):
    capsys.readouterr()
    assert run("env") == 0
    out = capsys.readouterr().out
    assert f"export XD_WORKSPACE={ws}" in out and "PYTHONDONTWRITEBYTECODE=1" in out and "XD_KICAD_SYMBOLS=" in out
