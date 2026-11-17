# Human and agent workflow (task 3.11)

Status: **AGREED 2026-11-14** (review answers → D123–D126). Built on D3, D15, D50–D53, D58–D61, D67, D71, D72, D98–D100, D113, D115, D119 (`../decisions.md`),
`repo-topology.md` §7, `checks.md`, `repo-layouts.md` §3, and how this planning session worked.

## 1. Roles

| Role | Who | Does |
|---|---|---|
| **Owner** | the user | sets goals, makes decisions, reviews and merges every PR, affirms evidence, makes baselines |
| **Domain engineer** | a person (SE, EE, ME, SW, integration) | authors and reviews content in their domain; affirms suspect links in their domain |
| **Agent author** | an AI agent | authors content on a branch: requirements, model, CAD through scripts, code, tests, docs; opens PRs |
| **Agent reviewer** | an AI agent (not the author) | first-pass review of a PR against checklists; posts findings as PR comments |
| **Coordinator agent** | the agent the owner talks to | plans, splits work, starts other agents, gathers results, keeps `plan.md` and the decision log |

Agents and people do the **same work with the same tools** (D3): curatrix, checks, the same skills and checklists. The differences are in §2.

## 2. What agents may and may not do

| Agents may | Agents may not |
|---|---|
| create branches, commit, push to their own branches | merge PRs (Phase 5 exception for the coordinator: D140, §3b), push to `main`, force-push to other people's branches |
| open PRs and issues, and comment on them, always with the provenance trailer (D72) | change repo or org settings, rulesets, secrets, create or delete repos **without your approval of the concrete action list** (D123) |
| add `Co-Authored-By`, and `Signed-off-by` in the owner's name where a repo requires it (D119) | **affirm** suspect links, give manual verdicts or write `Accepted-by:`. They only **propose** them; a human commit counts (D58, P5-4) |
| run any tool through curatrix, under limits (D71) | run tools without limits, install system packages, use sudo |
| record HIL evidence from `main` or baseline commits (D60) | record evidence from PR branches as anything but previews |
| post freely in robarm-* and xdmod; on **other repos** (zdocs, affirmatrix, upstream projects) only after the owner approved the draft (D124) | post to external services other than GitHub and the package/tool sources the workspace uses |

## 3. A change, end to end

1. **Start.** There is an issue (D53), or a task in `plan.md`. The issue names the affected needs if they're known.
2. **Branch.** One branch name for the change, in every repo it touches (D52), e.g. `feat/sys-req-0042-latency`.
3. **Author.** A person or agent edits content and runs `curatrix gen …` for generated files and `curatrix ids fix` for placeholder IDs.
4. **Local check.** `curatrix check <repo> --stage local` for every touched repo, with CAD content (D46). For `.FCStd` changes, also the review report as a Pages preview (D108).
5. **PRs.** One PR per repo. Each lists its sibling PRs and the affected needs (from `needs-diff`), and ends with the trailer.
6. **CI.** `--stage pr` per repo (D56, D101).
7. **Agent review (D126, every PR in robarm-* and xdmod).** A reviewer agent (not the author) runs `/xd-review-pr <repo> <PR>` (`xdmod/claude/commands/review-pr.md`). It runs `curatrix check <repo> --stage local` (for robarm-ee and robarm-me with CAD content, P5-11: the second run of every check that needs KiCad or FreeCAD; today there is none, they come with tasks 5.17-5.27), checks the change against the checklists (§5) and posts one comment with the result table and the findings.
8. **Human review and merge.** The owner or a domain engineer reviews, asks for changes, and **merges**, upstream repos first. Merge = approval (D51). In Phase 5 the coordinator agent may merge instead (§3b).
9. **Bump.** The bump bot collects the new SHAs into the bump PR (D89). Its full-set build must pass. The owner merges it.
10. **Suspect links.** If the change made links suspect (R7), an agent prepares the affirmation proposals (reason + diff). A domain engineer or the owner affirms them with their own commit (D58).
11. **Baseline**, when wanted: gates, tag, release (`repo-topology.md` §7).

## 3a. PR size and stacked PRs

- **One SYSMOD step or one tool feature per PR** (XD-RULE-0046). Generated files go with the change that causes them and are not counted. CK-H7 warns above 600 hand-written lines or 15 files (a repo may set `pr_size:`); it never fails. Documentation-only PRs may exceed it; say so in the PR text.
- **Stack** larger work as a chain of PRs, each layer one step or feature:
  1. Bottom layer: `curatrix work start feat/a <repos>`; open its PR against `main`.
  2. Next layer: `curatrix work start feat/b <repos> --base feat/a`; open its PR with `--base feat/a`. Repos that are not in the parent start from `main`. CI resolves siblings through the PR's base branch (one level: head branch, else the base branch, else `main` or the pin); CK-H7 and CK-H4 count per layer. Locally, set `XD_BASE_REF=origin/feat/a` to measure a layer the same way.
  3. **Review per layer**: every layer gets its own `/xd-review-pr`.
  4. **Merge bottom-up**: `feat/a` first. Then rebase the child onto `main` and force-push the own branch:
     `git -C <repo> fetch origin && git -C <repo> rebase --onto origin/main <old tip of feat/a> feat/b`, then `git -C <repo> push --force-with-lease origin feat/b`, and change the PR's base to `main` (`.venv/bin/gh pr edit <n> --base main`). Force-push only your own branches.

## 3b. Acceptance and merge rights

- **`Accepted-by: <name>`** is a commit trailer that accepts a finding (ERC/DRC, FreeCAD checks) in `accepted.yaml` (P5-4). **Only humans write it. Agents never do**, not even when asked in a brief; they propose the entry in the PR and leave the commit to the human. Such a commit has no agent trailer and touches only acceptance entries.
- **D140 is active for the whole of Phase 5** (P5-14). The coordinator agent may merge a PR in xdmod or robarm-* when all of these hold: an agent review by another agent (`/xd-review-pr`) with no open must-fix finding; the required checks are green (no Admin bypass); for robarm-ee and robarm-me PRs, the local CAD check run is posted in the review (P5-11). Other agents never merge. The owner reviews per block after the merge, against the canary with the demo script (`claude/notes/phase5-demos.md`), and reverts or asks for fixes.

## 4. Agents working in parallel

Several agents can work at the same time, as in this session's research and zdocs work. Rules:
- **One agent per branch per repo.** Two agents never edit the same repo checkout at the same time.
- **Isolation (D125).** An agent that changes repos works in its own **git worktrees** under `<ws>/.worktrees/<branch>/<repo>`. The coordinator creates them with `curatrix work start <branch> <repos…>` and removes them with `curatrix work done <branch>` after merge. Shared, read-only parts (Zephyr, libraries, `.venv`) are not duplicated. Builds go to `build/wt-<slug>/` (the branch with `/` as `-`: `feat/x` -> `build/wt-feat-x/`). curatrix maps paths so that docs and upstream builds see the worktree instead of the main checkout.
- **Briefs.** Each agent gets a brief with: its goal, the decisions that bind it, the files to read, its output paths, the limits rule, the trailer rule, and what it must not do.
- **Reports.** Each agent writes its result into a file (research report, PR, notes) and returns a short summary. The coordinator checks claims that matter before passing them on, e.g. by re-running a check or reading the PR.
- **Budget.** The coordinator keeps the number of parallel agents small (around 10 at most), and tells the owner before starting more.

## 5. Skills, commands and checklists (D113)

| Kind | Examples | Home |
|---|---|---|
| SYSMOD step skills | one per step: problem statement, stakeholders, needs, context, use cases, requirements (EARS), functional/logical/product architecture, features and configurations, verification | `xdmod/claude/skills/` |
| Cross-cutting skills | issue IDs, add a view, cross-repo change, prepare an affirmation, write a test spec | `xdmod/claude/skills/` |
| Domain skills | KiCad edits through scripts (no IPC write API in KiCad 10), FreeCAD parameter changes, ZTEST annotation (from safety's `annotate-ztest`), devicetree overlays | `<repo>/claude/skills/` |
| Commands | `/xd-review-pr` (exists); later `/new-requirement`, `/affirm-proposal`, `/bump-status`, `/baseline-check` | `xdmod/claude/commands/` |
| Review checklists | requirements, model, code, KiCad, FreeCAD, CI and tooling | `xdmod/claude/checklists/` |

Each skill says what to read first, what to produce, and which checks must pass. This follows SYSMOD4AI's idea of prompts per step.

Skills and commands are linked into `<ws>/.claude/` with the repo prefix: `xd-` for xdmod, `ee-` for robarm-ee, and so on. `xdmod/claude/commands/review-pr.md` is `/xd-review-pr`.

**D-numbers** (D127) stay as short names in code and agent files. They are the `legacy_id` of the `XD-ADR` needs in the manual; look one up with `grep -rn ":legacy_id: D127" xdmod/docs`. A D-number without a need is only in `xdmod/claude/decisions.md`.

## 6. Planning and records

- `plan.md` (in `xdmod/claude/` after D70) is the master plan. Tasks become issues in the repo where the work happens (D53).
- Decisions go into the decision log (and later ADRs, `framework-docs.md` question 1), never into the plan.
- Each phase ends with notes in `claude/notes/` (spike, retrospective).

## 7. Answered review questions (2026-11-14)

1. **GitHub admin by agents:** allowed only after the owner approves each concrete action list (D123).
2. **Approval before posting:** none needed in robarm-* and xdmod. On other repos, agents draft first and post after approval (D124).
3. **Parallel isolation:** git worktrees inside the workspace, created and removed by curatrix (D125).
4. **Agent review:** on every PR in robarm-* and xdmod, before the owner's review (D126).
