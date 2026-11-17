.. _adr-index:

Decisions
=========

This part records every decision about the XDMOD framework. Each decision is a need of type
``xd-adr`` (an *architecture decision record*), with an ID ``XD-ADR-nnnn`` from xdmod's ledger
``ids.yaml``. Decisions that are only about one project that uses XDMOD (its hardware, its repos,
its GitHub settings, its licence) are kept in that project's own documents, as ``prj-dec`` needs.
A project decision may ``follows`` a framework decision; a framework decision never links to a
project.

How to read a decision
----------------------

- ``legacy_id`` is the number the decision had in the planning log (``D1`` to ``D142``) before it
  became a need. Old texts and commit messages use these numbers.
- ``date`` is the day it was made.
- ``decision_status`` is ``proposed`` (written, but waiting for a spike or the owner), ``accepted``, ``revised`` (a newer decision changed part of it) or
  ``superseded`` (a newer decision replaced it). Changed decisions are never deleted or edited
  into something new: they keep their need, and the newer decision holds the link to them
  (``refines``, ``revises`` or ``supersedes``). The older need shows the link back as
  "refined by", "revised by" or "superseded by". This is the trace rule
  :need:`XD-ADR-0004` applied to decisions.
- Rules that a decision introduces are ``xd-rule`` needs that are ``decided_by`` it (see
  :doc:`../rules/index`).

How to add a decision
---------------------

1. Add an ``xd-adr`` need to the topic page it fits, with a placeholder ID
   (``<KIND>-NEW-<tag>``, see the ID scheme), ``decision_status: accepted``, ``status: valid`` and today's ``date``.
2. If it changes an older decision, add ``refines``, ``revises`` or ``supersedes`` with the older
   ID, and set the older need's ``decision_status``.
3. Run ``curatrix ids fix xdmod`` to issue the ID, then ``curatrix check xdmod --stage local``.

.. toctree::
   :maxdepth: 1

   method
   traces
   domains
   documents
   repos
   checks
   workflow
   scope

All decisions
-------------

.. needtable::
   :types: xd-adr
   :columns: id;legacy_id as "Old ID";title;decision_status as "Status";date
   :sort: id
   :style: table
