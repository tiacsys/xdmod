.. _howto-add-a-part:

Add a FreeCAD part or assembly
==============================

Use this guide when you add a FreeCAD part (``ME-PART``) or assembly (``ME-ASM``) that takes part
in trace links.

Steps
-----

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

``curatrix cam`` writes the design output of a top-level assembly under
``build/<repo>/cam/<assembly>/<version>/`` (:need:`XD-ADR-0143`): STEP, the printed parts, the
drawing, the exploded view, the BOM and four renderings per variant
(``renderings/front|top|right|iso.png``):

.. code-block:: sh

   curatrix cam robarm-me canary-assembly                # Blender if installed, else the fallback
   curatrix cam robarm-me canary-assembly --no-blender   # always the renderer without Blender

With Blender on the machine the renderings come from Blender (Cycles on the CPU, about 10 to 20
seconds per view); without it from a plain-Python renderer in ``FreeCADCmd``
(:need:`XD-ADR-0147`). ``cam.json`` says which (``renderings.method``: ``blender`` or ``zbuffer``).
Blender is optional and not pinnable, so these images are local only; CI never has Blender
(:need:`XD-ADR-NEW-blender`). Run Blender only through curatrix (``curatrix run -- blender``,
``curatrix launch blender``) or the ``.venv/bin/blender`` shim: they add ``--factory-startup`` and
keep its user files in ``.xdmod/blender/``. ``curatrix doctor`` shows the Blender version.

Pitfalls
--------

- ``.FCStd`` files can't be merged. On a conflict, take one side and redo the other change.
- An unchanged save still changes the file. The pre-commit hook warns when a ``.FCStd`` changed
  but its semantic JSON didn't.
