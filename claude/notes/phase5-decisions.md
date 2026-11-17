# Phase 5: decisions of the agents and the owner

Moved from the coordinator's working file `build/phase5-work/decision-log.md` (task 5.32), because
`build/` is emptied before the owner's review. Cleaned up: one section per task, in task order; every
decision, merge record and item for the owner is kept, and facts are updated from main where they
changed since (marked where the 5.32 agent added something). Open owner actions and decisions are collected in
`phase5-owner-actions.md`; what moved to iteration 2 in `iteration2-list.md`.

How Phase 5 ran: the owner asked (2026-11-17) to work through the blocks of Phase 5 one after
another, to stop only when something really blocks, to assume agreement with the coordinator's
decisions, to ask a Fable agent for a second opinion when in doubt, and to report every such decision
for a joint review. Each entry says what was decided, why, and how to undo it where that is not
obvious. "**For the owner**" marks an item that needs the owner.

## Owner decisions during the phase (2026-11-17)

- **StepUp (5.28):** try it with `HOME` sandboxed under `.xdmod/` for that process only, pinned by
  commit; record the licence gap; fall back to the scripted STEP path if scripting fails.
- **Create `tiacsys/robarm-freecad-pcba` now** (only this admin action; the rest of the 5.9 list
  waits for the owner).
- **Workspace-local tool shims** in `.venv/bin` (`kicad-cli`, `FreeCADCmd`, ...) and the hard rule
  "never run KiCad or FreeCAD outside curatrix or its shims, not even `--version`" (XD-ADR-0145).
- **No Blender** for 5.30 (renderings with FreeCAD's own means), **later reversed**: Blender as an
  optional local renderer, used through its executable, isolated, with the plain-Python renderer as
  the fallback (XD-ADR-0148, see 5.30).
- **Review fix of 5.22:** the `connects` minimum in `needs_config.toml` lowered from 2 to 1 (a cable
  whose two ends share a port def keeps one target); the two-ends rule lives in CK-F1 only. One
  `curatrix cam <repo> [<name>]` for boards and harnesses (`kind` in `cam.json`).
- **End of the phase:** before the owner's review, every worktree set is removed, `build/` is
  emptied and the workspace is at the manifest pins; the owner builds all outputs from a
  step-by-step guide. The decision log and the admin actions move into xdmod `claude/notes/` by PR
  in 5.32 (this file). The `docs/self-model-views` set was removed (branch pushed, PR #25 open).
- **The Phase 5 review** (5.32) by another agent runs on Fable, like the Phase 4 review.

## 5.1 Check runner honesty (feat/check-honesty, all seven repos)

- New check IDs **CK-H6** (expect list) and **CK-H7** (PR size), with XD-CHECK-0030/0031, rules
  XD-RULE-0045/0046 and one decision XD-ADR-0125 "Checks that bite". Every check needs an ID, a rule
  and a catalogue entry (D121); one ADR covers all of 5.1.
- **`expect:` must equal the enabled checks exactly** (built-in and commands), not only be a subset:
  a subset would not catch a new section that adds checks silently. Undo: relax `c_expect` to
  "expected is a subset of enabled".
- **CK-H7 counts added and removed lines** of non-generated files, ignores renames and binary files,
  and treats `generated/`, `model/generated/`, `views/`, `*.drawio.svg`, test `fixtures/` and the
  output paths named in checks.yaml as generated. Defaults 600 lines / 15 files, per repo
  `pr_size:`. Base: `XD_BASE_REF`, else `GITHUB_BASE_REF`, else `main` of the first remote. A warning
  at local and PR; it never fails.
- **A missing checks.yaml is an error everywhere** (`check` and the `gen`/`views` commands). An empty
  plan is a config error.
- **At the baseline stage every skipped error-level check fails**, including CK-G2 without `--base`
  and CAD checks with `--no-cad` (P4-4 item 3). So a baseline needs `--base`.
- **A `west list` failure is no longer silent:** a warning and the folder scan as fallback; CK-B6
  fails when no pinned SHA is known. A warning, not an error, because `doctor` and other commands
  use the repo list outside a west workspace too.
- **CK-H5 switched on for robarm-manifest** (`bootstrap_template: scripts/bootstrap.sh`; the crash
  that kept it off was fixed in xdmod#9).
- Agent review of xdmod#28: the must-fix (CK-H7 base in CI) was handled. **Left open on purpose:**
  (a) CK-H6 compares check IDs, not stages, so a command that drops a stage still passes; (b) a
  missing checks.yaml cannot write a failed `summary.json` (no area known), so an old summary can
  stay. Both small; revisit if they bite.
- **Merge order with a new config key:** old curatrix rejects `expect:`, new curatrix requires it, so
  robarm CI was red for the minutes between the xdmod merge and the sibling merges. Accepted then;
  for the future, introduce a key as optional first (now in `xdmod/claude/CLAUDE.md`).

## 5.2 One source for the trace model (feat/trace-model-source)

- New module `curatrix/tracemodel.py` reads `needs/needs_config.toml`; `graph.LINK_TYPES`,
  `graph.REQ_TYPES`, `ids.NEED_KINDS`, `ids.DOMAINS` and all ID regexes come from it. `LINK_TYPES`
  now includes `revises` and `supersedes` (the drift the review found).
- **Requirement types = directives ending in `-req`** (a naming rule of the ID scheme), because the
  toml has no category marker for types. `TR_DOMAINS` stays a constant, but a test compares it and
  the domain list with the toml's own `id_regex`.
- **CK-A4 and CK-A5 removed:** the schema rules XD-S-R3-* and XD-S-R5-* of `needs_config.toml`
  enforce them in CK-A6. Their catalogue entries stay with `retired:` and their XD-CHECK needs are
  rendered `status: retired` (D130: retire before delete). Every repo's `expect:` drops them.
- **`checks.py` table as dataclasses (P4-17): not done** in that PR (a pure refactor that would
  conflict with open work); moved to the end of block A if time allows. Still not done: `BUILTIN`
  is a list of tuples (iteration 2 list).

## 5.3 Canary C0 (robarm-syseng#8, robarm-ee#6, robarm-me#6, robarm-sw#6) and fixtures (xdmod#33)

Built by a delegated agent, reviewed by another. Decisions taken there:

- **SW-ARCH-0001 added** (the schema requires every SW-DD to refine a SW-ARCH).
- **SW-TC-0001 written by hand** until task 5.10 extracts test cases from ZTEST comments (5.10
  replaced it by the generated need, same ID).
- **The `configures` dependency lives in `product.sysml`**, not `configs.sysml`: the Pilot reads
  model files one by one in name order, so a forward reference fails. Pitfall carried to 5.15.
- **A usage named `unit` was renamed `canaryUnit`:** `satisfy ... by unit` resolved to the stub's
  `unit` value attribute and the satisfies link went missing without an error. Pitfall for the
  modelling skill; a check "a `satisfy` whose target is not a part" is an idea.
- **`.kicad_pro` saved by KiCad's pcbnew Python module** (`kicad-cli` cannot save a project); this
  also writes an empty `.kicad_pcb`.
- Model-generated SYS-EL/SYS-CFG needs could not carry `configs` (fixed in 5.15/5.16).
- **No HIL result** (agents have no hardware). A sim record (`curatrix evidence record --kind sim`)
  was validated as a dry run; writing it needs `main`. **For the owner:** the HIL result.
- Fixtures (xdmod#33): the `PLANTED` table and `curatrix fixtures`, plus a control test for the
  clean strict build. CK-A2 is covered inside CK-A6; the CK-F commands got planted errors with the
  domain tooling (5.17-5.25).
- **Rule-4 incident 1 (for the owner):** the agent's first `pcbnew` Python run went through `curatrix
  run --use kicad-cli`, which then (unlike `curatrix launch`) did not set `KICAD_CONFIG_HOME`. KiCad
  rewrote `~/.config/kicad/10.0/kicad_common.json` (same size, content change unknown). Fixed in
  xdmod#35: `curatrix run` with the `kicad-cli` or `freecad` limits always sets the workspace-local
  config. The owner may want to check that file.

## 5.4 CK-E2 compares numbers as numbers (xdmod#31)

- **CK-E2 is a warning everywhere** (was an error), as the plan says, until it ran on real
  requirements. The unit must stand right after its value, after the second number of a range, or
  after a ± term (review must-fix).
- **Known gaps, accepted while it is a warning:** a space as thousands separator can glue two numbers
  ("mode 2 100 cycles" reads 2100); `1e3`, `.5` and `2 × 10^6` are not read.

## 5.5 Tool pins (xdmod#32, robarm-syseng#7)

- **Minimum versions** for git (>=2.43), cmake (>=3.28), ninja (>=1.11), node (>=22), npm (>=10),
  dot (>=2.43): the versions of the CI runner. **Exact** pins for the tools that shape committed
  output or are installed by curatrix (Pilot, JDK, elkjs, drawio viewer, gh, ...). **firefox
  `160.*`** (it shapes the committed SVGs, but a patch release should not fail doctor). python3 stays
  `3.14.*`.
- Two tool files may pin the same tool as a minimum and an exact version; the stricter wins if they
  agree.
- **Provenance records are compared with the pins of every role** (so CI checks FreeCAD shape
  records without FreeCAD, xdmod#23); records of files that are gone are reported; a full `views
  build` drops them. `gen model` does not drop records (its file names are fixed by checks.yaml).

## 5.6 No robarm names in xdmod (feat/no-robarm-names)

- **"Framework repo" = a west project with a checks.yaml, plus xdmod** (`ws.is_framework_path`), used
  by `ci siblings` and the evidence writer. The reviewer confirmed it selects the same repos.
- **Evidence repo default** = the single `<project>-integration` framework repo, else `--repo` is
  required. The naming convention `<project>-<domain>` with no dash in `<project>` is now relied on
  (also by the `.claude/` link prefix); documented in the docstring.
- **The reusable workflow input `manifest` is required** (no robarm default); all robarm callers pass
  it (merged first).
- **gcc-multilib for native_sim by role** (`sw`, `full`) instead of by repo name.
- Text-only robarm mentions (README examples, run-record schema descriptions, the bootstrap.sh
  usage comment, `launch/CLAUDE.md`, which describes this very workspace) stay.

## 5.7 CI (xdmod#34, robarm-syseng#9, robarm-manifest#23)

- **CK-G1 base = the published needs of `latest/` on Pages** (main at the manifest pins), fetched by
  `curatrix ci base`, all or nothing; a fetch failure lets CK-G1 skip and never fails a PR. CK-G2
  (against the last baseline) waits for the first baseline (6.14).
- **CK-H4 = agent commits only**, recognised by "Claude Code" or anthropic.com in the message. Gap:
  an agent commit that names neither passes. Follow-up: a `commit-msg` hook keyed on the
  `CLAUDECODE` environment variable that adds the trailer (iteration 2 list).
- **Downstream full-set job** on xdmod and robarm-syseng PRs, reporting only (not a required check
  yet); about 3 minutes of runner time per push.
- **robarm-manifest `documents.yaml` had `base_url: http://localhost:8000/`** (a placeholder); it
  must be the Pages URL before a full-stage base is used. Not changed; still the placeholder at the
  end of Phase 5 (robarm-ee's registry already has the Pages URL).
- **Pages of robarm-manifest failed from the 5.1 merge** until the pin bump (the pinned xdmod predated
  `expect:`). The bump bot was triggered by hand (its schedule had not run since 2026-11-16 19:51).
  Lesson: a new checks.yaml key needs xdmod bumped in the manifest before or with the repos that use
  it (now in `xdmod/claude/CLAUDE.md`).
- **Stacked PRs** (part of 5.7): `curatrix work start --base <parent>`, sibling resolution through
  the PR's base chain, the size check and CK-H4 per layer.

## 5.8 Agent material (xdmod#36)

- **Merged (xdmod#36):** `xdmod/claude/CLAUDE.md`, the `/xd-review-pr` command with six checklists,
  the skills xd-sysmod-stakeholders-and-needs, xd-ears-requirements and xd-issue-ids (plus
  placeholder KiCad and FreeCAD skills), the workflow rules, and the demo script for block A.
- Under D140 only the coordinator agent merges, when there is an agent review without open must-fix,
  green required checks, and for robarm-ee/robarm-me the posted local CAD check run.
- Stacked PRs: measure a layer with `XD_BASE_REF=<parent>`; after the parent merges, retarget the
  child with `gh pr edit --base main`, force-push only the own branch.
- `/xd-review-pr` posts the check table and the findings; a reviewer uses a `review/<repo>-<n>` set
  when the author's set holds the branch.
- New pitfalls in the material: placeholders fail CK-A6 (run `ids fix` first); nested SysML packages
  must be `public package`; tests must not depend on `CLAUDECODE`, `XD_BASE_REF` or
  `GITHUB_BASE_REF`.
- The old `/review-pr` name stays in the XD-ADR-0115 record and in the robarm
  `claude/commands/README.md` examples (not worth five PRs).
- Follow-up recorded: the `commit-msg` hook keyed on `CLAUDECODE` (CK-H4 gap).

## 5.9 Admin actions (prepared, not executed)

- The concrete action list for the owner's approval (D123) is in `phase5-owner-actions.md` (moved
  from `build/phase5-work/admin-actions.md`). Only the creation of `robarm-freecad-pcba` was approved
  and done.
- **Action 3 (Actions may not approve PRs) is not recommended:** it is the same GitHub setting as
  "Actions may create PRs", which the bump bot needs, until the bump bot has its own identity
  (iteration 2, D134).

## 5.10 SW and integration tooling (xdmod#40, #42, #43; robarm-sw#7, #9)

- **CK-F2 (devicetree vs the EE board model) moved behind 5.15** (the EE board model did not exist),
  and was not built in Phase 5 (iteration 2 list). 5.10 did the rest: SW-IMPL / SW-TC extraction from
  code (generated, committed, checked like cad-needs), test results in the docs, a minimal trace
  report. The canary must merge first (5.10 changes its SW-TC need).
- New check **CK-D6** "code-needs.json matches the code" (XD-CHECK-0032, enforces XD-RULE-0033);
  `curatrix gen code-needs` reads `@xdid` blocks and ZTEST comments.
- Test results in the docs: `before_docs: true` for checks.yaml commands; a new **`curatrix evidence
  preview`** (Twister output to preview TR needs, tag `preview`, stable IDs), not `record --dry-run`,
  because a record allows one firmware image and robarm-sw has two test scenarios; a new repo command
  **CK-F5c** writes them; `xd-needimport :missing:` prints a sentence when there is no run. Real
  evidence ranks above a preview in the trace report.
- "Configs: SYS-CFG-0001." in the canary code comments (keeps the `configs` field).
- The Twister identifier is in the need's content (no fitting field in `needs_config.toml`).
- **`curatrix trace <repo|full>`** (md/html/json under `build/<area>/trace/`) is a command, not a
  check; the canary SYS-CFG is found by its title "canary" (`--canary` overrides); canary needs have
  their own section and are out of the coverage numbers.
- **Open:** a local full or Pages docs build on a machine that ran Twister also shows its preview
  results (tagged preview); only the canary has been through the code-needs reader.

## 5.11 Model spike (xdmod#37)

- A domain model that specializes the system model as a library set **works** (0 errors, about 15 s).
- The Pilot does **not** catch a missing or wrongly typed port redefinition, so curatrix must check
  both (became CK-E4). Double specialization works with one redefining port; the clash is only a
  Pilot warning (curatrix should report it). System IDs survive `compact`.
- `realizes` / `conforms` are derivable by joining the system model's committed
  `generated/model.json` by qualified name (no Java, so CI can run it).
- For 5.15: fix `top_packages` (brace depth), count an `ERROR:` export as an error, read a repo's own
  files as one set (forward references), add the EE/ME kinds, `model.conformance()`. `unit`
  resolution is normal SysML scoping (refer to outer elements by qualified name).
- The `model.top_packages` bug (indented nested packages taken as top level, so the Pilot export
  failed) was worked around in syseng with `public package Canary` and fixed in 5.15.

## 5.12 KiCad spike (xdmod#39) and KiCad isolation (xdmod#41)

- Design output through a jobset on a copy with the version written into `.kicad_pro` **works**
  (version in title block, frame, silkscreen, Gerber header). **A job can name a variant** (corrects
  P5-3). No native stackup or design-rule export (plain Python).
- Assembly variants work, and **any field can differ per variant**, so pin-header shunt positions can
  live in KiCad (decided in 5.14: EE model plus a per-variant field `Setting`).
- ERC/DRC JSON carries exclusions with comments, but a moved part loses its DRC exclusion and a stale
  ERC exclusion shows as a phantom accepted entry; `accepted.yaml` keyed by rule and designators
  stays right. An unrouted board has one DRC entry per missing connection. The XML netlist has pin,
  net and hidden fields. **MCP servers for KiCad cut** for iteration 1.
- Pitfalls for 5.20: an unparseable job makes `jobset run` run 0 jobs and exit 0; a BOM job without
  delimiters; ERC/DRC jobs fail the jobset on violations; the title block's Rev field truncates the
  version; variant jobs must copy the base job and match `schematic.variants`.
- `libs/kicad/packages3D` is not in the workspace for roles without `kicad-3d`, so renderings show
  bare boards.
- Isolation: KiCad also writes `~/.cache/kicad` and `~/.local/share/kicad`; xdmod#41 sets
  `KICAD_CACHE_HOME` / `KICAD_DOCUMENTS_HOME` under `.xdmod/` and `LC_ALL=C.UTF-8` for batch runs.
- **For the owner (unexplained):** `~/.config/kicad/10.0/kicad_common.json` was written at
  2026-11-17 02:30:43, not by the spike's runs and not by `curatrix doctor`. Most likely a direct
  `kicad-cli` call by an agent (see incident 2 under 5.19/5.20).

## 5.13 FreeCAD spike (xdmod#38)

- Master sketch across documents works only with the fallback **`assemblies/<name>/skeleton.FCStd`**
  (parameters and master sketch in their own document; the top-level document as master gives a
  document cycle). Model-driven spreadsheet writes work (one line of semantic JSON per value, no ID
  churn). Configuration tables and `Configs` presence work; LCS with `Port` and collision by boolean
  common work; the version emboss works.
- Exploded view: the GUI binary offscreen hung in 6 of 8 runs; **verdict: FreeCADCmd fallback** (the
  script builds the exploded compound and exports a TechDraw view as SVG, not a full page).
- **StepUp: not run in the spike** (it needs the GUI binary, writes `~/ksu-config.ini`, has no
  LICENSE file although AGPL is claimed, no releases, docs stop at FreeCAD 1.0). Owner decision: try
  it sandboxed (see 5.28).
- MCP servers for FreeCAD exist (MIT / Apache) but are not needed in iteration 1.
- Gaps for 5.23-5.27: the semantic JSON missed XLink targets, expressions, named constraints, `Port`
  as trace field and the variant table; FreeCAD backups (`*.FCBak`) to be switched off in the
  workspace config (done in 5.23: `CreateBackupFiles = false`).
- Findings for 5.24-5.26: FreeCADCmd exits 0 when the script raises (curatrix must check a result
  file); a raising script runs twice; `freecad_shapes` triggers FreeCAD's extra-argument import
  (traceback, exit 0).
- **Limits finding (rule 2):** a GUI FreeCAD survived an outer `timeout` around `curatrix run` and
  had to be killed by PID. To check whether curatrix's own timeout (systemd scope / ulimit fallback)
  kills the whole process tree (iteration 2 list).
- User config untouched (md5 before and after).

## 5.14 Decisions (xdmod#44)

ADRs XD-ADR-0126 to XD-ADR-0144. Own decisions of the writing agent:

- EE-HAR holds a new link `connects` (to EE-PORTs; minimum later lowered to 1, see owner decisions);
  EE-PORT/ME-PORT `part_of` optional (ports of external parts belong to no board); SW-ARCH/SW-DD may
  `conforms` to EE-PCBA/EE-PORT; `proposed` added to `decision_status`; `check_id` may carry a letter
  suffix (CK-F4a ERC, F4b DRC, F4c FreeCAD recompute); new CK-D checks start at CK-D7; every new check
  starts as a warning.
- A def without its own ID that specializes a system element is allowed only below the port level.
- Roles: `me` and `sw` also get the `ee` west group (no 3D models); doctor warns when KiCad 3D models
  are missing for a 3D role.
- **WireViz 0.4.1 pinned in xdmod's `requirements.txt`** (pip packages have no roles; `curatrix cam`,
  the harness directive and the full-set docs need it).
- Shunt positions: the EE model plus a per-variant KiCad field `Setting`.
- Process lessons: **a stacked PR was lost** (robarm-sw#8 was closed by GitHub when its parent #7
  merged and the branch was deleted; recreated). Retarget the child to `main` before the parent
  merges. A child that carries its parent's commits conflicts after a rebase merge of the parent: it
  must be rebased with `--onto` right after the parent merges (workflow.md §3a).

## 5.15 Domain models (xdmod#45, robarm-ee#7)

- CAD readers: an EE-PCBA / ME-ASM / port / harness TraceID in a CAD file is only a reference and
  makes no need (XD-ADR-0128); a need that moves to another generated file gets no tombstone.
- New check **CK-E4** (conformance, XD-CHECK-0033, XD-RULE-0047, warning); kind pairs without a link
  type and defs without an ID are CK-E4 findings. Library `xdmod/sysml/XdDomain.sysml` (board,
  external part, cable, assembly, connector, pin, mechanical port); variant names left to 5.16.
- Interconnection views draw the root's own ports; a board without inner parts gets a minimum box.
- **robarm-me had no model yet** (the canary was one part; an empty model section fails CK-E1); it
  came with 5.23. robarm-sw: no EE upstream yet. The `eeSw` view was skipped (the self-model with
  views is only on the unmerged xdmod#25).
- **Made up for the canary:** `CanaryHeader` (EE-PORT-0001) with a 2-pin map, nets CANARY_A/B; J1
  was drawn in KiCad in 5.18.
- `configs` for model needs now come from the SYS-CFG `configures` links; EE-PCBA-0001 lost its own
  `configs` and got it back that way. Conjugated ports and variant widening are handled in CK-E4.

## 5.16 Variants across levels (xdmod#46, robarm-ee#8)

- A domain variant: `part def X :> Board, XdDomain::DomainVariant { :>> variantName = "alt"; }`
  plus `dependency from X to <SYS-CFG>, <system usage>...`; no ID, no trace link.
- Pairs that need a variant: every usage of the realized system def times every configuration that
  configures it (all configurations if none does).
- New checks.yaml section `variants:` (optional `zephyr:` board roots), new check **CK-B8**
  (XD-CHECK-0034, XD-RULE-0048). Zephyr board name = KiCad project name with `-` as `_`; every Zephyr
  variant must be a board variant (not the reverse).
- The computed table "configuration to variant per usage" goes to the check log
  (`build/<area>/checks/variants-across-levels.md`), not to a Sphinx directive.
- Canary: only `default` names SYS-CFG-0001 and the usage; `alt` is unused (not checked in iteration
  1). KiCad variant entries written as text in the spike's format and read back by kicad-cli.
- **Not built:** CK-F13 (variant names and overrides across the EE model and the KiCad files,
  `Setting` per variant). robarm-sw has no board of its own (uses nucleo_g474re), so the Zephyr check
  has nothing to compare on the canary.

## 5.17 / 5.18 EE projects and connectors (xdmod#47, #48; robarm-ee#9, #10)

- New checks CK-F6, CK-F7 (projects, 1:1), CK-D7 (connectors.json fresh, plain Python, also in CI),
  CK-D8 (connectors vs KiCad's XML netlist, local), CK-F1 (pins and nets vs the EE model's pin maps).
  `curatrix new pcba <BoardDef> --repo R` with templates in `xdmod/templates/kicad-pcba/` (ERC
  severities from a KiCad 10.0.8 template project, 44 rules).
- A board def = a def that directly specializes `XdDomain::Pcba` (5.16 board variants stay out of the
  1:1 check). `proto/` projects are not 1:1-checked yet (no marker for prototype blocks).
- `Port` holds the EE-PORT def ID; two ports of the same def on one board are matched by count.
  Connectors = references J, P, CN, or any symbol with a `Port` field.
- Canary J1 drawn (Port = EE-PORT-0001, nets CANARY_A/B); its footprint on the PCB was open and was
  placed in 5.19 (the DRC errors J1.1-R1.1 show it). KiCad pitfall: a wire end inside another
  wire needs a junction.
- **Open:** buses, pin alternate names. User KiCad config untouched (33 entries, same timestamps).

## 5.19 / 5.20 ERC/DRC and EE design output (xdmod#49, #50; robarm-ee#11, #12)

- New checks CK-F4a ERC, CK-F4b DRC (with `--schematic-parity`), CK-F8 severities equal the
  template, CK-F9 acceptance; `curatrix cam`, CK-F10 (jobset sanity), CK-F11 (version variable use).
- **Acceptor rule:** the newest commit that wrote any line of the entry (git blame) decides; a later
  agent edit turns it back into a proposal. A KiCad exclusion: the commit that last added its key
  (git log -S), and that commit may change only the exclusion lists.
- **Rev field:** the full version goes into title-block comment 2, Rev stays empty (CK-F11 flags
  `${XD_VERSION}` in Rev). Side effect: the Gerber header shows `rev?`; the silkscreen shows the
  version.
- Variant jobs replace base jobs in a project with variants (id `<id>-<variant>`). KiCad pitfall: a
  job without a variant inherits the variant of the job before it, so CK-F10 requires the jobs
  without a variant first.
- Two separate branches (not stacked); IDs pre-split between the two xdmod PRs.
- **For the owner to accept (D58):** `robarm-ee/pcba/canary-board/accepted.yaml`, entry `check:
  CK-F4b, rule: unconnected_items, items: all` (2 DRC errors J1.1-R1.1, J1.2-R1.2; the canary is
  unrouted on purpose, XD-ADR-0144). Accept by a commit that touches only that entry, with an
  `Accepted-by: <name>` trailer and no agent trailer.
- **Open:** `cam` from a tag (tags are owner-only); STEP and renderings without parts
  (`libs/kicad/packages3D` not in the workspace for this role); CK-F9's git blame in shallow CI
  clones untested.
- **Rule-4 incident 2 (for the owner):** a review agent ran `kicad-cli --version` once directly; that
  alone rewrote `~/.config/kicad/10.0/kicad_common.json` at 06:29:22 (2598 to 2625 bytes). Likely the
  cause of the 02:30:43 write too. The proposal then: a `kicad-cli` / `FreeCADCmd` shim in
  `.venv/bin` that sets the workspace config and calls the real tool, `curatrix doctor` failing when
  `.venv/bin` is not first on `PATH` in agent sessions, and a hard line in xdmod `claude/CLAUDE.md`
  and the review checklist. It led to the shims and the hard rule (owner decision, XD-ADR-0145);
  doctor warns rather than fails.
  The owner may want to check the two changes to `kicad_common.json`.

## 5.21 Board document (xdmod#55, robarm-ee#14)

- Nine `xd-pcba-*` directives; a plain-Python BOM reader (`curatrix/bom.py`, equal to KiCad's BOM
  export for the base and both variants); new checks CK-F12 (Manufacturer/MPN, plain Python), CK-D9
  (BOM vs kicad-cli, local), CK-D10 (cam output of the current commit exists, local).
- `curatrix cam` also runs ERC/DRC and writes `findings.json` with acceptance states (tied to the
  commit like the renderings); the docs show cam output only from a run on the current commit (with
  uncommitted changes: newer than every changed file).
- A "standard part" for CK-F12 = a part with a field `Standard` (instead of Manufacturer/MPN).
- Renderings embedded as data URIs; PDFs named, not linked (zdocs doccheck rejects `file://` links).
- Fixed a bug of #51 (the harness document's link to the board document used the wrong zdocs name).
- **Open:** the harness diagram directive still shows the newest cam output (should reuse
  `cam.current`); zdocs incremental builds miss directive code changes (delete `build/<repo>/docs`).

## 5.22 Harness (xdmod#51, robarm-ee#13)

- Each harness end names its port in the connector `notes` (`Port: EE-PORT-....`; WireViz 0.4.1
  rejects other extra keys); the YAML names its cable in `metadata.TraceID`.
- The cable def has one port per end, typed by the conjugated port def it mates with; `connects` is
  derived from them. CK-F1 and CK-F7 extended (no new IDs), warnings.
- The canary cable realizes CanaryUnit through a dependency (no-orphans rule; no EE-REQ exists).
  External part CanaryTestLead with EE-PORT-0002. Limits `wireviz` 1G / 2m.
- A PLANTED entry may list several tests. #50 and #51 both added `cam`; the second to merge combined
  them.
- The agent fast-forwarded the main robarm-manifest checkout and ran `curatrix update` (to get
  WireViz into the venv): all main checkouts moved to the newest pins.
- **For the owner:** tag `canary-cable/v0.1.0` proposed (tags are owner-only).

## 5.23 / 5.24 ME assemblies and parameters (xdmod#53, #54; robarm-me#7, #8)

- A def whose short name is an ME-PART/EE-CMP ID is a reference to the CAD-owned part (no need), so
  the model can count part usages. Alias rule `<usage>_<attribute>` covers part usages too
  (`canaryPart_length`). `XdDomain::MechanicalPort` gets x, y, z, yaw, pitch, roll; new metadata
  `XdDomain::Tolerance` (later `@ModelMatchTolerance`); default tolerances 0.001 mm / 0.001 deg.
- The LCS lives in the skeleton (part `Skeleton`); the shared canary part takes its length from
  `skeleton#MasterSketch`. `CreateBackupFiles = false` in the workspace FreeCAD config.
- New checks CK-F3, CK-F14, CK-F15 (warnings at local, PR, baseline).
- FreeCAD finding: opened through the top document, the skeleton loads only partly (no Params); the
  writer opens the skeleton first and refuses partly loaded documents.
- Review fixes: **XD-ADR-0146 (proposed; refines 0137)**: `<usage>_<attribute>`, skeleton opened
  first, `<name>-skeleton.FCStd`; `@ModelMatchTolerance`; the canary part moved to
  `assemblies/canary-assembly/parts/`. **For the owner:** accept XD-ADR-0146.
- **Open:** variant rows of configuration tables (the canary has none); the ME block-diagram view;
  model.json grew about 5000 lines (SI unit expressions).
- Tool shims merged (xdmod#52, XD-ADR-0145) and installed in the main workspace (13 shims). Findings:
  (1) `curatrix update` had to run twice after a curatrix change (the running process keeps the old
  code when `west update` moves xdmod; fix proposed in xdmod#64, open at the time of writing).
  (2) **For the owner:** agent sessions (Claude Code's shell) do not have `.venv/bin` first on
  `PATH`, so a bare `kicad-cli` still reaches `/usr/bin`; doctor warns. Options: a workspace
  `.claude/settings.json` env `PATH` entry (needs the owner's OK, it changes how every session here
  runs), or the agent material telling agents to `eval "$(curatrix env)"` first (the rule is written;
  adherence is not enforced).

## 5.25 / 5.26 ME checks and design output (xdmod#56, #57; robarm-me#9, #10)

- Fastener = a `lib/` object with a `Standard` property; overlap tolerance 0.1 mm³ for jointed pairs,
  0.001 mm³ otherwise. Variants via `Configs` on links only (configuration-table rows not switched
  yet). Findings of shared documents (`parts/`, `lib/`) can be accepted in any assembly.
- CK-F18 (board inside its space budget): a skip with reason without a board model; "not checked
  yet" with one, until the budget form of 5.28 is checked (not built in Phase 5).
- TechDraw page export offscreen hangs; `drawing.svg/pdf` built in plain Python from FreeCADCmd views
  (fallback allowed by XD-ADR-0137); no editable title-block fields yet.
- Print profile `print/<name>.ini` copied next to 3MF/STL; emboss text `vX.Y.Z` (+`P` for a preview);
  DejaVu Sans Mono Bold vendored in xdmod with its licence; a run is a preview when `parts/`, `lib/`
  or `print/` have changes.
- 5.26 review fixes (xdmod#57 at d804d76, robarm-me#10 at 3d0d71c): CK-F19 renumbered to
  XD-CHECK-0056 / XD-RULE-0063. **Open nits:** versioned
  output file names; `MaxWidth` 16 on the canary part (needs a FreeCAD edit).
- **For the owner:** tag `canary-assembly/v0.1.0` proposed. **Configs on the link (not the part)**
  kept as the FreeCAD spike found; the owner to confirm.

## 5.27 Assembly document (xdmod#61, robarm-me#13)

- Eleven `xd-asm-*` directives; plain Python in CI (overview, parameters, materials, interfaces,
  BOM); the cam output of the current commit for drawing, exploded view, renderings, mass, findings
  (a fixed sentence otherwise).
- `curatrix cam` writes `mass.json` per variant and `findings.json` per run (one more FreeCADCmd run).
- Mass = solid volume times the density of `Material` from the new `curatrix/data/materials.yaml`;
  an own `Mass`/`Density` wins; printed parts count as solid (upper bound). Canary: 1.24 g, CoG
  (10, 5, 2.5) mm.
- CK-F12 / CK-D10 extended to ME (warnings, no new IDs): bought non-fastener parts need Manufacturer
  and MPN, own parts `Material`.
- robarm-me `me-design` imports `model-needs.json` (ME-ASM / ME-PORT were published nowhere before).
- Review fixes (#61): one `tree_state` hash for boards and assemblies, renderings from `cam.json`,
  sub-assembly chapters with every section (a fixed sentence where only the top level has data),
  units for Mass/Density.
- **Open:** findings of shared parts show in every assembly document; the board line and the
  sub-assembly chapters are only tested by fixtures; CK-H7 warned (1331 lines / 19 files).
- **For the owner (question added by the 5.32 agent, from the 5.27 agent's report and the review of
  xdmod#61; not in the decision log):** sub-assembly chapters print fixed sentences for drawings, exploded view,
  renderings and parameters (only the top-level assembly has them in iteration 1); confirm or ask for
  more.

## 5.28 Co-design (xdmod#59, robarm-syseng#10, robarm-me#12, robarm-ee#15)

- Spike: **StepUp push FreeCAD to KiCad (outline, holes) works** from a script in the GUI binary
  offscreen, `HOME` sandboxed (`.xdmod/stepup/home`), StepUp pinned at 3db98be under `.xdmod/stepup/`;
  holes as `Edge.Cuts` circles; `kicad-cli pcb upgrade --force` re-save; DRC clean. StepUp load
  KiCad to FreeCAD: **cut** (stalls offscreen); the scripted STEP path is used instead.
- Scope: keep-outs in iteration 2; connector positions are budget values but not pushed; **no push
  back from EE** (EE asks for a budget change on the same branch); harness length is a SYS-IF value,
  its route iteration 2.
- Licence gap recorded (no LICENSE file; AGPL-3.0 claimed). User dirs untouched; no
  `~/ksu-config.ini`.
- The hole-move scenario (hole 2 from x = 26 to 24 mm) ran through syseng, ME and EE on one branch:
  **exit criterion 4 met** once all merged.
- Own decisions: budget values as SysML `default` values; the board conforms to the budget via a
  dependency (a port would make CK-F1 ask for a connector); board frame = the outline's lower-left
  corner; **ME copies of budget values do not count toward the ten-parameter limit** (15 parameters,
  8 counted).
- Review must-fix: XD-ADR-0134 back to **proposed** (agents only propose; "try it" approved the
  spike, not the text). **For the owner:** accept XD-ADR-0134, and decide whether budget copies on a
  seat port count toward XD-ADR-0137's ten-parameter limit (the PR leaves them out).
- Merge order: xdmod#59, manifest bump, robarm-syseng#10, robarm-me#12, robarm-ee#15.
- **Open:** no curatrix command for the push yet (a wrapper script in `build/`, the manual shows the
  `curatrix run` line); StepUp not in `tools.yaml`; each push gives the `Edge.Cuts` items new IDs
  (KiCad exclusions on them are lost).

## 5.29 Board library (robarm-freecad-pcba skeleton and ruleset; robarm-manifest#39, xdmod#58, robarm-freecad-pcba#1, robarm-me#11)

- The repo sits at the workspace top level (`robarm-freecad-pcba/`, not `libs/`): worktree sets and
  CI sibling resolution handle only top-level repos. Files under `boards/`. No ids section (it owns
  no IDs).
- Ruleset 27440745 = a copy of robarm-me's, including today's bypass actors (the Admin-bypass
  removal still waits for the owner).
- **The initial push to the empty main** was allowed for the 5.29 agent (an empty repo has no main to
  open a PR against); afterwards only PRs.
- `curatrix cam <ee> <board> --board-model` (STEP on the build copy, headless FreeCAD import with
  TraceID/Version/Variant/Commit) and `--library [--into]` (tagged releases only, never overwrites);
  checks CK-F20 (library files vs board tags) and CK-F21 ("newer board version" note in robarm-me).
- STEP read as one shape (colours lost). **XD-ADR-0139 stays proposed** (owner to accept). Demo only
  with a local, never-pushed tag; the real canary has no tag (owner-only).
- IDs of #58 (XD-CHECK-0052/53, XD-RULE-0061/62) collided with #56/#57 and were renumbered at merge
  time (the first of the three ledger collisions; merge order #56, #57, then #58).

## 5.30 ME renderings (xdmod#60) and Blender (xdmod#62)

- Spike: the Render workbench is **no-go** (it needs an external renderer). Coin3D snapshots are
  **no-go** headless (offscreen `saveImage` gives a blank PNG, minimalegl dumps core, pivy
  `SoOffscreenRenderer` has no GLX context). **Go:** FreeCAD tessellation drawn into a numpy z-buffer
  with visible edges; Qt writes the text and the PNG. Note `claude/notes/me-renderings-spike.md`.
- Own decisions: the side view is `right` (as in `views/` and the drawing); colours by BOM kind, not
  from `GuiDocument.xml`; numpy (a FreeCAD dependency) inside FreeCADCmd. **XD-ADR-0147 proposed**.
  **For the owner:** accept XD-ADR-0147. User dirs unchanged.
- Owner decision (reverses "no Blender"): Blender 5.2.3 (system package) through its executable, no
  bpy wheel. Isolation: `BLENDER_USER_CONFIG/SCRIPTS/RESOURCES`, XDG and `TMPDIR` under
  `.xdmod/blender/`, `--factory-startup --offline-mode --disable-autoexec`, a curatrix wrapper and a
  `.venv/bin` shim, run without the venv. Not pinnable: Blender renderings are local only, doctor
  checks the version (`tools.yaml` `pinned: false`: missing is a note, another version a warning),
  CI uses the placeholder, `cam` falls back to the z-buffer renderer.
- Blender agent's decisions: an own `.glb` writer in `cam-asm.py` (FreeCAD's exporter has no colours
  in FreeCADCmd); Cycles CPU, 32 samples, seed 0, no denoiser, no shadows; orthographic iso; marking
  with blf at the same scale as #60; a failing Blender stops with a hint. Canary: 33 s with Blender,
  6 s without. Review fixes: the shim keeps `PATH`, `run -- blender` gets the blender limits, threads
  capped at half the cores. **XD-ADR-0148 proposed**.
  **For the owner:** accept XD-ADR-0148.
- Order: xdmod#60 (the fallback renderer) merged first, the Blender PR #62 was stacked on it.
- **Open:** overlapping faces mix in Blender. Do not run `curatrix update` from a main older than #62
  (its `write_shims` deletes the Blender shim it did not write).

## 5.31 Author loop (xdmod#63)

- Measured on the canary (`claude/notes/author-loop.md`). **No caching now:** the robarm-ee local
  check with CAD takes 28 s (limit 300 s); no command of the author loop takes more than 80 s; a role
  loop takes 0.5 to 1.5 minutes. User config unchanged over 126 measured commands.
- Options on record for when the canary grows: export only what curatrix reads from the Pilot
  (syseng exports 57 MB), reuse the Pilot result inside a loop, parallel Sphinx in zdocs (the console
  pool, see the issue draft `issue-drafts/zdocs-console-pool.md`), skip CK-A6 when `docs` just built
  the same tree.

## 5.32 Manual, fixture run, iteration 2 list

- Manual how-tos for the EE and ME roles (xdmod `docs/phase5-manual`), these records
  (`docs/phase5-records`), and the `curatrix update` fixes (xdmod#64, `fix/update-manifest`).
- The recorded local fixture run is in `phase5-fixture-run.md`; the draft iteration 2 list in
  `iteration2-list.md` (to be agreed by the owner, exit criterion 6).
- The Phase 5 review by another agent (Fable) follows.

## Merges and pin bumps (merge records)

- robarm-manifest#25 (pin bump, green full set): the manifest pinned xdmod 2844966 and the canary in
  every repo; the main workspace moved to these pins with `curatrix update`.
- Task 5.8 merged as xdmod#36 (see 5.8).
- Task 5.10 complete: xdmod#40, #42, #43, robarm-sw#7, #9 merged; pins bumped by robarm-manifest#26,
  #27, #28.
- Task 5.15 merged: xdmod#45, robarm-ee#7, pin bump robarm-manifest#29.
- Task 5.16 merged: xdmod#46, robarm-ee#8, pin bump robarm-manifest#30.
- Tasks 5.17/5.18 merged: xdmod#47, #48, robarm-ee#9, #10; pin bump robarm-manifest#31 and the next.
- Tasks 5.25/5.26: merge order xdmod#56, #57 (d804d76), then #58 (renumbered); robarm-me#10 at 3d0d71c.
- Task 5.28: merge order xdmod#59, manifest bump, robarm-syseng#10, robarm-me#12, robarm-ee#15.
- Task 5.29: robarm-manifest#39 (the new repo in the manifest), xdmod#58, robarm-freecad-pcba#1,
  robarm-me#11.
- Task 5.30: xdmod#60, then the stacked Blender PR xdmod#62.

## Workspace and process notes

- **Main of xdmod was red for about 30 minutes:** #33 and #34 were each green but were merged back to
  back without a combined run: the planted CK-H4 case of #33 used a commit message that the new
  agent-commit marker of #34 no longer counted. Fixed in #35. Lesson: rebase and re-run CI before merging the second of two PRs
  that touch the same check.
- **Canary merge order:** robarm-ee/me/sw merged before robarm-syseng#8, so their mains were red for
  a few minutes (their links point to syseng needs). Upstream first next time.
- **xdmod#35 merged with the non-required `downstream` check red** (red because of the canary order,
  not #35). The merge loop did not look at non-required checks; required ones are enforced by the
  ruleset.
- **Spikes 5.11-5.13 ran in parallel** with block B (reports only, independent of the open PRs);
  every agent was told to set the workspace-local config for every KiCad/FreeCAD run explicitly
  (the installed curatrix then predated xdmod#35) and to keep and report `~/.config` untouched; the
  reports showed it unchanged (the 02:30:43 write stays unexplained, see 5.12).
- **ID collisions between parallel xdmod PRs** happened three times (XD-CHECK/XD-RULE from the
  shared ledger). Practice: issue IDs (`ids fix`) right before pushing, merge the issuing PR first.
  Idea for iteration 2: a check that warns when a PR's new ledger numbers are already on main.
- **Resume after an interruption:** the first coordinator session stopped at 08:23 UTC with three
  agents running and the merge of robarm-manifest#39 in flight; the new session continued from the
  partial work in the sets.
- **`git pull` fails in robarm-manifest** ("Cannot rebase onto multiple branches", a global pull
  setting of the owner): use `git fetch` and `git merge --ff-only`.
- **`curatrix update` exited 1** after its last section "workspace state (.xdmod/)" without an error
  message once (doctor showed no FAIL; log `build/phase5-work/update.log`, now gone).
- **`curatrix update` did not move the manifest repo:** after bumps merged on GitHub, the local
  robarm-manifest `main` stayed 7 commits behind and `west update -k` checked out stale pins (xdmod
  went back to 6f566e8). Fixed by hand (`fetch` + `merge --ff-only`). Fix proposed in xdmod#64
  (`fix/update-manifest`, task 5.32, open at the time of writing): update fetches and fast-forwards
  the manifest repo when it is on its default branch and clean, and warns otherwise. The owner's from-scratch run would have hit this.
- **`curatrix update` ran old code after west moved xdmod** and crashed reading the new `tools.yaml`
  (`pinned:`); a second run worked. Fix proposed in xdmod#64 (open at the time of writing): update
  re-executes itself after the west step when xdmod's HEAD changed.
- The main checkout of robarm-syseng was behind the manifest pin for a while (`curatrix update` once
  the agents were idle).
