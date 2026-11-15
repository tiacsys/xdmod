import os
import subprocess
import xml.etree.ElementTree as ET

from curatrix import setup
from curatrix.ws import Workspace
from helpers import git_init, make_ws


def test_roles_match_repo_topology():
    assert setup.ROLES["syseng"] == []
    assert setup.ROLES["integration"] == ["+ee", "+me", "+sw", "+integration"]
    assert "+kicad-3d" in setup.ROLES["full"] and "+freecad-parts" in setup.ROLES["me"]


def test_claude_links(tmp_path, monkeypatch):
    root = make_ws(tmp_path)
    repo = root / "robarm-ee"
    (repo / "claude" / "skills" / "kicad-edit").mkdir(parents=True)
    (repo / "claude" / "commands").mkdir(parents=True)
    (repo / "claude" / "commands" / "netcheck.md").write_text("x")
    (repo / "checks.yaml").write_text("version: 1\n")
    ws = Workspace(root)
    made = setup.assemble_claude(ws)
    link = root / ".claude" / "skills" / "ee-kicad-edit"
    assert link.is_symlink() and link.resolve() == (repo / "claude/skills/kicad-edit").resolve()
    assert (root / ".claude/commands/ee-netcheck.md").is_symlink()
    assert setup.assemble_claude(Workspace(root)) == []                       # idempotent
    (repo / "claude/commands/netcheck.md").unlink()
    setup.assemble_claude(Workspace(root))
    assert not os.path.lexists(root / ".claude/commands/ee-netcheck.md")     # stale link removed


def test_freecad_and_kicad_config(tmp_path):
    ws = Workspace(make_ws(tmp_path))
    cfg = setup.ensure_freecad_config(ws)
    assert cfg == ws.state / "freecad/config/FreeCAD/v1-1/user.cfg"
    assert 'Name="CompressionLevel" Value="0"' in cfg.read_text()
    cfg.write_text(cfg.read_text().replace('Value="0"', 'Value="6"'))
    setup.ensure_freecad_config(ws)
    vals = [e.get("Value") for e in ET.parse(cfg).iter("FCInt") if e.get("Name") == "CompressionLevel"]
    assert vals == ["0"]
    env = setup.launch_env(ws, "freecad")
    assert env["XDG_CONFIG_HOME"] == str(ws.state / "freecad/config")
    kenv = setup.launch_env(ws, "kicad")
    assert kenv["KICAD_CONFIG_HOME"] == str(ws.state / "kicad")
    assert (ws.state / "kicad/10.0/sym-lib-table").read_text().startswith("(sym_lib_table")
    assert kenv["KICAD10_SYMBOL_DIR"] == kenv["XD_KICAD_SYMBOLS"]


def test_hooks_and_textconv(tmp_path):
    root = make_ws(tmp_path)
    repo = git_init(root / "robarm-me")
    (repo / "checks.yaml").write_text("version: 1\n")
    ws = Workspace(root)
    assert "robarm-me" in setup.install_hooks(ws)
    hook = repo / ".git/hooks/pre-commit"
    assert setup.HOOK_MARK in hook.read_text() and os.access(hook, os.X_OK)
    tc = subprocess.run(["git", "-C", str(repo), "config", "diff.fcstd.textconv"], capture_output=True, text=True).stdout
    assert "gen freecad-json --textconv" in tc
    assert setup.install_hooks(ws) == ["robarm-me"]          # only repos of this workspace, never the real xdmod


def test_doctor_ci_mode_downgrades_system_mismatch(tmp_path, monkeypatch, capsys):
    """Locally a wrong system tool version FAILs (4.4b); on a CI runner (--ci) it is a warning,
    while a tools.yaml tool that is not installed still FAILs."""
    from curatrix import setup
    from curatrix.ws import Workspace
    from helpers import make_ws
    root = make_ws(tmp_path, monkeypatch)
    (root / "xdmod").mkdir()
    (root / "xdmod" / "tools.yaml").write_text(
        "tools: []\nsystem:\n  - {name: git, version: '0.0.1'}\n")
    ws = Workspace(root)
    assert setup.doctor(ws) == 1
    assert "git" in capsys.readouterr().out
    assert setup.doctor(ws, ci=True) == 0
    out = capsys.readouterr().out
    assert "warn git" in out and "runner image" in out
    (root / "xdmod" / "tools.yaml").write_text(
        "tools:\n  - {name: jdk, version: '1', kind: file, url: 'https://x', sha256: 'ab', location: opt/jdk}\nsystem: []\n")
    assert setup.doctor(ws, ci=True) == 1
