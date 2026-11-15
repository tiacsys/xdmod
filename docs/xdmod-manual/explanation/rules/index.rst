.. _rules-index:

Rules
=====

The XDMOD method has rules: how links are written, how IDs are issued, how variants are bound,
and how repos are kept clean. Each rule is a need of type ``xd-rule`` with an ID
``XD-RULE-nnnn``. Each rule is ``decided_by`` the decision (``xd-adr``) that introduced it, and
each curatrix check that enforces a rule is an ``xd-check`` need that ``enforces`` it (see
:doc:`../../reference/checks`). So for every rule you can see why it exists and which check
catches a break of it. A rule without an "enforced by" link is followed by convention or by the
tools themselves, not by a check.

``legacy_id`` is the name the rule had in the planning drafts, for example ``R3`` or ``V4``, or
the place in the draft it comes from.

.. toctree::
   :maxdepth: 1

   trace
   ids
   variants
   checks

All rules
---------

.. needtable::
   :types: xd-rule
   :columns: id;legacy_id as "Old name";title;decided_by as "Decided by";enforces_back as "Enforced by"
   :sort: id
   :style: table
