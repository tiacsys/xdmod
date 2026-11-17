# KiCad board template (`curatrix new pcba`)

`curatrix new pcba <BoardDef> --repo <repo>` copies these files into `pcba/<board-def>/` of an EE
repo (task 5.17, XD-ADR-0128, XD-ADR-0129, XD-ADR-0142) and replaces the placeholders
(`__NAME__`, `__TITLE__`, `__ID__`, `__ROOT_UUID__`, `__TEXT_UUID__`, `__OUTLINE_UUID__`):

| File | What |
|---|---|
| `pcba.kicad_pro` | text variables `TraceID` (the board def's `EE-PCBA`) and `XD_VERSION = "unversioned"`; ERC severities (all rules, from the KiCad 10.0.8 project templates) and DRC severities; no variants |
| `pcba.kicad_sch`, `pcba.kicad_pcb` | empty sheet; a board with a 50 mm x 40 mm outline (so DRC starts clean); title block comment 2 `Version ${XD_VERSION}` (the `Rev` field cuts long versions off, KiCad spike §2.1); a silkscreen text `${XD_VERSION}` |
| `sym-lib-table`, `fp-lib-table` | workspace libraries only (`${XD_KICAD_*}`) |
| `pcba.kicad_jobset` | a **minimal** jobset (schematic PDF, BOM CSV with delimiters, XML netlist) until task 5.20 makes the shared CAM jobset. Its output folder is `${XD_CAM_OUT}/<name>`: the curatrix workspace env sets `XD_CAM_OUT` to `build/cam` (D46: output only under `build/`; `curatrix cam` sets its own). Run it only through curatrix (`curatrix run --use kicad-cli -- kicad-cli jobset run ...`, or KiCad from `curatrix launch kicad`); without the variable KiCad writes into a folder literally named `${XD_CAM_OUT}` |
| `doc/` | the `pcba-<name>` document skeleton; `new pcba` also adds its entry to `docs/documents.yaml` |

After copying, KiCad itself saves the schematic and the board (`kicad-cli sch upgrade --force`,
`kicad-cli pcb upgrade --force` under `curatrix run --use kicad-cli`), so the committed files are
in KiCad's own format.

`kicad-cli ... upgrade` also writes `<name>.kicad_prl` (per-user view state). An EE repo ignores
`*.kicad_prl` in its `.gitignore`, as robarm-ee does.
