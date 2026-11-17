.. _rules-variants:

Variant rules
=============

Rules for the feature model (F), the product models (V) and the traces of variants (T). Iteration 1 checks :need:`XD-RULE-0021`, :need:`XD-RULE-0022` and :need:`XD-RULE-0023` to :need:`XD-RULE-0027`.

.. xd-rule:: A configuration respects its feature tree
   :id: XD-RULE-0021
   :legacy_id: F1
   :tags: variants
   :status: valid
   :decided_by: XD-ADR-0095

   A configuration sets only features of its feature tree, and every feature group keeps its multiplicity.

.. xd-rule:: Feature constraints hold
   :id: XD-RULE-0022
   :legacy_id: F2
   :tags: variants
   :status: valid
   :decided_by: XD-ADR-0095

   Every requires, xor and implies constraint of the feature model holds in every configuration.

.. xd-rule:: One product model per configuration
   :id: XD-RULE-0023
   :legacy_id: V1
   :tags: variants
   :status: valid
   :decided_by: XD-ADR-0095

   Every product model names an existing configuration, and every configuration has exactly one product model.

.. xd-rule:: Every variation is bound
   :id: XD-RULE-0024
   :legacy_id: V2
   :tags: variants
   :status: valid
   :decided_by: XD-ADR-0095

   The product model binds every variation of the 150 % model.

.. xd-rule:: A variation is bound to its own variant
   :id: XD-RULE-0025
   :legacy_id: V3
   :tags: variants
   :status: valid
   :decided_by: XD-ADR-0095

   Each variation is bound to one of that variation's own variants.

.. xd-rule:: The chosen variant is enabled
   :id: XD-RULE-0026
   :legacy_id: V4
   :tags: variants
   :status: valid
   :decided_by: XD-ADR-0095

   The chosen variant is enabled by the configuration: all features it is bound to are chosen. Several bindings on one element mean AND.

.. xd-rule:: Exactly one variant per variation
   :id: XD-RULE-0027
   :legacy_id: V5
   :tags: variants
   :status: valid
   :decided_by: XD-ADR-0095

   Exactly one variant of each variation is enabled per configuration.

.. xd-rule:: Model constraints hold in each product model
   :id: XD-RULE-0028
   :legacy_id: V6
   :tags: variants
   :status: valid
   :decided_by: XD-ADR-0095

   The ``assert constraint`` statements of the 150 % model hold in each product model (simple ``==``, ``implies``, ``and``, ``or`` only).

.. xd-rule:: configs matches the source
   :id: XD-RULE-0029
   :legacy_id: T1
   :tags: variants
   :status: valid
   :decided_by: XD-ADR-0093, XD-ADR-0095

   The ``configs`` of a generated need equals what the model, CAD or build says.

.. xd-rule:: realizes respects configurations
   :id: XD-RULE-0030
   :legacy_id: T2
   :tags: variants
   :status: valid
   :decided_by: XD-ADR-0095

   A ``realizes`` link is allowed only if the source's ``configs`` is a subset of the target's ``configs``.

.. xd-rule:: Coverage counts per configuration
   :id: XD-RULE-0031
   :legacy_id: T3
   :tags: variants
   :status: valid
   :decided_by: XD-ADR-0094, XD-ADR-0095

   A ``TR`` counts for a requirement in a configuration only under the coverage rule: with ``verification_scope: logical`` a result from any configuration counts; with ``verification_scope: config`` a result is needed for each configuration that the requirement's ``where`` selects.

.. xd-rule:: One domain variant per configuration and usage
   :id: XD-RULE-0048
   :tags: variants
   :status: valid
   :decided_by: XD-ADR-0136

   A board or assembly variant is a def in the domain model that specializes the board or assembly def and ``XdDomain::DomainVariant``, with its name in ``variantName``. A dependency from the variant names the configurations (``SYS-CFG``) and the system usages it serves. Every dependency names at least one configuration and one usage. For each board or assembly with variants, and for each system def it realizes, every usage of that def gets exactly one variant in every configuration that configures that def. A def that no configuration configures is in every configuration (as for ``configs``), so each of its usages needs a variant in every configuration; this is intended, and the answer is to let the configurations that contain the def configure it (``dependency from <configuration> to <def>``). An upstream model without any configuration is a finding. Every variant with a name, also one that serves no pair yet, exists by the same name in the KiCad project (``schematic.variants``) or in a FreeCAD configuration table. Each Zephyr board variant maps to a board variant by name: the Zephyr board name is the KiCad project name in lower case with ``-`` as ``_``, a nested variant ``outer/inner`` counts as ``inner``, and a Zephyr board without such a project is ignored. At most two variants per board or assembly in iteration 1; a variant that serves no pair is not reported as unused in iteration 1.
