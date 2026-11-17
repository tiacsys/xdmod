# Phase 5 demo scripts (owner review per block, P5-14)

D140 stays active in Phase 5: agents merge after an agent review, green required checks and, for
EE and ME, the posted local CAD check run. The owner reviews **per block after the merge**, with
the script below, and reverts or asks for fixes. Each block adds its section when it is done.

All commands run from the workspace root, or from the demo set root where stated. Paths are
relative to that root. The expected output is shortened.

## Setup (all blocks)

The main checkouts sit at the manifest pins, which may lag behind `main`. Use a throw-away
worktree set on the current `main` of the repos you look at:

```sh
.venv/bin/curatrix work start demo/block-a xdmod robarm-ee robarm-syseng
cd .worktrees/demo/block-a
alias cx=.venv/bin/curatrix      # the set links .venv; curatrix runs from the set's xdmod
```

The branch `demo/block-a` is never pushed. At the end:

```sh
cd ../../.. && .venv/bin/curatrix work done demo/block-a --force --delete-branch   # likewise demo/canary
```

## Block A: checks that bite (tasks 5.1-5.6)

### A1. A check run says what is off and what it expects (5.1)

```sh
cx check robarm-ee --stage local --no-cad
```

Expect: `off for this repo: CK-B4 (needs model.variants: true); CK-D1 (needs a stubs section); ...`,
then one line per check, including `ok CK-H6 checks.yaml lists exactly the checks the repo runs
(expect:)` and `ok CK-H7 PR size ...`, and `CHECK PASSED`. Compare with the `expect:` list at the
end of `robarm-ee/checks.yaml`.

### A2. A lost or unknown check in `expect:` fails (5.1, CK-H6)

```sh
sed -i 's/, CK-H7$/, CK-H8/' robarm-ee/checks.yaml
cx check robarm-ee --stage local --only CK-H6
git -C robarm-ee checkout checks.yaml
```

Expect: `FAIL CK-H6` with `CK-H8: expected, but no such check` and `CK-H7: runs, but is not in
expect:`, and a `reproduce:` line.

### A3. No checks.yaml, no pass (5.1)

```sh
mv robarm-ee/checks.yaml robarm-ee/checks.yaml.off
cx check robarm-ee --stage local; echo "exit $?"
mv robarm-ee/checks.yaml.off robarm-ee/checks.yaml
```

Expect: `robarm-ee/checks.yaml: missing. Every repo that curatrix check runs on needs a
checks.yaml` and a non-zero exit.

### A4. A skipped error check fails at the baseline stage (5.1)

```sh
cx check robarm-ee --stage baseline --no-cad
```

Expect: `FAIL CK-G2 ... no base given ... skipped at the baseline stage: an error-level check must
run here`, `CHECK FAILED`. (A real baseline passes `--base`.)

### A5. A PR that is too large gets a warning (5.1, CK-H7)

```sh
XD_BASE_REF=origin/main~8 cx check xdmod --stage local --only CK-H7
```

Expect: `warn CK-H7 ... hand-written lines in .. files against origin/main~8 (limits 600 / 15):
one SYSMOD step or one tool feature per PR`, and still `CHECK PASSED` (a warning never fails).

### A6. Placeholders and requirement values (5.4, CK-C1, CK-E2, CK-E3)

Plant a requirement whose sentence disagrees with its fields:

```sh
cat >> robarm-ee/docs/ee-design/index.rst <<'EOF'

.. ee-req:: Demo
   :id: EE-REQ-NEW-demo
   :status: draft
   :derived: true
   :rationale: demo
   :ears: event
   :unit: ms
   :max: 20

   The board shall answer within 25 ms.
EOF
cx check robarm-ee --stage local --only CK-A6,CK-C1,CK-E2,CK-E3
```

Expect: `FAIL CK-A6` (the placeholder does not match the ID regex) and `FAIL CK-C1 ... placeholder
EE-REQ-NEW-demo (run curatrix ids fix)`. Then:

```sh
cx ids fix robarm-ee
cx check robarm-ee --stage local --only CK-A6,CK-C1,CK-E2,CK-E3
git -C robarm-ee checkout .
```

Expect: `EE-REQ-NEW-demo -> EE-REQ-0001`, then `ok CK-A6`, `ok CK-C1`, `warn CK-E2 ... max = 20 does
not appear as a number in the sentence`, `warn CK-E3 ... ears=event but the sentence does not start
like that pattern`. To see the number parsing, change the sentence to "When asked, the board shall
answer within 20 ms." and run the check again: both warnings go away.

### A7. Every check fails on its planted error (5.3, P5-13)

```sh
cx fixtures
```

Expect: one `ok CK-.. passed <test>` line per built-in check (also the tool-backed CK-E1 and CK-D3),
the control line, `FIXTURES PASSED` and the record path it prints (`build/fixtures/planted.json` from the set root)
(rule, test, result, tool versions, date). About one minute.
(The CK-H4 line needs xdmod 2844966 or later, where the planted commit names "Claude Code".)

### A8. One source for the trace model; no robarm names in xdmod (5.2, 5.6)

```sh
cx run --use tests -- .venv/bin/python -m pytest -q xdmod/curatrix/tests/test_tracemodel.py xdmod/curatrix/tests/test_framework_names.py
grep -rn "robarm" xdmod/curatrix/src | head
```

Expect: all tests pass (`test_no_hard_coded_copy_left`, `test_no_robarm_name_in_curatrix_code`);
the grep shows no robarm names in code.

### A9. Tool pins (5.5)

```sh
cx doctor
```

Expect: exact pins for tools that shape committed output, `>=` minimum versions for git, cmake,
ninja, node, npm, dot; no FAIL.

### A10. The canary chain (5.3; robarm-syseng#8, robarm-ee#6, robarm-me#6, robarm-sw#6 are merged)

```sh
# from the workspace root:
.venv/bin/curatrix work start demo/canary robarm-syseng robarm-ee robarm-me robarm-sw
cd .worktrees/demo/canary
cx check robarm-syseng --stage local
cx check robarm-ee --stage local          # with KiCad: the canary-board project
cx check robarm-me --stage local          # with FreeCAD: canary-part.FCStd
cx docs full
```

Expect: all pass; the full docs show the chain SYS-STH-0001 -> SYS-NEED-0001 -> SYS-REQ-0001 ->
SYS-EL-0001 -> board, part, SW design and test case, all in configuration `canary`.

## Block B: CI, agent material, admin actions, SW tooling (tasks 5.7-5.10)

To be written when block B is done. Planned: a PR's CK-G1 needs-diff against `latest/`
(`curatrix ci base`), CK-H4 on an agent commit without trailer, a stacked PR's sibling resolution,
an `/xd-review-pr` run on a canary PR, the SW-IMPL / SW-TC extraction.

## Block C: spikes (tasks 5.11-5.14)

To be written: the spike notes (`model-spike.md`, `kicad-spike.md`, `freecad-spike.md`) and the
accepted XD-ADRs.

## Block D: domain models and variants (tasks 5.15-5.16)

To be written: `curatrix check robarm-ee` with the EE model, conformance findings, the computed
configuration-to-variant table.

## Block E: EE on the canary (tasks 5.17-5.22)

To be written: `curatrix new pcba`, CK-F1, ERC/DRC with `accepted.yaml`, `curatrix cam robarm-ee`,
the `pcba-<name>` document, the harness.
