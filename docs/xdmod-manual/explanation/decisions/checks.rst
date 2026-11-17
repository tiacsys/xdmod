.. _adr-checks:

Checks, CI and evidence
=======================

Where checks run, CI, tool limits, generated files and test evidence.

.. xd-adr:: GitHub, GitHub Actions and pull requests
   :id: XD-ADR-0012
   :legacy_id: D15
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   All repos are hosted on **GitHub**. CI runs on GitHub Actions; changes are reviewed through pull requests.

.. xd-adr:: Tool versions of the reference machine
   :id: XD-ADR-0014
   :legacy_id: D19
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   We use the tool versions **installed on this machine**. A Docker image with all tools comes later.

.. xd-adr:: Generated outputs are built by CI
   :id: XD-ADR-0025
   :legacy_id: D31
   :date: 2026-11-14
   :decision_status: revised
   :status: valid

   Generated outputs are **built by CI**: workflow artifacts on pull requests, release assets on tags. Revised by :need:`XD-ADR-0032`: drawio files are committed.

.. xd-adr:: drawio files are committed and checked
   :id: XD-ADR-0032
   :legacy_id: D38
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid
   :revises: XD-ADR-0025

   **Drawio files are committed**, and CI checks that they match the model. **HIL test results** are packaged with the user's bundling tool, the same way as design outputs.

.. xd-adr:: Study affirmatrix for suspect links
   :id: XD-ADR-0038
   :legacy_id: D44
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **Suspect/stale link detection:** study the user's tool **affirmatrix** (https://github.com/tiacsys/affirmatrix) in Phase 1.

.. xd-adr:: Every check also runs locally
   :id: XD-ADR-0040
   :legacy_id: D46
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **Every check also runs locally** (one command per repo), not only in GitHub Actions.

.. xd-adr:: GitHub CI builds docs and runs trace checks only
   :id: XD-ADR-0041
   :legacy_id: D47
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   In iteration 1, **GitHub CI only builds docs and runs trace checks**. Checks that need KiCad, FreeCAD or the Zephyr SDK run locally until the Docker image exists.

.. xd-adr:: CI runs without CAD content
   :id: XD-ADR-0049
   :legacy_id: D56
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0041

   **X1 CI scope:** in iteration 1, GitHub CI builds docs and traces **without CAD content**, so its trace graph is partial. Full builds that include KiCad and FreeCAD content run only through the local one-command check (:need:`XD-ADR-0040`). Refines :need:`XD-ADR-0041`.

.. xd-adr:: HIL evidence on an orphan branch
   :id: XD-ADR-0050
   :legacy_id: D57
   :date: 2026-11-14
   :decision_status: revised
   :status: valid

   **X2 HIL evidence:** HIL run records (``sha256(zephyr.bin)``, manifest repo SHAs, Twister JUnit/JSON, evidence rule: clean tree and pinned versions) live on **their own orphan branch in robarm-sw**, the same idea as affirmatrix's ``case`` branch. The test report reads them from there. Revised by :need:`XD-ADR-0066`: the evidence branch lives in robarm-integration.

.. xd-adr:: affirmatrix is adapted through upstream issues and PRs
   :id: XD-ADR-0052
   :legacy_id: D59
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **X4 Suspect links:** we use **affirmatrix** and adapt it through **issues and PRs on tiacsys/affirmatrix**. Needed changes: read imported/upstream needs, accept open link types from our table (:need:`XD-ADR-0030`), take input from our needs.json extractors.

.. xd-adr:: Evidence only from main or baseline commits
   :id: XD-ADR-0053
   :legacy_id: D60
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **X5 SHAs:** rebase merge stays. **Evidence is recorded only against commits on ``main`` or baseline tags**, after merge. Runs on PR branches are previews and are not kept as evidence.

.. xd-adr:: A bump bot for manifest pins
   :id: XD-ADR-0054
   :legacy_id: D61
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0045

   **X6 Cross-repo flow:** :need:`XD-ADR-0045` stays for PR CI. In addition, a **bump bot**: each merge to ``main`` in a robarm repo opens or updates a manifest bump PR, and that PR's CI builds the full set.

.. xd-adr:: FreeCAD files uncompressed, with textconv and a review report
   :id: XD-ADR-0056
   :legacy_id: D63
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0035

   **X8 FreeCAD storage** (resolves :need:`XD-ADR-0035`): ``.FCStd`` saved **uncompressed**, a git **textconv** for readable diffs, and a **review report** (drawing SVG, image diff, changed parameters and trace IDs) built locally and attached to the PR.

.. xd-adr:: A memory limit and a timeout for every tool
   :id: XD-ADR-0064
   :legacy_id: D71
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **Every tool runs with a memory limit and a timeout**, for humans' scripts and all agents alike. The limits are set per tool and use. Swap is off inside the limit, so a runaway tool is killed and can't stall the machine or block agents. Interim wrapper: ``.venv/bin/xd-limit`` (systemd user scope + ``timeout``); xdmod's command layer takes this over (3.13).

.. xd-adr:: The bump bot is a scheduled poll
   :id: XD-ADR-0081
   :legacy_id: D89
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0054

   **Bump bot = a scheduled poll** in robarm-manifest (e.g. every 30 min, plus manual). It uses its own ``GITHUB_TOKEN``, so no extra secret is needed. Because PRs opened with that token don't trigger CI, the job builds the full set itself and reports on the bump PR. Refines :need:`XD-ADR-0054`.

.. xd-adr:: One framework tool: curatrix
   :id: XD-ADR-0089
   :legacy_id: D98
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0042

   **One xdmod tool, ``curatrix``,** with subcommands ``check``, ``gen``, ``ids``, ``views`` and later ``bootstrap``/``launch``. Refines :need:`XD-ADR-0042` for the framework's own tooling.

.. xd-adr:: Verification coverage is a warning in iteration 1
   :id: XD-ADR-0090
   :legacy_id: D99
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **Verification coverage** (:need:`XD-CHECK-0007`, rule :need:`XD-RULE-0009`) is a warning in iteration 1, and an error at the baseline gate from iteration 2.

.. xd-adr:: Pre-commit hooks
   :id: XD-ADR-0091
   :legacy_id: D100
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid

   **Pre-commit hooks** (normalizers, ID placeholders, fast checks) are installed by the bootstrap in every active repo.

.. xd-adr:: CAD-derived needs are committed
   :id: XD-ADR-0100
   :legacy_id: D110
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0049

   **CAD-derived needs are committed** (``generated/cad-needs.json``, stable and sorted), generated and checked locally and at the baseline. CI imports them, so CI sees the full trace graph. Refines :need:`XD-ADR-0049`.

.. xd-adr:: The command layer is only curatrix
   :id: XD-ADR-0105
   :legacy_id: D116
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0089

   The command layer is **only ``curatrix``**; there is no west extension alias.

.. xd-adr:: GUI tools get a memory limit only
   :id: XD-ADR-0106
   :legacy_id: D117
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0064

   **GUI tools** started by ``curatrix launch`` get a **memory limit only** (8 GB, no swap), no timeout. Refines :need:`XD-ADR-0064`.

.. xd-adr:: PR CI sibling resolution
   :id: XD-ADR-0116
   :legacy_id: D127
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0045

   **PR CI sibling resolution:** same-name branch → the repo's ``main`` if the manifest pin is an ancestor of it → manifest pin. So downstream PRs see upstream changes merged but not yet bumped. Refines :need:`XD-ADR-0045`.

.. xd-adr:: Evidence validity
   :id: XD-ADR-0120
   :legacy_id: D131
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0053

   **Evidence validity:** a test result counts only if its recorded SHAs (and firmware sha256) match the current pins on ``main`` or the baseline being built; otherwise it's ``stale``. Each baseline records the evidence branch SHA. Analysis, inspection and demonstration evidence are authored `TR`s with ``method`` and reviewer, under the same rule.

.. xd-adr:: Suspect links before affirmatrix
   :id: XD-ADR-0121
   :legacy_id: D132
   :date: 2026-11-14
   :decision_status: accepted
   :status: valid
   :refines: XD-ADR-0052

   **Suspect links before affirmatrix:** "last confirmed" = the last baseline's ``needs.json`` (for PRs: ``main``'s). Hashed fields: title, content, status, value fields, links.

.. xd-adr:: Checks that bite
   :id: XD-ADR-0125
   :date: 2026-11-17
   :decision_status: accepted
   :status: valid

   **A check run passes only if it checked something** (Phase 4 review P4-4, P4-14; plan Phase 5, task 5.1). A missing ``checks.yaml`` and an empty plan fail. Each repo lists the checks it runs in ``expect:``, so a lost section is an error (CK-H6); ``curatrix check`` prints the checks that are off and why. An error-level check that is skipped at the baseline stage fails. Failures of git and west are reported, never treated as "nothing found". A pull request gets a warning when it changes more than 600 hand-written lines or 15 files against its base (CK-H7): one SYSMOD step or one tool feature per PR.
