.. _howto-add-a-pcba:

Add a PCBA or circuit block
===========================

Use this guide when you add a KiCad project (a PCBA), a circuit block or a component that takes
part in trace links. Prototype wiring is EE content too: a KiCad schematic of the prototype
setup whose elements carry ``configs`` (:need:`XD-ADR-0067`).

The board itself is a def in the EE model; the KiCad project only names it
(:need:`XD-ADR-0128`). Circuit blocks and components keep their trace IDs inside the KiCad files
(:need:`XD-ADR-0023`).

Steps
-----

0. Add the board def to ``model/`` in the EE repo: ``part def <'EE-PCBA-NEW-a'> MyBoard :>
   <the SYS-EL def>, XdDomain::Pcba``, with a connector port def (``EE-PORT``) for every port it
   inherits (:need:`XD-ADR-0130`). Run ``curatrix ids fix robarm-ee`` and ``curatrix gen model
   robarm-ee``; ``realizes`` and ``conforms`` come from ``:>``.

1. Make the KiCad project in the EE repo (e.g. ``pcba/<name>/``). Use only the workspace
   libraries: start KiCad with the launcher, which sets the library paths and keeps your
   user-global setup out (:need:`XD-ADR-0080`):

   .. code-block:: sh

      curatrix launch kicad robarm-ee/pcba/<name>/<name>.kicad_sch

2. For the PCBA itself, set the text variable ``TraceID`` in ``<name>.kicad_pro`` to the board
   def's ``EE-PCBA`` ID: a reference, the need comes from the model. For circuit blocks and
   components, add **hidden** symbol or sheet fields:

   .. list-table::
      :header-rows: 1

      * - Field
        - Value
      * - ``TraceID``
        - the need ID (kind ``EE-CMP``); write a placeholder ID, then issue it
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
- :need:`XD-CHECK-0016`, :need:`XD-CHECK-0017`: the EE model parses and its generated files are fresh.
- :need:`XD-CHECK-0033`: the board def redefines every inherited port with a fitting port def.
- :need:`XD-CHECK-0001`: the strict docs build; its needs schema fails an element that realizes or satisfies nothing (:need:`XD-RULE-0010`).
- Domain checks such as the netlist against the interface pin maps, and ERC, are commands in the
  repo's ``checks.yaml``.

Pitfalls
--------

- Hidden fields are easy to lose when you replace a symbol. Check ``cad-needs.json`` in the diff.
- There is one design document per PCBA and one per prototype configuration (:need:`XD-ADR-0102`).
