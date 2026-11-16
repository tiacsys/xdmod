.. _tut-first-requirement:

Your first requirement, end to end
==================================

.. note:: This tutorial is a skeleton. It is completed in Phase 6 on the real robot-arm repos.

Goal
----

You follow one stakeholder need all the way down the V-model and back up to a test result:

.. code-block:: text

   stakeholder need  <-refines-   system requirement (EARS)
                     <-satisfies- SysML part (through a generated stub)
                     <-realizes-  KiCad component (hidden TraceID field)
                     <-verifies-  test case  <-result_of-  test result

This is the chain the spike proved on a tiny example. Each arrow is a link that the more concrete
artifact holds (:need:`XD-RULE-0001`). Backlinks are computed by the docs build.

Steps
-----

The examples use the robot-arm repos. Replace the repo names with your own.

1. **Write the need and the requirement** in the requirements document of the syseng repo
   (``robarm-syseng/docs/se-req/``). Use placeholder IDs; see :doc:`/howto/add-a-requirement`.

   .. code-block:: rst

      .. sys-need:: Follow the leader arm
         :id: SYS-NEED-NEW-follow
         :category: need
         :raised_by: SYS-STH-0001

      .. sys-req:: Follow latency
         :id: SYS-REQ-NEW-latency
         :refines: SYS-NEED-NEW-follow
         :ears: ubiquitous
         :quantity: latency
         :unit: ms
         :max: 50

         The system shall move each follower joint within 50 ms of the leader joint.

2. **Issue the IDs** and build the docs, so the stubs can be made from the needs:

   .. code-block:: sh

      curatrix ids fix robarm-syseng
      curatrix docs robarm-syseng
      curatrix gen stubs robarm-syseng

3. **Satisfy the requirement in the model.** Give a part definition a short-name ID and add a
   ``satisfy`` through the generated stub; see :doc:`/howto/add-a-model-element`. Then regenerate
   the model needs:

   .. code-block:: sh

      curatrix ids fix robarm-syseng
      curatrix gen model robarm-syseng

4. **Realize the model element in a domain.** In the EE repo, give a KiCad symbol or sheet the
   hidden fields ``TraceID`` and ``Realizes``; see :doc:`/howto/add-a-pcba`. Then:

   .. code-block:: sh

      curatrix gen cad-needs robarm-ee

5. **Verify it.** Write a test case that ``verifies`` the requirement; see
   :doc:`/howto/add-a-test`. Its result becomes a test result need.

6. **Check and look.** Run the checks of each repo you touched, then build the full set:

   .. code-block:: sh

      curatrix check robarm-syseng --stage local
      curatrix check robarm-ee --stage local
      curatrix docs full

   A ``tracechain`` table in the project overview shows the chain, and gaps are marked as
   "(missing)".

What can go wrong
-----------------

- A link written on the wrong side, or to an unknown ID, fails the strict build (:need:`XD-RULE-0002`,
  :need:`XD-CHECK-0001`).
- A model element that realizes nothing and satisfies nothing is an orphan (:need:`XD-RULE-0010`,
  :need:`XD-CHECK-0004`).
- Generated files that don't match their sources fail the checks (:need:`XD-RULE-0033`). Run the matching
  ``curatrix gen`` command and commit the result.

Next: :doc:`first-change`.
