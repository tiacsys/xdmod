.. _rules-checks:

Check principles
================

General rules that the hygiene and generated-file checks enforce.

.. xd-rule:: Every check runs locally
   :id: XD-RULE-0032
   :legacy_id: checks 1
   :tags: checks
   :status: valid
   :decided_by: XD-ADR-0040, XD-ADR-0060

   Every check also runs locally, with one command per repo (``curatrix check <repo>``), from the workspace root. CI runs the same command.

.. xd-rule:: Generated files are committed and checked
   :id: XD-RULE-0033
   :legacy_id: checks 2 (CK-D)
   :tags: checks
   :status: valid
   :decided_by: XD-ADR-0032, XD-ADR-0036, XD-ADR-0087, XD-ADR-0100

   Files generated from models and CAD (stubs, model needs, CAD needs, views) are committed. A check regenerates them and fails when the committed copy differs from the source.

.. xd-rule:: Every document builds strict
   :id: XD-RULE-0034
   :legacy_id: checks 2 (CK-A6)
   :tags: checks
   :status: valid
   :decided_by: XD-ADR-0057

   Every document builds with warnings as errors (``-W --keep-going``), and every document reports its problems.

.. xd-rule:: The SysML model parses without errors
   :id: XD-RULE-0035
   :legacy_id: checks 2 (CK-E1)
   :tags: checks
   :status: valid
   :decided_by: XD-ADR-0001, XD-ADR-0058

   The OMG Pilot Implementation parses and resolves the model with 0 errors.

.. xd-rule:: Requirement values agree with the sentence
   :id: XD-RULE-0036
   :legacy_id: checks 2 (CK-E2)
   :tags: checks
   :status: valid
   :decided_by: XD-ADR-0076

   The value fields of a requirement (quantity, unit, min, max, nominal) agree with the number and unit in its sentence.

.. xd-rule:: Requirements use EARS patterns
   :id: XD-RULE-0037
   :legacy_id: checks 2 (CK-E3)
   :tags: checks
   :status: valid
   :decided_by: XD-ADR-0009, XD-ADR-0039

   System and domain requirements follow an EARS sentence pattern that matches their ``ears`` field and use "shall".

.. xd-rule:: Every change shows its impact
   :id: XD-RULE-0038
   :legacy_id: checks 2 (CK-G1)
   :tags: checks
   :status: valid
   :decided_by: XD-ADR-0038, XD-ADR-0121

   A pull request shows which needs it changes and which needs are affected through links (needs-diff against the target branch).

.. xd-rule:: Design files are stored uncompressed
   :id: XD-RULE-0039
   :legacy_id: checks 2 (CK-H1)
   :tags: checks
   :status: valid
   :decided_by: XD-ADR-0056, XD-ADR-0087

   FreeCAD ``.FCStd`` files and drawio diagrams are stored uncompressed, so git can diff them.

.. xd-rule:: Build output only under build/
   :id: XD-RULE-0040
   :legacy_id: checks 2 (CK-H2)
   :tags: checks
   :status: valid
   :decided_by: XD-ADR-0040

   Nothing generated goes into a repo, except the committed generated files. Build output goes to ``build/<area>/`` at the workspace root.

.. xd-rule:: Tools and packages are pinned
   :id: XD-RULE-0041
   :legacy_id: checks 2 (CK-H3)
   :tags: checks
   :status: valid
   :decided_by: XD-ADR-0014

   Every Python package and tool a repo uses has an exact pin (``requirements.txt``, ``tools.yaml``), and generated files record the tool versions that made them.

.. xd-rule:: Agent commits carry a trailer
   :id: XD-RULE-0042
   :legacy_id: checks 2 (CK-H4)
   :tags: checks
   :status: valid
   :decided_by: XD-ADR-0044

   Commits made by agents carry a ``Co-Authored-By`` trailer.

.. xd-rule:: Template copies match the template
   :id: XD-RULE-0043
   :legacy_id: checks 2 (CK-H5)
   :tags: checks
   :status: valid
   :decided_by: XD-ADR-0107

   A file copied from an xdmod template (for example ``scripts/bootstrap.sh`` in the manifest repo) stays equal to the template.

.. xd-rule:: Every tool runs under limits
   :id: XD-RULE-0044
   :legacy_id: checks 3
   :tags: checks
   :status: valid
   :decided_by: XD-ADR-0064

   Every tool runs with a memory limit and a timeout, so a runaway tool is stopped and can't stall the machine.

.. xd-rule:: A repo states the checks it runs
   :id: XD-RULE-0045
   :tags: checks
   :status: valid
   :decided_by: XD-ADR-0125

   A repo's ``checks.yaml`` lists in ``expect:`` exactly the checks it runs. A missing ``checks.yaml``, a check run that plans no check, and an error-level check skipped at the baseline stage all fail.

.. xd-rule:: Pull requests stay small
   :id: XD-RULE-0046
   :tags: checks
   :status: valid
   :decided_by: XD-ADR-0125

   A pull request holds one SYSMOD step or one tool feature. Generated files go with the change that causes them and are not counted.

.. xd-rule:: Documents follow the layout of their registry
   :id: XD-RULE-0067
   :tags: checks
   :status: valid
   :decided_by: XD-ADR-0149

   Every own document of a repo's docs registry has its folder below ``docs/``, and every document folder below ``docs/`` is in the registry. Per-deliverable documents sit in the sub-folder of their kind (``pcbas/pcba-<board>``, ``assemblies/asm-<assembly>``, ``firmware/fw-<name>``); every cable of a repo is in the one ``harnesses`` document.
