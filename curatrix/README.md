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
[Generated files](#generated-files) · [Model conventions](#sysml-model-conventions) ·
[CAD trace fields](#cad-trace-fields) · [Views](#views-drawiosvg) · [Docs](#docs-layout-and-the-sphinx-extension) ·
[Tests](#tests)

## CLI

| Command | Does |
|---|---|
| `curatrix env [--shell fish]` | prints the workspace env: `eval "$(curatrix env)"` (`PATH`, `ZEPHYR_BASE`, `JAVA_HOME`, `XD_KICAD_*`, `XD_FREECAD_PARTS`, `env:` of tools.yaml tools such as `ZEPHYR_SDK_INSTALL_DIR`, `PYTHONDONTWRITEBYTECODE=1`) |
| `curatrix run [--use USE] [-m MEM] [-t TIME] [-v] -- CMD…` | any command with the workspace env and limits (default use `script`, 1G/5m). Exit 124 = timeout, 137 = killed (memory) |
| `curatrix limits` | resolved limits table and backend (systemd / ulimit) |
| `curatrix doctor` | Python, venv, west state, role, every tools.yaml tool (installed version vs. pinned → **FAIL on mismatch**), system tool versions (FAIL on mismatch, `optional` → warning when missing), limits backend, Zephyr, zdocs, launch CLAUDE.md, `.xdmod/`, hooks. Exit 1 on any FAIL |
| `curatrix bootstrap --role R [--adopt] [--no-west] [--no-doctor]` | `west config manifest.group-filter` for the role + `xdmod.role`, `west update`, pip install of all active repos' `requirements.txt` (uv if present), tools.yaml tools into `.venv/opt` (sha256), copy `xdmod/launch/CLAUDE.md` to the root, `.claude/` symlinks (D113), pre-commit hooks + FreeCAD textconv (D100), `.xdmod/`, doctor. `--adopt`: stamp tools already in `.venv/opt` instead of re-downloading |
| `curatrix update [--adopt]` | `west update -k`, then the same refresh (pip only if a requirements file changed) |
| `curatrix launch kicad\|freecad\|drawio\|claude [ARGS…]` | GUI tools from the root with workspace-local config, memory limit only (D117). See [Launchers](#launchers) |
| `curatrix docs <repo\|full> [--open]` | zdocs build of `<repo>/docs` into `build/<area>/docs/` (strict, D64c) |
| `curatrix check [<repo>] [--stage local\|pr\|full\|baseline] [--no-cad] [--only IDs] [--base DIR] [--json]` | the repo's checks ([catalogue](#check-catalogue)); logs + `build/<area>/checks/summary.json`; prints a reproduce command per failure. `--only CK-D,CK-C1` runs those even outside the stage. `--json` puts the summary on stdout, the log on stderr |
| `curatrix gen stubs\|model\|cad-needs\|freecad-json\|tombstones\|all [<repo>] [--check]` | regenerate committed generated files ([Generated files](#generated-files)); `--check` only compares |
| `curatrix gen cad-exports [<repo>]` | kicad-cli sheet SVGs + BOM CSV into `build/<area>/cad/` (local, not committed) for the CAD directives |
| `curatrix gen freecad-json --textconv FILE` | semantic JSON of one `.FCStd` on stdout (git textconv driver, installed by bootstrap) |
| `curatrix ids new KIND [FILE] [--repo R]` | issue the next ID of KIND from the owning ledger; with FILE, replace that file's first `KIND-NEW-…` placeholder |
| `curatrix ids fix [<repo>] [--dry-run]` | replace every placeholder `<KIND>-NEW-<tag>` in the repo (same tag → same ID in every file) |
| `curatrix ids check [<repo>]` | CK-C1 + CK-C2 |
| `curatrix views build [<repo>] [--view NAME]` | model JSON → view graph (`build/<area>/views/<view>.json`) → elkjs → drawio → headless Firefox → `views/<view>.drawio.svg` |
| `curatrix views check [<repo>]` | CK-D3 (no browser) |
| `curatrix views normalize [<repo> \| FILES…] [--check]` | rewrite editor-saved `.drawio.svg` into the normalized form (decompress, drop editor attributes, sort cells, re-render, hash) |
| `curatrix variants [<repo>] [--model FILE] [-v]` | variant rules F1, F2, V1–V5 on a model JSON (Pilot export or compact) |
| `curatrix needs-diff BEFORE AFTER [-o FILE]` | change impact between two sets of needs.json (files or folders): changed needs, SUSPECT (direct/transitive), DANGLING. Exit 1 if any |
| `curatrix work start\|done` | **stub** (task 4.4c): prints how to create a worktree by hand, exit 2 |
| `curatrix hook pre-commit` | what the installed git hook runs (CK-C1 warning, CK-H1, `.drawio.svg` freshness, FCStd-without-JSON warning) |

Roles (`--role`, repo-topology.md §4): `syseng` (manifest default, D93), `ee` (`+ee`), `ee3d`
(`+ee,+kicad-3d`), `me` (`+me,+freecad-parts`), `sw` (`+sw`), `integration` (`+ee,+me,+sw,+integration`),
`full` (all, incl. big libraries), `ci-full` (= integration).

### Launchers

| Tool | Environment |
|---|---|
| `kicad` | `KICAD_CONFIG_HOME=<ws>/.xdmod/kicad` (with empty global `sym-lib-table`/`fp-lib-table` in `10.0/`, so no user-global libraries and no first-run dialog); `XD_KICAD_SYMBOLS`, `XD_KICAD_FOOTPRINTS`, `XD_KICAD_3DMODELS`, `XD_KICAD_TEMPLATES` → `libs/kicad/*`, also as `KICAD10_*_DIR`. A `.kicad_sch` argument opens eeschema |
| `freecad` | `XDG_CONFIG_HOME`, `XDG_DATA_HOME`, `XDG_CACHE_HOME` → `<ws>/.xdmod/freecad/{config,data,cache}`. **Verified with FreeCAD 1.1.4**: it then reads `…/config/FreeCAD/v1-1/user.cfg`; curatrix keeps `BaseApp/Preferences/Document/CompressionLevel = 0` there (D63; a save then stores entries at ~100 %). `FREECAD_USER_HOME`/`FREECAD_USER_DATA` are ignored by 1.1. `XD_FREECAD_PARTS` → `libs/freecad` (the parts-library add-on preference is not set yet) |
| `drawio` | `/usr/bin/drawio --user-data-dir=<ws>/.xdmod/drawio`; after saving a `.drawio.svg`, run `curatrix views normalize <file>` (the pre-commit hook insists) |
| `claude` | Claude Code at the root with the workspace env; memory limit `claude` (8G), no timeout |

## checks.yaml

`<repo>/checks.yaml` says what `curatrix check <repo>` runs. Every key is optional; an absent section
switches its checks off. Paths are relative to the repo unless they start with `{ws}/`. Globs (`*`,
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
  files: [model/generated/NeedStubs.sysml, "model/*.sysml"]   # required; in order
  export: [RobArm]                  # packages to export (default: every top-level package of `files`)
  json: generated/model.json        # compact model JSON (default)
  needs: generated/model-needs.json # model-derived needs (default)
  variants: true                    # run CK-B4 on the model JSON

stubs:                              # CK-D1
  out: model/generated/NeedStubs.sysml   # default
  docs: [se-req]                    # required: doc ids whose needs.json (build/<area>/docs/deploy/html/<doc>/) feed the stubs
  package: NeedStubs                # default

views:                              # CK-D3 (needs `model` too)
  dir: views                        # default; one <view>.drawio.svg per view
  model: generated/model.json       # default: model.json

cad:                                # CK-D4 (plain Python: runs without CAD tools), CK-H1
  kicad: ["pcba/*/*.kicad_sch"]     # ROOT schematics; hierarchical sheets are followed
  freecad: ["parts/*.FCStd", "assemblies/**/*.FCStd"]
  needs: generated/cad-needs.json   # default
  freecad_json: generated/freecad   # optional: semantic JSON per .FCStd (<path>.FCStd.json)

requirements: true                  # CK-E2 / CK-E3 on the repo's own requirement needs
bootstrap_template: scripts/bootstrap.sh   # CK-H5 (robarm-manifest): copy must equal xdmod/templates/bootstrap.sh

commands:                           # repo-specific checks (CK-F*, tests, ...)
  - id: CK-F1                       # required, unique
    name: KiCad netlist vs. interface pin maps   # required
    run: ["{python}", "tests/check_pinmap.py", "-o", "{build}/pinmap.xml"]   # required argv (no shell)
    use: kicad-cli                  # limits.yaml use (default: script)
    stages: [local, baseline]       # default: all four
    cad: true                       # needs CAD tools: skipped with --no-cad (default false)
    level: error                    # error | warning | report (default error)
    cwd: "{repo}"                   # default
```

Placeholders in `run` and `cwd`: `{ws}` workspace root, `{repo}` repo folder, `{build}`
`build/<area>/checks`, `{area}`, `{python}` the venv's python. A command fails when it exits non-zero;
its output is in `build/<area>/checks/<id>.log`.

**Summary JSON** (`build/<area>/checks/summary.json`, also `--json`):
`{"repo", "area", "stage", "no_cad", "ok", "checks": [{"id", "name", "status", "level", "findings": [str], "log", "repro", "seconds"}]}`
with `status` = `pass | fail | warn | report | skip`. A stage fails iff a check has `fail`.

## Check catalogue

Stages from `checks.md`. "own" = curatrix's graph check over all needs.json files of the docs build
(own and imported needs, so it also sees upstream needs, which sphinx-needs' schema skips).

| ID | Check | Needs section | Stages (level) | Implemented |
|---|---|---|---|---|
| CK-A6 | docs build strict (zdocs); sphinx-needs schema covers CK-A1–A3 per document | `docs` | all (error) | yes |
| CK-A1 | link to an unknown ID (own, over imported needs too) | `docs` | all | yes |
| CK-A3 | ID matches the scheme and its kind matches the need type | `docs` | all | yes |
| CK-A4 | R3 orphans (also a schema rule) | `docs` | all | yes |
| CK-A5 | R5 HIL `TR` carries `firmware_sha256` and `shas` (also a schema rule) | `docs` | all | yes |
| CK-B1 | R1 every SYS-REQ refined or satisfied (`draft` sources don't count) | `docs` | full, baseline | yes |
| CK-B2 | R2 every requirement verified | `docs` | full, baseline (warning, D99) | yes, **not per configuration** yet |
| CK-B3 | R4 links to retired needs | `docs` | local/pr/full warning, baseline error (D75) | yes |
| CK-B4 | variant rules F1, F2, V1–V5 | `model.variants` | all | yes (V6, T1–T3: later, D135) |
| CK-B5 | duplicate IDs across documents | `docs` | full, baseline | yes |
| CK-B6 | R5a stale evidence: `TR.shas` vs. current pins (`west list`) | `docs` | full, baseline (report) | first version |
| CK-B7 | tombstones in `generated/retired-needs.json` | `model` or `cad` | local, pr (warning) | yes |
| CK-C1 | placeholder IDs | `ids` | all (error) | yes |
| CK-C2 | every ID of an owned kind in the sources is in the ledger | `ids` | local, pr, baseline | yes |
| CK-D1 | SysML stubs match the needs | `stubs` | local, pr, baseline | yes |
| CK-E1 | the Pilot parses the model with 0 errors | `model` | local, pr, baseline | yes |
| CK-D2 | `model.json` + `model-needs.json` match the model | `model` | local, pr, baseline | yes |
| CK-D3 | views: content, uncompressed, geometry sane, picture fresh | `views` | local, pr, baseline | yes (kinds `interconnection`, `decomposition`) |
| CK-D4 | `cad-needs.json` matches KiCad/FreeCAD files (plain Python) | `cad` | local, baseline | yes |
| CK-D5 | generated files record the pinned tool versions (`generated/provenance.json`, 4.4b) | `model` or `cad.freecad_json` | local/pr/full warning, baseline error | yes |
| CK-E2 | value fields appear in the sentence (number + unit) | `requirements` | local, pr, baseline | first version |
| CK-E3 | EARS pattern vs. sentence start, "shall" | `requirements` | local, pr, baseline (warning) | first version |
| CK-G1 | needs-diff against `--base` (report, `build/<area>/checks/needs-diff.md`) | `docs` | pr, full | yes (skipped without `--base`) |
| CK-G2 | suspect links against the last baseline's needs (R7) | `docs` | full (report), baseline (error) | yes, needs `--base` |
| CK-H1 | `.FCStd` stored compressed; compressed drawio | — | local, pr, baseline | yes |
| CK-H2 | build output inside the repo | — | local, pr | yes |
| CK-H3 | unpinned `requirements.txt` lines; broken `tools.yaml` | — | local, pr (warning) | yes |
| CK-H4 | commits since `origin/main` without `Co-Authored-By` | — | pr (warning) | yes |
| CK-H5 | `scripts/bootstrap.sh` drifted from `xdmod/templates/bootstrap.sh` (D118) | `bootstrap_template` | all (warning) | yes |
| CK-F* | domain checks (pin maps, devicetree, firmware, ERC, …) | `commands` | per command | via `commands` only |

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
tools:                        # installed into <ws>/.venv/<location>
  - name: jdk
    version: "21.0.13+9"
    kind: tarball             # tarball | zip | conda | file | npm
    url: https://…
    sha256: d7f5…             # required except for npm (npm checks integrity itself)
    location: opt/jdk         # relative to .venv
    strip: 1                  # tarball: leading path components dropped (default 1)
    subdir: share/…           # conda / zip: copy only this folder of the package
    package: elkjs            # npm: package name (default: name)
    links: {gh: bin/gh}       # symlinks .venv/bin/<name> -> <location>/<path>
    env: {JAVA_HOME: "{location}"}   # exported by `curatrix env` ({location}, {venv})
    roles: [sw]               # optional: only for these roles
system:                       # used from the machine (D19)
  - name: kicad-cli
    version: "10.0.8"         # exact | "any" | prefix wildcard "10.0.*"
    cmd: [kicad-cli, --version]   # default [name, --version]
    regex: '(\d+\.\d+\.\d+)'  # default: first x.y[.z] in the output
    optional: true            # missing = warning; a wrong version is always a FAIL
    roles: [ee, integration, full]
```

Downloads are cached in `<ws>/.xdmod/cache/downloads/` and checked against `sha256` before use.
Each installed tool gets a stamp `.venv/opt/.xd-stamps/<name>.json` (name, version, sha256); `doctor`
compares stamps with tools.yaml. The Zephyr SDK belongs in robarm-sw's tools.yaml (D138), e.g.
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
| `generated/retired-needs.json` | `gen model` / `gen cad-needs` / `gen tombstones` | tombstones (D130): a generated need that vanished without `status: retired` keeps `{id, type, title, status: retired, retired_on, source_file}` until the next `baseline/*` tag of the manifest | CK-B7 |
| `generated/freecad/<path>.FCStd.json` | `gen freecad-json [--shape]` | trace part (plain Python: objects, `trace` fields, placements, plain values, spreadsheets) + optional `shapes` (FreeCAD: volume, bbox, solids) | textconv / review |
| `views/<view>.drawio.svg` | `views build` | model.json | CK-D3 |
| `generated/provenance.json` | `gen model`, `gen freecad-json --shape`, `views build` | the tool versions used (tools.yaml stamps, system `--version`) for each file they wrote | CK-D5 (record vs. tools.yaml pins; no tools needed, so it runs in CI) |

**Tool provenance (4.4b).** Files made with an external tool (the Pilot + JDK for `model.json` and
`model-needs.json`; elkjs, drawio viewer and Firefox for views; FreeCAD for `--shape` JSON) get an
entry `{"made_by": "curatrix gen model", "tools": {"jdk": "21.0.13+9", "sysml-pilot": "0.63.1"}}`
in `generated/provenance.json`. CK-D5 reports a file whose record is missing or differs from the
pins in tools.yaml (e.g. made on a rolling distro with another Firefox), so after a pin bump the
files must be regenerated. Plain-Python outputs (stubs, cad-needs, tombstones) have no entry.
`curatrix doctor` fails when an installed tool differs from its pin.

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
`--shape`, tombstones, cad-exports), `ids`, `views` (interconnection, decomposition), `variants`,
`needs-diff`, pre-commit hook, Sphinx extension, reusable CI workflow (first version, untested on GitHub).

Stubbed / later: `work start|done` (4.4c); view kinds `context`, `usecases`, `allocation`, `variants`;
coverage per configuration (R2 per cell, `coverage-matrix`), `config-page`, `sysml-element`;
variant rules V6, T1–T3 and `configs` derivation; FreeCAD TechDraw / GLB exports and the review
report; CK-F* domain checks (repos add them as `commands`); TR extraction from test reports (4.5a);
affirmatrix integration for R7 (needs-diff is the interim).

## Tests

```sh
curatrix run --use tests -- .venv/bin/python -m pytest -q xdmod/curatrix/tests             # all
curatrix run --use tests -- .venv/bin/python -m pytest -q -m "not tools" xdmod/curatrix/tests   # no Java/node/Firefox
```

Markers: `sphinx` (runs sphinx-build), `tools` (Pilot, elkjs, Firefox). Temporary files go to
`build/xdmod-dev/pytest/`.
