.. _adr-traces:

Traces and IDs
==============

The trace rule, link types, need kinds and the ID scheme.

.. xd-adr:: Trace rule: the concrete side holds the link
   :id: XD-ADR-0004
   :legacy_id: D5
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **Trace rule:** trace annotations go right-to-left in the V-model and from concrete to abstract. The more concrete artifact holds the link; backlinks are only ever computed. Refined by :need:`XD-ADR-0030`.

.. xd-adr:: A new ID prefix scheme
   :id: XD-ADR-0013
   :legacy_id: D17
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   We design a **new ID prefix scheme**. The SEG IDs are not reused.

.. xd-adr:: Trace IDs live inside the CAD files
   :id: XD-ADR-0023
   :legacy_id: D29
   :date: 2026-11-14
   :decision_status: revised
   :status: valid

   Trace IDs for CAD elements live **inside the CAD files** (KiCad symbol/sheet fields, FreeCAD object properties). Doc extraction reads them. Changed by :need:`XD-ADR-0128`: the IDs of boards, assemblies, ports and harnesses are owned by the domain model, and CAD files carry them only as references.

.. xd-adr:: Link-type table and interface elements
   :id: XD-ADR-0030
   :legacy_id: D36
   :date: 2026-11-14
   :decision_status: revised
   :status: valid
   :refines: XD-ADR-0004

   **Link-type table:** :need:`XD-ADR-0004` stays the default. A table of link types names the owner side of each. Peer interfaces (e.g. EE↔SW pin map, EE↔ME connector positions) are **interface elements in syseng**, and both domains link to them. Allocation is stored on the concrete side. Changed by :need:`XD-ADR-0131` (SW reads the board pin maps from EE) and :need:`XD-ADR-0134` (ME writes board geometry into KiCad in a co-design change).

.. xd-adr:: Small corrections from research
   :id: XD-ADR-0057
   :legacy_id: D64
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0030, XD-ADR-0032, XD-ADR-0036, XD-ADR-0040, XD-ADR-0047

   **Small corrections from research:** (a) a drawio file "matches the model" means its content (labels, parents, edge ends, kinds, links), not its geometry (:need:`XD-ADR-0032`); (b) stubs: ``concern`` for stakeholder needs, ``requirement`` for system requirements, so SYSMOD's ``frame`` link is kept (:need:`XD-ADR-0036`); (c) every doc build runs strict (``-W --keep-going``) with zdocs' CI pins (:need:`XD-ADR-0040`); (d) OCI tags map ``baseline/vX.Y.Z`` → ``X.Y.Z`` (:need:`XD-ADR-0047`); (e) a removed requirement is first marked ``retired``, and IDs are never reused; (f) devicetree trace IDs go in our own binding, never on upstream nodes; (g) CI checkouts use ``fetch-depth: 0`` and annotated tags; (h) link types are declared **per need type**, never globally (:need:`XD-ADR-0030`).

.. xd-adr:: Prototype wiring is EE content
   :id: XD-ADR-0067
   :legacy_id: D74
   :date: 2026-11-14
   :decision_status: revised
   :status: valid

   **Prototype wiring is EE content** in robarm-ee: a KiCad schematic of each prototype setup, whose elements are ``EE-CMP`` with ``variant: prototype``. They realize the ``SYS-PROTO`` / ``SYS-EL`` elements. Field changed by :need:`XD-ADR-0093` (``configs``).

.. xd-adr:: A grace period for retired needs
   :id: XD-ADR-0068
   :legacy_id: D75
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0057

   **Retired needs get a grace period until the next baseline.** On ``main`` and in PRs, a link to a ``retired`` need is a reported warning that doesn't fail the build. The baseline build fails while any such link remains. Refines :need:`XD-ADR-0057` (e).

.. xd-adr:: Code units implement design elements
   :id: XD-ADR-0070
   :legacy_id: D77
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **Code links:** a code unit (``SW-IMPL``) must ``implements`` a SW design element. It **may also ``satisfies`` a ``SW-REQ`` directly**, as in the safety repo.

.. xd-adr:: ID format DOMAIN-KIND-NNNN
   :id: XD-ADR-0071
   :legacy_id: D78
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **ID format** ``<DOMAIN>-<KIND>-<NNNN>`` with a 4-digit number. Domains are ``SYS``, ``SW``, ``EE``, ``ME``, ``INT``. Examples: ``SYS-REQ-0012``, ``SW-TC-0103``, ``EE-CMP-0007``. Test results: ``TR-<test case ID>-<run hash>``.

.. xd-adr:: No project code in the sources
   :id: XD-ADR-0072
   :legacy_id: D79
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **No project code in the sources.** A project code with the separator ``:`` (e.g. ``RA:SYS-REQ-0012``) is added only where IDs leave the workspace: bundles, published ``needs.json``, shared affirmatrix cases.

.. xd-adr:: SW test case IDs come from the ledger
   :id: XD-ADR-0073
   :legacy_id: D80
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **SW test case IDs** come from the ledger and are written into the ZTEST comment by a tool, like safety's ``@testid``.

.. xd-adr:: Tests live by what they verify
   :id: XD-ADR-0104
   :legacy_id: D115
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **Tests live by what they verify.** A test that verifies a ``SYS-REQ`` or ``SYS-IF`` lives in robarm-integration, even if it touches one domain only. Tests of domain requirements stay in their domain repo.

.. xd-adr:: Decisions become sphinx-needs
   :id: XD-ADR-0109
   :legacy_id: D120
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0071

   **Decisions become sphinx-needs.** Framework decisions are ``XD-ADR-nnnn`` in the xdmod manual. Robot-arm decisions are ``PRJ-DEC-nnnn`` in the ``robarm`` overview doc (robarm-manifest). The old D-number is kept as ``legacy_id``. New ID domains ``XD`` and ``PRJ`` (extends :need:`XD-ADR-0071`). **In rst, every mention of a decision (and of a rule or check) is a real ``:need:`` reference.**

.. xd-adr:: Method rules are needs
   :id: XD-ADR-0110
   :legacy_id: D121
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0109

   **Method rules are needs** ``XD-RULE-nnnn`` (each ``decided_by`` an ``XD-ADR``). Each curatrix check is a generated ``XD-CHECK`` need that ``enforces`` a rule.

.. xd-adr:: Retiring generated needs
   :id: XD-ADR-0119
   :legacy_id: D130
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0057

   **Retiring generated needs:** status comes from the source (SysML metadata, KiCad ``Status`` field, FreeCAD ``Status`` property, Doxygen tag). Deleting without retiring first leaves a tombstone in ``generated/retired-needs.json`` until the next baseline. ``draft`` needs take part in structure checks but don't count as coverage.

.. xd-adr:: ID collisions show up as git conflicts
   :id: XD-ADR-0122
   :legacy_id: D133
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **ID collisions:** rulesets require PRs to be up to date with ``main`` before merge, and the ledger lists every issued number per kind, so that concurrent issuing conflicts in git.
