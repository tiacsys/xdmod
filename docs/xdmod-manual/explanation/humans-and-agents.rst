.. _expl-humans-and-agents:

Humans and agents
=================

In XDMOD, AI agents are first-class: they author and review design content the same way human
engineers do, with the same tools (:need:`XD-ADR-0003`). The difference is who may **decide**.

Roles
-----

.. list-table::
   :header-rows: 1
   :widths: 22 25 53

   * - Role
     - Who
     - Does
   * - Owner
     - a person
     - sets goals, makes decisions, reviews and merges every PR, affirms evidence, makes baselines
   * - Domain engineer
     - a person (SE, EE, ME, SW, integration)
     - authors and reviews content in their domain; affirms suspect links in their domain
   * - Agent author
     - an AI agent
     - authors content on a branch (requirements, model, CAD through scripts, code, tests,
       docs) and opens PRs
   * - Agent reviewer
     - an AI agent, not the author
     - first-pass review of a PR against checklists; posts findings as PR comments
   * - Coordinator agent
     - the agent the owner talks to
     - plans, splits work, starts other agents, gathers results, keeps the plan and the
       decision log

Propose versus affirm
---------------------

Agents analyse suspect links and prepare affirmations and verdicts. But **only a person's commit
counts** as an affirmation or a verdict (:need:`XD-ADR-0051`). The same holds for merging: the owner's
review and merge is the approval (:need:`XD-ADR-0044`).

What agents may and may not do
------------------------------

.. list-table::
   :header-rows: 1
   :widths: 50 50

   * - Agents may
     - Agents may not
   * - create branches, commit, push to their own branches
     - merge PRs, push to ``main``, force-push to other people's branches
   * - open PRs and issues and comment on them, with the provenance trailer (:need:`XD-ADR-0065`)
     - change repo or org settings, rulesets or secrets, or create or delete repos, without the
       owner's approval of the concrete action list (:need:`XD-ADR-0112`)
   * - add ``Co-Authored-By``, and ``Signed-off-by`` in the owner's name where a repo requires
       it (:need:`XD-ADR-0108`)
     - affirm suspect links or give manual verdicts; they only propose them (:need:`XD-ADR-0051`)
   * - run any tool through curatrix, under limits (:need:`XD-ADR-0064`)
     - run tools without limits, install system packages, use sudo
   * - record HIL evidence from ``main`` or baseline commits (:need:`XD-ADR-0053`)
     - record evidence from PR branches as anything but previews
   * - post freely in the project's own repos and in xdmod
     - post on other repos (doc engine, tools, upstream projects) before the owner approved the
       draft (:need:`XD-ADR-0113`)

These limits are policy in iteration 1: agents work under the owner's GitHub account
(:need:`XD-ADR-0123`).

Provenance
----------

Every agent commit carries a ``Co-Authored-By`` trailer (:need:`XD-ADR-0044`, :need:`XD-RULE-0042`). Everything an
agent posts on GitHub (issues, comments, PR texts, reviews) ends with the line
``🤖 Generated with [Claude Code](https://claude.com/claude-code)`` (:need:`XD-ADR-0065`). The check
:need:`XD-CHECK-0028` warns about commits without the trailer.

Review by another agent
-----------------------

Every pull request in the project repos and in xdmod gets a review by an agent other than the
author, before the owner's review (:need:`XD-ADR-0115`).

Working in parallel
-------------------

Several agents can work at the same time. Two agents never edit the same repo checkout at once.
An agent that changes repos works in its own **git worktrees** under
``<ws>/.worktrees/<branch>/<repo>``, made with ``curatrix work start`` (:need:`XD-ADR-0114`). Shared,
read-only parts (Zephyr, libraries, ``.venv``) are not duplicated.

Each agent gets a short brief: its goal, the decisions that bind it, the files to read, its
output paths, and what it must not do. It returns a short report; the coordinator checks the
claims that matter before passing them on.

Agent material in the repos
---------------------------

Each repo has a ``claude/`` folder with its own rules, skills and pitfalls (:need:`XD-ADR-0062`). xdmod
holds the launch ``CLAUDE.md`` for the workspace root, and shared skills, commands and checklists.
The bootstrap copies the launch file to the root and links all skills and commands into
``<workspace>/.claude/`` (:need:`XD-ADR-0103`). See :doc:`../reference/repo-layouts`.
