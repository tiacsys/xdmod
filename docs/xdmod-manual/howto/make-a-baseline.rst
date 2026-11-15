.. _howto-make-a-baseline:

Make a baseline
===============

Use this guide when you want a fixed, released set of repo versions. A **baseline** is a tag
``baseline/vX.Y.Z`` of the manifest repo; a **bundle** is the package of outputs built from it
(:need:`XD-ADR-0034`, :need:`XD-ADR-0047`).

Steps
-----

1. Merge the open bump PR, so the manifest pins the latest ``main`` of every repo.
2. Use a workspace with the ``full`` role, so all CAD content is there (:need:`XD-ADR-0049`).
3. Run the baseline gates for every repo, then the full set:

   .. code-block:: sh

      curatrix check robarm-syseng --stage baseline --base <last-baseline-needs>
      curatrix check robarm-manifest --stage baseline --base <last-baseline-needs>

   ``--base`` points at the ``needs.json`` files of the last baseline.
4. Fix what fails. The baseline stage is stricter than ``local`` and ``pr``:

   - :need:`XD-CHECK-0008`: links to retired needs fail now; the grace period ends (:need:`XD-RULE-0011`,
     :need:`XD-ADR-0068`).
   - :need:`XD-CHECK-0024`: open suspect links fail (:need:`XD-RULE-0014`).
   - :need:`XD-CHECK-0020`: generated files must record the pinned tool versions.
   - :need:`XD-CHECK-0011`: stale evidence doesn't count (:need:`XD-RULE-0013`).
   - :need:`XD-CHECK-0007`: missing verification is a warning in iteration 1 (:need:`XD-ADR-0090`).

5. Tag the manifest repo with an annotated tag and push it:

   .. code-block:: sh

      git -C robarm-manifest tag -a baseline/v0.1.0 -m "baseline v0.1.0"
      git -C robarm-manifest push origin baseline/v0.1.0

6. Create the GitHub release. Its assets are the outputs (docs, later CAM data and firmware).

.. note:: Bundles, CAM output and PDF documents come in iteration 2 (:need:`XD-ADR-0037`). The docs of
   each baseline are hosted next to ``main`` on Pages (:need:`XD-ADR-0048`); multi-version hosting is
   still being built.

Pitfalls
--------

- Tombstones in ``generated/retired-needs.json`` are dropped at the next baseline. Remove the
  links to them before you tag.
- Only a person makes baselines. Agents may prepare the gate results.
