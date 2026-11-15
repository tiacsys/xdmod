# Sphinx configuration of the document "XDMOD Manual" (xdmod-manual).
# The shared XDMOD setup (xdmod/sphinx/xdmod_conf.py) wraps zdocs' configure() and loads the
# XDMOD Sphinx extension (with the reference directives that read curatrix and needs_config.toml).
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(os.environ["ZDOCS_WEST_TOPDIR"]) / "xdmod" / "sphinx"))
from xdmod_conf import configure  # noqa: E402

configure(globals(), __file__, "XDMOD Manual")

# Agent-readable output (D122): sphinx-llm writes a Markdown copy of every page and llms.txt /
# llms-full.txt into the HTML output. No page summaries (they would call an LLM service).
extensions.append("sphinx_llm.txt")  # noqa: F821
llms_txt_description = "XDMOD: a method and tools for cross-domain, multi-repo systems engineering."
llms_txt_full_build = True
llms_txt_build_parallel = False
