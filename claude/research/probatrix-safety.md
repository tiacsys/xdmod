# Research — probatrix and the `safety` repo

Date: 2026-11-14. Source: the owner's repo `extra/safety` (read-only).

- `main` at `f5d891d` (2026-10-15).
- probatrix: branch `origin/tkaestner/kernel-unit-backlog` at `d69a236` (2026-11-08). This branch is
  `main` plus 35 commits, rebased and curated. probatrix arrives in `727eef8` (core + latbench),
  `0885b9c` (tlaplus) and `73dcdd7` (twister). The later commits add kernel unit tests (`k_stack`,
  `k_queue`, `k_mutex`, …). `origin/tkaestner/tla-spec` (339 commits ahead of `main`) is the older
  working branch with the same work in raw form, including the removed ssh runner (`7a9d947`).

Paths with `kub:` are inside the extracted branch
(`/tmp/claude-1000/-home-tobias-z-wrk-ws-syseng/cc4a5268-5423-4e94-be0d-4c1055bbe07f/scratchpad/research-probatrix/kub`).
Paths without a prefix are on `safety` `main`.
Markers: **[verified]** = I ran it. **[read]** = I read code or docs only.

## Summary

- **probatrix is an evidence recorder, not a test runner.** It wraps existing tools (a custom latency
  firmware, Twister, TLC) in "studies". Each study has a question, hypotheses written *before* the runs,
  and checks. Every run is sealed (SHA-256 per file) and gets a role: `evidence`, `historical` or
  `excluded`. **[read + verified tests]**
- **A run counts as evidence only if it came from a clean, pinned state**, and only while the files it
  depends on (`subject`) and the tools that made it (`tools`) are byte-equal to the current design.
  Change a subject file and old runs turn `historical` on the next `analysis build`. This is a
  content-based link from a result to its subject version. **[read]**
- **Remote machines: there is no transport.** A "lab space" is a folder on one host. You log in to
  that host yourself (ssh), run `study.py … campaign run --detach`, then move results with
  `lab export` → copy the tar file (`scp`) → `lab import` on another lab space. The old ssh runner was
  removed on purpose. **[read]**
- **HIL on a NUCLEO-G474RE already works, but only for the latency benchmark kind (`latbench`).** It
  builds, flashes (openocd), reads the serial console, uses a Twister hardware map with fixtures and a
  per-board lock. The `twister` kind is **host-only** (`unit_testing`, `native_sim`); it has no
  `--device-testing`. For robot-arm HIL we would need a new kind or an extension. **[read]**
- **Results do not reach sphinx-needs or affirmatrix yet.** The results tree lives outside git.
  The `safety` docs cite runs by `<instance>/<experiment>/<run id> sha256:<digest>`, written by hand.
  firmhold is named as the future store for sealed runs. **[read]**
- **probatrix is tied to the `safety` repo.** Design roots, the default kind, the env var names and the
  ref names are hard-coded (`kub:scripts/probatrix/core/config.py:62-81`, `core/kinds.py:40`). The
  package is not on PyPI. Version 0.1.0, Apache-2.0. **[read]**
- **Hands-on:** 655 of 656 unit tests pass in a scratch git snapshot (12 skipped). The one failure
  depends on the shell's nice level, not on the code. `study.py --help` and `design lint` work. **[verified]**
- **`safety` `main` is the best reference for our SW trace chain.** requirement → design (`fulfills`)
  → implementation (`@satisfies`) → test case (`@verifies`, `@testid`) → test result (Twister) →
  coverage adequacy. Each link is held by the more concrete side (matches D5). Three post-build checks
  find links that drop out silently. **[read]**
- **Copy directly:** the `needs_config.toml` style (one project-wide vocabulary, `reproducible_json`),
  the `documents.yaml` registry, the "accepted findings with a reason" file pattern, the append-only
  test-ID ledger, `test-scope.yaml`, and the agent slash command `annotate-ztest`.
- **Contradictions with plan.md:** probatrix pins Zephyr trees in its own files (vs. D39 "the manifest is
  the only place that pins"). Manual verdicts and the CBMC review rule say "a review by an agent does not
  count" (vs. D3). `safety` declares link types globally, which the traceability research says cannot
  enforce the owner side (D36).

---

## 1. probatrix in detail

### 1.1 What it is [read]

- "The Python package behind the study tools of the safety repository. It has a generic core and the
  kinds of study." (`kub:scripts/probatrix/README.rst:7-8`)
- Package metadata: name `probatrix`, 0.1.0, "Studies of safety evidence: designs, runs, instances and
  verdicts", Python ≥ 3.10, deps PyYAML, jsonschema, packaging; extras `benchmarks` (pyserial,
  matplotlib, west) and `notebooks` (pandas, plotly). Not published
  (`kub:scripts/probatrix/pyproject.toml:4-35`).
- About 40 000 lines including tests and fixtures. The core is about 2 500 lines.
- Entry points: `scripts/probatrix/study.py` or `python -m probatrix` (`README.rst:43-50`).
  Namespaces: `design`, `lab`, `campaign`, `trees`, `instance`, `analysis`, `import-lab`, `tlaplus`,
  `twister` **[verified with `--help`]**.

### 1.2 Core and kinds [read]

- The core reads and checks the design files, builds results, seals runs, runs campaigns and evaluates
  checks. "The core imports no kind." (`kub:doc/benchmark-guide/explanation/probatrix.rst:12-15`)
- A kind "knows one sort of evidence": how to make the points of an experiment, read the data of a run,
  and read one value (`probatrix.rst:17-20`). Required hooks: `name`, `schema_prefix`, `schema_folder`,
  `format_prefix`, `ref_prefix`, `tool`, `points`, `run_json`, `app_json`, `value`, `known`. Optional:
  `dirt_paths`, `extra_forms`, `generated_checks`, `instance_axis` (e.g. per board), `central_result`,
  `commands`, … (`probatrix.rst:37-60`).
- Registry: `PLUGINS` in `kub:scripts/probatrix/core/kinds.py:40`; later it should come from the
  entry-point group `probatrix.kinds` (`kinds.py:27-30`).
- `core/toolkind.py` is the shared base for kinds that "run a tool on a pinned tree" (tlaplus, twister,
  a planned cbmc): the same folder walk, instance folders, run-list entry and role rule
  (`kub:scripts/probatrix/core/toolkind.py:4-17`).

The three kinds:

| Kind | Folder | Tool | Hardware | Design root |
|---|---|---|---|---|
| `latbench` | `benchmarks/` | own latency firmware: build, flash, capture serial | **yes**: boards from a hardware map, fixture `latbench_loopback`, wire check, per-board lock | `validation/empirical/latencies` |
| `tlaplus` | `tlaplus/` | TLC model checking, simulation, trace check | no; lab-wide lock because TLC uses much memory | `validation/formal/kernel-spec` |
| `twister` | `twister/` | `scripts/twister` for safety unit tests and Zephyr tests | **no**: "the tests use host platforms only" | `validation/testing/kernel-tests` |

Sources: `README.rst:18-38`, `kub:scripts/probatrix/twister/campaign.py:17`,
`kub:doc/benchmark-guide/reference/cli/study-py.rst:509-512`. The twister command line has only
`-T`, `-s`, `-p`, `-O` and `-x=ZEPHYR_MODULES` (`kub:scripts/probatrix/twister/run.py:97-110`).

### 1.3 The study model [read]

Folder layout (`kub:validation/README.rst:14-20`): `validation/trees/` (pinned Zephyr trees, one west
manifest each), `testing/` (twister), `formal/` (tlaplus), `empirical/` (latbench). Folders are
`st-<name>` (study) and `ex-<name>` (experiment).

- **`study.yaml`**: `name`, `kind`, `question`, `experiments`, `imports` (`mode: reuse` or `rerun`),
  `substudies` (optionally `instances: per-board`), `central_results`
  (`kub:doc/benchmark-guide/reference/files/study-yaml.rst`). Example:
  `kub:validation/testing/kernel-tests/st-sem/study.yaml:4-11`.
- **`hypotheses.yaml`**: 1–4 hypotheses per study. Each has `statement`, `basis`, `wrong_if` and
  `checks` (`experiment`, `metric`, `expect`, or `manual: true`). Hypotheses are written before the
  runs, so the data can prove them wrong (`explanation/studies-and-verdicts.rst:15-26`). Example: H1
  "each test case of each unit test scenario of kernel/sem.c passes", checks `bad == 0` and
  `evidence == true` (`kub:validation/testing/kernel-tests/st-sem/hypotheses.yaml:12-32`).
- **`experiment.yaml`** (twister): `name`, `list` (one line = one point: `<root> <path> <scenario>
  <platform> [allow=…]`), `trees`, `subject`, `tools`
  (`kub:validation/testing/kernel-tests/st-sem/ex-sem-unit/experiment.yaml:14-26`,
  `kub:scripts/probatrix/twister/schemas/experiment.schema.yaml:13-51`).
- **Verdicts**: per check and hypothesis: confirmed / wrong / open / draft; *provisional* while a
  campaign still has to run an experiment (`studies-and-verdicts.rst:28-58`). Central results are
  sentences with placeholders filled from data; `stat: conclusion` needs a person:
  `instance verdict … --verdict confirmed --by "<name>"` (`howto/write-a-central-result.rst:41-46`).
- **Campaign**: runs all experiments below a folder, in order, after a pre-flight check (clean repo,
  pinned trees, board present, wire works). It sets a local ref `refs/latbench/campaign/<id>` so the
  commit survives a rebase. A failed experiment does not stop the campaign. A new commit in the
  design repo stops it (`explanation/campaigns.rst:29-61, 116-120`).

### 1.4 Lab spaces and lab config [read]

- A lab space is "a folder with the file `.lab/config`, as a west workspace is a folder with
  `.west/config`" (`kub:doc/benchmark-guide/reference/files/lab-config.rst:6-10`).
- INI keys: `[lab] id/name`, `[design] repo` (a clone of `safety` inside the lab folder), `[trees] root/source`,
  `[toolchain] zephyr_sdk`, `[results] root`, `[hardware] map`, `[python] venv` (`lab-config.rst:15-64`).
  tlaplus adds `[tlaplus] archive, java_home` (`README.rst:27-29`).
- `.lab/` also holds the build cache, campaign records, locks (one `flock` per board, one for the
  results build) and wire-check records (`lab-config.rst:70-73`, `campaigns.rst:98-110`).
- **Re-exec**: any `study.py` started inside a lab space re-runs the `study.py` of the lab's own clone
  with the lab's venv. So the code and packages of the lab space are always the ones used
  (`explanation/probatrix.rst:113-130`).
- Each pinned tree is a west manifest in `validation/trees/<tree>.yml`; `trees setup` makes one west
  workspace per tree. A pinned revision never changes; a new revision means a new tree name
  (`explanation/decisions/0006-lab-space.rst:22-31`, `explanation/reproducibility.rst:14-19, 41-49`).
- Setup: clone, venv, `pip install -r requirements.lock`, write `hw-map.yml`, `lab init`,
  `trees setup`, `lab status`, `lab hwcheck <board>` (`howto/set-up-a-lab-space.rst:8-63`).

### 1.5 Lab exchange: combining labs [read]

- Purpose: "One host has only some boards of a study, and a second host makes a study faster."
  (`explanation/lab-exchange.rst:6-8`)
- `lab export -o file.tar.gz` writes the runs plus a `.sha256`, and a **git bundle** of the run commits.
  You copy the file yourself ("for example with `scp`"). `lab import --dry-run`, then `lab import`,
  then `analysis build` (`howto/combine-lab-spaces.rst:9-39`).
- Import checks: the `experiment.yaml` content must be equal in both labs (comments and renames are
  ignored), or the run is refused. A different `study.yaml`/`hypotheses.yaml` only warns, because the
  importer builds verdicts from its own design. Each run's seal must match its run-list digest
  (`lab-exchange.rst:13-29`). The git bundle makes `run.py --rebuild` work in the importing lab
  (`lab-exchange.rst:41-46`).
- `instance merge OTHER ROOT --origin HOST:PATH` is for a results tree outside a lab space
  (`reference/cli/study-py.rst:446-452`).

### 1.6 How it runs on remote machines [read]

- **What runs where:** everything runs on the lab host: build (`west build` in the tree workspace),
  flash, capture, seal, analysis. The developer machine only needs the design repo.
- **Transport and auth:** none built in. The user logs in to the host (ssh). `campaign run --detach`
  starts the campaign in a new session and returns; output goes to `.lab/campaigns/<id>/campaign.log`
  (`study-py.rst:388-391`). The campaign engine traps `SIGHUP` "the ssh connection of a campaign
  without --detach" (`kub:scripts/probatrix/core/campaign.py:480`).
- Results move by export file + `scp` + import. The old ssh runner `scripts/tla/run_tlc_remote.py`
  was removed (`explanation/probatrix.rst:27-28`, `kub:scripts/probatrix/tlaplus/run.py:9`).
- The lab clone gets new commits by a normal `git pull`/`fetch` on the host. The campaign refuses a
  dirty or moving repo.

### 1.7 Results and subject versions [read]

- **Seal**: `<UTC>.sha256` beside the run folder, one line per file; the run digest is the SHA-256 of
  that file. Run folders never change (`kub:scripts/probatrix/core/seal.py:4-10`).
- **Run record** (twister): `job.json` (tree name, rev, pin, dirty; repo rev, dirty; status; points),
  `subject.json`, `tools.json` (host, SDK, gcc, python — recorded, not checked), plus the kept Twister
  files (`twister.json`, logs) (`kub:scripts/probatrix/twister/adapter.py:6-17`).
- **Git SHAs**: each run gets a local ref `refs/<kind>/run/<experiment>/<UTC>` that keeps the commit
  alive ("never pushed") (`kub:scripts/probatrix/tlaplus/subject.py:160-169`, `campaigns.rst:118-120`).
- **Subject tree**: for each path in `subject` and `tools`, the git object id at the run's commit
  (`git rev-parse <rev>:<path>`). "A run on another revision counts for the experiment if its subject
  tree is the tree of the current design" (`subject.py:4-11, 74-92`).
- **`subject_exclude`**: files below a subject path that do not count (README, CMakeLists, a coverage
  list). If any excluded file is present, the id becomes `x-<sha256>` over the remaining files
  (`subject.py:55-71`). Use: a README edit must not turn evidence runs historical
  (`kub:validation/formal/kernel-spec/st-design-properties/ex-mc-expected/experiment.yaml:12-14, 26-33`).
  The lint checks that excludes lie inside a subject path and never exclude the list file
  (`kub:scripts/probatrix/tlaplus/kind.py:181-189`).
- **Firmware hash** (latbench): a content hash of the firmware files of `tests/benchmarks`, passed to
  the build as `LATBENCH_SRC_REV` instead of the commit, so the same firmware gives the same image at
  any commit (`explanation/reproducibility.rst:107-118`).
- **Build cache key**: SHA-256 over board, app, pinned tree revs, `BUILD_VERSION`, builder version, SDK
  version, firmware hash, module tree hash and the point's Kconfig/overlays. No host path and no commit
  (`reproducibility.rst:122-160`).
- **Role now**: on every `analysis build`, twister and tlaplus runs are re-judged against `HEAD`. A run
  is `historical` if its subject or tool tree differs, with the list of changed paths. A run is never
  promoted back (`subject.py:129-157`, `study-py.rst:600-610`).

### 1.8 Evidence rules [read]

- twister: the safety repo was clean at the revision, the tree was at its pin, clean and not local, and
  the run completed. "A failed test is not a reason: the failure is the result."
  (`adapter.py:33-34, 164-181`)
- Shared rule: evidence = kind rule OK + subject tree and tool tree equal to the design + all points of
  the design present; else `historical`; a local tree gives `excluded` (`adapter.py:190-194`,
  `core/toolkind.py:138-153`).
- latbench: `run.py` stops before building if the repo is dirty, the lab uses another design repo, a
  tree is not at its pin or dirty, or the SDK version differs (`reproducibility.rst:22-33`).
- Planned cbmc kind: evidence only if a **person** reviewed the predicate at the run's content hashes;
  "A review by an agent does not count." (`kub:doc/specification/formal-design/methodology/09-checks-tests-evidence.rst:225-232`,
  `kub:doc/specification/formal-design/decisions.rst` D38)

### 1.9 How results reach the docs and affirmatrix [read]

- Today: **they do not, automatically.** "Evidence stays out of the repository … The results tree is
  not in the repository. This rule holds for every kind." (`explanation/probatrix.rst:132-139`)
- probatrix makes its own outputs in the results tree: `run.json`, `experiment.json`, `study.json`,
  plots, HTML pages and executed Jupyter notebooks (`study-py.rst:653+`, `study-yaml.rst` "Notebooks").
- The docs plan: "A document cites a run by its instance, its experiment, its run id and its digest …
  `<instance>/<experiment>/<run id> sha256:<digest>`." The k_sem consistency record "becomes a page of
  this document. The page cites the runs. It is planned and not written yet."
  (`kub:doc/specification/formal-design/decisions.rst`, D19 at lines ~365-392)
- "Later, sealed bundles of runs go to an artifact registry (firmhold)." (same D19; also
  `09-checks-tests-evidence.rst:252-253`)
- The `benchmark-guide` is a zdocs document without needs (`kub:doc/documents.yaml`, entry
  `benchmark-guide`).
- The test report on `main` reads Twister output from a fixed folder given at configure time
  (`-DZDOCS_TWISTER_OUT=…`, `CLAUDE.md:91-92`), not from probatrix.
- affirmatrix: `affirmatrix.yaml:7-8` "The configuration names no test run: a run is given as a bundle
  on the command line." Drift detection is affirmatrix's job, and a human review record "Later an
  affirmation of affirmatrix can replace it" (`decisions.rst` D37, D38). There is no code that turns a
  probatrix run into an affirmatrix bundle yet.

---

## 2. Fit for this project

### 2.1 HIL of the robot-arm firmware (D8, D38)

What fits well:

- The NUCLEO-G474RE is already a supported board, with ST-LINK/openocd flashing and the console on
  `/dev/serial/by-id/...-if02` (`kub:doc/benchmark-guide/howto/wire-the-nucleo-g474re.rst:4-32`).
- The hardware map **is** a Twister hardware map with `fixtures` (`reference/files/hw-map.rst:6-23`,
  `howto/make-a-hardware-map.rst:24-34`). Our planned fixture (e.g. `joint_rig`) fits the same scheme
  as `latbench_loopback`.
- The "wire check" idea maps to a rig self-test: before a HIL campaign, check that the PCA9685 and
  MCP3208 answer and a pot reads in range.
- Per-board locks, detached campaigns and lab export/import solve "board at another desk / another
  machine".

What is missing:

- The `twister` kind does not do `--device-testing --hardware-map`, has no board lock and no fixture
  selection (`twister/run.py:97-110`, `study-py.rst:509-512`). latbench flashes boards but runs its own
  capture protocol, not ztest/pytest.
- So robot-arm HIL needs **either** (a) a new kind `hil` / `twister-device` built on `core/toolkind.py`
  (adds `--device-testing --hardware-map <lab map> -p nucleo_g474re`, a board lock, the fixture, and
  pytest-harness output), **or** (b) plain `west twister --device-testing` without probatrix in
  iteration 1.
- probatrix is hard-wired to the `safety` repo (roots in `core/config.py:75-81`, "safety repo" in
  messages, `LATBENCH_*` env names, `ZEPHYR_SAFETY_MODULE`). Using it from `robarm-sw` means a fork or
  a refactor of `Project`.

How HIL would run with it (sketch, not tried):

1. `robarm-sw/validation/trees/<tree>.yml` pins Zephyr (or points at our manifest — see 2.4).
2. `validation/testing/hil/st-joint/ex-joint-hil/experiment.yaml`: `list` of HIL scenarios on
   `nucleo_g474re`, `subject` = app + tests + overlay, `tools` = run tool + adapter.
3. `hypotheses.yaml`: e.g. "servo pulse width follows pot within ±1 step", checks on `bad == 0` and
   `evidence == true`.
4. On the machine with the board (this one or a lab host): `lab init`, `trees setup`, `lab hwcheck`,
   `hil campaign run … --detach`.
5. Remote lab: `lab export` → `scp` → `lab import` on the machine that builds the docs.
6. A small exporter turns `study.json`/run records into `test_result` needs with the run digest
   (does not exist yet).

### 2.2 Prototype vs. product variants (D37)

- probatrix has a per-board axis (`instance_axis`, `instances: per-board`, `probatrix.rst:56-57`,
  `study-yaml.rst`). A variant could be an instance axis: `prototype` (Nucleo + breakouts) and later
  `product` (own PCB). Hypotheses then say which instance proves which requirement.
- "A prototype test verifies the logical and SW requirements it covers" maps to: the same experiment,
  instance `prototype`; product-only requirements stay `open` ("no evidence run") until a product
  instance exists. This matches how `analysis missing` reports gaps (`study-py.rst:625-627`).

### 2.3 Traceability of results to requirements (D36)

- probatrix has **no requirement IDs** in its model. A hypothesis or experiment does not name a need.
- For D36 we need a link from the result side to the test spec (concrete side holds it). Options: add a
  `verifies:`/`test_case:` field to `experiment.yaml` or to each list line, and export `test_result`
  needs with `result_of` → test case and the run digest. That is a new exporter, not in probatrix.
- The subject-tree rule is a good "is this result still valid" check, close to what affirmatrix does
  for links. Together they cover "result is stale" (probatrix) and "link is suspect" (affirmatrix).

### 2.4 Local checks (D46) vs. GitHub CI (D47)

- probatrix is a lab tool. It needs a clean, committed repo, a pinned tree and often a board. It does
  not fit GitHub CI in iteration 1 (D47 says SDK checks run locally). Good fit for D46 as the *local*
  HIL/evidence command; **not** a fit as the per-repo fast check.
- `study.py design lint` is cheap and needs no SDK **[verified: `0 errors, 0 warnings` on
  `validation/testing/kernel-tests`]**. It could run in GitHub CI to check study designs.
- **Pin conflict with D39:** probatrix pins trees in `validation/trees/*.yml` and forbids changing a
  pin (`reproducibility.rst:41-49`). Our plan says the manifest repo is the only place that pins. A
  fix: let the tree file be generated from (or point to) a manifest baseline tag (`baseline/vX.Y.Z`,
  D54), and treat a baseline as an immutable tree.
- **Rebase-merge (D50):** recorded commit SHAs change when a PR is rebase-merged. probatrix keeps the
  commit alive with local refs (never pushed), and judges evidence by content (subject trees), not by
  SHA. That survives rebases. But a doc that cites a SHA from a feature branch will point to a commit
  not on `main`.

### 2.5 Firmhold bundles (iteration 2, D43)

- firmhold attaches "SBOMs, test results, and attestations … to the digest of the binary they
  describe" as OCI referrers (`extra/firmhold/README.md:3-9`, `doc/explanation/referrer-graph.rst:9-27`).
  I found no test-result command in its source yet (`src/firmhold/core/oci.py:882` mentions an
  attachment vocabulary). **[read]**
- The link point is clean: a probatrix run has a sealed digest and (for firmware) the image hash /
  build-cache key. A HIL run record → a firmhold referrer on the firmware digest. This also answers
  the open question in `zephyr-west.md` §"HIL results storage": in iteration 1, results stay in the lab
  results tree; in iteration 2, sealed runs go to firmhold, which matches the plan in `safety`'s D19.

### 2.6 Non-SW studies

- Technically yes. Any tool that runs on a pinned commit and writes files fits `toolkind`: list file →
  points, run tool → raw folder, adapter → values. Candidate kinds: `kicad` (`kicad-cli sch erc`,
  `pcb drc`), `freecad` (headless interference / range-of-motion script), `sysml` (model parse and
  rule checks).
- But: ERC, DRC and SysML parse checks are **deterministic pass/fail checks**. They belong in the D46
  check command and in CI, not in a study with hypotheses. probatrix adds value where results vary or
  need a hardware setup: HIL timing (leader → follower latency), servo accuracy, range-of-motion
  measured on the real arm, or a FreeCAD sweep with a stated hypothesis ("no collision over the full
  joint range").

---

## 3. Reusable patterns from `safety` (main)

### 3.1 `doc/needs_config.toml`

- One project-wide vocabulary loaded by every document through `ZDOCS_NEEDS_CONFIG`
  (`needs_config.toml:3-11`, `doc/CMakeLists.txt:66`). Reason given: every document imports every
  other's needs, so all must agree on types and link names. **Copy this.**
- `build_json = true` and `reproducible_json = true` (no time stamps, so needs.json can be hashed by
  affirmatrix) (`needs_config.toml:22-28`). **Copy this.**
- Types: `test_case`, `test_procedure`, `test_result`, `impl`, `design`, `adequacy`, `req`
  (`:32-90`); on kub also `prop` (TLA+ model property).
- Links: `verifies`, `result_of`, `covers` (derived), `satisfies`, `assesses`, `fulfills`, `trace`
  (`:99-139`); on kub also `expresses`.
- Every custom field is declared with a schema type and `nullable` (`:141-294`).
- **Compare with D36:** `safety` declares links **globally** (`[needs.links.*]`). The traceability
  research found that global links accept wrong-side links silently; to enforce the owner side,
  declare each link only on the need type that holds it (`research/traceability.md:59-63, 169-184`).
  So copy the file style, but **not** the global link declarations. Also `safety` has no
  `target_types` or `minItems` rules.
- Names worth reusing for our table: `verifies` (test → req), `result_of` (result → test),
  `satisfies` (code → req), `fulfills` (design → req, kept separate so "satisfied by" means code only,
  `:128-133`), `trace` for req → parent (we would call it `refines`).

### 3.2 `doc/documents.yaml` (zdocs registry)

- One declaration per document drives targets, intersphinx, Doxygen tag files, nav groups and needs
  imports (`documents.yaml:1-8`). Groups `specification`, `verification`, `reference`, `governance`,
  `internal` (`:36-58`).
- Good habits: a `xref_smoketest` page so `doc-check` is not "a green gate that checked nothing"
  (`:22-28`); `doc_check_accepted` with exact text and a reason per accepted finding (`:30-34`); a
  comment on each entry saying why it is there.
- The test report names its spec as `testmodule: spec: test-specification` (`:122-127`).
- **Copy:** the group set and the commented-entry style map well onto D21/D27 (SW requirements,
  SW architecture, SW test spec, test report).

### 3.3 Check scripts

- `doc/_scripts/satisfies_check.py`: every `@satisfies` must land on exactly one `impl` need; classes
  OK / MISSING / DUPLICATE; `--accepted` file with reasons; stale accepted entries warn
  (`satisfies_check.py:6-36`).
- `doc/_scripts/testspec_check.py`: every ZTEST in scope must be a `test_case` in the built spec;
  classes in spec / TWIN / MISSING / MISATTACHED / CROSS-MODULE (`testspec_check.py:6-44`).
- `design_gen.py check`: every design block gives exactly one `design` need (`design_gen.py:30-34`).
- All three run as stand-alone targets and as POST_BUILD of `all-docs` (`doc/CMakeLists.txt:272-362`).
- **Pattern to copy:** "find links that drop out silently" by comparing *sources* with the built
  `needs.json`. sphinx-needs warns on dangling links, but not on a tag that never became a need. We
  need the same for SysML stubs (D42), KiCad fields and FreeCAD properties (D29).

### 3.4 Test IDs: `assign_testids.py`, `testids.yaml`, `test-scope.yaml`

- IDs `TSPEC-<code>-<NNN>`; append-only; the ledger keeps the last number per area so a number is
  never reused (`assign_testids.py:6-25`, `testids.yaml:1-2`). New ids get `@draft`. Dry run by default,
  `--write` to change (`assign_testids.py:25, 131`). **Copy directly** (adapt the regex).
- `test-scope.yaml`: per area `path`, `code` (never changes once ids exist), `title`, `modules`; the
  generator makes the Doxygen INPUT, groups and the spec/report page tree from it
  (`test-scope.yaml:1-27`, `_scripts/testspec_scope.py:340-375`). **Copy the idea**; our scope is small,
  so a short file is enough.

### 3.5 `affirmatrix.yaml`

- Invocation only: case path, implementation repo, repo paths, producers (requirements export,
  implementations, test specs) with `types`, `parent-field`, `source-map` (`affirmatrix.yaml:1-90`).
  "Nothing here enters a hash." Good template once we adopt affirmatrix (see `affirmatrix.md`).
- Note: it reads needs.json from a separate doc build (`build-prague`), with a comment that the build
  must use the same revisions (`:10-13`). For us, the manifest baseline should fix that.

### 3.6 `.claude/commands/annotate-ztest.md`

- A slash command that tells an agent exactly how to document a ZTEST: group hierarchy, docstring
  template with `@brief`/`@details`/requirement refs/`@see`, in-body `@par Arrange/Act/Assert/Teardown`,
  rules to classify helpers, style rules (no Unicode in C comments), and a checklist that ends with a
  build command (`annotate-ztest.md:1-234`).
- **Copy the pattern** for D3/3.11: one command per authoring task (write a requirement, annotate a
  test, add a KiCad trace field), each with a template and a closing check command. Update the
  template: it still uses `:external+req:ref:` in a verbatim block (`:59-61`), while `CLAUDE.md:48-51`
  now says `@verifies <UID>`, one per command. The two disagree.

### 3.7 `CLAUDE.md` conventions for agents

- Purpose, workspace layout, "do not conflate" table, ID rules (uppercase, one UID per command), the
  build commands, the full trace chain as a diagram, and where open work is tracked
  (`CLAUDE.md:1-334`).
- **Copy:** the trace-chain section and the exact build/check commands. Keep ours shorter; `safety`'s
  is 334 lines and mixes rules with history.

---

## 4. SW trace chain in `safety`

The chain on `main` (`CLAUDE.md:133-153` gives the overview). Each row: what produces the link, which
side holds it, and what checks it.

| Step | Source and tag | Producer | Need / link | Held by | Check |
|---|---|---|---|---|---|
| Requirement | StrictDoc `.sdoc` in `doc/reqmgmt` | `strictdoc export` → Zephyr's `gen_requirements.py`, unchanged (`doc/CMakeLists.txt:88-113`) | `req`, link `trace` to parent (`needs_config.toml:85-90, 135-139`) | child req (`affirmatrix.yaml:30-31` "points from a child to its parent") | dangling `trace` → sphinx-needs warning; UID in Doxygen unknown → Doxygen warning gate (`CLAUDE.md:52`) |
| Design | `.. design:: DESIGN-X` with `:fulfills:` in Zephyr `doc/kernel` | `design_gen.py generate` → `architecture` doc (`design_gen.py:6-29`) | `design`, link `fulfills` | design element | `design_gen.py` fails on dangling target; `design-check` one need per block (`CMakeLists.txt:299-318`) |
| Implementation (API) | `@satisfies <UID>` on public symbols | Doxygen `dox-zephyr-safety-api` → `symbolneeds::` in `api-documentation` (`documents.yaml:136-151`, `satisfied-requirements.rst:13`) | `impl` `IMPL-<symbol>`, link `satisfies` | code | `satisfies-check` (`CMakeLists.txt:320-362`), accepted list `satisfies-accepted.yaml` |
| Implementation (internal) | `@satisfies` in `kernel/*.c`, `queue.h_` | `dox-zephyr-safety-detailed-design` → `symbolneeds::` in `architecture` (`documents.yaml:86-92`) | `impl`, `satisfies` | code | same `satisfies-check` |
| Test case | `ZTEST` with `@testid{TSPEC-…}` and `@verifies <UID>` | `assign_testids.py` adds ids; `testspec_scope.py` makes groups and pages; Doxygen `dox-zephyr-safety-testspec`; `.. testmodule::` per module (`testspec_scope.py:354-358`) | `test_case`, link `verifies` | test | `testspec-check` (`CMakeLists.txt:272-297`); Doxyfile says "This project is the \verifies side" (`dox/zephyr-safety-testspec/Doxyfile.in:774`) |
| Test result | Twister `twister_report.xml` / `twister.json` in `ZDOCS_TWISTER_OUT` | `.. testreport:: twister_report.xml :path: <module>` (`testspec_scope.py:360-366`) | `test_result`, links `result_of` → test case and `covers` → req (derived) (`needs_config.toml:104-112`) | result | dangling `result_of`; `depends_met`/`skip_class` explain skips (`CLAUDE.md:187-197`) |
| Adequacy | per-test coverage run (`ZDOCS_COVERAGE_OUT`) | `.. testcoverage::` in `verification/test-report/adequacy.rst:48-50` | `adequacy` `ADQ-<run>/<req>`, link `assesses` | adequacy need | verdict field (`true` / `partial` / `unresolved` / …) (`CLAUDE.md:198-210`) |
| Views | — | `need_count` tables, pie charts per layer (`CLAUDE.md:211-217`) | — | — | gaps shown, not failed |

Notes:

- Every link is on the concrete side (code, test, result, design, child requirement). This matches D5.
- The requirement page shows "verified by", "satisfied by", "covered by", "fulfilled by", "assessed by"
  as computed backlinks, because all four needs documents import each other (`CLAUDE.md:150-153`).
- Ids: requirements use authored UIDs; test ids `TSPEC-<AREA>-<NNN>`; results `TR-*`; impl
  `IMPL-<symbol>`; adequacy `ADQ-<run>/<req>`.
- Weak points: results come from one fixed Twister folder with no provenance record (which commit,
  which board, dirty or not); a test can `@verifies` any requirement type (no `target_types`); there is
  no "every requirement has a test" rule that fails the build, only views.

On `kernel-unit-backlog` the chain grows, but the new parts are not yet linked:

- New doc `formal-design` with `prop` needs and link `expresses` from TLA+ `@expresses` tags
  (`kub:doc/needs_config.toml` new type `prop` and link `expresses`; `kub:doc/_extensions/tla_domain.py:27, 46`).
- New Doxygen doc `dox-kernel-unit-testspec` with `crossref: false` (`kub:doc/documents.yaml`).
- The kernel unit tests "have no `@testid` and no `@verifies` yet" (`kub:tests/kernel/unit/README.rst:1260`).
- Their results go through probatrix (`twister` kind), not through the test report.

### Mapping to `robarm-sw` (D21, D36)

| `safety` | `robarm-sw` | Note |
|---|---|---|
| `requirements` (StrictDoc → `req`, `trace`) | SW requirements, sphinx-needs rst, `swreq` with `refines` → `sys` (upstream syseng, built locally, D35) | We author in rst (D6), so no StrictDoc step |
| `architecture` + `design` (`fulfills`) | SW architecture and design doc; design needs with `fulfills` → `swreq`; allocation from SysML on the concrete side | Generated from SysML where possible (D22) |
| `api-documentation` + `impl` (`@satisfies`) | SW design (API) via Doxygen `@satisfies SWREQ_…` + `symbolneeds::` | Copy `satisfies_check.py` |
| `test-specification` (`@testid`, `@verifies`) | SW test spec: ZTEST + `@testid{TSPEC-…}` + `@verifies SWREQ_…` | Copy `assign_testids.py`, `testids.yaml`, `test-scope.yaml`, `testspec_check.py`, `annotate-ztest` |
| `test-report` (`testreport::`) | Test report: host tests (`native_sim`) + HIL results on `nucleo_g474re` | Add a provenance record per run (from probatrix or our own) |
| `adequacy` | later | Needs a coverage run; skip in iteration 1 |
| global `[needs.links]` | per-type link declarations with `target_types`, `minItems` | Enforces D36 owner side |

---

## Hands-on results

All in `/tmp/claude-1000/-home-tobias-z-wrk-ws-syseng/cc4a5268-5423-4e94-be0d-4c1055bbe07f/scratchpad/research-probatrix`.
No remote host, no ssh, no board, no change to the `safety` repo.

| # | Step | Result |
|---|---|---|
| 1 | `git archive origin/tkaestner/kernel-unit-backlog \| tar -x` (also `tla-spec`) | OK **[verified]** |
| 2 | venv (Python 3.14.10), `pip install PyYAML jsonschema packaging pytest pyserial west` | OK. matplotlib install was slow; I stopped it. Plot tests were skipped. **[verified]** |
| 3 | `python scripts/probatrix/study.py --help`, `twister --help` | Works. Shows the namespaces above. **[verified]** |
| 4 | `study.py design lint validation/testing/kernel-tests` | `0 errors, 0 warnings` **[verified]** |
| 5 | `pytest scripts/probatrix` in the plain extract | 647 passed, 9 failed, 12 skipped. 8 failures: "not a git repository" (the extract has no `.git`); 1: see row 7. **[verified]** |
| 6 | Same in a scratch `git init` snapshot, venv on `PATH` | **655 passed, 1 failed, 12 skipped** in 47 s **[verified]** |
| 7 | The one failure: `tlaplus/tests/test_run.py::test_the_tool_runs_selftest_first…` expects `nice=10`, got `nice=6`, because my shell runs at nice `-4`. The test assumes a base nice of 0. Environment, not a code bug. **[verified]** |
| 8 | Without the venv on `PATH`, 5 more tlaplus tests fail: the fake `run_tlc.sh` calls `mc_runs.py` with the system Python, which lacks jsonschema. In a lab space the venv is on `PATH`, so this is fine there. **[verified]** |

---

## Recommendations

Iteration 1:

1. **Do not adopt probatrix for iteration 1 HIL.** Its twister kind has no device testing, and the
   package is bound to `safety`. Use `west twister --device-testing --hardware-map` with a fixture
   (`zephyr-west.md` §HIL) for the one-joint test.
2. **Adopt its evidence rules by hand** in a small record per run: repo SHA + dirty flag, manifest
   freeze, tree at pin, `sha256(zephyr.bin)`, board serial, `status: complete`. Same rule as
   `twister/adapter.py:164-181`. This is what `zephyr-west.md` already proposed as a "build record".
3. **Copy from `safety` main:** the `needs_config.toml` pattern (with per-type links instead of global
   ones), the `documents.yaml` style, `assign_testids.py` + `testids.yaml`, a reduced
   `test-scope.yaml`, `testspec_check.py` and `satisfies_check.py` (adapted), the accepted-findings
   files, and an `annotate-ztest`-style command for agents.
4. Keep HIL results out of git (as `safety` does) and say so in the plan: in iteration 1 they live in
   a local results folder plus a release asset on the baseline tag (closes the open question in
   `zephyr-west.md`).

Later (iteration 2+):

5. Ask the owner to split probatrix from `safety` (configurable `Project`, entry-point kinds). Then add
   a `hil` kind (device testing, board lock, fixture, pytest harness) and use lab spaces for a remote
   rig.
6. Add an exporter: probatrix run → `test_result` needs (with run digest) and → affirmatrix bundle →
   firmhold referrer on the firmware digest.
7. Use studies with hypotheses for measured properties: leader → follower latency, servo accuracy,
   range of motion on the real arm. Keep ERC/DRC/SysML checks as plain checks.

---

## Findings for the owner (nothing was changed)

1. probatrix twister kind is host-only; no `--device-testing` / hardware map, so it cannot run HIL
   Twister tests yet (`twister/run.py:97-110`, `study-py.rst:509-512`).
2. Design roots, default kind and `LATBENCH_*`/`refs/latbench/*` names are hard-coded for `safety`
   (`core/config.py:62-81`). Reuse in other repos needs a configurable `Project` (maybe a
   `probatrix.toml` like `.lab/config`).
3. The README section "Run the tests" (`README.rst:52-59`) does not say that the tests need a git
   checkout and the venv first on `PATH` (8 + 5 failures otherwise). One test assumes nice 0
   (`tlaplus/tests/test_run.py`, the `nice=10` assertion).
4. Results have no path into sphinx-needs or affirmatrix yet; D19's "a page cites the runs" is still
   planned. An exporter to `test_result` needs with the digest would close this.
5. `annotate-ztest.md:59-61` still tells agents to write `:external+req:ref:` in a verbatim block, while
   `CLAUDE.md:47-51` says `@verifies <UID>`, one per command. The command also points at
   `doc/_doxygen/safety-test-groups.dox` and `/wrk/z/ws-safety/bdoc` (`:23, 233`), which no longer
   match the generated groups and `../bdoc-zdocs`.
6. `needs_config.toml` declares links globally; nothing stops a requirement from holding `verifies`.
   Per-type link declarations (sphinx-needs ≥ 9.1) would enforce the owner side.
7. The kernel unit tests on kub have no `@testid`/`@verifies` yet (`tests/kernel/unit/README.rst:1260`),
   so their probatrix evidence has no link to requirements.
8. `doc/benchmark-guide` uses Jupyter HTML that loads plotly from a CDN (`study-yaml.rst`, Notebooks);
   offline review of reports does not show figures.

## Risks and open questions

- **D39 conflict:** probatrix tree files are a second pin location. How should a tree relate to a
  manifest baseline? (Proposal: a tree = a baseline tag; generated, never edited.)
- **D3 conflict:** manual verdicts take `--by NAME`, and the cbmc rule says agent reviews do not count.
  Our plan treats agents as first-class reviewers. The owner's position on agent verdicts must be
  settled before we reuse this (same issue as affirmatrix's human-only affirmation).
- **D50:** local refs keep run commits alive, but they are never pushed. Results cited by SHA from a
  PR branch point to commits not on `main` after a rebase-merge. Cite by digest and subject tree, not
  by SHA.
- probatrix is pre-release (0.1.0), on a feature branch, about 40 k lines, one main author. Moving
  fast; API may change.
- Remote labs rely on manual ssh and scp. Fine for one person; for a team or agents, a defined
  transport and auth (and who may start a campaign on a shared rig) is open.
- Open: should iteration-1 HIL results be committed (small JSON) or only release assets? `safety`
  says never commit evidence; our D8 wants results traced in docs. The doc build then needs the result
  files at build time from outside git.
