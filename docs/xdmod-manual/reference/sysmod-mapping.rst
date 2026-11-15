.. _ref-sysmod-mapping:

SYSMOD mapping
==============

How each SYSMOD step maps to a work product, where it is authored, its need type, and the
document it appears in. Background: :doc:`../explanation/sysmod-and-sysml`.

Steps and work products
-----------------------

.. list-table::
   :header-rows: 1
   :widths: 6 22 32 20 20

   * - #
     - SYSMOD step / work product
     - Authored in
     - Need type (ID kind)
     - Document
   * - 01
     - Project (owner, purpose, process)
     - ``.sysml`` (``#project``), short
     - —
     - requirements spec, introduction
   * - 02
     - Brownfield architecture
     - —
     - —
     - skipped for greenfield projects
   * - 03
     - Problem statement
     - rst, one need with ``category: problem``; ``concern`` stub generated (:need:`XD-ADR-0074`)
     - ``SYS-NEED``
     - requirements spec
   * - 04
     - Stakeholders
     - rst, with SYSMOD's fields (categories, risk, effort); ``part`` stubs generated
     - ``SYS-STH``
     - requirements spec
   * - 05
     - Stakeholder needs
     - rst; ``concern`` stubs generated
     - ``SYS-NEED``
     - requirements spec
   * - 06
     - System idea and system objectives
     - idea: ``.sysml`` (``systemIdeaContext``); objectives: rst, needs with
       ``category: objective`` (:need:`XD-ADR-0075`)
     - ``SYS-NEED``
     - requirements spec
   * - 07
     - System context (actors, system ports, interfaces)
     - ``.sysml`` (``specificationContext``)
     - ``SYS-EL`` (``layer: context``), ``SYS-IF``
     - system architecture
   * - 08
     - Use cases (and flows)
     - ``.sysml`` (``use case … : SystemUseCase``)
     - ``SYS-UC``
     - requirements spec
   * - 09
     - System requirements
     - rst, EARS (:need:`XD-ADR-0039`), with value fields (:need:`XD-ADR-0076`); ``requirement`` stubs generated
     - ``SYS-REQ``
     - requirements spec
   * - 10a
     - Functional architecture
     - ``.sysml`` (``functionalContext``) (:need:`XD-ADR-0078`)
     - ``SYS-EL`` (``layer: functional``)
     - system architecture
   * - 10b
     - Logical architecture
     - ``.sysml`` (``logicalContext``), ``allocate`` functional to logical
     - ``SYS-EL`` (``layer: logical``)
     - system architecture
   * - 10c
     - Product architecture (150 %, with variation points) and allocation
     - ``.sysml`` (``productContext``), ``allocate`` logical to product
     - ``SYS-EL`` (``layer: product``, ``configs``)
     - system architecture
   * - 10d
     - Features and configurations (VAMOS/PLEML, :need:`XD-ADR-0092`)
     - ``.sysml``: feature model, one product model per configuration
     - ``SYS-FEAT``, ``SYS-CFG``
     - system architecture; one page per configuration (:need:`XD-ADR-0096`)
   * - 11
     - Verification and validation
     - rst test specs in the integration repo (:need:`XD-ADR-0066`); a SysML verification context later
     - ``INT-STC``, ``INT-ITC``
     - system and integration test spec

Links between the products follow the link table in :doc:`trace-model`, for example:

- ``SYS-REQ`` refines ``SYS-NEED`` (SYSMOD's ``frame``, kept in sphinx-needs).
- ``SYS-UC`` addresses ``SYS-NEED``.
- A product ``SYS-EL`` satisfies ``SYS-REQ`` (SysML ``satisfy`` on the stub) and realizes a
  logical ``SYS-EL`` (from ``allocate``).

Files in the systems engineering repo
-------------------------------------

.. code-block:: text

   model/                  SysML sources (authored)
     project.sysml         01
     context.sysml         06, 07: idea and specification context, actors, ports, interfaces
     usecases.sysml        08
     functional.sysml      10a
     logical.sysml         10b
     product.sysml         10c: product context and allocations
     features.sysml        10d: feature model (PLEML)
     configs.sysml         10d: configurations, one product model each
     views.sysml           view definitions
     generated/            stubs from the needs (committed, checked)
   docs/
     se-req/               requirements spec: 01, 03, 04, 05, 06, 08 (generated), 09
     se-arch/              system architecture: 07, 10 (from the model) and views
   generated/              model.json, model-needs.json (committed, checked)
   views/                  <view>.drawio.svg (committed, checked)

Requirement fields
------------------

.. list-table::
   :header-rows: 1
   :widths: 30 30 40

   * - Field
     - Example
     - Use
   * - ``ears``
     - ``ubiquitous``, ``event``, ``state``, ``optional``, ``unwanted``, ``complex``
     - the EARS pattern, checked against the sentence (:need:`XD-CHECK-0022`)
   * - ``quantity``, ``unit``, ``min``, ``max``, ``nominal``
     - ``latency``, ``ms``, —, ``50``, —
     - values that model attributes and tests can be checked against (:need:`XD-CHECK-0021`)
   * - ``verification_method``
     - ``test``
     - test, analysis, inspection or demonstration
   * - ``category``
     - ``functional``, ``performance``, ``interface``, ``constraint``
     - grouping in the spec
