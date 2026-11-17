"""`curatrix fixtures`: run the planted error of every built-in check and record the result
(task 5.3; Phase 5 exit criterion 2, review finding P5-13).

The table of planted errors is ``PLANTED`` in ``curatrix/tests/test_planted_errors.py``: check ID
-> the test that plants an error the check must report. Plain-Python cases also run in CI (the
`XD-T1` test command); this command runs all of them, including the ones that need a tool (the
Pilot), under limits, and writes ``build/fixtures/planted.json``: per check the test, its result,
plus the tool versions and the date. The Phase 5 review and every baseline repeat it.
"""
from __future__ import annotations

import datetime as dt
import importlib.util
import json
import xml.etree.ElementTree as ET

from curatrix import limits


def planted_table(ws) -> dict[str, str]:
    path = ws.xdmod / "curatrix" / "tests" / "test_planted_errors.py"
    import sys
    sys.path.insert(0, str(path.parent))                    # the module imports `helpers`
    try:
        spec = importlib.util.spec_from_file_location("_xd_planted", path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
    finally:
        sys.path.remove(str(path.parent))
    return dict(mod.PLANTED)


def _tool_versions(ws) -> dict[str, str]:
    from curatrix import provenance, tools
    out = {}
    for kind in ("model", "views", "freecad-shapes"):
        out.update(provenance.used(ws, kind))
    ts = tools.load_all(ws)
    if "kicad-cli" in ts.system:
        out["kicad-cli"] = tools.system_version(ts.system["kicad-cli"], ws) or "missing"
    return dict(sorted(out.items()))


def run(ws, log=print) -> tuple[bool, dict]:
    table = planted_table(ws)
    out = ws.build("fixtures")
    out.mkdir(parents=True, exist_ok=True)
    junit = out / "planted-junit.xml"
    nodes = sorted(set(table.values()))
    argv = [str(ws.venv / "bin" / "python"), "-m", "pytest", "-q", "-p", "no:cacheprovider", "-m", "tools or not tools",
            f"--junitxml={junit}", *nodes]
    with open(out / "pytest.log", "w") as fh:
        limits.run(argv, "tests", ws, cwd=str(ws.xdmod), stdout=fh, stderr=fh)
    results: dict[str, str] = {}                            # node id (no params) -> passed|failed|skipped
    if junit.exists():
        for tc in ET.parse(junit).getroot().iter("testcase"):
            node = tc.get("classname", "").rsplit(".", 1)[-1] + "::" + tc.get("name", "").split("[")[0]
            state = "failed" if tc.find("failure") is not None or tc.find("error") is not None else \
                "skipped" if tc.find("skipped") is not None else "passed"
            prev = results.get(node)
            results[node] = state if prev in (None, "passed") or state == "failed" else prev
    rows = []
    for cid, node in sorted(table.items()):
        mod, _, fn = node.partition("::")
        state = results.get(mod.rsplit("/", 1)[-1].removesuffix(".py") + "::" + fn, "not run")
        rows.append({"check": cid, "test": node, "result": state})
        log(f"  {'ok  ' if state == 'passed' else 'FAIL'} {cid:6} {state:8} {node}")
    ok = all(r["result"] == "passed" for r in rows)
    doc = {"date": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"), "ok": ok,
           "tools": _tool_versions(ws), "checks": rows}
    (out / "planted.json").write_text(json.dumps(doc, indent=2) + "\n")
    log(f"{'FIXTURES PASSED' if ok else 'FIXTURES FAILED'}: every check failed on its planted error"
        if ok else f"FIXTURES FAILED; see {ws.rel(out / 'pytest.log')}")
    log(f"  record: {ws.rel(out / 'planted.json')}")
    return ok, doc
