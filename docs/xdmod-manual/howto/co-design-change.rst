.. _howto-co-design-change:

Make a co-design change (ME and EE)
===================================

Use this guide when a board's mechanical interface changes: its outline, a mounting hole, the
space above or below it, a connector position. Such a change touches three repos on one branch
(:need:`XD-ADR-0134`, :need:`XD-ADR-0045`): the space budget in robarm-syseng, the board seat in
robarm-me, and the board outline in robarm-ee. It is the general :ref:`howto-cross-repo-change`
with one extra tool step, the push from FreeCAD into KiCad.

The example is the canary: the budget ``CanaryBoardSpace`` (``SYS-IF``), the seat
``CanaryBoardSeat`` (``ME-PORT``) of the canary assembly, and the canary board (``EE-PCBA``).

What sits where
---------------

.. list-table::
   :header-rows: 1

   * - Repo
     - Holds
     - Owner, reviewer
   * - robarm-syseng
     - The budget: a port def with the box (``width``, ``depth``, ``heightAbove``,
       ``heightBelow``), the hole list (``hole<n>X``, ``hole<n>Y``, ``holeDiameter``) and the
       connector positions (``<ref>X``, ``<ref>Y``, pin 1), in the board frame: origin at the
       lower-left corner of the outline seen from the top, x right, y up, z = 0 on the top face.
       Values are ``default`` values, so the domains can restate them.
     - systems engineering; reviews whether the budget still fits the system
   * - robarm-me
     - The seat: a port def that specializes the budget and restates the values FreeCAD needs;
       the port usage gives its placement (``LCS_<usage>`` in the skeleton). In the skeleton the
       sketch ``BoardOutline`` follows ``Params.<usage>_*``.
     - ME; reviews the mount, clearances and the assembly
   * - robarm-ee
     - ``dependency from <board> to <budget>`` in the EE model (the board conforms to it); outline
       and holes on ``Edge.Cuts`` of the ``.kicad_pcb``, written by the push.
     - EE; reviews the pushed file, the DRC and the connector positions, and merges its part

Steps
-----

1. **One branch, three repos:**

   .. code-block:: sh

      .venv/bin/curatrix work start feat/move-hole robarm-syseng robarm-me robarm-ee
      cd .worktrees/feat/move-hole

2. **Budget** (robarm-syseng): change the value in the budget's port def, e.g.
   ``attribute hole2X default 24 [mm];``. Then ``curatrix gen model robarm-syseng``.
3. **Seat** (robarm-me): restate the same value in the seat's port def
   (``:>> hole2X = 24 [mm];``), then write it into FreeCAD and regenerate:

   .. code-block:: sh

      curatrix gen model robarm-me
      curatrix gen freecad-params robarm-me      # Params, the sketch BoardOutline follows
      curatrix gen all robarm-me                 # semantic JSON of the skeleton

4. **Push** (into robarm-ee), always on a copy under ``build/``: copy the skeleton and the
   ``.kicad_pcb`` (with its ``.kicad_pro`` and library tables) to ``build/<area>/co-design/``, run
   the StepUp push (StepUp pinned by commit under ``.xdmod/stepup/``, ``HOME`` only for this
   process under ``.xdmod/``):

   .. code-block:: sh

      eval "$(.venv/bin/curatrix env)"
      curatrix run --use freecad -- env HOME=$PWD/.xdmod/stepup/home QT_QPA_PLATFORM=offscreen \
        XD_STEPUP=$PWD/.xdmod/stepup/kicadStepUpMod XD_BOARD=$PWD/build/<area>/co-design/<board>.kicad_pcb \
        XD_SKELETON=$PWD/build/<area>/co-design/<asm>-skeleton.FCStd XD_RESULT=$PWD/build/<area>/co-design/push.json \
        FreeCAD xdmod/templates/codesign/stepup-push.py

   It replaces everything on ``Edge.Cuts`` with the sketch: the outline and the holes as circles
   (non-plated cut-outs). The board frame lands on the grid origin, or on the lower-left corner of
   the old outline. ``push.json`` says ``"ok": true`` and lists the new items. Then re-save the
   copy by KiCad 10, run DRC on it, and only then copy it back into the repo:

   .. code-block:: sh

      curatrix run --use kicad-cli -- kicad-cli pcb upgrade --force build/<area>/co-design/<board>.kicad_pcb
      curatrix run --use kicad-cli -- kicad-cli pcb drc --format json --severity-all \
        -o build/<area>/co-design/drc.json build/<area>/co-design/<board>.kicad_pcb
      cp build/<area>/co-design/<board>.kicad_pcb robarm-ee/pcba/<board>/

5. **Check** all three repos with CAD content, then ``curatrix ids fix`` where new IDs came in:

   .. code-block:: sh

      curatrix check robarm-syseng --stage local
      curatrix check robarm-me --stage local
      curatrix check robarm-ee --stage local

6. **Three PRs**, each naming the other two. Merge order: robarm-syseng, then robarm-me, then
   robarm-ee (the push result). A PR that needs a newer curatrix waits for the xdmod merge and the
   manifest bump.

Who reviews what
----------------

- **robarm-syseng PR:** the budget values and their meaning; ME and EE comment when the budget
  does not fit them.
- **robarm-me PR:** the seat values equal the budget, CK-F3 is green, the skeleton recomputes.
- **robarm-ee PR:** the EE role reviews the pushed ``.kicad_pcb`` (only ``Edge.Cuts`` changed, plus
  the KiCad re-save), the DRC findings, and that the connectors still sit at the budget's
  positions. EE owns and merges its part. ME never writes into the EE repo outside such a branch.

Conflicts
---------

- **EE needs a different budget** (a bigger box, a hole elsewhere): EE does not push geometry back.
  EE asks for a budget change in the syseng PR of the same branch (or opens a co-design branch of
  its own); ME then follows with the seat and the push. The board model reaches FreeCAD by the
  STEP export of a tagged board (board library), not through StepUp.
- **EE changed the outline by hand in KiCad:** the next push overwrites ``Edge.Cuts``. Bring the
  change into the budget first, then push.
- **Two branches change the same budget:** the second rebases, takes the merged values, and pushes
  again; never merge two ``.kicad_pcb`` files by hand.

Checks
------

- CK-F3: the seat's values in the skeleton's ``Params`` and its LCS equal the ME model.
- CK-F4b: DRC of the pushed board (the push itself adds no findings on the canary).
- Planned (ME checks, task 5.25), "board inside its space budget": the seat's restated values
  equal the budget's; the KiCad outline and ``Edge.Cuts`` circles equal ``width``, ``depth`` and the
  hole list; each connector named in the budget sits at its position (footprint pin 1, in the
  board frame); the board model (STEP) placed at the seat's LCS fits the box and does not collide
  with the direct children of the assembly.

Pitfalls
--------

- Never run StepUp with your own ``HOME``: it writes ``~/ksu-config.ini``. Never run FreeCAD or
  KiCad outside curatrix or its shims.
- The push needs the FreeCAD GUI binary (StepUp imports ``FreeCADGui``); offscreen it must not open
  a dialog, so the script replaces them by log lines. StepUp's board load (KiCad to FreeCAD) stalls
  offscreen: use the STEP path.
- ``kicad-cli pcb upgrade`` needs ``--force`` (StepUp keeps the version header) and may add a few
  default values (text thickness) to footprints on the first re-save.
- Every push gives all ``Edge.Cuts`` items new UUIDs, so a KiCad DRC exclusion on one of them is
  lost; accept such findings in ``accepted.yaml`` instead.
- A budget value is a ``default`` in syseng; ``=`` would bind it, and the seat could not restate it.
