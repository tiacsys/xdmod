"""xdmod Sphinx extension (D34; doc-architecture.md §4).

Directives
----------
``sysml-view``
    ``.. sysml-view:: /views/jointInterconnection.drawio.svg`` (path in the Sphinx source tree;
    ``/`` = source root). Puts the committed editable SVG (D96) inline. Cells with a trace ID carry
    ``need:<ID>`` links; they are resolved to the need's page in this build (never hard URLs:
    hosting is versioned, D55). An unknown ID is a warning (fails a strict build).
    Options: ``:caption:``. No browser is needed: the picture is in the committed file.

``xd-needimport``
    ``.. xd-needimport:: /generated/retired-needs.json`` with ``:optional:`` -- like ``needimport``
    (all other options are passed on), but an optional file that does not exist is skipped
    silently (e.g. ``retired-needs.json`` before the first tombstone). ``:missing: <sentence>``
    makes the file optional too, and prints the sentence in its place (e.g. preview test results
    that exist only after a local test run). ``:stamp:`` reads the run stamp next to the file
    (``<name>.stamp.json``, written by ``curatrix evidence preview --commit-of``): the needs are shown
    with a line "results of the local test run of <date>, commit <sha>" only while the repo is at
    that commit; otherwise (or without a stamp) the ``:missing:`` sentence is shown.

``kicad-sheet``, ``kicad-bom``, ``kicad-nets``, ``freecad-drawing``, ``freecad-3d``
    CAD content that needs the CAD tools. The argument names an export below ``xd_cad_dir``
    (default ``build/<area>/cad``, made by ``curatrix gen cad-exports`` locally). If the export is
    there it is shown (SVG inline, CSV as a table, other files as a download link); if not -- in
    CI, or before the export ran -- the directive shows a short notice instead ("built locally"),
    without a warning, so a strict build passes (D56).

``freecad-params``
    ``.. freecad-params:: /parts/link.FCStd`` -- spreadsheet aliases and values as a table, read in
    plain Python from the committed ``.FCStd`` (works in CI). ``:sheet:`` limits it to one sheet.

``tracechain``
    ``.. tracechain:: sys-need <-refines- sys-req <-satisfies- sys-el <-realizes- ee-cmp``
    One row per path from each need of the first type down the back links; gaps are shown.

``xd-harness-ends``, ``xd-harness-diagram``, ``xd-harness-wires``, ``xd-harness-bom``
    The ``harness-<name>`` document (task 5.22); see ``harness.py``.

Reference directives (``xd-need-types``, ``xd-link-types``, ``xd-need-fields``, ``xd-id-kinds``,
``xd-check-table``, ``xd-check-needs``, ``xd-cli``)
    Tables and needs generated from needs_config.toml and curatrix; see ``reference.py``.

``coverage-matrix``, ``config-page``
    Iteration 1 stubs: they render a notice. (Requirement x configuration matrix, D104; one page per
    configuration, D106.)
"""
from __future__ import annotations

import csv
import re
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

from docutils import nodes
from docutils.parsers.rst import Directive, directives
from sphinx.util import logging

log = logging.getLogger(__name__)
__version__ = "0.1.0"


class sysml_view(nodes.General, nodes.Element):
    pass


class tracechain(nodes.General, nodes.Element):
    pass


def _src_path(directive, arg: str) -> tuple[str, Path]:
    env = directive.state.document.settings.env
    rel, path = env.relfn2path(arg, env.docname)
    env.note_dependency(rel)
    return rel, Path(path)


def notice(text: str, cls: str = "xd-notice") -> nodes.Node:
    n = nodes.note()
    n["classes"].append(cls)
    n += nodes.paragraph(text=text)
    return n


# ------------------------------------------------------------------ sysml-view
def inline_svg(text: str) -> str:
    """The SVG for HTML: no XML declaration, without the embedded diagram (content attribute)."""
    text = re.sub(r"^<\?xml[^>]*>\s*", "", text.strip())
    text = re.sub(r'\scontent="[^"]*"', "", text, count=1)
    return re.sub(r'\sdata-xdmod-hash="[^"]*"', "", text, count=1)


class SysmlViewDirective(Directive):
    required_arguments = 1
    option_spec = {"caption": directives.unchanged}

    def run(self):
        _, path = _src_path(self, self.arguments[0])
        if not path.exists():
            raise self.error(f"sysml-view: {self.arguments[0]} not found (is it in the conf.py `generated` inputs?)")
        svg = inline_svg(path.read_text(encoding="utf-8"))
        return [sysml_view(svg=svg, caption=self.options.get("caption", ""), src=self.arguments[0])]


def need_url(app, fromdoc: str, need: dict) -> str:
    if need.get("is_external"):
        return need.get("external_url") or ""
    return app.builder.get_relative_uri(fromdoc, need["docname"]) + "#" + need["id"]


def _needs(app):
    from sphinx_needs.data import SphinxNeedsData
    return SphinxNeedsData(app.env).get_needs_view()


def resolve(app, doctree, fromdoc):
    needs = None
    for node in list(doctree.findall(sysml_view)):
        needs = needs if needs is not None else _needs(app)

        def repl(m, node=node):
            nid = m.group(2)
            if nid not in needs:
                log.warning(f"sysml-view {node['src']}: link to unknown need {nid}", location=node)
                return m.group(1) + "#" + '"'
            return m.group(1) + need_url(app, fromdoc, needs[nid]) + '"'

        svg = re.sub(r'((?:xlink:)?href=")need:([^"]+)"', repl, node["svg"])
        html = f'<figure class="sysml-view">{svg}'
        if node["caption"]:
            html += f"<figcaption>{node['caption']}</figcaption>"
        node.replace_self(nodes.raw("", html + "</figure>", format="html"))
    for node in list(doctree.findall(tracechain)):
        needs = needs if needs is not None else _needs(app)
        node.replace_self(_tracechain_table(app, fromdoc, needs, node["types"], node["links"]))


# ------------------------------------------------------------------ xd-needimport
class XdNeedimportDirective(Directive):
    required_arguments = 1
    final_argument_whitespace = False
    has_content = False
    option_spec = {"optional": directives.flag, "missing": directives.unchanged, "stamp": directives.flag}
    MISSING = "No results: the file is not there in this build."

    def run(self):
        _, path = _src_path(self, self.arguments[0])
        missing = [nodes.paragraph(text=self.options.get("missing") or self.MISSING)]
        if not path.exists():
            if "missing" in self.options:
                return missing
            if "optional" in self.options:
                return []
            raise self.error(f"xd-needimport: {self.arguments[0]} not found")
        out = []
        if "stamp" in self.options:
            line = _stamp_line(self.state.document.settings.env.config, path)
            if line is None:
                return missing
            out.append(nodes.paragraph(text=line))
        lines = [f".. needimport:: {self.arguments[0]}"]
        for k, v in self.options.items():
            if k not in ("optional", "missing", "stamp"):
                lines.append(f"   :{k}: {v if v is not None else ''}".rstrip())
        self.state_machine.insert_input(lines, self.state_machine.input_lines.source(0))
        return out


def _stamp_line(config, path: Path) -> str | None:
    """The line shown above stamped previews, or None if there is no stamp or the repo has moved
    on from the stamped commit (an old run must not look like this build's result)."""
    import json
    import subprocess
    sp = path.with_name(path.stem + ".stamp.json")
    if not sp.exists():
        return None
    try:
        st = json.loads(sp.read_text())
    except ValueError:
        return None
    repo = getattr(config, "xd_repo", "") or ""
    head = subprocess.run(["git", "-C", repo, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip() \
        if repo else ""
    if not st.get("commit") or st["commit"] != head:
        return None
    return (f"Results of the local test run of {st.get('run_date') or 'an unknown date'}, commit {st['commit'][:12]}"
            f"{' with uncommitted changes' if st.get('dirty') else ''}. They are previews, never evidence.")


def _passthrough_options(d):
    class Opts(dict):
        def __missing__(self, key):
            return directives.unchanged
    d.option_spec = Opts(d.option_spec)
    return d


# ------------------------------------------------------------------ CAD directives (notice in CI)
CAD_WHAT = {
    "kicad-sheet": "KiCad schematic sheet (SVG from kicad-cli)",
    "kicad-bom": "KiCad bill of materials (CSV from kicad-cli)",
    "kicad-nets": "KiCad nets vs. interfaces",
    "freecad-drawing": "FreeCAD TechDraw drawing (SVG)",
    "freecad-3d": "FreeCAD 3D view (GLB)",
}


def make_cad_directive(name: str):
    class CadDirective(Directive):
        required_arguments = 1
        option_spec = {"caption": directives.unchanged}

        def run(self):
            env = self.state.document.settings.env
            cad_dir = Path(env.config.xd_cad_dir)
            f = cad_dir / self.arguments[0].lstrip("/")
            if not f.exists():
                return [notice(f"{CAD_WHAT[name]} '{self.arguments[0]}': built locally with the CAD tools "
                               f"(curatrix gen cad-exports); not part of this build.")]
            env.note_dependency(str(f))
            cap = self.options.get("caption", "")
            if f.suffix == ".svg":
                html = f'<figure class="xd-cad">{inline_svg(f.read_text(encoding="utf-8"))}'
                html += f"<figcaption>{cap}</figcaption></figure>" if cap else "</figure>"
                return [nodes.raw("", html, format="html")]
            if f.suffix == ".csv":
                with open(f, newline="", encoding="utf-8") as fh:
                    rows = list(csv.reader(fh))
                return [_table(rows[0], rows[1:])] if rows else []
            return [nodes.paragraph("", "", nodes.reference("", f.name, refuri=f.as_uri()))]
    CadDirective.__name__ = f"CadDirective_{name.replace('-', '_')}"
    return CadDirective


def _table(head, rows, classes=("xd-table",)):
    table = nodes.table(classes=list(classes))
    tg = nodes.tgroup(cols=len(head))
    table += tg
    for _ in head:
        tg += nodes.colspec(colwidth=1)
    th = nodes.thead()
    tg += th
    hr = nodes.row()
    th += hr
    for h in head:
        hr += nodes.entry("", nodes.paragraph(text=str(h)))
    tb = nodes.tbody()
    tg += tb
    for r in rows:
        row = nodes.row()
        tb += row
        for c in list(r) + [""] * (len(head) - len(r)):
            row += nodes.entry("", nodes.paragraph(text=str(c)))
    return table


class FreecadParamsDirective(Directive):
    required_arguments = 1
    option_spec = {"sheet": directives.unchanged}

    def run(self):
        _, path = _src_path(self, self.arguments[0])
        if not path.exists():
            raise self.error(f"freecad-params: {self.arguments[0]} not found")
        with zipfile.ZipFile(path) as z:
            root = ET.fromstring(z.read("Document.xml"))
        types = {o.get("name"): o.get("type") for o in root.iter("Object") if o.get("type")}
        rows = []
        data = root.find("ObjectData")
        for o in (data if data is not None else []):
            if types.get(o.get("name")) != "Spreadsheet::Sheet":
                continue
            label = o.get("name")
            for p in o.iter("Property"):
                if p.get("name") == "Label":
                    s = p.find("String")
                    label = s.get("value") if s is not None else label
            if self.options.get("sheet") and self.options["sheet"] not in (label, o.get("name")):
                continue
            for c in o.iter("Cell"):
                if c.get("alias"):
                    rows.append((label, c.get("alias"), (c.get("content") or "").lstrip("=")))
        if not rows:
            return [notice(f"freecad-params: no spreadsheet aliases in {self.arguments[0]}")]
        return [_table(("Sheet", "Parameter", "Value"), sorted(rows))]


# ------------------------------------------------------------------ tracechain (port of the spike)
class TraceChainDirective(Directive):
    required_arguments = 1
    final_argument_whitespace = True

    def run(self):
        toks = self.arguments[0].split()
        types, links = [toks[0]], []
        for i in range(1, len(toks), 2):
            m = re.fullmatch(r"<-([\w-]+)-", toks[i])
            if not m or i + 1 >= len(toks):
                raise self.error(f"tracechain: bad step {toks[i]!r}")
            links.append(m.group(1))
            types.append(toks[i + 1])
        return [tracechain(types=types, links=links)]


def _tracechain_table(app, fromdoc, needs, types, links):
    back: dict[str, dict[str, list[str]]] = {}
    for nid, n in needs.items():
        for lt in set(links):
            for t in n.get(lt) or []:
                back.setdefault(t, {}).setdefault(lt, []).append(nid)
    rows = []

    def walk(path):
        depth = len(path)
        if depth == len(types):
            rows.append(path)
            return
        cur = path[-1]
        nxt = [needs[i] for i in back.get(cur["id"], {}).get(links[depth - 1], []) if i in needs
               and needs[i]["type"] == types[depth]]
        if not nxt:
            rows.append(path + [None] * (len(types) - depth))
            return
        for n in sorted(nxt, key=lambda n: n["id"]):
            walk(path + [n])

    for start in sorted((n for n in needs.values() if n["type"] == types[0]), key=lambda n: n["id"]):
        walk([start])
    head = [t if i == 0 else f"{t} ({links[i - 1]})" for i, t in enumerate(types)]
    table = _table(head, [], classes=("tracechain",))
    tbody = next(table.findall(nodes.tbody))
    gaps = 0
    for path in rows:
        r = nodes.row()
        tbody += r
        for n in path:
            e = nodes.entry()
            if n is None:
                e += nodes.paragraph(text="(missing)", classes=["trace-gap"])
                gaps += 1
            else:
                p = nodes.paragraph()
                p += nodes.reference("", n["id"], refuri=need_url(app, fromdoc, n))
                extra = [n.get("title") or ""] + ([f"[{n['status']}]"] if n.get("status") else [])
                p += nodes.Text(" — " + " ".join(x for x in extra if x))
                e += p
            r += e
    cont = nodes.container()
    cont += table
    cont += nodes.paragraph(text=f"{len(rows)} chain(s), {gaps} gap(s).")
    return cont


# ------------------------------------------------------------------ stubs for later iterations
def make_stub(name: str, what: str):
    class Stub(Directive):
        optional_arguments = 1
        final_argument_whitespace = True
        has_content = True
        option_spec = None

        def run(self):
            return [notice(f"{name}: {what} -- not implemented yet (XDMOD iteration 1 stub).")]
    Stub.__name__ = f"Stub_{name.replace('-', '_')}"
    return Stub


def setup(app):
    app.add_config_value("xd_cad_dir", "", "env")
    app.add_config_value("xd_repo", "", "env")
    app.add_node(sysml_view)
    app.add_node(tracechain)
    app.add_directive("sysml-view", SysmlViewDirective)
    app.add_directive("xd-needimport", _passthrough_options(XdNeedimportDirective))
    for name in CAD_WHAT:
        app.add_directive(name, make_cad_directive(name))
    app.add_directive("freecad-params", FreecadParamsDirective)
    app.add_directive("tracechain", TraceChainDirective)
    app.add_directive("coverage-matrix", make_stub("coverage-matrix", "requirement x configuration coverage (D104)"))
    app.add_directive("config-page", make_stub("config-page", "one generated page per configuration (D106)"))
    app.add_directive("sysml-element", make_stub("sysml-element", "attributes, ports and relations of a model element"))
    from xdmod_sphinx import harness, reference
    reference.setup(app)
    harness.setup(app)
    app.connect("doctree-resolved", resolve)
    return {"version": __version__, "parallel_read_safe": True, "parallel_write_safe": True}
