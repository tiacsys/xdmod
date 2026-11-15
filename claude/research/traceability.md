# Research 1.1 — Traceability

Date: 2026-11-14. Author: research agent 1.1.

How to read this report:

- **[verified]** means I ran it on this machine and saw the result.
- **[read]** means I only read it in docs, source code or web pages.
- **[memory]** means it comes from my prior knowledge and I did not check it again today.

Hands-on work lives in
`/tmp/claude-1000/-home-tobias-z-wrk-ws-syseng/cc4a5268-5423-4e94-be0d-4c1055bbe07f/scratchpad/research-traceability/`
(venv, demo projects, scripts). That directory is temporary.

---

## 1. Summary

- **sphinx-needs 9.2.0 (released 2026-11-04) can enforce most of our link-type table by itself.** If you declare each link type
  **only on the need type that owns it**, a link written from the wrong side gives a
  `needs.undeclared_for_type` warning. `target_types` catches a link to the wrong kind of need. `minItems` catches a missing link.
  `back_links` with `minItems` catches a need that nothing links to (for example "no test"). With `-W`, the build fails on all of these. **[verified]**
- **Dangling links are caught for free.** If an upstream requirement is removed, every downstream link to it gives `needs.link_outgoing`.
  This also covers links from test results and from C code. **[verified]**
- **Big gap: coverage of *upstream* needs cannot be checked downstream with built-in features.** `needs_warnings` skips external
  needs (this is in the source code). `back_links` checks also skip external needs (per the docs). A check like "every SYS requirement is refined by
  at least one SW requirement" needs either one build where all needs are local (manifest/full build) or a small custom check. **[verified]**
- **Code and tests fit the D5 rule.** sphinx-codelinks reads one-line markers in C comments, and the code holds the link.
  sphinx-test-reports turns JUnit XML (Twister writes JUnit) into `testcase` needs. A `<property name="verifies">` becomes a real link. **[verified]**
- **KiCad, FreeCAD and SysML can join the same trace graph** if a small extractor writes a file in `needs.json` format. The
  downstream doc then reads it with `needimport` or `needs_external_needs`. I showed this with a mock KiCad export. **[verified]**
- **Change impact is not built in.** No open-source tool diffs two `needs.json` files. A small script that diffs `needs.json`
  between two git revisions and lists *removed*, *changed* and *impacted downstream* needs is about 40 lines (prototype done). **[verified]**
- **Eclipse S-CORE does almost exactly what D35 says.** Each module checks links only against needs it owns plus its declared
  *upward* modules, and cycles are forbidden. Their open issues show the limits we will hit: the `is_external` flag,
  `needextend` on imported needs, and version skew between modules. **[read]**
- **Zephyr's own safety requirements use StrictDoc, not sphinx-needs.** LOBSTER (BMW) has the clearest "policy" model for a link-type
  table (`trace-to` + `requires` with AND/OR groups). OpenFastTrace and Doorstop solve suspect links with revisions/fingerprints. **[read]**
- **sphinx-needs moves fast.** 9.1 had breaking changes, the schema system is replacing `needs_constraints`/`needs_warnings`,
  and `needs.json` gets a new format version. We must pin exact versions. **[read + verified version]**

---

## 2. Findings per tool / topic

### 2.1 sphinx-needs (core)

- Source: https://github.com/useblocks/sphinx-needs · docs https://sphinx-needs.readthedocs.io/en/latest/
- Licence: MIT **[verified in package metadata]**. Maintainer: useblocks GmbH plus community. Very active. 9.1.0 came out on 2026-10-22 and 9.2.0 on
  2026-11-04 ([changelog](https://sphinx-needs.readthedocs.io/en/latest/changelog.html)). **[read]**
- Installed for the test: `sphinx 9.2.0`, `sphinx-needs 9.2.0`, `sphinx-codelinks 2.1.0`, `sphinx-test-reports 4.0.0`,
  `ub-needs-exchange 1.1.0`, `ub-project 1.2.0` (Python 3.14). **[verified]**
- Not installed system-wide on this machine (`import sphinx_needs` failed). **[verified]**

Features that matter for us:

| Feature | What it does | Status for us |
|---|---|---|
| **Link types** (`needs_links`, old name `needs_extra_links`) | Named links, with outgoing/incoming labels. Backlinks (`<name>_back`) are **always computed**, never written. | Matches D5. **[verified]** |
| **Per-type link declarations** (`needs_types[].links`) | A link type declared only on some types may only be used on those types. Others get `needs.undeclared_for_type` and **the value is dropped**. | This is how to enforce the owner side. **[verified]** |
| `target_types` | Allowed target types for a link type, including subtypes via `inherits`. Wrong target → `needs.link_target_type`. Works for external targets too. | Enforces the "to which type" column. **[verified]** |
| `schema: {minItems: 1}` on a link | Need must hold at least one link of this type. | "Mandatory link". **[verified]** |
| `back_links: {verifies: {schema: {minItems: 1}}}` | Need must be the *target* of at least one link. | Coverage ("each SW req has a test"). **Local needs only.** **[verified]** |
| Schema validation (`needs_schema_definitions`, `network`, `network_back`) | JSON-Schema rules over fields and over the link graph (up to 4 levels deep). Severities: violation / warning / info. Writes `schema_violations.json`. | Replaces `needs_constraints` and `needs_warnings` in the long run ([docs](https://sphinx-needs.readthedocs.io/en/latest/schema/index.html)). **[read; basic link rules verified]** |
| `id_regex` per type | Each type gets its own ID pattern. | Enforces the D17 prefix scheme. **[verified on upstream build]** |
| `needs_warnings` | Filter strings; if any need matches, it reports a warning. | **Skips external needs** (`warnings.py`: `filter_is_external(False)`). **[verified]** |
| `needs_constraints` | Older per-need rule checks with severity. | Superseded by the schema system. I did not test it. **[read]** |
| `needs_external_needs` | Reads another project's `needs.json` (local path or URL). Needs become *external*: you can link to them, and they link back to the upstream HTML. | Core of D35. **[verified]** |
| `needimport` | Copies needs from a `needs.json` into this doc as **local** needs. | Good for generated needs (KiCad/FreeCAD/SysML extractors). Bad for upstream requirements, because it takes over their ownership. **[verified]** |
| `needextend` | Changes fields/links of needs that match a filter. | Useful for computed data (codelinks uses it for `code_url`). Dangerous if it changes needs owned by another repo. S-CORE wants it limited to owned needs. **[read]** |
| Dynamic functions, `derive` | Computed fields and links (`copy`, `collect`, `union`, `join`). New in 9.1/9.2. | Could compute "summary" links such as test → system requirement. Very new. **[read]** |
| Variants | `needs_variant_data` (`var.*` in filters), inline variant syntax in fields, `needs_variants`, `needs_variant_data_file`. | One build per variant (prototype vs product, D37) via `-D needs_variant_data_file=…`. Not tested. **[read]** |
| `needs.json` | Built with `needs_build_json = True` or `-b needs`. Contains `needs_schema`. Options: `needs_reproducible_json`, `json_remove_defaults`. New experimental format `2a1`. | Exchange format for everything. **[verified]** |
| `ubproject.toml` | Declarative config shared by sphinx-needs, codelinks, test-reports and ubCode. | Good place for one shared link-type table. **[read]** |

Extension points: Sphinx events, `sphinx_needs.api` (`create_need`; `add_need` is deprecated), custom dynamic functions,
filter functions, `needs_services`, and the `ub-needs-exchange` reader (stdlib only) for our own tools. **[read in installed source]**

### 2.2 sphinx-codelinks (code → needs)

- Source: now in the sphinx-needs monorepo, `packages/sphinx-codelinks`. The old repo
  https://github.com/useblocks/sphinx-codelinks is archived. Docs: https://codelinks.useblocks.com/ . MIT. v2.1.0 needs
  `sphinx-needs>=9.2,<10`. **[verified metadata, read repo]**
- Two marker kinds **[verified]**:
  - One-line need: `// @Servo PWM writer, SWIMPL_SERVO_WRITE, swimpl, [SWREQ_SERVO_PERIOD]` creates a real need of type `swimpl`
    with an `implements` link. Fields are set in `oneline_comment_style.needs_fields`.
  - Reference only: `/* @need-ids: SWREQ_SERVO_PERIOD */` adds a computed `code_url` on the requirement (file + line).
- Parsing uses tree-sitter (C/C++, Python, Rust, Go, TS, YAML, …), with an optional libclang preprocessor. CLI: `codelinks analyse`
  writes `marked_content.json` with file, line, enclosing function and a GitHub URL pinned to the commit. **[verified]**
- Gotchas found **[verified]**:
  - It needs a git repo **with a remote**; otherwise you get the warning `codelinks.git_remote`.
  - One-line needs inside `/* … */` with `end_sequence="*/"` were **not** found. `//` comments with the default newline end worked.

### 2.3 sphinx-test-reports (tests → needs)

- Source: https://github.com/useblocks/sphinx-test-reports . MIT. v4.0.0 plus helper `ub-test-reports` 2.0.0 (CLI `test-reports`, pytest
  plugin). **[verified]**
- `.. test-file::` with `:auto_suites:` and `:auto_cases:` makes `testfile`/`testsuite`/`testcase` needs from JUnit XML. Each case gets a `result`
  (passed/failed). `tr_property_link_types = {"verifies": "verifies"}` turns `<property name="verifies" value="SWREQ_…"/>` into
  a real link. `tr_deterministic_case_ids = True` gives stable IDs. **[verified]**
- Gotcha **[verified]**: the stable IDs are lowercase (`testcase__servo__test_period_wawbo`). They break the default `needs_id_regex`, so you must widen it.
- For Zephyr: Twister writes JUnit XML (`twister_report.xml`). We have to find out how a ztest can emit a `verifies` property.
  That is for the zephyr-west agent (1.6).

### 2.4 OpenFastTrace-style tags

- OFT (https://github.com/itsallcode/openfasttrace, GPL-3.0, Java 17, v4.x). Item IDs carry a **revision**: `dsn~servo-period~1`.
  Items say what they need (`Needs: impl, utest`). Code tags look like `[impl->dsn~servo-period~1]`. If the requirement goes to `~2`,
  old links become *outdated*. **[memory; repo page read]**
- The idea worth borrowing: put a version in the link so that a change makes the link "suspect" without any extra state. That
  overlaps with affirmatrix (D44, agent 1.2), so I do not go deeper.

### 2.5 Alternatives

| Tool | Licence | What we can borrow | Why not as main tool |
|---|---|---|---|
| **StrictDoc** ([repo](https://github.com/strictdoc-project/strictdoc)) | Apache-2.0, very active | `@relation(REQ, scope=function)` markers in code. Parent/Child/File relations. ReqIF. Web editor. Used by Zephyr. | Own SDoc format, not Sphinx-native. D6 already chose sphinx-needs. **[read]** |
| **Doorstop** ([repo](https://github.com/doorstop-dev/doorstop)) | LGPL-3.0 | One YAML file per item. **Child links to parent** (same as D5). Link **stamps** (a fingerprint of the parent) give suspect links. `reviewed` stamp. | Small feature set, weak HTML. **[read + memory]** |
| **TRLC + LOBSTER** ([trlc](https://github.com/bmw-software-engineering/trlc), [lobster](https://github.com/bmw-software-engineering/lobster)) | TRLC GPL-3.0, LOBSTER AGPL-3.0 | **The tracing policy**: each level has `trace-to` (the direction, held by the lower level) and `requires` (AND of OR groups, e.g. "Code AND (Unit test OR Proof)"). One common `.lobster` JSON format from many tools (C++, gtest, Python, Codebeamer). CI report. | Different language. AGPL for LOBSTER. No sphinx-needs input. ([policy doc](https://github.com/bmw-software-engineering/lobster/blob/main/documentation/config_files.md)) **[read]** |
| **OpenFastTrace** | GPL-3.0 | Revisioned IDs. `Needs:`/`Covers:` coverage model. | Java. Own Markdown format. **[memory]** |

### 2.6 Frameworks to learn from

**Eclipse S-CORE docs-as-code** (https://github.com/eclipse-score/docs-as-code, Apache-2.0, very active, Bazel-based) **[read]**

- Has its own metamodel in `metamodel.yaml`: types with `mandatory_options`, `mandatory_links`, `optional_links` (with regexes on target IDs),
  `graph_checks` (`check_all`/`check_one` plus a condition, `info_only`), and `prohibited_words_checks`
  ([metamodel ext](https://eclipse-score.github.io/docs-as-code/main/internals/extensions/metamodel.html)). They built this before sphinx-needs
  had schemas. Today much of it fits into `needs_types` + schema.
- Code links: a comment `# req-Id: TOOL_REQ__X` in sources. Bazel collects it and stores it as `source_code_link` on the need
  ([how-to](https://eclipse-score.github.io/docs-as-code/main/how-to/source_to_doc_links.html)).
- Cross-module: the upstream `needs.json` is **built from a pinned Bazel dependency**, not downloaded from a website. You can either *link* (no backlinks upstream) or
  *mount* (one big build, with backlinks) ([concept](https://eclipse-score.github.io/docs-as-code/main/concepts/bidirectional_traceability.html),
  [other modules](https://eclipse-score.github.io/docs-as-code/main/how-to/other_modules.html)).
- Limits they hit:
  - Version skew: a module passes alone but fails when integrated. Their answer: narrow, explicit "allowances" that turn some findings into
    warnings only for imported needs ([cross-module](https://eclipse-score.github.io/docs-as-code/main/concepts/cross_module_compatibility.html)).
  - Issue [#683](https://github.com/eclipse-score/docs-as-code/issues/683): each bundle may link only to itself and its declared **upward**
    bundles, and Bazel rejects cycles. `needextend` must not touch imported needs. "A single `is_external` flag cannot
    represent both 'local for URL rendering' and 'foreign for gates and metrics'". Some graph features (dynamic functions,
    variants) must fail clearly in a partial build. They want upstream sphinx-needs APIs for this rather than patching internals.

**Zephyr safety requirements** (https://docs.zephyrproject.org/latest/safety/safety_requirements/safety_requirements.html) **[read]**

- Separate repo `zephyrproject-rtos/reqmgmt`. Uses **StrictDoc**. Two levels: system and software requirements. Statuses are Draft/Approved/Retired.
  UIDs are assigned by a tool (`strictdoc manage auto-uid`). CI checks for duplicate UIDs. A PR needs approval from a safety role.
- It describes the current kernel. It does not request new features. The page does not say how code or tests are traced.
- Lessons for us: tool-assigned IDs avoid merge clashes. A **Retired** status is a way to "remove" a requirement without breaking links at once.

**useblocks tooling** **[read]**

- Open source (MIT): sphinx-needs, sphinx-codelinks, sphinx-test-reports, ub-needs-exchange, ub-project, needs-config-writer, sphinx-mounts.
- Commercial: **ubCode** (VS Code language server for sphinx-needs with live validation) and **ubTrace** (trace dashboard). Per useblocks, the
  Pharaoh AI integration in ubCode is free for open-source projects ([pharaoh-skills](https://github.com/useblocks/pharaoh-skills)).
  These tools are **not open source**, so the mission brief rules them out as core tools. They are fine as optional helpers.
- x-as-code guide: https://x-as-code.useblocks.com/ .

---

## 3. Answers to questions a–e

### a) Enforcing the link-type table (owner side, D5/D36)

What works today **[verified]**:

1. Keep **one shared link-type table** in the framework repo (Python module or `ubproject.toml`). Every repo's `conf.py` loads it.
   All repos must know **all** need types, including upstream ones. Otherwise external needs carry links their type does not declare,
   and you get `undeclared_for_type` noise (I hit this).
2. Leave `needs_links` empty. Declare each link type **only** under the type that holds it:
   ```python
   {"directive": "swreq", "prefix": "SWREQ_",
    "links": {"refines": {"target_types": ["sys"], "schema": {"minItems": 1}, "incoming": "refined by"}},
    "back_links": {"verifies": {"schema": {"minItems": 1}}}},
   {"directive": "swtest", "prefix": "SWTEST_",
    "links": {"verifies": {"target_types": ["swreq"], "schema": {"minItems": 1}, "incoming": "verified by"}}},
   ```
3. Build with `sphinx-build -W --keep-going`. Each error class has its own tag:

| Mistake | Message | Fails `-W` build |
|---|---|---|
| Link held by the wrong side (requirement says `verifies: <test>`) | `needs.undeclared_for_type` (value is dropped) | yes |
| Link to the wrong type (test verifies a SYS requirement directly) | `needs.link_target_type` | yes |
| Missing outgoing link (SW requirement with no `refines`) | `sn_schema_violation.link_fail` (`minItems`) | yes (logged as ERROR) |
| Need with no incoming link (SW requirement with no test) | `sn_schema_violation.link_fail` on `verifies_back` | yes |
| Link to an ID that does not exist | `needs.link_outgoing` | yes |

Note: a dangling link still counts toward `minItems`. Only `link_outgoing` catches it **[verified]**. You can relax some checks with `severity: "warning"`
or `"info"` per type, for example while a requirement is still Draft.

Still open: (1) "Requires X **or** Y" rules (LOBSTER style) need `network` schema rules or a custom check. (2) Peer interface elements (D36) are
easy: both EE and SW types declare a `uses` link with `target_types: ["ifc"]`.

### b) Cross-repo traces from pinned west checkouts (D35, D39)

**[verified]** with two local projects:

- Build upstream (`syseng`) with `needs_build_json = True`. In the downstream (`sw`) `conf.py`:
  `needs_external_needs = [{"json_path": <abs path into the west checkout's build>, "base_url": <relative path to its HTML>}]`.
- Downstream links to upstream IDs resolve. `target_types` checks work across repos. Backlinks are computed **on the downstream side**: a
  `needtable` of upstream `sys` needs showed `refines_back` = the SW requirement. So a downstream doc can show coverage of upstream needs.
- **Gap:** you cannot *fail* the downstream build on missing coverage of upstream needs with built-in features. `needs_warnings` skips external needs, and
  `back_links` checks skip them too. Options:
  1. Run coverage checks in the **manifest repo's full build**, where everything is built together (D26). This is S-CORE's "mount" model.
  2. Write a small Sphinx extension in the framework repo (D34) that checks external needs' `*_back` at `env-check-consistency`/`build-finished`.
  3. Run a standalone script on the `needs.json` files.
  I recommend 1 for the coverage reports, plus 2 or 3 for local checks (D46).
- Whether upstream needs end up as *external* or *local* depends on how zdocs builds and imports them. Agent 1.8 must confirm this. If zdocs imports
  with `needimport`, upstream needs become local copies. Then coverage checks work, but ownership rules (who may change them) need care.
- Learn from S-CORE #683: allow links only to the repo's **own** needs and **declared upstream** repos (the west manifest gives that list). Never
  apply `needextend` to imported needs.

### c) Change-impact analysis

- There is no ready-made open tool for `needs.json` diffs. **[read: searched, found none]** ubTrace may have this, but it is commercial.
- I wrote a prototype, `scripts/needs_diff.py` (about 40 lines) **[verified]**. It
  1. loads two `needs.json` files (old and new upstream revision),
  2. lists **removed**, **added** and **changed** IDs (a hash of title, content, status, type), and
  3. scans downstream `needs.json` files and prints `DANGLING` (link to a removed ID) and `SUSPECT` (link to a changed ID) lines.
  Output from the demo:
  ```
  removed: ['SYS_JOINT_RATE']
  changed: ['SYS_POSE_STORE']
    SYS_POSE_STORE.content: '... the current leader pose.' -> '... the current leader pose within 100 ms.'
  DANGLING: SWREQ_SERVO_PERIOD --refines--> SYS_JOINT_RATE  (sw)
  ```
- For git revisions: run `git worktree add <tmp> <rev>`, then `sphinx-build -b needs`, for both revisions, then the diff. In CI this fits a PR job:
  base = manifest main, head = PR branch. A real version should read link fields from `needs_schema` (not "all list fields") and use
  `ub-needs-exchange` to read the files. It should also walk **transitively** (requirement → SW requirement → test → result).
- Suspect links over time (state stored per link) belong to affirmatrix (agent 1.2). The diff above is the "what changed in this PR" view. affirmatrix is
  the "what was confirmed against which version" view. The two fit together.

### d) Removing a requirement

**[verified]** I deleted `SYS_JOINT_RATE` upstream and rebuilt downstream against the new `needs.json`:

- Downstream gets `WARNING: Need 'SWREQ_SERVO_PERIOD' has unknown outgoing link 'SYS_JOINT_RATE' in field 'refines' [needs.link_outgoing]`.
  With `-W`, the build fails (exit 1). Links from test results (`<property verifies=…>`) to a missing ID give the same warning.
- sphinx-needs cannot tell "removed on purpose" from "typo". The diff tool (c) can, because it compares with the old revision.
- `allow_dead_links: True` per link type turns the error into a styled "dead link". Do **not** use this by default.
- Recommended process:
  1. Don't delete at once. Set `status: retired` (as Zephyr does). A schema rule warns on links to retired needs, which gives downstream
     owners a grace period across repos (one PR per repo, D39).
  2. Then delete. CI on the manifest PR proves there are no dangling links left.
  3. Keep the ID reserved, and never reuse it. A check can compare against the IDs in the last baseline tag.
- Removal also orphans needs *below* it. For example, the SW requirement now has nothing to refine. `minItems` on `refines` will not fire if the
  dangling ID is still written, but `link_outgoing` will.

### e) SysML, KiCad, FreeCAD and C tests in one trace graph

One rule: **every source writes `needs.json`-format data, and Sphinx reads it.** **[mechanism verified with a mock KiCad export]**

| Source | How it becomes needs | Who holds the link (D5) |
|---|---|---|
| Requirements (rst) | sphinx-needs directives | Lower level holds `refines` |
| SysML v2 (`.sysml`) | Extractor (agent 1.3 parser) writes `needs.json` of model elements (parts, ports, interfaces) with `satisfies`/`refines` from SysML `satisfy`/`#refinement`. Imported with `needimport` in the syseng doc. Requirement stubs go the other way (D42), generated from `needs.json`. | The SysML element (more concrete) holds `satisfies` |
| KiCad | Extractor reads symbol/sheet fields (D29: e.g. `TraceId`, `Satisfies`) via `kicad-cli sch export netlist` or s-expr parsing, and writes `needs.json`. I tested `needimport` with mock data: the need `EEPART_U2` with `satisfies: SYS_JOINT_RATE` showed up in the upstream `satisfies_back`. | The KiCad symbol holds the link |
| FreeCAD | Extractor with `FreeCADCmd` reads object properties (D29), then the same way | The FreeCAD object holds the link |
| C code | sphinx-codelinks one-line needs or `@need-ids:` refs | The code holds the link |
| Tests / results | sphinx-test-reports from JUnit (Twister) with a `verifies` property; or `swtest` needs written by hand | The test holds the link |

Notes:

- Extractors should run as a **pre-build step** (one command per repo, D46) and write `_generated/*.json`. That is easier to debug than a
  Sphinx extension, and agents can run it alone.
- Give generated needs their own types and prefixes (D17), and set `tags: generated` so nobody edits them by hand.
- KiCad/FreeCAD extraction needs those tools, which are not in GitHub CI yet (D47). So either commit the generated JSON (then CI checks it is fresh
  locally only) or accept that CI does not see CAD links until the Docker image exists. **This is an open decision.**

---

## 4. Hands-on results (what I ran)

Everything is under `.../scratchpad/research-traceability/`.

1. `python3 -c "import sphinx_needs"` → `ModuleNotFoundError`. Not installed system-wide.
2. `pip install` into a venv hung for more than 3 minutes (resolver). `uv pip install -p venv/bin/python sphinx-needs` took seconds →
   sphinx 9.2.0 + sphinx-needs 9.2.0. Then `sphinx-codelinks 2.1.0` and `sphinx-test-reports 4.0.0`.
3. `demo/syseng`: types `stk`, `sys` (`refines`→`stk`, `minItems: 1`), `ifc`. Build clean. `needs.json` holds `refines_back` on `STK_001`.
4. `demo/sw`: `needs_external_needs` → syseng's `needs.json`. Types `swreq`, `swtest`, `swimpl`, `testcase`. Clean build. The coverage
   table of upstream `sys` needs shows `SYS_POSE_STORE` has no SW refinement.
5. Negative tests (`bad.rst`) with `sphinx-build -W --keep-going`, exit 1:
   - **With global `needs_links`:** wrong-side links (`swreq` holding `verifies`, `swtest` holding `refines`) were **accepted silently**, and the
     wrong-side `verifies` even showed up as a backlink on the test.
   - **With per-type declarations only:** both gave `needs.undeclared_for_type`. Wrong target gave `needs.link_target_type`. Missing link and
     missing test gave `sn_schema_violation.link_fail`. Unknown ID gave `needs.link_outgoing`.
6. Removal scenario: `demo/syseng_v2` with `SYS_JOINT_RATE` deleted and `SYS_POSE_STORE` reworded.
   `UPSTREAM_JSON=…/syseng_v2/... sphinx-build -W` on `sw` → `link_outgoing`, exit 1. `python3 -I scripts/needs_diff.py old new sw` →
   removed, changed and DANGLING lines (see 3c).
7. sphinx-codelinks: `src/servo.c` with `// @…` one-line need → need `SWIMPL_SERVO_WRITE` (`implements` → `SWREQ_SERVO_PERIOD`).
   `@need-ids:` → `code_url: src/servo.c#L9` on the requirement. `codelinks analyse ubproject.toml -o out` → JSON with function scope and a
   commit-pinned GitHub URL. Needed `git init` plus a remote. `/* … */` one-line form did not work.
8. sphinx-test-reports: `results/twister.xml` (mock JUnit, 1 pass and 1 fail) → `testcase` needs with `result` and `verifies` links. The failing
   case pointed at `SWREQ_GONE` → `link_outgoing`. Needed a wider `needs_id_regex`.
9. `demo/ee`: `needimport` of a mock KiCad `needs.json` → local need `EEPART_U2` linked to upstream `SYS_JOINT_RATE`.
   `needs_warnings` probe: rules on external needs **never fire**, and `sphinx_needs/warnings.py` line 55 filters them out.

Not tested: variants, `needs_constraints`, `network`/`network_back` schema rules, `needs_reproducible_json` diff stability, zdocs integration.

---

## 5. Recommendations for this project

1. **Pin** `sphinx-needs==9.2.0`, `sphinx-codelinks==2.1.0` and `sphinx-test-reports==4.0.0` in a lock file in the framework repo. Install with `uv` in a
   venv. Upgrade on purpose only (9.1 had breaking changes; `add_need` will go away in 10.0).
2. Put the **link-type table as code** in the framework repo: one module with all need types, prefixes, `id_regex`, per-type `links` (with
   `target_types`, `minItems`, severity) and `back_links`. Every repo imports it. **Never** declare link types globally. Generate the Phase 3.1 table
   document *from* this module, so the doc and the check cannot drift apart.
3. Use the **schema system**, not `needs_constraints`/`needs_warnings` (those are on their way out and skip external needs anyway).
4. Write two small framework tools (D34):
   - `trace-check`: coverage of **upstream/external** needs (the gap in 3b), plus LOBSTER-style AND/OR `requires` rules.
   - `needs-diff`: impact report between two revisions (based on the prototype, reading with `ub-needs-exchange`), posted on PRs.
5. All model/CAD sources produce **`needs.json`-format files** through extractors. Use `needimport` for these generated, repo-owned needs.
   Use `needs_external_needs` for needs owned by other repos.
6. Copy S-CORE's rules: each repo links only to its own needs plus its **declared upstream** repos (derive the list from the west manifest), no cycles,
   no `needextend` on foreign needs.
7. Use a `retired` status before removing anything, and never reuse IDs.
8. Use `// @…` one-line comments for code needs and `@need-ids:` for plain refs. Agree on one style now, because agents will copy it.
9. Run builds with `-W --keep-going` in CI and in the local check command (D46). Use `severity: info` for Draft-stage rules instead of disabling checks.

---

## 6. Risks and open questions

- **Speed of change in sphinx-needs.** Many features I used (`target_types`, per-type `links`, `back_links`, `undeclared_for_type`) are from
  9.1/9.2, so only weeks old. Docs, examples and LLM knowledge lag behind. Agents may write old-style config (`needs_extra_links`), which
  silently turns off the owner-side check. **Mitigation:** a test that fails if `needs_links` is non-empty.
- **External needs are second-class** for checks (`needs_warnings`, `back_links`). S-CORE hit the same wall (the `is_external` issue). How zdocs
  imports upstream needs (local vs external) decides how much custom code we need. **Ask agent 1.8.**
- **D19 tension:** sphinx-needs is not installed on this machine, so we have to install it (venv). The plain `pip` resolver was very slow here, while `uv` was fast.
- **D47 tension:** CAD-derived needs cannot be produced in GitHub CI yet. Either commit generated JSON or accept partial traces in CI.
- **needs.json format change** (`2a1` experimental, `format_version`). Our diff, stub generator (D42) and extractors should go through
  `ub-needs-exchange`, not parse raw JSON by hand.
- **Need ID rules differ between tools.** sphinx-test-reports' stable IDs are lowercase and long. The D17 prefix scheme must allow them, or we need a
  mapping.
- **Commercial pull.** ubCode/ubTrace give the best UX (live validation, trace dashboards) but are not open source. We must make sure our
  framework does not depend on them.
- **Suspect links** (link confirmed against an old version of its target) are not covered by sphinx-needs. See the affirmatrix report (1.2). OFT
  revisions and Doorstop stamps are prior art.
- Open: how does a ztest/Twister case declare `verifies` so that it lands in the JUnit `<properties>`? (agent 1.6)
- Open: should the full-set coverage checks run only in the manifest repo build (simple), or also in each repo (needs custom code)?
