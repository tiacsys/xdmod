"""Writes conn.kicad_sch: rotated and mirrored symbols, local and global labels, a label inside a
wire, a power symbol, a T without a junction, crossing wires (test of curatrix.connectors).

    python -I make_conn.py conn.kicad_sch <ws>/libs/kicad/symbols <ws>/xdmod/curatrix/src
    curatrix run --use kicad-cli -- kicad-cli sch upgrade --force conn.kicad_sch
    curatrix run --use kicad-cli -- kicad-cli sch export netlist --format kicadxml -o conn.net.xml conn.kicad_sch
"""
import re, sys, uuid
sys.path.insert(0, sys.argv[3])
from curatrix import connectors as C
from curatrix.cad import sexpr, _children
LIB = sys.argv[2]
out = sys.argv[1]
U = lambda: str(uuid.uuid4())
ROOT = "11111111-2222-3333-4444-555555555555"

def libsym(lib, name):
    t = open(f"{LIB}/{lib}.kicad_symdir/{name}.kicad_sym").read()
    i = t.index('(symbol "')
    body = t[i:t.rindex(")")].rstrip()
    return body.replace(f'(symbol "{name}"', f'(symbol "{lib}:{name}"', 1), sexpr(body)

libs = {}
def pins(lib, name, at, mirror=None):
    key = f"{lib}:{name}"
    if key not in libs:
        libs[key] = libsym(lib, name)
    tree = libs[key][1]
    return {n: C.transform(x, y, at, mirror) for n, _, x, y in C._lib_pins(tree, 1, 1)}

items = []
def sym(lib, name, ref, value, at, mirror=None, fields=None, fp=""):
    ps = pins(lib, name, at, mirror)
    f = "".join(f'(property "{k}" "{v}" (at {at[0]} {at[1]} 0) (effects (font (size 1.27 1.27)) (hide yes)))' for k, v in (fields or {}).items())
    m = f"(mirror {mirror})" if mirror else ""
    items.append(f'''(symbol (lib_id "{lib}:{name}") (at {at[0]} {at[1]} {at[2]}) {m} (unit 1) (body_style 1) (exclude_from_sim no) (in_bom yes) (on_board yes) (in_pos_files yes) (dnp no) (uuid "{U()}")
  (property "Reference" "{ref}" (at {at[0]} {at[1]-3} 0) (effects (font (size 1.27 1.27))))
  (property "Value" "{value}" (at {at[0]} {at[1]+3} 0) (effects (font (size 1.27 1.27))))
  (property "Footprint" "{fp}" (at {at[0]} {at[1]} 0) (effects (font (size 1.27 1.27)) (hide yes)))
  {f}
  (instances (project "t" (path "/{ROOT}" (reference "{ref}") (unit 1)))))''')
    return {k: (v[0] / C.SCALE, v[1] / C.SCALE) for k, v in ps.items()}

def wire(a, b):
    items.append(f'(wire (pts (xy {a[0]} {a[1]}) (xy {b[0]} {b[1]})) (stroke (width 0) (type default)) (uuid "{U()}"))')

def label(kind, name, at):
    extra = ' (shape input)' if kind == "global_label" else ""
    items.append(f'({kind} "{name}"{extra} (at {at[0]} {at[1]} 0) (effects (font (size 1.27 1.27))) (uuid "{U()}"))')

j1 = sym("Connector_Generic", "Conn_01x03", "J1", "Conn_01x03", (100.33, 100.33, 0), fields={"Port": "EE-PORT-0001"},
         fp="Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical")
r1 = sym("Device", "R", "R1", "10k", (130.81, 120.65, 90))
r2 = sym("Device", "R", "R2", "1k", (160.02, 80.01, 270), mirror="x")
j2 = sym("Connector_Generic", "Conn_01x02", "J2", "Conn_01x02", (180.34, 120.65, 180), mirror="y", fields={"Port": "-"})
gnd = sym("power", "GND", "#PWR01", "GND", (90.17, 130.81, 0))
p = j1["1"]; q = (p[0] - 7.62, p[1]); wire(p, q); label("label", "CANARY_A", q)
p = j1["2"]; q = (p[0] - 5.08, p[1]); wire(p, q); wire(q, (q[0], r1["1"][1])); wire((q[0], r1["1"][1]), r1["1"])
p = r1["2"]; q = (p[0] + 5.08, p[1]); wire(p, q); label("global_label", "G_OUT", q)
p = j1["3"]; wire(p, (gnd["1"][0], p[1])); wire((gnd["1"][0], p[1]), gnd["1"])
p = j2["1"]; wire(p, (r2["1"][0], p[1])); wire((r2["1"][0], p[1]), r2["1"])
p = r2["2"]; q = (p[0], p[1] - 5.08); wire(p, q); label("label", "CANARY_A", q)
p = j2["1"]; label("label", "MID", ((p[0] + r2["1"][0]) / 2, p[1]))
# a wire crossing J1's net wire without a junction: must not connect
wire((95.0, 90.0), (95.0, 110.0))
txt = f'''(kicad_sch (version 20260306) (generator "eeschema") (generator_version "10.0") (uuid "{ROOT}") (paper "A4")
(lib_symbols {" ".join(v[0] for v in libs.values())})
{chr(10).join(items)}
(sheet_instances (path "/" (page "1"))))
'''
open(out, "w").write(txt)
