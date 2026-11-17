# XDMOD workspace

This file is copied to the workspace root by `curatrix bootstrap` / `curatrix update` from
`xdmod/launch/CLAUDE.md` (D69). Do not edit the copy; change the original in xdmod.

The workspace is one west topdir (D68): `.west/`, `.venv/`, `build/`, `.xdmod/` and all repos sit
here. The design repos are at the top level (`robarm-*`), dependencies under `tools/` and `libs/`,
Zephyr under `zephyr/` and `modules/`. Each repo has a `claude/` folder with its own rules, skills
and pitfalls; read `<repo>/claude/CLAUDE.md` before you change that repo. Shared skills and commands
are linked into `.claude/` (D113).

## Rules

1. **Run every command from the workspace root** (D67), including GUI launchers and doc builds.
   `git -C <repo> ...` is the only exception. Paths in output and docs are relative to the root.
2. **Every tool runs under a memory limit and a timeout** (D71). Use curatrix: its subcommands apply
   the limits from `xdmod/curatrix/limits.yaml` themselves; anything else goes through
   `curatrix run [--use USE | -m MEM -t TIME] -- <cmd>` (exit 124 = timeout, 137 = out of memory).
   `curatrix limits` shows the table. Never raise a limit to make a runaway tool pass; find out why.
3. **Build output only under `build/<area>/`** (D46): `<area>` = the repo name, `full` for the full set,
   `<branch>` for worktree builds, or a named step. Nothing generated goes into a repo except the
   committed generated files (`generated/`, `model/generated/`, `views/`), which `curatrix gen` /
   `curatrix views build` write and `curatrix check` compares.
4. **Use the workspace venv** (`.venv`, `eval "$(curatrix env)"`). No system packages, no sudo, no
   user-global tool configuration (KiCad, FreeCAD and drawio run with `.xdmod/` configs through
   `curatrix launch`). **Never run KiCad, FreeCAD or Blender outside curatrix or its `.venv/bin`
   shims, not even `--version`**: a bare `kicad-cli --version` rewrites `~/.config/kicad`.
5. **Trace rule** (D5, D36): the more concrete artifact holds the link; links point right to left in
   the V and from concrete to abstract. Backlinks are only ever computed. Each link type is declared
   on the need type that owns it (`xdmod/needs/needs_config.toml`).
6. **IDs** (`<DOMAIN>-<KIND>-<NNNN>`, D78) come from the repo's ledger `ids.yaml`. Write placeholders
   like `SYS-REQ-NEW-a` and run `curatrix ids fix <repo>`; never invent numbers, never reuse one.
   Retire needs (`status: retired`) before deleting them (D64e, D130).
7. **Check before you push**: `curatrix check <repo> --stage local` for every repo you touched
   (with CAD content, D46). Fix what it reports; it prints the command that reproduces each failure.
8. **Commits** carry the trailer `Co-Authored-By: <agent> <noreply@anthropic.com>` (D51); add
   `Signed-off-by` in the owner's name only where a repo requires it (D119). Everything posted on
   GitHub (issues, comments, PR texts, reviews) ends with
   `🤖 Generated with [Claude Code](https://claude.com/claude-code)` (D72).

## What agents may and may not do (workflow.md §2)

| Agents may | Agents may not |
|---|---|
| create branches, commit, push to their own branches | merge PRs (Phase 5: see D140 below), push to `main`, force-push to other people's branches |
| open PRs and issues and comment on them, with the provenance trailer | change repo or org settings, rulesets, secrets, create or delete repos without the owner's approval of the concrete action list (D123) |
| add `Co-Authored-By`, and `Signed-off-by` where a repo requires it | affirm suspect links, give manual verdicts or write an `Accepted-by:` trailer: they only propose them; a human commit counts (D58, P5-4) |
| run any tool through curatrix, under limits | run tools without limits, install system packages, use sudo |
| record HIL evidence from `main` or baseline commits (D60) | record evidence from PR branches as anything but previews |
| post freely in robarm-* and xdmod | post on other repos (zdocs, affirmatrix, upstream) before the owner approved the draft (D124) |

Every PR in robarm-* and xdmod gets a review by another agent (`/xd-review-pr <repo> <PR>`) before
the owner's review (D126). A change across repos uses one branch name in every repo it touches (D52).

## Pull requests (workflow.md §3a, §3b)

- **One SYSMOD step or one tool feature per PR.** CK-H7 warns above 600 hand-written lines or 15
  files (generated files do not count).
- **Stack** larger work: `curatrix work start <child> <repos> --base <parent>` and a PR against
  `<parent>`. Review each layer, merge bottom-up, then rebase the child onto `origin/main`
  (steps in `xdmod/claude/framework/workflow.md` §3a).
- **`Accepted-by:`** (accepting an ERC/DRC or FreeCAD finding) is written only by humans. Agents
  never write it; they propose the `accepted.yaml` entry in the PR.
- **D140 is active in Phase 5** (P5-14): the coordinator agent may merge a PR in xdmod or robarm-* after an
  agent review without open must-fix findings, with green required checks, and for robarm-ee and
  robarm-me with the local CAD check run posted in the review. Other agents never merge.
- **D-numbers** (D127) are the `legacy_id` of the `XD-ADR` needs (workflow.md §5):
  `grep -rn ":legacy_id: D127" xdmod/docs`.

## Commands (curatrix, D98)

| Command | Does |
|---|---|
| `curatrix doctor` | tools, versions (tools.yaml), paths, hooks, west state |
| `curatrix update` | `west update -k`, refresh `.venv`, tools, `.claude/` links, hooks |
| `curatrix check <repo> --stage local` | the repo's checks (`<repo>/checks.yaml`); `--no-cad`, `--only CK-D3`, `--json` |
| `curatrix docs <repo>` / `docs full` | strict zdocs build into `build/<area>/docs/` |
| `curatrix gen stubs\|model\|cad-needs\|code-needs\|freecad-json\|all <repo>` | regenerate the committed generated files |
| `curatrix ids new <KIND>` / `ids fix <repo>` | issue IDs, replace placeholders |
| `curatrix views build\|check\|normalize <repo>` | views as editable `.drawio.svg` |
| `curatrix launch kicad\|freecad\|blender\|drawio\|claude` | GUI tools with workspace-local config (memory limit only) |
| `curatrix run -- <cmd>` | anything else, with the workspace env and limits |

`west update` moves projects back to their pins (detached HEAD). While you work on branches use
`curatrix update` (it runs `west update -k`).
