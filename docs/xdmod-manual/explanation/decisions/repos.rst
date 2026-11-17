.. _adr-repos:

Repos and workspace
===================

Repos, the west workspace, names, tags and paths.

.. xd-adr:: A multi-repo workspace with west
   :id: XD-ADR-0006
   :legacy_id: D7
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   Repos are managed as a multi-repo workspace with **west**.

.. xd-adr:: A dedicated manifest repo
   :id: XD-ADR-0011
   :legacy_id: D14
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   The west manifest lives in a **dedicated manifest repo**.

.. xd-adr:: The manifest is the only place that pins revisions
   :id: XD-ADR-0033
   :legacy_id: D39
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **The manifest is the only place that pins revisions.** A downstream PR's CI builds against the upstream revisions on the manifest's main branch. A change across several repos = one PR per repo + one manifest PR that bumps them together.

.. xd-adr:: Terms: baseline and bundle
   :id: XD-ADR-0034
   :legacy_id: D40
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0019
   :supersedes: XD-ADR-0026

   **Terms:** a baseline is a tag of the manifest repo (a fixed set of repo versions). A bundle is the package of outputs (docs, CAM, firmware, HIL results) built from one baseline.

.. xd-adr:: Names: XDMOD, -trix tools, robarm- repos
   :id: XD-ADR-0042
   :legacy_id: D49
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **Repo names:** the framework (methods and tools) is **XDMOD** ("Cross-Domain MODeling", named like SYSMOD), repo ``xdmod``. Each tool in it gets a **Latin stem with a ``-trix`` suffix**, like affirmatrix and probatrix. The example repos use the prefix ``robarm-`` (``robarm-manifest``, ``robarm-syseng``, ``robarm-ee``, ``robarm-me``, ``robarm-sw``). Extended by :need:`XD-ADR-0066`: ``robarm-integration``.

.. xd-adr:: SemVer tags and baseline tags
   :id: XD-ADR-0047
   :legacy_id: D54
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **Tags:** each repo uses SemVer tags ``vX.Y.Z``. Baselines are manifest tags ``baseline/vX.Y.Z``, and their GitHub release carries the outputs.

.. xd-adr:: xdmod is in every workspace
   :id: XD-ADR-0059
   :legacy_id: D66
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **xdmod is in every workspace** that uses the framework, as a west project in its manifest.

.. xd-adr:: All commands run from the workspace root
   :id: XD-ADR-0060
   :legacy_id: D67
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **All commands run from the workspace root** (the west topdir). That includes CLI tools (west, claude, doc builds, checks, extractors) and **launchers for GUI tools** (KiCad, FreeCAD and others), so paths and environment are set up correctly. git is the only exception.

.. xd-adr:: One west topdir at the workspace root
   :id: XD-ADR-0061
   :legacy_id: D68
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **One west topdir at the workspace root.** The root holds ``.west/``, ``.venv/``, ``build/`` and all repos.

.. xd-adr:: Agent material in each repo's claude/ folder
   :id: XD-ADR-0062
   :legacy_id: D69
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **Agent material in repos:** each repo has a ``claude/`` subfolder. A **launch ``CLAUDE.md``** for the workspace root lives in xdmod and is **copied there during workspace bootstrap**.

.. xd-adr:: The planning folder moves into xdmod
   :id: XD-ADR-0063
   :legacy_id: D70
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   This workspace's planning folder (``claude/``: plan, research, notes, mission brief) **moves to ``xdmod/claude/``** once the xdmod repo exists (Phase 4).

.. xd-adr:: An integration repo for system tests and HIL
   :id: XD-ADR-0066
   :legacy_id: D73
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0042
   :revises: XD-ADR-0050

   **New repo ``robarm-integration``.** It holds system test cases (``INT-STC``), integration test cases (``INT-ITC``), the HIL setups, and the **orphan evidence branch** for HIL runs. Revises :need:`XD-ADR-0050`, which put that branch in robarm-sw. robarm-syseng stays the left side of the V (needs, requirements, model).

.. xd-adr:: West submanifests and project groups
   :id: XD-ADR-0079
   :legacy_id: D86
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **West submanifests and project groups.** The manifest repo splits its project list into submanifest files (one per area, e.g. framework, syseng, ee, me, sw, integration), imported by the main ``west.yml``. Projects carry **groups**, so each engineer or agent checks out only what their role needs (``manifest.group-filter``). A role's group set always includes its upstream repos and the framework (:need:`XD-ADR-0029`, :need:`XD-ADR-0059`). Details are in task 3.4.

.. xd-adr:: Pinned, isolated component libraries
   :id: XD-ADR-0080
   :legacy_id: D88
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **Component libraries are pinned west projects, isolated from user-global setups.** EE uses the tiacsys KiCad libraries (``kicad-symbols``, ``kicad-footprints``, ``kicad-packages3D``, ``kicad-templates``, ``kicad-library-utils``). ME uses the FreeCAD parts library (``FreeCAD/FreeCAD-library``). KiCad projects use project-local library tables that point into the workspace through variables, and the GUI launchers (:need:`XD-ADR-0060`, 3.13) set those variables. FreeCAD gets its parts path from its launcher. User-global libraries are not used. The big libraries (``kicad-packages3D`` about 1.8 GB, FreeCAD-library about 5.7 GB) get their own groups (:need:`XD-ADR-0079`) and shallow clones.

.. xd-adr:: The integration role
   :id: XD-ADR-0082
   :legacy_id: D90
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0079

   The **integration role** checks out everything except the big libraries (KiCad 3D models, FreeCAD parts).

.. xd-adr:: Workspace paths
   :id: XD-ADR-0083
   :legacy_id: D91
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **Workspace paths:** design repos at the top level; dependencies under ``tools/`` (zdocs, affirmatrix) and ``libs/`` (SYSMOD, KiCad, FreeCAD).

.. xd-adr:: A minimal default group filter
   :id: XD-ADR-0084
   :legacy_id: D93
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0079

   The manifest's **default group filter is minimal** (framework, syseng, Zephyr). Each role switches its groups on.

.. xd-adr:: The bootstrap assembles .claude/
   :id: XD-ADR-0103
   :legacy_id: D113
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0062

   The **bootstrap assembles ``<workspace>/.claude/``** (skills, commands) as symlinks into ``xdmod/claude/`` and the active repos' ``claude/`` folders, prefixed by repo.

.. xd-adr:: bootstrap.sh is a copy of the xdmod template
   :id: XD-ADR-0107
   :legacy_id: D118
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **``bootstrap.sh`` is a copy in robarm-manifest** (``scripts/``), made from ``xdmod/templates/bootstrap.sh``. A check warns when the copy drifts from the template.

.. xd-adr:: Tags per board, assembly and harness, made by the owner
   :id: XD-ADR-0140
   :date: 2026-11-17
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0047

   **Boards, assemblies and harnesses have their own tags** ``<name>/vX.Y.Z`` (for example
   ``joint-controller/v1.2.0``) in their domain repo, next to the repo tags (:need:`XD-ADR-0047`). The
   design output takes its version from ``git describe --match '<name>/*'``. ME tags only assemblies;
   an exported part carries the version of the assembly. **Only the owner creates these tags**, like
   baselines; an agent proposes a tag in its PR. Unfinished designs use ``v0.x`` tags, as the owner set for the canary (Phase 5 plan review, P5-12).

.. xd-adr:: Roles: EE gets FreeCAD, ME gets the KiCad files, SW gets the EE model
   :id: XD-ADR-0141
   :date: 2026-11-17
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0079

   **The roles change with the cross-domain work of Phase 5.**

   - **ee** also needs FreeCAD (``FreeCADCmd``): it imports the board's STEP export into the board
     library (:need:`XD-ADR-0139`).
   - **me** also needs the EE repo with the KiCad libraries (west group ``ee``, without the 3D models)
     and ``kicad-cli``: StepUp pushes into the ``.kicad_pcb``, and the pushed file is re-saved by KiCad
     10 (:need:`XD-ADR-0134`).
   - **sw** also gets the EE repo (west group ``ee``): SW reads the board pin maps from the EE model
     (:need:`XD-ADR-0131`).
   - Both ee and me get the board library repo once it exists (:need:`XD-ADR-0139`).

   ``tools.yaml`` and the roles of ``curatrix bootstrap`` follow; ``curatrix doctor`` warns when a role
   with ``kicad-cli`` has no KiCad 3D models (STEP and renderings then show bare boards).

.. xd-adr:: KiCad and FreeCAD never run outside curatrix; shims in .venv/bin
   :id: XD-ADR-0145
   :date: 2026-11-17
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0080

   **Never run KiCad or FreeCAD outside curatrix or its shims, not even** ``--version``. A bare
   ``kicad-cli --version`` rewrites ``~/.config/kicad/10.0/kicad_common.json``; agents did this twice.
   As a safety net, ``curatrix bootstrap`` and ``update`` write shims into ``<workspace>/.venv/bin`` for
   ``kicad-cli``, ``kicad``, ``eeschema``, ``pcbnew``, ``FreeCAD``, ``FreeCADCmd`` and ``freecad`` (each one
   that exists on the machine). A shim sets the workspace-local config that ``curatrix run`` sets and
   runs the real binary, found by absolute path when the shim is written (never ``.venv/bin`` itself or
   another shim). ``curatrix env`` puts ``.venv/bin`` first on ``PATH``; ``curatrix doctor`` warns when
   a KiCad or FreeCAD name on ``PATH`` is not the shim. Nothing outside the workspace changes: no
   user-global files, no ``PATH`` edits in shell profiles. The shims set no limits, so the tools still
   run through curatrix (:need:`XD-ADR-0064`).
