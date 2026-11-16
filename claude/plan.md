# Plan — Iteration 1

Status: **AGREED 2026-11-14.** Tick boxes (`[x]`) as items are done. Every item that produces
something names it in *italics*.

## Decisions

All decisions (D1–D143) are in **`decisions.md`**. Tasks refer to them as `D<n>`.

## Phase 0 — Make the problem statement well-posed

- [x] 0.1 Resolve Q1–Q18 and record the answers in the decision table
- [x] 0.2 Plan review by a second agent; resolve its findings A1–A8 and the scope cut (→ D35–D45)
- [x] 0.3 Confirm D46 and D47
- [x] 0.4 Agree on this plan (status → AGREED)

## Phase 1 — Research (8 agents in parallel)

Each agent writes *`claude/research/<topic>.md`*. Every report contains: findings with source links, how mature
and maintained each tool is, its licence, its extension points, and concrete recommendations and risks for this
project. Where a tool is installed on this machine, the agent also **tries it hands-on** and reports what happened.

- [x] 1.1 **Traceability** (main focus) → *`traceability.md`*
      - sphinx-needs: link types, `needs.json`, `external_needs`/`needimport`, `needs_constraints`, `needs_warnings`, `needextend`, variants.
      - Linking from code and tests: sphinx-codelinks, sphinx-test-reports, OpenFastTrace-style tags.
      - Alternatives for comparison: StrictDoc, Doorstop, TRLC.
      - Whole frameworks to learn from: Eclipse S-CORE, Zephyr's safety requirements setup, useblocks tooling.
      - Questions: how to enforce the link-type table (D36); change-impact analysis; what happens when a requirement is **removed** (dangling links).
- [x] 1.2 **affirmatrix** (stale and suspect links, D44) → *`affirmatrix.md`*
      - What the tool does and how it stores the state of a link target (version or hash).
      - How it would fit sphinx-needs, zdocs, the SysML stubs (D42) and trace IDs inside CAD files (D29).
      - Gaps for this project.
- [x] 1.3 **SysML v2 and SYSMOD** → *`sysml-sysmod.md`*
      - Tools: Pilot Implementation, SysIDE (which parts are open source?), SysON, Sysand, Python parsers, standard API/JSON.
      - Views and viewpoints as defined by the standard, and existing renderers.
      - Variants for prototype vs. product (D37). Generated requirement stubs (D42). Model consistency checks.
      - SYSMOD from https://mbse4u.com/sysmod/: work products, their order, mapping to SysML v2. Is the site complete without the book?
      - Requirement docs: ISO/IEC/IEEE 29148 structure; EARS usage (D45).
      - Hands-on: parse a small `.sysml` file on this machine.
- [x] 1.4 **KiCad** → *`kicad.md`*
      - Prior art: KiCad ↔ Sphinx integrations, including older plugins that rendered PCB layouts into Sphinx; do they work with current versions?
      - Doc extraction: `kicad-cli` SVG/PDF/BOM/netlist/ERC, KiBot, IPC/Python API, custom fields for trace IDs (D29).
      - Git versioning: the repo's SHA-1 or tag in title blocks and on the PCB silkscreen (text variables, `--define-var`, KiBot).
      - Review in PRs: visual diff (KiRi, `kicad-cli` + image diff).
      - Agent authoring: can an agent reliably create and change a schematic (IPC API, s-expression libraries, MCP servers)?
      - CAM feasibility only (Gerber, drill, pick-and-place); the pipeline itself is iteration 2.
      - Hands-on: `kicad-cli` exports on this machine.
- [x] 1.5 **FreeCAD** → *`freecad.md`*
      - Prior art: FreeCAD ↔ Sphinx integrations.
      - Doc extraction: headless `FreeCADCmd`, TechDraw SVG, spreadsheet parameters, object properties for trace IDs (D29).
      - Git versioning: the repo's SHA-1 or tag in TechDraw frames (editable template texts).
      - Storage and review (D41): uncompressed save, git filters/textconv, parts as Python scripts, visual diffs.
      - Agent authoring: can an agent reliably create and change a part (Python scripting, MCP servers)?
      - CAM feasibility only (3MF/STL export).
      - Hands-on: `FreeCADCmd` export on this machine.
- [x] 1.6 **Zephyr and west** → *`zephyr-west.md`*
      - West: manifest topologies; how Zephyr handles PRs across repos, manifest bumps and CI against pinned upstream (D39).
      - Devicetree and Kconfig as a link point to the model.
      - Drivers for PCA9685 and MCP3208 on the NUCLEO-G474RE.
      - ztest/Twister results → sphinx-needs; HIL with the Twister hardware map.
      - Parameter exchange: one source for shared values (pins, PWM range, ADC resolution, link lengths) flowing from SysML into devicetree, KiCad fields and FreeCAD spreadsheets. Generate or check?
      - SPDX / `west spdx` as prior art for the bundle.
- [x] 1.7 **drawio** → *`drawio.md`*
      - File format, Python libraries, auto-layout, headless SVG export, Sphinx integration.
      - How layout could be kept across regenerations (design input for iteration 2).
      - Hands-on: generate and export one diagram on this machine.
- [x] 1.8 **zdocs** (local clone, no web) → *`zdocs.md`*
      - Registry, needs import, testmodule/Twister, the PDF set.
      - How to build upstream documents locally (D35).
      - The CMake/Zephyr-module build for non-SW repos (syseng, ee, me).
      - Gaps for ME and EE.
- [x] 1.10 **firmhold** (the user's bundle tool, `extra/firmhold`) → *`firmhold.md`*: what it does today, fit for bundles with non-firmware outputs, test results against a firmware digest
- [x] 1.11 **probatrix and the safety repo** (`extra/safety`, branch `tkaestner/kernel-unit-backlog`) → *`probatrix-safety.md`*: verification studies, lab spaces on remote machines, HIL fit, patterns to copy from safety
- [x] 1.9 Synthesis → *`claude/research/summary.md`*: integration map, tool gaps that need custom extensions, risks, proposed changes to decisions

- [x] 1.12 Resolve research conflicts X1–X8 with the user (→ D56–D65)

## Phase 2 — Thin spike (test the toolchain before designing on paper)

Local repos only; GitHub comes in Phase 4.

- [x] 2.1 One trace chain across two repos: one need → one SysML element (via stub) → one KiCad field → one test result → one trace report
- [x] 2.2 One SysML → drawio view, exported to SVG and shown in a Sphinx page
- [x] 2.3 First change scenario on the spike: change one requirement and **remove** one, then show impact and dangling links
- [x] 2.4 Write down what worked and what did not in *`claude/notes/spike.md`*

## Phase 3 — Framework definition

- [x] 3.1 *Link-type table and trace model* — draft: *`claude/framework/trace-model.md`*: artifact types per domain, link types, owner side of each (D5, D36)
- [x] 3.2 *ID prefix scheme* — draft: *`claude/framework/id-scheme.md`* for all artifact types across domains (D17)
- [x] 3.3 *SYSMOD work products* — draft: *`claude/framework/sysmod-work-products.md`* and the format each is captured in (sphinx-needs vs. `.sysml`)
- [x] 3.4 *Repo topology* — draft: *`claude/framework/repo-topology.md`*, west manifest and the cross-repo change workflow (D14, D39, D52, D61, D68). Covers submanifest files and project groups per role, e.g. EE, ME, SW, syseng, integration and a full checkout (D86). Each role must still get its upstream repos for local doc builds (D35). Zephyr: the full tree for every role for now (D87). Component libraries go in their own submanifests and groups, with shallow clones for the big ones (D88).
- [x] 3.5 *View generation* — draft: *`claude/framework/views.md`*: SysML → drawio → SVG/HTML/JSON (iteration 1: auto-layout only)
- [x] 3.6 *Consistency checks* — draft: *`claude/framework/checks.md`*: what is checked, where (local, pre-commit, CI), what fails a build vs. what only warns; suspect links (D44)
- [x] 3.7 *Variant model* — *`claude/framework/variants.md`*: prototype vs. product, and what a prototype test proves (D37)
- [x] 3.8 *FreeCAD storage and review* — draft: *`claude/framework/freecad-storage.md`* (D41)
- [x] 3.9 *Document architecture* — draft: *`claude/framework/doc-architecture.md`*: full doc list, zdocs registries, which content each doc extracts from which model (D21, D22, D27, D35)
- [x] 3.10 *Framework docs* — draft: *`claude/framework/framework-docs.md`*: a Sphinx project that describes the framework (methods, tools, trace model, workflows) (D13)
- [x] 3.11 *Human and agent workflow* — draft: *`claude/framework/workflow.md`*: authoring, review and change process (D3); agent instructions and skills per repo
- [x] 3.13 *Workspace command layer* — draft: *`claude/framework/command-layer.md`* (D66, D67): one way to run every tool from the workspace root, as subcommands of `curatrix` (D98). This includes GUI launchers for KiCad and FreeCAD that set paths, libraries, templates and environment variables (no user-global libraries, D88), CLI commands for checks and builds, and how claude is started. (No west extension alias, D116.) Builds write to `build/<area>/`. Every command runs under a memory limit and a timeout (D71). Includes the **workspace bootstrap** (west init/update, `.venv` setup from the repos' package lists, copying the launch `CLAUDE.md` from xdmod to the root, D69).
- [x] 3.12 *Domain repo layouts* — draft: *`claude/framework/repo-layouts.md`*: the internal folder layout of robarm-syseng, robarm-ee, robarm-me, robarm-sw and robarm-integration, following one common pattern.
      Covers models and CAD sources, libraries and templates, docs, extractor configs, review reports, and each repo's `requirements.txt` / `tools.yaml`.
      Also covers **locations for agent material**: each repo's `claude/` subfolder and its agent instructions (D69), skills and commands (e.g. `.claude/skills/`, `.claude/commands/`), and other data meant for agents (review checklists, templates, domain glossaries).
      Decide which of these are shared across repos (kept once in `xdmod` and pulled in via west) and which stay local to a repo. The content itself is task 3.11.
      The layout must allow N PCBAs and N assemblies (one folder each), so the PCBA trade study (6.4, D28) only adds folders.
      Libraries (D88): EE uses the tiacsys `kicad-*` repos and ME uses `FreeCAD/FreeCAD-library`, both as pinned west projects. Decide where project-local parts live (parts not in those libraries), how KiCad project library tables and FreeCAD paths refer to the workspace, and check the FreeCAD-library licence (GitHub reports none).

## Phase 4 — Workspace setup

- [x] 4.0 Install the GitHub CLI (`gh`, not installed yet) after you approve, and log in
- [x] 4.1 Toolchain: find the installed versions of Zephyr SDK, KiCad, FreeCAD, JDK 21 + SysML Pilot jar, sphinx-needs venv, elkjs, (optional) drawio, and record them in *`claude/notes/toolchain.md`* (D19). Install whatever is missing, after you approve it.
- [x] 4.2 Create the repos in tiacsys (D48, D49, D73: robarm-manifest, xdmod, robarm-syseng, robarm-ee, robarm-me, robarm-sw, robarm-integration), set rulesets (D50, D51), and run `west init` / `west update`. Repos, settings and labels done 2026-11-15; ruleset after the skeletons (4.9); west init in 4.10
- [x] 4.2b Move the workspace `claude/` folder into `xdmod/claude/` and keep its history in a first commit (D70). Convert the framework drafts into manual pages, the decision log into `XD-ADR` / `PRJ-DEC` needs, and method rules into `XD-RULE` needs, with real references everywhere (D120, D121)
- [x] 4.2c Try the sphinx-llm extension on the xdmod manual (D122)
- [x] 4.2a CI: sibling checkout by branch name (D52); Pages publishing with versions for the full set (D55)
- [x] 4.3 zdocs + sphinx-needs skeleton in each repo; upstream docs built locally (D35); full set in the manifest repo
- [x] 4.3a Pin the zdocs PR branches (#35–#38) in the manifest until they merge
- [x] 4.4 One local check command per repo (D46); CI for docs build and trace checks without CAD content (D47, D56)
- [x] 4.4a CI groundwork (Phase 3 review, R9): measure a cold CI run (full Zephyr tree, SDK, JDK/Pilot) and add caching or Zephyr's CI image; limit fallback on runners (`timeout` + `ulimit`); test the sibling resolution of D127 first; check CK-D4 in CI by reading KiCad and FreeCAD trace fields in plain Python
- [x] 4.4b `curatrix doctor` fails on tool version mismatch (rolling distro vs. D19) and generated files record the tool versions that made them
- [x] 4.4c Worktree spike (D125): registries with `../../` paths and Zephyr module discovery must see the worktree, not the main checkout
- [x] 4.5 Bump bot: a scheduled workflow in robarm-manifest opens or updates the bump PR and builds the full set (D61, D89). Needs the org setting that lets Actions create PRs, a commit status usable as a required check, and a keep-alive against GitHub's 60-day schedule pause
- [x] 4.5a Schema for HIL run records (fields, hashes, SHAs of all pinned repos, config, evidence rule), before the writer
- [x] 4.6 Orphan evidence branch in robarm-integration (D73) and the HIL run-record writer (D57, D60)
- [x] 4.8 curatrix core and xdmod tooling: CLI (root detection, env, run with limits and runner fallback, doctor, bootstrap, update, launch, docs, check runner with `checks.yaml`, gen, ids, views), `needs_config.toml`, SysML library, Sphinx extensions, bootstrap template, reusable workflows (port from the spike)
- [x] 4.9 Initial skeletons of robarm-manifest and the five domain repos (common layout, docs registries, `checks.yaml`, `ids.yaml`, package lists, `claude/`), then switch on the org ruleset (D136, D140)
- [x] 4.10 `west init` at the workspace root and bootstrap with the integration role; first full local check
- [x] 4.7 Open issues on tiacsys/zdocs (#25–#34, D62) and tiacsys/affirmatrix (#10–#18, D59), after the user approved the drafts in *`claude/notes/issue-drafts/`*
- [ ] 4.7a PRs for those issues, as agreed per issue
      - zdocs PRs opened 2026-11-14, waiting for the user's review: #35 (→ #34, sphinx-needs 9.2), #36 (→ #29, strict mode), #37 (→ #25, version_project), #38 (→ #26, imports). Not stacked; ADR index lines conflict trivially.

### Phase 4 follow-ups (non-blocking review points, to become issues)

- xdmod: convert D143 to an `XD-ADR` (and a `PRJ-DEC` for the Pages URL); remove bare IDs from generated CLI help and API docstrings
- xdmod: reference extension — register `ids.py` as a build dependency, don't unload foreign curatrix modules, replace the `[!dr]*` exclude
- xdmod: weak need links — XD-RULE-0042 (also D72/D119), XD-RULE-0041, CK-A1 → XD-RULE-0002; robarm: PRJ-DEC-0006 → D112, PRJ-DEC-0018 refines PRJ-DEC-0017
- xdmod: sphinx-llm output (HTML entities in llms.txt, duplicate .md/.html.md)
- xdmod: CI memory-limit smoke test should check a marker, not any non-zero exit
- xdmod: `curatrix work` always re-execs from the set's xdmod; README wording
- xdmod#12: provenance — FreeCAD shape records not compared in CI; stale view entries never removed
- robarm-manifest: publish job keeps the write token in its checkout; dry runs run `prepare` with write scopes; `report` has one permission too many; reusable workflow called `@main` (old baselines may rebuild differently); gh-pages history growth; actions pinned by major tag
- evidence: no proof that the firmware was built from the recorded trees; staleness compares SHAs only; optional ruleset for the `evidence` branch (owner decision)
- zdocs PRs #35–#38: review and merge by the owner, then move the zdocs pin from #36's head to zdocs main

## Phase 5 — Domain structure, interaction and tooling (EE and ME)

Inserted 2026-11-17 after the Phase 4 review (finding P4-2: the tooling the vertical bar needs was
missing and not planned). The owner's expectations, questions and answers are in
*`claude/notes/phase5-expectations.md`* (EE-1 to EE-9, ME-1 to ME-8, variants); the tasks refer to
them. The plan was reviewed by a Fable agent (findings P5-1 to P5-16); the owner's decisions on it
are at the end of the same notes file.

**How this phase runs**
- The **canary** is the spine (P5-1). It starts small (5.3) and grows with the tooling: a tooling task is done only when the canary uses it and its planted error fails; no task is closed on unit tests alone. The canary does not need to be perfect or even work: it is about the motions and the tool integration. Agents author its KiCad and FreeCAD files, with MCP servers and skills where they help (P5-12). Everything that belongs to it is owned by a system configuration `canary`, which reports, BOM totals and coverage numbers exclude (P5-16).
- **D140 stays active for the whole phase** (P5-14): agents merge after an agent review, green required checks and, for EE and ME PRs, the local CAD check run posted in the review. The owner reviews per block after the merge, against the canary with a demo script per block, and reverts or asks for fixes.
- **Spikes are time-boxed** (at most two days each) and end with a written "works / works with this fallback / cut". No tooling task starts before its spike reports.
- **Every new rule** gets an ID, a stage and a severity in *`checks.md`* before its code, and starts as a warning until it ran on the canary.

**Limits for iteration 1**

| Area | Limit |
|---|---|
| KiCad output | One shared jobset template in xdmod, copied by `curatrix new pcba`; no "Execute Command" jobs; always run on a copy under `build/`; stackup as a table (plus an optional SVG cross-section) |
| Variants | At most two variants per board and per assembly; presence by `Configs`, not by a suppressed state; Zephyr board-variant check by name, on the canary |
| Acceptance | One `accepted.yaml` format for EE and ME; a positive human marker (`Accepted-by:`); KiCad severities pinned to the template |
| FreeCAD | Master sketch only in the top-level assembly, at most ten driving parameters; collision check only between direct children of one assembly; exploded view: one day in the spike, back to the owner if it fails |
| Co-design | The `SYS-IF` budget is a box (width, depth, height above and below the board), a hole list and connector positions; StepUp pushes at least outline and holes. Keep-outs, connector positions, the harness length and route, and anything pushed back from EE: decided by the co-design spike (5.28) |
| Harness | One harness in iteration 1 |
| Library repo | Tagged boards only; at most 5 MB per file to start; the STEP path as the scripted route |
| Documents | One directive set per document type; a section without data prints one fixed sentence; no per-board layout options |
| Domain models | EE: board, connector ports, pin maps, external parts. ME: assembly, sub-assemblies, ports. No circuit block diagrams inside a board |
| Pilot time | Measured after 5.15; if one local check of robarm-ee takes more than five minutes, 5.31 is no longer optional |

**Exit criteria**
1. The canary chain is green locally with CAD content and in CI without it.
2. Every rule in *`checks.md`* has a planted error that fails: plain-Python rules in the CI fixture, tool-backed rules in a recorded local fixture run (`curatrix check fixtures --stage local`; rule, tool version, date) (P5-13).
3. `curatrix cam` ran for the canary board (both variants) and the canary assembly, from a tag and from a dirty tree, with the preview marking visible in both.
4. One co-design change went through three repos on one branch name.
5. The author loop is measured, and the numbers are in the Phase 5 review.
6. A list of what moved to iteration 2, agreed by the owner.

**A. Checks that bite and the canary seed** (the agreed "Phase 5.0" of the Phase 4 review response)
- [ ] 5.1 Check runner honesty (P4-4): a missing `checks.yaml` or an empty plan fails; each repo lists the checks it expects (`expect:`); `check` prints the checks that are off and why; a skipped `error` check fails at the baseline stage; no silent fallbacks; CK-H5 runs for the manifest repo. A PR size warning that counts only hand-written lines against the PR's base (P4-14)
- [ ] 5.2 One source for the trace model (P4-9, P4-17): `graph.py` and `ids.py` read link types, requirement types and kinds from `needs_config.toml`; a test that no copy is left; drop CK-A4 and CK-A5; the `checks.py` table as dataclasses
- [ ] 5.3 Canary step C0 (P4-1, P5-1): the chain agreed after Phase 4 (stakeholder need → SYS-REQ → system block → one KiCad sheet and one FreeCAD part saved by the real tools → one SW-DD with code → one test case → one HIL result) in the robarm repos, owned by the system configuration `canary`; the planted-error fixtures for today's rules: a fixture workspace in xdmod CI (plain-Python rules) and the local fixture command for tool-backed rules
- [ ] 5.4 CK-E2 compares numbers as numbers (ranges, unit names, thousands separators) and is a warning until it ran on real requirements; table-driven tests for `c_ears`, `c_diff`, `c_trailers`, `c_pins`, `c_hygiene_build` (P4-8)
- [ ] 5.5 Tool pins: exact only for tools that shape committed output, minimum versions for the rest; commit syseng `provenance.json`; fix xdmod#23 (P4-12, P4-17)
- [ ] 5.6 No robarm names in xdmod (P4-16): `ws.framework_repos` and the manifest URL from west

**B. Alongside the spikes and the domain blocks**
- [ ] 5.7 CI (P4-5, P4-6, P4-7, P4-10): `--base` for CK-G1 from the published `latest/` needs, and from the last baseline for CK-G2; CK-H4 from the PR base, agent commits only; a downstream full-set job on xdmod and robarm-syseng PRs; `stage: full` and `permissions:` in the manifest's `check.yml`. Stacked PRs: `curatrix work start --base <parent>`, sibling resolution through the PR's base chain, the size check and CK-H4 per layer
- [ ] 5.8 Agent material (P4-3, P4-15, P5-11): *`xdmod/claude/CLAUDE.md`*; a `/review-pr` command with requirement, model, code, KiCad and FreeCAD checklists, which for robarm-ee and robarm-me re-runs `curatrix check --stage local` with CAD content and posts the result table; the skills for 6.1–6.3 and for KiCad and FreeCAD authoring (with the MCP servers the spikes select); the rules "one SYSMOD step or one tool feature per PR", stacking, and `Accepted-by:` (agents never write it) in *`workflow.md`* and the launch `CLAUDE.md`; a demo script per block for the owner's review; the D-number note; fix the stale note in `add-a-test.rst`
- [ ] 5.9 Admin actions, after the owner approved the concrete list (D123): `integration_id` on the manifest ruleset; org default workflow token read-only; Actions may not approve PRs; remove the Admin bypass from the rulesets of all repos
- [ ] 5.10 SW and integration tooling, sized for the canary (P4-2, P5-9): CK-F2 (devicetree vs the EE board model); `SW-IMPL` and `SW-TC` extraction; test results in the docs, with the check order fixed so that the docs build sees the Twister results of the same run; a minimal trace report

**C. Spikes** (in parallel, each at most two days, with a written go/no-go and fallback; then the decisions)
- [ ] 5.11 Model spike (P5-2): two small `.sysml` files in two folders; a board def that specializes a system block, a port def that specializes an interface def, one missing redefinition, one multiple specialization; the Pilot with the upstream as library set; `realizes` and `conforms` derived from the export; what happens to upstream IDs. Result in *`claude/notes/model-spike.md`*
- [ ] 5.12 KiCad 10 spike, on the canary board (P5-3): the jobset run on a copy with the version written into its text variables; variants through the single exports (`--variant`) where a job cannot name one; orthographic renderings; ERC/DRC JSON with exclusions (are the comments in the JSON?); assembly variants (DNP, field values per variant); the XML netlist; which MCP servers can drive KiCad. Result in *`claude/notes/kicad-spike.md`*
- [ ] 5.13 FreeCAD 1.1 spike, on the canary part (P5-5, P5-6): StepUp pinned and installed workspace-locally, and which of its functions run from a script; the master sketch referenced from other documents; scripted spreadsheet writes (diff size, headless recompute, propagation); configuration tables; part presence by `Configs`; exploded view as a TechDraw view exported headless (one day); LCS with a `Port` property; collision check; version embossed at export; which MCP servers can drive FreeCAD. Result in *`claude/notes/freecad-spike.md`*
- [ ] 5.14 Decisions (`XD-ADR`), first as *proposed*, accepted after 5.11–5.13 reported (P5-2), and framework pages: domain repos refine the system model in their own `model/` by specialization, with the levels of detail (EE-6); curatrix checks conformance (every inherited port is redefined by a port whose def specializes the interface def); the domain model emits the `EE-PCBA`, `ME-ASM`, `EE-PORT`, `ME-PORT` needs and CAD files carry these IDs only as references, `EE-CMP` and `ME-PART` stay CAD-owned (P5-8); the exceptions to the peer rule: SW reads the board pin maps from EE (EE-6), ME writes board geometry into KiCad inside a co-design change (ME-5); WireViz adopted (EE-9); CAM for EE and ME in iteration 1 (changes D23/D43); iteration 1 includes a PCB layout: placement, outline and silkscreen, routing not completed, the unrouted-net DRC errors accepted (changes D43); need kinds `EE-PORT`, `ME-PORT`, `EE-HAR`; bought boards and parts are external parts (a def with ports, no CAD project), and a `proto/` project is 1:1 with a block of the prototype configuration (P5-12); board, assembly and harness tags `<name>/vX.Y.Z`, created by the owner only; the domain variant names the configurations and usages it serves, the table is computed (P5-10); syseng owns the usages it sees, the domain model the internal ones; one `accepted.yaml` format with `Accepted-by:` (P5-4); the roles change: EE needs FreeCAD, ME needs the KiCad files and libraries (P5-6); a table of all new check IDs, stages and severities. Update `needs_config.toml`, *`trace-model.md`*, *`repo-layouts.md`*, *`doc-architecture.md`*, *`checks.md`*, `tools.yaml`, the west groups and `doctor`

**D. Domain models and variants**
- [ ] 5.15 `model/` in robarm-ee and robarm-me: `checks.yaml` model section, the Pilot with syseng and the libraries as upstream, `gen model` for the domain kinds, `realizes` / `conforms` derived from specialization, the conformance check, block-diagram views of boards and assemblies. SysML library: PCBA, assembly, connector and mechanical port defs, external parts, variant names. robarm-sw gets robarm-ee as upstream (docs registry, west groups); self-model pair view `eeSw`. Measure the Pilot time
- [ ] 5.16 Variants across levels (EE-2, EE-8, ME variants, P5-10): each board or assembly variant names the system configurations and usages it serves; the table "configuration → variant per usage" is computed; a check in the domain repo against the published syseng needs: exactly one variant per usage and configuration, and the variant exists in the domain model and in KiCad / FreeCAD; board variants map to Zephyr board variants (by name, on the canary)

**E. EE on the canary** (canary step C1; EE-1 to EE-9)
- [ ] 5.17 KiCad projects (EE-1, EE-2): found by `pcba/*/*.kicad_pro` and `proto/*/*.kicad_pro`; folder check; 1:1 between a board def in the EE model and its project (the project carries the model's `EE-PCBA` ID); `curatrix new pcba <element>` creates the folder, project, library tables, the jobset and severities from the template, the version variable, the `pcba-<name>` document and its registry entry
- [ ] 5.18 Connectors and CK-F1 (EE-6): a `Port` field on every connector (a reference to the `EE-PORT`); committed `generated/<project>.connectors.json` with a freshness check; CK-F1 compares net names and pin numbers with the pin maps in the EE model; the extraction cross-checked against KiCad's XML netlist on every board (P5-15)
- [ ] 5.19 ERC and DRC (EE-7, P5-4): CK-F4a/b per board and ERC per prototype schematic; fail on errors that are neither excluded in KiCad nor accepted in `pcba/<name>/accepted.yaml` (entries keyed by rule and designators; the unrouted-net errors of a board accepted in one entry); the acceptor is a human commit with `Accepted-by:`; the project's severities equal the template; warnings listed only; stated rule: a KiCad exclusion is lost when its items move
- [ ] 5.20 EE design output (EE-3, P5-3): `curatrix cam robarm-ee [<project>]` copies the project into `build/robarm-ee/cam/<project>/<version>/`, writes the version (`git describe --match '<project>/*'`, preview marking) into the copy and runs the jobset there, with single exports per variant where needed: Gerber and drill, pick-and-place, netlist, STEP, top and bottom renderings (orthographic) and one 3D rendering, schematic PDF and SVG, stackup table (optional SVG cross-section), design-rule table, BOM CSV; plain-Python checks: frames and silkscreen use the version variable; no "Execute Command" jobs and no "Copy Files" outside the output folder
- [ ] 5.21 Board document (EE-4, EE-6, EE-7, EE-8): directives for the `pcba-<name>` document: overview, renderings and schematic (local, placeholder in CI), stackup and design rules (plain Python), connector pin tables, ERC/DRC findings with acceptance (local), variants table, BOM in the appendix (variant columns, Manufacturer and MPN warning); the plain-Python BOM reader cross-checked against `kicad-cli sch export bom --variant` on every board (P5-15)
- [ ] 5.22 One harness with WireViz (EE-9): WireViz pinned; `harness/<name>/` 1:1 with a cable def in the EE model; both ends name their `EE-PORT`, also on external parts (servo, pot); CK-F1 checks pin to pin against both ends; diagram, harness BOM and version in `curatrix cam`; a `harness-<name>` document with links to the boards it connects

**F. ME on the canary** (canary step C2; ME-1 to ME-8)
- [ ] 5.23 Assemblies (ME-1, ME-2): `assemblies/<name>/` with one top document; own parts in the assembly folder, shared parts in `parts/`; 1:1 between an assembly or sub-assembly def in the ME model and its document (the document carries the model's `ME-ASM` ID); FreeCAD links per part vs usages (syseng usages for the blocks it realizes, the ME model for internal ones, P5-10); `curatrix new asm <element>`
- [ ] 5.24 Master sketch and model-driven parameters (ME-6): the top-level assembly's master sketch driven by the parameter spreadsheet; `curatrix gen freecad-params robarm-me` writes the model values into it; interfaces as LCS with a `Port` property (reference to the `ME-PORT`); CK-F3 compares spreadsheet aliases (`<port>_<attribute>`) and LCS placements with the model, with default tolerances per kind
- [ ] 5.25 ME checks (ME-7, P5-4): recompute without errors, valid solids, collisions between direct children (joined parts may touch, library fasteners excluded), boards inside their space budget; accepted findings in `assemblies/<name>/accepted.yaml` (same format and check code as EE)
- [ ] 5.26 ME design output (ME-3): `curatrix cam robarm-me <asm>`: STEP, 3MF and STL per printed part with the print profile, TechDraw PDF and SVG, exploded view (if the spike allows), flat BOM CSV; per variant (filtered by `Configs`); version from the assembly tags, embossed on printed parts at export
- [ ] 5.27 Assembly document (ME-4, ME-8): one `asm-<name>` document per top-level assembly with a chapter per sub-assembly: drawings, exploded view, mass and center of gravity (local, placeholder in CI), parameters, materials, interfaces (plain Python), findings, indented BOM in the appendix (standard designations for fasteners, one line per board and harness); renderings come with 5.30

**G. Co-design and the board library** (canary step C3)
- [ ] 5.28 ECAD/MCAD co-design: design task with a spike, after 5.13 (ME-5, EE-9, P5-6): board space budgets (box, holes, connector positions) and the harness length and route as `SYS-IF` values; StepUp push FreeCAD → KiCad, at least outline and holes; decide keep-outs, connector positions and pushing back from EE (in, or iteration 2); pushed `.kicad_pcb` files re-saved by KiCad 10 before commit; one cross-repo branch over robarm-me, robarm-ee and robarm-syseng; who reviews what; conflicts; checks. One written scenario, run on the canary. Result: a manual page and the decision
- [ ] 5.29 Board library (EE-5, P5-7): skeleton of `robarm-freecad-pcba` (created after the owner approved it, D123; west project and group for ee and me, `checks.yaml` with `expect:`, CI, ruleset, `claude/CLAUDE.md`, licence, bump bot, full set); the scripted export (`kicad-cli pcb export step` with `--variant` and the version, a headless FreeCAD import that adds the board ID and version) of a tagged board, added by a PR of the EE agent; at most 5 MB per file to start; a check that every file names an existing board tag; a note or issue on robarm-me when a newer board version exists. Record the AGPL-3.0 licence check of StepUp

**H. End of the phase**
- [ ] 5.30 ME renderings (front, top, side, one 3D view) at the end of the phase (P5-5): compare FreeCAD's rendering (Render workbench) and Blender (pinned, headless on the STEP export); fallback TechDraw or Draft SVG projections
- [ ] 5.31 Measure the author loop on the canary (P4-11); caching only if the numbers ask for it (mandatory if one local check of robarm-ee takes more than five minutes)
- [ ] 5.32 Manual: how-to pages for the EE and ME roles (new board, new assembly, design output, a co-design change; the owner reviews EE and ME PRs from a local docs build); the recorded local fixture run; the list of what moved to iteration 2, agreed by the owner; then a review of Phase 5 by another agent, like the Phase 4 review

## Phase 6 — Iteration 1 content (T-shape)

**Horizontal bar: system level (syseng)**
- [ ] 6.1 Problem statement, stakeholders, system context
- [ ] 6.2 Stakeholder needs and use cases (mirror, store pose, recall pose, …)
- [ ] 6.3 System requirements, including interfaces and performance (latency, update rate, accuracy)
- [ ] 6.4 Functional (short, D85) and logical architecture in SysML; product architecture down to EE/ME/SW elements; trade study on the PCBA split (D28)
- [ ] 6.5 Feature model, configurations (prototype, product) and the 150 % product architecture with PLEML; `curatrix check variants`; the prototype's mechanics: bench rig and printed arm are two variants of one assembly (D102–D107; owner 2026-11-17)
- [ ] 6.6 Generated views (drawio → SVG) embedded in the syseng docs

**Vertical bar: one joint, end to end (prototype variant)**
- [ ] 6.7 Choose the joint and refine its requirements into EE/ME/SW requirements; define its peer interfaces in syseng (D36)
- [ ] 6.7a The joint's cables as WireViz harnesses (adopted, 5.14 and 5.22); prototype jumper wiring stays a KiCad schematic per prototype setup (D74)
- [ ] 6.8 Prototype: model the Nucleo + PCA9685 + MCP3208 + SG90 + pot setup and its wiring
- [ ] 6.9 EE: product schematic for the joint, rendered in its `pcba-<name>` document and its PCB layout (placement, outline, silkscreen; routing not completed, unrouted-net DRC errors accepted, 5.14)
- [ ] 6.10 ME: joint assembly in FreeCAD (servo mount, link, pot mount) on the master sketch, rendered in its `asm-<name>` document
- [ ] 6.11 SW: Zephyr application with devicetree overlay checked against the model; reads one pot and drives one servo
- [ ] 6.12 Verification: ztest/Twister and HIL tests on the prototype, results traced to requirements
- [ ] 6.13 Consistency report: complete traces for the joint, coverage gaps for the rest of the system

## Phase 7 — Change demonstration and retrospective

- [ ] 6.14 First baseline `baseline/v0.1.0` (gates, tag, release); it is the "before" state for 7.1
- [ ] 7.1 Change scenario on the real content: add, change and **remove** a requirement; show impact analysis, suspect links, propagation and re-verification
- [ ] 7.1a Second baseline `baseline/v0.2.0` after the change scenario
- [ ] 7.2 Retrospective in *`claude/notes/`*: what worked, which tool gaps remain, and the scope of iteration 2

## Iteration 2 backlog
- Technical enforcement of agent limits: GitHub App identity or signed commits (D134)
- Variant rule V6, `configs` derivation (T1), per-configuration pages (D135)
- FreeCAD review report as Pages preview (D108, D135)
- SW architecture as a SysML sub-model in robarm-sw (D76)

- Bundles built with the user's bundling tool (D24, D38, D40); the EE and ME CAM output itself moved to 5.20 and 5.26
- CAM output, renderings and ERC/DRC reports in CI and on Pages (iteration 1: local only, placeholder in CI)
- A devicetree generated from the KiCad schematic (EE-6)
- Printability checks for printed parts (minimum wall, overhang) (ME-7)
- Simulation models from the ME assemblies (ME-5)
- BOM totals over all instances in the system (EE-8)
- Change impact (CK-G1) per layer of a stacked PR
- Completed PCB routing of the product boards (iteration 1 stops before routing, 5.14)
- GLB export of assemblies (ME-3; STEP covers iteration 1)
- EE pushing geometry back through StepUp, unless the co-design spike (5.28) takes it in
- Warnings for board or assembly variants that no configuration uses
- A Zephyr board for the product board (iteration 1 uses the prototype's Nucleo)
- More than one harness; more than two variants per board or assembly; circuit block diagrams inside a board
- Linked PDF document set
- Layout keeping in drawio (D2)
- Docker image with all tools, for CI (D19)
- Document control (D33)

The review log is in `decisions.md`.
