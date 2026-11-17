# What moved to iteration 2 (Phase 5, exit criterion 6)

Status: **DRAFT, to be agreed by the owner.** Written by the 5.32 agent on 2026-11-17 from the
"Iteration 2 backlog" of `plan.md`, every open point and follow-up of `phase5-decisions.md`, the
options of the author-loop note (5.31) and the end-of-phase findings. Each item: what, where it comes
from, and one line why it is not in iteration 1. The owner strikes, moves back or adds items; the
agreed list then replaces the backlog section of `plan.md`.

Sources: **P** = `plan.md` "Iteration 2 backlog"; **L** = `phase5-decisions.md` (task); **N** =
`author-loop.md` (5.31); **E** = end of Phase 5 (5.32).

## A. Method, trace model and checks

| # | Item | Source | Why not now |
|---|---|---|---|
| A1 | Variant rule V6, `configs` derivation (T1), per-configuration pages | P (D135) | the canary has one configuration in use; nothing to test it on |
| A2 | Warnings for board or assembly variants that no configuration uses | P; L 5.16 (canary `alt` unused) | needs real configurations to be useful |
| A3 | CK-F13: variant names and overrides equal across EE model, `.kicad_pro`, `.kicad_sch`, `.kicad_pcb`; `Setting` per variant | L 5.16 | not built; CK-B8 covers the variant names that matter for the canary |
| A4 | CK-F2: Zephyr devicetree vs the EE board model | L 5.10 | moved behind 5.15, then not built; robarm-sw has no board of its own yet |
| A5 | CK-F18 for real: board inside its space budget (outline, holes, connector positions, STEP fits the box) | L 5.25, 5.28 | the check exists but skips; budget form came late (5.28) |
| A6 | Change impact (CK-G1) per layer of a stacked PR | P | one level of stacking is enough so far |
| A7 | CK-H4 gap: a `commit-msg` hook keyed on `CLAUDECODE` that adds the trailer | L 5.7, 5.8 | an agent commit without the marker passes CK-H4; policy covers it today |
| A8 | A check that warns when a PR's new ledger IDs are already on main | L (process notes) | three ID collisions between parallel PRs; practice "ids fix right before push" works |
| A9 | CK-H6 compares stages too, not only check IDs | L 5.1 | small; revisit if it bites |
| A10 | A failed `summary.json` when checks.yaml is missing (no stale summary left) | L 5.1 | small |
| A11 | CK-E2: read `1e3`, `.5`, `2 × 10^6`; spaces as thousands separators | L 5.4 | CK-E2 is a warning until it ran on real requirements |
| A12 | A check for `satisfy ... by <x>` whose target is not a part | L 5.3 | a modelling pitfall, written into the skill |
| A13 | `checks.py` `BUILTIN` table as dataclasses (P4-17) | L 5.2 | pure refactor; never the right moment during Phase 5 |
| A14 | Run CK-B8's Zephyr board-variant mapping on a real board | L 5.16 | robarm-sw uses nucleo_g474re, nothing to compare |

## B. EE

| # | Item | Source | Why not now |
|---|---|---|---|
| B1 | Completed PCB routing of the product boards | P (5.14, XD-ADR-0144) | iteration 1 stops before routing |
| B2 | A devicetree generated from the KiCad schematic | P (EE-6) | needs A4 first |
| B3 | A Zephyr board for the product board | P | iteration 1 uses the prototype's Nucleo |
| B4 | More than one harness; more than two variants per board or assembly; circuit block diagrams inside a board | P | limits of iteration 1 |
| B5 | BOM totals over all instances in the system | P (EE-8) | needs instance counts across repos |
| B6 | Connectors: buses, pin alternate names | L 5.17/5.18 | the canary has neither |
| B7 | `proto/` projects 1:1 with prototype blocks (a marker for prototype blocks) | L 5.17/5.18 | no prototype project yet |
| B8 | KiCad 3D models in the workspace for the renderings (role `ee3d` / `full`), or a smaller model set | L 5.12, 5.19/5.20 | the EE role has no `kicad-3d` group; renderings show bare boards |
| B9 | Harness route (length is a `SYS-IF` value already) | L 5.28 | scope of the co-design spike |
| B10 | Harness diagram directive reuses `cam.current` (shows only the current commit's output) | L 5.21 | small; the board document already does it |
| B11 | CK-F9's git blame in shallow CI clones | L 5.19/5.20 | untested; acceptance is checked locally today |

## C. ME

| # | Item | Source | Why not now |
|---|---|---|---|
| C1 | Printability checks for printed parts (minimum wall, overhang) | P (ME-7) | needs a slicer or own geometry code |
| C2 | Simulation models from the ME assemblies | P (ME-5) | out of scope for iteration 1 |
| C3 | GLB export of assemblies | P (ME-3) | STEP covers iteration 1 (the Blender path leaves an intermediate `<variant>.scene.glb` beside `cam.json`, not a deliverable) |
| C4 | FreeCAD review report as a Pages preview | P (D108, D135) | iteration 1 keeps it local |
| C5 | Variant rows of FreeCAD configuration tables (presence today by `Configs` on links only) | L 5.23/5.24, 5.25/5.26 | the canary has no configuration-table rows |
| C6 | ME block-diagram view | L 5.23/5.24 | not built |
| C7 | Drawings, exploded view, renderings and parameters for sub-assemblies (today a fixed sentence) | L 5.27 | only the top-level assembly has them in iteration 1 (owner to confirm) |
| C8 | TechDraw title-block fields editable; dimensions on the drawing | L 5.25/5.26 | the TechDraw page export hangs offscreen; plain-Python sheet instead |
| C9 | Versioned output file names; `MaxWidth` of the canary part's version mark (FreeCAD edit) | L 5.26 review | nits |
| C10 | Findings of shared parts shown only in the assembly that uses them | L 5.27 | today every assembly document shows them |
| C11 | `mecam.current` freshness by the `tree_state` hash everywhere; the board line and sub-assembly chapters tested on real data, not only fixtures | L 5.27 | partly fixed in the #61 review; no real sub-assembly yet |
| C12 | Overlapping faces in Blender renderings (z-fighting) | L 5.30 | cosmetic |
| C13 | Better renderings than the z-buffer fallback in CI (or Blender in CI) | L owner decision 5.30 | Blender is not pinnable; CI has the placeholder |
| C14 | Semantic JSON: XLink targets, expressions, named constraints, `Port`, the variant table | L 5.13 | partly done in 5.23-5.27; the rest when reviews need it |

## D. Co-design and board library

| # | Item | Source | Why not now |
|---|---|---|---|
| D1 | EE pushing geometry back through StepUp | P; L 5.28 | the co-design spike decided: no push back; EE asks for a budget change |
| D2 | Keep-outs in the space budget | L 5.28 | scope of the spike |
| D3 | Connector positions pushed into KiCad (today budget values only) | L 5.28 | scope of the spike |
| D4 | A curatrix command for the StepUp push; StepUp pinned in `tools.yaml` and cloned by `curatrix update` | L 5.28 | the manual shows the `curatrix run` line; licence gap open |
| D5 | StepUp licence: a LICENSE file upstream or a written answer (AGPL-3.0 only claimed) | L 5.13, 5.28 | outside our control; recorded |
| D6 | KiCad exclusions on `Edge.Cuts` items survive a push (new UUIDs each push) | L 5.28 | accept such findings in `accepted.yaml` instead |
| D7 | Board library: colours of the STEP import (read as one shape today) | L 5.29 | cosmetic |
| D8 | Bump bot for the board library and a first real library file (needs a board tag) | L 5.29 | no tagged board yet (owner-only) |

## E. CI, workflow and tooling

| # | Item | Source | Why not now |
|---|---|---|---|
| E1 | Technical enforcement of agent limits: GitHub App identity or signed commits | P (D134) | iteration 1 relies on policy (XD-ADR-0123) |
| E2 | Bundles built with the user's bundling tool | P (D24, D38, D40) | the EE and ME CAM output moved to 5.20 / 5.26 |
| E3 | CAM output, renderings and ERC/DRC reports in CI and on Pages | P | iteration 1: local only, placeholder in CI |
| E4 | Docker image with all tools, for CI | P (D19) | not needed for the canary |
| E5 | Downstream full-set job as a required check | L 5.7 | reporting only so far; about 3 minutes per push |
| E6 | CK-G2 against the last baseline | L 5.7 | no baseline exists before 6.14 |
| E7 | The merge helper retargets a stacked child before the parent merges and rebases it after | L 5.14 | a stacked PR was lost once; workflow.md says how to do it by hand |
| E8 | curatrix's own timeout kills the whole process tree (a GUI FreeCAD survived an outer timeout) | L 5.13 | to verify with the systemd-scope and ulimit backends |
| E9 | `.venv/bin` first on `PATH` in agent sessions (workspace `.claude/settings.json`) | L 5.23/5.24 | needs the owner's OK; rule written, not enforced |
| E10 | `curatrix update` exit 1 after "workspace state (.xdmod/)" without a message | L process notes | seen once, not reproduced |
| E11 | `robarm-manifest` `documents.yaml` `base_url` = the Pages URL | L 5.7 | placeholder still there; needed before a full-stage CK-G1 base |
| E12 | Preview TR needs show up in a local full or Pages build on a machine that ran Twister (tagged preview) | L 5.10 | accepted as is; previews never count |
| E13 | zdocs incremental builds miss directive code changes (delete `build/<area>/docs`) | L 5.21 | upstream zdocs; workaround documented |
| E14 | Pilot file order: a repo's own files as one set (forward references) | L 5.3, 5.11 | done for the canary's needs in 5.15; check on larger models |

## F. Speed (author loop, 5.31: no caching now)

| # | Item | Source | Why not now |
|---|---|---|---|
| F1 | Export only what curatrix reads from the Pilot (syseng exports 59 packages, 57 MB) | N | an estimated 15-20 s per syseng Pilot run; first step before any cache |
| F2 | Reuse the Pilot result inside a loop (`check` after `gen model`) | N | 33 s of the 80 s syseng loop; a cache key that misses an input gives a stale pass |
| F3 | **zdocs: Sphinx runs serialised through Ninja's console pool (`USES_TERMINAL`)** | N; E (issue draft `issue-drafts/zdocs-console-pool.md`, not posted, D124) | `docs full` 70 s of serial Sphinx runs, 15 of 16 threads idle; upstream change |
| F4 | Skip CK-A6 in `check` when `curatrix docs` just built the same tree | N | 5-75 s per repo; needs a staleness key over the whole docs input |

## G. Documents and others

| # | Item | Source | Why not now |
|---|---|---|---|
| G1 | Linked PDF document set | P | HTML only in iteration 1 |
| G2 | Layout keeping in drawio | P (D2) | views are regenerated |
| G3 | Document control | P (D33) | not needed before releases |
| G4 | SW architecture as a SysML sub-model in robarm-sw | P (D76) | SW-ARCH as rst needs in iteration 1 |
| G5 | The XDMOD self-model with diagrams in the manual (xdmod#25) | L owner instructions | PR open, set removed; not part of Phase 5 |

## Not on this list (fixed in Phase 5)

- `curatrix update` did not move the manifest repo, and ran old code after `west update` moved xdmod:
  fix proposed in xdmod#64 (`fix/update-manifest`, task 5.32), not yet merged at the time of writing.
  If #64 is not merged, both go back on the list (E).
- Skeleton document names unique per assembly (`<name>-skeleton.FCStd`, document `<name>_skeleton`):
  done in 5.23/5.24 (XD-ADR-0146).
- The doc inconsistencies `build/<branch>/` vs `build/wt-<branch>/` and the stale `curatrix work`
  note: fixed by the manual PR of task 5.32.
