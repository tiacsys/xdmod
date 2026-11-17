import json
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
    r = subprocess.run(["kicad-cli", "--version"], env=env, capture_output=True, text=True, check=True, timeout=30)
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


def test_shim_names_are_derived_from_the_install_folders(tmp_path, monkeypatch):
    """All KiCad programs with a kiface (gerbview, pl_editor, ...) and every freecad* program,
    not a short fixed list; GUI shims keep the user's locale, only kicad-cli sets LC_ALL."""
    ws = Workspace(make_ws(tmp_path, monkeypatch))
    sysbin = tmp_path / "usr" / "bin"
    for n in ("kicad", "kicad-cli", "eeschema", "gerbview", "pl_editor", "pcb_calculator", "idfcyl",
              "freecadcmd", "FreeCAD", "fcinfo"):
        _fake_tool(sysbin, n)
    for k in ("_gerbview.kiface", "_pl_editor.kiface", "_pcb_calculator.kiface", "_kipython.kiface"):
        (sysbin / k).write_text("")
    names = setup.shim_names(ws, str(sysbin))
    assert names == ["kicad-cli", "kicad", "eeschema", "gerbview", "pcb_calculator", "pl_editor",
                     "FreeCAD", "freecadcmd"]
    setup.write_shims(ws, str(sysbin))
    assert "LC_ALL" not in (ws.venv / "bin" / "kicad").read_text()
    assert "LC_ALL" not in (ws.venv / "bin" / "gerbview").read_text()
    assert "KICAD_CONFIG_HOME" in (ws.venv / "bin" / "gerbview").read_text()
    assert "XDG_CONFIG_HOME" in (ws.venv / "bin" / "freecadcmd").read_text()


def test_stale_shim_fails_clearly_and_doctor_reports_it(tmp_path, monkeypatch):
    ws = Workspace(make_ws(tmp_path, monkeypatch))
    sysbin = tmp_path / "usr" / "bin"
    real = _fake_tool(sysbin, "kicad-cli")
    path = os.pathsep.join([str(ws.venv / "bin"), str(sysbin)])
    setup.write_shims(ws, path)
    assert setup.shim_real(ws.venv / "bin" / "kicad-cli") == real
    real.unlink()                                                       # KiCad removed or moved
    rows = setup.shim_rows(ws, path)
    assert rows == [("warn", f"stale shim .venv/bin/kicad-cli: {real} is gone", "curatrix update")]
    r = subprocess.run([str(ws.venv / "bin" / "kicad-cli")], capture_output=True, text=True, timeout=30,
                       env={"PATH": "/usr/bin:/bin"})
    assert r.returncode == 127 and "run curatrix update" in r.stderr
    assert setup.write_shims(ws, path) == [] and not (ws.venv / "bin" / "kicad-cli").exists()


def test_doctor_names_a_user_file_in_venv_bin(tmp_path, monkeypatch):
    ws = Workspace(make_ws(tmp_path, monkeypatch))
    sysbin = tmp_path / "usr" / "bin"
    _fake_tool(sysbin, "kicad-cli")
    _fake_tool(ws.venv / "bin", "kicad-cli", "mine")
    rows = setup.shim_rows(ws, os.pathsep.join([str(ws.venv / "bin"), str(sysbin)]))
    assert rows[0][0] == "warn" and "remove or rename .venv/bin/kicad-cli" in rows[0][2]


def test_shims_from_a_worktree_set_belong_to_the_main_workspace(tmp_path, monkeypatch):
    """`curatrix update` in a set must not write the set's paths into the shared .venv/bin."""
    main = make_ws(tmp_path)
    wroot = main / ".worktrees" / "feat" / "x"
    wroot.mkdir(parents=True)
    (wroot / ".venv").symlink_to(os.path.relpath(main / ".venv", wroot))
    (wroot / ".xdmod-worktree.json").write_text(json.dumps({"branch": "feat/x", "main_workspace": str(main)}))
    sysbin = tmp_path / "usr" / "bin"
    _fake_tool(sysbin, "kicad-cli")
    assert setup.write_shims(Workspace(wroot), str(sysbin)) == ["kicad-cli"]
    text = (main / ".venv" / "bin" / "kicad-cli").read_text()
    assert f"# workspace: {main}\n" in text and ".worktrees" not in text
    assert f"KICAD_CONFIG_HOME={main / '.xdmod' / 'kicad'}\n" in text
    assert not (wroot / ".xdmod").exists()


def test_launch_runs_the_real_binary_not_the_shim(tmp_path, monkeypatch):
    ws = Workspace(make_ws(tmp_path, monkeypatch))
    sysbin = tmp_path / "usr" / "bin"
    for n in ("kicad", "FreeCAD"):
        _fake_tool(sysbin, n)
    path = os.pathsep.join([str(ws.venv / "bin"), str(sysbin)])
    setup.write_shims(ws, path)
    monkeypatch.setenv("PATH", path)
    seen = []
    monkeypatch.setattr(setup.limits, "wrap", lambda cmd, lim: cmd)
    monkeypatch.setattr(setup.subprocess, "run",
                        lambda cmd, **kw: seen.append((cmd, kw["env"])) or subprocess.CompletedProcess(cmd, 0))
    assert setup.launch(ws, "kicad", []) == 0
    assert setup.launch(ws, "freecad", []) == 0
    assert [c[0][0] for c in seen] == [str(sysbin / "kicad"), str(sysbin / "FreeCAD")]
    assert seen[0][1]["KICAD_CONFIG_HOME"] == str(ws.state / "kicad")      # launch_env still applies


def test_blender_is_isolated_in_every_call(tmp_path, monkeypatch):
    """Owner decision 2026-11-17 (Blender for the ME renderings): every Blender call gets
    --factory-startup and the user paths under .xdmod/blender, through curatrix and through the
    shim; Blender's Python never sees the workspace .venv. No Blender runs here (fake binary)."""
    from curatrix import blender, limits
    ws = Workspace(make_ws(tmp_path, monkeypatch))
    sysbin = tmp_path / "usr" / "bin"
    _fake_tool(sysbin, "blender", 'echo "$BLENDER_USER_CONFIG|$XDG_CACHE_HOME|$TMPDIR|${VIRTUAL_ENV-unset}|$PATH|$*"')
    path = os.pathsep.join([str(ws.venv / "bin"), str(sysbin), "/usr/bin", "/bin"])
    assert "blender" in setup.write_shims(ws, path)
    text = (ws.venv / "bin" / "blender").read_text()
    assert f"export BLENDER_USER_RESOURCES={ws.state / 'blender' / 'user'}\n" in text
    assert text.rstrip().endswith(f'exec {sysbin / "blender"} --factory-startup --offline-mode --disable-autoexec "$@"')
    home = tmp_path / "home"
    home.mkdir()
    env = {"PATH": path, "HOME": str(home), "VIRTUAL_ENV": str(ws.venv)}
    r = subprocess.run(["blender", "--version"], env=env, capture_output=True, text=True, check=True, timeout=30)
    cfg, cache, tmp, venv, p, args = r.stdout.strip().split("|")
    assert cfg == str(ws.state / "blender" / "user" / "config") and cache.startswith(str(ws.state / "blender"))
    assert tmp == str(ws.state / "blender" / "tmp") and venv == "unset" and str(ws.venv / "bin") not in p
    assert args == "--factory-startup --offline-mode --disable-autoexec --version"
    assert list(home.iterdir()) == []
    # curatrix run / limits.run: the same variables, the real binary, the arguments once
    monkeypatch.setenv("PATH", path)
    e = limits.tool_env(ws, "script", {"PATH": path, "VIRTUAL_ENV": "x"}, ["blender", "--version"])
    assert e["BLENDER_USER_SCRIPTS"] == str(ws.state / "blender" / "user" / "scripts") and "VIRTUAL_ENV" not in e
    assert str(ws.venv / "bin") not in e["PATH"].split(os.pathsep)
    assert limits.tool_cmd(ws, ["blender", "--factory-startup", "-b"]) == \
        [str(sysbin / "blender"), "--factory-startup", "--offline-mode", "--disable-autoexec", "-b"]
    assert limits.tool_cmd(ws, ["git", "status"]) == ["git", "status"]
    assert "BLENDER_USER_CONFIG" not in limits.tool_env(ws, "script", {"PATH": path}, ["git"])
    assert setup.launch_env(ws, "blender")["BLENDER_USER_CONFIG"] == str(ws.state / "blender" / "user" / "config")
    assert blender.find(ws) == sysbin / "blender"


def test_doctor_blender_not_pinnable(tmp_path, monkeypatch, capsys):
    """A system tool with pinned: false (Blender): missing = a note, another version = a warning;
    neither fails the doctor."""
    from curatrix import tools
    ws = Workspace(make_ws(tmp_path, monkeypatch))
    st = tools.SystemTool(name="blender", version="5.2.3", optional=True, pinned=False)
    for have, status in ((None, "note"), ("5.3.0", "warn"), ("5.2.3", "ok")):
        monkeypatch.setattr(tools, "for_role", lambda ts, role: tools.ToolSet(system={"blender": st}))
        monkeypatch.setattr(tools, "system_version", lambda s, w=None: have)
        setup.doctor(ws)
        out = capsys.readouterr().out
        line = next(ln for ln in out.splitlines() if "blender" in ln)
        assert line.strip().startswith(status), line
        assert "FAIL" not in line
