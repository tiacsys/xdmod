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

.. xd-rule:: One FreeCAD document per assembly def
   :id: XD-RULE-0055
   :tags: trace, cad
   :status: valid
   :decided_by: XD-ADR-0128, XD-ADR-0137

   Each assembly or sub-assembly def of the ME model (a def that specializes ``XdDomain::Assembly`` directly, with an ``ME-ASM`` short name) has exactly one FreeCAD document, named after the def (``CanaryAssembly`` → ``canary-assembly.FCStd``), with one object whose ``TraceID`` is the def's ID; every such document names one def. A top-level assembly is the folder ``assemblies/<name>/`` with the top document ``<name>.FCStd`` and ``<name>-skeleton.FCStd``; its own parts sit in the folder, shared parts in ``parts/``. No document refers to a top document: parts and sub-assemblies refer only to the skeleton. Links of an assembly come from the model, not from document properties.

.. xd-rule:: FreeCAD links follow the usages
   :id: XD-RULE-0056
   :tags: trace, cad
   :status: valid
   :decided_by: XD-ADR-0138

   In the document of an assembly def, the number of FreeCAD links to a part or sub-assembly (named by the ``TraceID`` of the link target) equals its usages: the usages the ME model owns (internal parts and sub-assemblies, with multiplicity) plus the usages of the system model inside the system blocks the assembly realizes, counted for the ME def that realizes each used block. A link with ``Configs`` counts only for those configurations. Every other link target has a ``TraceID``; the link to the skeleton is not counted.

.. xd-rule:: The ME model drives the FreeCAD parameters
   :id: XD-RULE-0057
   :tags: trace, cad
   :status: valid
   :decided_by: XD-ADR-0137, XD-ADR-0146

   Every attribute with a value of a part or port usage of a top-level assembly def, or of the usage's def, is a parameter with the alias ``<usage>_<attribute>`` in the spreadsheet ``Params`` of the assembly's ``<name>-skeleton.FCStd``; at most ten per assembly. ``curatrix gen freecad-params`` writes the values; the master sketch and the parts take their dimensions from ``Params``. Each port with a placement (``x``, ``y``, ``z``, ``yaw``, ``pitch``, ``roll`` of ``XdDomain::MechanicalPort``) has one LCS with the property ``Port`` = its ``ME-PORT``, at that placement in the assembly. Values agree within the default tolerance of their kind (lengths 0.001 mm, angles 0.001 deg) or the one of ``@XdDomain::ModelMatchTolerance`` on the attribute, in the attribute's own unit: the agreement of the number in the CAD file with the model, not a manufacturing tolerance. ``Params`` holds no alias the model does not know.

.. xd-rule:: Connectors name their port and follow its pin map
   :id: XD-RULE-0050
   :tags: trace, cad
   :status: valid
   :decided_by: XD-ADR-0128, XD-ADR-0129

   Every connector symbol of a board (reference ``J``, ``P`` or ``CN``, or any symbol with the field) has a ``Port`` field: the ``EE-PORT`` ID of the connector port def it implements, or ``-`` for a connector without a port of the board def. Each port of the board def is named by one connector, and the connector's pins carry the nets of the port def's pin map (pin number and net name; a root-sheet label ``/X`` is the net ``X``). A connector pin that is not in the pin map stays unconnected. The connector tables are committed as ``generated/<project>.connectors.json``, extracted in plain Python and equal to KiCad's XML netlist.

.. xd-rule:: ERC and DRC errors are fixed or accepted by a human
   :id: XD-RULE-0051
   :tags: checks, cad
   :status: valid
   :decided_by: XD-ADR-0126, XD-ADR-0144

   Every KiCad project passes ERC, and every board passes DRC (with the schematic parity test), apart from errors that are accepted: an entry of the project's ``accepted.yaml`` (check, KiCad rule, designators or ``all``, reason) or a KiCad exclusion, each counted only when the newest commit that wrote it carries an ``Accepted-by:`` trailer, has one parent and no agent mark, changes nothing but acceptance entries or exclusions, and every earlier commit of the entry is its ancestor. Anything else is a proposal. This relies on rebase merges, which keep the owner's commit and its trailer; a squash merge turns every acceptance into a proposal, a merge commit never accepts. The unrouted nets of a board are accepted in one entry (``unconnected_items``, ``all``). Warnings are listed, never fail. A KiCad exclusion is lost when its items move; a stale ERC exclusion of a rule that is off is a finding.

.. xd-rule:: ERC and DRC severities equal the template
   :id: XD-RULE-0052
   :tags: checks, cad
   :status: valid
   :decided_by: XD-ADR-0126

   A project's ERC and DRC rule severities and the ERC pin conflict matrix (``.kicad_pro``) equal those of the ``curatrix new pcba`` template; a missing ``erc`` section counts as the template, which holds KiCad 10.0.8's defaults. A custom rule in ``.kicad_dru`` with a severity other than ``error`` is a difference too. A difference needs an accepted ``accepted.yaml`` entry with ``check: CK-F8`` and the rule key (``dru:<name>`` for a custom rule).
.. xd-rule:: The CAM jobset is the shared template, run on a copy
   :id: XD-RULE-0053
   :tags: checks, cad
   :status: valid
   :decided_by: XD-ADR-0142

   A board's jobset is the shared template of ``curatrix new pcba``: no "Execute Command" job, no "Copy Files" job, output folder or job file name outside ``${XD_CAM_OUT}``, no statistics job, no ERC or DRC job, BOM delimiters set. Every job equals its template job; in a project with variants, each variant-dependent template job is replaced by one job per variant (``<template id>-<variant>``) that equals the template job except for the variant and the file name; the variant names in the jobs equal the project's variants, and the jobs without a variant come first, because KiCad keeps the variant of the last job for the following ones. ``curatrix cam`` runs it only on a copy under ``build/``.

.. xd-rule:: The version is shown in the frames and on the silkscreen
   :id: XD-RULE-0054
   :tags: checks, cad
   :status: valid
   :decided_by: XD-ADR-0142, XD-ADR-0140

   Every sheet and the board have a title-block comment line with ``${XD_VERSION}``, and the board has a silkscreen text with it. The ``Rev`` field stays empty, because KiCad cuts long values off there. The committed value of ``XD_VERSION`` is ``unversioned``; ``curatrix cam`` writes the version into its copy.

.. xd-rule:: Every BOM part names its manufacturer part
   :id: XD-RULE-0058
   :tags: checks, cad
   :status: valid
   :decided_by: XD-ADR-0129

   Every part in a board's bill of materials, in the base schematic or in any variant, has the fields ``Manufacturer`` and ``MPN``. A standard part carries a field ``Standard`` with its standard designation instead. A variant that changes a part's value or footprint names its own MPN. A missing field is a warning (owner, EE-8).

.. xd-rule:: The board document's BOM is KiCad's BOM
   :id: XD-RULE-0059
   :tags: checks, cad
   :status: valid
   :decided_by: XD-ADR-0129, XD-ADR-0136

   The board document reads the BOM in plain Python, so CI shows it without KiCad. For every board, without a variant and for each variant, the reader gives the same parts, values, footprints, DNP marks, ``Manufacturer``, ``MPN`` and ``Setting`` as ``kicad-cli sch export bom --variant`` (P5-15).

.. xd-rule:: A board document shows only the output of its own commit
   :id: XD-RULE-0060
   :tags: checks, cad
   :status: valid
   :decided_by: XD-ADR-0129

   Renderings, schematic and ERC/DRC findings of a board come from the local ``curatrix cam`` output of the commit the repo is at; with uncommitted changes in the project folder, from a run on exactly that uncommitted state (a hash of ``git status`` and the changed files, kept in ``cam.json``). Older output is never shown: the section prints a fixed sentence instead, as in CI. Missing output is a local warning, and an error at the baseline once the check ran on the canary.
