"""needs_config.toml is the single source of the trace model (D64h, task 5.2, P4-9): curatrix
derives its lists from it and keeps no copy."""
import re
import subprocess
from pathlib import Path

from curatrix import graph, ids, tracemodel

SRC = Path(__file__).resolve().parents[1] / "src" / "curatrix"


def test_link_types_include_every_declared_link():
    assert {"revises", "supersedes", "refines", "verifies"} <= set(graph.LINK_TYPES)
    assert set(graph.LINK_TYPES) == {lt for t in tracemodel.types() for lt in (t.get("links") or {})}


def test_kinds_and_requirement_types():
    assert {"SYS-REQ", "EE-PCBA", "XD-CHECK", "PRJ-DEC"} <= ids.NEED_KINDS
    assert not any(k.startswith("TR") for k in ids.NEED_KINDS)
    assert set(graph.REQ_TYPES) == {"sys-req", "sw-req", "ee-req", "me-req"}
    for k in ids.NEED_KINDS:
        assert tracemodel.directive_of(k) == ids.directive_of(k), k


def test_id_patterns_match_the_toml_id_regex():
    """The toml's id_regex (sphinx-needs) and curatrix's ID_RE accept the same domains."""
    toml = tracemodel.config()["id_regex"]
    m = re.search(r"\(\(\(([A-Z|]+)\)-", toml)
    assert m and set(m.group(1).split("|")) == set(ids.DOMAINS)
    tr = re.search(r"TR-\(([A-Z|]+)\)", toml)
    assert tr and set(tr.group(1).split("|")) == set(ids.TR_DOMAINS)
    for nid in ("SYS-REQ-0012", "EE-CMP-0003.2", "PRJ-DEC-0001", "TR-INT-STC-0001-3f9a1c2e"):
        assert ids.valid_id(nid) and re.match(toml, nid), nid


def test_no_hard_coded_copy_left():
    """No list of link types, requirement types or kinds is written out in curatrix's code."""
    pats = [r'"refines", "raised_by"', r'"sys-req", "sw-req"', r'"SYS-STH", "SYS-NEED"', r"SYS\|SW\|EE\|ME\|INT\|XD"]
    for p in pats:
        hits = subprocess.run(["grep", "-rnE", p, str(SRC), "--include=*.py"], capture_output=True, text=True).stdout
        assert hits == "", hits
