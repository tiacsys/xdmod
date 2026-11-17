# Phase 5: open owner actions and decisions

Moved from the coordinator's `build/phase5-work/admin-actions.md` (task 5.32) and completed with every
open owner decision of `phase5-decisions.md`. Status at the end of Phase 5 (2026-11-17). Agents do
none of these themselves: admin actions need the owner's approval of the concrete list (D123),
acceptances, tags and ADR acceptance are the owner's (D58, XD-ADR-0126, XD-ADR-0140).

## A. Admin actions (task 5.9, D123): prepared, not executed

Agents change repo or org settings only after the owner approved this concrete list.

| # | Action | Why | Command |
|---|---|---|---|
| 1 | robarm-manifest ruleset 27289841: the required check `full-set` must come from GitHub Actions (integration_id 15368), like the other repos | P4-7: today any status named `full-set` from any token satisfies it | `gh api -X PUT repos/tiacsys/robarm-manifest/rulesets/27289841 --input <ruleset with integration_id 15368 on full-set>` (the bump bot sets this status with the GITHUB_TOKEN, which is the Actions app, so the bump flow keeps working) |
| 2 | Org tiacsys: default workflow token read-only | P4-10: every workflow without a `permissions:` block gets a write token | `gh api -X PUT orgs/tiacsys/actions/permissions/workflow -f default_workflow_permissions=read -F can_approve_pull_request_reviews=true` |
| 3 | ~~Org tiacsys: Actions may not approve PRs~~ **not recommended now** | P4-10 | GitHub has one setting for "create and approve pull requests" (`can_approve_pull_request_reviews`). The bump bot creates its PR with the GITHUB_TOKEN (task 4.5), so switching it off stops the bump bot. Keep it on until the bump bot has its own identity (iteration 2, D134) |
| 4 | **Remove the Admin bypass** (`RepositoryRole` 5, `bypass_mode: pull_request`) from the rulesets of all eight repos (the seven of Phase 4 plus robarm-freecad-pcba, ruleset 27440745, a copy of robarm-me's) | Owner decision 2026-11-16 (P4-14, option B): required checks bind agents and the owner | per repo: `gh api -X PUT repos/tiacsys/<repo>/rulesets/<id> --input <same ruleset with bypass_actors: []>`; ids: xdmod 27289839, robarm-manifest 27289841, robarm-freecad-pcba 27440745, the others from `gh api repos/tiacsys/<repo>/rulesets` |
| 5 | ~~Create `tiacsys/robarm-freecad-pcba`~~ **done** (owner approved 2026-11-17) | EE-5, P5-7, task 5.29 | created with the ruleset of the other repos; the initial push to the empty `main` was allowed once, afterwards only PRs |

Check after 2: the bump bot needs `contents: write` and `pull-requests: write`; `bump.yml` declares
them per job, so a read-only default does not break it. `pages.yml` declares its own permissions too.
Check after 4: a red required check can no longer be merged by anyone; in an emergency the owner
adds the bypass back for a moment.

## B. Decisions (XD-ADR) to accept

The agents wrote these as `proposed` (`decision_status`); accepting is the owner's (a commit that sets
`decision_status: accepted`). All are on `main` of xdmod, `docs/xdmod-manual/explanation/decisions/`.

| ADR | Title | File | Context |
|---|---|---|---|
| XD-ADR-0134 | ME writes board geometry into KiCad in a co-design change | `domains.rst` | 5.28: the StepUp push works; "try it" approved the spike, not the text |
| XD-ADR-0139 | A board library repo for ME | `domains.rst` | 5.29: skeleton, `cam --board-model / --library`, CK-F20, CK-F21 |
| XD-ADR-0146 | FreeCAD assemblies: skeleton file name, parameter aliases, open order | `domains.rst` | 5.23/5.24 review (refines XD-ADR-0137) |
| XD-ADR-0147 | ME renderings without OpenGL, the fallback when Blender is absent | `scope.rst` | 5.30 |
| XD-ADR-0148 | Blender as an optional local renderer of the ME renderings | `scope.rst` | owner decision for Blender, 5.30 follow-up |

No other ADR on `main` is `proposed` (checked 2026-11-17).

## C. Open questions for the owner

1. **The ten-parameter limit** (XD-ADR-0137): do the ME copies of the space-budget values on a seat
   port count toward the ten driving parameters of a top-level assembly? The co-design PR leaves them
   out (the canary has 15 parameters, 8 counted), because they are copies of `SYS-IF` values, not ME
   choices.
2. **`Configs` on the link, not on the part:** the presence of a part per configuration is set on the
   FreeCAD link (as the FreeCAD spike found it works), not on the part document. Confirm.
3. **Sub-assembly chapters with fixed sentences:** in the assembly document, a sub-assembly chapter
   prints a fixed sentence for drawings, exploded view, renderings and parameters (only the top-level
   assembly has them in iteration 1). Confirm, or ask for more in iteration 2.
4. **`.venv/bin` first on `PATH` in agent sessions:** a workspace `.claude/settings.json` env entry
   would make the shims win for every Claude Code session here (a change of how sessions run, so it
   needs the owner's OK); today the rule "`eval "$(curatrix env)"` first" is written but not
   enforced.

## D. Owner-only acts on the canary

| What | Where | How |
|---|---|---|
| Accept the unrouted-net DRC errors | `robarm-ee/pcba/canary-board/accepted.yaml`, entry `check: CK-F4b, rule: unconnected_items, items: all` | an own commit that touches only that entry, with `Accepted-by: <name>` and no agent trailer (XD-ADR-0126) |
| Tag `canary-assembly/v0.1.0` | robarm-me, on `main` | `git -C robarm-me tag -a canary-assembly/v0.1.0 -m ... && git push origin canary-assembly/v0.1.0`; then `curatrix cam robarm-me canary-assembly` shows the release marking (exit criterion 3, "from a tag") |
| Tag `canary-cable/v0.1.0` | robarm-ee, on `main` | the same for the harness |
| A tag for the canary board (`canary-board/v0.1.0`), if wanted | robarm-ee | lets `cam --library` write the first board-library file (XD-ADR-0139) |
| **Tag ruleset** | all robarm repos | a tag ruleset so that only the owner can create `*/v*` tags (XD-ADR-0140 says tags are owner-only; today nothing enforces it). Needs approval as an admin action (D123): `gh api -X POST repos/tiacsys/<repo>/rulesets -f target=tag ...` with the owner as the only bypass actor |
| The HIL result of the canary | robarm-integration | the owner records it from `main` (D60); agents have no hardware |

## E. Things the owner may want to check

- `~/.config/kicad/10.0/kicad_common.json` was rewritten three times on 2026-11-17 by KiCad runs
  outside the workspace config (02:30:43, 06:29:22 and once in the canary C0 run); see the rule-4
  incidents in `phase5-decisions.md`. Since the shims and the hard rule (XD-ADR-0145), the author-loop
  measurement (126 commands) and the fixture run left it unchanged.
- `robarm-manifest/docs/documents.yaml` still has `base_url: http://localhost:8000/`; it must be the
  Pages URL before a full-stage CK-G1 base is used.
- PR xdmod#25 (`docs/self-model-views`, the self-model with diagrams) is still open; its set was
  removed.
