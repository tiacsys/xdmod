# Decisions

> **Frozen 2026-11-15 (D120).** Decisions D1–D142 are now sphinx-needs: framework decisions are `XD-ADR` needs in the XDMOD manual (`xdmod/docs/xdmod-manual/explanation/decisions/`), robot-arm decisions are `PRJ-DEC` needs in robarm-manifest's `robarm` doc. D143 is converted in a follow-up. New decisions are written as needs, not here. This file stays as the historical log.

This file is the decision log for the XDMOD framework and its robot-arm example. The work plan is in `plan.md`.
Each decision has an ID (`D<n>`), which never changes and is never reused. If a decision is changed later, its row stays and says *revised by* or *superseded by*, and a new row records the change.

## How decisions were made

- Q1–Q18: questions to make the problem statement well-posed → D14–D34.
- A1–A8: findings from the plan review by a second agent → D35–D45 (see "Review log").
- X1–X8: conflicts found in the Phase 1 research (`research/summary.md` §4) → D56–D65.
- All other decisions came from the user directly during planning.

## Decision table

Rows marked *revised* or *superseded* were changed later. The note in the row names the decision that changed them.

| # | Decision | Date |
|---|----------|------|
| D1 | The system model is written in **SysML v2 textual notation** (`.sysml`). | 2026-11-14 |
| D2 | Views are rendered as **drawio** files by our own tooling. Content comes from the model; manual **layout tweaks are kept** when views are regenerated. *Revised by D43: layout keeping moves to iteration 2.* | 2026-11-14 |
| D3 | **Agents are first-class**: they edit and review design content the same way human engineers do. | 2026-11-14 |
| D4 | Iteration 1 is **T-shaped**: broad at the requirements/system level, then end-to-end for **one joint**. | 2026-11-14 |
| D5 | **Trace rule:** trace annotations go right-to-left in the V-model and from concrete to abstract. The more concrete artifact holds the link; backlinks are only ever computed. *Refined by D36.* | 2026-11-14 |
| D6 | Requirements (stakeholder needs, system requirements) are written in **sphinx-needs**. SysML elements reference them by ID (see D42). | 2026-11-14 |
| D7 | Repos are managed as a multi-repo workspace with **west**. | 2026-11-14 |
| D8 | One-joint E2E target: design artifacts plus **Zephyr firmware that builds and runs on a real STM32G4 board**, with the verification evidence traced back to requirements. | 2026-11-14 |
| D9 | The main SYSMOD reference is https://mbse4u.com/sysmod/. | 2026-11-14 |
| D10 | Available hardware: NUCLEO-G4 board, PCA9685 breakout, MCP3208 breakout, SG90 servos, potentiometers. | 2026-11-14 |
| D11 | **Prototypes are first-class.** Prototype setups (e.g. Nucleo + breakouts) are part of the model and are traced like the product design. *Refined by D37.* | 2026-11-14 |
| D12 | Requirements use **EARS** sentence patterns. *Refined by D45.* | 2026-11-14 |
| D13 | The framework itself gets its **own Sphinx documentation**, separate from the example's design docs. | 2026-11-14 |
| D14 | The west manifest lives in a **dedicated manifest repo**. | 2026-11-14 |
| D15 | All repos are hosted on **GitHub**. CI runs on GitHub Actions; changes are reviewed through pull requests. | 2026-11-14 |
| D16 | The board is a **NUCLEO-G474RE**. | 2026-11-14 |
| D17 | We design a **new ID prefix scheme**. The SEG IDs are not reused. | 2026-11-14 |
| D18 | The leader and follower **can be the same size**. | 2026-11-14 |
| D19 | We use the tool versions **installed on this machine**. A Docker image with all tools comes later. | 2026-11-14 |
| D20 | All content is in **English**. | 2026-11-14 |
| D21 | The result is a **set of linked Sphinx documents** that describes the project in full: system architecture; SW requirements, SW architecture and design, SW test specification; ME and EE requirements; ME assembly design; one design doc per PCBA. | 2026-11-14 |
| D22 | Documents **extract content from the design models** where possible (SysML, FreeCAD, KiCad), the way API docs come from Doxygen comments. | 2026-11-14 |
| D23 | Creating and storing **CAM data from CAD data** (ME and EE) is a task of the framework. *Moved to iteration 2 by D43.* | 2026-11-14 |
| D24 | All design outputs, including the pre-built firmware, go into a **bundle**. The user will share a bundling tool later. *Terms fixed by D40; moved to iteration 2 by D43.* | 2026-11-14 |
| D25 | **zdocs** (https://github.com/tiacsys/zdocs) links the documents together. | 2026-11-14 |
| D26 | Each repo has **its own zdocs registry**. The manifest repo has a registry that builds the **full linked set**. *Revised by D35: upstream docs are built locally, not used as remote documents.* | 2026-11-14 |
| D27 | Added documents: stakeholder needs and system requirements spec; system and integration test spec; EE and ME test specs; one doc per prototype setup. | 2026-11-14 |
| D28 | The number of PCBAs is **left to the SE work** (trade study in Phase 5). | 2026-11-14 |
| D29 | Trace IDs for CAD elements live **inside the CAD files** (KiCad symbol/sheet fields, FreeCAD object properties). Doc extraction reads them. | 2026-11-14 |
| D30 | ME CAM output is **3MF (and STL) plus a print-settings profile**. No G-code. | 2026-11-14 |
| D31 | Generated outputs are **built by CI**: workflow artifacts on pull requests, release assets on tags. *Revised by D38: drawio files are committed.* | 2026-11-14 |
| D32 | ~~A bundle is one tag of the manifest repo.~~ *Superseded by D40.* | 2026-11-14 |
| D33 | **No document control** (`doc_control`) in iteration 1. Git history and PR reviews are enough for now. | 2026-11-14 |
| D34 | Features that zdocs lacks are built as **separate Sphinx extensions in the framework repo**. Useful ones may move into zdocs later. | 2026-11-14 |
| D35 | **Cross-repo traces:** each repo's zdocs registry also **builds its upstream documents locally** from the west checkout that the manifest pins. This is how a downstream repo checks its links into upstream needs. (zdocs imports needs only from locally built documents.) | 2026-11-14 |
| D36 | **Link-type table:** D5 stays the default. A table of link types names the owner side of each. Peer interfaces (e.g. EE↔SW pin map, EE↔ME connector positions) are **interface elements in syseng**, and both domains link to them. Allocation is stored on the concrete side. | 2026-11-14 |
| D37 | **Prototype and product are variants** of one logical architecture (SysML v2 variants). A prototype test verifies the logical and SW requirements it covers. Product-specific requirements need product evidence. The vertical bar of iteration 1 is the **prototype variant**. *Revised by D102–D107.* | 2026-11-14 |
| D38 | **Drawio files are committed**, and CI checks that they match the model. **HIL test results** are packaged with the user's bundling tool, the same way as design outputs. | 2026-11-14 |
| D39 | **The manifest is the only place that pins revisions.** A downstream PR's CI builds against the upstream revisions on the manifest's main branch. A change across several repos = one PR per repo + one manifest PR that bumps them together. | 2026-11-14 |
| D40 | **Terms:** a *baseline* is a tag of the manifest repo (a fixed set of repo versions). A *bundle* is the package of outputs (docs, CAM, firmware, HIL results) built from one baseline. | 2026-11-14 |
| D41 | **FreeCAD storage and diff** (`.FCStd` is a zip file) is decided in Phase 3, after hands-on research. | 2026-11-14 |
| D42 | **SysML references to requirements:** a tool generates a package of **read-only requirement stubs** (ID + short name) from `needs.json`. Nobody edits them by hand; CI checks that they match. | 2026-11-14 |
| D43 | **Moved to iteration 2:** CAM pipeline and bundle, the PDF document set, layout keeping in drawio, product PCB layout. Iteration 1 builds HTML docs only. | 2026-11-14 |
| D44 | **Suspect/stale link detection:** study the user's tool **affirmatrix** (https://github.com/tiacsys/affirmatrix) in Phase 1. | 2026-11-14 |
| D45 | EARS is used for **system and domain requirements**. Stakeholder needs may be plain statements. | 2026-11-14 |
| D46 | **Every check also runs locally** (one command per repo), not only in GitHub Actions. | 2026-11-14 |
| D47 | In iteration 1, **GitHub CI only builds docs and runs trace checks**. Checks that need KiCad, FreeCAD or the Zephyr SDK run locally until the Docker image exists. | 2026-11-14 |
| D48 | Repos live in the existing **tiacsys** GitHub org and are **public from day one**. CI can check out other repos without extra tokens. | 2026-11-14 |
| D49 | **Repo names:** the framework (methods and tools) is **XDMOD** ("Cross-Domain MODeling", named like SYSMOD), repo `xdmod`. Each tool in it gets a **Latin stem with a `-trix` suffix**, like affirmatrix and probatrix. The example repos use the prefix `robarm-` (`robarm-manifest`, `robarm-syseng`, `robarm-ee`, `robarm-me`, `robarm-sw`). | 2026-11-14 | *Extended by D73: `robarm-integration`.*
| D50 | **Merging:** trunk-based on `main`. Every change goes through a PR, required checks must pass, and PRs are **rebase-merged** (linear history). Enforced with org rulesets. | 2026-11-14 |
| D51 | **Agent identity:** agents work under the user's account, and their commits carry a `Co-Authored-By` trailer. GitHub does not let you approve your own PR, so rulesets **require passing checks but no approval count**. The user's review and merge is the approval. | 2026-11-14 |
| D52 | **Changes across repos:** the same branch name is used in every repo the change touches. CI checks out sibling repos at that branch if it exists, otherwise at the manifest pin. Upstream merges first, then one manifest PR bumps all pins. | 2026-11-14 |
| D53 | **Planning:** `plan.md` stays the master plan. Tasks become GitHub issues in the repo where the work happens, and PRs close them. An org Projects board is optional. | 2026-11-14 |
| D54 | **Tags:** each repo uses SemVer tags `vX.Y.Z`. Baselines are manifest tags `baseline/vX.Y.Z`, and their GitHub release carries the outputs. | 2026-11-14 |
| D55 | **Docs hosting:** GitHub Pages on the manifest repo hosts the full linked set, with `main` as "latest" plus one folder per baseline. PR docs are CI artifacts. This adds **multi-version hosting**, which zdocs lacks today. The model to follow is the tiacsys/bridle docs. | 2026-11-14 |
| D56 | **X1 CI scope:** in iteration 1, GitHub CI builds docs and traces **without CAD content**, so its trace graph is partial. Full builds that include KiCad and FreeCAD content run only through the local one-command check (D46). Refines D47. | 2026-11-14 |
| D57 | **X2 HIL evidence:** HIL run records (`sha256(zephyr.bin)`, manifest repo SHAs, Twister JUnit/JSON, evidence rule: clean tree and pinned versions) live on **their own orphan branch in robarm-sw**, the same idea as affirmatrix's `case` branch. The test report reads them from there. *Revised by D73: the evidence branch lives in robarm-integration.* | 2026-11-14 |
| D58 | **X3 Agents and evidence:** agents analyse suspect links and prepare affirmations and verdicts, but **only a human's commit counts** as an affirmation or verdict. Refines D3. | 2026-11-14 |
| D59 | **X4 Suspect links:** we use **affirmatrix** and adapt it through **issues and PRs on tiacsys/affirmatrix**. Needed changes: read imported/upstream needs, accept open link types from our table (D36), take input from our needs.json extractors. | 2026-11-14 |
| D60 | **X5 SHAs:** rebase merge stays. **Evidence is recorded only against commits on `main` or baseline tags**, after merge. Runs on PR branches are previews and are not kept as evidence. | 2026-11-14 |
| D61 | **X6 Cross-repo flow:** D52 stays for PR CI. In addition, a **bump bot**: each merge to `main` in a robarm repo opens or updates a manifest bump PR, and that PR's CI builds the full set. | 2026-11-14 |
| D62 | **X7 zdocs gaps** (version_project ignored for Sphinx docs; every indirect upstream doc must be listed by hand; no import-only mode) are fixed through **issues and PRs on tiacsys/zdocs**. Until those merge, the framework uses workarounds. Refines D34 for these three gaps. | 2026-11-14 |
| D63 | **X8 FreeCAD storage** (resolves D41): `.FCStd` saved **uncompressed**, a git **textconv** for readable diffs, and a **review report** (drawing SVG, image diff, changed parameters and trace IDs) built locally and attached to the PR. | 2026-11-14 |
| D64 | **Small corrections from research:** (a) a drawio file "matches the model" means its content (labels, parents, edge ends, kinds, links), not its geometry (D38); (b) stubs: `concern` for stakeholder needs, `requirement` for system requirements, so SYSMOD's `frame` link is kept (D42); (c) every doc build runs strict (`-W --keep-going`) with zdocs' CI pins (D46); (d) OCI tags map `baseline/vX.Y.Z` → `X.Y.Z` (D54); (e) a removed requirement is first marked `retired`, and IDs are never reused; (f) devicetree trace IDs go in our own binding, never on upstream nodes; (g) CI checkouts use `fetch-depth: 0` and annotated tags; (h) link types are declared **per need type**, never globally (D36). | 2026-11-14 |
| D65 | **SysML toolchain:** OMG Pilot Implementation through `jshell` for checking and JSON export; our own Python tools read that JSON; Sysand for libraries; SYSMOD library `mbse4u/sysmod-sysmlv2`. Syside isn't used, because its CLI and Python library need a paid licence. | 2026-11-14 |
| D66 | **xdmod is in every workspace** that uses the framework, as a west project in its manifest. | 2026-11-14 |
| D67 | **All commands run from the workspace root** (the west topdir). That includes CLI tools (west, claude, doc builds, checks, extractors) and **launchers for GUI tools** (KiCad, FreeCAD and others), so paths and environment are set up correctly. git is the only exception. | 2026-11-14 |
| D68 | **One west topdir at the workspace root.** The root holds `.west/`, `.venv/`, `build/` and all repos. | 2026-11-14 |
| D69 | **Agent material in repos:** each repo has a `claude/` subfolder. A **launch `CLAUDE.md`** for the workspace root lives in xdmod and is **copied there during workspace bootstrap**. | 2026-11-14 |
| D70 | This workspace's planning folder (`claude/`: plan, research, notes, mission brief) **moves to `xdmod/claude/`** once the xdmod repo exists (Phase 4). | 2026-11-14 |
| D71 | **Every tool runs with a memory limit and a timeout**, for humans' scripts and all agents alike. The limits are set per tool and use. Swap is off inside the limit, so a runaway tool is killed and can't stall the machine or block agents. Interim wrapper: `.venv/bin/xd-limit` (systemd user scope + `timeout`); xdmod's command layer takes this over (3.13). | 2026-11-14 |
| D72 | **Provenance on GitHub:** everything an agent posts on the user's behalf (issues, comments, PR descriptions, reviews, release notes) ends with the trailer `🤖 Generated with [Claude Code](https://claude.com/claude-code)`. Commits keep the `Co-Authored-By` trailer. Extends D51. | 2026-11-14 |
| D73 | **New repo `robarm-integration`.** It holds system test cases (`INT-STC`), integration test cases (`INT-ITC`), the HIL setups, and the **orphan evidence branch** for HIL runs. Revises D57, which put that branch in robarm-sw. robarm-syseng stays the left side of the V (needs, requirements, model). | 2026-11-14 |
| D74 | **Prototype wiring is EE content** in robarm-ee: a KiCad schematic of each prototype setup, whose elements are `EE-CMP` with `variant: prototype`. They realize the `SYS-PROTO` / `SYS-EL` elements. *Field changed by D103 (`configs`).* | 2026-11-14 |
| D75 | **Retired needs get a grace period until the next baseline.** On `main` and in PRs, a link to a `retired` need is a reported warning that doesn't fail the build. The baseline build fails while any such link remains. Refines D64e. | 2026-11-14 |
| D76 | **SW architecture** is written in rst in iteration 1. A SysML SW sub-model in robarm-sw is tried in iteration 2. | 2026-11-14 |
| D77 | **Code links:** a code unit (`SW-IMPL`) must `implements` a SW design element. It **may also `satisfies` a `SW-REQ` directly**, as in the safety repo. | 2026-11-14 |
| D78 | **ID format** `<DOMAIN>-<KIND>-<NNNN>` with a 4-digit number. Domains are `SYS`, `SW`, `EE`, `ME`, `INT`. Examples: `SYS-REQ-0012`, `SW-TC-0103`, `EE-CMP-0007`. Test results: `TR-<test case ID>-<run hash>`. | 2026-11-14 |
| D79 | **No project code in the sources.** A project code with the separator `:` (e.g. `RA:SYS-REQ-0012`) is added only where IDs leave the workspace: bundles, published `needs.json`, shared affirmatrix cases. | 2026-11-14 |
| D80 | **SW test case IDs** come from the ledger and are written into the ZTEST comment by a tool, like safety's `@testid`. | 2026-11-14 |
| D81 | The **problem statement** (SYSMOD step 03) is a `SYS-NEED` with `category: problem`. Other needs and objectives link to it with `addresses`. A `concern` stub is generated for it. | 2026-11-14 |
| D82 | **System objectives** (SYSMOD step 06) are `SYS-NEED` with `category: objective`. No separate kind. | 2026-11-14 |
| D83 | **Requirement values** (quantity, unit, min/max/nominal, EARS pattern) are need fields next to the EARS text. They are copied into the `requirement` stubs as attributes and checked against the sentence. | 2026-11-14 |
| D84 | The **SYSMOD v5 library** (`mbse4u/sysmod-sysmlv2`) is a **west project** pinned at a commit. Sysand stays optional. | 2026-11-14 |
| D85 | Iteration 1 includes a **short functional architecture** (SYSMOD 10a): functions realize use cases, and logical elements realize functions (`functional2logical`). `SYS-EL` gets a `layer` field (`functional`, `logical`, `product`). | 2026-11-14 |
| D86 | **West submanifests and project groups.** The manifest repo splits its project list into submanifest files (one per area, e.g. framework, syseng, ee, me, sw, integration), imported by the main `west.yml`. Projects carry **groups**, so each engineer or agent checks out only what their role needs (`manifest.group-filter`). A role's group set always includes its upstream repos and the framework (D35, D66). Details are in task 3.4. | 2026-11-14 |
| D87 | **Zephyr:** for now, every role checks out the full Zephyr tree, including roles that only build docs. A smaller doc-only subset may come later. | 2026-11-14 |
| D88 | **Component libraries are pinned west projects, isolated from user-global setups.** EE uses the tiacsys KiCad libraries (`kicad-symbols`, `kicad-footprints`, `kicad-packages3D`, `kicad-templates`, `kicad-library-utils`). ME uses the FreeCAD parts library (`FreeCAD/FreeCAD-library`). KiCad projects use project-local library tables that point into the workspace through variables, and the GUI launchers (D67, 3.13) set those variables. FreeCAD gets its parts path from its launcher. User-global libraries are not used. The big libraries (`kicad-packages3D` about 1.8 GB, FreeCAD-library about 5.7 GB) get their own groups (D86) and shallow clones. | 2026-11-14 |
| D89 | **Bump bot = a scheduled poll** in robarm-manifest (e.g. every 30 min, plus manual). It uses its own `GITHUB_TOKEN`, so no extra secret is needed. Because PRs opened with that token don't trigger CI, the job builds the full set itself and reports on the bump PR. Refines D61. | 2026-11-14 |
| D90 | The **integration role** checks out everything except the big libraries (KiCad 3D models, FreeCAD parts). | 2026-11-14 |
| D91 | **Workspace paths:** design repos at the top level; dependencies under `tools/` (zdocs, affirmatrix) and `libs/` (SYSMOD, KiCad, FreeCAD). | 2026-11-14 |
| D92 | robarm-manifest pins **xdmod by SHA** for now. Once xdmod has a stable release for other workspaces, it gets SemVer tags. | 2026-11-14 |
| D93 | The manifest's **default group filter is minimal** (framework, syseng, Zephyr). Each role switches its groups on. | 2026-11-14 |
| D94 | **View definitions live in the model:** SysML v2 `view`s (in `views.sysml`) with `expose`/`filter` and an `@XdView` annotation naming the view kind. | 2026-11-14 |
| D95 | **Trace graphs** are drawn with sphinx-needs `needflow` (graphviz), not drawio. The user has a separate tool for analysing trace graphs interactively in the works. | 2026-11-14 |
| D96 | **Views are committed as editable SVG** (`<view>.drawio.svg`: the rendered picture with the drawio diagram embedded). They are rendered locally with stable IDs and a hash of the embedded diagram. CI checks the content against the model and the freshness of the picture, without a browser. Refines D38. | 2026-11-14 |
| D97 | **drawio desktop 31.7.0** is installed as a system package (`/usr/bin/drawio`). It is used to open and arrange views, and to test the editor round trip. | 2026-11-14 |
| D98 | **One xdmod tool, `curatrix`,** with subcommands `check`, `gen`, `ids`, `views` and later `bootstrap`/`launch`. Refines D49 for the framework's own tooling. | 2026-11-14 |
| D99 | **Verification coverage (CK-B2/R2)** is a warning in iteration 1, and an error at the baseline gate from iteration 2. | 2026-11-14 |
| D100 | **Pre-commit hooks** (normalizers, ID placeholders, fast checks) are installed by the bootstrap in every active repo. | 2026-11-14 |
| D101 | **robarm-sw CI builds the firmware** with the Zephyr SDK, runs the devicetree-vs-model check (CK-F2), and runs unit tests on `native_sim`. This is not CAD, so D56 doesn't exclude it. | 2026-11-14 |
| D102 | **Variants follow VAMOS, in SysML v2 through PLEML** (MBSE4U, MIT, pinned west project). The core is the functional and logical architecture. A feature model, a 150 % product architecture with variation points bound to features, and one product model per configuration complete it. Revises D37. | 2026-11-14 |
| D103 | **Variant fields:** design elements and test cases carry `configs` (list of `SYS-CFG` IDs, derived where possible), requirements carry `where` (feature condition, matching EARS "Where …"), and test results carry `config`. These replace the `variant` field of D37; D74's prototype wiring uses `configs`. | 2026-11-14 |
| D104 | **Coverage per configuration:** requirements carry `verification_scope` (`logical`: evidence from any configuration counts; `config`: evidence needed per applicable configuration). The coverage report is a requirement × configuration matrix. | 2026-11-14 |
| D105 | **Variant rules** F1–F2 (feature model), V1–V6 (product models), T1–T3 (traces) replace R6. All are errors and checked by `curatrix check variants`. Several feature bindings on one element mean AND. | 2026-11-14 |
| D106 | **One variant-aware doc set** with configuration badges and a generated page per configuration. No separate doc set per variant. | 2026-11-14 |
| D107 | **IDs:** `SYS-CFG` for configurations and `SYS-FEAT` for features. `SYS-PROTO` is dropped (never issued). | 2026-11-14 |
| D108 | **FreeCAD review report** is published as a **Pages preview** of robarm-me (`previews/pr-<n>/`), linked from the PR (with the provenance trailer) and removed when the PR closes. | 2026-11-14 |
| D109 | **Test reports are separate documents**: one spec doc and one report doc per domain and for integration. | 2026-11-14 |
| D110 | **CAD-derived needs are committed** (`generated/cad-needs.json`, stable and sorted), generated and checked locally and at the baseline. CI imports them, so CI sees the full trace graph. Refines D56. | 2026-11-14 |
| D111 | The **XDMOD manual is part of the robarm full set**, built from the pinned xdmod. robarm docs link to method pages; xdmod never links to robarm. | 2026-11-14 |
| D112 | **One EE design doc per PCBA** and **one per prototype configuration**. **WireViz** is evaluated for wiring harnesses (prototype jumper wiring, cables between boards). | 2026-11-14 |
| D113 | The **bootstrap assembles `<workspace>/.claude/`** (skills, commands) as symlinks into `xdmod/claude/` and the active repos' `claude/` folders, prefixed by repo. | 2026-11-14 |
| D114 | **robarm-sw is a Zephyr module** (`zephyr/module.yml` with `dts_root`/`board_root`). | 2026-11-14 |
| D115 | **Tests live by what they verify.** A test that verifies a `SYS-REQ` or `SYS-IF` lives in robarm-integration, even if it touches one domain only. Tests of domain requirements stay in their domain repo. | 2026-11-14 |
| D116 | The command layer is **only `curatrix`**; there is no west extension alias. | 2026-11-14 |
| D117 | **GUI tools** started by `curatrix launch` get a **memory limit only** (8 GB, no swap), no timeout. Refines D71. | 2026-11-14 |
| D118 | **`bootstrap.sh` is a copy in robarm-manifest** (`scripts/`), made from `xdmod/templates/bootstrap.sh`. A check warns when the copy drifts from the template. | 2026-11-14 |
| D119 | **Sign-off:** agents may add `Signed-off-by` in the user's name where a repo's convention requires it, always together with the `Co-Authored-By` trailer. The user certifies by reviewing and merging. | 2026-11-14 |
| D120 | **Decisions become sphinx-needs.** Framework decisions are `XD-ADR-nnnn` in the xdmod manual. Robot-arm decisions are `PRJ-DEC-nnnn` in the `robarm` overview doc (robarm-manifest). The old D-number is kept as `legacy_id`. New ID domains `XD` and `PRJ` (extends D78). **In rst, every mention of a decision (and of a rule or check) is a real `:need:` reference.** | 2026-11-14 |
| D121 | **Method rules are needs** `XD-RULE-nnnn` (each `decided_by` an `XD-ADR`). Each curatrix check is a generated `XD-CHECK` need that `enforces` a rule. | 2026-11-14 |
| D122 | **Agent-readable docs:** the **sphinx-llm** extension is tried for llms.txt / Markdown output of the doc sets. | 2026-11-14 |
| D123 | **GitHub admin by agents** (repos, rulesets, labels, Pages settings) only after the owner approves each concrete action list. | 2026-11-14 |
| D124 | **Posting approval:** agents post freely in robarm-* and xdmod (with the trailer). On other repos (zdocs, affirmatrix, upstream projects), they draft first and post after the owner's approval. | 2026-11-14 |
| D125 | **Parallel agents work in git worktrees** under `<ws>/.worktrees/<branch>/<repo>` (`curatrix work start/done`). Shared parts aren't duplicated, and builds go to `build/wt-<slug>/` (`feat/x` -> `build/wt-feat-x/`). | 2026-11-14 |
| D126 | **Every PR in robarm-* and xdmod gets an agent review** (by an agent other than the author, `/review-pr`) before the owner's review. | 2026-11-14 |
| D127 | **PR CI sibling resolution:** same-name branch → the repo's `main` if the manifest pin is an ancestor of it → manifest pin. So downstream PRs see upstream changes merged but not yet bumped. Refines D52. | 2026-11-14 |
| D128 | **The definition holds the trace ID** (SysML `part def`, KiCad sheet file, FreeCAD part file). Usages are listed in an `instances` field, not as separate needs. A usage gets its own ID `<ID>.<n>` only if it has its own requirement. | 2026-11-14 |
| D129 | **Only model elements with trace links become `SYS-EL` needs** (satisfy, allocate, or linked from another repo). They get a short-name ID when their first link appears. `layer` gains `context` (actors, system ports, system of interest). | 2026-11-14 |
| D130 | **Retiring generated needs:** status comes from the source (SysML metadata, KiCad `Status` field, FreeCAD `Status` property, Doxygen tag). Deleting without retiring first leaves a tombstone in `generated/retired-needs.json` until the next baseline. `draft` needs take part in structure checks but don't count as coverage. | 2026-11-14 |
| D131 | **Evidence validity:** a test result counts only if its recorded SHAs (and firmware sha256) match the current pins on `main` or the baseline being built; otherwise it's `stale`. Each baseline records the evidence branch SHA. Analysis, inspection and demonstration evidence are authored `TR`s with `method` and reviewer, under the same rule. | 2026-11-14 |
| D132 | **Suspect links before affirmatrix:** "last confirmed" = the last baseline's `needs.json` (for PRs: `main`'s). Hashed fields: title, content, status, value fields, links. | 2026-11-14 |
| D133 | **ID collisions:** rulesets require PRs to be up to date with `main` before merge, and the ledger lists every issued number per kind, so that concurrent issuing conflicts in git. | 2026-11-14 |
| D134 | **Agent limits stay policy only in iteration 1** (agents use the owner's login, D51). Technical enforcement (a GitHub App identity or signed commits) is in the iteration 2 backlog. | 2026-11-14 |
| D135 | **Scope cuts for iteration 1:** variants start with `buildKind` and rules F1, F2, V1–V5; the FreeCAD review report stays local (D108 deferred); robarm-ee and robarm-me start with one doc each. | 2026-11-14 |
| D136 | **Phase 4 GitHub action list approved** (D123): create the 7 public repos (`xdmod`, `robarm-manifest`, `robarm-syseng`, `robarm-ee`, `robarm-me`, `robarm-sw`, `robarm-integration`); settings (rebase merge only, delete branch on merge, Issues and Projects on, Wiki off); org ruleset `xdmod-main` (PR required with no approval count, up-to-date branches, linear history, no force push or deletion, admin bypass; required checks added once CI exists); labels; issues in project "xd-mod" (#3); Pages on robarm-manifest. Phase 4 runs autonomously within this list. | 2026-11-14 |
| D137 | **Licence: Apache-2.0 for all repos** (code, models, CAD, docs). | 2026-11-14 |
| D138 | **Zephyr SDK 1.0.1, ARM toolchain only**, installed into `.venv/opt/zephyr-sdk` and recorded in robarm-sw's `tools.yaml` with sha256. | 2026-11-14 |
| D139 | **Workspace root before `west init`:** `spike/`, `zdocs-tests/` and `.venv-zdocs/` move to `archive/`. The `zdocs/` clone becomes the west project `tools/zdocs`, pinned to the PR branches (task 4.3a). `extra/` and `build/` stay. Nothing is deleted. | 2026-11-14 |
| D140 | **Phase 4 merge rights:** initial skeletons go straight to `main` of the new repos before the ruleset is switched on. After that, all Phase 4 work goes through PRs, and the coordinator agent may merge them in xdmod and robarm-* once CI is green and the agent review has no blocking findings. The owner gets a summary of each merge. This is a Phase 4 exception to D51/D58. | 2026-11-15 |
| D141 | **Rulesets are per repo, not per org.** Org rulesets need the GitHub Team plan. Each of the 7 repos has the same `xdmod-main` ruleset on its default branch: PR required (0 approvals, rebase only), linear history, no force push, no deletion. The admin role may bypass **only through a PR** (no direct pushes to `main`). Required status checks and "branches up to date" (D133) are added in task 4.4, once each repo's CI check names exist. Refines D136. | 2026-11-15 |
| D142 | **Required checks (task 4.4):** in each repo's `xdmod-main` ruleset, required status checks with "branches up to date" (D133) from the GitHub Actions app: xdmod `tests` + `check / check`; robarm-syseng, -ee, -me, -sw, -integration `check / check`; robarm-manifest `full-set` (check run on normal PRs, commit status on bump PRs). CI installs the pinned Doxygen 1.18.0 from the release tarball, because Ubuntu's 1.9.8 breaks `sw-api`. | 2026-11-15 |
| D143 | **Pages:** live at https://tiacsys.github.io/robarm-manifest/ (`latest/` from `main`, `vX.Y.Z/` per baseline, `versions.json`, switcher). Publishing builds at the exact pins; **PR dry runs resolve siblings like PR CI** (D127). The bump bot moves a pin only when the compare API says it is behind `main`; a failed compare stops the run unchanged. **Stacked PRs with rebase merge:** after each merge, rebase the next PR onto `main` with only its own commits (`git rebase --onto`), because GitHub's own update conflicts on the rewritten commits. | 2026-11-15 |

## Review log

- 2026-11-14: A Fable agent reviewed the plan. Accepted findings led to D35–D45, the thin spike (Phase 2), an earlier change
  scenario with removal (2.3), new research topics (variants, CAD review and agent authoring, multi-repo workflow,
  parameter exchange, HIL, SPDX, 29148, hands-on runs), and the scope cut (D43).
- 2026-11-14: A Fable agent reviewed the Phase 3 results (`framework/*.md`). Mechanical fixes were applied directly:
  - check IDs renamed to `CK-*`
  - `.drawio.svg` used everywhere
  - leftover prototype-variant wording removed
  - `SYS-VIEW` reserved as a kind that is not a need
  - FreeCAD JSON split into a plain-Python trace part and a FreeCAD shape part
  - CI full set uses the integration role
  - `<area>` defined
  - limits fall back to `timeout` + `ulimit` on GitHub runners
  - `raised_by` link added; `runs_on` dropped
  - D115 conflict in the link table fixed
  - plan tasks 4.5a (run-record schema), 5.14 and 6.1a (baselines) added

  The findings that need decisions became R1–R9.
