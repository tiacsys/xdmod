.. _howto-add-a-view:

Add a view
==========

Use this guide when you want a diagram of the model in the docs. Views come from the model:
nobody draws model content by hand (:need:`XD-ADR-0002`, :need:`XD-ADR-0085`).

Steps
-----

1. Define the view in ``model/views.sysml`` as a SysML ``view`` with ``@XdView`` metadata. Its
   short name is a ``SYS-VIEW`` ID, a reserved kind that is not a need:

   .. code-block:: text

      view <'SYS-VIEW-NEW-joint'> jointView {
          @XdView { kind = "interconnection"; root = "RobArm::JointModule"; }
          expose RobArm::JointModule::**;
      }

2. Issue the ID and build the view:

   .. code-block:: sh

      curatrix ids fix robarm-syseng
      curatrix gen model robarm-syseng
      curatrix views build robarm-syseng --view jointView

   This writes ``views/jointView.drawio.svg``: the picture with the drawio diagram embedded
   (:need:`XD-ADR-0087`). Commit it.

3. Show it in a document:

   .. code-block:: rst

      .. sysml-view:: /views/jointView.drawio.svg
         :caption: Joint module

   The document's ``conf.py`` must list ``(REPO, "views/*.drawio.svg")`` in ``generated``.

4. Optional: arrange the boxes by hand.

   .. code-block:: sh

      curatrix launch drawio robarm-syseng/views/jointView.drawio.svg
      curatrix views normalize robarm-syseng/views/jointView.drawio.svg

   Layout is not model content. The check compares content, not geometry (:need:`XD-ADR-0057` (a)).

Checks
------

- :need:`XD-CHECK-0018`: content matches the model, the diagram is uncompressed, geometry is sane and
  the picture is fresh. It needs no browser.
- :need:`XD-CHECK-0025`: no compressed diagrams (:need:`XD-RULE-0039`).

.. note:: Iteration 1 builds the view kinds ``interconnection`` and ``decomposition``.
   ``context``, ``usecases``, ``allocation`` and ``variants`` come later. Keeping manual layout
   across rebuilds is iteration 2 (:need:`XD-ADR-0037`). Trace graphs use ``needflow``, not drawio
   (:need:`XD-ADR-0086`).

Pitfalls
--------

- ``views build`` needs node, elkjs and Firefox. They are installed by the bootstrap; it runs
  locally only.
- After saving in drawio, always run ``views normalize``. The pre-commit hook insists.
