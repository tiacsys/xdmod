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
| 2 | Model drives CAD (script writes cells) | **Works**: 2 to 18 changed lines in `Document.xml`, 1 line per value in the semantic JSON, no object-ID churn |
| 3 | Configuration tables, presence by `Configs` | **Works** (one ordering pitfall); presence by `Configs` works, FreeCAD itself can also hide a link per variant |
| 4 | LCS with `Port`; collision check | **Works**; the semantic JSON needs small additions |
| 5 | Exploded view as a TechDraw view | **Works with this fallback**: only with the GUI binary offscreen, not with `FreeCADCmd` |
| 6 | Version embossed at export | **Works**, source file unchanged (md5 checked) |
| 7 | KiCad StepUp | **Works with this fallback** (from code reading only): GUI binary only, core push and load functions take arguments but can open modal dialogs; scripted use was not run (see 7) |
| 8 | MCP servers | **Works with this fallback**: two candidates can be pinned and run with the workspace-local config; not needed for iteration 1 |

User-global FreeCAD config stayed untouched: see "Isolation" at the end.

## How FreeCAD was run

Every run used the workspace-local XDG dirs of `curatrix launch freecad` and the curatrix limits
(wrapper `build/spike-freecad/scripts/fc.sh`):

```sh
env XDG_CONFIG_HOME=.xdmod/freecad/config XDG_DATA_HOME=.xdmod/freecad/data \
    XDG_CACHE_HOME=.xdmod/freecad/cache QT_QPA_PLATFORM=offscreen \
    .venv/bin/curatrix run --use freecad -- FreeCADCmd <script.py>     # or FreeCAD (GUI binary)
```

FreeCAD confirmed it used them (first lines of `q1_build.py`):

```
compression 0
UserAppData .../ws-syseng/.xdmod/freecad/data/FreeCAD/v1-1/ UserConfig .../ws-syseng/.xdmod/freecad/config/FreeCAD/v1-1/
```

The semantic JSON came from `curatrix.cad.freecad_trace` of xdmod `origin/main` (the code behind
`curatrix gen freecad-json`), called by `scripts/sem.py` under `curatrix run --use script`.

Found on the way (for curatrix, not changed here):

- `cad.freecad_shapes` (the shape part of `gen freecad-json`) starts `FreeCADCmd` with
  `ws.run_env()` only, so **without** the XDG dirs: it reads and writes the user's `~/.config/FreeCAD`.
  It must use `launch_env(ws, "freecad")` (or the same XDG dirs). The same holds for `curatrix run`.
- Every save writes a backup `<name>.<timestamp>.FCBak` next to the file. Set
  `Document/CreateBackupFiles = false` in the workspace `user.cfg`, and ignore `*.FCBak` in robarm-me.
- `FreeCADCmd` treats extra command-line arguments as files to open ("File format not supported").
  Pass script inputs by environment variables (`XD_VERSION=...`), as the scripts here do.
- When a script raises, `FreeCADCmd` printed the script's output twice and the second document got
  the name `asm_var1`: the script seems to run twice. Scripts must write into a fresh directory.

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
- **GUI binary, `QT_QPA_PLATFORM=offscreen`** (`FC_GUI=1 scripts/fc.sh q5.py`): works.
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
- Not solved in the time-box: the page template frame did not show in the SVG export (only the
  views); the export with our own template (freecad-storage.md §4) was not tried here.

Input for 5.26 / 5.27: exploded view **in**: the owner (or an agent in the GUI binary) defines the
moves in the assembly document; `curatrix cam` exports with the GUI binary offscreen, like the
full-page TechDraw export. Checks that run in `FreeCADCmd` must ignore the proxy error of exploded
views. Use `freecad` limits (it took a few seconds).

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
  workspace dir for StepUp runs (or patch that line); and it stores 87 preferences under
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
- **Not run.** My test (`scripts/q7.py`: push a 50 × 30 mm outline with two holes into a copy of the
  canary board, then load it back) was blocked by the session's permission check (running a cloned
  third-party workbench), so the KiCad 10 file format (`version 20260206`) is untested with StepUp's
  parser. The script is ready; the owner can run it:
  `HOME=build/spike-freecad/q7/home FC_GUI=1 build/spike-freecad/scripts/fc.sh build/spike-freecad/scripts/q7.py`

Input for 5.19 / 5.28: keep the review's split: the STEP path (`kicad-cli pcb export step`) for the
automated board model; StepUp for the interactive push ME → KiCad (outline and holes), run by a
person in `curatrix launch freecad`, or by a curatrix wrapper in the GUI binary offscreen with the
dialogs patched out, after the run above shows it works on a KiCad 10 board. `tools.yaml` pins the
commit; `curatrix update` clones it into `.xdmod/freecad/data/.../Mod/`; set `HOME` for it.
5.28 must start with that test.

## 8. MCP servers for FreeCAD

From GitHub (metadata by `gh api repos/<repo>`, 2026-11-17):

| Repo | Licence | Last push | Stars | What it does |
|---|---|---|---|---|
| [neka-nat/freecad-mcp](https://github.com/neka-nat/freecad-mcp) | MIT | 2026-11-16 | 3364 | FreeCAD addon starts an XML-RPC server in the GUI; MCP server via `uvx freecad-mcp`; tools to create/edit objects, run code (`execute_code`, also `execute_code_headless` = `freecadcmd -c` in a separate process), screenshots. Tags up to `v0.1.32` |
| [spkane/freecad-addon-robust-mcp-server](https://github.com/spkane/freecad-addon-robust-mcp-server) | Apache-2.0 | 2026-11-16 | 271 | PyPI `freecad-robust-mcp` (0.5.0-beta) plus a bridge workbench; XML-RPC, socket, headless and embedded modes; 150+ tools (documents, PartDesign, export, macros) |
| [bonninr/freecad_mcp](https://github.com/bonninr/freecad_mcp) | MIT | 2025-03-20 | 230 | addon + socket server, basic modelling; inactive |
| [contextform/freecad-mcp](https://github.com/contextform/freecad-mcp) | none | 2025-08-15 | 139 | automation server; no licence |
| [theosib/FreeCAD-MCP-Server](https://github.com/theosib/FreeCAD-MCP-Server) | none on GitHub (README says LGPL-2.1+) | 2026-03-05 | 37 | bridge to an addon over TCP 9876, for Claude Code |
| [jango-blockchained/mcp-freecad](https://github.com/jango-blockchained/mcp-freecad) | MIT | 2025-11-06 | 27 | general server |
| [lucygoodchild/freecad-mcp-server](https://github.com/lucygoodchild/freecad-mcp-server) | none | 2025-06-02 | 9 | Node server, primitives only |

Pinned and workspace-local: yes for the first two. The addon part goes into
`.xdmod/freecad/data/FreeCAD/v1-1/Mod/` at a pinned tag (FreeCAD finds it there because of the XDG
dirs); the MCP part runs from the workspace venv (`pip install freecad-robust-mcp==<ver>` or
`uvx freecad-mcp@0.1.32`); the MCP server entry goes into the workspace `.claude/` settings, not the
user's. Both open a local port and give the agent arbitrary code execution inside FreeCAD, so the
FreeCAD started by `curatrix launch freecad` must run under the memory limit as today. Not tried here.

Verdict: not needed for iteration 1: everything above works with plain scripts under
`curatrix run`, which are reviewable and repeatable. An MCP server helps an agent that works
interactively in the owner's running FreeCAD (inspect the model, screenshots). Candidate if wanted:
`neka-nat/freecad-mcp` (most used, MIT, active) or `spkane` (Apache-2.0, headless mode).

## Input for 5.14 (decisions)

- ADR: per top assembly a `skeleton.FCStd` with `Params` (aliases `<port>_<attribute>`, the variant
  table) and the master sketch; parts refer only to the skeleton; no references from parts to the top
  document (no document cycles; a check can find `XLink file=` pointing to the top document).
- ADR: model drives CAD through one curatrix writer with the recompute order of 1; it writes values
  only, never rebuilds objects.
- ADR: variant = row of the configuration table + `Configs` on links; no suppression.
- ADR: CAD output (exploded views, full TechDraw pages, StepUp) needs the GUI binary with
  `QT_QPA_PLATFORM=offscreen`; checks and value writes use `FreeCADCmd`. Both through curatrix with the
  workspace XDG dirs (fix `freecad_shapes` and `curatrix run` first).
- `tools.yaml`: StepUp pinned by commit (role me, and ee for the board model if the owner keeps it),
  a pinned font for the version emboss; `doctor` checks both.
- `checks.md`: CK-F3 also over all variant rows; collision check by boolean common per variant;
  "one solid after emboss" in CAM.
- `freecad_trace` additions: `XLink*`, expressions, named sketch constraints, `Port`, the variant table.

## Isolation evidence

Before the first and after the last FreeCAD run:

```sh
find ~/.config/FreeCAD ~/.local/share/FreeCAD ~/.cache/FreeCAD -printf '%T@ %s %p\n' | sort -k3   # 18 entries
ls -la --time-style=full-iso ~/.config/FreeCAD ~/.local/share/FreeCAD ~/.cache/FreeCAD
```

Both outputs were identical (`find` listing md5 `5e694d863995b193715368c10c6893aa` before and after,
including `~/.config/FreeCAD/v1-1/user.cfg` at mtime `1794871415.85`, 20111 bytes). No
`~/ksu-config.ini` exists. All FreeCAD state went to `.xdmod/freecad/`.
