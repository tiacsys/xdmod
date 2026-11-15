# Research 1.3 — SysML v2 textual tooling and SYSMOD

Date: 2026-11-14. Author: research agent 1.3.

Legend: **[verified]** = I ran it on this machine. **[read]** = taken from a web page or repo, not run.
**[known]** = from general knowledge, not checked online today.

Scratch dir with all files, scripts and outputs:
`/tmp/claude-1000/-home-tobias-z-wrk-ws-syseng/cc4a5268-5423-4e94-be0d-4c1055bbe07f/scratchpad/research-sysml`

## Summary

- **The OMG Pilot Implementation is the best open-source basis.** It parses, resolves names, type-checks,
  evaluates `expose`/`filter` of views and exports the model as Systems-Modeling-API JSON. It has no
  official CLI, but its Java API (`SysMLInteractive`) works headless. One run (load library, check
  4 files, export JSON) took **11 s** on this machine. **[verified]**
- **Syside (Sensmetry) is not an option for our core tooling.** The Python library / CLI ("Syside Automator",
  `pip install syside`, v0.11.0) is proprietary and refuses to run without a paid licence key. The free
  part is the VS Code editor extension. **[verified for Automator, read for editor]**
- **Sysand** (MIT/Apache-2.0) is a useful package manager for SysML libraries (`.kpar`). It does not
  validate models. We can use it later to share the SYSMOD library and our stub package. **[verified]**
- **Other open parsers are not ready** as a semantic basis: `sysml2` (C) segfaults on JSON export and
  misses dangling references; `sysml2py` and `tree-sitter-sysml` only parse syntax. They are fine for
  quick syntax checks or editors. **[verified]**
- **SYSMOD v5 (5.1.x) is fully described on the website** plus the Apache-2.0 GitHub library
  `mbse4u/sysmod-sysmlv2`. The book covers SYSMOD v3 / SysML v1, so we do not need it. **[read]**
  The SYSMOD library and the Delivery Drone example load in the Pilot 0.63.1 with only a few errors
  (all in the example, none in the library). **[verified]**
- **SYSMOD keeps needs and requirements inside SysML** (`concern` for needs, `requirement` with `frame`
  links). Our D6/D42 keep them in sphinx-needs. That works, but the stub generator must make
  **`concern` stubs for stakeholder needs** and **`requirement` stubs for system requirements**, or the
  SYSMOD `frame` trace is lost. See "Contradictions".
- **Requirement stubs (D42) are sound.** The Pilot accepts a generated `library package` of
  `requirement def <'SYS_REQ_001'> Name` plus usages, and `satisfy` resolves. A removed stub gives a
  clear error ("Couldn't resolve reference to Feature 'sysReq999'"), so dangling SysML links fail CI. **[verified]**
- **Variants work for parsing, not for checking.** `variation part` / `variant part` parse and export
  (`VariantMembership`), but the Pilot does **not** check that a configuration picks a valid variant,
  and its PlantUML IBD renderer **breaks on a variation**. We need our own checks. **[verified]**
- **Views:** the standard gives `view`, `viewpoint`, `expose`, `filter`, `render`. We can define our own
  `rendering def DrawioRendering`. The Pilot exports the evaluated `exposedElement` list, which is
  exactly the input our drawio generator needs. **[verified]**

## Tool comparison

| Tool | Licence | Maturity / maintenance | Headless / CLI | Semantic checks | Machine-readable export | Notes |
|---|---|---|---|---|---|---|
| **SysML v2 Pilot Implementation** (OMG, Java/Xtext) — [repo](https://github.com/Systems-Modeling/SysML-v2-Pilot-Implementation), [release](https://github.com/Systems-Modeling/SysML-v2-Release/releases) | EPL-2.0 (some parts GPL, see LICENSE-GPL) | Reference implementation. Monthly releases; latest 2026-09.1 (30 Oct 2026), kernel 0.63.1. | No official CLI. Jupyter kernel, Eclipse editor. **Java API works headless via `jshell` [verified]**. Needs Java 21. | Full: name resolution, typing, many validation rules. **[verified]** | `%export` / `SysMLInteractive.export()` → JSON (API format). `%viz` → SVG via bundled PlantUML. **[verified]** | 133 MB jar + library. Bundled PlantUML is old (1.2022.7). |
| **Syside** (Sensmetry) — [site](https://sensmetry.com/syside/), [PyPI](https://pypi.org/project/syside/) | Automator/CLI: **proprietary**, paid (30-day trial). Editor extension: free. Old `sysml-2ls` was open, now legacy. | Active, commercial. | Python lib + CLI exist, **but need a licence key** (`License check failed`). **[verified]** | Yes (per docs). **[read]** | JSON import/export, ReqIF (per README). **[read]** | Good product, but conflicts with "all tools open source". |
| **Sysand** (Sensmetry) — [repo](https://github.com/sensmetry/sysand) | MIT / Apache-2.0 | Young (v0.2.1 on PyPI). Active. | CLI `sysand`, Python + Java bindings. **[verified]** | None (package manager only). | Builds `.kpar` (KerML project archive) with `.project.json` / `.meta.json` index. **[verified]** | Can share SYSMOD library and our stubs as versioned packages; index at sysand.com. |
| **SysON** (Obeo/Eclipse) — [repo](https://github.com/eclipse-syson/syson), [site](https://mbse-syson.org) | EPL-2.0 | Active; 2026.9 released. **[read]** | Web server (Docker), no CLI. REST API. **[read]** | Yes (in GUI). | Textual import/export (improving each release), REST API. **[read]** | Good graphical viewer/editor for humans. Not a CI tool. Not tested. |
| **SysML-v2-API-Services** — [repo](https://github.com/Systems-Modeling/SysML-v2-API-Services) | EPL-2.0 | Proof of concept, Java 11 + Play + PostgreSQL. **[read]** | REST server. | No. | API JSON. | Reference server for the Systems Modeling API. Too heavy for us. |
| **sysml2** (C) — [repo](https://github.com/zbigniewsobiecki/sysml2) | MIT | Small (9 stars), last commit 2026-02. | CLI. Needed a build fix (`-D_POSIX_C_SOURCE`). **[verified]** | Partial. Missed a dangling `satisfy` target. **[verified]** | `-f json` **segfaulted** (exit 139). **[verified]** | Rejected valid `render Views::asInterconnectionDiagram;`. Not usable. |
| **sysml2py** — [PyPI](https://pypi.org/project/sysml2py/) | MIT | v1.2.0 (Oct 2026). | Python API `read_model`, `print_model`. **[verified]** | Syntax only. | Python AST; round-trip print (not byte-identical). **[verified]** | Could help agents edit text, not validate. |
| **tree-sitter-sysml** — [PyPI](https://pypi.org/project/tree-sitter-sysml/) | MIT | v0.1.0 (Mar 2026). | Python/Rust bindings. **[verified]** | Syntax only. | Concrete syntax tree. | Parsed our test file with no errors. Good for editors and fast pre-commit syntax check. |
| Others seen, not tested: [MontiCore sysmlv2](https://github.com/MontiCore/sysmlv2) (Java CLI), [SysML2Tools](https://github.com/demaconsulting/SysML2Tools) (.NET, lint/render), [sysml-v2-parser](https://lib.rs/crates/sysml-v2-parser) (Rust), [pysysmlv2](https://github.com/HansBug/pysysmlv2), [sysmlpy](https://github.com/conconga/sysmlpy) | mostly MIT/Apache | early | CLIs | partial | various | Worth a re-check in iteration 2. |

**Systems Modeling API and Services** (standard, version 1.0 is final per the 2026-01 release notes **[read]**):
a REST/HTTP API plus a JSON serialisation of the model. Each element is `{"@id", "@type", ...properties}`;
references are `{"@id": "..."}`. The Pilot `export()` writes a list of `{identity:{@id}, payload:{@type, ...}}`
records in this format **[verified]**. It includes derived properties such as `qualifiedName`,
`declaredShortName`, `isVariation`, `exposedElement`. This is the format our own tools should read.

**Best basis for our tooling:** the Pilot (validation and JSON export) + our own Python code that reads the
JSON (needs export, drawio views, custom checks). See Recommendations.

## Findings

### 2. Views and viewpoints

Standard concepts (SysML v2 spec, clause on views; library `Views.sysml`, `StandardViewDefinitions.sysml`) **[read + verified in library]**:

- `viewpoint def` — what a stakeholder wants to see. It `frame`s one or more `concern`s.
- `view def` — a kind of view. It may `satisfy` a viewpoint, has `filter` conditions (e.g.
  `filter @SysML::PartUsage;`) and a `render` (how to draw it).
- `view` (usage) — a concrete view. `expose X::**;` selects the model content. Filters reduce it.
- `rendering` — standard renderings: `asTreeDiagram`, `asInterconnectionDiagram`, `asTextualNotation`,
  `asElementTable`. Kinds: `TextualRendering`, `GraphicalRendering`, `TabularRendering`.
- Standard view defs: `GeneralView`, `InterconnectionView`, `ActionFlowView`, `StateTransitionView`,
  `SequenceView`, `GeometryView`, `GridView`, `BrowserView`.

What I verified with the Pilot:

- A custom `rendering def DrawioRendering :> GraphicalRendering { attribute layout : String; }`, a
  `viewpoint def` framing a `concern`, a `view def` with `satisfy`, `filter ... or ...`, and `render`
  all validate. File: `model/Views.sysml`.
- The exported JSON of `view jointWiring { expose Arm::JointSystem::**; }` contains `exposedElement` with
  11 elements (parts, ports, connections, variants) — the filter was applied (the `satisfy` was filtered out).
  **So the Pilot does the selection; our generator only has to lay out and draw.**
- `viewRendering` was `null` on the view usage in the export (the rendering sits on the view def). Our tool
  must follow the type to find the rendering.
- Existing renderers: Pilot `%viz` / `%view` → PlantUML → SVG. Tree view of the package worked well.
  Interconnection view of a part **with a `variation`** failed with a PlantUML syntax error. An IBD without
  variation rendered fine. SysON and Syside have their own diagram renderers (GUI). No open drawio renderer found.

How far the standard helps: it gives us a **standard, in-model way to declare views** (what to show, for which
concern, with which rendering). It does **not** define layout or a diagram file format. Layout and drawio
mapping are ours. SYSMOD v5 already ships viewpoint and view defs per step (`SYSMODViews.sysml`, e.g.
`ProblemStatementView`, `LogicalArchitectureView`) that we can reuse and give our own drawio rendering.

### 3. Variants (D37)

SysML v2 has `variation` (a definition or usage whose members are the allowed choices) and `variant`
(one choice). A configuration picks a variant by redefinition. Example I validated **[verified]**:

```sysml
part def JointSystem {
    part sensor : AngleSensor;
    variation part controller : JointController {
        variant part prototype : NucleoG474RE;
        variant part product   : CustomCtrlPcba;
    }
    part actuator : JointActuator;
    connect sensor.angleOut to controller.angleIn;
    connect controller.cmdOut to actuator.cmdIn;
    satisfy sysReq001 by controller;
}
part prototypeJoint : JointSystem {
    part :>> controller = controller::prototype;
}
```

Findings:

- Parses and exports. JSON has `isVariation: true` and `VariantMembership` for `prototype` and `product`.
- **The Pilot does not enforce the choice.** `part :>> controller = sensor;` and `part :>> controller : SG90;`
  gave **no error**. We need a custom check: "each configuration binds every variation to one of its variants".
- The Pilot IBD renderer breaks on variations (see 2).
- Modeling advice: keep the **logical architecture variant-free** (SYSMOD `logicalContext`). Put variations
  in the **product architecture** (SYSMOD `productContext`), with `prototype` and `product` as two
  configurations. Allocation `logical2product` stays one link per logical element. Then "what a prototype
  test proves" (D37) = requirements satisfied by elements that are common, or that are in the prototype
  configuration.
- EARS "Where <feature is included>" requirements fit variant-specific requirements well.

### 4. Requirement stubs (D42)

**Sound. Verified with the Pilot.** Generated file (from `needs.json`, never edited):

```sysml
// GENERATED from needs.json - do not edit by hand (D42).
library package RequirementStubs {
    private import TraceMeta::*;
    requirement def <'SYS_REQ_001'> FollowerMirrorsLeader {
        doc /* summary only; source of truth is sphinx-needs */
        @NeedRef { needId = "SYS_REQ_001"; needType = "sysreq"; }
    }
    requirement <'SYS_REQ_001.u'> sysReq001 : FollowerMirrorsLeader;
}
```

with

```sysml
library package TraceMeta {
    private import ScalarValues::*;
    metadata def NeedRef { attribute needId : String; attribute needType : String; }
    metadata def TraceId { attribute id : String; }
}
```

Points:

- **Short names** `<'ID'>` carry the need ID. They show up as `declaredShortName` in the JSON **[verified]**.
  Quotes are needed when an ID has `-` or `.` (e.g. `'SYS-REQ-001'`).
- `satisfy` needs a **requirement usage** (or a def). I generated both def and usage. A `library package`
  marks the stubs as read-only in intent.
- **Removal works as wanted:** satisfying a missing stub fails with
  `Couldn't resolve reference to Feature 'sysReq999'` **[verified]**. So when a need is removed and the stubs
  are regenerated, CI flags every SysML link to it.
- Metadata (`@NeedRef`) duplicates the short name but makes the intent machine-checkable. Optional.
- **For SYSMOD:** stakeholder needs are `concern`s in SYSMOD, and requirements `frame` them. So generate
  `concern def <'STK_NEED_003'> ...` for needs and `requirement def` for system requirements. The
  requirement → need link then stays in sphinx-needs (D5/D6), and we do **not** write `frame` in SysML,
  or we generate it from the needs links too. Decide in Phase 3.3.
- Keep the stub text short (title only). Full text in the stub invites people to edit it, and drifts.

Alternatives considered:

- **Only metadata / doc tags** (`@NeedRef { needId = "SYS_REQ_001"; }` on a design element, no stub):
  no native `satisfy`, no name resolution, our tool must check every ID. Weaker.
- **Short name only, no stub**: impossible, a reference needs a target element.
- **IDs in `doc` text**: not machine-safe. Avoid.

How SysML elements carry trace IDs **out** to sphinx-needs:

- Give every element that docs and other domains must reference a **short name** as its trace ID
  (e.g. `part def <'LA_JOINT_CTRL'> JointController`), or a `@TraceId { id = "..."; }` metadata.
  Short names are shorter and native; metadata allows extra fields (status, owner). Both export to JSON **[verified]**.
- Our exporter turns the Pilot JSON into a `needs.json`-compatible file (one need per tagged element, type
  e.g. `sysml_part`, links from `satisfy` → stub ID, `allocate`, `refines` etc.). sphinx-needs imports it with
  `needimport` / `external_needs` (see report 1.1). The backlinks (need ← SysML) are computed, as D5 wants.

### 5. Model consistency checks from the command line

What the Pilot gives for free **[verified]**:

- Syntax errors (with line/column).
- Name resolution (`Couldn't resolve reference to ...`) — also catches dangling links to removed stubs.
- Typing rules (`A port must be typed by port definitions`, `A requirement must be typed by one requirement
  definition`, `Must reference a requirement`).
- Warnings (e.g. `Bound features should have conforming types`, duplicate names).
- Results come as `SysMLInteractiveResult.getSyntaxErrors() / getSemanticErrors() / getWarnings()`.

Gotchas **[verified]**:

- `process()` treats each input string as one resource and **drops it if it has errors**. Files with circular
  imports (SYSMOD ↔ ISO15288) must be loaded **in one call** (concatenate files), or errors cascade.
- The REPL `main()` reads one line per cell and loops on EOF. Use the Java API, not the REPL.

What we must build ourselves (custom checks on the exported JSON, Python):

- Variant selection valid (see 3).
- Every system requirement stub is satisfied by at least one element (coverage).
- Every element with a trace ID has a unique ID; IDs match the prefix scheme (D17).
- Stub package matches `needs.json` (D42).
- drawio files match the model (D38).
- Optional: SysML `constraint` / `assert` evaluation is possible in the Pilot (`%eval`), not needed now.

### 6. SYSMOD

Source: [mbse4u.com/sysmod](https://mbse4u.com/sysmod/), library [mbse4u/sysmod-sysmlv2](https://github.com/mbse4u/sysmod-sysmlv2)
(Apache-2.0, last commit 2026-11-07, file header "SYSMOD v5 ... Version v5.1.7"; site says 5.1.8) **[read + cloned]**.

**Version:** SYSMOD v5 for SysML v2. The website says the book covers **SYSMOD v3 with SysML v1**. So the
**website + GitHub library are enough**, and more current than the book. The site also has per-step pages,
"microstories" (small `.sysml` examples per step), a full Delivery Drone example, an online parser and a
"sysml-check" tool. SYSMODViews (viewpoints) is marked beta (since 5.1.6).

**Work products in order, and their SysML v2 form** (from `SYSMOD.sysml` and the step pages):

| # | Step / work product | SysML v2 element in the SYSMOD library | Our home (D6) |
|---|---|---|---|
| 01 | Project (owner, purpose, process) | `#project occurrence def` specialising `SYSMOD::Project` | `.sysml` |
| 02 | Brownfield architecture (optional) | `brownfieldContext` / `brownfieldContextImpl : SystemContext` | `.sysml` (skip: greenfield) |
| 03 | Problem statement | `concern problemStatement : ExtendedConcern` (stakeholder = project owner) | sphinx-needs text + concern stub? |
| 04 | Stakeholders | `part projectStakeholders : ExtendedStakeholder` (risk, effort, categories) | `.sysml` or sphinx-needs |
| 05 | Stakeholder needs | `concern stakeholderNeeds` with nested concerns | **sphinx-needs** → `concern` stubs |
| 06 | System idea + system objectives | `systemIdeaContext(Impl)`; `concern systemObjectives` | `.sysml` + needs |
| 07 | Specification system (system context: actors, system ports, interfaces) | `specificationContext(Impl)`, `actors`, `actorSystemInterfaces` | `.sysml` |
| 08 | Use cases (and flows) | `use case ... : SystemUseCase` (trigger, result, motivation) | `.sysml` |
| 09 | System requirements | `requirement systemRequirementSpecification : ExtendedRequirement`, boilerplates (`MaxValue`, `RangeValue`...), `frame` to needs | **sphinx-needs** → `requirement` stubs |
| 10 | Functional (opt.), logical (opt.), product architecture + allocations | `functionalContext(Impl)`, `logicalContext(Impl)`, `productContext(Impl)`, `allocation functional2logical`, `logical2product`; product system `satisfy systemRequirementSpecification` | `.sysml` |
| 11 | Verification and validation | `verificationContext`, `verification verificationCases` | sphinx-needs test specs + `.sysml` |

One line: Project → (Brownfield) → Problem statement → Stakeholders → Stakeholder needs → System idea &
objectives → Specification system / system context → Use cases → System requirements → Functional /
Logical / Product architecture (+ allocations) → Verification & validation.

Notes:

- SYSMOD builds a **chain of contexts by specialisation** (brownfield → idea → specification → logical →
  product). Each later context inherits actors and ports. This is a strong pattern for our model.
- SYSMOD has **no variant concept** in the library. D37 variants are our addition (see 3).
- SYSMOD4AI adds AI prompts as metadata (`create_prompt`, `validation_prompt`) per step. Interesting for D3
  (agents as first-class), worth a look in Phase 3.11.
- The SYSMOD library + Drone example loaded in the Pilot 0.63.1 with **4 errors** ("Must be an accessible
  feature") in the example use-case flow and about 27 warnings, **0 errors in the library** — when all files
  are loaded in one call **[verified]**.

### 7. Requirement documents (29148, EARS)

ISO/IEC/IEEE 29148:2018 information items **[known — standard is paywalled, outline from memory]**:

**Stakeholder Requirements Specification (StRS)** outline:
1. Introduction — purpose, scope, overview, definitions, stakeholders
2. References
3. Business management requirements — business environment, mission / goals / objectives, business model, information environment
4. System operational requirements — system processes, operational policies and rules, operational constraints, operational modes and states
5. User requirements
6. Detailed life-cycle concepts — operational concept, operational scenarios, acquisition, deployment, support, retirement concepts
7. Project constraints
8. Appendix — acronyms and abbreviations

**System Requirements Specification (SyRS)** outline:
1. Introduction — system purpose, scope, overview (context, functions, user characteristics), definitions
2. References
3. System requirements — functional, usability, performance, system interfaces, system operations,
   system modes and states, physical characteristics, environmental conditions, security, information
   management, policies and regulations, life-cycle sustainment, packaging/handling/shipping/transport
4. Verification — one sub-section per section 3 (method per requirement)
5. Appendices — assumptions and dependencies, acronyms

29148 also lists requirement attributes and quality rules (necessary, unambiguous, complete, singular,
feasible, verifiable, correct, conforming). These map well to sphinx-needs options (status, verification
method, rationale, priority) and to `needs_warnings` checks.

Mapping to SYSMOD: StRS ≈ steps 03–06 (problem statement, stakeholders, needs, objectives, use cases as
operational scenarios). SyRS ≈ steps 07–09 + verification method.

**EARS** (Mavin et al.) patterns **[known]**:

| Pattern | Template | Use here |
|---|---|---|
| Ubiquitous | The <system> shall <response>. | Always-true properties |
| Event-driven | When <trigger>, the <system> shall <response>. | "When the user presses store, ..." |
| State-driven | While <state>, the <system> shall <response>. | "While in mirror mode, ..." |
| Unwanted behaviour | If <trigger>, then the <system> shall <response>. | Faults, out-of-range pots |
| Optional feature | Where <feature is included>, the <system> shall <response>. | **Variant-specific (prototype/product)** |
| Complex | Combinations, order While → When → If-then. | Rare |

D45 is a good fit: stakeholder needs as plain statements; system and domain requirements (SW, EE, ME) in EARS.
EARS can be checked lightly by regex in a sphinx-needs warning (starts with The/When/While/If/Where, has
exactly one "shall").

## Hands-on results

Machine: no `syside`, `sysml`, `sysand`, `java`, `conda`, `jupyter` installed. `python3` 3.14, `uv`, `node`,
`gcc` 16, `cmake`, `cargo`, `docker`, `dot`, `rsvg-convert` present. All installs went into the scratch dir.

1. **Syside Automator** — `uv venv .venv -p 3.12; uv pip install syside` → `syside==0.11.0`, licence
   `LicenseRef-Proprietary`. `.venv/bin/syside --help` → `License check failed: Failed to load license key`.
   **Not usable without paying.**
2. **Sysand** — `uv pip install sysand` → 0.2.1. `sysand init --publisher demo --name arm-demo --version 0.1.0`,
   `sysand include *.sysml`, `sysand build` → `output/arm_demo-0.1.0.kpar` (2 kB). `.meta.json` lists the
   top-level packages per file. **Works.**
3. **Pilot Implementation** — downloaded Temurin JDK 21.0.13 tarball and the conda package
   `jupyter-sysml-kernel-0.63.1` (124 MB; contains `jupyter-sysml-kernel-0.63.1-all.jar` and `sysml.library`),
   unpacked with `unzip` + `tar --zstd`. No conda, no Jupyter needed.
   - `java -cp "$K/*" org.omg.sysml.interactive.SysMLInteractive $K/sysml.library/` is a line-based REPL.
     Usable only for one-line inputs; loops on EOF. **Not a good CLI.**
   - **`jshell --class-path <jar> script.jsh`** with `SysMLInteractive.getInstance()`, `loadLibrary()`,
     `process(fileText)`, `export(name, [])`, `viz(...)`, `view(...)` **works**. Scripts:
     `scripts/export.jsh`, `scripts/views.jsh`, `scripts/viz2.jsh`, `scripts/sysmod.jsh`.
   - Test model `model/{TraceMeta,RequirementStubs,Arm,Views}.sysml` (part defs with ports, conjugated port,
     connections, requirement stubs with short names and metadata, `satisfy`, `variation`/`variant`,
     configuration, custom view/viewpoint/rendering): **0 errors**.
   - Negative tests: `satisfy sysReq999` → error (good). Invalid variant choice → **no error** (gap).
   - JSON export: `out/Arm.json` (237 elements, 2 MB), `out/ArmViews.json`.
     Contains `declaredShortName`, `qualifiedName`, `isVariation`, `VariantMembership`,
     `SatisfyRequirementUsage`, `MetadataUsage`, `exposedElement`.
   - Viz: `out/Arm-tree.svg` (tree, good), `out/J2-ibd.svg` (IBD without variation, good),
     `out/JointSystem-ibd.svg` and `out/jointIbd-view.svg` (with variation → PlantUML "Syntax Error").
   - SYSMOD library + Drone example in one call: library 0 errors; example 4 errors, ~27 warnings.
   - Time per run (JVM start + library load + 4 files + export): **11 s**.
4. **sysml2 (C)** — cloned, build failed with GCC 16 (`implicit declaration of fileno`); fixed with
   `-DCMAKE_C_FLAGS="-D_POSIX_C_SOURCE=200809L -D_DEFAULT_SOURCE"`. Rejected valid `render` syntax; with the view
   removed and `-I <sysml.library>` it passed, but did **not** detect the dangling `satisfy sysReq999`;
   `-f json` crashed with exit 139. **Not usable.**
5. **sysml2py 1.2.0** — `read_model(path)` parsed both files; `print_model` round-trip not byte-identical.
   Syntax only.
6. **tree-sitter-sysml 0.1.0** — parsed `Arm.sysml` with no error nodes. Syntax only.

## Recommendations

1. **Use the Pilot Implementation as the validator and JSON exporter.** Wrap it in one small tool
   (`sysml-check`): a Java main or a jshell script in the framework repo, run with a pinned JDK 21 and a pinned
   kernel jar (fetched from conda-forge, no conda needed). Inputs: all `.sysml` files of the repo + library
   paths. Outputs: issues (non-zero exit on error) and `model.json`. One command, runs locally (D46).
2. **Load all files in one `process()` call** (or in dependency order without cycles). Keep a clear package
   dependency order in our repos anyway.
3. **Write all downstream tools in Python on the exported JSON**: needs export (SysML → sphinx-needs),
   custom checks (variants, coverage, ID scheme, stubs-in-sync), drawio views. This keeps the Java part tiny and
   lets us swap the parser later (e.g. to an open Syside-like tool) without touching the rest.
4. **Declare views in the model** with standard `view`/`viewpoint`/`expose`/`filter` and our own
   `rendering def DrawioRendering`. The generator reads `exposedElement` from the JSON. Reuse SYSMOD view defs
   where they fit.
5. **Adopt the SYSMOD v5 library as-is** (Apache-2.0) as a pinned dependency (west project, or later a sysand
   package). Follow its context chain. Skip brownfield (greenfield project) and the functional architecture
   in iteration 1.
6. **Stubs:** generate `concern` stubs for stakeholder needs and `requirement` stubs for system requirements,
   with short name = need ID and title as name. Commit the generated file; CI regenerates and diffs (D42).
7. **Trace IDs out of SysML:** use short names `<'ID'>` on elements other repos must reference. Add a
   `TraceId` metadata only if we need more fields.
8. **Variants:** logical architecture variant-free; variations in the product architecture; two configurations
   `prototype` and `product`; custom check for valid variant choice; requirement text uses EARS "Where".
9. **Agents and humans** can use the free Syside VS Code editor or SysON for viewing — but CI must not depend on them.
10. Use tree-sitter-sysml for a fast pre-commit syntax check if 11 s is too slow; full check in CI and in the
    per-repo check command.

## Risks and open questions

- **Pilot is a reference implementation, not a product.** No official CLI, API may change between monthly
  releases, large jar (133 MB), old PlantUML. Mitigation: pin the version, keep the Java wrapper tiny.
- **JSON export is big and full of derived and implied data** (237 elements for a toy model). Our readers
  must work on `payload` + `@type` and ignore implied relationships. Need a small schema contract.
- **Variant semantics are not checked** by any open tool I tried. We own that check.
- **Pilot IBD rendering breaks on variations** — fine since we render drawio ourselves, but we lose the
  quick fallback for those views.
- **SYSMOD expects needs and requirements in SysML.** Splitting them into sphinx-needs (D6) means SYSMOD's
  own views (StakeholderNeedsView, SystemRequirementsView) and its AI validation prompts see only stubs.
  Acceptable, but our docs must show needs/requirements from sphinx-needs instead.
- **Syside is the most capable modern tool but proprietary.** If the team later accepts a paid tool, it would
  replace the Pilot wrapper. Our JSON-based design keeps this option open.
- **SysON** not tested hands-on (needs Docker + server). It may be the best GUI for human reviewers.
- **Spec churn:** SysML 2.0 is final, but 2.1 revision work is ongoing; library names may shift.
- **29148 content is from memory** (standard is paywalled). Please check against your copy.
- Open: do stakeholders and use cases live in SysML or in sphinx-needs? (SYSMOD puts them in SysML; D6 only
  names needs and requirements.) Decide in Phase 3.3.
- Open: do we model the requirement → need `frame` link in SysML (generated) or only in sphinx-needs?

## Contradictions / tensions with plan.md

- **D6 / D42 vs. SYSMOD (D9):** not a contradiction, but D42 says "requirement stubs". For SYSMOD,
  stakeholder needs must be **`concern`** stubs, not `requirement` stubs. Suggest refining D42.
- **D37 "SysML v2 variants":** works for modeling, but no tool checks variant choices and the Pilot renderer
  fails on them. Plan 3.7 must include a custom check.
- **"All tools open source" (mission brief) vs. Syside:** Syside's CLI/Python API is paid. The SysML tool
  in D19/4.1 should be the Pilot (open), plus Java 21 — which is **not installed** on this machine today.
- **D19 "use installed versions":** no SysML v2 tool and no Java is installed. 4.1 must install JDK 21 and
  the Pilot jar (both work without sudo, tested here).
