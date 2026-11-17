"""Directives of the ``asm-<name>`` assembly document (task 5.27; ME-4, ME-8, XD-ADR-0129): one
directive set, so every assembly document looks the same. Each takes the name of the top-level
assembly (``assemblies/<name>/`` of the repo this document belongs to). The chapter directives take
``:sub: <ME-ASM ID>`` to show one sub-assembly instead; ``xd-asm-subassemblies`` writes one chapter
per sub-assembly with them.

Plain Python, everywhere (CI and Pages too; ``curatrix/asmdoc.py``):

``xd-asm-overview``        the assembly need, documents, sub-assemblies, variants, version shown
``xd-asm-parameters``      the parameters of the model and their values in the skeleton's ``Params``
``xd-asm-materials``       material, density, parts and print profiles
``xd-asm-interfaces``      the ports: ``ME-PORT``, the ``SYS-IF`` they conform to, placement, LCS, values
``xd-asm-subassemblies``   a chapter per sub-assembly (overview, interfaces, materials, mass, findings)
``xd-asm-bom``             the indented BOM (for the appendix), a quantity column per variant

Local only, from the ``curatrix cam`` output of the commit the repo is at
(``build/<area>/cam/<name>/<version>/``, ``curatrix.mecam.current``); never an older run:

``xd-asm-drawing``         the drawing sheet (SVG) per variant; the PDF named
``xd-asm-exploded``        the exploded view per variant
``xd-asm-renderings``      ``<variant>/renderings/<view>.png`` (front, top, right, iso; task 5.30), in the
                           order of ``cam.json`` (``per_variant.<v>.renderings``, ``renderings.views``)
``xd-asm-mass``            mass and center of gravity per variant (``mass.json``)
``xd-asm-findings``        the ME check findings with their acceptance state (``findings.json``)

A section without data prints one fixed sentence (``NO_DATA``, ``LOCAL``); CK-D10 warns locally
when the output is missing or stale, so the strict docs build never depends on it.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from docutils import nodes
from docutils.parsers.rst import Directive, directives
from docutils.statemachine import StringList

NO_DATA = "No data yet."
LOCAL = "Made locally with FreeCAD (curatrix cam) for the current commit; not part of this build."
NO_RENDERINGS = ("The curatrix cam output of the current commit has no renderings (they come with task 5.30: "
                 "renderings/<view>.png per variant, listed in cam.json).")
VIEW_ORDER = ("front", "top", "right", "iso")
INDENT = "· "                # one per level in the BOM designation (docutils drops leading spaces)
TOP_ONLY = ("Made for the top-level assembly only: curatrix cam makes drawings, the exploded view and "
            "renderings per top-level assembly (iteration 1); see the chapter of the top-level assembly.")
PARAMS_TOP = ("A sub-assembly has no parameters of its own: the parameters of an assembly live in the skeleton "
              "of its top-level assembly (XD-ADR-0137); see the Parameters section.")


def _cur(name: str):
    from xdmod_sphinx.reference import curatrix_module
    return curatrix_module(name)


class _Asm:
    """What the directives of one assembly read."""

    def __init__(self, directive):
        env = directive.state.document.settings.env
        self.env = env
        self.name = directive.arguments[0]
        self.repo = Path(env.config.xd_repo)
        self.cfg = _cur("checkcfg").load(self.repo / "checks.yaml", self.repo.parent)
        self.folder = self.repo / "assemblies" / self.name
        if not (self.folder / f"{self.name}.FCStd").is_file():
            raise directive.error(f"{directive.name}: no assemblies/{self.name}/{self.name}.FCStd")
        for f in self.cfg.globs((self.cfg.section("cad") or {}).get("freecad") or []):
            env.note_dependency(str(f))          # re-read the page when a FreeCAD file changes
        self.docs = _cur("meassemblies").documents(self.cfg)
        self.tree = _cur("asmdoc").tree(self.cfg, self.folder, self.docs)
        if self.tree is None:
            raise directive.error(f"{directive.name}: assemblies/{self.name}/{self.name}.FCStd has no object with "
                                  f"an ME-ASM TraceID")
        sub = (directive.options or {}).get("sub")
        self.path, self.node = "", self.tree
        if sub:
            hit = _cur("asmdoc").find(self.tree, sub)
            if hit is None:
                raise directive.error(f"{directive.name}: no sub-assembly {sub} in {self.name}")
            self.path, self.node = hit

    def model(self):
        s = self.cfg.section("model") or {}
        mj = self.cfg.resolve(s.get("json", "generated/model.json"))
        if not mj.is_file():
            return None
        self.env.note_dependency(str(mj))
        return _cur("model").Model.load(mj)

    def asm_def(self, m):
        asms, _ = _cur("meassemblies").model_defs(m)
        return asms.get(self.node.id)

    def cam(self):
        """(record, folder with the per-variant outputs) of the current commit's run, or (None, None)."""
        rec, top, _ = _cur("mecam").current(Path(self.env.config.xd_cam_dir), self.name, self.repo, self.folder)
        if rec is None:
            return None, None
        self.env.note_dependency(str(top / "cam.json"))
        return rec, top


def _cell(s) -> str:
    from xdmod_sphinx.pcba import _cell as c
    return c(s)


def _lit(s) -> str:
    return f"``{s}``" if s not in (None, "") else "—"


def _rst(directive, lines: list[str], titles: bool = False) -> list[nodes.Node]:
    node = nodes.section() if titles else nodes.container()
    node.document = directive.state.document
    if titles:
        from sphinx.util.nodes import nested_parse_with_titles
        nested_parse_with_titles(directive.state, StringList(lines, source="xd-asm"), node)
    else:
        directive.state.nested_parse(StringList(lines, source="xd-asm"), directive.content_offset, node)
    return node.children


def _table(head, rows) -> list[str]:
    lines = [".. list-table::", "   :header-rows: 1", "   :class: xd-table", ""]
    for r in [head] + rows:
        lines.append(f"   * - {r[0]}")
        lines += [f"     - {c}" for c in r[1:]]
    return lines + [""]


def _need(i: str) -> str:
    return f":need:`{i}`" if i else "—"


def _xyz(v) -> str:
    return "(" + ", ".join(f"{x:g}" for x in v) + ") mm" if v else "—"


SUB = {"sub": directives.unchanged}


class Overview(Directive):
    required_arguments = 1
    option_spec = SUB

    def run(self):
        a = _Asm(self)
        ad = _cur("asmdoc")
        n = a.node
        lines = [f"* Assembly: {_need(n.id)}, FreeCAD document ``{n.file}``"]
        if n is a.tree:
            lines.append(f"* Skeleton: ``{a.folder.relative_to(a.repo)}/{_cur('meassemblies').skeleton_name(a.name)}``")
            rec, _ = a.cam()
            lines.append(f"* Version: ``{rec['version']}``, local output of {rec.get('date', '')}" if rec else
                         f"* Version, drawings, mass, findings: {LOCAL}")
            vs = ad.variants(a.tree)
            lines.append("* Variants: " + (", ".join(_lit(v) for v in vs) if vs != [ad.ALL] else
                                          "none (no link has ``Configs``)"))
        else:
            uses = ad.uses(a.tree, n)
            lines.append(f"* Used {len(uses)} time{'s' if len(uses) != 1 else ''} in {a.name}: "
                         + ", ".join(_lit(u) for u in uses))
        subs = [x for x in n.children if x.kind == "assembly"]
        lines.append("* Sub-assemblies: " + (", ".join(f"{_lit(s.designation)} ({_need(s.id)})" for s in subs)
                                            if subs else "none"))
        parts = sum(1 for _, x in n.walk() if x is not n and x.kind != "assembly")
        lines.append(f"* Parts below it (links, all levels): {parts}")
        return _rst(self, lines)


class Parameters(Directive):
    required_arguments = 1
    option_spec = SUB

    def run(self):
        a = _Asm(self)
        if a.node is not a.tree:
            return [nodes.paragraph(text=PARAMS_TOP)]
        m = a.model()
        asm = a.asm_def(m) if m is not None else None
        if asm is None:
            return [nodes.paragraph(text=NO_DATA)]
        sk = a.docs.get(str((a.folder / _cur("meassemblies").skeleton_name(a.name)).relative_to(a.repo)))
        rows = _cur("asmdoc").parameters(m, asm, sk.sem if sk else None)
        if not rows:
            return [nodes.paragraph(text=NO_DATA)]
        return _rst(self, ["The values of the ME model (``model/``) and of the alias in the spreadsheet ``Params`` "
                           "of the skeleton, which ``curatrix gen freecad-params`` writes and CK-F3 compares. "
                           "\"Budget\" marks a copy of a ``SYS-IF`` space-budget value, changed only together "
                           "with the budget.", ""]
                       + _table(["Alias", "Model", "Params", "Tolerance", "Port", "Source"],
                                [[_lit(r["alias"]), _cell(r["model"]), _cell(r["params"] or "missing"),
                                  _cell(r["tolerance"]), _need(r["port"]), "budget" if r["budget"] else "ME"]
                                 for r in rows]))


class Materials(Directive):
    required_arguments = 1
    option_spec = SUB

    def run(self):
        a = _Asm(self)
        rows = _cur("asmdoc").materials(a.node)
        if not rows:
            return [nodes.paragraph(text=NO_DATA)]
        return _rst(self, _table(["Material", "Density (g/cm³)", "Parts", "Print profiles"],
                                 [[_cell(r["material"] or "no Material"),
                                   f"{r['density']:g}" if r["density"] is not None else "—",
                                   _cell(", ".join(r["parts"])), _cell(", ".join(r["print_profiles"]))]
                                  for r in rows]))


class Interfaces(Directive):
    required_arguments = 1
    option_spec = SUB

    def run(self):
        a = _Asm(self)
        m = a.model()
        asm = a.asm_def(m) if m is not None else None
        if asm is None:
            return [nodes.paragraph(text=NO_DATA)]
        rows = _cur("asmdoc").interfaces(a.cfg, m, asm, a.folder if a.node is a.tree else None, a.docs)
        if not rows:
            return [nodes.paragraph(text="No ports.")]

        def place(p):
            return ", ".join(f"{k} = {v}" for k, v in p.items()) or "—"
        return _rst(self, _table(["Port", "Port def", "Conforms to", "Placement (model)", "LCS", "Values"],
                                 [[_lit(r["usage"]), f"{_lit(r['port_def'])} ({_need(r['id'])})",
                                   ", ".join(_need(c) for c in r["conforms"]) or "—", _cell(place(r["placement"])),
                                   _cell(", ".join(f"{Path(f).name}#{o}" for f, o in r["lcs"])),
                                   _cell(place(r["values"]))] for r in rows]))


class Bom(Directive):
    required_arguments = 1

    def run(self):
        a = _Asm(self)
        ad = _cur("asmdoc")
        vs = ad.variants(a.tree)
        rows = ad.indented_bom(a.tree, vs)
        if not rows:
            return [nodes.paragraph(text=NO_DATA)]
        docs = _registry_docs(a.repo)
        qty_head = ["Qty"] if vs == [ad.ALL] else [f"Qty {v}" for v in vs]

        def ident(r):
            i = _need(r["id"]) if r["id"].startswith("ME-") else _lit(r["id"])
            d = r["document"]
            if d:
                i += f", :external+{docs[d]}:doc:`{d} <index>`" if d in docs else f", document ``{d}``"
            return i
        body = [[_lit(r["pos"]), INDENT * r["level"] + _cell(r["designation"]), _cell(r["kind"]), ident(r),
                 *[str(r["qty"][v]) for v in vs], _cell(r["material"]), _cell(r["print_profile"]),
                 _cell(r["manufacturer"]), _cell(r["mpn"])] for r in rows]
        return _rst(self, ["Quantities per parent assembly. A standard fastener is named by its standard designation; "
                           "a board or harness is one line with its version and its document (its parts are in "
                           "the EE BOM). The flat list with totals for ordering is ``bom.csv`` of ``curatrix cam``.", ""]
                       + _table(["Pos", "Designation", "Kind", "ID", *qty_head, "Material", "Print profile",
                                 "Manufacturer", "MPN"], body))


def _registry_docs(repo: Path) -> dict[str, str]:
    from xdmod_sphinx.harness import _registry_docs as r
    return r(repo)


class Drawing(Directive):
    required_arguments = 1
    option_spec = SUB

    def run(self):
        from xdmod_sphinx import inline_svg
        a = _Asm(self)
        if a.node is not a.tree:
            return [nodes.paragraph(text=TOP_ONLY)]
        rec, top = a.cam()
        if rec is None:
            return [nodes.paragraph(text=LOCAL)]
        out, html, pdfs = [], [], []
        for v in rec.get("variants") or []:
            f = top / a.name / v / "drawing.svg"
            if f.is_file():
                html.append(f'<figure class="xd-cad">{inline_svg(f.read_text(encoding="utf-8"))}<figcaption>'
                            f'Drawing, variant {v}, {rec["version"]}</figcaption></figure>')
            if (top / a.name / v / "drawing.pdf").is_file():
                pdfs.append(f"{a.name}/{v}/drawing.pdf")
        if not html:
            return [nodes.paragraph(text=NO_DATA)]
        out.append(nodes.raw("", "\n".join(html), format="html"))
        if pdfs:                            # a file:// link would be dead on any other machine
            p = nodes.paragraph(text="PDF per variant, in the local output folder: ")
            p += nodes.literal(text=", ".join(pdfs))
            out.append(p)
        return out


class Exploded(Directive):
    required_arguments = 1
    option_spec = SUB

    def run(self):
        from xdmod_sphinx import inline_svg
        a = _Asm(self)
        if a.node is not a.tree:
            return [nodes.paragraph(text=TOP_ONLY)]
        rec, top = a.cam()
        if rec is None:
            return [nodes.paragraph(text=LOCAL)]
        src = ("the moves of explode.yaml" if (a.folder / "explode.yaml").is_file()
               else "automatic moves away from the assembly's centre (no explode.yaml)")
        html = []
        for v in rec.get("variants") or []:
            f = top / a.name / v / "exploded.svg"
            if f.is_file():
                html.append(f'<figure class="xd-cad">{inline_svg(f.read_text(encoding="utf-8"))}<figcaption>'
                            f'Exploded view, variant {v}, {rec["version"]}, {src}</figcaption></figure>')
        return [nodes.raw("", "\n".join(html), format="html")] if html else [nodes.paragraph(text=NO_DATA)]


class Renderings(Directive):
    """``<variant>/renderings/<view>.png`` of the cam output (task 5.30 makes them): Sphinx image
    nodes, so the PNGs are copied to ``_images/``; the views in ``VIEW_ORDER`` first."""
    required_arguments = 1
    option_spec = SUB

    def run(self):
        env = self.state.document.settings.env
        a = _Asm(self)
        if a.node is not a.tree:
            return [nodes.paragraph(text=TOP_ONLY)]
        rec, top = a.cam()
        if rec is None:
            return [nodes.paragraph(text=LOCAL)]
        docdir = Path(env.doc2path(env.docname)).parent
        result = []
        for v in rec.get("variants") or []:
            pngs = _renderings(rec, top / a.name / v, v)
            if not pngs:
                continue
            result.append(nodes.paragraph(text=f"Variant {v}, {rec['version']}: {', '.join(f.stem for f in pngs)}."))
            result += [nodes.image(uri=os.path.relpath(f, docdir), alt=f"Variant {v}, {f.stem}", width="48%")
                       for f in pngs]
        return result or [nodes.paragraph(text=NO_RENDERINGS)]


def _renderings(rec: dict, folder: Path, variant: str) -> list[Path]:
    """The PNGs of one variant: in the order cam.json lists them (``per_variant.<v>.renderings``,
    else ``renderings.views``, task 5.30), each ``renderings/<view>.png``; without a list, every
    PNG of ``renderings/``, the views of ``VIEW_ORDER`` first."""
    d = folder / "renderings"
    per = ((rec.get("per_variant") or {}).get(variant) or {}).get("renderings")
    top = rec.get("renderings")
    listed = per or (top.get("views") if isinstance(top, dict) else None)
    if isinstance(listed, dict):                # {view: file} or {view: {...}}: the views
        listed = [v if isinstance(v, str) else k for k, v in listed.items()]
    if listed:
        files = [d / f"{Path(str(x)).stem}.png" for x in listed]
        return [f for f in files if f.is_file()]
    return sorted(d.glob("*.png"), key=lambda f: (VIEW_ORDER.index(f.stem) if f.stem in VIEW_ORDER
                                                    else len(VIEW_ORDER), f.stem))


class Mass(Directive):
    required_arguments = 1
    option_spec = SUB

    def run(self):
        a = _Asm(self)
        rec, top = a.cam()
        if rec is None:
            return [nodes.paragraph(text=LOCAL)]
        ad = _cur("asmdoc")
        lines = []
        for v in rec.get("variants") or []:
            f = top / a.name / v / "mass.json"
            if not f.is_file():
                continue
            m = json.loads(f.read_text(encoding="utf-8"))
            if a.node is not a.tree:
                m = ad.sub_mass(m, ad.uses(a.tree, a.node)[0])
            if not m.get("parts"):
                continue
            inc = "" if m["complete"] else f" (incomplete: no mass for {', '.join(m['missing'])})"
            lines += [f"**Variant {v}** ({rec['version']}): mass {m['total_g']:g} g{inc}, center of gravity "
                      f"{_xyz(m['cog_mm'])} in the frame of {a.name}.", ""]
            lines += _table(["Part", "ID", "Material", "Volume (mm³)", "Mass (g)", "From", "Center of mass"],
                            [[_lit(p["path"]), _lit(p["id"]), _cell(p["material"]),
                              f"{p['volume_mm3']:g}" if p["volume_mm3"] is not None else "—",
                              f"{p['mass_g']:g}" if p["mass_g"] is not None else "—", _cell(p["source"]),
                              _xyz(p["com_mm"])] for p in m["parts"]])
        if not lines:
            return [nodes.paragraph(text=NO_DATA)]
        return _rst(self, ["Masses from the solid volume and the density of the material, or a part's own ``Mass`` "
                           "or ``Density`` property. Printed parts count as solid, without the infill of the print "
                           "profile, so their mass is an upper bound.", ""] + lines)


class Findings(Directive):
    required_arguments = 1
    option_spec = SUB
    STATES = {"open": "open error", "proposal": "proposed, not accepted", "accepted": "accepted",
              "warning": "warning", "stale": "stale"}

    def run(self):
        a = _Asm(self)
        rec, top = a.cam()
        f = top / "findings.json" if rec else None
        if f is None or not f.is_file():
            return [nodes.paragraph(text=LOCAL)]
        d = json.loads(f.read_text(encoding="utf-8"))
        rows = d.get("rows") or []
        if a.node is not a.tree:
            rows = [r for r in rows if r["description"].startswith(a.node.file + ":")
                    or any(r["description"].startswith(c.file + ":") for _, c in a.node.walk() if c is not a.node)]
        lines = [f"Checks {', '.join(d.get('checks') or [])} ({rec['version']}): {len(rows)} finding"
                 f"{'s' if len(rows) != 1 else ''}." + (f" An error is accepted in ``assemblies/{a.name}/accepted.yaml`` "
                                                       f"by a human commit with ``Accepted-by``." if rows else ""), ""]
        if rows:
            lines += _table(["State", "Check", "Rule", "Items", "Description", "Acceptance"],
                            [[self.STATES.get(r["state"], r["state"]), _lit(r["check"]), _lit(r["rule"]),
                              _cell(r["items"]), _cell(r["description"]), _cell(r["note"])] for r in rows])
        for k, why in sorted((d.get("skipped") or {}).items()):
            lines += [f"{k}: skipped, {_cell(why)}.", ""]
        return _rst(self, lines)


class SubAssemblies(Directive):
    """One chapter per sub-assembly (each distinct document once) with the sections of the top-level
    chapter and ``:sub:``. Drawings, exploded view, renderings and parameters print a fixed sentence
    there: ``curatrix cam`` and the skeleton are per top-level assembly (XD-ADR-0137, iteration 1)."""
    required_arguments = 1

    def run(self):
        a = _Asm(self)
        subs = _cur("asmdoc").sub_assemblies(a.tree)
        if not subs:
            return [nodes.paragraph(text=f"{a.name} has no sub-assemblies.")]
        lines = []
        for _, n in subs:
            title = f"Sub-assembly {n.designation} ({n.id})"
            lines += [title, "~" * len(title), ""]
            for what, d in (("Overview", "overview"), ("Drawings", "drawing"), ("Exploded view", "exploded"),
                            ("Renderings", "renderings"), ("Mass and center of gravity", "mass"),
                            ("Parameters", "parameters"), ("Materials", "materials"), ("Interfaces", "interfaces"),
                            ("Findings", "findings")):
                lines += [f".. rubric:: {what}", "", f".. xd-asm-{d}:: {a.name}", f"   :sub: {n.id}", ""]
        return _rst(self, lines, titles=True)


DIRECTIVES = {"xd-asm-overview": Overview, "xd-asm-parameters": Parameters, "xd-asm-materials": Materials,
              "xd-asm-interfaces": Interfaces, "xd-asm-bom": Bom, "xd-asm-drawing": Drawing,
              "xd-asm-exploded": Exploded, "xd-asm-renderings": Renderings, "xd-asm-mass": Mass,
              "xd-asm-findings": Findings, "xd-asm-subassemblies": SubAssemblies}


def setup(app):
    if "xd_cam_dir" not in app.config:      # also registered by the board and harness directives
        app.add_config_value("xd_cam_dir", "", "env")
    for name, cls in DIRECTIVES.items():
        app.add_directive(name, cls)
