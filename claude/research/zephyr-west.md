# Research 1.6 — Zephyr and west

Date: 2026-11-14. Author: research agent 1.6.
Markers: **[verified]** = I ran it on this machine. **[read]** = from docs or source, not run.
Scratch work (apps, scripts, logs): `/tmp/claude-1000/-home-tobias-z-wrk-ws-syseng/cc4a5268-5423-4e94-be0d-4c1055bbe07f/scratchpad/research-zephyr/`

## Summary

- **Both drivers are upstream and build for the NUCLEO-G474RE.** `nxp,pca9685-pwm` and `microchip,mcp3208` are in Zephyr 4.4.2. A test app with both devices, one servo channel and one pot channel builds with `west build -b nucleo_g474re` (43.7 KB flash). [verified]
- **Toolchain on this machine:** west 1.5.0, Zephyr 4.4.2 (workspace `ws-t`, `v4.4-branch`), Zephyr main 4.4.99 (`ws-up`), Zephyr SDK 1.0.1 (inside `ws-up`, registered in `~/.cmake/packages`). There is no global `west` and no `ZEPHYR_BASE`; each workspace has its own `.venv`. [verified]
- **West topology:** D14 is the west "T3 forest" topology. It works with plain non-Zephyr repos. A manifest `revision: pull/N/head` fetches a GitHub PR ref, so a "manifest PR" can point at open PRs in other repos. [verified with local repos]
- **Non-firmware repos** (syseng, ee, me, framework) can be plain west projects. If they add a `zephyr/module.yml`, Zephyr's module scan finds them. zdocs needs this: its doc build calls `find_package(Zephyr COMPONENTS doc)`. So **every doc build needs a Zephyr checkout, but no SDK.** [verified scan; read zdocs]
- **Devicetree is a good link point to the model.** `edt.pickle` from the build can be read with Zephyr's in-tree `python-devicetree`. I wrote a ~40-line extractor and a checker that compares devicetree facts to model values by trace ID. [verified]
- **Trace IDs in devicetree:** you **cannot** add new properties to upstream nodes (the build fails). Use a project binding (e.g. `robot,joint` with a `trace-id` property) or the free-form `zephyr,user` node. [verified]
- **Tests:** Twister writes `twister.json` and JUnit XML (`twister_report.xml`). Neither has a requirement ID, the app commit or a firmware hash. We must add these ourselves. Firmware `zephyr.bin` was byte-identical across two build dirs, so a SHA-256 of the binary is a usable firmware ID. [verified]
- **Zephyr's own traceability** is early: requirements in StrictDoc (`reqmgmt`, "preliminary work"); doxygen aliases `@satisfy{@req{..}}` and `@verify{@req{..}}` exist, but 0 tests in the tree use `@verify`. Nothing to copy as-is. [verified grep; read]
- **Parameter exchange:** I found no open tool that flows values from SysML into devicetree, KiCad and FreeCAD. Recommend **check, not generate** for devicetree (iteration 1); generate later only for simple key/value files.
- **SBOM:** `west spdx` works and gives SPDX 2.3 with git SHAs of every module. It needs `CONFIG_BUILD_OUTPUT_META=y`. The `zephyr.meta` file also records a workspace `dirty` flag. Good prior art for the bundle. [verified]

## Findings

### 1. West: topologies, manifest repo, pinning, multi-repo PRs

**Topologies** [read: https://docs.zephyrproject.org/latest/develop/west/workspaces.html]

- T1 star, Zephyr is the manifest repo (upstream Zephyr itself).
- T2 star, the application repo is the manifest repo (e.g. `zephyrproject-rtos/example-application`, nRF Connect SDK `sdk-nrf`).
- T3 forest, a dedicated manifest repo with no code. This is **D14**.

**Useful manifest features** [read + verified where marked]

- `import:` pulls in another manifest (e.g. Zephyr's `west.yml`). `name-allowlist` keeps only needed modules. The `ws-t` workspace on this machine already uses this with `cmsis_6`, `hal_stm32` etc. [verified by reading the local file]
- `groups:` plus `group-filter:` hide optional projects. Verified: projects in group `hw` were skipped until `west config manifest.group-filter +hw`. [verified]
- `revision:` can be a branch, tag, SHA or a ref like `pull/7/head`. [verified]
- `west manifest --freeze` prints the manifest with every revision turned into a SHA. `--resolve` resolves imports. `--validate` checks the syntax. [verified]
- `west update --narrow -o=--depth=1` keeps CI clones small. [read, `west update --help`]
- `west compare` shows local changes against the manifest. [verified]

**How Zephyr does multi-repo PRs** [read: https://docs.zephyrproject.org/latest/develop/modules.html, section "Process for submitting changes to existing modules"]

1. Open the PR in the module repo.
2. Open a PR in the zephyr repo that changes `west.yml` to `revision: pull/<n>/head`.
3. Mark that PR as draft or `DNM`.
4. After the module PR merges, change the revision to the merged SHA. Then merge the zephyr PR.

**Automation used upstream**

- `zephyrproject-rtos/action-manifest` (https://github.com/zephyrproject-rtos/action-manifest). It compares the old and new manifest, posts a table of changed revisions, adds labels, and adds a `DNM` label when a revision points to a PR. Zephyr's `.github/workflows/manifest.yml` runs it on `pull_request_target` with `check-impostor-commits: true` (SHA must be on the project's real branches). [verified by reading the local workflow file; action read only]
- nRF Connect SDK: `nrfconnect/action-manifest-pr` (https://github.com/nrfconnect/action-manifest-pr). When a PR opens in a project repo (e.g. `sdk-zephyr`), it **auto-creates a PR in the manifest repo** that sets that project to `pull/<nr>/head`, and updates it on push and close. It edits YAML with `ruamel.yaml` so comments stay. The manifest PR's CI then runs the whole downstream test suite. [read]
- `zephyrproject-rtos/action-zephyr-setup` (https://github.com/zephyrproject-rtos/action-zephyr-setup): sets up west, the workspace and the SDK in GitHub Actions; takes `west-group-filter` and `west-project-filter`. [read]
- Memfault Interrupt blog, "Building nRF Connect SDK projects with GitHub Actions": https://interrupt.memfault.com/blog/ncs-github-actions [read, title only]. Golioth reference designs use T2 manifests [read only, not checked in detail].

Maturity: west is stable (1.x, Apache-2.0). Both manifest actions are used every day by large projects, but they fit T1/T2 star setups. For our T3 setup a small custom workflow is simpler (see below).

### 2. Non-firmware repos in a west workspace

- Any git repo can be a west project. It needs no Zephyr content. [verified: syseng/ee/me/framework stubs]
- A repo becomes a Zephyr module when it has `zephyr/module.yml`. All fields are optional; `build: cmake:` and `kconfig:` default to `zephyr/` if present. Other fields: `build.settings` (`dts_root`, `board_root`, …), `package-managers: pip: requirement-files`, `security: external-references`, `blobs`. [read: modules doc]
- Verified: `zephyr_module.py` found the stub repos `syseng` and `ee` (they have `module.yml`) and skipped `sw` (no `module.yml`). [verified]
- Prior art on this machine: `zephyr-school-doctools` is a docs-only Zephyr module with just `name` and `package-managers: pip:`. zdocs has `module.yml` with `build: cmake: .`. [verified by reading]
- **Important for D47:** zdocs doc builds use `find_package(Zephyr REQUIRED ... COMPONENTS doc)` and `west topdir`. So a docs-only CI job still needs west plus a Zephyr checkout (shallow is fine), but **no SDK and no HALs**. Put HALs in a `fw` group and filter it out in docs CI. [read zdocs source]
- `module.yml`'s `package-managers: pip:` lets `west packages pip --install` install each repo's Python needs (e.g. sphinx-needs). [read]

### 3. Devicetree and Kconfig as link points to the model

**Build outputs** [verified]: each build writes `build/zephyr/zephyr.dts` (final tree, with a comment on every line saying which file set it) and `build/zephyr/edt.pickle` (the parsed tree from `edtlib`).

**Parsing** [verified]

- Use Zephyr's own copy: `$ZEPHYR_BASE/scripts/dts/python-devicetree/src`. The pickle needs the same version that wrote it.
- The PyPI package `devicetree` is **0.0.2 and stale**. Do not use it. [verified]
- My extractor (`scripts/dt_extract.py` in scratch) gets, per joint: trace ID, PWM controller and channel, period, pulse range, ADC controller and input, I2C address and bus speed, SPI CS GPIO and max speed, and bus pins (e.g. `i2c1_scl_pb8`, `spi1_sck_pa5`). Output: `dt_facts.json`.
- My checker (`scripts/dt_check.py`) compares that JSON with model values by trace ID. It reports `MISSING`, `MISMATCH` and `UNTRACED`. Run with a planted error, it printed `MISMATCH IF_J1_SERVO_POT.pulse_ns: model=[500000, 2500000] devicetree=[500000, 2400000]` and exited 1.
- Other tools: `dtsh` (devicetree shell/viewer) [read]; Zephyr's `gen_defines.py` uses the same `edtlib`.

**Where to put trace IDs** [verified]

| Option | Result |
|---|---|
| New property on an upstream node (e.g. `trace-id` on the PCA9685 node) | **Build error**: "'trace-id' … is not declared in 'properties:'" |
| Project binding (`robot,joint`, with `trace-id`, `pwms`, `io-channels`, `min-pulse`, `max-pulse`) in the app's `dts/bindings/` | Works. Needs a `vendor-prefixes.txt` entry (`robot`), or you get a warning. The value can also reach C code via `DT_PROP(node, trace_id)`; it showed up in the binary. |
| `zephyr,user` node with free properties (e.g. `pca9685-trace-id = "EE_U3"`) | Works. No binding needed, but no type checks. |
| Node labels (e.g. `joint1:`) | Work, but a label is a C name, not a free ID. |
| Comments in `.overlay` | Lost: the C preprocessor removes them. |

Recommendation: a small **project binding per model concept** (joint, sensor channel, actuator channel). It points to the upstream nodes by phandle and holds `trace-id`. This keeps D5 (the concrete side, SW, holds the link) and D36 (it links to the EE↔SW interface element in syseng).

**Kconfig** [read]: Kconfig has no free attributes. Options: app-level symbols (e.g. `CONFIG_ROBOT_SAMPLE_RATE_HZ`) with the trace ID in the `help` text, read with `kconfiglib` from `build/zephyr/.config` and the Kconfig tree. Use Kconfig for software values (rates, filter lengths). Use devicetree for hardware facts.

### 4. Drivers and board

| Item | Status | Notes |
|---|---|---|
| `nxp,pca9685-pwm` (`drivers/pwm/pwm_pca9685.c`, `CONFIG_PWM_PCA9685`) | Upstream since 2022. Builds. [verified] | Assumes the **internal 25 MHz oscillator** (hard-coded); no EXTCLK support. One prescaler for all 16 channels, so one frequency (fine: all servos at 50 Hz). At 20 ms period the step is ~4.9 µs, about 390 steps over 0.5–2.4 ms. The internal oscillator has a tolerance of a few percent, so the real period and pulse widths are off by the same amount; check with a scope during HIL. A shield exists: `adafruit_pca9685` (Arduino I2C). [read source] |
| `microchip,mcp3208` (`drivers/adc/adc_mcp320x.c`, `CONFIG_ADC_MCP320X`) | Upstream. Builds. [verified] | Only gain 1, `ADC_REF_EXTERNAL0`, default acquisition time, 12-bit. Channels are set as `channel@N` child nodes. Uses its own thread (`CONFIG_ADC_MCP320X_ACQUISITION_THREAD_*`). At 3.3 V the MCP3208 is good to about 1 MHz SPI clock (datasheet [read]); I used `spi-max-frequency = <1000000>`. Pots are ratiometric, so `zephyr,vref-mv` is not needed. |
| `nucleo_g474re` | Upstream board. Arduino aliases: `arduino_i2c` = I2C1 (PB8/PB9), `arduino_spi` = SPI1 (PA5/PA6/PA7, CS PB6 = D10). Runners: stm32cubeprogrammer, openocd, pyocd, jlink. [verified by reading board files] | **PA5 is both SPI1 SCK and the user LED LD2** (`led0`). The board doc warns about this. Do not use `led0` with SPI1, or use SPI2/SPI3. Check the I2C pull-up voltage on the PCA9685 breakout (VCC 3.3 V or 5 V) against the STM32 pin limits. |
| Servo sample | `samples/basic/servo_motor` uses a `pwm-servo` binding that lives **in the sample**, not in Zephyr's main bindings. [verified] | Our `robot,joint` binding replaces it. |

No open upstream bug for either driver came up in a short search [read; not exhaustive].

Sample code: the scratch app `app/` (overlay `boards/nucleo_g474re.overlay`, `src/main.c`): reads pot channel 0 and maps it to the servo pulse on PCA9685 channel 0.

### 5. Tests and traceability

**Twister outputs** [verified with a 2-case ztest on `native_sim/native/64`]

- `twister.json`: `environment` has `zephyr_version` (`v4.4.2-103-gfbab2f598d54`), `toolchain`, `commit_date`, `run_date`. Each suite has `platform`, `status`, `run_id`, and `testcases[].identifier`, e.g. `robot.joint.map.joint_map.endpoints` (the `test_` prefix is dropped).
- `twister_report.xml` (JUnit): one `testsuite` per platform, `testcase classname="robot.joint.map" name="robot.joint.map.joint_map.endpoints"`.
- **Missing:** requirement IDs, app repo SHA, workspace/baseline, firmware hash, board serial.

**Mapping to sphinx-needs** (recommendation; tooling is covered by research 1.1 and 1.8)

1. Test specs are needs in the SW test spec, one per test case, with `:verifies: SWREQ_…` and a field `twister_id: robot.joint.map.joint_map.endpoints`. The test spec is the concrete side, so it holds the link (D5).
2. Optional `@verifies SWREQ_…` doxygen tag above each `ZTEST()`. A check compares it with the test spec need (sphinx-codelinks or a small script).
3. Results come in from `twister_report.xml` (sphinx-test-reports) or `twister.json` (small importer). They link to test-spec needs by `twister_id`.
4. Each run also writes a **build record**: `sha256(zephyr.bin)`, the frozen manifest (`west manifest --freeze`), `zephyr.meta` (all module SHAs + `workspace.dirty`), board, and HIL rig ID. A result is only valid evidence if `dirty: false` and the frozen manifest matches a baseline tag (D40).

**Firmware hash** [verified]: two builds in different build dirs gave the same `zephyr.bin` SHA-256 (`a4e140bb…`). The boot banner includes `git describe` of Zephyr only. Add an app `VERSION` file or `CONFIG_BUILD_OUTPUT_META` for app identity.

**HIL with a hardware map** [read; not run, no board flashed]

- `west twister --generate-hardware-map map.yml` finds connected boards. Then `west twister --device-testing --hardware-map map.yml -p nucleo_g474re -T tests/`.
- Use `harness_config: fixture: joint_rig` in `testcase.yaml` and `fixtures: [joint_rig]` in the map, so HIL tests run only on the wired rig.
- For real servo/pot checks, use the `pytest` harness (pytest-twister-harness) to talk to the shell over serial.
- The user already uses a hardware map (`ws-b/hw-map.yaml`, an STLINK-V3 board). openocd is installed. [verified]

**Zephyr's own requirements work** [read]

- `zephyrproject-rtos/reqmgmt`: StrictDoc, about 226 commits, README says "preliminary work". Published at https://zephyrproject-rtos.github.io/reqmgmt/. Docs list "link requirements to test cases" as a next step, not as done.
- Zephyr docs (`doc/project/documentation.rst`) define doxygen aliases `@satisfy{@req{N}}` (code) and `@verify{@req{N}}` (tests), with a plan to parse doxygen XML into a matrix. The aliases exist in `zephyr.doxyfile.in`, but **0 tests in `tests/` use `@verify{`**. [verified grep]
- Safety process docs: https://docs.zephyrproject.org/latest/safety/safety_requirements/index.html
- Conclusion: the idea (tags in code, matrix built from parsed output, links held by the test) matches D5. There is no ready tool to reuse.

### 6. Parameter exchange (one source for shared values)

- Prior art: I found **no** open tool that takes values from SysML v2 into devicetree, KiCad fields and FreeCAD spreadsheets. Papers show SysML → CAD parameters (e.g. Fraunhofer FreeCAD macro), but not for this toolset. [read, short search]
- Values and where they live:

| Value | Owner (proposal) | Devicetree / Kconfig | KiCad | FreeCAD |
|---|---|---|---|---|
| Pin and bus map (I2C1 PB8/PB9, SPI1, CS PB6) | syseng interface element (D36) | overlay, pinctrl | net labels, symbol fields | — |
| PCA9685 address, channel per joint | syseng interface | `reg`, `pwms` cell | address jumpers, field | — |
| PWM period, pulse min/max | syseng (servo spec) | `pwms` period, `min-pulse`/`max-pulse` | — | — |
| ADC resolution, channel per joint | syseng | `channel@N`, `zephyr,resolution` | field | — |
| Sample rate | syseng performance req | Kconfig symbol | — | — |
| Link lengths | syseng / ME | (only if kinematics in SW) | — | Spreadsheet aliases |

- **Recommendation: check first, generate later.**
  - Devicetree is a rich language (phandles, macros, includes, board files). Generating it from SysML hides that from SW engineers and agents. A check (extract facts → compare to model) is easy and is already working (§3).
  - For flat values (rates, link lengths, pulse ranges), a **generated read-only parameter file** works: e.g. a JSON/YAML exported from SysML attributes. Then: a Kconfig fragment or C header for SW, a FreeCAD spreadsheet import, KiCad text variables. Mark generated files and check them in CI, the same way as D42 stubs.
  - Do not generate pinctrl or bus nodes in iteration 1.

### 7. SPDX / `west spdx` (prior art for the bundle, iteration 2)

[verified]

```
west spdx --init -d build3
west build -b nucleo_g474re -d build3 . -- -DCONFIG_BUILD_OUTPUT_META=y
west spdx -d build3
```

- Without `CONFIG_BUILD_OUTPUT_META=y`, it fails: "cannot find a valid zephyr.meta".
- Output: `app.spdx`, `zephyr.spdx`, `build.spdx`, `modules-deps.spdx` (SPDX 2.3 tag-value). Packages use `PackageDownloadLocation: git+<url>@<sha>`; files have SHA1/SHA256 checksums; module CPE/PURL refs come from `module.yml` `security:`.
- `zephyr.meta` lists every west project with remote, SHA and a `-dirty` suffix, plus `workspace: dirty: true/false`. This is exactly the "which baseline built this firmware" record we need.
- Only SPDX 2.2/2.3, no 3.0, in 4.4.2. It covers sources and the binary, not docs or CAD. A bundle manifest for docs/CAD could follow the same pattern.

## Recommended multi-repo GitHub workflow

Repos: `manifest` (T3, D14), `framework`, `syseng`, `ee`, `me`, `sw`. Plus `zephyr` and `zdocs` as upstream projects.

**Manifest (`manifest/west.yml`)**

```yaml
manifest:
  version: "1.2"
  remotes:
    - name: proj
      url-base: https://github.com/<org>
    - name: zephyrproject-rtos
      url-base: https://github.com/zephyrproject-rtos
  projects:
    - name: zephyr
      remote: zephyrproject-rtos
      revision: v4.4.2            # tag, not a branch (D19, D39)
      import:
        name-allowlist: [cmsis_6, hal_stm32]
        # docs-only CI can skip the HALs with: west config manifest.project-filter -- -cmsis_6,-hal_stm32
    - name: zdocs
      url: https://github.com/tiacsys/zdocs
      revision: <sha>
    - { name: framework, remote: proj, revision: <sha> }
    - { name: syseng,    remote: proj, revision: <sha> }
    - { name: ee,        remote: proj, revision: <sha>, groups: [hw] }
    - { name: me,        remote: proj, revision: <sha>, groups: [hw] }
    - { name: sw,        remote: proj, revision: <sha> }
  self:
    path: manifest
```

Every project is pinned to a SHA or tag on `main` (D39). Baselines are tags of this repo (D40).

**A. Change in one repo**

1. PR in e.g. `syseng`. Its CI: `west init -m <manifest> && west update --narrow -o=--depth=1`, then check out the PR head in `syseng/`, then run the docs build and trace checks (D47). Upstream repos come from the manifest's `main` (D39).
2. Merge.
3. A workflow in `syseng` on `push: main` sends a `repository_dispatch` to `manifest`. A workflow there opens or updates a **bump PR** "syseng → <sha>". The bump PR's CI builds the full linked set (D26) and runs all trace checks across repos. If green, it auto-merges (or a human or agent approves).

**B. Change across several repos** (e.g. syseng interface + sw overlay)

1. One PR per repo. Each PR body has a trailer `Manifest-PR: <org>/manifest#<n>`.
2. One **manifest PR** (draft) that sets each touched project to `revision: pull/<n>/head`. This works with west (verified). It can be made by hand or by a bot copied from `nrfconnect/action-manifest-pr`.
3. Component PR CI: if the trailer exists, use that manifest PR's `west.yml` instead of `main`. This lets the `sw` PR see the unmerged `syseng` change. This is a small **extension of D39**.
4. The manifest PR's CI is the gate. It builds the full set with all PR heads together.
5. Merge the component PRs, upstream first (syseng → ee/me → sw).
6. Update the manifest PR to the **merged** SHAs (with squash or rebase merges, the PR head SHA is not on `main`). A check rejects any `pull/` revision or any SHA not on the project's `main` (like `check-impostor-commits`). Then merge the manifest PR.

**C. Local** (D46): `west update` then one command per repo (e.g. `west check` as a west extension command in `framework`, listed via `west-commands` in `framework`'s `module.yml`/manifest). Firmware build and Twister/HIL run locally until the Docker image exists (D47).

**Comment bot (optional):** run `zephyrproject-rtos/action-manifest` on the manifest repo for the revision diff table and the `DNM` label. It is built for this and works on any west manifest repo.

## Hands-on results

All runs used the `ws-t` workspace's venv and Zephyr 4.4.2 **read-only** (`git status` in `ws-t/zephyr` was clean after the runs). Output went to the scratch dir. Side effect outside scratch: Zephyr writes its normal cache to `~/.cache/zephyr`.

| # | Command / step | Result |
|---|---|---|
| 1 | `west --version`, `echo $ZEPHYR_BASE`, search for workspaces | No global west, no `ZEPHYR_BASE`. Found `ws-up` (Zephyr main 4.4.99 + SDK 1.0.1), `ws-t` (Zephyr 4.4.2, manifest in `trainings/…/west.yml`), `ws-b` (Bridle, `hw-map.yaml`). west 1.5.0 in each `.venv`. cmake 4.5.0, ninja 1.13.2. |
| 2 | `ZEPHYR_BASE=…/ws-t/zephyr west build -b nucleo_g474re -d <scratch>/build -p always app` | **Success.** SDK 1.0.1, GCC 14.3.0. FLASH 43740 B (8.34 %), RAM 8 KB. `CONFIG_PWM_PCA9685=y`, `CONFIG_ADC_MCP320X=y`. First run warned "unknown vendor prefix 'robot'"; fixed with `dts/bindings/vendor-prefixes.txt` in the app. |
| 3 | Extra overlay adding `trace-id` to the PCA9685 node | **Build error** (property not declared in binding). |
| 4 | Extra overlay with `zephyr,user { pca9685-trace-id = "EE_U3"; … }` | Works; values appear in `zephyr.dts`. |
| 5 | `pip install devicetree` in scratch venv | Installs 0.0.2 (stale). Used in-tree `python-devicetree` instead. |
| 6 | `python dt_extract.py build` (loads `edt.pickle`) | **Success.** JSON with trace ID, PWM channel 0 / 20 ms / 0.5–2.4 ms, ADC input 0, I2C1 @0x40 400 kHz on PB8/PB9, SPI1 CS PB6, 1 MHz, pins PA5/PA6/PA7. |
| 7 | `python dt_check.py dt_facts.json model_params.json` (planted error) | Reported the pulse mismatch, exit 1. |
| 8 | `west twister -T ztest_demo -p native_sim/native/64` | **2/2 passed.** Wrote `twister.json`, `twister.xml`, `twister_report.xml`. Contents as in §5. |
| 9 | `west spdx --init` + build + `west spdx` | Failed first ("no zephyr.meta"). With `-DCONFIG_BUILD_OUTPUT_META=y`: **success**, 4 SPDX 2.3 files. |
| 10 | `sha256sum` of `zephyr.bin` from two build dirs | Identical (`a4e140bb…8d2965`). |
| 11 | Local T3 workspace from bare git repos (`manifest`, `framework`, `syseng`, `ee`, `me`, `sw`); `west init -m file://…/manifest`, `west update` | **Success.** Group filter `-hw` skipped ee/me; `+hw` added them. `west manifest --freeze` gave SHAs. |
| 12 | Set `sw` to `revision: pull/7/head` (fake PR ref) and `west update sw` | **Success**: checked out the PR commit. |
| 13 | `zephyr_module.py --modules syseng ee sw` | Found `syseng` and `ee` (have `module.yml`), skipped `sw`. |

Not done: flashing, HIL, Twister on the real board (no hardware access allowed).

## Recommendations

1. Pin Zephyr to **tag `v4.4.2`** (installed and tested), not `v4.4-branch`. Use `name-allowlist: [cmsis_6, hal_stm32]`.
2. Use the multi-repo workflow above: auto **bump PRs** on every merge, a **manifest PR** with `pull/N/head` for cross-repo changes, and a `Manifest-PR:` trailer so component CI can see co-dependent changes.
3. Give syseng, ee, me and framework a `zephyr/module.yml` (name + pip requirements). Docs CI fetches Zephyr shallow, no SDK, HALs filtered out.
4. Put the devicetree link in a **project binding** (`<prefix>,joint`) with `trace-id`. Check the overlay against the model with an `edt.pickle` extractor plus checker. Do not generate overlays in iteration 1.
5. Keep shared flat values in **one generated, read-only parameter file** exported from SysML. Use it for Kconfig/C header, FreeCAD spreadsheet and KiCad text variables, checked in CI like the D42 stubs.
6. Test traceability: one test-spec need per Twister test-case ID, holding `:verifies:`. Import JUnit/`twister.json` results. Add a **build record** (`sha256(zephyr.bin)`, `west manifest --freeze`, `zephyr.meta`) to every result.
7. Turn on `CONFIG_BUILD_OUTPUT_META=y` in the app. It is cheap and gives the SBOM and the baseline record.
8. Hardware: avoid `led0` (PA5) with SPI1, or move the MCP3208 to SPI2. Measure the real PCA9685 period once and record it.
9. Add the `robot`-style vendor prefix to the project prefix scheme (D17).

## Risks and open questions

- **D39 bump lag.** Strict SHA pinning means downstream repos see upstream changes only after a bump PR merges. Without automation this will stall work. Bump bot is required, not optional.
- **D39 co-dependent PRs.** "Build against manifest `main`" fails when two PRs need each other. The `Manifest-PR` trailer is a needed refinement of D39.
- **Squash merges change SHAs.** A manifest PR that pins `pull/N/head` must be updated after merge. Needs a CI check.
- **D47 docs CI needs Zephyr.** zdocs uses `find_package(Zephyr COMPONENTS doc)`, so docs CI must fetch Zephyr (no SDK). Cost: clone time; use shallow, narrow clones and caching.
- **SDK location.** SDK 1.0.1 sits inside `ws-up`, found via `~/.cmake/packages`. If `ws-up` is moved or deleted, all builds break. Record this in `toolchain.md` (4.1).
- **`edt.pickle` is version-bound.** Tools must load the in-tree `python-devicetree` of the pinned Zephyr.
- **PCA9685 accuracy.** Internal oscillator tolerance gives a few percent error on servo pulses. Matters for pose accuracy requirements.
- **HIL results storage in iteration 1.** D38 says HIL results go into the bundle, but D43 moves bundles to iteration 2. Where do iteration-1 HIL results live (committed JSON in `sw`? release asset on the manifest tag?)? Open.
- **Zephyr's own requirements/test tracing is immature**: nothing to reuse directly; our own tags and importers are needed.
- Open: should HALs be a `fw` group in our manifest (needs the imported projects to carry groups), or is a `west-project-filter` in CI enough? Test in Phase 4.

## Sources

- West workspaces/topologies: https://docs.zephyrproject.org/latest/develop/west/workspaces.html
- West manifest reference: https://docs.zephyrproject.org/latest/develop/west/manifest.html
- Modules and module change process: https://docs.zephyrproject.org/latest/develop/modules.html
- action-manifest: https://github.com/zephyrproject-rtos/action-manifest
- action-manifest-pr (Nordic): https://github.com/nrfconnect/action-manifest-pr
- action-zephyr-setup: https://github.com/zephyrproject-rtos/action-zephyr-setup
- example-application (T2 template): https://github.com/zephyrproject-rtos/example-application
- Memfault, NCS with GitHub Actions: https://interrupt.memfault.com/blog/ncs-github-actions
- Twister: https://docs.zephyrproject.org/latest/develop/test/twister.html
- Zephyr safety requirements: https://docs.zephyrproject.org/latest/safety/safety_requirements/index.html
- reqmgmt: https://github.com/zephyrproject-rtos/reqmgmt and https://zephyrproject-rtos.github.io/reqmgmt/
- Zephyr code documentation / traceability tags: https://docs.zephyrproject.org/latest/project/documentation.html
- Adafruit PCA9685 shield in Zephyr: https://docs.zephyrproject.org/latest/boards/shields/adafruit_pca9685/doc/index.html
- `west spdx`: https://docs.zephyrproject.org/latest/develop/west/zephyr-cmds.html
- Local source read: `ws-t/zephyr/drivers/pwm/pwm_pca9685.c`, `drivers/adc/adc_mcp320x.c`, `boards/st/nucleo_g474re/*`, `.github/workflows/manifest.yml`, `doc/project/documentation.rst`, `doc/zephyr.doxyfile.in`
