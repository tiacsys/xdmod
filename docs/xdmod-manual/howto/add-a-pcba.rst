.. _howto-add-a-pcba:

Add a board (PCBA) or circuit block
===================================

Use this guide when you, in the EE role, add a new board: a KiCad project for a board def of the
EE model, with its connectors, ERC and DRC, design output and board document. It also covers circuit
blocks and components that take part in trace links. Prototype wiring is EE content too: a KiCad
schematic of the prototype setup whose elements carry ``configs`` (:need:`XD-ADR-0067`).

The board itself is a def in the EE model; the KiCad project only names it
(:need:`XD-ADR-0128`). Circuit blocks and components keep their trace IDs inside the KiCad files
(:need:`XD-ADR-0023`). The example is the canary board ``canary-board`` of robarm-ee.

Work on a branch in a worktree set (:ref:`howto-cross-repo-change`):

.. code-block:: sh

   .venv/bin/curatrix work start feat/my-board robarm-ee
   cd .worktrees/feat/my-board

In the set, call curatrix as ``.venv/bin/curatrix`` (it runs the set's xdmod), or run
``eval "$(.venv/bin/curatrix env)"`` once, which puts ``.venv/bin`` first on ``PATH``; the commands
below are written as ``curatrix ...``.

Steps
-----

1. **Board def.** Add the board def to ``model/`` in the EE repo: ``part def <'EE-PCBA-NEW-a'>
   MyBoard :> <the SYS-EL def>, XdDomain::Pcba``, with a connector port def (``EE-PORT``) for every
   port it inherits, each with its pin map (:need:`XD-ADR-0130`). Then issue the IDs and regenerate
   the model; ``realizes`` and ``conforms`` come from ``:>``:

   .. code-block:: sh

      curatrix ids fix robarm-ee
      curatrix gen model robarm-ee

2. **KiCad project and document.** ``curatrix new pcba`` makes them from the shared template in
   ``xdmod/templates/kicad-pcba/``:

   .. code-block:: sh

      curatrix new pcba MyBoard --repo robarm-ee

   It writes ``pcba/<name>/`` (``<name>`` = the board def's name in kebab case, ``MyBoard`` ->
   ``my-board``): the ``.kicad_pro`` with
   ``TraceID`` = the def's ``EE-PCBA`` ID and ``XD_VERSION = unversioned``, the ERC/DRC severities
   of the template, library tables with workspace variables only, the CAM jobset, and a schematic
   and board saved by KiCad. It also writes the board document ``docs/pcba-<name>/`` and its entry
   in ``docs/documents.yaml``. The ``TraceID`` is a reference; the need comes from the model.
   ``Realizes``, ``Configs`` or other link fields in the ``.kicad_pro`` are reported, because links
   and ``configs`` come from the model.

3. **Draw** schematic and board. Open the project only with the launcher, which sets the library
   paths and keeps your user-global KiCad setup out (:need:`XD-ADR-0080`, :need:`XD-ADR-0145`):

   .. code-block:: sh

      curatrix launch kicad robarm-ee/pcba/<name>/<name>.kicad_pro

   - Keep ``${XD_VERSION}`` in a title-block comment line of every sheet and of the board, and in a
     silkscreen text; leave the ``Rev`` field empty (CK-F11).
   - Iteration 1 stops before routing: placement, outline and silkscreen; the unrouted-net DRC
     errors are accepted in one entry (:need:`XD-ADR-0144`, step 6).
   - The outline and holes come from the board's space budget through the co-design push, not by
     hand (:ref:`howto-co-design-change`).

4. **Connectors.** Every connector symbol (reference ``J``, ``P``, ``CN``, or any symbol with a
   ``Port`` field) gets a ``Port`` field with the ``EE-PORT`` def ID it implements. Then write the
   connector tables and commit them:

   .. code-block:: sh

      curatrix gen connectors robarm-ee        # generated/<name>.connectors.json

   CK-F1 compares pins and nets with the pin maps of the EE model, CK-D7 that the JSON is fresh, and
   CK-D8 (local, KiCad) the extraction against KiCad's XML netlist.

5. **Variants** (at most two, :need:`XD-ADR-0136`): add them in KiCad as assembly variants (DNP and
   fields per variant; a pin-header shunt position as a field ``Setting``), write one def per
   variant in the EE model (``part def MyBoardAlt :> MyBoard, XdDomain::DomainVariant { :>>
   variantName = "alt"; }``) with a dependency to the configurations and usages it serves, and
   rewrite the jobset so that every variant gets its jobs:

   .. code-block:: sh

      curatrix cam robarm-ee <name> --update-jobset

6. **ERC and DRC.** ``curatrix check robarm-ee --stage local`` runs both (CK-F4a, CK-F4b) and fails
   on an error that is neither excluded in KiCad nor accepted. Accept a finding in
   ``pcba/<name>/accepted.yaml``, keyed by check, rule and designators (:need:`XD-ADR-0126`):

   .. code-block:: yaml

      version: 1
      accepted:
        - check: CK-F4b
          rule: unconnected_items
          items: all
          reason: Placement and outline only; routing is not done in iteration 1 (XD-ADR-0144).

   An entry counts only when the newest commit that wrote it carries ``Accepted-by: <name>``, has no
   agent trailer and changes nothing but acceptance entries (CK-F9). **Agents only propose entries**
   in their PR; the EE engineer or the owner accepts them with an own commit. Prefer
   ``accepted.yaml`` to a KiCad exclusion: an exclusion is lost when its items move.

7. **Circuit blocks and components** that take part in trace links get **hidden** symbol or sheet
   fields:

   .. list-table::
      :header-rows: 1

      * - Field
        - Value
      * - ``TraceID``
        - the need ID (kind ``EE-CMP``); write a placeholder ID, then issue it
      * - ``Realizes``
        - the product-layer ``SYS-EL`` IDs (comma list)
      * - ``Satisfies``
        - ``EE-REQ`` IDs
      * - ``Conforms``
        - ``SYS-IF`` IDs of the interfaces it meets
      * - ``PartOf``
        - the ``EE-PCBA`` ID
      * - ``Status``
        - ``draft``, ``valid`` or ``retired``
      * - ``Configs``
        - ``SYS-CFG`` IDs, if it belongs only to some configurations

   A sheet used several times carries one ID; its usages become ``instances`` (:need:`XD-ADR-0117`).
   Every BOM part needs ``Manufacturer`` and ``MPN``, or a ``Standard`` designation (CK-F12). Then
   issue the IDs and regenerate the CAD needs:

   .. code-block:: sh

      curatrix ids fix robarm-ee
      curatrix gen cad-needs robarm-ee

   Commit ``generated/cad-needs.json`` (:need:`XD-ADR-0100`).

8. **Design output and the board document.** Make the design output of the current commit, then
   build the document (:ref:`howto-design-output`):

   .. code-block:: sh

      curatrix cam robarm-ee <name>
      curatrix docs robarm-ee

9. **Check and open the PR.** ``curatrix check robarm-ee --stage local`` with CAD content
   (:need:`XD-ADR-0040`). The PR names the proposed ``accepted.yaml`` entries; the reviewer follows
   :ref:`howto-review-a-domain-pr`.

The board document
------------------

Every board has one document ``pcba-<name>`` with the same sections (:need:`XD-ADR-0129`), one
``xd-pcba-*`` directive each: overview, variants, renderings, schematic, stackup, design rules,
connectors, ERC and DRC findings, and the BOM in the appendix (a column per variant). The tables come
from the KiCad files in plain Python and show in CI too. Renderings, schematic and findings come
from the ``curatrix cam`` output of the commit the repo is at (:need:`XD-RULE-0060`); without it, and
in CI, they print a fixed sentence, and CK-D10 warns locally.

Checks
------

- :need:`XD-CHECK-0016`, :need:`XD-CHECK-0017`: the EE model parses and its generated files are fresh.
- :need:`XD-CHECK-0033`: the board def redefines every inherited port with a fitting port def.
- CK-F6, CK-F7: one project per ``pcba/<name>/`` folder, 1:1 with the board defs.
- CK-D7, CK-D8, CK-F1: connectors (fresh JSON, KiCad netlist, pin maps of the model).
- CK-F4a, CK-F4b, CK-F8, CK-F9: ERC, DRC, the template severities, acceptance.
- CK-F10, CK-F11: the jobset is the template's, the version variable is used.
- CK-F12, CK-D9: Manufacturer and MPN; the BOM reader equals KiCad's BOM export per variant.
- :need:`XD-CHECK-0034`: exactly one variant per configuration and usage, and each variant is in the ``.kicad_pro``.
- :need:`XD-CHECK-0019`: ``cad-needs.json`` matches the KiCad files (plain Python, no KiCad needed).
- :need:`XD-CHECK-0001`: the strict docs build; its needs schema fails an element that realizes or
  satisfies nothing (:need:`XD-RULE-0010`).

CK-D8, CK-D9, CK-F4a and CK-F4b need KiCad and run only locally; CK-D10 needs no CAD tool but runs
only locally (it looks for the ``cam`` output). PR CI runs the rest.

Pitfalls
--------

- Never run ``kicad-cli`` or KiCad outside curatrix or its ``.venv/bin`` shims, not even
  ``--version``: it rewrites ``~/.config/kicad`` (:need:`XD-ADR-0145`).
- Save KiCad files through KiCad. A hand-edited file that KiCad has not re-saved shows up as a diff
  on the next save.
- Hidden fields are easy to lose when you replace a symbol. Check ``cad-needs.json`` and the
  connector JSON in the diff.
- A wire end inside another wire needs a junction, or the net is split.
- There is one design document per PCBA and one per prototype configuration (:need:`XD-ADR-0102`).
