.. _expl-multi-repo:

Many repos, one workspace
=========================

An XDMOD project lives in several git repos: one per engineering domain, one for integration,
one manifest, and the framework itself. They are managed together as one **west workspace**
(:need:`XD-ADR-0006`). The diagrams *workspaceRepos* and *workspaceInterconnection* in
:ref:`expl-framework-model` show the repos, their files and what flows between them.

Why several repos
-----------------

Each domain has its own tools, reviewers and pace. Separate repos keep their histories, checks
and permissions apart, while the trace links still connect them. Example (robot arm): the repos
``robarm-syseng``, ``robarm-ee``, ``robarm-me``, ``robarm-sw`` and ``robarm-integration``, with
``robarm-manifest`` as the manifest and ``xdmod`` as the framework (:need:`XD-ADR-0042`).

- The **systems engineering** repo holds needs, requirements, the SysML model and views. It is
  upstream of every domain.
- Each **domain** repo (EE, ME, SW) holds its requirements, design and domain tests.
- The **integration** repo holds the system and integration tests, the HIL setups and the
  orphan evidence branch (:need:`XD-ADR-0066`). A test that verifies a system requirement or an interface
  lives there, even if it touches one domain only (:need:`XD-ADR-0104`).
- The **manifest** repo pins every other repo (:need:`XD-ADR-0011`), builds the full document set, and
  holds the baselines.
- **xdmod** is in every workspace that uses the framework (:need:`XD-ADR-0059`).

The manifest pins everything
----------------------------

The manifest repo is the **only** place that pins revisions (:need:`XD-ADR-0033`). Framework and design
repos and libraries are pinned by commit SHA; third-party trees such as Zephyr may be pinned by
tag. No other repo has its own ``west.yml``.

The manifest is split into **submanifests**, one per area, and its projects carry **groups**
(:need:`XD-ADR-0079`). Each role checks out only what it needs, through west's group filter. The default
filter is minimal: framework, systems engineering and Zephyr (:need:`XD-ADR-0084`). A role always gets its
upstream repos and the framework. The integration role gets everything except the big CAD
libraries (:need:`XD-ADR-0082`). Component libraries are pinned west projects too, isolated from any
user-global setup (:need:`XD-ADR-0080`).

West rule to remember: a project is active as soon as **one** of its groups is enabled. So a big
library carries only its own group, never also the domain group.

One workspace root
------------------

The workspace root is the west topdir (:need:`XD-ADR-0061`). It holds ``.west/``, ``.venv/``, ``build/``
and all repos. Design repos sit at the top level; dependencies go under ``tools/`` and ``libs/``
(:need:`XD-ADR-0083`). Every command runs from the root (:need:`XD-ADR-0060`). See :doc:`../reference/workspace`.

A change across repos
---------------------

1. **One branch name** in every repo the change touches (:need:`XD-ADR-0045`).
2. **One pull request per repo.** Each lists its sibling PRs.
3. **PR CI** checks each repo against its siblings. For each sibling it takes, in this order: a
   branch with the same name; the repo's ``main`` if the manifest pin is an ancestor of it; the
   manifest pin (:need:`XD-ADR-0116`). So downstream PRs see upstream changes that are merged but not yet
   bumped.
4. **Merge upstream first**: systems engineering, then the domains, then integration. Framework
   changes merge before the repos that use them. Every PR is rebase-merged (:need:`XD-ADR-0043`).
5. **Bump bot.** A scheduled job in the manifest repo compares each repo's ``main`` with its pin
   and opens or updates one bump PR (:need:`XD-ADR-0054`, :need:`XD-ADR-0081`). Because a PR opened with the job's
   own token does not trigger CI, the job builds the full set itself and reports on the PR.

Baselines and bundles
---------------------

A **baseline** is a tag ``baseline/vX.Y.Z`` of the manifest repo: a fixed set of repo versions
(:need:`XD-ADR-0034`, :need:`XD-ADR-0047`). A **bundle** is the package of outputs built from one baseline: docs,
CAM data, firmware, HIL results. Bundles come in iteration 2 (:need:`XD-ADR-0037`).

Before a baseline is tagged, the gates run: no links to retired needs (:need:`XD-RULE-0011`), no open suspect
links (:need:`XD-RULE-0014`), and a full local build with CAD content. The documentation is published on
GitHub Pages of the manifest repo, with ``main`` as "latest" and one folder per baseline
(:need:`XD-ADR-0048`).

Documents across repos
----------------------

Each repo has its own zdocs registry (:need:`XD-ADR-0021`), which also builds its upstream documents
locally from the west checkout, so links into upstream needs resolve (:need:`XD-ADR-0029`). The manifest
repo's registry builds the full linked set. The XDMOD manual is part of that set; project
documents link to the manual, but the manual never links to a project (:need:`XD-ADR-0101`).
