# Minimal Sphinx project that loads xdmod's needs_config.toml (used by test_needs_config.py).
import os
from pathlib import Path

project = "needs-config-test"
extensions = ["sphinx_needs"]
needs_from_toml = str(Path(os.environ.get("XD_NEEDS_CONFIG", Path(__file__).resolve().parents[4] / "needs" / "needs_config.toml")))
suppress_warnings = ["needs.type_near_name"]
exclude_patterns = ["_build"]
needs_build_json = True
