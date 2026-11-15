# Research 1.8 — zdocs

Source studied: local clone of https://github.com/tiacsys/zdocs at `f9b701c` (2026-11-02), read-only.
All `file:line` citations refer to that commit. Hands-on runs were made in
`/tmp/claude-1000/-home-tobias-z-wrk-ws-syseng/cc4a5268-5423-4e94-be0d-4c1055bbe07f/scratchpad/research-zdocs`.

Legend: **[verified]** = I ran it and saw the result. **[read]** = I only read the code or docs.

zdocs is pre-release (`README.rst:12`). Licence: Apache-2.0 (`LICENSE`, `REUSE.toml`). Engine
version string `0.1.0-dev` (`cmake/zdocs.cmake:40`). It has its own unit tests (`pytest.ini`) and an
acceptance suite in a separate repo that I did not see.

## Summary

- **D35 works today, with gaps.** A downstream registry can list upstream documents with a
  relative `doc_dir:` into the sibling west project (`../../syseng/docs/sysreq`). I built a `sw`
  set that builds syseng's two documents locally and imports their needs. Links, back-links and
  intersphinx all resolved. **[verified]**
- **Gap 1 (D35): `version_project` is ignored for Sphinx documents.** `zdocs_conf.py:185` passes only
  `scope`. Upstream documents built in `sw` show **sw's** commit as their version. The Doxygen CLI
  path does honour it, so the two disagree. **[verified]**
- **Gap 2 (D35): every transitive upstream document must be listed** in each downstream registry, or
  the upstream document itself gets dangling links. There is no "index only / import only" mode, so
  each repo renders full HTML of all its upstream documents. **[verified]**
- **Gap 3: dangling or wrong-type links do not fail the build.** Default options are `-q -j auto`
  (`cmake/sphinx.cmake:37`); `doccheck` checks HTML links and a smoke page, not needs links.
  With `-DZDOCS_SPHINXOPTS_EXTRA="-W;--keep-going"` the build fails as wanted. **[verified]**
- **Non-SW repos need no Zephyr SDK and no toolchain.** They need Python ≥ 3.12, CMake, west, the
  zdocs pip pins, and a Zephyr *tree* only for its CMake package and `doc/_extensions`. A 13 MB
  subset (`cmake/ share/ scripts/ modules/ doc/_extensions VERSION`) was enough. **[verified]**
- **Extension approach (D34) works:** a framework extension on `sys.path` plus
  `configure(..., extensions=[...])` in the document's `conf.py`. A toy "KiCad parts" extension
  emitted needs that linked to upstream system requirements. **[verified]**
- **The link-type table (D36) can be enforced with sphinx-needs 8.3 schemas** in the shared
  `needs_config.toml` (`ZDOCS_NEEDS_CONFIG`). A "swreq refines only sysreq" rule caught a bad
  link and a missing target. zdocs only passes the TOML through. **[verified]**
- **zdocs' own docs build in ~11 s**, but only with the CI pins (`doc/requirements-ci.txt`); with
  the README's `doc/requirements.txt`, Pygments 2.21 makes `doc-check` fail. **[verified]**
- Twister/testmodule needs Doxygen (≥ 1.16 for `\satisfies`/needs tag) and annotated ztest C
  sources; test results come from `ZDOCS_TWISTER_OUT` and a missing run is not an error. **[read]**
- Multi-version hosting: zdocs has none; bridle's approach (one folder per version + one
  `versions.json` + switcher JS) fits a zdocs deploy tree well, because zdocs HTML links are
  relative. Bridle does **not** use GitHub Pages; it uploads to its own server. **[read]**

## Answers

### 1. How zdocs works

**Registry (`documents.yaml`).** One file per set. Read and validated by `scripts/docrefs.py`
(`_registry` `:88`, `_validate` `:240-432`). Full schema: `doc/manual/reference/registry-schema.rst`.
CMake reads it via `docrefs.py manifest` (`cmake/registry.cmake:156-172`) and creates one
`add_sphinx_target`/`add_doxygen_target` per document (`registry.cmake:221-360`). Each `conf.py`
reads it again through `docrefs.load()` (`docrefs.py:912`) to get intersphinx, doxylink, external
needs and nav links (`docrefs.py:1023-1077`). Kinds: `sphinx`, `doxygen`, `external`,
`sphinx-external`, `doxygen-external` (`docrefs.py:143`, `registry-schema.rst:356-364`).

**Groups.** Required, non-empty list of `{id, title, mode, display}` (`docrefs.py:242-262`). They only
drive the sidebar navigation (`grouped_links`, `docrefs.py:448-487`) and the aggregate CMake targets
`<group>-<builder>` (`registry.cmake:367-383`). A group id equal to a document id collides with that
document's own target name (noted in `doc/documents.yaml:12-23`, not validated).

**Prefixes.** `prefix:` (default: id with `-`→`_`) is the key for intersphinx and doxylink
(`docrefs.py:1032`, `:1040`). It is **not checked for uniqueness**; a clash silently overwrites
(`registry-schema.rst:148-155`).

**Versions.** `resolve_version()` (`docrefs.py:609-682`): `VERSION` env wins; else `version_scope`
→ `git describe --tags --match "<scope>/*"` in `ZDOCS_PROJECT_BASE`, prefix stripped (`"/"` = all
tags); else `version_project` → `west list` + `git describe` in that project; else
`v0.0-dev+g<sha>`. **But** the Sphinx path calls it with `scope` only (`sphinx/zdocs_conf.py:185`),
so `version_project` works only for the `docrefs.py version` CLI (Doxygen side, `docrefs.py:1641-1648`).

**Needs import.** A document with `needs:` is importable by every peer.
- `source: json`: the peer reads `deploy/html/<id>/needs.json`, added to `needs_external_needs`
  only if the file exists (sphinx-needs raises on a missing file) (`docrefs.py:1060-1077`).
  `needs_build_json = True` is forced so the stage-1 `xref` build writes it (`zdocs_conf.py:291`).
- `source: inventory`: builds a stub needs.json from an `objects.inv` with the `sphobjinv` CLI
  (`docrefs.py:523-586`); upstream says this path never ran (`sphinx/requirements-doc.txt:44-51`).
- Every document imports every other needs-publishing document; there is no per-document import
  list. So the needs config must be one project-wide TOML (`zdocs_conf.py:363-380`).
- When imported needs change, the peer re-reads its sources (`needs_config_state` extension,
  `registry-schema.rst:244-247`).

**Two-stage build.** Stage 1 `<doc>-index` runs a custom `xref` builder that writes only
`objects.inv` and `needs.json` (`cmake/sphinx.cmake:255-277`). Stage 2 `<doc>-<builder>` waits for
the `doc-index` aggregate (`sphinx.cmake:417`). This lets circular references resolve.

**testmodule + Twister.** Opt-in per document via a `testmodule:` block (`docrefs.py:325-412`,
`zdocs_conf.py:170-172`). Chain: annotated ztest C → a `kind: doxygen` document with
`doxygen_xml: true` → `.. testmodule::` emits one need per test case → `.. testreport::` and
`.. twisterinfo::` read `twister_report.xml`/`twister.json` from `ZDOCS_TWISTER_OUT` and emit result
needs linked to the cases (`doc/manual/explanation/testmodule-and-twister.rst`,
`doc/manual/howto/render-test-specifications.rst`). Requirement links come from Doxygen aliases
(`\xrefitem reqrefs`). Need type and link names are configurable roles
(`test_module.py:915-930`, decision 0009). A missing spec fails; a missing Twister run renders
"not found" and passes. `.. testcoverage::` adds coverage adequacy needs (`test_coverage.py:469-488`).
`symbol_needs:` emits one need per API symbol with Doxygen `\satisfies` (`registry-schema.rst:279-307`).

**Integrity gate (`doccheck`).** `add_doc_check()` runs `scripts/doccheck.py` as `doc-check` and as a
POST_BUILD step of `all-docs` (`cmake/common.cmake:160-190`). It checks (a) a smoke-test page whose
bullets must all be links (`doccheck.py:81`), (b) dead links inside `deploy/` (`doccheck.py:232`),
(c) links between PDFs. Accepted findings via `doc_check_accepted:` (`registry-schema.rst:57-73`).
It does **not** check sphinx-needs links; those are Sphinx warnings only.

**Deploy tree.** `deploy/html/<id>/`, `deploy/pdf/<title>_<version>.pdf`, `deploy/xml/<id>/`
(`doc/manual/explanation/deploy-layout.rst`). HTML links peers by **relative** path
(`docrefs.py:947-962`), so `deploy/html/` can be served from any folder or from `file://`.

### 2. D35 — building upstream documents locally

**Supported today, by `doc_dir:`.** A relative `doc_dir` is resolved against the registry's own
folder (`registry.cmake:225-235`). It can point into another west project. The upstream
document's own `conf.py` is used, read from its authored folder (`sphinx.cmake:215-217`), and its
sources are copied into the downstream build. I built this. **[verified]**

What is missing or weak:

| # | Gap | Evidence |
|---|-----|----------|
| G1 | `version_project` ignored for Sphinx; upstream docs show the **downstream** repo's version. `version_scope` would describe the downstream repo's tags (wrong repo). | `zdocs_conf.py:185`; sw build showed `v0.0-dev+g9b3b353` (sw sha) on `sysreq`; CLI gave `sysreq/v1.0` **[verified]** |
| G2 | CLI result for `version_project` is not scope-stripped (`sysreq/v1.0`, not `v1.0`). | `docrefs.py:662-680` **[verified]** |
| G3 | Transitive upstream docs must all be listed by hand. Leaving out `stkreq` gave dangling `derives` links inside the locally built `sysreq`. | **[verified]** |
| G4 | No "import only" mode: each upstream doc is fully rendered in every downstream repo (cost grows with depth). A stage-1-only kind would be enough for traces. | `registry.cmake:277-301` **[read]** |
| G5 | `doc_dir` paths depend on the west layout (`../../syseng/...`); no `${west:syseng}` style placeholder, no env expansion. | `registry.cmake:228-233` **[read]** |
| G6 | Anything an upstream doc needs from **its** repo's CMakeLists (`ZDOCS_NEEDS_CONFIG`, `ZDOCS_SPHINX_EXTRA_ENV`, `ZDOCS_TWISTER_OUT`) must be repeated downstream. | `sphinx.cmake:218-236` **[read]** |
| G7 | A document **without** `doc_dir` is read from `<CMakeLists dir>/<id>`, but a relative `doc_dir` from the registry dir. Easy to trip over if the registry and CMakeLists are in different folders. | `sphinx.cmake:185`, `registry.cmake:94-110`; hit it in a test **[verified]** |
| G8 | Upstream docs built downstream show downstream back-links ("refined by SWREQ-ADC"). Good for impact, but each repo's view of an upstream doc differs from the upstream's own build. | **[verified]** |

D39 fits: the manifest pins the revisions, so `west update` puts the right upstream sources at
`../../syseng`. No zdocs change is needed for that.

Sketch of the `sw` registry: see "Sketched registries" below.

### 3. Full linked set in the manifest repo (D26)

Same mechanism: one registry in the manifest repo whose `doc_dir`s point into every project. Each
document appears exactly once. Sketch below. Points to watch: unique ids and prefixes across all
repos (G-prefix not validated); group ids must not equal document ids; one shared needs TOML.

### 4. What non-SW repos need (syseng, ee, me, framework)

**[verified]** for syseng and sw toy sets:

- Python ≥ 3.12 (Zephyr's FindPython minimum; machine has 3.14.10 and it worked).
- CMake ≥ 3.20, Ninja (or make). Graphviz `dot` only if graphviz/needflow is used.
- pip: `sphinx/requirements-doc.txt` pins + `west`. Use the `requirements-ci.txt` style full pins.
- A west workspace (`west topdir`), with zdocs as a west project. The Zephyr module system then
  finds zdocs by itself (`ZEPHYR_ZDOCS_MODULE_DIR`); `-DEXTRA_ZEPHYR_MODULES` was not needed.
- A Zephyr tree, **only** for `find_package(Zephyr COMPONENTS doc)` (which includes `extensions`,
  `python`, `west`, `root`, `zephyr_module` — `zephyr/cmake/modules/doc.cmake`) and for
  `doc/_extensions/zephyr/external_content.py` (`zdocs_conf.py:48-53,149-153`). A full shallow clone
  is 565 MB (125 MB `.git`); a subset of 13 MB worked: `cmake/ share/ scripts/ modules/
  doc/_extensions/ VERSION`. `modules/` is required (`zephyr_module.cmake:123`).
- `ZEPHYR_BASE` must be set (or the package registered with `west zephyr-export`, which writes to
  `~/.cmake`). Without it, `find_package` failed. Pass `-DUSER_CACHE_DIR=...` to keep Zephyr's user
  cache out of `~/.cache/zephyr`.
- **No Zephyr SDK, no toolchain, no HAL.** zdocs' own `doc/west.yml` says the same (`:12-14`).
- Doxygen only for `kind: doxygen` docs (sw). zdocs' CI downloads Doxygen from GitHub releases with
  a SHA check (`.github/workflows/docs.yml:76-93`), because distro versions are too old for 1.16
  features.

**Cost.** CI (D47): pip install ~30–60 s with cache; sparse Zephyr checkout a few seconds; build of
a small set 4–11 s (syseng 2 docs: 4 s, sw 4 docs: 7 s, zdocs own docs: 11 s, on this machine).
One-command local check (D46): a wrapper script that sets `ZEPHYR_BASE`, runs `cmake -S docs -B build
-GNinja -DZDOCS_SPHINXOPTS_EXTRA="-W;--keep-going"` and `cmake --build build`. In a west workspace
the only heavy part is the first `west update` of Zephyr; recommend a manifest `import` with
narrow fetch, or a sparse checkout, for non-SW work.

### 5. Extension points (D34) and need/link types (D36)

- **conf.py shim.** Every document's `conf.py` calls `zdocs_conf.configure(globals(), doc_dir=...,
  extensions=[...], needs_config=..., static_path=..., css_files=..., templates_path=...)`
  (`zdocs_conf.py:61-74`). `extensions` is **appended** to the engine list (`:155`). After
  `configure()` the `conf.py` may set any other Sphinx value.
- **Finding our extensions.** Put the framework repo's extension folder on `sys.path` in `conf.py`,
  using `ZDOCS_WEST_TOPDIR`, which zdocs passes to every sphinx-build (`sphinx.cmake:224`). Or pass
  a path with `ZDOCS_SPHINX_EXTRA_ENV`. Or pip-install the framework package. **[verified first way]**
- **Input files.** `external_content` copies only the document folder; extra inputs (KiCad, FreeCAD,
  `.sysml`) outside it can be added with `external_content_contents.append(...)` (as `doc/api/conf.py:33`
  does) or read by absolute path and registered with `env.note_dependency`.
- **Need types, links, fields.** Not defined by zdocs. They come from one sphinx-needs TOML,
  `ZDOCS_NEEDS_CONFIG` → `needs_from_toml` (`zdocs_conf.py:378-380`, `consumer-contract.rst`).
  `sphinx/_scripts/needs_fields.py` is **not** a place to declare fields; it is a helper that sets
  the `depends_on` field only if the consumer declared it. Declare `[[needs.types]]`,
  `[needs.links.<name>]`, `[needs.fields.<name>]` in the TOML. **[verified]**
- **Layouts.** `need_layouts.need_layout(fields=[...], hide_backlinks=[...])` returns a card layout
  for `needs_layouts` in `conf.py` (`sphinx/_scripts/need_layouts.py:83-105`), styled by
  `need_cards` and `zdocs-needs.css`. `hide_backlinks` is useful for requirements with many
  incoming test results.
- **Link-type table (D36).** Yes: put the link types and sphinx-needs 8.3 schema rules in the same
  TOML (`[[needs.schema_definitions.schemas]]` with `validate.network.<link>`). The test rule
  reported `network_local_fail` for a wrong target type and `network_missing_target` for a removed
  target, also writing `schema_violations.json`. Severity "violation" printed `ERROR:` but did not
  fail the build without `-W`. **[verified]**

### 6. Gaps and risks for ME/EE/SE documents and HTML-only (D43)

- zdocs has no ME/EE/SysML awareness. Everything (KiCad, FreeCAD, SysML extraction) is our own
  extension (D34). zdocs gives the plumbing (registry, needs import, nav, checks).
- Test reporting is Zephyr/Twister-only. EE/ME test specs and HIL results need our own directives
  or must produce Twister-like output. Prototype test results for ME/EE have no importer.
- `doccheck` checks dead HTML links, not traces. Trace checks must come from sphinx-needs warnings
  under `-W`, schemas, and our own checks (D44 affirmatrix).
- Each dangling link is reported once per document that imports it (seen 5× in a 4-doc set) and
  the first failing target under `-W` may be an innocent upstream doc.
- HTML-only is the default path and well-tested here. PDF needs latexmk + xelatex (not installed on
  this machine); fine for iteration 1.
- `doc_control` and `latexinclude` are always loaded but inert (D33 OK).

### 7. Python dependencies

Engine pins (`sphinx/requirements-doc.txt`): `sphinx==9.1.0`, `sphinx_rtd_theme==3.1.0`,
`sphinx-needs==8.3.0`, `sphinxcontrib-doxylink==1.13.0`, `PyYAML==6.0.3`, `pypdf==6.15.0`,
`sphinx-autobuild==2025.8.25`, `sphobjinv` (unpinned). Own docs add
`sphinxcontrib-moderncmakedomain==3.29.0`. CI pins all transitive packages incl.
`docutils==0.22.4`, `Pygments==2.20.0` (`doc/requirements-ci.txt`).

On this machine: system Python 3.14.10, no Sphinx installed system-wide, PyYAML 6.0.3, CMake 4.5.0,
Ninja, Doxygen 1.18.0, Graphviz 16.1.1, no west (installed in venv: 1.5.0), no latexmk. All pins
installed and worked in a venv on Python 3.14. **[verified]** zdocs' CI tests Python 3.12, so 3.14 is
outside their tested range. Two Zephyr trees exist (`~/z/wrk/ws-up`, `~/z/wrk/ws-t`); I cloned
v4.4.1 from `ws-t` locally (`--depth 1`, 6 s).

### 8. Multi-version hosting (bridle's approach)

Read in a shallow clone of https://github.com/tiacsys/bridle (`12aff75`, 2026-11-13). **[read]**

- **Folder layout:** `<host>/doc/<version>/<docset>/...`, with `latest` for `main` and one folder
  per release (`4.4`, `4.4.0`, …), plus `PR-<n>` previews.
- **Version list:** one file `doc/versions.json` (`{"VERSIONS": ["latest", "4.4", ...]}`), copied
  into each build's HTML root (`doc/CMakeLists.txt:543-552`). Only the copy under `latest/` is read.
- **Switcher:** in the theme `sphinx-tsn-theme` (MIT, pip). Its JS
  (`static/js/tiac.js_t:15-80`) takes the version from the first path segment after `/doc/`,
  loads `latest/versions.json`, and links each entry to **the same page** in the other version. It
  also shows a banner for old or dev versions.
- **CI:** `doc-build.yml` builds, tars `html/`, and writes a "monitor" file
  `publish2 <approved|development|preview> <latest|branch|PR-n> <archive>` (`:193-221`).
  `doc-publish.yml` (on `workflow_run`) uploads by `scp` to a server inbox (`:43-61`); a server-side
  job (not in the repo) unpacks it. `doc-remove.yml` removes a PR preview when the PR closes.
  **It does not use GitHub Pages.**

**Applying it to a zdocs full set on GitHub Pages of the manifest repo:**

1. Build the full set; publish `deploy/html/` as a folder. zdocs links are relative, so the tree
   works unchanged under `latest/` or `baseline-v1.2.0/`.
2. Keep a `gh-pages` branch (Pages "deploy from branch"). The `actions/deploy-pages` flow replaces
   the whole site each time, so it cannot keep old baselines unless the job first restores them.
   On push to `main`: replace `latest/`. On tag `baseline/vX.Y.Z`: add `baseline-vX.Y.Z/` (no `/`
   in the folder name) and add it to a root `versions.json`. Never rewrite old folders.
3. Switcher: zdocs uses `sphinx_rtd_theme` plus its own `layout.html`; add a small JS file
   (`html_js_files` set in `conf.py` after `configure()`, file in `static_path`) that reads
   `/<repo>/versions.json` and builds a drop-down linking to the same page path. Same logic as
   `tiac.js_t`, but the Pages prefix is `/<repo>/` not `/doc/`.
4. Version label: for a baseline build set `VERSION=baseline/vX.Y.Z` (env wins over all,
   `docrefs.py:629-631`) — but that hides each document's own version. Better to keep per-document
   versions (fix G1) and show the baseline in the switcher only.
5. PR previews: not on Pages; use workflow artifacts (D31).

## Sketched registries

Assumed west layout: all repos are siblings in the workspace top dir; each repo keeps documents in
`docs/<id>/` and its registry at `docs/documents.yaml`. Shared needs TOML:
`framework/needs/needs_config.toml`. Ids carry the domain so they stay unique in the full set.

### `sw/docs/documents.yaml` (D35)

```yaml
base_url: "http://localhost:8000/"
groups:
  - id: up-se            # never equal to a document id
    title: "System (upstream, syseng)"
    display: collapsed_at_opening
  - id: sw-docs
    title: "Software"
doxygen_xml: true        # needed by testmodule

documents:
  # -- upstream, built locally from the west checkout; all transitive upstreams listed (G3)
  se-stkreq:
    title: "Stakeholder Needs and System Requirements"
    group: up-se
    doc_dir: ../../syseng/docs/se-stkreq
    version_project: syseng      # ignored for Sphinx today (G1)
    builders: [html]
    needs: {source: json}
  se-arch:
    title: "System Architecture"
    group: up-se
    doc_dir: ../../syseng/docs/se-arch
    version_project: syseng
    builders: [html]
    needs: {source: json}
  se-proto-joint:
    title: "Prototype Setup: One Joint"
    group: up-se
    doc_dir: ../../syseng/docs/se-proto-joint
    version_project: syseng
    builders: [html]
    needs: {source: json}

  # -- own documents
  sw-req:
    title: "SW Requirements"
    group: sw-docs
    version_scope: sw-req
    builders: [html]
    needs: {source: json}
  sw-design:
    title: "SW Architecture and Design"
    group: sw-docs
    version_scope: sw-design
    builders: [html]
    needs: {source: json}
    symbol_needs: {doxygen_source: dox-sw-api}
  dox-sw-api:
    kind: doxygen
    title: "Firmware API"
    group: sw-docs
  dox-sw-tests:
    kind: doxygen
    title: "Firmware Test Sources"
    group: sw-docs
  sw-testspec:
    title: "SW Test Specification"
    group: sw-docs
    builders: [html]
    needs: {source: json}
    testmodule: {doxygen_source: dox-sw-tests, api_reference: dox-sw-api}
  sw-testreport:
    title: "SW Test Report"
    group: sw-docs
    builders: [html]
    needs: {source: json}
    testmodule: {spec: sw-testspec, doxygen_source: dox-sw-tests, api_reference: dox-sw-api}
```

`sw/docs/CMakeLists.txt` (tested shape): `find_package(Zephyr REQUIRED HINTS $ENV{ZEPHYR_BASE}
COMPONENTS doc)`; `ZDOCS_PROJECT_BASE` = repo root; `ZDOCS_WEST_TOPDIR` from `west topdir`;
`ZDOCS_NEEDS_CONFIG` = `${WEST_TOPDIR}/framework/needs/needs_config.toml`; `include(zdocs)`;
`add_docs_from_registry(...)`; `add_doc_check(...)`. Best moved into one shared
`framework/cmake/docs.cmake` so every repo (and the manifest) gets the same settings (G6).

### `manifest/docs/documents.yaml` (D26, D21 + D27)

```yaml
base_url: "https://<org>.github.io/<manifest-repo>/latest/"
xref_smoketest: "html/index-set/xref-smoke-test.html"
doxygen_xml: true
groups:
  - {id: g-start, title: "Start", mode: single_doc_title_merge}
  - {id: g-se,    title: "Systems Engineering"}
  - {id: g-proto, title: "Prototype Setups", display: collapsed_at_opening}
  - {id: g-ee,    title: "Electrical"}
  - {id: g-me,    title: "Mechanical"}
  - {id: g-sw,    title: "Software"}
  - {id: g-fw,    title: "Framework", display: collapsed_at_opening}

documents:
  index-set:      {title: "Robot Arm Documentation", group: g-start, builders: [html]}   # manifest/docs/index-set
  # syseng
  se-stkreq:      {title: "Stakeholder Needs and System Requirements", group: g-se, doc_dir: ../../syseng/docs/se-stkreq, version_project: syseng, builders: [html], needs: {source: json}}
  se-arch:        {title: "System Architecture",                       group: g-se, doc_dir: ../../syseng/docs/se-arch,   version_project: syseng, builders: [html], needs: {source: json}}
  se-sit-spec:    {title: "System and Integration Test Spec",          group: g-se, doc_dir: ../../syseng/docs/se-sit-spec, version_project: syseng, builders: [html], needs: {source: json}}
  se-proto-joint: {title: "Prototype Setup: One Joint",                group: g-proto, doc_dir: ../../syseng/docs/se-proto-joint, version_project: syseng, builders: [html], needs: {source: json}}
  # ee
  ee-req:         {title: "EE Requirements",          group: g-ee, doc_dir: ../../ee/docs/ee-req,         version_project: ee, builders: [html], needs: {source: json}}
  ee-pcba-joint:  {title: "PCBA Design: Joint Board", group: g-ee, doc_dir: ../../ee/docs/ee-pcba-joint,  version_project: ee, builders: [html], needs: {source: json}}  # one per PCBA (D28)
  ee-test-spec:   {title: "EE Test Spec",             group: g-ee, doc_dir: ../../ee/docs/ee-test-spec,   version_project: ee, builders: [html], needs: {source: json}}
  # me
  me-req:         {title: "ME Requirements",          group: g-me, doc_dir: ../../me/docs/me-req,         version_project: me, builders: [html], needs: {source: json}}
  me-assembly:    {title: "ME Assembly Design",       group: g-me, doc_dir: ../../me/docs/me-assembly,    version_project: me, builders: [html], needs: {source: json}}
  me-test-spec:   {title: "ME Test Spec",             group: g-me, doc_dir: ../../me/docs/me-test-spec,   version_project: me, builders: [html], needs: {source: json}}
  # sw
  sw-req:         {title: "SW Requirements",            group: g-sw, doc_dir: ../../sw/docs/sw-req,    version_project: sw, builders: [html], needs: {source: json}}
  sw-design:      {title: "SW Architecture and Design", group: g-sw, doc_dir: ../../sw/docs/sw-design, version_project: sw, builders: [html], needs: {source: json}, symbol_needs: {doxygen_source: dox-sw-api}}
  dox-sw-api:     {kind: doxygen, title: "Firmware API",          group: g-sw, doc_dir: ../../sw/docs/dox-sw-api}
  dox-sw-tests:   {kind: doxygen, title: "Firmware Test Sources", group: g-sw, doc_dir: ../../sw/docs/dox-sw-tests}
  sw-testspec:    {title: "SW Test Specification", group: g-sw, doc_dir: ../../sw/docs/sw-testspec,   version_project: sw, builders: [html], needs: {source: json}, testmodule: {doxygen_source: dox-sw-tests, api_reference: dox-sw-api}}
  sw-testreport:  {title: "SW Test Report",        group: g-sw, doc_dir: ../../sw/docs/sw-testreport, version_project: sw, builders: [html], needs: {source: json}, testmodule: {spec: sw-testspec, doxygen_source: dox-sw-tests, api_reference: dox-sw-api}}
  # framework (D13) — not part of the trace graph
  fw-manual:      {title: "Framework Manual", group: g-fw, doc_dir: ../../framework/docs/fw-manual, version_project: framework, builders: [html], crossref: false}
```

Notes: the `kind: doxygen` `doc_dir` needs a `Doxyfile.in` there (not tested). `ZDOCS_TWISTER_OUT`
must be set for the report. `crossref: false` keeps the framework manual out of needs imports.

## Hands-on results

All in `/tmp/claude-1000/-home-tobias-z-wrk-ws-syseng/cc4a5268-5423-4e94-be0d-4c1055bbe07f/scratchpad/research-zdocs`.

1. **Setup.** `python3 -m venv venv; pip install -r ws/zdocs/doc/requirements.txt west` → OK on
   Python 3.14. `git clone --depth 1 --branch v4.4.1 file:///home/tobias/z/wrk/ws-t/zephyr` → 6 s.
   `west init -l --mf doc/west.yml zdocs` → OK.
2. **zdocs' own docs.** `cmake -S doc -B build-zdocs-doc -GNinja` without `ZEPHYR_BASE` → *"Could not
   find a package configuration file provided by Zephyr"*. With `ZEPHYR_BASE` set → configure 1 s.
   `cmake --build` → both docs built, then **`doc-check` FAILED**: `html/api/_modules/doccheck.html:
   dead link -> ([^`. Cause: Pygments 2.21.0 does not escape `"` in code; `doccheck`'s regex
   `href="([^"#?]+)` (`doccheck.py:142`) then matches its own source shown by viewcode. Known
   upstream (`doc/requirements-ci.txt:32-36` pins Pygments 2.20.0). After `pip install
   Pygments==2.20.0`: build OK in 11 s, `doccheck: OK`, 0 Sphinx warnings.
3. **Two-repo set (syseng + sw), workspace `ws2`.** Local git repos `manifest`, `framework`,
   `syseng`, `sw` plus zdocs and Zephyr; `west init -l manifest`. zdocs found as a module without
   `EXTRA_ZEPHYR_MODULES`.
   - syseng (`stkreq`, `sysreq`, `needs: {source: json}`): built in 4 s, `doccheck OK`.
     `sysreq` needs link `derives: STKN-*` resolved; `stkreq` showed computed back-links
     "derived into SYSREQ-RATE" with relative URLs `../sysreq/index.html#SYSREQ-RATE`.
     Version from scoped tag: `sysreq` showed `v1.0` (tag `sysreq/v1.0`); `stkreq` (no tag) showed
     `v0.0-dev+gc800621`.
   - sw (upstream `stkreq`, `sysreq` via `doc_dir: ../../syseng/docs/...`, plus `swreq`, `swtest`):
     built in 7 s, `rc=0`, `doccheck OK`. `swreq` → `SYSREQ-RATE` links worked; `:external+sysreq:doc:`
     worked; the locally built `sysreq` showed "refined by SWREQ-ADC" and "allocates PCB-U1".
     Upstream docs showed version `v0.0-dev+g9b3b353` = **sw's** commit (G1). `docrefs.py version
     sysreq --west ws2` printed `sysreq/v1.0` (G2).
   - A deliberate dangling link (`SWREQ-DANGLING :refines: SYSREQ-REMOVED`) gave 5 warnings (one per
     document) and **rc=0, doccheck OK**. With `-DZDOCS_SPHINXOPTS_EXTRA="-W;--keep-going"` →
     build failed (rc=1), first on `stkreq-html`.
   - Removing `stkreq` from the sw registry → `sysreq` built in sw got dangling `derives` warnings (G3).
4. **Framework extension (D34).** `framework/sphinx_ext/kicad_parts.py` (toy directive reading a
   JSON BOM and emitting `pcbpart` needs with `allocated_to` links) loaded via `sys.path` from
   `ZDOCS_WEST_TOPDIR` and `configure(..., extensions=["kicad_parts"])`. Needs `PCB-U1/U2` rendered
   and linked to `SYSREQ-RATE` / `SWREQ-ADC`. **Worked.**
5. **Link-type rule (D36).** Schema in the shared TOML: swreq `refines` must target `sysreq`. A need
   `SWREQ-BADTYPE :refines: STKN-MIRROR` → `ERROR ... "sysreq" was expected
   [sn_schema_violation.network_local_fail]`; `SWREQ-DANGLING` →
   `network_missing_target`; `schema_violations.json` written. Build still rc=0 without `-W`.
6. **Minimal Zephyr.** A 13 MB copy (`cmake share scripts modules doc/_extensions VERSION`) as
   `ZEPHYR_BASE` → sw set configured and built the same. Without `modules/` → *"No
   modules/modules.cmake found in module root"*.

Not tried: Doxygen documents, testmodule/Twister, PDF, `source: inventory`, the full manifest set.

## Findings for the zdocs owner

(Reported only; zdocs was not changed.)

1. **`version_project` is ignored for Sphinx documents** (`zdocs_conf.py:185` passes only `scope`).
   Sphinx and Doxygen can show different versions for the same document. Needed for D35-style
   upstream builds.
2. `version_project` result is not stripped of the tag namespace (`sysreq/v1.0`), unlike
   `version_scope`; and `version_scope` of a document built from another repo describes the
   *consumer's* repo. A per-document "repo root" (from `doc_dir`'s git root or the west project)
   would fix both.
3. **README build recipe fails `doc-check`** with current unpinned Pygments (2.21). README points to
   `doc/requirements.txt`; only `requirements-ci.txt` works. `HREF_RE` should skip code blocks.
4. README says `cmake -S doc -B <build> -DEXTRA_ZEPHYR_MODULES=$PWD` but does not mention that
   `ZEPHYR_BASE` (or `west zephyr-export`) is required for `find_package(Zephyr ... HINTS
   $ENV{ZEPHYR_BASE} ..)`; the `..` hint did not find the sibling `zephyr/`.
5. No "import-only" document kind: a downstream set must fully render upstream documents just to get
   their `needs.json`. A kind that runs only stage 1 (or reads a published `needs.json`) would cut
   cost and noise.
6. Needs import is all-to-all. No per-document `imports:` list, so transitive upstreams must be
   added by hand and every warning repeats once per importing document.
7. No placeholder for west project paths in `doc_dir` (e.g. `{west:syseng}/docs/x`).
8. `doc_dir` default (caller dir) vs. relative `doc_dir` (registry dir) differ; consider one base.
9. Prefix uniqueness and group-id vs. document-id target clashes are not validated (both documented
   as known).
10. Default build does not fail on sphinx-needs warnings or schema violations; `doccheck` does not
    look at needs links. A documented "strict" switch (or doccheck reading `schema_violations.json`
    and needs warnings) would help.
11. `ZDOCS_NEEDS_CONFIG` is missing from the consumer block comment in `cmake/zdocs.cmake`
    (already self-reported in `consumer-contract.rst`).
12. No multi-version hosting or version switcher.

## Recommendations

- Adopt zdocs as planned (D25). Use `doc_dir` for D35 now.
- Put one shared CMake include and one shared `needs_config.toml` (types, links, fields, schema
  rules = D36 table) in the **framework** repo; every repo's `docs/CMakeLists.txt` includes it.
- Build with `-DZDOCS_SPHINXOPTS_EXTRA="-W;--keep-going"` in CI and in the local check (D46), so
  dangling links and schema violations fail.
- Pin the full Python set (copy zdocs' `requirements-ci.txt` approach), incl. `Pygments==2.20.0`.
- For non-SW repos and docs CI: sparse checkout of Zephyr (`cmake share scripts modules
  doc/_extensions` + root files), `ZEPHYR_BASE` set, no SDK.
- Until finding 1 is fixed, give upstream-built documents a version some other way (e.g. in our
  shared CMake: `ZDOCS_SPHINX_EXTRA_ENV`, or a tiny override in each upstream `conf.py` that calls
  `docrefs.resolve_version(project=...)`), or accept the wrong label in iteration 1.
- Ask the owner about findings 1, 5, 6 (they matter most for D35).
- Write extraction extensions so they also run standalone (tests without zdocs), and register input
  files with `env.note_dependency`.
- For multi-version Pages: gh-pages branch, `latest/` + `baseline-vX.Y.Z/` folders, root
  `versions.json`, small switcher JS (bridle pattern).

## Risks and open questions

- zdocs is pre-release; schema and `ZDOCS_*` contract may change without notice (`README.rst:12`).
- Python 3.14 here vs. 3.12 in zdocs' CI: worked for HTML, but not covered by their tests.
- Build time grows with depth: each repo renders all transitive upstream docs; the manifest set
  renders everything once. Fine at our size.
- Each repo's local copy of an upstream doc shows different back-links than the upstream's own build.
  Reviewers may be confused about which copy is "the" document.
- Twister reporting fits SW only. How do EE/ME/HIL results become needs? (Our extension or
  Twister-shaped output.)
- Doxygen ≥ 1.16 is needed for `\satisfies`/needs tag; CI must download it like zdocs does.
- Open: should upstream documents be built locally (D35) or should zdocs gain an import-only kind?
  The answer changes CI cost and what reviewers see.
- Open: GitHub Pages vs. own server (bridle uses its own server); Pages cannot host PR previews.

## Contradictions with plan.md

- None hard. D35's note "zdocs imports needs only from locally built documents" is correct
  (`docrefs.py:1060-1077`); `sphinx-external` docs give intersphinx only, no needs.
- D35 works only partly as written: versions of upstream docs are wrong today (finding 1), and every
  transitive upstream document must be listed.
- D46/D47: "every check runs locally" needs a strict flag; the default zdocs build passes with
  dangling trace links.
