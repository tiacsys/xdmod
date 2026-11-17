__TITLE_RST__

This document describes the assembly ``__NAME__`` (``__ID__``): the FreeCAD top document
``assemblies/__NAME__/__NAME__.FCStd``, its skeleton ``__NAME__-skeleton.FCStd`` and the assembly
def of the ME model it implements. It was made by ``curatrix new asm``; every assembly document has
the same sections (ME-4, XD-ADR-0129). Parameters, materials, interfaces and the BOM come from the
FreeCAD files and the ME model in plain Python; drawings, exploded view, renderings, mass and
findings come from the local ``curatrix cam`` output of the current commit and are not part of CI
builds.

Overview
--------

.. xd-asm-overview:: __NAME__

Block diagrams
--------------

The assembly def of the ME model: its parts, and its ports (from the model; ``curatrix views build``):

__BLOCK_DIAGRAMS__
Drawings
--------

.. xd-asm-drawing:: __NAME__

Exploded view
-------------

.. xd-asm-exploded:: __NAME__

Renderings
----------

.. xd-asm-renderings:: __NAME__

Mass and center of gravity
--------------------------

.. xd-asm-mass:: __NAME__

Parameters
----------

.. xd-asm-parameters:: __NAME__

Materials
---------

.. xd-asm-materials:: __NAME__

Interfaces
----------

.. xd-asm-interfaces:: __NAME__

Findings
--------

.. xd-asm-findings:: __NAME__

Sub-assemblies
--------------

.. xd-asm-subassemblies:: __NAME__

Appendix: bill of materials
---------------------------

.. xd-asm-bom:: __NAME__
