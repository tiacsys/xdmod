# Consistency checks (task 3.6)

Status: **AGREED 2026-11-14** (review answers → D98–D101). Collects every check decided so far: D38, D46, D47, D56, D60, D63, D64, D71, D75, D78, D83, D86–D89 (`../decisions.md`),
rules R1–R7 in `trace-model.md` §4, `id-scheme.md` §6, `views.md` §6, and the spike's lessons (`../notes/spike.md` §9).

## 1. Where checks run

| Stage | Who runs it | Scope | CAD content | Purpose |
|---|---|---|---|---|
| **local** | person or agent, one command per repo from the workspace root (D46, D67), under the limits of D71 (applied by curatrix) | the repo + its upstream docs (D35) | **yes** (KiCad, FreeCAD installed locally) | full feedback before pushing |
| **pre-commit** | git hooks, installed by the bootstrap in every active repo (D100); fast, staged files only | changed files | no | normalizers, ID placeholders, formatting |
| **PR CI** | GitHub Actions per repo (D47, D56) | the repo + siblings on the same branch name (D52) | **no** | gate for merging |
| **full set** | bump-bot job in robarm-manifest (D89) | all repos at the new pins | no | cross-repo rules |
| **baseline gate** | person, locally, before tagging `baseline/vX.Y.Z` | all repos, full checkout | **yes** | release quality |

Check IDs use the prefix `CK-` (e.g. `CK-D4`) so that they can't be confused with decisions, review findings or variant rules. They become `XD-CHECK` needs later (D121).

**Level** means what a finding does: **error** fails the stage, **warning** is reported but does not fail, **report** adds a summary to the PR.

## 2. Check catalogue

### CK-A. Need structure (sphinx-needs schema, strict build)

| # | Check | Stages | Level |
|---|---|---|---|
| CK-A1 | Link written on the wrong side, to an unknown ID, or to a wrong target type (link types declared per need type, D64h) | local, PR, full | error |
| CK-A2 | Required links ("Min" in the link table) and required fields present; `status`, `layer`, `category`, `verification_scope` from their enums; `configs`/`config` hold valid `SYS-CFG` IDs | local, PR, full | error |
| CK-A3 | ID matches the regex and its kind matches the need type (D78) | local, PR, full | error |
| ~~CK-A4~~ | No orphans (R3). Retired 2026-11-17: the schema rule of `needs_config.toml` enforces it in CK-A6 (task 5.2) | — | — |
| ~~CK-A5~~ | HIL test results carry `firmware_sha256` and SHAs (R5, D60). Retired 2026-11-17: schema rule, CK-A6 (task 5.2) | — | — |
| CK-A6 | Every doc builds strict (`-W --keep-going`, every doc reports, D64c); `doccheck` passes | local, PR, full | error |

### CK-B. Graph rules (own check in xdmod, because sphinx-needs skips external needs)

| # | Check | Stages | Level |
|---|---|---|---|
| CK-B1 | Every `SYS-REQ` is refined or satisfied (R1) | full, baseline | error |
| CK-B2 | Every requirement has a `verifies` link (R2) | full, baseline | warning in iteration 1; error at the baseline gate from iteration 2 (D99) |
| CK-B3 | Links to `retired` needs (R4, D75) | local, PR, full: **warning**; baseline: **error** | grace until baseline |
| CK-B4 | Variant rules F1–F2, V1–V6, T1–T3 (`curatrix check variants`, D105) | local, PR, full | error |
| CK-B5 | No duplicate IDs across all repos | full, baseline | error |
| CK-B6 | Stale evidence: `TR` whose SHAs don't match the pins or the baseline (R5a, D131) | full: report; baseline: doesn't count | report |
| CK-B7 | Tombstones: deleted generated needs without retiring first get a tombstone; tombstones older than the last baseline are removed (D130) | local, PR | warning |

### CK-C. IDs and ledger (`id-scheme.md` §6)

| # | Check | Stages | Level |
|---|---|---|---|
| CK-C1 | No placeholder IDs (`…-NEW-…`) | pre-commit (warning), PR (error) | error on PR |
| CK-C2 | Every ID in the sources is ≤ the ledger's number for its kind | local, PR | error |

### CK-D. Generated and committed files ("generate, commit, check", spike lesson 2)

| # | Check | Stages | Level |
|---|---|---|---|
| CK-D1 | SysML stubs (`concern`, `requirement`, stakeholder `part`) match the needs, including value attributes (D42, D83) | local, PR | error |
| CK-D2 | `model-needs.json` matches the model (needs the Pilot / Java) | local, PR (syseng only) | error |
| CK-D3 | drawio views (`.drawio.svg`) match the model in **content**, not geometry; uncompressed; geometry sane; picture fresh (hash) (D38, D64a, D96) | local, PR | error |
| CK-D4 | Committed CAD-derived needs (`generated/cad-needs.json`) match the CAD files (KiCad netlist fields, FreeCAD `Document.xml`) (D110) | local, PR (plain-Python readers of the trace fields, no CAD tools; xdmod#11), baseline | error |
| CK-D5 | `generated/provenance.json` records the tool versions that made the generated files; mismatch with `tools.yaml` | local, PR, full: warning; baseline: error (xdmod#12) |

### CK-E. Model

| # | Check | Stages | Level |
|---|---|---|---|
| CK-E1 | The Pilot parses and resolves the model with 0 errors (marker line, since jshell's exit code is unreliable) | local, PR (syseng) | error |
| CK-E2 | Requirement value fields agree with the EARS sentence (number and unit in the text match `max`/`unit`, D83) | local, PR | error |
| CK-E3 | EARS pattern: the sentence matches its `ears` field | local, PR | warning |

### CK-F. Domain consistency against syseng interfaces (`SYS-IF`): checked, not generated

| # | Check | Stages | Level |
|---|---|---|---|
| CK-F1 | KiCad netlist matches the pin maps of the interfaces (spike: working check) | local, baseline | error |
| CK-F2 | Zephyr devicetree matches the model (pins, buses, channels, `trace-id` in our own binding, D64f) | local, PR (robarm-sw CI builds the firmware with the Zephyr SDK, D101) | error |
| CK-F5 | Firmware builds for `nucleo_g474re`; unit tests pass on `native_sim` (Twister) | local, PR (robarm-sw, D101) | error |
| CK-F3 | FreeCAD spreadsheet parameters match model attributes (link lengths, servo envelope) | local, baseline | error |
| CK-F4 | KiCad ERC passes; FreeCAD documents recompute without errors | local, baseline | error |

### CK-G. Change and suspect links

| # | Check | Stages | Level |
|---|---|---|---|
| CK-G1 | `needs-diff` against the target branch: changed, removed and transitively affected needs, as a PR comment | PR, full | report |
| CK-G2 | Suspect links (R7): affirmatrix `graph status` once adapted (D59); until then, `needs-diff` lists links whose targets changed | full: report; baseline: error | gate before a baseline |

### CK-H. Hygiene

| # | Check | Stages | Level |
|---|---|---|---|
| CK-H1 | `.FCStd` stored uncompressed (D63); drawio uncompressed | pre-commit, PR | error |
| CK-H2 | No build output inside repos (D46: outputs go to `build/<area>/`) | PR | error |
| CK-H3 | `requirements.txt` / `tools.yaml` pins exist for every tool a repo uses | PR | warning |
| CK-H4 | Commit trailers on agent commits (D51) | PR | warning |

## 3. The check runner

xdmod has **one tool, `curatrix`**, with subcommands (D98): `check`, `gen` (stubs, model needs, view JSON), `ids` (ledger), `views` (drawio + SVG), and later `bootstrap` and `launch` (3.13). The check runner is called the same way for every repo and stage:

```
curatrix check <repo> [--stage local|pr|full|baseline] [--no-cad] [--only A,B] [--json]
```

- It knows each repo's checks from a small `checks.yaml` in the repo, e.g. which docs to build and which generated files to verify.
- It runs every tool under per-tool limits (D71) from `limits.yaml`. On GitHub runners, which have no systemd user scope, it falls back to `timeout` plus `ulimit -v` (address-space limit).
- It writes all output to `build/<area>/checks/` and a summary JSON for agents and for CI comments.
- It prints the exact command to reproduce each failure.
- `--stage pr --no-cad` is what GitHub CI runs (D56). robarm-sw's CI also builds the firmware (D101). The baseline gate runs `--stage baseline` with CAD content.

## 4. Answered review questions (2026-11-14)

1. **Tooling:** one tool with subcommands, named **`curatrix`** ("she who takes care of, curates") (D98).
2. **B2 coverage:** a warning in iteration 1; an error at the baseline gate from iteration 2 (D99).
3. **Pre-commit hooks:** installed by the bootstrap (D100).
4. **Devicetree check in CI:** yes. robarm-sw CI builds the firmware with the Zephyr SDK and runs F2 and the `native_sim` unit tests (D101).
