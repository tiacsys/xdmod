"""Code-derived needs in plain Python (task 5.10; D77, D80): code units and test cases.

Code units (``SW-IMPL``): a Doxygen block ``/** ... */`` with ``@xdid{SW-IMPL-0001}``. The title is
the name the declaration after the block declares (``canary_update()``). Links and fields are
short sentences in the block::

    /**
     * @brief Return the new canary output for an input value.
     *
     * @xdid{SW-IMPL-0001}
     * Implements SW-DD-0001.
     * Satisfies SW-REQ-0001.
     * Configs: SYS-CFG-0001.
     */
    int32_t canary_update(int32_t input);

Test cases (``SW-TC``, any ``*-TC``): the comment right above a ``ZTEST(...)`` (the same comment
``curatrix evidence`` reads to map Twister results to test cases)::

    /**
     * @brief The canary output follows a changed input within 1 ms.
     *
     * Test case: SW-TC-0001. Verifies SW-REQ-0001.
     */
    ZTEST(canary, test_output_follows_input)

The title is the ``@brief`` text. The Twister identifiers of the test (``<scenario>.<suite>.<name>``,
from the nearest ``testcase.yaml``) go into the content: needs_config.toml has no field for them.

Link sentences: ``Implements``, ``Satisfies``, ``Verifies`` (also as Doxygen commands
``\\satisfies``, ``@verifies``), followed by one or more IDs. A link the need type does not declare
in needs_config.toml is a finding. ``Configs:`` lists ``SYS-CFG`` IDs (D103); ``Status:`` is
draft, valid or retired (default valid).
"""
from __future__ import annotations

import re
from pathlib import Path

from curatrix import evidence, ids as idmod, tracemodel

XDID_RE = re.compile(r"[@\\]xdid\{\s*([A-Z0-9-]+)\s*\}")
BLOCK_RE = re.compile(r"/\*\*(?P<c>(?:(?!\*/).)*)\*/(?P<decl>(?:(?!/\*)[^;{])*)", re.S)
ID = r"[A-Z]{2,5}-[A-Z]{2,5}-[0-9]{4,}"
LINK_RE = re.compile(r"(?:[@\\]|\b)(implements|satisfies|verifies)\b:?\s+((?:" + ID + r"(?:\s*,\s*|\s+and\s+|\s+)?)+)",
                     re.I)
CONFIGS_RE = re.compile(r"\bConfigs:\s*((?:SYS-CFG-[0-9]{4,}(?:\s*,\s*|\s+)?)+)")
STATUS_RE = re.compile(r"\bStatus:\s*(\w+)")
BRIEF_RE = re.compile(r"[@\\]brief\s+(.+?)(?:\n\s*\n|\n\s*[@\\]|$)", re.S)
TESTCASE_RE = re.compile(r"\bTest case:\s*(" + ID + ")")


def _text(comment: str) -> str:
    """Comment body without the leading ``*`` of each line."""
    return "\n".join(re.sub(r"^\s*\*?\s?", "", ln) for ln in comment.splitlines()).strip()


def _line(src: str, pos: int) -> int:
    return src.count("\n", 0, pos) + 1


def _allowed_links(directive: str) -> set[str]:
    for t in tracemodel.types():
        if t["directive"] == directive:
            return set(t.get("links") or {})
    return set()


def _need(nid: str, title: str, content: str, text: str, where: str) -> tuple[dict | None, list[str]]:
    kind = idmod.kind_of(nid)
    if kind is None:
        return None, [f"{where}: {nid!r} is not a valid ID"]
    directive = idmod.directive_of(kind)
    findings = []
    n = {"id": nid, "type": directive, "title": title, "content": content, "status": "valid",
         "source_file": where.split(":")[0]}
    m = STATUS_RE.search(text)
    if m:
        n["status"] = m.group(1)
        if n["status"] not in ("draft", "valid", "retired"):
            findings.append(f"{where}: {nid}: Status {n['status']!r} is not draft, valid or retired")
    allowed = _allowed_links(directive)
    for m in LINK_RE.finditer(text):
        link = m.group(1).lower()
        targets = re.findall(ID, m.group(2))
        if link not in allowed:
            findings.append(f"{where}: {nid}: a {directive} has no link {link!r} (needs_config.toml)")
            continue
        bad = [t for t in targets if not idmod.valid_id(t)]
        if bad:
            findings.append(f"{where}: {nid}: {link} holds invalid IDs {bad}")
        n[link] = sorted(set(n.get(link, [])) | (set(targets) - set(bad)))
    m = CONFIGS_RE.search(text)
    if m:
        n["configs"] = sorted(set(re.findall(r"SYS-CFG-[0-9]{4,}", m.group(1))))
    return n, findings


def _declared_name(decl: str) -> str:
    """``int32_t canary_update(int32_t input)`` -> ``canary_update()``; ``struct foo`` -> ``foo``."""
    d = re.sub(r"\s+", " ", decl).strip()
    m = re.search(r"(\w+)\s*\(", d)
    if m:
        return m.group(1) + "()"
    m = re.search(r"(\w+)\s*(?:\[[^\]]*\])?\s*(?:=.*)?$", d)
    return m.group(1) if m else d


def code_units(path: Path, rel: str) -> tuple[dict[str, dict], list[str]]:
    src = path.read_text(errors="replace")
    needs, findings = {}, []
    for m in BLOCK_RE.finditer(src):
        ids = XDID_RE.findall(m.group("c"))
        if not ids:
            continue
        where = f"{rel}:{_line(src, m.start())}"
        if len(ids) > 1:
            findings.append(f"{where}: more than one @xdid in one block ({', '.join(ids)})")
        text = _text(m.group("c"))
        decl = re.sub(r"\s+", " ", m.group("decl")).strip()
        title = _declared_name(decl) if decl else Path(rel).name
        brief = BRIEF_RE.search(text)
        content = (re.sub(r"\s+", " ", brief.group(1)).strip() + "\n\n") if brief else ""
        content += f"Declared in ``{rel}``" + (f": ``{decl}``." if decl else ".")
        n, f = _need(ids[0], title, content, text, where)
        findings += f
        if n is not None:
            if n["id"] in needs:
                findings.append(f"{where}: {n['id']} is on more than one block")
                continue
            needs[n["id"]] = n
    return needs, findings


def _scenarios(test_file: Path) -> list[str]:
    """Twister scenario names from the nearest testcase.yaml / sample.yaml above the file."""
    import yaml
    for d in test_file.resolve().parents:
        for name in ("testcase.yaml", "sample.yaml"):
            y = d / name
            if y.is_file():
                try:
                    return sorted((yaml.safe_load(y.read_text()) or {}).get("tests") or {})
                except yaml.YAMLError:
                    return []
    return []


def test_cases(path: Path, rel: str) -> tuple[dict[str, dict], list[str]]:
    src = path.read_text(errors="replace")
    needs, findings = {}, []
    for m in evidence.ZTEST_RE.finditer(src):
        comment = m.group("c").split("/*")[-1]
        text = _text(comment.lstrip("*"))
        tc = TESTCASE_RE.search(text)
        ids = [tc.group(1)] if tc else evidence.TC_RE.findall(text)
        if not ids:
            continue
        where = f"{rel}:{_line(src, m.start('suite'))}"
        suite, name = m.group("suite"), m.group("name")
        short = name[5:] if name.startswith("test_") else name
        brief = BRIEF_RE.search(text)
        title = re.sub(r"\s+", " ", brief.group(1)).strip().rstrip(".") if brief else f"{suite}.{short}"
        twister = [f"``{s}.{suite}.{short}``" for s in _scenarios(path)]
        content = f"ZTEST ``{name}`` in suite ``{suite}`` (``{rel}``)."
        if twister:
            content += f" Twister reports it as {', '.join(twister)}."
        n, f = _need(ids[0], title, content, text, where)
        findings += f
        if n is not None:
            if n["id"] in needs:
                findings.append(f"{where}: {n['id']} is on more than one test")
                continue
            needs[n["id"]] = n
    return needs, findings
