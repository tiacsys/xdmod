# Document architecture (task 3.9)

Status: **AGREED 2026-11-14** (review answers → D109–D112). Built on D13, D21, D22, D25–D27, D34, D35, D43, D55, D56, D62, D73, D74, D94–D96, D98, D104, D106
(`../decisions.md`), `trace-model.md`, `views.md`, `variants.md`, `freecad-storage.md`, `../research/zdocs.md`, and the safety repo's document set.

## 1. Principles

1. **One linked set, built per repo.** Each repo builds its own documents plus its upstream documents (D35). The manifest repo builds the full set (D26) and publishes it on Pages (D55).
2. **Documents are "Doxygen-like" where possible** (D22). Authored rst gives structure and prose; extensions pull content from the models (SysML, KiCad, FreeCAD, code, test results).
3. **HTML only in iteration 1** (D43), plus `needs.json` and `objects.inv` per document for tools and agents.
4. **Variant-aware** (D106). The 150 % content is shown with configuration badges, and there is a generated page per configuration.
5. **CAD content degrades gracefully in CI** (D56). Without CAD tools, a CAD directive renders a short notice ("built locally") instead of its pictures. The **CAD-derived needs are committed** (`generated/cad-needs.json`, D110), so CI still sees the full trace graph.

## 2. Document list

| Repo | Doc id (zdocs) | Title | Content (authored + extracted) | Upstream docs it links to |
|---|---|---|---|---|
| robarm-syseng | `se-req` | Stakeholder & System Requirements Specification | problem statement, stakeholders, needs, objectives (rst); use cases (from the model); system requirements (rst, EARS + value fields) | — |
| | `se-arch` | System Architecture | context, functional, logical, 150 % product architecture, interfaces (from the model + views); features and configurations; **one generated page per configuration** | `se-req` |
| robarm-sw | `sw-req` | SW Requirements Specification | SW requirements (rst, EARS) | `se-req`, `se-arch` |
| | `sw-arch` | SW Architecture & Design | architecture and detailed design (rst); devicetree/model check result | `sw-req`, `se-arch` |
| | `sw-api` | SW API & Implementation (Doxygen) | code units (`@xdid`, `\satisfies`) | `sw-arch`, `sw-req` |
| | `sw-test-spec` | SW Test Specification | test cases from ZTEST annotations (zdocs `testmodule`, test-ID ledger) | `sw-req`, `sw-arch` |
| | `sw-test-report` | SW Test Report | Twister results (`native_sim` in CI, D101), coverage | `sw-test-spec` |
| robarm-ee | `ee-req` | EE Requirements Specification | EE requirements (rst, EARS) | `se-req`, `se-arch` |
| | `pcba-<name>` | PCBA Design: <name> (one per board, from the start, XD-ADR-0129) | overview with version; renderings and schematic (local, placeholder in CI); stackup and design-rule tables, connector pin tables (plain Python); ERC/DRC findings with acceptance (local); variants table; BOM with a column per variant in the appendix | `ee-req`, `se-arch` |
| | `proto-<name>` | Prototype Setup: <name> (one per `proto/` project, D27, D74, XD-ADR-0135) | wiring between external parts (KiCad schematic), modules, build steps | `ee-req`, `se-arch` |
| | `harness-<name>` | Harness: <name> (one per harness, XD-ADR-0127) | WireViz diagram, pin-to-pin table, harness BOM, version; links to the `pcba-<name>` documents and `EE-PORT`s it connects | `pcba-<name>` of both ends, `se-arch` |
| | `ee-test-spec` | EE Test Specification | EE test cases (rst, scripted checks) | `ee-req` |
| | `ee-test-report` | EE Test Report | results of scripted checks (JUnit) | `ee-test-spec` |
| robarm-me | `me-req` | ME Requirements Specification | ME requirements (rst, EARS) | `se-req`, `se-arch` |
| | `asm-<name>` | Assembly Design: <name> (one per top-level assembly, a chapter per sub-assembly, XD-ADR-0129) | drawings, exploded view, mass and center of gravity (local, placeholder in CI); parameters, materials, interfaces (plain Python); findings; indented BOM in the appendix (boards and harnesses one line each, with version and link) | `me-req`, `se-arch`, `pcba-<name>`, `harness-<name>` |
| | `me-test-spec` | ME Test Specification | ME test cases (rst) | `me-req` |
| | `me-test-report` | ME Test Report | results (JUnit, measurements) | `me-test-spec` |
| robarm-integration | `int-test-spec` | System & Integration Test Specification | system and integration test cases, HIL setups (rst) | `se-req`, `se-arch`, and every domain spec |
| | `int-test-report` | System & Integration Test Report | results from the evidence branch (D73); **requirement × configuration coverage matrix** (D104) | `int-test-spec` + all requirement docs |
| robarm-manifest | `robarm` | Robot Arm: Project Overview | landing page, baseline info, cross-repo trace report, overall coverage matrix, change report (needs-diff) | all of the above |
| xdmod | `xdmod-manual` | XDMOD Manual (D13) | methods, trace model, ID scheme, variant model, workflows (from `claude/framework/*`), Diátaxis structure | — |
| | `xdmod-ref` | curatrix Reference | CLI and API reference of curatrix, needs config tables (generated) | `xdmod-manual` |

The robarm documents link to `xdmod-manual` (method references). xdmod never links to robarm, because the framework doesn't know its users (D5 spirit).

**Iteration 1 (D135, changed by XD-ADR-0129):** robarm-ee and robarm-me each keep **one document** for requirements and overview (`ee-design`, `me-design`). Each board, harness and top-level assembly gets its own document from the start, created with its registry entry by `curatrix new pcba` / `new asm`. One directive set per document type; a section without data prints one fixed sentence. Test spec and report documents come once tests exist.

## 3. Registries (zdocs `documents.yaml`, D26, D35)

- Each repo's registry lists **its own documents** and **its upstream documents**, with `doc_dir` pointing into the upstream west project, e.g. `../../robarm-syseng/docs/se-req`. Until zdocs #26/#27 are fixed, indirect upstream documents are also listed by hand (the workaround from the spike).
- **Groups** (navigation): System, Software, Electrical, Mechanical, Integration, Project, Framework.
- **Prefixes** = doc ids (`se-req`, `sw-arch`, …). They are unique by convention; zdocs #34 adds a check.
- **Versions:** each document shows its own repo's version (`version_project`, zdocs #25). Until that is fixed, upstream documents built downstream show the wrong version (known workaround).
- **Strict build** for every document (D64c; zdocs #29).
- **Needs config:** one shared `needs_config.toml` from xdmod for every document (`trace-model.md` §1 principle 7).

## 4. Extensions (in xdmod, D34, D98)

| Directive / extension | Purpose | Source | CI (no CAD, D56) |
|---|---|---|---|
| `needimport` of generated needs | model, CAD and code needs into the docs | `generated/*.json` from `curatrix gen` | yes: model, code and CAD needs are all committed (D110) |
| `sysml-view` | inline editable-SVG view with links (D96) | `views/*.drawio.svg` | yes |
| `sysml-element` | table of an element's attributes, ports and relations | model JSON | yes (model JSON is committed) |
| `config-page` (generator) | one page per configuration (D106) | model JSON + needs | yes |
| `coverage-matrix` | requirement × configuration matrix (D104) | needs + test results | yes |
| `xd-pcba-*` (overview, renderings, schematic, stackup, rules, connectors, findings, variants, BOM) | the `pcba-<name>` document (task 5.21) | KiCad files (plain Python), `generated/<project>.connectors.json`, local CAM output | stackup, rules, connectors, variants, BOM: yes; renderings, schematic, findings: placeholder |
| `xd-harness` | the `harness-<name>` document (task 5.22) | WireViz YAML (plain Python + Graphviz) | yes |
| `xd-asm-*` (overview, drawing, exploded, renderings, mass, parameters, materials, interfaces, findings, subassemblies, BOM) | the `asm-<name>` document (task 5.27) | `.FCStd` files and model.json (plain Python), local CAM output (`mass.json`, `findings.json`, `renderings/<view>.png` as listed in `cam.json`, task 5.30) | overview, parameters, materials, interfaces, sub-assembly chapters, BOM: yes; drawings, exploded view, renderings, mass, findings: placeholder |
| `testmodule` (zdocs), `test-report` (sphinx-test-reports) | test specs from ZTEST, results from JUnit / run records | code, results | yes |
| `needflow` (graphviz) | trace graphs (D95) | needs | yes |

## 5. Outputs

- `build/<area>/docs/deploy/html/<doc-id>/`: HTML, plus `needs.json` and `objects.inv` per document.
- The full set in robarm-manifest goes to Pages, with `main` as "latest" plus one folder per baseline (D55, zdocs #33).
- PDF and bundles come in iteration 2 (D43).

## 6. Answered review questions (2026-11-14)

1. **Test reports** are separate documents, one per domain plus integration (D109).
2. **CAD-derived needs** are generated locally, committed (`generated/cad-needs.json`), and checked locally and at the baseline (check CK-D4). CI imports them and sees the full trace graph (D110).
3. **The XDMOD manual** is part of the robarm full set, built from the pinned xdmod (D111).
4. **One doc per PCBA and one per prototype configuration** (D112). For wiring harnesses, **WireViz** (YAML → harness diagram + BOM) is evaluated as an option. Adopted 2026-11-17 (XD-ADR-0127): one `harness-<name>` document per harness.
