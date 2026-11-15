.. _adr-scope:

Scope and iterations
====================

What is in iteration 1 and what moved to iteration 2.

.. xd-adr:: CAM data from CAD data is a framework task
   :id: XD-ADR-0018
   :legacy_id: D23
   :date: 2026-11-14
   :decision_status: revised
   :status: valid

   Creating and storing **CAM data from CAD data** (ME and EE) is a task of the framework. Moved to iteration 2 by :need:`XD-ADR-0037`.

.. xd-adr:: All design outputs go into a bundle
   :id: XD-ADR-0019
   :legacy_id: D24
   :date: 2026-11-14
   :decision_status: revised
   :status: valid

   All design outputs, including the pre-built firmware, go into a **bundle**. The user will share a bundling tool later. Terms fixed by :need:`XD-ADR-0034`; moved to iteration 2 by :need:`XD-ADR-0037`.

.. xd-adr:: ME CAM output is 3MF and STL plus print settings
   :id: XD-ADR-0024
   :legacy_id: D30
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   ME CAM output is **3MF (and STL) plus a print-settings profile**. No G-code.

.. xd-adr:: A bundle is one tag of the manifest repo
   :id: XD-ADR-0026
   :legacy_id: D32
   :date: 2026-11-14
   :decision_status: superseded
   :status: valid

   A bundle is one tag of the manifest repo. Superseded by :need:`XD-ADR-0034`.

.. xd-adr:: FreeCAD storage is decided after research
   :id: XD-ADR-0035
   :legacy_id: D41
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **FreeCAD storage and diff** (``.FCStd`` is a zip file) is decided in Phase 3, after hands-on research.

.. xd-adr:: Scope moved to iteration 2
   :id: XD-ADR-0037
   :legacy_id: D43
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid
   :revises: XD-ADR-0002, XD-ADR-0018, XD-ADR-0019

   **Moved to iteration 2:** CAM pipeline and bundle, the PDF document set, layout keeping in drawio, product PCB layout. Iteration 1 builds HTML docs only.

.. xd-adr:: FreeCAD review report as a Pages preview
   :id: XD-ADR-0098
   :legacy_id: D108
   :date: 2026-11-14
   :decision_status: revised
   :status: valid

   **FreeCAD review report** is published as a **Pages preview** of robarm-me (``previews/pr-<n>/``), linked from the PR (with the provenance trailer) and removed when the PR closes.

.. xd-adr:: Scope cuts for iteration 1
   :id: XD-ADR-0124
   :legacy_id: D135
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0095
   :revises: XD-ADR-0098

   **Scope cuts for iteration 1:** variants start with ``buildKind`` and rules :need:`XD-RULE-0021`, :need:`XD-RULE-0022`, :need:`XD-RULE-0023` to :need:`XD-RULE-0027`; the FreeCAD review report stays local (:need:`XD-ADR-0098` deferred); robarm-ee and robarm-me start with one doc each.
