---
description: Review a PR in xdmod or robarm-* as the agent reviewer (D126): run the local checks, go through the checklists, post one comment with the check table and the findings. Never merges.
argument-hint: <repo> <PR number>
---

# Review a pull request

You review PR **$ARGUMENTS** (repo and PR number) as the agent reviewer (D126,
`xdmod/claude/framework/workflow.md` §3). You are not the author. You read, run checks and comment.

**Never** merge, approve-and-merge, push to the PR branch, write an `Accepted-by:` trailer, affirm a
suspect link, give a manual verdict or accept a finding (D58, P5-4). You only report and propose.

## 1. Get the change

Always review in a set of your own, `review/<repo>-<n>`, never in the author's set. From the
workspace root (`<ws>`):

```sh
.venv/bin/gh pr view <n> -R tiacsys/<repo> --json title,body,baseRefName,headRefName,headRefOid,files,commits
.venv/bin/curatrix work start review/<repo>-<n> <repo> [sibling repos with the same branch]
cd .worktrees/review/<repo>-<n>
git -C <repo> fetch origin <head branch> && git -C <repo> checkout --detach FETCH_HEAD
git -C <repo> rev-parse HEAD            # must equal headRefOid; otherwise fetch again
git -C <repo> fetch origin <base branch>
git -C <repo> diff origin/<base>...HEAD --stat
git -C <repo> diff origin/<base>...HEAD
```

- Do the same `fetch` + `checkout --detach FETCH_HEAD` in every sibling repo (same branch name in
  other repos, D52), so the check sees the whole change.
- Never use `work start <head branch>`: it reuses the author's set (with uncommitted changes) or
  an old local branch.
- A stacked PR (base is not `main`): review only this layer and run the checks with
  `XD_BASE_REF=origin/<base>`.
- Read the PR text: does it say what it changes, list sibling PRs and affected needs, and end with
  the provenance line?

## 2. Run the local check

From the set root (the set links `.venv`):

```sh
.venv/bin/curatrix check <repo> --stage local
```

- For **robarm-ee and robarm-me** run it **with CAD content** (no `--no-cad`, P5-11). PR CI has no
  KiCad or FreeCAD, so this is the second run of every check that needs one: EE CK-D8, CK-D9,
  CK-F4a, CK-F4b; ME CK-F4c, CK-F16, CK-F17, CK-F18; both CK-D10. Name them in the table with the
  KiCad / FreeCAD versions. Run `curatrix cam` before the check when CK-D10 should see the design
  output, and build the documents as in the manual's how-to "Review an EE or ME pull request from a
  local docs build" when the PR changes what they show.
- For xdmod the check runs the curatrix tests (XD-T1, XD-T2) and the strict manual build. If the PR
  adds or changes a check, also run `.venv/bin/curatrix fixtures`.
- For each failure, run the printed `reproduce:` command and read the log before you write a finding.

Put the result table at the top of the findings comment (§4). Build it from the `summary.json`
path that `curatrix check` prints:

```markdown
**`curatrix check <repo> --stage local`** (with CAD content | --no-cad), head `<short sha>`, <date>

| Check | Status | Findings |
|---|---|---|
| CK-A6 | ok | |
| CK-E2 | warn | SYS-REQ-0003: max = 20 does not appear as a number in the sentence |

Off for this repo: <the "off for this repo" line>. Checks that needed a CAD tool: <none | list, with kicad-cli / FreeCAD versions>.
```

## 3. Go through the checklists

Use every checklist that matches a changed file (`xdmod/claude/checklists/`):

| Changed | Checklist |
|---|---|
| rst needs: `SYS-STH`, `SYS-NEED`, requirements, test specs | `requirements.md` |
| `model/*.sysml`, views, `model/generated/` | `model.md` |
| Python, C, devicetree, tests, scripts | `code.md` |
| `*.kicad_*`, `pcba/`, `proto/`, `harness/` | `kicad.md` |
| `*.FCStd`, `parts/`, `assemblies/` | `freecad.md` |
| `checks.yaml`, workflows, `tools.yaml`, `requirements.txt`, curatrix itself | `ci-and-tooling.md` |

Every PR also gets the general items:

- One SYSMOD step or one tool feature (CK-H7 warns above the size limit; a docs-only PR may exceed
  it if the PR text says so). Larger work should be stacked.
- Every agent commit carries `Co-Authored-By: <agent> <noreply@anthropic.com>` (CK-H4).
- No `Accepted-by:` trailer in an agent commit. No `status` changes that only a human may make.
- Generated files are committed with the change that causes them, and fresh.
- New IDs come from the ledger (`ids.yaml` grew by exactly the new numbers, no gaps filled, none reused).

## 4. Post one findings comment

Exactly **one** comment: the check table from §2 first, then all findings, sorted by weight.
Each finding names the file and line and says what to change.

```markdown
**Agent review** (`/xd-review-pr`), head `<short sha>`

<check table from §2>

**Must fix** (blocks the merge)
1. `docs/se-req/needs.rst:42` SYS-REQ-0004 has `max: 20` but the sentence says 25 ms. Make them agree.

**Should fix**
1. ...

**Nits**
1. ...

Checked: requirements.md, model.md. Not checked: <what you could not check, and why>.
Result: <no must-fix findings | N must-fix findings>.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
```

- **Must fix:** a failed check, a broken trace link or link direction, an invented or reused ID,
  stale generated files, a rule from `CLAUDE.md` broken, a wrong statement in docs, a bug.
- **Should fix:** a warning that the PR introduced, unclear text, a missing test or planted error.
- **Nits:** wording, order, style.
- If there is nothing to report, still post the comment with "No findings".

Post with `.venv/bin/gh pr comment <n> -R tiacsys/<repo> --body-file <file in build/>`. Do not use
`gh pr review --approve`.

## 5. Clean up

```sh
cd <ws> && .venv/bin/curatrix work done review/<repo>-<n> --force --delete-branch   # only your review set
```

Report to whoever started you: PR URL, the check result line, the number of must-fix findings.
