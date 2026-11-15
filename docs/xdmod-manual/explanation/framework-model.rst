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
diagram has a legend and fits a 4:3 or 16:9 page, upright or across. In short:

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

The five domains
----------------

XDMOD splits a project into five domains. Each domain has its own repo, its own need types and
its own reviewers (:need:`XD-ADR-0006`, :need:`XD-ADR-0061`):

- **SYS**, systems engineering: stakeholders, system requirements and the SysML model.
- **EE**, electrical engineering: KiCad projects and prototype wiring.
- **ME**, mechanical engineering: FreeCAD parts and assemblies.
- **SW**, software: the Zephyr firmware.
- **INT**, system-level verification: system and integration tests and HIL runs. A test that
  touches the system lives here, even if it touches one domain only (:need:`XD-ADR-0104`).

The domain is the first part of every ID in its repo (:need:`XD-ADR-0071`). Two more ID
prefixes are not domains: **XD** for the framework itself and **PRJ** for project decisions.

Each domain has two diagrams. The first shows its repo with the documents and design files it
holds; the ``doc`` compartment says where each file lives. The second shows its need types
and the trace links between them. Every need type is an ``item def`` whose short name is its
sphinx-needs directive (``<sys-req>``). The line ``:> Requirement`` names its category, its place
in the V (`Need categories`_ below).

The concrete side holds the link (:need:`XD-ADR-0004`, :need:`XD-RULE-0001`). The diamond sits on
the need type that holds the link; the arrow points to the more abstract type, so the abstract
types stand at the top. The label next to the diamond names the link type. ``[1..*]`` marks a
link that is required; the need schema in ``needs_config.toml`` enforces it
(:need:`XD-RULE-0002`, :need:`XD-RULE-0007`). Some links may point to more than one need type.
The model then has one reference per target type, each ``[0..*]``, and "(>= 1 in total)" says
that at least one of them is required.

Systems engineering (SYS)
~~~~~~~~~~~~~~~~~~~~~~~~~

The systems repo holds the SysML model, the documents with the requirements and the architecture, and the files curatrix generates from them: requirement stubs for the model, the compact model export, the needs taken from the model, and the views (:need:`XD-ADR-0001`).

.. sysml-view:: /views/sysRepo.drawio.svg
   :caption: sysRepo: the repo, its documents and design files (general view)

Stakeholders raise needs; system requirements refine them. Use cases address needs, and system model elements satisfy requirements and realize use cases. A configuration selects model elements. Interfaces and features are the targets of the other domains: nothing inside SYS links to them.

.. sysml-view:: /views/sysNeeds.drawio.svg
   :caption: sysNeeds: need types and the trace links inside the domain (general view)

Electrical engineering (EE)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The EE repo holds one KiCad project per PCBA, the prototype wiring, the domain tests and the needs curatrix reads from the KiCad files (:need:`XD-ADR-0102`, :need:`XD-ADR-0023`).

.. sysml-view:: /views/eeRepo.drawio.svg
   :caption: eeRepo: the repo, its documents and design files (general view)

A circuit block is part of a PCBA. Both satisfy EE requirements. EE tests verify EE requirements, and test results point back to the test case they come from.

.. sysml-view:: /views/eeNeeds.drawio.svg
   :caption: eeNeeds: need types and the trace links inside the domain (general view)

Mechanical engineering (ME)
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The ME repo holds the FreeCAD parts and assemblies, the domain tests and the needs curatrix reads from the FreeCAD files (:need:`XD-ADR-0056`).

.. sysml-view:: /views/meRepo.drawio.svg
   :caption: meRepo: the repo, its documents and design files (general view)

The same pattern as EE: a part is part of an assembly, both satisfy ME requirements, and ME tests verify them.

.. sysml-view:: /views/meNeeds.drawio.svg
   :caption: meNeeds: need types and the trace links inside the domain (general view)

Software (SW)
~~~~~~~~~~~~~

The SW repo holds the Zephyr application, its tests and the software documents, from the requirements to the test report (:need:`XD-ADR-0069`).

.. sysml-view:: /views/swRepo.drawio.svg
   :caption: swRepo: the repo, its documents and design files (general view)

Software has the longest chain inside one domain: requirements, architecture, detailed design and code units, which curatrix extracts from the code (:need:`XD-ADR-0070`). Each level refines or implements the one above and satisfies the requirements.

.. sysml-view:: /views/swNeeds.drawio.svg
   :caption: swNeeds: need types and the trace links inside the domain (general view)

System-level verification (INT)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The integration repo holds the system and integration tests, the HIL setups and the HIL run records (:need:`XD-ADR-0066`). Run records live on the orphan branch ``evidence``.

.. sysml-view:: /views/intRepo.drawio.svg
   :caption: intRepo: the repo, its documents and design files (general view)

Inside the domain there is only one kind of link: a test result points to its test case. Everything a system-level test verifies is in SYS (next section). A run result also carries the firmware hash and the pinned SHAs (:need:`XD-RULE-0012`).

.. sysml-view:: /views/intNeeds.drawio.svg
   :caption: intNeeds: need types and the trace links inside the domain (general view)

Between two domains
-------------------

These diagrams show only the links that cross from one domain to another. Every crossing link
goes to systems engineering: a domain requirement refines a system requirement or an interface,
a design element realizes a system model element and conforms to an interface, and a
system-level test verifies a system requirement or an interface.

.. sysml-view:: /views/sysSw.drawio.svg
   :caption: sysSw: software to systems engineering (general view)

.. sysml-view:: /views/sysEe.drawio.svg
   :caption: sysEe: electrical engineering to systems engineering (general view)

.. sysml-view:: /views/sysMe.drawio.svg
   :caption: sysMe: mechanical engineering to systems engineering (general view)

.. sysml-view:: /views/sysInt.drawio.svg
   :caption: sysInt: system-level verification to systems engineering (general view)

There are no diagrams for EE and SW, EE and ME, or ME and SW, because these pairs have no links
by design. Peer domains never link to each other. When EE and SW must agree on a pin map, the
agreement is an interface need (``SYS-IF``) in the systems repo, and both link to it with
``conforms`` (:need:`XD-RULE-0003`, :need:`XD-ADR-0030`). In the diagrams above, ``Interface``
is that meeting point. System-level verification has no links to the engineering domains
either: it verifies the system. It does import their needs, as the next section shows.

The whole workspace
-------------------

Needs flow from the abstract side to the concrete side. The systems repo exports its needs. The
engineering repos import them as upstream documents, and the integration repo imports all of them
(:need:`XD-ADR-0021`). Trace links point back the other way (:need:`XD-RULE-0001`). The manifest
builds the full set.

.. sysml-view:: /views/workspaceNeeds.drawio.svg
   :caption: workspaceNeeds: how needs flow between the repos (interconnection view)

xdmod serves every repo with the need types, the Sphinx extensions, the SysML library, curatrix
and the reusable workflows (:need:`XD-ADR-0059`). The manifest pins every repo
(:need:`XD-ADR-0033`).

.. sysml-view:: /views/workspacePins.drawio.svg
   :caption: workspacePins: the framework and the pins (interconnection view)

Every repo has the same configuration files, whatever its domain.

.. sysml-view:: /views/repoLayout.drawio.svg
   :caption: repoLayout: what every repo has (general view)

The framework repo and the manifest repo are not domains.

.. sysml-view:: /views/frameworkRepos.drawio.svg
   :caption: frameworkRepos: xdmod and the manifest (general view)

XDMOD knows three kinds of files. **Source** files are written by people and agents.
**Generated** files are written by curatrix, committed, and compared by ``curatrix check``
(:need:`XD-RULE-0033`). **Build output** goes to ``build/<area>/`` and is never committed
(:need:`XD-RULE-0040`). The plain source files (documents, models, configuration) are in the repo
diagrams above.

.. sysml-view:: /views/artifactKinds.drawio.svg
   :caption: artifactKinds: source, generated and build files (general view)

Need categories
---------------

``Need`` declares every link type once. Each need type then narrows the link types it holds to
the target types it may point to (:need:`XD-RULE-0002`). The categories group the need types by
their place in the V.

.. sysml-view:: /views/needCategories.drawio.svg
   :caption: needCategories: the general need and its categories (general view)

Test results come from two sources: run results written by curatrix and test reports imported from
JUnit files. Each points to the test case it comes from (domain diagrams above).

.. sysml-view:: /views/testResults.drawio.svg
   :caption: testResults: kinds of test results (general view)

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

A change runs on one branch name in every repo it touches (:need:`XD-ADR-0045`). It is checked
locally and in CI, and reviewed by a second agent (:need:`XD-ADR-0115`). Then a person, the owner
or a domain engineer, reviews and merges it (:need:`XD-ADR-0043`, :need:`XD-ADR-0051`). If the
change made links suspect, an agent prepares the affirmations and a person confirms them
(:need:`XD-RULE-0014`). After each action name comes its action definition: the kind of task
(agent work, agent review, a person's decision, a CI run), which says who may do it.

.. sysml-view:: /views/changeProcess.drawio.svg
   :caption: changeProcess: one change, from the first branch to the merge (action flow view)

The bump bot runs on a schedule, not as a step of one change (:need:`XD-ADR-0081`). It collects
the new SHAs of all repos into one bump PR, whose full-set check must pass before the owner merges
it. Then the documents are published.

.. sysml-view:: /views/pinBump.drawio.svg
   :caption: pinBump: the scheduled bump of the manifest pins (action flow view)

Life cycles
-----------

A need starts as ``draft``. A merged change sets it to ``valid``; only ``valid`` needs count for
coverage. A need is retired before it is deleted, and its ID is never issued again
(:need:`XD-RULE-0020`, :need:`XD-RULE-0011`).

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
pinned SHAs still match (:need:`XD-ADR-0053`, :need:`XD-ADR-0120`, :need:`XD-RULE-0013`). A record
never changes: a new run writes a new record.

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
