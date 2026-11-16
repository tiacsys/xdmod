# FreeCAD storage and review (task 3.8)

Status: **AGREED 2026-11-14** (review answer → D108). Writes up D63 (resolves D41) with the details from `../research/freecad.md` §5–6
(all verified with FreeCAD 1.1.4 on this machine), plus D29, D56, D67, D88, D100.

## 1. Storage

- **`.FCStd` stays the source of truth.** It is saved with **compression level 0**: a zip whose entries are stored uncompressed (about 86 kB instead of 11 kB for a test part). Git's delta compression works much better on that.
- Compression is a **FreeCAD user preference** (`Document/CompressionLevel`). So the FreeCAD launcher (`curatrix launch freecad`, D67) starts FreeCAD with a **workspace-local user config dir** that sets level 0, our templates and the parts library path (D88). User-global FreeCAD settings are not used.
- Check CK-H1 (`checks.md`) rejects a compressed `.FCStd` in pre-commit and PR CI.
- `.gitattributes` in robarm-me: `*.FCStd diff=fcstd -merge`. `.FCStd` files can't be merged, so a conflict means "choose one side and redo the other change".

## 2. Readable diffs (textconv)

- A small extractor in curatrix (`curatrix gen freecad-json <file>`) prints a **semantic JSON** of a document, in two parts:
  - **Trace part, plain Python** (reads `Document.xml`, no FreeCAD needed, so it runs in CI): objects, `TraceID` and link properties, spreadsheet aliases and values, placements.
  - **Shape part, needs FreeCAD** (local only): volume, bounding box, number of solids.

  Together they cover:
  - objects with their `TraceID` and link properties (D29)
  - spreadsheet aliases and values
  - placements
  - a shape summary (volume, bounding box, number of solids)

  It leaves out noise: temp paths, dates, object ids, UUIDs.
- It is the git `textconv` driver for `*.FCStd`. In the research, a parameter change showed as **one line** (`"link_length": "80 mm"` → `"95 mm"`). With plain `unzip Document.xml` it showed as 24 noisy lines.
- The bootstrap sets the driver in each clone (`git config diff.fcstd.textconv …`), because git doesn't take driver settings from the repo (D100).
- The same JSON also feeds the trace extraction (CAD needs) and check CK-F3 (parameters vs. model).

## 3. Review report (GitHub shows `.FCStd` as binary)

GitHub's PR view ignores textconv. So for every PR that changes `.FCStd` files, the author (person or agent) runs `curatrix check robarm-me --stage local`, which writes a **review report** to `build/robarm-me/review/<branch>/`:
- the semantic JSON diff per changed file
- TechDraw page SVGs before and after, plus an image diff
- a 3D render (GLB) of the changed parts, before and after
- changed parameters and trace IDs as a table

**Iteration 1 (D135):** the report stays local (`build/robarm-me/review/<branch>/`). Reviewers use it together with the committed semantic JSON, which GitHub diffs as text. **Later (D108):** the author publishes the report as a Pages preview of robarm-me, in the folder `previews/pr-<n>/` (D108), and links it from the PR with a comment that carries the provenance trailer (D72). Reviewers get clickable pages, including the 3D viewer. A workflow removes the folder when the PR closes. CI can't build the report, because CAD is local only (D56). The PR template asks for it when `.FCStd` files change.

## 4. Drawings and git version

- Drawings use **our own TechDraw template**, an SVG with `freecad:editable` fields. It has a wide revision field for `git describe` strings (the stock ISO field is too narrow).
- Git values (version, SHA, dirty flag) are **only set at export time**. The exporter opens the file, writes the values into the template's editable texts, exports, and **closes without saving**. The `.FCStd` stays unchanged (verified).
- Full-page SVG and PDF export needs the GUI binary with `QT_QPA_PLATFORM=offscreen` (no display needed), run under curatrix limits (D71). FreeCAD prints noise to stdout, so results go to files.

## 5. Known limits

- An unchanged save still writes a few noise lines into `Document.xml`. The semantic JSON hides them, but the binary changes anyway. The pre-commit hook warns when a `.FCStd` changed while its semantic JSON didn't ("save without change").
- Rebuilding a part from a script changes object ids and UUIDs. So scripted parts (option 2 in the research) are not used in iteration 1.
- glTF/GLB export needs a tessellate step first.
- TechDraw export may change between FreeCAD versions. The version is pinned in `tools.yaml` (D19).
- Assemblies and BOM were not tested in the research. The tooling is Phase 5 (5.23–5.27), the joint assembly task 6.10.

## 6. Answered review question (2026-11-14)

1. **Report delivery:** a Pages preview folder `previews/pr-<n>/` on robarm-me, linked from the PR and removed when the PR closes (D108).
