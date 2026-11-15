# Research synthesis — Phase 1

Date: 2026-11-14. This file sums up the 10 research reports in this folder. Each section names its source report.
Decisions are referenced as D<n> from `claude/plan.md`.

## 1. The integration map

```
            syseng (sphinx-needs + SysML v2)
   needs ──► generated stubs (.sysml) ──► Pilot (jshell) ──► model JSON
     │                                                     │
     │                         ┌───────────────────────────┼────────────────────┐
     ▼                         ▼                           ▼                    ▼
 needs.json             drawio views (own writer     needs from model      interface / pin maps
 (per doc, zdocs)        + elkjs, SVG via headless   (extractor)            and parameters
     │                   browser)                                              │ (check, not generate)
     │                                                                         ▼
     ├──────────► ee:  kicad-cli → SVG, netlist (hidden trace fields), ERC ── netlist vs pin map
     ├──────────► me:  Document.xml → trace IDs + parameters; FreeCAD → STL/3MF/STEP/GLB, drawings
     └──────────► sw:  Doxygen \satisfies / ZTEST \verifies → test spec; Twister → test report;
                       devicetree checked against model (own binding with trace-id)
                                  │
                    HIL run record: sha256(zephyr.bin) + repo SHAs + Twister JUnit
                                  │ (iteration 2)
                                  ▼
                firmhold: one signed release index per baseline (fw, docs, CAM, evidence)
```

Every domain gets an **extractor** that writes needs in `needs.json` format. zdocs imports them into the docs.
sphinx-needs checks the link-type table. A `needs-diff` tool shows the impact of a change.

## 2. Toolchain per area (recommended)

| Area | Recommended | Status on this machine | Source |
|---|---|---|---|
| Requirements, traces | sphinx-needs 9.2 (pinned), link types declared **per need type** with schema rules; strict build (`-W --keep-going`) | not installed → venv | traceability, zdocs |
| Doc engine | zdocs; non-SW repos need only a 13 MB Zephyr subset, no SDK | clone available | zdocs |
| SysML v2 | OMG Pilot Implementation 0.63.x driven through `jshell` (check, `expose`/`filter`, JSON export); own Python tools on the JSON; Sysand for libraries | JDK 21 + jar not installed | sysml-sysmod |
| SYSMOD | Website + `mbse4u/sysmod-sysmlv2` library (Apache-2.0); the library loads with 0 errors | — | sysml-sysmod |
| Views | Own Python drawio writer (stable IDs = qualified names), elkjs layered layout, SVG via headless Firefox + drawio viewer, own `sysml-view` directive that puts the SVG inline | Firefox ok; drawio desktop not installed (optional) | drawio |
| EE | `kicad-cli` only (KiCad 10.0.8); trace IDs as hidden symbol fields, read from the XML netlist; `${GIT_REV}` via KiCad 10 `@{vcs…}` functions | installed | kicad |
| ME | `FreeCADCmd` (1.1.4) for exports; trace IDs and parameters read from `Document.xml` with plain Python; drawings via GUI binary offscreen | installed | freecad |
| SW | Zephyr 4.4.2, upstream PCA9685 + MCP3208 drivers (build ok, 43.7 KB); devicetree **checked** against the model | SDK in `ws-up` | zephyr-west |
| Evidence | Iteration 1: `west twister --device-testing` + one record per run (probatrix evidence rule, `sha256(zephyr.bin)`) | — | probatrix-safety, firmhold |
| Bundle | firmhold (iteration 2): one signed release index per baseline | pre-alpha, internal GitLab | firmhold |
| Suspect links | affirmatrix (needs work, see §4) or a Doorstop-style stamp in the child need | — | affirmatrix |

## 3. What we must build ourselves (framework repo, D34)

1. **Shared need-type and link-type module** (`needs_config` + schema rules), and a document generated from it (task 3.1). (traceability, probatrix-safety)
2. **Extractors to `needs.json`**: SysML JSON, KiCad netlist, FreeCAD `Document.xml`, devicetree. (all domain reports)
3. **Requirement and concern stub generator** for SysML (D42), with a CI check. (sysml-sysmod)
4. **drawio view generator** + `sysml-view` Sphinx directive + a content-only CI check. (drawio)
5. **Sphinx extensions** for KiCad and FreeCAD content in docs (about 150 lines each). (kicad, freecad)
6. **Cross-repo coverage check**: sphinx-needs skips coverage checks for imported (external) needs. (traceability)
7. **`needs-diff`** for change impact between two revisions. (traceability)
8. **Checks**: netlist vs. pin map, devicetree vs. model, variant selection (no tool checks it). (kicad, zephyr-west, sysml-sysmod)
9. **HIL run record** writer (hashes, SHAs, Twister JUnit → test-report needs). (probatrix-safety, firmhold)
10. **FreeCAD textconv + review report** (if D41 goes that way). (freecad)

To copy from `safety`: `needs_config.toml` (but declare link types per need type), `documents.yaml` style,
`assign_testids.py` + `testids.yaml`, `test-scope.yaml`, `testspec_check.py`, `satisfies_check.py`, the
accepted-findings file, and the `annotate-ztest` agent command. (probatrix-safety)

## 4. Cross-cutting conflicts (need a decision)

These came up in more than one report.

| # | Conflict | Reports | Options |
|---|---|---|---|
| X1 | **What GitHub CI builds in iteration 1 (D47).** zdocs needs a Zephyr subset; PCBA docs need `kicad-cli`; FreeCAD drawings need the GUI binary; CAD-derived needs are part of the trace graph. | zephyr-west, kicad, freecad, traceability, zdocs | (a) CI uses the official KiCad Docker image + Zephyr subset; FreeCAD drawings are committed SVGs. (b) Commit all generated CAD outputs (SVG, netlist, needs JSON) like drawio files. (c) CAD content only in local builds; CI traces are partial. |
| X2 | **Where HIL evidence lives in iteration 1** (D8, D38, D43). safety keeps evidence out of git; firmhold can't carry it yet. | zephyr-west, firmhold, probatrix-safety | (a) Small run records committed to the SW repo via PR. (b) Records as release assets / CI artifacts. (c) A probatrix-style lab space on this machine, imported into the docs. |
| X3 | **May agents confirm evidence?** affirmatrix and probatrix are human-only by design. D3 says agents are first-class. | affirmatrix, probatrix-safety | (a) Agents propose, only humans affirm. (b) Agents may affirm, marked as agent; some link types need a human. (c) Agents equal to humans. |
| X4 | **Suspect-link mechanism in iteration 1.** affirmatrix reads one `needs.json`, has fixed link types, stores state in a central `case` branch. | affirmatrix, traceability | (a) Adapt affirmatrix (owner work: cross-repo needs, open link types). (b) Doorstop-style stamp (parent hash) stored in the child need, using sphinx-needs hash fields. (c) Defer to iteration 2. |
| X5 | **Rebase merge (D50) vs. recorded commit SHAs.** affirmatrix, probatrix and firmhold record SHAs; PR-branch SHAs are not on `main` after a rebase merge. | affirmatrix, probatrix-safety, zephyr-west | (a) Record evidence only from `main` (after merge). (b) Use merge commits so PR SHAs stay reachable. (c) Rely on content hashes, not commit SHAs. |
| X6 | **Cross-repo change flow (D52).** Zephyr/Nordic use a manifest PR that points at `pull/N/head` and a `Manifest-PR:` line; tested with west. A bump bot keeps downstream current. | zephyr-west | (a) Keep D52 (same branch name). (b) Zephyr-style manifest PR + `Manifest-PR:` line + bump bot. (c) Both: branch name for local work, manifest PR for CI. |
| X7 | **zdocs gaps** for D35: `version_project` ignored for Sphinx docs; every indirect upstream doc must be listed by hand; no "import only" mode. | zdocs | (a) Owner fixes in zdocs. (b) Work around in the framework. |
| X8 | **FreeCAD storage (D41).** | freecad | (1) Uncompressed `.FCStd` + git textconv + CI review report (recommended). (2) Simple parts as Python scripts. (3) Unzipped storage. |

## 5. Small corrections to apply without a new decision

- **D38:** "matches the model" means content (labels, parents, edge ends, kinds, links), not geometry. (drawio)
- **D42:** generate `concern` stubs for stakeholder needs and `requirement` stubs for system requirements, so SYSMOD's `frame` link is kept. (sysml-sysmod)
- **D46/D47:** all doc builds run strict (`-W --keep-going`); otherwise broken links pass. Use zdocs' `requirements-ci.txt` pins. (zdocs, traceability)
- **D54:** OCI tags can't contain `/`; map `baseline/vX.Y.Z` → `X.Y.Z` for firmhold. (firmhold)
- **Requirement removal:** mark `retired` first, delete later; never reuse IDs. (traceability)
- **Devicetree:** own binding (e.g. `robot,joint` with `trace-id`); don't add properties to upstream nodes. (zephyr-west)
- **CI checkout:** `fetch-depth: 0` and annotated tags, for KiCad's `@{vcs…}` functions. (kicad)
- **Task 3.7:** variant selection checks must be custom-built. (sysml-sysmod)
- **Task 4.1:** add JDK 21, the Pilot jar, a sphinx-needs venv; drawio desktop is optional; `gh`. (sysml-sysmod, drawio)

## 6. Top risks

1. **Young tools.** sphinx-needs schema features are weeks old; the SysML Pilot API changes monthly; firmhold and affirmatrix are pre-alpha. → Pin versions; keep our code thin.
2. **Agent editing of CAD.** KiCad 10 IPC can't edit schematics (KiCad 11 announced); `kiutils` drops hidden flags; `kicad-skip` is unmaintained. FreeCAD MCP servers need the GUI. → Agents edit CAD through small, tested scripts; humans do complex layout.
3. **Review of binary or noisy files** on GitHub (`.FCStd`, KiCad diffs). → CI posts a visual review report on each PR.
4. **Cross-repo coverage** can't fail a downstream build out of the box. → Own check + full-set build.
5. **Version skew:** KiCad 10 files don't open in KiCad 9; TechDraw export may break between FreeCAD versions; the SDK path depends on `ws-up`. → D19 pins + the Docker image in iteration 2.
6. **ISO 29148 outlines** in the SYSMOD report are from memory (paywalled). → Check against a copy.

## 7. Housekeeping

- A firmhold test pulled the Docker image `ghcr.io/project-zot/zot-linux-amd64:latest` (330 MB). No container is running. Remove with `docker rmi …` if wanted.
- Findings for the tool owner are listed in: zdocs.md, affirmatrix.md, firmhold.md, probatrix-safety.md.
