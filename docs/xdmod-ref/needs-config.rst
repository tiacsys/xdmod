.. _ref-needs-config:

Needs configuration
===================

``xdmod/needs/needs_config.toml`` is the one needs configuration of every XDMOD document. zdocs
loads it through ``ZDOCS_NEEDS_CONFIG``, which ``xdmod/cmake/xdmod-docs.cmake`` sets. The tables
below are generated from that file. What the types and links mean is explained in the manual's
:external+xdmod-manual:doc:`reference/trace-model` page.

Need types
----------

.. xd-need-types::

Link types
----------

Each link type is declared on the need type that holds it (the owner).

.. xd-link-types::

Fields
------

.. xd-need-fields::

ID kinds
--------

.. xd-id-kinds::
