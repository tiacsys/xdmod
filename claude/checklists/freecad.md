# Checklist: FreeCAD

For `.FCStd` files in robarm-me (`parts/`, `assemblies/`, `lib/`). Background:
`robarm-me/claude/CLAUDE.md`, `framework/freecad-storage.md`, skill `xd-freecad-authoring`. This
list grows with tasks 5.13 and 5.23-5.27.

## Run
- [ ] The local check ran **with CAD content** and its table is posted (P5-11). It names the
      checks that needed KiCad or FreeCAD; today there are none (they come with tasks 5.17-5.27).
- [ ] For changed `.FCStd` files: the local review report (`build/robarm-me/review/<branch>/`) is
      summarized in the PR (D135).

## Files
- [ ] No FreeCAD ran outside curatrix or its `.venv/bin` shims, not even `FreeCADCmd --version`
      (a bare call writes `~/.config/FreeCAD`). A PR text or log showing a bare `FreeCAD`,
      `FreeCADCmd`, `freecad` or `freecadcmd` call is a must-fix: ask the owner to check `~/.config/FreeCAD`.
- [ ] Saved by FreeCAD started through `curatrix launch freecad` (or `curatrix run --use freecad`),
      so the file is stored uncompressed (CK-H1, D63).
- [ ] No unchanged document re-saved: a `.FCStd` changed but its semantic JSON did not -> drop it.
- [ ] Parameters were edited, parts not rebuilt from scratch by a script (rebuilding changes all
      internal object IDs and makes a huge diff).
- [ ] No merge of two `.FCStd` versions: on a conflict one side was taken and the other change redone.

## Trace fields
- [ ] Objects with a trace ID have the `Trace` property group (`TraceID`, links, `PartOf`,
      `Status`, `Configs`) with **real IDs**: placeholders inside `.FCStd` are refused, so IDs come
      from `curatrix ids new ME-PART` (or `ME-ASM`).
- [ ] `curatrix gen all robarm-me` was run; `generated/cad-needs.json` and `generated/freecad/*.json`
      are committed with the `.FCStd` and fresh (CK-D4, CK-D5).

## Findings
- [ ] Recompute errors, invalid solids and collisions are fixed or proposed for `accepted.yaml`.
      An agent never writes the `Accepted-by:` commit (P5-4).
