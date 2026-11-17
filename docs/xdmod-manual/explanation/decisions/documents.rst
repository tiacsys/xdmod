.. _adr-documents:

Documents
=========

The linked document set, zdocs, and how documents get their content.

.. xd-adr:: The framework has its own Sphinx documentation
   :id: XD-ADR-0010
   :legacy_id: D13
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   The framework itself gets its **own Sphinx documentation**, separate from the example's design docs.

.. xd-adr:: All content is in English
   :id: XD-ADR-0015
   :legacy_id: D20
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   All content is in **English**.

.. xd-adr:: A set of linked Sphinx documents
   :id: XD-ADR-0016
   :legacy_id: D21
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   The result is a **set of linked Sphinx documents** that describes the project in full: system architecture; SW requirements, SW architecture and design, SW test specification; ME and EE requirements; ME assembly design; one design doc per PCBA.

.. xd-adr:: Documents extract content from the models
   :id: XD-ADR-0017
   :legacy_id: D22
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   Documents **extract content from the design models** where possible (SysML, FreeCAD, KiCad), the way API docs come from Doxygen comments.

.. xd-adr:: zdocs links the documents
   :id: XD-ADR-0020
   :legacy_id: D25
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **zdocs** (https://github.com/tiacsys/zdocs) links the documents together.

.. xd-adr:: One zdocs registry per repo, the full set in the manifest repo
   :id: XD-ADR-0021
   :legacy_id: D26
   :date: 2026-11-14
   :decision_status: revised
   :status: valid

   Each repo has **its own zdocs registry**. The manifest repo has a registry that builds the **full linked set**. Revised by :need:`XD-ADR-0029`: upstream docs are built locally, not used as remote documents.

.. xd-adr:: More documents: needs, test specs, prototype setups
   :id: XD-ADR-0022
   :legacy_id: D27
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   Added documents: stakeholder needs and system requirements spec; system and integration test spec; EE and ME test specs; one doc per prototype setup.

.. xd-adr:: No document control in iteration 1
   :id: XD-ADR-0027
   :legacy_id: D33
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **No document control** (``doc_control``) in iteration 1. Git history and PR reviews are enough for now.

.. xd-adr:: Missing zdocs features become Sphinx extensions in xdmod
   :id: XD-ADR-0028
   :legacy_id: D34
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   Features that zdocs lacks are built as **separate Sphinx extensions in the framework repo**. Useful ones may move into zdocs later.

.. xd-adr:: Upstream documents are built locally
   :id: XD-ADR-0029
   :legacy_id: D35
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid
   :revises: XD-ADR-0021

   **Cross-repo traces:** each repo's zdocs registry also **builds its upstream documents locally** from the west checkout that the manifest pins. This is how a downstream repo checks its links into upstream needs. (zdocs imports needs only from locally built documents.)

.. xd-adr:: Docs hosting on GitHub Pages with versions
   :id: XD-ADR-0048
   :legacy_id: D55
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **Docs hosting:** GitHub Pages on the manifest repo hosts the full linked set, with ``main`` as "latest" plus one folder per baseline. PR docs are CI artifacts. This adds **multi-version hosting**, which zdocs lacks today. The model to follow is the tiacsys/bridle docs.

.. xd-adr:: zdocs gaps are fixed upstream
   :id: XD-ADR-0055
   :legacy_id: D62
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0028

   **X7 zdocs gaps** (version_project ignored for Sphinx docs; every indirect upstream doc must be listed by hand; no import-only mode) are fixed through **issues and PRs on tiacsys/zdocs**. Until those merge, the framework uses workarounds. Refines :need:`XD-ADR-0028` for these three gaps.

.. xd-adr:: Test reports are separate documents
   :id: XD-ADR-0099
   :legacy_id: D109
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0016

   **Test reports are separate documents**: one spec doc and one report doc per domain and for integration.

.. xd-adr:: The XDMOD manual is part of the full set
   :id: XD-ADR-0101
   :legacy_id: D111
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   The **XDMOD manual is part of the robarm full set**, built from the pinned xdmod. robarm docs link to method pages; xdmod never links to robarm.

.. xd-adr:: One EE document per PCBA and per prototype configuration
   :id: XD-ADR-0102
   :legacy_id: D112
   :date: 2026-11-14
   :decision_status: revised
   :status: valid
   :refines: XD-ADR-0016, XD-ADR-0022

   **One EE design doc per PCBA** and **one per prototype configuration**. **WireViz** is evaluated for wiring harnesses (prototype jumper wiring, cables between boards). Changed by :need:`XD-ADR-0127` (WireViz adopted for cables between parts; prototype wiring stays KiCad).

.. xd-adr:: Agent-readable docs with sphinx-llm
   :id: XD-ADR-0111
   :legacy_id: D122
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **Agent-readable docs:** the **sphinx-llm** extension is tried for llms.txt / Markdown output of the doc sets.

.. xd-adr:: WireViz for harnesses
   :id: XD-ADR-0127
   :date: 2026-11-17
   :decision_status: accepted
   :status: valid
   :revises: XD-ADR-0102

   **WireViz is adopted** for cables between boards and external parts. It is a pinned pip package
   (xdmod ``requirements.txt``), plain Python with Graphviz, so CI and Pages can draw the diagrams
   too. Each harness is one folder ``harness/<name>/`` with one WireViz YAML ``<name>.yml`` as entry
   point, 1:1 with a cable def in the EE model (``EE-HAR``, :need:`XD-ADR-0128`). The connectors at
   both ends name the ``EE-PORT`` they mate with, also on external parts; CK-F1 checks pin to pin
   against both ends. ``curatrix cam`` makes the diagram, the harness BOM (with Manufacturer and MPN)
   and the version from tags ``<name>/vX.Y.Z``. One harness in iteration 1. The harness length and
   route are a co-design value between EE and ME (task 5.28). Prototype jumper wiring stays a KiCad
   schematic per prototype setup (:need:`XD-ADR-0067`).

.. xd-adr:: One document per board, harness and assembly
   :id: XD-ADR-0129
   :date: 2026-11-17
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0102
   :revises: XD-ADR-0124

   **Each board, harness and top-level assembly gets its own document from the start:**
   ``pcba-<name>`` (and ``proto-<name>`` per prototype project), ``harness-<name>`` and ``asm-<name>``
   (with one chapter per sub-assembly). ``ee-design`` and ``me-design`` keep the requirements and the
   overview. ``curatrix new pcba`` / ``new asm`` create the document and its registry entry. One
   directive set per document type, so all documents of one type look the same; a section without
   data prints one fixed sentence.

   **What CI can show:** everything read in plain Python appears everywhere: stackup and design-rule
   tables, connector pin tables (from the committed ``generated/<project>.connectors.json``), the
   BOM (in the appendix, one column per variant), the variants table, parameters, materials and
   interfaces of assemblies, the harness diagram and pin-to-pin table. What needs KiCad or FreeCAD
   (schematic, renderings, ERC/DRC findings, drawings, exploded view, mass and center of gravity) is
   included only in local builds, from ``build/<repo>/cam/``, with the version it shows; CI and Pages
   show a placeholder. At the baseline stage, missing or stale local output is an error. A board or
   harness appears in the assembly BOM as one line with its version and a link to its document.
