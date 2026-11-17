"""needs/needs_config.toml under a strict Sphinx build: the sample passes, each planted error fails.

These tests run sphinx-build (a few seconds each). Skip them with `-m "not sphinx"`.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

FIXTURE = Path(__file__).parent / "fixtures" / "needsdoc"
pytestmark = pytest.mark.sphinx


def build(tmp_path, extra_rst=""):
    src = tmp_path / "src"
    shutil.copytree(FIXTURE, src)
    if extra_rst:
        with open(src / "index.rst", "a") as f:
            f.write("\n" + extra_rst)
    out = tmp_path / "out"
    r = subprocess.run([sys.executable, "-m", "sphinx", "-W", "--keep-going", "-q", "-b", "html",
                        str(src), str(out)], capture_output=True, text=True, timeout=300)
    return r.returncode, r.stdout + r.stderr, out


def test_sample_builds_strict(tmp_path):
    rc, log, out = build(tmp_path)
    assert rc == 0, log
    d = json.loads((out / "needs.json").read_text())
    needs = d["versions"][d["current_version"]]["needs"]
    assert needs["SYS-REQ-0001"]["max"] == 50
    assert needs["SYS-EL-0003"]["configs"] == ["SYS-CFG-0001"]
    assert needs["SW-REQ-0002"]["derived"] is True
    # R4 grace (D75): SYS-EL-0003 satisfies the retired SYS-REQ-0002 and the build passes.
    assert "SYS-REQ-0002" in needs["SYS-EL-0003"]["satisfies"]
    # Phase 5 kinds (5.14): ports, harness, SW conforms to the EE board model.
    assert needs["EE-HAR-0001"]["connects"] == ["EE-PORT-0001", "EE-PORT-0002"]
    assert needs["ME-PORT-0001"]["part_of"] == ["ME-ASM-0001"]
    assert needs["SW-DD-0002"]["conforms"] == ["EE-PCBA-0001", "EE-PORT-0001"]
    assert needs["XD-ADR-0002"]["decision_status"] == "proposed"


BAD = {
    "wrong-side": """
.. sys-need:: Bad
   :id: SYS-NEED-0090
   :status: valid
   :category: problem
   :refines: SYS-REQ-0001
""",
    "unknown-target": """
.. sw-req:: Bad
   :id: SW-REQ-0090
   :status: valid
   :refines: SYS-REQ-9999
""",
    "wrong-target-type": """
.. sw-req:: Bad
   :id: SW-REQ-0091
   :status: valid
   :refines: SYS-NEED-0002
""",
    "missing-required-link": """
.. sys-req:: Bad
   :id: SYS-REQ-0090
   :status: valid
""",
    "bad-enum": """
.. sys-sth:: Bad
   :id: SYS-STH-0090
   :status: obsolete
""",
    "bad-id": """
.. sys-sth:: Bad
   :id: SYS-STH-12
   :status: valid
""",
    "kind-mismatch": """
.. sys-sth:: Bad
   :id: SYS-REQ-0091
   :status: valid
""",
    "orphan-design": """
.. ee-cmp:: Bad
   :id: EE-CMP-0090
   :status: valid
""",
    "derived-without-rationale": """
.. me-req:: Bad
   :id: ME-REQ-0090
   :status: valid
   :derived: true
""",
    "need-without-stakeholder": """
.. sys-need:: Bad
   :id: SYS-NEED-0091
   :status: valid
   :category: need
""",
    "functional-without-uc": """
.. sys-el:: Bad
   :id: SYS-EL-0090
   :status: valid
   :layer: functional
""",
    "orphan-product-el": """
.. sys-el:: Bad
   :id: SYS-EL-0091
   :status: valid
   :layer: product
""",
    "hil-with-hash-but-no-shas": """
.. tr:: Bad
   :id: TR-INT-STC-0001-bbbbbbbb
   :status: valid
   :result_of: INT-STC-0001
   :method: hil
   :firmware_sha256: 0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef
""",
    "ee-port-conforms-to-element": """
.. ee-port:: Bad
   :id: EE-PORT-0090
   :status: valid
   :conforms: SYS-EL-0003
""",
    "ee-port-part-of-assembly": """
.. ee-port:: Bad
   :id: EE-PORT-0091
   :status: valid
   :part_of: ME-ASM-0001
""",
    # a harness with one `connects` target is valid: an extension cable has the same port def at
    # both ends; CK-F1 counts the ends of the cable def (task 5.22 review)
    "harness-to-a-board": """
.. ee-har:: Bad
   :id: EE-HAR-0091
   :status: valid
   :connects: EE-PCBA-0001, EE-PORT-0001
""",
    "me-port-part-of-board": """
.. me-port:: Bad
   :id: ME-PORT-0090
   :status: valid
   :part_of: EE-PCBA-0001
""",
    "ee-links-to-sw": """
.. ee-pcba:: Bad
   :id: EE-PCBA-0090
   :status: valid
   :realizes: SYS-EL-0003
   :conforms: SW-ARCH-0001
""",
    "me-conforms-to-ee-port": """
.. me-part:: Bad
   :id: ME-PART-0090
   :status: valid
   :part_of: ME-ASM-0001
   :satisfies: ME-REQ-0001
   :conforms: EE-PORT-0001
""",
    "sw-conforms-to-ee-cmp": """
.. sw-dd:: Bad
   :id: SW-DD-0090
   :status: valid
   :refines: SW-ARCH-0001
   :conforms: EE-CMP-0001
""",
    "bad-decision-status": """
.. xd-adr:: Bad
   :id: XD-ADR-0090
   :status: valid
   :decision_status: maybe
""",
    "hil-without-sha": """
.. tr:: Bad
   :id: TR-INT-STC-0001-aaaaaaaa
   :status: valid
   :result_of: INT-STC-0001
   :method: hil
""",
}


# Why the Phase 5 cases must fail (task 5.14), so that they do not pass for another reason.
REASON = {
    "ee-port-conforms-to-element": "needs.link_target_type",
    "ee-port-part-of-assembly": "needs.link_target_type",
    "harness-to-a-board": "needs.link_target_type",
    "me-port-part-of-board": "needs.link_target_type",
    "ee-links-to-sw": "needs.link_target_type",
    "me-conforms-to-ee-port": "needs.link_target_type",
    "sw-conforms-to-ee-cmp": "needs.link_target_type",
    "bad-decision-status": "schema violations",
}


@pytest.mark.parametrize("name", sorted(BAD))
def test_planted_error_fails(tmp_path, name):
    rc, log, _ = build(tmp_path, BAD[name])
    assert rc != 0, f"{name} should fail the strict build:\n{log}"
    if name in REASON:
        assert REASON[name] in log, log
