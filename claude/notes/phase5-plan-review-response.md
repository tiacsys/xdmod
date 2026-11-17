# Owner decisions on the Phase 5 plan review (Fable, 2026-11-17)

> Moved from `build/review-phase5-plan/` into the repo on 2026-11-17, before `build/` was emptied. The logs and
> experiments it refers to under `build/review-phase5-plan/` are in the owner's local archive of `build/`
> (2026-11-17), not in the repo.

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
- **"What to constrain" (2026-11-17), all three parts agreed** (order, limits with the two co-design
  limits open until 5.28, the deferral list as sorted with the owner, the six exit criteria). Plan
  rewritten from this list.
