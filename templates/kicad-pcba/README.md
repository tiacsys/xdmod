# KiCad board template (`curatrix new pcba`)

`curatrix new pcba <BoardDef> --repo <repo>` copies these files into `pcba/<board-def>/` of an EE
repo (task 5.17, XD-ADR-0128, XD-ADR-0129, XD-ADR-0142) and replaces the placeholders
(`__NAME__`, `__TITLE__`, `__ID__`, `__ROOT_UUID__`, `__TEXT_UUID__`, `__TEXT2_UUID__`, `__OUTLINE_UUID__`):

| File | What |
|---|---|
| `pcba.kicad_pro` | text variables `TraceID` (the board def's `EE-PCBA`), `XD_BOARD` (the board name, `__NAME__`) and `XD_VERSION = "unversioned"`; ERC severities (all rules, from the KiCad 10.0.8 project templates, plus the six rules the KiCad 10 GUI adds when it saves a project, e.g. `undefined_netclass`; owner decision Q12) and DRC severities; no variants |
| `pcba.kicad_sch`, `pcba.kicad_pcb` | empty sheet; a board with a 50 mm x 40 mm outline (so DRC starts clean); title block with title `${XD_BOARD}` and rev `${XD_VERSION}` (`curatrix cam` writes the version without the `<board>/` tag prefix, so it fits), comment 1 the board def's title, comment 2 its ID; two left-justified silkscreen lines `${XD_BOARD}` and `${XD_VERSION}` at the lower left of the outline (move and size them so the longest preview version, e.g. `v0.1.0-12-gabc1234-dirty-preview`, stays inside the outline and off holes and pads) |
| `sym-lib-table`, `fp-lib-table` | workspace libraries only (`${XD_KICAD_*}`) |
| `pcba.kicad_jobset` | the **shared CAM jobset** (task 5.20, XD-ADR-0142): first the jobs without a variant (schematic SVG, XML netlist, Gerber with job file, Excellon drill), then the variant-dependent ones (schematic PDF, BOM CSV with delimiters, pick-and-place CSV, STEP, orthographic top and bottom renderings, one 3D rendering). No ERC, DRC, statistics or Execute Command job. Output folder `${XD_CAM_OUT}/<name>`: `curatrix cam` sets `XD_CAM_OUT` to its version folder under `build/<area>/cam/`, the workspace env to `build/cam`. A board with variants gets one job per variant instead of each variant-dependent job (`curatrix cam <repo> <name> --update-jobset`); KiCad keeps the variant of the last job for the next one, so the jobs without a variant stay first. The SVG job writes one file per sheet, named after the sheet, into the output root; KiCad 10.0.8 ignores its file name, also a folder name with `/`, so `curatrix cam` adds the per-variant SVGs as single exports. The pick-and-place job appends `-all-pos` to its file name. CK-F10 checks the rules. Stackup and design-rule tables come from `curatrix cam` in plain Python |
| `doc/` | the `pcba-<name>` document: one section per `xd-pcba-*` directive (`sphinx/xdmod_sphinx/pcba.py`, task 5.21); `new pcba` also adds its entry to `docs/documents.yaml` |

Connectors are not in the template: each connector you place gets the reference prefix `X` (KiCad's
connector symbols default to `J`) and the hidden fields `portName`, `portType`, `portTypeID` that
name the board def's port it implements (CK-F1, CK-F22; how-to "Add a PCBA", step 4).

After copying, KiCad itself saves the schematic and the board (`kicad-cli sch upgrade --force`,
`kicad-cli pcb upgrade --force` under `curatrix run --use kicad-cli`), so the committed files are
in KiCad's own format.

`kicad-cli ... upgrade` also writes `<name>.kicad_prl` (per-user view state). An EE repo ignores
`*.kicad_prl` in its `.gitignore`, as robarm-ee does.
