# Plain Sphinx project (no zdocs) for test_sphinx_ext.py: xdmod_sphinx + the shared needs config.
import os
import sys
from pathlib import Path

XDMOD = Path(os.environ.get("XD_XDMOD") or Path(__file__).resolve().parents[4])
sys.path.insert(0, str(XDMOD / "sphinx"))
from xdmod_conf import apply  # noqa: E402

project = "xdmod-sphinx-test"
extensions = ["sphinx_needs", "sphinx_test_reports", "xdmod_sphinx"]
needs_from_toml = os.environ.get("XD_NEEDS_CONFIG", str(XDMOD / "needs" / "needs_config.toml"))
needs_build_json = True
exclude_patterns = ["_build"]
apply(globals(), str(Path(__file__).resolve().parent / "doc" / "conf.py"), cad_dir=os.environ.get("XD_CAD_DIR", "/nonexistent"))
