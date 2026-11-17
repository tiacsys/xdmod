.. _ref-workspace:

Workspace
=========

Paths, roles, environment and limits of an XDMOD workspace. Background:
:doc:`../explanation/multi-repo`.

Layout
------

The workspace root is the west topdir (:need:`XD-ADR-0061`). Every command runs from here
(:need:`XD-ADR-0060`); paths in output and documents are relative to it.

.. code-block:: text

   <workspace>/
     .west/                west config, incl. manifest.group-filter and the role
     .venv/                workspace venv: west, curatrix, pinned packages, opt/ tools
     .xdmod/               workspace-local tool configs, caches, limit overrides (not a repo)
     .claude/              links to the shared and per-repo agent skills and commands
     .worktrees/<branch>/  worktree sets for parallel work
     build/<area>/         all build output
     CLAUDE.md             launch file, copied from xdmod by the bootstrap
     <manifest repo>/
     xdmod/
     <design repos>/       one per domain, plus integration, at the top level
     tools/                zdocs, affirmatrix
     libs/                 SYSMOD library, PLEML, KiCad and FreeCAD libraries
     zephyr/  modules/     Zephyr and its allowlisted modules, if the project uses Zephyr

Design repos sit at the top level, because people and agents work in them. Dependencies go
under ``tools/`` and ``libs/`` (:need:`XD-ADR-0083`).

Roles
-----

A role decides which repos a workspace checks out, through west's group filter
(:need:`XD-ADR-0079`). The manifest's default is minimal (:need:`XD-ADR-0084`). The roles that curatrix knows:

.. list-table::
   :header-rows: 1
   :widths: 15 35 50

   * - Role
     - Group filter (added to the default)
     - Gets
   * - ``syseng``
     - (manifest default)
     - framework, systems engineering, SYSMOD and PLEML libraries, Zephyr
   * - ``ee``
     - ``+ee``
     - plus the EE repo and the KiCad libraries without 3D models
   * - ``ee3d``
     - ``+ee,+kicad-3d``
     - like ``ee``, plus the KiCad 3D models
   * - ``me``
     - ``+me,+freecad-parts,+ee``
     - plus the ME repo, the FreeCAD parts library, and the EE repo with the KiCad libraries
       (:need:`XD-ADR-0141`)
   * - ``sw``
     - ``+sw,+ee``
     - plus the SW repo and the EE repo, for the board pin maps (:need:`XD-ADR-0131`)
   * - ``integration``
     - ``+ee,+me,+sw,+integration``
     - everything except the big libraries (:need:`XD-ADR-0082`)
   * - ``full``
     - all groups
     - everything, for local full builds and baselines
   * - ``ci-full``
     - same as ``integration``
     - what the full-set CI job uses; CI builds without CAD content (:need:`XD-ADR-0049`)

Set or change the role with ``curatrix bootstrap --role <role>``. Repos that become inactive are
left on disk.

Bootstrap
---------

From an empty folder (example: the robot arm's manifest repo):

.. code-block:: sh

   git clone https://github.com/tiacsys/robarm-manifest
   robarm-manifest/scripts/bootstrap.sh --role ee

``bootstrap.sh`` creates ``.venv`` with west, runs ``west init -l`` and ``west update``,
installs curatrix from xdmod (editable), and hands over to ``curatrix bootstrap --role <role>``.
That command:

1. sets the role's group filter and runs ``west update``;
2. installs the active repos' ``requirements.txt`` into ``.venv`` and their ``tools.yaml``
   tools into ``.venv/opt/``, with sha256 checks (:need:`XD-ADR-0014`);
3. copies ``xdmod/launch/CLAUDE.md`` to the root (:need:`XD-ADR-0062`) and links ``.claude/``
   (:need:`XD-ADR-0103`);
4. installs the pre-commit hooks and the FreeCAD diff driver in every active repo
   (:need:`XD-ADR-0091`);
5. creates ``.xdmod/``;
6. runs ``curatrix doctor``.

On branches, use ``curatrix update`` (it runs ``west update -k``). Plain ``west update`` moves
every project back to its pin, as a detached HEAD.

Environment
-----------

``eval "$(curatrix env)"`` sets ``PATH`` (with ``.venv/bin``), ``ZEPHYR_BASE``, ``JAVA_HOME``,
the ``XD_KICAD_*`` and ``XD_FREECAD_PARTS`` library variables, the ``env:`` entries of the
``tools.yaml`` tools, and ``PYTHONDONTWRITEBYTECODE=1``. ``curatrix run -- <cmd>`` runs any
command with this environment and the default limits.

No user-global configuration is used. KiCad, FreeCAD and drawio get workspace-local config
folders under ``.xdmod/`` through ``curatrix launch`` (:need:`XD-ADR-0080`).

Limits
------

Every tool runs under a memory limit and a timeout (:need:`XD-ADR-0064`, :need:`XD-RULE-0044`). curatrix applies
them itself from ``xdmod/curatrix/limits.yaml``, which ``<workspace>/.xdmod/limits.yaml`` can
override per key. ``curatrix limits`` shows the resolved table.

- Backend: a systemd user scope with ``MemoryMax`` and no swap, plus ``timeout``. Without a
  systemd user session, curatrix falls back to ``timeout`` plus ``ulimit -v``.
- Exit code 124 means timeout, 137 means killed for memory.
- GUI tools started with ``curatrix launch`` get a memory limit only, no timeout
  (:need:`XD-ADR-0106`).
- Never raise a limit to make a runaway tool pass; find out why it runs away.

Commands
--------

``curatrix`` is the only command layer (:need:`XD-ADR-0089`, :need:`XD-ADR-0105`). The full list of subcommands
and options is in the curatrix reference. The most used:

.. list-table::
   :header-rows: 1
   :widths: 40 60

   * - Command
     - Does
   * - ``curatrix doctor``
     - checks tools, versions, paths, hooks and the west state
   * - ``curatrix update``
     - ``west update -k``, refresh ``.venv``, tools, ``.claude/`` links and hooks
   * - ``curatrix check <repo> --stage local``
     - the repo's checks (:doc:`checks`)
   * - ``curatrix docs <repo>`` / ``docs full``
     - strict docs build into ``build/<area>/docs/``
   * - ``curatrix gen <what> <repo>``
     - regenerate the committed generated files
   * - ``curatrix ids new <KIND>`` / ``ids fix <repo>``
     - issue IDs, replace placeholders (:doc:`id-scheme`)
   * - ``curatrix views build|check|normalize <repo>``
     - views as editable ``.drawio.svg``
   * - ``curatrix launch kicad|freecad|drawio|claude``
     - GUI tools with workspace-local config
   * - ``curatrix work start|done``
     - worktree sets for parallel work (:need:`XD-ADR-0114`)
   * - ``curatrix run -- <cmd>``
     - anything else, with the workspace env and limits
