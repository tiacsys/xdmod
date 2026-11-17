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
    assert "+ee" in setup.ROLES["me"] and "+ee" in setup.ROLES["sw"]   # task 5.14: KiCad files, pin maps


def test_update_reapplies_the_role(monkeypatch):
    from types import SimpleNamespace
    calls = []
    ws = SimpleNamespace(has_west=True, role="sw")
    monkeypatch.setattr(setup, "set_role", lambda w, r: calls.append(("role", r)))
    monkeypatch.setattr(setup, "west", lambda w, *a, **k: calls.append(("west", a)) or 0)
    monkeypatch.setattr(setup, "refresh", lambda w, adopt=False: None)
    monkeypatch.setattr(setup, "doctor", lambda w, quiet=False: 0)
    assert setup.update(ws) == 0
    assert calls == [("role", "sw"), ("west", ("update", "-k"))]   # filter first, then the update
    calls.clear()
    ws.role = None                                                    # no role: filter untouched
    setup.update(ws)
    assert calls == [("west", ("update", "-k"))]


def test_doctor_warns_on_missing_kicad_models_only_for_3d_roles(tmp_path):
    ws = Workspace(make_ws(tmp_path))
    for role in ("ee", "me", "integration", "sw", None):
        assert setup.kicad_models_row(ws, role) is None
    assert setup.kicad_models_row(ws, "ee3d")[0] == "warn"
    assert setup.kicad_models_row(ws, "full", ci=True) is None
    (ws.root / "libs" / "kicad" / "packages3D").mkdir(parents=True)
    assert setup.kicad_models_row(ws, "full") is None


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


def _fake_tool(d, name, body="echo real"):
    d.mkdir(parents=True, exist_ok=True)
    p = d / name
    p.write_text(f"#!/bin/sh\n{body}\n")
    p.chmod(0o755)
    return p


def test_shims_set_the_workspace_config_and_exec_the_real_binary(tmp_path, monkeypatch):
    """Owner decision 2026-11-17: a bare `kicad-cli --version` rewrote ~/.config/kicad. The shims
    in .venv/bin set what `curatrix run` sets and exec the real binary by absolute path. No KiCad or
    FreeCAD runs here: the "real" tools are fake scripts."""
    ws = Workspace(make_ws(tmp_path, monkeypatch))
    sysbin = tmp_path / "usr" / "bin"
    for n in ("kicad-cli", "FreeCADCmd"):
        _fake_tool(sysbin, n)
    path = os.pathsep.join([str(ws.venv / "bin"), str(sysbin)])
    assert setup.write_shims(ws, path) == ["kicad-cli", "FreeCADCmd"]   # only tools that exist
    assert not (ws.venv / "bin" / "pcbnew").exists()
    kc = (ws.venv / "bin" / "kicad-cli").read_text()
    assert setup.is_shim(ws.venv / "bin" / "kicad-cli") and os.access(ws.venv / "bin" / "kicad-cli", os.X_OK)
    assert f"export KICAD_CONFIG_HOME={ws.state / 'kicad'}\n" in kc
    for var in ("KICAD_CACHE_HOME", "KICAD_DOCUMENTS_HOME", "KICAD10_SYMBOL_DIR", "KICAD10_FOOTPRINT_DIR"):
        assert f"export {var}=" in kc
    assert "export LC_ALL=C.UTF-8\n" in kc and "XDG_" not in kc
    assert kc.rstrip().endswith(f'exec {sysbin / "kicad-cli"} "$@"')
    fc = (ws.venv / "bin" / "FreeCADCmd").read_text()
    assert f"export XDG_CONFIG_HOME={ws.state / 'freecad' / 'config'}\n" in fc and "LC_ALL" not in fc
    # same variables as `curatrix run -- kicad-cli`
    run = setup.limits.tool_env(ws, "script", {}, ["kicad-cli"])
    assert setup.shim_env(ws, "kicad-cli") == dict(sorted(run.items()))
    # idempotent; a tool that is gone loses its shim
    assert setup.write_shims(ws, path) == ["kicad-cli", "FreeCADCmd"]
    (sysbin / "FreeCADCmd").unlink()
    assert setup.write_shims(ws, path) == ["kicad-cli"]
    assert not (ws.venv / "bin" / "FreeCADCmd").exists()


def test_shim_runs_with_the_workspace_config_without_touching_home(tmp_path, monkeypatch):
    ws = Workspace(make_ws(tmp_path, monkeypatch))
    sysbin = tmp_path / "usr" / "bin"
    _fake_tool(sysbin, "kicad-cli", 'echo "$KICAD_CONFIG_HOME|$LC_ALL|$*"')
    setup.write_shims(ws, os.pathsep.join([str(ws.venv / "bin"), str(sysbin)]))
    home = tmp_path / "home"
    home.mkdir()
    env = {"PATH": os.pathsep.join([str(ws.venv / "bin"), str(sysbin), "/usr/bin", "/bin"]), "HOME": str(home)}
    r = subprocess.run(["kicad-cli", "--version"], env=env, capture_output=True, text=True, check=True)
    assert r.stdout.strip() == f"{ws.state / 'kicad'}|C.UTF-8|--version"
    assert list(home.iterdir()) == []


def test_shims_never_point_at_themselves_or_other_shims(tmp_path, monkeypatch):
    ws = Workspace(make_ws(tmp_path, monkeypatch))
    other = tmp_path / "other-ws" / ".venv" / "bin"                    # another workspace's shim
    _fake_tool(other, "kicad-cli", setup.SHIM_MARK + "\nexec /nowhere")
    linked = tmp_path / "venv-link"                                     # .venv/bin under another name
    linked.symlink_to(ws.venv / "bin")
    # no real binary: no shim, and none that execs itself
    path = os.pathsep.join([str(ws.venv / "bin"), str(linked), str(other)])
    assert setup.write_shims(ws, path) == []
    real = _fake_tool(tmp_path / "usr" / "bin", "kicad-cli")
    assert setup.write_shims(ws, path + os.pathsep + str(real.parent)) == ["kicad-cli"]
    assert setup.real_tool(ws, "kicad-cli", path + os.pathsep + str(real.parent)) == real
    assert f"exec {real} " in (ws.venv / "bin" / "kicad-cli").read_text()
    # a non-shim file of the same name in .venv/bin is left alone
    (ws.venv / "bin" / "kicad").write_text("#!/bin/sh\nmine\n")
    _fake_tool(real.parent, "kicad")
    setup.write_shims(ws, str(real.parent))
    assert (ws.venv / "bin" / "kicad").read_text() == "#!/bin/sh\nmine\n"


def test_doctor_warns_when_kicad_on_path_is_not_the_shim(tmp_path, monkeypatch, capsys):
    ws = Workspace(make_ws(tmp_path, monkeypatch))
    sysbin = tmp_path / "usr" / "bin"
    _fake_tool(sysbin, "kicad-cli")
    rows = setup.shim_rows(ws, str(sysbin))                             # no shim yet
    assert rows[0][0] == "warn" and "kicad-cli" in rows[0][1] and "curatrix update" in rows[0][2]
    setup.write_shims(ws, str(sysbin))
    rows = setup.shim_rows(ws, str(sysbin))                             # shim exists, PATH without .venv/bin
    assert rows[0][0] == "warn" and 'curatrix env' in rows[0][2]
    assert setup.shim_rows(ws, os.pathsep.join([str(ws.venv / "bin"), str(sysbin)])) == \
        [("ok", "KiCad/FreeCAD shims first on PATH", ".venv/bin")]
    assert setup.shim_rows(ws, str(tmp_path / "empty")) == []          # no KiCad, no FreeCAD: nothing
    monkeypatch.setenv("PATH", os.pathsep.join([str(sysbin), os.environ["PATH"]]))
    setup.doctor(ws)
    assert "warn kicad-cli on PATH is" in capsys.readouterr().out


def test_curatrix_env_puts_the_shims_first(tmp_path, monkeypatch):
    ws = Workspace(make_ws(tmp_path, monkeypatch))
    assert ws.env()["PATH"].split(os.pathsep)[0] == str(ws.venv / "bin")
    assert ws.run_env()["PATH"].split(os.pathsep)[0] == str(ws.venv / "bin")
