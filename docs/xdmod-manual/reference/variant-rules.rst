.. _ref-variant-rules:

Variant rules
=============

These rules check a variant model: the feature model, the product models of the configurations,
and the trace links between variant elements (:need:`XD-ADR-0095`). All are errors. curatrix checks them
with :need:`XD-CHECK-0009` (``curatrix pleml check`` runs them alone; ``curatrix variants`` without ``list`` is its old name, kept for one release); the SysML Pilot checks none of them.
They run locally, in PR CI of the systems engineering repo, and in the full set. Background:
:doc:`../explanation/variants`.

.. needtable::
   :types: xd-rule
   :tags: variants
   :columns: id;legacy_id as "Rule";title
   :style: table

Notes
-----

- :need:`XD-RULE-0021` and :need:`XD-RULE-0022` check the **feature model**: a configuration sets only features of
  its tree, feature groups keep their multiplicity, and every ``requires``, ``xor`` or
  ``implies`` constraint holds in every configuration.
- :need:`XD-RULE-0023` to :need:`XD-RULE-0027` check the **product models**: one product model per configuration,
  every variation bound to one of its own variants, the chosen variant enabled by the
  configuration, and exactly one variant enabled per variation.
- :need:`XD-RULE-0026`: several feature bindings on one element mean **AND**. PLEML does not say this, so
  it is an XDMOD convention.
- :need:`XD-RULE-0028` checks the ``assert constraint`` statements of the 150 % model in each product model
  (simple ``==``, ``implies``, ``and``, ``or`` only).
- :need:`XD-RULE-0029` to :need:`XD-RULE-0031` check **traces**: ``configs`` of a generated need equals what the
  source says; a ``realizes`` link needs the source's ``configs`` to be a subset of the target's;
  a test result counts for a requirement in a configuration only under the coverage rule
  (:need:`XD-ADR-0094`).

What curatrix checks today
--------------------------

Iteration 1 checks :need:`XD-RULE-0021`, :need:`XD-RULE-0022` and :need:`XD-RULE-0023` to :need:`XD-RULE-0027` (:need:`XD-ADR-0124`).
:need:`XD-RULE-0028`, :need:`XD-RULE-0029`, :need:`XD-RULE-0030` and :need:`XD-RULE-0031` come when the product configuration has real
content.

Example (robot arm): a configuration that chooses both ``prototypeBuild`` and ``productBuild``
breaks :need:`XD-RULE-0022` (the two features are ``xor``). A product model that binds the variation
``controller`` to ``customPcba`` in the prototype configuration breaks :need:`XD-RULE-0026`, because
``customPcba`` is bound to ``productBuild``.
