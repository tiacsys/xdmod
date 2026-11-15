.. _ref-sysml-library:

SysML library
=============

xdmod has a small SysML v2 library, ``xdmod/sysml/XdTrace.sysml`` (package ``XdTrace``). It
holds the metadata that connects the model with the needs and the views. curatrix always loads
it first, before the libraries and files that ``checks.yaml`` names.

Elements
--------

.. list-table::
   :header-rows: 1
   :widths: 15 30 55

   * - Metadata
     - Attributes
     - Use
   * - ``NeedRef``
     - ``needId``, ``status``
     - Marks a generated stub (``concern``, ``requirement``, stakeholder ``part``) as the mirror of
       a need. ``curatrix gen stubs`` writes the stubs; nobody edits them (:need:`XD-ADR-0036`).
   * - ``Trace``
     - ``status`` (``draft``, ``valid``, ``retired``; default ``valid``), ``layer``
       (``context``, ``functional``, ``logical``, ``product``)
     - Trace data of a model element that becomes a need. On a package it is the default for
       every element inside. Generated needs take their status from here (:need:`XD-ADR-0119`).
   * - ``XdView``
     - ``kind``, ``root``, ``layer``, ``direction``, ``show``, ``compartments``
     - Names the kind of a SysML ``view`` (``context``, ``usecases``, ``decomposition``,
       ``interconnection``, ``allocation``, ``variants``, and the SysML v2 standard views
       ``general``, ``actionflow``, ``statetransition``) and its options (:need:`XD-ADR-0085`).
   * - ``See``
     - ``needId``
     - Names the need (decision, rule or check) that explains a model element. Views link the
       element's box to that need's page. Used by the XDMOD self-model.

The need ID of a model element is its **short name**. Only kinds of the model become needs:
``SYS-EL``, ``SYS-IF``, ``SYS-UC``, ``SYS-CFG`` and ``SYS-FEAT``. Views use the reserved kind
``SYS-VIEW``, which is not a need.

Examples
--------

A logical part definition that becomes the need ``SYS-EL-0012``:

.. code-block:: text

   package Logical {
       @XdTrace::Trace { layer = "logical"; }
       part def <'SYS-EL-0012'> JointController;
   }

An element that is retired, so downstream links get the grace period:

.. code-block:: text

   part def <'SYS-EL-0007'> OldDriver {
       @XdTrace::Trace { status = "retired"; }
   }

A generated requirement stub (in ``model/generated/NeedStubs.sysml``):

.. code-block:: text

   requirement <'SYS-REQ-0012'> sys_req_0012 {
       doc /* Follow latency. The system shall ... within 50 ms ... */
       @NeedRef { needId = "SYS-REQ-0012"; status = "valid"; }
       attribute unit : String = "ms";
       attribute max : Real = 50.0;
       frame sys_need_0003;
   }

The ``frame`` line is SYSMOD's link from a requirement to the concern it answers; in the needs
it is the ``refines`` link. A model element satisfies the requirement through the stub:
``satisfy sys_req_0012 by ctrl;``.

A view:

.. code-block:: text

   view <'SYS-VIEW-0001'> jointView {
       @XdView { kind = "interconnection"; root = "RobArm::JointModule"; }
       expose RobArm::JointModule::**;
   }
