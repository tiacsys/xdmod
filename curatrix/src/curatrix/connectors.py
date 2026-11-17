"""Connector pin tables of a KiCad project, in plain Python (task 5.18; EE-6, XD-ADR-0128,
XD-ADR-0129; checks CK-D7, CK-D8, CK-F1).

``generated/<project>.connectors.json`` lists every connector of a project: designator, its
``Port`` field (the ``EE-PORT`` it implements, ``-`` = none), value, footprint, and per pin the
number, the pin name and the net. The nets come from the schematic's connectivity, computed here
without KiCad:

* connection points: wire ends, pins, labels, junctions, sheet pins; items at the same point
  connect; inside a wire only junctions and labels join it (a wire end or a pin on the middle of
  another wire does not, as in KiCad 10 without a junction); crossing wires do not connect;
* labels join by name: local labels within one sheet instance, global labels and power symbols
  everywhere, hierarchical labels with the sheet pin of the same name on the parent sheet. Only a
  power symbol with a ``power_in`` pin names and joins (``PWR_FLAG`` does not); a hidden
  ``power_in`` pin of a normal symbol joins the global net of its pin name (older libraries);
* net names as KiCad 10 writes them in the XML netlist: a global label; else a power symbol; else
  the local or hierarchical label of the shallowest sheet with its sheet path (``/CANARY_A``,
  ``/sub/X``); else ``Net-(<ref><unit>-<pin name>)`` or ``Net-(<ref><unit>-Pad<n>)`` of one of its
  pins (pins with a name first); a pin alone ``unconnected-(<ref>-<pin name>-Pad<n>)``;
* the library symbol of a placed symbol is its ``lib_name`` if it has one, else its ``lib_id``;
* buses are not read: a sheet with a bus is listed under ``unsupported`` in the file, and CK-D7
  and CK-F1 report it.

The extraction equals KiCad's netlist (every pin of every symbol) on the KiCad demos
complex_hierarchy, ecc83-pp, multichannel_mixer, StickHub and interf_u; on video (buses through
hierarchical sheets) it does not, and says so.

KiCad's XML netlist is the reference: CK-D8 compares this extraction with
``kicad-cli sch export netlist --format kicadxml`` (local, P5-15). CK-D7 regenerates the file
and compares it with the committed one (plain Python, so also in CI). CK-F1 compares connectors
with the pin maps of the EE model.
"""
from __future__ import annotations

import json
import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

from curatrix.cad import _children, _props, sexpr

CONNECTOR_REF = re.compile(r"^(J|P|CN)\d")
NO_PORT = "-"
SCALE = 10000                       # file units (mm, 4 decimals) -> integers


def is_connector(ref: str, fields: dict) -> bool:
    return "Port" in fields or bool(CONNECTOR_REF.match(ref))


def _pt(x, y) -> tuple[int, int]:
    return (round(float(x) * SCALE), round(float(y) * SCALE))


def _at(node):
    a = _children(node, "at")
    if not a:
        return None
    return a[0][1:4] + [0] * (4 - len(a[0]))


def _flag(node, name) -> bool:
    c = _children(node, name)
    return bool(c) and (len(c[0]) == 1 or c[0][1] in ("yes", "true"))


def transform(px: float, py: float, at, mirror: str | None) -> tuple[int, int]:
    """A library point of a placed symbol, in sheet coordinates (KiCad's TRANSFORM: library Y
    points up, the sheet's Y down; rotation counterclockwise on screen; then the mirror)."""
    x, y = px, -py
    rot = float(at[2] or 0) % 360
    c, s = round(math.cos(math.radians(rot))), round(math.sin(math.radians(rot)))
    x, y = x * c + y * s, -x * s + y * c
    if mirror == "x":
        y = -y
    elif mirror == "y":
        x = -x
    return _pt(float(at[0]) + x, float(at[1]) + y)


@dataclass
class Pin:
    number: str
    name: str
    pos: tuple[int, int]


@dataclass
class Sym:
    ref: str
    fields: dict
    lib_id: str
    value: str
    footprint: str
    sheet: str                 # sheet path names, e.g. "/" or "/sub/"
    inst: str                  # sheet instance (uuid path)
    power: bool
    pins: list[Pin] = field(default_factory=list)


class _UF:
    def __init__(self):
        self.p: dict = {}

    def find(self, a):
        self.p.setdefault(a, a)
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb


def _lib_pins(lib_sym, unit: int, body: int) -> list[tuple[str, str, float, float, str, bool]]:
    """(number, name, x, y, electrical type, hidden) of a library symbol's pins for one unit and
    body style."""
    out = []
    for sub in _children(lib_sym, "symbol"):
        m = re.search(r"_(\d+)_(\d+)$", sub[1] if len(sub) > 1 else "")
        if not m:
            continue
        u, b = int(m.group(1)), int(m.group(2))
        if u not in (0, unit) or b not in (0, body):
            continue
        for p in _children(sub, "pin"):
            at = _at(p)
            num = _children(p, "number")
            nm = _children(p, "name")
            name = nm[0][1] if nm and len(nm[0]) > 1 else ""
            hidden = "hide" in p[1:] or _flag(p, "hide")
            out.append((num[0][1] if num and len(num[0]) > 1 else "", "" if name == "~" else name,
                        float(at[0]), float(at[1]), p[1] if len(p) > 1 and isinstance(p[1], str) else "", hidden))
    return out


def _units(lib_sym) -> int:
    us = set()
    for sub in _children(lib_sym, "symbol"):
        m = re.search(r"_(\d+)_(\d+)$", sub[1] if len(sub) > 1 else "")
        if m and int(m.group(1)) > 0:
            us.add(int(m.group(1)))
    return len(us)


def _power_kind(lib_sym) -> str | None:
    """global | local for a power symbol (``(power)``, ``(power global)``, ``(power local)``)."""
    c = _children(lib_sym, "power")
    if not c:
        return None
    return "local" if len(c[0]) > 1 and c[0][1] == "local" else "global"


def _on_segment(p, a, b) -> bool:
    (x, y), (x1, y1), (x2, y2) = p, a, b
    if (x2 - x1) * (y - y1) - (y2 - y1) * (x - x1) != 0:
        return False
    return min(x1, x2) <= x <= max(x1, x2) and min(y1, y2) <= y <= max(y1, y2)


@dataclass
class Netlist:
    symbols: list[Sym]
    nets: dict[tuple[str, str], str]           # (ref, pin number) -> net name
    files: list[Path]
    findings: list[str] = field(default_factory=list)   # what the reader does not support (buses)


# net name priority of the items that can name a net (KiCad 10: a global label wins over a power
# symbol, a power symbol over a local label)
PRIORITY = {"global_label": 7, "power": 6, "power_local": 5, "label": 4, "hierarchical_label": 3, "sheet_pin": 2}


def netlist(root_sch: Path) -> Netlist:
    """Symbols and the net of every pin, from the schematic files (hierarchy followed)."""
    uf = _UF()
    symbols: list[Sym] = []
    labels: list[tuple[str, str, int, str, object]] = []      # (kind, name, depth, sheet path, node)
    files: list[Path] = []
    findings: list[str] = []
    pending_sheet_pins: dict[tuple[str, str], object] = {}    # (child inst, pin name) -> parent node
    unit_letter: dict[int, str] = {}                           # id(sym) -> "A", "B", ... (multi-unit symbols)

    def uuid_of(node) -> str:
        u = _children(node, "uuid")
        return u[0][1] if u and len(u[0]) > 1 else ""

    def visit(sch: Path, path: str, inst: str | None, depth: int):
        if depth > 20:
            return
        if sch.resolve() not in [f.resolve() for f in files]:
            files.append(sch)
        tree = sexpr(sch.read_text(encoding="utf-8"))
        if inst is None:
            inst = "/" + uuid_of(tree)
        libs = {s[1]: s for s in (_children(tree, "lib_symbols")[0][1:] if _children(tree, "lib_symbols") else [])
                if isinstance(s, list) and len(s) > 1}
        if _children(tree, "bus") or _children(tree, "bus_entry"):
            findings.append(f"{sch.name}: buses are not read yet; nets through a bus are missing here "
                            f"(CK-D8 compares with KiCad)")
        mid_ok: set[tuple[int, int]] = set()      # points that join a wire also inside it

        def pnode(xy, inside=False):
            if inside:
                mid_ok.add(xy)
            return ("pt", inst, xy)

        segs = []
        for w in _children(tree, "wire"):
            pts = [_pt(c[1], c[2]) for c in _children(_children(w, "pts")[0], "xy")]
            for a, b in zip(pts, pts[1:]):
                segs.append((a, b))
                uf.union(pnode(a), pnode(b))
        for kind in ("junction", "no_connect"):
            for j in _children(tree, kind):
                at = _at(j)
                uf.find(pnode(_pt(at[0], at[1]), inside=kind == "junction"))
        for kind in ("label", "global_label", "hierarchical_label"):
            for lb in _children(tree, kind):
                at = _at(lb)
                labels.append((kind, lb[1], depth, path, pnode(_pt(at[0], at[1]), inside=True)))
                if kind == "hierarchical_label" and (inst, lb[1]) in pending_sheet_pins:
                    uf.union(pending_sheet_pins[(inst, lb[1])], ("pt", inst, _pt(at[0], at[1])))
        for s in _children(tree, "symbol"):
            lid = _children(s, "lib_id")
            if not lid:
                continue
            ln = _children(s, "lib_name")          # the cached symbol's name when it differs from the library
            lib = libs.get(ln[0][1]) if ln and len(ln[0]) > 1 else None
            lib = lib or libs.get(lid[0][1])
            props = _props(s)
            ref = props.get("Reference", "")
            for ins in _children(s, "instances"):
                for proj in _children(ins, "project"):
                    for p in _children(proj, "path"):
                        if len(p) > 1 and p[1] == inst and _children(p, "reference"):
                            ref = _children(p, "reference")[0][1]
            if lib is None:
                findings.append(f"{sch.name}: {ref}: library symbol {lid[0][1]} is not in the sheet's lib_symbols")
                continue
            at = _at(s)
            mir = _children(s, "mirror")
            unit = int((_children(s, "unit") or [[0, 1]])[0][1])
            body = int((_children(s, "body_style") or _children(s, "convert") or [[0, 1]])[0][1])
            power = _power_kind(lib)
            sym = Sym(ref, props, lid[0][1], props.get("Value", ""), props.get("Footprint", ""), path, inst,
                      power is not None or ref.startswith("#"))
            if _units(lib) > 1:
                unit_letter[id(sym)] = chr(ord("A") + unit - 1)
            for num, name, x, y, etype, hidden in _lib_pins(lib, unit, body):
                pos = transform(x, y, at, mir[0][1] if mir and len(mir[0]) > 1 else None)
                sym.pins.append(Pin(num, name, pos))
                uf.union(("pin", inst, ref, num, id(sym)), pnode(pos))
                if etype == "power_in" and power is not None:
                    # a power symbol names and joins its net (PWR_FLAG, power_out, does not)
                    labels.append(("power" if power == "global" else "power_local", sym.value, depth, path,
                                   ("pt", inst, pos)))
                elif etype == "power_in" and hidden and name:
                    # a hidden power input of a normal symbol joins the global net of its name
                    labels.append(("power", name, depth, path, ("pt", inst, pos)))
            symbols.append(sym)
        sheets = []
        for sh in _children(tree, "sheet"):
            p = _props(sh)
            name = p.get("Sheetname") or p.get("Sheet name", "")
            sub = p.get("Sheetfile") or p.get("Sheet file", "")
            child = inst + "/" + uuid_of(sh)
            for sp in _children(sh, "pin"):
                at = _at(sp)
                node = pnode(_pt(at[0], at[1]))
                labels.append(("sheet_pin", sp[1], depth, path, node))
                pending_sheet_pins[(child, sp[1])] = node
            sheets.append((sch.parent / sub, path + name + "/", child))
        for a, b in segs:
            for xy in mid_ok:
                if _on_segment(xy, a, b):
                    uf.union(("pt", inst, a), ("pt", inst, xy))
        for sub, sp, child in sheets:
            if sub.is_file():
                visit(sub, sp, child, depth + 1)
            else:
                findings.append(f"{sch.name}: sheet file {sub.name} not found")

    visit(root_sch, "/", None, 0)
    # labels of the same name join: local, local power and hierarchical within a sheet instance;
    # global labels and power symbols everywhere
    first: dict = {}
    for kind, name, _d, path, node in labels:
        if kind == "sheet_pin":
            continue
        key = (("g", name) if kind in ("global_label", "power") else (kind, node[1], name))
        if key in first:
            uf.union(first[key], node)
        else:
            first[key] = node
    named: dict = {}
    for kind, name, d, path, node in labels:
        cand = (-PRIORITY[kind], d, name if kind in ("power", "global_label") else path + name)
        r = uf.find(node)
        if r not in named or cand < named[r]:
            named[r] = cand
    members: dict = {}
    for s in symbols:
        if s.power:
            continue
        for p in s.pins:
            members.setdefault(uf.find(("pin", s.inst, s.ref, p.number, id(s))), []).append((s, p))
    nets: dict[tuple[str, str], str] = {}
    for r, ms in members.items():
        if r in named:
            name = named[r][2]
        else:
            name = _default_net_name(ms, unit_letter)
        for s, p in ms:
            nets[(s.ref, p.number)] = name
    return Netlist([s for s in symbols if not s.power], nets, files, findings)


def _default_net_name(ms, unit_letter) -> str:
    """KiCad's name of a net without a label: from one of its pins; a pin with a name (other than
    its number) is preferred, then the smallest name."""
    def pin_name(s, p, unconnected):
        ref = s.ref + unit_letter.get(id(s), "")
        named = bool(p.name) and p.name != p.number
        if unconnected:
            return f"unconnected-({ref}-{p.name}-Pad{p.number})" if named else f"unconnected-({ref}-Pad{p.number})"
        return f"Net-({ref}-{p.name})" if named else f"Net-({ref}-Pad{p.number})"
    if len(ms) == 1:
        return pin_name(*ms[0], True)
    cands = [(not (p.name and p.name != p.number), pin_name(s, p, False)) for s, p in ms]
    return min(cands)[1]


def _ref_key(s: str):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]


def connectors(nl: Netlist) -> list[dict]:
    """The connector table (sorted by designator): ref, Port, value, footprint, pins."""
    out: dict[str, dict] = {}
    for s in nl.symbols:
        if not is_connector(s.ref, s.fields):
            continue
        c = out.setdefault(s.ref, {"ref": s.ref, "port": s.fields.get("Port"), "value": s.value,
                                   "footprint": s.footprint, "lib_id": s.lib_id, "sheet": s.sheet, "pins": {}})
        for p in s.pins:
            c["pins"][p.number] = {"number": p.number, "name": p.name, "net": nl.nets.get((s.ref, p.number), "")}
    for c in out.values():
        c["pins"] = [c["pins"][k] for k in sorted(c["pins"], key=_ref_key)]
    return [out[k] for k in sorted(out, key=_ref_key)]


def document(project: str, root_sch: Path, repo: Path) -> dict:
    """The content of generated/<project>.connectors.json. It lists its input files but no hash of
    them, so an edit that changes no connector (a moved label) does not make it stale."""
    nl = netlist(root_sch)
    rel = lambda p: str(p.resolve().relative_to(repo.resolve()))  # noqa: E731
    doc = {"project": project, "root_sheet": rel(root_sch), "inputs": sorted(rel(f) for f in nl.files),
           "connectors": connectors(nl)}
    if nl.findings:
        doc["unsupported"] = nl.findings
    return doc


def dumps(doc: dict) -> str:
    return json.dumps(doc, indent=2, sort_keys=True) + "\n"


# ------------------------------------------------------------------ the XML netlist (CK-D8)
def from_xml(xml: Path) -> list[dict]:
    """The same table from ``kicad-cli sch export netlist --format kicadxml``: pin names from
    ``libparts`` (``pinfunction`` is ``<name>_<number>`` in KiCad 10), nets from ``nets``."""
    root = ET.parse(xml).getroot()
    libpins = {}
    for lp in root.iter("libpart"):
        libpins[(lp.get("lib"), lp.get("part"))] = {p.get("num"): p.get("name") or "" for p in lp.iter("pin")}
    nets = {}
    for n in root.iter("net"):
        for node in n.iter("node"):
            nets[(node.get("ref"), node.get("pin"))] = n.get("name")
    out = []
    for comp in root.iter("comp"):
        ref = comp.get("ref", "")
        fields = {x.get("name"): (x.text or "") for x in comp.iter("field")}
        if not is_connector(ref, fields):
            continue
        ls = comp.find("libsource")
        lib, part = (ls.get("lib"), ls.get("part")) if ls is not None else ("", "")
        pins = libpins.get((lib, part), {})
        out.append({"ref": ref, "port": fields.get("Port"), "value": comp.findtext("value") or "",
                    "pins": [{"number": k, "name": "" if pins[k] == "~" else pins[k], "net": nets.get((ref, k), "")}
                             for k in sorted(pins, key=_ref_key)]})
    return sorted(out, key=lambda c: _ref_key(c["ref"]))


def compare(mine: list[dict], kicad: list[dict], where: str) -> list[str]:
    """CK-D8: differences between the plain-Python table and KiCad's netlist."""
    findings = []
    a = {c["ref"]: c for c in mine}
    b = {c["ref"]: c for c in kicad}
    for ref in sorted(set(a) | set(b), key=_ref_key):
        if ref not in a:
            findings.append(f"{where}: {ref} is in KiCad's netlist, not in the extraction")
            continue
        if ref not in b:
            findings.append(f"{where}: {ref} is in the extraction, not in KiCad's netlist")
            continue
        if a[ref].get("port") != b[ref].get("port"):
            findings.append(f"{where}: {ref}: Port {a[ref].get('port')!r} here, {b[ref].get('port')!r} in KiCad")
        pa = {p["number"]: p for p in a[ref]["pins"]}
        pb = {p["number"]: p for p in b[ref]["pins"]}
        for n in sorted(set(pa) | set(pb), key=_ref_key):
            x, y = pa.get(n), pb.get(n)
            if x is None or y is None:
                findings.append(f"{where}: {ref} pin {n}: only in {'KiCad' if x is None else 'the extraction'}")
            elif (x["name"], x["net"]) != (y["name"], y["net"]):
                findings.append(f"{where}: {ref} pin {n}: name/net {x['name']!r}/{x['net']!r} here, "
                                f"{y['name']!r}/{y['net']!r} in KiCad")
    return findings


# ------------------------------------------------------------------ CK-F1: against the EE model
def pin_maps(m) -> tuple[dict[str, dict[str, str]], dict[str, str]]:
    """(EE-PORT ID -> {pin number: net}, EE-PORT ID -> qualified name) of the model's connector
    port defs: their PinSignal ports with ``pin`` and ``net`` values."""
    from curatrix import ids as idmod
    maps, names = {}, {}
    for p in m.user():
        sid = p.get("declaredShortName") or ""
        if p.get("@type") != "PortDefinition" or idmod.kind_of(sid) != "EE-PORT":
            continue
        names[sid] = m.qn(p)
        pm = {}
        for port in _ports_with_supers(m, p):
            vals = {}
            for _, f in m.owned(port):
                if f.get("name") in ("pin", "net"):
                    for _, v in m.owned(f):
                        if "value" in v and str(v.get("@type", "")).startswith("Literal"):
                            vals[f["name"]] = str(v["value"])
            if "pin" in vals:
                pm.setdefault(vals["pin"], vals.get("net", ""))
        maps[sid] = pm
    return maps, names


def _ports_with_supers(m, p, seen=None):
    from curatrix.model import owned_ports
    seen = seen or set()
    if p["@id"] in seen:
        return
    seen.add(p["@id"])
    yield from owned_ports(m, p)
    for s in m.supers(p):
        if not s.get("isLibraryElement"):
            yield from _ports_with_supers(m, s, seen)


def board_ports(m, board) -> list[tuple[str, str]]:
    """(port name, EE-PORT ID of its def) for each port of a board def (conjugated `~X` = X)."""
    from curatrix.model import owned_ports
    out = []
    for f in owned_ports(m, board):
        t = next(iter(m.declared_types(f)), None)
        d, _ = m.port_def(t)
        sid = (d or {}).get("declaredShortName") or ""
        out.append((f.get("name") or "", sid))
    return out


def strip_root(net: str) -> str:
    """A root-sheet local label net ``/X`` is ``X`` in the model (KiCad spike §5)."""
    return net[1:] if net.startswith("/") and net.count("/") == 1 else net


def conformance(doc: dict, board_id: str | None, m, where: str) -> list[str]:
    """CK-F1 for one project: every connector has a Port (``-`` = none); each Port names an
    EE-PORT that is the def of a port of the board def; each port of the board def is named by
    one connector (or as many as the board has ports of that def); pin numbers and net names
    equal the pin map."""
    from curatrix import eeprojects
    findings = []
    boards, _, _ = eeprojects.model_defs(m)
    maps, names = pin_maps(m)
    board = boards.get(board_id or "")
    if board is None:
        return [f"{where}: TraceID {board_id!r} names no board def of the EE model (see CK-F7)"]
    findings += [f"{where}: {u}" for u in doc.get("unsupported", [])]
    want: dict[str, list[str]] = {}
    for pname, pid in board_ports(m, board):
        if pid:
            want.setdefault(pid, []).append(pname)
    have: dict[str, list[str]] = {}
    for c in doc.get("connectors", []):
        port = (c.get("port") or "").strip()
        if not port:
            findings.append(f"{where}: {c['ref']} has no Port field; name its EE-PORT, or `-` for none")
            continue
        if port == NO_PORT:
            continue
        if port not in maps:
            findings.append(f"{where}: {c['ref']}: Port {port} is no connector port def (EE-PORT) of the EE model")
            continue
        have.setdefault(port, []).append(c["ref"])
        pins = {p["number"]: p for p in c["pins"]}
        for num, p in sorted(pins.items(), key=lambda kv: _ref_key(kv[0])):
            if num not in maps[port] and not p["net"].startswith("unconnected-"):
                findings.append(f"{where}: {c['ref']} ({names[port]}): pin {num} is on net {p['net']!r}, but the "
                                f"pin map has no pin {num}; add it to the port def or leave the pin unconnected")
        for num, net in sorted(maps[port].items(), key=lambda kv: _ref_key(kv[0])):
            p = pins.get(num)
            if p is None:
                findings.append(f"{where}: {c['ref']} ({names[port]}): pin {num} of the pin map is not on the connector")
            elif strip_root(p["net"]) != net:
                findings.append(f"{where}: {c['ref']} ({names[port]}): pin {num} is on net {p['net']!r}, "
                                f"the pin map says {net!r}")
    for pid, pnames in sorted(want.items()):
        refs = have.get(pid, [])
        if len(refs) != len(pnames):
            findings.append(f"{where}: the board def has {len(pnames)} port(s) of {names.get(pid, pid)} "
                            f"({', '.join(pnames)}), {len(refs)} connector(s) name it ({', '.join(refs) or 'none'})")
    for pid, refs in sorted(have.items()):
        if pid not in want:
            findings.append(f"{where}: {', '.join(refs)}: Port {pid} is not a port of the board def {m.qn(board)}")
    return findings
