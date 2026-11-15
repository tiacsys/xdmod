from curatrix import needs


def test_tombstones():
    old = {"SYS-EL-0001": {"id": "SYS-EL-0001", "type": "sys-el", "title": "A", "status": "valid"},
           "SYS-EL-0002": {"id": "SYS-EL-0002", "type": "sys-el", "title": "B", "status": "valid"}}
    new = {"SYS-EL-0001": old["SYS-EL-0001"]}
    t, msgs = needs.update_tombstones(old, new, {}, today="2026-11-15")
    assert list(t) == ["SYS-EL-0002"]
    assert t["SYS-EL-0002"]["status"] == "retired" and t["SYS-EL-0002"]["retired_on"] == "2026-11-15"
    # it comes back: the tombstone goes
    t2, msgs = needs.update_tombstones(new, old, t, today="2026-11-16")
    assert t2 == {} and "removed" in msgs[0]
    # pruned at the next baseline
    kept, _ = needs.prune_tombstones(t, "2026-11-15")
    assert kept == t
    gone, msgs = needs.prune_tombstones(t, "2026-12-01")
    assert gone == {} and "dropped" in msgs[0]


def test_doc_format_roundtrip(tmp_path):
    p = tmp_path / "n.json"
    needs.write(p, {"B": {"id": "B"}, "A": {"id": "A"}}, "proj")
    assert list(needs.load(p)) == ["A", "B"]
    assert needs.load(p) == {"A": {"id": "A"}, "B": {"id": "B"}}
