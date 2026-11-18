"""Directives of the ``harnesses`` document (task 5.22; XD-ADR-0129; one document for every cable of the
repo, owner decision Q8 / finding 15 of tiacsys/xdmod#69): one directive set, so every cable section
looks the same. Each takes the harness name (``harness/<name>/<name>.yml`` of the repo this document
belongs to), except ``xd-harnesses``.

``xd-harnesses``        every harness of the repo (``cad.harnesses``): which local ``curatrix cam``
                        runs are missing or stale, then one section per cable with the four
                        sections below

``xd-harness-ends``     the ends: connector, the ``EE-PORT`` it mates with, the board (with a link to
                        its ``pcba-<name>`` document when the registry has one) or external part
                        that owns that port, and the harness's own ``EE-HAR``
``xd-harness-diagram``  the WireViz diagram from the local ``curatrix cam`` output
                        (``build/<area>/cam/<name>/<version>/``), with its version and commit; a
                        notice in CI and without a local run (``curatrix cam <repo>`` makes every
                        board and harness)
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


def xref_name(env, repo: Path, doc: str) -> str | None:
    """The intersphinx name of document ``doc`` in THIS build, or None when the build does not know
    it. The repo's own registry gives the prefix ``pcba_x`` (the zdocs default), the full set's
    registry ``pcba-x`` (prefix = ID); try the name each registry would give."""
    have = getattr(env.config, "intersphinx_mapping", None) or {}
    for name in (_registry_docs(repo).get(doc), doc, doc.replace("-", "_")):
        if name and name in have:
            return name
    return None


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
        env = self.state.document.settings.env
        from xdmod_sphinx.reference import curatrix_module
        kebab = curatrix_module("eeprojects").kebab
        rows = []
        for des, c in sorted(h.connectors().items()):
            f = hm.port_fields(c or {})
            port = hm.port_of(c or {}) or ""
            parts = []
            for kind, name, oid, pname in owners.get(port, []):
                if kind == "board":
                    doc = f"pcba-{kebab(name)}"
                    xn = xref_name(env, repo, doc)
                    link = f", :external+{xn}:doc:`{doc} <index>`" if xn else ""
                    parts.append(f"board {name} port ``{pname}`` (:need:`{oid}`{link})" if oid
                                 else f"board {name} port ``{pname}``")
                else:
                    parts.append(f"external part {name} port ``{pname}``")
            pins, labels = hm.pins_of(c or {})
            end = f.get("portName") or ""
            pdesc = (f"``{end}`` ({f.get('portType') or '?'}, :need:`{port}`)" if port.startswith("EE-PORT-") and end
                     else (f":need:`{port}`" if port.startswith("EE-PORT-") else _cell(end or port)))
            rows.append([des, pdesc, "; ".join(parts) or "—",
                         _cell(", ".join(f"{p} {lb}" for p, lb in zip(pins, labels)))])
        if not rows:
            return out + [nodes.paragraph(text=NO_DATA)]
        return out + _rst_table(self, ["End", "Port", "Mates with", "Pins"], rows)


def _cam_record(cam_dir: Path, name: str):
    """(record, folder) of the newest local ``curatrix cam`` output of a harness, or None."""
    best = None
    for f in (cam_dir / name).glob("*/cam.json"):
        try:
            rec = json.loads(f.read_text(encoding="utf-8"))
        except ValueError:
            continue
        if rec.get("kind") == "harness" and (best is None or f.stat().st_mtime > best[0]):
            best = (f.stat().st_mtime, rec, f.parent)
    return (best[1], best[2]) if best else None


def _head(repo: Path) -> str:
    import subprocess
    try:
        return subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True,
                              timeout=30).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def _watch_cam(env) -> None:
    # the cam output lives outside the source tree and appears or changes between builds:
    # re-read this document on every build (env-get-outdated below)
    if not hasattr(env, "xd_harness_docs"):
        env.xd_harness_docs = set()
    env.xd_harness_docs.add(env.docname)


class HarnessDiagram(Directive):
    required_arguments = 1

    def run(self):
        from xdmod_sphinx import inline_svg, notice, svg_figure
        env = self.state.document.settings.env
        name = self.arguments[0]
        _watch_cam(env)
        repo = _repo(self)
        found = _cam_record(Path(env.config.xd_cam_dir), name)
        svg = found[1] / name / f"{name}.svg" if found else None
        if not svg or not svg.is_file():
            return [notice(f"WireViz diagram of {name}: made locally by `curatrix cam {repo.name}` (every board "
                           f"and harness) or `curatrix cam {repo.name} {name}`; not part of this build.")]
        env.note_dependency(str(svg))
        rec = found[0]
        commit = str(rec.get("commit") or "")
        old = bool(commit) and commit != _head(repo)
        cap = f"{rec.get('version', '')}" + ("" if rec.get("release") else " (preview)") + \
              f", local output of {rec.get('date', '')}" + \
              (f", from commit {commit[:7]}, not the current one: run `curatrix cam {repo.name}` again" if old else "")
        return [nodes.raw("", svg_figure(inline_svg(svg.read_text(encoding="utf-8")), cap), format="html")]


class Harnesses(Directive):
    """Every harness of the repo in one document (owner decision Q8, finding 15 of tiacsys/xdmod#69)."""

    def run(self):
        from sphinx.util.nodes import nested_parse_with_titles
        from xdmod_sphinx import notice
        from xdmod_sphinx.reference import curatrix_module
        env = self.state.document.settings.env
        _watch_cam(env)
        repo = _repo(self)
        try:
            cfg = curatrix_module("checkcfg").load(repo / "checks.yaml", repo.parent)
            hm = curatrix_module("harness")
            hs = hm.discover(cfg) if hm.patterns(cfg) else []
        except Exception as e:  # noqa: BLE001
            raise self.error(f"xd-harnesses: {repo.name}/checks.yaml: {e}")
        for h in hs:
            env.note_dependency(str(h.yml))
        if not hs:
            return [nodes.paragraph(text="No harness in this repo (checks.yaml cad.harnesses).")]
        cam = Path(env.config.xd_cam_dir)
        head = _head(repo)
        missing, stale = [], []
        for h in hs:
            found = _cam_record(cam, h.name)
            if not found or not (found[1] / h.name / f"{h.name}.svg").is_file():
                missing.append(h.name)
            elif found[0].get("commit") and found[0].get("commit") != head:
                stale.append(h.name)
        out = [nodes.paragraph(text=f"{len(hs)} cable(s): " + ", ".join(h.name for h in hs) + ".")]
        if missing or stale:
            parts = ([f"no local output for {', '.join(missing)}"] if missing else []) + \
                    ([f"output of an older commit for {', '.join(stale)}"] if stale else [])
            out.append(notice(f"Missing curatrix cam runs: {'; '.join(parts)}. Run `curatrix cam {repo.name}` "
                              f"(every board and harness) and build the documents again. CI builds never "
                              f"have this output."))
        lines = []
        for h in hs:
            title = f"{h.title} ({h.name})" if h.title != h.name else h.name
            lines += [f".. _harness-{h.name}:", "", title, "-" * len(title), ""]
            for sub, d in (("Ends", "ends"), ("Diagram", "diagram"), ("Wiring", "wires"),
                           ("Bill of materials", "bom")):
                lines += [sub, "~" * len(sub), "", f".. xd-harness-{d}:: {h.name}", ""]
        node = nodes.section()
        node.document = self.state.document
        nested_parse_with_titles(self.state, StringList(lines, source="xd-harnesses"), node)
        return out + node.children


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
    app.add_directive("xd-harnesses", Harnesses)
    app.add_directive("xd-harness-ends", HarnessEnds)
    app.add_directive("xd-harness-diagram", HarnessDiagram)
    app.add_directive("xd-harness-wires", HarnessWires)
    app.add_directive("xd-harness-bom", HarnessBom)
