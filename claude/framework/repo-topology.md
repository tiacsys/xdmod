# Repo topology, west manifest and cross-repo workflow (task 3.4)

Status: **AGREED 2026-11-14** (review answers → D89–D93). Built on D7, D14, D25, D35, D39, D48–D52, D54, D56, D60, D61, D66–D70, D73, D84, D86–D88 (`../decisions.md`),
`../research/zephyr-west.md` and the spike (`../notes/spike.md` §7).

## 1. Repos

| Repo | Owner / remote | Role | Pinned by |
|---|---|---|---|
| `robarm-manifest` | tiacsys | The west manifest (self). It builds the full linked doc set, runs the bump PRs, and holds baseline tags | — (it is the pin) |
| `xdmod` | tiacsys | The framework: methods, tools (`-trix`), shared needs config, launch `CLAUDE.md`, skills | SHA |
| `robarm-syseng` | tiacsys | Needs, requirements, SysML model, views | SHA |
| `robarm-ee` | tiacsys | EE requirements, KiCad projects (PCBAs, prototype wiring), EE tests | SHA |
| `robarm-me` | tiacsys | ME requirements, FreeCAD parts and assemblies, ME tests | SHA |
| `robarm-sw` | tiacsys | SW requirements, design, Zephyr application, SW tests | SHA |
| `robarm-integration` | tiacsys | System and integration tests, HIL setups, evidence branch | SHA |
| `zdocs` | tiacsys | Doc engine (Zephyr module) | SHA |
| `affirmatrix` | tiacsys | Suspect-link tool | SHA |
| `sysmod-sysmlv2` | mbse4u | SYSMOD v5 library (D84) | SHA |
| `PLEML` | MBSE4U | Variant library, SysML v2 successor of VAMOS (D102) | SHA |
| `zephyr` + modules | zephyrproject-rtos | RTOS. All roles get the full tree for now (D87); HAL modules come in through an allowlist | tag `v4.4.2` |
| `kicad-symbols`, `kicad-footprints`, `kicad-packages3D`, `kicad-templates`, `kicad-library-utils` | tiacsys (forks) | EE component libraries (D88) | SHA |
| `FreeCAD-library` | FreeCAD | ME parts library (D88) | SHA |

The manifest is the **only** place that pins revisions (D39). No repo carries its own `west.yml` for imports.

## 2. Workspace layout (one topdir at the root, D68)

```
<workspace>/                     west topdir; every command runs here (D67)
  .west/                         west config (incl. manifest.group-filter for the role)
  .venv/                         workspace venv (tools, D19); built from the repos' requirements.txt / tools.yaml
  build/<area>/                  all build output
  CLAUDE.md                      launch file, copied from xdmod by the bootstrap (D69)
  robarm-manifest/               manifest repo (self)
  xdmod/
  robarm-syseng/  robarm-ee/  robarm-me/  robarm-sw/  robarm-integration/
  tools/zdocs/  tools/affirmatrix/
  libs/sysmod-sysmlv2/  libs/pleml/
  libs/kicad/symbols/  libs/kicad/footprints/  libs/kicad/packages3D/  libs/kicad/templates/  libs/kicad/library-utils/
  libs/freecad/
  zephyr/  modules/…             Zephyr and its allowlisted modules (west default paths)
```

The design repos sit at the top level because people and agents work in them. Dependencies go under `tools/` and `libs/`. (The paths `tools/zdocs` and `tools/affirmatrix` match the safety repo.)

## 3. Manifest structure (submanifests, D86)

```yaml
# robarm-manifest/west.yml
manifest:
  version: "1.2"
  self:
    path: robarm-manifest
    import: submanifests            # every *.yml in submanifests/, in name order
  group-filter: [-ee, -me, -sw, -integration, -kicad-3d, -freecad-parts]   # minimal by default (D93): roles switch groups on
```

```yaml
# robarm-manifest/submanifests/00-framework.yml        (no groups: always active)
manifest:
  remotes:
    - name: tiacsys
      url-base: https://github.com/tiacsys
  projects:
    - { name: xdmod,       remote: tiacsys, revision: <sha> }
    - { name: zdocs,       remote: tiacsys, revision: <sha>, path: tools/zdocs }
    - { name: affirmatrix, remote: tiacsys, revision: <sha>, path: tools/affirmatrix }
    - { name: PLEML, url: https://github.com/MBSE4U/PLEML, revision: <sha>, path: libs/pleml }
    - { name: robarm-syseng, remote: tiacsys, revision: <sha> }      # upstream of every domain (D35)
    - name: sysmod-sysmlv2
      url: https://github.com/mbse4u/sysmod-sysmlv2
      revision: <sha>
      path: libs/sysmod-sysmlv2
```

| File | Projects | Groups |
|---|---|---|
| `00-framework.yml` | xdmod, zdocs, affirmatrix, robarm-syseng, sysmod-sysmlv2, PLEML (`libs/pleml`) | none: always active |
| `10-zephyr.yml` | zephyr (`import:` with `name-allowlist: [cmsis_6, hal_stm32]`) | none: always active (D87) |
| `20-ee.yml` | robarm-ee, kicad-symbols, kicad-footprints, kicad-templates, kicad-library-utils | `ee` |
|  | kicad-packages3D (`clone-depth: 1`) | `kicad-3d` only |
| `30-me.yml` | robarm-me | `me` |
|  | FreeCAD-library (`clone-depth: 1`) | `freecad-parts` only |
| `40-sw.yml` | robarm-sw | `sw` |
| `50-integration.yml` | robarm-integration | `integration` |

The syseng repo has no group, because every role needs it as its upstream (D35). It is placed in `00-framework.yml` for that reason.

## 4. Roles

The manifest default is **minimal** (D93): framework, syseng and Zephyr only. A role switches groups on. The bootstrap (3.13) sets the role once with `west config manifest.group-filter <filter>`, then runs `west update`.

| Role | Group filter (added to the manifest default) | Gets |
|---|---|---|
| (none) / syseng | — | framework, syseng, SYSMOD library, Zephyr |
| ee | `+ee` | + robarm-ee, KiCad libraries (no 3D models) |
| ee + 3D | `+ee,+kicad-3d` | + KiCad 3D models |
| me | `+me,+freecad-parts,+ee` | + robarm-me, FreeCAD parts, robarm-ee and the KiCad libraries (StepUp push, XD-ADR-0141) |
| sw | `+sw,+ee` | + robarm-sw, robarm-ee (board pin maps, XD-ADR-0131) |
| integration | `+ee,+me,+sw,+integration` | everything except the big libraries (D90) |
| full (local, baseline) | `+ee,+me,+sw,+integration,+kicad-3d,+freecad-parts` | everything |
| CI full set (bump job) | same as integration | everything except the big libraries: CI builds without CAD content (D56) |

West rule: a project is active if **any** of its groups is enabled (it is inactive only when all its groups are disabled). So the big libraries carry **only** their own group (`kicad-3d`, `freecad-parts`); otherwise the plain `ee`/`me` roles would fetch them. Fixed after the Stage 2 manifest work found the error.

## 5. Pinning

- Our repos and the libraries are pinned **by SHA**. Zephyr is pinned **by tag**.
- The bump bot (§7) moves the SHAs. People don't edit them by hand, except for libraries and Zephyr upgrades, which are deliberate PRs.
- A baseline is a tag `baseline/vX.Y.Z` on robarm-manifest (D40, D54). Each robarm repo also gets its own SemVer tag at release time.

## 6. Working locally

- **Bootstrap** (3.13): clone robarm-manifest, then run `west init -l robarm-manifest`, set the role's group filter, run `west update`, build `.venv` from the active repos' package lists, and copy the launch `CLAUDE.md` from xdmod.
- **On a branch:** `west update` would move a project back to its pinned SHA (detached HEAD). While working on branches, use `west update -k` (keep descendants), or update only the projects you aren't working on (`west update <projects>`). The spike found this; the bootstrap documents it.
- **Checks:** one command per repo from the root (D46). The full set builds through robarm-manifest.

## 7. Cross-repo change workflow (D50, D52, D60, D61)

1. **Branch.** A change gets one branch name. The same name is used in every repo it touches, e.g. `feat/sys-req-0042-latency`.
2. **PR per repo.** Each touched repo gets a PR. All PR texts list the sibling PRs and end with the provenance trailer (D72).
3. **PR CI** (per repo, without CAD content, D56):
   - Check out robarm-manifest `main` and run `west update` with the repo's role filter (for robarm-syseng and xdmod: the integration role, so that every downstream repo is checked too).
   - For every active robarm repo and xdmod, resolve the revision in this order (D127): (1) a branch with the PR's branch name, if the remote has one; (2) the repo's `main`, if the manifest pin is an ancestor of it (so changes merged upstream but not yet bumped are seen); (3) the manifest pin.
   - Check out the PR's own repo at the PR head.
   - Run the repo's checks and the docs build (strict, D64c).
4. **Merge order:** upstream first. That is syseng, then ee / me / sw, then integration. xdmod changes merge before the repos that use them. Every PR is rebase-merged (D50).
5. **Bump bot** (D61, D89): a **scheduled workflow in robarm-manifest** (e.g. every 30 minutes, plus a manual trigger). It needs no extra token.
   - It compares the `main` of xdmod and each robarm repo with the pins in the submanifests.
   - If any have moved, it opens or updates **one** bump PR, e.g. "bump: robarm-ee → <sha>, xdmod → <sha>", using its own `GITHUB_TOKEN`.
   - A PR opened with `GITHUB_TOKEN` doesn't trigger CI by itself. So the same job builds the **full set** (all groups, without CAD content) and reports the result as a check and a comment on the PR, with the provenance trailer (D72).
   - The user reviews and merges. Several bumps collect in the one open bump PR.
6. **Evidence and affirmations** are recorded only against commits on `main` or baseline tags (D60). A HIL run on a PR branch is a preview.
7. **Baseline:**
   - Merge the bump PR.
   - Run the baseline gates: no links to retired needs (D75), no open suspect links (R7), and a full local build with CAD content (D56).
   - Tag `baseline/vX.Y.Z` and create the GitHub release.

## 8. Answered review questions (2026-11-14)

1. **Bump bot:** a scheduled poll in robarm-manifest with its own `GITHUB_TOKEN`. No extra secret is needed. The job builds the full set itself (D89).
2. **Integration role:** everything except the big libraries (D90).
3. **Paths:** dependencies under `tools/` and `libs/` (D91).
4. **xdmod pin:** by SHA now. SemVer tags come later, once xdmod has a stable release for other workspaces (D92).
5. **Default:** minimal. Without a role, a workspace gets framework, syseng and Zephyr (D93).
