.. _rules-trace:

Trace rules
===========

The principles of the trace model and the rules on the trace graph.

.. xd-rule:: The concrete side holds the link
   :id: XD-RULE-0001
   :legacy_id: trace-model 1.1
   :tags: trace
   :status: valid
   :decided_by: XD-ADR-0004, XD-ADR-0030

   A trace link is stored on the more concrete artifact. In the V-model, links point from right to left and from concrete to abstract. Backlinks such as "refined by" or "verified by" are never written; they are only computed.

.. xd-rule:: Link types are declared on the need type that owns them
   :id: XD-RULE-0002
   :legacy_id: trace-model 1.2
   :tags: trace
   :status: valid
   :decided_by: XD-ADR-0030, XD-ADR-0057

   Every link type is declared only on the need type that holds it, in the shared needs configuration. There is no global link table. A link written on the wrong side, a link to an unknown ID, and a link to a wrong target type are build errors.

.. xd-rule:: Peer interfaces live in systems engineering
   :id: XD-RULE-0003
   :legacy_id: trace-model 1.3
   :tags: trace
   :status: valid
   :decided_by: XD-ADR-0030, XD-ADR-0131, XD-ADR-0134

   Interfaces between peer domains (for example EE and ME) are interface needs (``SYS-IF``) in the systems engineering repo. Both domains link to the interface; neither domain links to the other. Two exceptions: SW reads the board pin maps from the EE model and may link to ``EE-PCBA`` and ``EE-PORT`` needs, while EE never links to SW; and ME writes board geometry into EE's KiCad project, but only inside a co-design change, without any trace link from ME to EE.

.. xd-rule:: Allocation is stored on the concrete side
   :id: XD-RULE-0004
   :legacy_id: trace-model 1.4
   :tags: trace
   :status: valid
   :decided_by: XD-ADR-0030, XD-ADR-0092

   When a logical element is allocated to a product element, the product element ``realizes`` the logical element. The same holds from functional to logical elements.

.. xd-rule:: Variants are expressed with configs and where
   :id: XD-RULE-0005
   :legacy_id: trace-model 1.5
   :tags: trace
   :status: valid
   :decided_by: XD-ADR-0092, XD-ADR-0093

   Variants follow VAMOS through PLEML. The core is the functional and logical architecture; variants live in the 150 % product architecture. Design elements and test cases carry ``configs``, requirements carry ``where``, and test results carry ``config``.

.. xd-rule:: Generated needs follow the same rules
   :id: XD-RULE-0006
   :legacy_id: trace-model 1.6
   :tags: trace
   :status: valid
   :decided_by: XD-ADR-0017, XD-ADR-0023, XD-ADR-0100

   Needs generated from SysML, KiCad, FreeCAD, code and test results follow the same rules as authored needs. Their links come from the source files: SysML ``satisfy`` and ``:>`` across the repo boundary, CAD trace fields, Doxygen ``\satisfies`` and ZTEST ``\verifies``.

.. xd-rule:: One shared needs configuration
   :id: XD-RULE-0007
   :legacy_id: trace-model 1.7
   :tags: trace
   :status: valid
   :decided_by: XD-ADR-0030, XD-ADR-0057

   One module in xdmod (``needs/needs_config.toml``) defines all need types, fields and link types. Every document of every repo uses it, and the reference tables are generated from it.

.. xd-rule:: Every system requirement is refined or satisfied
   :id: XD-RULE-0008
   :legacy_id: R1
   :tags: trace
   :status: valid
   :decided_by: XD-ADR-0030

   Every ``SYS-REQ`` is refined by at least one domain requirement or satisfied by at least one ``SYS-EL``. Needs with ``status: draft`` don't count. Checked over the full set, because the links come from other repos.

.. xd-rule:: Every requirement is verified
   :id: XD-RULE-0009
   :legacy_id: R2
   :tags: trace
   :status: valid
   :decided_by: XD-ADR-0090, XD-ADR-0094

   Every requirement (``SYS-REQ`` and the domain requirements) has at least one ``verifies`` link pointing at it, per applicable configuration. It is a warning in iteration 1 and an error at the baseline gate from iteration 2.

.. xd-rule:: No orphan design elements
   :id: XD-RULE-0010
   :legacy_id: R3
   :tags: trace
   :status: valid
   :decided_by: XD-ADR-0030

   Every product-layer ``SYS-EL``, ``SW-ARCH``, ``EE-PCBA``, ``EE-CMP``, ``ME-ASM`` and ``ME-PART`` has a ``realizes`` or a ``satisfies`` link.

.. xd-rule:: Links to retired needs are reported, with a grace period
   :id: XD-RULE-0011
   :legacy_id: R4
   :tags: trace
   :status: valid
   :decided_by: XD-ADR-0057, XD-ADR-0068

   A link to a need with ``status: retired`` is reported. On ``main`` and in pull requests it is a warning that does not fail the build. The baseline build fails while any such link remains.

.. xd-rule:: HIL results carry the firmware hash and the pinned SHAs
   :id: XD-RULE-0012
   :legacy_id: R5
   :tags: trace
   :status: valid
   :decided_by: XD-ADR-0050, XD-ADR-0053

   Every ``TR`` from a hardware-in-the-loop run carries ``firmware_sha256`` and the SHAs of all pinned repos it depends on.

.. xd-rule:: Only valid evidence counts
   :id: XD-RULE-0013
   :legacy_id: R5a
   :tags: trace
   :status: valid
   :decided_by: XD-ADR-0120

   A ``TR`` counts only if its recorded SHAs (and firmware hash) match the current manifest pins on ``main``, or the baseline being built. Otherwise it is shown as stale and does not count for coverage.

.. xd-rule:: Suspect links are reviewed before a baseline
   :id: XD-RULE-0014
   :legacy_id: R7
   :tags: trace
   :status: valid
   :decided_by: XD-ADR-0038, XD-ADR-0052, XD-ADR-0121

   A link is suspect when its target changed after the link was last confirmed. Until affirmatrix is adapted, "last confirmed" means the ``needs.json`` of the last baseline (for pull requests: of ``main``). A change is a change of title, content, status, value fields or links. Suspect links are reported in pull requests and block a baseline.

.. xd-rule:: Domain models conform to the system model
   :id: XD-RULE-0047
   :tags: trace
   :status: valid
   :decided_by: XD-ADR-0130, XD-ADR-0132

   A domain def (board, connector, cable, assembly, mechanical port) specializes the system def it realizes or the interface def it meets. Every port it inherits from a system def is redefined somewhere in the chain by a port whose def specializes the inherited port's def; inside port defs the same holds for the signal ports. A port name inherited more than once is redefined by one port that redefines all of them. The trace link of a specialization comes from the pair of kinds (``realizes`` to a ``SYS-EL``, ``conforms`` to a ``SYS-IF``); a pair without a link type is a finding.

.. xd-rule:: One KiCad project per board def
   :id: XD-RULE-0049
   :tags: trace, cad
   :status: valid
   :decided_by: XD-ADR-0128, XD-ADR-0135

   A KiCad project is the ``.kicad_pro`` in its own folder ``pcba/<name>/`` or ``proto/<name>/``, named like the folder, with the root sheet ``<name>.kicad_sch``; no KiCad project file lies outside these folders. Each board def of the EE model (a def that specializes ``XdDomain::Pcba`` directly; a board variant, which specializes its board def, is not a board def of its own) has exactly one ``pcba/`` project, in the folder named after the def (``JointController`` → ``joint-controller``), whose text variable ``TraceID`` is the def's ``EE-PCBA`` ID; every ``pcba/`` project names exactly one board def. External parts have no project. Links of a board come from the model, not from project variables.

.. xd-rule:: Connectors name their port and follow its pin map
   :id: XD-RULE-0050
   :tags: trace, cad
   :status: valid
   :decided_by: XD-ADR-0128, XD-ADR-0129

   Every connector symbol of a board (reference ``J``, ``P`` or ``CN``, or any symbol with the field) has a ``Port`` field: the ``EE-PORT`` ID of the connector port def it implements, or ``-`` for a connector without a port of the board def. Each port of the board def is named by one connector, and the connector's pins carry the nets of the port def's pin map (pin number and net name; a root-sheet label ``/X`` is the net ``X``). A connector pin that is not in the pin map stays unconnected. The connector tables are committed as ``generated/<project>.connectors.json``, extracted in plain Python and equal to KiCad's XML netlist.
