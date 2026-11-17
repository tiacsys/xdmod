"""Directives of the ``harness-<name>`` document (task 5.22; XD-ADR-0129): one directive set, so every
harness document looks the same. Each takes the harness name (``harness/<name>/<name>.yml`` of the
repo this document belongs to).

``xd-harness-ends``     the ends: connector, the ``EE-PORT`` it mates with, the board (with a link to
                        its ``pcba-<name>`` document when the registry has one) or external part
                        that owns that port, and the harness's own ``EE-HAR``
``xd-harness-diagram``  the WireViz diagram from the local ``curatrix cam`` output
                        (``build/<area>/cam/<name>/<version>/``), with its version; a notice in CI
``xd-harness-wires``    the pin-to-pin table (plain Python, from the YAML)
``xd-harness-bom``      the harness BOM (plain Python, from the YAML)

A section without data prints one fixed sentence. The YAML and the model are read with
``curatrix.harness`` in plain Python; WireViz itself is never imported (GPL-3.0, XD-ADR-0127).
"""
from __future__ import annotations

import json
from pathlib import Path

import yaml
from docutils import nodes
from docutils.parsers.rst import Directive
from docutils.statemachine import StringList

NO_DATA = "No data yet."


def _repo(directive) -> Path:
    return Path(directive.state.document.settings.env.config.xd_repo)


def _harness(directive):
    from xdmod_sphinx.reference import curatrix_module
    hm = curatrix_module("harness")
    name = directive.arguments[0]
    yml = _repo(directive) / "harness" / name / f"{name}.yml"
    if not yml.is_file():
        raise directive.error(f"{directive.name}: no harness {name} (harness/{name}/{name}.yml)")
    directive.state.document.settings.env.note_dependency(str(yml))
    h = hm.load(yml)
    if h.error:
        raise directive.error(f"{directive.name}: harness/{name}/{name}.yml: {h.error}")
    return hm, h


def _cell(s: str) -> str:
    return s.replace("|", "\\|") if s else "—"


def _rst_table(directive, head, rows) -> list[nodes.Node]:
    lines = [".. list-table::", "   :header-rows: 1", "   :class: xd-table", ""]
    for r in [head] + rows:
        lines.append(f"   * - {r[0]}")
        lines += [f"     - {c}" for c in r[1:]]
    node = nodes.container()
    directive.state.nested_parse(StringList(lines, source="xd-harness"), directive.content_offset, node)
    return node.children


def _rst(directive, text: str) -> list[nodes.Node]:
    node = nodes.container()
    directive.state.nested_parse(StringList(text.splitlines(), source="xd-harness"), directive.content_offset, node)
    return node.children


def _registry_docs(repo: Path) -> dict[str, str]:
    """Document ID -> its intersphinx name in zdocs (the registry ``prefix``, else the ID with
    ``_`` for ``-``)."""
    try:
        cy = yaml.safe_load((repo / "checks.yaml").read_text()) or {}
        reg = repo / ((cy.get("docs") or {}).get("registry") or "docs/documents.yaml")
        docs = (yaml.safe_load(reg.read_text()) or {}).get("documents") or {}
        return {d: (m or {}).get("prefix") or d.replace("-", "_") for d, m in docs.items()}
    except (OSError, yaml.YAMLError, AttributeError):
        return {}


def _model(repo: Path):
    from xdmod_sphinx.reference import curatrix_module
    try:
        cy = yaml.safe_load((repo / "checks.yaml").read_text()) or {}
        mj = repo / ((cy.get("model") or {}).get("json") or "generated/model.json")
        return curatrix_module("model").Model.load(mj) if mj.is_file() else None
    except (OSError, ValueError, yaml.YAMLError):
        return None


class HarnessEnds(Directive):
    required_arguments = 1

    def run(self):
        hm, h = _harness(self)
        repo = _repo(self)
        out = []
        if h.trace_id:
            out += _rst(self, f"Harness :need:`{h.trace_id}`, ``harness/{h.name}/{h.name}.yml``.")
        m = _model(repo)
        owners = hm.port_owners(m) if m is not None else {}
        docs = _registry_docs(repo)
        from xdmod_sphinx.reference import curatrix_module
        kebab = curatrix_module("eeprojects").kebab
        rows = []
        for des, c in sorted(h.connectors().items()):
            port = hm.port_of(c or {}) or ""
            parts = []
            for kind, name, oid in owners.get(port, []):
                if kind == "board":
                    doc = f"pcba-{kebab(name)}"
                    link = f", :external+{docs[doc]}:doc:`{doc} <index>`" if doc in docs else ""
                    parts.append(f"board {name} (:need:`{oid}`{link})" if oid else f"board {name}")
                else:
                    parts.append(f"external part {name}")
            pins, labels = hm.pins_of(c or {})
            rows.append([des, f":need:`{port}`" if port.startswith("EE-PORT-") else _cell(port),
                         "; ".join(parts) or "—", _cell(", ".join(f"{p} {lb}" for p, lb in zip(pins, labels)))])
        if not rows:
            return out + [nodes.paragraph(text=NO_DATA)]
        return out + _rst_table(self, ["End", "Port", "Mates with", "Pins"], rows)


class HarnessDiagram(Directive):
    required_arguments = 1

    def run(self):
        from xdmod_sphinx import inline_svg, notice
        env = self.state.document.settings.env
        name = self.arguments[0]
        # the cam output lives outside the source tree and appears or changes between builds:
        # re-read this document on every build (env-get-outdated below)
        if not hasattr(env, "xd_harness_docs"):
            env.xd_harness_docs = set()
        env.xd_harness_docs.add(env.docname)
        cam = Path(env.config.xd_cam_dir) / name
        best = None
        for f in cam.glob("*/cam.json"):
            try:
                rec = json.loads(f.read_text(encoding="utf-8"))
            except ValueError:
                continue
            if rec.get("kind") == "harness" and (best is None or f.stat().st_mtime > best[0]):
                best = (f.stat().st_mtime, rec, f.parent)
        svg = best[2] / name / f"{name}.svg" if best else None
        if not svg or not svg.is_file():
            return [notice(f"WireViz diagram of {name}: built locally with `curatrix cam <repo> {name}`; "
                           f"not part of this build.")]
        env.note_dependency(str(svg))
        rec = best[1]
        cap = f"{rec.get('version', '')}" + ("" if rec.get("release") else " (preview)") + \
              f", local output of {rec.get('date', '')}"
        html = f'<figure class="xd-cad">{inline_svg(svg.read_text(encoding="utf-8"))}<figcaption>{cap}</figcaption></figure>'
        return [nodes.raw("", html, format="html")]


class HarnessWires(Directive):
    required_arguments = 1

    def run(self):
        hm, h = _harness(self)
        rows = [[_cell(x) for x in r] for r in hm.pin_table(h)]
        if not rows:
            return [nodes.paragraph(text=NO_DATA)]
        return _rst_table(self, ["From", "Signal", "Wire", "Color", "To", "Signal"], rows)


class HarnessBom(Directive):
    required_arguments = 1

    def run(self):
        hm, h = _harness(self)
        rows = [[_cell(x) for x in r] for r in hm.bom(h)]
        if not rows:
            return [nodes.paragraph(text=NO_DATA)]
        return _rst_table(self, ["Designators", "Description", "Qty", "Unit", "Manufacturer", "MPN"], rows)


def _outdated(app, env, added, changed, removed):
    return sorted(d for d in getattr(env, "xd_harness_docs", set()) if d in env.found_docs)


def _purge(app, env, docname):
    getattr(env, "xd_harness_docs", set()).discard(docname)


def _merge(app, env, docnames, other):
    env.xd_harness_docs = getattr(env, "xd_harness_docs", set()) | \
        (getattr(other, "xd_harness_docs", set()) & set(docnames))


def setup(app):
    app.add_config_value("xd_cam_dir", "", "env")
    app.connect("env-get-outdated", _outdated)
    app.connect("env-purge-doc", _purge)
    app.connect("env-merge-info", _merge)
    app.add_directive("xd-harness-ends", HarnessEnds)
    app.add_directive("xd-harness-diagram", HarnessDiagram)
    app.add_directive("xd-harness-wires", HarnessWires)
    app.add_directive("xd-harness-bom", HarnessBom)
