from curatrix import stubs

NEEDS = {
    "SYS-STH-0001": {"id": "SYS-STH-0001", "type": "sys-sth", "title": "Operator", "status": "valid"},
    "SYS-NEED-0001": {"id": "SYS-NEED-0001", "type": "sys-need", "title": "Problem */ x", "status": "valid"},
    "SYS-REQ-0001": {"id": "SYS-REQ-0001", "type": "sys-req", "title": "Latency", "status": "valid",
                     "refines": ["SYS-NEED-0001"], "ears": "event", "quantity": "latency", "unit": "ms", "max": 50,
                     "min": 2.5},
    "SYS-REQ-0002": {"id": "SYS-REQ-0002", "type": "sys-req", "title": "Old", "status": "retired",
                     "refines": ["SYS-NEED-0001"]},
    "SYS-REQ-0009": {"id": "SYS-REQ-0009", "type": "sys-req", "title": "Ext", "is_external": True},
    "SW-REQ-0001": {"id": "SW-REQ-0001", "type": "sw-req", "title": "Not a stub"},
}


def test_generate():
    text = stubs.generate(NEEDS)
    assert text.startswith("// GENERATED") and "library package NeedStubs {" in text
    assert "part <'SYS-STH-0001'> sys_sth_0001 {" in text
    assert "concern <'SYS-NEED-0001'> sys_need_0001 {" in text and "* /" in text   # no early comment end
    assert "attribute max : Real = 50.0;" in text and "attribute min : Real = 2.5;" in text
    assert 'attribute unit : String = "ms";' in text and 'attribute ears : String = "event";' in text
    assert "frame sys_need_0001;" in text
    assert 'status = "retired"' in text
    assert "SYS-REQ-0009" not in text and "SW-REQ" not in text
    assert stubs.generate(dict(reversed(list(NEEDS.items())))) == text            # order-independent
