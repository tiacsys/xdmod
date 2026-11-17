# Checklist: code and tests

For Python (curatrix, scripts), C and devicetree (robarm-sw), and test code. Background: the repo's
`claude/CLAUDE.md`, `xdmod/claude/CLAUDE.md` for curatrix.

## Correctness
- [ ] The change does what the PR text says; edge cases (empty input, missing file, missing tool)
      give a clear message, not a traceback and not a silent pass.
- [ ] No silent fallback: a check that cannot run says `skip` with the reason, or fails.
- [ ] Every subprocess runs under limits (`limits.run`, `curatrix run`) with a timeout.
- [ ] Paths are relative to the workspace root in output; nothing writes outside `build/<area>/`.
- [ ] No user-global state: no `~/.config`, no global git config, no system packages.

## Tests
- [ ] New behaviour has a test; a new or changed check has a planted error in `PLANTED`
      (`curatrix/tests/test_planted_errors.py`) that asserts the reason, not just "some finding".
- [ ] Tests that need Java, node or Firefox are marked `tools`.
- [ ] Tests do not depend on the caller's environment (`XD_BASE_REF`, `GITHUB_BASE_REF`,
      the current branch) or on the wording of a planted commit message (CK-H4 matches "Claude Code"
      or anthropic.com).
- [ ] Temporary files under `build/xdmod-dev/pytest/` (the conftest default), not `/tmp`.

## Trace in code (robarm-sw)
- [ ] Code units carry `@xdid{SW-IMPL-...}` and implement a SW design element (D77).
- [ ] Test IDs (`SW-TC`) in the ZTEST comment come from the ledger, written by the tool (D80).
- [ ] Trace IDs in the devicetree only on nodes of our own bindings (`robot,joint`), never on
      upstream nodes (D64f).
- [ ] A test that verifies a `SYS-REQ` or `SYS-IF` lives in robarm-integration (D115).
- [ ] `west build` uses `-d build/robarm-sw/...`.

## Style
- [ ] No robarm names in xdmod code (task 5.6).
- [ ] D-numbers in comments are fine as short names; docs use `:need:` references.
- [ ] Docstrings and README rows updated for changed commands and options.
