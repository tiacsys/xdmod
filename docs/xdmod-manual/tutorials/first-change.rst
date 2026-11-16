.. _tut-first-change:

Your first change
=================

.. note:: This tutorial is a skeleton. It is completed in Phase 6 on the real robot-arm repos.

Goal
----

You change one requirement and retire another. You see what each check reports, read the change
impact, fix the downstream links, and prepare the affirmation of the suspect links.

Steps
-----

1. **Start a branch.** Use one branch name in every repo you touch (:need:`XD-ADR-0045`):

   .. code-block:: sh

      curatrix work start feat/latency robarm-syseng robarm-ee

   ``curatrix work`` is being added (task 4.4c); see :doc:`/howto/cross-repo-change`.

2. **Change a requirement.** Edit the sentence and its value fields together (:need:`XD-RULE-0036`), e.g.
   ``100 ms`` becomes ``50 ms`` and ``:max:`` becomes ``50``. A text change fails no build. Only
   the change impact shows it.

3. **Retire a requirement.** Set ``:status: retired``. Never delete a need that others link to
   before it is retired (:need:`XD-RULE-0020`). Links to it are reported as warnings until the next
   baseline (:need:`XD-RULE-0011`, :need:`XD-CHECK-0008`).

4. **Regenerate** what depends on the needs:

   .. code-block:: sh

      curatrix docs robarm-syseng
      curatrix gen all robarm-syseng

5. **Read the change impact.** Compare the needs before and after the change:

   .. code-block:: sh

      curatrix needs-diff build/main-needs/ build/robarm-syseng/docs/deploy/html/ -o build/robarm-syseng/needs-diff.md

   It lists changed needs, direct and transitive **suspect** links, and dangling links
   (:need:`XD-RULE-0014`). In a PR, :need:`XD-CHECK-0023` writes the same report.

6. **Fix downstream.** Each downstream owner updates the links that pointed at the retired need,
   on the same branch name, and runs the checks of their repo.

7. **Affirm.** For each suspect link, an agent may prepare a proposal (reason and diff). Only a
   person's commit affirms it (:need:`XD-ADR-0051`).

8. **Open the PRs**, one per repo, and list the sibling PRs in each; see
   :doc:`/howto/cross-repo-change`.

What you learned
----------------

- Structure errors fail the build at once. Content changes need the change-impact report.
- Retired needs keep their ID forever, and IDs are never reused.
