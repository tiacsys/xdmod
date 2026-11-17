"""Writes hier.kicad_sch + hier_ch.kicad_sch: a sheet used twice (sheet pins, hierarchical labels),
PWR_FLAG on GND, a global label on the GND net (it names the net), a connector placed with
lib_name (test of curatrix.connectors). Then let KiCad save both and export the netlist:

    python -I mkhier.py <dir> <ws>/libs/kicad/symbols <ws>/xdmod/curatrix/src
    curatrix run --use kicad-cli -- kicad-cli sch upgrade --force <dir>/hier.kicad_sch   (and hier_ch)
    curatrix run --use kicad-cli -- kicad-cli sch export netlist --format kicadxml -o <dir>/hier.net.xml <dir>/hier.kicad_sch
"""
import sys, uuid
from pathlib import Path
sys.path.insert(0, sys.argv[3])
from curatrix import connectors as C
from curatrix.cad import sexpr
OUT, LIB = Path(sys.argv[1]), sys.argv[2]
U = lambda: str(uuid.uuid4())
ROOT, CHILD = "aaaaaaaa-0000-0000-0000-000000000001", "aaaaaaaa-0000-0000-0000-000000000002"
S1, S2 = "aaaaaaaa-0000-0000-0000-000000000011", "aaaaaaaa-0000-0000-0000-000000000012"
E = "(effects (font (size 1.27 1.27)))"


def libsym(lib, name, as_name=None):
    t = open(f"{LIB}/{lib}.kicad_symdir/{name}.kicad_sym").read()
    body = t[t.index('(symbol "'):t.rindex(")")].rstrip()
    new = as_name or f"{lib}:{name}"
    if as_name:                                    # sub-symbols carry the new name too
        body = body.replace(f'(symbol "{name}_', f'(symbol "{as_name}_')
    body = body.replace(f'(symbol "{name}"', f'(symbol "{new}"', 1)
    return body, sexpr(body)


class Sheet:
    def __init__(self):
        self.libs, self.items = {}, []

    def sym(self, lib, name, refs, value, at, mirror=None, fields=None, lib_name=None):
        key = lib_name or f"{lib}:{name}"
        if key not in self.libs:
            self.libs[key] = libsym(lib, name, lib_name)
        pins = {n: C.transform(x, y, at, mirror) for n, _, x, y, *_ in C._lib_pins(self.libs[key][1], 1, 1)}
        f = "".join(f'(property "{k}" "{v}" (at {at[0]} {at[1]} 0) (effects (font (size 1.27 1.27)) (hide yes)))'
                    for k, v in (fields or {}).items())
        ln = f'(lib_name "{lib_name}")' if lib_name else ""
        m = f"(mirror {mirror})" if mirror else ""
        inst = "".join(f'(path "{p}" (reference "{r}") (unit 1))' for p, r in refs)
        self.items.append(f'''(symbol {ln} (lib_id "{lib}:{name}") (at {at[0]} {at[1]} {at[2]}) {m} (unit 1) (body_style 1)
 (exclude_from_sim no) (in_bom yes) (on_board yes) (in_pos_files yes) (dnp no) (uuid "{U()}")
 (property "Reference" "{refs[0][1]}" (at {at[0]} {at[1] - 3} 0) {E})
 (property "Value" "{value}" (at {at[0]} {at[1] + 3} 0) {E})
 (property "Footprint" "" (at {at[0]} {at[1]} 0) (effects (font (size 1.27 1.27)) (hide yes)))
 {f} (instances (project "hier" {inst})))''')
        return {k: (v[0] / C.SCALE, v[1] / C.SCALE) for k, v in pins.items()}

    def wire(self, a, b):
        self.items.append(f'(wire (pts (xy {a[0]} {a[1]}) (xy {b[0]} {b[1]})) (stroke (width 0) (type default)) (uuid "{U()}"))')

    def label(self, kind, name, at, rot=0):
        shape = " (shape input)" if kind in ("global_label", "hierarchical_label") else ""
        self.items.append(f'({kind} "{name}"{shape} (at {at[0]} {at[1]} {rot}) {E} (uuid "{U()}"))')

    def write(self, path, uid, extra=""):
        path.write_text(f'''(kicad_sch (version 20260306) (generator "eeschema") (generator_version "10.0") (uuid "{uid}") (paper "A4")
(lib_symbols {" ".join(v[0] for v in self.libs.values())})
{chr(10).join(self.items)}
{extra})
''')


# child sheet: hierarchical label IN -> R pin 1; R pin 2 -> GND (power) with a PWR_FLAG; a local label MID on IN
ch = Sheet()
refs = lambda a, b: [(f"/{ROOT}/{S1}", a), (f"/{ROOT}/{S2}", b)]
r = ch.sym("Device", "R", refs("R1", "R2"), "1k", (120.65, 100.33, 0))
ch.wire((100.33, r["1"][1]), r["1"]); ch.label("hierarchical_label", "IN", (100.33, r["1"][1]), 180)
ch.label("label", "MID", (110.49, r["1"][1]))
g = ch.sym("power", "GND", refs("#PWR01", "#PWR02"), "GND", (r["2"][0], r["2"][1] + 5.08, 0))
ch.wire(r["2"], g["1"])
fl = ch.sym("power", "PWR_FLAG", refs("#FLG01", "#FLG02"), "PWR_FLAG", (r["2"][0] + 5.08, r["2"][1] + 2.54, 0))
ch.wire(fl["1"], (fl["1"][0], r["2"][1] + 2.54)); ch.wire((r["2"][0], r["2"][1] + 2.54), (fl["1"][0], r["2"][1] + 2.54))
ch.items.append(f'(junction (at {r["2"][0]} {r["2"][1] + 2.54}) (diameter 0) (color 0 0 0 0) (uuid "{U()}"))')
ch.write(OUT / "hier_ch.kicad_sch", CHILD)

# root: J1 (placed with lib_name) pin 1 -> sheet ch1 pin IN, pin 2 -> sheet ch2 pin IN,
# pin 3 -> GND power symbol and a global label ZZZ on the same wire; a PWR_FLAG on +5V alone
rt = Sheet()
j = rt.sym("Connector_Generic", "Conn_01x03", [(f"/{ROOT}", "J1")], "Conn_01x03", (80.01, 100.33, 0), mirror="y",
           fields={"portName": "servoOut", "portType": "ServoHeader", "portTypeID": "EE-PORT-0001"}, lib_name="Conn_01x03_1")
sheets = ""
for sid, nm, y, page in ((S1, "ch1", 80.01, "2"), (S2, "ch2", 120.65, "3")):
    pin = (110.49, y + 5.08)
    sheets += f'''(sheet (at 110.49 {y}) (size 20.32 10.16) (stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0.0)) (uuid "{sid}")
 (property "Sheetname" "{nm}" (at 110.49 {y - 0.7} 0) (effects (font (size 1.27 1.27)) (justify left bottom)))
 (property "Sheetfile" "hier_ch.kicad_sch" (at 110.49 {y + 10.8} 0) (effects (font (size 1.27 1.27)) (justify left top)))
 (pin "IN" input (at {pin[0]} {pin[1]} 180) (uuid "{U()}") (effects (font (size 1.27 1.27)) (justify left)))
 (instances (project "hier" (path "/{ROOT}" (page "{page}")))))
'''
    src = j["1"] if nm == "ch1" else j["2"]
    rt.wire(src, (95.25, src[1])); rt.wire((95.25, src[1]), (95.25, pin[1])); rt.wire((95.25, pin[1]), pin)
gnd = rt.sym("power", "GND", [(f"/{ROOT}", "#PWR03")], "GND", (90.17, 110.49, 0))
rt.wire(j["3"], (90.17, j["3"][1])); rt.wire((90.17, j["3"][1]), gnd["1"])
rt.label("global_label", "ZZZ", (90.17, j["3"][1] + 2.54))
sheets += f'(sheet_instances (path "/" (page "1")) (path "/{S1}" (page "2")) (path "/{S2}" (page "3")))'
rt.write(OUT / "hier.kicad_sch", ROOT, sheets)
