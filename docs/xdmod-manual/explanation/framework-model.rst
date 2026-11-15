.. _expl-framework-model:

XDMOD as a SysML model
======================

XDMOD describes itself in SysML v2, the same way a project describes its system
(:need:`XD-ADR-0001`). The model lives in ``xdmod/model/``. Each diagram on this page is a
**view** of that model: a SysML ``view`` in ``xdmod/model/views.sysml``, rendered by
``curatrix views build xdmod`` into ``xdmod/views/<view>.drawio.svg`` (:need:`XD-ADR-0085`,
:need:`XD-ADR-0087`). Nobody draws these pictures by hand. To change one, change the model,
rebuild the views and commit both. ``curatrix check xdmod`` fails when a view no longer matches
the model (:need:`XD-RULE-0033`).

The diagrams use the SysML v2 graphical notation where drawio has a matching shape. Each
diagram has a legend. In short:

- A sharp box is a **definition** and a rounded box is a **usage**. The keyword in guillemets
  (``«item def»``) names the kind of element, and the short name in angle brackets (``<sys-req>``)
  comes before the name.
- A **hollow triangle** points from a specialised type to its general type.
- A **filled diamond** sits on the owner of a composite feature (a part or an item it contains).
- A **hollow diamond with an open arrow** is a reference feature. The diamond end holds the
  reference, and the label gives its name and multiplicity.
- Boxes with a decision, rule or check behind them are links: click them to open that need.

The model is checked against the configuration it describes. A test compares the need types and
link types in package ``XdmodNeeds`` with ``needs/needs_config.toml``
(:need:`XD-RULE-0007`), so the trace diagrams below always show what sphinx-needs enforces.

Domains, repos and files
------------------------

A workspace holds xdmod, the manifest repo and one repo per domain (:need:`XD-ADR-0006`,
:need:`XD-ADR-0061`). Every repo has the same configuration files. Each domain repo adds its
own documents and design files. The ``domain`` value is the first part of every ID in that repo
(:need:`XD-ADR-0071`).

.. sysml-view:: /views/workspaceRepos.drawio.svg
   :caption: workspaceRepos: the repos of a workspace, their domains, documents and design files
             (general view)

Needs flow from the abstract side to the concrete side: the systems repo exports its needs, and
the domain repos and the integration repo import them as upstream documents
(:need:`XD-ADR-0021`). Trace links point back the other way (:need:`XD-RULE-0001`). The manifest
pins every repo (:need:`XD-ADR-0033`) and builds the full set.

.. sysml-view:: /views/workspaceInterconnection.drawio.svg
   :caption: workspaceInterconnection: needs, pins and the framework between the repos
             (interconnection view)

XDMOD knows two kinds of files. **Source** files are written by people and agents. **Generated**
files are written by curatrix, committed, and compared by ``curatrix check``
(:need:`XD-ADR-0100`).

.. sysml-view:: /views/artifactKinds.drawio.svg
   :caption: artifactKinds: source and generated files (general view)

Need types
----------

Every need type is an ``item def`` whose short name is its sphinx-needs directive. The abstract
types group them by their place in the V. ``Need`` declares every link type once. Each need type
then narrows the link types it holds to the target types it may point to
(:need:`XD-RULE-0002`).

.. sysml-view:: /views/needKinds.drawio.svg
   :caption: needKinds: all need types, grouped by their place in the V (general view)

Trace links
-----------

The concrete side holds the link (:need:`XD-ADR-0004`, :need:`XD-RULE-0001`). In these
diagrams the concrete types stand on the right and the abstract types on the left, so every
reference points from right to left, as in the V. ``[1..*]`` marks a link that is required
(:need:`XD-RULE-0008`, :need:`XD-RULE-0009`).

.. sysml-view:: /views/traceSystem.drawio.svg
   :caption: traceSystem: systems engineering and integration tests (general view)

.. sysml-view:: /views/traceSoftware.drawio.svg
   :caption: traceSoftware: the software domain down to code units and tests (general view)

.. sysml-view:: /views/traceHardware.drawio.svg
   :caption: traceHardware: the electrical and mechanical domains (general view)

Test results point to the test case they come from. A run result also carries the firmware hash
and the pinned SHAs (:need:`XD-RULE-0012`).

.. sysml-view:: /views/traceResults.drawio.svg
   :caption: traceResults: test results and test reports (general view)

Decisions, rules and checks are needs too (:need:`XD-ADR-0109`, :need:`XD-ADR-0110`). A rule
is decided by a decision, and a check enforces a rule. A project decision follows a framework
decision.

.. sysml-view:: /views/traceGovernance.drawio.svg
   :caption: traceGovernance: decisions, rules and checks (general view)

Build and check
---------------

The same steps run locally and in CI (:need:`XD-ADR-0040`, :need:`XD-RULE-0032`). Each action
has its inputs and outputs as pins, and the thick arrows show which file goes where. Only a
passing check leads to publishing.

.. sysml-view:: /views/buildAndCheck.drawio.svg
   :caption: buildAndCheck: from sources to needs, views, documents and check results
             (action flow view)

The change process
------------------

A change runs on one branch name in every repo it touches (:need:`XD-ADR-0045`), is checked
locally, reviewed by a second agent (:need:`XD-ADR-0115`) and merged by the owner
(:need:`XD-ADR-0043`, :need:`XD-ADR-0051`). The bump bot then moves the manifest pins
(:need:`XD-ADR-0081`). The type after each action name says who does it.

.. sysml-view:: /views/changeProcess.drawio.svg
   :caption: changeProcess: from the first branch to the published documents (action flow view)

Life cycles
-----------

A need starts as ``draft``. Only ``valid`` needs count for coverage, and a need is retired before
it is deleted (:need:`XD-RULE-0020`).

.. sysml-view:: /views/needStatus.drawio.svg
   :caption: needStatus (state transition view)

A newer decision revises or supersedes an older one, and the newer one holds the link
(:need:`XD-ADR-0109`).

.. sysml-view:: /views/decisionStatus.drawio.svg
   :caption: decisionStatus (state transition view)

A link becomes suspect when its target changes. Only a person's commit confirms it again
(:need:`XD-ADR-0051`, :need:`XD-ADR-0121`), and no suspect link may remain at a baseline
(:need:`XD-RULE-0014`).

.. sysml-view:: /views/traceLinkStatus.drawio.svg
   :caption: traceLinkStatus (state transition view)

HIL evidence counts only when it was recorded from ``main`` or a baseline, and only while the
pinned SHAs still match (:need:`XD-ADR-0053`, :need:`XD-ADR-0120`, :need:`XD-RULE-0013`).

.. sysml-view:: /views/evidenceStatus.drawio.svg
   :caption: evidenceStatus (state transition view)

People, agents and automation
-----------------------------

Agents author and review like people do (:need:`XD-ADR-0003`). Only people decide: the owner
merges, and a person affirms suspect links (:need:`XD-ADR-0051`). The full list of what agents
may and may not do is in :doc:`humans-and-agents`.

.. sysml-view:: /views/rolesAndUseCases.drawio.svg
   :caption: rolesAndUseCases: who does what (use cases)

.. sysml-view:: /views/roleKinds.drawio.svg
   :caption: roleKinds: people and agents (general view)
