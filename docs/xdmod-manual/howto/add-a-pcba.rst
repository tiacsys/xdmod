.. _howto-add-a-pcba:

Add a PCBA or circuit block
===========================

Use this guide when you add a KiCad project (a PCBA), a circuit block or a component that takes
part in trace links. Prototype wiring is EE content too: a KiCad schematic of the prototype
setup whose elements carry ``configs`` (:need:`XD-ADR-0067`).

Trace IDs live inside the KiCad files (:need:`XD-ADR-0023`). The docs read them from there.

Steps
-----

1. Make the KiCad project in the EE repo (e.g. ``pcba/<name>/``). Use only the workspace
   libraries: start KiCad with the launcher, which sets the library paths and keeps your
   user-global setup out (:need:`XD-ADR-0080`):

   .. code-block:: sh

      curatrix launch kicad robarm-ee/pcba/<name>/<name>.kicad_sch

2. For the PCBA itself, set text variables in ``<name>.kicad_pro``. For circuit blocks and
   components, add **hidden** symbol or sheet fields:

   .. list-table::
      :header-rows: 1

      * - Field
        - Value
      * - ``TraceID``
        - the need ID (kind ``EE-PCBA`` or ``EE-CMP``); write a placeholder ID, then issue it
      * - ``Realizes``
        - the product-layer ``SYS-EL`` IDs (comma list)
      * - ``Satisfies``
        - ``EE-REQ`` IDs
      * - ``Conforms``
        - ``SYS-IF`` IDs of the interfaces it meets
      * - ``PartOf``
        - the ``EE-PCBA`` ID
      * - ``Status``
        - ``draft``, ``valid`` or ``retired``
      * - ``Configs``
        - ``SYS-CFG`` IDs, if it belongs only to some configurations

   A sheet used several times carries one ID; its usages become ``instances`` (:need:`XD-ADR-0117`).

3. List the root schematic in the repo's ``checks.yaml`` under ``cad.kicad``, then issue the IDs
   and regenerate the CAD needs:

   .. code-block:: sh

      curatrix ids fix robarm-ee
      curatrix gen cad-needs robarm-ee

   Commit ``generated/cad-needs.json`` (:need:`XD-ADR-0100`).

4. Show the schematic in the PCBA document with ``kicad-sheet``, ``kicad-bom`` and ``kicad-nets``.
   Make the exports locally with ``curatrix gen cad-exports robarm-ee``. In CI the directives show
   a "built locally" notice (:need:`XD-ADR-0049`).

Checks
------

- :need:`XD-CHECK-0019`: ``cad-needs.json`` matches the KiCad files (plain Python, no KiCad needed).
- :need:`XD-CHECK-0004`: each element realizes or satisfies something (:need:`XD-RULE-0010`).
- Domain checks such as the netlist against the interface pin maps, and ERC, are commands in the
  repo's ``checks.yaml``.

Pitfalls
--------

- Hidden fields are easy to lose when you replace a symbol. Check ``cad-needs.json`` in the diff.
- There is one design document per PCBA and one per prototype configuration (:need:`XD-ADR-0102`).
