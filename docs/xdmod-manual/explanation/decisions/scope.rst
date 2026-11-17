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
   :decision_status: revised
   :status: valid
   :revises: XD-ADR-0002, XD-ADR-0018, XD-ADR-0019

   **Moved to iteration 2:** CAM pipeline and bundle, the PDF document set, layout keeping in drawio, product PCB layout. Iteration 1 builds HTML docs only. Changed by :need:`XD-ADR-0142`, :need:`XD-ADR-0143` (CAM in iteration 1) and :need:`XD-ADR-0144` (a PCB layout without routing).

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
   :decision_status: revised
   :status: valid
   :refines: XD-ADR-0095
   :revises: XD-ADR-0098

   **Scope cuts for iteration 1:** variants start with ``buildKind`` and rules :need:`XD-RULE-0021`, :need:`XD-RULE-0022`, :need:`XD-RULE-0023` to :need:`XD-RULE-0027`; the FreeCAD review report stays local (:need:`XD-ADR-0098` deferred); robarm-ee and robarm-me start with one doc each. Changed by :need:`XD-ADR-0129` (one document per board, harness and assembly).

.. xd-adr:: EE design output in iteration 1
   :id: XD-ADR-0142
   :date: 2026-11-17
   :decision_status: accepted
   :status: valid
   :revises: XD-ADR-0037
   :refines: XD-ADR-0018

   **The EE part of the CAM pipeline moves into iteration 1.** ``curatrix cam <repo> [<project>]``
   copies the KiCad project into ``build/<repo>/cam/<project>/<version>/``, writes the version into
   the copy's ``.kicad_pro`` text variable ``XD_VERSION`` and runs the jobset there with ``kicad-cli
   jobset run``. The committed project keeps ``XD_VERSION = "unversioned"``.

   - **Version:** ``git describe --match '<project>/*'`` (:need:`XD-ADR-0140`). A dirty tree, or a
     commit that is not on ``main`` or a baseline, gives a version marked as preview; without a tag
     it is ``<project>/v0.0.0-<n>-g<sha>-preview``. The full version goes into a title-block comment
     line and a silkscreen text; the ``Rev`` field cuts long strings off, so it holds only the short
     version or nothing.
   - **Jobset:** one shared template in xdmod, copied by ``curatrix new pcba``. A job can name a
     variant (KiCad 10.0.8, KiCad spike §2.2), so the jobset holds one job per variant-dependent output
     and variant, copied from its base job except for the variant and file name; the variant names in
     the jobs equal those of the project. No "Execute Command" jobs, no "Copy Files" outside the
     output folder, no statistics job, BOM delimiters set, ERC and DRC not in the jobset (the checks
     evaluate them). curatrix fails the run when fewer jobs ran than the jobset has (a job KiCad
     cannot parse drops all jobs with exit code 0).
   - **Outputs:** Gerber and drill, pick-and-place, netlist, STEP, top and bottom renderings
     (orthographic) and one 3D rendering, schematic PDF and SVG, BOM CSV. The stackup table (and an
     optional SVG cross-section) and the design-rule table come from plain Python, because KiCad
     exports neither.
   - **Where:** output only under ``build/``, never committed, no release asset, run only locally (no
     KiCad in CI). The bundle stays in iteration 2. KiCad batch runs use the workspace-local
     configuration, cache and documents folders, the C locale and a ``TMPDIR`` under ``build/``, one
     after the other.

.. xd-adr:: ME design output in iteration 1
   :id: XD-ADR-0143
   :date: 2026-11-17
   :decision_status: accepted
   :status: valid
   :revises: XD-ADR-0037
   :refines: XD-ADR-0018, XD-ADR-0024

   **The ME part of the CAM pipeline moves into iteration 1.** ``curatrix cam <repo> <asm>`` runs
   FreeCAD headless under limits into ``build/<repo>/cam/<asm>/<version>/``: STEP of the assembly; 3MF
   and STL per printed part with its print profile (:need:`XD-ADR-0024`); TechDraw drawings as PDF and
   SVG; the exploded view as a TechDraw view SVG, built in ``FreeCADCmd`` (:need:`XD-ADR-0137`); a flat BOM
   CSV with totals. Per variant: set the variant row, recompute, export, close without saving;
   presence by ``Configs``. The version comes from the assembly tags (:need:`XD-ADR-0140`), with the
   same preview marking as EE. A shared part from ``parts/`` carries the version of the assembly
   being exported.

   **Version on printed parts:** a part marks the face for it with an LCS (``Role =
   version-emboss``, text size, maximum width). At export, and only there, curatrix embosses the
   short version (the full string goes into the drawing) with a font pinned in xdmod; the
   ``.FCStd`` stays unchanged, and the export fails unless the result is exactly one valid solid.
   GLB is deferred; renderings come at the end of Phase 5 (task 5.30). Output only under ``build/``,
   only locally. Based on the FreeCAD spike (§5, §6).

.. xd-adr:: ME renderings without OpenGL, the fallback when Blender is absent
   :id: XD-ADR-0147
   :date: 2026-11-17
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0143

   Proposed by the agent of task 5.30, for the owner to accept or change. The spike
   (``claude/notes/me-renderings-spike.md``) found that neither the Render workbench (an addon that
   needs an external renderer) nor a Coin3D snapshot (``saveImage`` in the GUI binary offscreen gives a
   blank image; ``SoOffscreenRenderer`` finds no GL context) works headless. The owner first ruled out
   Blender, then allowed it as an optional local renderer (a separate change); this decision is the
   renderer ``curatrix cam`` uses **when Blender is absent**, and in every environment without it.

   ``curatrix cam <repo> <asm>`` writes ``renderings/front|top|right|iso.png`` per variant from the
   same ``FreeCADCmd`` run (method ``zbuffer`` in ``cam.json``): FreeCAD tessellates the present
   parts, the script draws the facets flat-shaded into a z-buffer (numpy, a dependency of FreeCAD)
   with the visible edges on top, and FreeCAD's Qt writes the text and the PNG. The views are the
   ones of the drawing (``right`` is the side view); front, top and right share one scale, iso has
   its own, and the scale is on each image. Colours come from the BOM kind, not from the document.
   Each image carries the assembly, the variant, the full version and the view, and ``PREVIEW``
   unless a release; a rendering without a drawn facet, or a pinned font that does not load, fails
   the run.

   **Limits:** orthographic and flat-shaded, no perspective, shadows or materials; where two parts
   overlap in one plane (a collision) the part drawn first shows, and edges that lie in another
   part's face show through. Time grows with the drawn pixels and the facet count: 4 to 8 s per view
   for 272 000 facets (60 filleted tubes), about 1 s per view for a few boxes, on the owner's machine,
   well inside the ``freecad`` limit of 10 minutes for a few variants.

.. xd-adr:: Blender as an optional local renderer of the ME renderings
   :id: XD-ADR-0148
   :date: 2026-11-17
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0147

   Proposed by the agent of the Blender follow-up to task 5.30, for the owner to accept or change.
   The owner reversed "no Blender" on 2026-11-17: the Blender package of the machine may render,
   through its executable only (no ``bpy`` wheel, no new system package).

   **Optional and local.** When ``blender`` is on the machine, ``curatrix cam <repo> <asm>`` lets
   ``FreeCADCmd`` write the tessellated parts per variant as glTF (``<variant>.scene.glb`` beside
   ``cam.json``; colour by BOM kind, as before) and Blender render the same four views
   (``renderings/front|top|right|iso.png``, same size, names and marking) with Cycles on the CPU:
   orthographic cameras, three sun lights and a dim sky, no shadows (overlapping or touching parts
   would shade each other black), Freestyle edges, fixed samples and seed, no denoiser, half the
   cores as threads (the output does not depend on the thread count). Without
   Blender, or with ``--no-blender``, the z-buffer renderer of :need:`XD-ADR-0147` runs, so CI and
   machines without Blender get renderings too. ``cam.json`` says which: ``renderings.method`` is
   ``blender`` or ``zbuffer``; for Blender also its version, engine, samples and seed.

   **Not pinnable.** Blender comes from the distribution and curatrix installs nothing, so its
   output is never committed or compared, and ``tools.yaml`` records the version it was tried
   with (``pinned: false``): ``curatrix doctor`` notes a missing Blender and warns on another
   version, it never fails on them. Tests that need Blender are marked ``tools`` and run locally
   only.

   **Isolated.** Every call, from curatrix, ``curatrix run -- blender``, ``curatrix launch
   blender`` or the ``.venv/bin/blender`` shim, gets ``--factory-startup --offline-mode
   --disable-autoexec`` and the user paths under ``.xdmod/blender/`` (``BLENDER_USER_RESOURCES``,
   ``_CONFIG``, ``_SCRIPTS``, ``_DATAFILES``, ``_EXTENSIONS``, the XDG dirs for the caches,
   ``TMPDIR``), as :need:`XD-ADR-0145` does for KiCad and FreeCAD; Blender's Python runs without the
   workspace venv, and ``.xdmod/blender/bin`` (a copy of the shim) comes first on ``PATH``, so a
   ``blender`` started by a child process is isolated too. Never call Blender bare. The ``blender`` limits (4 GB, 10 minutes per variant)
   apply, also to ``curatrix run -- blender`` without ``--use``.

.. xd-adr:: A PCB layout in iteration 1, without routing
   :id: XD-ADR-0144
   :date: 2026-11-17
   :decision_status: accepted
   :status: valid
   :revises: XD-ADR-0037

   **Iteration 1 includes a PCB layout** for the product board: placement, board outline and
   silkscreen. Routing is not completed. The DRC errors of unrouted nets (one ``unconnected_items``
   entry per missing connection, so pads − 1 per net) are accepted in **one** entry of the board's
   ``accepted.yaml`` (:need:`XD-ADR-0126`), not as KiCad exclusions, which change with every move.
   All other DRC errors must be fixed or accepted one by one.
