"""KiCad ERC and DRC per project, accepted findings and severities (task 5.19; XD-ADR-0126,
XD-ADR-0144; checks CK-F4a, CK-F4b, CK-F8, CK-F9).

* **CK-F4a / CK-F4b** run ``kicad-cli sch erc`` (every project, ``pcba/`` and ``proto/``) and
  ``kicad-cli pcb drc --schematic-parity`` (projects with a board) with ``--format json
  --severity-all`` and evaluate the JSON here. An error passes only when it is excluded in KiCad or
  matched by an entry of ``<project>/accepted.yaml``, and that exclusion or entry is *accepted*
  (below). Warnings are listed in the report file, never as findings.
* **CK-F8**: the project's ERC and DRC rule severities and the ERC pin conflict matrix equal those
  of the ``curatrix new pcba`` template (a missing ``erc`` section counts as the template, which holds KiCad 10.0.8's defaults);
  a custom rule in ``.kicad_dru`` that lowers its severity counts as a difference. A difference
  needs an accepted entry ``{check: CK-F8, rule: <rule>}``.
* **CK-F9**: ``accepted.yaml`` is well formed, and every entry and KiCad exclusion is either
  accepted or reported as a proposal.
* The ME checks (``mechecks``: CK-F4c, CK-F16, CK-F17, task 5.25) use the same file in
  ``assemblies/<name>/accepted.yaml``, the same entries (items: part names) and the same acceptor
  rule; CK-F9 covers those files too.

Accepted (XD-ADR-0126): the newest commit that wrote one of the entry's own lines (``git blame``),
or the one that added the exclusion to the ``.kicad_pro`` (``git log -S``), carries an
``Accepted-by:`` trailer (a real git trailer, not a line in the subject or prose), has one parent and
no agent mark, and changes nothing but ``accepted.yaml`` files and the exclusion lists of
``.kicad_pro`` files; every other commit that wrote the entry's lines is an ancestor of it (a
change merged in from a parallel branch is not accepted). Anything else, also an entry that is not
committed, is a proposal. Agents never write ``Accepted-by:``.

This relies on **rebase merges** (the rulesets of the design repos allow only these): a rebase keeps
the owner's commit message with its trailer. A squash merge would put the agent's proposal and the
owner's acceptance into one commit with the agent trailer, so every acceptance becomes a proposal
(fail-closed); a merge commit never accepts.

``accepted.yaml``::

    version: 1
    accepted:
      - check: CK-F4b              # CK-F4a | CK-F4b | CK-F8; ME: CK-F4c | CK-F16 | CK-F17
        rule: unconnected_items    # the KiCad rule key (CK-F8: the severity key or dru:<rule name>)
        items: all                 # or a list of designators: [J1, R1]
        reason: routing is not done in iteration 1 (XD-ADR-0144)

An entry matches a finding of its check and rule whose designators are all in ``items`` (``all``
matches every finding of the rule). Entries name designators, never positions, so they survive a
move; a KiCad exclusion is lost when its items move (KiCad spike §4.4).
"""
from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import yaml

ACCEPTED = "accepted.yaml"
ENTRY_CHECKS = ("CK-F4a", "CK-F4b", "CK-F8", "CK-F4c", "CK-F16", "CK-F17")   # EE, then ME (mechecks)
ENTRY_KEYS = {"check", "rule", "items", "reason"}
REF = re.compile(r"\b(?:of|[Ss]ymbol|[Ff]ootprint)\s+([A-Za-z_#]*[A-Za-z][0-9]+[A-Za-z0-9_]*)\b")
UNCOMMITTED = "0" * 40


# ------------------------------------------------------------------ reports
@dataclass
class Finding:
    check: str                   # CK-F4a | CK-F4b; ME (mechecks): CK-F4c | CK-F16 | CK-F17
    rule: str                    # KiCad's type key; ME: recompute | solid | overlap
    severity: str                # error | warning | "" (a rule switched off)
    description: str
    items: list[str]
    uuids: list[str]
    excluded: bool = False
    comment: str = ""
    names: list[str] = field(default_factory=list)   # ME: the part names an entry's items name

    @property
    def refs(self) -> list[str]:
        if self.names:
            return sorted(set(self.names))
        return sorted({m.group(1) for i in self.items for m in REF.finditer(i)})

    def line(self) -> str:
        where = ", ".join(self.refs) or "; ".join(self.items)[:120] or "-"
        return f"{self.rule} ({self.severity or 'off'}): {self.description} [{where}]"


def read_report(path: Path, check: str) -> list[Finding]:
    """The findings of a kicad-cli ERC or DRC JSON report (``--severity-all``)."""
    d = json.loads(path.read_text(encoding="utf-8"))
    raw = [v for s in d.get("sheets") or [] for v in s.get("violations") or []]
    for key in ("violations", "unconnected_items", "schematic_parity"):
        raw += d.get(key) or []
    return [Finding(check, v.get("type", ""), v.get("severity", ""), v.get("description", ""),
                    [i.get("description", "") for i in v.get("items") or []],
                    [i.get("uuid", "") for i in v.get("items") or [] if i.get("uuid")],
                    bool(v.get("excluded")), v.get("comment") or "") for v in raw]


# ------------------------------------------------------------------ accepted.yaml
@dataclass
class Entry:
    index: int                   # 1-based position in the file
    check: str
    rule: str
    items: list[str] | str       # designators or "all"
    reason: str
    lines: tuple[int, int]       # 1-based first and last line in the file
    status: str = "proposed"     # accepted | proposed
    why: str = ""                # why it is a proposal, or who accepted it
    hits: int = 0

    def label(self) -> str:
        items = self.items if isinstance(self.items, str) else ", ".join(self.items)
        return f"entry {self.index} ({self.check} {self.rule}: {items})"

    def matches(self, f: Finding) -> bool:
        if f.check != self.check or f.rule != self.rule:
            return False
        if self.items == "all":
            return True
        refs = f.refs
        return bool(refs) and set(refs) <= set(self.items)


def load_entries(path: Path) -> tuple[list[Entry], list[str]]:
    """(entries, format findings) of an accepted.yaml; a missing file has no entries."""
    if not path.is_file():
        return [], []
    text = path.read_text(encoding="utf-8")
    try:
        root = yaml.compose(text)
        data = yaml.safe_load(text) or {}
    except yaml.YAMLError as e:
        return [], [f"not valid YAML: {e}".replace("\n", " ")]
    errs: list[str] = []
    if not isinstance(data, dict) or set(data) - {"version", "accepted"}:
        return [], ["the file is a mapping with the keys version (1) and accepted (a list)"]
    if data.get("version") != 1:
        errs.append("version: 1 is missing")
    items = data.get("accepted") or []
    if not isinstance(items, list):
        return [], errs + ["accepted: must be a list of entries"]
    nodes = next((v.value for k, v in root.value if k.value == "accepted"), []) if root is not None else []
    out = []
    lines = text.splitlines()

    def trimmed(first: int, last: int) -> int:          # no trailing blank or comment lines
        while last > first and (last > len(lines) or not lines[last - 1].strip()
                                or lines[last - 1].lstrip().startswith("#")):
            last -= 1
        return last
    for i, (e, node) in enumerate(zip(items, nodes), 1):
        bad = []
        if not isinstance(e, dict):
            errs.append(f"entry {i}: not a mapping")
            continue
        if set(e) - ENTRY_KEYS:
            bad.append(f"unknown key(s) {', '.join(sorted(set(e) - ENTRY_KEYS))}")
        if e.get("check") not in ENTRY_CHECKS:
            bad.append(f"check must be one of {', '.join(ENTRY_CHECKS)}")
        if not isinstance(e.get("rule"), str) or not e.get("rule"):
            bad.append("rule (the KiCad rule key, or the ME rule) is missing")
        its = e.get("items")
        if not (its == "all" or (isinstance(its, list) and its and all(isinstance(x, str) and x for x in its))):
            bad.append("items must be `all` or a list of designators or part names (never positions)")
        if not isinstance(e.get("reason"), str) or not e["reason"].strip():
            bad.append("reason is missing")
        if bad:
            errs.append(f"entry {i}: " + "; ".join(bad))
            continue
        out.append(Entry(i, e["check"], e["rule"], its, e["reason"].strip(),
                         (node.start_mark.line + 1, trimmed(node.start_mark.line + 1, _last_line(node)))))
    return out, errs


def _last_line(node) -> int:
    """1-based last line of a YAML node's own content. A node's end mark points behind it: at the
    next entry's ``- `` (column > 0 on that line) or at column 0 of the line after; neither line
    belongs to the node. So take the end of the deepest last value instead."""
    while isinstance(node, (yaml.MappingNode, yaml.SequenceNode)) and node.value:
        last = node.value[-1]
        node = last[1] if isinstance(node, yaml.MappingNode) else last
    m = node.end_mark
    if isinstance(node, yaml.ScalarNode) and node.style in ("|", ">"):
        return m.line if m.column == 0 else m.line + 1     # a block scalar ends on the next line
    return m.line + 1


# ------------------------------------------------------------------ who accepted (git)
def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=60)


EXCLUSION_PATHS = (("erc", "erc_exclusions"), ("board", "design_settings", "drc_exclusions"))


def _without_exclusions(text: str):
    try:
        d = json.loads(text)
    except ValueError:
        return None
    for path in EXCLUSION_PATHS:
        node = d
        for k in path[:-1]:
            node = node.get(k) if isinstance(node, dict) else None
        if isinstance(node, dict):
            node.pop(path[-1], None)
    return d


class Acceptors:
    """Verdicts on commits: is this an acceptance commit (XD-ADR-0126)? Cached per SHA."""

    def __init__(self, repo: Path):
        self.repo = repo
        self.cache: dict[str, tuple[bool, str]] = {}

    def verdict(self, sha: str) -> tuple[bool, str]:
        if sha == UNCOMMITTED:
            return False, "not committed"
        if sha not in self.cache:
            self.cache[sha] = self._verdict(sha)
        return self.cache[sha]

    def _verdict(self, sha: str) -> tuple[bool, str]:
        from curatrix.checks import AGENT_MARK      # one definition of an agent commit (CK-H4)
        short = sha[:10]
        body = _git(self.repo, "show", "-s", "--format=%B", sha).stdout
        if AGENT_MARK.search(body):
            return False, f"commit {short} is an agent commit (agents never accept)"
        parents = _git(self.repo, "show", "-s", "--format=%P", sha).stdout.split()
        if len(parents) > 1:
            return False, f"commit {short} is a merge commit (an acceptance is a single commit, rebase merges only)"
        by = [v.strip() for v in _git(self.repo, "show", "-s", "--format=%(trailers:key=Accepted-by,valueonly)",
                                      sha).stdout.splitlines() if v.strip()]
        if not by:
            return False, f"commit {short} has no `Accepted-by:` trailer"
        files = _git(self.repo, "diff-tree", "--root", "--no-commit-id", "--name-only", "-r", sha).stdout.split()
        for f in files:
            name = f.rsplit("/", 1)[-1]
            if name == ACCEPTED:
                continue
            if name.endswith(".kicad_pro"):
                new = _git(self.repo, "show", f"{sha}:{f}")
                old = _git(self.repo, "show", f"{sha}^:{f}")
                if new.returncode == 0 and old.returncode == 0 and \
                        _without_exclusions(new.stdout) == _without_exclusions(old.stdout) is not None:
                    continue
                return False, f"commit {short} changes {f} beyond its ERC/DRC exclusions"
            return False, f"commit {short} also changes {f} (an acceptance commit changes nothing else)"
        return True, f"Accepted-by: {by[0]} in {short}"

    def entry(self, rel: str, e: Entry) -> None:
        """Set e.status/why from the newest commit that wrote one of the entry's lines: the owner
        accepts a proposal by a commit that changes the entry (for example its reason); a later
        change by anyone else turns it back into a proposal."""
        p = _git(self.repo, "blame", "--porcelain", "--ignore-revs-file=", "-L", f"{e.lines[0]},{e.lines[1]}",
                 "--", rel)
        shas = {m.group(1) for m in re.finditer(r"^([0-9a-f]{40}) \d+ \d+", p.stdout, re.M)} if p.returncode == 0 else set()
        if not shas or UNCOMMITTED in shas:
            e.status, e.why = "proposed", "not committed"
            return
        anc = lambda a, b: _git(self.repo, "merge-base", "--is-ancestor", a, b).returncode == 0  # noqa: E731
        tips = sorted(t for t in shas if not any(o != t and anc(t, o) for o in shas))
        if len(tips) > 1:              # changes on parallel branches: no single commit has the last word
            e.status, e.why = "proposed", (f"commits {', '.join(t[:10] for t in tips)} changed the entry on "
                                           f"parallel branches")
            return
        ok, e.why = self.verdict(tips[0])
        e.status = "accepted" if ok else "proposed"

    def exclusion(self, rel_pro: str, key: str) -> tuple[bool, str]:
        """The commit that last added ``key`` to the committed .kicad_pro, and its verdict."""
        head = _git(self.repo, "show", f"HEAD:{rel_pro}")
        if head.returncode or key not in head.stdout:
            return False, "not committed"
        p = _git(self.repo, "log", "-n", "1", "--format=%H", "-S", key, "--", rel_pro)
        sha = p.stdout.strip()
        if not sha:
            return False, "the commit that added it was not found"
        return self.verdict(sha)


def exclusions(pro: Path) -> list[tuple[str, str, str]]:
    """(kind erc|drc, key, comment) of the KiCad exclusions in a .kicad_pro."""
    try:
        d = json.loads(pro.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    out = []
    for kind, lst in (("erc", (d.get("erc") or {}).get("erc_exclusions")),
                      ("drc", ((d.get("board") or {}).get("design_settings") or {}).get("drc_exclusions"))):
        for x in lst or []:
            key, comment = (x[0], x[1] if len(x) > 1 else "") if isinstance(x, list) else (str(x), "")
            out.append((kind, key, comment))
    return out


def exclusion_key(f: Finding, keys: list[str]) -> str | None:
    """The exclusion key of an excluded finding: same rule, every item UUID in the key."""
    for k in keys:
        parts = k.split("|")
        if f.uuids and parts[0] == f.rule and set(f.uuids) <= {x.lstrip("/") for x in parts}:
            return k
    return None


# ------------------------------------------------------------------ evaluation
@dataclass
class Outcome:
    problems: list[str] = field(default_factory=list)     # findings of the check
    listed: list[str] = field(default_factory=list)       # warnings and accepted errors (report only)
    rows: list[dict] = field(default_factory=list)        # one per finding, for the board document

    def row(self, f: Finding, state: str, note: str = "") -> None:
        """state: open | proposal | accepted | warning | stale (an exclusion of a rule that is off)."""
        self.rows.append({"check": f.check, "rule": f.rule, "severity": f.severity or "off", "state": state,
                          "items": ", ".join(f.refs) or "; ".join(f.items)[:120], "description": f.description,
                          "note": note})


def evaluate(findings: list[Finding], entries: list[Entry], excl: dict[str, tuple[bool, str]]) -> Outcome:
    """CK-F4a/b: the errors that are neither accepted in KiCad nor in accepted.yaml.

    ``excl``: exclusion key -> (accepted, why) for the kind (ERC or DRC) of ``findings``."""
    o = Outcome()
    open_ = {(f.rule, tuple(sorted(f.uuids))) for f in findings if not f.excluded}
    by_entry: dict[int, list[Finding]] = {}
    for f in findings:
        if f.excluded:
            if f.severity == "":
                o.problems.append(f"stale KiCad exclusion of a rule that is off: {f.line()}; remove the exclusion")
                o.row(f, "stale", "KiCad exclusion of a rule that is off")
                continue
            if f.check == "CK-F4a" and (f.rule, tuple(sorted(f.uuids))) in open_:
                continue                 # a phantom of a stale ERC exclusion (KiCad spike §4.4)
            key = exclusion_key(f, list(excl))
            ok, why = excl.get(key, (False, "no matching exclusion in the .kicad_pro")) if key else \
                (False, "no matching exclusion in the .kicad_pro")
            if f.severity != "error":
                o.listed.append(f"warning, excluded: {f.line()}")
                o.row(f, "warning", f"excluded in KiCad: {f.comment}" if f.comment else "excluded in KiCad")
            elif ok:
                o.listed.append(f"accepted (KiCad exclusion, {why}): {f.line()}")
                o.row(f, "accepted", f"KiCad exclusion{': ' + f.comment if f.comment else ''}; {why}")
            else:
                o.problems.append(f"excluded in KiCad, but the exclusion is a proposal ({why}): {f.line()}")
                o.row(f, "proposal", f"KiCad exclusion{': ' + f.comment if f.comment else ''}; {why}")
            continue
        if f.severity != "error":
            o.listed.append(f"warning: {f.line()}")
            o.row(f, "warning")
            continue
        e = next((e for e in entries if e.matches(f)), None)
        if e is None:
            o.problems.append(f"error: {f.line()}")
            o.row(f, "open")
            continue
        e.hits += 1
        if e.status == "accepted":
            o.listed.append(f"accepted ({ACCEPTED} {e.label()}, {e.why}): {f.line()}")
            o.row(f, "accepted", f"{e.reason.rstrip('.')} ({ACCEPTED} entry {e.index}; {e.why})")
        else:
            by_entry.setdefault(e.index, []).append(f)
            o.row(f, "proposal", f"{e.reason.rstrip('.')} ({ACCEPTED} entry {e.index}; {e.why})")
    for e in entries:
        if e.index in by_entry:
            n = len(by_entry[e.index])
            kinds = list(dict.fromkeys(f.line() for f in by_entry[e.index]))
            o.problems.append(f"{ACCEPTED} {e.label()} is a proposal, not accepted ({e.why}); it covers "
                              f"{n} error{'s' if n != 1 else ''}: " + "; ".join(kinds[:3]) + (" ..." if len(kinds) > 3 else ""))
    return o


# ------------------------------------------------------------------ severities (CK-F8)
def severities(pro: Path) -> tuple[dict, dict]:
    d = json.loads(pro.read_text(encoding="utf-8"))
    erc = (d.get("erc") or {}).get("rule_severities")
    drc = ((d.get("board") or {}).get("design_settings") or {}).get("rule_severities")
    return erc, drc


def dru_lowered(dru: Path) -> list[tuple[str, str]]:
    """(rule name, severity) of custom rules in a .kicad_dru that are not errors."""
    if not dru.is_file():
        return []
    from curatrix import cad
    root = cad.sexpr("(dru " + dru.read_text(encoding="utf-8") + ")")
    out = []
    for r in root[1:]:
        if isinstance(r, list) and r and r[0] == "rule" and len(r) > 1:
            for c in r[2:]:
                if isinstance(c, list) and c and c[0] == "severity" and len(c) > 1 and c[1] != "error":
                    out.append((r[1], c[1]))
    return out


def severity_diffs(pro: Path, template: Path) -> list[tuple[str, str]]:
    """(rule, text) of every difference between a project's ERC/DRC severities and the template's."""
    t_erc, t_drc = severities(template)
    p_erc, p_drc = severities(pro)
    out = []
    for kind, mine, tmpl in (("ERC", p_erc, t_erc), ("DRC", p_drc, t_drc)):
        if mine is None:
            continue                     # no section: KiCad's defaults = the template's values
        for k in sorted(set(mine) | set(tmpl or {})):
            want, have = (tmpl or {}).get(k), mine.get(k, (tmpl or {}).get(k))
            if want is None:
                out.append((k, f"{kind} rule {k}: {have!r}; not in the template (another KiCad version?)"))
            elif have != want:
                out.append((k, f"{kind} rule {k}: {have!r}, the template has {want!r}"))
    t_pin = (json.loads(template.read_text(encoding="utf-8")).get("erc") or {}).get("pin_map")
    p_pin = (json.loads(pro.read_text(encoding="utf-8")).get("erc") or {}).get("pin_map")
    if p_pin is not None and p_pin != t_pin:
        cells = [f"[{i}][{j}] {v} (template {t_pin[i][j]})" for i, row in enumerate(p_pin) for j, v in enumerate(row)
                 if t_pin and i < len(t_pin) and j < len(t_pin[i]) and t_pin[i][j] != v]
        out.append(("pin_map", f"ERC pin conflict matrix erc.pin_map differs from the template: "
                               + (", ".join(cells[:6]) + (" ..." if len(cells) > 6 else "") if cells else "other size")))
    for name, sev in dru_lowered(pro.with_suffix(".kicad_dru")):
        out.append((f"dru:{name}", f"custom rule {name!r} in {pro.with_suffix('.kicad_dru').name}: severity {sev}"))
    return out


# ------------------------------------------------------------------ per project
def project_entries(cfg, pr, acc: Acceptors) -> tuple[list[Entry], list[str]]:
    return folder_entries(cfg, pr.folder, acc)


def folder_entries(cfg, folder: Path, acc: Acceptors) -> tuple[list[Entry], list[str]]:
    """The entries of ``<folder>/accepted.yaml`` with their acceptance (a KiCad project folder or an
    ME assembly folder, XD-ADR-0126), and format findings."""
    path = folder / ACCEPTED
    entries, errs = load_entries(path)
    rel = str(path.resolve().relative_to(cfg.repo.resolve()))
    for e in entries:
        acc.entry(rel, e)
    return entries, [f"{rel}: {x}" for x in errs]


def exclusion_verdicts(cfg, pr, acc: Acceptors, kind: str) -> dict[str, tuple[bool, str]]:
    rel = str(pr.pro.resolve().relative_to(cfg.repo.resolve()))
    return {key: acc.exclusion(rel, key) for k, key, _ in exclusions(pr.pro) if k == kind}


def run_tool(ws, pr, kind: str, out: Path) -> tuple[Path | None, str]:
    """Run ERC (kind erc) or DRC (drc) of a project; (report, error text)."""
    from curatrix import limits
    out.mkdir(parents=True, exist_ok=True)
    rep = out / f"{pr.name}.{kind}.json"
    rep.unlink(missing_ok=True)
    if kind == "erc":
        argv = ["kicad-cli", "sch", "erc", "--format", "json", "--severity-all", "-o", str(rep),
                str(pr.sch.resolve())]
    else:
        argv = ["kicad-cli", "pcb", "drc", "--schematic-parity", "--format", "json", "--severity-all",
                "-o", str(rep), str(pr.pro.with_suffix(".kicad_pcb").resolve())]
    p = limits.run(argv, "kicad-cli", ws, capture_output=True, text=True)
    if p.returncode or not rep.is_file():
        return None, (f"{pr.name}: kicad-cli {' '.join(argv[1:3])} failed (exit {p.returncode} "
                      f"{limits.explain_rc(p.returncode)}): {(p.stdout + p.stderr)[-300:]}")
    return rep, ""


def check_project(ws, cfg, pr, kind: str, out: Path, acc: Acceptors) -> tuple[list[str], list[str], str]:
    """CK-F4a (kind erc) / CK-F4b (drc) for one project: (problems, listed, tool error)."""
    check = "CK-F4a" if kind == "erc" else "CK-F4b"
    rep, err = run_tool(ws, pr, kind, out)
    if rep is None:
        return [], [], err
    entries, _ = project_entries(cfg, pr, acc)
    entries = [e for e in entries if e.check == check]
    o = evaluate(read_report(rep, check), entries, exclusion_verdicts(cfg, pr, acc, kind))
    rel = str((pr.folder / ACCEPTED).resolve().relative_to(cfg.repo.resolve()))
    for e in entries:
        if not e.hits:
            o.problems.append(f"{rel} {e.label()} matches no {kind.upper()} finding; remove it")
    return [f"{pr.name}: {p}" for p in o.problems], o.listed, ""


def document_rows(ws, cfg, pr, out: Path, acc: Acceptors) -> dict:
    """ERC and DRC of one project for its board document (`curatrix cam`, task 5.21): kind -> one
    row per finding with its state (open, proposal, accepted, warning, stale). Reports go to ``out``."""
    res = {}
    for kind, check in (("erc", "CK-F4a"), ("drc", "CK-F4b")):
        if kind == "drc" and (pr.kind != "pcba" or not pr.pro.with_suffix(".kicad_pcb").is_file()):
            continue
        rep, err = run_tool(ws, pr, kind, out)
        if rep is None:
            raise RuntimeError(err)
        entries = [e for e in project_entries(cfg, pr, acc)[0] if e.check == check]
        res[kind] = evaluate(read_report(rep, check), entries, exclusion_verdicts(cfg, pr, acc, kind)).rows
    return res
