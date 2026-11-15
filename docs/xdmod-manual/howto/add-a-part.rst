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
   (:need:`XD-ADR-0124`). Publishing it as a Pages preview (:need:`XD-ADR-0098`) comes later. TechDraw and GLB
   exports are not implemented yet.

Pitfalls
--------

- ``.FCStd`` files can't be merged. On a conflict, take one side and redo the other change.
- An unchanged save still changes the file. The pre-commit hook warns when a ``.FCStd`` changed
  but its semantic JSON didn't.
