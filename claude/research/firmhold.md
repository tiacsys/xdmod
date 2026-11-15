# Research 1.10 — firmhold (the owner's bundle tool)

Source: `extra/firmhold` (local git repo, `main` at `97ff883`, 36 commits, version `0.1.0.dev0`, Apache-2.0,
"pre-alpha scaffold, API not stable" — `README.md:11`). The repo was only read. All hands-on work ran on a
clone in the scratch dir.

Marks: **[verified]** = I ran it. **[read]** = I read code or docs only. **[fake-reg]** = I ran it against a
small in-memory OCI registry I wrote (not a real registry).

Paths below are relative to `extra/firmhold/`.

## Summary

- firmhold packs **one Zephyr build** into an OCI "deployment container": a manifest with one layer per file
  (`zephyr.bin/.hex/.elf` as *payload*, `.config`, `zephyr.dts`, `zephyr.map`, `build_info.yml` as
  *provenance*). It pushes this to any OCI registry, keeps a **release index** per version (one member per
  board), and can **sign** a container or an index with ES256. **[verified]**
- Working CLI today: `pack`, `list`, `show`, `pull`, `export`, `sign`, `verify` (`src/firmhold/cli.py:1004-1011`).
  An exported folder verifies **offline with `sha256sum` and `openssl`** alone. **[verified]**
- **Not built yet** (docs only, each tutorial says "does not work yet"): `test-result`, `attach` (SBOM),
  `attest` (in-toto/SLSA/DSSE), cosign, `collect-twister`, `query`, Twister ingestion, SUIT, `west deploy`.
  The README promises these; the code does not have them.
- **GHCR gap:** GHCR has no native OCI Referrers API. firmhold's fallback for this is not built
  (`doc/explanation/decisions/0013-native-signing.rst:95-101,134-137`). So on GHCR, `pack/list/show/pull/export`
  should work, but signatures (and any future test-result referrers) cannot be found again. Only a fully
  conformant registry (Zot, ACR, ECR) works for sign/verify today. **[read]**
- **Non-firmware outputs:** the core model is generic enough. I pushed docs (tarball), `needs.json`, Gerbers,
  STL and a JUnit file through the library API, and `show`/`export`/`sign` handled them. **[fake-reg]** But there
  is no CLI path for this (only the Zephyr adapter), files must be flat (no folders), and export names collide
  when two files share an extension (two `.gbr` files → error). **[verified on fake-reg]**
- A whole **bundle can be one signed release index** whose members are separate containers (firmware, docs,
  CAM-EE, CAM-ME, HIL results). I did this with the existing index code by using the "board" field as a
  component name. One signature over the index covers everything, and it verified offline. **[fake-reg]**
  This is a workaround; "board" is the wrong word for it.
- **Iteration 1:** firmhold cannot record HIL results yet. But the firmware's layer digest is simply
  `sha256(zephyr.bin)`. If iteration 1 records that hash with each HIL result, the evidence will match the
  digest a later firmhold container holds. No rework.
- **Plan conflicts:** D38 ("HIL results are packaged with the bundling tool") cannot be met with today's
  firmhold. D54's `baseline/vX.Y.Z` is not a legal OCI tag, and firmhold does not clean up the version string
  (it does clean up the board).
- The unit and acceptance tests pass: **345 passed, 1 skipped** (the opt-in live GHCR probe). **[verified]**
  Note: the acceptance suite started a Zot container with docker, and docker **pulled the Zot image** as a
  side effect (see Hands-on results).

## Answers

### 1. What firmhold does today (implemented vs. planned)

| Feature | Status | Evidence |
|---|---|---|
| Pack a Zephyr build dir into an OCI container | **Implemented** | `src/firmhold/adapters/zephyr/__init__.py:112-191`, `src/firmhold/core/oci.py:770-838` |
| Fixed file set: 3 payload + 4 provenance files, typed media types | **Implemented** | `adapters/zephyr/__init__.py:26-41`; ADR `0015-provenance-capture.rst:36-80` |
| App/board from `CMakeCache.txt`; version from `git describe --tags`; source = `commit <short sha>` | **Implemented** | `adapters/zephyr/__init__.py:101-109,144-153` |
| Per-board tag `<version>-<board>` + release index at `<version>` | **Implemented** | `core/oci.py:752-767,1046-1150`; ADR `0012` |
| `list`, `show`, `pull`, `export` (flat folder of files + `descriptor.json` + `manifest.json` + `.sig`) | **Implemented** | `cli.py:342-770`, `core/oci.py:1624-1769` |
| Native ES256 sign/verify of a container or release index (detached DER sig as a referrer, public key in an annotation) | **Implemented** | `core/trust.py:225-600`; ADRs `0013`, `0014` |
| Offline verify with `sha256sum` + `openssl` | **Implemented** | `doc/tutorials/sign-a-build.rst:116-178`; FH13 |
| Generic referrer push primitive (`push_referrer`, `list_referrers`) | **Implemented in library**, used only by signing | `core/oci.py:862-1007` |
| Registry auth: Basic and Bearer (PAT → token), creds only from `~/.docker/config.json` `auths` | **Implemented** | `core/oci.py:86-137,233-307`; `registries/github.rst:7-17` |
| Referrers **fallback tag** scheme (`sha256-<digest>`) for GHCR/GitLab | **Planned** | ADR `0003:38-41`; ADR `0013:95-101,134-137`; `registries/github.rst:18-20` |
| Delete / retention backend, GHCR delete via GitHub API | **Planned** | `registries/index.rst:27-29`; `registries/github.rst:21-22` |
| `test-result` command, Twister ingestion, `collect-twister`, `pull --platforms` | **Planned** | `doc/tutorials/record-test-results.rst:4-8`; ADR `0002:29-32`; `explanation/adapters/zephyr.rst:6-8,17-18` |
| `attach --type sbom` (SPDX), VEX | **Planned** | `doc/tutorials/attach-an-sbom.rst:4-8,47-49` |
| `attest` (in-toto Statement + SLSA provenance + DSSE) | **Planned** | `doc/tutorials/attest-provenance.rst:4-8,24-39`; `explanation/trust-stack.rst` |
| cosign key / keyless sign and verify | **Planned** | `doc/tutorials/release-with-cosign.rst:4-8`; `verify-as-auditor.rst:4-8` |
| `core.attach`, `core.collection`, `query` | **Planned** | `architecture/building-blocks.rst:56-62,89-94` |
| Offline export/import as an OCI image-layout archive | **Planned** (scope note only) | ADR `0003:73-76`; no code (`grep` finds nothing) |
| Project-definable "which files to include" policy | **Deferred** until a second adapter exists | ADR `0015:129-142` |
| SUIT emission, `west flash`, `west deploy` shim | **Planned** | ADR `0002:29-40`; `adapters/zephyr.rst:21-26,90-103` |

Other notes from the code:

- The container digest covers metadata as well as files: app, version, board, the provenance string and
  `build_info.yml` (which holds absolute paths). So two machines that build the same commit get **different
  container digests** (ADR `0015:166-173`). The **layer digest** of `zephyr.bin` is just its SHA-256 and does
  not change. **[verified: the same `zephyr.bin` had the same layer digest in two containers with different digests]**
- `verify` passes if **at least one** signature checks out ("existential"), so a junk referrer cannot block a
  good one (ADR `0013:82-117`).
- Signing an index covers the set **as it was at signing time**. Re-packing moves the tag, and the old
  signature is orphaned. `pack` prints a note about this (ADR `0014:43-99`).
- CI: GitHub Actions workflow exists but is "retained, unused". The real CI is GitLab, and it has no runner.
  The real gate is `make check` with a pre-push hook (ADR `0009`, ADR `0010`).

### 2. Fit with our bundle (D24, D40)

**Can a bundle hold non-firmware outputs?** Yes in principle, no in practice through the CLI.

- The model is neutral: a `DeploymentDescriptor` is `app, version, board, provenance, representations[]`, and
  each representation has `name, media_type, digest, role` (`core/model.py:32-118`). Nothing ties it to
  firmware except the word "board" and the `payload`/`provenance` roles.
- An unknown role (I used `docs` and `cam`) is shown as an `other` group and is still exported
  (ADR `0016:89-116`). **[fake-reg]**
- Limits I hit:
  - **Only one adapter.** `pack` only knows Zephyr (`cli.py:47-49`). There are no `--app/--version/--board`
    flags (`doc/reference/cli.rst:44-45`). Packing docs or CAM needs Python code or a new adapter.
  - **Flat names only.** A name must be one path part, with no `/` (`core/oci.py:1469-1497`; ADR `0016:33-45`).
    An HTML site must be packed as one tarball.
  - **Export names use only the file extension** for non-provenance roles (`core/oci.py:1596-1621`).
    `docs-html.tar.gz` exported as `robarm-0.1.0-docs.gz` and `needs.json` as `...-docs.json`. Two Gerber
    layers in one container failed: `export naming collision` **[verified on fake-reg]**. A KiCad CAM set
    (about 10 Gerber layers, a drill file, a pos file) cannot be exported this way as separate files today.
  - **Version is used raw in the tag.** `container_tag` cleans the board but not the version
    (`core/oci.py:752-767`). A git tag like `baseline/v0.2.0` became the tag `baseline/v0.2.0-nucleo_g474re`.
    My fake registry accepted it, but a real registry will refuse it (`/` is not allowed in a tag).
    **[fake-reg; real-registry failure is read only]**

**One artifact with many layers, or a referrer graph?** Use firmhold's own split rule (ADR `0015:36-57`):

- **Layers** = files made by the same build step that should be covered by the same signature
  (firmware + its `.config`/`.dts`/`.map`; docs HTML + `needs.json`; a Gerber set + drill + pos).
- **Referrers** = claims made later, often by another actor, about an existing digest
  (signature, HIL test result, SBOM, review approval).
- **Bundle** = one **release index** at the baseline version. Its members are one container per output kind.
  One signature over the index covers all members through their digests (ADR `0014:43-64`). I built this
  with today's code (members `fw-nucleo_g474re`, `docs`, `cam-me`), signed the index, exported it, and
  `openssl dgst -verify` said `Verified OK`. **[fake-reg]**

**Adapters we would need** (the owner's ADR `0015:129-142` waits for exactly this "second adapter"):

| Adapter | Input | Layers |
|---|---|---|
| `files` (generic, smallest step) | a small YAML list: path, media type, role | anything; would fix most of the gaps above |
| `kicad` | `kicad-cli` / KiBot output folder | Gerbers, drill, pos, BOM, schematic PDF/SVG, netlist, ERC/DRC report |
| `freecad` | `FreeCADCmd` export folder | 3MF, STL, print profile (D30), TechDraw SVG/PDF, parameter spreadsheet CSV |
| `docs` (zdocs/Sphinx) | Sphinx build dir | HTML site as a tarball, `needs.json`, trace/coverage report |
| `hil` (or the planned Twister ingestion) | `twister.json`, `twister_report.xml`, hardware map, rig ID | test-result referrer on the firmware container |

Each adapter must also allow a version from outside (the baseline), because the version must not come from
`git describe` of one repo.

### 3. HIL and test results (D38, D43)

- **Today:** firmhold has **no** way to record a test result through the CLI. The target design is
  `firmhold test-result <ref> --outcome --suite --runner --file twister.json --source-commit` which pushes a
  test-result **referrer** whose subject is the firmware container's digest
  (`doc/tutorials/record-test-results.rst:24-46,98-114`).
- The tutorial names two kinds of link (`record-test-results.rst:116-131`):
  - **digest link** — the test ran these exact bytes (our HIL case: Twister flashes the real `zephyr.bin`);
  - **commit link** — a test matrix built from the same commit (our ztest/native_sim case). firmhold does not
    check this join.
- **Library workaround:** `push_referrer` works for any claim. I pushed a JUnit file as a test-result
  referrer with annotations `outcome=pass`, `rig=nucleo-rig-1`, `baseline=baseline/v0.1.0`, and
  `list_referrers` found it next to the signature. **[fake-reg]** But `show` and `export` ignore it
  (`export` writes only `.sig` referrers — `cli.py:708-720`). So it is invisible to users. It also will not
  work on GHCR (no Referrers API, see section 5).
- **Iteration 1 (bundles moved to iteration 2 by D43):** do not depend on firmhold. Record, per HIL run, a
  small **build record** as zephyr-west.md (§5, item 4) already proposes: `sha256(zephyr.bin)`,
  `west manifest --freeze`, `zephyr.meta`/dirty flag, board, rig ID, plus `twister.json` and the JUnit XML.
  `sha256(zephyr.bin)` is **exactly** the layer digest firmhold stores for `zephyr.bin`, so iteration-1
  evidence can be linked to an iteration-2 container without changes. **[verified: layer digest = `sha256sum`]**
- Possible in iteration 1 for a demo only: `firmhold pack` + `sign` of the firmware to a local Zot.
  Do not build iteration-1 evidence on it.

### 4. Traceability links (sphinx-needs ↔ OCI digests ↔ git)

- **Yes, a need can point at a digest.** A verification-evidence need can carry fields such as
  `fw_sha256: 69d5e4…` (the `zephyr.bin` layer digest), `oci_ref: ghcr.io/tiacsys/robarm-bundle@sha256:…`
  (container or index) and `baseline: baseline/v0.1.0`. A digest never moves; a tag can (ADR `0012`,
  `content-addressing.rst:28-32`).
- **Which digest to cite:**
  - `sha256(zephyr.bin)` = "which firmware". It is stable and the same on every machine if the build is
    reproducible.
  - Container manifest digest = "which signed package". It changes with metadata and `build_info.yml`
    paths (ADR `0015:166-173`).
  - Index digest = "which bundle". It changes every time a member is re-packed (ADR `0014:43-64`).
- **Cycle to avoid:** the docs container is inside the bundle. So the docs cannot quote the bundle index
  digest (or their own digest). The docs may quote the firmware digest and the HIL result, because those
  are made earlier. The bundle digest is shown only outside the bundle (GitHub release notes, the Pages
  landing page, or the signed index itself).
- **Git SHAs:** firmhold records only `commit <short sha>` of the **app repo** and `git describe --tags`
  (`adapters/zephyr/__init__.py:101-109`). It records **no dirty flag**: I changed the source tree and `pack`
  still said `version=v0.1.0`. **[fake-reg]** It does not record the manifest baseline or other repo SHAs.
  Fix on our side: add `west manifest --freeze` output (and `zephyr.meta`) as a provenance layer of every
  container, and put the baseline tag in the descriptor's `provenance` text.
- **KiCad/FreeCAD stamping:** the stamp shows the **ee/me repo's** SHA (kicad.md, line 124), and it is inside
  the exported Gerbers/PDFs/SVGs. Those bytes are layers, so the layer digest covers the stamp too. The frozen
  manifest in the bundle then maps baseline → repo SHAs → stamped files. All three can be checked offline.

### 5. GitHub fit (D48, D54, D55)

- **GHCR as the registry** for `ghcr.io/tiacsys/robarm-*`: pack/pull/list/show/export should work (Bearer auth
  is implemented and tested against a fake; there is an opt-in live probe `tests/acceptance/test_ghcr_probe.py`
  that "is never run in CI"). **[read]** Nobody has confirmed that GHCR accepts the custom media types (that is
  the probe's purpose).
- **Blocking for trust on GHCR:** no Referrers API on GHCR, and firmhold's fallback is not built. Signing would
  push the signature, but `verify` and `export` would not find it (`core/oci.py:603-655` treats 404 as "no
  referrers"). **[read]** Until the fallback exists, either use a conformant registry or rely on the exported
  folder (the `.sig` must then be made where the referrer can be read back).
- **Credentials:** only `auths.<host>.auth` in `~/.docker/config.json` is read; credential helpers
  (`credsStore`/`credHelpers`) are not supported (`core/oci.py:98-137`). On a GitHub runner,
  `docker/login-action` writes `auths`, so it works. On a desktop with a credential helper, it will not find
  the PAT. Anonymous reads of public packages should work through the Bearer flow (no creds → anonymous
  token). **[read]**
- **Workflow on `baseline/*` tags** (iteration 2), sketch:
  1. `on: push: tags: ['baseline/v*']`, `permissions: packages: write, contents: write`.
  2. `west init -l` + `west update` at the tag; save `west manifest --freeze`.
  3. Build or collect the outputs: firmware (needs the Zephyr SDK image, D19/D47), docs, CAM.
  4. `firmhold pack` per component with `--version 0.1.0` (flag does not exist yet) into
     `ghcr.io/tiacsys/robarm-bundle`.
  5. `firmhold sign <repo>:0.1.0` (key from an Actions secret; later cosign keyless with the workflow identity).
  6. `firmhold export <repo>:0.1.0 --outdir out/` and upload `out/*` as **GitHub release assets** (D31, D54).
  7. Write the index digest into the release notes and the Pages version folder (D55).
- **Offline check by a reviewer:** download the release assets, then `sha256sum *.manifest.json`, compare the
  digests listed in the manifests with `sha256sum` of each file, and run
  `openssl dgst -sha256 -verify robarm.pub -signature robarm-0.1.0.sig robarm-0.1.0.manifest.json`.
  No firmhold and no network needed. **[verified on fake-reg export]**
- **Tags:** an OCI tag cannot contain `/`. Map `baseline/v0.1.0` → OCI tag `0.1.0` (or `baseline-v0.1.0`) and
  keep the real git tag in the descriptor's `provenance` text.

### 6. Gaps, risks, findings

See "Findings for the owner" and "Risks and open questions" below.

## Hands-on results

Setup: `git clone extra/firmhold` → `scratchpad/research-firmhold/firmhold`; `uv venv` +
`uv pip install -e ".[dev]"`. `firmhold --version` → `firmhold 0.1.0.dev0`. **[verified]**

| # | Command | Result |
|---|---|---|
| 1 | `pytest -q` (whole suite, 323 unit + 23 acceptance) | **345 passed, 1 skipped** in 95 s. The skipped test is the opt-in GHCR probe. |
| 1a | (side effect) | The acceptance fixtures run `docker run ghcr.io/project-zot/zot-linux-amd64:latest` when docker works (`tests/acceptance/conftest.py:37-61`). The image was not on this machine, so **docker pulled it** (LastTagTime 2026-11-14 20:17 UTC, 330 MB). This broke the "no docker pulls" rule; I did not expect the suite to do this. No container was left running. Remove it with `docker rmi ghcr.io/project-zot/zot-linux-amd64:latest` if you do not want it. Good side: the 22 acceptance scenarios (pack … sign/verify/offline) **passed against a real Zot**. |
| 2 | Wrote `scripts/minireg.py`: an in-memory OCI v2 registry with the Referrers API, on `127.0.0.1:5077` | Works with firmhold (localhost → plain http). |
| 3 | Fake west build dir (`CMakeCache.txt` with `CACHED_BOARD=nucleo_g474re`, `CMAKE_PROJECT_NAME=robarm-joint`, app repo tagged `v0.1.0`; dummy `zephyr.bin/hex/elf`, `.config`, `zephyr.dts`, `zephyr.map`, `build_info.yml`) → `firmhold pack build --repo localhost:5077/tiacsys/robarm-sw-fw` | `captured 3 payload, 4 provenance`, tag `v0.1.0-nucleo_g474re`, index `v0.1.0 (1 platform)`. |
| 4 | `list`, `show` | As documented; `show` prints `source commit 2073a98` and digests per file. |
| 5 | `openssl ecparam … -out ci-es256.pem`; `firmhold sign` on the container and on the index; `verify --key ci.pub`; `verify` without key | Both signed. Pinned: `PASS (pinned key)`. Unpinned: `PASS (self-embedded key)` + `WARNING: integrity only`. |
| 6 | `firmhold export …:v0.1.0 --outdir release`; then `sha256sum` + `openssl dgst -verify` on index and container manifests | `sha256sum` of `*.manifest.json` = the digests; `zephyr.bin` hash = its layer digest; **`Verified OK`** twice. |
| 7 | Library script: one container with `docs-html.tar.gz`, `needs.json` (role `docs`), a Gerber + STL (role `cam`), `junit.xml` (role `provenance`) | Pushed. `show` lists `provenance` + `other` groups; `list` says `1 provenance 4 other`. Export wrote `…-baseline.gz`, `…-baseline.json`, `…-baseline.gbr`, `…-baseline.stl` — original names lost. |
| 8 | Library: `push_referrer` of `junit.xml` onto the firmware digest with outcome/rig/baseline annotations | `list_referrers` shows the signature and the test result. `verify` still PASS. `export` does **not** include the test result. |
| 9 | Two `.gbr` files in one container → `export` | `error: export naming collision … 'robarm-cam-v0.1.0-pcba-main.gbr'`, exit 1. |
| 10 | Edit the app source (dirty tree) → `pack` | `version=v0.1.0`, no dirty marker. |
| 11 | One commit after the tag → `pack` | `version=v0.1.0-1-ge125955`, tag `v0.1.0-1-ge125955-nucleo_g474re`. |
| 12 | Tag the app repo `baseline/v0.2.0` → `pack` | Tag sent as `baseline/v0.2.0-nucleo_g474re` (illegal in OCI). My lenient fake registry accepted it; a real one will refuse it. |
| 13 | Library: bundle as **release index** in one repo `tiacsys/robarm-manifest-bundle`, version `0.1.0`, members `fw-nucleo_g474re` (from the Zephyr adapter, with app/version/board replaced), `docs`, `cam-me` → `firmhold sign …:0.1.0` → `export` → `openssl` | `list` shows `0.1.0 index robarm 3 platforms`. Export wrote every member plus `robarm-0.1.0.manifest.json` + `.sig`; **`Verified OK`**. The firmware container digest changed (other metadata), but the `zephyr.bin` layer digest did not. |

Scratch files: `/tmp/claude-1000/-home-tobias-z-wrk-ws-syseng/cc4a5268-5423-4e94-be0d-4c1055bbe07f/scratchpad/research-firmhold/`
(`scripts/minireg.py`, `scripts/bundle_try.py`, `scripts/bundle_index.py`, `scripts/collide.py`, `work/`).

## Proposed bundle layout for this project (sketch)

One OCI repo per project: `ghcr.io/tiacsys/robarm-bundle`. One bundle per baseline.

```text
ghcr.io/tiacsys/robarm-bundle
│
├── :0.1.0   ← release index = THE BUNDLE for manifest tag baseline/v0.1.0
│     annotations: app=robarm, version=0.1.0, (wanted) baseline=baseline/v0.1.0, manifest-sha=<sha>
│     signed once (ES256 now; cosign keyless from the baseline workflow later)
│     members (one container each, "board" slot = component):
│
│   ├── :0.1.0-fw-nucleo_g474re   firmware (Zephyr adapter)
│   │     payload:    zephyr.bin, zephyr.hex, zephyr.elf
│   │     provenance: .config, zephyr.dts, zephyr.map, build_info.yml,
│   │                 west-manifest.frozen.yml, zephyr.meta, spdx/*.spdx (or SBOM as referrer)
│   │     referrers:  signature; HIL test result (twister.json + JUnit, rig ID, outcome)
│   │
│   ├── :0.1.0-docs               docs (docs adapter)
│   │     docs-html.tar.gz (full linked zdocs set), needs.json (full set),
│   │     trace-report.json/html, coverage report
│   │
│   ├── :0.1.0-cam-ee-<pcba>      EE CAM (kicad adapter)   [iteration 2+, after PCB layout]
│   │     gerbers.zip (or one layer per file once naming is fixed), drill, pos (pick-and-place),
│   │     bom.csv, schematic.pdf, erc/drc reports
│   │
│   ├── :0.1.0-cad-ee-<pcba>      EE design exports (iteration 2 without layout): schematic.pdf/svg, netlist, BOM
│   │
│   └── :0.1.0-cam-me             ME CAM (freecad adapter)
│         <part>.3mf, <part>.stl, print-profile.ini (D30), techdraw/*.pdf|svg, parameters.csv
│
└── GitHub release "baseline/v0.1.0" on robarm-manifest
      assets = `firmhold export robarm-bundle:0.1.0` folder (all files + *.manifest.json + *.sig)
      notes  = index digest, public key fingerprint, how to verify offline
```

Rules:

- Layers for files made together; referrers for later claims (tests, reviews, SBOM).
- The bundle version comes from the manifest tag (`baseline/v0.1.0` → `0.1.0`), never from `git describe` of
  one repo.
- Docs cite the firmware layer digest and HIL result IDs, never the bundle digest (avoids a cycle).

## Recommendations

**Iteration 1 (no bundles, D43):**

1. Do not put firmhold on the iteration-1 critical path. Its test-result feature does not exist, and GHCR
   cannot hold referrers yet.
2. For each HIL run, store a build record next to the results: `sha256(zephyr.bin)`, `west manifest --freeze`,
   `zephyr.meta` (dirty flag), board, rig ID, `twister.json`, `twister_report.xml`. Store it where
   zephyr-west.md decides (committed JSON in `robarm-sw`, or a release asset). Use the **same hash form**
   firmhold uses (`sha256:<hex>`) so the records connect to iteration-2 containers.
3. In the SW test spec needs, add the fields `fw_sha256` and `baseline`. A sphinx-needs check can then say
   "evidence is for the firmware in this baseline".
4. Optional demo: `firmhold pack` + `sign` + `export` of the one-joint firmware against a local Zot. Show the
   offline `openssl` check in the retrospective. Low cost; it gives the owner real-use feedback.

**Iteration 2 (bundles, D24/D40):**

1. Ask the owner for the features listed below (generic `files` adapter, `--version`, names, test results,
   GHCR fallback). These are the minimum for our bundle.
2. Use the "bundle = signed release index of component containers" layout above.
3. Use the baseline workflow (section 5) on `baseline/*` tags, push to GHCR, and also attach the export folder
   to the GitHub release, so reviewers do not need a registry.
4. Use cosign keyless with the GitHub OIDC identity of the baseline workflow when firmhold supports it.
   Until then, keep the ES256 public key in the manifest repo and publish its fingerprint.

## Findings for the owner (do not change firmhold; suggestions only)

1. **Docs say more than the code.** `README.md:3-9` and `src/firmhold/__init__.py:3-6` promise SBOMs, test
   results, attestations, cosign/DSSE/in-toto. Only signing exists. Suggest a "Status" table in the README.
2. **Stale doc text:** `architecture/building-blocks.rst:56-62` says only `pack` exists and `core.trust` is
   not wired. `registries/index.rst:25-26` says "no referrers exist yet". Both are out of date since FH11–FH14.
   `cli.py:753` / `cli.rst:463` say `--no-referrers` drops "signatures, SBOMs, attestations", but only
   signatures exist.
3. **Small inconsistency:** `trust-stack.rst:217-219,255` says unpinned `verify` reports `WARN`. The code and
   `sign-a-build.rst:100-106` print `PASS (self-embedded key)` + a WARNING line.
4. **Version is not cleaned for tags** (`core/oci.py:752-767`; only the board is cleaned). A tag such as
   `baseline/v0.2.0`, or any `git describe` output with `/`, makes an illegal OCI tag and a `/` in export
   file names (`semantic_base_name`, `core/oci.py:1577-1593`).
5. **No dirty marker:** `git describe --tags` without `--dirty` (`adapters/zephyr/__init__.py:101-103`). A pack
   from a modified tree looks like a clean release. The provenance commit is a short SHA
   (`__init__.py:106-109`); a full SHA is safer for audits.
6. **Export naming for non-provenance roles** uses only the extension (`core/oci.py:1596-1621`). Two files with
   the same extension collide, and names such as `needs.json` turn into `<base>.json`. Suggest keeping the
   whole name for every role except payload.
7. **No way to set app/version/board** from the CLI (`cli.rst:44-45`). Needed when the version is a baseline
   of several repos, or when CI builds in a detached checkout.
8. **Credential helpers** (`credsStore`/`credHelpers`) are not read (`core/oci.py:98-137`). Desktop users with
   `docker login` + a helper get no auth.
9. **GHCR + referrers:** signatures pushed to GHCR cannot be read back until the fallback tag scheme exists.
   This is the main blocker for a GitHub-hosted project (ADR `0013:134-137`).
10. **Acceptance suite pulls `zot:latest` implicitly** (`tests/acceptance/conftest.py:37`). Suggest pinning a
    version or digest, and skipping when the image is missing unless an env var allows a pull.
11. **"board" is firmware-specific.** For bundles of mixed outputs, a neutral name (target/component/variant)
    or a separate "component" annotation would fit better. Our use case is a concrete "second adapter" for
    ADR `0015`'s deferred inclusion policy.
12. **Release-index race** (ADR `0012:83-87`): a CI matrix that packs components in parallel can lose index
    members. A bundle workflow must pack serially, or the index must be built once at the end.

## Risks and open questions

- **Maturity:** pre-alpha, one author, API unstable (`README.md:11`; ADR `0015:157-160` already breaks a library
  type). Pin a firmhold commit in the west manifest or as a pip requirement.
- **Hosting:** firmhold lives on an internal GitLab (ADR `0009:12-14`). Our public tiacsys repos and CI need a
  public source (PyPI or a public mirror) to install it. Open: will it be published?
- **GHCR referrers:** without the fallback, D38 (HIL results in the bundle) cannot be met on GHCR. Use a
  different registry, or wait for the fallback. Open: which comes first?
- **GHCR package visibility:** a new container package may start as private even in a public org. Check
  whether it must be made public by hand once (D48 says "public from day one"). [not verified]
- **GHCR media types:** nobody has confirmed that GHCR accepts `application/vnd.zephyr.*` (the opt-in probe
  exists but has not run in CI). [read]
- **Reproducibility:** container digests differ between machines (`build_info.yml` absolute paths). Evidence
  must cite the `zephyr.bin` layer digest, not the container digest, if CI and the HIL bench build separately.
- **Firmware built locally (D47):** in iteration 2 either the Docker image with the SDK exists, or the bench
  machine packs and pushes. The second needs a PAT in a plain docker `config.json`.
- **Cycle docs ↔ bundle digest** (section 4): decide where the bundle digest is published (release notes and
  Pages, not inside the docs).
- **Plan conflicts:**
  - D38 assumes the bundling tool can carry HIL results. Today it cannot (planned only).
  - D54 `baseline/vX.Y.Z` cannot be used as an OCI tag. A mapping rule is needed (suggest `X.Y.Z`).
  - D24/D40 "all design outputs into a bundle": possible only with a generic adapter or the library API.
    Not with the CLI as it is.
  - D31 (release assets on tags) fits well: `firmhold export` produces the asset folder, and it verifies offline.
