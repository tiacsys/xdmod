# FreeCAD assembly template (`curatrix new asm`)

`curatrix new asm <AssemblyDef> --repo <repo>` makes `assemblies/<assembly-def>/` in an ME repo
(task 5.23, XD-ADR-0128, XD-ADR-0137). FreeCAD itself writes both documents: curatrix runs
`new-asm.py` in `FreeCADCmd` under the `freecad` limits with the workspace-local config
(uncompressed saves, CK-H1), and judges success by the script's result file, never by the exit
code (FreeCADCmd exits 0 when a script raises).

| File | What |
|---|---|
| `new-asm.py` | makes `<name>-skeleton.FCStd` (App::Part `Skeleton` with the master sketch `MasterSketch`, spreadsheet `Params`) and the top document `<name>.FCStd` (`Assembly::AssemblyObject` `Assembly` with `TraceID` = the def's `ME-ASM`, a `Joints` group, an `App::Link` to the skeleton) |
| `check-asm.py` | not a template: the `FreeCADCmd` script of the ME checks CK-F4c, CK-F16, CK-F17, CK-F18 (task 5.25, `mechecks.py`); opens every document, recomputes, never saves, writes a result file |
| `cam-asm.py` | not a template: the `FreeCADCmd` script of `curatrix cam` for an assembly (task 5.26, `mecam.py`): STEP, 3MF/STL of the printed parts with the version embossed, TechDraw view SVGs, the exploded view; never saves |
| `fonts/` | the pinned font of the version emboss (DejaVu Sans Mono Bold, with its licence) |
| `doc/` | the `asm-<name>` document skeleton (`__NAME__`, `__TITLE__`, `__ID__`, `__TITLE_RST__`); `new asm` also adds its entry to `docs/documents.yaml` |

The skeleton's file name carries the assembly name because FreeCAD names a document after its
file and a cross-document expression names that document (`canary_assembly_skeleton#MasterSketch...`):
two assemblies with a plain `skeleton.FCStd` would clash when opened together (XD-ADR-0146).

Parts are linked into the top document by the designer (FreeCAD links, one per usage in the
model, CK-F15). Parts refer only to the skeleton, never to the top document (CK-F14).
