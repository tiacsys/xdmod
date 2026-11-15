# Research 1.5 — FreeCAD in the framework

Author: research agent 1.5 · Date: 2026-11-14 · Tool on this machine: **FreeCAD 1.1.4** (Arch package `freecad 1.1.4-3`,
OCCT 7.9, Python 3.14), binaries `/usr/bin/FreeCADCmd`, `/usr/bin/freecad`, plus `/usr/bin/fcinfo`.

Legend: **[verified]** = I ran it on this machine. **[read]** = from docs or web pages only, not tested.

All hands-on scripts and outputs are in
`/tmp/claude-1000/-home-tobias-z-wrk-ws-syseng/cc4a5268-5423-4e94-be0d-4c1055bbe07f/scratchpad/research-freecad/`
(`scripts/` and `out/`). That folder is temporary; copy the scripts into the framework repo in Phase 2/4 if wanted.

---

## Summary

- **Headless FreeCAD works well for the model side** [verified]. `FreeCADCmd` built a sketch + pad part whose size is
  driven by spreadsheet aliases, added custom trace properties, saved, re-opened, changed a parameter, and exported
  **STL, 3MF, STEP, OBJ and glTF/GLB**. STL and 3MF output was byte-identical across two runs.
- **Trace IDs (D29) fit FreeCAD well** [verified]. Custom properties (`App::PropertyString` / `App::PropertyStringList`
  in a property group `Trace`) on `App::Part` and `PartDesign::Body` survive save/load. They are plain text in
  `Document.xml`, so a **50-line pure-Python script reads them without FreeCAD**. That means trace extraction can run in
  GitHub CI today, even under D47.
- **TechDraw drawings need a GUI process, but no display** [verified]. In `FreeCADCmd` only DXF and bare view
  fragments export. Full-page **SVG and PDF** worked with `freecad` + `QT_QPA_PLATFORM=offscreen` (no X server, no
  Xvfb), with a small wait loop and a hard exit at the end.
- **Git stamping without a dirty tree works** [verified]: open the file, write `git describe` into the template's
  `EditableTexts`, export, close **without saving**. The `.FCStd` SHA-1 stayed the same. The stock ISO template field
  for the revision is too narrow for a `git describe` string; we need our own template.
- **Storage/review (D41):** a zip `.FCStd` is opaque on GitHub. Plain `Document.xml` diffs are readable but noisy.
  The best value is a **semantic text diff** (parameters, trace IDs, objects, volume) plus **rendered drawing/image
  diffs** posted by a check. Recommended: keep `.FCStd` with compression level 0, add a git `textconv`, and generate a
  review report. Storing only `Document.xml` as text is technically possible (verified: FreeCAD rebuilds the geometry
  from it) but needs custom tooling — keep it as a later option.
- **Prior art is thin.** No maintained FreeCAD↔Sphinx(-needs) bridge exists. Closest pieces: **FCBot** (KiBot-like
  CI exporter, MIT, small), **GitCAD** (uncompressed storage via git filters, MIT), **History Workbench** (visual and
  structural diff inside FreeCAD, LGPL, early), **sphinxcontrib-cadquery** (CadQuery models in Sphinx). We must build
  our own small Sphinx extension (fits D34).
- **Agents can author FreeCAD parts via Python** [verified for a simple part]. The validation API is good:
  `isValid()`, solid count, volume, bounding box, `common()` for interference, mesh checks. Several FreeCAD MCP servers
  exist (neka-nat/freecad-mcp is the largest), but they drive a running GUI. For our flow a **script run by
  `FreeCADCmd` is simpler and reproducible**.
- **Parameter exchange:** spreadsheet aliases are easy to set and read by script and also readable from
  `Document.xml` without FreeCAD. Recommended direction: **check, not generate** in iteration 1 (SysML value ⇄
  spreadsheet alias, compared by a check), with a "sync" script as the fix action.
- **Small surprises:** the document default licence is "All rights reserved" (set it per file); `fcinfo` shows only
  the last item of a string list (bug); glTF export in `FreeCADCmd` is empty unless shapes are tessellated first.

---

## Findings

### 1. Prior art

| Project | What it does | Licence | Maturity | Notes |
|---|---|---|---|---|
| **FCBot** — https://github.com/asymworks/fcbot | KiBot-style YAML config; exports STEP, STL, TechDraw PDF, screenshots; GitHub Action `asymworks/fcbot@v0` + Docker image `ghcr.io/asymworks/fcbot` | MIT | small (≈15 commits, 4 stars), FreeCAD 1.0 | [read] Good model for a later Docker/CI step. No SVG, no BOM, no revision stamping. |
| **GitCAD** — https://github.com/MikeOpsGit/GitCAD | Git clean filter + hooks store an **unzipped** copy of each `.FCStd`; binaries (`.brp`, maps, thumbnails) go into zips in Git LFS; own lock files | MIT | medium (≈700 commits, 39 stars, no releases) | [read] Heavy: hooks, LFS, locks, special `git` commands. |
| **History Workbench** (eblanshey, page found at DiffCAD URL) — https://github.com/eblanshey/DiffCAD | Inside-FreeCAD visual diff (changed geometry coloured) and structural/property diff; uses git internally | LGPL-2.1 | early, FreeCAD 1.1+, ≈170 stars | [read] Good for a human reviewing locally, not for a PR page or an agent. |
| **fcinfo** (ships with FreeCAD) — https://wiki.freecad.org/Arch_Git | Text report of an `.FCStd`; documented as a git `textconv` | LGPL | old, part of FreeCAD | [verified] Works. Noisy (temp path, SHA1, dates) and **bug: shows only the last entry of a StringList**. |
| **freecad-ci-tools** — https://github.com/maltfield/freecad-ci-tools | One script: `.FCStd` → PNG for PR comments | GPL-3.0 | tiny (10 commits) | [read] Idea is right, tool is minimal. |
| **OSE workbench Sphinx ext** — https://ose-workbench-platform.readthedocs.io/en/stable/osewb/osewb.docs.ext.html | Directive that tables the properties of scripted FreeCAD objects (for *code* docs) | — | niche | [read] Not about design data. |
| **sphinxcontrib-cadquery** — https://sphinxcontrib-cadquery.readthedocs.io | `cadquery-vtk` (3D in browser via vtk.js) and `cadquery-svg` directives | Apache-2.0 | maintained fork of CadQuery's own ext | [read] Shows the pattern we want: "model source → view in docs". |
| **sphinxstl** — https://github.com/Peque/sphinxstl | `stl` directive for Sphinx | BSD-3 | old, small | [read] |
| **solid-node** — https://solid-node.readthedocs.io | three.js viewer + Sphinx directive for its STL exports | — | small | [read] |
| **FreeCAD Continuous Integration wiki** — https://wiki.freecad.org/Continuous_Integration | CI of FreeCAD itself, not of models | — | — | [read] |

**Verdict:** nobody bridges FreeCAD to sphinx-needs. The pieces we need are small: (a) a FreeCAD export script,
(b) a pure-Python `.FCStd` reader, (c) a Sphinx extension that turns the reader output into needs and embeds
SVG/GLB. FCBot is the best reference for config shape and for the later Docker image.

### 2. Doc extraction (D22)

- **Headless scripting** [verified]: `FreeCADCmd script.py` runs any Python with `FreeCAD`, `Part`, `PartDesign`,
  `Sketcher`, `Spreadsheet`, `Mesh`, `Import`, `TechDraw` (App part). Arguments go in via environment variables
  (simplest). FreeCAD also prints progress noise to stdout; write results to files, not stdout.
- **Isolated preferences** [verified]: `FreeCADCmd -u <tmp>/user.cfg -s <tmp>/system.cfg` plus `XDG_CONFIG_HOME`,
  `XDG_DATA_HOME`, `XDG_CACHE_HOME` pointing to a temp folder. No global user settings were touched. Use this in the
  framework's wrapper so checks are reproducible.
- **TechDraw** [verified]:
  - In `FreeCADCmd`: `TechDraw.writeDXFPage(page, file)` works (views only, no template text). `TechDraw.viewPartAsSvg(view)`
    gives a bare SVG fragment per view. There is **no full-page SVG/PDF export in App mode**.
  - Full page: `TechDrawGui.exportPageAsSvg(page, file)` and `exportPageAsPdf(...)` in a **GUI process**.
    It worked with `QT_QPA_PLATFORM=offscreen freecad script.py` after: activating the TechDraw workbench,
    `page.ViewObject.doubleClicked()` (opens the page scene), waiting until `view.getVisibleEdges()` is non-empty
    (hidden-line removal runs in threads), then exporting and calling `os._exit(0)` (normal GUI shutdown hung in offscreen
    mode). Without opening the page view the SVG was empty.
  - Output SVG renders fine with `rsvg-convert` → PNG, and embeds directly in Sphinx (`.. image:: x.svg`).
  - Templates: the stock ISO templates have `freecad:editable` fields (`drawing_number`, `revision_index`,
    `date_of_issue`, `title`, `part_material`, …) — see §4.
- **Spreadsheet parameters** [verified]: `sheet.set("B1","80 mm"); sheet.setAlias("B1","link_length")`, used in
  sketch constraints by `sk.setExpression("Constraints[i]", "Params.link_length")` and in features by
  `pad.setExpression("Length", "Params.thickness")`. Read back with `sheet.get("link_length")`. In `Document.xml`
  each alias is a `<Cell address=… content="=80 mm" alias="link_length"/>` → readable without FreeCAD.
- **Assembly structure** [read]: FreeCAD 1.0 added a built-in **Assembly workbench** (Ondsel solver); 1.1
  (released 2026-03-24) added "insert new part", simulation, and **BOM with chosen properties** (PR #20732), see
  https://wiki.freecad.org/Release_notes_1.1. The BOM property columns could carry our `TraceId`. Assembly4 and A2plus
  are add-ons; with a built-in workbench in 1.x there is no reason to use them for new work. Assembly structure is
  readable by walking `App::Part` / `App::Link` / `Assembly::AssemblyObject` groups in Python; I did not test assemblies
  hands-on.
- **3D views for HTML** [verified export, read viewer]: `Import.export([obj], "x.glb")` works in `FreeCADCmd` **only
  after `obj.Shape.tessellate(0.05)`**; otherwise the glTF has nodes but no meshes. The GLB can be shown with Google's
  `<model-viewer>` web component (Apache-2.0, https://modelviewer.dev) via a tiny custom directive or raw HTML. No
  existing Sphinx directive for glTF found; sphinxstl/solid-node do STL with three.js.

### 3. Trace IDs on objects (D29)

[verified] Script:

```python
part.addProperty("App::PropertyString", "TraceId", "Trace", "Framework trace ID"); part.TraceId = "ME-PRT-0001"
part.addProperty("App::PropertyStringList", "Satisfies", "Trace", "..."); part.Satisfies = ["ME-REQ-0003", "ME-REQ-0007"]
```

- Works on `App::Part`, `PartDesign::Body` and any other object. Property group `Trace` makes them easy to find
  (`getGroupOfProperty`). Users can add/edit the same properties in the GUI (property editor → "Add property").
- Note: `App::Part` already has a `Material` property in 1.1 — pick names that do not clash (I used `PrintMaterial`).
- In `Document.xml`:
  `<Property name="TraceId" type="App::PropertyString" group="Trace" …><String value="ME-PRT-0001"/></Property>`.
- **Reading without FreeCAD** [verified]: `scripts/fcstd_extract.py` (zipfile + ElementTree, ~50 lines) prints JSON
  with all `Trace`-group properties per object and all spreadsheet aliases. A Sphinx extension can turn this into
  needs (`type: me_part`, `id: ME-PRT-0001`, links `satisfies: [...]`), or write `needs.json` directly. This runs in
  GitHub CI without FreeCAD, so D47 does not block ME trace checks.
- Per D5 the part (concrete) holds the link to the requirement (`Satisfies`). Backlinks are computed by sphinx-needs.
- Each object also has an internal `Uid` (UUID) in 1.x; it could serve as a stable anchor if a label is renamed, but
  the human trace ID should remain the key.

### 4. Git version in TechDraw frames

[verified] `scripts/drawing.py`:

```python
texts = page.Template.EditableTexts            # dict: field name -> text
texts["revision_index"] = os.environ["GIT_REV"] # e.g. `git describe --always --dirty`
texts["drawing_number"] = part.TraceId
page.Template.EditableTexts = texts
doc.recompute(); TechDrawGui.exportPageAsSvg(page, out)   # then close WITHOUT saving
```

- The `.FCStd` SHA-1 was identical before and after (`25ed7de…`), so the working tree stays clean. The SVG and PDF
  contained `v0.1.0-3-gabc1234` and `ME-PRT-0001` (checked with `grep` and `pdftotext`).
- Rule for the framework: **template fields that come from git are only set at export time**. In the committed file
  they hold a placeholder (e.g. `$GIT_REV`). A check can verify the placeholder is still there.
- Problem found: in the stock `A4_Landscape_ISO5457_minimal.svg` the `revision_index` box is too small;
  `v0.1.0-3-gabc1234` overflowed into the next box. We should ship **our own template** (SVG, editable fields with
  `freecad:editable="git_rev"` etc.) with a wide revision/version field. Templates are plain SVG — easy to version.
- For a dirty tree, `git describe --dirty` makes the stamp honest.

### 5. Storage and review (D41)

What I measured [verified], FreeCAD 1.1.4, simple part, saved by script:

- An `.FCStd` holds `Document.xml` (63 kB here), `StringHasher.Table.txt`, `*.Shape.brp` (OCC BRep, **text** by
  default: `SaveBinaryBrep=false`), `*.Map.txt` (topological naming maps). A GUI save also adds `GuiDocument.xml`
  (colours, visibility) and `thumbnails/Thumbnail.png` [read: https://wiki.freecad.org/File_Format_FCStd].
- **Compression level 0** (`Preferences/Document/CompressionLevel = 0`; user setting) still writes a zip with
  deflate entries but stores the data uncompressed (86 kB vs 11 kB). Git's delta compression works better on this.
  It does not change what GitHub shows: still "Binary file".
- **No "save as folder" in FreeCAD 1.1.** I found no such option in the binaries or docs. `Std_ProjectUtil`
  (Tools menu) can extract a file and rebuild it, by hand. [read + strings check]
- **Noise in `Document.xml`:**
  - Open + save with no change → 7 changed lines (Label, LastModifiedDate, `status` attributes, a last-digit float
    change in a quaternion, an `AttacherEngine` enum).
  - Change one parameter (80 → 95 mm) → 24 changed lines: the same noise + the spreadsheet cell + the sketch constraint
    + 3 sketch geometry lines. Readable, but a reviewer must know what to ignore.
  - Two *fresh* builds from the same script differ in object `id`s, UUIDs and map files → scripts that rebuild a
    file from scratch create big diffs. Prefer "open, change, save".
- **Opening a `Document.xml`-only file works** [verified]: I zipped only `Document.xml` into an `.FCStd`; FreeCAD
  opened it and a recompute rebuilt the body (volume 3840 mm³, valid). So the geometry caches (`.brp`, maps) are not
  needed to restore a simple PartDesign model. Unknown for complex models with topological-naming-dependent
  references and for Assembly solver state.

**git textconv** [verified] in a test repo (`gitdemo/`):

| Option | What `git diff` shows for "link_length 80 → 95 mm" |
|---|---|
| none | `Binary files differ`, `Bin 86405 -> 86491 bytes` |
| `textconv = unzip -p $1 Document.xml` | 24 XML lines, signal + noise |
| `textconv = fcinfo` | per-object properties; noise from temp path, SHA1, dates; StringList bug |
| `textconv = fcstd_extract.py` (our semantic JSON) | **one line**: `- "link_length": "80 mm"` / `+ "95 mm"` |

Limits: `.gitattributes` is committed, but the `diff.fcstd.textconv` driver must be set in each clone's git config
(a setup step in the repo's check command or west). **GitHub's PR web view ignores textconv**, so human reviewers on
GitHub see "binary" unless CI posts a report.

**Options ranked for D41** (what a PR reviewer sees):

1. **Keep `.FCStd` (compression 0) + generated review report** — *recommended*. A local check (and later CI, when the
   Docker image exists) produces for each changed `.FCStd`: semantic diff (parameters, trace properties, object
   list, volume/bbox per body, validity), the exported drawing SVG, and a before/after **image diff** (verified:
   `rsvg-convert` + `magick compare` marks changed edges in red). Humans see a PR comment/artifact with images; agents
   read the JSON/text diff; locally `git diff` works via textconv. Low tooling cost, FreeCAD stays the source of truth,
   GUI users work normally. Note: under D47 the FreeCAD-dependent parts (drawings, image diff) run locally in
   iteration 1; the semantic diff runs in GitHub CI since it needs no FreeCAD.
2. **Parts as Python scripts (`FreeCADCmd`-generated `.FCStd` as build output)** — reviewer sees a normal code diff,
   which is the best review experience and best for agents. Cost: human engineers lose GUI editing (edits in GUI are
   overwritten), and fresh builds are not byte-stable (ids/UUIDs) — so the `.FCStd` should not be committed at all.
   Good for **simple parametric parts** (links, brackets, servo mounts); poor for organic work and drawings with manual
   dimension placement. Can be mixed with option 1 per part.
3. **Unzipped storage (GitCAD-style, or our own "Document.xml + GuiDocument.xml only")** — reviewer sees XML diffs in
   GitHub directly. Cost: git filters/hooks, LFS or regenerate caches, risk with complex models, and still noisy XML.
   Keep as a later option if option 1's report is not enough.
4. **CadQuery / build123d instead of FreeCAD** — code review like option 2, strong Sphinx tooling
   (sphinxcontrib-cadquery). But the mission brief names FreeCAD as the ME tool; use them only as a comparison, not
   as a replacement.
5. **Plain `.FCStd` with no help** — "Binary files differ". Not acceptable for D3.

### 6. Agent authoring

- [verified] An agent (me) wrote a working parametric part script in a few tries. Errors met: `App::Part` already has
  `Material`; TechDraw view list is nested inside the projection group; GUI export needs the page opened and a wait.
  These are the kinds of API traps an agent skill file should list.
- Validation API [verified]: `shape.isValid()`, `isClosed()`, `len(shape.Solids)`, `Volume`, `BoundBox`;
  interference `a.common(b).Volume` (gave 480 mm³ for an overlapped copy) and `a.distToShape(b)`; mesh checks
  `MeshPart.meshFromShape(...)` → `isSolid()`, `hasNonManifolds()`, `hasSelfIntersections()`; document health
  `obj.State` contains `Invalid`/`Error` after `recompute()`. These make good **pass/fail checks** for agent edits and
  for the local check command (D46): "all bodies valid, one solid each, no interference in the assembly, parameters
  equal to SysML values".
- MCP servers [read]: **neka-nat/freecad-mcp** (MIT, ~3.3k stars; addon runs an RPC server inside the FreeCAD GUI;
  create/edit objects, run Python, screenshots) https://github.com/neka-nat/freecad-mcp;
  **theosib/FreeCAD-MCP-Server** (LGPL-2.1, TCP 9876) https://github.com/theosib/FreeCAD-MCP-Server;
  **freecad-robust-mcp** on PyPI https://pypi.org/project/freecad-robust-mcp/. All drive a *running GUI*; useful for
  interactive work and screenshots, not needed for CI or reproducible edits. Recommendation: agents edit through
  **scripts run with `FreeCADCmd`** ("open, change via API, recompute, validate, save"), never by editing
  `Document.xml` text by hand.

### 7. CAM feasibility (D30)

[verified] `Mesh.export([body], "x.stl")` (binary STL) and `Mesh.export([body], "x.3mf")` work in `FreeCADCmd`.
The 3MF is a valid 3MF zip (`3D/3dmodel.model`, unit millimetre). Output was byte-identical across two runs
(the zip entry timestamps inside 3MF follow the clock, so across different minutes the 3MF bytes will differ — the
bundle tool should hash STL or the 3MF *model* XML, or normalise timestamps). STEP export via `Import.export` also
works (contains a timestamp in its header). Mesh tolerance can be set with `MeshPart.meshFromShape(LinearDeflection=…)`
before export. Print-settings profile (D30) is outside FreeCAD (slicer profile file) — iteration 2.

### 8. Parameter exchange (SysML ⇄ FreeCAD)

- Spreadsheet aliases are the right interface: named, unit-aware (`"80 mm"`), used by expressions everywhere. [verified]
- **Reading** is possible without FreeCAD (from `Document.xml`) [verified], so a GitHub CI check can compare SysML
  attribute values (e.g. `attribute linkLength = 80 [mm]`) with spreadsheet aliases. Convention needed: one alias name
  per SysML attribute (e.g. alias = SysML qualified name with `_`), and units normalised.
- **Writing** needs FreeCAD (set alias, recompute, save) [verified]. Recommended for iteration 1: **check, not
  generate**. A `sync-params` script (run locally by a human or agent) writes the SysML values into the sheet and
  recomputes; the check fails if they differ. This keeps the CAD file the owner of its geometry and fits D5 (the
  concrete artifact holds the link). Optionally mark synced cells (e.g. a comment/column "from SysML: <id>").
- Servo envelope (SG90 dimensions) should be a sheet or a separate reference part with its own trace ID, used by the
  servo mount via expressions or a shape binder.

---

## Hands-on results (exact)

Wrapper (isolated config; no global preferences changed):
`scripts/fc.sh` = `XDG_*` → scratch, `exec FreeCADCmd -u <scratch>/cfg/user.cfg -s <scratch>/cfg/system.cfg "$@"`;
`scripts/fcgui.sh` = same with `FreeCAD`.

| # | Command | Result |
|---|---|---|
| 1 | `which freecadcmd FreeCADCmd freecad` | all present → `/usr/lib/freecad/bin/`; version 1.1.4 (R45040) |
| 2 | `OUT=out/c3 COMPRESSION=3 fc.sh make_part.py` | ✅ sketch+pad body from sheet aliases, `valid True, 1 solid, 3840 mm³, bbox 80×12×4`; saved; reopened; `TRACE Link1 App::Part ME-PRT-0001 ['ME-REQ-0003','ME-REQ-0007']`; changed alias → bbox 95; STL, 3MF, STEP written. First try failed: custom `Material` clashes with 1.1's built-in property. |
| 3 | same with `COMPRESSION=0`, twice | ✅ zip entries stored uncompressed (86 kB). STL and 3MF byte-identical; `Document.xml` differs in object ids/UUIDs; map/hasher files differ. |
| 4 | `edit_part.py` no change / `NEWLEN="95 mm"` | ✅ diffs: 7 noise lines / 24 lines (noise + real change) |
| 5 | `fcinfo file.FCStd` | ✅ readable report; **StringList shows only last element** |
| 6 | `python3 -I fcstd_extract.py file.FCStd` (no FreeCAD) | ✅ JSON of trace props + aliases |
| 7 | git repo + `.gitattributes *.FCStd diff=fcstd` + 3 textconv drivers | ✅ see table in §5 |
| 8 | `fc.sh drawing.py` (FreeCADCmd) | ⚠️ DXF ok, per-view SVG fragments only; no page SVG/PDF; `DrawPage` has no `isTouched()` |
| 9 | `QT_QPA_PLATFORM=offscreen fcgui.sh drawing.py` | first: empty SVG (page view not opened), then hang at exit; final version ✅ SVG 14 kB + PDF 14 kB with ISO A4 frame, 3 views, `drawing_number=ME-PRT-0001`, `revision_index=v0.1.0-3-gabc1234`; `.FCStd` SHA-1 unchanged; revision text overflows its box |
| 10 | `rsvg-convert` + `magick compare` on 80 mm vs 95 mm drawing | ✅ diff PNG with changed edges and stamp in red |
| 11 | `gltf.py`: `Import.export` → .glb/.gltf | ⚠️ files written but **no meshes**; after `Shape.tessellate(0.05)` ✅ 3.2 kB GLB with mesh |
| 12 | shape checks | ✅ `isValid`, `common().Volume=480` for overlap, mesh solid, no non-manifolds |
| 13 | zip with only `Document.xml` → open + recompute | ✅ body rebuilt, valid, same volume |
| 14 | `pip install build123d` in a scratch venv (system Python 3.14) | ❌ not finished after >3 min (likely no prebuilt OCP wheel for Python 3.14, so pip tried a source build); stopped. Not tested. It would need Python 3.12 (present at `~/.local/bin/python3.12`). Comparison only, so not pursued. |

---

## Recommendations

1. **D41 (ranked):** (1) `.FCStd` with compression level 0 + git textconv using our semantic extractor + a generated
   review report (semantic diff, drawing SVG, image diff); (2) for simple parametric parts allow "part = Python script,
   `.FCStd` is a build output"; (3) unzipped storage only if (1) proves too weak; (4) CadQuery/build123d only for
   comparison. Never rely on GitHub's raw diff of `.FCStd`.
2. **Framework tool `fcstd_extract.py` → Sphinx extension** (in the framework repo, D34): reads `.FCStd` without
   FreeCAD, emits needs for parts (`TraceId`, `Satisfies`, material, key parameters) and a parameter table.
   Runs in GitHub CI under D47.
3. **Framework tool `fc-export`** (local in iteration 1, CI later): wrapper with isolated config; per `.FCStd`:
   drawing SVG (git-stamped, not saved), GLB (tessellated) for a `<model-viewer>` directive, STL/3MF (D30 later),
   validity/interference checks. Config file per repo (FCBot's YAML shape is a good model).
4. **Own TechDraw template** with fields `trace_id`, `git_rev`, `git_date`, wide enough for `git describe`.
   Committed files keep placeholders; a check verifies that.
5. **Conventions:** property group `Trace`; names `TraceId`, `Satisfies` (StringList), avoid built-in names;
   set document `License`/`LicenseURL` (default is "All rights reserved"); one trace ID per `App::Part`, optional
   per `Body`.
6. **Agent skill for FreeCAD:** edit only through Python run with `FreeCADCmd` ("open → change → recompute →
   validate → save"); list the API traps above; run validation before commit.
7. **Parameters:** check-not-generate between SysML attributes and spreadsheet aliases; a sync script as the fix.

## Risks and open questions

- **TechDraw export needs the GUI binary** and some fragile steps (open page, wait for threads, hard exit). Can break
  between FreeCAD versions. Needs a version pin (D19) and a smoke test. In Docker it will need Qt offscreen libs
  (no X needed in my test).
- **Topological naming:** FreeCAD 1.x mitigates it, but models built by agents should reference datum planes and
  sketches, not generated faces, to stay robust when parameters change.
- **Diff noise** (status flags, float last digits, ids) can hide real changes in XML diffs; the semantic diff must be
  the primary review view. Fresh rebuilds from scripts are not byte-stable.
- **Textconv is per clone** and GitHub ignores it → we need a setup step and a CI report.
- **Merge conflicts** on `.FCStd` cannot be merged; we need a rule (one owner per file during a PR, or GitCAD-style
  locks) — open question for 3.8/3.11.
- **Document.xml-only storage** worked for one simple part only; not tested on assemblies, links or TechDraw pages.
- **Assembly workbench + BOM** not tested hands-on; needed for the ME assembly design doc (D21). Test in Phase 2/5.
- **3MF/STEP determinism:** timestamps inside; bundle hashing must account for that (iteration 2).
- **MCP servers** are young and GUI-bound; maintenance status unknown.
- Open: does the ME doc show 3D (GLB + model-viewer, an external JS dependency) in iteration 1, or only SVG drawings?

## Possible conflicts with plan.md

- **D47** says FreeCAD checks run locally only. That still holds for drawings and shape checks, but **trace and
  parameter extraction do not need FreeCAD** — they can and should run in GitHub CI in iteration 1. Not a conflict,
  but a useful refinement.
- **D31** (outputs built by CI) vs. D47: drawing SVGs need FreeCAD, which CI will not have in iteration 1. Either the
  ME doc build in CI uses committed drawing SVGs (like drawio in D38, with a local "is it up to date" check), or the
  drawings appear only in locally built docs until the Docker image exists. Needs a decision (3.8/3.9).
- **D22** "extract like Doxygen": true for trace IDs and parameters; drawings are an *export* step that needs FreeCAD,
  not a pure extraction.
