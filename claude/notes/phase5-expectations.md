# Phase 5 expectations: domain structure, interaction and tooling (EE and ME)

Taken 2026-11-16/17 by the coordinator agent while the owner shared expectations one by one.
The tasks of Phase 5 in `claude/plan.md` are written from them.

## Frame (owner, 2026-11-16)

- A new Phase 5 goes in before the current Phase 5 (T-shape content). The current phases 5 and 6
  become 6 and 7.
- Goal: refine the structure, interaction and tooling of the downstream repos (review finding
  P4-2: the tooling the vertical bar needs), in place before the T-shape is fleshed out.
- Focus: EE and ME, starting with EE.

## Impact of the renumbering (to do with the task list, one change set)

- `xdmod/claude/plan.md`: phases 5 and 6 become 6 and 7, tasks 5.x become 6.x and 6.x become 7.x.
  Note: task 5.14 (first baseline) sits under Phase 6 today; it would become 6.14 under Phase 7.
- About 30 files in xdmod and the five robarm repos cite "Phase 5" or task numbers (READMEs, doc
  index pages, the manual tutorials and how-tos, `claude/framework/*.md`, `robarm-syseng/model/*.sysml`).
  One branch name in every touched repo (D52).
- `xdmod/claude/decisions.md` is frozen (D120): its phase numbers stay as history.
- `claude/notes/phase4-review-response.md` and D140 say "Phase 5.0".

## Open questions

- Phase 5.0 "make the checks bite" (agreed 2026-11-15): does it become part of the new Phase 5,
  or stay as its own step before it? D140 ends when it is finished.
  Owner (2026-11-17): part of the new Phase 5 (tasks 5.1-5.8); the checks bite by the end of this
  phase, "but we will see". No further expectations for EE, ME, SW or integration.

## EE expectations

### EE-1 KiCad projects: entry point, folders, one project per model element (2026-11-16)

Owner:
- A KiCad project's entry point is its `.kicad_pro` file.
- For now each KiCad project sits in its own subfolder under `pcba/` or `proto/`.
- The project name comes from a block in the system architecture: a 1:1 correspondence between a
  model element and a PCBA design project.

Today (robarm-ee, xdmod):
- The folder rule is a convention only (`pcba/README.md`, `repo-layouts.md` §2: `pcba/<name>/`
  with `<name>.kicad_pro/.kicad_sch/.kicad_pcb`); nothing checks it.
- The entry point is the root schematic: `checks.yaml` globs `pcba/*/*.kicad_sch` and
  `proto/*/*.kicad_sch`; `cad.py` finds the `.kicad_pro` from the schematic name.
- The PCBA's need ID (`EE-PCBA`) and its links (`Realizes`, ...) are text variables of the
  `.kicad_pro`. Nothing ties the project to one model element, and nothing says which model
  elements must have a project.

Gaps, to become tasks:
- Discover projects by `pcba/*/*.kicad_pro` and `proto/*/*.kicad_pro`; the root sheet is the
  `.kicad_sch` with the same name. A check: exactly one `.kicad_pro` per folder, file name equals
  folder name, no KiCad files outside these folders.
- Mark the model elements that are PCBAs (for example a `PCBA` part def or metadata in the xdmod
  SysML library, used in the robarm-syseng product architecture).
- A check in both directions: each PCBA element has exactly one project, and each project realizes
  exactly one PCBA element. Name rule from element name to folder name (e.g. `JointController` ->
  `pcba/joint-controller/joint-controller.kicad_pro`).
- Maybe: `curatrix new pcba <element>` creates the folder, project, library tables and text
  variables from the model element (my suggestion).

Questions:
- `proto/`: which model element does a prototype project correspond to: a prototype
  configuration (variants model), or a block of its own in the architecture?
- Is the name derived from the element (checked), or only motivated by it, with the link in
  `Realizes` as the actual tie?

### EE-2 Several instances of one PCBA (2026-11-16)

Owner:
- The system architecture must support several instances of one PCBA (for example the same
  controller board in every joint).

What follows (my reading, to confirm):
- The 1:1 of EE-1 is between a PCBA **definition** (`part def`) and a KiCad project. The
  instances are `part` usages typed by that definition, in any number and at any place of the
  product architecture. One project, one `EE-PCBA` need, many usages.
- The check of EE-1 then reads: every PCBA definition used in the product architecture has exactly
  one project; every usage is typed by such a definition; no project without a definition.
- Links: the KiCad project realizes the definition. Requirements allocated to one instance (for
  example "the shoulder board ...") stay on the usage in the model and reach the board through
  its definition; the coverage report must show which instances a board serves.
- Views: the product architecture and interconnection views show the usages with their names
  (`shoulder : JointController`); a parts list counts instances per definition.

Questions:
- Can instances differ? For example address straps or solder jumpers, unpopulated parts (DNP),
  a different firmware configuration or node ID. If yes: are these variants of the definition
  (KiCad assembly variants, or our variants model, D102-D107) or attributes of the usage
  (for example `nodeId = 3`) that the SW domain reads?
- Does SW need one devicetree or configuration per instance? (Touches the robarm-sw layout.)
- Do instances need their own IDs in the trace (for HIL results per physical board), or is the
  definition enough in iteration 1?

Answers (owner, 2026-11-16):
1. Yes, instances can differ.
2. SW: Zephyr board variants model this (hardware model v2: `board[@revision]/soc[/variant]`).
3. In iteration 1 the definition is enough for the trace; instances get no IDs of their own.

What follows:
- A PCBA definition with an MCU maps to one Zephyr board in robarm-sw; instances that differ map to
  variants of that board. The model must name, per usage, which board variant it uses, and a
  check compares that with the boards in robarm-sw (fits CK-F2, devicetree vs model).
- Still open: how the differences are described on the EE side and in the model, before they reach
  Zephyr (usage attributes such as `nodeId = 3`, DNP or jumper settings per variant, KiCad
  assembly variants or our variants model). Also: is a Zephyr board variant always one of these
  differences, or can SW add variants of its own?

### EE-3 Design output (CAM) through KiCad output jobs, with a version pin (2026-11-16)

Owner:
- Each KiCad project gets tooling that makes its design output with KiCad's native output jobs.
- First set: Gerber files, pick-and-place file, netlist, 3D model, renderings of the board from top
  and bottom (orthographic), one 3D rendering; the schematic as PDF and SVG; a picture of the
  board's stackup; a table of the design rules. More outputs later.
- During output generation a version derived from `git describe` is pinned into the outputs: into
  the frames (title blocks) and into the board's silkscreen.

Context:
- This brings the EE part of the CAM pipeline (D23) forward from the iteration 2 backlog
  (plan.md: "CAM pipeline (D23, D30) ... iteration 2", moved there by D43). The plan and
  that backlog line change with it.
- Tools: `kicad-cli` 10.0.8 is pinned as optional for the ee, integration and full roles
  (tools.yaml). PR CI has no KiCad (D56).

What follows (to verify against KiCad 10):
- One output-job file (`<name>.kicad_jobset`) per project, or one shared jobset in xdmod that each
  project uses, run with `kicad-cli jobset run`. A curatrix command, for example
  `curatrix cam <repo> [<project>]`, runs it under limits into `build/<repo>/cam/<project>/<version>/`
  (D46).
- Native in KiCad: Gerber and drill, position file, netlist, STEP (or GLB), `pcb render`
  (top and bottom; orthographic still to check), schematic PDF and SVG. The stackup picture and the
  design rules table may not be native outputs: either a placed stackup / board characteristics
  table on a user layer that is plotted, or a small generator in curatrix that reads
  `.kicad_pro` / `.kicad_pcb` / `.kicad_dru`.
- Version pin: a project text variable (for example `${XD_VERSION}`), used in the title block of
  every sheet and in a silkscreen text on the board; set at generation time (`kicad-cli` can
  define variables for exports; to check for `jobset run`), never committed with a real value.
- A check that the title blocks and the silkscreen actually use the variable (plain Python, so CI
  can run it without KiCad).

Questions:
- Version source: several projects share one repo. Plain `git describe` gives the repo's version,
  not the board's. Per-project tags (for example `joint-controller/v1.2.0`, `git describe --match`)
  or the repo version for all boards?
- A dirty tree or a branch that is not `main` or a baseline: refuse, or mark the outputs as preview
  (`-dirty`, as for HIL evidence, D60)?
- Where does release output go: only `build/` and a release asset at a baseline, or also committed?
- Where does it run: locally only (KiCad on the reference machine), or also in a CI job with a
  KiCad container at baselines?

Answers (owner, 2026-11-16):
1. Each board has its own tags (for example `joint-controller/v1.2.0`); the version comes from
   `git describe --match '<project>/*'`.
2. A dirty tree, or a commit that is not on `main` or a baseline, gives output marked as preview
   (the version says so, for example `-dirty` / `-preview`, in the frames and the silkscreen too).
3. Output goes only to `build/` (no commit, no release asset for now).
4. Only locally for now; no CI job with KiCad.

What follows:
- The tag scheme `<project>/vX.Y.Z` goes into `workflow.md` / the EE `claude/CLAUDE.md`; who may
  create a board tag (owner only, like baselines?) is decided with the release tasks.
- Without any tag for the project: version `<project>/v0.0.0-<n>-g<sha>` or similar, still marked
  as preview.

### EE-4 Documentation outputs in the board's Sphinx document (2026-11-16)

Owner:
- The documentation outputs (renderings, schematic, design rules table, stackup) are included in the
  Sphinx documentation of the board.

Context:
- The framework already plans one document per PCBA, `pcba-<name>` "PCBA Design: <name>" (D21,
  doc-architecture.md §2, repo-layouts.md §2), and one per prototype setup, `proto-<config>`. Today
  robarm-ee has only `ee-design`, which was planned to be split once content exists.
- Conflict with EE-3: CAM output goes only to `build/` and runs only locally; PR CI and Pages have
  no KiCad (D56). So a CI docs build cannot show what only KiCad makes.

What follows (proposal):
- Split by who can make the output:
  - Stackup and design rules table: read in plain Python from `.kicad_pcb` / `.kicad_pro` /
    `.kicad_dru` and rendered as Sphinx tables by a directive (for example
    `.. xd-pcba-rules:: joint-controller`). Works in CI, never stale.
  - Schematic SVG/PDF and the renderings need KiCad. Either they are committed as generated files
    for the docs (like `views/`: `curatrix gen pcba-docs`, a check that they match the current
    KiCad files, by an input hash written into the file), or CI docs show a placeholder
    "rendered locally" and only local builds show them.
- One directive set for a board page (`xd-pcba` with the board's need, renderings, schematic sheets,
  stackup, rules), so every `pcba-<name>` document looks the same; the project template (EE-1
  scaffold) creates the document with it.
- The version shown in the docs is the one from EE-3 (preview marked).

Questions:
- Commit the docs outputs (schematic SVG, renderings) as generated files so CI and Pages show
  them, or keep them local-only with a placeholder in CI? (Answer 3 of EE-3 was "only build/" for
  the CAM output.)
- One document per board (`pcba-<name>`) from the start, as planned, or sections in `ee-design`
  for iteration 1?

Answers (owner, 2026-11-16):
1. Schematic and renderings stay local for now: CI and Pages builds show a placeholder
   ("rendered locally with KiCad"); local builds include them from `build/robarm-ee/cam/...`.
   Stackup and design rules tables come from plain Python and appear everywhere.
2. One separate document per board, `pcba-<name>`, from the start (and `proto-<config>` per
   prototype setup). `ee-design` keeps the EE requirements and the overview, or becomes `ee-req`
   as planned in doc-architecture.md.

What follows:
- The directive must find the local CAM output of the matching version, and say which version it
  shows; if the output is missing or older than the KiCad files, a warning (not an error, since
  CI never has it).
- The docs registry gets one entry per board document; the scaffold (EE-1) adds it.

### EE-5 The board's 3D model, ready for FreeCAD, from the start (2026-11-16)

Owner:
- A 3D model of each PCBA is prepared for import into FreeCAD.
- This may be a job for a FreeCAD plugin that works directly on the KiCad project.
- Important enough to have from the start.

Context:
- Nothing exists for this yet: no KiCad-to-FreeCAD path in the framework docs, tools.yaml or the
  ME repo. EE-3 already makes a 3D model (STEP) as CAM output, local, in `build/`.
- EE and ME are peers: they never link to each other, both link to interfaces in robarm-syseng
  (XD-RULE-0003, D36). The board's shape (outline, thickness, mounting holes, connector and
  component envelopes) is a mechanical interface between them.
- FreeCAD 1.1.4 is pinned (optional, roles me, integration, full); FreeCAD runs with a
  workspace-local config through `curatrix launch freecad`.

Two ways (to compare in a short spike):
- A. STEP from the CAM job (EE-3), imported into FreeCAD by a curatrix step or a small macro, as a
  part of its own (`ME-PART`? or a reference part) in the ME assembly. Simple, one-way, works from
  a version-pinned file.
- B. A FreeCAD workbench that reads `.kicad_pcb` directly, for example the KiCad StepUp workbench
  (FreeCAD addon). It loads the board with its components, and can also push a board outline or
  mounting-hole positions from FreeCAD back into KiCad (ECAD/MCAD round trip). More power, one
  more tool to pin and install workspace-locally (no user-global addons, rule 4).

What follows either way:
- The ME assembly refers to a board version (the board tag of EE-3), not to a moving file.
- The file must reach robarm-me without a direct EE->ME dependency: through the workspace
  (`build/robarm-ee/cam/<project>/<version>/`), or published by EE and pinned by ME.
- A check that the board and its mount agree (outline, holes) belongs to the mechanical interface:
  candidate for CK-F3 in iteration 1 or 2.

Questions:
- Plugin (B) from the start, or STEP import (A) first and the plugin later?
- FreeCAD assemblies are committed, but EE-3 output is local only. How does a committed ME
  assembly refer to the board: a link to the local build file (breaks on a fresh checkout until
  `curatrix cam` ran), a committed simplified board (envelope STEP) in robarm-me, or a parametric
  placeholder driven by interface values from the model?
- Who owns the mechanical interface of a board: syseng (`SYS-IF` with outline and holes as
  attributes), and EE and ME both conform to it?

Answers (owner, 2026-11-16):
1. The FreeCAD plugin from the start (KiCad StepUp workbench or similar, reading the KiCad project
   directly). It is pinned and installed workspace-locally (`.xdmod/` FreeCAD config, rule 4).
2. The board model for ME is committed to a dedicated FreeCAD library.
3. The board's mechanical interface is owned by syseng (`SYS-IF` with outline, thickness, mounting
   holes, connector positions); EE and ME both conform to it.

Context for 2:
- The workspace has only the upstream `FreeCAD/FreeCAD-library` (`libs/freecad`, about 5.7 GB,
  shallow, group `freecad-parts`, only the me and full roles). Nothing of ours.
- A dedicated library keeps EE and ME peers: EE writes board models into it, ME reads from it,
  neither depends on the other's repo.

What follows:
- A new library repo (for example `tiacsys/freecad-pcba-models`, path `libs/freecad-pcba`),
  small, in its own west group that the ee and me roles both get. Creating it is an admin action
  (D123).
- A curatrix step, after `curatrix cam` (EE-3), exports the board through the plugin at a board
  tag (`joint-controller/v1.2.0`) into the library: one file per board version, with the board's
  `EE-PCBA` ID and version as properties. Only tagged (non-preview) versions are committed.
- The ME assembly links to a fixed version in the library; moving to a new board version is an
  explicit ME change.

Questions:
- Library scope: only this project's boards (robarm), or a tiacsys-wide library for all projects?
- How does a board version get into the library: a PR to the library repo by the EE agent, or a
  bot like the pin bump?

Answers (owner, 2026-11-16):
1. Only robarm's boards: a robarm-* repo (for example `robarm-freecad-pcba`), so agents post
   freely there (workflow.md §2) and it gets the robarm checks and agent review (D126).
2. The EE agent opens the PR that adds a board version to the library.

### EE-6 Connector pin assignments in the board docs; connectors name their model port (2026-11-16)

Owner:
- The PCBA document shows information extracted from the schematic, with scripts and Sphinx
  directives. Start with the pin assignments of the board's connectors.
- Each connector carries, besides its designator, a property that names the port of the board's
  system model element (the PCBA part def of EE-1/EE-2).
- So the syseng role can see whether a board interface is implemented and whether it conforms to
  the interface specification.

Context:
- `cad.py` reads hidden trace fields (TraceID, Realizes, Satisfies, Conforms, PartOf, Status,
  Configs) in plain Python. It does not know nets: pin-to-net needs the connectivity (wires,
  labels, hierarchical sheets), which the KiCad XML netlist (`kicad-cli sch export netlist
  --format kicadxml`) gives; `cad.py` can already read that netlist.
- CK-F1 "KiCad netlist matches the pin maps of the interfaces" is specified (checks.md, local and
  baseline, error) but not built. This expectation is its first real use.

What follows (proposal):
- A new hidden connector field, for example `Port` = the port name in the PCBA part def
  (`servoOut`). Connectors without a port (test points, debug headers) say so explicitly
  (`Port = -`), so a forgotten field is an error, not a silent gap.
- Extraction: from the netlist, per connector: designator, `Port`, value / footprint, and per pin:
  number, pin name, net name. Written as a committed generated file
  (`generated/<project>.connectors.json`, like `cad-needs.json`), so that CI and Pages show the
  tables without KiCad; CK-D4 style check that it matches the KiCad files (locally, and a
  hash of the schematic files in CI).
- Directive `.. xd-pcba-connectors:: joint-controller`: one table per connector (pin, signal / net,
  pin name), headed by designator and port, with a link to the port's interface (`SYS-IF`).
- Conformance (CK-F1): per port of the PCBA part def, exactly one connector names it; every `Port`
  value exists in the model; the connector's pins carry the signals the interface defines (pin
  count, signal names, maybe pin numbers and directions). Result per interface in the syseng
  trace report: implemented by `<board>/<designator>`, conforms yes / no, why not.
- The interface specification must then define signals at pin level: a port def (or interface def)
  in syseng with one nested port or attribute per signal, and optionally a pin map.

Questions:
- Commit the extracted connector data (small JSON) so CI and Pages show the pin tables, unlike the
  renderings (EE-4)? I recommend yes: it is text, reviewable, and the conformance check needs it.
- How is a signal matched to a pin: by net name (naming rule, e.g. net `SERVO_PWM` = signal
  `pwm`), by pin number from a pin map in the interface spec, or by both?
- Does the interface spec fix the connector type and pin numbers (mechanical and electrical),
  or only the signals, with pin numbers chosen by EE?

Answers (owner, 2026-11-16):
1. Commit the extracted connector data for now (`generated/<project>.connectors.json`).
2. Signals are matched by net name and pin number.
3. Connector type and pin numbers are EE design decisions, but captured in SysML v2 and related
   back to the system model. A place in robarm-ee for board connector definitions is needed: a new
   top-level folder, or `model/`, which can later also hold the board block diagrams in SysML v2.
   The owner asks for a proposal: where model information lives at which level of detail, and how
   refine / realize relations work for trace. "This is exactly at the heart of what we try to
   realize with xdmod."

### Proposal: domain sub-models (answer to EE-6 question 3, given to the owner 2026-11-16)

Levels of detail:
- System model, `robarm-syseng/model/`: what crosses a domain boundary. Blocks down to the product
  level (one part def per PCBA, ME assembly, SW component), their ports, and the interface defs
  (`SYS-IF`) at signal level: signal names, direction, kind, values from requirements. No connector
  types, pin numbers or part numbers.
- Domain model, `robarm-ee/model/` (new, same layout and checks as syseng): how EE realizes one
  block. Board defs, connector port defs with connector type and pin map (pin number, net name per
  signal); later the board's block diagram (circuit blocks, EE-CMP). Imports syseng and the xdmod
  libraries only, never ME or SW (XD-RULE-0003).
- Implementation, `robarm-ee/pcba/<name>/`: the KiCad project, with trace fields that name the
  domain model elements (TraceID of the project, `Port` of each connector).

Relations:
- Domain block realizes system block by SysML specialization: `part def JointControllerBoard :>
  JointController`. The ports are inherited and must be redefined, so the Pilot checks names and
  types (conformance at signal level for free). `gen model` turns `:>` across the repo boundary
  into a `realizes` link of the EE-PCBA need to the SYS-EL (the trace rule: concrete holds the link).
- Connector port def specializes the interface: `port def ServoHeader :> ServoIf`, adding
  connector type and pin / net per signal; `conforms` to the SYS-IF is derived the same way.
- KiCad implements the domain model: one ID for the board. The EE model element owns
  `EE-PCBA-nnnn` (short name); the KiCad project's TraceID must equal it, and every EE-PCBA board def
  has exactly one project (the 1:1 of EE-1). Each connector's `Port` names a port of that board def.
- Checks: Pilot (domain model vs system model); CK-F1 (KiCad netlist pin numbers and net names vs
  the pin map in the domain model); the 1:1 check of EE-1.

Why not the alternatives:
- Pin maps in syseng: every pin swap would be a syseng change, and syseng would own EE decisions.
- Pin tables only in rst in `ee-design` / `pcba-<name>`: no machine check against KiCad or the
  model.
- A separate top-level folder for connectors: `model/` holds them and later the block diagrams, with
  the existing `gen model` / views / checks machinery.

The same pattern later for ME (`robarm-me/model/`: assembly defs, mounting interfaces with
geometry, EE-5's board outline) and SW (D76 moves forward: SW sub-model). It becomes a framework
decision (new XD-ADR): "domain repos refine the system model in their own `model/` by
specialization".

Open points of the proposal:
- A new need kind for connector ports (`EE-PORT`?) or ports without IDs, traced through the board.
- The EE<->SW pin map (MCU pin to signal) stays an interface in syseng (D36), or SW reads it from the
  EE model? (Peer rule says syseng.)
- Each domain model costs a Pilot run (about 45 s, P4-11).

Owner on the proposal (2026-11-16): "a good start", accepted as the basis for the EE tasks.
1. New need kind for connector ports (`EE-PORT`, name to confirm in the task list): owned by the
   port in the EE model, `conforms` to the SYS-IF; the KiCad connector's `Port` field names it.
2. SW reads the MCU pin map from EE, not from syseng. Assumption: a tool later generates a
   devicetree from a KiCad schematic.
3. The extra Pilot run per domain model is accepted.

What follows from 2 (needs a decision, it changes a rule):
- It is an exception to D36 and XD-RULE-0003 (peers meet only at SYS-IF): SW becomes downstream of
  EE for the board pin map. New XD-ADR: "SW consumes the EE board model (pin maps) directly; EE
  never links to SW." The direction stays acyclic: syseng -> EE -> SW.
- Effects: robarm-sw lists the EE documents (or the EE model) as upstream (docs registry, D35;
  west groups for the sw role); SW needs (devicetree, SW-DD) may link to EE-PORT / EE-PCBA; the
  model check of robarm-sw (when it has one, D76) imports the EE model; CK-F2 (devicetree vs model)
  compares with the EE board model instead of syseng; the self-model and the domain-pair views
  (sysSw/sysEe, "no peer links") change: a new pair view eeSw.
- The devicetree generator from KiCad is a later tool (iteration 2 backlog); in iteration 1 the
  devicetree is written by hand and checked against the EE model.

### EE-7 ERC and DRC in the local checks; findings and acceptance in the docs (2026-11-16)

Owner:
- The local KiCad checks of a board include ERC and DRC.
- The board's documentation lists the findings and whether each has an annotation that it was
  accepted.

Context:
- CK-F4 (checks.md) covers ERC only ("KiCad ERC passes; FreeCAD documents recompute"), local and
  baseline, error; not built (no `commands` in `robarm-ee/checks.yaml`). DRC is not specified.
- KiCad keeps accepted findings as exclusions in the `.kicad_pro` (ERC and DRC), each with an
  optional comment. `kicad-cli sch erc` / `pcb drc` write JSON reports and can include the
  excluded findings (to verify the exact options in KiCad 10).

What follows (proposal):
- CK-F4 split: CK-F4a ERC and CK-F4b DRC per board (and ERC for each `proto/` schematic), plus
  FreeCAD recompute as its own ID. `curatrix check robarm-ee --stage local` runs them through
  `kicad-cli` under limits; baseline too.
- Rule: a check fails on any error or warning that is not excluded. An exclusion without a comment
  counts as not accepted (the comment is the annotation: the reason, maybe who and when).
- Reports `<project>.erc.json` / `.drc.json` with all findings: severity, rule, message, location
  (sheet / layer, items), accepted yes / no, comment.
- Directive `.. xd-pcba-findings:: joint-controller` (ERC and DRC tables, accepted ones with their
  reason, open ones highlighted), in the `pcba-<name>` document; a summary line (n open, m accepted)
  in the board overview.

Questions:
- Docs in CI: commit the reports as generated files, like the connector data (EE-6), so CI and Pages
  show the findings; or local only with a placeholder, like the renderings (EE-4)? I recommend commit:
  small, text, and the accepted findings are review-relevant. Plain Python can also read the
  exclusions and their comments from the `.kicad_pro` in CI.
- Who may accept a finding? Accepting a rule violation is a verdict; by D58 agents only propose it,
  and only a human's commit counts. Then the check needs to know who made the exclusion (git blame
  of the exclusion line, or a name in the comment).
- Warnings: must every warning be accepted too, or only errors?

Answers (owner, 2026-11-16):
1. ERC/DRC reports stay local; CI and Pages builds show a placeholder in the findings section.
2. The name of who accepted a finding comes from git history (the commit that added the exclusion
   to the `.kicad_pro`).
3. Only errors must be accepted for now; warnings are listed but do not fail the check.

What follows:
- Agents commit under the owner's git identity (D51), so the author name alone does not tell a
  human from an agent. A human acceptance = the commit that added the exclusion has no agent
  trailer (`Co-Authored-By: <agent>`, the same rule CK-H4 uses). An exclusion added by an agent commit,
  or not committed yet, counts as proposed, not accepted (D58); the check fails on it at the
  baseline stage and warns locally.
- Mapping an exclusion to its commit: `git log -L` / blame on the exclusion entry in the
  `.kicad_pro` (JSON); robust to reordering by matching the exclusion's text, not its line.

### EE-8 Bill of materials in the board document's appendix (2026-11-16)

Owner:
- The board documentation lists the bill of materials in its appendix.

What follows (proposal):
- The BOM can be read in plain Python from the `.kicad_sch` files (reference, value, footprint,
  fields such as manufacturer and MPN, the "exclude from BOM" and DNP flags), with hierarchical
  sheets and multi-unit symbols followed. So, unlike the renderings and ERC/DRC, it works in CI and
  on Pages without KiCad and without a committed file. (Cross-check locally against
  `kicad-cli sch export bom` once, in a test.)
- Directive `.. xd-pcba-bom:: joint-controller`, grouped by value + footprint + MPN, references
  collapsed (`R1-R4, R7`), quantity per board; placed in an appendix of the `pcba-<name>` document
  (zdocs: a last chapter titled "Appendix", or the Sphinx appendix mechanism of the zdocs theme, to
  check).
- The same BOM as a CSV in the CAM output (EE-3), so the docs and the fab data agree.

Questions:
- Which fields must every part have (for example Manufacturer, MPN; supplier and order number)?
  A check (warning) for missing fields?
- Board variants (EE-2: instances can differ, DNP per variant): one BOM per variant, or one BOM with a
  column per variant?
- Instance count: per board only, or also the totals over all instances in the system (EE-2)?

Answers (owner, 2026-11-16):
1. Every BOM part must have Manufacturer and MPN; a missing field is a warning (a check, local and
   CI, since the reader is plain Python).
2. Board variants: one BOM with a column per variant (quantity or DNP per variant).
3. Quantities per board only for now; no system totals.

What follows:
- The BOM reader must know the board variants and which parts each variant leaves out: this ties
  to the open EE-2 question of how instance differences are described on the EE side (KiCad
  assembly variants, DNP fields per variant, or our variants model). To settle in the task list.

### EE-2/EE-8 follow-up: how board variants are described (owner, 2026-11-16)

Owner:
- Use KiCad assembly variants for now.
- But variants are also given by how jumpers are set, and the owner is not sure an assembly variant
  can represent that.

Analysis (to verify in a KiCad 10 spike):
- Assembly variants decide per part: fitted or DNP, maybe field values per variant (KiCad 10
  feature set to check: DNP / exclude-from-BOM per variant, field overrides per variant, what
  `kicad-cli` exports per variant).
- Jumpers come in two kinds:
  - Set at assembly: solder jumpers and 0-ohm links. "Bridged" = fitted, "open" = DNP. These fit an
    assembly variant directly.
  - Set by hand after assembly: pin headers with a removable shunt (or DIP switches). The part is
    always fitted; only its position differs ("1-2", "2-3", open). Not an assembly matter. If KiCad 10
    can override a field per variant, a field `Setting` per variant can carry the position;
    otherwise it lives in the EE model.
- Proposal: the EE model (`robarm-ee/model/`) holds the board variants anyway (Zephyr board
  variants for SW, EE-2): per variant, the jumper settings as attributes (`J5 = "1-2"`), and what they
  mean (for example I2C address 0x41). KiCad holds what is fitted (assembly variant). A check
  compares: the variant names match between KiCad and the EE model; every jumper part in KiCad has a
  setting per variant in the EE model. The BOM shows the setting in the variant column ("fitted,
  1-2"). The board document gets a "Variants" table: variant, fitted differences, jumper settings,
  Zephyr board variant.

Answer (owner, 2026-11-16): the robarm boards use solder jumpers and pin header shunts (no DIP
switches). The proposal above is agreed: solder jumpers through KiCad assembly variants (fitted =
bridged), shunt positions per variant in the EE model, checked against KiCad.

### EE-9 Wiring harnesses (owner, 2026-11-17: "forgotten in the EE section")

Owner: the wiring harness is needed too (raised during ME-8).

Today: `robarm-ee/harness/README.md`: one folder per cable between boards, `harness/<name>/`, as
WireViz YAML, "only if WireViz is adopted" (D112, task 5.7a evaluates WireViz). D74: prototype
wiring is EE content (KiCad schematic per prototype setup).

Transposed from EE-1 to EE-8 (draft, to go through with the owner):
- 1:1: each harness is one folder `harness/<name>/` with one WireViz YAML as entry point, 1:1 with a
  model element: a harness / cable def in the EE model whose ends connect board ports (the
  connections of the system interconnection that cross between boards). Instances: the same cable
  used several times (one per joint).
- Connectors at both ends name the `EE-PORT` they mate with; pin-to-pin wiring checked against the pin
  maps of both boards (CK-F1, extended to harnesses): signal names and pin numbers on both sides.
- Outputs (local, `curatrix cam`): WireViz diagram (SVG / PNG), harness BOM (cable, connectors,
  contacts, with Manufacturer / MPN), a version from tags `<harness>/vX.Y.Z`.
- Docs: a section or document per harness (`harness-<name>`?): diagram, pin-to-pin table, BOM.
  WireViz runs in plain Python (no KiCad), so CI and Pages could show the diagrams.
- ME link: the harness's length and routing come from the ME assembly (cable path in FreeCAD), and
  the ME BOM lists the harness as one line (like a board). Another co-design point (EE <-> ME):
  length is an ME value, the wiring an EE value.
- Prototype jumper wiring (D74): stays a KiCad schematic per prototype setup, or WireViz too
  (task 5.7a compares them).

Answers (owner, 2026-11-17):
1. WireViz is adopted now (new XD-ADR; replaces the evaluation in task 5.7a and the "if adopted" in
   `harness/README.md`). WireViz becomes a pinned tool (tools.yaml, venv).
2. One document per harness (`harness-<name>`), with links to the boards it connects (their
   `pcba-<name>` documents and `EE-PORT`s).
3. The harness length and route are another co-design task (EE <-> ME), next to the board space
   budget: part of the same design task and spike.
4. Prototype jumper wiring stays a KiCad schematic per prototype setup (D74).

## ME expectations

Draft (2026-11-16): the EE expectations EE-1 to EE-8 transposed to ME / FreeCAD by the coordinator,
to be gone through with the owner one by one.

Today in robarm-me: `parts/*.FCStd` (flat), `assemblies/<asm>/` (`**/*.FCStd`), `lib/`, `templates/`,
`print/`, one document `me-design`; trace fields as object properties (group `Trace`: TraceID
ME-PART / ME-ASM, Realizes, ...); semantic JSON per file committed in `generated/freecad/` (D63);
TechDraw template with git fields set at export (freecad-storage.md §4); ME CAM = 3MF + STL + print
profile, no G-code (D30); review report locally (D135). Need kinds: ME-REQ, ME-ASM, ME-PART.

- ME-1 (from EE-1) Entry point and 1:1: each assembly is one folder `assemblies/<name>/` with one
  top assembly document `<name>.FCStd` (Assembly workbench root) as its entry point; 1:1 with a
  system block (part def) that is mechanical. Open: where its own parts live (in the assembly folder,
  or shared in `parts/`); are single parts (not assemblies) also 1:1 with model elements?
  Answers (owner, 2026-11-16):
  1. Both: an assembly's own parts may live in its folder (`assemblies/<name>/parts/`), shared parts
     in `parts/`.
  2. Agreed: only assemblies are 1:1; a single part only when the model treats it as a block.
  3. An assembly may cover several system blocks. Assemblies may be composed of sub-assemblies.
     Not all of this is exposed to the system model, but at the level of assemblies and
     sub-assemblies the owner expects a block diagram at the ME model level.
  What follows:
  - The 1:1 moves one level down: between an ME model element (assembly or sub-assembly def in
    `robarm-me/model/`) and its FreeCAD document. The ME model has its own decomposition
    (assembly -> sub-assemblies -> parts), drawn as block diagrams by the views engine
    (general / interconnection views in robarm-me).
  - Towards the system model: every mechanical system block is realized by exactly one ME model
    element (by specialization `:>`, as for EE); an ME element may realize several blocks (multiple
    specialization) or none (an internal sub-assembly that syseng never sees).
  - Checks: ME model vs FreeCAD (each assembly def has exactly one document, and back; the
    sub-assembly structure in FreeCAD matches the ME model's composition); ME model vs system model
    (each mechanical block realized exactly once, Pilot checks ports).
  - Same shape as EE (board def 1:1 KiCad project; board block diagram later), so one framework
    rule for both domains.
- ME-2 (from EE-2) Instances: 1:1 between definition and document; instances are usages (six joint
  modules, one design). Instance differences = ME variants (ME-8 follow-up). Trace on the definition.
  Answers (owner, 2026-11-16):
  1. Instances that differ mechanically (link length, servo size) are variants of one design: one
     document with parameter sets, not separate designs.
  2. Yes: a check compares the number of FreeCAD links (placements) per part / sub-assembly in an
     assembly with the number of usages in the ME model.
- ME-3 (from EE-3) Design output: no output-job mechanism in FreeCAD; a curatrix-run FreeCAD script
  per assembly (headless, under limits): STEP, 3MF + STL (D30), TechDraw drawings PDF + SVG,
  renderings (orthographic views, one 3D view), GLB. Version from `git describe --match
  '<asm>/*'` into the TechDraw title block (already planned) and, transposed from the silkscreen,
  maybe embossed or engraved on printed parts. Preview marking, `build/` only, local only (as EE-3).
  Answers (owner, 2026-11-16):
  1. Output set agreed: STEP of the assembly; 3MF + STL per printed part with the print profile;
     TechDraw PDF + SVG; GLB; renderings front / top / side (orthographic) and one 3D view, per
     assembly. Run by `curatrix cam robarm-me <asm>` (FreeCAD headless, under limits) into
     `build/robarm-me/cam/<asm>/<version>/`; preview marking, `build/` only, local only (as EE-3).
  2. Yes: the version is embossed or engraved on printed parts, at export time only (the `.FCStd`
     stays unchanged); the part marks the face for it (property such as `VersionFace`); a check warns
     when a printed part has no version face.
  3. Only assemblies are tagged (`<asm>/vX.Y.Z`); an exported part carries the version of the
     assembly being exported, also a shared part from `parts/`.
- ME-4 (from EE-4) Documentation: one document per assembly (`asm-<name>`, instead of one
  `me-asm`); renderings and drawings local with a placeholder in CI; parameter, material and mass
  tables from the committed semantic JSON (plain Python, CI works).
  Answers (owner, 2026-11-17):
  1. One document per top-level assembly (`asm-<name>`), with a chapter per sub-assembly.
  2. Mass and center of gravity: local only for now (placeholder in CI).
  Added output (to ME-3 and ME-4): an exploded view per assembly, as a rendering and in the
  document (local, placeholder in CI). FreeCAD's Assembly workbench has exploded views (to verify
  in FreeCAD 1.1: headless export, and whether the explode steps are stored in the document).
- ME-5 (from EE-5) Models across domains: ME reads board models at fixed versions from
  `robarm-freecad-pcba`; ME checks the board's mechanical interface (SYS-IF: outline, holes,
  connectors) against its mounts (CK-F3). Open: does ME publish anything for other domains
  (for example the arm's STEP for integration or simulation)?
  Answers (owner, 2026-11-17):
  1. ME only takes models in for now. Simulation is iteration 2.
  2. Pushing from FreeCAD into KiCad (StepUp) must be a wanted behaviour, not a local helper. It is
     not only mounts: also clearance, and making sure boards fit into the space allotted to them.
     How this workflow works in practice is another value proposition of xdmod.
  3. A newer board version gives a note or an issue on robarm-me; pulling the new board in stays
     with the ME role (no bot PR).
  What follows from 2 (sketch, to design as its own task, with a decision):
  - "ECAD/MCAD co-design" workflow. The space a board may take (outline, height, keep-outs,
    mounting holes, connector positions) is a system-level budget: the board's mechanical SYS-IF in
    syseng holds the values that both sides depend on.
  - A geometry change that starts in ME is one cross-repo change with one branch name (D52):
    robarm-me (the mount / housing), robarm-ee (outline, holes, keep-outs pushed by StepUp into the
    KiCad project), and robarm-syseng when the interface values change. The EE side reviews and
    owns the merge of its part; EE never takes ME geometry outside such a change.
  - Exception to the peer rule (like the EE->SW pin map): ME writes into EE's KiCad project through
    a defined tool step. New XD-ADR, together with the EE->SW one.
  - Checks: committed KiCad outline / holes match the SYS-IF; the board model (with components)
    fits the allotted volume in the ME assembly without collisions (ME-7); CK-F3.
  - Open for the design task: what exactly StepUp pushes (outline, holes, keep-out zones, component
    positions such as connectors?), whether EE may push back (component heights, connector moves),
    and how a conflict is resolved.
  - Owner (2026-11-17): direction agreed; a design task of its own in the new Phase 5, with a
    spike on a real board (StepUp push FreeCAD -> KiCad and back, cross-repo branch, checks).
- ME-6 (from EE-6) Interfaces: an ME domain model `robarm-me/model/` (assembly defs specialize system
  blocks; mechanical port defs specialize SYS-IF with geometry: hole pattern, positions, envelope).
  In FreeCAD each interface is a local coordinate system (LCS) or datum with a `Port` property naming
  the model port; new kind `ME-PORT`. Extracted (position, orientation, dimensions) from the
  semantic JSON, committed; table in the docs; conformance check (CK-F3) by name and value.
  Answers (owner, 2026-11-17):
  1. LCS (local coordinate systems) as the anchors of interfaces, with a `Port` property.
  2. Parameters in a FreeCAD spreadsheet, tied to model attributes by a naming rule: alias
     `<port>_<attribute>` (for example `servoMount_holeSpacing`).
  3. Tolerances: one default per kind (lengths, angles), overridable per attribute in the model.
  Added (owner): at least the top-level assembly uses the master sketch design pattern.
  What follows:
  - The top-level assembly has a master sketch (skeleton): the key geometry of the arm (joint axes,
    link lengths, board envelopes and other space budgets) in one place, driven by the parameter
    spreadsheet. Sub-assemblies and parts take their placement and main dimensions from it
    (expressions, sub-shape binders or links), and the interface LCS sit on it.
  - So the master sketch is where system-level geometry enters ME: the values that the system model
    fixes (link lengths, envelopes from SYS-IF) reach FreeCAD through the spreadsheet, and CK-F3
    compares them.
  - To verify in the spike / FreeCAD 1.1: references across documents (binders to a master sketch in
    another `.FCStd`) are fragile; how the semantic JSON shows them; recompute order.
  - Question: does the model only check the spreadsheet (CK-F3), or does a curatrix step write the
    model values into the spreadsheet (model drives CAD)?
  - Owner (2026-11-17): B, the model drives the CAD. A curatrix step (for example
    `curatrix gen freecad-params robarm-me`) writes the model values into the parameter spreadsheet
    of the top-level assembly; CK-F3 stays as the check that they agree. To test in the spike: that
    a script change of spreadsheet cells gives a small semantic-JSON diff (no object-ID churn, the
    risk in freecad-storage.md §5), headless recompute, and propagation through the master sketch.
- ME-7 (from EE-7) Checks and findings: recompute without errors (CK-F4), valid solids (Part check),
  interference between parts in assemblies, maybe printability (minimum wall, overhang). FreeCAD
  has no exclusion mechanism like KiCad: accepted findings need a committed file (for example
  `assemblies/<name>/accepted.yaml` with finding key and reason), acceptor from git history (no
  agent trailer). Local only with a placeholder in CI; only errors must be accepted.
  Answers (owner, 2026-11-17):
  1. Printability checks (minimum wall thickness, overhangs) go to iteration 2.
  2. Intended contacts: parts connected by an assembly joint may touch but not overlap beyond a
     tolerance; standard fasteners from the library are left out of the collision check; every
     other overlap must be accepted.
  3. Accepted findings in `assemblies/<name>/accepted.yaml` (check, parts, reason); the acceptor from
     git history (no agent trailer = human; agent commits only propose, D58); only errors must be
     accepted; reports local, placeholder in CI.
  Checks in iteration 1: recompute without errors, valid solids, collisions in assemblies, boards
  inside their allotted space (co-design task).
- ME-8 (from EE-8) BOM in the appendix: from the Assembly workbench / the semantic JSON (plain Python,
  CI works): printed parts (material, print profile) and bought parts (Manufacturer and MPN required,
  warning: screws, bearings, servos). Variants as columns; per assembly.
  Answers (owner, 2026-11-17):
  1. Standard fasteners carry their standard designation (for example `ISO 4762 M3x10, A2`);
     Manufacturer and MPN are required (warning) only for other bought parts.
  2. Both: an indented BOM along the assembly structure in the appendix, and a flat list with totals
     for the top-level assembly in the CAM output (CSV, for ordering).
  3. A board appears as one line with its board version and a link to its `pcba-<name>` document;
     its components stay in the EE BOM. The same holds for harnesses (EE-9).
- Variants (from the EE-2/EE-8 follow-up): ME variants by part presence and parameter sets (FreeCAD
  spreadsheet configuration tables); for example bench rig vs printed arm (D102-D107).
  Answers (owner, 2026-11-17):
  1. FreeCAD: parameter sets as a configuration table in the parameter spreadsheet; part presence
     per variant by the suppressed state (to verify in FreeCAD 1.1). Variants table and BOM columns
     as for EE; `curatrix cam` makes the outputs per variant.
  2. Across levels: board and assembly variants are named in the EE / ME model; each system
     configuration (`SYS-CFG`, variants model) picks one domain variant per instance (usage). One
     check across all domains: every picked variant exists in the domain model and in KiCad /
     FreeCAD; a domain variant that no configuration uses is a warning.
  3. Bench rig and printed arm are two variants of one assembly (settles the open point of task 5.5
     on the prototype's mechanics).

## Plan review (owner, 2026-11-17)

- D43 changes: iteration 1 includes a PCB layout. Routing is not completed, and the DRC errors
  from unrouted nets are accepted (plan 5.9, 5.18, 6.9).
- D140: agents may merge while the "checks that bite" block (5.1-5.8) runs; agreed. (Superseded by P5-14 below: D140 stays active for the whole of Phase 5.)

## Owner decisions on the plan review (Fable, 2026-11-17)

Review: `claude/notes/phase5-plan-review.md`. Decisions taken finding by finding with the
owner; the plan is updated from this list afterwards.

- **P5-1 accepted (2026-11-17; the D140 sentence is superseded by P5-14).** The canary becomes the spine of Phase 5: C0 right after 5.2 (the
  chain agreed after Phase 4, one KiCad sheet and one FreeCAD part saved by the real tools, the
  planted-error fixture for today's rules); C1 grows the canary board with 5.15 -> 5.17 -> 5.18 ->
  5.16 -> 5.21; C2 the assembly with 5.22 -> 5.23 -> 5.25 -> 5.24 -> 5.26; C3 co-design and the
  board library (5.12, 5.19) last. A tooling task is done only when the canary uses it. D140 ends
  when C0 and 5.1-5.7 are done; 5.8 (admin actions) runs independently.
- **P5-2 accepted (2026-11-17).** New model spike 5.9a before 5.9 (two tiny .sysml files in two
  folders: board def specializes a system block, port def specializes an interface def, one
  missing redefinition, one multiple specialization; Pilot with the upstream as library set;
  derive `realizes` / `conforms` from the export). 5.9 writes the XD-ADRs as *proposed*; they are
  accepted after spikes 5.9a-5.12 report. Correction recorded: conformance is not free from the
  Pilot; curatrix checks that every inherited port is redefined by a port whose def specializes the
  interface def.
- **P5-3 accepted (2026-11-17).** Design output always runs on a copy of the project in `build/`.
  Version: curatrix writes it into the copy's text variables and runs the jobset there (A).
  Variants: the single `kicad-cli` exports with `--variant` (B) if a job cannot name a variant;
  spike 5.10 ends with a written go/no-go. A plain-Python check forbids "Execute Command" jobs and
  "Copy Files" outside the output folder in jobsets. Stackup in iteration 1: a table, plus
  (optional, only if the canary needs it) a simple SVG cross-section drawn by curatrix from the
  same data.
- **P5-4 accepted (2026-11-17).** (1) A human acceptance is a commit with an explicit
  `Accepted-by: <name>` trailer, which agents must never write; a check: such a commit has no agent
  trailer and touches only acceptance entries. Real enforcement (commits signed with a key only the
  owner holds) stays in the iteration 2 backlog (D134). (2) A plain-Python check that the project's
  ERC/DRC severities equal the `curatrix new pcba` template; a difference is a finding that needs
  acceptance. (3) One acceptance file format for EE and ME: `pcba/<name>/accepted.yaml` and
  `assemblies/<name>/accepted.yaml`, same check code; entries keyed by rule and designators /
  part names, not positions, so they survive moves. KiCad's own exclusions stay for single findings;
  stated rule: a KiCad exclusion is lost when its items move.
- **P5-5 accepted with changes (2026-11-17).** (1) Part presence per variant through the existing
  `Configs` property on links, read by curatrix (export, BOM, collision check, usage count filter
  by it); the spike only confirms it. (2) Exploded view: a TechDraw view of the exploded view,
  exported headless, with a fixed time box in spike 5.11; if it fails, back to the owner before it
  is dropped. (3) ME renderings move to the end of Phase 5 (a late task after C2). Options to
  compare there: FreeCAD's rendering (the Render workbench addon, which drives external renderers)
  and Blender (pinned tool, headless `blender -b` on the GLB/STEP export, Cycles on CPU); fallback
  TechDraw / Draft SVG projections. (4) Spike 5.11 (master sketch across documents,
  configuration tables) finishes before 5.22-5.24 start.
- **P5-6 accepted (2026-11-17).** StepUp for the interactive push FreeCAD -> KiCad; the scriptable
  path (`kicad-cli pcb export step` with `--variant` and the version variable, plus a headless
  FreeCAD import that adds the board ID and version) for the export into the library; spike 5.11
  decides. Roles change: EE needs FreeCAD, ME needs the KiCad files and libraries (roles, west
  groups, tools.yaml, doctor). Pushed `.kicad_pcb` files are re-saved by KiCad 10 before commit.
  Minimum push in iteration 1: outline and mounting holes; the co-design spike 5.12 decides about
  keep-outs and connector positions (in, or iteration 2). Record the AGPL-3.0 licence check.
  Owner addition: where a step needs the GUI, MCP servers may let agents drive the tools (a running
  FreeCAD or KiCad started by `curatrix launch`, under limits). Evaluate in spikes 5.10/5.11:
  which MCP servers exist for FreeCAD and KiCad, pinned version, local only, what they can do
  (they run code inside the tool, so they are pinned and reviewed like any tool), and whether
  their results are reproducible enough for checks (or only for authoring).
- **P5-7 accepted (2026-11-17).** New task "skeleton of robarm-freecad-pcba" next to 5.19 (west
  project and group for ee and me, `checks.yaml` with `expect:`, CI, ruleset, `claude/CLAUDE.md`,
  licence, bump bot, full set). Size limit 5 MB per file to start (board body, connectors and parts
  above a height threshold, no tracks), revised on the first real board (C3); Git LFS only if
  simplified boards stay too large. A check that every file names an existing board tag. The
  repo's creation moves out of 5.8 to that task.
- **P5-8 accepted (2026-11-17), extended to ports.** Decide in 5.9: the domain model emits the
  `EE-PCBA` / `ME-ASM` and `EE-PORT` / `ME-PORT` needs; KiCad and FreeCAD carry these IDs only as
  references (TraceID of the project / top document, `Port` fields); the `Realizes` / `Conforms`
  fields on projects go away (derived from specialization). CK-D4 changes with it; the 1:1 checks
  (EE-1, ME-1) verify the references in both directions. `EE-CMP` and `ME-PART` stay CAD-owned.
- **P5-9 accepted (2026-11-17).** New block "SW and integration tooling", sized for the canary only:
  CK-F2 (devicetree vs the EE board model), SW-IMPL and SW-TC extraction, test results in the docs
  (with the check order fixed so that the docs build sees the Twister results of the same run,
  P4-2), a minimal trace report. The board-variant <-> Zephyr board variant check runs on the canary
  by name; a Zephyr board for the product board is not needed in iteration 1.
- **P5-10 accepted (2026-11-17).** The domain variant names the system configurations and usages it
  serves (`Configs`); the table "configuration -> variant per usage" is computed like a backlink;
  the check "exactly one variant per usage and configuration" runs in the domain repo against the
  published syseng needs. Instance counts: syseng owns the usages it sees (blocks of the product
  architecture); the domain model refers to them and does not repeat them; the domain model owns
  internal sub-assemblies and parts. The FreeCAD link-count check (ME-2) uses both.
- **P5-11 accepted (2026-11-17).** `/review-pr` for robarm-ee and robarm-me re-runs
  `curatrix check --stage local` with CAD content and posts the result table in the review. At the
  baseline stage, missing or stale local output is an error. The how-to (5.29) says that the owner
  reviews EE and ME PRs from a local docs build.
- **P5-12 accepted (2026-11-17).**
  1. A `proto/` project is 1:1 with a block of the prototype configuration in the system model
     (for example `JointProtoRig`). Bought boards and modules (Nucleo, PCA9685 and MCP3208
     breakouts) are external parts: a def with their headers as ports in the EE model, no KiCad
     project, outside the 1:1 project rule.
  2. Harness ends on bought parts (servo, pot) use port defs of these external parts in the EE model;
     CK-F1 checks against them.
  3. Only the owner creates board, assembly and harness tags (like baselines); agents propose a tag in
     the PR. The canary uses `v0.x` tags (for example `canary-board/v0.1.0`) for unfinished boards.
  4. SW adds no Zephyr board variants of its own in iteration 1; every Zephyr board variant maps to a
     board variant.
  5. Harness need kind: `EE-HAR`.
  6. Agents author the canary's KiCad and FreeCAD files, with MCP servers and skills where they help
     (the owner has seen good results). The canary does not need to be perfect or even work: it is
     about the motions and the tool integration. The owner steps in only where agents get stuck.
  7. 5.9 assigns IDs, stages and severities to all new checks in one table (CK-F5 exists already).
- **P5-13 accepted (2026-11-17).** The exit criterion is split: plain-Python rules fail on planted
  errors in the CI fixture; tool-backed rules (ERC, DRC, recompute, collision, StepUp, CAM) fail in a
  local fixture run, one command (for example `curatrix check fixtures --stage local`), whose result
  (rule, tool version, date) is recorded in the Phase 5 review and repeated at every baseline.
- **P5-14: option B (2026-11-17).** The owner: "Limiting D140 was a mistake of mine. I take the risk
  on option B." D140 (agents may merge) stays active for the whole of Phase 5. Conditions per PR:
  an agent review (`/review-pr`), green required checks (no Admin bypass after 5.8), and for EE / ME
  PRs the local CAD check run posted in the review (P5-11). The owner reviews per block (model, EE,
  ME, SW/integration, co-design) after the merge, against the canary with a demo script per block,
  and reverts or asks for fixes. This supersedes "D140 ends when C0 and 5.1-5.7 are done" (P5-1)
  and the plan's line on D140.
- **P5-15 accepted (2026-11-17).** Permanent local checks on every board: the plain-Python BOM reader
  against `kicad-cli sch export bom --variant`, and the connector extraction against KiCad's XML
  netlist (also part of the review run of P5-11).
- **P5-16: option B (2026-11-17).** The canary stays separate from the joint (revises the Phase 4
  answer "doubles as the first joint"). Everything that belongs to it is owned by a system
  configuration `canary` (`SYS-CFG`); reports, BOM totals and coverage numbers exclude that
  configuration. It stays as a stable test object for later tool changes; it need not be perfect
  or work.
- **"What to constrain" (2026-11-17), all three parts agreed:** the order (with D140 per P5-14), the
  limits per area (the two co-design limits stay open until spike 5.28 reports), the deferral list
  as sorted with the owner (deferred: GLB, EE pushing back through StepUp, unused-variant warnings;
  kept: exploded view time-boxed, version embossing, harness co-design, mass and center of
  gravity local, `curatrix new asm`), and the six exit criteria. The plan was rewritten from this list.
