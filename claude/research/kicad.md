# Research 1.4 — KiCad in the framework

Author: research agent 1.4 · Date: 2026-11-14 · KiCad on this machine: **10.0.8** (Arch/CachyOS package, `KICAD_IPC_API=ON`).

Legend: **[V]** = verified hands-on on this machine. **[R]** = only read (docs, READMEs, source); not run.

Hands-on files: `/tmp/claude-1000/-home-tobias-z-wrk-ws-syseng/cc4a5268-5423-4e94-be0d-4c1055bbe07f/scratchpad/research-kicad/` (sub-folders `hands-on/`, `scripts/`, `kicanvas-web/`).

---

## Summary

- **Prior art for Sphinx is thin and dead.** The only KiCad ↔ Sphinx extension found is
  [`sphinx-pcbdraw`](https://github.com/nobodywasishere/sphinx-pcbdraw) (MIT, 12 stars, last push 2021).
  It renders **PCB boards only** (no schematics) via the old PcbDraw 0.x CLI and KiKit, i.e. KiCad 5/6.
  It will not work with PcbDraw 1.x / KiCad 10 without a rewrite. The Eagle analogue
  [`sphinxcontrib-eagle`](https://github.com/ponty/sphinxcontrib-eagle) (2017) shows the same pattern. **[R]**
  Verdict: not worth reviving. A new, small Sphinx extension that calls `kicad-cli` is about 150 lines.
- **`kicad-cli` 10.0.8 covers almost all doc extraction** we need: schematic SVG/PDF, netlist (XML/s-expr),
  configurable BOM CSV with custom fields, ERC/DRC as JSON, PCB SVG/Gerber/drill/pos/3D render, plus
  `--define-var` and `--variant`. **[V]**
- **Trace IDs (D29) work as custom symbol fields.** A hidden field `TraceID` is invisible in the drawing but
  appears in the XML netlist, the s-expr netlist and the BOM CSV. **[V]**
- **Git stamping is built into KiCad 10.** New text-expression functions `@{vcsidentifier(7)}`,
  `@{vcsnearestlabel()}`, `@{vcsdirtysuffix()}`, `@{vcsbranch()}` … resolve from the repo at plot time, in title
  blocks and on silkscreen. A project text variable can default to these and be overridden with
  `kicad-cli -D GIT_REV=…`. Nothing is written back: the **working tree stays clean**. **[V]**
- **Interactive viewer:** [KiCanvas](https://github.com/theacodes/kicanvas) (MIT, alpha) renders a
  KiCad 10 schematic in a `<kicanvas-embed>` web component. It does not resolve text variables. **[V]**
- **PR review:** no maintained tool gives a polished GitHub-native schematic diff. Options: KiRi (web UI,
  MIT), KiDiff/KiBot (PDF diff, GPL/AGPL), or our own `kicad-cli` SVG + ImageMagick diff (tested, works). **[V]/[R]**
- **Agent authoring:** the IPC API in KiCad 10 is **PCB only and needs a running GUI**; schematic IPC and a
  headless `kicad-cli api-server` are announced for **KiCad 11** (seen in `kicad-python` 0.8.0). **[V]/[R]**
  Today the safe path is s-expression editing with **kicad-skip** + `kicad-cli sch upgrade --force`
  (normalises the file) + ERC + netlist compare. **kiutils 1.4.8 corrupts KiCad 9/10 files** (drops `hide`). **[V]**
- **Model check:** comparing the XML netlist with a pin map from the SysML interface elements (D36) is simple;
  a 30-line prototype works. **[V]**
- **CAM is feasible** with plain `kicad-cli` (Gerber X2, Excellon, pos CSV, BOM); KiBot is optional. **[V]**

---

## 1. Prior art: KiCad ↔ Sphinx and related tools

| Tool | What it does | KiCad versions | State / licence | Use for us |
|---|---|---|---|---|
| [sphinx-pcbdraw](https://github.com/nobodywasishere/sphinx-pcbdraw) | `.. pcbdraw:: board.kicad_pcb` directive; calls PcbDraw, embeds the 2D board image. Options `:back:`, `:mirror:`, `:style:`, `:remap:`. | 5 / early 6 (old PcbDraw 0.x CLI) | Abandoned since 2021, MIT, 12★, not on PyPI | Pattern only. PCB only, no schematic. |
| [sphinxcontrib-eagle](https://github.com/ponty/sphinxcontrib-eagle) | Same idea for Eagle (images + part list at build time) | n/a | Dead (2017), BSD | Pattern only |
| [PcbDraw](https://github.com/yaqwsx/PcbDraw) 1.3.0 | Stylised 2D board drawings, pinout diagrams | 6–10 (active, pushed 2026-10) | MIT | Iteration 2 (PCB layout) |
| [KiBot](https://github.com/INTI-CMNB/KiBot) 1.9.1 | YAML-driven output generator (schematic PDF/SVG, BOM, iBOM, Gerber, diff, 3D, …) | 5–10 (v1.9 adds KiCad 10 items, [changelog](https://kibot.readthedocs.io/en/v1.9.1/Changelog.html)) | Very active, **AGPL-3.0**, 763★ | Optional runner for CAM in iteration 2 |
| [KiCanvas](https://kicanvas.org/embedding/) | Browser viewer, `<kicanvas-embed src=… controls=basic>` web component, no runtime deps | 6+ (KiCad 10 schematic rendered OK in my test) | "Early alpha", MIT, 1172★, last push 2026-04 | Interactive view in the PCBA doc (optional) |
| [InteractiveHtmlBom](https://github.com/openscopeproject/InteractiveHtmlBom) | Interactive HTML BOM from the **PCB** | 5–10 | Active, MIT, 4.6k★ | Iteration 2 (needs a layout, D43) |
| [kicad_svg_parser](https://github.com/SpaceTeam/kicad_svg_parser) | `.kicad_sch` → stylable SVG | 6+ | Dead (2023), 0★ | No |
| [plotkicadsch/plotgitsch](https://ocaml.org/p/plotkicadsch/0.8.0/README.md.html) | KiCad 5 schematic plot + git diff (OCaml) | 5 | Old | No |
| [kicad-happy](https://github.com/aklofas/kicad-happy) | Claude Code / Codex skills: parse, review, BOM, EMC of KiCad projects | 9/10 | Active, MIT, 1.7k★ | Ideas for agent review skills |

The project owner probably remembers `sphinx-pcbdraw` (or KiBot's PcbDraw output). It rendered PCB layouts, not
schematics. **Revival is not worth it**: the code is a thin wrapper around a CLI that has changed, and today
`kicad-cli` does the rendering itself. I found no KiCad forum thread with a Sphinx plugin.
Search used: GitHub API (`sphinx kicad`, `sphinxcontrib kicad`), PyPI name probes, web search. **[R]**

**Recommendation:** write our own small extension in the framework repo (D34), e.g. `sphinx_kicad`:
- `.. kicad-schematic:: path/to/x.kicad_sch` → runs `kicad-cli sch export svg` (cached by file hash), embeds
  one figure per sheet; option `:interactive:` adds a KiCanvas embed.
- `.. kicad-bom::` → table from `kicad-cli sch export bom` CSV.
- `.. kicad-erc::` → table from ERC JSON.
- A needs generator (see §3) that creates sphinx-needs objects from the netlist fields.

## 2. Doc extraction (D22)

### kicad-cli 10.0.8 (all **[V]** unless marked)

| Command | Output | `-D` var | Notes |
|---|---|---|---|
| `sch export svg` | one SVG per sheet | yes | `-e` no frame, `-n` no background, `--theme`, `--pages`, `--variant` |
| `sch export pdf` | multi-page PDF | yes | Title block text searchable (pdftotext) |
| `sch export netlist --format kicadxml\|kicadsexpr\|spice\|…` | netlist | no (not needed) | Custom fields included |
| `sch export bom --fields … --labels … --group-by …` | CSV | – | Custom fields as columns. `--preset`/`--format-preset` use presets stored in the schematic |
| `sch export python-bom` | legacy XML (full data) | – | Same data as kicadxml netlist |
| `sch erc --format json --severity-all --exit-code-violations` | JSON report with `$schema` | yes | Non-zero exit on violations → usable as a check |
| `sch upgrade --force` | re-saves the file in KiCad's canonical format | – | Key tool to normalise agent edits (§6) |
| `pcb export svg/pdf/gerbers/drill/pos/step/glb/ipc2581/odb/…` | | yes for plots | |
| `pcb drc --format json --schematic-parity` | JSON | yes | Parity check needs a layout |
| `pcb render --side top --rotate …` | PNG/JPEG raytraced 3D image | yes | Worked headless here |
| `jobset run` | runs a `.kicad_jobset` (KiCad's own output pipeline) | | **[R]** not tried; native alternative to KiBot |

Also present: `--variant` (KiCad 10 design variants) on most exports. This may map to D37 (prototype vs product
variants) for BOM/DNP differences. **[R]**, worth a look in Phase 3.

### APIs
- **SWIG `pcbnew` Python module**: still shipped and importable in 10.0.8 (`python3 -c "import pcbnew"` → 10.0.8). **[V]** PCB only, deprecated in favour of IPC. **[R]**
- **IPC API** + [`kicad-python`](https://pypi.org/project/kicad-python/) (`kipy`, MIT, 0.8.0, 2026-08): protobuf over a socket to a **running KiCad GUI**. In 0.8.0 the `Schematic` class is marked "added in KiCad 11", and `kipy/server.py` starts `kicad-cli api-server`, which does **not exist** in 10.0.8 (`kicad-cli api-server` → usage error). **[V]** So for iteration 1, no schematic IPC and no headless IPC.
- **Direct s-expression parsing**: works well for reading. With `sexpdata` I read all `TraceID`/`Satisfies` fields in ~10 lines (`scripts/read_fields.py`). **[V]** But the **XML netlist is a better extraction source**: stable, documented, flattened over hierarchy, and needs no parser of our own.

### Embedding a schematic in Sphinx
1. **Static SVG** (recommended default): `kicad-cli sch export svg -n` → `.. figure::`. 560 kB for one A4 sheet; renders well (`rsvg-convert` check). Text is real `<text>` → searchable. **[V]**
2. **Interactive**: copy `kicanvas.js` (477 kB, from kicanvas.org) into `_static`, add a raw HTML `<kicanvas-embed src="_static/x.kicad_sch" controls="basic">`. I rendered a KiCad 10 schematic in headless Firefox: correct drawing, but `${GIT_REV}` and `@{…}` stayed unresolved (it does not run KiCad's variable engine). **[V]** Alpha quality, no pinned release; vendor a copy.

## 3. Trace IDs inside KiCad files (D29)

- **Symbol fields:** any number of custom properties per symbol, e.g. `TraceID = EE-CMP-R1`, `Satisfies = SYS-REQ-042`. Set them `hide yes` so the drawing stays clean; KiCad shows them in the Symbol Fields Table for editing. **[V]**
- **Where they come out [V]:**
  - XML netlist: `<field name="TraceID">EE-CMP-R1</field>` and `<property name="TraceID" …/>` per component.
  - s-expr netlist and python-bom XML: same.
  - BOM CSV: as a column.
  - SVG/PDF: **not** shown when hidden (checked with grep).
- **Pitfall [V]:** BOM `--group-by Value` merged R1 (with TraceID) and R2 (without) into one row showing R1's ID. Never group when extracting trace data; use the netlist.
- **Sheet fields:** hierarchical sheet symbols also carry custom fields (one per sub-circuit, e.g. the joint's driver block) and appear in the netlist `<sheet>` data. **[R]** The root sheet has no fields; use title block comments or project text variables for document-level IDs.
- **Into sphinx-needs:** a small generator reads `net.xml` and writes one need per component/sheet with the ID, ref, value, footprint, and outgoing links from fields (`satisfies`, `implements` → link types from the D36 table). Either as generated `.rst` (`.. ee_part:: … :id: EE-CMP-R1 :satisfies: SYS-REQ-042`) or as a `needs.json` for `needimport`. Backlinks are computed by sphinx-needs (D5).
- **Also:** symbols carry a stable `uuid`; useful for affirmatrix (1.2) as a content anchor, but the human ID should stay in a field.

## 4. Git version in title block and silkscreen

Three methods tested; **#3 is the recommendation**.

1. **`kicad-cli -D GIT_REV=$(git describe …)`** on every plot/ERC/DRC/render. The project file holds a default (`text_variables: {"GIT_REV": "unversioned"}`); the CLI overrides it in memory. Title block `(rev "${GIT_REV}")` and silkscreen `rev ${GIT_REV}` came out as `2e81726` in SVG, PDF and PCB SVG. **Tracked files unchanged** (`git status` clean, only an untracked `.kicad_prl` appeared). **[V]**
2. **KiBot `set_text_variables` preflight** writes the values into `.kicad_pro` → dirties the tree unless restored ([KiBot docs](https://kibot.readthedocs.io/en/latest/configuration/preflights/set_text_variables.html), [issue #686](https://github.com/INTI-CMNB/KiBot/issues/686)). **[R]** Not recommended.
3. **KiCad 10 built-in VCS text functions** ([`text_eval_vcs.h`](https://docs.kicad.org/doxygen/text__eval__vcs_8h.html)): `vcsidentifier([len])`, `vcsnearestlabel([match],[anyTags])`, `vcslabeldistance()`, `vcsdirty()`, `vcsdirtysuffix()`, `vcsbranch()`, `vcscommitdate()`, `vcsauthor()`, per-file variants `vcsfileidentifier()` etc. Results **[V]**:
   - `@{vcsidentifier(7)}@{vcsdirtysuffix()}` → `fdbbc65`, and `fdbbc65-dirty` after editing a tracked file.
   - `@{vcsnearestlabel()}` → `<unknown>` for lightweight tags, `v0.2` for an annotated tag (default ignores lightweight tags).
   - Works on PCB silkscreen too: `rev @{vcsnearestlabel()} @{vcsidentifier(7)}` → `rev v0.2 ced394d` in the SVG plot and Gerber.
   - **Best combo:** project variable `GIT_REV = "@{vcsnearestlabel()}-@{vcsidentifier(7)}@{vcsdirtysuffix()}"`, used as `${GIT_REV}` in the drawing sheet and silkscreen. Plot gives `v0.2-360e10f`; `-D GIT_REV=override-123` still overrides it. **[V]**
   - **Failure modes [V]:** shallow clone (`--depth 1`, the GitHub Actions default) → hash OK, tag `<unknown>`. `git archive` export (no `.git`) → all `<unknown>`. CI must use `fetch-depth: 0`, or pass `-D` explicitly.

Note for west/baselines (D40): the stamp shows the **ee repo's** commit, not the manifest baseline tag. That is correct for traceability (the file version), but the bundle must map baseline → repo SHAs.

## 5. Review of changes in pull requests

| Option | How | Output | State |
|---|---|---|---|
| Raw `git diff` of `.kicad_sch` | s-expressions are line-oriented in KiCad 9/10 | e.g. `-(property "Value" "100K"` / `+"220K"` | **[V]** readable for value/field changes; useless for wiring/geometry |
| `kicad-cli` + image diff | export SVG for base and head (`-e -n`), rasterise (`rsvg-convert`), `compare -metric AE` / `magick -compose difference … -trim` | diff PNG + bounding box of the change | **[V]**: a 100K→220K value change gave 38 pixels changed, box at 1243,574 |
| [KiRi](https://github.com/leoheck/kiri) | web UI to step through commits, schematic sheets, layers | local web app / archive + `kiri-server` | **[R]** MIT, 722★, active 2026-06; uses `kicad-cli` for KiCad 7+ |
| [KiDiff](https://github.com/INTI-CMNB/KiDiff) (`kicad-diff`) / KiBot `diff` output | coloured overlay PDF/SVG, git plug-in | PDF | **[R]** GPL-2.0, active 2026-09 |
| [KiCad-Diff](https://github.com/Gasman2014/KiCad-Diff) | PCB layer image diff | HTML | **[R]** last push 2024 |
| ERC/netlist diff | diff of `net.xml` (minus date lines) or a normalised net list | text | **[V]** shows exactly which pins moved nets |

**Recommendation:** a local command (D46) that produces, for base vs head: (a) side-by-side + overlay PNG per
changed sheet, (b) a **semantic diff** (components added/removed/changed fields, pin↔net changes) from the XML
netlists, (c) ERC JSON delta. The semantic diff is what an agent reviewer reads; the images are for humans.
Post both as a PR comment/artifact once KiCad runs in CI.

## 6. Agent authoring

| Path | Verdict |
|---|---|
| IPC API (`kicad-python`) | KiCad 10: PCB only, needs GUI. Schematic + headless arrive in KiCad 11. **Not usable in iteration 1** for schematics. **[V]**/[R] |
| [kiutils](https://github.com/mvnmgrx/kiutils) 1.4.8 (GPL-3.0, last release 2024-02) | **Do not use.** Round-trip of a KiCad 9 file dropped all 110 `(hide yes)` flags → hidden fields became visible; also dropped `exclude_from_sim`, `pin_numbers`. KiCad still loaded it and the netlist matched, so the damage is silent. **[V]** |
| [kicad-skip](https://github.com/psychogenic/kicad-skip) 0.2.5 (LGPL-2.1, last push 2024-05) | **Works.** Read fields by `sch.symbol.R1.property.TraceID.value`; added a field by cloning a property. All 110 `hide` flags kept. Output is one-line-ish formatting, but after `kicad-cli sch upgrade --force` on both files the diff was **only the 10 lines of the new field**. **[V]** Unmaintained → risk. |
| [kicad-sch-api](https://github.com/circuit-synth/kicad-sch-api) 0.5.6 (MIT) | Claims byte-exact format and has its own MCP server; README says KiCad 7/8. **[R]** not tested |
| MCP servers | Many, fast-moving: [mixelpixx/KiCAD-MCP-Server](https://github.com/mixelpixx/KiCAD-MCP-Server) (MIT, 3.3k★, SWIG + experimental IPC, KiCad 9/10), [kicad-mcp-pro](https://github.com/oaslananka/kicad-mcp-pro) (MIT), [Seeed kicad-mcp-server](https://github.com/Seeed-Studio/kicad-mcp-server) (analysis + ERC via `kicad-cli`, no licence file), [lamaalrajih/kicad-mcp](https://github.com/lamaalrajih/kicad-mcp) (stale). **[R]** Mostly analysis; editing quality unknown. |
| [SKiDL](https://github.com/devbisme/skidl) / [atopile](https://github.com/atopile/atopile) | Circuit-as-code generating netlists. Different paradigm; a schematic drawing is then generated or absent. Not aligned with "KiCad schematic is the design artifact". **[R]** |

**Can an agent reliably create and change a schematic?** *Change*: yes, for **field/value/footprint edits**
(trace IDs, part values) — safe and verified. *Wiring changes* (place symbol, draw wires, labels) by text edit
are possible but fragile: coordinates must hit pin endpoints on the 1.27 mm grid, and symbols must be copied
into `lib_symbols`. Using **net labels on pins** instead of drawn wires makes agent edits much more robust.
*Creating* a readable schematic from scratch is not reliable today; layout quality is poor.

**Validation loop (all `kicad-cli`, all [V]):** (1) `sch upgrade --force` → canonical file and small diff,
(2) `sch erc --format json --exit-code-violations`, (3) export XML netlist and compare with the expected
connections (§8), (4) SVG export for a visual check by a human or a vision-capable agent.

## 7. CAM feasibility (iteration 2)

On the demo PCB, all with plain `kicad-cli`, exit code 0 **[V]**: `pcb export gerbers` (20 layers, X2 attributes,
job file), `pcb export drill` (Excellon), `pcb export pos --format csv --units mm`, `sch export bom`,
`pcb render` (PNG), `pcb drc --format json`. Also available: STEP/GLB, IPC-2581, ODB++. **[V]** (help only for the last three).
Gerber headers carry `%TF.ProjectId,…,rev?*%` — set the PCB title block rev (e.g. `${GIT_REV}`) so the
revision lands in X2 metadata. Feasible without KiBot; KiBot or KiCad jobsets add convenience (zip, naming).

## 8. Checking the schematic against the system model

Prototype `scripts/check_pinmap.py` (30 lines, stdlib only) **[V]**: reads `net.xml`, builds `(ref, pin) → net`,
and for each interface signal in a pin map checks that all listed pins share one net; also checks that each
expected `TraceID` is present. Result on the demo: correct signal → `OK`, wrong pin on purpose → `FAIL`,
missing trace ID → `FAIL`, exit code 1.

For the project: the pin map comes from the **interface elements in syseng** (D36), exported from SysML as JSON
(same pattern as the D42 stubs). Signals should use **net names** (net labels = SysML signal names) plus
`(ref, pin)` pairs. The same JSON can feed the devicetree check (1.6). Checks: every model signal exists as a
net with exactly the listed pins; no extra pins on interface nets (optional, warn); every connector pin used in
the model exists. For the prototype variant (Nucleo + breakouts, D37) the "schematic" is a wiring harness:
model the boards as symbols with connector pins so the same check applies.

---

## Hands-on results (exact commands)

Setup: copied `/usr/share/kicad/demos/ecc83` (KiCad 9-format file) into `hands-on/ecc83`, `git init`, added
hidden fields `TraceID=EE-CMP-R1`, `Satisfies=SYS-REQ-042` on R1, title block `(rev "${GIT_REV}")`,
`(comment 1 "git: ${GIT_REV} (${GIT_DATE})")`, project `text_variables`, and a silkscreen `gr_text "rev ${GIT_REV}"`.

| # | Command | Result |
|---|---|---|
| 1 | `kicad-cli version` | `10.0.8` |
| 2 | `kicad-cli sch export svg -D GIT_REV=2e81726 -D GIT_DATE=2026-11-14 -o out/svg ecc83-pp.kicad_sch` | OK; SVG shows `Rev: 2e81726`, `git: 2e81726 (2026-11-14)`; hidden fields not drawn |
| 3 | same without `-D` | shows project default `unversioned` |
| 4 | `kicad-cli sch export pdf -D … -o out/sch.pdf` | OK; `pdftotext` finds the rev |
| 5 | `kicad-cli sch export netlist --format kicadxml -o out/net.xml` | OK; contains `TraceID`/`Satisfies` fields |
| 6 | `kicad-cli sch export bom --fields 'Reference,Value,Footprint,TraceID,Satisfies,QUANTITY' --group-by Value` | OK; fields as columns; grouping pitfall (see §3) |
| 7 | `kicad-cli sch erc --format json --severity-all -o out/erc.json` | OK; 6 violations (missing footprint libs in the demo), JSON with schema URL |
| 8 | `kicad-cli pcb export svg -D GIT_REV=… -l F.SilkS,Edge.Cuts,F.Cu --mode-single` | OK; silkscreen text `rev 2e81726` |
| 9 | `kicad-cli pcb export gerbers / drill / pos`, `pcb drc --format json`, `pcb render` | all OK (exit 0) |
| 10 | `@{vcsidentifier()}`, `@{vcsnearestlabel()}`, `@{vcsdirty()}`, `@{vcsdirtysuffix()}`, `@{vcsbranch()}`, `@{vcscommitdate()}`, `@{vcslabeldistance()}` in title block, no `-D` | full hash, `<unknown>` (lightweight tag) / `v0.2` (annotated tag), `0`/`1`, `-dirty`, `main`, date, distance |
| 11 | project var `GIT_REV="@{vcsnearestlabel()}-@{vcsidentifier(7)}@{vcsdirtysuffix()}"` | `v0.2-360e10f`; `-D GIT_REV=override-123` overrides |
| 12 | same in `git clone --depth 1` / in a `git archive` copy | `<unknown>-360e10f` / `<unknown>-<unknown>` |
| 13 | `git status` after all exports | tracked files unchanged; `.kicad_prl` created (untracked) |
| 14 | venv: `pip install sexpdata kiutils kicad-skip kicad-python` | installed: sexpdata 1.0.2, kiutils 1.4.8, kicad-skip 0.2.5, kicad-python 0.8.0 |
| 15 | `python -I scripts/read_fields.py ecc83-pp.kicad_sch` (sexpdata) | `R1 EE-CMP-R1 SYS-REQ-042 1.5K` |
| 16 | kiutils read + add field + write | reads OK (0.01 s); writes KiCad-7-style file; **all `hide` flags lost** |
| 17 | kicad-skip read + clone field + write, then `kicad-cli sch upgrade --force` on original and edited copy, `diff` | diff = only the new property block (10 lines) |
| 18 | netlist diff original vs edited (kiutils and skip) | only the new `TraceID` field differs |
| 19 | `kicad-cli api-server` | not a command in 10.0.8 |
| 20 | Change R3 100K→220K; SVG of old/new; `compare -metric AE -fuzz 5%` | 38 px changed; bounding box locates the change |
| 21 | KiCanvas: `<kicanvas-embed src="v10.kicad_sch" controls="basic">`, served by `python -m http.server`, `firefox --headless --screenshot` | Schematic rendered correctly (KiCad 10 format); variables not resolved |
| 22 | `python -I scripts/check_pinmap.py out/net.xml scripts/pinmap.json` | OK/FAIL lines as designed, exit 1 |

Not tried: KiBot, KiRi, KiDiff, KiCad jobsets, MCP servers, kicad-sch-api, IPC API with a running GUI.

---

## Recommendations

1. **Extraction = `kicad-cli` only** (no KiBot dependency in iteration 1). One local script per ee repo (D46) runs: ERC JSON, XML netlist, SVG per sheet, BOM CSV. A small Sphinx extension in the framework repo (D34) embeds them and generates needs from the netlist fields.
2. **Trace IDs:** hidden symbol fields `TraceID` plus one field per link type of the D36 table (e.g. `Satisfies`, `Implements`). Extract from the **XML netlist**, never from a grouped BOM. Use hierarchical sheet fields for sub-circuit IDs.
3. **Git stamp:** in each KiCad project set the text variable `GIT_REV = @{vcsnearestlabel()}-@{vcsidentifier(7)}@{vcsdirtysuffix()}` (tested), and use only `${GIT_REV}` in drawing sheets and silkscreen. Locally this just works; CI uses `fetch-depth: 0` or passes `-D GIT_REV=…`. Never write stamps into tracked files. Use **annotated tags** (the `anyTags` argument for lightweight tags is documented but not tested).
4. **Agent edits:** allow field/value edits via **kicad-skip** (or a thin own sexpdata writer) followed by `kicad-cli sch upgrade --force`, ERC, netlist check. Prefer net labels over drawn wires. Ban kiutils. Re-evaluate IPC when KiCad 11 is out.
5. **Normalise on commit:** a pre-commit hook that runs `kicad-cli sch upgrade --force` on changed `.kicad_sch` keeps diffs minimal for humans and agents alike. `.gitignore`: `*.kicad_prl`, `*-backups/`, `fp-info-cache`, `_autosave-*`.
6. **PR review:** own small tool: semantic netlist/field diff (text, for agents) + SVG overlay images (for humans). Consider KiRi for interactive local review.
7. **Model check:** export interface pin maps from SysML as JSON; check against `net.xml` (prototype exists). Same JSON feeds the devicetree check.
8. **KiCanvas** only as an optional "interactive" toggle; static SVG is the normative view.

## Risks and open questions

- **D47 vs D21/D22/D31:** the PCBA design doc needs `kicad-cli` output at docs-build time, but D47 says GitHub CI does not run KiCad in iteration 1. Options: (a) use the official `kicad/kicad:10.0` Docker image in CI now (cheap, it is only kicad-cli), or (b) commit generated SVG/netlist like drawio (D38) and check them locally. **Needs a decision.**
- **KiCad version lock:** files re-saved by 10.0.8 have format `20260306` and **cannot be opened by KiCad 9**. All humans, agents and CI must use KiCad 10 (consistent with D19, but must be stated).
- **VCS functions are new** (KiCad 10, a fix landed in 10.0.2 for CLI context path) and not yet in the user manual; behaviour may change. Fallback `-D` keeps us safe.
- **Shallow clones / tarballs** give `<unknown>` stamps; CI configuration must handle this.
- **Library tooling is fragile:** kiutils corrupts silently; kicad-skip is unmaintained since 2024; MCP servers move fast and are unproven for editing. Pin versions and always validate with ERC + netlist.
- **IPC API schematic support only in KiCad 11** (from kicad-python 0.8.0 source, not from a KiCad release note). Unknown release date.
- **KiCanvas is alpha** with no versioned releases; vendor a copy.
- **KiBot is AGPL-3.0**: fine as a tool, but avoid copying its code into our extensions.
- **Prototype variant (D37):** how to model Nucleo + breakout wiring in KiCad (a "harness" schematic?) is open; KiCad 10 design variants (`--variant`) may help for product vs prototype BOMs — not yet studied.
- Open: should trace fields be filled in symbol **libraries** (part-type IDs) or per **instance** (part IDs)? Probably instance only; decide in Phase 3 (ID scheme, D17).
