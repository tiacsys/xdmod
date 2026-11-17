"""Cut a .kicad_pcb down to what `curatrix variants list` reads: per footprint its Reference,
its (attr ..) and its own (variant ..) blocks. Usage: python cut_board.py IN.kicad_pcb OUT.kicad_pcb"""
import sys
from pathlib import Path

from curatrix.cad import _children, sexpr


def dump(n, ind=0):
    if not isinstance(n, list):
        return f'"{n}"' if (not n or any(c in n for c in ' ()"') or n[0].isupper() or "/" in n) else n
    return "\t" * ind + "(" + " ".join(dump(x) for x in n if not isinstance(x, list)) + \
        "".join("\n" + dump(x, ind + 1) for x in n if isinstance(x, list)) + \
        ("\n" + "\t" * ind if any(isinstance(x, list) for x in n) else "") + ")"


tree = sexpr(Path(sys.argv[1]).read_text(encoding="utf-8"))
out = ["kicad_pcb"]
for fp in _children(tree, "footprint"):
    keep = [fp[0], fp[1]] + [c for c in fp[2:] if isinstance(c, list) and (
        c[0] in ("attr", "variant") or (c[0] == "property" and len(c) > 1 and c[1] == "Reference"))]
    out.append([k if not (isinstance(k, list) and k[0] == "property") else k[:3] for k in keep])
Path(sys.argv[2]).write_text(dump(out) + "\n", encoding="utf-8")
