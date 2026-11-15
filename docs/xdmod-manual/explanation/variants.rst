.. _expl-variants:

Variants
========

A project often builds more than one product from one design: a prototype and a product, a
small and a large version. XDMOD models these as **variants of one product line**, following
VAMOS (:need:`XD-ADR-0092`).

VAMOS and PLEML
---------------

VAMOS, by Tim Weilkiens, is a variant method for SysML v1. XDMOD uses **PLEML** (MBSE4U, MIT
licence), its SysML v2 successor. PLEML is a west project pinned at a commit, next to the SYSMOD
library. SYSMOD v5 itself has no variant concept.

The parts of a variant model:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Part
     - What it is
   * - Core
     - The variant-free functional and logical architecture.
   * - Feature model
     - Features and feature groups, with constraints such as ``requires`` and ``xor``.
   * - 150 % product architecture
     - The product architecture with **variation points**. Each variation has variants, and
       each variant is bound to features.
   * - Configurations
     - A choice of features. Each configuration has exactly one product model.

Example (robot arm): the feature group ``buildKind`` has the features ``prototypeBuild`` and
``productBuild``. The variation ``controller`` has the variants ``nucleoBreakouts`` (bound to
``prototypeBuild``) and ``customPcba`` (bound to ``productBuild``). The configurations are
``prototype`` (``SYS-CFG-0001``) and ``product`` (``SYS-CFG-0002``).

Variant fields on needs
-----------------------

Needs carry their variant information in fields (:need:`XD-ADR-0093`, :need:`XD-RULE-0005`):

- ``configs`` on product-layer system elements, domain design elements and test cases: the
  configurations the element belongs to. Empty means all.
- ``where`` on requirements: a feature condition, matching the EARS "Where <feature>, the system
  shall ..." pattern. Empty means all configurations.
- ``verification_scope`` on requirements: ``logical`` or ``config`` (see below).
- ``config`` on test results: the one configuration the run was made on.

Configurations and features have their own ID kinds, ``SYS-CFG`` and ``SYS-FEAT``
(:need:`XD-ADR-0097`). They are written as SysML short names.

Why own checks
--------------

The SysML Pilot checks none of the variant rules: in a test it accepted every planted error. So
curatrix checks them itself (:need:`XD-ADR-0095`, :need:`XD-CHECK-0009`). The rules cover the feature model
(:need:`XD-RULE-0021`, :need:`XD-RULE-0022`), the product models (:need:`XD-RULE-0023` to :need:`XD-RULE-0028`) and the trace links
(:need:`XD-RULE-0029` to :need:`XD-RULE-0031`). They are listed in :doc:`../reference/variant-rules`. Several feature
bindings on one element mean AND (:need:`XD-RULE-0026`); PLEML does not say this, so it is an XDMOD
convention.

Coverage per configuration
--------------------------

The coverage report is a requirement × configuration matrix (:need:`XD-ADR-0094`). A cell is covered
when:

- ``verification_scope: logical``: at least one test result from **any** configuration verifies
  the requirement. Example: SW logic tested on the prototype also counts for the product.
- ``verification_scope: config``: at least one result with ``config`` = C verifies it, for each
  configuration C that the requirement's ``where`` selects.

The verification rule :need:`XD-RULE-0009` applies per cell.

One document set
----------------

There is **one variant-aware document set** (:need:`XD-ADR-0096`), not one set per variant. Documents show
the 150 % content with configuration badges. A generated page per configuration lists the
elements and requirements that apply to it, and its column of the coverage matrix.

What iteration 1 covers
-----------------------

Iteration 1 starts with one feature group and the rules :need:`XD-RULE-0021`, :need:`XD-RULE-0022` and :need:`XD-RULE-0023` to
:need:`XD-RULE-0027` (:need:`XD-ADR-0124`). The rule :need:`XD-RULE-0028`, the derivation of ``configs`` for :need:`XD-RULE-0029`, and
the pages per configuration come later.
