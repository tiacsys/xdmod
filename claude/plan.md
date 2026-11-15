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
      The layout must allow N PCBAs and N assemblies (one folder each), so the PCBA trade study (5.4, D28) only adds folders.
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

## Phase 5 — Iteration 1 content (T-shape)

**Horizontal bar: system level (syseng)**
- [ ] 5.1 Problem statement, stakeholders, system context
- [ ] 5.2 Stakeholder needs and use cases (mirror, store pose, recall pose, …)
- [ ] 5.3 System requirements, including interfaces and performance (latency, update rate, accuracy)
- [ ] 5.4 Functional (short, D85) and logical architecture in SysML; product architecture down to EE/ME/SW elements; trade study on the PCBA split (D28)
- [ ] 5.5 Feature model, configurations (prototype, product) and the 150 % product architecture with PLEML; `curatrix check variants`; confirm the prototype's mechanics (bench rig vs. printed arm) (D102–D107)
- [ ] 5.6 Generated views (drawio → SVG) embedded in the syseng docs

**Vertical bar: one joint, end to end (prototype variant)**
- [ ] 5.7 Choose the joint and refine its requirements into EE/ME/SW requirements; define its peer interfaces in syseng (D36)
- [ ] 5.7a Evaluate **WireViz** for wiring harnesses (D112): prototype jumper wiring and cables between boards; YAML in robarm-ee, diagram and BOM in the `proto-<config>` doc; compare with a KiCad wiring schematic
- [ ] 5.8 Prototype: model the Nucleo + PCA9685 + MCP3208 + SG90 + pot setup and its wiring
- [ ] 5.9 EE: product schematic for the joint (no PCB layout, D43), rendered in the PCBA doc
- [ ] 5.10 ME: joint parts in FreeCAD (servo mount, link, pot mount), drawings rendered in the ME design doc
- [ ] 5.11 SW: Zephyr application with devicetree overlay checked against the model; reads one pot and drives one servo
- [ ] 5.12 Verification: ztest/Twister and HIL tests on the prototype, results traced to requirements
- [ ] 5.13 Consistency report: complete traces for the joint, coverage gaps for the rest of the system

## Phase 6 — Change demonstration and retrospective

- [ ] 5.14 First baseline `baseline/v0.1.0` (gates, tag, release); it is the "before" state for 6.1
- [ ] 6.1 Change scenario on the real content: add, change and **remove** a requirement; show impact analysis, suspect links, propagation and re-verification
- [ ] 6.1a Second baseline `baseline/v0.2.0` after the change scenario
- [ ] 6.2 Retrospective in *`claude/notes/`*: what worked, which tool gaps remain, and the scope of iteration 2

## Iteration 2 backlog
- Technical enforcement of agent limits: GitHub App identity or signed commits (D134)
- Variant rule V6, `configs` derivation (T1), per-configuration pages (D135)
- FreeCAD review report as Pages preview (D108, D135)
- SW architecture as a SysML sub-model in robarm-sw (D76)

- CAM pipeline (D23, D30) and bundles built with the user's bundling tool (D24, D38, D40)
- Linked PDF document set
- Layout keeping in drawio (D2)
- Product PCB layout, incl. git version on the silkscreen
- Docker image with all tools, for CI (D19)
- Document control (D33)

The review log is in `decisions.md`.
