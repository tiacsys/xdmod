# xdmod: rules for agents

Read the workspace `CLAUDE.md` (copied from `xdmod/launch/CLAUDE.md`) first. This file adds the
rules for changing xdmod itself: the method pages, the manual, and the tool `curatrix`.

## What this repo is

| Path | What |
|---|---|
| `curatrix/src/curatrix/` | the command layer and check runner (`cli.py` entry, `checks.py` built-in checks, `work.py` worktree sets, `ci.py`, `fixtures.py`, `ids.py`, `gen.py`, ...) |
| `curatrix/src/curatrix/data/checks.yaml` | check catalogue: each built-in check's `XD-CHECK` need ID and the `XD-RULE`s it enforces |
| `curatrix/tests/` | pytest suite; `test_planted_errors.py` holds the planted error of every check (`PLANTED`) |
| `curatrix/README.md` | CLI table, checks.yaml format, check catalogue table, worktrees, tests |
| `curatrix/limits.yaml` | memory and time limits per use (`curatrix limits`) |
| `needs/needs_config.toml` | the trace model: need types, link types on their owning type, fields, schema rules |
| `sphinx/`, `sysml/`, `cmake/` | Sphinx extensions and conf helper, SysML trace library, the zdocs consumer block |
| `docs/xdmod-manual/`, `docs/xdmod-ref/` | the manual (decisions `XD-ADR`, rules `XD-RULE`, checks `XD-CHECK` as needs) and the reference |
| `claude/` | plan, decision log, framework pages (`framework/*.md`), notes, and the agent material: `skills/`, `commands/`, `checklists/` |
| `launch/CLAUDE.md` | the workspace rules; copied to the workspace root by `curatrix bootstrap` / `update` |
| `templates/`, `workflows/`, `.github/workflows/` | bootstrap template, CI caller template, reusable check workflow |
| `checks.yaml`, `ids.yaml`, `tools.yaml` | xdmod's own checks, ID ledger (`XD-ADR`, `XD-RULE`, `XD-CHECK`), tool pins |

Skills and commands in `claude/skills/<name>/` and `claude/commands/<name>.md` are linked into
`<ws>/.claude/` as `xd-<name>` (`setup.assemble_claude`). So `claude/commands/review-pr.md` is
`/xd-review-pr`.

## Where to work

- **Main checkouts sit at the manifest pins** (detached HEAD after `west update`). Never edit
  them. Work only in a worktree set: from the workspace root
  `.venv/bin/curatrix work start <branch> xdmod [other repos]`, then `cd .worktrees/<branch>`.
- Inside a set whose xdmod is on the branch, curatrix runs from the set's `xdmod/curatrix/src`.
  Call it as `.venv/bin/curatrix` from the set root (the set links `.venv`).
- Do not run `west update` or `curatrix update` inside a set.
- Builds of a set go to `build/wt-<slug>/` (`docs/agent-material` -> `wt-docs-agent-material`); from
  the set root that is `build/<area>/`, through the set's `build` link.

## Tests

From the set root (or the workspace root), always under limits:

```sh
curatrix run --use tests -- .venv/bin/python -m pytest -q -m "not tools" xdmod/curatrix/tests   # what CI runs (XD-T1)
curatrix run --use tests -- .venv/bin/python -m pytest -q -m tools xdmod/curatrix/tests         # Pilot, elkjs, Firefox (XD-T2, local)
curatrix run --use tests -- .venv/bin/python -m pytest -q xdmod/curatrix/tests/test_check_runner.py -k expect
curatrix fixtures                                                                                # planted error of every check
```

Markers: `tools` (needs Java, node or Firefox), `sphinx` (runs sphinx-build). Temporary files go
to `build/xdmod-dev/pytest/`. Then the repo check, which also builds the manual strictly:

```sh
curatrix check xdmod --stage local
```

A new `.rst` page must be in a toctree, or the strict build fails.

## How to add a built-in check

Every new rule gets an ID, a stage and a severity in `claude/framework/checks.md` **before** its
code, and starts as a warning until it ran on the canary. Then, in one PR:

1. **Code:** a function `c_<name>(ctx, r)` and a row in `BUILTIN` in `curatrix/src/curatrix/checks.py`
   (ID, name, level per stage, the checks.yaml section it needs, CAD or not, function name).
   If it needs a section, add its text to `NEED_TEXT` so `check` can say why it is off.
2. **Catalogue:** an entry in `curatrix/src/curatrix/data/checks.yaml` with `need: XD-CHECK-NEW-<tag>`,
   `enforces: [XD-RULE-...]` and a description. If no rule fits, add an `xd-rule` need in
   `docs/xdmod-manual/explanation/rules/` (placeholder ID, `decided_by` an `XD-ADR`). Then
   `curatrix ids fix xdmod`. Never type a number.
3. **Planted error:** a test that plants the error and asserts the check reports it, and its entry
   in `PLANTED` in `curatrix/tests/test_planted_errors.py`. A check without an entry fails
   `test_every_check_has_a_planted_error`. Mark it `tools` if it needs a tool.
4. **Docs:** a row in the catalogue table of `curatrix/README.md` and in `claude/framework/checks.md`.
5. **Every repo's `expect:` list** (CK-H6): add the new ID to `checks.yaml` of xdmod and of each
   robarm repo whose sections switch the check on. Otherwise CK-H6 fails there.
6. Run the tests, `curatrix fixtures` and `curatrix check xdmod --stage local`.

## Merge order for a new checks.yaml key

Old curatrix rejects an unknown key; new curatrix may require it. So:

1. Merge the xdmod PR first, and **bump xdmod in the manifest** (bump PR) before or together
   with the repos that use the key. Otherwise the manifest's Pages build and robarm CI run the old
   pinned curatrix and fail.
2. Then merge the robarm PRs (same branch name, D52).
3. Better: introduce a new key as optional first, make it required in a later PR.

## Rules

- **One tool feature per PR**, stacked for larger work, D-numbers, `Accepted-by:`, D140:
  `claude/framework/workflow.md` §3a, §3b, §5.
- **No robarm names in xdmod code** (task 5.6). Text examples in docs are fine.
- Decisions go into the decision log and `claude/decisions.md`, never into `plan.md`.
- The manual quotes decisions and rules as `:need:` references, not as D-numbers.

## Pitfalls

- **KiCad and FreeCAD only through curatrix** (`curatrix launch kicad|freecad`, or `curatrix run
  --use kicad-cli|freecad`), which set the workspace-local config. A bare `pcbnew` or `FreeCADCmd`
  call writes to `~/.config` (rule 4; the canary C0 incident). Never touch `~/.config`.
- A test that runs `git` in a temp repo must not see the caller's environment by accident:
  `XD_BASE_REF` and `GITHUB_BASE_REF` change the base of CK-H4 and CK-H7.
- CK-H4 detects agent commits by "Claude Code" or anthropic.com in the message. A planted message
  that only says "Claude" is a human commit.
- A placeholder ID fails the strict docs build (the ID regex), not only CK-C1. Run
  `curatrix ids fix xdmod` before `curatrix check`.
- The manual is built from the docs registry; new pages that are not in a toctree fail the build.
- `curatrix check` with `--only` runs a check outside its stage; use it to reproduce one failure.
