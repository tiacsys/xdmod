.. _howto-design-output:

Make the design output of a board or assembly
=============================================

Use this guide when you need the manufacturing and review files of a board, a harness or an
assembly: Gerber, drill, pick-and-place, STEP, printed parts, drawings, renderings, BOMs. One command
makes them for both domains, always locally and on a copy under ``build/``
(:need:`XD-ADR-0142`, :need:`XD-ADR-0143`). CI never runs it; the documents show a fixed sentence
there instead.

.. code-block:: sh

   curatrix cam robarm-ee canary-board        # a board (pcba/<name>/)
   curatrix cam robarm-ee canary-cable        # a harness (harness/<name>/)
   curatrix cam robarm-me canary-assembly     # a top-level assembly (assemblies/<name>/)
   curatrix cam robarm-ee                     # every board and harness of the repo

The version
-----------

Each run writes into ``build/<area>/cam/<name>/<version>/`` (in a worktree set:
``build/wt-<branch>/<area>/cam/...``). The version comes from the tags of that board, harness or
assembly, ``<name>/vX.Y.Z`` (``git describe --tags --match '<name>/*'``):

- **Release:** the commit is exactly a tag on ``main`` and the folder has no uncommitted changes. The
  output carries ``v1.2.0``.
- **Preview:** anything else: commits after the tag, a dirty folder, or no tag yet
  (``<name>/v0.0.0-<n>-g<sha>-preview``). The output carries the version with ``-dirty`` or
  ``-preview``, the renderings and drawings a red ``PREVIEW``, an embossed part a ``P``.

Only the owner creates tags (:need:`XD-ADR-0140`). To see the release marking, run ``cam`` on a
tagged commit with a clean tree; to see the preview marking, change a file in the board's or
assembly's folder and run it again.

Boards (EE)
-----------

``curatrix cam robarm-ee <board>`` copies the ``pcba/<board>/`` project into the version folder,
writes the version without the ``<board>/`` tag prefix into the copy's ``XD_VERSION`` (``v0.1.0``,
``v0.1.0-3-gabc1234-preview``) and the board name into ``XD_BOARD``, and runs the board's KiCad
jobset there (the shared template, CK-F10). Title blocks show ``${XD_BOARD}`` as title and
``${XD_VERSION}`` as revision, the silkscreen both on two lines (CK-F11). Per variant (``default``, ``alt``, ...) it writes:

.. list-table::
   :header-rows: 1

   * - Output
     - Files
   * - Fabrication
     - ``gerbers/`` (Gerber and drill), ``pos-<variant>-all-pos.csv`` (pick and place)
   * - Assembly
     - ``bom-<variant>.csv``, ``netlist.xml``
   * - 3D
     - ``<board>-<variant>.step``, ``render-top|bottom|3d-<variant>.png`` (orthographic top and
       bottom, one 3D view)
   * - Schematic
     - ``<board>-schematic-<variant>.pdf``, ``schematic-svg-<variant>/``
   * - Board data
     - ``stackup.csv``, ``design-rules.csv`` (plain Python; KiCad has no export)
   * - Findings
     - ``erc-drc/`` (KiCad's JSON) and ``findings.json`` with the acceptance state of each finding
   * - Record
     - ``cam.json`` (version, commit, files, tree state), ``jobset.log``

The run fails when a job fails or fewer jobs ran than the jobset has. After you add a variant, write
the jobset again with ``curatrix cam robarm-ee <board> --update-jobset``. STEP and renderings show
the parts only when the KiCad 3D models are in the workspace (``libs/kicad/packages3D``, the west
group ``kicad-3d``, about 1.8 GB). Only the roles ``ee3d`` and ``full`` include that group; the roles
``ee``, ``me`` and ``integration`` leave it out, though they can run ``curatrix cam``. Without the
models KiCad renders the bare board without a message, so curatrix says it in four places:
``curatrix doctor`` warns in every role that runs design output (``ee``, ``ee3d``, ``me``,
``integration``, ``full``); ``curatrix cam`` prints a warning, records ``kicad_3d_models``
(``present``, ``partial``, ``missing`` or ``none``) and the missing model paths in ``cam.json``, and
puts a red banner on every ``render-*.png``; and the board document's renderings section shows a
warning. To get the models: ``curatrix bootstrap --role full --adopt`` (or ``--role ee3d``), then
run ``curatrix cam`` again.

A harness (``harness/<name>/<name>.yml``) gets its WireViz diagram (``<name>.svg``, ``.png``) with
the version as label and its BOM (``<name>.bom.tsv``) (:need:`XD-ADR-0127`).

The FreeCAD model of a board for the ME side comes from the same command:
``--board-model`` writes it for any version under ``build/<area>/board-model/``; ``--library`` does
so only for a tagged release and copies it into a board-library checkout for its PR
(:need:`XD-ADR-0139`). The model sits in the board frame of the co-design budget
(:need:`XD-ADR-0134`): origin at the lower-left corner of the ``Edge.Cuts`` outline seen from the
top, x right, y up, z = 0 on the top face (``general.thickness`` of the board, in the ``Board``
property ``Thickness``). An assembly places it with the seat's LCS as it is. The outline must be
drawn on the board (lines, rects, polygons, circles, arcs); ``Edge.Cuts`` items inside a footprint are
not read.

The model is made by the FreeCAD GUI binary on Qt's offscreen platform (no window opens): the
``App::Part`` ``Board`` carries the trace properties (``TraceID``, ``Version``, ``Variant``,
``Board``, ``Commit``, ``Source``) and holds one object per component, named by its reference
designator (``R1``, ``J1``, ``PCB`` for the board body), in the colours of the STEP. Each object is
a link to the component's 3D model, kept once per model in the hidden group ``Models``.
``board-model.json`` lists the components with their colours per file; ``board-model/<board>/<version>/``
also keeps the STEP and the import result (``*.result.json``). A file without colours is reported as
a finding.

Assemblies (ME)
---------------

``curatrix cam robarm-me <assembly>`` runs ``FreeCADCmd`` once per variant: each configuration that a
link's ``Configs`` names, plus ``base`` (the links without ``Configs``), or ``all`` when no link has
``Configs``. Per variant, in ``<assembly>/<variant>/``:

.. list-table::
   :header-rows: 1

   * - Output
     - Files
   * - 3D
     - ``<assembly>.step``
   * - Printed parts
     - ``parts/<part>.3mf`` and ``.stl`` with the short version embossed on the part's version mark,
       ``print/<profile>.ini`` copied from the repo
   * - Drawing
     - ``drawing.svg`` and ``drawing.pdf`` (front, top and right in first-angle projection, the iso
       view, frame and title block), ``views/*.svg``
   * - Exploded view
     - ``exploded.svg`` (moves from ``assemblies/<assembly>/explode.yaml``, else automatic)
   * - Renderings
     - ``renderings/front|top|right|iso.png``
   * - BOM and mass
     - ``bom.csv`` (flat, with totals), ``mass.json`` (mass and center of gravity)

The version folder also holds ``findings.json`` (CK-F4c, CK-F16, CK-F17 with their acceptance state)
and ``cam.json``.

Blender or the fallback renderer
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The renderings come from one of two renderers. ``cam.json`` names the one used
(``renderings.method``: ``blender`` or ``zbuffer``):

.. list-table::
   :header-rows: 1

   * -
     - Blender (:need:`XD-ADR-0148`)
     - Fallback (:need:`XD-ADR-0147`)
   * - When
     - Blender is on the machine and you did not pass ``--no-blender``
     - no Blender, or ``--no-blender``; always in CI
   * - How
     - ``FreeCADCmd`` writes a coloured glTF scene, Blender renders it with Cycles on the CPU
       (fixed samples and seed, edges drawn)
     - FreeCAD's tessellation drawn into a z-buffer in plain Python inside ``FreeCADCmd``, with visible
       edges; no OpenGL
   * - Look
     - shaded with light and materials
     - flat shading by BOM kind, sharp edges
   * - Time (canary)
     - about 35 s for the whole ``cam`` run
     - about 6 s for the whole ``cam`` run

Both write the same files at the same scales (front, top and right at one scale, iso at its own),
with assembly, variant, version and view on each image. Blender is optional and not pinnable, so its
images are local only; ``curatrix doctor`` shows its version. Run Blender only through curatrix
(``curatrix run -- blender``, ``curatrix launch blender``) or the ``.venv/bin/blender`` shim: they
start it with ``--factory-startup --offline-mode --disable-autoexec`` and keep its user files in
``.xdmod/blender/``.

.. code-block:: sh

   curatrix cam robarm-me canary-assembly                # Blender if installed, else the fallback
   curatrix cam robarm-me canary-assembly --no-blender   # always the fallback (quick look, as CI)

Design output in the documents
------------------------------

The board and assembly documents show renderings, schematic, drawings, exploded view, mass and
findings only from the ``cam`` output of the commit the repo is at, or, with uncommitted changes, from
a run newer than every changed file (:need:`XD-RULE-0060`). So run ``cam`` before ``docs``:

.. code-block:: sh

   curatrix cam robarm-ee canary-board && curatrix docs robarm-ee
   curatrix cam robarm-me canary-assembly && curatrix docs robarm-me

Without a matching run, these sections print a fixed sentence and CK-D10 warns locally.

Pitfalls
--------

- Never edit the copy under ``build/`` and commit it back; change the project and run ``cam`` again.
- ``cam`` writes nothing into the repo. Its output is not committed; a release is reproduced from its
  tag.
- A tag made locally and never pushed gives release output that no one else can reproduce. Tags are
  the owner's (:need:`XD-ADR-0140`).
