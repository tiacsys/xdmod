"""A minimal trace report (task 5.10): one row per system requirement, from the merged needs of a
docs build (``build/<area>/docs/deploy/html/*/needs.json``).

Columns: refined by, satisfied by, verified by (test cases, also those that verify a requirement
refining it), latest result (``TR`` needs; one per test case, the newest by ``run_id``, not per
platform), gaps. Only evidence counts (D60, R5a, D131): a result tagged ``preview`` is shown as
"preview, not evidence" and a ``stale`` one is a gap; neither counts as passed.

Requirements of the system configuration ``canary`` (P5-16) get their own section and stay out of
the coverage numbers: a requirement belongs to it when all of its ``configs`` are canary
``SYS-CFG`` (a requirement of the canary and another configuration stays in), or when a canary
``SYS-CFG`` ``configures`` it. A canary ``SYS-CFG`` is one with the tag ``canary`` or with
"canary" in its title, or the ones given with ``--canary``.

Output: ``build/<area>/trace/trace.md`` and ``trace.html``.
"""
from __future__ import annotations

import html
import re
from pathlib import Path

from curatrix import graph as graphmod, tracemodel

TC_TYPES = tuple(t["directive"] for t in tracemodel.types() if t["directive"].endswith(("-tc", "-itc", "-stc")))


def canary_configs(needs: dict[str, dict], given: list[str] | None = None) -> set[str]:
    if given:
        return set(given)
    return {nid for nid, n in needs.items() if n.get("type") == "sys-cfg"
            and ("canary" in (n.get("tags") or []) or "canary" in (n.get("title") or "").lower())}


def canary_needs(needs: dict[str, dict], cfgs: set[str]) -> set[str]:
    out = {nid for nid, n in needs.items() if cfgs and n.get("configs") and set(n["configs"]) <= cfgs}
    for c in cfgs:
        out |= set((needs.get(c) or {}).get("configures") or [])
    return out


def _latest(trs: list[dict]) -> tuple[dict | None, dict | None]:
    """(newest evidence result, newest preview result), by run_id."""
    ev = [t for t in trs if "preview" not in (t.get("tags") or [])]
    pv = [t for t in trs if "preview" in (t.get("tags") or [])]

    def key(t):
        return (t.get("run_id") or "", t["id"])
    return (max(ev, key=key) if ev else None), (max(pv, key=key) if pv else None)


def _brief(t: dict | None) -> dict | None:
    if t is None:
        return None
    tags = t.get("tags") or []
    return {"id": t["id"], "verdict": t.get("verdict"), "preview": "preview" in tags, "stale": "stale" in tags}


def counts_passed(r: dict | None) -> bool:
    """A result that counts as passed: evidence, not stale, verdict passed."""
    return bool(r) and not r["preview"] and not r["stale"] and r["verdict"] == "passed"


def rows(g: graphmod.Graph) -> list[dict]:
    needs, back = g.needs, g.back()

    def live(ids):
        return sorted(i for i in ids if graphmod.counts(needs.get(i)))

    out = []
    for rid in sorted(i for i, n in needs.items() if n.get("type") == "sys-req" and n.get("status") != "retired"):
        refined = live(back[rid].get("refines", []))
        satisfied = live(back[rid].get("satisfies", []))
        # the requirement and every requirement that refines it (down the tree)
        reqs, todo = {rid}, [rid]
        while todo:
            for c in back[todo.pop()].get("refines", []):
                if c not in reqs and needs.get(c, {}).get("type") in tracemodel.req_types():
                    reqs.add(c)
                    todo.append(c)
        tcs = live({t for r in reqs for t in back[r].get("verifies", []) if needs.get(t, {}).get("type") in TC_TYPES})
        results, previews = {}, {}
        for tc in tcs:
            ev, pv = _latest([needs[t] for t in back[tc].get("result_of", []) if t in needs])
            results[tc], previews[tc] = _brief(ev), _brief(pv)
        gaps = []
        if not refined and not satisfied:
            gaps.append("not refined or satisfied")
        if not tcs:
            gaps.append("no test case")
        for tc, r in results.items():
            if r is None:
                gaps.append(f"{tc}: only a preview result (not evidence)" if previews[tc] else f"{tc}: no result")
            elif r["stale"]:
                gaps.append(f"{tc}: stale result")
            elif r["verdict"] != "passed":
                gaps.append(f"{tc}: {r['verdict']}")
        out.append({"id": rid, "title": needs[rid].get("title", ""), "status": needs[rid].get("status", "valid"),
                    "refined_by": refined, "satisfied_by": satisfied, "verified_by": tcs,
                    "results": results, "previews": previews,
                    "gaps": gaps})
    return out


def _result_text(r: dict | None, p: dict | None) -> str:
    out = []
    if r is not None:
        out.append(r["verdict"] + (" (stale)" if r["stale"] else ""))
    if p is not None:
        out.append(f"{p['verdict']} (preview, not evidence)")
    return ", ".join(out) or "-"


def coverage(rs: list[dict]) -> dict:
    valid = [r for r in rs if r["status"] == "valid"]
    return {"requirements": len(valid),
            "refined_or_satisfied": sum(1 for r in valid if r["refined_by"] or r["satisfied_by"]),
            "with_test_case": sum(1 for r in valid if r["verified_by"]),
            "passed": sum(1 for r in valid if r["verified_by"] and all(counts_passed(x) for x in r["results"].values()))}


def report(g: graphmod.Graph, title: str, canary: list[str] | None = None) -> tuple[str, str, dict]:
    """(markdown, html, summary) of the trace report."""
    cfgs = canary_configs(g.needs, canary)
    cn = canary_needs(g.needs, cfgs)
    rs = rows(g)
    main = [r for r in rs if r["id"] not in cn]
    can = [r for r in rs if r["id"] in cn]
    cov = coverage(main)
    head = ["Requirement", "Refined by", "Satisfied by", "Verified by", "Latest result", "Gaps"]

    def cells(r):
        res = "; ".join(f"{tc}: {_result_text(x, r['previews'][tc])}" for tc, x in r["results"].items()) or "-"
        return [f"{r['id']} {r['title']}" + (f" ({r['status']})" if r["status"] != "valid" else ""),
                ", ".join(r["refined_by"]) or "-", ", ".join(r["satisfied_by"]) or "-",
                ", ".join(r["verified_by"]) or "-", res, "; ".join(r["gaps"]) or "none"]

    def md_table(rows_):
        if not rows_:
            return ["No requirements.", ""]
        lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
        lines += ["| " + " | ".join(c.replace("|", "\\|") for c in cells(r)) + " |" for r in rows_]
        return lines + [""]

    def html_table(rows_):
        if not rows_:
            return "<p>No requirements.</p>"
        t = "<table><tr>" + "".join(f"<th>{h}</th>" for h in head) + "</tr>"
        for r in rows_:
            t += "<tr>" + "".join(f"<td>{html.escape(c)}</td>" for c in cells(r)) + "</tr>"
        return t + "</table>"

    cov_text = (f"{cov['requirements']} valid system requirements (without the canary): "
                f"{cov['refined_or_satisfied']} refined or satisfied, {cov['with_test_case']} with a test case, "
                f"{cov['passed']} with all latest results passed (evidence only: previews and stale results do not count).")
    can_text = (f"Configuration canary ({', '.join(sorted(cfgs)) or 'no canary SYS-CFG found'}): "
                f"{len(can)} requirement(s), not counted above (P5-16).")
    md = [f"# Trace report: {title}", "", "Results tagged *preview* come from a local test run; they are not evidence.",
          "", "## Coverage", "", cov_text, "", "## System requirements", "", *md_table(main),
          "## Configuration canary", "", can_text, "", *md_table(can)]
    page = (f"<!doctype html><html><head><meta charset='utf-8'><title>Trace report: {html.escape(title)}</title>"
            "<style>body{font-family:sans-serif;margin:1em}table{border-collapse:collapse}"
            "td,th{border:1px solid #999;padding:4px;text-align:left;vertical-align:top}</style></head><body>"
            f"<h1>Trace report: {html.escape(title)}</h1>"
            "<p>Results tagged <em>preview</em> come from a local test run; they are not evidence.</p>"
            f"<h2>Coverage</h2><p>{html.escape(cov_text)}</p><h2>System requirements</h2>{html_table(main)}"
            f"<h2>Configuration canary</h2><p>{html.escape(can_text)}</p>{html_table(can)}</body></html>\n")
    summary = {"title": title, "coverage": cov, "canary_configs": sorted(cfgs), "rows": rs,
               "canary": [r["id"] for r in can]}
    return "\n".join(md), page, summary


def write(files: list[Path], out: Path, title: str, canary: list[str] | None = None) -> dict:
    import json
    g = graphmod.load(files)
    md, page, summary = report(g, title, canary)
    out.mkdir(parents=True, exist_ok=True)
    (out / "trace.md").write_text(md)
    (out / "trace.html").write_text(page)
    (out / "trace.json").write_text(json.dumps(summary, indent=2) + "\n")
    return summary
