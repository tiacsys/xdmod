__TITLE_RST__

This document describes the board ``__NAME__``: the KiCad project
``pcba/__NAME__/__NAME__.kicad_pro`` and the board def of the EE model it implements. It was made
by ``curatrix new pcba``; every board document has the same sections (XD-ADR-0129). The tables come
from the KiCad files in plain Python; renderings, schematic and ERC/DRC findings come from the local
``curatrix cam`` output of the current commit and are not part of CI builds.

Overview
--------

.. xd-pcba-overview:: __NAME__

Block diagram
-------------

The board def of the EE model with its connector ports (from the model; ``curatrix views build``):

__BLOCK_DIAGRAM__
Variants
--------

.. xd-pcba-variants:: __NAME__

__VARIANTS_VIEW__
Renderings
----------

.. xd-pcba-renderings:: __NAME__

Schematic
---------

.. xd-pcba-schematic:: __NAME__

Stackup
-------

.. xd-pcba-stackup:: __NAME__

Design rules
------------

.. xd-pcba-rules:: __NAME__

Connectors
----------

.. xd-pcba-connectors:: __NAME__

ERC and DRC findings
--------------------

.. xd-pcba-findings:: __NAME__

Appendix: bill of materials
---------------------------

.. xd-pcba-bom:: __NAME__
