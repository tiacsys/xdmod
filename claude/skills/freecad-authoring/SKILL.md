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

## Printed parts and design output (task 5.26; XD-ADR-0143)

- A printed part has the properties `PrintProfile` (the name of `print/<name>.ini` in the repo)
  and `Material` (group `BOM`), and one version mark in its document: an LCS `VersionMark` with
  `Role = version-emboss`, `TextSize`, `MaxWidth` (optional `EmbossDepth`, default 0.6 mm) on the
  face for the version, its z axis out of the part (CK-F19). Never emboss in the `.FCStd`.
- `curatrix cam robarm-me <asm>` writes the output under `build/robarm-me/cam/<asm>/<version>/`;
  the exploded view takes its moves from `assemblies/<asm>/explode.yaml` (`{link name: [dx, dy,
  dz]}`, mm) if it exists. Version tags `<asm>/vX.Y.Z` are the owner's; agents propose them.
- The renderings (`renderings/front|top|right|iso.png`, task 5.30) come from the same run (without
  Blender: XD-ADR-0147): shaded without OpenGL, colour by BOM kind (printed orange, board green, fastener grey, bought dark grey,
  other blue), not by the colours in the document. Do not try the 3D view's `saveImage` or the
  Render workbench headless: both give nothing here (`claude/notes/me-renderings-spike.md`).
  With Blender installed, `cam` renders them with Blender instead (glTF from `FreeCADCmd`, Cycles
  CPU; `--no-blender` for the fallback; `cam.json` `renderings.method`). Never call `blender` bare,
  not even `--version`: only `curatrix run -- blender`, `curatrix launch blender` or the
  `.venv/bin/blender` shim (`--factory-startup`, user paths in `.xdmod/blender/`).

`curatrix variants list robarm-me` lists the assembly variants: the model def, the configuration
table row with its parameters, the links with `Configs`, and what each variant serves.

## Driving the FreeCAD GUI through the MCP server

- The owner (or you, with decision Q2) starts `curatrix launch freecad --mcp`: the addon FreeCADMCP
  opens 127.0.0.1:9875 with the workspace token for that session only, `HOME=.xdmod/stepup/home`.
  Claude Code reaches it through the `freecad` server of `<ws>/.mcp.json` (written by
  `curatrix update`; start Claude with `curatrix launch claude` so `XD_FREECAD_MCP_TOKEN` is set).
- Check `get_rpc_status` first. Give long calls an explicit `timeout`. A call that opens a modal box
  blocks the GUI thread until a human closes it (`still_running`, then `GUI_DISPATCH_STUCK`); so
  in `execute_code` replace `QMessageBox` statics and `QMessageBox`/`QDialog` `exec`/`exec_` by
  logging before you call an addon that may ask something.
- StepUp board load (`XD_STEPUP` on `sys.path`): set `Mod/kicadStepUpGui` `prefix3d_1` to
  `libs/kicad/packages3D` and `pcb_placement` to 2 (or a board grid origin), then
  `kicadStepUptools.onLoadBoard(file_name=<copy under build/>)`. Gives one coloured object per
  component (`claude/notes/codesign-spike.md`, addendum 2026-11-18). Never on a repo file.

## To be added

Part presence by `Configs` and variant rows in `Params`; recompute, solid and collision checks
with `accepted.yaml` (only humans write `Accepted-by:`); the StepUp push through the MCP server; CAM output.
