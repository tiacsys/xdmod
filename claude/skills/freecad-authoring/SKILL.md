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

## To be added after the spike

Assemblies and `curatrix new asm`; the master sketch and `curatrix gen freecad-params`; LCS with a
`Port` property; part presence by `Configs`; recompute, solid and collision checks with
`accepted.yaml` (only humans write `Accepted-by:`); StepUp; CAM output; the MCP server.
