# curatrix

The XDMOD workspace command layer (D98, `command-layer.md`): one CLI for people, agents and CI.
Checks, generators, IDs, views, docs builds, tool installation and GUI launchers, every tool under a
memory limit and a timeout (D71).

- Python ≥ 3.12, only PyYAML at runtime. Installed **editable** into the workspace venv:
  `.venv/bin/pip install -e xdmod/curatrix` (`templates/bootstrap.sh` does this).
- **Run every command from the workspace root** (D67). curatrix finds the root itself: `$XD_WORKSPACE`,
  else the nearest folder with `.west/`, else the folder above the xdmod checkout it was installed from.
- Status: iteration 1, first version (task 4.8). See [What is implemented](#what-is-implemented).

Contents: [CLI](#cli) · [checks.yaml](#checksyaml) · [Check catalogue](#check-catalogue) ·
[limits.yaml](#limitsyaml) · [tools.yaml](#toolsyaml) · [ids.yaml](#idsyaml-the-ledger) ·
[Generated files](#generated-files) · [Evidence](#evidence-run-records) · [Worktrees](#worktrees-d125) · [Model conventions](#sysml-model-conventions) ·
[CAD trace fields](#cad-trace-fields) · [Views](#views-drawiosvg) · [Docs](#docs-layout-and-the-sphinx-extension) ·
[Tests](#tests)

## CLI

| Command | Does |
|---|---|
| `curatrix env [--shell fish]` | prints the workspace env: `eval "$(curatrix env)"` (`PATH`, `ZEPHYR_BASE`, `JAVA_HOME`, `XD_KICAD_*`, `XD_CAM_OUT` (`build/cam`, the output folder of the template jobset), `XD_FREECAD_PARTS`, `env:` of tools.yaml tools such as `ZEPHYR_SDK_INSTALL_DIR` and `XD_STEPUP`, `XD_FREECAD_MCP_TOKEN` (from `.xdmod/freecad/mcp-token`), `PYTHONDONTWRITEBYTECODE=1`) |
| `curatrix run [--use USE] [-m MEM] [-t TIME] [-v] -- CMD…` | any command with the workspace env and limits (default use `script`, 1G/5m; `blender` for a `blender` command). Exit 124 = timeout, 137 = killed (memory) |
| `curatrix limits` | resolved limits table and backend (systemd / ulimit) |
| `curatrix fixtures` | runs the planted error of every built-in check (`curatrix/tests/test_planted_errors.py`, also the tool-backed ones) under limits and records the result in `build/fixtures/planted.json` (rule, test, result, tool versions, date). Exit 1 if a check did not fail on its planted error. Run for the Phase 5 review and at every baseline |
| `curatrix doctor` | Python, venv, west state, role, every tools.yaml tool (installed version vs. pinned → **FAIL on mismatch**), system tool versions (FAIL on mismatch, `optional` → warning when missing; `pinned: false` (Blender) → a note when missing, a warning on another version), limits backend, Zephyr, zdocs, launch CLAUDE.md, `.xdmod/`, hooks, missing KiCad 3D models (`libs/kicad/packages3D`) in every role that runs EE design output (`ee`, `ee3d`, `me`, `integration`, `full`; warning), KiCad/FreeCAD/Blender names on PATH that are not the `.venv/bin` shims, stale shims (warnings). Exit 1 on any FAIL |
| `curatrix bootstrap --role R [--adopt] [--no-west] [--no-doctor]` | `west config manifest.group-filter` for the role + `xdmod.role`, `west update`, pip install of all active repos' `requirements.txt` (uv if present), tools.yaml tools into `.venv/opt` (sha256), copy `xdmod/launch/CLAUDE.md` to the root, `.claude/` symlinks (D113), pre-commit hooks + FreeCAD textconv (D100), `.xdmod/`, shims in `.venv/bin` for every KiCad and FreeCAD program found (XD-ADR-0145: workspace-local config, then exec of the real binary; always the main workspace's, also from a set), doctor. `--adopt`: stamp tools already in `.venv/opt` instead of re-downloading |
| `curatrix update [--adopt]` | fast-forwards the manifest repo to its remote default branch (fetch + `merge --ff-only`, only when it is on that branch, without changes to tracked files and not ahead; else a warning), `west update -k`, re-executes itself when that moved xdmod (the new curatrix does the rest), then the same refresh (pip only if a requirements file changed). Refuses inside a worktree set. The first update after this came in runs the old code: fast-forward the manifest repo once by hand (`git -C <manifest> fetch origin && git -C <manifest> merge --ff-only origin/main`) |
| `curatrix launch kicad\|freecad\|blender\|drawio\|claude [ARGS…]` | GUI tools from the root with workspace-local config, memory limit only (D117). See [Launchers](#launchers) |
| `curatrix docs <repo\|full> [--open]` | zdocs build of `<repo>/docs` into `build/<area>/docs/` (strict, D64c) |
| `curatrix check [<repo>] [--stage local\|pr\|full\|baseline] [--no-cad] [--only IDs] [--base DIR] [--json]` | the repo's checks ([catalogue](#check-catalogue)); logs + `build/<area>/checks/summary.json`; prints a reproduce command per failure. `--only CK-D,CK-C1` runs those even outside the stage. `--json` puts the summary on stdout, the log on stderr |
| `curatrix gen stubs\|model\|cad-needs\|freecad-json\|tombstones\|all [<repo>] [--check]` | regenerate committed generated files ([Generated files](#generated-files)); `--check` only compares |
| `curatrix gen connectors [<repo>]` | `generated/<project>.connectors.json` per KiCad project (plain Python; `cad.connectors`) |
| `curatrix gen cad-exports [<repo>]` | kicad-cli sheet SVGs + BOM CSV into `build/<area>/cad/` (local, not committed) for the CAD directives |
| `curatrix gen freecad-json --textconv FILE` | semantic JSON of one `.FCStd` on stdout (git textconv driver, installed by bootstrap) |
| `curatrix new pcba <BoardDef> [--repo R] [--no-kicad]` | a KiCad project for a board def of the repo's EE model (task 5.17): `pcba/<board-def>/` from `xdmod/templates/kicad-pcba/` (`.kicad_pro` with `TraceID` = the def's `EE-PCBA` and `XD_VERSION = unversioned`, ERC/DRC severities, library tables with workspace variables only, the jobset), schematic and board saved by KiCad (`kicad-cli sch\|pcb upgrade --force`, `kicad-cli` limits), the document `docs/pcba-<board-def>/` and its registry entry. External parts get no project |
| `curatrix cam <repo> [<name>] [--update-jobset \| --board-model \| --library [--into DIR]]` | EE design output of a `pcba/` project or a harness named `<name>` (default: all; a name that is both is refused). A board (task 5.20, XD-ADR-0142; local, needs KiCad): copies the `pcba/` project into `build/<area>/cam/<project>/<version>/project/`, writes `XD_VERSION` (`git describe --tags --match '<project>/*'`; `-dirty`/`-preview` unless an exact tag on main with a clean folder; no tag: `<project>/v0.0.0-<n>-g<sha>-preview`) into the copy, runs the jobset there (`XD_CAM_OUT` = the version folder, `TMPDIR` under `build/`), fails when fewer jobs succeeded than the jobset has, exports the schematic SVG per variant, writes `stackup.csv`, `design-rules.csv` and `cam.json`. Checks the 3D model of every footprint (paths resolved with the KiCad run's variables): `cam.json` `kicad_3d_models` = `present` \| `partial` \| `missing` \| `none`, `kicad_3d_models_missing`, `renderings_marked`; when models are missing it warns and puts a red banner on every `render-*.png` (KiCad renders a bare board silently; the board document shows a warning). Refuses a jobset with an Execute Command job, a file or folder outside `${XD_CAM_OUT}`, a job without a variant after a variant job, or a wrong variant name. `--update-jobset` writes the project's jobset from the shared template and its variants. A harness (task 5.22, XD-ADR-0127): WireViz as a separate process (`wireviz` limits) on a copy of `harness/<name>/<name>.yml` with the version as diagram label: `<name>.svg`, `.png`, `.bom.tsv`, `cam.json` in the version folder; same version rule. An assembly of an ME repo (a repo with `cad.freecad` and without `cad.projects`; task 5.26, XD-ADR-0143; local, needs FreeCAD): `FreeCADCmd` (`templates/freecad-asm/cam-asm.py`) per variant (each configuration a link's own `Configs` names, and `base` with only the links without `Configs`; no `Configs` at all: `all`) into `build/<area>/cam/<asm>/<version>/<asm>/<variant>/`: `<asm>.step`, `parts/<part>.3mf` and `.stl` per printed part (`PrintProfile`) with the short version (`vX.Y.Z`, `P` appended for a preview) embossed on its version mark in the pinned font (fails unless exactly one valid solid), `print/<profile>.ini` copied from the repo's `print/`, TechDraw views `views/*.svg`, `drawing.svg` and `drawing.pdf` (a plain-Python view sheet, not a TechDraw page: front, top and right in first-angle projection, aligned, at one standard scale, the iso view, frame and title block with the full version, scale, projection symbol and `PREVIEW`; no dimensions, no TechDraw template, since a full TechDraw page needs the GUI binary, which hangs offscreen; a view without a visible edge fails the run), `exploded.svg` (moves from `assemblies/<asm>/explode.yaml` or automatic), `renderings/front|top|right|iso.png` (task 5.30, XD-ADR-0147, the fallback when Blender is absent: shaded, 1600 x 1200 px, with visible edges; FreeCAD's tessellation drawn into a numpy z-buffer in `cam-asm.py`, text and PNG by FreeCAD's Qt, no OpenGL; front, top and right at one scale, iso at its own, the scale in px/mm on the image; method `zbuffer` in `cam.json`; a pinned font that does not load fails the run; assembly, variant, version and view on each image, `PREVIEW` in red unless a release; a rendering without a drawn facet fails the run; listed in `cam.json` per variant. With Blender on the machine and without `--no-blender`: `cam-asm.py` writes `<variant>.scene.glb` beside `cam.json` instead and `templates/blender/render-asm.py` renders the same files with Cycles on the CPU (same scales and marking, fixed samples and seed, half the cores as threads, Freestyle edges, `blender` limits, isolated call); `cam.json` `renderings.method` is `blender` or `zbuffer`; per variant `painted` = facets that won a pixel (z-buffer), `pixels` = pixels off the background (Blender), `facets` = triangles drawn or exported), `bom.csv` (flat, with totals), `mass.json` (mass and center of gravity from the volume and center of mass of every present part and the density of its `Material` in `data/materials.yaml`, or its own `Mass` / `Density` property; task 5.27), and in the version folder `findings.json` (the ME check findings CK-F4c, CK-F16, CK-F17 of the assembly and the shared documents with their acceptance state; one more `FreeCADCmd` run); the version is a preview also when `parts/`, `lib/` or `print/` have changes; the md5 of every source document must be unchanged afterwards. `cam.json` has `kind: board\|harness\|assembly`. `--board-model` (task 5.29, XD-ADR-0139; local, needs KiCad and FreeCAD): one `pcba/` project as FreeCAD model per variant into `build/<area>/board-model/<name>/<version>/`: `kicad-cli pcb export step --no-dnp --subst-models [--variant]` on the build copy (no tracks), then the FreeCAD GUI binary on Qt's offscreen platform (`templates/freecad-pcba/import-step.py`, `ImportGui.insert`, no window): `App::Part` `Board` with `TraceID` = the project's `EE-PCBA`, `Version`, `Variant`, `Board`, `Commit`, holding one `App::Link` per component named by its reference designator (`PCB` = board body) to its 3D model, stored once per model in the hidden group `Models` with the STEP colours per face (`ShapeAppearance`, `GuiDocument.xml`), saved uncompressed; `board-model.json` lists components and colours; a file above 5 MB or saved compressed is a finding (exit 1), a file without colours is a finding. `--library [--into DIR]`: the same for a release only (an exact tag `<name>/vX.Y.Z` without suffix on main, clean folder; refused otherwise, before KiCad runs), then copies the files into `boards/<name>/<name>-<vX.Y.Z>[-<variant>].FCStd` of the board library (a checkout with a `board_library` section, on a branch other than main); never overwrites a file |
| `curatrix new asm <AssemblyDef> [--repo R] [--no-freecad]` | the FreeCAD documents of an assembly def of the repo's ME model (task 5.23, XD-ADR-0137): `assemblies/<assembly-def>/` with the top document `<name>.FCStd` (`Assembly::AssemblyObject` with `TraceID` = the def's `ME-ASM`, a `Joints` group, a link to the skeleton) and `<name>-skeleton.FCStd` (spreadsheet `Params`, master sketch `MasterSketch` in the part `Skeleton`), both written by `FreeCADCmd` (`xdmod/templates/freecad-asm/new-asm.py`, `freecad` limits, workspace config; success from the script's result file), the document `docs/asm-<assembly-def>/` and its registry entry |
| `curatrix gen freecad-params <repo>` | the ME model drives the CAD (task 5.24, XD-ADR-0137): writes the parameters of every top-level assembly def (aliases `<usage>_<attribute>`, see CK-F3) into `Params` of its `<name>-skeleton.FCStd` with `FreeCADCmd` (`templates/freecad-asm/write-params.py`, `freecad` limits): opens the skeleton, then the top document, writes values only, recomputes skeleton, parts, top, checks every object and saves only the documents whose values or shapes changed; success from the script's result file (`build/<area>/freecad-params/`) |
| `curatrix ids new KIND [FILE] [--repo R]` | issue the next ID of KIND from the owning ledger; with FILE, replace that file's first `KIND-NEW-…` placeholder |
| `curatrix ids fix [<repo>] [--dry-run]` | replace every placeholder `<KIND>-NEW-<tag>` in the repo (same tag → same ID in every file) |
| `curatrix ids check [<repo>]` | CK-C1 + CK-C2 |
| `curatrix views build [<repo>] [--view NAME]` | model JSON → view graph (`build/<area>/views/<view>.json`) → elkjs → drawio → headless Firefox → `views/<view>.drawio.svg` |
| `curatrix views check [<repo>]` | CK-D3 (no browser) |
| `curatrix views normalize [<repo> \| FILES…] [--check]` | rewrite editor-saved `.drawio.svg` into the normalized form (decompress, drop editor attributes, sort cells, re-render, hash) |
| `curatrix variants list [<repo>] [--json]` | every board and assembly variant across levels (xdmod#69 Q14), plain Python: the model def (`DomainVariant`, `variantName`), the KiCad variant (`.kicad_pro` `schematic.variants`, description) or FreeCAD configuration-table row, the differences (parts fitted differently from the base schematic, e.g. `R1 DNP`, and where the `.kicad_pcb` footprint fits it differently in that variant, `R1 DNP (board: fitted)`; the row's parameters and links with `Configs`), and the (configuration, usage) pairs it serves (the dependencies CK-B8 reads, `domvariants.table`); a variant that serves no pair is listed and marked, a pair no variant serves is listed. Order: serving variants first, then by configuration, then in CAD order. Text table, `--json` for tools. Without a repo: the repo of the current folder, as `pleml check` does; from the workspace root every repo that has variants |
| `curatrix pleml check [<repo>] [--model FILE] [-v]` | PLEML feature-variation rules F1, F2, V1–V5 on a model JSON (Pilot export or compact), CK-B4 alone. `curatrix variants [<repo>]` (no `list`) is its old name: still works for one release, with a deprecation warning |
| `curatrix needs-diff BEFORE AFTER [-o FILE]` | change impact between two sets of needs.json (files or folders): changed needs, SUSPECT (direct/transitive), DANGLING. Exit 1 if any |
| `curatrix evidence record TWISTER_DIR --config SYS-CFG-n [--kind sim\|hil] [--setup S] [--branch B] [--create] [--dry-run]` | a run record from a Twister output dir + the workspace state, committed onto the orphan branch `evidence` of robarm-integration through a worktree in `build/evidence/` ([Evidence](#evidence-run-records)) |
| `curatrix evidence preview TWISTER_DIR -o FILE [--tests DIR] [--config SYS-CFG-n]` | preview `TR` needs from a local Twister output dir, for the docs build of the same check run (no record, never evidence); no Twister output: removes FILE |
| `curatrix evidence read [--repo R] [--branch B] [-o FILE]` | run records → `TR` needs (`build/<repo>/evidence/tr-needs.json`), stale ones tagged |
| `curatrix trace <repo\|full> [--canary SYS-CFG-n] [-o DIR]` | minimal trace report from the last docs build: one row per `SYS-REQ` (refined by, satisfied by, verified by test cases, also through refining requirements, latest result: one per test case, newest by `run_id`, not per platform; gaps). Only evidence counts: a `preview` result is shown as "preview, not evidence" and a `stale` one is a gap. Requirements of the configuration `canary` (all their `configs` canary ones, or `configures` from a canary `SYS-CFG`: tag `canary` or "canary" in the title, or `--canary`) in their own section, left out of the coverage numbers (P5-16). Writes `build/<area>/trace/trace.md`, `trace.html`, `trace.json` |
| `curatrix evidence validate FILE` | a record against the schema |
| `curatrix work start <branch> <repos…> [--base <parent>]` / `work done <branch> [--force] [--delete-branch]` / `work list` | worktree set `.worktrees/<branch>/` for parallel work (D125): the named repos as git worktrees on `<branch>` (new branches start from `main`, or from `<parent>` for a stacked PR), the other framework repos as detached worktrees, shared trees symlinked to the main checkout, its own `.west/`, `build` → `build/wt-<branch>/`. Work from `.worktrees/<branch>/` ([Worktrees](#worktrees-d125)) |
| `curatrix hook pre-commit` | what the installed git hook runs (CK-C1 warning, CK-H1, `.drawio.svg` freshness, FCStd-without-JSON warning) |

Roles (`--role`, repo-topology.md §4): `syseng` (manifest default, D93), `ee` (`+ee`), `ee3d`
(`+ee,+kicad-3d`), `me` (`+me,+freecad-parts,+ee`), `sw` (`+sw,+ee`), `integration` (`+ee,+me,+sw,+integration`),
`full` (all, incl. big libraries), `ci-full` (= integration).

### Launchers

| Tool | Environment |
|---|---|
| `kicad` | `KICAD_CONFIG_HOME=<ws>/.xdmod/kicad` (with empty global `sym-lib-table`/`fp-lib-table` in `10.0/`, so no user-global libraries and no first-run dialog); `XD_KICAD_SYMBOLS`, `XD_KICAD_FOOTPRINTS`, `XD_KICAD_3DMODELS`, `XD_KICAD_TEMPLATES` → `libs/kicad/*`, also as `KICAD10_*_DIR`. A `.kicad_sch` argument opens eeschema |
| `freecad` | `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_CACHE_HOME` → `<ws>/.xdmod/freecad/{config,data,cache}`. **Verified with FreeCAD 1.1.4**: it then reads `…/config/FreeCAD/v1-1/user.cfg`; curatrix keeps `BaseApp/Preferences/Document/CompressionLevel = 0` there (D63; a save then stores entries at ~100 %). `FREECAD_USER_HOME`/`FREECAD_USER_DATA` are ignored by 1.1. `XD_FREECAD_PARTS` → `libs/freecad` (the parts-library add-on preference is not set yet). `--mcp`: the FreeCAD MCP addon (tools.yaml `freecad-mcp-addon`, in the workspace `Mod/`) starts its XML-RPC server on 127.0.0.1:9875 (token, remote off) for this run only (`auto_start_rpc` on, and off again when FreeCAD exits; every launch without `--mcp` switches it off), with `HOME=.xdmod/stepup/home` (StepUp writes `~/ksu-config.ini`; `XAUTHORITY` kept) |
| `blender` | Always `--factory-startup --offline-mode --disable-autoexec`; `BLENDER_USER_RESOURCES`, `BLENDER_USER_CONFIG`, `_SCRIPTS`, `_DATAFILES`, `_EXTENSIONS` → `<ws>/.xdmod/blender/user/…`, `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_CACHE_HOME` → `<ws>/.xdmod/blender/xdg/…`, `TMPDIR` → `<ws>/.xdmod/blender/tmp`; without `VIRTUAL_ENV` and without any venv on `PATH` (Blender's Python would take the workspace venv and miss its own numpy); `<ws>/.xdmod/blender/bin` (a copy of the shim) first on `PATH`, so a `blender` that a child process starts is isolated too. The same for `curatrix run -- blender` (limits `blender`) and the `.venv/bin/blender` shim. **Verified with Blender 5.2.3**: `~/.config/blender` and `~/.cache/blender` unchanged. Optional, not pinnable (owner decision 2026-11-17) |
| `drawio` | `/usr/bin/drawio --user-data-dir=<ws>/.xdmod/drawio`; after saving a `.drawio.svg`, run `curatrix views normalize <file>` (the pre-commit hook insists) |
| `claude` | Claude Code at the root with the workspace env; memory limit `claude` (8G), no timeout |

## checks.yaml

`<repo>/checks.yaml` says what `curatrix check <repo>` runs. A missing file is an error. Every key is
optional; an absent section switches its checks off, and `curatrix check` prints which checks are off
and why. `expect:` lists the checks the repo runs, so that a lost section fails CK-H6. A run that plans
no check fails, and an error-level check skipped at the baseline stage fails. Paths are relative to the repo unless they start with `{ws}/`. Globs (`*`,
`**`) are expanded in the order given. Unknown keys are errors.

```yaml
version: 1                          # schema version (only 1)
area: robarm-syseng                 # build/<area>/ (default: the repo folder name)

docs:                               # CK-A6 strict docs build; its needs.json feed CK-A1/A3/A4/A5, CK-B*, CK-E2/E3, CK-G*
  registry: docs/documents.yaml     # informational; the build uses <repo>/docs/CMakeLists.txt

ids:                                # CK-C1 (placeholders), CK-C2 (ledger)
  ledger: ids.yaml                  # default
  exclude: ["docs/examples/**"]     # fnmatch globs: files whose IDs / placeholders are examples

model:                              # CK-E1, CK-D2 (needs the Pilot), CK-B4 (variants)
  libraries: ["{ws}/libs/pleml/PLEML.sysml"]   # loaded first; xdmod/sysml/*.sysml is always loaded first of all
  files: [model/generated/NeedStubs.sysml, "model/*.sysml"]   # required; read as ONE set, so order does not matter
  export: [RobArm]                  # packages to export (default: every top-level package of `files`, nested ones excluded)
  json: generated/model.json        # compact model JSON (default)
  needs: generated/model-needs.json # model-derived needs (default)
  variants: true                    # run CK-B4 on the model JSON
  upstream: ["{ws}/myproj-syseng/generated/model.json"]   # domain models: the upstream's committed model JSON (CK-E4, CK-B8)

variants:                           # CK-B8 variants across levels (domain repos; needs model.upstream, reads cad.kicad, cad.projects, cad.freecad)
  zephyr: ["{ws}/myproj-sw/boards"] # optional: Zephyr board roots; their board.yml variants map to board variants by name.
                                    # Zephyr board = KiCad project name, lower case, `-` as `_`; `outer/inner` counts as `inner`;
                                    # a Zephyr board without such a project is ignored

stubs:                              # CK-D1
  out: model/generated/NeedStubs.sysml   # default
  docs: [se-req]                    # required: doc ids whose needs.json (build/<area>/docs/deploy/html/<doc>/) feed the stubs
  package: NeedStubs                # default

views:                              # CK-D3 (needs `model` too)
  dir: views                        # default; one <view>.drawio.svg per view
  model: generated/model.json       # default: model.json

cad:                                # CK-D4 (plain Python: runs without CAD tools), CK-H1
  projects: ["pcba/*/*.kicad_pro", "proto/*/*.kicad_pro"]   # CK-F6, CK-F7 (with `model`); root sheet = <name>.kicad_sch
  connectors: generated             # CK-D7, CK-D8, CK-F1 (with `model`): <dir>/<project>.connectors.json per project
  harnesses: ["harness/*/*.yml"]    # CK-F7, CK-F1 (with `model`), `curatrix cam`: WireViz harnesses, <name>/<name>.yml
  kicad: ["pcba/*/*.kicad_sch"]     # extra ROOT schematics (the projects' root sheets are read anyway); sheets are followed
  freecad: ["parts/*.FCStd", "assemblies/**/*.FCStd"]
  needs: generated/cad-needs.json   # default
  freecad_json: generated/freecad   # optional: semantic JSON per .FCStd (<path>.FCStd.json)
  board_library: "{ws}/<library>"   # CK-F21 (an ME repo): links into this board library that have a newer version there

board_library:                      # CK-F20: this repo IS the board library (XD-ADR-0139)
  source: "{ws}/<ee repo>"          # required: the EE repo with the board tags <board>/vX.Y.Z
  max_mb: 5                         # default: the size limit per file

code:                               # CK-D6 (plain Python): code units and test cases from the C sources
  sources: ["app/src/**/*.[ch]"]    # @xdid{SW-IMPL-nnnn} Doxygen blocks
  tests: ["tests/**/*.c"]           # "Test case: SW-TC-nnnn. Verifies ..." in the comment above ZTEST
  needs: generated/code-needs.json  # default

requirements: true                  # CK-E2 / CK-E3 on the repo's own requirement needs
bootstrap_template: scripts/bootstrap.sh   # CK-H5 (robarm-manifest): copy must equal xdmod/templates/bootstrap.sh
pr_size: {lines: 600, files: 15}    # CK-H7: PR size warning (the defaults)
expect: [CK-A6, CK-A1, CK-C1, CK-H2]   # CK-H6: exactly the checks this repo runs (built-in + commands)

commands:                           # repo-specific checks (CK-F*, tests, ...)
  - id: CK-F1                       # required, unique
    name: KiCad netlist vs. interface pin maps   # required
    run: ["{python}", "tests/check_pinmap.py", "-o", "{build}/pinmap.xml"]   # required argv (no shell)
    use: kicad-cli                  # limits.yaml use (default: script)
    stages: [local, baseline]       # default: all four
    cad: true                       # needs CAD tools: skipped with --no-cad (default false)
    level: error                    # error | warning | report (default error)
    cwd: "{repo}"                   # default
    before_docs: false              # true: runs before the docs build (CK-A6), e.g. tests whose results the docs show
```

Placeholders in `run` and `cwd`: `{ws}` workspace root, `{repo}` repo folder, `{build}`
`build/<area>/checks`, `{area}`, `{python}` the venv's python. A command fails when it exits non-zero;
its output is in `build/<area>/checks/<id>.log`. Commands with `before_docs: true` run first, in
the order of the file, before CK-A6 and the other built-in checks; all other commands run last.
Every check run first removes `build/<area>/checks/preview/` (`{build}/preview`): outputs that
belong to one run, such as preview test results, go there, so no later docs build of another run
shows them as its own.

**Summary JSON** (`build/<area>/checks/summary.json`, also `--json`):
`{"repo", "area", "stage", "no_cad", "ok", "checks": [{"id", "name", "status", "level", "findings": [str], "log", "repro", "seconds"}]}`
with `status` = `pass | fail | warn | report | skip`. A stage fails iff a check has `fail`.

## Check catalogue

Each built-in check is also an `XD-CHECK` need (D121). Its need ID and the method rules (`XD-RULE`) it
`enforces` are in `src/curatrix/data/checks.yaml` (IDs from xdmod's ledger; a test keeps it in step with
`checks.BUILTIN`). The XDMOD manual renders the needs and the table with the `xd-check-needs` and
`xd-check-table` directives (`sphinx/xdmod_sphinx/reference.py`).

Stages from `checks.md`. "own" = curatrix's graph check over all needs.json files of the docs build
(own and imported needs, so it also sees upstream needs, which sphinx-needs' schema skips).

| ID | Check | Needs section | Stages (level) | Implemented |
|---|---|---|---|---|
| CK-A6 | docs build strict (zdocs); sphinx-needs schema covers CK-A1–A3 per document | `docs` | all (error) | yes |
| CK-A1 | link to an unknown ID (own, over imported needs too) | `docs` | all | yes |
| CK-A3 | ID matches the scheme and its kind matches the need type | `docs` | all | yes |
| ~~CK-A4~~ | retired 2026-11-17: R3 orphans is a schema rule of `needs_config.toml` (CK-A6) | — | — | — |
| ~~CK-A5~~ | retired 2026-11-17: R5 HIL fields is a schema rule of `needs_config.toml` (CK-A6) | — | — | — |
| CK-B1 | R1 every SYS-REQ refined or satisfied (`draft` sources don't count) | `docs` | full, baseline | yes |
| CK-B2 | R2 every requirement verified | `docs` | full, baseline (warning, D99) | yes, **not per configuration** yet |
| CK-B3 | R4 links to retired needs | `docs` | local/pr/full warning, baseline error (D75) | yes |
| CK-B4 | variant rules F1, F2, V1–V5 (alone: `curatrix pleml check`) | `model.variants` | all | yes (V6, T1–T3: later, D135) |
| CK-B8 | variants across levels: exactly one domain variant per configuration and usage, the variant in KiCad `schematic.variants` / a FreeCAD configuration table, Zephyr board variants by name, at most two per board; the computed table "configuration → variant per usage" is in the log `variants-across-levels.md`; `curatrix variants list` shows every variant with what it serves | `variants` | local, pr, full (warning) | yes (unused variants: iteration 2) |
| CK-B5 | duplicate IDs across documents | `docs` | full, baseline | yes |
| CK-B6 | R5a stale evidence: `TR.shas` vs. current pins (`west list`) | `docs` | full, baseline (report) | first version |
| CK-B7 | tombstones in `generated/retired-needs.json` | `model`, `cad` or `code` | local, pr (warning) | yes |
| CK-C1 | placeholder IDs | `ids` | all (error) | yes |
| CK-C2 | every ID of an owned kind in the sources is in the ledger | `ids` | local, pr, baseline | yes |
| CK-D1 | SysML stubs match the needs | `stubs` | local, pr, baseline | yes |
| CK-E1 | the Pilot parses the model with 0 errors | `model` | local, pr, baseline | yes |
| CK-D2 | `model.json` + `model-needs.json` match the model | `model` | local, pr, baseline | yes |
| CK-E4 | conformance of a domain model to its upstream (inherited ports redefined, port defs specialize, name clashes solved, link type per kind pair) on the committed JSON, no Java | `model.upstream` | local, pr (warning) | yes |
| CK-D3 | views: content, uncompressed, geometry sane, picture fresh | `views` | local, pr, baseline | yes (kinds `interconnection`, `decomposition`) |
| CK-D4 | `cad-needs.json` matches KiCad/FreeCAD files (plain Python, so also in PR CI) | `cad` | local, pr, baseline | yes |
| CK-F6 | KiCad projects by `.kicad_pro`: one per folder, named like the folder, root sheet of the same name; no KiCad project file outside the project folders (plain Python) | `cad.projects` | local, pr, baseline (warning) | yes |
| CK-F7 | board defs of the EE model (`XdDomain::Pcba`) 1:1 with `pcba/` projects by `TraceID` = `EE-PCBA`, folder named after the def; external parts have none (plain Python, committed `model.json`) | `cad.projects` + `model` | local, pr, baseline (warning) | yes (`proto/` projects: not yet); cable defs 1:1 with `harness/<name>/<name>.yml` by `metadata.TraceID` = `EE-HAR` (with `cad.harnesses`) |
| CK-F14 | assembly defs of the ME model (`XdDomain::Assembly`) 1:1 with FreeCAD documents by `TraceID` = `ME-ASM`, file named after the def; a top-level assembly is `assemblies/<name>/` with `<name>.FCStd` and `<name>-skeleton.FCStd`; no `XLink` from another document to a top document (plain Python, committed `model.json`) | `cad.freecad` + `model` | local, pr, baseline (warning) | yes |
| CK-F15 | FreeCAD links (`App::Link`) per part or sub-assembly in an assembly's document = its usages: ME model usages (multiplicity) plus the system model's usages in the realized blocks (`model.upstream`), per configuration (`Configs` on links; model usages not filtered yet); targets named by their `TraceID`; the skeleton link not counted; a repeated system usage, a block realized twice and a multiplicity range are findings | `cad.freecad` + `model` | local, pr, baseline (warning) | yes |
| CK-F4c | every FreeCAD document of `cad.freecad` recomputes in `FreeCADCmd` (each assembly's skeleton, then its top document, then the rest; nothing saved) without an invalid object; exploded-view proxies left out; an error passes only when accepted in `assemblies/<name>/accepted.yaml` (rule `recompute`, items `<stem>#<object>`, `Accepted-by:` as CK-F9); report `build/<area>/checks/me-checks/CK-F4c.txt` | `cad.freecad` | local, baseline (warning), needs FreeCAD | yes |
| CK-F16 | objects with an `ME-PART` `TraceID` are valid solids (Part check valid, at least one solid, each with a volume, no free face or shell); rule `solid` | `cad.freecad` | local, baseline (warning), needs FreeCAD | yes |
| CK-F17 | no overlap (boolean common) above 0.001 mm³ between the direct children of an assembly, per variant (`Configs` on links); joined pairs (assembly joints) 0.1 mm³; skeleton link and library fasteners (`lib/` objects with `Standard`) left out; rule `overlap`, items the two link names | `cad.freecad` | local, baseline (warning), needs FreeCAD | yes |
| CK-F18 | board models (links to an `EE-PCBA` object) inside their `SYS-IF` space budget; always a skip with its reason until task 5.28 gives the budget its form (no board model, or board models placed but not checked); never a finding | `cad.freecad` | local, baseline (warning), needs FreeCAD | yes |
| CK-F19 | every printed part (an object with a `PrintProfile`) has one version mark in its document: an LCS with `Role = version-emboss` (`TextSize`, `MaxWidth`, optional `EmbossDepth`), where `curatrix cam` embosses the version (plain Python) | `cad.freecad` | local, pr (warning) | yes |
| CK-F3 | `Params` of `assemblies/<name>/<name>-skeleton.FCStd`: aliases `<usage>_<attribute>` = the values of the top-level assembly def's part and port usages in the ME model (units mm, cm, m, deg, rad); LCS with `Port` at the port's `x`, `y`, `z`, `yaw`, `pitch`, `roll` (composed with the top document's link to the skeleton); tolerance per kind (0.001 mm, 0.001 deg) or `@XdDomain::ModelMatchTolerance` (model-to-CAD agreement, in the attribute's unit); at most ten parameters; no unknown alias (plain Python) | `cad.freecad` + `model` | local, pr, baseline (warning) | yes (variant rows: not yet) |
| CK-D7 | `generated/<project>.connectors.json` equals the connector tables read from the schematic (plain Python, so also in PR CI); no file of a removed project | `cad.projects` + `cad.connectors` | local, pr (warning) | yes |
| CK-D8 | the plain-Python connector extraction equals `kicad-cli sch export netlist --format kicadxml` (P5-15); netlists in `build/<area>/checks/netlists/` | `cad.projects` + `cad.connectors` | local, baseline (warning), needs KiCad | yes |
| CK-F1 | connectors vs. the EE model: `portName` on every connector (`-` = none) names a port usage of the board def, `portType` and `portTypeID` = its def's name and `EE-PORT` ID (owner decisions Q10, Q11; the old `Port` field is a finding), each port of the board def named by exactly one connector, pin numbers and net names = the pin map (`PinSignal` `pin`/`net`; root-sheet `/X` = `X`), no connected pin outside the pin map | `cad.projects` + `cad.connectors` + `model` | local, pr, baseline (warning) | yes (boards; harness ends with `cad.harnesses`, task 5.22: lines `portName:`, `portType:`, `portTypeID:` in each WireViz connector's notes naming the end port of the cable def, pins and pin labels contain the pin map (same net names at both ends), one net per conductor (loops included), wires by number, label or unique color, unwired pins another end carries, the ends = the cable def's ports (at least two)) |
| CK-F4a | KiCad ERC of every project (`kicad-cli sch erc --format json --severity-all`): an error passes only when excluded in KiCad or matched by an `accepted.yaml` entry, either accepted by a human commit with `Accepted-by:` (XD-ADR-0126); stale ERC exclusions (phantoms) are not counted; warnings listed in `build/<area>/checks/erc-drc/erc.txt` | `cad.projects` | local, baseline (warning), needs KiCad | yes |
| CK-F4b | KiCad DRC with schematic parity of every `pcba/` board, same rule; the unrouted nets in one entry (`unconnected_items`, `items: all`, XD-ADR-0144); report `erc-drc/drc.txt` | `cad.projects` | local, baseline (warning), needs KiCad | yes |
| CK-F8 | ERC/DRC severities and `erc.pin_map` (`.kicad_pro`, `.kicad_dru` custom rules) equal `templates/kicad-pcba/pcba.kicad_pro`; a missing `erc` section = the template; a difference needs an accepted `CK-F8` entry | `cad.projects` | local, pr, baseline (warning) | yes |
| CK-F9 | `accepted.yaml` well formed; each entry (newest commit of its lines, `git blame`) and each KiCad exclusion (`git log -S`) accepted by a single-parent commit with an `Accepted-by:` trailer (rebase merges only), no agent mark, no parallel-branch change of the entry, nothing but acceptance entries or exclusions changed; else reported as a proposal; also `assemblies/<name>/accepted.yaml` of an ME repo (CK-F4c, CK-F16, CK-F17) | `cad.projects` or `cad.freecad` | local, pr, baseline (warning) | yes |
| CK-F10 | the jobset of every `pcba/` project: no Execute Command, Copy Files, output folder or job file name (`output_filename`, `output_dir`) outside `${XD_CAM_OUT}`, no statistics/ERC/DRC job, BOM delimiters; every template job, equal to it except variant and file name (per variant: `<id>-<variant>`); variant names = `schematic.variants`; no job without a variant after a variant job | `cad.projects` | local, pr (warning) | yes |
| CK-F11 | title `${XD_BOARD}` and Rev `${XD_VERSION}` in the title block of every sheet and the board; two silkscreen lines `${XD_BOARD}` and `${XD_VERSION}`, both lines inside the outline and off holes and pads, the version line filled with a long preview version (estimated); committed values `XD_VERSION = unversioned`, `XD_BOARD` = the project name (owner decision Q13) | `cad.projects` | local, pr (warning) | yes |
| CK-F12 | every part in the BOM of a `pcba/` board (base or a variant) has `Manufacturer` and `MPN`, or a `Standard` field instead (`curatrix/bom.py`); ME (task 5.27, `curatrix/asmdoc.py`): every bought part below a top-level assembly that is not a standard fastener has `Manufacturer` and `MPN`, every own part a `Material`, every link a target | `cad.projects` or `cad.freecad` | local, pr (warning) | yes |
| CK-D9 | the plain-Python BOM equals `kicad-cli sch export bom` (one line per reference) of every board, without a variant and per variant (P5-15); CSVs in `build/<area>/checks/bom/` | `cad.projects` | local, baseline (warning), needs KiCad | yes |
| CK-D10 | the `curatrix cam` output of every board and every top-level assembly exists for the current commit (`cam.current`, `mecam.current`), so the board and assembly documents show their local sections; never in CI | `cad.projects` or `cad.freecad` | local, baseline (warning), CAD content | yes |
| CK-F22 | port names: port usages of the parts of the EE model (boards, cables, external parts) are lowerCamelCase and not designator-like (`j1`, `p3`, `x2`: a KiCad reference prefix and digits; `i2c0`, `spi1`, `can0` pass); a connector whose `portName` names a port has an `X` designator (owner decisions Q10, Q11) | `cad.projects` + `cad.connectors` + `model` | local, pr, baseline (warning) | yes |
| CK-F20 | board library: every `.FCStd` at `boards/<board>/<board>-vX.Y.Z[-<variant>].FCStd`; object `Board` with an `EE-PCBA` `TraceID`, `Version` = `<board>/vX.Y.Z` and `Variant` as in the name; the tag exists in `board_library.source`, its project (`<board>/<board>.kicad_pro` at the tag) has the same `TraceID`, `Commit` = the tag's commit, `Board` = the folder; the tag is on the source's main and, when the source has an `origin`, pushed there (CI's west clones have none); at most `max_mb` (5 MB); uncompressed; against the PR base, files under `boards/` are only added, never changed or deleted (plain Python) | `board_library` | local, pr, full (error) | yes |
| CK-F21 | board versions: an ME FreeCAD file whose link (`XLink` file) points into `boards/` of the board library gets a note when the library has a newer version of that board and variant, or when the linked file is not a board version there (moving to it is an ME change, XD-ADR-0139) | `cad.board_library` | local, pr, full (warning) | yes |
| CK-D6 | `code-needs.json` matches the code: `@xdid` blocks, comments above `ZTEST` (plain Python) | `code` | local, pr, baseline | yes |
| CK-D5 | generated files record the pinned tool versions (`generated/provenance.json`, 4.4b) | `model` or `cad.freecad_json` | local/pr/full warning, baseline error | yes |
| CK-E2 | value fields appear in the sentence as numbers (any format, `a ± b`), the unit once as symbol or name | `requirements` | local, pr, baseline (warning until it ran on real requirements) | yes |
| CK-E3 | EARS pattern vs. sentence start, "shall" | `requirements` | local, pr, baseline (warning) | first version |
| CK-G1 | needs-diff against `--base` (report, `build/<area>/checks/needs-diff.md`) | `docs` | pr, full | yes (skipped without `--base`) |
| CK-G2 | suspect links against the last baseline's needs (R7) | `docs` | full (report), baseline (error) | yes, needs `--base` |
| CK-H1 | `.FCStd` stored compressed; compressed drawio | — | local, pr, baseline | yes |
| CK-H2 | build output inside the repo | — | local, pr | yes |
| CK-H3 | unpinned `requirements.txt` lines; broken `tools.yaml` | — | local, pr (warning) | yes |
| CK-H4 | commits since `origin/main` without `Co-Authored-By` | — | pr (warning) | yes |
| CK-H5 | `scripts/bootstrap.sh` drifted from `xdmod/templates/bootstrap.sh` (D118) | `bootstrap_template` | all (warning) | yes |
| CK-H6 | `expect:` differs from the checks the repo runs (a lost section, a new one not listed) | — | all | yes |
| CK-H7 | PR changes more hand-written lines / files than `pr_size` against its base (`GITHUB_BASE_REF`, `XD_BASE_REF` or `main`); generated files excluded | — | local, pr (warning) | yes |
| CK-F* | other domain checks (devicetree, firmware, ERC, …) | `commands` | per command | via `commands` only |

## limits.yaml

`xdmod/curatrix/limits.yaml`, overridable per key in `<ws>/.xdmod/limits.yaml` (same format).

```yaml
defaults: {memory: 1G, timeout: 5m}
uses:
  docs:  {memory: 4G, timeout: 15m}
  pilot: {memory: 4G, timeout: 10m, java_heap: 3g, vmem: none}
  gui:   {memory: 8G, timeout: none, vmem: none}     # D117: memory limit only
  ...
```

- `memory`: systemd `MemoryMax` (swap off: `MemorySwapMax=0`). `timeout`: coreutils syntax or `none`.
- `vmem`: only for the **fallback** without a systemd user session (GitHub runners): `ulimit -v`;
  default = memory; `none` for tools that reserve much more address space than they use (JVM,
  node, Firefox). `java_heap`: `-R-Xmx` for the Pilot's engine.
- Backend: `systemd-run --user --scope -p MemoryMax -p MemorySwapMax=0 -- timeout --kill-after=10s T cmd`
  when a user session answers, else `sh -c 'ulimit -v KB; exec "$@"'` + `timeout`. Force one with
  `XD_LIMIT_BACKEND=systemd|ulimit|none`.
- Uses: `script` 1G/5m, `docs` 4G/15m, `pilot` 4G/10m, `kicad-cli` 2G/5m, `freecad` 4G/10m,
  `firefox` 2G/5m, `elk` 1G/2m, `west` 2G/30m, `west-build` 4G/20m, `tests` 4G/30m,
  `install` 4G/30m, `git` 1G/10m, `gui` 8G/none, `claude` 8G/none.
- From Python: `limits.run(argv, "docs", ws, ...)` (a `subprocess.run` wrapper) — use it for every
  subprocess in curatrix code.

## tools.yaml

At each repo root (xdmod's own: `xdmod/tools.yaml`). curatrix merges the files of all active repos;
the same tool with two different versions is an error.

```yaml
tools:                        # installed into <ws>/.venv/<location> (or <ws>/.xdmod/…)
  - name: jdk
    version: "21.0.13+9"
    kind: tarball             # tarball | zip | conda | file | npm | git
    url: https://…
    sha256: d7f5…             # required except for npm (npm checks integrity itself) and git
    commit: 3db9…             # git only, instead of sha256: the full commit hash (40 hex digits)
    location: opt/jdk         # relative to .venv; `.xdmod/…` = relative to the workspace root
    strip: 1                  # tarball: leading path components dropped (default 1)
    subdir: share/…           # tarball / zip / conda / git: copy only this folder
    package: elkjs            # npm: package name (default: name)
    licence: "MIT"            # optional: the licence and any gap in it (doctor shows it)
    links: {gh: bin/gh}       # symlinks .venv/bin/<name> -> <location>/<path>
    env: {JAVA_HOME: "{location}"}   # exported by `curatrix env` ({location}, {venv}, {state} = .xdmod)
    roles: [sw]               # optional: only for these roles
system:                       # used from the machine (D19)
  - name: kicad-cli
    version: "10.0.8"         # exact | "any" | prefix wildcard "10.0.*" | minimum ">=10.0"
    cmd: [kicad-cli, --version]   # default [name, --version]
    regex: '(\d+\.\d+\.\d+)'  # default: first x.y[.z] in the output
    optional: true            # missing = warning; a wrong version is a FAIL (unless pinned: false)
    pinned: false             # optional: a version the tool was tried with, not a pin (Blender):
                              # missing = note, another version = warning, never a FAIL
    roles: [ee, integration, full]
```

Downloads are cached in `<ws>/.xdmod/cache/downloads/` and checked against `sha256` before use.
`kind: git` (a tool without release archives, such as KiCad StepUp) fetches exactly `commit` into a
bare cache repo `<ws>/.xdmod/cache/git/<name>.git`, checks that it got that commit, and extracts its
tree (or `subdir`) with `git archive` into the location: no checkout, no remote. `url` must be
`https://` (no ssh, no `ext::`, nothing option-like; `git fetch` gets it after `--`). A location that
is already a git checkout (cloned by hand before) is adopted and stamped only at the pinned commit
and without changed or added files; otherwise `update` stops with a message and never deletes it,
and `doctor` fails. Each
installed tool gets a stamp `.venv/opt/.xd-stamps/<name>.json` (name, version, sha256, commit); `doctor`
compares stamps with tools.yaml and fails when an adopted checkout moved off its commit.

Curated tools of xdmod beyond the pip packages: `stepup` (KiCad StepUp, git pin, into
`.xdmod/stepup/kicadStepUpMod`, `XD_STEPUP` and `XD_STEPUP_HOME` (its sandbox `HOME`) from `curatrix env`;
AGPL-3.0 claimed without a LICENSE file: called in its own FreeCAD process, never imported), and
the FreeCAD MCP server (neka-nat/freecad-mcp, MIT; xdmod#69 finding 18): the addon
`freecad-mcp-addon` (tarball with `subdir`, into `.xdmod/freecad/data/FreeCAD/v1-1/Mod/FreeCADMCP`)
and the pip package `freecad-mcp` at the same version. `curatrix update` also makes the token file
`.xdmod/freecad/mcp-token` (0600), writes the addon settings (`freecad_mcp_settings.json`: remote
off, allowed IPs 127.0.0.1, the token, auto-start off), the server `freecad` in `<ws>/.mcp.json`
(`.venv/bin/freecad-mcp`, headless runs through `curatrix run --use freecad -- FreeCADCmd`,
`FREECAD_MCP_TOKEN=${XD_FREECAD_MCP_TOKEN}`) and its approval in `<ws>/.claude/settings.local.json`;
`curatrix env` exports `XD_FREECAD_MCP_TOKEN`, so start Claude Code with `curatrix launch claude`
or after `eval "$(curatrix env)"`. `doctor` fails on another addon or pip version, unsafe or stale
settings, and warns about auto-start left on, a missing `.mcp.json` entry, or a user-global
`~/.local/share/FreeCAD/*/Mod/FreeCADMCP`. The Zephyr SDK belongs in robarm-sw's tools.yaml (D138), e.g.
`env: {ZEPHYR_SDK_INSTALL_DIR: "{location}"}`.

## ids.yaml (the ledger)

`<repo>/ids.yaml` lists **every number ever issued** per kind the repo owns, one per line,
append-only (id-scheme.md §4, D133). A kind with nothing issued yet is `KIND: []` — that line is
what makes the repo the owner of the kind (`ids new` finds the ledger by it).

```yaml
# ID ledger (id-scheme.md §4, D133). …
SYS-NEED:
  - 1
  - 2
SYS-REQ: []
SYS-VIEW: []          # reserved non-need kind (view short names), issued like the others
```

- ID formats (`curatrix.ids.ID_RE`): `<DOMAIN>-<KIND>-<NNNN>` with DOMAIN `SYS|SW|EE|ME|INT|XD|PRJ`,
  KIND 2–5 capitals, 4+ digits; usage IDs `<ID>.<n>` (D128); `TR-<test case ID>-<8 hex>`.
- Placeholders: `<KIND>-NEW-<tag>` (`SYS-REQ-NEW-a`, `SYS-EL-NEW-ctrl`), anywhere in text sources
  (rst, sysml, py/c/h, kicad files, yaml/json). `ids fix` issues `max(ledger, IDs in sources) + 1`.
  Placeholders inside `.FCStd` are refused (set the TraceID in FreeCAD).
- CK-C2 only looks at kinds the ledger owns; other IDs are upstream references.

## Generated files

All committed generated files use the sphinx-needs **import format** (what `needimport` reads),
sorted and stable:

```json
{"created": "", "current_version": "", "project": "<repo>-model",
 "versions": {"": {"needs": {"SYS-EL-0012": {"id": "SYS-EL-0012", "type": "sys-el", "title": "…",
   "content": "…", "status": "valid", "layer": "logical", "qualified_name": "RobArm::…",
   "sysml_kind": "PartDefinition", "instances": ["…"], "source_file": "model/logical.sysml",
   "satisfies": ["SYS-REQ-0003"], "realizes": ["SYS-EL-0004"]}}}}}
```

| File (default path) | Made by | From | Checked by |
|---|---|---|---|
| `model/generated/NeedStubs.sysml` | `gen stubs` | needs.json of `stubs.docs` (run `curatrix docs <repo>` first) | CK-D1 |
| `generated/model.json` | `gen model` | the Pilot export, **compacted**: non-library elements with the payload keys curatrix reads, referenced library elements as stubs, stable IDs (qualified name or `<owner>/<index>`), sorted. Same shape as the Pilot JSON (`[{"identity": {"@id"}, "payload": {…}}]`) | CK-D2; input of views, variants, model-needs (so no Java downstream) |
| `generated/model-needs.json` | `gen model` | model.json | CK-D2 |
| `generated/cad-needs.json` | `gen cad-needs` | KiCad `.kicad_sch`/`.kicad_pro`, FreeCAD `Document.xml` (plain Python) | CK-D4 |
| `generated/<project>.connectors.json` | `gen connectors` | the KiCad schematic of each project (plain Python): per connector `ref`, `portName`, `portType`, `portTypeID` (and `Port` while a connector still has the old field), `value`, `footprint`, `lib_id`, `sheet`, `pins` (`number`, `name`, `net`, net names as in KiCad's XML netlist), `inputs` (the schematic files, no hash) and `unsupported` (sheets with buses, which are not read) | CK-D7; CK-F1, the board document's pin tables |
| `generated/code-needs.json` | `gen code-needs` | C sources: a Doxygen block with `@xdid{SW-IMPL-nnnn}` (title: the declared name; `Implements X.`, `Satisfies X.`, `Configs: SYS-CFG-nnnn.`, `Status: draft.`), and the comment above each `ZTEST` with `Test case: SW-TC-nnnn. Verifies X.` (title: `@brief`; the Twister identifiers from the nearest `testcase.yaml` go into the content). One ID per `@xdid` and per `Test case:`; anything the reader is unsure of is a finding. String literals and `//` comments are skipped, `#if 0` code is still read; tests behind wrapper macros are not seen. `ZTEST`, `ZTEST_F`, `ZTEST_USER`, `ZTEST_USER_F`, `ZTEST_P` | CK-D6 |
| `generated/retired-needs.json` | `gen model` / `gen cad-needs` / `gen code-needs` / `gen tombstones` | tombstones (D130): a generated need that vanished without `status: retired` keeps `{id, type, title, status: retired, retired_on, source_file}` until the next `baseline/*` tag of the manifest | CK-B7 |
| `generated/freecad/<path>.FCStd.json` | `gen freecad-json [--shape]` | trace part (plain Python: objects, `trace` fields incl. `Port`, placements, plain values, `links` per link property as `{file, object, sub}` without the stamp, `expressions` `{path: expression}`, named sketch `constraints`, spreadsheets) + optional `shapes` (FreeCAD: volume, bbox, solids) | textconv / review |
| `views/<view>.drawio.svg` | `views build` | model.json | CK-D3 |
| `generated/provenance.json` | `gen model`, `gen freecad-json --shape`, `views build` | the tool versions used (tools.yaml stamps, system `--version`) for each file they wrote | CK-D5 (record vs. tools.yaml pins; no tools needed, so it runs in CI) |

**Tool provenance (4.4b).** Files made with an external tool (the Pilot + JDK for `model.json` and
`model-needs.json`; elkjs, drawio viewer and Firefox for views; FreeCAD for `--shape` JSON) get an
entry `{"made_by": "curatrix gen model", "tools": {"jdk": "21.0.13+9", "sysml-pilot": "0.63.1"}}`
in `generated/provenance.json`. CK-D5 reports a file whose record is missing or differs from the
pins in tools.yaml (e.g. made on a rolling distro with another Firefox), so after a pin bump the
files must be regenerated. Plain-Python outputs (stubs, cad-needs, tombstones) have no entry.
`curatrix doctor` fails when an installed tool differs from its pin.

## Evidence (run records)

Tasks 4.5a/4.6, D57, D60, D73, D131, trace-model.md R5/R5a. Schema:
[`src/curatrix/data/run-record.schema.json`](src/curatrix/data/run-record.schema.json)
(JSON Schema 2020-12, `"schema": "xdmod-run-record/1"`).

**Where.** One folder per run on the orphan branch `evidence` of robarm-integration:
`runs/<YYYY>/<run id>/record.json` plus the Twister reports (`twister.json`, `twister_report.xml`).
The branch has no common history with `main`; the writer works in a git worktree under
`build/evidence/` and only moves the local branch `evidence`, so the checkout and `main` stay as
they are. Pushing is a separate step (`git -C robarm-integration push origin evidence`).

**Fields** (all required unless noted):

| Field | Meaning |
|---|---|
| `schema` | `xdmod-run-record/1` |
| `run_id` | `<UTC yyyymmddThhmmssZ>-<8 hex>`; the 8 hex digits (from firmware hash, manifest SHA and time) end every `TR` ID of the run |
| `kind` | `hil` (on the HIL setup; R5 applies) or `sim` (native_sim / QEMU: a test result, **never HIL evidence**) |
| `created`, `recorded_by` | UTC time; `git config user.name` of whoever recorded it |
| `config` | the one `SYS-CFG` the run was made on (D103) |
| `setup` | HIL setup folder `hil/<setup>` (required for `hil`, else null) |
| `platform` | Twister platform, e.g. `nucleo_g474re`, `native_sim/native` |
| `firmware` | `{file, sha256}`: `zephyr.bin` (hardware) or `zephyr.exe` (native_sim) of the run; one image per record |
| `workspace.manifest`, `workspace.repos` | for the manifest and **every west project** (xdmod, robarm-*, Zephyr, modules, tools, libraries): `sha` (HEAD), `pin` (manifest revision), `clean`, and for the manifest, xdmod and robarm-* `on`: `main`, `baseline/vX.Y.Z` or null |
| `evidence` | `{ok, base, problems}`: the evidence rule at record time; `base` = `main` or the manifest's baseline tag |
| `results` | per Twister test case: `test` (Twister identifier), `suite`, `test_case` (the traced `SW-TC`/`INT-ITC`/`INT-STC`/`EE-TC`/`ME-TC` from the comment above the `ZTEST`, D80, or `--map TEST=ID`; null = verifies nothing), `status`, `duration` |
| `tool` | `twister`, the Zephyr version, sha256 of the stored reports |
| `note` | optional free text |

**Evidence rule (D60).** `evidence.ok` holds only if every west project is at its manifest pin with a
clean tree (no changes, no untracked files), and the commits of the manifest, xdmod and every
robarm repo are on their remote `main` (the manifest may instead be at a `baseline/*` tag). The
writer **refuses** a record that fails the rule on the branch `evidence` (it is a preview, D60);
`--branch <scratch>` writes it elsewhere, e.g. for a test of the tooling. Local records that were
not pushed yet are never dropped: if the remote branch moved meanwhile, the writer replays them
onto the remote head (records are new files only) or refuses without changing anything.

**Known limits (iteration 1).** The record proves which trees were checked out and which image
was tested (its sha256), not that the image was built from those trees: Twister builds it in the
same run, but nothing re-checks that link later (a reproducible rebuild would). Staleness (D131)
compares only the recorded SHAs with the current pins; it doesn't rebuild to compare the firmware
hash, and a changed pin of an unrelated project (e.g. a KiCad library) also makes a run stale.

**Reader and validity (D131).** `curatrix evidence read` validates every record against the
schema (invalid ones are skipped and reported, exit 1) and turns every result with a `test_case`
of every record with `evidence.ok` into a need
`TR-<test case>-<8 hex>`, one per Twister test (the 8 hex digits hash run id and test, so two tests
of one test case keep both results) (`result_of`, `method` = `hil`/`test`, `config`, `firmware_sha256`,
`shas` = `repo=sha` for all projects, `verdict`). A record whose SHAs differ from the current pins
(`west list`) gets the tag `stale` and a note in its content; CK-B6 reports the same from `shas`.
A test report imports the file with `.. xd-needimport:: /…/tr-needs.json` and `:optional:`.

**Previews of the local run (task 5.10).** `curatrix evidence preview` turns a Twister output dir
straight into `TR` needs with the tag `preview` (all suites and platforms, no firmware hash, no
workspace state, IDs `TR-<test case>-<8 hex of "preview" and the test>`). A repo runs its Twister
command and the preview command with `before_docs: true`, so the test report of the same
`curatrix check` run shows them; the report imports the file with
`.. xd-needimport:: /…/tr-needs.json`, `:stamp:` and `:missing: <sentence>`. With `--commit-of
<repo>`, `preview` writes a run stamp (`tr-needs.stamp.json`: run date, commit, uncommitted changes);
the docs show the previews with the line "results of the local test run of <date>, commit <sha>"
only while the repo is at that commit, and the sentence otherwise (no run in this check run,
`curatrix docs` alone after a new commit, no Twister). Previews never go onto the evidence branch;
published results stay `evidence read`.

**A preview never counts** (D60): a `TR` with the tag `preview` is never coverage, never a
baseline result and never evidence. Every consumer of TR needs (trace report, coverage, CK-B*)
must check the tag. A repo runs its preview command at the stages `local` and `pr` only, never at
`baseline`.

## SysML model conventions

- Library `xdmod/sysml/XdTrace.sysml` (always loaded first): `NeedRef { needId; status; }` (stubs),
  `Trace { status; layer; }`, `XdView { kind; root; layer; }`.
- **A model element becomes a need when its short name is an ID** of a model kind
  (`SYS-EL`, `SYS-IF`, `SYS-UC`, `SYS-CFG`, `SYS-FEAT`): `part def <'SYS-EL-0012'> JointController {…}`.
  The definition holds the ID; usages typed by it are listed in `instances` (D128).
- `@XdTrace::Trace { layer = "logical"; status = "draft"; }` on the element or on an owning package
  (inherited). Every `SYS-EL` needs a layer (`context|functional|logical|product`). Status default `valid`.
- Links:
  - `satisfy sys_req_0012 by ctrl;` → the ID behind `ctrl` (itself, else its definition) `satisfies SYS-REQ-0012`
    (requirements are referenced through the generated stubs `sys_req_nnnn`).
  - `dependency from <S> to <T>;` and `allocate <T> to <S>;` (the allocated-to side holds the link):
    link type by kinds: SYS-UC→SYS-NEED `addresses`, SYS-EL→SYS-UC `realizes`, SYS-EL→SYS-EL `realizes`,
    SYS-EL→SYS-REQ `satisfies`, SYS-CFG→SYS-EL `configures`. Anything else is a finding.
    `allocate` works between usages (not definitions): e.g. `part f : Follow; part c : Ctrl; allocate f to c;`.
  - PLEML `#FeatureBinding` dependencies are variant data, not trace links.
- Concern stubs carry no `stakeholder` parameter (the Pilot requires a subject first); `raised_by`
  stays an rst link.
- Views: `view <'SYS-VIEW-0001'> jointView { @XdView { kind = "interconnection"; root = "RobArm::JointModule"; } expose RobArm::JointModule::**; }`.

## CAD trace fields

Same names in KiCad (hidden symbol / sheet fields; for the PCBA: `text_variables` in `<project>.kicad_pro`)
and FreeCAD (object properties, e.g. `App::PropertyString` in group `Trace`):

| Field | Need field / link |
|---|---|
| `TraceID` | the need ID (kind decides the type: `EE-PCBA`, `EE-CMP`, `ME-ASM`, `ME-PART`) |
| `Realizes`, `Satisfies`, `Conforms`, `PartOf` | `realizes`, `satisfies`, `conforms`, `part_of` (comma lists) |
| `Status` | `draft | valid | retired` (D130) |
| `Configs` | `configs` (SYS-CFG IDs, D103) |

A KiCad sheet file used several times carries one ID; its usages become `instances`
(`/joint1/`, `/joint2/`), and so do the per-instance references of traced symbols inside it.

## Views (.drawio.svg)

The committed file is the rendered SVG with the normalized, **uncompressed** drawio diagram in the root
`content` attribute and `data-xdmod-hash="sha256:<hex of the normalized diagram>"`. Cell IDs are SysML
qualified names; every cell is an `<object>` with `label`, `sysml_kind`, `trace_id`, `layer`,
`configs` and `link="need:<ID>"` for traced elements; one legend cell (`xd-legend`). The SVG's random
`ge-svg-*` ID is pinned to `xd-view-<view>`. A rebuild of an unchanged model is byte-identical.
CK-D3 compares content (label, parent, edge ends, kind, link, trace_id, layer, configs), never
geometry; it rejects compressed diagrams, children outside their parent, and stale pictures.
Rendering needs node + elkjs + Firefox + the pinned drawio viewer (local only).

## Docs layout and the Sphinx extension

- `<repo>/docs/CMakeLists.txt` includes `xdmod/cmake/xdmod-docs.cmake` and calls
  `xdmod_docs(REGISTRY ${CMAKE_CURRENT_LIST_DIR}/documents.yaml PROJECT_BASE ${CMAKE_CURRENT_LIST_DIR}/..)`
  (sets `ZDOCS_NEEDS_CONFIG` to `xdmod/needs/needs_config.toml`).
- `curatrix docs <repo>`: `cmake -S <repo>/docs -B build/<area>/docs -GNinja` then
  `cmake --build … -- -k 0`. Strict: `-DZDOCS_STRICT=ON` if the zdocs checkout knows it (PR #36),
  else `-DZDOCS_SPHINXOPTS_EXTRA=-W;--keep-going`. Output per document:
  `build/<area>/docs/deploy/html/<doc-id>/` with `needs.json` (read by the graph checks and stubs).
  `full` builds the manifest repo into `build/full/`.
- Each document's `conf.py`:

  ```python
  import os, sys
  from pathlib import Path
  sys.path.insert(0, str(Path(os.environ["ZDOCS_WEST_TOPDIR"]) / "xdmod" / "sphinx"))
  from xdmod_conf import configure, repo_root
  REPO = repo_root(__file__)
  configure(globals(), __file__, "System Architecture",
            generated=[(REPO, "generated/*.json"), (REPO, "views/*.drawio.svg")])
  ```

  then in rst: `.. needimport:: /generated/model-needs.json`,
  `.. xd-needimport:: /generated/retired-needs.json` with `:optional:`,
  `.. sysml-view:: /views/jointView.drawio.svg`. `configure` loads sphinx-test-reports and
  `xdmod_sphinx` in every document and suppresses `needs.type_near_name`.
- Directives (`xdmod/sphinx/xdmod_sphinx`): `sysml-view` (inline SVG; `need:<ID>` → the need's page in
  this build; unknown ID = warning), `xd-needimport`, `kicad-sheet`/`kicad-bom`/`kicad-nets`/
  `freecad-drawing`/`freecad-3d` (show `build/<area>/cad/<arg>` if `curatrix gen cad-exports` made it,
  else a "built locally" notice without a warning, D56), `freecad-params` (spreadsheet aliases, plain
  Python, works in CI), `tracechain`. Stubs (notice only): `coverage-matrix`, `config-page`, `sysml-element`.
- Need types are the ID kinds in lower case (`.. sys-req::`, `.. ee-cmp::`, `.. tr::`); see
  `xdmod/needs/needs_config.toml`.

## What is implemented

Working and tested: `env`, `run`, `limits`, `doctor`, `bootstrap`/`update` (their west and pip steps
were not run against a real manifest yet), `launch` (env verified; GUIs not started in tests),
`docs`, `check` with the catalogue above, `gen` (stubs, model, cad-needs, freecad-json incl.
`--shape`, tombstones, cad-exports), `ids`, `views` (interconnection, decomposition), `variants list`, `pleml check`,
`needs-diff`, pre-commit hook, Sphinx extension, reusable CI workflow (first version, untested on GitHub).

Stubbed / later: view kinds `context`, `usecases`, `allocation`, `variants`;
coverage per configuration (R2 per cell, `coverage-matrix`), `config-page`, `sysml-element`;
variant rules V6, T1–T3 and `configs` derivation; FreeCAD TechDraw / GLB exports and the review
report; CK-F* domain checks (repos add them as `commands`);
affirmatrix integration for R7 (needs-diff is the interim).

## Worktrees (D125)

`curatrix work start feat/x robarm-syseng` makes `.worktrees/feat/x/` a workspace root of its own:

- **Every framework repo is a git worktree in the set:** xdmod, the manifest and every robarm repo. The named repos are on `feat/x` (from `main`, or the existing local / `origin` branch). All others are detached at the main checkout's HEAD; treat them as read-only.
- **Paths between our repos stay inside the set**, even when resolved physically. A registry path `../../robarm-syseng/docs/se-req` from robarm-ee reaches the set's robarm-syseng whichever repos the change touches.
- **Shared and third-party trees are relative symlinks** to the main checkout: `zephyr`, `modules`, `tools`, `libs`, `.venv`, `.xdmod`, `CLAUDE.md`, `.claude`. Nothing in them refers to our repos by relative path.
- **`.west/` is a real folder** with a copy of the west config.
- **`build` points to `build/wt-feat-x/`.** The `wt-` prefix keeps branch builds apart from the repo areas.

Then `cd .worktrees/feat/x` and use curatrix as usual:

- West finds its topdir from the current directory. So `west list`, `west build`, Zephyr's module discovery (`zephyr_module.py`) and the docs build (`west topdir`) all see the set.
- curatrix finds the set root from any folder of the set, also from a symlinked one (`.worktrees/feat/x/zephyr`), through the logical `$PWD`. West needs a real folder of the set as its current directory: the set root or a repo.
- Builds land in `build/wt-feat-x/<area>/`. The main checkouts are not touched.
- If `xdmod` is on the branch, curatrix re-executes itself from the set's `xdmod/curatrix/src`.
- Don't run `west update` / `curatrix update` inside a set: it would move the worktrees to the pins.
- Branch names that would nest (`feat` and `feat/x`) or share a build folder (`feat/x` and `feat-x`) are refused.

To add a repo to the change, run `work start feat/x robarm-ee` again: its detached worktree moves onto the branch.

`curatrix work done feat/x` removes all worktrees of the set, the links and the folder. It refuses while there are uncommitted changes unless `--force`; `--delete-branch` also deletes merged branches. `start` writes its marker file first, so a failed `start` can be repeated or undone with `done`. All git calls run under the `git` limits (D71).

Tested in `tests/test_work.py`: a real west workspace of local repos. It covers physical `../../` resolution in both directions, `west topdir` from a repo outside the change, root detection from a symlinked folder, `zephyr_module.py`, a half-done start, and refused names.

## Tests

```sh
curatrix run --use tests -- .venv/bin/python -m pytest -q xdmod/curatrix/tests             # all
curatrix run --use tests -- .venv/bin/python -m pytest -q -m "not tools" xdmod/curatrix/tests   # no Java/node/Firefox
```

Markers: `sphinx` (runs sphinx-build), `tools` (Pilot, elkjs, Firefox). Temporary files go to
`build/xdmod-dev/pytest/`.
