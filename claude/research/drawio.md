# Research 1.7 — drawio views from the SysML v2 model

Status: done 2026-11-14. Context: D2, D38, D43 (layout keeping is iteration 2), D19 (tools installed on this machine), D47 (CI only builds docs and runs trace checks).

Tags used below:
- **[verified]**: I ran it on this machine, or read it in installed source code.
- **[read]**: taken from docs, web pages or memory. Not tested.

## Summary

- **We should write the drawio XML ourselves.** It is a small, plain XML format (`mxfile > diagram > mxGraphModel > root > mxCell`). Writing it by hand takes about 150 lines of Python. This gives us full control over IDs, attribute order and number format, so the files are byte-stable and diff well. [verified]
- **Python libraries are not a good fit as the core.** drawpyo (MIT, active) assigns cell IDs from Python `id()` (memory addresses) and writes a `modified=` timestamp, so its output changes on every run. N2G (MIT) needs igraph for layout and is aimed at network diagrams. Either could be patched, but they add little. [verified]
- **Use ELK (elkjs, EPL-2.0) for auto-layout.** Its `layered` algorithm handles nested parts, fixed-side ports and orthogonal edges. This fits interconnection (IBD-like) views well. It runs headless in Node (`npm i elkjs`, no browser needed). Graphviz `dot` 16.1.1 is installed and fits trees and requirement/trace graphs, but its port support is weak. [verified]
- **drawio desktop is NOT installed here.** No `drawio`, no flatpak or snap, no `xvfb-run`/`Xvfb`. My attempt to download the AppImage into scratch was blocked by the permission system. So I could not test `drawio --export` or `sphinxcontrib-drawio`. [verified]
- **Headless SVG export still worked**, using drawio's own renderer: I loaded drawio's `viewer-static.min.js` (Apache-2.0) into the system **Firefox 160** in headless mode, driven by `puppeteer-core` over WebDriver BiDi, and called `Graph.getSvg()`. The SVG keeps `data-cell-id="<SysML qualified name>"` on every shape, and `link` attributes become clickable `<a xlink:href>`. `rsvg-convert` → PNG and `inkscape` → PDF also worked. [verified]
- **The exported SVG is not byte-stable.** drawio puts a random `id="ge-svg-…"` on the root (used for dark-mode CSS). That is fine if CI builds the SVGs and does not commit them (D31). It matters only if SVGs are committed. [verified]
- **`sphinxcontrib-drawio` (MIT, small but alive)** needs the drawio desktop binary (plus Xvfb on headless Linux). It embeds the result as `<img>`, so **links inside the SVG are not clickable**. For clickable views we need our own small directive that inlines the SVG or uses `<object>`. [verified in installed source]
- **Layout keeping (iteration 2) is cheap if IDs are stable.** I prototyped it: regenerate from the model, then copy `mxGeometry` from the committed file for every cell ID that still exists. A manual move survived regeneration byte-for-byte. A **content check** for CI (D38) compares only semantic fields (label, parent, source, target, kind, link) and ignores geometry. It caught a changed label and a re-wired connector. [verified]
- **Notation:** follow the SysML v2 standard graphical notation (Clause 8.2.3 of the SysML v2 spec), as SysON and the pilot's PlantUML visualizer do. Parts are rectangles with compartments, ports are small squares on the border, and `«keyword»` appears above the name. [read]

## Findings

### 1. File format [verified unless marked]

Structure:

```xml
<mxfile host="..." >
  <diagram id="view-joint-ibd" name="joint IBD">      <!-- one per page; multi-page = several <diagram> -->
    <mxGraphModel grid="1" gridSize="10" page="0">
      <root>
        <mxCell id="0"/>                               <!-- root -->
        <mxCell id="1" parent="0"/>                    <!-- default layer -->
        <object id="Pkg::joint.adc" label="adc : MCP3208" link="model.html#..." sysml_kind="part">
          <mxCell style="rounded=1;container=1;..." parent="Pkg::joint" vertex="1">
            <mxGeometry x="52" y="40" width="140" height="70" as="geometry"/>
          </mxCell>
        </object>
        <object id="Pkg::joint.c_spi" label="SPI">
          <mxCell style="endArrow=none;edgeStyle=none;" parent="1" edge="1"
                  source="Pkg::joint.adc.spi" target="Pkg::joint.mcu.spi">
            <mxGeometry relative="1" as="geometry"><Array as="points"><mxPoint x=".." y=".."/></Array></mxGeometry>
          </mxCell>
        </object>
```

- **Compressed vs. plain.** In older files, `<diagram>` holds deflate+base64+URL-encoded text. The editor writes plain XML by default in recent versions ("Compressed" is a file property). Our generator must always write plain XML. CI should reject compressed diagrams. [read: drawio docs/blog; plain XML loads fine — verified]
- **IDs are free strings.** `Pkg::joint.adc.spi` worked as an ID in the viewer and was kept in the SVG `data-cell-id`. [verified]
- **Custom properties.** Wrap the `mxCell` in `<object id label ...any attrs>`. Extra attributes such as `sysml_kind` and `satisfies` are kept by the editor ("Edit Data"). The `link` attribute becomes a hyperlink. [verified for viewer/SVG export]
- **Styles** are `key=value;` strings. They are fine for diffs if we always emit them in a fixed order.
- **Containers / nested parts:** use `container=1;collapsible=0` on the parent. Children use `parent="<container id>"` and their geometry is relative to the parent's top-left corner. [verified]
- **Ports:** small child vertices on the parent's border (here 12×12 centered on the border). Edges use the port cell as `source`/`target`. drawio has no real port type; `portConstraint=` style keys and `constraint` points exist, but child cells are the common way. [verified]
- **Edges:** `edgeStyle=none` + explicit `<Array as="points">` keeps ELK's routing exactly. `edgeStyle=orthogonalEdgeStyle` lets drawio re-route and treats points only as hints. Edges in layer `1` use absolute coordinates, even when their ends sit inside containers. [verified]
- **Labels:** `html=1` labels and `whiteSpace=wrap` both produce `<foreignObject>` in SVG export. Non-browser renderers (rsvg, Inkscape, PDF tools) then show the plain `<text>` fallback, plus a "Text is not SVG – cannot display" note. Use `html=0` and no `whiteSpace=wrap` for generated views. [verified]

**Diff-friendly rules** (all applied in the prototype):
1. Plain (uncompressed) XML. One element per line, fixed indentation.
2. IDs = model qualified names. Never random IDs.
3. Integer coordinates (round). No `modified`, `etag`, `agent` or `version` noise in `<mxfile>`. No `dx`/`dy` (editor scroll position).
4. Stable element order: depth-first in model order.
5. A pre-commit/CI normalizer that re-serializes files edited in the editor. The editor adds `dx`, `dy`, `pageWidth` and similar, and may reorder attributes. [read/expected; not tested without the desktop app]

### 2. Libraries

| Library | Licence | State | Fit | Tag |
|---|---|---|---|---|
| **Own ElementTree writer** | ours | prototype works | best: stable IDs, our own styles | verified |
| [drawpyo](https://github.com/XMCesari/drawpyo) (moved from MerrimanInd; PyPI 0.2.5) | MIT | ~414★, pushed 2026-10 | OK API, but `id(self)` IDs + timestamp → non-deterministic; tree layouts only | verified |
| [N2G](https://github.com/dmulyalin/N2G) 0.3.3 | MIT | 177★, last push 2025-04 | network-diagram focus; layout needs python-igraph (failed without it) | verified |
| [jgraph/drawio-mcp](https://github.com/jgraph/drawio-mcp) | Apache-2.0 | official, very active | for agents creating diagrams in the editor; offers ELK post-layout and libavoid routing; not a batch generator | read |
| [mxgraph](https://github.com/jgraph/mxgraph) | Apache-2.0 | **archived 2020** | do not use | read |
| `drawio-diagram-generators`, `py2drawio` | — | could not find a maintained repo by these names | skip | verified (GitHub API: not found) |

### 3. Auto-layout

- **ELK / [elkjs](https://github.com/kieler/elkjs)** 0.12.1 (EPL-2.0, active, 2.9k★). It runs in Node with no browser. The `layered` algorithm with `hierarchyHandling=INCLUDE_CHILDREN`, `portConstraints=FIXED_SIDE`, `edgeRouting=ORTHOGONAL` and `json.shapeCoords/edgeCoords=ROOT` (absolute coordinates) gave a clean IBD with no manual tuning. [verified]
  - Interconnection view (parts + ports + connectors): **ELK layered**, direction RIGHT.
  - Definition / decomposition tree (BDD-like): ELK `mrtree` or layered DOWN. Graphviz `dot` is also fine.
  - Requirement / trace views: ELK layered or Graphviz `dot` (rank by V-model level). Use `stress` or `force` only for large, loose graphs.
- **Graphviz** 16.1.1 is installed. `dot -Tjson` gives coordinates for nodes and cluster bounding boxes. Watch out: y points up and units are points. Ports only work through record/HTML labels, which do not map to drawio child cells. [verified]
- **drawio's own layouts** (hierarchical, tree, organic) only run in the editor. drawio-mcp's ELK post-layout is also editor-side. [read]
- **Text sizes:** ELK needs label widths up front. In the prototype I guessed them. In the real tool, estimate width from character count × font size, or measure with a font library. [verified as a gap]

### 4. Headless export

| Path | State on this machine | Notes |
|---|---|---|
| `drawio --export --format svg/png/pdf` ([drawio-desktop](https://github.com/jgraph/drawio-desktop), GPL-3.0 app, v32.6.10 from 2026-11-04) | **not installed**; AppImage download into scratch was **blocked** by the permission system | Electron app. Needs a display, so `xvfb-run -a drawio --no-sandbox -x -f svg ...` on CI. Options: `--crop`, `--page-index`, `--embed-diagram`, `--embed-svg-fonts`, `--svg-theme`. [read] Pacman/AUR package `drawio-desktop` would fit D19 if you approve it (Phase 4.1). |
| Docker [rlespinasse/drawio-export](https://github.com/rlespinasse/drawio-export) / [docker-drawio-desktop-headless](https://github.com/rlespinasse/docker-drawio-desktop-headless) | Docker works here, but I did **not pull** (that would change things outside scratch) | MIT, very active (pushed 2026-11). The usual CI route. GitHub Action `rlespinasse/drawio-export-action`. [read] |
| **Firefox headless + puppeteer-core + drawio `viewer-static.min.js`** | **works** [verified] | Uses drawio's own renderer (same output as the editor). No Electron, no X server. Needs a browser in CI (Firefox or Chrome; `ubuntu-latest` runners have both). |
| Firefox `--headless --screenshot` of an HTML page with the viewer | works, PNG only [verified] | quick visual check |
| SVG → PNG/PDF: `rsvg-convert`, `inkscape` | installed, worked [verified] | only after `html=0` labels |
| Own SVG renderer from the ELK result | not built | fallback, possible because we own the geometry |

Also see ["Truly headless draw.io exports"](https://fasterthanli.me/series/dont-shell-out/part-1) for a write-up on removing the Electron dependency. [read]

### 5. Sphinx integration

- [sphinxcontrib-drawio](https://github.com/Modelmat/sphinxcontrib-drawio) 0.0.17, MIT, 42★, last push 2026-04. It has directives `drawio-image` and `drawio-figure` (`:page-name:`/`:page-index:`) and config keys `drawio_binary_path`, `drawio_headless` (starts Xvfb itself) and `drawio_no_sandbox`. It **calls the desktop binary** and emits a docutils `image` node → `<img>` → **SVG links are not clickable**. [verified in installed source]
- **Recommended:** our own small directive in the framework repo (D34), e.g. `.. sysml-view:: views/joint-ibd.drawio`. It would:
  1. Use the SVG that the export step built (no export inside Sphinx). This keeps the Sphinx build free of browsers.
  2. Inline the SVG, or use `<object>`, so the `<a>` links work.
  3. Rewrite each `link` to the real doc URL: sphinx-needs IDs → `need` page and anchor; SysML element → model page anchor. Do this in Python at generate time, or set relative links in the drawio `link` attribute.
  4. Optionally create a sphinx-needs object per view (e.g. type `view`) so views show up in trace tables.
- **Stable IDs:** the SVG keeps `data-cell-id` = drawio cell ID = SysML qualified name. CSS/JS can use this for hover, highlight or "show in model". [verified]
- **Alternative:** drawio's viewer JS in the page (`<div class="mxgraph" data-mxgraph=...>`) gives zoom, layers and pages in the browser. But it needs 4.6 MB of JS and does not work in PDF. [verified that it renders]

### 6. Keeping manual layout (input for iteration 2) and the CI check (D38)

Strategies:
1. **Merge geometry from the committed file by ID** (prototyped, works). Generate from the model with auto-layout. Then, for every ID that is also in the committed file, take the old `mxGeometry` (and edge points). New elements get ELK positions; deleted ones disappear. [verified]
   - Weak spots: new elements may overlap old hand-placed ones. Fix: run ELK in "interactive" mode, or fix the old nodes in place and lay out only the new ones (ELK `layered` supports `interactive` strategies; libavoid can re-route only edges). [read]
   - A renamed element = new ID → its manual position is lost. A rename map from the model diff could help.
   - Edge points must be dropped when an end moved, or the edge looks broken.
2. **Layout sidecar** (`view.layout.json` keyed by element ID, plus a generated `.drawio`). This is what [Structurizr](https://docs.structurizr.com/) does (workspace JSON with layout merged by element identity). Eclipse Sirius/Capella do the same (`.aird` layout separate from the semantic model), and so does SysON (diagram layout stored apart from the model). It gives clean content/layout separation. The cost: editors must not hand-edit the drawio, or we must extract geometry back from it. [read]
3. **The committed drawio file *is* the layout store** (strategy 1). This fits D38, because the drawio files are committed anyway. Humans and agents edit layout in the editor or the XML, and content always comes from the model. **Recommended.**

**CI "matches model" check** (prototyped): regenerate in memory, then compare per cell ID the tuple (label, parent, source, target, kind, link, trace attrs). Geometry and style are ignored. Report MISSING / NOT IN MODEL / CHANGED, and exit 1. This runs in plain Python plus Node (elkjs), with no browser, so it fits D47. Also fail on compressed diagrams. [verified]

### 7. Notation for our view styles [read]

- The SysML v2 spec (OMG formal/2025, Part 1, clause 8.2.3 "Graphical Notation") defines the standard views: General, Interconnection, Action Flow, State Transition, Sequence, Geometry, Grid, Browser. Summary of the shapes:
  - Definitions are rectangles with square corners and `«part def»` style keywords.
  - Usages are rectangles with rounded corners.
  - Ports are small squares on the border.
  - Connections are plain lines, and flows have arrows.
  - Compartments list attributes, ports and parts.
  - Requirements use `«requirement»` with id/text compartments.
  - Relations use UML-like heads (generalization: hollow triangle; satisfy/verify: dashed arrows with keywords).
- [SysML v2 Pilot Implementation](https://github.com/Systems-Modeling/SysML-v2-Pilot-Implementation) (EPL-2.0, active) renders views through PlantUML (`%viz` in Jupyter, PlantUML view in Eclipse). Good as a visual reference for what "standard-like" looks like; layout is Graphviz.
- [SysON](https://github.com/eclipse-syson/syson) (EPL-2.0, active) is web-based, built on Sirius Web. Its General and Interconnection views follow the standard notation closely. Good reference for colors and compartments.
- Tom Sawyer offers a commercial SysML v2 viewer with automatic layout. It is closed source and only useful as visual inspiration.
- Proposal for our styles: parts = rounded rectangles (usages) with `name : Type`; definitions = square corners + `«part def»`; ports = 12 px squares on the border, name outside; interfaces/connections = plain lines with an optional label; trace links = dashed arrows with `«satisfy»`/`«verify»`/`«refine»`. One style table in the framework, keyed by SysML metaclass.

## Hands-on results (exact)

Scratch: `/tmp/claude-1000/-home-tobias-z-wrk-ws-syseng/cc4a5268-5423-4e94-be0d-4c1055bbe07f/scratchpad/research-drawio/`

| Step | Command / action | Result |
|---|---|---|
| Inventory | `which drawio draw.io xvfb-run Xvfb dot node npx docker inkscape rsvg-convert firefox` | drawio ✗, draw.io ✗, xvfb-run ✗, Xvfb ✗, flatpak/snap ✗; dot ✓ (graphviz 16.1.1), node v26.13.1, npm 12.2.2, docker ✓ (user in group), inkscape ✓, rsvg-convert ✓, firefox 160.0 ✓; Python 3.14.10 |
| Python libs | `venv; pip install drawpyo N2G sphinxcontrib-drawio` | drawpyo 0.2.5, n2g 0.3.3, sphinxcontrib-drawio 0.0.17 installed |
| drawio AppImage | `curl` v32.6.10 AppImage to scratch, `--appimage-extract` | **blocked by the permission system** (download+run of a binary). Not retried. |
| elkjs | `npm install elkjs` (scratch/node) | 0.12.1 ✓ |
| Generator | `gen/gen_drawio.py` (model dict → ELK JSON → `node elk_layout.mjs` → ElementTree → `out/joint-ibd.drawio`) | ✓ Part `joint` with 2 boundary ports, 3 nested parts (adc, mcu, pwm) with 2 ports each, 4 connectors. 90 lines of XML. |
| Determinism | generate twice, `cmp` | byte-identical ✓ |
| Viewer PNG | `firefox --headless --no-remote --profile <scratch> --screenshot` on an HTML page with `viewer-static.min.js` (drawio v32.6.1, jsDelivr) | ✓ correct rendering |
| SVG export | `node gen/export_svg.mjs` (puppeteer-core 25.17.0, `browser:"firefox"`, `executablePath:/usr/bin/firefox`, `GraphViewer` + `graph.getSvg()`) | ✓ `out/joint-ibd.svg`, 8 KB, `data-cell-id` on all cells, 4 `<a xlink:href>` from `link` attrs. Takes ~5 s, mostly browser start. |
| SVG stability | export twice, diff | differs **only** in the random root `id="ge-svg-…"` |
| html labels | first run with `html=1;whiteSpace=wrap` | `<foreignObject>` + "Text is not SVG" note in rsvg. Fixed by `html=0`, no wrap → 0 foreignObject |
| SVG → PNG/PDF | `rsvg-convert`, `inkscape --export-type=pdf` | ✓ both (Inkscape warns about the CSS `background` property, which is harmless) |
| Layout keep | change mcu geometry by hand in a copy → `gen_drawio.py regen.drawio --keep manual.drawio` | "kept geometry for 16 cells"; regen == manual byte-for-byte ✓ |
| CI check | `gen_drawio.py --check committed.drawio` | geometry-only change → exit 0; label change + re-wired connector → `CHANGED: …` lines, exit 1 ✓ |
| drawpyo | 2 boxes + edge | works; IDs like `140431412113296` (memory address), `modified=` timestamp → not stable |
| N2G | 2 nodes + link + `layout("kk")` | failed: needs `python-igraph` |
| Graphviz | `dot -Tjson` with a cluster | ✓ node positions + cluster bounding box |

Result image (rendered by drawio's engine, converted with rsvg): the part `joint : JointController` contains `adc : MCP3208 → mcu : STM32G474 → pwm : PCA9685` in one row, with port squares on the borders and connectors labelled SPI and I2C.

## Recommendations

**Iteration 1 generator stack**
1. **Model access** comes from the SysML research (1.3). It gives a list of elements with qualified names.
2. **View definitions** (which elements, which view kind) live in the model (SysML v2 `view` / `expose`) or in a small YAML file per view.
3. **Python generator** (framework repo) writes **plain, normalized drawio XML** with **cell ID = qualified name**. It wraps cells in `<object>` with `sysml_kind`, trace attributes and `link`. Use `html=0` labels. One `<diagram>` page per view, or one file per view. **One file per view is simpler for diffs and Sphinx.**
4. **Layout:** elkjs in Node, called as a subprocess (JSON in, JSON out). Use ELK layered for interconnection, decomposition and trace views. Graphviz is optional for big trace graphs.
5. **Export:** for iteration 1, use **headless Firefox/Chrome + puppeteer-core + pinned drawio `viewer-static.min.js`**, vendored at a fixed version in the framework repo (Apache-2.0). This works today without new system packages. As a second option, install drawio desktop (pacman/AUR or the AppImage) in Phase 4.1 and use `xvfb-run drawio -x -f svg` in the later Docker image. Both use the same rendering engine.
6. **Sphinx:** our own `sysml-view` directive that inlines the built SVG with working links. Do not use sphinxcontrib-drawio, because it gives `<img>` without links and needs the desktop binary.
7. **Check (D38):** `views check` = regenerate in memory + semantic compare + "no compressed diagrams". Runs locally (D46) and in GitHub CI (D47: it is a model/trace check and needs only Python + Node).

**Iteration 2 layout keeping:** use the committed drawio as the layout store. Regenerate content, merge geometry by ID, and lay out only new elements around fixed old ones (ELK interactive / fixed positions). Drop edge points whose ends moved. Write a "layout changes only" diff report for reviewers. Consider a rename map so moved or renamed elements keep their place.

## Risks and open questions

- **Export toolchain not settled.** drawio desktop is missing here, and my download was blocked. The browser route works but adds Node + a browser to CI. Decide in Phase 4.1: (a) vendored viewer + puppeteer, (b) drawio desktop + Xvfb, (c) the rlespinasse Docker image. D19 says "use what is installed", and only route (a) works with what is installed.
- **Licence:** elkjs is EPL-2.0 (weak copyleft). That is fine for use as a tool. drawio desktop is GPL-3.0 as an application. That is fine because we only run it and do not ship it. The drawio viewer JS is Apache-2.0. [read]
- **Editor round-trip:** when a human saves in drawio desktop, the editor adds attributes (`dx`, `dy`, page size, maybe `etag`/`modified`) and may compress the file if that setting is on. We need a normalizer step (pre-commit) and a test with the real editor. **Not verified**, because the editor is not installed.
- **Agents editing XML:** agents can edit geometry in plain XML easily, but they can break parent-relative coordinates. The check script should also validate geometry (no child outside its parent, no overlaps). jgraph/drawio-mcp is an option for agent-driven layout edits.
- **Label sizing:** ELK needs text widths. A bad estimate gives clipped or overflowing labels. The fix is a font-metrics helper.
- **SVG not byte-stable** (random root id). Do not commit SVGs. This is consistent with D31/D38.
- **Clickable links in PDF** (iteration 2 PDF set): SVG → PDF through Inkscape keeps the shapes. Whether the links survive is not tested.
- **Contradiction check with plan.md:** no direct conflict. Two notes:
  1. D2/D38 say "drawio files are committed and CI checks that they match the model". This works only if "match" means **semantic content, not geometry**. This should be written down explicitly in 3.5/3.6, because otherwise any manual layout tweak (even in iteration 1) fails CI.
  2. Plan item 4.1 lists drawio as a tool to find. It is **not installed**, and whether to install it is open. The headless-browser export removes the hard need for drawio desktop in iteration 1.

## Sources

- drawio format & export: https://www.drawio.com/doc/faq/ (format, compressed XML), https://www.drawio.com/blog/export-svg.html, https://github.com/jgraph/drawio (Apache-2.0), https://github.com/jgraph/drawio-desktop (GPL-3.0, v32.6.10)
- Headless: https://github.com/rlespinasse/drawio-export, https://github.com/rlespinasse/docker-drawio-desktop-headless, https://fasterthanli.me/series/dont-shell-out/part-1, https://linuxcommandlibrary.com/man/drawio
- Libraries: https://github.com/XMCesari/drawpyo, https://github.com/dmulyalin/N2G, https://github.com/jgraph/drawio-mcp, https://github.com/jgraph/mxgraph (archived)
- Layout: https://github.com/kieler/elkjs, https://github.com/eclipse-elk/elk, https://eclipse.dev/elk/reference.html, https://graphviz.org
- Sphinx: https://github.com/Modelmat/sphinxcontrib-drawio
- SysML v2: https://github.com/Systems-Modeling/SysML-v2-Pilot-Implementation, https://github.com/Systems-Modeling/SysML-v2-Release, https://github.com/eclipse-syson/syson
- Layout persistence prior art: https://docs.structurizr.com/ (layout merge), Eclipse Sirius/Capella `.aird` representation files
