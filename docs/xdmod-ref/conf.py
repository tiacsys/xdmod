# Sphinx configuration of the document "curatrix Reference" (xdmod-ref).
# The shared XDMOD setup (xdmod/sphinx/xdmod_conf.py) wraps zdocs' configure() and loads the
# XDMOD Sphinx extension (with the reference directives that read curatrix and needs_config.toml).
# autodoc reads curatrix from this xdmod tree, not from the copy installed in the venv.
import os
import sys
from pathlib import Path

XDMOD = Path(os.environ["ZDOCS_WEST_TOPDIR"]) / "xdmod"
sys.path.insert(0, str(XDMOD / "sphinx"))
sys.path.insert(0, str(XDMOD / "curatrix" / "src"))
from xdmod_conf import configure  # noqa: E402

configure(globals(), __file__, "curatrix Reference", extensions=["sphinx.ext.autodoc"])
autodoc_member_order = "bysource"
autodoc_typehints = "none"
