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

   model/                  EE domain model: board defs, connector port defs with pin maps,
                           cable defs, external parts, board variants
   pcba/<name>/            one KiCad project per board def: <name>.kicad_pro, schematic, board,
                           library tables, <name>.kicad_jobset, accepted.yaml
   proto/<name>/           one KiCad project per block of the prototype configuration
   harness/<name>/         one WireViz harness per cable def: <name>.yml
   lib/                    project-local symbols, footprints, 3D models
   tests/                  scripted EE checks, JUnit output
   generated/              cad-needs.json, model.json, <project>.connectors.json
   docs/                   ee-design; one document per board (pcba-<name>), prototype
                           project (proto-<name>) and harness (harness-<name>)

KiCad library tables refer to the shared libraries only through variables (``${XD_KICAD_SYMBOLS}``
and so on) and to ``lib/`` through ``${KIPRJMOD}``. ``curatrix launch kicad`` sets the variables
(:need:`XD-ADR-0080`). The domain model owns the board, port and harness IDs; KiCad and WireViz
files refer to them (:need:`XD-ADR-0128`): a KiCad project by its ``TraceID`` text variable, a
WireViz harness by ``metadata: {TraceID: EE-HAR-....}``, and each of its connectors by a line
``Port: EE-PORT-....`` in its ``notes`` (the port it mates with, on a board or an external part;
WireViz shows the notes in the diagram). The connector's ``pins`` and ``pinlabels`` are the pin
numbers and net names of that port's pin map; the pin maps at both ends use the same net names
(the pin map of a bought part names its pins with our nets, not the vendor's). The cable def has one port per end, typed by the
(conjugated) port def it mates with; ``EE-HAR connects EE-PORT`` comes from these ports (one target
for a cable with the same port def at both ends; CK-F1 counts the ends). The jobset is a copy of the xdmod template
(:need:`XD-ADR-0142`); ``accepted.yaml`` holds the accepted ERC and DRC findings (:need:`XD-ADR-0126`).
There is one document per board, prototype project and harness (:need:`XD-ADR-0129`,
:need:`XD-ADR-0127`).

ME repo
-------

.. code-block:: text

   model/                  ME domain model: assembly defs, mechanical port defs, variants
   parts/<part>.FCStd      shared parts, stored uncompressed
   assemblies/<name>/      <name>.FCStd (top document), skeleton.FCStd (parameters, variant
                           table, master sketch), parts/, accepted.yaml
   lib/                    project-local parts
   templates/              TechDraw templates
   print/                  print-settings profiles
   tests/                  scripted ME checks, JUnit output
   generated/              cad-needs.json, model.json, semantic JSON of each .FCStd
   docs/                   me-design; one document per top-level assembly (asm-<name>)

FreeCAD files are stored uncompressed, with a git textconv for readable diffs (:need:`XD-ADR-0056`,
:need:`XD-RULE-0039`). Parts refer only to the skeleton, never to the top document
(:need:`XD-ADR-0137`). Board models come at fixed versions from a board library repo
(:need:`XD-ADR-0139`). Boards, harnesses and assemblies have their own tags
``<name>/vX.Y.Z``, made by the owner only (:need:`XD-ADR-0140`).

Board library repo
------------------

.. code-block:: text

   boards/<board>/<board>-<vX.Y.Z>[-<variant>].FCStd
                           one FreeCAD model per tagged board version and variant: board body and
                           components, no tracks; App::Part "Board" with TraceID (EE-PCBA),
                           Version, Variant, Commit; uncompressed; at most 5 MB; never replaced
   docs/                   board-library: the list of board versions, made from the files
   checks.yaml             board_library: {source: "{ws}/<ee repo>"} (CK-F20); no ids.yaml

A top-level west project in the west groups of EE and ME (:need:`XD-ADR-0139`). EE writes
a tagged board version with ``curatrix cam <ee repo> <board> --library`` and opens the pull request;
ME links one fixed version, and ``cad.board_library`` in the ME repo's checks.yaml notes a newer one
(CK-F21).

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
     - slash commands, linked as ``/xd-<name>``, e.g. ``/xd-review-pr``
     - shared
   * - ``<repo>/claude/CLAUDE.md``
     - repo rules: layout, checks, pitfalls
     - local
   * - ``<repo>/claude/skills/``, ``commands/``
     - domain skills, e.g. KiCad edits through scripts
     - local

The bootstrap links all skills and commands into ``<workspace>/.claude/``, prefixed with the
repo name (:need:`XD-ADR-0103`).
