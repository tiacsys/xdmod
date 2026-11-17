"""XDMOD never names the example project's repos (D66, D111, P4-16, task 5.6)."""
import subprocess
from pathlib import Path

import pytest

from curatrix import cli, setup
from curatrix.ws import Repo, is_framework_path

SRC = Path(__file__).resolve().parents[1] / "src" / "curatrix"


def test_no_robarm_name_in_curatrix_code():
    hits = subprocess.run(["grep", "-rn", "robarm", str(SRC), "--include=*.py"], capture_output=True, text=True).stdout
    assert hits == "", hits


def test_framework_path_is_a_checks_yaml(tmp_path):
    (tmp_path / "foo-ee").mkdir()
    (tmp_path / "foo-ee" / "checks.yaml").write_text("version: 1\n")
    (tmp_path / "zephyr").mkdir()
    assert is_framework_path(tmp_path / "foo-ee", "foo-ee")
    assert not is_framework_path(tmp_path / "zephyr", "zephyr")
    assert is_framework_path(tmp_path / "nowhere", "xdmod")


@pytest.mark.parametrize("name,prefix", [("xdmod", "xd"), ("robarm-ee", "ee"), ("acme-manifest", "manifest"),
                                         ("solo", "solo")])
def test_repo_prefix(name, prefix):
    assert setup.repo_prefix(name) == prefix


def test_integration_repo_default(tmp_path):
    class WS:
        framework_repos = [Repo("acme-ee", tmp_path, "acme-ee"), Repo("acme-integration", tmp_path, "acme-integration")]
    assert cli._integration_repo(WS()) == "acme-integration"
    WS.framework_repos = WS.framework_repos[:1]
    with pytest.raises(SystemExit, match="--repo"):
        cli._integration_repo(WS())
