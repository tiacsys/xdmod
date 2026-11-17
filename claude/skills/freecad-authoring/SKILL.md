---
name: xd-freecad-authoring
description: Use when you create or change FreeCAD files in robarm-me (parts/, assemblies/, lib/) - workspace-local config, uncompressed saves through FreeCAD, trace properties, generated JSON. Placeholder skill - completed after the FreeCAD spike (task 5.13).
---

# FreeCAD authoring (placeholder)

**Status:** what is known today. This skill is completed after the FreeCAD 1.1 spike (plan task
5.13, result in `xdmod/claude/notes/freecad-spike.md`) and tasks 5.23-5.27 (assemblies, master
sketch, ME checks, CAM). The spike also decides which MCP servers may drive FreeCAD.

Read first: `robarm-me/claude/CLAUDE.md`, `xdmod/claude/framework/freecad-storage.md`,
`xdmod/curatrix/README.md` ("CAD trace fields", "Launchers"), review list
`xdmod/claude/checklists/freecad.md`.

## Rules known today

- **Workspace-local config only.** Start FreeCAD with `curatrix launch freecad`; scripts run with
  `curatrix run --use freecad -- FreeCADCmd ...`. Both use the `.xdmod/` FreeCAD config, which
  saves `.FCStd` uncompressed (D63). A compressed file fails CK-H1. Never touch `~/.config`.
- **Files are saved by FreeCAD.** Change parameters (spreadsheet, properties) instead of
  rebuilding a part from a script: a rebuild changes internal object IDs and makes a huge diff.
- Do not re-save an unchanged document: the file changes anyway. The pre-commit hook warns when a
  `.FCStd` changed but its semantic JSON did not; then drop the change.
- **Trace properties** in the group `Trace`: `TraceID` (`ME-PART`, `ME-ASM`), `Realizes`,
  `Satisfies`, `Conforms`, `PartOf`, `Status`, `Configs`. **Placeholders inside `.FCStd` are
  refused:** take a real ID with `curatrix ids new ME-PART` and set it (skill `xd-issue-ids`).
- After every change: `curatrix gen all robarm-me` (cad-needs and semantic JSON in
  `generated/freecad/`), commit both with the `.FCStd`.
- `.FCStd` cannot be merged; on a conflict take one side and redo the other change.
- Run `curatrix check robarm-me --stage local` **with CAD content**; the reviewer runs it again
  (P5-11). Summarize the local review report (`build/robarm-me/review/<branch>/`) in the PR.

## Example: canary C0

The canary part `robarm-me/parts/canary-part.FCStd` on main is the smallest complete example: one part saved by
FreeCAD with a real `TraceID`, uncompressed, its semantic JSON and `generated/cad-needs.json`
committed. It belongs to the configuration `canary` (`Configs` property).

## Assemblies and model-driven parameters (tasks 5.23, 5.24; XD-ADR-0137)

1. Add the assembly def to `model/` (`part def <'ME-ASM-NEW-a'> X :> <system block>, Assembly`),
   its part usages (`part p : P;`; a CAD-owned part is `part def <'ME-PART-0001'> P;`, a
   reference) and port usages with values (`port mount : M { :>> x = 10 [mm]; }`).
   `curatrix ids fix`, `curatrix gen model`.
2. `curatrix new asm X --repo robarm-me`: FreeCAD writes `assemblies/x/x.FCStd` and
   `x-skeleton.FCStd`. Link each part once per usage into the top document (CK-F15).
3. `curatrix gen freecad-params robarm-me`: the model values into `Params` (aliases
   `<usage>_<attribute>`, at most ten). Drive the master sketch's named constraints and the LCS
   placements from `Params` by expressions; parts take dimensions from
   `x_skeleton#MasterSketch.Constraints.<name>` (the document name of `x-skeleton.FCStd`), never
   from the top document (CK-F14); such parts sit in `assemblies/x/parts/`.
4. Each interface is an LCS in the skeleton with the property `Port` (group `Trace`) = its
   `ME-PORT` (CK-F3 compares its placement).

Scripts: inputs by environment variables (FreeCADCmd opens extra arguments as files); judge
success by a result file the script writes (FreeCADCmd exits 0 when a script raises, and runs a
raising script twice); open the skeleton before the top document (through the top it loads only
partially); save a document before a cross-document link or expression points from it.

## To be added

Part presence by `Configs` and variant rows in `Params`; recompute, solid and collision checks
with `accepted.yaml` (only humans write `Accepted-by:`); StepUp; CAM output; the MCP server.
