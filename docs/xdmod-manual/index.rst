.. _manual-index:

XDMOD Manual
============

**XDMOD** (Cross-Domain MODeling) is a method plus tools for developing a product across systems
engineering, software, electronics and mechanics, in many git repos, with people and AI agents
working side by side. It is built on SYSMOD and SysML v2 for the system model, sphinx-needs for
requirements and traces, zdocs for a linked document set, and west for the workspace. Its one
tool is ``curatrix``.

XDMOD gives you three things:

1. **One trace graph across all domains.** Every need, model element, CAD part, code unit and
   test result has an ID, and the more concrete side holds each link. Checks find broken, missing
   and suspect links, in every repo and across the full set.
2. **Documents that come from the design.** Requirements, architecture, CAD and code produce one
   linked, versioned document set. Generated content is committed and checked, so it can't drift.
3. **One workflow for humans and agents.** The same commands, checks and reviews apply to
   everyone. Agents propose; only a human's commit affirms.

Examples in this manual come from the robot arm, the worked example of XDMOD. Every page reads
on its own without it.

How to read this manual
-----------------------

The manual follows Diátaxis:

- :doc:`tutorials/index` walk you through your first workspace, requirement and change.
- :doc:`howto/index` are short recipes for one task each.
- :doc:`reference/index` lists the facts: trace model, ID scheme, checks, layouts.
- :doc:`explanation/index` says why things are the way they are, and holds every framework
  decision and method rule as a need.

The command line and the Sphinx extensions are documented in the curatrix reference
(``xdmod-ref``).

.. toctree::
   :maxdepth: 2

   tutorials/index
   howto/index
   reference/index
   explanation/index
