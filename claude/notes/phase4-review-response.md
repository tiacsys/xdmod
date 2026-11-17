# Response to the Phase 4 review (Fable, 2026-11-15)

> Moved from `build/review-phase4/` into the repo on 2026-11-17, before `build/` was emptied. The logs and
> experiments it refers to under `build/review-phase4/` are in the owner's local archive of `build/`
> (2026-11-17), not in the repo.

Author: coordinator agent (Claude), 2026-11-15. Review: `claude/notes/phase4-review.md`.

## Summary

I agree with the verdict. Phase 4 built and tested the pipeline, but only with empty content, so a
green check today proves very little. I spot-checked several claims, and they hold: `graph.py`
`LINK_TYPES` lacks `revises` and `supersedes` (P4-9), and `robarm-manifest/.github/workflows/check.yml`
has no `permissions:` block (P4-10).

I accept P4-1 to P4-14 in substance. Two are partial (P4-11, P4-17), and I disagree with one
point of P4-17. My proposal is a short **Phase 5.0, "make the checks bite"**, before any real
content. Its tasks are listed at the end. Several findings need your decision; they are marked
**[owner]**.

One finding is about me. P4-14 notes that the main xdmod checkout was on a branch with
uncommitted changes. That was my diagram work (PR xdmod#25). I worked in the main checkout and not
in a worktree set, against our own rule (XD-ADR-0114). It did no harm, because the reviewer read
pinned commits, but it is exactly the mix-up the rule prevents. From now on I use
`curatrix work start` for every change.

## Finding by finding

| # | Assessment | What I propose | When |
|---|---|---|---|
| P4-1 empty pipeline | Agree. This is the most important point. | A permanent **canary chain** in the robarm repos: one stakeholder need, one SYS-REQ, one SYS-EL, a KiCad sheet and a FreeCAD part saved by the real tools, one SW-DD with code, one test case, one HIL result. It runs through the real registries and real CI. Add a **planted-error fixture workspace** in xdmod CI, where each rule must fail. The canary stays after Phase 5 and is marked as such. **[owner]** canary in robarm repos (my preference: it doubles as the first joint) or in a separate fixture workspace. | 5.0 |
| P4-2 missing tooling | Agree. PR xdmod#25 already adds `usecases` and the SysML standard views `general`, `actionflow` and `statetransition`. Still missing: `context`, `allocation` and `variants` (these can map onto `general` and `interconnection` with filters), CK-F1 to F4, SW-IMPL and SW-TC extraction, test results in docs, coverage and report pages. | Add tooling tasks to Phase 5, each next to the content task that needs it. **[owner]** what to cut from iteration 1. My proposal: keep CK-F2 (devicetree vs model), SW-IMPL/SW-TC extraction, test results in docs and a minimal trace report; defer CK-F3, TechDraw export, `config-page` and the coverage matrix per configuration to iteration 2. | 5.0 / alongside |
| P4-3 agent material | Agree. The launch `CLAUDE.md` names a `/review-pr` command that does not exist. That is worse than having none. | Before 5.1: `xdmod/claude/CLAUDE.md`, a `/review-pr` command with requirement, model and code checklists, and the skills for 5.1–5.3 (stakeholders and needs, EARS requirements, issuing IDs). Write other skills when their step comes. | 5.0 |
| P4-4 checks pass without checking | Agree with all four points. | A missing `checks.yaml` or an empty plan is an error. `check` prints the checks that are off and why. A skipped `error` check fails at the `baseline` stage. Each repo states the checks it expects (`expect:`). Silent fallbacks become errors. Fix CK-H5 for the manifest repo. | 5.0 |
| P4-5 CK-G1, CK-H4 never run in CI | Agree. | The workflow downloads `latest/` needs.json from Pages as `--base`, and the report goes to the job summary. CK-H4 uses the PR base SHA from the event and checks only agent commits (author or committer is the agent identity, or a provenance line in the body). | 5.0 |
| P4-6 no downstream check on upstream PRs | Agree. The spec says so and the code does not. | A second job on xdmod and robarm-syseng PRs: `curatrix check robarm-manifest --stage full --no-cad` with the PR branch. It reports at first, and becomes required once it is stable. | 5.0 |
| P4-7 full-set weaker than its name | Agree. | `stage: full` in the manifest's `check.yml`. **[owner]** add `integration_id` 15368 to the manifest ruleset (admin action). | 5.0 |
| P4-8 CK-E2 false errors, untested checks | Agree. I reproduced the logic from the code. | Numeric comparison, ranges, unit names and thousands separators. CK-E2 is a warning until it has run on real requirements. Table-driven tests for `c_ears`, `c_diff`, `c_trailers`, `c_pins` and `c_hygiene_build`. | 5.0 |
| P4-9 trace model in three places | Agree. PR xdmod#25 adds the same kind of guard for the new SysML self-model (a test compares it with `needs_config.toml`), but `graph.py` and `ids.py` are still separate copies. | `graph.py` and `ids.py` read link types, requirement types and kinds from `needs_config.toml` at run time. One test asserts that no hard-coded list is left. Drop CK-A4 and CK-A5 where the schema already enforces them. | 5.0 |
| P4-10 token defaults | Agree. | Add `permissions:` to the manifest's `check.yml` (a normal PR). **[owner]** set org default workflow permissions to read and switch off PR approval by Actions (admin action, D123). | 5.0 |
| P4-11 slow author loop | Partly agree. The numbers are right. But a Pilot cache keyed on input hashes adds a correctness risk. | First measure with real content (about 30 requirements and 20 elements, from the canary and 5.1–5.3). Until then, give agents the fast inner loop (`--only CK-E1,CK-D2`) in the repo's `CLAUDE.md`, and let `check` reuse a `gen model` result from the same run. Add caching only if the measurement asks for it. | measure in 5.3 |
| P4-12 exact pins for rolling tools | Agree. | Exact pins only for tools that shape committed output (Pilot, Firefox and drawio viewer, elkjs, KiCad, FreeCAD, Doxygen); minimum versions for git, cmake, ninja, node, npm and curl. Graphviz renders only HTML, so CI and local may differ, but I will note it. Commit syseng `provenance.json`. | 5.0 |
| P4-13 CAD path on hand-made fixtures | Agree. | The canary uses files saved by KiCad 10 and FreeCAD 1.1. A local-only test compares the plain-Python readers with `kicad-cli` netlist output and a FreeCAD property dump. | 5.0 with the canary |
| P4-14 checks advisory, D140 open-ended | Agree. | A new decision need: D140 ends with Phase 4, so from Phase 5 only the owner merges. **[owner]** confirm, or extend it on purpose. Phase 5 PRs stay small: one SYSMOD step or one tool feature each. I use worktree sets myself (see above). `doctor` warns when a framework repo in the main checkout is dirty or off its pin. | now |
| P4-15 two ID systems for decisions | Agree. | Keep D-numbers as short names in code and agent files (they are in `legacy_id`), say so in the launch `CLAUDE.md` with a lookup command, and fix the stale note in `add-a-test.rst`. New decisions get only XD-ADR IDs. | 5.0 (small) |
| P4-16 framework hardcodes robarm | Agree. | Use `ws.framework_repos` and the manifest URL from `west`, with no robarm names in xdmod. | 5.0 (small) |
| P4-17 cut or simplify | Partly agree. Agreed: drop CK-A4/A5 (via P4-9), turn the `checks.py` table into dataclasses, move the inline Python of the bump bot into `scripts/`, and state honestly that the ulimit fallback does not protect the heavy tools. Not agreed: (a) **remove provenance**. CK-D5 is how a reviewer sees which Pilot or viewer made a committed file, and the views just showed that renderer versions matter. I would fix #23 and simplify it, not remove it. (b) **remove worktree sets**. Phase 5 will run parallel agents, and P4-14 shows what happens without them. (c) **switch off sphinx-llm**: it costs little, and agents are first-class readers. I would keep it, fix #20, and test it in 5.x by letting a reviewer agent work from `llms.txt`. | Simplifications in 5.0; the three keeps are **[owner]** decisions. | 5.0 |

## Proposed Phase 5.0 "make the checks bite" (for plan.md, after your decisions)

1. 5.0a Canary chain through all repos with real-tool CAD files, and the planted-error fixture workspace in xdmod CI (P4-1, P4-13)
2. 5.0b Check runner honesty: missing config or empty plan fails, `expect:` list, skipped `error` fails at baseline, no silent fallbacks, CK-H5 on (P4-4)
3. 5.0c One source for the trace model in curatrix (`needs_config.toml`), drop the duplicate rules (P4-9, P4-17)
4. 5.0d CI: `--base` for CK-G1 from Pages, CK-H4 from the PR base, the downstream full-set job, `stage: full` and `permissions` for the manifest (P4-5, P4-6, P4-7, P4-10)
5. 5.0e CK-E2 numeric comparison and tests for the five untested checks (P4-8)
6. 5.0f Tool pins: exact only for output-shaping tools; syseng provenance (P4-12)
7. 5.0g Agent material: `xdmod/claude/CLAUDE.md`, `/review-pr` with checklists, skills for 5.1–5.3; D-number note (P4-3, P4-15)
8. 5.0h Remove robarm names from xdmod (P4-16)
9. Phase 5 tasks get their tooling next to them, and the iteration-1 cuts are written down (P4-2)

## Decisions for you [owner]

1. Canary in the robarm repos (my preference) or in a separate fixture workspace? (P4-1)
2. Iteration-1 cuts as proposed under P4-2?
3. Admin actions: `integration_id` on the manifest ruleset, org token default to read, Actions may not approve PRs (P4-7, P4-10).
4. D140 ends with Phase 4: only the owner merges from Phase 5 on (P4-14)?
5. Keep provenance, worktree sets and sphinx-llm, as argued under P4-17?

## Owner decisions (2026-11-15)

- All points of this response are agreed, including the five open decisions, with one change:
  **D140 stays active until Phase 5.0 is finished** (agents may still merge during 5.0).
- Order: first a second round of the self-model diagrams (split by the five domains SYS, EE, ME,
  SW and system-level verification INT; views across two domains; canvas between 9:16 and 16:9).
  Then wait for the owner's input before Phase 5.0 starts. The admin actions also wait for that.

## Owner decisions (2026-11-16): points the response missed

- **Rulesets bind everyone (P4-14, option B).** The Admin bypass (`RepositoryRole` 5,
  `bypass_mode: pull_request`) is removed from the rulesets of all seven repos, so a PR merges only
  with green required checks, for agents and the owner alike. In an emergency the owner switches
  the bypass back on for a moment. Added to the admin action list; it runs with the other admin
  actions after the owner's go for 5.0. A separate agent identity (option C) is deferred to
  iteration 2 or the end of D140.
- **PR size (P4-14, option B).** One SYSMOD step or one tool feature per PR, written into
  `workflow.md` and the launch `CLAUDE.md`. A new check counts only hand-written lines (generated
  files excluded, using the list `check` already knows), against the PR's base, and warns above a
  first limit of about 600 lines or 15 files. It never fails. Part of 5.0b. PR xdmod#25 stays as it
  is.
- **Stacked PRs where they make sense.** The workflows allow and encourage them. What exists:
  PR CI runs for any base branch (`on: pull_request`), and only rebase merges are allowed with
  branches deleted on merge, so GitHub retargets a child PR when its parent merges. What 5.0 adds:
  - `curatrix work start <branch> --base <parent-branch>` (today a set always starts from `main`).
  - Sibling resolution (D127): when a sibling repo has no branch of the same name, try the PR's
    base branch chain before `main` / the pin, so that a stacked layer in one repo sees the
    parent layer in another.
  - The size check and CK-H4 compare with the PR's base, so each layer is counted and checked on
    its own. CK-G1 compares with `latest/` (main) in iteration 1, so a stacked PR shows the impact of
    the whole stack; per-layer impact is iteration 2.
  - `workflow.md`: how to stack (each layer reviewed on its own by `/review-pr`, merged bottom-up,
    after a parent merges the child is rebased with `git rebase --onto main <old-parent-tip>` and
    force-pushed to its own branch, which agents may do).
