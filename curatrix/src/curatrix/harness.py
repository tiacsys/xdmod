"""Wiring harnesses of an EE repo (task 5.22; XD-ADR-0127, XD-ADR-0129, XD-ADR-0133, XD-ADR-0135,
XD-ADR-0140): discovery, the 1:1 with the cable defs of the EE model (CK-F7), the harness ends
against the pin maps of both ports (CK-F1), the design output (``curatrix cam``) and the plain-Python
tables of the ``harness-<name>`` document.

A harness is one folder ``harness/<name>/`` with one WireViz YAML ``<name>.yml`` as entry point
(checks.yaml ``cad.harnesses``, e.g. ``["harness/*/*.yml"]``). It is 1:1 with a cable def of the EE
model, a def that specializes ``XdDomain::Cable`` and carries an ``EE-HAR`` ID; the YAML names it in
``metadata: {TraceID: EE-HAR-....}`` (WireViz keeps any metadata key). The folder is named after the
def (``CanaryCable`` -> ``canary-cable``). The cable def owns one port per end, typed by the
(conjugated) connector port def the end mates with; the model derives ``EE-HAR connects EE-PORT``
from them (``model.to_needs``).

Each connector of the YAML names the end port of the cable def it is, as a KiCad connector names
the port of its board def (owner decisions Q10, Q11 of tiacsys/xdmod#69), on three lines of its
``notes``: ``portName: boardEnd`` (the port usage; ``portName: -`` for none), ``portType:
CanaryHeader`` (its def, ``~X`` counts as ``X``) and ``portTypeID: EE-PORT-....`` (the def's ID,
which is also the port it mates with). WireViz shows the notes in the diagram and allows no other
free key on a connector. Its ``pins`` are the pin numbers of that port, its ``pinlabels`` the net
(signal) names of the port's pin map.

CK-F1 reads the YAML in plain Python: a subset of the WireViz connection syntax (connection sets of
``{designator: pins}`` entries, pin numbers, pin labels, ranges ``1-3``); anything else (mates,
templates, auto-generated designators) is reported as unsupported, never silently passed.

WireViz is GPL-3.0 (XD-ADR-0127): curatrix never imports it. ``cam`` runs the ``wireviz`` command
as a separate process under the limits of the use ``wireviz``.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from curatrix import ids as idmod

CABLE_DEF = "XdDomain::Cable"
NOTE_RE = re.compile(r"^\s*(portName|portType|portTypeID|Port):\s*(\S+)\s*$", re.M)
NO_PORT = "-"


class HarnessError(Exception):
    pass


# ------------------------------------------------------------------ discovery and reading
@dataclass
class Harness:
    name: str                 # folder name
    folder: Path
    yml: Path                 # the entry point <name>.yml
    data: dict = field(default_factory=dict)
    error: str = ""

    @property
    def trace_id(self) -> str:
        return str((self.data.get("metadata") or {}).get("TraceID") or "").strip()

    @property
    def title(self) -> str:
        return str((self.data.get("metadata") or {}).get("title") or self.name)

    def connectors(self) -> dict[str, dict]:
        c = self.data.get("connectors") or {}
        return c if isinstance(c, dict) else {}

    def cables(self) -> dict[str, dict]:
        c = self.data.get("cables") or {}
        return c if isinstance(c, dict) else {}


def patterns(cfg) -> list[str]:
    return list((cfg.section("cad") or {}).get("harnesses") or [])


def load(yml: Path) -> Harness:
    h = Harness(yml.parent.name, yml.parent, yml)
    try:
        d = yaml.safe_load(yml.read_text(encoding="utf-8"))
        if not isinstance(d, dict):
            raise ValueError("not a mapping")
        h.data = d
    except (OSError, ValueError, yaml.YAMLError) as e:
        h.error = f"not a WireViz YAML ({str(e).splitlines()[0] if str(e) else type(e).__name__})"
    return h


def files(cfg) -> list[Path]:
    """Every YAML file the ``cad.harnesses`` globs find (sorted)."""
    return sorted(p for p in cfg.globs(patterns(cfg)) if p.is_file())


def discover(cfg) -> list[Harness]:
    """The harnesses of a repo: the files whose stem is their folder's name."""
    return [load(f) for f in files(cfg) if f.stem == f.parent.name]


# ------------------------------------------------------------------ the EE model side
def cable_defs(m) -> tuple[dict[str, dict], list[str]]:
    """(cable defs by EE-HAR ID, findings): defs that specialize XdDomain::Cable directly."""
    out, findings = {}, []
    for p in m.user():
        if p.get("@type") != "PartDefinition":
            continue
        if CABLE_DEF not in {s.get("qualifiedName") or "" for s in m.supers(p)}:
            continue
        sid = p.get("declaredShortName") or ""
        if idmod.kind_of(sid) != "EE-HAR":
            findings.append(f"model {m.qn(p)}: a cable def ({CABLE_DEF}) without an EE-HAR ID (short name)")
            continue
        out[sid] = p
    return out, findings


def cable_ports(m, cable) -> list[tuple[str, str]]:
    """(port name, EE-PORT ID of its def) for each end of a cable def (``~X`` counts as X)."""
    from curatrix.connectors import board_ports
    return board_ports(m, cable)


def port_owners(m) -> dict[str, list[tuple[str, str, str, str]]]:
    """EE-PORT ID -> [(kind 'board'|'external', owner def name, owner ID or '', port name)] of the
    ports of boards and external parts typed by that def."""
    from curatrix import eeprojects
    from curatrix.connectors import board_ports
    boards, externals, _ = eeprojects.model_defs(m)
    out: dict[str, list[tuple[str, str, str, str]]] = {}
    for kind, defs in (("board", boards), ("external", externals)):
        for key, p in sorted(defs.items()):
            for pname, pid in board_ports(m, p):
                if pid:
                    own = key if idmod.kind_of(key) else ""
                    out.setdefault(pid, []).append((kind, p.get("name") or "", own, pname))
    return out


# ------------------------------------------------------------------ wiring (plain Python)
def _expand(v) -> list[str]:
    if v is None:
        return []
    if isinstance(v, list):
        return [x for e in v for x in _expand(e)]
    s = str(v).strip()
    m = re.fullmatch(r"(-?\d+)\s*-\s*(-?\d+)", s)
    if m:
        a, b = int(m.group(1)), int(m.group(2))
        step = 1 if b >= a else -1
        return [str(i) for i in range(a, b + step, step)]
    return [s]


def pins_of(conn: dict) -> tuple[list[str], list[str]]:
    """(pin numbers, pin labels) of a WireViz connector (pins default to 1..pincount)."""
    pins = [str(p) for p in conn.get("pins") or []]
    labels = [str(x) for x in conn.get("pinlabels") or []]
    if not pins:
        n = conn.get("pincount") or len(labels) or (1 if conn.get("style") == "simple" else 0)
        pins = [str(i) for i in range(1, int(n) + 1)]
    return pins, labels


@dataclass
class Wiring:
    groups: list[list[tuple[str, str]]]          # each: the (designator, pin|wire) joined by one conductor
    wires: list[tuple[tuple[str, str], tuple[str, str], tuple[str, str]]]   # (from end, (cable, wire), to end)
    unsupported: list[str]


def wiring(h: Harness) -> Wiring:
    """The conductors of a harness from its connection sets."""
    conns, cabs = h.connectors(), h.cables()
    parent: dict = {}
    unsupported: list[str] = []
    rows: list[list[tuple[str, str]]] = []

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def resolve(des: str, v: str, i: int) -> str | None:
        """A pin number for a connector (pin labels map to pins); a wire number for a cable (wire
        labels and unique colors map to wires, like WireViz); None if it cannot be read."""
        if des in conns:
            pins, labels = pins_of(conns[des])
            if v not in pins and v in labels:
                return pins[labels.index(v)]
            return v
        c = cabs[des] or {}
        if v.isdigit() or v.lower() == "s":
            return v.lower()
        for key in ("wirelabels", "colors"):
            vals = [str(x) for x in c.get(key) or []]
            if vals.count(v) == 1:
                return str(vals.index(v) + 1)
        unsupported.append(f"connection set {i}: {des} wire {v!r} is no wire number, unique wire label or unique "
                           f"color of the cable (color codes are not read)")
        return None

    for i, cs in enumerate(h.data.get("connections") or [], 1):
        if not isinstance(cs, list):
            unsupported.append(f"connection set {i}: not a list")
            continue
        entries = []
        for e in cs:
            if isinstance(e, dict) and len(e) == 1:
                des, v = next(iter(e.items()))
                des = str(des)
                if des not in conns and des not in cabs:
                    unsupported.append(f"connection set {i}: {des} is no connector or cable of this file "
                                       f"(templates and auto-generated designators are not read)")
                    entries = None
                    break
                vals = [resolve(des, x, i) for x in _expand(v)] or ["1"]
                if None in vals:
                    entries = None
                    break
                entries.append((des, vals))
            else:
                unsupported.append(f"connection set {i}: entry {e!r} (mates, arrows and bare designators are not read)")
                entries = None
                break
        if not entries:
            continue
        n = max(len(v) for _, v in entries)
        if any(len(v) not in (1, n) for _, v in entries):
            unsupported.append(f"connection set {i}: the entries have different lengths")
            continue
        for k in range(n):
            row = [(d, v[0] if len(v) == 1 else v[k]) for d, v in entries]
            for a, b in zip(row, row[1:]):
                parent[find(a)] = find(b)
            rows.append(row)
    # loops: a wire between two pins of one connector (WireViz `loops`), part of the conductors
    for des, c in conns.items():
        for lp in (c or {}).get("loops") or []:
            ps = [str(x) for x in (lp if isinstance(lp, list) else [lp])]
            if len(ps) != 2:
                unsupported.append(f"connector {des}: loop {lp!r} is not a pair of pins")
                continue
            a, b = ((des, x) for x in ps)
            parent[find(a)] = find(b)
    groups: dict = {}
    for x in list(parent):
        groups.setdefault(find(x), []).append(x)
    wires = []
    for row in rows:
        for j, (d, w) in enumerate(row):
            if d in cabs and 0 < j < len(row) - 1:
                wires.append((row[j - 1], (d, w), row[j + 1]))
    return Wiring(sorted(sorted(g) for g in groups.values()), wires, unsupported)


def port_fields(conn: dict) -> dict[str, str]:
    """The port lines of a connector's notes: portName, portType, portTypeID (and the old Port)."""
    return {m.group(1): m.group(2) for m in NOTE_RE.finditer(str(conn.get("notes") or ""))}


def port_of(conn: dict) -> str | None:
    """The EE-PORT a connector mates with (its portTypeID; the old ``Port:`` line), ``-`` or None."""
    f = port_fields(conn)
    if (f.get("portName") or "") == NO_PORT:
        return NO_PORT
    return f.get("portTypeID") or f.get("Port")


# ------------------------------------------------------------------ CK-F1: harness ends
def conformance(h: Harness, m, where: str) -> list[str]:
    """CK-F1 for one harness: every connector names the end port of the cable def it is
    (portName, portType, portTypeID; ``portName: -`` = none), each end by exactly one connector; each port's pin map is on the connector with its pin numbers and net names
    (pin labels); every conductor joins pins of one net; a pin-map net that another end carries is
    wired."""
    from curatrix.connectors import _ref_key, check_port_fields, pin_maps, port_table
    if h.error:
        return [f"{where}: {h.error}"]
    findings: list[str] = []
    maps, names = pin_maps(m)
    cables, _ = cable_defs(m)
    cable = cables.get(h.trace_id)
    ends_of = {n: (dn, did) for n, dn, did in port_table(m, cable)} if cable is not None else {}
    w = wiring(h)
    findings += [f"{where}: {u}" for u in w.unsupported]
    ports: dict[str, str] = {}                       # designator -> EE-PORT
    named: dict[str, list[str]] = {}                 # end port name -> designators
    for des, c in sorted(h.connectors().items()):
        c = c if isinstance(c, dict) else {}
        port, f = check_port_fields(port_fields(c), ends_of, f"connector {des}", where,
                                    "has no line `portName: ...` in its notes; name the end port of the cable def "
                                    "it is, or `portName: -` for none")
        if cable is not None:
            findings += f
        name = port_fields(c).get("portName") or ""
        if name in ends_of:
            named.setdefault(name, []).append(des)
        if port is None:
            continue
        if port not in maps:
            findings.append(f"{where}: connector {des}: portTypeID {port} is no connector port def (EE-PORT) of the EE model")
            continue
        ports[des] = port
        pins, labels = pins_of(c)
        label = dict(zip(pins, labels))
        for num, net in sorted(maps[port].items(), key=lambda kv: _ref_key(kv[0])):
            if num not in pins:
                findings.append(f"{where}: {des} ({names[port]}): pin {num} of the pin map is not on the connector")
            elif label.get(num) != net:
                findings.append(f"{where}: {des} ({names[port]}): pin {num} is labelled {label.get(num)!r}, "
                                f"the pin map says {net!r}")
    # conductors: one net per conductor; wired pins that the pin map does not have
    wired: set[tuple[str, str]] = set()
    for g in w.groups:
        ends = [(d, p) for d, p in g if d in h.connectors()]
        wired |= set(ends)
        nets = {}
        for d, p in ends:
            if d in ports:
                net = maps[ports[d]].get(p)
                if net is None:
                    findings.append(f"{where}: {d} ({names[ports[d]]}): pin {p} is wired, but the pin map has no pin {p}")
                else:
                    nets.setdefault(net, []).append(f"{d}:{p}")
        if len(nets) > 1:
            findings.append(f"{where}: one conductor joins different nets: "
                            + ", ".join(f"{n} ({' '.join(v)})" for n, v in sorted(nets.items())))
    for des, port in sorted(ports.items()):
        others = {net for d, p2 in ports.items() if d != des for net in maps[p2].values()}
        for num, net in sorted(maps[port].items(), key=lambda kv: _ref_key(kv[0])):
            if net in others and (des, num) not in wired:
                findings.append(f"{where}: {des} ({names[port]}): pin {num} ({net}) is not wired, but another end "
                                f"carries {net}")
    # the ends against the cable def's ports
    if cable is None:
        findings.append(f"{where}: TraceID {h.trace_id or '(none)'} names no cable def of the EE model (see CK-F7)")
        return findings
    for pname, (dname, pid) in ends_of.items():
        if not pid:
            findings.append(f"{where}: the end {pname} of the cable def {m.qn(cable)} is typed by no connector port "
                            f"def with an EE-PORT ID")
        elif len(named.get(pname, [])) != 1:
            got = named.get(pname, [])
            findings.append(f"{where}: the end {pname} ({dname}) of the cable def {m.qn(cable)} is named by {len(got)} "
                            f"connector(s) ({', '.join(sorted(got)) or 'none'}); exactly one names it in portName")
    if len(ends_of) < 2:
        findings.append(f"{where}: the cable def {m.qn(cable)} has {len(ends_of)} end(s); a cable has at least two "
                        f"(one port per end)")
    return findings


# ------------------------------------------------------------------ CK-F7: cable defs <-> harness folders
def one_to_one(cfg, m) -> list[str]:
    """CK-F7 for cables: each cable def has exactly one ``harness/<name>/<name>.yml`` whose
    ``metadata.TraceID`` is its EE-HAR, in the folder named after the def; and back."""
    from curatrix import eeprojects
    cables, findings = cable_defs(m)
    repo = cfg.repo.resolve()
    by_id: dict[str, list[Harness]] = {}
    for f in files(cfg):
        rel = f.resolve().relative_to(repo)
        if f.stem != f.parent.name:
            findings.append(f"{rel}: not the entry point of its folder; a harness folder harness/<name>/ has "
                            f"one WireViz YAML <name>.yml")
            continue
        h = load(f)
        if h.error:
            findings.append(f"{rel}: {h.error}")
            continue
        tid = h.trace_id
        if not tid:
            findings.append(f"{rel}: no metadata TraceID; set it to the EE-HAR ID of its cable def")
            continue
        if tid not in cables:
            findings.append(f"{rel}: TraceID {tid} names no cable def of the EE model ({CABLE_DEF})")
            continue
        by_id.setdefault(tid, []).append(h)
        want = eeprojects.kebab(cables[tid].get("name") or "")
        if want and h.name != want:
            findings.append(f"{rel}: the cable def {cables[tid].get('name')} ({tid}) gives the folder name "
                            f"harness/{want}/")
    for hid, p in sorted(cables.items()):
        hs = by_id.get(hid, [])
        if not hs:
            findings.append(f"model {m.qn(p)} ({hid}): no harness; create harness/{eeprojects.kebab(p.get('name') or '')}/"
                            f"{eeprojects.kebab(p.get('name') or '')}.yml with metadata TraceID {hid}")
        elif len(hs) > 1:
            findings.append(f"model {m.qn(p)} ({hid}): {len(hs)} harnesses name it "
                            f"({', '.join(str(x.yml.relative_to(cfg.repo)) for x in hs)}); exactly one")
    return findings


# ------------------------------------------------------------------ document tables (plain Python)
def pin_table(h: Harness) -> list[tuple[str, ...]]:
    """One row per wire: (from, from signal, wire, color, to, to signal)."""
    conns, cabs = h.connectors(), h.cables()

    def end(e):
        d, p = e
        if d not in conns:
            return f"{d}:{p}", ""
        pins, labels = pins_of(conns[d])
        return f"{d}:{p}", dict(zip(pins, labels)).get(p, "")

    def color(c, w):
        cols = [str(x) for x in (cabs.get(c) or {}).get("colors") or []]
        return cols[int(w) - 1] if w.isdigit() and 0 < int(w) <= len(cols) else ""

    rows = []
    for a, (c, w), b in wiring(h).wires:
        (fa, sa), (fb, sb) = end(a), end(b)
        rows.append((fa, sa, f"{c}:{w}", color(c, w), fb, sb))
    return rows


def bom(h: Harness) -> list[tuple[str, ...]]:
    """(designators, description, qty, unit, manufacturer, MPN), connectors by type, cables by
    length; like WireViz's BOM, from the YAML."""
    rows: dict[tuple, list] = {}

    def s(v):
        if isinstance(v, list):             # per-wire part data of a bundle
            return "; ".join(sorted({str(x) for x in v if x is not None}))
        return "" if v is None else str(v)

    for des, c in sorted(h.connectors().items()):
        c = c or {}
        if c.get("ignore_in_bom"):
            continue
        pins, _ = pins_of(c)
        desc = ", ".join(x for x in ("Connector", s(c.get("type")), s(c.get("subtype")),
                                     f"{len(pins)} pins" if pins else "") if x)
        key = (desc, "", s(c.get("manufacturer")), s(c.get("mpn")))
        rows.setdefault(key, [[], 0.0])
        rows[key][0].append(des)
        rows[key][1] += 1
    for des, c in sorted(h.cables().items()):
        c = c or {}
        if c.get("ignore_in_bom"):
            continue
        n = c.get("wirecount") or len(c.get("colors") or [])
        desc = ", ".join(x for x in ("Cable", s(c.get("type")),
                                     f"{n} x {s(c.get('gauge'))}".strip(" x") if n else "") if x)
        unit = s(c.get("length_unit") or "m")
        key = (desc, unit, s(c.get("manufacturer")), s(c.get("mpn")))
        rows.setdefault(key, [[], 0.0])
        rows[key][0].append(des)
        rows[key][1] += float(c.get("length") or 0)
    out = []
    for (desc, unit, man, mpn), (des, qty) in sorted(rows.items()):
        q = f"{qty:g}"
        out.append((", ".join(des), desc, q, unit, man, mpn))
    return out


# ------------------------------------------------------------------ cam (XD-ADR-0127, XD-ADR-0140)
def _git(repo: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True, timeout=60)


def out_dir(ws, cfg, name: str) -> Path:
    return ws.build(cfg.area) / "cam" / name


def latest(ws, cfg, name: str) -> dict | None:
    """The newest cam.json of a harness (local output), with its folder as ``_dir``."""
    best = None
    for f in out_dir(ws, cfg, name).glob("*/cam.json"):
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if rec.get("kind") == "harness" and (best is None or f.stat().st_mtime > best[0]):
            best = (f.stat().st_mtime, dict(rec, _dir=str(f.parent)))
    return best[1] if best else None


def run_one(ws, repo, cfg, h: Harness, log=print) -> dict:
    """WireViz on a copy of the YAML (with the version as the diagram label) in
    ``build/<area>/cam/<name>/<version>/``: ``<name>.svg``, ``.png``, ``.bom.tsv``, and ``cam.json``."""
    from curatrix import limits
    if h.error:
        raise HarnessError(f"{h.name}: {h.error}")
    from curatrix.cam import version
    ver, release = version(repo.path, h.name, h.folder)       # the boards' rule (XD-ADR-0140, XD-ADR-0142)
    short = ver.split("/", 1)[1] if "/" in ver else ver
    top = out_dir(ws, cfg, h.name) / short
    if top.exists():
        shutil.rmtree(top)
    src = top / "src"
    shutil.copytree(h.folder, src)
    data = dict(h.data)
    data["metadata"] = dict(data.get("metadata") or {}, version=ver)
    tweak = dict(data.get("tweak") or {})
    app = tweak.get("append") or []
    app = [app] if isinstance(app, str) else list(app)
    label = f"{h.title} {ver}".replace("\\", "\\\\").replace('"', '\\"')
    tweak["append"] = app + [f'\tlabel="{label}"\n', "\tlabelloc=b\n"]
    data["tweak"] = tweak
    yml = src / h.yml.name
    yml.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    out = top / h.name
    out.mkdir(parents=True)
    exe = ws.venv / "bin" / "wireviz"
    argv = [str(exe) if exe.exists() else "wireviz", "-f", "pst", "-o", str(out), "-O", h.name, str(yml)]
    log(f"  {h.name} {ver}: wireviz in {ws.rel(out)}")
    p = limits.run(argv, "wireviz", ws, cwd=str(src), capture_output=True, text=True)
    (top / "wireviz.log").write_text(p.stdout + p.stderr, encoding="utf-8")
    want = [out / f"{h.name}.svg", out / f"{h.name}.png", out / f"{h.name}.bom.tsv"]
    if p.returncode or not all(f.is_file() for f in want):
        raise HarnessError(f"{h.name}: wireviz: exit {p.returncode} {limits.explain_rc(p.returncode)}; "
                           f"log: {ws.rel(top / 'wireviz.log')}")
    head = _git(repo.path, "rev-parse", "HEAD").stdout.strip()
    rec = {"kind": "harness", "harness": h.name, "trace_id": h.trace_id, "version": ver, "release": release,
           "commit": head, "date": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
           "files": sorted(str(f.relative_to(top)) for f in out.rglob("*") if f.is_file())}
    (top / "cam.json").write_text(json.dumps(rec, indent=2) + "\n", encoding="utf-8")
    log(f"  {h.name}: {len(rec['files'])} files in {ws.rel(out)} ({'release' if release else 'preview'})")
    return rec


def run(ws, repo, cfg, name: str | None = None, log=print) -> list[dict]:
    hs = [h for h in discover(cfg) if name is None or h.name == name]
    if name is not None and not hs:
        raise HarnessError(f"no harness {name} in {repo.name} (checks.yaml cad.harnesses)")
    return [run_one(ws, repo, cfg, h, log) for h in hs]
