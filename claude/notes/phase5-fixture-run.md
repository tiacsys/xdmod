# Phase 5: the recorded local fixture run (exit criterion 2)

Exit criterion 2 of Phase 5: every rule in `claude/framework/checks.md` has a planted error that
fails; plain-Python rules in the CI fixture (XD-T1), tool-backed rules in a recorded local run of
`curatrix fixtures`, whose record is `build/fixtures/planted.json` (rule, test, result, tool versions,
date) and whose summary goes into the Phase 5 review. Because `build/` is emptied before the owner's
review, the record is copied here.

## Summary

**`curatrix fixtures` passed on 2026-11-17T19:23:12+00:00** ("FIXTURES PASSED: every check failed on its planted
error"): 62 rows, **56 checks plus the control build, every row `passed`**
(84 pytest tests, 64.8 s; the tool-marked tests ran too, nothing skipped). Run by the 5.32 agent in
the main workspace at xdmod 83578e4 (= `origin/main`), with KiCad, FreeCAD, the Pilot, elkjs and
Firefox through curatrix.

"passed" means the test passed: the check reported its planted error (and, where the test has one,
the clean case stayed clean). Exception: CK-F18, whose test asserts a skip (see below). The `control` row is the clean strict build of the sample project.

User configuration: no file under `~/.config/kicad`, `~/.config/FreeCAD`, `~/.local/share/kicad`,
`~/.cache/kicad` or `~/.config/blender` changed during the run (the newest, `kicad_common.json`, is
from 2026-11-17 06:29 local time, before the run).

## Tool versions

| Tool | Version |
|---|---|
| FreeCADCmd | 1.1.4 |
| drawio-viewer | 32.6.1 |
| elkjs | 0.12.1 |
| firefox | 160.0 |
| jdk | 21.0.13+9 |
| kicad-cli | 10.0.8 |
| sysml-pilot | 0.63.1 |

Blender is not in the record: no check needs it (it renders only).

## Rules without a planted error of their own

Every built-in check of the catalogue (`curatrix/src/curatrix/data/checks.yaml`) that is not retired
is in the run; `test_every_check_has_a_planted_error` enforces that. Rules of `checks.md` that are not
built-in checks:

| Rule | Status |
|---|---|
| CK-A2 | required links and fields: enforced by the sphinx-needs schema inside CK-A6, so its planted error is CK-A6's |
| CK-A4, CK-A5 | retired (task 5.2): the schema of `needs_config.toml` enforces them in CK-A6 |
| CK-F2 | devicetree vs the EE board model: not built (moved behind 5.15, then to iteration 2) |
| CK-F5 (a, b, c) | firmware build, Twister, preview TR needs: repo commands of robarm-sw (`checks.yaml` `commands`), not built-in; their failure is the command's exit code, no planted error in the xdmod fixture |
| CK-F13 | variant names and overrides across the EE model and KiCad files: not built (iteration 2) |
| CK-F18 | board inside its space budget: the check exists, but it is always a skip with its reason until the budget is checked, so its planted test `test_f18_space_budget` asserts the skip, not a finding (iteration 2 list, A5) |

## The record

| Check | Test | Result |
|---|---|---|
| CK-A1 | `curatrix/tests/test_planted_errors.py::test_a1_unknown_link` | passed |
| CK-A3 | `curatrix/tests/test_planted_errors.py::test_a3_id_does_not_match_its_type` | passed |
| CK-A6 | `curatrix/tests/test_needs_config.py::test_planted_error_fails` | passed |
| CK-B1 | `curatrix/tests/test_planted_errors.py::test_b1_requirement_not_refined` | passed |
| CK-B2 | `curatrix/tests/test_planted_errors.py::test_b2_requirement_not_verified` | passed |
| CK-B3 | `curatrix/tests/test_planted_errors.py::test_b3_link_to_retired` | passed |
| CK-B4 | `curatrix/tests/test_variants.py::test_planted_errors` | passed |
| CK-B5 | `curatrix/tests/test_planted_errors.py::test_b5_duplicate_id` | passed |
| CK-B6 | `curatrix/tests/test_planted_errors.py::test_b6_stale_evidence` | passed |
| CK-B7 | `curatrix/tests/test_planted_errors.py::test_b7_tombstone` | passed |
| CK-B8 | `curatrix/tests/test_planted_errors.py::test_b8_variants_across_levels` | passed |
| CK-C1 | `curatrix/tests/test_planted_errors.py::test_c1_placeholder` | passed |
| CK-C2 | `curatrix/tests/test_planted_errors.py::test_c2_id_not_in_ledger` | passed |
| CK-D1 | `curatrix/tests/test_planted_errors.py::test_d1_stale_stubs` | passed |
| CK-D10 | `curatrix/tests/test_bom.py::test_d10_cam_output_of_the_current_commit` | passed |
| CK-D10 | `curatrix/tests/test_asmdoc.py::test_d10_assembly_output` | passed |
| CK-D2 | `curatrix/tests/test_planted_errors.py::test_d2_stale_model_json` | passed |
| CK-D3 | `curatrix/tests/test_views.py::test_content_change_and_stale_picture` | passed |
| CK-D4 | `curatrix/tests/test_cli.py::test_gen_and_check_cad_needs` | passed |
| CK-D5 | `curatrix/tests/test_provenance.py::test_made_with_another_version_is_reported` | passed |
| CK-D6 | `curatrix/tests/test_planted_errors.py::test_d6_code_changed_after_gen` | passed |
| CK-D7 | `curatrix/tests/test_connectors.py::test_d7_fresh` | passed |
| CK-D8 | `curatrix/tests/test_connectors.py::test_d8_against_kicad_cli` | passed |
| CK-D9 | `curatrix/tests/test_bom.py::test_d9_against_kicad_cli` | passed |
| CK-E1 | `curatrix/tests/test_planted_errors.py::test_e1_pilot_error_through_the_check` | passed |
| CK-E2 | `curatrix/tests/test_planted_errors.py::test_e2_value_not_in_sentence` | passed |
| CK-E3 | `curatrix/tests/test_planted_errors.py::test_e3_wrong_ears_pattern` | passed |
| CK-E4 | `curatrix/tests/test_planted_errors.py::test_e4_conformance` | passed |
| CK-F1 | `curatrix/tests/test_connectors.py::test_f1_against_the_model` | passed |
| CK-F1 | `curatrix/tests/test_harness.py::test_f1_harness_ends` | passed |
| CK-F10 | `curatrix/tests/test_cam.py::test_f10_jobset` | passed |
| CK-F11 | `curatrix/tests/test_cam.py::test_f11_version_variable` | passed |
| CK-F12 | `curatrix/tests/test_bom.py::test_f12_bom_fields` | passed |
| CK-F12 | `curatrix/tests/test_asmdoc.py::test_f12_me_bom_fields` | passed |
| CK-F14 | `curatrix/tests/test_meassemblies.py::test_f14_one_to_one` | passed |
| CK-F15 | `curatrix/tests/test_meassemblies.py::test_f15_link_counts` | passed |
| CK-F16 | `curatrix/tests/test_mechecks.py::test_me_checks_freecad` | passed |
| CK-F17 | `curatrix/tests/test_mechecks.py::test_me_checks_freecad` | passed |
| CK-F17 | `curatrix/tests/test_mechecks.py::test_f17_collisions_and_acceptance` | passed |
| CK-F18 | `curatrix/tests/test_mechecks.py::test_f18_space_budget` | passed |
| CK-F19 | `curatrix/tests/test_mecam.py::test_f19_version_face` | passed |
| CK-F20 | `curatrix/tests/test_boardlib.py::test_f20_board_library` | passed |
| CK-F21 | `curatrix/tests/test_boardlib.py::test_f21_newer_board_version` | passed |
| CK-F3 | `curatrix/tests/test_meparams.py::test_f3_freecad_params` | passed |
| CK-F4a | `curatrix/tests/test_ercdrc.py::test_f4a_erc` | passed |
| CK-F4b | `curatrix/tests/test_ercdrc.py::test_f4b_unrouted_board` | passed |
| CK-F4c | `curatrix/tests/test_mechecks.py::test_me_checks_freecad` | passed |
| CK-F6 | `curatrix/tests/test_eeprojects.py::test_f6_folder_rule` | passed |
| CK-F7 | `curatrix/tests/test_eeprojects.py::test_f7_one_to_one` | passed |
| CK-F7 | `curatrix/tests/test_harness.py::test_f7_cables_one_to_one` | passed |
| CK-F8 | `curatrix/tests/test_ercdrc.py::test_f8_severities` | passed |
| CK-F9 | `curatrix/tests/test_ercdrc.py::test_f9_acceptance` | passed |
| CK-G1 | `curatrix/tests/test_planted_errors.py::test_g1_g2_changed_need_makes_links_suspect` | passed |
| CK-G2 | `curatrix/tests/test_planted_errors.py::test_g1_g2_changed_need_makes_links_suspect` | passed |
| CK-H1 | `curatrix/tests/test_planted_errors.py::test_h1_compressed_fcstd` | passed |
| CK-H2 | `curatrix/tests/test_planted_errors.py::test_h2_build_output` | passed |
| CK-H3 | `curatrix/tests/test_planted_errors.py::test_h3_unpinned_requirement` | passed |
| CK-H4 | `curatrix/tests/test_planted_errors.py::test_h4_missing_trailer` | passed |
| CK-H5 | `curatrix/tests/test_planted_errors.py::test_h5_bootstrap_drift` | passed |
| CK-H6 | `curatrix/tests/test_check_runner.py::test_expect_list` | passed |
| CK-H7 | `curatrix/tests/test_check_runner.py::test_pr_size_counts_hand_written_lines_only` | passed |
| control | `curatrix/tests/test_needs_config.py::test_sample_builds_strict` | passed |
