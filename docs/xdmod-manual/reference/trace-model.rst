.. _ref-trace-model:

Trace model
===========

The trace model names every need type, every link type and every shared field. One shared file,
``xdmod/needs/needs_config.toml``, defines them for every document of every repo (:need:`XD-RULE-0007`).
The tables on this page are generated from that file. The reasons behind the model are in
:doc:`../explanation/v-model-and-traces`. Diagrams of the need types and link types are in
:ref:`expl-framework-model`.

Need types
----------

Each need type has a directive name equal to its ID kind in lower case (``.. sys-req::`` for
``SYS-REQ-0012``). A link type is declared only on the need type that holds it (:need:`XD-RULE-0002`).

.. xd-need-types::

Where the need types live
-------------------------

.. list-table::
   :header-rows: 1
   :widths: 25 20 55

   * - Area
     - Kinds
     - Authored or generated
   * - Systems engineering
     - ``SYS-STH``, ``SYS-NEED``, ``SYS-REQ``
     - authored in rst; stakeholder needs and requirements get SysML stubs (:need:`XD-ADR-0036`)
   * -
     - ``SYS-UC``, ``SYS-IF``, ``SYS-EL``, ``SYS-CFG``, ``SYS-FEAT``
     - authored in SysML, generated as needs by the model extractor
   * - Integration
     - ``INT-STC``, ``INT-ITC``
     - authored in rst
   * - Software
     - ``SW-REQ``, ``SW-ARCH``, ``SW-DD``
     - authored in rst (``SW-DD`` also as a Doxygen group)
   * -
     - ``SW-IMPL``, ``SW-TC``
     - generated from Doxygen tags and ZTEST annotations
   * - Electrical
     - ``EE-REQ``, ``EE-TC``
     - authored in rst (test cases also from scripted checks)
   * -
     - ``EE-PCBA``, ``EE-PORT``, ``EE-HAR``
     - authored in the EE domain model, generated as needs; KiCad and WireViz files refer to them
       (:need:`XD-ADR-0128`, :need:`XD-ADR-0133`)
   * -
     - ``EE-CMP``
     - generated from KiCad symbol or sheet fields (:need:`XD-ADR-0023`)
   * - Mechanical
     - ``ME-REQ``, ``ME-TC``
     - authored in rst
   * -
     - ``ME-ASM``, ``ME-PORT``
     - authored in the ME domain model, generated as needs; FreeCAD documents and LCS refer to them
       (:need:`XD-ADR-0128`, :need:`XD-ADR-0133`)
   * -
     - ``ME-PART``
     - generated from FreeCAD object properties
   * - Framework and project
     - ``XD-ADR``, ``XD-RULE``, ``PRJ-DEC``
     - authored in rst (:need:`XD-ADR-0109`, :need:`XD-ADR-0110`)
   * -
     - ``XD-CHECK``
     - generated from curatrix's check catalogue
   * - Results
     - ``TR``
     - generated from test output; for HIL runs from the evidence branch

Prototype wiring is EE content: a KiCad schematic of the prototype, whose elements are
``EE-CMP`` with ``configs`` set to the prototype configuration (:need:`XD-ADR-0067`). Code units must
``implements`` a design element and may also ``satisfies`` a SW requirement directly
(:need:`XD-ADR-0070`).

Levels of detail
----------------

Domain repos refine the system model in their own ``model/`` folder by SysML specialization
(:need:`XD-ADR-0130`). The system model holds what crosses a domain boundary: blocks down to the
product level, their ports, and interface defs at signal level. A domain model holds how the domain
realizes a block: board defs with connector ports and pin maps, cable defs, external parts and board
variants for EE; assembly defs with mechanical ports and assembly variants for ME. KiCad, WireViz and
FreeCAD files implement the domain model and name its elements by ID. curatrix checks that every
inherited port is redefined with a conforming port def, and derives ``realizes`` and ``conforms``
from the specialization (:need:`XD-ADR-0132`). Each board def has one KiCad project, each cable def one
harness, each assembly def one FreeCAD document; external parts have none (:need:`XD-ADR-0135`).

Two exceptions to the peer rule (:need:`XD-RULE-0003`): SW reads the board pin maps from the EE model
(:need:`XD-ADR-0131`), and ME writes board geometry into the KiCad files inside a co-design change
(:need:`XD-ADR-0134`).

Definitions and instances
-------------------------

- **The definition holds the ID** (:need:`XD-ADR-0117`): a SysML ``part def``, a KiCad sheet file, a
  FreeCAD part file. Its usages are listed in an ``instances`` field, not as separate needs.
- A usage gets its own ID ``<ID>.<n>`` (for example ``SYS-EL-0012.1``) only if it has its own
  requirement.
- **Only model elements with trace links become needs** (:need:`XD-ADR-0118`): ``satisfy``,
  ``allocate``, or a link from another repo.

Link types
----------

The owner is the need type that holds the link. "Min" is the number of targets the schema
requires. Some minimums depend on a field and are schema rules instead:

- A domain requirement without an upstream link must have ``derived: true`` and a
  ``rationale``.
- ``raised_by`` is required for stakeholder needs with ``category: need`` or ``objective``.
- Every domain design element needs at least one ``realizes`` or ``satisfies`` (:need:`XD-RULE-0010`).
- Coverage minimums are graph rules (:need:`XD-RULE-0008`, :need:`XD-RULE-0009`), not single-need rules.

.. xd-link-types::

Fields
------

.. xd-need-fields::

Notes on the fields:

- ``status``: ``draft`` needs take part in all structure checks, but don't count as coverage.
  Generated needs take their status from the source (:need:`XD-ADR-0119`): SysML metadata, the KiCad
  field ``Status``, the FreeCAD property ``Status``, or a Doxygen tag.
- ``configs``, ``where``, ``verification_scope``, ``config``: see
  :doc:`../explanation/variants` (:need:`XD-ADR-0093`, :need:`XD-ADR-0094`).
- ``ears``, ``quantity``, ``unit``, ``min``, ``max``, ``nominal``: requirement values
  (:need:`XD-ADR-0076`).

Rules
-----

The trace principles and graph rules:

.. needtable::
   :types: xd-rule
   :tags: trace
   :columns: id;legacy_id as "Rule";title
   :style: table

Where each rule is checked:

.. list-table::
   :header-rows: 1
   :widths: 20 45 35

   * - Rule
     - Checked by
     - Level
   * - :need:`XD-RULE-0008`
     - :need:`XD-CHECK-0006`, full set
     - error in the full set
   * - :need:`XD-RULE-0009`
     - :need:`XD-CHECK-0007`
     - warning in iteration 1, error later (:need:`XD-ADR-0090`)
   * - :need:`XD-RULE-0010`
     - schema rule and :need:`XD-CHECK-0004`
     - error
   * - :need:`XD-RULE-0011`
     - :need:`XD-CHECK-0008`
     - warning on ``main`` and in PRs; error at the baseline (:need:`XD-ADR-0068`)
   * - :need:`XD-RULE-0012`
     - schema rule and :need:`XD-CHECK-0005`
     - error
   * - :need:`XD-RULE-0013`
     - :need:`XD-CHECK-0011`
     - stale results are reported; at the baseline they don't count
   * - the variant rules
     - :need:`XD-CHECK-0009`, see :doc:`variant-rules`
     - error
   * - :need:`XD-RULE-0014`
     - :need:`XD-CHECK-0024` (needs-diff now, affirmatrix later)
     - report in PRs; gate before a baseline

:need:`XD-RULE-0011` is deliberately not a schema rule: a strict build would turn it into an error at
once, and the grace period would be lost.
