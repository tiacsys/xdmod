# Phase 2 — thin spike: notes

Date: 2026-11-14. Status: tasks 2.1, 2.2, 2.3 done; this file is 2.4.
All repos are local git repos. Nothing was pushed. Commits end with the `Co-Authored-By` line.

## 1. Result in one paragraph

The whole chain works end to end on a tiny example, with strict builds:
stakeholder need → system requirement (EARS) → SysML part (`satisfy` through a generated stub)
→ KiCad symbol (hidden field) → test result (JUnit from a netlist check). The full linked set
in the manifest repo shows a trace report with 6 chains and 0 gaps, and a graph. A generated
drawio view of the model is shown inline in Sphinx, and its parts link to their needs.
A wrong-direction link and a dangling link both fail the build. The change scenario shows
what each layer reports, and our `needs_diff.py` lists the suspect links transitively.
affirmatrix works for the `refines` links only.

## 2. What I built

```
/home/tobias/z/wrk/ws-syseng/
├── .venv/                      one venv for everything (Python 3.14.10), tools in .venv/opt/
├── build/spike/                ALL build output (never inside the repos)
└── spike/                      west topdir (.west/ is here, see §7)
    ├── robarm-manifest/        west.yml (all projects pinned by SHA), full-set docs, ./check,
    │   ├── docs/index-set/       start page + trace-report.rst
    │   └── scenarios/            negative-tests.sh, change-scenario.sh, affirmatrix-trial.sh
    ├── mbse-framework/         = the future `xdmod` repo (not renamed, to save time)
    │   ├── requirements.txt      pinned pip set (+ requirements.in)
    │   ├── tools.yaml            non-pip tools: name, version, URL, sha256, location
    │   ├── needs/needs_config.toml   need types + link types PER TYPE (D36, D64h) + schema rule
    │   ├── cmake/mbse-docs.cmake     shared zdocs consumer block, strict by default
    │   ├── sphinx_ext/           mbse_conf.py (conf helper), mbse_sphinx.py (sysml-view, tracechain)
    │   └── tools/                install-tools.sh, env.sh, sysml_check.py (Pilot via jshell),
    │                             gen_stubs.py, sysml_tools.py (needs + drawio), elk_layout.mjs,
    │                             export_svg.mjs, kicad_to_needs.py, check_pinmap.py,
    │                             needs_diff.py, open-kicad.sh
    ├── robarm-syseng/          ./check, requirements.txt, tools.yaml
    │   ├── docs/se-req/          STKN-MIRROR, SYSREQ-FOLLOW-LATENCY, SYSREQ-SERVO-PWM
    │   ├── docs/se-arch/         inline view + model elements (needimport)
    │   ├── model/RobArm.sysml    4 parts, 3 connections, 2 satisfy
    │   ├── model/TraceMeta.sysml
    │   ├── model/generated/      NeedStubs.sysml, model-needs.json   (generated, committed, checked)
    │   ├── views/joint-system.drawio                                  (generated, committed, checked)
    │   └── interfaces/joint-servo-pinmap.json   peer interface EE/SW (D36)
    ├── robarm-ee/              ./check [gen], requirements.txt, tools.yaml
    │   ├── kicad/joint.kicad_sch J1, J2 with hidden TraceID + Realizes fields
    │   ├── tools/make_joint_sch.py   writes the schematic (no KiCad libraries are installed)
    │   └── docs/ee-joint, ee-test, documents.yaml (also builds se-req, se-arch locally, D35)
    ├── zdocs/                  clone of github.com/tiacsys/zdocs at f9b701c (= GitHub HEAD)
    └── zephyr/                 15 MB doc-build subset of ws-t/zephyr (v4.4.2-103), own git repo
```

Need types (provisional IDs, D17 is Phase 3): `stkn`, `sysreq` (`refines`→stkn),
`sysel` (`satisfies`→sysreq), `eecomp` (`realizes`→sysel), `testcase` (`verifies`→eecomp|sysreq).
There is no global link table. Each link is declared only on the type that holds it.

## 3. Commands (all from the workspace root `/home/tobias/z/wrk/ws-syseng`; git is the only exception)

Every tool runs under `.venv/bin/xd-limit` (D71). The check scripts do this themselves:
docs builds 4G/15m, Pilot 4G/10m (jshell `-J-Xmx1g`, engine `-R-Xmx3g`), kicad-cli 2G/5m,
headless Firefox SVG export 2G/5m, ELK layout 1G/2m, small Python scripts 1G/5m.

```sh
# 1. install (venv, pip pins, JDK 21, Pilot 0.63.1, elkjs, puppeteer-core, drawio viewer)
.venv/bin/xd-limit -m 4G -t 30m -- spike/mbse-framework/tools/install-tools.sh   # optional: TOOL_CACHE=<dir>
#    (on a machine without .venv/xd-limit yet, run the script directly once)
# 2. workspace (already done; west topdir is spike/)
(cd spike && ../.venv/bin/west update -k)               # -k keeps local branches that contain the pin
# 3. checks (each one writes to build/spike/<repo>/)
spike/robarm-syseng/check            # Pilot check + JSON, generated files vs model, docs, stubs vs needs
spike/robarm-syseng/check --update   # regenerate model-needs.json, drawio view, stubs (then run again)
spike/robarm-ee/check                # ERC, netlist, SVG, KiCad needs, pin-map JUnit, docs (with syseng docs)
spike/robarm-ee/check gen            # only the generated inputs (used by the full set)
spike/robarm-manifest/check --all    # every repo check, then the full set -> build/spike/full-set/
# 4. scenarios
spike/robarm-manifest/scenarios/negative-tests.sh       # -> build/spike/negative-tests/
spike/robarm-manifest/scenarios/change-scenario.sh      # -> build/spike/change-scenario/
spike/robarm-manifest/scenarios/affirmatrix-trial.sh    # -> build/spike/affirmatrix/ (run after the change scenario)
# GUI
spike/mbse-framework/tools/open-kicad.sh spike/robarm-ee/kicad/joint.kicad_sch
```

`MBSE_BUILD_ROOT` changes the output root (the scenarios use it for one folder per step).

### Files to open

| What | Path |
|---|---|
| Full set start page | `build/spike/full-set/docs/deploy/html/index-set/index.html` |
| Trace report (table + graph) | `build/spike/full-set/docs/deploy/html/index-set/trace-report.html` |
| Inline drawio view (clickable) | `build/spike/full-set/docs/deploy/html/se-arch/index.html` |
| Requirements | `build/spike/full-set/docs/deploy/html/se-req/index.html` |
| Schematic + KiCad needs / test report | `.../html/ee-joint/index.html`, `.../html/ee-test/index.html` |
| Change scenario: impact reports | `build/spike/change-scenario/needs-diff-A-change-and-retire.md`, `needs-diff-B2-removed-model-fixed.md` |
| Change scenario: build logs per step | `build/spike/change-scenario/*.log`, console: `build/spike/change-scenario-console.log` |
| Negative tests | `build/spike/negative-tests-console.log`, `build/spike/negative-tests/*.log` |
| affirmatrix trial | `build/spike/affirmatrix-console.log` |
| Last full check log | `build/spike/full-check.log` |

## 4. What worked

- **zdocs with sphinx-needs 9.2.0** (zdocs pins 8.3.0) and Sphinx 9.1.0 on Python 3.14: no problem.
  Per-type link declarations in the shared TOML work through `ZDOCS_NEEDS_CONFIG`.
- **Strict builds catch link errors.** Wrong direction → `needs.undeclared_for_type`. Dangling →
  `needs.link_outgoing` (and `needs.external_link_outgoing` in every document that imports it).
- **Pilot via jshell**: checks the model and exports JSON (243 elements). `satisfy 'SYSREQ-X' by part`
  works with the stub's short name, so model IDs = need IDs. `frame` from requirement stub to concern
  stub works. A removed stub gives `Couldn't resolve reference`.
- **SysML → needs**: part usages with a short name `<'SYSEL-…'>` become needs; `satisfy` becomes a link.
- **SysML → drawio → SVG**: qualified names as cell IDs, elkjs layout, headless Firefox export, SVG
  inline with `need:<ID>` links rewritten to real URLs by our directive. Content check works.
- **KiCad**: the schematic was written by a script; `kicad-cli` netlist kept the hidden fields;
  the pin-map check writes JUnit; sphinx-test-reports turns `<property name="verifies">` into links
  (a comma list works).
- **D35**: robarm-ee builds se-req and se-arch from the west checkout and links into them.
- **Trace report**: own `tracechain` directive walks back links over all needs (external ones too)
  and shows gaps. `needflow` with Graphviz draws the graph.
- **Change impact**: our `needs_diff.py` (from the research prototype) found all direct and
  transitive suspects and dangling links (see §6).

## 5. What failed or needed a workaround

| Problem | Workaround / note |
|---|---|
| `needs_statuses` is deprecated in 9.2 | `[needs.fields.status] schema.enum` in the TOML |
| JSON schema `not` is not allowed in `validate.network.*.local` | use `enum` of allowed values |
| The rule's `severity = "warning"` was reported as **violation** for a network rule | Strict build fails either way; note for D64e (no real "grace period" under `-W`) |
| `needflow` default engine is PlantUML (not installed): the page shows "PlantUML is not available!" and **the strict build still passes** | `flow_engine = "graphviz"` in the TOML |
| `needflow` warns in zdocs' stage-1 `xref` builder ("only supported for HTML") → `-W` fails | wrap it in `.. only:: html` |
| ninja stops at the first failed doc; with an imported dangling link that is an **innocent upstream doc** (`se-req`) | `cmake --build … -- -k 0` so every doc reports |
| `needimport` paths: zdocs copies only the doc folder; absolute paths do not work (`relfn2path`) | add files via `external_content_contents` (helper `extra_inputs`), then `/path` in the source tree |
| Generated inputs of upstream docs (model needs) must exist downstream (zdocs gap G6) | commit `model-needs.json` (like drawio files, checked against the model) so ee needs no Java |
| jshell exit code is not reliable (`System.exit` kills only the engine; a failing statement drops into the prompt and hangs on stdin) | stdin from `/dev/null`, a marker line `SYSML-RESULT errors=N`, parse it |
| No KiCad symbol libraries installed | the symbol is defined in the script and embedded; ERC shows library-table warnings only |
| `${GIT_REV}` unresolved in ERC | pass `-D GIT_REV=…` to `erc` and `export svg` |
| sphinx-test-reports adds its own `testcase` type | declare `testcase` in the TOML with its links; load the extension in every doc |
| west update moves projects to a detached pin | `west update -k` while developing in place |
| Python bytecode inside repos | `PYTHONDONTWRITEBYTECODE=1` in `env.sh`; `.gitignore` |

## 6. Change scenario (2.3)

Branch `change-scenario` in robarm-syseng (3 commits), main is unchanged.

| Step | Change | What reports it | Result |
|---|---|---|---|
| A | LATENCY text 100 ms → 50 ms; SERVO-PWM `status: retired`; stubs regenerated | schema rule `no-link-to-retired-sysreq` on `SYSEL-SERVO-DRV` (in se-arch, in every repo that builds it) | all 3 checks FAIL. The text change itself fails nothing. |
| B1 | SERVO-PWM removed from rst, stubs regenerated, model not touched | Pilot: `Couldn't resolve reference to Feature 'SYSREQ-SERVO-PWM'`; docs: `link_outgoing` from the committed model-needs | all FAIL |
| B2 | model owner removes the `satisfy`, `--update` | — | all PASS |

`needs_diff.py` (baseline → A): 2 changed needs, 10 SUSPECT links (2 direct, 8 transitive down to
the test results). Baseline → B2: 1 removed, 2 changed, 10 suspects, one marked "link removed since".

Gaps seen:
- After B2, `SYSEL-SERVO-DRV` and `EECMP-J1-SERVO` satisfy nothing, but nothing fails and the trace
  report simply has fewer rows. We need an "orphan" check (each `sysel` with an `eecomp` must satisfy
  something, or a rule per type).
- The text change (A) passes all builds. Only the diff (or affirmatrix) shows it. So suspect-link
  checks must be a separate gate.
- Retiring and removing a requirement needs the model owner in the same change (same branch, D52),
  because the stubs and `model-needs.json` are committed.

affirmatrix (pip-installed from GitHub at `fb3f4dc` into `.venv`): on a merged export of all
documents' needs, the two `Refines` edges went pending → active (after `edge affirm`) →
`directlyOutdated` (LATENCY text) → `vanished` (SERVO-PWM removed). The `retired` status change was
**not** seen (status is not hashed). With all types, it took `sysel`, `eecomp`, `testcase` as plain
"Requirement" nodes and ignored `satisfies`, `realizes`, `verifies`. It needed an absolute `source`
path and one merged `needs.json`. The case store was a scratch git repo in `build/spike/affirmatrix/`.

## 7. One west topdir at the workspace root (decided for the real workspace)

The spike keeps `spike/` as the topdir (moving it was not worth the time). With the topdir at
`/home/tobias/z/wrk/ws-syseng`:
- `.west/` at the root; repos next to `claude/`, `extra/`, `.venv/`, `build/`. west only touches the
  paths listed in `west.yml`, so the other folders are safe, but no project may be named `build`,
  `claude`, `extra` or `.venv`.
- `url-base` in `west.yml` changes (later GitHub anyway).
- `env.sh`: `VENV` and `MBSE_BUILD_ROOT` become `$TOP/.venv` and `$TOP/build/spike` instead of `$TOP/../…`.
- `mbse_conf.build_root()` the same.
- zdocs `doc_dir: ../../robarm-syseng/docs/…` stays the same (repos stay siblings).
- Simpler overall: one root for commands, west, venv and build; the scripts already find the topdir
  by looking for `.west/` upward.

## 8. Timings (this machine, warm caches)

| Step | Time |
|---|---|
| install-tools.sh with cached downloads (JDK 208 MB + Pilot 124 MB not downloaded again) | 5 s |
| pip install of the pinned set (uv) | 5 s |
| `west update` | < 1 s |
| Pilot check + export (JVM start + library + 3 files) | 12–13 s |
| syseng docs (2 docs, incl. one Firefox SVG export) | 8 s |
| ee check (kicad-cli + 4 docs) | 12 s |
| full set (5 docs) | 14 s |
| `robarm-manifest/check --all` from clean | 51 s |
| change scenario (4 full runs + 3 updates) | about 4 min |

Install footprint: `.venv` 726 MB = JDK 347 MB, Pilot 135 MB, Python packages 145 MB, node
(elkjs, puppeteer-core) 41 MB, drawio viewer 4 MB (plus `opt/gh` 55 MB, not from this spike).
Spike repos: Zephyr subset 26 MB (with .git), zdocs 2.5 MB, our repos < 0.5 MB each.

## 9. Input for Phase 3

1. **Link-type table (3.1):** per-type declarations in one TOML work and give good errors. Keep the
   table in the framework repo. Every doc must know all types, also downstream ones (external needs).
   Add rules for orphans (part with no `satisfies`) — the build does not see them today.
2. **Generated-but-committed files** are a pattern: stubs, `model-needs.json`, drawio views. Each has a
   generator and a `--check`. This keeps downstream repos free of Java. Phase 3 should define the
   list and one `--update` flow (stubs need a docs build first, so it is two passes today).
3. **Checks (3.6):** strict build = link structure. Suspect links (text changes) need a separate gate
   (`needs_diff` on PRs, affirmatrix later). A `retired` status fails at once under `-W`; if we want a
   grace period, the rule must be `info` plus a report, or a separate non-strict gate.
4. **One check command per repo** works well with a shared `env.sh`; the full set uses `gen` mode of
   each repo. Every tool call is wrapped in `xd-limit`. Fold this into `xdmod`'s command layer (3.13).
5. **IDs (3.2):** short names in SysML can be the need IDs (`<'SYSEL-…'>`), and `satisfy` can use the
   requirement ID directly. KiCad `TraceID` field = need ID. sphinx-test-reports IDs are long and
   lowercase (`testcase__IF_JOINT_SERVO__signal_PWM_yfesz`); the ID regex must allow them or we map them.
6. **Interfaces (D36):** the pin map as a syseng file worked; next step is to generate it from the model.
7. **View generation (3.5):** reading ports/connections from the Pilot JSON is easy (feature chains).
   The SVG export needs Firefox in every docs build that renders an upstream view (also downstream).
8. **Workspace:** one topdir at the root (§7); `west update -k` while working in place.
9. **Build cost grows with depth (zdocs G4):** ee rebuilds both syseng docs, incl. their SVG export.

## 10. Input for the zdocs and affirmatrix issues (D59, D62)

zdocs (new, beyond research findings 1–12):
- Works with sphinx-needs 9.2; consider moving the pin.
- Add a documented strict mode; with it, make ninja keep going (`-k 0`) or report every failing doc,
  because the first failure is often an innocent upstream doc.
- Stage-1 `xref` builder makes `needflow` warn ("only supported for HTML"); skip such directives there.
- A way to add extra input files per document from the registry (today: `external_content_contents`
  in `conf.py`), and a variable for "generated inputs of project X" (G6).
- `needimport` with absolute paths cannot work in a copied source tree; document the pattern.

affirmatrix:
- Read several `needs.json` files (one per zdocs document) or a full-set merge; spike used a merge.
- Open link vocabulary: `satisfies`, `realizes`, `verifies` (per our TOML), not only `refines`.
- Respect need types: `sysel`/`eecomp`/`testcase` should not become "Requirement".
- Optionally hash `status`, so a `retired` change makes links suspect.
- Accept `source` relative to the repository (spike needed an absolute path).
- Case commits by agents: the user's rule wants a `Co-Authored-By` trailer; ADR-0009 forbids it. Decide.

## 11. Notes

- The framework repo is called `mbse-framework` here; it corresponds to `xdmod`.
- zdocs is pinned to `f9b701c` with the GitHub URL as remote (read-only, never fetched again).
- Nothing in the spike depends on the `/tmp` scratch dirs any more; downloads are re-fetched by
  `install-tools.sh` (with sha256 checks) if `TOOL_CACHE` is not set.
