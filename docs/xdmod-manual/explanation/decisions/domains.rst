.. _adr-domains:

Domain models and CAD
=====================

How the EE and ME repos refine the system model, which needs their models emit, and how KiCad
and FreeCAD files refer to them (Phase 5, task 5.14). Decisions that rest on the FreeCAD spike are
*proposed* until that spike is merged.

.. xd-adr:: Domain repos refine the system model by specialization
   :id: XD-ADR-0130
   :date: 2026-11-17
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0030

   **The EE and ME repos each have their own SysML model in** ``model/`` **and refine the system
   model by specialization.** SW keeps its architecture in rst in iteration 1 (:need:`XD-ADR-0069`);
   a SW sub-model would follow the same pattern in iteration 2. There are three levels of detail:

   - **System model** (the systems engineering repo): what crosses a domain boundary. Blocks down to
     the product level (one part def per board, assembly and SW component), their ports, and the
     interface defs (``SYS-IF``) at signal level: signal names, direction, kind, values from the
     requirements. No connector types, pin numbers or part numbers.
   - **Domain model** (``<domain repo>/model/``): how the domain realizes a block. EE: board defs,
     connector port defs with connector type and pin map (pin number and net name per signal), cable
     defs, external parts, board variants. ME: assembly and sub-assembly defs, mechanical port defs
     with geometry, assembly variants. In iteration 1 there are no circuit block diagrams inside a
     board.
   - **Implementation** (KiCad projects, WireViz files, FreeCAD documents): they name the domain
     model elements they implement.

   A domain def specializes the system def it realizes (``part def JointControllerBoard :>
   JointController``) and redefines every inherited port with a port whose def specializes the
   interface def (``port def ServoHeader :> ServoIf``). A domain def may specialize several system
   defs; a name clash between inherited ports is solved by one port that redefines all of them
   (``port :>> A::p, B::p : X;``). Redefined signal ports repeat their direction (``out port :>>
   pwm``). Inside a def that specializes a system def, outer elements are named by qualified name,
   because inherited members hide outer names.

   A domain model imports only the system model and the xdmod libraries; SW reads the EE model
   (:need:`XD-ADR-0131`). It reads the upstream model twice, both from the same west pin: as a
   library set for the Pilot, and as the upstream's committed ``generated/model.json`` for the
   checks that run without Java. The repo's own model files are read as one set, so their order does
   not matter. Each domain model costs one more Pilot run; the owner accepted that. Based on the
   model spike (``claude/notes/model-spike.md``).

.. xd-adr:: curatrix checks conformance and derives the links
   :id: XD-ADR-0132
   :date: 2026-11-17
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0130

   **Conformance is a curatrix check, not a Pilot result.** The Pilot finds neither a missing
   redefinition nor a redefinition with the wrong port def. So curatrix checks, on the committed
   model JSON of the domain repo and its upstream: every port that a domain def inherits from a
   system def is redefined somewhere in the chain between the two, and the most specific
   redefinition's def specializes the inherited port's def. The same rule holds inside port defs at
   signal level. A variant def of a board does not repeat the redefinitions of its parent. An
   unsolved name clash of inherited ports is an error.

   **Links come from specialization.** ``curatrix gen model`` turns a ``:>`` across the repo boundary
   into a trace link on the domain need, chosen by the pair of kinds: ``EE-PCBA`` / ``ME-ASM`` /
   ``EE-HAR`` to ``SYS-EL`` is ``realizes``; ``EE-PORT`` / ``ME-PORT`` to ``SYS-IF`` is ``conforms``.
   Any other pair is a finding, never skipped. A def without an ID of its own that specializes a
   system element is allowed only below the port level (for example a signal def inside a port def);
   anywhere else it is a warning.

.. xd-adr:: The domain model owns the IDs of boards, assemblies, ports and harnesses
   :id: XD-ADR-0128
   :date: 2026-11-17
   :decision_status: accepted
   :status: valid
   :revises: XD-ADR-0023

   **The domain model emits the** ``EE-PCBA``, ``EE-PORT``, ``EE-HAR``, ``ME-ASM`` **and**
   ``ME-PORT`` **needs.** The ID is the short name of the def in the domain model. KiCad, WireViz and
   FreeCAD files carry these IDs only as references: the ``TraceID`` of a KiCad project or of the top
   FreeCAD document of an assembly, the ``Port`` field of a KiCad connector, the ``Port`` property of
   a FreeCAD LCS, the port names at both ends of a harness. The ``Realizes`` and ``Conforms`` fields on
   KiCad projects and FreeCAD documents go away: these links are derived from specialization
   (:need:`XD-ADR-0132`). ``EE-CMP`` and ``ME-PART`` stay owned by the CAD files, as before
   (:need:`XD-ADR-0023`).

   **One CAD file per domain def.** Each board def has exactly one KiCad project
   ``pcba/<name>/<name>.kicad_pro``, each cable def exactly one harness folder ``harness/<name>/``, each
   assembly or sub-assembly def exactly one FreeCAD document; and each of these files names exactly
   one def. The folder name comes from the element name (``JointController`` →
   ``joint-controller``). The project's entry point is its ``.kicad_pro``; the root schematic has the
   same name. Instances are usages of the def, in any number; the trace stays on the def
   (:need:`XD-ADR-0117`). A single ME part is 1:1 with a model element only when the model treats it
   as a block. The CK-D4 readers change with this decision.

.. xd-adr:: Need kinds EE-PORT, ME-PORT and EE-HAR
   :id: XD-ADR-0133
   :date: 2026-11-17
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0030

   **Three new need kinds.**

   - ``EE-PORT``: a connector port of a board, or a port of an external part, in the EE model. It
     ``conforms`` to the ``SYS-IF`` it specializes and is ``part_of`` its board (``EE-PCBA``). A port
     of an external part has no ``part_of``; its qualified name names the part. A KiCad connector
     names it in its ``Port`` field; a connector without a port says so with ``Port = -``.
   - ``ME-PORT``: a mechanical interface of an assembly in the ME model, with its geometry. It
     ``conforms`` to the ``SYS-IF`` it specializes and is ``part_of`` its assembly (``ME-ASM``). In
     FreeCAD it is an LCS with a ``Port`` property.
   - ``EE-HAR``: a wiring harness, 1:1 with a cable def in the EE model. It ``connects`` the two or more
     ``EE-PORT`` s its ends mate with. The harness is built to fit those ports, so it is the more
     concrete side and holds the link (:need:`XD-ADR-0004`). Like every design element it must
     ``realizes`` a ``SYS-EL`` or ``satisfies`` an ``EE-REQ`` (no orphans, :need:`XD-RULE-0010`); it may
     also ``conforms`` to a ``SYS-IF``. Ports are not in the orphan rule: a port of an external part
     may conform to nothing.

.. xd-adr:: SW reads the board pin maps from EE
   :id: XD-ADR-0131
   :date: 2026-11-17
   :decision_status: accepted
   :status: valid
   :revises: XD-ADR-0030

   **First exception to the peer rule: SW is downstream of EE for the board model.** The MCU pin map
   of a board is an EE design decision, so it lives in the EE model, not in a ``SYS-IF``. SW reads it
   from there: SW needs (``SW-ARCH``, ``SW-DD``) may ``conforms`` to an ``EE-PCBA`` or an
   ``EE-PORT``, the SW repo lists the EE documents and the EE model as upstream, and the sw role gets
   the EE repo. EE never links to SW. The direction stays acyclic: syseng → EE → SW. CK-F2
   (devicetree against the model) compares with the EE board model. In iteration 1 the devicetree is
   written by hand; a generator from KiCad is iteration 2. Each Zephyr board variant maps to one
   board variant by name, and SW adds no board variants of its own in iteration 1.

.. xd-adr:: ME writes board geometry into KiCad in a co-design change
   :id: XD-ADR-0134
   :date: 2026-11-17
   :decision_status: proposed
   :status: valid
   :revises: XD-ADR-0030
   :refines: XD-ADR-0137

   **Second exception to the peer rule: ME may write into EE's KiCad project, but only inside a
   co-design change.** The space a board may take is a ``SYS-IF`` budget in the system model: a port
   def with a box (``width``, ``depth``, ``heightAbove``, ``heightBelow``), a hole list
   (``hole<n>X``, ``hole<n>Y``, ``holeDiameter``) and connector positions (``<ref>X``, ``<ref>Y``,
   pin 1), in the board frame (origin at the lower-left corner of the outline seen from the top, x
   right, y up, z = 0 on the top face). The values are defaults, so a domain def can restate them.
   The board def conforms to it by ``dependency from <board> to <budget>`` (a budget is no connector
   port); the ME port def of the board seat specializes it and restates the values FreeCAD needs.
   **Open for the owner:** the restated budget values (the attributes that redefine an attribute of
   the ``SYS-IF`` budget, not the placement and not attributes ME adds itself) are copied from the
   system model, not chosen in ME, so this decision proposes that they do not count toward the "at
   most ten driving parameters" of :need:`XD-ADR-0137`. That is an interpretation of XD-ADR-0137,
   although the copies drive the sketch ``BoardOutline``; the owner decides it when accepting this
   decision. A geometry change is one change with one branch name over the systems engineering, ME
   and EE repos (:need:`XD-ADR-0045`).

   **The push is one tool step on copies:** the sketch ``BoardOutline`` of the skeleton (driven by
   the parameters) goes into a copy of the ``.kicad_pcb`` by KiCad StepUp (``export_pcb``), run from
   a script in the FreeCAD GUI binary offscreen, with ``HOME`` set to a folder under ``.xdmod/`` for
   that process only (StepUp writes ``~/ksu-config.ini``); then ``kicad-cli pcb upgrade --force``
   re-saves the copy in the KiCad 10 format, DRC runs on it, and only then the file goes back into
   the EE repo. StepUp is pinned by commit under ``.xdmod/stepup/`` (pin and licence gap:
   :ref:`howto-co-design-change`). It pushes the outline and the holes
   (as ``Edge.Cuts`` circles, non-plated cut-outs); the board frame lands on the grid origin, or on
   the lower-left corner of the old outline. The EE side reviews and merges its part. ME never takes
   EE geometry outside such a change, and ME needs never link to EE needs.

   **Scope in iteration 1** (co-design spike, ``claude/notes/codesign-spike.md``): keep-out zones
   are not pushed (the box covers the space; StepUp could push them, iteration 2). Connector
   positions are budget values, but never pushed: EE places connectors, and a planned check (task
   5.25) compares them. EE does not push back through StepUp: the board model reaches FreeCAD by the
   scripted STEP path (``kicad-cli pcb export step``, headless import), because StepUp's board load
   stalls offscreen; a change EE needs (a bigger box, a moved hole) is a budget change in the same
   co-design branch. A harness length is a ``SYS-IF`` value its cable def conforms to like a board
   (``EE-HAR`` to ``SYS-IF``); its route in the ME assembly is iteration 2.

.. xd-adr:: External parts and prototype projects
   :id: XD-ADR-0135
   :date: 2026-11-17
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0067

   **Bought boards and parts are external parts:** a def in the EE model with their headers or
   terminals as ports (``EE-PORT``), but no KiCad project. They are outside the 1:1 project rule
   (:need:`XD-ADR-0128`). Examples: an MCU evaluation board, a PWM or ADC breakout, a servo, a
   potentiometer. Harness ends and prototype wiring name their ports, and CK-F1 checks against them.

   **A prototype project** ``proto/<name>/<name>.kicad_pro`` **is 1:1 with a block of the prototype
   configuration** in the system model (for example ``JointProtoRig``), like a board project with its
   board def. Its schematic shows the wiring between external parts (:need:`XD-ADR-0067`).

.. xd-adr:: Variants: the domain variant names what it serves
   :id: XD-ADR-0136
   :date: 2026-11-17
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0092, XD-ADR-0093

   **Board and assembly variants are named in the domain model.** Each domain variant names the
   system configurations (``SYS-CFG``) and usages it serves (``Configs``). The table
   "configuration → variant per usage" is computed, like a backlink; nobody writes it. A check in the
   domain repo, against the published needs of the systems engineering repo: exactly one variant per
   usage and configuration, and the variant exists in the domain model and in KiCad or FreeCAD. At
   most two variants per board and per assembly in iteration 1. Unused variants are not reported in
   iteration 1.

   **EE:** board variants are KiCad assembly variants. A solder jumper or 0 Ω link is fitted (=
   bridged) or DNP per variant. The position of a pin-header shunt is set by hand after assembly, so
   it is not an assembly matter: the EE model holds it per variant (with its meaning, for example an
   I²C address), and the KiCad part carries the same value in a per-variant field ``Setting`` (KiCad
   10 can override any field per variant, KiCad spike §3.3), so the BOM shows it. A check compares
   the variant names and settings in the EE model, the ``.kicad_pro``, the ``.kicad_sch`` and the
   ``.kicad_pcb``. Each Zephyr board variant maps to one board variant by name (checked on the
   canary). ME variants: :need:`XD-ADR-0137`.

.. xd-adr:: Who owns instance counts
   :id: XD-ADR-0138
   :date: 2026-11-17
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0117

   **The systems engineering repo owns the usages it sees** (the blocks of the product architecture,
   for example six joints). A domain model refers to them and does not repeat them. **The domain model
   owns its internal usages** (sub-assemblies and parts that the system model never sees). The check
   that counts FreeCAD links per part or sub-assembly against the usages uses both, filtered by
   ``Configs`` per variant. Instances may differ only through variants (:need:`XD-ADR-0136`); in
   iteration 1 they get no IDs of their own.

.. xd-adr:: FreeCAD assemblies: a skeleton document, values from the model
   :id: XD-ADR-0137
   :date: 2026-11-17
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0130

   **Each top-level assembly is a folder** ``assemblies/<name>/`` with its top document
   ``<name>.FCStd``, a skeleton document ``skeleton.FCStd``, and its own parts; shared parts stay in
   ``parts/``. The skeleton holds the parameter spreadsheet ``Params`` and the master sketch. The
   master sketch cannot live in the top document: parts that refer to it would form a document cycle,
   and FreeCAD then recomputes in an undefined order (FreeCAD spike §1). Parts refer only to the
   skeleton, never to the top document; the top document links the skeleton and the parts. At most ten
   driving parameters in iteration 1.

   **The model drives the CAD.** ``curatrix gen freecad-params`` writes the model values into
   ``Params`` (aliases ``<port>_<attribute>``): it opens the top document first, writes values only
   (it never rebuilds objects, so object IDs do not churn), recomputes skeleton, parts, sub-assemblies
   and top in this order, and saves only the documents whose values changed. CK-F3 checks that they
   agree.

   **Interfaces** are LCS with a ``Port`` property (the ``ME-PORT`` ID). **Variants** are rows of a
   configuration table in ``Params`` plus ``Configs`` on the links; part presence comes from
   ``Configs``, never from a suppressed state. Checks, value writes and the exploded view run in
   ``FreeCADCmd``. The exploded view uses the fallback of the FreeCAD spike (§5): the moves are data
   (a small table per assembly, or read from the ``Move`` objects in ``Document.xml``), and a script
   builds the exploded compound and its TechDraw view; the Assembly workbench's exploded view in the
   GUI binary hung in 6 of 8 runs, so it is only a design aid. Only full TechDraw pages and StepUp
   need the GUI binary with ``QT_QPA_PLATFORM=offscreen``; task 5.26 first shows that the page export
   runs reliably, or falls back to view SVGs. Both run through curatrix with the workspace-local
   configuration. Based on the FreeCAD spike (``claude/notes/freecad-spike.md``).

.. xd-adr:: FreeCAD assemblies: skeleton file name, parameter aliases, open order
   :id: XD-ADR-0146
   :date: 2026-11-17
   :decision_status: proposed
   :status: valid
   :refines: XD-ADR-0137

   Proposed by the agent of tasks 5.23 and 5.24, for the owner to accept or change; it states what
   the code of these tasks does where it differs from :need:`XD-ADR-0137`.

   - **The skeleton is** ``assemblies/<name>/<name>-skeleton.FCStd``, not ``skeleton.FCStd``.
     FreeCAD names a document after its file, and a cross-document expression names that document
     (``canary_assembly_skeleton#MasterSketch.Constraints.partLength``). With one file name for every
     skeleton, two assemblies opened together clash, and a later rename touches every part
     expression.
   - **The parameter aliases are** ``<usage>_<attribute>``: the usage is a port or a part usage of the
     top-level assembly def (``mount_x``, ``canaryPart_length``), so a main dimension of a part can be
     a parameter too; :need:`XD-ADR-0137` said ``<port>_<attribute>``.
   - **The writer opens the skeleton first, then the top document.** The top document links only the
     part ``Skeleton`` of the skeleton, so through the top FreeCAD loads the skeleton only partially,
     without ``Params`` (found in task 5.24). The skeleton depends on no other document; the parts
     then load fully through the top. The writer stops when any document is still partial.
   - Parts that take values from a skeleton belong to that assembly and sit in its folder
     (``assemblies/<name>/parts/``); a shared part in ``parts/`` takes no value from a skeleton.

.. xd-adr:: A board library repo for ME
   :id: XD-ADR-0139
   :date: 2026-11-17
   :decision_status: proposed
   :status: valid
   :refines: XD-ADR-0128, XD-ADR-0141

   **FreeCAD models of the boards live in their own repo,** ``robarm-freecad-pcba`` in the robot arm
   (a top-level west project like the other design repos, in the west groups ``ee`` and ``me``, so
   the ee and me roles both get it). EE writes into it,
   ME reads from it, so neither depends on the other's repo. Only tagged board versions go in
   (:need:`XD-ADR-0140`): ``kicad-cli pcb export step`` with the variant and the version, then a
   headless FreeCAD import that adds the board's ``EE-PCBA`` ID and version as properties. The EE agent
   opens the PR that adds a board version. At most 5 MB per file to start (board body, connectors and
   tall parts, no tracks). An ME assembly links one fixed board version; a newer version gives a note
   or an issue on the ME repo, and moving to it is an ME change. Creating the repo is an admin action
   that needs the owner's approval (:need:`XD-ADR-0112`). Proposed until task 5.29 has shown the
   headless STEP import (the FreeCAD spike did not test it).

   Task 5.29 showed the headless STEP import (``FreeCADCmd``, ``Part.Shape.read``, canary board:
   about 0.04 MB per variant without component models) and settled the details: one file per tagged
   version and variant at ``boards/<board>/<board>-vX.Y.Z[-<variant>].FCStd``; an ``App::Part``
   ``Board`` with ``TraceID`` (the ``EE-PCBA``), ``Version``, ``Variant``, ``Board`` and ``Commit``;
   ``curatrix cam <ee repo> <board> --library`` refuses anything but an exact release tag
   ``<board>/vX.Y.Z`` (no suffix such as ``-rc1``) on main with a clean project folder, writes only
   into a checkout with a ``board_library`` section on a branch, and never overwrites a file; CK-F20
   (an error) reports a changed or deleted board file against the PR base. The repo is top level
   (not under ``libs/``), because it is a design repo with its own checks: worktree sets and the CI
   sibling resolution handle only top-level repos. Checks: :need:`XD-RULE-0064` (CK-F20) and :need:`XD-RULE-0065` (CK-F21).
