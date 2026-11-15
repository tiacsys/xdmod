.. _adr-workflow:

Workflow and agents
===================

Branches, merging, reviews, and what agents may do.

.. xd-adr:: Agents are first-class
   :id: XD-ADR-0003
   :legacy_id: D3
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **Agents are first-class**: they edit and review design content the same way human engineers do.

.. xd-adr:: Trunk-based merging with rebase
   :id: XD-ADR-0043
   :legacy_id: D50
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **Merging:** trunk-based on ``main``. Every change goes through a PR, required checks must pass, and PRs are **rebase-merged** (linear history). Enforced with org rulesets.

.. xd-adr:: Agents work under the user's account
   :id: XD-ADR-0044
   :legacy_id: D51
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **Agent identity:** agents work under the user's account, and their commits carry a ``Co-Authored-By`` trailer. GitHub does not let you approve your own PR, so rulesets **require passing checks but no approval count**. The user's review and merge is the approval.

.. xd-adr:: One branch name across repos
   :id: XD-ADR-0045
   :legacy_id: D52
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **Changes across repos:** the same branch name is used in every repo the change touches. CI checks out sibling repos at that branch if it exists, otherwise at the manifest pin. Upstream merges first, then one manifest PR bumps all pins.

.. xd-adr:: Planning with plan.md, issues and PRs
   :id: XD-ADR-0046
   :legacy_id: D53
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **Planning:** ``plan.md`` stays the master plan. Tasks become GitHub issues in the repo where the work happens, and PRs close them. An org Projects board is optional.

.. xd-adr:: Only a human's commit affirms
   :id: XD-ADR-0051
   :legacy_id: D58
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0003

   **X3 Agents and evidence:** agents analyse suspect links and prepare affirmations and verdicts, but **only a human's commit counts** as an affirmation or verdict. Refines :need:`XD-ADR-0003`.

.. xd-adr:: Provenance trailer on GitHub posts
   :id: XD-ADR-0065
   :legacy_id: D72
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0044

   **Provenance on GitHub:** everything an agent posts on the user's behalf (issues, comments, PR descriptions, reviews, release notes) ends with the trailer ``🤖 Generated with [Claude Code](https://claude.com/claude-code)``. Commits keep the ``Co-Authored-By`` trailer. Extends :need:`XD-ADR-0044`.

.. xd-adr:: Sign-off by agents
   :id: XD-ADR-0108
   :legacy_id: D119
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0044

   **Sign-off:** agents may add ``Signed-off-by`` in the user's name where a repo's convention requires it, always together with the ``Co-Authored-By`` trailer. The user certifies by reviewing and merging.

.. xd-adr:: GitHub admin by agents only after approval
   :id: XD-ADR-0112
   :legacy_id: D123
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **GitHub admin by agents** (repos, rulesets, labels, Pages settings) only after the owner approves each concrete action list.

.. xd-adr:: Posting approval outside our repos
   :id: XD-ADR-0113
   :legacy_id: D124
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **Posting approval:** agents post freely in robarm-* and xdmod (with the trailer). On other repos (zdocs, affirmatrix, upstream projects), they draft first and post after the owner's approval.

.. xd-adr:: Parallel agents work in git worktrees
   :id: XD-ADR-0114
   :legacy_id: D125
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **Parallel agents work in git worktrees** under ``<ws>/.worktrees/<branch>/<repo>`` (``curatrix work start/done``). Shared parts aren't duplicated, and builds go to ``build/<branch>/``.

.. xd-adr:: Every PR gets an agent review
   :id: XD-ADR-0115
   :legacy_id: D126
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **Every PR in robarm-* and xdmod gets an agent review** (by an agent other than the author, ``/review-pr``) before the owner's review.

.. xd-adr:: Agent limits are policy only in iteration 1
   :id: XD-ADR-0123
   :legacy_id: D134
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0044

   **Agent limits stay policy only in iteration 1** (agents use the owner's login, :need:`XD-ADR-0044`). Technical enforcement (a GitHub App identity or signed commits) is in the iteration 2 backlog.
