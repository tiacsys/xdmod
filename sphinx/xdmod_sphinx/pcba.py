"""Directives of the ``pcba-<name>`` board document (task 5.21; XD-ADR-0129): one directive set, so
every board document looks the same. Each takes the project name (``pcba/<name>/`` of the repo this
document belongs to). No options: no per-board layout.

Plain Python, everywhere (CI and Pages too):

``xd-pcba-overview``     the board need, the project, the version shown, variants, ERC/DRC summary
``xd-pcba-variants``     variant, description, fitted differences, shunt ``Setting``, Zephyr board variant
``xd-pcba-stackup``      the stackup (Board Setup, or KiCad's default)
``xd-pcba-rules``        design rules: board, net classes, custom rules
``xd-pcba-connectors``   one pin table per connector (committed ``generated/<name>.connectors.json``)
``xd-pcba-bom``          the BOM with a column per variant (for the appendix)

Local only, from the ``curatrix cam`` output of the commit the repo is at
(``build/<area>/cam/<name>/<version>/``, ``curatrix.cam.current``); never an older run:

``xd-pcba-renderings``   top, bottom and 3D renderings per variant
``xd-pcba-schematic``    the schematic sheets (SVG) and the PDF per variant
``xd-pcba-findings``     ERC and DRC findings with their acceptance state

A section without data prints one fixed sentence (``NO_DATA``, ``LOCAL``); CK-D10 warns locally
when the output is missing or stale, so the strict docs build never depends on it.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path

from docutils import nodes
from docutils.parsers.rst import Directive
from docutils.statemachine import StringList

NO_DATA = "No data yet."
LOCAL = "Made locally with KiCad (curatrix cam) for the current commit; not part of this build."


def _cur(name: str):
    from xdmod_sphinx.reference import curatrix_module
    return curatrix_module(name)


class _Board:
    """What the directives of one board read."""

    def __init__(self, directive):
        env = directive.state.document.settings.env
        self.env = env
        self.name = directive.arguments[0]
        self.repo = Path(env.config.xd_repo)
        self.cfg = _cur("checkcfg").load(self.repo / "checks.yaml", self.repo.parent)
        pr = next((p for p in _cur("eeprojects").discover(self.cfg) if p.kind == "pcba" and p.name == self.name), None)
        if pr is None:
            raise directive.error(f"{directive.name}: no pcba/{self.name}/ project (checks.yaml cad.projects)")
        self.pr = pr
        for f in sorted(pr.folder.glob("*.kicad_*")):    # re-read the page when a KiCad file changes
            env.note_dependency(str(f))

    def variants(self) -> list[dict]:
        d = json.loads(self.pr.pro.read_text(encoding="utf-8"))
        return [v for v in ((d.get("schematic") or {}).get("variants") or []) if v.get("name")]

    def parts(self):
        return _cur("bom").read(self.pr.sch)

    def cam(self):
        """(record, folder with the outputs) of the current commit's run, or (None, None)."""
        rec, top, _ = _cur("cam").current(Path(self.env.config.xd_cam_dir), self.name, self.repo, self.pr.folder)
        if rec is None:
            return None, None
        self.env.note_dependency(str(top / "cam.json"))
        return rec, top / self.name


def _cell(s) -> str:
    """Free text in a table cell, with rST markup escaped (KiCad messages, descriptions, pin names)."""
    s = str(s) if s not in (None, "") else "—"
    return re.sub(r"([\\*_`|:<>\[\]])", r"\\\1", s.replace("\n", " "))


def _rst(directive, lines: list[str]) -> list[nodes.Node]:
    node = nodes.container()
    directive.state.nested_parse(StringList(lines, source="xd-pcba"), directive.content_offset, node)
    return node.children


def _table(head, rows) -> list[str]:
    lines = [".. list-table::", "   :header-rows: 1", "   :class: xd-table", ""]
    for r in [head] + rows:
        lines.append(f"   * - {r[0]}")
        lines += [f"     - {c}" for c in r[1:]]
    return lines + [""]


def _lit(s: str) -> str:
    return f"``{s}``" if s else "—"


def _version(rec) -> str:
    return rec["version"]                  # a preview carries "-preview" in the version itself


class Overview(Directive):
    required_arguments = 1

    def run(self):
        b = _Board(self)
        tid = (b.pr.variables().get("TraceID") or "").strip()
        rec, out = b.cam()
        vs = b.variants()
        lines = [f"* Board: :need:`{tid}`" if tid else "* Board: no ``TraceID`` in the project",
                 f"* KiCad project: ``{b.pr.pro.relative_to(b.repo)}``",
                 f"* Version: ``{_version(rec)}``, local output of {rec.get('date', '')}" if rec else
                 f"* Version, ERC/DRC: {LOCAL}",
                 f"* Variants: {', '.join(_lit(v['name']) for v in vs)}" if vs else "* Variants: none"]
        f = out / "findings.json" if out else None
        if f and f.is_file():
            rows = [r for k in ("erc", "drc") for r in json.loads(f.read_text()).get(k, [])]
            n = {s: sum(r["state"] == s for r in rows) for s in ("open", "proposal", "accepted", "warning", "stale")}
            lines.append(f"* ERC/DRC: {n['open']} open, {n['proposal']} proposed, {n['accepted']} accepted, "
                         f"{n['warning']} warnings, {n['stale']} stale exclusions")
        return _rst(self, lines)


class Variants(Directive):
    required_arguments = 1

    def run(self):
        b = _Board(self)
        vs = b.variants()
        if not vs:
            return [nodes.paragraph(text=NO_DATA)]
        z = (b.cfg.section("variants") or {}).get("zephyr")
        dv = _cur("domvariants")
        zephyr = dv.zephyr_boards(b.cfg.globs([z] if isinstance(z, str) else z)) if z else None
        rows = _cur("bom").variants_table(b.parts(), vs, zephyr, b.name.replace("-", "_").lower())
        rows = [[_lit(r[0]), _cell(r[1]), _cell(r[2]), _cell(r[3]), _lit(r[4]) if r[4] != "—" else "—"] for r in rows]
        return _rst(self, _table(["Variant", "Description", "Fitted differences", "Jumper settings",
                                  "Zephyr board variant"], rows))


class Stackup(Directive):
    required_arguments = 1

    def run(self):
        b = _Board(self)
        pcb = b.pr.pro.with_suffix(".kicad_pcb")
        if not pcb.is_file():
            return [nodes.paragraph(text=NO_DATA)]
        cam = _cur("cam")
        rows, source = cam.stackup(pcb)
        head = ["Layer", "Type", "Material", "Thickness (mm)", "εr", "Loss tangent"]
        return _rst(self, [f"Source: {source}.", ""] + _table(head, [[_cell(r.get(k)) for k in cam.STACKUP_COLS[:6]]
                                                                    for r in rows]))


class Rules(Directive):
    required_arguments = 1

    def run(self):
        b = _Board(self)
        rows = _cur("cam").design_rules(b.pr.pro)
        if not rows:
            return [nodes.paragraph(text=NO_DATA)]
        return _rst(self, _table(["Scope", "Rule", "Value", "Unit"],
                                 [[_cell(r["scope"]), _lit(r["rule"]), _cell(r["value"]), _cell(r["unit"])]
                                  for r in rows]))


class Connectors(Directive):
    required_arguments = 1

    def run(self):
        b = _Board(self)
        f = _cur("gen").connectors_path(b.cfg, b.name)
        if not f.is_file():
            return [nodes.paragraph(text=NO_DATA)]
        b.env.note_dependency(str(f))
        doc = json.loads(f.read_text(encoding="utf-8"))
        lines = []
        for c in doc.get("connectors") or []:
            port = c.get("port") or ""
            pdesc = f":need:`{port}`" if port.startswith("EE-PORT-") else ("no port" if port == "-" else _lit(port))
            lines += [f"**{c['ref']}** ({_lit(c.get('value'))}, {_lit(c.get('footprint'))}): {pdesc}", ""]
            lines += _table(["Pin", "Pin name", "Net"], [[_cell(p["number"]), _cell(p.get("name")), _lit(p.get("net"))]
                                                          for p in c.get("pins") or []])
        return _rst(self, lines) if lines else [nodes.paragraph(text=NO_DATA)]


class Bom(Directive):
    required_arguments = 1

    def run(self):
        b = _Board(self)
        head, rows = _cur("bom").table(b.parts(), [v["name"] for v in b.variants()])
        if not rows:
            return [nodes.paragraph(text=NO_DATA)]
        return _rst(self, _table(head, [[_cell(c) for c in r] for r in rows]))


class Renderings(Directive):
    """Top, bottom and 3D per variant, each distinct image once: Sphinx image nodes, so the PNGs are
    copied to ``_images/`` and not embedded in the page; an image equal to one shown before is
    named instead."""
    required_arguments = 1
    VIEWS = (("render-top", "top"), ("render-bottom", "bottom"), ("render-3d", "3D"))

    def run(self):
        env = self.state.document.settings.env
        b = _Board(self)
        rec, out = b.cam()
        if rec is None:
            return [nodes.paragraph(text=LOCAL)]
        docdir = Path(env.doc2path(env.docname)).parent
        result, seen = [], {}
        for v in [x["name"] for x in b.variants()] or [None]:
            cap = f"Variant {v}" if v else "Board"
            imgs, same = [], []
            for stem, what in self.VIEWS:
                f = out / f"{stem}{'-' + v if v else ''}.png"
                if not f.is_file():
                    continue
                key = hashlib.sha256(f.read_bytes()).hexdigest()
                if key in seen:
                    same.append(f"{what}: same as {seen[key]}")
                    continue
                seen[key] = f"{cap.lower()} {what}"
                imgs.append(nodes.image(uri=os.path.relpath(f, docdir), alt=f"{cap}, {what}", width="32%"))
            if not imgs and not same:
                continue
            shown = [i["alt"].split(", ")[-1] for i in imgs]
            para = nodes.paragraph(text=f"{cap}, {_version(rec)}: " + "; ".join(
                ([", ".join(shown)] if shown else []) + same) + ".")
            result += [para, *imgs]
        return result or [nodes.paragraph(text=NO_DATA)]


class Schematic(Directive):
    required_arguments = 1

    def run(self):
        from xdmod_sphinx import inline_svg
        b = _Board(self)
        rec, out = b.cam()
        if rec is None:
            return [nodes.paragraph(text=LOCAL)]
        root = out / f"{b.name}.svg"
        sheets = ([root] if root.is_file() else []) + sorted(f for f in out.glob("*.svg") if f != root)
        if not sheets:
            return [nodes.paragraph(text=NO_DATA)]
        html = [f'<figure class="xd-cad">{inline_svg(f.read_text(encoding="utf-8"))}<figcaption>{f.stem}, '
                f"{_version(rec)}</figcaption></figure>" for f in sheets]
        pdfs = sorted(out.glob(f"{b.name}-schematic*.pdf"))
        out_nodes = [nodes.raw("", "\n".join(html), format="html")]
        if pdfs:                           # a file:// link would be dead on any other machine
            p = nodes.paragraph(text="PDF per variant, in the local output folder: ")
            p += nodes.literal(text=", ".join(f.name for f in pdfs))
            out_nodes.append(p)
        return out_nodes


class Findings(Directive):
    required_arguments = 1
    STATES = {"open": "open error", "proposal": "proposed, not accepted", "accepted": "accepted",
              "warning": "warning", "stale": "stale exclusion"}

    def run(self):
        b = _Board(self)
        rec, out = b.cam()
        f = out / "findings.json" if rec else None
        if f is None or not f.is_file():
            return [nodes.paragraph(text=LOCAL)]
        d = json.loads(f.read_text(encoding="utf-8"))
        lines = []
        for kind in ("erc", "drc"):
            if kind not in d:
                continue
            rows = d[kind]
            lines += [f"**{kind.upper()}** ({_version(rec)}): {len(rows)} finding{'s' if len(rows) != 1 else ''}.", ""]
            if rows:
                lines += _table(["State", "Severity", "Rule", "Items", "Description", "Acceptance"],
                                [[self.STATES.get(r["state"], r["state"]), r["severity"], _lit(r["rule"]),
                                  _cell(r["items"]), _cell(r["description"]), _cell(r["note"])] for r in rows])
        return _rst(self, lines) if lines else [nodes.paragraph(text=NO_DATA)]


DIRECTIVES = {"xd-pcba-overview": Overview, "xd-pcba-variants": Variants, "xd-pcba-stackup": Stackup,
              "xd-pcba-rules": Rules, "xd-pcba-connectors": Connectors, "xd-pcba-bom": Bom,
              "xd-pcba-renderings": Renderings, "xd-pcba-schematic": Schematic, "xd-pcba-findings": Findings}


def setup(app):
    if "xd_cam_dir" not in app.config:      # also registered by the harness directives
        app.add_config_value("xd_cam_dir", "", "env")
    for name, cls in DIRECTIVES.items():
        app.add_directive(name, cls)

