.. _ref-id-scheme:

ID scheme
=========

Every need has an ID. IDs are stable, never reused, readable, and unique across the whole
workspace. They work in every tool: sphinx-needs, SysML short names, KiCad fields, FreeCAD
properties, Doxygen tags and test reports. The scheme is new; it does not reuse older ID schemes
(:need:`XD-ADR-0013`).

Format
------

.. code-block:: text

   <DOMAIN>-<KIND>-<NNNN>   e.g.  SYS-REQ-0012, SW-TC-0103, EE-CMP-0007, INT-ITC-0003
   TR-<TESTCASE-ID>-<RUN>   e.g.  TR-SW-TC-0103-3f9a1c2e   (test results only)

- ``DOMAIN``: ``SYS``, ``SW``, ``EE``, ``ME``, ``INT`` (integration and system verification),
  ``XD`` for the framework's own items and ``PRJ`` for project-level items (:need:`XD-ADR-0071`,
  :need:`XD-ADR-0109`).
- ``KIND``: 2 to 5 capital letters. Domain and kind together name the need type.
- ``NNNN``: a number with 4 digits, zero-padded, issued per kind. Above 9999 it simply grows.
- ``RUN``: the first 8 hex digits of the run record's hash (HIL runs) or of the JUnit file. So a
  test result is unique per run.
- A usage of a definition may get ``<ID>.<n>`` (:need:`XD-ADR-0117`).
- Regex:
  ``^((SYS|SW|EE|ME|INT|XD|PRJ)-[A-Z]{2,5}-[0-9]{4,}|TR-(SYS|SW|EE|ME|INT)-[A-Z]{2,5}-[0-9]{4,}-[0-9a-f]{8})$``

**No project code in the sources** (:need:`XD-ADR-0072`). All repos of a project share one ID space.
Where IDs leave the workspace (bundles, published ``needs.json``, shared affirmatrix cases), the
exporting tool puts a project code in front, with ``:`` as the separator. Example (robot arm):
``RA:SYS-REQ-0012``.

Kinds
-----

Generated from curatrix and the needs configuration:

.. xd-id-kinds::

``SYS-VIEW`` is a reserved kind that is not a need. It is only used as the SysML short name of a
view (:need:`XD-ADR-0085`). Its numbers still come from the ledger. Configurations and features have the
kinds ``SYS-CFG`` and ``SYS-FEAT`` (:need:`XD-ADR-0097`). SW test case IDs come from the ledger and a tool
writes them into the ZTEST comment (:need:`XD-ADR-0073`).

Where the ID lives in each tool
-------------------------------

.. list-table::
   :header-rows: 1
   :widths: 20 50 30

   * - Tool
     - Where the ID is written
     - Read by
   * - sphinx-needs (rst)
     - ``:id:`` of the directive
     - Sphinx
   * - SysML v2
     - short name: ``part def <'SYS-EL-0012'> ArmController { … }``; stubs use the
       requirement's ID
     - Pilot JSON, then curatrix
   * - KiCad
     - hidden symbol or sheet field ``TraceID``; links in further hidden fields (``Realizes``,
       ``Satisfies``, ``Conforms``, ``PartOf``)
     - curatrix (plain Python)
   * - FreeCAD
     - object properties ``TraceID``, ``Realizes``, ``Satisfies``, ``Conforms``, ``PartOf``
     - ``Document.xml``, read by curatrix
   * - Doxygen / C
     - ``@xdid{SW-IMPL-0004}``, ``\satisfies``, ``\verifies``; test IDs in the ZTEST comment
     - Doxygen XML, then zdocs
   * - Twister / JUnit
     - the test case's ``SW-TC`` ID in the test name or a property
     - test reports, then ``TR`` needs
   * - Devicetree
     - ``trace-id`` property of the project's own binding, never on upstream nodes
       (:need:`XD-ADR-0057` (f))
     - the devicetree check

The ledger
----------

Each repo keeps one ledger file, ``ids.yaml``. It lists **every number ever issued** per kind
that the repo owns, one per line. It is append-only. Listing every number (not just the last)
means that two PRs that issue the same number touch the same line, so git reports a conflict
(:need:`XD-ADR-0122`).

.. code-block:: yaml

   # Every number issued per kind, one per line. Append-only.
   SYS-REQ:
     - 41
     - 42
   SYS-NEED:
     - 17
   SYS-FEAT: []       # owned, nothing issued yet

A kind with nothing issued yet is written ``KIND: []``. That line makes the repo the owner of
the kind.

Issuing IDs
-----------

- **Placeholders.** Write a need with a placeholder ID of the form ``<KIND>-NEW-<tag>``, for
  example the kind ``SYS-REQ`` followed by ``-NEW-a``. Then run
  ``curatrix ids fix <repo>``. It replaces every placeholder with the next free number
  (``max(ledger, IDs in the sources) + 1``) and adds it to the ledger. The same placeholder gets
  the same ID in every file.
- ``curatrix ids new <KIND> [FILE]`` issues one ID, and with ``FILE`` replaces that file's first
  placeholder of the kind.
- Never invent a number. Never reuse one.
- **Parallel PRs.** Two PRs may issue the same number. The second to rebase gets a ledger
  conflict. Rerun ``curatrix ids fix``, which renumbers that PR's new IDs. Rulesets require PRs
  to be up to date with ``main`` before merge, so the duplicate check runs on the combined state.
- **Retiring.** A retired need keeps its ID with ``status: retired`` (:need:`XD-ADR-0057` (e),
  :need:`XD-ADR-0119`). When it is finally deleted, the ledger still holds its number.

Rules
-----

.. needtable::
   :types: xd-rule
   :tags: ids
   :columns: id;title
   :style: table

- :need:`XD-RULE-0015` is checked by :need:`XD-CHECK-0003`.
- :need:`XD-RULE-0016` is checked by :need:`XD-CHECK-0010` across documents and in the full set.
- :need:`XD-RULE-0017` is checked by :need:`XD-CHECK-0013`.
- :need:`XD-RULE-0018` is checked by :need:`XD-CHECK-0014`.
- :need:`XD-RULE-0020` is helped by :need:`XD-CHECK-0012` (tombstones of deleted generated needs).
- :need:`XD-RULE-0019` is applied by the test-report extractor.
