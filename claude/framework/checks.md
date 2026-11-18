# Consistency checks (task 3.6)

Status: **AGREED 2026-11-14** (review answers → D98–D101). Collects every check decided so far: D38, D46, D47, D56, D60, D63, D64, D71, D75, D78, D83, D86–D89 (`../decisions.md`),
rules R1–R7 in `trace-model.md` §4, `id-scheme.md` §6, `views.md` §6, and the spike's lessons (`../notes/spike.md` §9).

## 1. Where checks run

| Stage | Who runs it | Scope | CAD content | Purpose |
|---|---|---|---|---|
| **local** | person or agent, one command per repo from the workspace root (D46, D67), under the limits of D71 (applied by curatrix) | the repo + its upstream docs (D35) | **yes** (KiCad, FreeCAD installed locally) | full feedback before pushing |
| **pre-commit** | git hooks, installed by the bootstrap in every active repo (D100); fast, staged files only | changed files | no | normalizers, ID placeholders, formatting |
| **PR CI** | GitHub Actions per repo (D47, D56) | the repo + siblings on the same branch name (D52) | **no** | gate for merging |
| **full set** | bump-bot job in robarm-manifest (D89) | all repos at the new pins | no | cross-repo rules |
| **baseline gate** | person, locally, before tagging `baseline/vX.Y.Z` | all repos, full checkout | **yes** | release quality |

Check IDs use the prefix `CK-` (e.g. `CK-D4`) so that they can't be confused with decisions, review findings or variant rules. They become `XD-CHECK` needs later (D121).

**Level** means what a finding does: **error** fails the stage, **warning** is reported but does not fail, **report** adds a summary to the PR.

## 2. Check catalogue

### CK-A. Need structure (sphinx-needs schema, strict build)

| # | Check | Stages | Level |
|---|---|---|---|
| CK-A1 | Link written on the wrong side, to an unknown ID, or to a wrong target type (link types declared per need type, D64h) | local, PR, full | error |
| CK-A2 | Required links ("Min" in the link table) and required fields present; `status`, `layer`, `category`, `verification_scope` from their enums; `configs`/`config` hold valid `SYS-CFG` IDs | local, PR, full | error |
| CK-A3 | ID matches the regex and its kind matches the need type (D78) | local, PR, full | error |
| ~~CK-A4~~ | No orphans (R3). Retired 2026-11-17: the schema rule of `needs_config.toml` enforces it in CK-A6 (task 5.2). Catalog parts are left out: an `ME-PART` with a `standard` (FreeCAD `Standard`) or `catalog` (`Manufacturer` + `MPN`) field from `curatrix gen cad-needs` (xdmod#69 finding 16; KiCad components not yet) | — | — |
| ~~CK-A5~~ | HIL test results carry `firmware_sha256` and SHAs (R5, D60). Retired 2026-11-17: schema rule, CK-A6 (task 5.2) | — | — |
| CK-A6 | Every doc builds strict (`-W --keep-going`, every doc reports, D64c); `doccheck` passes | local, PR, full | error |
| CK-A7 | Document layout (xdmod#69 Q8, finding 15): every own registry entry has its folder, every folder below `docs/` with a `conf.py` is in the registry, per-deliverable documents sit in `docs/pcbas/`, `docs/assemblies/`, `docs/firmware/`, `docs/protos/`, one `harnesses` document per repo with harnesses. Plain Python; only in repos with a `cad` or `code` section | local, PR, baseline | warning until it ran on the canary |

### CK-B. Graph rules (own check in xdmod, because sphinx-needs skips external needs)

| # | Check | Stages | Level |
|---|---|---|---|
| CK-B1 | Every `SYS-REQ` is refined or satisfied (R1) | full, baseline | error |
| CK-B2 | Every requirement has a `verifies` link (R2) | full, baseline | warning in iteration 1; error at the baseline gate from iteration 2 (D99) |
| CK-B3 | Links to `retired` needs (R4, D75) | local, PR, full: **warning**; baseline: **error** | grace until baseline |
| CK-B4 | Variant rules F1–F2, V1–V6, T1–T3 (`curatrix pleml check`, D105) | local, PR, full | error |
| CK-B8 | Variants across levels (§2a; task 5.16, implemented): one domain variant per configuration and usage, in the model and in KiCad / FreeCAD, Zephyr board variants by name; `curatrix variants list` lists every variant and what it serves | local, PR, full | warning until it ran on the canary |
| CK-B5 | No duplicate IDs across all repos | full, baseline | error |
| CK-B6 | Stale evidence: `TR` whose SHAs don't match the pins or the baseline (R5a, D131) | full: report; baseline: doesn't count | report |
| CK-B7 | Tombstones: deleted generated needs without retiring first get a tombstone; tombstones older than the last baseline are removed (D130) | local, PR | warning |

### CK-C. IDs and ledger (`id-scheme.md` §6)

| # | Check | Stages | Level |
|---|---|---|---|
| CK-C1 | No placeholder IDs (`…-NEW-…`) | pre-commit (warning), PR (error) | error on PR |
| CK-C2 | Every ID in the sources is ≤ the ledger's number for its kind | local, PR | error |

### CK-D. Generated and committed files ("generate, commit, check", spike lesson 2)

| # | Check | Stages | Level |
|---|---|---|---|
| CK-D1 | SysML stubs (`concern`, `requirement`, stakeholder `part`) match the needs, including value attributes (D42, D83) | local, PR | error |
| CK-D2 | `model-needs.json` matches the model (needs the Pilot / Java) | local, PR (syseng only) | error |
| CK-D3 | drawio views (`.drawio.svg`) match the model in **content**, not geometry; uncompressed; geometry sane; picture fresh (hash) (D38, D64a, D96) | local, PR | error |
| CK-D4 | Committed CAD-derived needs (`generated/cad-needs.json`) match the CAD files (KiCad netlist fields, FreeCAD `Document.xml`) (D110) | local, PR (plain-Python readers of the trace fields, no CAD tools; xdmod#11), baseline | error |
| CK-D6 | Committed code-derived needs (`generated/code-needs.json`) match the code: code units from `@xdid` Doxygen blocks, test cases from the comment above each `ZTEST` (D77, D80; task 5.10) | local, PR (plain Python), baseline | error |
| CK-D5 | `generated/provenance.json` records the tool versions that made the generated files; mismatch with `tools.yaml` | local, PR, full: warning; baseline: error (xdmod#12) |

### CK-E. Model

| # | Check | Stages | Level |
|---|---|---|---|
| CK-E1 | The Pilot parses and resolves the model with 0 errors (marker line, since jshell's exit code is unreliable) | local, PR (syseng) | error |
| CK-E2 | Requirement value fields agree with the EARS sentence: each of `min`/`max`/`nominal` occurs as a number (any format), the `unit` once as symbol or name (D83, task 5.4) | local, PR | warning until it ran on real requirements |
| CK-E3 | EARS pattern: the sentence matches its `ears` field | local, PR | warning |
| CK-E4 | Conformance of a domain model to its upstream model (§2a; task 5.15, implemented) | local, PR | warning until it ran on a canary board with ports (the C0 canary unit has none) |

### CK-F. Domain consistency against syseng interfaces (`SYS-IF`): checked, not generated

| # | Check | Stages | Level |
|---|---|---|---|
| CK-F1 | KiCad connectors and harness ends match the pin maps of the domain model (net name and pin number per signal); extended in Phase 5, see §2a | local, PR, baseline | warning until it ran on the canary, then error |
| CK-F2 | Zephyr devicetree matches the model (pins, buses, channels, `trace-id` in our own binding, D64f) | local, PR (robarm-sw CI builds the firmware with the Zephyr SDK, D101) | error |
| CK-F5 | Firmware builds for `nucleo_g474re`; unit tests pass on `native_sim` (Twister); the Twister run has `before_docs: true` and its results show as preview `TR` needs in the SW test report of the same run (task 5.10). A preview never counts: not coverage, not a baseline result, not evidence (D60); the preview command runs at `local` and `pr` only | local, PR (robarm-sw, D101) | error |
| CK-F3 | FreeCAD spreadsheet parameters and LCS placements match model attributes, every variant row; extended in Phase 5, see §2a | local, PR, baseline | warning until it ran on the canary, then error |
| ~~CK-F4~~ | KiCad ERC passes; FreeCAD documents recompute. Split 2026-11-17 into CK-F4a (ERC), CK-F4b (DRC), CK-F4c (FreeCAD recompute), see §2a; never built | — | — |

### CK-G. Change and suspect links

| # | Check | Stages | Level |
|---|---|---|---|
| CK-G1 | `needs-diff` against the target branch: changed, removed and transitively affected needs, as a PR comment | PR, full | report |
| CK-G2 | Suspect links (R7): affirmatrix `graph status` once adapted (D59); until then, `needs-diff` lists links whose targets changed | full: report; baseline: error | gate before a baseline |

### CK-H. Hygiene

| # | Check | Stages | Level |
|---|---|---|---|
| CK-H1 | `.FCStd` stored uncompressed (D63); drawio uncompressed | pre-commit, PR | error |
| CK-H2 | No build output inside repos (D46: outputs go to `build/<area>/`) | PR | error |
| CK-H3 | `requirements.txt` / `tools.yaml` pins exist for every tool a repo uses | PR | warning |
| CK-H4 | Commit trailers on agent commits (D51) | PR | warning |
| CK-H5 | A copy of an xdmod template (`scripts/bootstrap.sh`) equals the template (D118) | all | warning |
| CK-H6 | `checks.yaml` lists in `expect:` exactly the checks the repo runs (task 5.1) | all | error |
| CK-H7 | PR size: hand-written lines and files against the base (task 5.1) | local, PR | warning |

## 2a. New checks of Phase 5 (task 5.14)

Every check that Phase 5 adds, with its ID, before its code (`claude/CLAUDE.md`, "How to add a
built-in check"). **Every new check starts as a warning** and becomes an error (the "target" column)
only after it ran on the canary. "PR" means the check is plain Python and runs in CI without KiCad or
FreeCAD; a check without "PR" needs the tool and runs locally (`curatrix fixtures` records its
planted error, P5-13). Decisions: XD-ADR-0126 to XD-ADR-0144 in the manual
(`explanation/decisions/`). IDs: CK-D6 is taken by xdmod#40 (SW-IMPL and SW-TC from the code, task
5.10, not merged yet), so the new CK-D checks start at CK-D7.

| ID | Name | Area | What it checks | Stages | Start | Target | Task |
|---|---|---|---|---|---|---|---|
| CK-D6 | code-needs | SW | committed code needs match the code (xdmod#40) | local, PR | as in xdmod#40 | | 5.10 |
| CK-E4 | conformance | model | every port a domain def inherits from a system def is redefined in the chain, by a port whose def specializes the inherited one; the same at signal level; name clashes solved; every (domain kind, system kind) pair of a specialization has a link type (XD-ADR-0132) | local, PR | warning | error | 5.15 |
| CK-F6 | ee-projects | EE | projects found by `pcba/*/*.kicad_pro` and `proto/*/*.kicad_pro` (checks.yaml `cad.projects`); one `.kicad_pro` per folder, file name = folder name, root schematic of the same name; no KiCad project files (`.kicad_pro/sch/pcb/prl/jobset/dru`, library tables) outside these folders. **Implemented** (task 5.17, plain Python; XD-CHECK-0035, XD-RULE-0049) | local, PR | warning | error | 5.17 |
| CK-F7 | ee-one-to-one | EE | each board def (not external) has exactly one project whose `TraceID` is its `EE-PCBA`, each cable def one `harness/<name>/`, each block of the prototype configuration one `proto/` project; and back; no `Realizes` / `Conforms` fields left on projects (XD-ADR-0128, XD-ADR-0135). **Implemented for boards** (task 5.17; XD-CHECK-0036, XD-RULE-0049; a board def is a def that specializes `XdDomain::Pcba` directly, so board variants do not count; the folder name follows the def name); cables **implemented** (task 5.22): each cable def (`XdDomain::Cable`, `EE-HAR`) 1:1 with `harness/<name>/<name>.yml` by its `metadata.TraceID`, folder named after the def; `proto/` projects: not yet (no prototype-block marker in the EE model) | local, PR | warning | error | 5.17, 5.22 |
| CK-F1 | connectors | EE | every connector has a `portName` field (`-` = none) naming a port usage of the board def, with `portType` and `portTypeID` = its def's name and `EE-PORT` ID (owner decisions Q10, Q11 of tiacsys/xdmod#69, replacing the single `Port` field with the def ID, so two connectors of one def are told apart); each port of the board def is named by exactly one connector; net names and pin numbers equal the pin map in the EE model; harness ends pin to pin against both ports, also on external parts. **Implemented for boards** (task 5.18, plain Python on the committed connectors JSON and model.json; connectors are references `X`, `P`, `CN` or any symbol with a port field (`J`/`JP` are jumpers); a connector with `portName = -` and leftover `portType`/`portTypeID` is a finding; root-sheet nets `/X` compare as `X`; a connector pin on a net that is not in the pin map is a finding, an unconnected one is not). **Harness ends implemented** (task 5.22, plain Python on the WireViz YAML and model.json, checks.yaml `cad.harnesses`): each WireViz connector names the end port of the cable def on lines `portName: ...`, `portType: ...`, `portTypeID: ...` of its `notes` (`portName: -` = none; WireViz allows no other free connector key); its `pins` and `pinlabels` contain the pin map (both ends use the same net names, also the pin map of an external part); every conductor, connector `loops` included, joins pins of one net; wires named by number, wire label or unique color; a cable def has at least two ends, each typed by an `EE-PORT` def; a pin-map pin whose net another end carries is wired; the ends are the ports of the cable def, whose `connects` the model derives from its ports typed by (conjugated) connector port defs; a subset of the connection syntax is read, the rest (mates, templates) is reported) | local, PR, baseline | warning | error | 5.18, 5.22 |
| CK-F22 | port-names | EE | port usages of the parts of the EE model (boards, cables, external parts) have functional lowerCamelCase names, never designators (`j1`, `p3`, `x2`); every part with a `portName` has an `X` designator, so connectors are told apart from jumpers (owner decisions Q10, Q11). **Implemented** (plain Python on model.json and the connectors JSON; designator-like = a KiCad reference prefix (J, JP, P, X, CN, U, R, C, L, D, Q, K, SW, TP, F, Y, T, H, FB, RN, BT, IC) and digits, case-insensitive, so devicetree-style names like `i2c0`, `spi1`, `can0` pass; connectors with `portName = -` are not asked for `X`; pins and signals inside port defs are left out; ME ports not yet: robarm-me has no `cad.connectors`) | local, PR, baseline | warning | warning | Q10, Q11 |
| CK-D7 | connectors-fresh | EE | committed `generated/<project>.connectors.json` matches the KiCad files. **Implemented** (task 5.18): the extraction is plain Python, so CI regenerates and compares like locally; the file lists its input files without a hash, so an edit that changes no connector does not make it stale; a sheet with a bus is listed under `unsupported` and reported | local, PR | warning | error | 5.18 |
| CK-D8 | connectors-vs-netlist | EE | the plain-Python connector extraction equals KiCad's XML netlist (`kicad-cli sch export netlist --format kicadxml`), every board (P5-15). **Implemented** (task 5.18; equal to KiCad on every pin of the KiCad demos complex_hierarchy, ecc83-pp, multichannel_mixer, StickHub, interf_u and on the hierarchy fixture; buses are not read) | local, baseline | warning | error | 5.18 |
| CK-F4a | erc | EE | KiCad ERC per board and per prototype schematic: no error that is neither excluded in KiCad nor accepted in `accepted.yaml`, where both count only under the `Accepted-by:` rule of CK-F9 (XD-ADR-0126); warnings listed only. **Implemented** (task 5.19; `kicad-cli sch erc --format json --severity-all`, evaluated in Python; an ERC exclusion with a not-excluded twin is a phantom and does not count, an excluded finding of a rule that is off is a finding) | local, baseline | warning | error | 5.19 |
| CK-F4b | drc | EE | KiCad DRC per board, same rule; unrouted nets accepted in one `accepted.yaml` entry (XD-ADR-0144). **Implemented** (task 5.19; with `--schematic-parity`) | local, baseline | warning | error | 5.19 |
| CK-F8 | severities | EE | the project's ERC and DRC severities equal the `curatrix new pcba` template (a missing `erc` section = KiCad 10.0.8 defaults); a difference needs acceptance. **Implemented** (task 5.19; custom rules in `.kicad_dru` with a severity other than `error` count as differences, rule key `dru:<name>`; the ERC pin conflict matrix `erc.pin_map`, rule key `pin_map`; unused CK-F8 entries are reported) | local, PR | warning | error | 5.19 |
| CK-F9 | acceptance | EE, ME | `accepted.yaml` entries are well formed and keyed by rule and items; an entry, and a KiCad ERC/DRC exclusion in the `.kicad_pro`, counts only if added by a human commit with `Accepted-by:`, no agent trailer, and nothing but acceptance entries or exclusions; else a proposal (XD-ADR-0126). **Implemented** (task 5.19; an entry counts from the newest commit that wrote one of its own lines, a real `Accepted-by` trailer, one parent, every other commit of the entry its ancestor; this needs rebase merges (squash: every acceptance a proposal; merge commits never accept); the owner accepts a proposal by a commit that changes the entry, and any later change by an agent makes it a proposal again; an exclusion from the commit that last added its key; baseline stays a warning until it ran on the canary; task 5.25: also `assemblies/<name>/accepted.yaml` of an ME repo, so the check needs `cad.projects` or `cad.freecad`) | local, PR: warning; baseline: error | warning | error at baseline | 5.19, 5.25 |
| CK-F10 | jobset | EE | jobset rules: no "Execute Command" job, no "Copy Files" outside the output folder, no statistics job, BOM delimiters set, variant names in jobs = the project's variants, each variant job = its base job except variant and file name (XD-ADR-0142). **Implemented** (task 5.20; the base job is the job of the shared template; in a project with variants each variant-dependent template job is replaced by `<id>-<variant>`; new rule from the canary run: no job without a variant after a variant job, because KiCad 10.0.8 keeps the last job's variant; ERC/DRC jobs not allowed; job `output_filename`/`output_dir` must stay inside `${XD_CAM_OUT}`; every job, also without a variant, equals its template job except variant and file name; `curatrix cam` refuses Execute Command, files outside the output, the order and variant findings) | local, PR | warning | error | 5.20 |
| CK-F11 | version-variable | EE | title block of every sheet and of the board: title `${XD_BOARD}`, Rev `${XD_VERSION}`; the board's silkscreen has the two lines `${XD_BOARD}` and `${XD_VERSION}`; the committed values are `XD_VERSION = unversioned` and `XD_BOARD` = the project name. **Implemented** (task 5.20; changed by owner decision Q13 of tiacsys/xdmod#69: `curatrix cam` writes the version without the `<board>/` tag prefix, so a release version fits the Rev field (a preview version is cut off at the frame: open point for the owner), and the board name into `XD_BOARD`; both silkscreen lines (the version line filled with a long preview version) must stay inside the outline's bounding box (x and y) and off Edge.Cuts circles and footprint pads, estimated at 0.87 x character width per character) | local, PR | warning | error | 5.20 |
| CK-F12 | bom-fields | EE, ME | every BOM part has Manufacturer and MPN; standard fasteners carry their standard designation instead. **Implemented for boards** (task 5.21; XD-CHECK-0049, XD-RULE-0058; plain Python, `curatrix/bom.py`; every part as the base schematic and each variant see it; a variant that changes value or footprint must also override the MPN; the standard designation is a field `Standard`); **implemented for ME** (task 5.27, plain Python, `curatrix/asmdoc.py`: below each top-level assembly, a bought part (a `lib/` object, or one with `Manufacturer` or `MPN`) that is not a standard fastener (`Standard` property) needs `Manufacturer` and `MPN`; an own part needs `Material`; a link to an object that is not there is a finding; boards and harnesses are one BOM line each) | local, PR | warning | warning (owner) | 5.21, 5.27 |
| CK-D9 | bom-vs-kicad | EE | the plain-Python BOM reader equals `kicad-cli sch export bom --variant`, every board and variant (P5-15). **Implemented** (task 5.21; XD-CHECK-0050, XD-RULE-0059; one line per reference, compared: value, footprint, DNP, Manufacturer, MPN, Setting; base and every variant; equal to KiCad 10.0.8 on the fixture `bom/`: a sheet used twice, a multi-unit symbol, DNP, `in_bom no`, a value override and a `Setting` per variant) | local, baseline | warning | error | 5.21 |
| CK-F13 | ee-variants | EE | variant names equal in the EE model, `.kicad_pro`, `.kicad_sch` and `.kicad_pcb`; per-reference overrides agree between schematic and board; every shunt part has a `Setting` per variant equal to the EE model (XD-ADR-0136) | local, PR | warning | error | 5.16 |
| CK-B8 | variants-across-levels | cross-domain | against the published syseng needs: exactly one domain variant per usage and configuration; the picked variant exists in the domain model and in KiCad / FreeCAD; Zephyr board variants map to board variants by name (canary) (XD-ADR-0136); implemented (XD-CHECK-0034, XD-RULE-0048): checks.yaml section `variants`, optional `variants.zephyr`; KiCad projects from `cad.kicad` and `cad.projects` (task 5.17) | local, PR, full | warning | error | 5.16 |
| CK-F14 | me-one-to-one | ME | `assemblies/<name>/` with `<name>.FCStd` and `<name>-skeleton.FCStd`; each assembly or sub-assembly def has exactly one document whose `TraceID` is its `ME-ASM`, and back; no reference from a part to the top document (XD-ADR-0128, XD-ADR-0137). **Implemented** (task 5.23, plain Python on `Document.xml` and the committed model.json; an assembly def specializes `XdDomain::Assembly` directly; the document file is named after the def; a def no other assembly def uses is top-level and needs its folder; `Realizes` / `Conforms` / `Satisfies` / `PartOf` next to the ME-ASM TraceID are findings) | local, PR | warning | error | 5.23 |
| CK-F15 | link-counts | ME | FreeCAD links per part or sub-assembly equal the usages (syseng for the blocks it sees, the ME model for internal ones), per variant filtered by `Configs` (XD-ADR-0138). **Implemented** (task 5.23: a link names its target by the target object's `TraceID`; the ME model's usages count with their multiplicity, a CAD-owned part is a def with an `ME-PART` short name (a reference, no need); syseng usages count for the ME def that specializes the used block; per configuration named in `Configs` of the links, a link without `Configs` counts for all; the model usages are not filtered by configuration yet; the skeleton link and links into the board library (`cad.board_library`, a board is an EE block) are not counted; findings: a usage the ME model repeats from the system model, a system block realized by two ME defs, a multiplicity that is not one number; a system usage of a block no ME def realizes is not counted, since it may be an EE or SW block) | local, PR | warning | error | 5.23 |
| CK-F3 | freecad-params | ME | spreadsheet aliases `<usage>_<attribute>` (XD-ADR-0146; was `<port>_<attribute>`) of every variant row and LCS placements (with `Port`) equal the model, default tolerance per kind (lengths, angles), overridable per attribute. **Implemented** (task 5.24, plain Python on `Document.xml` and the committed model.json: aliases are `<usage>_<attribute>` of the part and port usages of a top-level assembly def; the port placement is `x`, `y`, `z`, `yaw`, `pitch`, `roll` of `XdDomain::MechanicalPort`; defaults 0.001 mm and 0.001 deg, `@XdDomain::ModelMatchTolerance { value = ...; }` per attribute, in its own unit; variant rows not yet: the canary has no configuration table) | local, PR, baseline | warning | error | 5.24 |
| CK-F4c | recompute | ME | every FreeCAD document recomputes without errors (exploded-view proxy error ignored in `FreeCADCmd`). **Implemented** (task 5.25; one `FreeCADCmd` run for CK-F4c, CK-F16, CK-F17, CK-F18: each assembly's skeleton, then its top document, then every other document of `cad.freecad`, recompute all, never save; findings accepted in `assemblies/<name>/accepted.yaml`, items `<document stem>#<object>`; a shared document's finding in any assembly's file) | local, baseline | warning | error | 5.25 |
| CK-F16 | solids | ME | every part shape is a valid solid. **Implemented** (task 5.25: objects with an `ME-PART` `TraceID`; valid, at least one solid, each solid valid with a volume, no face or shell outside the solids; rule `solid`) | local, baseline | warning | error | 5.25 |
| CK-F17 | collisions | ME | no overlap above a small tolerance between direct children of one assembly, per variant; parts joined by an assembly joint may touch; library fasteners left out; other overlaps need acceptance. **Implemented** (task 5.25: boolean common of each pair of links in the assembly object's group, 0.001 mm³, joined pairs (`Reference1`/`Reference2` of a joint) 0.1 mm³; the skeleton link left out; a fastener is a `lib/` object with a `Standard` property; per variant from the links' own `Configs`, not yet from a configuration-table row; rule `overlap`, items the two link names) | local, baseline | warning | error | 5.25 |
| CK-F18 | space-budget | ME | each board model stays inside its `SYS-IF` space budget in the assembly; details from the co-design spike. **Implemented** (tasks 5.25, 5.28, finding 16 of xdmod#69: a board model is a link to an object with an `EE-PCBA` `TraceID`; it sits at a seat LCS (`Port` = an `ME-PORT` that specializes a `SYS-IF` budget) and inside the budget's box in the board frame (`width` x `depth`, `-heightBelow` to `heightAbove`, the seat's restated values else the budget's defaults, tolerance 0.01 mm); no other part reaches into the box and no library fastener into the board (0.001 mm³); with `mountZoneDiameter` in the budget, a cylinder of that diameter around each hole `hole<n>X`/`hole<n>Y`, through the whole box height, is left out of the box (mounting zones: supports below, fastener heads above; owner decision of 2026-11-18 on the canary bosses, XD-ADR-0134 note); a budget without one of the four box values is a finding; findings print the check's level; rule `space`, acceptable in `accepted.yaml` (items the board, or the part / fastener); a skip without a board model. Not yet: the KiCad outline, `Edge.Cuts` holes and connector positions against the budget) | local, baseline | warning | error | 5.25, 5.28 |
| CK-F19 | version-face | ME | every printed part has a version mark (LCS with `Role = version-emboss`). **Implemented** (task 5.26, plain Python on the `.FCStd` files: an object with a `PrintProfile` is a printed part; exactly one mark per document; `curatrix cam` stops at a printed part without one) | local, PR | warning | warning | 5.26 |
| CK-F20 | board-library | library | every file of the board library names an existing board tag and its `EE-PCBA`; at most 5 MB per file. **Implemented** (task 5.29, plain Python; also: file name `boards/<board>/<board>-vX.Y.Z[-<variant>].FCStd`, `Version` and `Variant` properties = the name, `Commit` = the tag's commit, `Board` = the folder, the project's `TraceID` at the tag (required), the tag on main and pushed, files under `boards/` only added against the PR base). An error from the start (review of xdmod#58): the library is empty, so no canary risk | local, PR, full | error | error | 5.29 |
| CK-F21 | board-versions | ME | an ME FreeCAD file links a board version of the library, and the library has a newer one of that board and variant (or the linked file is not in the library): the "newer board version" note of XD-ADR-0139; moving is an ME change. **Implemented** (task 5.29, plain Python, `cad.board_library`) | local, PR, full | warning | warning | 5.29 |
| CK-D10 | local-cad-output | EE, ME | the local CAM output the documents include (schematic, renderings, ERC/DRC reports, drawings) exists and is not older than the CAD files; never in CI. **Implemented for boards** (task 5.21; XD-CHECK-0051, XD-RULE-0060; the `curatrix cam` run of the commit the repo is at; with uncommitted changes in the project folder, a run on exactly that state (`tree_state` in `cam.json`: a hash of `git status` and the changed files, so a later edit, deletion or revert makes it stale); `curatrix cam` also writes the ERC/DRC findings with their acceptance state; baseline stays a warning until it ran on the canary); **implemented for assemblies** (task 5.27: every top-level assembly, `mecam.current`: the run of the current commit, with uncommitted changes in the assembly folder or `parts/`, `lib/`, `print/` one on exactly that state, by the same `tree_state` hash as the boards (an edit, deletion or revert after the run makes it stale); `curatrix cam` also writes `mass.json` and `findings.json`) | local: warning; baseline: error | warning | error at baseline | 5.21, 5.27 |

Changed by these decisions: CK-D4 reads no `Realizes` / `Conforms` fields from KiCad projects and
FreeCAD top documents any more (XD-ADR-0128). Not checks but guards inside `curatrix cam`: the
number of jobs KiCad ran equals the jobset's job count; an embossed part is exactly one valid solid.
Co-design checks (KiCad outline and holes against the `SYS-IF`) get their IDs from task 5.28.

## 3. The check runner

xdmod has **one tool, `curatrix`**, with subcommands (D98): `check`, `gen` (stubs, model needs, view JSON), `ids` (ledger), `views` (drawio + SVG), and later `bootstrap` and `launch` (3.13). The check runner is called the same way for every repo and stage:

```
curatrix check <repo> [--stage local|pr|full|baseline] [--no-cad] [--only A,B] [--json]
```

- It knows each repo's checks from a small `checks.yaml` in the repo, e.g. which docs to build and which generated files to verify.
- It runs every tool under per-tool limits (D71) from `limits.yaml`. On GitHub runners, which have no systemd user scope, it falls back to `timeout` plus `ulimit -v` (address-space limit).
- It writes all output to `build/<area>/checks/` and a summary JSON for agents and for CI comments.
- It prints the exact command to reproduce each failure.
- `--stage pr --no-cad` is what GitHub CI runs (D56). robarm-sw's CI also builds the firmware (D101). The baseline gate runs `--stage baseline` with CAD content.

## 4. Answered review questions (2026-11-14)

1. **Tooling:** one tool with subcommands, named **`curatrix`** ("she who takes care of, curates") (D98).
2. **B2 coverage:** a warning in iteration 1; an error at the baseline gate from iteration 2 (D99).
3. **Pre-commit hooks:** installed by the bootstrap (D100).
4. **Devicetree check in CI:** yes. robarm-sw CI builds the firmware with the Zephyr SDK and runs F2 and the `native_sim` unit tests (D101).
