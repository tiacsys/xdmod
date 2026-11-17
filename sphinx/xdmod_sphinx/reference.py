"""Reference directives: tables and needs generated from xdmod's own config and code (D121,
framework-docs.md §4: "reference tables that come from code or config are generated, never typed").

All directives take no arguments. They read the xdmod tree this extension lives in, never an
installed copy, so a worktree or a pinned checkout documents itself.

``xd-need-types``   need types of ``needs/needs_config.toml`` (directive, ID prefix, title, links)
``xd-link-types``   the link-type table: owner type, link, targets, minimum, meaning
``xd-need-fields``  the need fields and their allowed values
``xd-id-kinds``     ID kinds known to curatrix (``curatrix.ids``) with their need types
``xd-check-table``  curatrix's built-in checks: level per stage, config section, rules enforced
``xd-check-needs``  one ``xd-check`` need per built-in check (ID from the check catalogue
                    ``curatrix/src/curatrix/data/checks.yaml``), each ``enforces`` its rules
``xd-cli``          the curatrix command line, from its argparse parser

Each directive builds reStructuredText and parses it in place, so the result is ordinary tables,
sections and needs (with working ``:need:`` references).
"""
from __future__ import annotations

import argparse
import importlib
import sys
import tomllib
from functools import lru_cache
from pathlib import Path

import yaml
from docutils import nodes
from docutils.parsers.rst import Directive
from docutils.statemachine import StringList
from sphinx.util.nodes import nested_parse_with_titles

XDMOD = Path(__file__).resolve().parents[2]
NEEDS_CONFIG = XDMOD / "needs" / "needs_config.toml"
CATALOGUE = XDMOD / "curatrix" / "src" / "curatrix" / "data" / "checks.yaml"
STAGES = ("local", "pr", "full", "baseline")


# ------------------------------------------------------------------ sources
@lru_cache(maxsize=None)
def needs_config(path: Path = NEEDS_CONFIG) -> dict:
    return tomllib.loads(path.read_text())["needs"]


def curatrix_module(name: str):
    """Import curatrix.<name> from this xdmod tree (not from an installed copy)."""
    src = str(XDMOD / "curatrix" / "src")
    if src not in sys.path:
        sys.path.insert(0, src)
    pkg = sys.modules.get("curatrix")
    if pkg is not None and not str(getattr(pkg, "__file__", "")).startswith(src):
        for k in [k for k in sys.modules if k == "curatrix" or k.startswith("curatrix.")]:
            del sys.modules[k]
    return importlib.import_module(f"curatrix.{name}")


def catalogue(path: Path = CATALOGUE) -> dict:
    return yaml.safe_load(path.read_text())["checks"]


def checks() -> list[dict]:
    """Built-in checks in curatrix order, joined with the catalogue."""
    cat = catalogue()
    out = []
    for cid, name, levels, section, cad, _fn in curatrix_module("checks").BUILTIN:
        c = cat.get(cid)
        if c is None or c.get("retired"):
            raise ValueError(f"{cid} is in checks.BUILTIN but not in {CATALOGUE.name}")
        out.append({"id": cid, "name": name, "levels": levels, "section": section, "cad": cad, **c})
    return out


# ------------------------------------------------------------------ rst helpers
def esc(text) -> str:
    return str(text).replace("\\", "\\\\").replace("*", "\\*").replace("`", "\\`").replace("|", "\\|")


def lit(text) -> str:
    return f"``{text}``" if text not in (None, "") else ""


def list_table(head: list[str], rows: list[list[str]], widths: str | None = None) -> list[str]:
    out = [".. list-table::", "   :header-rows: 1"]
    if widths:
        out.append(f"   :widths: {widths}")
    out.append("")
    for row in [head, *rows]:
        for i, cell in enumerate(row):
            out.append(("   * - " if i == 0 else "     - ") + (cell or ""))
    return out + [""]


def need_types_rows(cfg: dict) -> list[list[str]]:
    rows = []
    for t in cfg.get("types", []):
        links = []
        for ln, ld in (t.get("links") or {}).items():
            mn = (ld.get("schema") or {}).get("minItems", 0)
            links.append(f"``{ln}`` → " + ", ".join(lit(x) for x in ld.get("target_types", [])) + (f" (min {mn})" if mn else ""))
        rows.append([lit(t["directive"]), lit(t.get("prefix", "")), esc(t.get("title", "")), "; ".join(links)])
    return rows


def link_rows(cfg: dict) -> list[list[str]]:
    rows = []
    for t in cfg.get("types", []):
        for ln, ld in (t.get("links") or {}).items():
            mn = (ld.get("schema") or {}).get("minItems", 0)
            rows.append([lit(ln), lit(t["directive"]), ", ".join(lit(x) for x in ld.get("target_types", [])),
                         str(mn), esc(ld.get("description", ""))])
    return rows


def field_rows(cfg: dict) -> list[list[str]]:
    rows = []
    for name, f in (cfg.get("fields") or {}).items():
        s = f.get("schema") or {}
        if "enum" in s:
            values = ", ".join(lit(v) for v in s["enum"])
        elif s.get("type") == "array":
            values = "list of " + (s.get("items") or {}).get("type", "string")
        else:
            values = s.get("type", "")
        if s.get("pattern") or (s.get("items") or {}).get("pattern"):
            values += " matching " + lit(s.get("pattern") or s["items"]["pattern"])
        rows.append([lit(name), values, esc(f.get("description", ""))])
    return rows


def id_kind_rows(cfg: dict) -> list[list[str]]:
    ids = curatrix_module("ids")
    by_prefix = {t.get("prefix", "").rstrip("-"): t for t in cfg.get("types", [])}
    rows = []
    for kind in sorted(ids.ALL_KINDS):
        t = by_prefix.get(kind)
        if t is None:
            rows.append([lit(kind), "(reserved, not a need)", ""])
        else:
            rows.append([lit(kind), esc(t.get("title", "")), lit(t["directive"])])
    return rows


def check_table_lines() -> list[str]:
    rows = []
    for c in checks():
        levels = ", ".join(f"{s}: {c['levels'][s]}" for s in STAGES if s in c["levels"])
        rows.append([f":need:`{c['need']}`", lit(c["id"]), esc(c["name"]), lit(c["section"] or "always"),
                     levels, ", ".join(f":need:`{r}`" for r in c["enforces"])])
    return list_table(["Need", "Check", "Name", "checks.yaml section", "Level per stage", "Enforces"], rows,
                      "10 8 30 14 22 16")


def check_need_lines() -> list[str]:
    out = []
    for c in checks():
        levels = "; ".join(f"{s}: {c['levels'][s]}" for s in STAGES if s in c["levels"])
        out += [f".. xd-check:: {esc(c['name'])}", f"   :id: {c['need']}", f"   :check_id: {c['id']}",
                "   :status: valid", "   :enforces: " + ", ".join(c["enforces"]), "",
                f"   {esc(c['description'])}", "",
                f"   Runs when the ``{c['section']}`` section of ``checks.yaml`` is set." if c["section"]
                else "   Runs for every repo.",
                f"   Levels: {levels}. Run it alone: ``curatrix check <repo> --only {c['id']}``.", ""]
    for cid, c in catalogue().items():          # removed checks keep a retired need (D130)
        if c.get("retired"):
            out += [f".. xd-check:: {esc(cid)} (retired)", f"   :id: {c['need']}", f"   :check_id: {cid}",
                    "   :status: retired", "   :enforces: " + ", ".join(c["enforces"]), "",
                    f"   {esc(c['description'])}", "", f"   Retired: {esc(c['retired'])}.", ""]
    return out


def _parser_actions(p: argparse.ArgumentParser):
    subs = [a for a in p._actions if isinstance(a, argparse._SubParsersAction)]
    opts = [a for a in p._actions if not isinstance(a, (argparse._SubParsersAction, argparse._HelpAction))]
    return opts, subs


def cli_lines() -> list[str]:
    cli = curatrix_module("cli")
    p = cli.parser()
    _, subs = _parser_actions(p)
    helps = {}
    for s in subs:
        for ca in s._choices_actions:
            helps[ca.dest] = ca.help
    out = [esc(p.description or ""), ""]
    rows = []
    for s in subs:
        for name in s.choices:
            if helps.get(name) in (None, argparse.SUPPRESS):
                continue
            rows.append([f":ref:`curatrix {name} <cli-{name}>`", esc(helps[name])])
    out += list_table(["Command", "Does"], rows, "25 75")
    for s in subs:
        for name, sp in s.choices.items():
            if helps.get(name) in (None, argparse.SUPPRESS):
                continue
            title = f"curatrix {name}"
            out += [f".. _cli-{name}:", "", title, "-" * len(title), "", esc(helps[name]) + ".", "",
                    ".. code-block:: text", ""]
            out += ["   " + ln for ln in sp.format_help().rstrip().splitlines()] + [""]
    return out


# ------------------------------------------------------------------ directives
class _Generated(Directive):
    has_content = False
    required_arguments = 0
    optional_arguments = 0

    def lines(self) -> list[str]:
        raise NotImplementedError

    def run(self):
        env = self.state.document.settings.env
        for dep in (NEEDS_CONFIG, CATALOGUE, XDMOD / "curatrix" / "src" / "curatrix" / "checks.py",
                    XDMOD / "curatrix" / "src" / "curatrix" / "cli.py"):
            env.note_dependency(str(dep))
        src = f"<{self.name}>"
        node = nodes.container(classes=["xd-generated"])
        nested_parse_with_titles(self.state, StringList(self.lines(), source=src), node)
        return node.children


class NeedTypes(_Generated):
    def lines(self):
        return list_table(["Directive", "ID prefix", "Need type", "Link types (→ targets)"],
                          need_types_rows(needs_config()), "12 12 20 56")


class LinkTypes(_Generated):
    def lines(self):
        return list_table(["Link", "Owner (source)", "Targets", "Min", "Meaning"], link_rows(needs_config()),
                          "12 14 24 6 44")


class NeedFields(_Generated):
    def lines(self):
        return list_table(["Field", "Values", "Meaning"], field_rows(needs_config()), "18 32 50")


class IdKinds(_Generated):
    def lines(self):
        return list_table(["Kind", "Need type", "Directive"], id_kind_rows(needs_config()), "20 50 30")


class CheckTable(_Generated):
    def lines(self):
        return check_table_lines()


class CheckNeeds(_Generated):
    def lines(self):
        return check_need_lines()


class Cli(_Generated):
    def lines(self):
        return cli_lines()


DIRECTIVES = {"xd-need-types": NeedTypes, "xd-link-types": LinkTypes, "xd-need-fields": NeedFields,
              "xd-id-kinds": IdKinds, "xd-check-table": CheckTable, "xd-check-needs": CheckNeeds,
              "xd-cli": Cli}


def setup(app):
    for name, cls in DIRECTIVES.items():
        app.add_directive(name, cls)
