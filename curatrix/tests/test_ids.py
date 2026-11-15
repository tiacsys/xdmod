from pathlib import Path

import pytest

from curatrix import ids


@pytest.mark.parametrize("nid,kind", [
    ("SYS-REQ-0012", "SYS-REQ"), ("SW-TC-0103", "SW-TC"), ("EE-CMP-0007", "EE-CMP"),
    ("INT-ITC-0003", "INT-ITC"), ("XD-ADR-0001", "XD-ADR"), ("PRJ-DEC-0042", "PRJ-DEC"),
    ("SYS-EL-0012.1", "SYS-EL"), ("SYS-REQ-12345", "SYS-REQ"), ("SYS-VIEW-0001", "SYS-VIEW"),
    ("TR-SW-TC-0103-3f9a1c2e", "TR"),
])
def test_valid_ids(nid, kind):
    assert ids.valid_id(nid)
    assert ids.kind_of(nid) == kind


@pytest.mark.parametrize("nid", ["SYS-REQ-12", "sys-req-0001", "FOO-REQ-0001", "SYS-R-0001", "SYS-REQ-NEW-a",
                                 "TR-SW-TC-0103-XYZ", "TR-XD-ADR-0001-3f9a1c2e", "SYSREQ-0001"])
def test_invalid_ids(nid):
    assert not ids.valid_id(nid)


def test_ledger_roundtrip_and_issue(tmp_path):
    p = tmp_path / "ids.yaml"
    p.write_text("SYS-REQ:\n  - 41\n  - 42\nSYS-NEED: []\n")
    lg = ids.Ledger.load(p)
    assert lg.highest("SYS-REQ") == 42
    assert lg.issue("SYS-REQ") == 43
    assert lg.issue("SYS-NEED", used={7}) == 8        # sources ahead of the ledger: above both
    lg.save()
    text = p.read_text()
    assert "SYS-REQ:\n  - 41\n  - 42\n  - 43\n" in text   # append-only, one number per line (D133)
    assert "SYS-NEED:\n  - 8\n" in text
    assert ids.Ledger.load(p).kinds == lg.kinds
    with pytest.raises(ids.IdError):
        lg.issue("SW-REQ")                               # not owned by this ledger


def test_ledger_rejects_duplicates_and_bad_kinds(tmp_path):
    p = tmp_path / "ids.yaml"
    p.write_text("SYS-REQ: [1, 1]\n")
    with pytest.raises(ids.IdError):
        ids.Ledger.load(p)
    p.write_text("sys-req: [1]\n")
    with pytest.raises(ids.IdError):
        ids.Ledger.load(p)


def _repo(tmp_path):
    r = tmp_path / "repo"
    (r / "docs").mkdir(parents=True)
    (r / "model").mkdir()
    (r / "ids.yaml").write_text("SYS-REQ:\n  - 1\n  - 2\nSYS-EL: []\nSYS-VIEW: []\n")
    (r / "docs" / "req.rst").write_text(
        ".. sys-req:: A\n   :id: SYS-REQ-NEW-a\n\n.. sys-req:: B\n   :id: SYS-REQ-NEW-b\n   :refines: SYS-NEED-0003\n")
    (r / "model" / "m.sysml").write_text(
        "part def <'SYS-EL-NEW-x'> Ctrl { }\nsatisfy SYS-REQ-NEW-a by Ctrl;\nview <'SYS-VIEW-NEW-1'> v;\n")
    return r


def test_fix_replaces_placeholders_consistently(tmp_path):
    r = _repo(tmp_path)
    lg = ids.Ledger.load(r / "ids.yaml")
    mapping = ids.fix(r, lg)
    assert mapping == {"SYS-REQ-NEW-a": "SYS-REQ-0003", "SYS-REQ-NEW-b": "SYS-REQ-0004",
                       "SYS-EL-NEW-x": "SYS-EL-0001", "SYS-VIEW-NEW-1": "SYS-VIEW-0001"}
    assert "satisfy SYS-REQ-0003 by Ctrl" in (r / "model" / "m.sysml").read_text()   # same token, same ID
    assert ":id: SYS-REQ-0003" in (r / "docs" / "req.rst").read_text()
    assert ids.Ledger.load(r / "ids.yaml").kinds["SYS-REQ"] == [1, 2, 3, 4]
    assert ids.scan_placeholders(ids.source_files(r)) == []


def test_fix_dry_run_changes_nothing(tmp_path):
    r = _repo(tmp_path)
    before = (r / "docs" / "req.rst").read_text()
    assert ids.fix(r, ids.Ledger.load(r / "ids.yaml"), dry_run=True)
    assert (r / "docs" / "req.rst").read_text() == before
    assert ids.Ledger.load(r / "ids.yaml").kinds["SYS-REQ"] == [1, 2]


def test_new_with_file(tmp_path):
    r = _repo(tmp_path)
    lg = ids.Ledger.load(r / "ids.yaml")
    nid = ids.new(lg, "SYS-REQ", r, r / "docs" / "req.rst")
    assert nid == "SYS-REQ-0003"
    text = (r / "docs" / "req.rst").read_text()
    assert ":id: SYS-REQ-0003" in text and "SYS-REQ-NEW-b" in text
    with pytest.raises(ids.IdError):
        ids.new(lg, "SYS-FOO", r)


def test_checks_placeholders_and_ledger(tmp_path):
    r = _repo(tmp_path)
    files = ids.source_files(r)
    assert len(ids.check_placeholders(files, r)) == 5
    (r / "docs" / "more.rst").write_text("See SYS-REQ-0002 and SYS-REQ-0009 and upstream SYS-NEED-0003.\n")
    errs = ids.check_ledger(ids.source_files(r), ids.Ledger.load(r / "ids.yaml"), r)
    assert len(errs) == 1 and "SYS-REQ-0009" in errs[0]       # SYS-NEED is not owned: upstream reference


def test_exclude(tmp_path):
    r = _repo(tmp_path)
    assert ids.check_placeholders(ids.source_files(r, ["docs/**", "model/*"]), r) == []


def test_tr_ids_are_not_counted_as_test_case_ids(tmp_path):
    r = tmp_path / "r"
    r.mkdir()
    (r / "x.rst").write_text("TR-SW-TC-0099-3f9a1c2e\n")
    assert ids.scan_ids(ids.source_files(r)) == {}
