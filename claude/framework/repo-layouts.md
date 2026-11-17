# Domain repo layouts (task 3.12)

Status: **AGREED 2026-11-14** (review answers → D113–D115). Built on D46, D63, D67–D70, D73, D78, D84, D88, D91, D96, D98, D100, D102, D108–D112
(`../decisions.md`), `repo-topology.md`, `doc-architecture.md`, `sysmod-work-products.md` §3, and the spike repos.

## 1. Common pattern (every robarm repo)

```
robarm-<x>/
  README.md
  checks.yaml            what `curatrix check` runs for this repo (docs, generated files, domain checks)
  ids.yaml               ID ledger (D78)
  requirements.txt       pinned pip packages this repo needs (D19)
  tools.yaml             pinned non-pip tools (name, version, source, sha256)
  docs/
    documents.yaml       zdocs registry: own docs + upstream docs (D35)
    CMakeLists.txt
    <doc-id>/            one folder per document (conf.py shim + rst)
  generated/             committed generated files, checked by `curatrix check` (D42, D96, D110)
  claude/                agent material for this repo (D69), see §3
  .github/
    workflows/           thin callers of reusable workflows in xdmod
    pull_request_template.md
  .gitattributes         diff drivers (e.g. *.FCStd diff=fcstd -merge), linguist hints
```

Rules:
- **No build output in repos** (CK-H2). Everything goes to `<workspace>/build/<area>/` (D46), where `<area>` is the repo name, `full` for the full set, `<branch>` for worktree builds (D125), or a named step such as `spike` or `research-vamos`.
- **Generated files are committed only in `generated/`**, except where the tool needs them next to the source (SysML stubs in `model/generated/`, views in `views/`).
- **Folder names are lowercase with dashes.** Each PCBA, assembly and configuration gets its own folder, so adding one never moves another (D28).

## 2. Per repo

### robarm-syseng
```
model/                   *.sysml per SYSMOD step: project, context, usecases, functional, logical, product (150 %),
                         features, configs, views (D85, D94, D102)
model/generated/         stubs from needs: concern, requirement, stakeholder (D42)
views/                   <view>.drawio.svg (D96)
generated/               model-needs.json, model.json (Pilot export), interfaces.json (pin maps etc. from SYS-IF)
docs/se-req/  docs/se-arch/
```

### robarm-ee
```
model/                   EE domain model (*.sysml): board defs that specialize system blocks, connector port defs
                         with connector type and pin map, cable defs, external parts, board variants (XD-ADR-0130)
model/generated/         as in syseng, if the EE model needs stubs
pcba/<name>/             one KiCad project per board def (1:1, XD-ADR-0128): <name>.kicad_pro (entry point)/.kicad_sch/
                         .kicad_pcb, sym-lib-table, fp-lib-table, <name>.kicad_jobset (copied from the xdmod
                         template, XD-ADR-0142), accepted.yaml (accepted ERC/DRC findings, XD-ADR-0126)
proto/<name>/            one KiCad project per block of the prototype configuration (XD-ADR-0135): wiring between
                         external parts; same files as pcba/<name>/
harness/<name>/          one WireViz harness per cable def: <name>.yml, both ends name their EE-PORT (XD-ADR-0127)
lib/                     project-local symbols, footprints, 3D models that aren't in the tiacsys libraries (D88)
tests/                   scripted EE checks → JUnit
generated/               cad-needs.json (D110), model.json and model-needs.json, <project>.connectors.json (CK-D7)
docs/ee-design/  docs/pcba-<name>/  docs/proto-<name>/  docs/harness-<name>/  docs/ee-test-spec/  docs/ee-test-report/
```
Board, harness and prototype tags `<name>/vX.Y.Z`, made by the owner only (XD-ADR-0140). Design output (`curatrix cam`) goes to `build/robarm-ee/cam/<name>/<version>/`, never into the repo. KiCad and WireViz files carry the model's IDs only as references: the project's `TraceID` text variable, each connector's `Port` field, the port names at the harness ends; no `Realizes` / `Conforms` fields on projects.
KiCad library tables refer to the shared libraries only through variables (`${XD_KICAD_SYMBOLS}`, …) and to `lib/` through `${KIPRJMOD}`. The launcher sets the variables (`command-layer.md`).

### robarm-me
```
model/                   ME domain model (*.sysml): assembly and sub-assembly defs that specialize system blocks,
                         mechanical port defs with geometry, assembly variants (XD-ADR-0130)
parts/<part>.FCStd       shared parts (compression 0, D63)
assemblies/<name>/       one folder per top-level assembly: <name>.FCStd (top document, TraceID = its ME-ASM),
                         skeleton.FCStd (spreadsheet Params with the variant table, master sketch; parts refer only
                         to it, XD-ADR-0137), parts/ (own parts), accepted.yaml (accepted findings, XD-ADR-0126)
lib/                     project-local parts not in FreeCAD-library (D88)
templates/               TechDraw templates with git fields (freecad-storage.md §4)
print/                   print-settings profiles (D30)
tests/                   scripted ME checks → JUnit
generated/               cad-needs.json, <file>.json semantic exports (D110, textconv), model.json and model-needs.json
docs/me-design/  docs/asm-<name>/  docs/me-test-spec/  docs/me-test-report/
```
Only assemblies are tagged (`<name>/vX.Y.Z`, owner only, XD-ADR-0140). Design output (`curatrix cam`, XD-ADR-0143) goes to `build/robarm-me/cam/<name>/<version>/`. Board models come at fixed versions from robarm-freecad-pcba.

### robarm-freecad-pcba (board library, XD-ADR-0139; created in task 5.29 after the owner's approval)
```
boards/<board>/<board>-<vX.Y.Z>[-<variant>].FCStd   one file per tagged board version and variant: board body and
                                  components, no tracks; App::Part `Board` with TraceID (EE-PCBA), Version, Variant,
                                  Commit; saved uncompressed; at most 5 MB per file to start; never replaced
docs/board-library/              the list of board versions, made from the files at build time
checks.yaml  claude/  .github/   no ids.yaml: the repo owns no IDs (the files carry robarm-ee's EE-PCBA IDs)
```
Top-level west project `robarm-freecad-pcba` (like the other design repos, so worktree sets and CI sibling
resolution work), west groups `ee` and `me`. The EE agent writes a board version with `curatrix cam robarm-ee
<board> --library` (tagged releases only: `kicad-cli pcb export step`, headless FreeCAD import) and opens the PR.
CK-F20 checks every file against the board tags; CK-F21 in robarm-me (`cad.board_library`) notes a link to an
older board version.

### robarm-sw
```
app/                     Zephyr application: CMakeLists.txt, prj.conf, src/, boards/<board>.overlay
dts/bindings/            our own bindings, e.g. robot,joint with trace-id (D64f)
zephyr/module.yml        robarm-sw is a Zephyr module (dts_root, board_root), so that bindings and overlays are found (D114)
tests/<suite>/           ztest suites (native_sim and hardware), with test IDs from the ledger (D80)
generated/               code-needs.json if not produced by zdocs directly
docs/sw-req/  docs/sw-arch/  docs/sw-api/ (Doxygen)  docs/sw-test-spec/  docs/sw-test-report/
```

### robarm-integration
```
tests/                   system and integration test cases (scripts, Twister configs): every test that verifies a `SYS-REQ` or `SYS-IF`, even if it touches only one domain (D115)
hil/<setup>/             HIL setups: hardware map, fixtures, wiring reference (to robarm-ee proto/), runner config
docs/int-test-spec/  docs/int-test-report/
branch `evidence`        orphan branch with HIL run records (D57, D73), never merged into main
```

### robarm-manifest
```
west.yml                 imports submanifests/ (D86)
submanifests/*.yml
scripts/bootstrap.sh     first-time setup (command-layer.md §2)
docs/                    full-set registry + `robarm` overview doc (D111)
.github/workflows/       bump bot (D89), full-set build, Pages publishing (D55)
```

### xdmod
```
claude/                  planning folder (D70) + shared agent material: skills/, commands/, checklists/, glossary.md
launch/CLAUDE.md         launch file, copied to the workspace root by the bootstrap (D69)
curatrix/                the tool (Python package, D98), incl. the variant checker (D105)
sphinx/                  Sphinx extensions (doc-architecture.md §4)
needs/                   needs_config.toml (need types, link types, schema rules)
sysml/                   SysML library: trace metadata, @XdView (D94)
templates/               KiCad title block, FreeCAD TechDraw template, PR templates
workflows/               reusable GitHub workflows (.github/workflows in each repo calls these)
docs/xdmod-manual/  docs/xdmod-ref/
```

## 3. Agent material (D69)

| Where | What | Shared or local |
|---|---|---|
| `xdmod/launch/CLAUDE.md` → `<workspace>/CLAUDE.md` | workspace rules (run from the root, curatrix limits, build paths, trace rule, trailers), pointers to each repo's `claude/` | shared |
| `xdmod/claude/skills/` | one skill per SYSMOD step, EARS writing, ID issuing, review checklists, change workflow | shared |
| `xdmod/claude/commands/` | slash commands, linked as `/xd-<name>`, e.g. `/xd-review-pr` | shared |
| `<repo>/claude/CLAUDE.md` | repo-specific rules: layout, checks, pitfalls | local |
| `<repo>/claude/skills/`, `commands/` | domain skills, e.g. KiCad edits through scripts, FreeCAD parameter changes, ZTEST annotation (from safety's `annotate-ztest`) | local |
| `<repo>/claude/glossary.md` | domain terms | local |

Claude Code is started from the workspace root (D67). It finds skills and commands in `<workspace>/.claude/`. So the **bootstrap assembles `<workspace>/.claude/`** from symlinks to the xdmod and repo folders, for the repos active in the role (D113). Names are prefixed with the repo (e.g. `ee-kicad-edit`), and the links are refreshed on `curatrix update` and on a role change.

## 4. Library inputs (D88)

- **EE:** tiacsys `kicad-symbols`, `kicad-footprints`, `kicad-packages3D`, `kicad-templates` and `kicad-library-utils` as west projects under `libs/kicad/`. Parts not in them go into `robarm-ee/lib/`. `kicad-library-utils` can check our local library against the KiCad library conventions.
- **ME:** `FreeCAD/FreeCAD-library` under `libs/freecad/`. Parts not in it go into `robarm-me/lib/`. **Licence to check:** GitHub reports none. To be confirmed before bundles (iteration 2) contain parts from it.

## 5. Answered review questions (2026-11-14)

1. **Agent material discovery:** the bootstrap assembles `<workspace>/.claude/` from symlinks (D113).
2. **robarm-sw** is a Zephyr module (D114).
3. **Test location follows what a test verifies.** A test that verifies a `SYS-REQ`/`SYS-IF` is an `INT-STC`/`INT-ITC` in robarm-integration, even if it touches one domain only. Tests of domain requirements stay in the domain repo (D115).
