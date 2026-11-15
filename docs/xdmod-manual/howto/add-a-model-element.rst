.. _howto-add-a-model-element:

Add a model element
===================

Use this guide when you add a SysML element that takes part in a trace link: a function, a
logical or product part, an interface, a use case, a feature or a configuration.

Only model elements with trace links become needs (:need:`XD-ADR-0118`). Elements without links stay in
the model only and need no ID.

Steps
-----

1. Pick the file of the SYSMOD step (:need:`XD-ADR-0007`): for example ``functional.sysml`` (10a),
   ``logical.sysml`` (10b), ``product.sysml`` (10c), ``features.sysml`` and ``configs.sysml``
   (10d). The mapping is in the SYSMOD mapping reference.
2. Give the **definition** a short-name placeholder ID. The definition holds the ID; its usages
   are listed in the need's ``instances`` field (:need:`XD-ADR-0117`).

   .. code-block:: text

      @XdTrace::Trace { layer = "logical"; }
      part def <'SYS-EL-NEW-ctrl'> JointController { ... }

3. Set the layer with ``@XdTrace::Trace`` on the element or its package (``context``,
   ``functional``, ``logical``, ``product``, :need:`XD-ADR-0078`).
4. Add the links:

   - ``satisfy sys_req_0012 by ctrl;`` makes the element satisfy ``SYS-REQ-0012``, through the
     generated requirement stub.
   - ``allocate <T> to <S>;`` between usages makes ``S`` realize ``T``. The concrete side holds
     the link (:need:`XD-RULE-0004`).

5. Issue the ID and regenerate the model files:

   .. code-block:: sh

      curatrix ids fix robarm-syseng
      curatrix gen model robarm-syseng

   This writes ``generated/model.json`` and ``generated/model-needs.json``. Commit both.

Checks
------

.. code-block:: sh

   curatrix check robarm-syseng --stage local

- :need:`XD-CHECK-0016`: the Pilot parses the model with 0 errors (:need:`XD-RULE-0035`).
- :need:`XD-CHECK-0017`: the committed model files match the model (:need:`XD-RULE-0033`).
- :need:`XD-CHECK-0004`: a product-layer element realizes or satisfies something (:need:`XD-RULE-0010`).
- :need:`XD-CHECK-0018`: views that show the element are up to date (see :doc:`add-a-view`).

Pitfalls
--------

- :need:`XD-CHECK-0016` and :need:`XD-CHECK-0017` need Java and the Pilot. Run ``curatrix doctor`` if they fail to start.
- A link that is not ``satisfy``, ``allocate`` or ``dependency`` between known kinds is a finding.
- If you delete a traced element without setting ``status = "retired"`` first, curatrix keeps a
  tombstone in ``generated/retired-needs.json`` until the next baseline (:need:`XD-ADR-0119`,
  :need:`XD-CHECK-0012`).
