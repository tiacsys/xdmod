"""Writes bom.kicad_pro, bom.kicad_sch and bom_ch.kicad_sch: a BOM fixture with two assembly
variants (a, b), a sheet used twice, a multi-unit symbol, DNP and in_bom flags, field overrides per
variant and a shunt `Setting` (test of curatrix.bom). No wires: only the BOM matters. Then let KiCad
save the sheets and record its BOM exports (one line per reference, curatrix.bom.KICAD_FIELDS):

    python -I make_bom.py <dir> <ws>/libs/kicad/symbols
    curatrix run --use kicad-cli -- kicad-cli sch upgrade --force <dir>/bom.kicad_sch   (and bom_ch)
    for v in base a b: curatrix run --use kicad-cli -- kicad-cli sch export bom <curatrix.bom.kicad_argv> -> bom.<v>.csv
"""
import json
import sys
import uuid
from pathlib import Path

OUT, LIB = Path(sys.argv[1]), sys.argv[2]
U = lambda: str(uuid.uuid4())  # noqa: E731
ROOT, CHILD = "bbbbbbbb-0000-0000-0000-000000000001", "bbbbbbbb-0000-0000-0000-000000000002"
S1, S2 = "bbbbbbbb-0000-0000-0000-000000000011", "bbbbbbbb-0000-0000-0000-000000000012"
E = "(effects (font (size 1.27 1.27)))"
H = "(effects (font (size 1.27 1.27)) (hide yes))"


def libsym(lib, name):
    t = open(f"{LIB}/{lib}.kicad_symdir/{name}.kicad_sym").read()
    body = t[t.index('(symbol "'):t.rindex(")")].rstrip()
    return body.replace(f'(symbol "{name}"', f'(symbol "{lib}:{name}"', 1)


class Sheet:
    def __init__(self):
        self.libs, self.items, self.x = {}, [], 50.8

    def sym(self, lib, name, insts, value, fp="", fields=None, unit=1, in_bom=True, dnp=False):
        """insts: [(path, reference, variant s-expr)]"""
        self.libs.setdefault(f"{lib}:{name}", libsym(lib, name))
        self.x += 12.7
        yn = lambda b: "yes" if b else "no"  # noqa: E731
        f = "".join(f'(property "{k}" "{v}" (at {self.x} 100 0) {H})' for k, v in (fields or {}).items())
        inst = "".join(f'(path "{p}" (reference "{r}") (unit {unit}) {var})' for p, r, var in insts)
        self.items.append(f'''(symbol (lib_id "{lib}:{name}") (at {self.x} 100.33 0) (unit {unit}) (body_style 1)
 (exclude_from_sim no) (in_bom {yn(in_bom)}) (on_board yes) (in_pos_files yes) (dnp {yn(dnp)}) (uuid "{U()}")
 (property "Reference" "{insts[0][1]}" (at {self.x} 97 0) {E})
 (property "Value" "{value}" (at {self.x} 104 0) {E})
 (property "Footprint" "{fp}" (at {self.x} 100 0) {H})
 {f} (instances (project "bom" {inst})))''')

    def write(self, path, uid, extra=""):
        path.write_text(f'''(kicad_sch (version 20260306) (generator "eeschema") (generator_version "10.0") (uuid "{uid}") (paper "A4")
(lib_symbols {" ".join(self.libs.values())})
{chr(10).join(self.items)}
{extra})
''')


R0603 = "Resistor_SMD:R_0603_1608Metric"
MF = {"Manufacturer": "Yageo", "MPN": "RC0603FR-071KL"}

# child sheet, used twice: R2 (ch1) and R3 (ch2); R3 is DNP in variant b
ch = Sheet()
ch.sym("Device", "R", [(f"/{ROOT}/{S1}", "R2", ""), (f"/{ROOT}/{S2}", "R3", '(variant (name "b") (dnp yes))')],
       "1k", R0603, MF)
ch.write(OUT / "bom_ch.kicad_sch", CHILD)

rt = Sheet()
p = f"/{ROOT}"
# R1: value 4k7 and its MPN in variant a (field overrides)
rt.sym("Device", "R", [(p, "R1", '(variant (name "a") (field (name "Value") (value "4k7")) '
                                 '(field (name "MPN") (value "RC0603FR-074K7L")))')], "10k", R0603,
       {"Manufacturer": "Yageo", "MPN": "RC0603FR-0710KL"})
# U1: two units of one dual op-amp, one part in the BOM; DNP on unit 2 only marks the part DNP (KiCad)
for unit in (1, 2):
    rt.sym("Amplifier_Operational", "LM2904", [(p, "U1", "")], "LM2904", "Package_SO:SOIC-8_3.9x4.9mm_P1.27mm",
           {"Manufacturer": "Texas Instruments", "MPN": "LM2904DR"}, unit=unit, dnp=unit == 2)
# J1: a pin header with a shunt; Setting 1-2, 2-3 in variant b; no MPN (CK-F12)
rt.sym("Connector_Generic", "Conn_01x03", [(p, "J1", '(variant (name "b") (field (name "Setting") (value "2-3")))')],
       "Conn_01x03", "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical", {"Setting": "1-2"})
# JP1: a solder jumper, open (DNP) in the base, bridged (fitted) in variant b; a standard designation
rt.sym("Jumper", "SolderJumper_2_Open", [(p, "JP1", '(variant (name "b") (dnp no))')], "SolderJumper_2_Open",
       "Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm", {"Standard": "solder bridge"}, dnp=True)
# H1: a mounting hole, not in the BOM
rt.sym("Mechanical", "MountingHole", [(p, "H1", "")], "MountingHole", "MountingHole:MountingHole_3.2mm_M3",
       in_bom=False)
sheets = ""
for sid, nm, y, page in ((S1, "ch1", 130, "2"), (S2, "ch2", 150, "3")):
    sheets += f'''(sheet (at 110.49 {y}) (size 20.32 10.16) (stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0.0)) (uuid "{sid}")
 (property "Sheetname" "{nm}" (at 110.49 {y - 0.7} 0) (effects (font (size 1.27 1.27)) (justify left bottom)))
 (property "Sheetfile" "bom_ch.kicad_sch" (at 110.49 {y + 10.8} 0) (effects (font (size 1.27 1.27)) (justify left top)))
 (instances (project "bom" (path "/{ROOT}" (page "{page}")))))
'''
sheets += f'(sheet_instances (path "/" (page "1")) (path "/{S1}" (page "2")) (path "/{S2}" (page "3")))'
rt.write(OUT / "bom.kicad_sch", ROOT, sheets)
(OUT / "bom.kicad_pro").write_text(json.dumps({
    "meta": {"filename": "bom.kicad_pro", "version": 3},
    "schematic": {"variants": [{"name": "a", "description": "R1 4k7"},
                               {"name": "b", "description": "R3 DNP, JP1 bridged, shunt 2-3"}]},
    "text_variables": {"TraceID": "EE-PCBA-0001"}}, indent=2) + "\n")
