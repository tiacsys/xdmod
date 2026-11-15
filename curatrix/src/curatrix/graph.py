"""Graph rules on the merged needs of a docs build (trace-model.md §4; checks CK-A4, CK-B1-B3,
CK-B5, CK-B6, CK-G1/G2). sphinx-needs skips external needs in its own schema checks, so these
run here over every needs.json of a build (own and imported needs alike).

Back links are computed here from the outgoing links (never trusted from the files).
`draft` needs take part in structure checks but do not count as coverage (D130).
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from curatrix import ids as idmod
from curatrix import needs as needsmod

LINK_TYPES = ("refines", "raised_by", "addresses", "realizes", "satisfies", "configures", "conforms",
              "part_of", "implements", "verifies", "decided_by", "enforces", "follows", "result_of")
REQ_TYPES = ("sys-req", "sw-req", "ee-req", "me-req")
ORPHAN_TYPES = ("sw-arch", "ee-pcba", "ee-cmp", "me-asm", "me-part")
VALUE_FIELDS = ("quantity", "unit", "min", "max", "nominal")
# D132: hashed fields for suspect links
HASHED = ("title", "content", "status", *VALUE_FIELDS)


@dataclass
class Finding:
    rule: str
    level: str          # error | warning | report
    need: str
    message: str

    def __str__(self):
        return f"{self.rule} {self.need}: {self.message}"


@dataclass
class Graph:
    needs: dict[str, dict]
    owners: dict[str, list[str]] = field(default_factory=dict)   # id -> documents that own it (B5)

    def links(self, n: dict) -> dict[str, list[str]]:
        return {lt: list(n.get(lt) or []) for lt in LINK_TYPES if n.get(lt)}

    def back(self) -> dict[str, dict[str, list[str]]]:
        b: dict[str, dict[str, list[str]]] = defaultdict(lambda: defaultdict(list))
        for nid, n in self.needs.items():
            for lt, targets in self.links(n).items():
                for t in targets:
                    b[t][lt].append(nid)
        return b


def load(paths: list[Path]) -> Graph:
    """Merge the needs.json files of a build. Own needs win over imported copies."""
    owners: dict[str, list[str]] = defaultdict(list)
    for p in paths:
        for nid, n in needsmod.load(p).items():
            if not n.get("is_external"):
                owners[nid].append(str(p))
    return Graph(needsmod.load_built(paths, own_only=False), dict(owners))


def counts(n: dict | None) -> bool:
    return bool(n) and n.get("status", "valid") == "valid"


def check(g: Graph, stage: str) -> list[Finding]:
    out: list[Finding] = []
    back = g.back()
    N = g.needs
    for nid, n in sorted(N.items()):
        t = n.get("type", "")
        st = n.get("status", "valid")
        if st == "retired":
            continue
        # R1 (CK-B1): every SYS-REQ is refined by a domain requirement or satisfied by a SYS-EL
        if t == "sys-req":
            ok = any(counts(N.get(s)) and N[s].get("type") in ("sw-req", "ee-req", "me-req") for s in back[nid]["refines"]) \
                or any(counts(N.get(s)) and N[s].get("type") == "sys-el" for s in back[nid]["satisfies"])
            if not ok:
                out.append(Finding("CK-B1", "error", nid, "not refined by a domain requirement and not satisfied by a SYS-EL (R1)"))
        # R2 (CK-B2): every requirement has a verifies link (warning in iteration 1, D99)
        if t in REQ_TYPES and not any(counts(N.get(s)) for s in back[nid]["verifies"]):
            out.append(Finding("CK-B2", "warning", nid, "no (valid) test case verifies it (R2)"))
        # R3 (CK-A4): no orphans
        if (t in ORPHAN_TYPES or (t == "sys-el" and n.get("layer") == "product")) \
                and not (n.get("realizes") or n.get("satisfies")):
            out.append(Finding("CK-A4", "error", nid, "orphan: neither realizes nor satisfies anything (R3)"))
        # R4 (CK-B3): links to retired needs; grace until the baseline (D75)
        for lt, targets in g.links(n).items():
            for tgt in targets:
                tn = N.get(tgt)
                if tn is not None and tn.get("status") == "retired":
                    out.append(Finding("CK-B3", "error" if stage == "baseline" else "warning", nid,
                                       f"{lt} -> {tgt}, which is retired (R4; fails at the baseline)"))
                elif tn is None:
                    out.append(Finding("CK-A1", "error", nid, f"{lt} -> {tgt}: unknown ID"))
        # R5 (CK-A5): HIL results carry the firmware hash and the pinned SHAs
        if t == "tr" and n.get("method") == "hil" and not (n.get("firmware_sha256") and n.get("shas")):
            out.append(Finding("CK-A5", "error", nid, "HIL result without firmware_sha256 and shas (R5)"))
        # CK-A3: ID format and kind
        if t not in ("testfile", "testsuite", "testcase"):
            k = idmod.kind_of(nid)
            if k is None:
                out.append(Finding("CK-A3", "error", nid, "ID does not match the ID scheme"))
            elif t and t != ("tr" if k == "TR" else idmod.directive_of(k)):
                out.append(Finding("CK-A3", "error", nid, f"ID kind {k} does not match the need type {t}"))
    # B5: duplicates across documents/repos
    for nid, docs in sorted(g.owners.items()):
        if len(set(docs)) > 1:
            out.append(Finding("CK-B5", "error", nid, f"defined in more than one document: {sorted(set(docs))}"))
    return out


def stale_evidence(g: Graph, pins: dict[str, str]) -> list[Finding]:
    """R5a (CK-B6): a TR counts only if its recorded SHAs match the current pins (D131)."""
    out = []
    for nid, n in sorted(g.needs.items()):
        if n.get("type") != "tr" or not n.get("shas"):
            continue
        for entry in n["shas"]:
            repo, _, sha = entry.partition("=")
            pin = pins.get(repo)
            if pin and not (pin.startswith(sha) or sha.startswith(pin)):
                out.append(Finding("CK-B6", "report", nid, f"stale: {repo} {sha} != pin {pin[:12]} (R5a)"))
                break
    return out


# ------------------------------------------------------------------ needs-diff (CK-G1, R7)
def fingerprint(n: dict) -> str:
    data = {k: n.get(k) for k in HASHED} | {k: sorted(n.get(k) or []) for k in LINK_TYPES}
    return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()[:12]


def needs_diff(old: dict[str, dict], new: dict[str, dict]) -> tuple[list[str], list[str], int]:
    """(changes, impact lines, number of suspect/dangling links). Port of the spike's needs_diff:
    changed = a hashed field or a link changed (D132); SUSPECT = a link whose target changed,
    directly or transitively over the old graph's back links (R7); DANGLING = link to a missing ID."""
    removed = sorted(set(old) - set(new))
    added = sorted(set(new) - set(old))
    changed = sorted(i for i in set(old) & set(new) if fingerprint(old[i]) != fingerprint(new[i]))
    lines = [f"- REMOVED `{i}` ({old[i].get('type')}): {old[i].get('title')}" for i in removed]
    lines += [f"- ADDED `{i}` ({new[i].get('type')}): {new[i].get('title')}" for i in added]
    for i in changed:
        diffs = [f"{k}: {old[i].get(k)!r} -> {new[i].get(k)!r}" for k in (*HASHED, *LINK_TYPES)
                 if (old[i].get(k) or None) != (new[i].get(k) or None)]
        lines.append(f"- CHANGED `{i}` ({new[i].get('type')}): " + "; ".join(diffs))
    impact = []
    for nid, n in sorted(new.items()):
        for lt in LINK_TYPES:
            for t in n.get(lt) or []:
                if t not in new:
                    impact.append(f"- DANGLING `{nid}` --{lt}--> `{t}` (target {'removed' if t in old else 'unknown'})")
    oldg = Graph(old)
    back = oldg.back()
    seen = set()

    def walk(target, path):
        for lt, srcs in back.get(target, {}).items():
            for src in sorted(srcs):
                key = (src, lt, target)
                if key in seen:
                    continue
                seen.add(key)
                kind = "direct" if len(path) == 1 else "transitive"
                gone = (" (source removed)" if src not in new
                        else " (link removed since)" if target not in (new[src].get(lt) or []) else "")
                impact.append(f"- SUSPECT ({kind}) `{src}` --{lt}--> `{target}`{gone}; cause: "
                              + " <- ".join(f"`{p}`" for p in path))
                walk(src, path + [src])

    for t in sorted(set(removed) | set(changed)):
        walk(t, [t])
    return lines, impact, len(impact)


def diff_report(old: dict, new: dict, before: str, after: str) -> tuple[str, int]:
    changes, impact, n = needs_diff(old, new)
    text = "\n".join([
        "# needs-diff", "",
        f"- before: `{before}` ({len(old)} needs)", f"- after: `{after}` ({len(new)} needs)", "",
        "## Changed needs", "", *(changes or ["- none"]), "",
        "## Impact on links (suspect links, R7)", "", *(impact or ["- none"]), ""])
    return text, n
