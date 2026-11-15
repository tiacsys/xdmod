.. _howto-work-as-an-agent:

Work as an agent
================

Use this guide if you are an AI agent, or if you brief one. Agents do the same work with the same
tools as people (:need:`XD-ADR-0003`). The differences are listed here.

Before you start
----------------

1. Read the workspace ``CLAUDE.md`` (copied from ``xdmod/launch/CLAUDE.md``, :need:`XD-ADR-0062`) and
   the ``claude/CLAUDE.md`` of each repo you change.
2. Get a brief: goal, binding decisions, files to read, output paths, and what you must not do.
3. Work in your own worktree set (:need:`XD-ADR-0114`): ``curatrix work start <branch> <repos...>``.
   One agent per branch per repo.

What agents may and may not do
------------------------------

.. list-table::
   :header-rows: 1

   * - Agents may
     - Agents may not
   * - create branches, commit, push to their own branches
     - merge PRs, push to ``main``, force-push to other people's branches
   * - open PRs and issues and comment on them, with the provenance trailer (:need:`XD-ADR-0065`)
     - change repo or org settings without the owner's approval of the concrete action list
       (:need:`XD-ADR-0112`)
   * - add ``Co-Authored-By``, and ``Signed-off-by`` where a repo requires it (:need:`XD-ADR-0108`)
     - affirm suspect links or give manual verdicts; they only propose them (:need:`XD-ADR-0051`)
   * - run any tool through curatrix, under limits (:need:`XD-ADR-0064`)
     - run tools without limits, install system packages, use sudo
   * - post freely in the framework and project repos
     - post on other repos before the owner approved the draft (:need:`XD-ADR-0113`)

Rules while working
-------------------

- Run every command from the workspace root (:need:`XD-ADR-0060`). Run tools that curatrix has no
  subcommand for through ``curatrix run -- <cmd>`` (:need:`XD-RULE-0044`).
- Write placeholder IDs and run ``curatrix ids fix``; never invent numbers (:need:`XD-RULE-0017`).
- Put build output only under ``build/<area>/`` (:need:`XD-RULE-0040`).
- Every commit ends with ``Co-Authored-By: <agent> <noreply@anthropic.com>`` (:need:`XD-ADR-0044`,
  :need:`XD-RULE-0042`). Everything posted on GitHub ends with the provenance trailer.
- Run ``curatrix check <repo> --stage local`` for every repo you touched before you push.
- Every PR gets a review by another agent before the owner's review (:need:`XD-ADR-0115`).

Skills and checklists
---------------------

The bootstrap links skills and commands from ``xdmod/claude/`` and each active repo's
``claude/`` folder into ``<workspace>/.claude/`` (:need:`XD-ADR-0103`).

.. note:: The SYSMOD step skills, the review checklists and commands such as ``/review-pr`` are
   written in Phase 5.

Pitfalls
--------

- Agents use the owner's login. The limits above are policy, not technical enforcement, in
  iteration 1 (:need:`XD-ADR-0123`).
