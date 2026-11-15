"""Shared conf.py helper for every document of a repo that uses XDMOD (wraps zdocs_conf.configure).

In <repo>/docs/<doc>/conf.py::

    import os, sys
    from pathlib import Path
    sys.path.insert(0, str(Path(os.environ["ZDOCS_WEST_TOPDIR"]) / "xdmod" / "sphinx"))
    from xdmod_conf import configure, repo_root

    REPO = repo_root(__file__)
    configure(globals(), __file__, "System Architecture",
              generated=[(REPO, "generated/*.json"), (REPO, "views/*.drawio.svg")])

``generated`` lists (base folder, glob) pairs of files outside the document folder that the
document reads (generated needs, views, JUnit XML). zdocs copies only the document folder into
the Sphinx source tree, so these are staged through ``external_content_contents``; in rst they are
then addressed from the source root, e.g. ``.. needimport:: /generated/model-needs.json``.

It also loads, in every document: sphinx-test-reports (so imported test needs are known
everywhere) and ``xdmod_sphinx`` (sysml-view, CAD directives, xd-needimport, tracechain).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

XDMOD = Path(__file__).resolve().parent.parent


def repo_root(conf_file: str) -> Path:
    """<repo> for <repo>/docs/<doc>/conf.py."""
    return Path(conf_file).resolve().parents[2]


def workspace() -> Path:
    return Path(os.environ.get("ZDOCS_WEST_TOPDIR") or XDMOD.parent).resolve()


def area_of(repo: Path) -> str:
    """build/<area>: the repo's checks.yaml `area`, else the repo folder name."""
    cy = repo / "checks.yaml"
    if cy.is_file():
        try:
            import yaml
            a = (yaml.safe_load(cy.read_text()) or {}).get("area")
            if a:
                return str(a)
        except Exception:  # noqa: BLE001
            pass
    return repo.name


def configure(ns: dict, conf_file: str, project: str, generated=(), extensions=(), cad_dir: str | None = None):
    sys.path.insert(0, os.environ["ZDOCS_CONF_DIR"])
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from zdocs_conf import configure as zdocs_configure

    zdocs_configure(ns, doc_dir=Path(conf_file).resolve().parent, project=project,
                    extensions=["sphinx_test_reports", "xdmod_sphinx", *extensions])
    apply(ns, conf_file, generated, cad_dir)


def apply(ns: dict, conf_file: str, generated=(), cad_dir: str | None = None):
    """The xdmod part of the configuration (also usable without zdocs, e.g. in tests)."""
    for base, pattern in generated:
        ns.setdefault("external_content_contents", []).append((Path(base), pattern))
    # sphinx-test-reports: a <property name="verifies"> becomes a link; deterministic IDs
    ns["tr_property_link_types"] = {"verifies": "verifies", "result_of": "result_of"}
    ns["tr_deterministic_case_ids"] = True
    # `configures` (link) and `configs` (field) are both fixed by the trace model
    sw = list(ns.get("suppress_warnings") or [])
    for w in ("needs.type_near_name",):
        if w not in sw:
            sw.append(w)
    ns["suppress_warnings"] = sw
    repo = repo_root(conf_file)
    ns["xd_repo"] = str(repo)
    ns["xd_cad_dir"] = cad_dir or os.environ.get("XD_CAD_DIR") or str(workspace() / "build" / area_of(repo) / "cad")
