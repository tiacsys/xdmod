"""Code-derived needs in plain Python (task 5.10; D77, D80): code units and test cases.

Code units (``SW-IMPL``): a Doxygen block ``/** ... */`` with ``@xdid{SW-IMPL-0001}`` (exactly one
ID per block). The title is the name the declaration after the block declares (``canary_update()``,
a struct, a ``#define``, a typedef); a block with ``@file`` is titled with the file name. Links and
fields are short sentences in the block::

    /**
     * @brief Return the new canary output for an input value.
     *
     * @xdid{SW-IMPL-0001}
     * Implements SW-DD-0001.
     * Satisfies SW-REQ-0001.
     * Configs: SYS-CFG-0001.
     */
    int32_t canary_update(int32_t input);

Test cases (``SW-TC``, any ``*-TC``): the comment right above a ``ZTEST``, ``ZTEST_F``,
``ZTEST_USER``, ``ZTEST_USER_F`` or ``ZTEST_P`` (the same comment ``curatrix evidence`` reads to
map Twister results to test cases)::

    /**
     * @brief The canary output follows a changed input within 1 ms.
     *
     * Test case: SW-TC-0001. Verifies SW-REQ-0001.
     */
    ZTEST(canary, test_output_follows_input)

The ID must follow ``Test case:`` (one ID per test). The title is the first sentence of the
``@brief``. The Twister identifiers of the test (``<scenario>.<suite>.<name>``, from the nearest
``testcase.yaml`` inside the repo) go into the content: needs_config.toml has no field for them.

Link sentences: ``Implements``, ``Satisfies``, ``Verifies`` (also as Doxygen commands
``\\satisfies``, ``@verifies``), followed by one or more IDs. A link the need type does not declare
in needs_config.toml is a finding. ``Configs:`` lists ``SYS-CFG`` IDs (D103); ``Status:`` is
draft, valid or retired (default valid).

Limits (findings, never silent where the reader is unsure): string literals and ``//`` comments
are skipped; code inside ``#if 0`` is still read. Tests behind a wrapper macro (``MYTEST(n)``) are
not seen.
"""
from __future__ import annotations

import re
from pathlib import Path

from curatrix import ids as idmod, tracemodel

ID = r"[A-Z]{2,5}-[A-Z]{2,5}-[0-9]{4,}"
TC_RE = re.compile(r"\b(?:" + "|".join(sorted(tracemodel.kinds_of("TC", "ITC", "STC"))) + r")-[0-9]{4,}\b")
ZTEST_RE = re.compile(
    r"/\*(?P<c>(?:(?!\*/).)*)\*/\s*ZTEST(?:_F|_USER|_USER_F|_P)?\(\s*(?P<suite>\w+)\s*,\s*(?P<name>\w+)\s*\)", re.S)
XDID_RE = re.compile(r"[@\\]xdid\{([^}]*)\}")
BLOCK_RE = re.compile(r"/\*\*(?P<c>(?:(?!\*/).)*)\*/", re.S)
LINK_RE = re.compile(r"(?:[@\\]|\b)(implements|satisfies|verifies)\b:?\s+((?:" + ID + r"(?:\s*,\s*|\s+and\s+|\s+)?)+)",
                     re.I)
CONFIGS_RE = re.compile(r"\bConfigs:\s*((?:SYS-CFG-[0-9]{4,}(?:\s*,\s*|\s+)?)+)")
STATUS_RE = re.compile(r"\bStatus:\s*(\w+)")
BRIEF_RE = re.compile(r"[@\\]brief\s+(.+?)(?:\n\s*\n|\n\s*[@\\]|$)", re.S)
TESTCASE_RE = re.compile(r"\bTest case:\s*([\w-]+(?:\s*(?:,|\band\b)\s*[\w-]+)*)", re.I)


def mask(src: str) -> str:
    """The source with string and char literals and ``//`` comments replaced by spaces (same
    length, newlines kept), so that comment and declaration regexes never match inside them.
    Block comments stay."""
    out, i, n = list(src), 0, len(src)
    while i < n:
        c = src[i]
        if src.startswith("/*", i):
            j = src.find("*/", i + 2)
            i = n if j < 0 else j + 2
        elif src.startswith("//", i):
            while i < n and src[i] != "\n":
                out[i] = " "
                i += 1
        elif c in "\"'":
            j = i + 1
            while j < n and src[j] != c and src[j] != "\n":
                j += 2 if src[j] == "\\" else 1
            for k in range(i, min(j + 1, n)):
                if out[k] != "\n":
                    out[k] = " "
            i = j + 1
        else:
            i += 1
    return "".join(out)


def _text(comment: str) -> str:
    """Comment body without the leading ``*`` of each line."""
    return "\n".join(re.sub(r"^\s*\*?\s?", "", ln) for ln in comment.splitlines()).strip()


def _line(src: str, pos: int) -> int:
    return src.count("\n", 0, pos) + 1


def _brief(text: str) -> str:
    """The first sentence of the @brief (one line or several)."""
    m = BRIEF_RE.search(text)
    if not m:
        return ""
    b = re.sub(r"\s+", " ", m.group(1)).strip()
    return re.split(r"(?<=[.!?])\s", b, maxsplit=1)[0].rstrip(".")


def _allowed_links(directive: str) -> set[str] | None:
    for t in tracemodel.types():
        if t["directive"] == directive:
            return set(t.get("links") or {})
    return None


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
    if allowed is None:
        return None, [f"{where}: {nid}: unknown need type {directive!r} (needs_config.toml)"]
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


def declaration(after: str) -> tuple[str, str]:
    """(title, declaration text) of the declaration that follows a block (masked source)."""
    rest = after.lstrip()
    if rest.startswith("#"):
        line = rest.split("\n", 1)[0].strip()
        m = re.match(r"#\s*define\s+(\w+)", line)
        return (m.group(1), line) if m else ("", "")
    m = re.match(r"(?:(?!/\*)[^;{#])*", rest)
    decl = re.sub(r"\s+", " ", m.group(0)).strip() if m else ""
    if not decl:
        return "", ""
    fp = re.search(r"\(\s*\*\s*(\w+)\s*\)\s*\(", decl)            # typedef / pointer to function
    if fp:
        return fp.group(1), decl
    fn = re.search(r"(\w+)\s*\(", decl)
    if fn:
        return fn.group(1) + "()", decl
    name = re.search(r"(\w+)\s*(?:\[[^\]]*\])?\s*(?:=.*)?$", decl)
    return (name.group(1) if name else ""), decl


def _ids_in_braces(raw: str) -> list[str]:
    return [x for x in re.split(r"[,\s]+", raw.strip()) if x]


def code_units(path: Path, rel: str) -> tuple[dict[str, dict], list[str]]:
    src = path.read_text(errors="replace")
    masked = mask(src)
    needs, findings = {}, []
    for m in BLOCK_RE.finditer(masked):
        tags = XDID_RE.findall(m.group("c"))
        if not tags:
            continue
        where = f"{rel}:{_line(src, m.start())}"
        ids = [i for t in tags for i in _ids_in_braces(t)]
        if len(ids) != 1:
            findings.append(f"{where}: one @xdid with exactly one ID per block (found {ids or 'none'}); "
                            "no code unit made")
            continue
        if not idmod.valid_id(ids[0]):
            findings.append(f"{where}: @xdid{{{ids[0]}}} is not a valid ID; no code unit made")
            continue
        text = _text(m.group("c"))
        if re.search(r"[@\\]file\b", text):
            title, decl = Path(rel).name, ""
        else:
            title, decl = declaration(masked[m.end():])
            if not title:
                findings.append(f"{where}: {ids[0]}: no declaration after the block; titled with the file name")
                title = Path(rel).name
        brief = _brief(text)
        content = (brief + ".\n\n") if brief else ""
        content += f"Declared in ``{rel}``" + (f": ``{decl}``." if decl else ".")
        n, f = _need(ids[0], title, content, text, where)
        findings += f
        if n is not None:
            if n["id"] in needs:
                findings.append(f"{where}: {n['id']} is on more than one block")
                continue
            needs[n["id"]] = n
    return needs, findings


def _scenarios(test_file: Path, root: Path) -> tuple[list[str], list[str]]:
    """Twister scenario names from the nearest testcase.yaml / sample.yaml above the file, inside
    the repo; (names, findings)."""
    import yaml
    for d in test_file.resolve().parents:
        for name in ("testcase.yaml", "sample.yaml"):
            y = d / name
            if y.is_file():
                try:
                    return sorted((yaml.safe_load(y.read_text()) or {}).get("tests") or {}), []
                except yaml.YAMLError as e:
                    return [], [f"{y.relative_to(root)}: not valid YAML ({str(e).splitlines()[0]})"]
        if d == root:
            break
    return [], []


def test_cases(path: Path, rel: str) -> tuple[dict[str, dict], list[str]]:
    src = path.read_text(errors="replace")
    root = path.resolve().parents[len(Path(rel).parts) - 1]
    needs, findings = {}, []
    for m in ZTEST_RE.finditer(mask(src)):
        comment = m.group("c").split("/*")[-1]
        text = _text(comment.lstrip("*"))
        where = f"{rel}:{_line(src, m.start('suite'))}"
        tc = TESTCASE_RE.search(text)
        if not tc:
            if TC_RE.search(text):
                findings.append(f"{where}: a test case ID without 'Test case:' ({TC_RE.search(text).group(0)}); "
                                "write 'Test case: <ID>.' to make it the test's ID")
            continue
        ids = [x for x in re.split(r"\s*(?:,|\band\b)\s*", tc.group(1).strip()) if x]
        if len(ids) != 1:
            findings.append(f"{where}: one test case ID per test (found {ids}); no test case made")
            continue
        if not TC_RE.fullmatch(ids[0]):
            findings.append(f"{where}: {ids[0]!r} after 'Test case:' is not a valid test case ID")
            continue
        suite, name = m.group("suite"), m.group("name")
        short = name[5:] if name.startswith("test_") else name
        title = _brief(text) or f"{suite}.{short}"
        scen, f = _scenarios(path, root)
        findings += f
        twister = [f"``{s}.{suite}.{short}``" for s in scen]
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
