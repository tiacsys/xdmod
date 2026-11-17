.. _howto-cross-repo-change:

Make a change across repos
==========================

Use this guide when one change touches more than one repo, for example a new system requirement
plus the domain requirements and design that follow from it.

Steps
-----

1. **One branch name** for the change, in every repo it touches (:need:`XD-ADR-0045`), e.g.
   ``feat/latency``. Work in a worktree set, so the main checkouts stay untouched
   (:need:`XD-ADR-0114`):

   .. code-block:: sh

      curatrix work start feat/latency robarm-syseng robarm-sw
      cd .worktrees/feat/latency

   Builds of the set go to ``build/wt-feat-latency/``.

   .. note:: ``curatrix work`` is being added (task 4.4c). Until it is on ``main``, make the
      worktrees by hand: ``git -C <repo> worktree add ../.worktrees/<branch>/<repo> -b <branch>``.

2. **Author** the change in each repo, run ``curatrix gen`` and ``curatrix ids fix`` where
   needed.
3. **Check every repo you touched**, with CAD content where the repo has it (:need:`XD-ADR-0040`):

   .. code-block:: sh

      curatrix check robarm-syseng --stage local
      curatrix check robarm-sw --stage local

4. **Open one PR per repo.** Each PR lists its sibling PRs and the affected needs, and ends with
   the provenance trailer (:need:`XD-ADR-0065`).
5. **PR CI** checks each repo without CAD content (:need:`XD-ADR-0049`). For sibling repos it uses, in
   this order: a branch with the same name; the repo's ``main`` if the manifest pin is an
   ancestor of it; the manifest pin (:need:`XD-ADR-0116`).
6. **Merge upstream first**: syseng, then the domains, then integration. Framework changes merge
   before the repos that use them. Every PR is rebase-merged (:need:`XD-ADR-0043`).
7. **Bump.** The bump bot in the manifest repo collects the new ``main`` SHAs into one bump PR and
   builds the full set (:need:`XD-ADR-0054`, :need:`XD-ADR-0081`). Merging it moves the pins (:need:`XD-ADR-0033`).
8. When everything is merged:

   .. code-block:: sh

      curatrix work done feat/latency

Roles
-----

The bootstrap's role decides which repos you have. A role always includes its upstream repos and
the framework (:need:`XD-ADR-0079`).

.. list-table::
   :header-rows: 1

   * - Role
     - Group filter
     - You get
   * - ``syseng`` (default)
     - (manifest default)
     - framework, syseng, libraries, Zephyr
   * - ``ee`` / ``ee3d``
     - ``+ee`` / ``+ee,+kicad-3d``
     - plus the EE repo and KiCad libraries (with 3D models)
   * - ``me``
     - ``+me,+freecad-parts,+ee``
     - plus the ME repo, the FreeCAD parts library, the EE repo and KiCad libraries
   * - ``sw``
     - ``+sw,+ee``
     - plus the SW repo and the EE repo
   * - ``integration``
     - ``+ee,+me,+sw,+integration``
     - every repo without the big libraries (:need:`XD-ADR-0082`)
   * - ``full``
     - all groups
     - everything

Pitfalls
--------

- ``west update`` moves repos back to their pins (detached HEAD). On branches use
  ``curatrix update``. Never run either inside a worktree set.
- A ledger conflict after a rebase means two PRs issued the same ID. Rerun ``curatrix ids fix``.
