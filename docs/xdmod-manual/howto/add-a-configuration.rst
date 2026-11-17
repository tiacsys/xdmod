.. _howto-add-a-configuration:

Add a feature or configuration
==============================

Use this guide when the product line gets a new feature, a new variant at a variation point, or
a new configuration. Variants follow VAMOS in SysML v2 through PLEML (:need:`XD-ADR-0092`).

Steps
-----

1. **Feature.** Add it to the feature model (``features.sysml``) with a ``SYS-FEAT`` short-name
   ID (:need:`XD-ADR-0097`). Add constraints such as ``requires`` or ``xor`` there.
2. **Variant.** In the 150 % product architecture (``product.sysml``), add the variant to its
   ``variation part`` and bind it to features with PLEML feature bindings. Several bindings on
   one element mean AND (:need:`XD-RULE-0026`).
3. **Configuration.** In ``configs.sysml``, add the configuration with a ``SYS-CFG`` ID and
   exactly one product model that binds every variation (:need:`XD-RULE-0023`, :need:`XD-RULE-0024`).
4. **Fields.** Elements that belong only to some configurations carry ``configs``; requirements
   that apply only to some carry ``where`` (:need:`XD-ADR-0093`, :need:`XD-RULE-0005`). Set ``verification_scope``
   on requirements (:need:`XD-ADR-0094`).
5. Issue the IDs and regenerate:

   .. code-block:: sh

      curatrix ids fix robarm-syseng
      curatrix gen model robarm-syseng
      curatrix pleml check robarm-syseng -v

Checks
------

- :need:`XD-CHECK-0009` runs the variant rules :need:`XD-RULE-0021`, :need:`XD-RULE-0022` and :need:`XD-RULE-0023` to :need:`XD-RULE-0027`. All
  are errors.

.. note:: Iteration 1 checks :need:`XD-RULE-0021`, :need:`XD-RULE-0022` and :need:`XD-RULE-0023` to :need:`XD-RULE-0027` only
   (:need:`XD-ADR-0124`). :need:`XD-RULE-0028`, the derivation of ``configs`` (:need:`XD-RULE-0029`), :need:`XD-RULE-0030`,
   :need:`XD-RULE-0031`, the coverage per configuration and the per-configuration pages come later.

Pitfalls
--------

- The Pilot accepts models that break every variant rule. Only ``curatrix pleml check`` finds them.
- A ``realizes`` link from an element that exists in more configurations than its target breaks
  :need:`XD-RULE-0030` once that rule is checked.
