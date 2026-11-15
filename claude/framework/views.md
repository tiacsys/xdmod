# View generation (task 3.5)

Status: **AGREED 2026-11-14** (review answers → D94–D97). Built on D2, D38, D43, D56, D64a, D65, D85 (`../decisions.md`), `../research/drawio.md`,
`../research/sysml-sysmod.md` §2, and the spike (`../notes/spike.md`: one working view).

## 1. Goals

- **Views come from the model.** People and agents never draw model content by hand.
- **One source, several outputs:**
  - drawio for people to view and arrange
  - inline SVG in the HTML docs, with clickable links
  - JSON for agents and tools
  - PDF in iteration 2
- **Reviewable in git.** Committed views are editable SVG (`.drawio.svg`, D96) whose embedded diagram is plain, normalized XML with stable IDs.
- **Layout may be tuned by hand later** (iteration 2, D43), so it must never count as model content.

## 2. View kinds (iteration 1)

| View kind | Shows | Mainly from SYSMOD step | Layout |
|---|---|---|---|
| `context` | the system, its actors, system ports, interfaces | 07 | ELK layered |
| `usecases` | use cases, actors, the needs they address | 08 | ELK layered |
| `decomposition` | parts and their sub-parts (BDD-like), per layer: functional, logical, product | 10a–10c | ELK layered (tree) |
| `interconnection` | parts with ports and connectors inside one part (IBD-like) | 10b–10d | ELK layered, ports on borders |
| `allocation` | functional → logical → product (150 %) (`realizes`) | 10a–10d | ELK layered, three columns |
| `variants` | per configuration: the variant chosen at each variation point, side by side (D102) | 10c–10d | ELK layered, one column per configuration |
| `general` | SysML v2 general view: what `expose`/`filter` select; definitions, usages, specialization, composite and reference features, dependencies (added 2026-11-15 for the XDMOD self-model) | any | ELK layered, `direction` option |
| `actionflow` | SysML v2 action flow view: actions with pins, successions, flows, decide/merge/fork/join, start/done | any | ELK layered, model-order cycle breaking |
| `statetransition` | SysML v2 state transition view: states, entry, transitions with trigger and guard | any | ELK layered |
| `trace` | needs graph around one need (requirement ↔ model ↔ domain ↔ tests) | all | sphinx-needs `needflow` (graphviz); not drawio (question 2) |

## 3. Where views are defined

Each view is a **SysML v2 `view`** in `robarm-syseng/model/views.sysml`. Its `expose` and `filter` select the elements; the Pilot already evaluates both (research, verified). A small metadata annotation names the view kind and options:

```sysml
view <'SYS-VIEW-0001'> jointInterconnection {
    @XdView { kind = "interconnection"; root = "RobArm::Product::JointModule"; }
    expose RobArm::Product::JointModule::**;
    filter @SysML::PartUsage or @SysML::PortUsage or @SysML::ConnectionUsage;
}
```

`XdView` is defined in xdmod's SysML library (next to the trace metadata used in the spike). Views are model elements, not needs, so `SYS-VIEW` is a reserved non-need kind (`id-scheme.md` §3): only a SysML short name, no row in the trace model.

## 4. Pipeline

```
.sysml ──Pilot (jshell, D65)──► model JSON + per-view exposed elements
        ──view generator (xdmod, Python)──► view graph JSON  ──► build/<area>/views/<view>.json   (for agents)
        ──elkjs layout (Node)──► positions
        ──drawio writer + SVG render (headless Firefox + pinned drawio viewer, locally)──► robarm-syseng/views/<view>.drawio.svg   (committed: editable SVG = picture + embedded diagram, D96)
        ──`sysml-view` Sphinx directive──► inline SVG in HTML, with links to need pages
```

Rules for the drawio file (all verified in the research or the spike):
- **Cell ID = SysML qualified name.** So output is byte-stable across runs, and a reviewer sees real names in diffs.
- Every cell is wrapped in `<object>` with `sysml_kind`, `trace_id` (the need ID, if any), `layer`, `configs`, and `trace_id`-based links that the docs build resolves to the right page (no hard-coded URLs, because hosting is versioned, D55).
- Labels use `html=0`. The embedded diagram is stored **uncompressed**. There is one file per view.
- **Editable SVG (D96).** The committed file is a `.drawio.svg`: the rendered picture with the drawio diagram embedded. drawio desktop opens it as a diagram, and browsers and Sphinx show it as an image. The export step replaces the random SVG IDs with fixed ones, and writes the hash of the embedded diagram into the SVG, so CI can tell whether the picture is fresh.
- Each view has a legend cell, which explains the shapes and colours of that view kind.

## 5. Styles

Shapes follow the SysML v2 graphical notation where it's simple: parts are rectangles with a `«part»` heading, ports are small squares on the border, connectors are plain lines, and use cases are ellipses.
Colour shows the **layer** (functional, logical, product). Elements that belong to only some configurations show their `configs` as a badge, and variation points get a dashed border. The styles are defined once in xdmod, as a style table per `sysml_kind`.

## 6. Checks

Details are in `checks.md`.
- **View content check (D38, D64a, D96).** The tool regenerates each view in memory and compares the **content** with the diagram embedded in the committed file: labels, parents, edge ends, kinds and links. Geometry is not compared, so a moved box never fails CI. It also rejects compressed diagrams and geometry errors, such as a child outside its parent. It also checks that the picture is fresh, by comparing the hash stored in the SVG with the embedded diagram. CI needs no browser for this.
- **Normalizer.** A pre-commit step rewrites a `.drawio.svg` saved by the editor into the normalized form. It removes editor attributes, sorts cells and decompresses. drawio desktop 31.7.0 is installed (D97), so the round trip with `.drawio.svg` is tested in Phase 4.

## 7. Iteration 2: keeping manual layout

The committed `.drawio.svg` becomes the layout store. Content is regenerated, and geometry is merged in from the old file by ID. Only new elements are laid out, around the fixed old ones (ELK interactive mode). Edge points whose ends moved are dropped. A "layout changes only" report helps reviewers. The research showed a working prototype of this merge.

## 8. Answered review questions (2026-11-14)

1. **View definitions** live in the model as SysML `view`s with `@XdView` metadata (D94).
2. **Trace graphs** use sphinx-needs `needflow` (graphviz). The user has a separate tool for analysing trace graphs interactively in the works (D95).
3. **SVG in CI:** views are committed as **editable SVG** (`.drawio.svg`), rendered locally. CI checks content and freshness without a browser (D96).
4. **drawio desktop** 31.7.0 is already installed as a system package (D97).
