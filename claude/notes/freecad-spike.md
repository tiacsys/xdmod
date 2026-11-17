# FreeCAD 1.1 spike (task 5.13)

Agent spike, 2026-11-17, about 1.5 hours. FreeCAD 1.1.4 (Revision 45040), `FreeCADCmd` unless
noted. Input: the canary part `parts/canary-part.FCStd` (robarm-me, branch `feat/canary-c0`) and the
canary board `pcba/canary-board/canary-board.kicad_pcb` (robarm-ee, same branch). All files, scripts
and logs are under `build/spike-freecad/` (not committed): `scripts/` (the scripts named below),
`q1/` to `q7/` (documents and results), `out/` (logs).

## Summary

| # | Question | Verdict |
|---|---|---|
| 1 | Master sketch across documents | **Works with this fallback**: parameters and master sketch in a skeleton document, not in the top assembly document (else a document cycle); a script opens the top first and recomputes in order |
| 2 | Model drives CAD (script writes cells) | **Works**: 6 to 18 changed lines in `Document.xml`, 1 line per value in the semantic JSON, no object-ID churn |
| 3 | Configuration tables, presence by `Configs` | **Works** (one ordering pitfall); presence by `Configs` works, FreeCAD itself can also hide a link per variant |
| 4 | LCS with `Port`; collision check | **Works**; the semantic JSON needs small additions |
| 5 | Exploded view as a TechDraw view | **Works with this fallback**: the Assembly exploded view needs the GUI binary, and that run hung in 6 of 8 tries; a scripted exploded compound with a TechDraw view in `FreeCADCmd` worked 3 of 3 (view SVG, no page frame) |
| 6 | Version embossed at export | **Works**, source file unchanged (md5 checked) |
| 7 | KiCad StepUp | **Open**: not run. From the code: GUI binary only; the push and load functions take arguments but can open modal dialogs. The scripted test (`scripts/q7.py`) is the first step of 5.28 |
| 8 | MCP servers | **Cut for iteration 1**: not needed; two candidates named, not tried |

User-global FreeCAD config stayed untouched: see "Isolation" at the end.

## How FreeCAD was run

Every run used the workspace-local XDG dirs of `curatrix launch freecad` (under `.xdmod/freecad/`)
and the curatrix limits. The first pass set the `XDG_*` variables by hand, because the installed
curatrix did not set them for `curatrix run` then. Since xdmod#35 `limits.run` sets them itself for
the `freecad` use and every `FreeCAD*` command, so the evidence rerun used curatrix alone
(wrapper `build/spike-freecad/scripts/fc.sh`, all runs: `scripts/rerun.sh`):

```sh
QT_QPA_PLATFORM=offscreen .venv/bin/curatrix run --use freecad -- FreeCADCmd <script.py>   # or FreeCAD
```

FreeCAD confirmed the dirs in both binaries (`out/where.log`, `out/where-gui.log`):

```
XDCONFIG UserConfig .../ws-syseng/.xdmod/freecad/config/FreeCAD/v1-1/ UserAppData .../ws-syseng/.xdmod/freecad/data/FreeCAD/v1-1/ UserCache .../ws-syseng/.xdmod/freecad/cache/FreeCAD/v1-1/Cache/
GuiUp 1 UserConfig .../ws-syseng/.xdmod/freecad/config/FreeCAD/v1-1/ ... (same for the GUI binary)
```

The semantic JSON came from `curatrix.cad.freecad_trace` of xdmod `origin/main` (the code behind
`curatrix gen freecad-json`), called by `scripts/sem.py` under `curatrix run --use script`.

Found on the way (for curatrix, not changed here):

- Every save writes a backup `<name>.<timestamp>.FCBak` next to the file. `setup.py`
  (`FREECAD_USER_CFG` / `ensure_freecad_config`, run by `curatrix update` and `launch`) should also
  write `Document/CreateBackupFiles = false` into the workspace `user.cfg`; 5.23 adds `*.FCBak` to
  robarm-me's `.gitignore`.
- `FreeCADCmd` treats extra command-line arguments as files to open ("File format not supported").
  Pass script inputs by environment variables (`XD_VERSION=...`), as the scripts here do.
  `cad.freecad_shapes` is hit, but works today: it passes `script fcstd out.json`, and FreeCADCmd
  runs the script (which writes the JSON), then opens the `.FCStd` a second time, then tries to
  import the output `.json` as a FEM mesh and prints a traceback
  (`importYamlJsonMesh.py ... invalid literal for int() with base 10: 'bbox'`), with exit code 0
  (`out/freecad_shapes.log`, `out/freecad_shapes_by_hand.log`). It works only because of this order.
  Pass the paths by environment variables instead.
- `FreeCADCmd` exits with 0 when the script raises (`out/q5_cmd_fallback_no_template.log`:
  `Exception while processing file ... [Template not set for Page]`, `exit 0`). Every curatrix
  FreeCAD step must judge success by a result file it checks, not by the exit code.
- When a script raises, `FreeCADCmd` runs it a second time in the same process
  (`out/t_raise.log`: `RUN pid 1723555 document name twice`, then `... document name twice1`).
  Scripts must be safe to run twice (fresh output directory, no appends).
- A GUI FreeCAD killed by an outer `timeout` around `curatrix run` stays alive (curatrix's own
  `timeout 10m` child survives). Use curatrix's timeout only.

## 1. Master sketch across documents (ME-6)

**What I built** (`scripts/q1_build.py`, `q1/`): top document `asm-top.FCStd` with a spreadsheet
`Params` (aliases `servoMount_holeSpacing`, `servoMount_width`, `link1_length`) and a sketch
`MasterSketch` whose named constraints are driven by the aliases
(`sk.setExpression("Constraints.holeSpacing", "Params.servoMount_holeSpacing")`). A part document
`servo-mount.FCStd` (PartDesign body) takes dimensions from it in three ways:

- (a) cross-document expression to a cell: `asm_top#Params.servoMount_width` on a sketch constraint
- (b) cross-document expression to a master-sketch constraint:
  `asm_top#MasterSketch.Constraints.holeSpacing / 10` on the pad length
- (c) a `PartDesign::SubShapeBinder` of `MasterSketch`

and the top document links the part body (`App::Link`, with a `Configs` property).

**Results**

- Builds and recomputes headless; all objects valid. The part document must be **saved once before**
  a cross-document expression is set, else: `Exception ... [Owner document not saved]`.
- **Document cycle.** Top links part, part refers to top. Every save of the top prints
  `<Exception> Document::getDependentDocuments: The graph must be a DAG.` The save still works, but
  recompute order across documents is undefined in this case.
- **Propagation is not automatic in a fresh process.** Change the cells in the top (`q1_change.py`),
  save, then open only the part (`q1_check.py`):
  ```
  servo_mount#MasterBinder.Support: Time stamp changed on link asm_top#MasterSketch
  before recompute: width 60.0 mm pad 4.0 mm touched ['MasterBinder']
  recompute objects 2 width 60.0 mm pad 4.0 mm
  ```
  Only the binder is marked as changed; the cross-document expressions keep the old values. Opening
  the part first loads the top only partially:
  `Please reload partial document 'asm-top' for recomputation.`
- **What works** (`q1_recipe.py`): open the **top first** (it then loads the part fully through the
  link), write the cells, `recompute()` the top, then the part, save both. Re-opened afterwards:
  `width 90.0 mm pad 7.0 mm touched []`. Also works within one session (`q1_session.py`).
- **Without the cycle** (`q1b.py`, `q1b/`): `skeleton.FCStd` holds `Params` and `MasterSketch`; the part
  takes `skeleton#MasterSketch.Constraints.mountWidth`; the top links both the skeleton and the part.
  No DAG warning; open top, write cell, recompute skeleton, part, top: `plate length 75.0 mm`, and
  the placed link follows (`link bbox BoundBox (0, 20, 0, 75, 40, 4)`).

**How the reference looks.** In `Document.xml` of the part:

```xml
<ExpressionEngine count="1" xlink="1">
    <XLinks count="1" docs="1">
        <DocMap name="asm_top" label="asm-top" index="0"/>
        <XLink file="asm-top.FCStd" stamp="2026-11-17T02:32:19+01:00" name="Params"/>
    </XLinks>
    <Expression path=".Constraints.width" expression="asm_top#Params.servoMount_width"/>
</ExpressionEngine>
<Property name="Support" type="App::PropertyXLinkSubList">  <!-- the binder -->
    <XLink file="asm-top.FCStd" stamp="..." name="MasterSketch" sub=""/>
```

The link in the top: `<XLink file="servo-mount.FCStd" stamp="..." name="Body"/>` on `LinkedObject`.
References are by **relative file name** and **document name** (from the file name, `-` becomes `_`),
so renaming or moving a file breaks them. The `stamp` is the other file's last save time: every save
of the skeleton changes a line in every document that refers to it (see 2).

In the semantic JSON **none of this shows today**: `freecad_trace` drops expressions, and
`_prop_value` reads `Link` but not `XLink`, so `ServoMountLink` has no target, and the master sketch's
named constraints (`holeSpacing = 70`) are not listed. Only the spreadsheet values show.

**Input for 5.23 / 5.24**

- Put `Params` and the master sketch in `assemblies/<name>/skeleton.FCStd`; the top document links
  the skeleton and the parts. This keeps "master sketch at the top level" in spirit (one per top
  assembly, at most ten driving parameters) without a document cycle. If the owner wants it in the
  top document itself, parts may only take **placements** from it (expressions on the links in the
  top document), not dimensions.
- `curatrix gen freecad-params` must: open the top document first, write cells, recompute in
  dependency order (skeleton, parts, sub-assemblies, top), check `isValid()` everywhere, save all
  changed documents. Never open a part alone and trust its values.
- Parts that refer to the skeleton must be saved before the reference is made (`curatrix new part`
  saves first).
- File and document names are part of the reference: renames need a scripted "rename and fix
  references" step, or a rule "no renames".
- Extend `freecad_trace`: `XLink`, `XLinkSub`, `XLinkSubList` as `{file, object, sub}` without
  `stamp`; the `ExpressionEngine` as `{path: expression}`; named sketch constraints as
  `{name: value}`. Then CK-F3 can also check that a part really takes its value from the skeleton.

## 2. Model drives CAD (owner choice B)

`q1b.py "82 mm"` changed one cell in the skeleton (75 → 82 mm); diff of `Document.xml` before/after
(`q2/`):

| Document | Lines | Changed lines (`diff`, `<` + `>`) | What changed |
|---|---|---|---|
| `skeleton.FCStd` | 250 | 8 | `LastModifiedDate`, the cell, the constraint value, the sketch geometry end point |
| `servo-mount.FCStd` | 157 | 6 | date, the `stamp` of the XLink, the box length |
| `asm-top.FCStd` | 252 | 6 | date, two `stamp`s |

For the PartDesign variant (`q1/`, sketches and pad): `asm-top` 12 of 354 lines, `servo-mount` 18 of
760 lines. The `.brp` shape files inside the zip change too (binary).

Semantic JSON diff (the textconv view):

```
skeleton.json:     <  "servoMount_width": "75 mm"   >  "servoMount_width": "82 mm"
servo-mount.json:  <  "Length": 75.0                >  "Length": 82.0
asm-top.json:      (no change)
```

**Object-ID churn: none.** The `id="..."` attributes were compared before and after: 0 changes in
every document. The churn in freecad-storage.md §5 comes from rebuilding objects, not from writing
values.

Input for 5.24: B is fine. The writer should skip saving documents whose values did not change
(a stamp-only change is noise; the pre-commit warning "FCStd changed, JSON not" will catch it).

## 3. Variants: configuration tables and `Configs`

FreeCAD's "Configuration table" dialog writes a fixed pattern; done by script (`q3.py`, `q3/`):

```python
ps.set("A2", "short"); ps.set("B2", "=100 mm"); ps.set("C2", "1")   # one row per variant
ps.set("A3", "long");  ps.set("B3", "=140 mm"); ps.set("C3", "0")
ps.setAlias("B1", "link1_length"); ps.setAlias("C1", "gripper_present")   # row 1: current values
doc.recompute()                     # needed: cells must be computed before the Enum reads them
ps.addProperty("App::PropertyEnumeration", "Variant", "ConfigurationTable")
ps.setExpression(".Variant.Enum", "cells[<<A2:|>>]")
doc.recompute(); ps.Variant = "short"
ps.setExpression(".cells.Bind.B1.ZZ1",
    "tuple(.cells; <<B>> + str(hiddenref(Params.Variant) + 2); <<ZZ>> + str(hiddenref(Params.Variant) + 2))")
```

Pitfall: without the first `recompute()` the enumeration became `['None', 'None']` and setting
`Variant = "short"` failed.

Switching headless:

```
variant=short: link1_length=100.0 mm box=100.0 mm gripper_present=1 GripperLink.Visibility=True invalid=[]
variant=long:  link1_length=140.0 mm box=140.0 mm gripper_present=0 GripperLink.Visibility=False invalid=[]
```

It survives save and reopen (`q3_switch.py`: `reopened: variant long ... switched to short box 100.0 mm`).

Part presence: links carry `Configs` (`SYS-CFG-0001` / `SYS-CFG-0001, SYS-CFG-0002`); a filter in
the script gives `SYS-CFG-0002 links present: ['Link1Link']`. `Configs` already shows in the semantic
JSON `trace`. In addition, a link's `Visibility` accepts an expression (`Params.gripper_present == 1`),
so the FreeCAD view can follow the variant. Visibility is not presence: export and BOM must still
filter by `Configs`.

Semantic JSON gaps: bound row-1 cells show as `"link1_length": ".B3"` (the binding, not a value), and
the `Variant` property of the sheet is not shown at all.

Input for 5.24 / 5.26: the variant table lives in the skeleton's `Params` (rows = variants, columns =
aliases); `curatrix gen freecad-params` writes all rows; CK-F3 compares every row with the model, not
only the current one. `freecad_trace` should print the table as `{variant: {alias: value}}` plus the
active variant. Presence by `Configs` (as the review said); `Visibility` by expression is optional.
Export per variant: set `Params.Variant`, recompute, export, close without saving.

## 4. Interfaces (LCS with `Port`) and collision check

`q4.py` (`q4/`): in a copy of the canary part,

```python
lcs = part.addObject("Part::LocalCoordinateSystem", "LCS_mount")
lcs.Placement = App.Placement(App.Vector(20, 5, 2.5), App.Rotation(App.Vector(0, 1, 0), 90))
lcs.addProperty("App::PropertyString", "Port", "Trace"); lcs.Port = "ME-PORT-0001"
```

Semantic JSON: type `Part::LocalCoordinateSystem`, `placement` `{Px 20, Py 5, Pz 2.5, Q1 0.707107,
Q3 0.707107}`, and `Port` under `values` (not under `trace`, because `Port` is not in `TRACE_FIELDS`).

Collision, four links of the canary block in one assembly document:

```
common volume A ~ B_overlap: 250.0 mm3 COLLISION
common volume A ~ C_touch: 0.0 mm3 ok
common volume A ~ D_free: 0.0 mm3 ok
distToShape A~C_touch 0.0 A~D_free 30.0
```

`a.Shape.common(b.Shape).Volume` on links gives the placed shapes; touching faces give 0 (so "joined
parts may touch" is free). `distToShape` gives clearance.

Input for 5.24 / 5.25: add `Port` to `TRACE_FIELDS` (or a `ports` section). The LCS placement is
local to its part; the global placement is link placement × LCS placement, which curatrix can compose
in plain Python from the JSON. CK for collisions: pairs of direct children, filtered by `Configs`
per variant, volume above a small tolerance (for example 1e-3 mm³), library fasteners excluded.

## 5. Exploded view (time-box 1 hour, used about 25 minutes)

`q5.py` (`q5/`): an `Assembly::AssemblyObject` with two links of the canary block, an exploded view
with one move (`CommandCreateView.ExplodedView` / `ExplodedViewStep`, lid moved 30 mm in z), a
TechDraw page with a `DrawViewPart` whose `Source` is the exploded view object.

- `FreeCADCmd`: fails at the import, as the review found:
  `File "/usr/lib/freecad/Mod/Assembly/CommandCreateView.py", line 578 ... class TaskAssemblyCreateView(QtCore.QObject): NameError: name 'QtCore' is not defined`.
  A document that contains an exploded view opens in `FreeCADCmd` and recomputes, but the view's
  proxy is `None` (it prints the same error).
- **GUI binary, `QT_QPA_PLATFORM=offscreen`** (`FC_GUI=1 scripts/fc.sh q5.py`): worked in the first
  run and in try 6 of the rerun (`out/q5_gui_try6.result.log`):
  ```
  CommandCreateView imported
  exploded shape bbox BoundBox (0, 0, 0, 20, 10, 40) lid placement after (should be unchanged) Vector (0.0, 0.0, 5.0)
  plain view edges 14
  view valid True state ['Up-to-date'] edges 19
  page export [('page.svg', 15052), ('page.pdf', 4067)]
  ```
  TechDraw itself calls the exploded view's `getExplodedShape` (the parts are not moved in the
  document). The page shows the exploded view with the explosion line next to the plain view.
  Two things are needed: TechDraw computes hidden lines in a thread, so the script must wait
  (`Gui.updateGui()` and sleep until `view.getVisibleEdges()` is not empty, 0.5 s here), and the
  script must end with `os._exit(0)` (the GUI binary does not quit by itself).
- **But it is not reliable.** In 6 of 8 runs it hung after the TechDraw view was added
  (`out/q5_gui.log`, `q5_gui_try2..5,7,8`): a `faulthandler` dump shows the main thread stuck in
  `Gui.updateGui()` (and the same with `QCoreApplication.processEvents()`), line 45 of `q5.py`
  (`out/q5_gui_try4.stack.txt`, `q5_gui_try5.stack.txt`). A second FreeCAD running at the same time
  is not the cause (try 7 was clean and hung). Cause not found in the time-box.
- **Headless fallback that works** (`scripts/q5_cmd_fallback.py`, 3 of 3 runs,
  `out/q5_cmd_fallback_{1,2,3}.log`): the script builds the exploded compound itself (each part's
  shape at its placement plus its move, plus explosion lines), a `TechDraw::DrawViewPart` of it in
  `FreeCADCmd`, `TechDraw.viewPartAsSvg(view)`: `visible edges 19`, SVG of 1317 bytes, the same as
  the GUI result. A page needs a template, else `Template not set for Page`. This gives the view as
  SVG, not a full page (PDF) with frame.
- Not solved in the time-box: the page template frame did not show in the SVG export (only the
  views); the export with our own template (freecad-storage.md §4) was not tried here.

Input for 5.26 / 5.27: exploded view **in, by the fallback**: the moves are data (a small table per
assembly: link, offset; or read from the `Move` objects' `References` and `MovementTransform` in
`Document.xml`, which plain Python can do), `curatrix cam` builds the exploded compound and the
TechDraw view in `FreeCADCmd` and exports the view SVG. The Assembly workbench's exploded view in the
GUI binary is not reliable enough for CAM (6 of 8 hangs); the owner may still use it to design the
moves. Checks that run in `FreeCADCmd` must ignore the proxy error of exploded
views. Use `freecad` limits (it took a few seconds). **Open item for 5.26:** a full page with our
TechDraw template (frame and editable fields) exported by the GUI binary offscreen is not shown yet;
here the frame was missing from the SVG, and the GUI run hung in 6 of 8 tries. 5.26 starts by
showing that the page export works reliably (for example 10 runs in a row), or falls back to view SVGs.

## 6. Version on parts at export

`q6_mark.py` marks the face once (a design step, saved): an LCS `VersionMark` on the top face with
`Role = "version-emboss"` and `TextSize = 4`. `q6_export.py` at export time, without saving:

```python
ss = Draft.make_shapestring(String=version, FontFile=FONT, Size=float(mark.TextSize), Tracking=0)
ss.Placement = mark.Placement                     # then shrink the size to fit the mark's width
out = body.Shape.fuse(ss.Shape.extrude(App.Vector(0, 0, 0.6))).removeSplitter()
out.exportStep(...); Mesh ... write(".stl"); App.closeDocument(d.Name)   # not saved
```

```
XD_VERSION=v1.2.3-4-gabc1234: shapestring valid True faces 17 bbox BoundBox (2, 1.64469, 5, 18, 3.29687, 5)
RESULT body vol 1000.0 embossed vol 1003.13 solids 1 valid True
q6/canary-part.FCStd: OK          (md5sum -c of the source before and after)
```

Without fitting, the long string ran past the block and the result had 11 solids. Input for 5.26:
the mark is an LCS with `Role`, `TextSize` and a maximum width; the exporter fits the text, embosses
(or engraves with `cut`), and fails if the result is not exactly one valid solid. A fixed font file
pinned in xdmod (here `DejaVuSans.ttf` from the system). A `git describe` string gets small (1.6 mm
here); use the short tag on printed parts and the full string in the drawing.

## 7. KiCad StepUp (EE-5, P5-6)

- Repository: <https://github.com/easyw/kicadStepUpMod>, cloned to `build/spike-freecad/ext/`.
  HEAD `3db98be23aae40413eab041f19de5ab2e168157e` (2026-09-04); 31 commits in the last year, 705
  stars, 44 open issues, no releases or tags (`package.xml` version `11.09.6`).
- Licence: AGPL-3.0 per README and `package.xml`, but **the repo has no `LICENSE` file** (GitHub
  shows no licence; `package.xml` points to a missing `LICENSE`). Fine as a tool; record it.
- FreeCAD 1.1: README lists "0.19, 0.20, 0.21, 0.22, 1.0" and warns that the Addon Manager may fail on
  Linux from 1.0.1. 1.1 is not listed and was not tested (see "Not run" below). The repo is active
  in 2026 (commits in July to September), so 1.1 users are likely, but that is not proof.
- Workspace-local install: yes, by design of the XDG dirs: clone at a pinned commit into
  `.xdmod/freecad/data/FreeCAD/v1-1/Mod/kicadStepUpMod` (the `UserAppData` that FreeCAD reported),
  or add it to `sys.path` in a script. Two catches: it keeps its own config in **`~/ksu-config.ini`**
  (`home = expanduser("~")`, line 3026 of `kicadStepUptools.py`), so curatrix must set `HOME` to a
  workspace dir (absolute, under `.xdmod/`) **only for the StepUp process**, because `HOME` also
  changes what git, gh and ssh read (or patch that line); and it stores 87 preferences under
  `Mod/kicadStepUpGui` in the workspace `user.cfg`.
- Script use (from reading the code): `kicadStepUptools.py` (22 857 lines) imports `FreeCADGui`,
  `PySide.QtGui`, `ImportGui` and `pivy` at module level, so it **cannot load in `FreeCADCmd`**; only
  the GUI binary (offscreen). The core functions take arguments:
  - `onLoadBoard(file_name, load_models, insert)` loads a `.kicad_pcb` (skips the file dialog when
    `file_name` is given), but can open `QMessageBox.information` and a preferences dialog (`exec_()`)
    on warnings, which would block an offscreen run until the timeout.
  - `export_pcb(fname, sklayer, skname)` is the push: it writes a sketch (by name) into the given
    `.kicad_pcb` on a layer (`Edge.Cuts`, also keep-out and fill zones), replacing the old outline.
    The GUI command `PushPCB` only adds the selection and a file dialog around it. Warnings go through
    `say_warning`, a modal `QMessageBox`.
  - So both can be called from a script in the GUI binary, with the risk of a hidden modal dialog;
    a wrapper must time out (curatrix limits do) and could replace `say_warning` and
    `QMessageBox.information` with logging before the call.
- **Not run.** Running the cloned third-party workbench was blocked by the session's permission
  check, and the owner decides whether it runs. So the KiCad 10 file format (`version 20260206`) is
  untested with StepUp's parser. The test is written: `build/spike-freecad/scripts/q7.py` pushes a
  50 × 30 mm outline with two 3.2 mm holes into a copy of the canary board (replacing
  `say_warning` and `QMessageBox.information` by logging, so no dialog blocks), then loads the
  board back. The run command is in its header:
  ```sh
  mkdir -p .xdmod/stepup-home build/spike-freecad/q7
  cp .worktrees/feat/canary-c0/robarm-ee/pcba/canary-board/canary-board.kicad_pcb build/spike-freecad/q7/
  HOME=$PWD/.xdmod/stepup-home QT_QPA_PLATFORM=offscreen \
    .venv/bin/curatrix run --use freecad -- FreeCAD build/spike-freecad/scripts/q7.py
  ```

Input for 5.28 / 5.29: keep the review's split: the STEP path (`kicad-cli pcb export step`) for the
automated board model; StepUp for the interactive push ME → KiCad (outline and holes), run by a
person in `curatrix launch freecad`, or by a curatrix wrapper in the GUI binary offscreen with the
dialogs patched out, after the run above shows it works on a KiCad 10 board. `tools.yaml` pins the
commit; `curatrix update` clones it into `.xdmod/freecad/data/.../Mod/`; set `HOME` for the StepUp process only.
5.28 must start with that test (`q7.py`). The missing `LICENSE` file goes into the
StepUp licence record of 5.29.

## 8. MCP servers for FreeCAD

From GitHub (metadata by `gh api repos/<repo>`, 2026-11-17), the two candidates:

| Repo | Licence | Last push | Stars | What it does |
|---|---|---|---|---|
| [neka-nat/freecad-mcp](https://github.com/neka-nat/freecad-mcp) | MIT | 2026-11-16 | 3364 | FreeCAD addon starts an XML-RPC server in the GUI; MCP server as the Python package `freecad-mcp`; tools to create/edit objects, run code (`execute_code`, also `execute_code_headless` = `freecadcmd -c` in a separate process), screenshots. Tags up to `v0.1.32` |
| [spkane/freecad-addon-robust-mcp-server](https://github.com/spkane/freecad-addon-robust-mcp-server) | Apache-2.0 | 2026-11-16 | 271 | PyPI `freecad-robust-mcp` (0.5.0-beta) plus a bridge workbench; XML-RPC, socket, headless and embedded modes; 150+ tools (documents, PartDesign, export, macros) |

Rejected: bonninr/freecad_mcp (MIT, no push since 2025-03), jango-blockchained/mcp-freecad (MIT,
small, since 2025-11), contextform/freecad-mcp, theosib/FreeCAD-MCP-Server and
lucygoodchild/freecad-mcp-server (no licence on GitHub; the last one only makes primitives).

Pinned and workspace-local: yes for the first two. The addon part goes into
`.xdmod/freecad/data/FreeCAD/v1-1/Mod/` at a pinned tag (FreeCAD finds it there because of the XDG
dirs); the MCP part is installed with `pip install <package>==<version>` into the workspace `.venv` (not
`uvx`, which uses the user-global uv cache and tool dirs); the MCP server entry goes into the workspace `.claude/` settings, not the
user's. Both open a local port and give the agent arbitrary code execution inside FreeCAD, so the
FreeCAD started by `curatrix launch freecad` must run under the memory limit as today. Not tried here.

Verdict: cut for iteration 1, not needed: everything above works with plain scripts under
`curatrix run`, which are reviewable and repeatable. An MCP server helps an agent that works
interactively in the owner's running FreeCAD (inspect the model, screenshots). Candidate if wanted:
`neka-nat/freecad-mcp` (most used, MIT, active) or `spkane` (Apache-2.0, headless mode).

## Found later (tasks 5.23, 5.24)

- **Partial load of the skeleton.** The top document links only the part `Skeleton` of the skeleton.
  Opened through the top, FreeCAD loads the skeleton partially (`Document.Partial` is true) and
  `Params` is missing; a script that then looks for `Params` finds nothing. The writer of
  `gen freecad-params` opens the skeleton first, then the top, and stops when a document is still
  partial.
- **Document name clash.** FreeCAD names a document after its file (`skeleton.FCStd` -> `skeleton`),
  and a cross-document expression stores that name (`skeleton#MasterSketch...`, next to the file
  XLink). Every assembly with a `skeleton.FCStd` would open as `skeleton`. The skeleton is therefore
  `<name>-skeleton.FCStd` (proposed decision XD-ADR-0146).
- A cross-document link from a new document needs the document saved first (`Owner document not
  saved`), as for expressions.

## Input for 5.14 (decisions)

- ADR: per top assembly a `skeleton.FCStd` with `Params` (aliases `<port>_<attribute>`, the variant
  table) and the master sketch; parts refer only to the skeleton; no references from parts to the top
  document (no document cycles; a check can find `XLink file=` pointing to the top document).
- ADR: model drives CAD through one curatrix writer with the recompute order of 1; it writes values
  only, never rebuilds objects.
- ADR: variant = row of the configuration table + `Configs` on links; no suppression.
- ADR: full TechDraw pages and StepUp need the GUI binary with
  `QT_QPA_PLATFORM=offscreen`; checks, value writes and the exploded view (fallback of 5) use `FreeCADCmd`. Both through curatrix, which
  sets the workspace XDG dirs (xdmod#35); a test that `freecad_shapes` gets them would keep it so.
- `tools.yaml`: StepUp pinned by commit (role me, and ee for the board model if the owner keeps it),
  a pinned font for the version emboss; `doctor` checks both.
- `checks.md`: CK-F3 also over all variant rows; collision check by boolean common per variant;
  "one solid after emboss" in CAM.
- `freecad_trace` additions: `XLink*`, expressions, named sketch constraints, `Port`, the variant table.

## Evidence files

All under `build/spike-freecad/` (not committed). `scripts/rerun.sh` reruns everything with logs in
`out/<script>.log` (first line: the command, last line: `exit <code>`), under curatrix limits with the
workspace config. Logs: `where*.log` (the dirs), `q1_build/change/check/check2/session/recipe/
recipe_check.log`, `q1b_build/change.log`, `q3.log`, `q3_switch.log`, `q4.log`, `q5_cmd*.log`,
`q5_gui*.log` and `*.stack.txt`, `q5_cmd_fallback_*.log`, `q6_export.log`, `q6_md5_*.txt`,
`t_raise.log`, `freecad_shapes*.log`, `isolation-*.txt`. The `Document.xml` and JSON diffs of 2 are in
`q2/` and `q2pd/`. In the rerun `q1_recipe` was run after `q1_check2`/`q1_session`, so its "before"
state differs from the first pass; the results are the same (`plain recompute: width 90.0 mm pad 7.0 mm`).

## Isolation evidence

Before the first and after the last FreeCAD run:

```sh
find ~/.config/FreeCAD ~/.local/share/FreeCAD ~/.cache/FreeCAD -printf '%T@ %s %p\n' | sort -k3   # 18 entries
ls -la --time-style=full-iso ~/.config/FreeCAD ~/.local/share/FreeCAD ~/.cache/FreeCAD
```

Both outputs were identical (`find` listing md5 `5e694d863995b193715368c10c6893aa` before and after,
including `~/.config/FreeCAD/v1-1/user.cfg` at mtime `1794871415.85`, 20111 bytes). The same holds
for the evidence rerun with curatrix alone setting the dirs: `out/isolation-before.txt` and
`out/isolation-after.txt` are identical, md5 again `5e694d86...` (`out/isolation-diff.txt`). No
`~/ksu-config.ini` exists. All FreeCAD state went to `.xdmod/freecad/`.

## Follow-up in task 5.26: the TechDraw page in the GUI binary

5.26 tried the full TechDraw page (template, three views of the canary assembly) in the GUI binary
with `QT_QPA_PLATFORM=offscreen` (`curatrix run -m 4G -t 60s/90s -- FreeCAD page-gui.py`, copies of
the canary documents under `build/me-proto/`). Without `Gui.updateGui()` the run ended (3 of 3),
but the views had no edges (the hidden-line threads never delivered) and the exported PDF/SVG held
no views. With `Gui.updateGui()` in the wait loop it hung until the timeout (2 of 2, exit 124), as in
§5. So `curatrix cam` uses the fallback of XD-ADR-0137: the views come from `FreeCADCmd`
(`TechDraw.viewPartAsSvg`, a page with the default template only to hold them), and curatrix
composes the drawing sheet (frame, title block, views) as SVG and as a vector PDF in plain Python.
Our own TechDraw template with editable fields is not used yet.
