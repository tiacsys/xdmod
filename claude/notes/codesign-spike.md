# Co-design spike (task 5.28): ECAD/MCAD, StepUp, space budgets

Date 2026-11-17. Inputs: ME-5 and EE-9 answers (`phase5-expectations.md`), FreeCAD spike §7
(StepUp not run then), owner decision 2026-11-17 (StepUp with `HOME` sandboxed, pinned under
`.xdmod/`; fallback the scripted STEP path). Result: XD-ADR-0134 proposed with the scope below (the owner accepts it in his own commit; the
owner's "try it" approved the spike, not the decision text), the
how-to `docs/xdmod-manual/howto/co-design-change.rst`, and the canary scenario as PRs on branch
`feat/codesign` in robarm-syseng, robarm-me, robarm-ee and xdmod.

## Verdicts

| # | Question | Verdict |
|---|---|---|
| 1 | StepUp push FreeCAD -> KiCad (outline + holes) from a script | **Works.** `export_pcb` in the FreeCAD GUI binary offscreen, dialogs replaced by logging, the sketch put into the GUI selection and `start_time` set (globals of the GUI command). Parses the KiCad 10 file (`version 20260206`), replaces every `Edge.Cuts` item, writes outline and holes in the old s-expression style |
| 2 | Re-save by KiCad 10 | **Works** with `kicad-cli pcb upgrade --force` (without `--force` nothing happens: StepUp keeps the version header). The first re-save of the canary board also added `(thickness 0.15)` to four footprint texts |
| 3 | DRC after the push | **Works**, no new findings (the two accepted unconnected items stay) |
| 4 | Board model KiCad -> FreeCAD by StepUp (`onLoadBoard`) | **Cut.** It builds the board, then stalls after "placing board @ 0,0" (a shown widget, `raise()` offscreen); hit the limit twice (10 min, then 3 min with every `exec_` patched) |
| 5 | Board model by the scripted STEP path | **Works**: `kicad-cli pcb export step --user-origin 88x112mm` + `Import.insert` in `FreeCADCmd`: board 30 x 20 x 1.51 mm in the board frame, holes at (4, 4) and (26, 16) r 1.6, J1's pin holes at (7, 12) and (7, 9.46). Component bodies missing: the KiCad 3D models are not in `libs/kicad/packages3D` (board library, 5.29) |
| 6 | Keep-out zones | **Out (iteration 2).** StepUp can push them (`KeepOutZone` layer); the budget's box covers the space in iteration 1 |
| 7 | Connector positions | **In the budget, not pushed.** Values `<ref>X/Y` (pin 1); EE places connectors, a check compares |
| 8 | EE pushing back | **Out.** EE asks for a budget change on the same branch; the board model reaches FreeCAD by STEP (5.29) |
| 9 | Harness length and route | Length: a `SYS-IF` value the cable def conforms to (`EE-HAR` -> `SYS-IF`, curatrix accepts the pair now); not on the canary (its cable goes to a bench lead, no ME part). Route: iteration 2 |

## How it was run

StepUp: <https://github.com/easyw/kicadStepUpMod> at `3db98be23aae40413eab041f19de5ab2e168157e`
(upstream HEAD on 2026-11-17, StepUp 13.1.7), cloned to `.xdmod/stepup/kicadStepUpMod`, put on
`sys.path` by the push script only (not into FreeCAD's `Mod/`, so normal FreeCAD sessions do not
load it). **Licence gap:** the repo has no `LICENSE` file; AGPL-3.0 is only claimed in the README
and `package.xml` (which points to the missing file). Fine as a tool we run, not ship; it goes into
the StepUp licence record of 5.29.

Every run through curatrix, with `HOME` set for the FreeCAD process only:

```sh
eval "$(.venv/bin/curatrix env)"
curatrix run --use freecad -- env HOME=$PWD/.xdmod/stepup/home QT_QPA_PLATFORM=offscreen \
  XD_STEPUP=... XD_BOARD=... XD_SKELETON=... XD_RESULT=... FreeCAD xdmod/templates/codesign/stepup-push.py
```

StepUp wrote nothing into the sandboxed `HOME` (no `ksu-config.ini`; it writes only from its
preference dialog). It writes a backup `<board>-bkp-<time>.kicad_pcb-bak` next to the board copy
(the spike wrapper in `build/spike-codesign/scripts/` deleted it; with the how-to it stays in
`build/` and only the `.kicad_pcb` is copied back). Spike scripts and logs: `build/spike-codesign/` (`scripts/push.py`,
`run-push.sh`, `codesign-push.sh`, `step_in.py`; `out/*.json`, `out/drc-*.json`, `p1`..`p4`).

Coordinates: StepUp writes sketch point (x, y) as KiCad (x, -y) when the grid origin is not set,
so the script shifts the board-frame sketch by the anchor (grid origin if set, else the lower-left
corner of the old outline: (88, 112) on the canary).

## Model decisions (taken in this task)

- The budget is a port def in syseng with `default` values (a binding `=` cannot be restated:
  the Pilot reports "Cannot override a binding feature value").
- ME restates the values FreeCAD needs in its seat port def (`:>> hole2X = 24 [mm];`), because the
  upstream model is a stub in the ME export and `gen freecad-params` cannot read its values. These
  copies do not count toward the ten parameters (curatrix change in `meparams.py`); the placement
  of the seat does. The canary assembly has 15 parameters, 8 counted.
- EE: `dependency from CanaryBoard to CanaryBoardSpace` -> `EE-PCBA conforms SYS-IF` (curatrix
  change in `LINK_BY_KINDS`; the trace model already declared it). Not a port of the board: CK-F1
  would want a connector for it.

## Check idea for task 5.25: "board inside its space budget"

Per budget (`SYS-IF` that an `EE-PCBA` conforms to):
1. ME: the seat port def's restated values equal the budget's (model vs upstream `model.json`).
2. EE (plain Python, on the `.kicad_pcb`): the `Edge.Cuts` outline's bounding box is `width` x
   `depth`; the `Edge.Cuts` circles (or `MountingHole` footprints) equal the hole list within
   0.01 mm; each `<ref>X/Y` connector's pin 1 sits at its position in the board frame (anchor as
   in the push).
3. ME (FreeCAD, local): the board STEP placed at the seat's LCS fits the box (`heightAbove`,
   `heightBelow`) and does not collide with the direct children of the assembly (ME-7).

Start as warnings.

## Scenario run on the canary

The first change brought the budget, the seat and the first push (outline + holes). The scenario
then moved hole 2 from (26, 16) to (24, 16): budget value, seat value, `gen freecad-params`, push,
re-save, DRC, checks, one commit per repo on `feat/codesign`. See the PRs. The pushed board's diff
is the hole's two coordinates plus new UUIDs on all six `Edge.Cuts` items (StepUp rewrites them);
the push into a board already re-saved by KiCad (multi-line items) worked too.

## Open

- A `curatrix` command for the push (copy, push, re-save, DRC, copy back) and the StepUp pin in
  `tools.yaml` with `curatrix update` cloning it; until then the steps of the how-to.
- The 3D models of the KiCad libraries for the STEP export (5.29).
- StepUp's board load offscreen (iteration 2, only if EE pushing back is wanted).
- Owner decisions: accept XD-ADR-0134 (status `proposed`), and whether the budget values a seat
  restates (attributes redefining a `SYS-IF` budget attribute) stay out of the ten driving
  parameters of XD-ADR-0137 (`meparams.py` leaves them out; that interprets XD-ADR-0137).
- Exit criterion 4 (one co-design change through three repos on one branch name) is ready, not
  done: it is shown when xdmod#59, the manifest bump, robarm-syseng#10, robarm-me#12 and
  robarm-ee#15 are merged in that order.
