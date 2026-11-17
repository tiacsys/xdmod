# Review of the XDMOD Phase 4 work products

> Moved from `build/review-phase4/` into the repo on 2026-11-17, before `build/` was emptied. The logs and
> experiments it refers to under `build/review-phase4/` are in the owner's local archive of `build/`
> (2026-11-17), not in the repo.

Reviewer: Fable agent, 2026-11-15. Reviewed state: xdmod `e626bd4`, robarm-manifest `4afe2f3`,
robarm-syseng `21faea7`, robarm-ee `56f14ae`, robarm-me `9aea2d4`, robarm-sw `eb910fa`,
robarm-integration `7f67366` (all equal to their `main` on GitHub and to the manifest pins).

What I ran (logs in `build/review-phase4/logs/`): `curatrix doctor` (OK), `curatrix check <repo>
--stage local` for all seven repos (all pass, one warning), a small Sphinx experiment in
`build/review-phase4/exp/`, and read-only `gh` queries. I did not run `curatrix docs full`
separately; the manifest check builds the same set.

## Verdict

The infrastructure is real and of good quality for two days of work: bootstrap, limits, strict
docs builds, the need schema, the ledger, rulesets, the bump bot and Pages all work, and the PR
reviews found real bugs. The code is readable and the error messages are good.

But Phase 4 proved the machine with nothing in it. Every robarm document has zero needs, the
model is nine empty packages, and there is no KiCad or FreeCAD file. So every trace, graph and
CAD check passes on empty input, in CI and locally. The parts that the vertical bar of Phase 5
needs most (domain checks CK-F1 to CK-F4, code and test extraction, test reports, two thirds of the
view kinds, the agent skills and checklists) do not exist, and the Phase 5 plan has no tasks for
them. The check runner also has several ways to report "passed" without checking anything.

Phase 5 can start, but not with content. It should start with a short "5.0": a planted trace chain
through all repos, the missing checks, and the agent material (P4-1 to P4-3).

## Findings

### P4-1 No real content has ever gone through the pipeline — blocking-for-phase-5

Evidence:
- Needs per document in the full set (`build/full/docs/deploy/html/*/needs.json`): `se-req` 0,
  `se-arch` 0, `ee-design` 0, `me-design` 0, `sw-req` 0, `sw-arch` 0, `sw-test-spec` 0,
  `sw-test-report` 0, `int-test-spec` 0, `int-test-report` 0. Only `robarm` (18 `prj-dec`) and
  `xdmod-manual` (197) have needs, and those have no cross-repo links.
- All domain ledgers are empty (`robarm-*/ids.yaml`: every kind is `[]`).
- `robarm-syseng/generated/model-needs.json`, `robarm-ee/generated/cad-needs.json` and
  `robarm-me/generated/cad-needs.json` hold `"needs": {}`. `robarm-syseng/views/` has only a
  README.
- CI log of robarm-sw run 43670409532: CK-A1, A3, A4, A5, B3, E2, E3 all "ok (0.0 s)".

So the chain need → stub → SysML element → model need → downstream link → CAD need → test case →
test result has run only in the Phase 2 spike and in unit-test fixtures, never in the real repos,
the real registries or the real CI. This is the same situation as "CI green while checking
nothing", only now by design. The schema itself is sound: I planted a wrong-type link and an
unknown ID from a downstream document to an external need, and both fail the strict build
(`build/review-phase4/exp/wrongtype.log`, `unknown.log`).

Suggestion: before any real content, port the spike's chain as a small permanent "canary" (one
need, one requirement, one model element, one KiCad sheet, one FreeCAD part, one test case, one
result) into the robarm repos or into a fixture workspace that CI builds through the real
registries. Add one planted-error job: a branch or fixture where each rule must fail. Keep both
after Phase 5.

### P4-2 Tooling that the vertical bar needs is missing and not planned — blocking-for-phase-5

The Phase 5 tasks in `xdmod/claude/plan.md` are content tasks only. These pieces are specified but
not built:

| Needed by | Missing | Evidence |
|---|---|---|
| 5.1, 5.2, 5.6 | view kinds `context`, `usecases`, `allocation`, `variants` | `curatrix/src/curatrix/views/__init__.py:38` `IMPLEMENTED = ("interconnection", "decomposition")` |
| 5.8, 5.9 | CK-F1 (netlist vs pin maps), CK-F4 (ERC) | no `commands` in `robarm-ee/checks.yaml` |
| 5.10 | CK-F3 (FreeCAD parameters vs model), CK-F4 (recompute), TechDraw export | no `commands` in `robarm-me/checks.yaml`; `gen.py:149` "not implemented yet" |
| 5.11 | CK-F2 (devicetree vs model), which D101 puts into PR CI | `robarm-sw/checks.yaml` has only CK-F5a/F5b |
| 5.11 | `SW-IMPL` needs from code (`@xdid`), D77 | no code for it in `curatrix/src` or `sphinx/` |
| 5.12 | tool that writes `SW-TC` IDs into ZTEST comments, D80 | not in curatrix |
| 5.12 | test results in the docs: `evidence read` is not called by any check or docs build; CK-F5b (Twister) runs after CK-A6 (docs), so a docs build can never show the results of its own run | `checks.py` `plan()` puts `commands` last |
| 5.5, 5.13 | `coverage-matrix`, `config-page`, `sysml-element` | stubs, `sphinx/xdmod_sphinx/__init__.py:341-343` |
| 5.13, 6.1 | trace report, coverage matrix, change report pages | "It is not built yet" in `robarm-manifest/docs/robarm/*.rst` |

With `--stage local` the CAD checks are the reason to run locally (checks.md §1). Today no check
has `cad: true` except xdmod's own tool tests, so "local with CAD" and "pr --no-cad" check the same
things in every robarm repo.

Suggestion: add tooling tasks to Phase 5 next to the content tasks, in the order the content needs
them (context and use-case views first). Decide now which of these are cut from iteration 1, and
say so in the plan, so that 5.13 does not promise a report that cannot be built.

### P4-3 The agent material does not exist — blocking-for-phase-5

Evidence:
- `.claude/skills/` and `.claude/commands/` at the workspace root are empty.
- `xdmod/claude/` holds only `decisions.md`, `plan.md`, `mission-brief.md`, `framework/`, `notes/`,
  `research/`. There is no `skills/`, `commands/`, `checklists/` and no `xdmod/claude/CLAUDE.md`.
- `xdmod/launch/CLAUDE.md:51` tells every agent to review with `/review-pr`, and says "read
  `<repo>/claude/CLAUDE.md` before you change that repo". For xdmod that file is missing. The
  five robarm `claude/skills/README.md` files point to `xdmod/claude/skills/`, which is missing.
- The manual says the skills, checklists and `/review-pr` "are written in Phase 5"
  (`howto/work-as-an-agent.rst:56`), but the plan has no such task.

Phase 5 is where agents write requirements, model, CAD and code, and where every PR needs an agent
review against checklists (D126). The Phase 4 reviews were good, but each reviewer worked from an
ad-hoc brief.

Suggestion: write, before 5.1: `xdmod/claude/CLAUDE.md` (how to change curatrix, run tests, add a
check), `/review-pr` with the requirement and model checklists, and the two or three skills that
5.1–5.3 need (stakeholders and needs, EARS requirements, ID issuing). Write the others when their
step comes. Until a command exists, remove its name from the launch `CLAUDE.md`.

### P4-4 The check runner can pass without checking — should-fix

1. **Missing `checks.yaml` passes.** `checkcfg.py:205` turns a missing file into `{}`, and
   `ws.py:170` accepts any folder as a repo. `curatrix check libs` plans only CK-H1–H3 and passes;
   with `--stage full` it plans zero checks and still prints "CHECK PASSED" (`checks.py:453`).
   A renamed or deleted `checks.yaml` therefore turns a repo's CI green.
2. **A missing section switches checks off silently.** Example found: `robarm-manifest/checks.yaml`
   has no `bootstrap_template` key, so CK-H5 (bootstrap copy vs template, D118) never runs,
   although `command-layer.md` §2 and the manifest's `claude/CLAUDE.md` say it does. (The copy is
   identical today.)
3. **`skip` never fails.** CK-G2 is the suspect-link gate at the baseline (`error`), but without
   `--base` it is skipped and the stage passes (`checks.py:284-288`).
4. **Silent fallbacks.** `c_hygiene_build` treats a failed `git ls-files` as "no files"
   (`checks.py:325`); `ws.repos` falls back to a folder scan when `west list` fails
   (`ws.py:153`), which loses the SHAs that CK-B6 compares.

Suggestion: fail when `checks.yaml` is missing or when the plan is empty; print the list of checks
that are off for this repo and why; make a skipped check with level `error` fail at the `baseline`
stage; let each repo state the checks it expects (`expect: [CK-D1, CK-E1, ...]`) so that a lost
section is an error. Turn the silent fallbacks into errors.

### P4-5 Change impact and trailer checks never run in CI — should-fix

Evidence, CI log of robarm-sw run 43670409532:
```
skip CK-G1  needs-diff against the base (change impact)
       no base given (--base DIR with the needs.json files of main / the last baseline)
skip CK-H4  commit trailers on agent commits
       no origin/main to compare with
```
- CK-G1: the workflow never passes `--base`, nothing fetches the `needs.json` of `main` (Pages
  already publishes them under `latest/`), and nothing posts the PR comment that `checks.md`
  promises. The same holds for CK-G2 in the bump job.
- CK-H4: west checkouts have no `origin` remote, so the check is skipped in every CI run. It also
  only looks for the string `Co-Authored-By:` in every commit, so it would warn on human commits.

The change scenario of Phase 6 depends on CK-G1/G2. Suggestion: let the workflow download the
published `needs.json` set of `latest/` (and of the last baseline for CK-G2) and pass it as
`--base`; write the report into the job summary first, a PR comment later. For CK-H4 use the PR
base SHA from the event, or drop the check.

### P4-6 Upstream PR CI does not check the downstream repos — should-fix

`repo-topology.md` §7.3 says robarm-syseng and xdmod use the integration role "so that every
downstream repo is checked too". The workflow checks out the downstream repos but runs only
`curatrix check "$REPO"` (`xdmod/.github/workflows/curatrix-check.yml`, last step), and
`robarm-syseng/docs/documents.yaml` builds only `se-req` and `se-arch`.

Effect: a syseng PR that deletes or changes a requirement, or an xdmod PR that changes
`needs_config.toml` or curatrix, is green. The break shows up after the merge, in the bump PR, and
because of D127 every downstream PR then turns red at once.

Suggestion: for `repo: robarm-syseng` and `repo: xdmod`, also run `curatrix check robarm-manifest
--stage full --no-cad` (the full set with the PR's branch) as a second required job, or at least as
a report.

### P4-7 `full-set` on robarm-manifest is weaker than its name — should-fix

- A normal manifest PR and a push to `main` run `curatrix-check.yml` with the default
  `stage: pr` (`robarm-manifest/.github/workflows/check.yml`). The `full` stage, with CK-B1
  (every SYS-REQ refined or satisfied), CK-B5 (duplicate IDs across repos) and CK-B6, runs only
  for bump PRs (`bump.yml`, `stage: full`). A hand-made pin change or library upgrade gets a green
  `full-set` without the cross-repo rules.
- The required check `full-set` has no `integration_id` in the ruleset (the other six repos pin
  `15368`, GitHub Actions). Any status with that name from any token satisfies it. D142 says
  "from the GitHub Actions app".

Suggestion: pass `stage: full` in the manifest's `check.yml`; add the integration ID to the
manifest ruleset (owner action, D123).

### P4-8 CK-E2 will fail correct requirements; five checks have no tests — should-fix

CK-E2 (`checks.py:257-275`, level `error`) wants every value as `<number><unit>` in the sentence.
I ran the same expression on plain sentences:

| Sentence | Fields | Result |
|---|---|---|
| "... shall be between 0.5 and 2.5 ms." | min 0.5, max 2.5, ms | false error on `min` |
| "... within 50 milliseconds." | max 50, ms | false error |
| "... a payload of 1,000 g." | max 1000, g | false error |
| "... at least 2000000 Hz." | min 2000000, Hz | false error (compares with `2e+06`) |
| "... 90° ± 2°." | nominal 90, max 92 | false error on `max` |

There is no test for `c_ears`, `c_diff`, `c_trailers`, `c_pins` or `c_hygiene_build`
(`grep` over `curatrix/tests`). The first range requirement in 5.3 will hit this.

Suggestion: compare numbers as numbers (all numbers found in the sentence, any order, unit once
after the group), accept unit names, and make CK-E2 a warning until it has run on the real
requirements. Add table-driven tests for these five functions.

### P4-9 The trace model exists in three places with nothing that ties them — should-fix

`needs/needs_config.toml` is declared the single source (D64h). But curatrix has its own copies:
`graph.py:19-22` (`LINK_TYPES`, `REQ_TYPES`, `ORPHAN_TYPES`), `ids.py:38` (`NEED_KINDS`) and two
more copies of the ID regex. They have already drifted: the toml declares the links `revises` and
`supersedes` (lines 448, 453), `LINK_TYPES` does not, so unknown-ID (CK-A1), retired-link (CK-B3)
and needs-diff do not see them. No test compares the lists (`test_reference.py` only compares the
check catalogue).

R3 (orphans) and R5 (HIL fields) are also implemented twice, as schema rules in the toml and as
CK-A4/CK-A5 in `graph.py`. External needs are validated in the build of the repo that owns them, so
the second copy adds little.

Suggestion: read link types, requirement types and kinds from the toml at run time (curatrix
already parses it for the reference docs), or add one test that fails on any difference. Keep in
`graph.py` only the rules that need the merged graph (B1, B2, B3, B5, B6, unknown IDs).

### P4-10 Token defaults and one missed workflow — should-fix

- Org and all seven repos: `default_workflow_permissions: write`, `can_approve_pull_request_reviews:
  true` (`gh api repos/tiacsys/<repo>/actions/permissions/workflow`). Every workflow without a
  `permissions:` block gets a write token.
- The "ci/permissions" PRs added `permissions: contents: read` to the check workflow of five
  repos. robarm-manifest was missed: its `check.yml` has no `permissions:` block, so the `full-set`
  job runs with the write default. (The reusable job is safe, because the called workflow
  narrows the token.)

Suggestion: set the default to read and switch off PR approval by Actions, at the org (owner
action); add the block to the manifest's `check.yml`. This closes the gap for every future
workflow, where issue robarm-manifest #17 only fixes the known ones.

### P4-11 The author loop is slow before any content exists — should-fix

Measured locally (`build/*/checks/summary.json`): the Pilot needs 42.6 s for nine empty packages
plus libraries (CK-E1); the full-set docs build needs 70 s for 13 nearly empty documents; the
integration docs need 20 s. The documented loop in `robarm-syseng/claude/CLAUDE.md` is docs → gen
all (Pilot) → views build → check (docs again, Pilot again), so one round is about two minutes on
an empty model. Every downstream repo builds all its upstream documents again (D35).

Suggestion: cache the Pilot export on a hash of the model files and libraries, and let `check` use
a fresh `gen` result; measure again with 30 requirements and 20 elements before Phase 5 goes wide.
Give agents a fast inner loop (`--only CK-E1,CK-D2`) in the repo's `CLAUDE.md`.

### P4-12 Exact pins for rolling system tools — should-fix

`xdmod/tools.yaml` pins `git 2.56.1`, `cmake 4.5.0`, `ninja`, `node`, `npm`, `firefox 160.0`,
`dot 16.1.1` exactly, and `curatrix doctor` fails on any difference. The reference machine is a
rolling distro, so the next system update breaks `doctor` for reasons that do not matter (a git
patch release). CI already differs and only warns: `cmake 3.31.6`, `node 22.23.4`, `dot 2.43.0`
(robarm-sw run 43670409532), so CI and local builds render graphs with different graphviz major
versions.

Related: robarm-syseng has no `generated/provenance.json`, so CK-D5 warns today and will be an
error at the first baseline (`build/review-phase4/logs/check-robarm-syseng.log`).

Suggestion: pin exactly only what changes generated or committed output (Firefox and the drawio
viewer for views, Pilot, KiCad, FreeCAD, Doxygen); use minimum versions for the others. Regenerate
and commit the syseng provenance file.

### P4-13 The CAD path is proven only on hand-written fixtures — should-fix

`curatrix/tests/fixtures/kicad/board.kicad_sch` says `(generator "xdmod test fixture")`; it was not
saved by KiCad 10. No test calls `kicad-cli` or `FreeCADCmd` (the `tools` marker covers Pilot,
elkjs and Firefox only). `gen cad-exports`, `freecad_shapes`, the project library tables with
`XD_KICAD_*` and the launcher configs have no test and no real file to run on. The plain-Python
readers decide what CI sees of the CAD content (D110), so a format detail that the fixture lacks
(multi-unit symbols, hierarchical sheet instances, FreeCAD links and expressions) gives wrong needs
without any error.

Suggestion: in the canary of P4-1, use files saved by the real tools, and add a local-only test
that compares the plain-Python reader with the `kicad-cli` netlist and the FreeCAD property dump
for the same file.

### P4-14 Checks are advisory for the only actor, and D140 is still open-ended — should-fix

All rulesets let the admin role bypass through a PR, agents use the owner's login (D51), and D140
lets the coordinator agent merge. All 20 merged PRs show `mergedBy: tobiaskaestner` and zero formal
reviews; the agent reviews are comments from the same account. This is accepted in D134, and the
merged PRs were green. Two points to fix anyway:
- D140 is a "Phase 4 exception". Nothing ends it. State in the plan or as a new decision that from
  Phase 5 only the owner merges, or extend it on purpose.
- xdmod #16 had 11,890 added lines in 97 files and one review comment. Reviews of that size cannot
  be deep. Keep Phase 5 PRs to one SYSMOD step each.

While I reviewed, the main xdmod checkout moved from the pinned commit to a branch
(`docs/self-model-views`) with uncommitted changes to `checks.yaml`, `sysml/XdTrace.sysml` and new
`model/`, `generated/` folders. Somebody is working in the main checkout, not in a worktree set
(D125). With several agents in Phase 5 this will mix work; `curatrix doctor` could warn when a
framework repo in the main checkout is dirty or off its pin.

### P4-15 Two ID systems for decisions — nice-to-have

D120 froze `decisions.md` and made decisions `XD-ADR` / `PRJ-DEC` needs. But the code, workflows
and agent files still cite D-numbers: 213 in `curatrix/src`, `sphinx`, `cmake`, `launch` and
`.github` of xdmod, zero `XD-ADR` there; the launch `CLAUDE.md` uses only D-numbers. New decisions
get no D-number, so the two systems drift from the next decision on. `howto/add-a-test.rst:54`
also still says the run-record schema "is being built (task 4.5a)".

Suggestion: keep D-numbers as the short name in code and agent files (they are in `legacy_id`),
and say so in one line of the launch `CLAUDE.md` with the lookup command; or give new decisions a
D-number too. Fix the stale note.

### P4-16 The framework hardcodes the example project — nice-to-have

`ci.py:30` `PREFIXES = ("xdmod", "robarm-")`, `evidence.py:37` `TRACKED`, `setup.py:139`
(`removeprefix("robarm-")`), `cli.py:531` (`--repo` default `robarm-integration`), the workflow
default `manifest: tiacsys/robarm-manifest`. D66 and D111 say xdmod serves any workspace and never
depends on robarm. `ws.framework_repos` (repos with a `checks.yaml`) already gives the right set.

### P4-17 What to cut or simplify — nice-to-have

- **Tool provenance (CK-D5, `provenance.py`, 125 lines).** It already has an open defect (#23) and
  warns in syseng. `doctor` plus the pins give most of the value. Consider one line in the
  generated file's header instead of a second file and a check.
- **Double rules** (P4-9): drop CK-A4 and CK-A5 from `graph.py`.
- **`checks.py` table.** The `is_cad` column is `False` in every row, `_lv()` returns its
  argument, and dispatch goes through `globals()[fn]`. A small dataclass per check with the function
  itself is shorter and can be type-checked.
- **Worktree sets with re-exec** (`work.py` 226 lines, `cli.py:546-562`). Useful, but it is the
  most fragile part (symlinked shared folders, `$PWD` logic in `ws.py:57-64`) and, as seen above, not
  what is used in practice. Keep it only if Phase 5 really runs parallel agents.
- **Tombstones** (D130) before the first generated need exists. Fine to keep, but do not extend.
- **sphinx-llm** (D122) has an open defect list (#20) and no user yet; switch it off until someone
  reads the output.
- **Limits fallback.** On the `ulimit` backend, `pilot`, `firefox`, `elk`, `install` and `gui`
  have `vmem: none`, so they run with a timeout only. That is honest in `limits.yaml`, but the CI
  smoke step then proves a fallback that does not protect the heavy tools. Say so, or drop the
  smoke step.
- **Bump bot**: three jobs, 250 lines of YAML with inline Python. It works. Move the inline Python
  into `scripts/` so it can be tested like `bump.py`.

## Done well

- **The need schema is real.** Link types per owning type, target types and minimum links fail
  the strict build, also across documents (my experiment), and `test_needs_config.py` plants
  twelve errors that must fail.
- **Generate, commit, check** is applied the same way to stubs, model, views and CAD needs, with
  plain-Python CAD readers so CI sees the full graph (D110).
- **Error messages**: each failed check prints its reproduce command and log path; `summary.json`
  is easy for agents to read; exit codes 124 and 137 are explained.
- **Limits** are applied inside curatrix, with a tested fallback, and all tool calls except short
  git and west queries go through them.
- **Bump bot**: never moves a pin backwards or on a failed compare, one PR, one comment, no retry
  storm, keep-alive, and a job split with a read-only build job.
- **Sibling resolution (D127)** is implemented, tested with real git repos (`test_ci.py`), and
  treats an `ls-remote` failure as an error, not as "no branch".
- **Evidence writer**: orphan branch, never touches `main`, refuses previews, keeps unpushed
  records when the remote moved; the review found and fixed a real ID collision.
- **Rulesets** match D141/D142 in all seven repos (checked through the API), and the pins equal
  `main` everywhere.
- **Per-repo `claude/CLAUDE.md`** files are short, concrete and list real pitfalls. The manual has
  tutorials and how-to pages, and `doctor` gives a clear picture of the workspace.
- **Honest scope notes**: the docs say where something is a stub, and known gaps were filed as
  issues (xdmod #17–#24, robarm-manifest #16–#18) instead of being hidden.
