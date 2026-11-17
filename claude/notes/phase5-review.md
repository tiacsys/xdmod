# Review of the XDMOD Phase 5 work products

Reviewer: Fable agent, 2026-11-17 (task 5.32), independent of the agents that built Phase 5.
Reviewed state: xdmod `91e735c`, robarm-manifest `d1ddc5a`, robarm-syseng `d5ca703`, robarm-ee
`4078b4c`, robarm-me `41cf477`, robarm-freecad-pcba `8ea3e0a`, robarm-sw `1f74b98`,
robarm-integration `3afb138`. Every checkout was clean, at its manifest pin and equal to
`origin/main`. No other agent was running.

## What I ran

Logs are in `build/review-phase5/logs/` (not committed), experiments in `build/review-phase5/exp/`.

| What | Result |
|---|---|
| `curatrix doctor` | OK, no warning (KiCad 10.0.8, FreeCAD 1.1.4, Blender 5.2.3, Pilot 0.63.1; shims first on PATH) |
| `curatrix check <repo> --stage local`, with CAD, eight repos | seven pass; robarm-freecad-pcba failed on a stale CMake cache in `build/` and passes from an empty build area (P5R-12) |
| `curatrix check robarm-manifest --stage full` | pass; CK-B2 warns: SYS-REQ-0001 has no test case (P5R-4) |
| `curatrix fixtures` | passed: 62 rows, 56 checks and the control build, 59 s |
| `curatrix cam robarm-ee canary-board` | 18 jobs, 34 files, both variants, version `canary-board/v0.0.0-28-g4078b4c-preview` |
| `curatrix cam robarm-me canary-assembly`, with Blender and with `--no-blender` | 17 files each, one variant (`all`), version `canary-assembly/v0.0.0-21-g41cf477-preview` |
| `curatrix docs full`, `docs robarm-ee`, `docs robarm-me`, `curatrix trace full` | all OK (strict) |
| Read-only `gh`: PRs, rulesets, token defaults, CI runs and logs, tags; the published Pages | see the findings |
| `~/.config`, `~/.cache`, `~/.local/share` of kicad, FreeCAD and blender, before and after | identical (94 lines each, no file added or changed) |

I looked at the board, harness and assembly documents and at the renderings myself. I did not run
`cam` from a tag or from a dirty tree: tags are the owner's, and I may not change a repo. I did not
re-run the Pilot on changed models.

## Verdict

Phase 5 did what Phase 4 lacked. There is now real content in every domain repo except one, saved
by the real tools, and it runs through the real registries and the real CI. The tooling for EE and
ME (domain models, 1:1 rules, connectors, ERC/DRC with acceptance, design output, documents, the
co-design push) exists and works on the canary. The records are honest: the decision log names
its own incidents, open points and what was not built. My own runs reproduce the claimed numbers
within a few percent, and the user configuration stayed untouched. For about twenty hours of
agent work this is a lot, and most of it holds.

Three things do not hold yet, and they are the Phase 4 theme in a new form:

1. **The new checks report, but they never fail.** Every check that Phase 5 added is a warning at
   every stage, also at the baseline. The canary is "green" with two DRC errors that nobody has
   accepted. With real content in Phase 6, a wrong pin map, an ERC error or a domain model that
   does not conform will also be green, locally and in CI (P5R-1).
2. **The canary is thin where Phase 6 is thick.** The chain stops at a preview result of a SW
   unit test; robarm-integration is empty. The ME canary is one box. The syseng model has no
   view, and no robarm document shows one (P5R-2, P5R-4, P5R-5).
3. **What the owner sees is not what was built.** The board, harness and assembly documents are
   not in the full set and not on Pages, and a docs build after `curatrix cam` still shows the
   placeholder sentences unless the build folder is deleted first (P5R-3, P5R-6).

**Can Phase 6 start? Yes, with the text part of the horizontal bar (6.1, 6.3) at once.** Before
the rest:

- before 6.2, 6.4 and 6.6 (use cases, architecture, views): P5R-2;
- before the vertical bar (6.7 onward): P5R-1, and then P5R-3 to P5R-8 in the order of the tasks
  that need them (table in P5R-8);
- any time, by the owner: the open owner actions (P5R-9). Exit criteria 3 and 6 stay open until
  then.

## Findings

### P5R-1 The checks of Phase 5 never fail — blocking-for-phase-6 (before 6.7)

Evidence:
- `curatrix/src/curatrix/checks.py`, table `BUILTIN`: CK-B8, CK-D7 to CK-D10, CK-E4, CK-F1, CK-F3,
  CK-F4a/b/c, CK-F6 to CK-F12, CK-F14 to CK-F19 and CK-F21 have the level `warning` at every stage
  they run in, the baseline included. Only CK-F20 (board library) is an error. A warning never
  changes the exit code.
- My run of `curatrix check robarm-ee --stage local` ends with `CHECK PASSED` and
  ```
  warn CK-F4b ... accepted.yaml entry 1 (CK-F4b unconnected_items: all) is a proposal, not
       accepted (commit 8c2b886527 is an agent commit (agents never accept)); it covers 2 errors
  warn CK-F9  ... proposal, not accepted
  ```
  So the acceptance rule of XD-ADR-0126 is checked and reported, but it gates nothing. CI of
  robarm-ee shows the same `warn CK-F9` and is green.
- `claude/framework/checks.md` §2a gives every one of these checks the target `error` "only after
  it ran on the canary". They all ran on the canary. No task, no decision and no item of the
  iteration 2 list promotes them.
- Exit criterion 2 says "a planted error that fails". The planted tests assert that the check
  reports a finding. That is fine for a test, but in a repo the same finding passes.

Why it matters now: Phase 6 puts a real schematic, a real assembly and real pin maps into the
repos. The first wrong net name is a line in a log that scrolls by.

Proposed action: one small PR before 6.7. Set the plain-Python checks (CK-E4, CK-F1, CK-F3,
CK-F6 to CK-F11, CK-F14, CK-F15, CK-D7, CK-B8) to `error` at local and PR, and the tool-backed
ones (CK-F4a/b/c, CK-F16, CK-F17, CK-D8, CK-D9) to `error` at local and baseline. Keep CK-F12,
CK-F19, CK-F21, CK-D10 as warnings on purpose and say so in `checks.md`. This needs the owner's
`Accepted-by:` commit for the canary's unrouted nets first (P5R-9), or robarm-ee turns red, which
is the point. At the baseline stage, make missing local output (CK-D10) an error, as the plan
review asked (P5-11).

### P5R-2 The views Phase 6 needs are not on main, and no document shows a view — blocking-for-phase-6 (before 6.2, 6.6)

Evidence:
- `curatrix/src/curatrix/views/__init__.py:38`: `IMPLEMENTED = ("interconnection",
  "decomposition")`, the same line as in the Phase 4 review (P4-2). The kinds `usecases`,
  `general`, `actionflow` and `statetransition` exist only in PR xdmod#25, which is open since
  2026-11-15, 47 PRs behind main and touches `model.py` and `views/`, which Phase 5 changed. The
  kinds `context`, `allocation` and `variants` exist nowhere.
- The iteration 2 list has #25 as G5, "not part of Phase 5". But 6.1 (system context), 6.2 (use
  cases), 6.5 (variants) and 6.6 ("generated views embedded in the syseng docs") need these kinds.
- robarm-syseng: `model/views.sysml` is an empty package and `views/` holds only a README. CK-D3
  ("views match the model") passes there on zero views. robarm-me has no view (5.15 asked for
  block diagrams of boards and assemblies; iteration 2 list C6). robarm-ee has one,
  `views/canaryBoard.drawio.svg`, and no document includes it: `grep` for `canaryBoard` or
  `drawio` in `robarm-ee/docs` finds nothing, and the built `ee-design` page does not contain it.
  So "view in a document" has never run in a robarm repo.

Proposed action: split the view kinds out of #25 into their own PR on today's main (the
self-model and its 17 diagrams can follow), add one view to the syseng canary and embed it in
`se-arch`, embed the EE view in `ee-design` or the board document, and add an ME view. Decide
whether `context`, `allocation` and `variants` map onto `general` and `interconnection` (as the
Phase 4 response proposed) and write that into `views.md`.

### P5R-3 Board, harness and assembly documents are missing from the full set and from Pages — should-fix (before 6.9)

Evidence:
- `robarm-manifest/docs/documents.yaml` lists `ee-design`, `me-design` and `board-library`, but
  not `pcba-canary-board`, `harness-canary-cable` or `asm-canary-assembly`. After `curatrix docs
  full`, `build/full/docs/deploy/html/` has 15 documents and none of the three.
- `https://tiacsys.github.io/robarm-manifest/latest/pcba-canary-board/index.html` and
  `.../asm-canary-assembly/index.html` answer 404.
- `curatrix new pcba` and `new asm` add the document to the registry of the domain repo only.
  Nothing checks that the full set holds every document of the domain repos.

So the documents the owner asked for (EE-4, ME-4) exist only in a local domain build. The harness
document links to the board document; in the full set that link has no target.

Proposed action: add the three documents to the manifest registry; let `new pcba` / `new asm` print
the registry line for the manifest (or open the sibling change); add a check at the `full` stage
that every document in a domain repo's registry is in the full-set registry.

### P5R-4 The canary chain stops before system verification — should-fix (before 6.12)

Evidence:
- robarm-integration has no canary content: both documents are Phase 4 skeletons, `ids.yaml` has
  no number, `hil/` and `tests/` hold a README, and the `evidence` branch holds only its README.
- `curatrix check robarm-manifest --stage full`: `warn CK-B2 SYS-REQ-0001: no (valid) test case
  verifies it (R2)`. `ok CK-B6 stale evidence` passes on zero records.
- `curatrix trace full`: SYS-REQ-0001 is "verified by SW-TC-0001", latest result "passed
  (preview, not evidence)". The trace report counts the test of the refining SW requirement;
  CK-B2 does not. The two disagree on what "verified" means.
- Task 5.3 asked for "one test case → one HIL result". The decision log says why there is none
  (agents have no hardware) and that a `sim` record was only validated as a dry run.

So `evidence record`, `evidence read`, TR needs from real records, CK-B6 and a system test case
with a HIL setup have still run only in unit tests. 6.12 depends on all of them.

Proposed action: add one `INT-TC` that verifies SYS-REQ-0001 with a `hil/canary` setup to
robarm-integration, and record one run from `main` (a `sim` record by an agent is enough to prove
the path; the HIL record stays the owner's). Settle the CK-B2 / trace report difference in
`trace-model.md`.

### P5R-5 The ME canary is one box; several ME rules have nothing to check — should-fix (before 6.10)

Evidence: `robarm-me/generated/freecad/...`: the top document links the skeleton and one part,
and the part is one `Part::Box`. `cam.json`: `"variants": ["all"]`, `"moves": {"CanaryPart":
[0, 0, 0]}`. The assembly document says "Variants: none", "Sub-assemblies: none".

| Rule or output | On the canary |
|---|---|
| CK-F17 collisions | one child, so no pair is ever compared |
| CK-F18 space budget | always a skip: "no board model in any assembly" |
| CK-F21 newer board version | no link into the board library (the library is empty) |
| ME variants by `Configs`, `cam` per variant | no variant |
| exploded view | one part that does not move: the picture equals the iso view |
| sub-assembly chapters, fasteners with a standard name, the board line in the BOM | fixtures only |
| drawing | four views, no dimensions (iteration 2 list C8) |

The planted tests for CK-F17 and CK-F18 feed a canned result into the check
(`monkeypatch.setattr(mechecks, "run", ...)`); only `test_me_checks_freecad` runs FreeCAD.

This is P4-1 at a smaller scale: the rules pass on almost nothing. The EE canary is better (two
variants, a connector with a pin map, a harness, an unrouted board).

Proposed action: before 6.10 grow the canary assembly by a second printed part with a joint, one
library fastener, one part with `Configs` (so there are two variants), and, once the owner tagged
the canary board, the board from the library on its seat.

### P5R-6 A docs build after `curatrix cam` still shows the placeholders — should-fix (before the owner's review)

Evidence: after my `cam` runs, `curatrix docs robarm-ee` and `docs robarm-me` both said OK, but
`pcba-canary-board/index.html` and `asm-canary-assembly/index.html` kept their time stamps of
19:15 and 19:16 and still read "Made locally with KiCad (curatrix cam) for the current commit;
not part of this build" for renderings, schematic and findings. After I moved `build/robarm-ee/docs`
and `build/robarm-me/docs` aside, the same commands showed the renderings, the schematic and
"DRC: 2 findings" (logs `docs-ee.log`, `docs-ee-fresh.log`).

Cause: Sphinx re-reads a page only when a source file changed. The `xd-pcba-*` and `xd-asm-*`
directives read the cam output, which is outside the source tree, and do not declare it. The
decision log knows a cousin of this ("incremental builds miss directive code changes"), but this
case is the normal path: the how-to `review-a-domain-pr.rst` step 3 is exactly `cam`, then `docs`.

Proposed action: the directives call `env.note_dependency()` on `cam.json` (or mark the page as
always outdated). Until then, the how-to says to delete `build/<area>/docs` first.

### P5R-7 The co-design chain has no check — should-fix (before 6.9 and 6.10)

The space budget goes: syseng `SYS-IF` → copies in the ME seat port → FreeCAD `Params` → KiCad
`Edge.Cuts` by the StepUp push. Only the third step is checked (CK-F3).

Evidence:
- `robarm-me/model/canary.sysml` restates seven budget values (`:>> hole2X = 24 [mm];`).
  `model.conformance()` (CK-E4) compares ports, not values; `meparams.py` uses the "copy" mark
  only to leave the values out of the ten-parameter count. A change of the budget in syseng alone
  leaves ME green.
- No code in `curatrix/src` reads `Edge.Cuts` or footprint positions (`grep "Edge.Cuts\|outline"`
  finds nothing). CK-F18 is `_me(ctx, r, "CK-F18")`, a skip. `checks.md` still says "Co-design
  checks get their IDs from task 5.28".
- `claude/notes/codesign-spike.md` lists the three checks under "Check idea"; none was built
  (iteration 2 list A5).
- Today the values agree; I compared by hand: outline 30 × 20 mm, holes at (4, 4) and (24, 16),
  J1 pin 1 at (7, 12) in the board frame.
- The push itself is a `curatrix run` line in the how-to with a script from
  `xdmod/templates/codesign/`; StepUp is not in `tools.yaml` and has no LICENSE file.

Proposed action: build checks 1 and 2 of the spike note (plain Python, they run in CI): ME copies
equal the budget; KiCad outline, holes and connector positions equal the budget. Leave check 3
(STEP inside the box) and a `curatrix` command for the push to iteration 2.

### P5R-8 The iteration 2 list: items that Phase 6 needs, and items that are missing — should-fix (exit criterion 6)

Needed before or inside Phase 6, so not iteration 2:

| Item on the list | Needed by | Why |
|---|---|---|
| G5 view kinds of xdmod#25 | 6.1, 6.2, 6.6 | P5R-2 |
| A4 CK-F2 devicetree vs the EE board model | 6.11 | the task says "devicetree overlay checked against the model"; D101 puts CK-F2 into PR CI. Also open from 5.15: robarm-sw has no EE upstream in its registry |
| B7 `proto/` projects 1:1 with prototype blocks | 6.8 | 6.8 models the prototype wiring; today a `proto/` project is in no 1:1 rule |
| A5 CK-F18, at least its plain-Python parts | 6.9, 6.10 | P5R-7 |
| E11 `base_url` of robarm-manifest | 6.14 | the full-stage base for CK-G1/G2 needs the Pages URL |
| E6 CK-G2 against the last baseline | 7.1 | it is the suspect-link gate of the change scenario; it must be tried when 6.14 makes the first baseline |

Missing from the list (or from any plan):

- the promotion of the Phase 5 warnings (P5R-1);
- the board, harness and assembly documents in the full set (P5R-3);
- the canary's system test case and evidence record (P5R-4), and growing the ME canary (P5R-5);
- the report pages of the manifest: `robarm-manifest/docs/robarm/trace-report.rst`,
  `coverage-matrix.rst` and `change-report.rst` still say "It is not built yet", and the
  directives `coverage-matrix`, `config-page`, `sysml-element` are stubs
  (`sphinx/xdmod_sphinx/__init__.py:389-391`). `curatrix trace` writes a file under `build/`, not a
  page. 6.13 ("consistency report") needs at least the trace report as a page;
- the agent material that was not finished (P5R-10);
- leftovers of the Phase 4 response (table below): `doctor` warning for a dirty or off-pin main
  checkout, the inline Python of the bump bot, the fast inner loop in the repo `CLAUDE.md`;
- a tag ruleset (it is in the owner actions, section D, but not on the list).

Stale on the list: "Not on this list" says xdmod#64 is not merged; it is. Item F1 quotes 57 MB and
59 packages for the syseng export; fine, but it is the cheapest speed-up and has no task.

### P5R-9 Nothing of the owner's list is done yet; one rule about decisions is unclear — should-fix

Verified today through the API and git:
- Org and all eight repos: `default_workflow_permissions: write`,
  `can_approve_pull_request_reviews: true`. Every ruleset still has the Admin bypass
  (`RepositoryRole` 5). `full-set` on robarm-manifest has no `integration_id`. No repo has a tag
  ruleset and no repo has a tag.
- Five ADRs are `proposed` (0134, 0139, 0146, 0147, 0148); the tooling built on them is merged.
- `accepted.yaml` of the canary board is a proposal; there is no HIL result.

So exit criterion 3 ("from a tag") and 6 cannot close, and P4-7, P4-10 and P4-14 are open. The
whole phase (about 120 PRs in eight repos) was merged under D140 by an agent with the owner's
login and the Admin bypass in place. Every PR I sampled (17) has an agent review with a check
table, and the EE and ME reviews name the local CAD run, so the process was followed. But the
gate is still policy only.

One point for the joint review: xdmod#44 set XD-ADR-0126 to 0144 to `accepted` in an agent
commit. They record the owner's answers from `phase5-expectations.md`, but the same PR also holds
decisions the writing agent took alone (the `connects` link, SW needs that `conforms` to EE needs,
the letter suffix of check IDs). Later the review of #59 moved XD-ADR-0134 back to `proposed`
with the reason "agents only propose". Both cannot be right.

Proposed action: the owner works through `phase5-owner-actions.md` A to D; confirms 0126 to 0144
in one commit or names the ones to reopen; `workflow.md` gets one line: an agent writes
`decision_status: proposed`, only a human commit sets `accepted`.

### P5R-10 Agent material is not complete for the EE and ME work of Phase 6 — should-fix (before 6.4 and 6.9)

Evidence:
- `claude/skills/kicad-authoring/SKILL.md` is still titled "KiCad authoring (placeholder)", with a
  section "To be added after the spike" (jobset, variants, ERC/DRC, `Port` fields, CAM). It still
  lists `Realizes` / `Conforms` as project fields "until 5.14". Tasks 5.12 and 5.17 to 5.22 are
  done; the skill was not updated. The FreeCAD skill is mostly updated but is also titled
  "placeholder", points to `robarm-me/parts/canary-part.FCStd` (moved to
  `assemblies/canary-assembly/parts/`) and has a "To be added" list.
- `robarm-ee/claude/CLAUDE.md` does not name `curatrix new pcba`, the connectors file,
  `accepted.yaml`, `cam`, variants or the co-design push, and still says "EE and SW never link to
  each other", which XD-ADR changed (SW reads the board pin maps from EE).
- `robarm-syseng/claude/CLAUDE.md` is unchanged since Phase 4 (2026-11-15). The pitfalls found on
  the canary are not in it: a usage named like a stub attribute (`unit`) loses its `satisfies`
  link without an error; no fast loop (`--only CK-E1,CK-D2`, promised in the Phase 4 response).
- `robarm-syseng/model/product.sysml` and `configs.sysml` carry comments about two workarounds
  ("the Pilot reads the model files in name order", "write `public package`"). `gen.py:84` now
  loads a repo's files as one set (`one_set=True`), and `top_packages` was fixed in 5.15. The
  comments now teach Phase 6 authors rules that no longer hold. The `dependency` to `CanaryUnit`
  could move back into `configs.sysml`.
- There is no skill for 6.4 to 6.6 (architecture in SysML, PLEML variants, views).
- `claude/notes/phase5-demos.md` has a script for block A only; blocks B to E say "To be
  written", F to H are missing. The owner's review "per block with a demo script" (P5-14) has
  only the how-to pages of 5.32 to go by.

Proposed action: finish the two CAD skills from the spike notes and the decision log before 6.9;
update the three repo `CLAUDE.md` files; clean the stale comments in syseng; write the modelling
skill when 6.4 starts; either write the demo scripts or say in the plan that the how-to pages
replace them.

### P5R-11 The EE version text on the board is cut off — note

Evidence: `render-top-default.png` and `render-3d-default.png` of my `cam` run. The silkscreen
text `${XD_VERSION}` is longer than the 30 mm board: it starts left of the board edge, runs
through mounting hole 1 and ends in "-prev". The 3D rendering also crops the board. The schematic
frame shows the full version ("Version canary-board/v0.0.0-28-g4078b4c-preview"), and the board
document prints it as text. The ME renderings and the drawing carry a red "PREVIEW".

For exit criterion 3 this means: the preview marking is visible in the EE output, but not on the
board itself. CK-F11 checks that the variable is used, not that the text fits. A tag
(`canary-board/v0.1.0`) is short enough. Proposed action: a smaller text or two lines on the
canary; a warning in `cam` when the silkscreen text leaves the outline; fit the 3D camera to the
board. The EE renderings show bare boards because the KiCad 3D models are not in the workspace
(iteration 2 list B8); for the joint board in 6.9 that item should move forward too.

### P5R-12 Workspace hygiene — note

- `curatrix check robarm-freecad-pcba` failed in my first run: `build/robarm-freecad-pcba/docs`
  held a CMake cache made from another source folder (`build/board-library/skeleton/docs`). From
  an empty folder it passes. The owner decided that `build/` is emptied before his review; it is
  not (about 125 entries, 76 of them `wt-*` areas of removed sets). `curatrix docs` could
  detect the changed source folder and start clean.
- `.worktrees/build/bl-checks/` holds five log files; it is not a worktree set.
- `robarm-ee/pcba/canary-board/canary-board.kicad_prl` sits in the main checkout (ignored by git,
  written at 17:36). The ERC, DRC, netlist and BOM checks run `kicad-cli` on the project folder
  in place (the folder's time stamp moved during my check); only `cam` works on a copy. Nothing
  tracked changed, so this is harmless today.
- `plan.md`: no task of Phase 5 is ticked, although Phase 4 is. A reader cannot see from the plan
  that 5.2, 5.8, 5.10, 5.15, 5.16, 5.17 and 5.25 are only partly done (table below).
- CI: when the Pages fetch fails, `curatrix ci base` ends with a Python traceback (HTTP 503 in
  robarm-ee run 44046103789) and CK-G1 is skipped without a word in the summary. By design it
  never fails a PR; a one-line message would do. CK-G1 did run in the other PR logs I read
  ("base: 3 needs.json from .../latest/").
- CK-E2 gives a false warning for a tolerance in percent ("5 V ± 5 %" with min 4.75, max 5.25).
  The five sentences of P4-8 pass now, and a wrong value or a wrong unit is found (`exp-ck-e2.log`).

### Decisions the agents took on their own

| Decision | Holds? |
|---|---|
| `expect:` must equal the enabled checks exactly (5.1) | Yes. Stricter than asked, and right |
| CK-A4 / CK-A5 removed, the schema enforces them (5.2) | Yes |
| Every new check starts as a warning (5.14) | Yes as a start; not any more (P5R-1) |
| CK-H4 knows an agent commit by "Claude Code" or anthropic.com in the message (5.7) | Weak, and known; fine until agents have their own identity |
| The model emits `EE-PCBA` / `ME-ASM`, the CAD file only refers to it (5.15) | Yes; one generator per need |
| Variants named by the domain side, table computed (5.16) | Yes; follows the trace rule. The table is only in a check log, the board document shows "—" for the Zephyr variant |
| Acceptor = newest commit that wrote a line of the entry (5.19) | Yes; fails closed |
| Version in title-block comment 2, `Rev` empty (5.20) | Yes; the Gerber header shows `rev?`, acceptable |
| The canary cable realizes the whole canary unit (5.22) | Marked as a shortcut in the model; do not copy it for the joint |
| Skeleton document per assembly, `<usage>_<attribute>` aliases (5.24, XD-ADR-0146) | Yes; it came from a real FreeCAD limit |
| Budget values are `default` values; ME restates them; copies do not count toward ten parameters (5.28) | The count rule is reasonable. The copies need a check (P5R-7) |
| The board conforms to its budget by a dependency, not a port (5.28) | Yes |
| The board library sits at the top level, not under `libs/` (5.29) | Yes, for the reason given |
| Own z-buffer renderer; Blender optional and not pinned (5.30) | Yes. Both outputs are readable; user paths stayed untouched |
| No caching of the Pilot (5.31) | Yes; my numbers agree |
| CK-F2 moved to iteration 2 (5.10) | No: 6.11 needs it (P5R-8) |
| Admin action 3 "not recommended" (5.9) | Yes, while the bump bot uses the Actions token |
| ADRs 0126 to 0144 set to `accepted` by an agent (5.14) | For the owner to confirm (P5R-9) |

## Exit criteria

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Canary chain green locally with CAD and in CI without | **partly met** | All eight local checks pass (one after an empty build folder). CI on `main` is green in all eight repos. But green includes two unaccepted DRC errors as warnings (P5R-1), and the chain ends at a preview result: SYS-REQ-0001 has no test case, robarm-integration is empty (P5R-4) |
| 2 | Every rule has a planted error that fails | **partly met** | `curatrix fixtures` passed here: 56 checks plus control. Not built: CK-F2, CK-F13. CK-F18's test asserts a skip. CK-F5a/b/c have no planted error. "Fails" means "is reported" for the warnings (P5R-1) |
| 3 | `curatrix cam` for the board (both variants) and the assembly, from a tag and from a dirty tree, preview marking visible | **partly met** | Ran from the clean, untagged tree: board `default` and `alt` (BOM, position file and 3D rendering differ as they should), assembly with and without Blender; all marked as preview. No tag exists (owner). The dirty case is covered by `test_cam.py::test_version` only. The marking on the board silkscreen is cut off (P5R-11) |
| 4 | One co-design change through three repos on one branch name | **met** | robarm-syseng#10, robarm-me#12, robarm-ee#15, all `feat/codesign`, merged 15:47 to 15:51 UTC. Hole 2 moved from x = 26 to 24 mm in the budget (`d5ca703`), the seat (`45a8bdc`) and the board (`4078b4c`: circle centre 114 → 112). No check guards the chain (P5R-7) |
| 5 | Author loop measured, numbers in this review | **met** | `claude/notes/author-loop.md`; my runs agree (below) |
| 6 | Iteration 2 list agreed by the owner | **not met** | Draft. It needs the changes of P5R-8 first |

## Tasks 5.1 to 5.32

| Task | Status | Open part |
|---|---|---|
| 5.1 check honesty | done | verified: missing `checks.yaml` exits 1; a skipped CK-G2 fails at baseline |
| 5.2 one trace model | mostly | `BUILTIN` is still a tuple list with `globals()` dispatch |
| 5.3 canary C0, fixtures | mostly | no HIL result, nothing in robarm-integration (P5R-4) |
| 5.4 CK-E2 | done | |
| 5.5 tool pins | done | |
| 5.6 no robarm names | done | only text and xdmod's own CI name the example project |
| 5.7 CI | done | CK-G2 has no baseline yet; the downstream job is not required |
| 5.8 agent material | partly | P5R-10 |
| 5.9 admin actions | prepared | owner (P5R-9) |
| 5.10 SW and INT tooling | mostly | CK-F2 not built |
| 5.11 to 5.13 spikes | done | clear verdicts and fallbacks in the notes |
| 5.14 decisions | done | five ADRs proposed; who accepts (P5R-9) |
| 5.15 domain models | mostly | no ME view, no `eeSw` view, robarm-sw has no EE upstream |
| 5.16 variants | mostly | CK-F13 not built; the Zephyr mapping has nothing to compare; `alt` is used by no configuration |
| 5.17 KiCad projects | mostly | `proto/` not in the 1:1 rule |
| 5.18 to 5.22 EE | done | as warnings (P5R-1); documents not in the full set (P5R-3) |
| 5.23, 5.24 ME assemblies, parameters | done | on a one-part assembly (P5R-5) |
| 5.25 ME checks | partly | CK-F18 is a skip; CK-F17 has no pair on the canary |
| 5.26, 5.27 ME output, document | done | drawing without dimensions and without TechDraw; one variant |
| 5.28 co-design | done | no checks, no command (P5R-7) |
| 5.29 board library | skeleton | the library is empty: no tagged board |
| 5.30 ME renderings | done | |
| 5.31 author loop | done | |
| 5.32 manual, records, list, review | done | the list is a draft; this review |

## Phase 4 findings

| # | Finding | Status on main | Evidence |
|---|---|---|---|
| P4-1 | no real content | **resolved** in SYS, EE, ME, SW; **open** for integration | P5R-4, P5R-5 |
| P4-2 | missing tooling | **partly**: CK-F1, F3, F4, SW-IMPL / SW-TC, test results in docs and `curatrix trace` exist. Open: view kinds, CK-F2, coverage matrix, report pages, `sysml-element` | P5R-2, P5R-8 |
| P4-3 | agent material | **mostly**: `xdmod/claude/CLAUDE.md`, `/xd-review-pr`, six checklists, three skills. Open: CAD skills | P5R-10 |
| P4-4 | checks pass without checking | **resolved** for the runner (my experiments). The theme is back as warnings | P5R-1 |
| P4-5 | CK-G1, CK-H4 never ran in CI | **resolved** for CK-G1 and CK-H4; CK-G2 waits for a baseline | CI logs of robarm-me, robarm-sw, xdmod |
| P4-6 | no downstream check on upstream PRs | **resolved** as a reporting job (`downstream / check` on xdmod and syseng PRs), not required | xdmod ruleset: required are `tests`, `check / check` |
| P4-7 | `full-set` weaker than its name | **partly**: `stage: full` is in `check.yml`; `integration_id` is not set | ruleset 27289841 |
| P4-8 | CK-E2 false errors, untested checks | **resolved** | `exp-ck-e2.log` |
| P4-9 | trace model in three places | **resolved**: `tracemodel.py` reads the toml; `model.LINK_BY_KINDS` is a new table, guarded by `test_model.py:116` | |
| P4-10 | token defaults | **partly**: `permissions:` in the manifest's `check.yml`; org default still `write` | API |
| P4-11 | slow author loop | **resolved** by measurement; not done: fast inner loop in `CLAUDE.md`, reuse of `gen model` in `check` | author-loop note |
| P4-12 | exact pins for rolling tools | **resolved** | `tools.yaml`; CK-D5 ok in syseng |
| P4-13 | CAD path on hand-made fixtures | **resolved** for KiCad (files saved by KiCad 10, CK-D8 and CK-D9 on every board); **partly** for FreeCAD (real files, but no standing comparison of the plain-Python reader with FreeCAD) | |
| P4-14 | checks advisory, D140 open-ended | **partly**: D140 extended on purpose, PRs are smaller, sets are used. Open: Admin bypass, `doctor` warning for a dirty or off-pin checkout | P5R-9 |
| P4-15 | two ID systems | **resolved** | launch `CLAUDE.md`, D-number note |
| P4-16 | robarm hardcoded | **resolved** | `grep` in `curatrix/src` |
| P4-17 | cut or simplify | **partly**: CK-A4/A5 dropped, provenance fixed. Not done: `checks.py` dataclasses, bump bot Python into `scripts/` (`bump.yml:135, 235`) | |

The findings of the Phase 5 plan review: P5-1 to P5-3, P5-5 to P5-10, P5-13, P5-15 and P5-16 are
taken up as proposed (the KiCad spike corrected P5-3: a job can name a variant). P5-4 is built,
but as warnings (P5R-1). P5-11: the review re-run is in `/xd-review-pr` and was done; the
baseline rule is not. P5-12: `proto/` and the tag rule are open. P5-14: demo scripts for block A
only.

## Author loop (exit criterion 5)

From `claude/notes/author-loop.md` (median of three, warm), next to one run of mine on the same
machine (laptop, clock capped at 1.7 GHz, nothing else running):

| Command | Note (s) | Mine (s) |
|---|---|---|
| `check robarm-syseng --stage local` | 40.0 | 42 |
| `check robarm-ee --stage local` (with CAD) | 28.4 | 28 |
| `check robarm-me --stage local` (with CAD) | 25.0 | 25 |
| `check robarm-sw --stage local` | 25.5 | 25 |
| `check robarm-integration --stage local` | not in the note | 19 |
| `check robarm-manifest --stage local` / `--stage full` | 76.4 / not in the note | 77 / 72 |
| `check xdmod --stage local` (with both test sets) | not in the note | 344 |
| `cam robarm-ee canary-board` | 12.5 | 12 |
| `cam robarm-me canary-assembly`, Blender / `--no-blender` | 36.0 / 5.6 | 37 / 6 |
| `docs full` | 71.0 | 72 |
| `curatrix fixtures` | 64.8 (fixture note) | 59 |

Role loops from the note: syseng 80 s, EE 52 s, ME 71 s (41 s without Blender), SW 26 s, full set
147 s. The robarm-ee check takes about a tenth of the plan's five-minute limit, so "no caching" is
right. Where the time goes, in my runs as in the note: the Pilot (CK-E1: 35 s in syseng, 14 s in
EE, 15 s in ME) and the serial Sphinx runs (CK-A6: 71 s for the full set). Two cheap steps are on
record and worth a task when the model grows: export only the packages curatrix reads, and let
zdocs run Sphinx in parallel. Missing in the note: the xdmod check itself (almost six minutes,
of which the tool tests take 227 s), which every xdmod PR and every review pays.

## Fixture run (exit criterion 2)

- The recorded run (`claude/notes/phase5-fixture-run.md`): 2026-11-17 19:23 UTC at xdmod
  `83578e4`, 62 rows, 56 checks plus the control build, all passed, 84 tests in 64.8 s.
- My run at xdmod `91e735c` (xdmod#64 changed `setup.py` since): 2026-11-17 20:46 UTC, the same
  62 rows and 57 names, all passed, 59 s, record `build/fixtures/planted.json`. Tools: KiCad
  10.0.8, FreeCAD 1.1.4, Pilot 0.63.1, JDK 21.0.13+9, elkjs 0.12.1, drawio viewer 32.6.1, Firefox
  160.0. The user configuration did not change.
- `test_every_check_has_a_planted_error` ties the list to `BUILTIN`, so a new check cannot be
  added without one. The plain-Python part runs in xdmod CI as `tests` (XD-T1), green on main.
- Limits of the claim, as the note itself says and as I confirm: CK-A2 rides on CK-A6; CK-F2 and
  CK-F13 are not built; CK-F5a/b/c are repo commands without a planted error; CK-F18 asserts a
  skip. I add: several ME tests feed a canned FreeCAD result into the check, so for CK-F17 and
  CK-F18 the tool is not in the loop; and for the warning-level checks the planted error is
  reported, not failed (P5R-1).

## Done well

- **The canary through real tools.** `canary-board.kicad_sch` is saved by eeschema 10.0, the
  FreeCAD files by FreeCAD 1.1; both go through plain-Python readers in CI and through the tools
  locally, and the readers are compared with KiCad on every check run (CK-D8, CK-D9).
- **The trace rule is kept.** Every new link is held by the concrete side: board and assembly
  specialize the system block, ports conform to the `SYS-IF`, domain variants name the
  configuration and usage they serve, the harness names its ports, CAD files only refer to model
  IDs. Backlinks and the variant table are computed.
- **Isolation of the user configuration.** Shims for 14 tool names, the Blender wrapper with
  every user path under `.xdmod/`, `doctor` checks the PATH order. Three incidents happened early
  in the phase; they are written down with times and led to the rule. My listings before and
  after about 25 minutes of KiCad, FreeCAD and Blender runs are identical.
- **CI versus local is split cleanly.** Everything plain Python runs in CI from committed
  generated files; tool-backed checks are named in the review comment with the tool versions; the
  documents say in a fixed sentence what is missing in a CI build.
- **The check runner is honest now.** A missing `checks.yaml`, an empty plan, a lost section and
  a skipped error check at the baseline all fail, and each run prints which checks are off and why.
- **The spikes paid off.** Each has a verdict table with fallbacks, and three plan assumptions
  were corrected by them (jobs can name a variant, the skeleton document, no TechDraw page
  offscreen). StepUp was tried sandboxed and its licence gap is recorded.
- **Acceptance fails closed.** An entry counts only with `Accepted-by:`, without an agent trailer
  and in a commit that changes nothing else; a later agent edit turns it back into a proposal.
- **The documents are useful.** The board document (variants, stackup, rules, connector pin
  table, BOM with variant columns) and the assembly document (parameters with model and CAD value
  side by side, interfaces, mass) read well and come from the files, not from hand-written text.
- **The records.** `phase5-decisions.md` says for each task what was decided, why, how to undo
  it and what is open, and it reports its own mistakes (red main for 30 minutes, a lost stacked
  PR, three ID collisions). This review could check claims instead of searching for them.
