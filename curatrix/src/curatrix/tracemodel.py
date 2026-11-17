"""The trace model as curatrix sees it, read from ``xdmod/needs/needs_config.toml`` (D64h).

needs_config.toml is the single source of the need types, their ID kinds and the link types
(task 5.2, Phase 4 review P4-9). curatrix never keeps its own copy of these lists: graph rules,
the ID ledger and the ID patterns are derived here.
"""
from __future__ import annotations

import functools
import os
import re
import tomllib
from pathlib import Path

XDMOD = Path(__file__).resolve().parents[3]
KIND_RE = re.compile(r"^([A-Z]+)-([A-Z]{2,5})-$")     # prefix of a need type with a ledger kind


def config_path() -> Path:
    env = os.environ.get("XD_NEEDS_CONFIG")
    if env:
        return Path(env)
    p = XDMOD / "needs" / "needs_config.toml"
    if p.is_file():
        return p
    from curatrix.ws import Workspace          # an installed curatrix: the workspace's xdmod
    return Workspace().xdmod / "needs" / "needs_config.toml"


@functools.cache
def config() -> dict:
    return tomllib.loads(config_path().read_text())["needs"]


def types() -> list[dict]:
    return list(config()["types"])


def link_types() -> tuple[str, ...]:
    """Every link type declared on any need type, in the order of the file."""
    out: list[str] = []
    for t in types():
        for lt in t.get("links") or {}:
            if lt not in out:
                out.append(lt)
    return tuple(out)


def need_kinds() -> set[str]:
    """ID kinds (``SYS-REQ``) of the need types with a ledger: prefix ``<DOMAIN>-<KIND>-``. Test
    results (``TR-...``, generated) and the sphinx-test-reports types have none."""
    out = set()
    for t in types():
        m = KIND_RE.match(t.get("prefix", ""))
        if m and m.group(1) != "TR":
            out.add(m.group(1) + "-" + m.group(2))
    return out


def domains() -> tuple[str, ...]:
    """Domains of the ID scheme, in the order of the file (``SYS``, ``INT``, ``SW``, ...)."""
    out: list[str] = []
    for t in types():
        m = KIND_RE.match(t.get("prefix", ""))
        if m and m.group(1) != "TR" and m.group(1) not in out:
            out.append(m.group(1))
    return tuple(out)


def directive_of(kind: str) -> str | None:
    for t in types():
        if t.get("prefix") == kind + "-":
            return t["directive"]
    return None


def req_types() -> tuple[str, ...]:
    """Requirement need types: directives named ``<domain>-req`` (id-scheme.md: kind REQ)."""
    return tuple(t["directive"] for t in types() if t["directive"].endswith("-req"))
