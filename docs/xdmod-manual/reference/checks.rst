.. _ref-checks:

Checks
======

curatrix runs every check with one command per repo, from the workspace root (:need:`XD-RULE-0032`):

.. code-block:: sh

   curatrix check <repo> [--stage local|pr|full|baseline] [--no-cad] [--only IDs] [--json]

The check catalogue on this page is generated from curatrix. Each check is also a need
(``XD-CHECK``) that enforces one or more method rules; see `Check needs`_ at the end.

Stages
------

.. list-table::
   :header-rows: 1
   :widths: 15 30 25 10 20

   * - Stage
     - Who runs it
     - Scope
     - CAD content
     - Purpose
   * - ``local``
     - a person or agent, one command per repo (:need:`XD-ADR-0040`), under limits (:need:`XD-ADR-0064`)
     - the repo and its upstream documents
     - yes
     - full feedback before pushing
   * - pre-commit
     - git hooks, installed by the bootstrap (:need:`XD-ADR-0091`); staged files only
     - changed files
     - no
     - normalizers, placeholder IDs, fast checks
   * - ``pr``
     - GitHub Actions per repo (:need:`XD-ADR-0041`, :need:`XD-ADR-0049`)
     - the repo and its siblings on the same branch name (:need:`XD-ADR-0045`)
     - no
     - gate for merging
   * - ``full``
     - the bump-bot job in the manifest repo (:need:`XD-ADR-0081`)
     - all repos at the new pins
     - no
     - cross-repo rules
   * - ``baseline``
     - a person, locally, before tagging ``baseline/vX.Y.Z``
     - all repos, full checkout
     - yes
     - release quality

GitHub CI runs ``--stage pr --no-cad``. Checks that need KiCad, FreeCAD or the SysML Pilot run
locally (:need:`XD-ADR-0049`). The committed CAD-derived needs let CI still see the full trace graph
(:need:`XD-ADR-0100`).

Levels
------

- **error**: the finding fails the stage.
- **warning**: the finding is reported but does not fail.
- **report**: the finding adds a summary, for example to a PR.

Catalogue
---------

.. xd-check-table::

Domain checks
-------------

Repos add their own checks as ``commands`` in their ``checks.yaml``. They are not curatrix
checks and have no ``XD-CHECK`` need. Typical domain checks compare domain content with the
interfaces in the systems engineering repo: a KiCad netlist against the pin maps, the Zephyr
devicetree against the model, FreeCAD parameters against model attributes, KiCad ERC and FreeCAD
recompute, the firmware build and unit tests.

Output
------

- Logs and a summary go to ``build/<area>/checks/``. The summary JSON
  (``build/<area>/checks/summary.json``, also printed with ``--json``) lists every check with its
  status (``pass``, ``fail``, ``warn``, ``report``, ``skip``), findings, log and reproduce command.
- For every failure, curatrix prints the command that reproduces it.
- A stage fails when any check has the status ``fail``.

The format of ``checks.yaml`` is in the curatrix reference.

Check needs
-----------

.. xd-check-needs::
