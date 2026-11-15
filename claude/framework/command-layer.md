# Workspace command layer (task 3.13)

Status: **AGREED 2026-11-14** (review answers → D116–D118). Built on D19, D46, D66–D71, D86–D93, D97, D98, D100 (`../decisions.md`), `repo-topology.md`,
`repo-layouts.md`, and the spike (`env.sh`, check scripts, the interim `xd-limit` wrapper).

## 1. Principles

1. **One entry point: `curatrix`**, installed into the workspace `.venv` from `xdmod/curatrix` (editable install), D98.
2. **Every command runs from the workspace root** (D67). curatrix finds the root (the west topdir) itself, so it also works from a subfolder. Paths in output and docs are relative to the root.
3. **Every tool runs under a memory limit and a timeout** (D71). curatrix applies them itself from a limits table, so `xd-limit` is no longer needed by hand.
4. **No user-global configuration.** KiCad, FreeCAD and drawio get workspace-local config folders and library paths (D88).
5. **Same commands for people, agents and CI.** CI calls the same subcommands with `--stage pr`.

## 2. Bootstrap (new workspace)

From an empty folder:

```sh
git clone https://github.com/tiacsys/robarm-manifest
robarm-manifest/scripts/bootstrap.sh --role ee        # role from repo-topology.md §4
```

`bootstrap.sh` is small and generic; it is a copy of `xdmod/templates/bootstrap.sh` (D118), and `curatrix check robarm-manifest` warns when the copy differs from the template. It does this:
1. Creates `.venv` and installs `west` into it.
2. Runs `west init -l robarm-manifest` and `west update` (minimal default, D93). This brings in xdmod.
3. Runs `pip install -e xdmod/curatrix`.
4. Hands over to `curatrix bootstrap --role ee`.

`curatrix bootstrap --role <role>`:
1. Sets `manifest.group-filter` for the role (D86, D93) and stores the role in `.west/config` (`[xdmod] role = ee`), then runs `west update`.
2. Builds `.venv` from the active repos' `requirements.txt` and installs their `tools.yaml` tools into `.venv/opt/<tool>/`, with sha256 checks (D19).
3. Copies `xdmod/launch/CLAUDE.md` to the root (D69) and assembles `<workspace>/.claude/` (`repo-layouts.md` §3).
4. Installs the pre-commit hooks (D100) and git diff drivers (FreeCAD textconv) in every active repo.
5. Creates `<workspace>/.xdmod/`, the workspace-local state: tool configs for KiCad, FreeCAD and drawio, caches, and the limits table overrides.
6. Runs `curatrix doctor` (§5).

`curatrix bootstrap --role <other>` changes the role later. It's the same steps; repos that become inactive are left on disk.

## 3. Subcommands

| Command | Does | Replaces (spike) |
|---|---|---|
| `curatrix bootstrap --role R` | §2 | manual west + venv setup |
| `curatrix update` | `west update -k` (keeps branches) + refresh `.venv` and tools when the package lists changed | `west update -k` by hand |
| `curatrix check <repo> [--stage …] [--no-cad] [--json]` | the check catalogue (`checks.md`) | `./check` per repo |
| `curatrix gen <what> [<repo>]` | generated files: `stubs`, `model`, `cad-needs`, `freecad-json`, `config-pages`, … | generator scripts |
| `curatrix ids new <KIND> [<file>]` / `ids fix` | issue IDs, replace placeholders (`id-scheme.md` §4) | — |
| `curatrix views [build|check|normalize]` | drawio views as editable SVG (D96) | view scripts |
| `curatrix docs <repo|full> [--open]` | zdocs build into `build/<area>/docs/` (`<area>` defined in `repo-layouts.md` §1) | cmake + ninja calls |
| `curatrix launch kicad|freecad|drawio [file]` | GUI tools with workspace-local config, library variables, templates (§4) | — |
| `curatrix launch claude [args]` | Claude Code at the root, with `.venv/bin` on `PATH` and the workspace env | — |
| `curatrix work start <branch> <repos…>` / `work done <branch>` | git worktrees for parallel work under `<ws>/.worktrees/` (D125) | — |
| `curatrix run -- <cmd>` | any command with the workspace env and default limits | `xd-limit`, `env.sh` |
| `curatrix env` | prints the workspace env for a shell (`eval "$(curatrix env)"`) | `env.sh` |
| `curatrix doctor` | checks tools, versions, paths, libraries, hooks, west state; prints fixes | — |

## 4. GUI launchers

| Tool | Environment set by `curatrix launch` |
|---|---|
| KiCad | `KICAD_CONFIG_HOME=<ws>/.xdmod/kicad` (no user-global libraries); `XD_KICAD_SYMBOLS`, `XD_KICAD_FOOTPRINTS`, `XD_KICAD_3DMODELS`, `XD_KICAD_TEMPLATES` → `libs/kicad/*`; project library tables use these variables (`repo-layouts.md` §2) |
| FreeCAD | workspace-local user config and data folders under `<ws>/.xdmod/freecad/`, with `CompressionLevel = 0` (D63), our TechDraw templates and the `libs/freecad` parts path. The exact mechanism (environment variables or command-line options of FreeCAD 1.1) is verified in Phase 4 |
| drawio | system binary (D97); opens `.drawio.svg` files; after saving, the pre-commit normalizer cleans the file |

GUI tools get a memory limit only, no timeout (§6, D117).

## 5. Environment and state

- `<ws>/.venv/`: Python, west, curatrix, pinned packages, `opt/` tools (JDK, Pilot, node packages, gh).
- `<ws>/.xdmod/`: workspace-local configs, caches and limit overrides. It isn't a repo and isn't shared.
- `<ws>/build/<area>/`: all outputs (D46).
- `curatrix env` sets `PATH`, `ZEPHYR_BASE`, `ZEPHYR_SDK_INSTALL_DIR` (from `tools.yaml`), `JAVA_HOME`, `XD_*` library variables and `PYTHONDONTWRITEBYTECODE=1`.

## 6. Limits (D71)

curatrix reads `xdmod/curatrix/limits.yaml` (defaults per tool and use; values from `../notes/toolchain.md`). A workspace can override it in `<ws>/.xdmod/limits.yaml`. Every subprocess runs in a systemd user scope with `MemoryMax` and no swap, plus `timeout`, the same as `xd-limit` today. On GitHub runners curatrix uses the systemd backend too: ubuntu-24.04 runners answer `systemd-run --user`. Without a systemd user session it falls back to `timeout` plus `ulimit -v` (address-space limit); CI proves that fallback in a smoke step, and the job's own `timeout-minutes` caps the whole run.

| Use | Memory | Timeout |
|---|---|---|
| GUI tools (KiCad, FreeCAD, drawio) | 8G | **none** (D117) |
| all others | see `../notes/toolchain.md` | |

## 7. Answered review questions (2026-11-14)

1. **Only `curatrix`**, with no `west xd` alias (D116).
2. **GUI tools** get a memory limit only (8 GB, no swap), no timeout (D117).
3. **`bootstrap.sh`** is a copy in robarm-manifest, made from xdmod's template and checked for drift (D118).
