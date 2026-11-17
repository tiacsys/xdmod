.. _howto-review-a-domain-pr:

Review an EE or ME pull request from a local docs build
=======================================================

Use this guide when you review a PR of robarm-ee or robarm-me as the owner or a domain engineer.
PR CI has no KiCad, FreeCAD or Blender, so it checks only the plain-Python part and its documents
show a fixed sentence where renderings, schematics, drawings and findings belong
(:need:`XD-ADR-0049`). You see the whole change only in a local build: the checks with CAD content,
the design output and the board or assembly document made from them. The agent review
(``/xd-review-pr``, :need:`XD-ADR-0115`) runs the same checks first and posts the result table; this
guide is the human review after it.

1. Get the change
-----------------

Review in a worktree set of your own, so neither the main checkouts nor the author's set change.
Put every repo of the change into it (same branch name, :need:`XD-ADR-0045`), and xdmod too when the
change needs an unmerged xdmod PR:

.. code-block:: sh

   .venv/bin/gh pr view 15 -R tiacsys/robarm-ee --json headRefName,headRefOid,files
   .venv/bin/curatrix work start review/robarm-ee-15 robarm-ee
   cd .worktrees/review/robarm-ee-15
   git -C robarm-ee fetch origin feat/move-hole && git -C robarm-ee checkout --detach FETCH_HEAD
   git -C robarm-ee rev-parse HEAD          # equals headRefOid

Repeat the ``fetch`` and ``checkout`` for each sibling repo. From now on, run every command from the
set root and call curatrix as ``.venv/bin/curatrix`` (inside the set it runs the set's xdmod). The
build area of the set is ``build/wt-review-robarm-ee-15/`` in the workspace, reached through the
set's ``build`` link.

2. Run the checks with CAD content
----------------------------------

.. code-block:: sh

   .venv/bin/curatrix check robarm-ee --stage local
   .venv/bin/curatrix check robarm-me --stage local

This is the run of every check that needs a CAD tool (EE: CK-D8, CK-D9, CK-F4a, CK-F4b; ME: CK-F4c,
CK-F16, CK-F17, CK-F18; both: CK-D10). Compare it with the table the agent reviewer posted. A warning
of CK-D10 here only means that the design output of this commit is not made yet (next step).

3. Make the design output and build the documents
-------------------------------------------------

.. code-block:: sh

   .venv/bin/curatrix cam robarm-ee <board>
   .venv/bin/curatrix docs robarm-ee --open
   .venv/bin/curatrix cam robarm-me <assembly>          # with Blender if installed
   .venv/bin/curatrix docs robarm-me --open

``docs`` prints the path of the start page (``build/<area>/docs/deploy/html/<doc>/index.html``,
inside the set's build area); ``--open`` opens it. The pages to read are ``pcba-<board>``,
``harness-<name>``, ``asm-<assembly>`` and the design document (``ee-design``, ``me-design``). The
output is a preview (red ``PREVIEW`` marking): a PR branch is never a release
(:ref:`howto-design-output`).

To compare with what is merged, build the same documents in the main checkouts (from the workspace
root, ``curatrix cam ...`` and ``curatrix docs ...``) and open both side by side; they go to
``build/robarm-ee/`` and ``build/robarm-me/``.

4. What to look at
------------------

.. list-table::
   :header-rows: 1

   * - Document section
     - Board (EE)
     - Assembly (ME)
   * - Overview, variants
     - board def, ``EE-PCBA``, the system element it realizes, the variants and the configurations
       they serve
     - assembly def, ``ME-ASM``, sub-assemblies, the variants by ``Configs``
   * - Pictures
     - top, bottom and 3D renderings; schematic per variant
     - drawing, exploded view, front/top/right/iso renderings (``cam.json`` says Blender or
       fallback)
   * - Values
     - stackup, design rules, connector pin tables against the pin maps of the model
     - parameters (model values and ``Params``; budget copies marked), interfaces with placement,
       materials, mass and center of gravity
   * - Findings
     - ERC and DRC findings with their state: open, excluded in KiCad, accepted, proposed
     - recompute, solid and collision findings with their state
   * - Appendix
     - BOM with a column per variant; every part with Manufacturer and MPN
     - indented BOM; fasteners by standard designation, boards and harnesses as one line each

Also read the diff itself: ``git -C robarm-me diff origin/main...HEAD`` shows ``.FCStd`` changes as
semantic JSON (the textconv driver of the bootstrap); on GitHub, read the committed
``generated/freecad/*.json`` instead. KiCad files are text and diff directly. For a co-design change,
follow the review split of :ref:`howto-co-design-change`.

5. Accept findings, comment, merge
----------------------------------

- **Proposed acceptances.** An agent PR may add entries to ``pcba/<name>/accepted.yaml`` or
  ``assemblies/<name>/accepted.yaml``; they stay proposals. To accept one, make your own commit on
  the branch that changes only that entry (for example its ``reason``) and carries
  ``Accepted-by: <your name>`` and no agent trailer (:need:`XD-ADR-0126`). Run the check again: the
  finding now shows as accepted.
- **Comments** go into the PR. Ask for a fix rather than fixing it in the review set; the set is
  detached and is thrown away.
- **Merge** upstream first (syseng, then ME, then EE for a co-design change), then the bump PR in the
  manifest (:ref:`howto-cross-repo-change`).
- **Clean up** the review set:

  .. code-block:: sh

     cd <workspace root>
     .venv/bin/curatrix work done review/robarm-ee-15

Pitfalls
--------

- Never ``work start`` the PR's own branch name for a review: it reuses the author's set or an old
  local branch. Use ``review/<repo>-<n>`` and a detached checkout.
- A docs build of the set without a ``cam`` run of the same commit shows the fixed sentences, as in
  CI. Run ``cam`` first.
- zdocs may keep an old page after a curatrix change of a directive; delete
  ``build/<area>/docs/`` of the set and build again.
- Do not run ``curatrix update`` or ``west update`` inside a set.
