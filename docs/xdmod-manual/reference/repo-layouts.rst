.. _ref-repo-layouts:

Repo layouts
============

Every repo that uses XDMOD follows one common pattern. Domain repos add their own folders.
Examples are from the robot arm.

Common pattern
--------------

.. code-block:: text

   <repo>/
     README.md
     checks.yaml            what `curatrix check` runs for this repo
     ids.yaml               ID ledger
     requirements.txt       pinned pip packages this repo needs
     tools.yaml             pinned non-pip tools (name, version, source, sha256)
     docs/
       documents.yaml       zdocs registry: own documents and upstream documents
       CMakeLists.txt
       <doc-id>/            one folder per document (conf.py and rst)
     generated/             committed generated files, checked by `curatrix check`
     claude/                agent material for this repo
     .github/
       workflows/           thin callers of the reusable workflows in xdmod
       pull_request_template.md
     .gitattributes         diff drivers (e.g. *.FCStd diff=fcstd -merge)

Rules:

- **No build output in repos** (:need:`XD-RULE-0040`, :need:`XD-CHECK-0026`). Everything goes to
  ``<workspace>/build/<area>/`` (:need:`XD-ADR-0040`). ``<area>`` is the repo name, ``full`` for the full
  set, the branch for worktree builds (:need:`XD-ADR-0114`), or a named step.
- **Generated files are committed only in** ``generated/``, except where the tool needs them next
  to the source: SysML stubs in ``model/generated/`` and views in ``views/``.
- **Folder names are lowercase with dashes.** Each PCBA, assembly and configuration gets its own
  folder, so adding one never moves another.

Systems engineering repo
------------------------

.. code-block:: text

   model/                  *.sysml per SYSMOD step (see the SYSMOD mapping)
   model/generated/        stubs from the needs
   views/                  <view>.drawio.svg
   generated/              model.json, model-needs.json
   docs/se-req/  docs/se-arch/

EE repo
-------

.. code-block:: text

   pcba/<name>/            one KiCad project per PCBA, with project-local library tables
   proto/<config>/         prototype wiring per prototype configuration (KiCad or WireViz)
   lib/                    project-local symbols, footprints, 3D models
   tests/                  scripted EE checks (netlist vs. pin map, ERC), JUnit output
   generated/              cad-needs.json
   docs/                   EE requirements and design; one document per PCBA and per
                           prototype configuration

KiCad library tables refer to the shared libraries only through variables (``${XD_KICAD_SYMBOLS}``
and so on) and to ``lib/`` through ``${KIPRJMOD}``. ``curatrix launch kicad`` sets the variables
(:need:`XD-ADR-0080`). There is one document per PCBA and one per prototype configuration (:need:`XD-ADR-0102`).

ME repo
-------

.. code-block:: text

   parts/<part>.FCStd      single parts, stored uncompressed
   assemblies/<asm>/       <asm>.FCStd and assembly-specific parts
   lib/                    project-local parts
   templates/              TechDraw templates
   print/                  print-settings profiles
   tests/                  scripted ME checks, JUnit output
   generated/              cad-needs.json, semantic JSON of each .FCStd
   docs/

FreeCAD files are stored uncompressed, with a git textconv for readable diffs (:need:`XD-ADR-0056`,
:need:`XD-RULE-0039`).

SW repo
-------

.. code-block:: text

   app/                    the firmware application
   dts/bindings/           the project's own devicetree bindings, with trace-id
   tests/<suite>/          unit and hardware test suites, with test IDs from the ledger
   docs/                   SW requirements, architecture and design, API (Doxygen),
                           test spec, test report

SW architecture is written in rst in iteration 1 (:need:`XD-ADR-0069`). Test reports are separate
documents from the test specs (:need:`XD-ADR-0099`).

Integration repo
----------------

.. code-block:: text

   tests/                  system and integration test cases
   hil/<setup>/            HIL setups: hardware map, fixtures, runner config
   docs/                   system and integration test spec and report
   branch `evidence`       orphan branch with HIL run records, never merged

Every test that verifies a system requirement or interface lives here (:need:`XD-ADR-0104`).

Manifest repo
-------------

.. code-block:: text

   west.yml                imports submanifests/
   submanifests/*.yml
   scripts/bootstrap.sh    first-time setup; a copy of xdmod/templates/bootstrap.sh
   docs/                   full-set registry and the project overview document
   .github/workflows/      bump bot, full-set build, Pages publishing

``scripts/bootstrap.sh`` is a copy of the xdmod template (:need:`XD-ADR-0107`); :need:`XD-CHECK-0029` warns when
it drifts (:need:`XD-RULE-0043`).

xdmod
-----

.. code-block:: text

   claude/                 planning folder and shared agent material: skills, commands, checklists
   launch/CLAUDE.md        launch file, copied to the workspace root by the bootstrap
   curatrix/               the tool (Python package)
   sphinx/                 Sphinx extensions and the shared conf helper
   needs/                  needs_config.toml (need types, link types, schema rules)
   sysml/                  SysML library: trace metadata, @XdView
   templates/              bootstrap.sh and other templates
   workflows/              reusable GitHub workflows
   docs/xdmod-manual/  docs/xdmod-ref/

Agent material
--------------

.. list-table::
   :header-rows: 1
   :widths: 40 45 15

   * - Where
     - What
     - Shared or local
   * - ``xdmod/launch/CLAUDE.md`` → ``<workspace>/CLAUDE.md``
     - workspace rules: run from the root, limits, build paths, trace rule, trailers
     - shared
   * - ``xdmod/claude/skills/``
     - skills per SYSMOD step, EARS writing, ID issuing, change workflow
     - shared
   * - ``xdmod/claude/commands/``
     - slash commands, e.g. ``/review-pr``
     - shared
   * - ``<repo>/claude/CLAUDE.md``
     - repo rules: layout, checks, pitfalls
     - local
   * - ``<repo>/claude/skills/``, ``commands/``
     - domain skills, e.g. KiCad edits through scripts
     - local

The bootstrap links all skills and commands into ``<workspace>/.claude/``, prefixed with the
repo name (:need:`XD-ADR-0103`).
