# Sphinx configuration of the document "XDMOD Manual" (xdmod-manual).
# The shared XDMOD setup (xdmod/sphinx/xdmod_conf.py) wraps zdocs' configure() and loads the
# XDMOD Sphinx extension (with the reference directives that read curatrix and needs_config.toml).
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(os.environ["ZDOCS_WEST_TOPDIR"]) / "xdmod" / "sphinx"))
from xdmod_conf import configure  # noqa: E402

configure(globals(), __file__, "XDMOD Manual")
