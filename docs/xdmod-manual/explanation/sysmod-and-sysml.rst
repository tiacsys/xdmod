.. _expl-sysmod-and-sysml:

SYSMOD and SysML v2
===================

XDMOD uses the SYSMOD method by Tim Weilkiens for systems engineering (:need:`XD-ADR-0007`), and writes the
system model in SysML v2 textual notation (:need:`XD-ADR-0001`).

Why SYSMOD
----------

SYSMOD gives a fixed order of steps and names for their work products: problem statement,
stakeholders, needs, system context, use cases, requirements, and the functional, logical and
product architecture. XDMOD keeps SYSMOD's order and names, so the SYSMOD website
(https://mbse4u.com/sysmod/) and its examples apply directly. The SYSMOD v5 library
(``mbse4u/sysmod-sysmlv2``) is a west project pinned at a commit, not a copy (:need:`XD-ADR-0077`).

Two worlds: text and model
--------------------------

- **Text that people review lives in sphinx-needs**: stakeholder needs, requirements, test
  specifications (:need:`XD-ADR-0005`).
- **Structure and behaviour live in SysML**: context, use cases, architecture, allocations,
  variants.

The two worlds meet through **generated stubs** (:need:`XD-ADR-0036`). A tool reads the needs and writes a
package of read-only stubs: a ``concern`` for each stakeholder need and a ``requirement`` for each
system requirement (:need:`XD-ADR-0057` (b)). Model elements refer to requirements through these stubs,
for example with ``satisfy``. Nobody edits the stubs by hand; a check compares them with the
needs (:need:`XD-CHECK-0015`).

The other way, model elements come back into the documents as generated needs. A model element
becomes a need only when it takes part in a trace link (:need:`XD-ADR-0118`). The definition holds the
ID; its usages are listed in an ``instances`` field (:need:`XD-ADR-0117`). The model extractor writes
``generated/model-needs.json``, which is committed and checked (:need:`XD-CHECK-0017`).

Requirement values
------------------

SYSMOD's requirement boilerplates give requirements machine-readable values. XDMOD keeps the EARS
sentence for people (:need:`XD-ADR-0009`, :need:`XD-ADR-0039`) and adds value fields next to it: ``quantity``,
``unit``, ``min``, ``max``, ``nominal`` (:need:`XD-ADR-0076`). The stub carries them as attributes, so a
model constraint or a test can read them. Checks compare the fields with the sentence
(:need:`XD-RULE-0036`, :need:`XD-RULE-0037`).

Problem statement and objectives
--------------------------------

The problem statement is a stakeholder need with ``category: problem`` (:need:`XD-ADR-0074`). System
objectives are stakeholder needs with ``category: objective`` (:need:`XD-ADR-0075`). Other needs and
objectives link to the problem statement with ``addresses``.

The chain of contexts
---------------------

SYSMOD builds a chain of contexts, each one specialising the one before: idea, specification,
functional, logical and product context. Later contexts inherit actors and ports. XDMOD includes
a short functional architecture: functions realize use cases, and logical elements realize
functions (:need:`XD-ADR-0078`). Each system element (``SYS-EL``) carries a ``layer``: ``context``,
``functional``, ``logical`` or ``product``.

Toolchain
---------

The model is checked with the OMG SysML v2 Pilot Implementation, run through ``jshell``, which
also exports the model as JSON (:need:`XD-ADR-0058`). XDMOD's own Python tools read that JSON. curatrix
stores a compact form of it in ``generated/model.json``, so later steps (views, variants, needs)
need no Java. The model must parse with 0 errors (:need:`XD-RULE-0035`, :need:`XD-CHECK-0016`).

The repo's model files are read as one set, after the libraries, so their order does not matter
(:need:`XD-ADR-0130`).

Domain models
-------------

The EE and ME repos have their own model in ``model/`` (:need:`XD-ADR-0130`). A domain def
specializes the system def it realizes and one base def of the xdmod library ``XdDomain``
(``Pcba``, ``ExternalPart``, ``Cable``, ``Assembly``; ``ConnectorPort``, ``PinSignal``,
``MechanicalPort`` for ports):

.. code-block:: text

   part def <'EE-PCBA-0012'> JointControllerBoard :> RobArmProduct::JointController, XdDomain::Pcba {
       port :>> servoOut : ServoHeader;
   }
   port def <'EE-PORT-0003'> ServoHeader :> RobArmInterfaces::ServoIf, XdDomain::ConnectorPort {
       :>> connector = "JST-XH-3";
       out port :>> pwm : Pin { :>> pin = "1"; :>> net = "SERVO_PWM"; }
   }

The domain repo's ``checks.yaml`` lists the system model files as ``model.libraries`` and the
system repo's committed ``generated/model.json`` as ``model.upstream``. ``curatrix gen model``
emits the ``EE-PCBA``, ``EE-PORT``, ``EE-HAR``, ``ME-ASM`` and ``ME-PORT`` needs and derives their
links from ``:>``: ``realizes`` to a ``SYS-EL``, ``conforms`` to a ``SYS-IF``, and ``part_of`` from a
port def to the board or assembly that has a port of it (:need:`XD-ADR-0132`, :need:`XD-ADR-0133`).
:need:`XD-CHECK-0033` checks conformance (:need:`XD-RULE-0047`). A conjugated port ``~X`` is
redefined by a conjugated ``~Y`` with ``Y :> X``. A domain need gets the ``configs`` of the
``SYS-CFG`` s that configure the system elements it realizes.

A variant of a board or assembly (``part def BoardB :> Board``) has no ID of its own for now: a
specialization between two domain defs makes no trace link, so a variant with an ID would realize
nothing. Variants across levels come with task 5.16 (:need:`XD-ADR-0136`).

Views of the model are SysML ``view`` definitions with an ``@XdView`` annotation (:need:`XD-ADR-0085`).
curatrix renders them as editable ``.drawio.svg`` files (:need:`XD-ADR-0087`).

The step-by-step mapping from SYSMOD steps to files and documents is in
:doc:`../reference/sysmod-mapping`.
