"""needs.json files: loading, merging, writing, and tombstones for retired generated needs (D130).

Generated needs files (``generated/model-needs.json``, ``generated/cad-needs.json``) use the
sphinx-needs import format (``needimport``)::

    {"created": "", "current_version": "", "project": "<repo>-<what>",
     "versions": {"": {"needs": {"<ID>": {"id": ..., "type": ..., "title": ..., ...}}}}}

Tombstones: ``generated/retired-needs.json`` (same format). When a generated need disappears
from its source without being retired first, curatrix keeps a tombstone (ID, type, title,
``status: retired``, ``retired_on`` date, ``source_file``) until the next baseline, so that
downstream links still resolve and get the grace period (R4, D75).
"""
from __future__ import annotations

import datetime
import json
from pathlib import Path

GENERATED_FIELDS_ORDER = ("id", "type", "title", "status")


def needs_of(doc: dict) -> dict[str, dict]:
    v = doc.get("versions", {})
    cur = doc.get("current_version", "")
    if cur not in v and v:
        cur = sorted(v)[-1]
    return dict((v.get(cur) or {}).get("needs", {}))


def load(path: Path) -> dict[str, dict]:
    return needs_of(json.loads(Path(path).read_text()))


def load_built(paths: list[Path], own_only: bool = True) -> dict[str, dict]:
    """Needs from one or more needs.json files of a docs build. A need is taken from the
    document that owns it (is_external false) unless own_only is False."""
    out: dict[str, dict] = {}
    ext: dict[str, dict] = {}
    for p in paths:
        for nid, n in load(p).items():
            if n.get("is_external"):
                ext.setdefault(nid, n)
            else:
                out[nid] = n
    if not own_only:
        for nid, n in ext.items():
            out.setdefault(nid, n)
    return out


def doc(needs: dict[str, dict], project: str) -> dict:
    return {"created": "", "current_version": "", "project": project,
            "versions": {"": {"needs": {k: needs[k] for k in sorted(needs)}}}}


def dumps(d: dict) -> str:
    return json.dumps(d, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def write(path: Path, needs: dict[str, dict], project: str) -> str:
    text = dumps(doc(needs, project))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return text


# ------------------------------------------------------------------ tombstones (D130)
def update_tombstones(old: dict[str, dict], new: dict[str, dict], tombstones: dict[str, dict],
                      today: str | None = None) -> tuple[dict[str, dict], list[str]]:
    """Needs that were in `old`, are gone from `new` and were not retired get a tombstone.
    A tombstone whose ID is back in `new` is dropped. Returns (tombstones, messages)."""
    today = today or datetime.date.today().isoformat()
    out = dict(tombstones)
    msgs = []
    for nid, n in sorted(old.items()):
        if nid in new or nid in out:
            continue
        out[nid] = {"id": nid, "type": n.get("type", ""), "title": n.get("title", ""), "status": "retired",
                    "retired_on": today, "source_file": n.get("source_file", ""),
                    "content": f"Tombstone (D130): ``{nid}`` was deleted from its source on {today} without "
                               f"being retired first. It is kept until the next baseline."}
        msgs.append(f"tombstone {nid} ({'was ' + n.get('status', 'valid')}): deleted without retiring first")
    for nid in sorted(out):
        if nid in new:
            del out[nid]
            msgs.append(f"tombstone {nid} removed: the need is back in its source")
    return out, msgs


def prune_tombstones(tombstones: dict[str, dict], baseline_date: str | None) -> tuple[dict[str, dict], list[str]]:
    """Drop tombstones older than the last baseline (retired_on < baseline date)."""
    if not baseline_date:
        return tombstones, []
    keep, msgs = {}, []
    for nid, t in tombstones.items():
        if (t.get("retired_on") or "") < baseline_date:
            msgs.append(f"tombstone {nid} dropped (older than the last baseline, {baseline_date})")
        else:
            keep[nid] = t
    return keep, msgs
