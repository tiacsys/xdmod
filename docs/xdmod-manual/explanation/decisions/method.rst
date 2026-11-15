.. _adr-method:

Method and model
================

How the system is modelled: SysML v2, SYSMOD, requirements, views and variants.

.. xd-adr:: SysML v2 textual notation for the system model
   :id: XD-ADR-0001
   :legacy_id: D1
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   The system model is written in **SysML v2 textual notation** (``.sysml``).

.. xd-adr:: Views as drawio files rendered from the model
   :id: XD-ADR-0002
   :legacy_id: D2
   :date: 2026-11-14
   :decision_status: revised
   :status: valid

   Views are rendered as **drawio** files by our own tooling. Content comes from the model; manual **layout tweaks are kept** when views are regenerated. Revised by :need:`XD-ADR-0037`: layout keeping moves to iteration 2.

.. xd-adr:: Requirements in sphinx-needs
   :id: XD-ADR-0005
   :legacy_id: D6
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   Requirements (stakeholder needs, system requirements) are written in **sphinx-needs**. SysML elements reference them by ID (see :need:`XD-ADR-0036`).

.. xd-adr:: SYSMOD is the main method reference
   :id: XD-ADR-0007
   :legacy_id: D9
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   The main SYSMOD reference is https://mbse4u.com/sysmod/.

.. xd-adr:: Prototypes are first-class
   :id: XD-ADR-0008
   :legacy_id: D11
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **Prototypes are first-class.** Prototype setups (e.g. Nucleo + breakouts) are part of the model and are traced like the product design. Refined by :need:`XD-ADR-0031`.

.. xd-adr:: Requirements use EARS
   :id: XD-ADR-0009
   :legacy_id: D12
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   Requirements use **EARS** sentence patterns. Refined by :need:`XD-ADR-0039`.

.. xd-adr:: Prototype and product are variants
   :id: XD-ADR-0031
   :legacy_id: D37
   :date: 2026-11-14
   :decision_status: revised
   :status: valid
   :refines: XD-ADR-0008

   **Prototype and product are variants** of one logical architecture (SysML v2 variants). A prototype test verifies the logical and SW requirements it covers. Product-specific requirements need product evidence. The vertical bar of iteration 1 is the **prototype variant**. Revised by :need:`XD-ADR-0092` to :need:`XD-ADR-0097`.

.. xd-adr:: Read-only requirement stubs in SysML
   :id: XD-ADR-0036
   :legacy_id: D42
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **SysML references to requirements:** a tool generates a package of **read-only requirement stubs** (ID + short name) from ``needs.json``. Nobody edits them by hand; CI checks that they match.

.. xd-adr:: EARS for system and domain requirements
   :id: XD-ADR-0039
   :legacy_id: D45
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0009

   EARS is used for **system and domain requirements**. Stakeholder needs may be plain statements.

.. xd-adr:: SysML toolchain: the OMG Pilot Implementation
   :id: XD-ADR-0058
   :legacy_id: D65
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **SysML toolchain:** OMG Pilot Implementation through ``jshell`` for checking and JSON export; our own Python tools read that JSON; Sysand for libraries; SYSMOD library ``mbse4u/sysmod-sysmlv2``. Syside isn't used, because its CLI and Python library need a paid licence.

.. xd-adr:: SW architecture in rst in iteration 1
   :id: XD-ADR-0069
   :legacy_id: D76
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **SW architecture** is written in rst in iteration 1. A SysML SW sub-model in robarm-sw is tried in iteration 2.

.. xd-adr:: The problem statement is a stakeholder need
   :id: XD-ADR-0074
   :legacy_id: D81
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   The **problem statement** (SYSMOD step 03) is a ``SYS-NEED`` with ``category: problem``. Other needs and objectives link to it with ``addresses``. A ``concern`` stub is generated for it.

.. xd-adr:: System objectives are stakeholder needs
   :id: XD-ADR-0075
   :legacy_id: D82
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **System objectives** (SYSMOD step 06) are ``SYS-NEED`` with ``category: objective``. No separate kind.

.. xd-adr:: Requirement values are need fields
   :id: XD-ADR-0076
   :legacy_id: D83
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **Requirement values** (quantity, unit, min/max/nominal, EARS pattern) are need fields next to the EARS text. They are copied into the ``requirement`` stubs as attributes and checked against the sentence.

.. xd-adr:: The SYSMOD library is a pinned west project
   :id: XD-ADR-0077
   :legacy_id: D84
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0058

   The **SYSMOD v5 library** (``mbse4u/sysmod-sysmlv2``) is a **west project** pinned at a commit. Sysand stays optional.

.. xd-adr:: A short functional architecture
   :id: XD-ADR-0078
   :legacy_id: D85
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   Iteration 1 includes a **short functional architecture** (SYSMOD 10a): functions realize use cases, and logical elements realize functions (``functional2logical``). ``SYS-EL`` gets a ``layer`` field (``functional``, ``logical``, ``product``).

.. xd-adr:: View definitions live in the model
   :id: XD-ADR-0085
   :legacy_id: D94
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **View definitions live in the model:** SysML v2 `view`s (in ``views.sysml``) with ``expose``/``filter`` and an ``@XdView`` annotation naming the view kind.

.. xd-adr:: Trace graphs with needflow
   :id: XD-ADR-0086
   :legacy_id: D95
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **Trace graphs** are drawn with sphinx-needs ``needflow`` (graphviz), not drawio. The user has a separate tool for analysing trace graphs interactively in the works.

.. xd-adr:: Views are committed as editable SVG
   :id: XD-ADR-0087
   :legacy_id: D96
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0032

   **Views are committed as editable SVG** (``<view>.drawio.svg``: the rendered picture with the drawio diagram embedded). They are rendered locally with stable IDs and a hash of the embedded diagram. CI checks the content against the model and the freshness of the picture, without a browser. Refines :need:`XD-ADR-0032`.

.. xd-adr:: drawio desktop 31.7.0
   :id: XD-ADR-0088
   :legacy_id: D97
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **drawio desktop 31.7.0** is installed as a system package (``/usr/bin/drawio``). It is used to open and arrange views, and to test the editor round trip.

.. xd-adr:: Variants follow VAMOS through PLEML
   :id: XD-ADR-0092
   :legacy_id: D102
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid
   :revises: XD-ADR-0031

   **Variants follow VAMOS, in SysML v2 through PLEML** (MBSE4U, MIT, pinned west project). The core is the functional and logical architecture. A feature model, a 150 % product architecture with variation points bound to features, and one product model per configuration complete it. Revises :need:`XD-ADR-0031`.

.. xd-adr:: Variant fields configs, where and config
   :id: XD-ADR-0093
   :legacy_id: D103
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid
   :revises: XD-ADR-0031, XD-ADR-0067

   **Variant fields:** design elements and test cases carry ``configs`` (list of ``SYS-CFG`` IDs, derived where possible), requirements carry ``where`` (feature condition, matching EARS "Where …"), and test results carry ``config``. These replace the ``variant`` field of :need:`XD-ADR-0031`; :need:`XD-ADR-0067`'s prototype wiring uses ``configs``.

.. xd-adr:: Coverage per configuration
   :id: XD-ADR-0094
   :legacy_id: D104
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid
   :revises: XD-ADR-0031

   **Coverage per configuration:** requirements carry ``verification_scope`` (``logical``: evidence from any configuration counts; ``config``: evidence needed per applicable configuration). The coverage report is a requirement × configuration matrix.

.. xd-adr:: Variant rules
   :id: XD-ADR-0095
   :legacy_id: D105
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid
   :revises: XD-ADR-0031

   **Variant rules** :need:`XD-RULE-0021` and :need:`XD-RULE-0022` (feature model), :need:`XD-RULE-0023` to :need:`XD-RULE-0028` (product models), and :need:`XD-RULE-0029` to :need:`XD-RULE-0031` (traces) are the variant part of the trace rules. All are errors and checked by ``curatrix check variants``. Several feature bindings on one element mean AND.

.. xd-adr:: One variant-aware document set
   :id: XD-ADR-0096
   :legacy_id: D106
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid
   :revises: XD-ADR-0031

   **One variant-aware doc set** with configuration badges and a generated page per configuration. No separate doc set per variant.

.. xd-adr:: IDs for configurations and features
   :id: XD-ADR-0097
   :legacy_id: D107
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid
   :revises: XD-ADR-0031

   **IDs:** ``SYS-CFG`` for configurations and ``SYS-FEAT`` for features. ``SYS-PROTO`` is dropped (never issued).

.. xd-adr:: The definition holds the trace ID
   :id: XD-ADR-0117
   :legacy_id: D128
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **The definition holds the trace ID** (SysML ``part def``, KiCad sheet file, FreeCAD part file). Usages are listed in an ``instances`` field, not as separate needs. A usage gets its own ID ``<ID>.<n>`` only if it has its own requirement.

.. xd-adr:: Only linked model elements become needs
   :id: XD-ADR-0118
   :legacy_id: D129
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **Only model elements with trace links become ``SYS-EL`` needs** (satisfy, allocate, or linked from another repo). They get a short-name ID when their first link appears. ``layer`` gains ``context`` (actors, system ports, system of interest).
