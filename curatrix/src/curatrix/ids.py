"""IDs and the ledger (id-scheme.md; D78, D79, D120, D128, D133).

Ledger ``<repo>/ids.yaml``: every number ever issued, per kind, one per line, append-only::

    # Every number issued per kind, one per line. Append-only: a number here is never issued again.
    SYS-REQ:
      - 41
      - 42
    SYS-NEED: []

A repo's ledger lists the kinds it owns (a kind with no number yet is ``KIND: []``).
Placeholders ``<KIND>-NEW-<tag>`` (e.g. ``SYS-REQ-NEW-a``) are replaced by ``curatrix ids fix``;
the same placeholder gets the same real ID in every file. ``SYS-VIEW`` is a reserved non-need
kind (SysML view short names): issued from the ledger, skipped by CK-A3.
"""
from __future__ import annotations

import re
import subprocess
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from curatrix import tracemodel

# Domains and kinds come from needs/needs_config.toml (task 5.2, D64h); a test compares them with
# the toml's id_regex, so the two ID patterns can't drift.
DOMAINS = tracemodel.domains()
TR_DOMAINS = ("SYS", "SW", "EE", "ME", "INT")   # domains whose test results get TR IDs (id-scheme.md §6)
_D = "|".join(DOMAINS)
# id-scheme.md §2 (exact), plus usage IDs <ID>.<n> (D128)
ID_RE = re.compile(
    rf"^(?:(?:{_D})-[A-Z]{{2,5}}-[0-9]{{4,}}(?:\.[0-9]+)?"
    rf"|TR-(?:{'|'.join(TR_DOMAINS)})-[A-Z]{{2,5}}-[0-9]{{4,}}-[0-9a-f]{{8}})$")
# an ID inside text (word boundaries; not inside a longer token)
ID_IN_TEXT = re.compile(rf"(?<![A-Za-z0-9_-])((?:{_D})-[A-Z]{{2,5}})-([0-9]{{4,}})(?![0-9])")
PLACEHOLDER = re.compile(rf"(?<![A-Za-z0-9_-])((?:{_D})-[A-Z]{{2,5}})-NEW-([A-Za-z0-9_]+)")
KIND_RE = re.compile(rf"^(?:{_D})-[A-Z]{{2,5}}$")
_ID_KIND = re.compile(rf"^((?:{_D})-[A-Z]{{2,5}})-[0-9]{{4,}}(?:\.[0-9]+)?$")

# id-scheme.md §3: the need-type kinds (from needs_config.toml), and the reserved non-need kind
NEED_KINDS = tracemodel.need_kinds()
RESERVED_KINDS = {"SYS-VIEW"}
ALL_KINDS = NEED_KINDS | RESERVED_KINDS

LEDGER_HEADER = ("# ID ledger (id-scheme.md §4, D133). Every number issued per kind, one per line.\n"
                 "# Append-only: a number listed here is never issued again. Edit it only through\n"
                 "# `curatrix ids new` / `curatrix ids fix`.\n")

# files scanned for IDs and placeholders (git-tracked, by suffix)
TEXT_SUFFIXES = {".rst", ".md", ".txt", ".sysml", ".kerml", ".py", ".c", ".h", ".cpp", ".hpp", ".dts",
                 ".dtsi", ".overlay", ".yaml", ".yml", ".json", ".kicad_sch", ".kicad_pro", ".kicad_pcb",
                 ".svg", ".toml", ".cmake"}
SKIP_NAMES = {"ids.yaml"}


class IdError(Exception):
    pass


def kind_of(nid: str) -> str | None:
    """'SYS-REQ-0012' -> 'SYS-REQ'; 'SYS-EL-0012.1' -> 'SYS-EL'; TR IDs -> 'TR'."""
    if nid.startswith("TR-"):
        return "TR" if ID_RE.match(nid) else None
    m = _ID_KIND.match(nid)
    return m.group(1) if m else None


def number_of(nid: str) -> int:
    return int(re.match(r"^.*?-([0-9]{4,})(?:\.[0-9]+)?$", nid).group(1))


def format_id(kind: str, n: int) -> str:
    return f"{kind}-{n:04d}"


def valid_id(nid: str) -> bool:
    return bool(ID_RE.match(nid))


def directive_of(kind: str) -> str:
    """Need type (directive) name for a kind: 'SYS-REQ' -> 'sys-req'."""
    return kind.lower()


# ------------------------------------------------------------------ ledger
@dataclass
class Ledger:
    path: Path
    kinds: dict[str, list[int]] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> "Ledger":
        if not path.is_file():
            return cls(path, {})
        data = yaml.safe_load(path.read_text()) or {}
        if not isinstance(data, dict):
            raise IdError(f"{path}: the ledger must be a mapping KIND -> [numbers]")
        kinds = {}
        for k, v in data.items():
            if not KIND_RE.match(str(k)):
                raise IdError(f"{path}: {k!r} is not a kind like SYS-REQ")
            nums = [int(x) for x in (v or [])]
            if len(set(nums)) != len(nums):
                raise IdError(f"{path}: {k} lists a number twice")
            kinds[str(k)] = nums
        return cls(path, kinds)

    def text(self) -> str:
        out = [LEDGER_HEADER]
        for k in sorted(self.kinds):
            nums = self.kinds[k]
            if not nums:
                out.append(f"{k}: []\n")
            else:
                out.append(f"{k}:\n" + "".join(f"  - {n}\n" for n in nums))
        return "".join(out)

    def save(self) -> None:
        self.path.write_text(self.text())

    def highest(self, kind: str) -> int:
        return max(self.kinds.get(kind) or [0])

    def owns(self, kind: str) -> bool:
        return kind in self.kinds

    def issue(self, kind: str, used: set[int] = frozenset()) -> int:
        """Next number above everything in the ledger and in the sources; appended."""
        if kind not in self.kinds:
            raise IdError(f"{self.path}: this ledger does not own kind {kind} (add '{kind}: []' to own it)")
        n = max([self.highest(kind), *used, 0]) + 1
        self.kinds[kind].append(n)
        return n


def find_ledger_for(ws, kind: str, repo_name: str | None = None) -> Ledger:
    """The ledger that owns `kind`: the given repo's, or the only one in the workspace that lists it."""
    if repo_name:
        return Ledger.load(ws.repo(repo_name).path / "ids.yaml")
    owners = [Ledger.load(r.path / "ids.yaml") for r in ws.repos if (r.path / "ids.yaml").is_file()]
    owners = [lg for lg in owners if lg.owns(kind)]
    if len(owners) == 1:
        return owners[0]
    if not owners:
        raise IdError(f"no ids.yaml in the workspace owns kind {kind}; add '{kind}: []' to the owning repo's ledger")
    raise IdError(f"kind {kind} is owned by several ledgers ({', '.join(str(o.path) for o in owners)}); use --repo")


# ------------------------------------------------------------------ scanning sources
def source_files(repo: Path, exclude: list[str] | tuple = ()) -> list[Path]:
    """Git-tracked (or, outside git, all) text and CAD files of a repo, minus `exclude` globs
    (relative to the repo, fnmatch style, e.g. "docs/examples/**", "*.md")."""
    import fnmatch
    try:
        out = subprocess.run(["git", "-C", str(repo), "ls-files", "-co", "--exclude-standard"],
                             capture_output=True, text=True, check=True, timeout=60).stdout
        files = [repo / f for f in out.splitlines()]
    except (OSError, subprocess.SubprocessError):
        files = [p for p in repo.rglob("*") if p.is_file() and ".git" not in p.parts]
    def excluded(f: Path) -> bool:
        rel = f.relative_to(repo).as_posix()
        return any(fnmatch.fnmatch(rel, pat) for pat in exclude)
    return sorted(f for f in files if f.is_file() and f.name not in SKIP_NAMES
                  and (f.suffix in TEXT_SUFFIXES or f.suffix == ".FCStd") and not excluded(f))


def read_text(p: Path) -> str:
    if p.suffix == ".FCStd":
        try:
            with zipfile.ZipFile(p) as z:
                return z.read("Document.xml").decode("utf-8", "replace")
        except (zipfile.BadZipFile, KeyError):
            return ""
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ""


def scan_ids(files: list[Path]) -> dict[str, set[int]]:
    """Numbers used in the sources, per kind."""
    used: dict[str, set[int]] = {}
    for f in files:
        for m in ID_IN_TEXT.finditer(read_text(f)):
            used.setdefault(m.group(1), set()).add(int(m.group(2)))
    return used


@dataclass
class Placeholder:
    token: str          # SYS-REQ-NEW-a
    kind: str
    file: Path
    line: int


def scan_placeholders(files: list[Path]) -> list[Placeholder]:
    out = []
    for f in files:
        text = read_text(f)
        for m in PLACEHOLDER.finditer(text):
            out.append(Placeholder(m.group(0), m.group(1), f, text.count("\n", 0, m.start()) + 1))
    return out


def fix(repo: Path, ledger: Ledger, files: list[Path] | None = None, dry_run: bool = False,
        exclude: list[str] | tuple = ()) -> dict[str, str]:
    """Replace every placeholder in the repo's text files with a newly issued ID.
    Returns {placeholder: new ID}. The same placeholder gets the same ID everywhere."""
    files = files if files is not None else source_files(repo, exclude)
    phs = scan_placeholders(files)
    used = scan_ids(files)
    mapping: dict[str, str] = {}
    for ph in phs:  # sorted by file, then position: deterministic
        if ph.token in mapping:
            continue
        if ph.file.suffix == ".FCStd":
            raise IdError(f"{ph.file}:{ph.line}: placeholder {ph.token} inside a .FCStd; set the TraceID in FreeCAD")
        n = ledger.issue(ph.kind, used.get(ph.kind, set()))
        used.setdefault(ph.kind, set()).add(n)
        mapping[ph.token] = format_id(ph.kind, n)
    if mapping and not dry_run:
        pat = re.compile("|".join(re.escape(t) + r"(?![A-Za-z0-9_])" for t in sorted(mapping, key=len, reverse=True)))
        for f in sorted({ph.file for ph in phs}):
            text = f.read_text(encoding="utf-8")
            new = pat.sub(lambda m: mapping[m.group(0)], text)
            if new != text:
                f.write_text(new, encoding="utf-8")
        ledger.save()
    return mapping


def new(ledger: Ledger, kind: str, repo: Path, file: Path | None = None, exclude: list[str] | tuple = ()) -> str:
    """Issue one ID. With `file`, replace that file's first placeholder of this kind."""
    if kind not in ALL_KINDS:
        raise IdError(f"unknown kind {kind}; known: {', '.join(sorted(ALL_KINDS))}")
    used = scan_ids(source_files(repo, exclude)).get(kind, set())
    nid = format_id(kind, ledger.issue(kind, used))
    if file is not None:
        text = file.read_text(encoding="utf-8")
        m = next((m for m in PLACEHOLDER.finditer(text) if m.group(1) == kind), None)
        if m is None:
            raise IdError(f"{file}: no {kind}-NEW-… placeholder to replace")
        token = m.group(0)
        text = re.sub(re.escape(token) + r"(?![A-Za-z0-9_])", nid, text)
        file.write_text(text, encoding="utf-8")
    ledger.save()
    return nid


# ------------------------------------------------------------------ checks CK-C1, CK-C2, CK-A3
def check_placeholders(files: list[Path], root: Path) -> list[str]:
    return [f"{p.file.relative_to(root)}:{p.line}: placeholder {p.token} (run `curatrix ids fix`)"
            for p in scan_placeholders(files)]


def check_ledger(files: list[Path], ledger: Ledger, root: Path) -> list[str]:
    """CK-C2: every ID of an owned kind in the sources is listed in the ledger (so the ledger is
    never behind the sources). Kinds the ledger does not own are upstream references."""
    errs = []
    for f in files:
        text = read_text(f)
        for m in ID_IN_TEXT.finditer(text):
            kind, n = m.group(1), int(m.group(2))
            if ledger.owns(kind) and n not in ledger.kinds[kind]:
                line = text.count("\n", 0, m.start()) + 1
                errs.append(f"{f.relative_to(root)}:{line}: {kind}-{n:04d} is not in {ledger.path.name} "
                            f"(highest issued: {ledger.highest(kind):04d})")
    return sorted(set(errs))
