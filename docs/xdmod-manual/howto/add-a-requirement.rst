.. _howto-add-a-requirement:

Add a requirement
=================

Use this guide when you add a system requirement (``sys-req``) or a domain requirement
(``sw-req``, ``ee-req``, ``me-req``).

Steps
-----

1. Open the requirements document of the repo that owns the requirement. System requirements
   live in the syseng repo; domain requirements in their domain repo.
2. Write the need with a **placeholder ID** of the form ``<KIND>-NEW-<tag>``. Never invent a
   number (:need:`XD-RULE-0017`).

   .. code-block:: rst

      .. sys-req:: Follow latency
         :id: SYS-REQ-NEW-latency
         :refines: SYS-NEED-0003
         :ears: ubiquitous
         :category: performance
         :quantity: latency
         :unit: ms
         :max: 50
         :verification_method: test
         :verification_scope: logical

         The system shall move each follower joint within 50 ms of the leader joint.

3. Write the sentence in an **EARS** pattern (:need:`XD-ADR-0009`, :need:`XD-ADR-0039`) and set ``:ears:`` to
   that pattern (:need:`XD-RULE-0037`). Stakeholder needs may be plain statements.
4. Put every number of the sentence into the value fields (``quantity``, ``unit``, ``min``,
   ``max``, ``nominal``, :need:`XD-ADR-0076`). The check compares them with the sentence (:need:`XD-RULE-0036`).
5. Add the upstream link. A system requirement ``refines`` a stakeholder need. A domain
   requirement ``refines`` a system requirement or an interface. A domain requirement with no
   upstream link needs ``:derived: true`` and a ``:rationale:``.
6. If the requirement applies only to some configurations, add ``:where:`` with the feature
   condition (:need:`XD-ADR-0093`).
7. Issue the ID:

   .. code-block:: sh

      curatrix ids fix robarm-syseng

8. For system requirements, rebuild the docs and the SysML stubs, so the model can refer to the
   new requirement (:need:`XD-ADR-0036`):

   .. code-block:: sh

      curatrix docs robarm-syseng
      curatrix gen stubs robarm-syseng

Checks
------

.. code-block:: sh

   curatrix check robarm-syseng --stage local

- :need:`XD-CHECK-0013` and :need:`XD-CHECK-0014`: no placeholders left, every ID is in the ledger.
- :need:`XD-CHECK-0021` and :need:`XD-CHECK-0022`: value fields and EARS pattern agree with the sentence.
- :need:`XD-CHECK-0015`: the stubs match the needs.
- :need:`XD-CHECK-0001`: the strict docs build; a missing ``refines`` fails it.

Pitfalls
--------

- Two PRs may issue the same number. The second one to rebase gets a ledger conflict. Take
  ``main``'s ledger and run ``curatrix ids fix`` again (:need:`XD-ADR-0122`).
- Don't delete a requirement. Set ``:status: retired`` first (:need:`XD-RULE-0020`).
