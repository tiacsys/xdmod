.. _ref-sphinx-extensions:

Sphinx extensions
=================

xdmod ships one Sphinx extension, ``xdmod_sphinx`` (``xdmod/sphinx/xdmod_sphinx/``), and a
``conf.py`` helper, ``xdmod_conf`` (``xdmod/sphinx/xdmod_conf.py``). Features that zdocs lacks are
built here (:need:`XD-ADR-0028`). Every document of every repo that uses XDMOD loads both.

conf.py
-------

Each document's ``conf.py`` calls ``configure``:

.. code-block:: python

   import os, sys
   from pathlib import Path
   sys.path.insert(0, str(Path(os.environ["ZDOCS_WEST_TOPDIR"]) / "xdmod" / "sphinx"))
   from xdmod_conf import configure, repo_root

   REPO = repo_root(__file__)
   configure(globals(), __file__, "System Architecture",
             generated=[(REPO, "generated/*.json"), (REPO, "views/*.drawio.svg")])

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Argument
     - Meaning
   * - ``ns``, ``conf_file``
     - ``globals()`` and ``__file__`` of the ``conf.py``.
   * - ``project``
     - The document title.
   * - ``generated``
     - ``(base folder, glob)`` pairs of files outside the document folder that the document
       reads: generated needs, views, JUnit XML. zdocs copies only the document folder, so these
       are staged into the source tree. In rst you address them from the source root, e.g.
       ``/generated/model-needs.json``.
   * - ``extensions``
     - More Sphinx extensions to load.
   * - ``cad_dir``
     - Folder of the CAD exports. Default: ``$XD_CAD_DIR``, else ``build/<area>/cad``.

``configure`` wraps zdocs' own ``configure``, loads ``sphinx_test_reports`` and ``xdmod_sphinx``,
sets the sphinx-test-reports link options (``verifies``, ``result_of``, deterministic IDs) and
suppresses the warning ``needs.type_near_name``. The shared needs configuration
(``xdmod/needs/needs_config.toml``) comes in through zdocs (``ZDOCS_NEEDS_CONFIG``), set by
``xdmod/cmake/xdmod-docs.cmake``.

Directives for design documents
-------------------------------

.. list-table::
   :header-rows: 1
   :widths: 20 30 50

   * - Directive
     - Argument and options
     - Does
   * - ``sysml-view``
     - path of a ``.drawio.svg`` in the source tree; ``:caption:``
     - Puts the committed editable SVG inline (:need:`XD-ADR-0087`). Cells with a trace ID link to the
       need's page in this build. A link to an unknown need is a warning, so a strict build
       fails.
   * - ``xd-needimport``
     - path of a needs JSON file; ``:optional:``; all other options go to ``needimport``
     - Like ``needimport``, but an optional file that doesn't exist is skipped, e.g.
       ``retired-needs.json`` before the first tombstone.
   * - ``kicad-sheet``, ``kicad-bom``, ``kicad-nets``, ``freecad-drawing``, ``freecad-3d``
     - name of an export below the CAD folder; ``:caption:``
     - Shows the export if ``curatrix gen cad-exports`` made it (SVG inline, CSV as a table,
       other files as a link). Otherwise a short "built locally" notice, without a warning
       (:need:`XD-ADR-0049`).
   * - ``freecad-params``
     - path of a committed ``.FCStd``; ``:sheet:``
     - Spreadsheet aliases and values as a table, read in plain Python (works in CI).
   * - ``tracechain``
     - a chain such as ``sys-need <-refines- sys-req <-satisfies- sys-el``
     - One row per path from each need of the first type down the back links. Gaps show as
       "(missing)".
   * - ``coverage-matrix``, ``config-page``, ``sysml-element``
     - (ignored)
     - Iteration 1 stubs: they show a notice (:need:`XD-ADR-0094`, :need:`XD-ADR-0096`).

Examples:

.. code-block:: rst

   .. sysml-view:: /views/jointView.drawio.svg
      :caption: Joint module

   .. xd-needimport:: /generated/retired-needs.json
      :optional:

   .. kicad-sheet:: joint/joint.svg

   .. freecad-params:: /parts/link.FCStd
      :sheet: Params

   .. tracechain:: sys-need <-refines- sys-req <-satisfies- sys-el <-realizes- ee-cmp

Reference directives
--------------------

These directives render reference tables and needs from xdmod's own configuration and code, so
the reference can't drift from it. They take no arguments. They live in
``xdmod/sphinx/xdmod_sphinx/reference.py``.

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Directive
     - Renders
   * - ``xd-need-types``
     - every need type of ``needs_config.toml``: directive, title, ID prefix, link types
   * - ``xd-link-types``
     - the link-type table: owner type, link, target types, minimum
   * - ``xd-need-fields``
     - the shared need fields with their description and allowed values
   * - ``xd-id-kinds``
     - the ID kinds curatrix knows, with their need types
   * - ``xd-check-table``
     - the catalogue of curatrix's built-in checks: ID, name, level per stage
   * - ``xd-check-needs``
     - one ``xd-check`` need per built-in check, with its ``enforces`` links
   * - ``xd-cli``
     - the curatrix command line, from its argument parser

Example: the check catalogue in the manual is
:external+xdmod-manual:doc:`reference/checks`.
