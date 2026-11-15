.. _rules-ids:

ID rules
========

Rules for IDs and the ledger.

.. xd-rule:: An ID matches the scheme and its need type
   :id: XD-RULE-0015
   :legacy_id: id-scheme 6.1
   :tags: ids
   :status: valid
   :decided_by: XD-ADR-0071, XD-ADR-0109

   Every ID matches ``<DOMAIN>-<KIND>-<NNNN>`` (or the test result form ``TR-<test case ID>-<run>``), and its kind matches the need type.

.. xd-rule:: IDs are unique
   :id: XD-RULE-0016
   :legacy_id: id-scheme 6.2
   :tags: ids
   :status: valid
   :decided_by: XD-ADR-0071, XD-ADR-0122

   Each ID is unique within its repo and across the whole workspace.

.. xd-rule:: No placeholders on main
   :id: XD-RULE-0017
   :legacy_id: id-scheme 6.3
   :tags: ids
   :status: valid
   :decided_by: XD-ADR-0071

   Placeholder IDs (``<KIND>-NEW-<tag>``) are replaced by real IDs with ``curatrix ids fix`` before a change is merged.

.. xd-rule:: The ledger is never behind the sources
   :id: XD-RULE-0018
   :legacy_id: id-scheme 6.4
   :tags: ids
   :status: valid
   :decided_by: XD-ADR-0122

   Every ID of a kind that a repo owns appears in that repo's ledger ``ids.yaml``.

.. xd-rule:: Test report IDs are mapped to TR IDs
   :id: XD-RULE-0019
   :legacy_id: id-scheme 6.5
   :tags: ids
   :status: valid
   :decided_by: XD-ADR-0071

   sphinx-test-reports makes lowercase ``tr_`` IDs. The run-record extractor maps them to ``TR-…`` IDs.

.. xd-rule:: IDs are never reused; retire before you delete
   :id: XD-RULE-0020
   :legacy_id: id-scheme 4
   :tags: ids
   :status: valid
   :decided_by: XD-ADR-0057, XD-ADR-0119

   A removed need is first marked ``status: retired``, and its ID is never issued again. A generated need whose source element was deleted without retiring keeps a tombstone in ``generated/retired-needs.json`` until the next baseline.
