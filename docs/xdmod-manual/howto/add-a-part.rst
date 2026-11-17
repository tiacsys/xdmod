.. _howto-add-a-part:

Add a FreeCAD part or assembly
==============================

Use this guide when you, in the ME role, add a new assembly (``ME-ASM``) with its skeleton,
parameters, interfaces, checks, design output and assembly document, or a FreeCAD part
(``ME-PART``) that takes part in trace links. The example is the canary assembly
``canary-assembly`` of robarm-me.

Work on a branch in a worktree set (:ref:`howto-cross-repo-change`):

.. code-block:: sh

   .venv/bin/curatrix work start feat/my-assembly robarm-me
   cd .worktrees/feat/my-assembly

New assembly
------------

1. **Assembly def.** Add it to ``model/`` in the ME repo: ``part def <'ME-ASM-NEW-a'> MyAssembly
   :> <the SYS-EL def>, XdDomain::Assembly``, with a part usage per part or sub-assembly and a port
   usage per interface (a port def that specializes ``XdDomain::MechanicalPort``, ``ME-PORT``; the
   usage gives ``x``, ``y``, ``z`` and the angles). The assembly's driving parameters are attributes
   of its usages, at most ten per top-level assembly (:need:`XD-ADR-0137`). Then:

   .. code-block:: sh

      curatrix ids fix robarm-me
      curatrix gen model robarm-me

2. **FreeCAD documents and the assembly document.** ``curatrix new asm`` writes them with
   ``FreeCADCmd`` (:need:`XD-ADR-0137`, :need:`XD-ADR-0146`):

   .. code-block:: sh

      curatrix new asm MyAssembly --repo robarm-me

   It makes ``assemblies/<name>/`` (``<name>`` = the def's name in kebab case) with the top document
   ``<name>.FCStd`` (an assembly with ``TraceID`` = the def's ``ME-ASM``, a ``Joints`` group and a
   link to the skeleton) and ``<name>-skeleton.FCStd`` (the spreadsheet ``Params`` and the master
   sketch ``MasterSketch`` in the part ``Skeleton``), plus the document ``docs/asm-<name>/`` and its
   registry entry.

3. **Parameters from the model.** Write the model values into ``Params`` (aliases
   ``<usage>_<attribute>``, e.g. ``canaryPart_length``); parts and the master sketch take their
   dimensions from there by expressions:

   .. code-block:: sh

      curatrix gen freecad-params robarm-me

   Change a value in the model and run this command again; never type it into ``Params``.

4. **Parts.** Own parts of the assembly go to ``assemblies/<name>/parts/``, shared parts to
   ``parts/``, bought parts and fasteners to ``lib/`` (a fastener has a ``Standard`` property such as
   ``ISO 4762 M3x10, A2``). Each part gets a ``TraceID`` (``ME-PART``, see "New part" below), an own
   part a ``Material``, a bought part ``Manufacturer`` and ``MPN``. A printed part names its print
   profile in ``PrintProfile`` (a file in ``print/``) and has one LCS with ``Role = version-emboss``
   where ``curatrix cam`` embosses the version (CK-F19).

5. **Links and interfaces.** Add one FreeCAD link per usage of the model to the top document; a part
   that exists only in some configurations names them in the link's ``Configs`` property (on the
   link, not on the part, :need:`XD-ADR-0138`). Every port usage is an LCS in the skeleton named
   ``LCS_<usage>`` with a ``Port`` property = its ``ME-PORT`` ID; its placement comes from
   ``Params``.

6. **Regenerate and check.** Write the CAD needs and the semantic JSON, then run the checks with
   CAD content:

   .. code-block:: sh

      curatrix gen all robarm-me
      curatrix check robarm-me --stage local

   The FreeCAD checks (CK-F4c recompute, CK-F16 valid solids, CK-F17 collisions between the direct
   children, CK-F18 boards in their space budget) run only locally. Accept a finding that is
   intended in ``assemblies/<name>/accepted.yaml`` (same format as the EE file,
   :need:`XD-ADR-0126`): **agents only propose** the entry, the ME engineer or the owner accepts it
   with an own commit carrying ``Accepted-by: <name>``.

7. **Design output and the document.** ``curatrix cam robarm-me <name>``, then ``curatrix docs
   robarm-me`` (:ref:`howto-design-output`). The PR names the proposed ``accepted.yaml`` entries;
   the reviewer follows :ref:`howto-review-a-domain-pr`.

New part
--------


1. Start FreeCAD with the launcher. It uses a workspace-local config that saves ``.FCStd`` files
   **uncompressed** and points at the pinned parts library (:need:`XD-ADR-0056`, :need:`XD-ADR-0080`):

   .. code-block:: sh

      curatrix launch freecad robarm-me/parts/link.FCStd

2. Add string properties in the group ``Trace`` to the part or assembly object: ``TraceID``,
   ``Realizes``, ``Satisfies``, ``Conforms``, ``PartOf``, ``Status``, ``Configs``. They mean the
   same as the KiCad fields (:doc:`add-a-pcba`).
3. Set the ``TraceID`` to a real ID. Placeholders inside ``.FCStd`` files are refused, so issue
   the ID first:

   .. code-block:: sh

      curatrix ids new ME-PART --repo robarm-me

4. Keep parameters in a spreadsheet with aliases. The ``freecad-params`` directive shows them in
   the docs, also in CI.
5. Regenerate the CAD needs and the semantic JSON, and commit both with the part:

   .. code-block:: sh

      curatrix gen cad-needs robarm-me
      curatrix gen freecad-json robarm-me

Checks
------

- :need:`XD-CHECK-0025`: the ``.FCStd`` is stored uncompressed (:need:`XD-RULE-0039`).
- :need:`XD-CHECK-0019`: ``cad-needs.json`` matches the FreeCAD files.
- :need:`XD-CHECK-0020`: the generated files record the tool versions that made them.
- CK-F14, CK-F15: one document per assembly def and back; FreeCAD links per part equal the usages.
- CK-F3: the skeleton's ``Params`` and the LCS placements equal the ME model.
- CK-F4c, CK-F16, CK-F17, CK-F18 (local, FreeCAD): recompute, valid solids, collisions, boards in
  their space budget; CK-F9 the acceptance of their findings.
- CK-F12, CK-F19: Manufacturer and MPN or ``Material``; one version mark per printed part.
- CK-D10 (local): the ``curatrix cam`` output of the current commit exists.

For review, ``git diff`` shows ``.FCStd`` changes as semantic JSON through the textconv driver
that the bootstrap installs. GitHub does not, so reviewers read the committed JSON.

.. note:: The full review report (drawing SVGs, image diff, 3D views) stays local in iteration 1
   (:need:`XD-ADR-0124`). Publishing it as a Pages preview (:need:`XD-ADR-0098`) comes later. The
   drawings and the exploded view of an assembly come from ``curatrix cam`` (see below); GLB
   exports are not implemented yet.

The assembly document
---------------------

Every top-level assembly has one document ``asm-<name>`` (:need:`XD-ADR-0129`), made by
``curatrix new asm`` with the same sections for every assembly, and a chapter per sub-assembly.
Each section is one ``xd-asm-*`` directive with the assembly name as its argument:

.. list-table::
   :header-rows: 1

   * - Section
     - Directive
     - Source
     - In CI
   * - Overview
     - ``xd-asm-overview``
     - FreeCAD files, local output (version)
     - yes, without the version
   * - Drawings
     - ``xd-asm-drawing``
     - ``drawing.svg`` per variant; the PDF is named, not linked
     - fixed sentence
   * - Exploded view
     - ``xd-asm-exploded``
     - ``exploded.svg`` per variant (``explode.yaml`` or automatic moves)
     - fixed sentence
   * - Renderings
     - ``xd-asm-renderings``
     - ``<variant>/renderings/<view>.png`` (front, top, right, iso), as ``cam.json`` lists them
     - fixed sentence
   * - Mass and center of gravity
     - ``xd-asm-mass``
     - ``mass.json`` per variant
     - fixed sentence
   * - Parameters
     - ``xd-asm-parameters``
     - ME model and the skeleton's ``Params`` (budget copies marked)
     - yes
   * - Materials
     - ``xd-asm-materials``
     - ``Material`` and ``PrintProfile`` of the parts, densities of ``curatrix/data/materials.yaml``
     - yes
   * - Interfaces
     - ``xd-asm-interfaces``
     - the ports of the assembly def: ``ME-PORT``, ``SYS-IF``, placement, LCS, values
     - yes
   * - Findings
     - ``xd-asm-findings``
     - ``findings.json``: CK-F4c, CK-F16, CK-F17 with their acceptance state
     - fixed sentence
   * - Sub-assemblies
     - ``xd-asm-subassemblies``
     - one chapter per sub-assembly (overview, interfaces, materials, mass, findings with ``:sub:``)
     - partly
   * - Appendix: bill of materials
     - ``xd-asm-bom``
     - the indented BOM along the structure, a quantity column per variant
     - yes

The local sections show only the ``curatrix cam`` output of the commit the repo is at
(:need:`XD-RULE-0060`); CK-D10 warns locally when it is missing. Make it before you build the
document:

.. code-block:: sh

   curatrix cam robarm-me <name>
   curatrix docs robarm-me

The mass is the solid volume of each present part times the density of its ``Material``, or the
part's own ``Mass`` (``12 g``) or ``Density`` (``1.24 g/cm^3``) property; both need a unit, and a
density outside 0.01 to 25 g/cm³ is refused. Printed parts count as solid; the infill of the print
profile is not applied, so their mass is an upper bound. The center of gravity is in the frame of
the top-level assembly. A sub-assembly chapter shows the mass of its first use; drawings, exploded
view, renderings and parameters exist only for the top-level assembly (iteration 1), so these
sections of a sub-assembly chapter print a fixed sentence.

In the BOM, a standard fastener (any object with a ``Standard`` property such as
``ISO 4762 M3x10, A2``, usually in ``lib/``) is named by its standard designation; another bought
part (a ``lib/`` object, or one with ``Manufacturer`` or ``MPN``) names
``Manufacturer`` and ``MPN``; a board model or harness is one line with its version and its
``pcba-<name>`` / ``harness-<name>`` document, its parts stay in the EE BOM. CK-F12 warns about a
bought part without them and about an own part without ``Material`` (:need:`XD-RULE-0058`).

Design output and renderings
----------------------------

``curatrix cam robarm-me <name>`` writes STEP, the printed parts, the drawing, the exploded view, the
BOM, the mass and four renderings per variant; the renderings come from Blender when it is
installed, else from the plain-Python fallback. See :ref:`howto-design-output`.

Pitfalls
--------

- ``.FCStd`` files can't be merged. On a conflict, take one side and redo the other change.
- An unchanged save still changes the file. The pre-commit hook warns when a ``.FCStd`` changed
  but its semantic JSON didn't.
- Open an assembly's skeleton before its top document; opened through the top document it loads
  only partly. ``gen freecad-params`` does this for you.
- Never run FreeCAD or Blender outside curatrix or its ``.venv/bin`` shims (:need:`XD-ADR-0145`).
