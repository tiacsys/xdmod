.. _ref-api:

curatrix Python API
===================

curatrix is a Python package (``xdmod/curatrix/src/curatrix``). Other tools and tests may call
these modules directly. Every subprocess must go through :func:`curatrix.limits.run`, so it gets
the memory limit and timeout of its use. This page is generated from the docstrings.

Workspace and limits
--------------------

.. automodule:: curatrix.ws
   :members: Workspace, find_root

.. automodule:: curatrix.limits
   :members: run, resolve

IDs and the ledger
------------------

.. automodule:: curatrix.ids
   :members: Ledger, fix, new, check_placeholders, check_ledger

Checks
------

.. automodule:: curatrix.checks
   :members: run

.. automodule:: curatrix.graph
   :members: load, check

Documents and generated files
-----------------------------

.. automodule:: curatrix.docs
   :members: build

.. automodule:: curatrix.gen
