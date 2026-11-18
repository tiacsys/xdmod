"""`curatrix new pcba <BoardDef> [--repo REPO]`: a KiCad project for a board def of the EE model
(task 5.17; XD-ADR-0128, XD-ADR-0129, XD-ADR-0142).

Creates, from ``xdmod/templates/kicad-pcba/``:

* ``pcba/<name>/<name>.kicad_pro`` with the text variables ``TraceID`` (the def's ``EE-PCBA``)
  ``XD_BOARD = <name>`` and ``XD_VERSION = "unversioned"``, the ERC and DRC severities of the
  template, no variants;
* ``<name>.kicad_sch`` and ``<name>.kicad_pcb`` (title block: title ``${XD_BOARD}``, rev
  ``${XD_VERSION}``; two silkscreen lines with both, CK-F11), then saved by KiCad itself (``kicad-cli sch|pcb
  upgrade --force`` under the ``kicad-cli`` limits and the workspace-local KiCad config);
* ``sym-lib-table`` and ``fp-lib-table`` with workspace libraries only;
* ``<name>.kicad_jobset`` (the shared jobset template);
* the document ``docs/pcbas/pcba-<name>/`` and its entry in the docs registry (``doc_dir:
  pcbas/pcba-<name>``; owner decision Q8 of tiacsys/xdmod#69); the document embeds the
  board's interconnection view (block diagram) and variants view from the model, or says which
  view to add (tiacsys/xdmod#69 finding 3).

``<name>`` is the def's name in kebab case (``JointController`` -> ``joint-controller``).
"""
from __future__ import annotations

import re
import uuid
from pathlib import Path

import yaml

from curatrix import eeprojects, model as modelmod

TEMPLATE_FILES = {"pcba.kicad_pro": "{name}.kicad_pro", "pcba.kicad_sch": "{name}.kicad_sch",
                  "pcba.kicad_pcb": "{name}.kicad_pcb", "pcba.kicad_jobset": "{name}.kicad_jobset",
                  "sym-lib-table": "sym-lib-table", "fp-lib-table": "fp-lib-table"}


class NewError(Exception):
    pass


def title_of(element: str) -> str:
    return re.sub(r"(?<=[a-z0-9])(?=[A-Z])", " ", element)


def element_id_of(p: dict) -> str:
    return p.get("declaredShortName") or p.get("shortName") or ""


def find_board_def(cfg, element: str) -> dict:
    """The board def (model element) of a board def name, qualified name or ID."""
    s = cfg.section("model")
    if s is None:
        raise NewError(f"{cfg.repo.name} has no model section in checks.yaml; a board project names a board "
                       f"def of the EE model (XD-ADR-0128)")
    mj = cfg.resolve(s.get("json", "generated/model.json"))
    if not mj.exists():
        raise NewError(f"{cfg.repo.name}/{mj.relative_to(cfg.repo)} missing; run `curatrix gen model {cfg.repo.name}`")
    m = modelmod.Model.load(mj)
    boards, externals, _ = eeprojects.model_defs(m)
    for bid, p in boards.items():
        if element in (p.get("name"), p.get("qualifiedName"), bid):
            return p
    for p in externals.values():
        if element in (p.get("name"), p.get("qualifiedName")):
            raise NewError(f"{element} is an external part: it has ports, but no KiCad project (XD-ADR-0135)")
    known = ", ".join(sorted(p.get("name") for p in boards.values())) or "none"
    raise NewError(f"no board def {element!r} in {cfg.repo.name}/{mj.relative_to(cfg.repo)} (board defs: {known}); add `part def <'EE-PCBA-NEW-x'> "
                   f"{element} :> <system block>, XdDomain::Pcba` to the model, `curatrix ids fix`, `curatrix gen model`")


def lower_camel(name: str) -> str:
    return name[:1].lower() + name[1:]


def views_block(cfg, qname: str, wanted: list[tuple[str, str, str]], log=print, optional: bool = False) -> str:
    """The rst that embeds the views of one def (tiacsys/xdmod#69 finding 3): for each wanted
    (kind, view name suffix, caption), the model's view of that kind with ``root`` = the def, as a
    ``sysml-view`` directive. A view the model does not have yet is a short paragraph with the
    SysML to add (a missing file would fail the strict docs build); the log says the same.
    ``optional``: a missing view is left out silently (a board without variants)."""
    from curatrix import views
    s = cfg.section("model") or {}
    mj = cfg.resolve(s.get("json", "generated/model.json"))
    # a view's root is a qualified name (views.graph finds it by exactly that; another spelling
    # fails `views build`), so the string compare finds every view that builds
    have = views.discover(modelmod.Model.load(mj)) if mj.exists() else []
    simple = qname.split("::")[-1]
    no_ck_d3 = cfg.section("views") is None
    out = []
    for kind, suffix, caption in wanted:
        hit = sorted(v.name for v in have if v.kind == kind and v.root == qname)
        if hit:
            # the caption is plain text (not rst): no backticks
            out.append(f".. sysml-view:: /views/{hit[0]}.drawio.svg\n   :caption: {caption} (view {hit[0]})\n")
            continue
        if optional:
            continue
        name = lower_camel(simple) + suffix
        snippet = f'view {name} {{ @XdView {{ kind = "{kind}"; root = "{qname}"; }} }}'
        ck = (" CK-D3 checks views only with a ``views:`` section in ``checks.yaml`` (and ``CK-D3`` in "
              "``expect:``); this repo has none yet." if no_ck_d3 else "")
        out.append(f"The model has no {kind} view of ``{simple}`` yet. Add ``{snippet}`` to the model, run "
                   f"``curatrix gen model`` and ``curatrix views build``, and replace this paragraph with "
                   f"``.. sysml-view:: /views/{name}.drawio.svg``.{ck}\n")
        log(f"  no {kind} view of {simple} in the model: add `{snippet}`, then `curatrix views build` "
            f"(the document says where it goes)")
        if no_ck_d3:
            log("  checks.yaml has no views: section: add `views: {dir: views}` and CK-D3 to expect:, so CK-D3 checks it")
    return "\n".join(out)


def _subst(text: str, values: dict[str, str]) -> str:
    for k, v in values.items():
        text = text.replace(k, v)
    return text


# sub-folder of docs/ per kind of per-deliverable document (owner decision Q8 of tiacsys/xdmod#69);
# the registry entry names it as ``doc_dir: <sub>/<id>``, the deploy path stays ``html/<id>/``
SUBFOLDERS = {"pcba-": "pcbas", "asm-": "assemblies", "fw-": "firmware", "proto-": "protos"}


def doc_folder(doc_id: str) -> str:
    """The folder of a document relative to the registry: ``pcbas/pcba-x``, else the ID."""
    sub = next((d for p, d in SUBFOLDERS.items() if doc_id.startswith(p)), None)
    return f"{sub}/{doc_id}" if sub else doc_id


def is_own(entry) -> bool:
    """A registry entry of the repo's own documents: no ``doc_dir``, or one inside the registry
    folder (``pcbas/pcba-x``); upstream documents point out of it (``../../<repo>/docs/<id>``)."""
    if not isinstance(entry, dict):
        return False
    d = str(entry.get("doc_dir") or "")
    return not d or not (d.startswith("/") or ".." in Path(d).parts)


def add_registry_entry(registry: Path, doc_id: str, title: str, project: str, doc_dir: str | None = None) -> bool:
    """Add a document entry to a zdocs registry, keeping its comments: after the repo's own
    documents (before the first ``# upstream`` comment line in ``documents:``, else at the end).
    ``doc_dir`` (relative to the registry) for a document in a sub-folder."""
    text = registry.read_text(encoding="utf-8")
    data = yaml.safe_load(text) or {}
    docs = data.get("documents") or {}
    if doc_id in docs:
        return False
    own = [d for d in docs.values() if is_own(d)]
    group = next((d.get("group") for d in own if d.get("group")), None)
    entry = [f"  {doc_id}:", f"    title: \"{title}\""] + ([f"    group: {group}"] if group else []) + \
            ([f"    doc_dir: {doc_dir}"] if doc_dir else []) + [f"    version_project: {project}", "    builders: [html]", "    needs: {source: json}", ""]
    lines = text.splitlines()
    start = next((i for i, ln in enumerate(lines) if re.match(r"^documents:\s*$", ln)), None)
    if start is None:
        raise NewError(f"{registry}: no `documents:` mapping")
    pos = next((i for i in range(start + 1, len(lines)) if re.match(r"^\s+#\s*upstream", lines[i], re.I)), None)
    if pos is None:
        pos = next((i for i in range(start + 1, len(lines)) if lines[i] and not lines[i][0].isspace()
                    and not lines[i].startswith("#")), len(lines))
        if pos == len(lines) and lines and lines[-1].strip():
            entry = [""] + entry[:-1]
    new = lines[:pos] + entry + lines[pos:]
    out = "\n".join(new) + "\n"
    if doc_id not in ((yaml.safe_load(out) or {}).get("documents") or {}):
        raise NewError(f"{registry}: could not add {doc_id} (unexpected layout); add it by hand")
    registry.write_text(out, encoding="utf-8")
    return True


def _make_project(ws, folder: Path, tmpl: Path, values: dict, name: str, kicad: bool, log) -> None:
    from curatrix import limits
    folder.mkdir(parents=True)
    for src, dst in TEMPLATE_FILES.items():
        (folder / dst.format(name=name)).write_text(_subst((tmpl / src).read_text(encoding="utf-8"), values),
                                                   encoding="utf-8")
    log(f"  wrote {ws.rel(folder)}/ ({', '.join(d.format(name=name) for d in TEMPLATE_FILES.values())})")
    if kicad:
        for argv in (["kicad-cli", "sch", "upgrade", "--force", str(folder / f"{name}.kicad_sch")],
                     ["kicad-cli", "pcb", "upgrade", "--force", str(folder / f"{name}.kicad_pcb")]):
            r = limits.run(argv, "kicad-cli", ws, capture_output=True, text=True)
            if r.returncode:
                raise NewError(f"{' '.join(argv[:3])}: exit {r.returncode} {limits.explain_rc(r.returncode)} "
                               f"{(r.stdout + r.stderr)[-500:]}")
        log("  saved by KiCad: schematic and board (kicad-cli sch|pcb upgrade --force)")


def new_pcba(ws, repo, cfg, element: str, kicad: bool = True, log=print) -> Path:
    bdef = find_board_def(cfg, element)
    name_el, bid = bdef.get("name"), element_id_of(bdef)
    name = eeprojects.kebab(name_el)
    folder = cfg.repo / "pcba" / name
    if folder.exists():
        raise NewError(f"{ws.rel(folder)} exists")
    tmpl = ws.xdmod / "templates" / "kicad-pcba"
    title = title_of(name_el)
    values = {"__NAME__": name, "__TITLE__": title, "__ID__": bid, "__ROOT_UUID__": str(uuid.uuid4()),
              "__TEXT_UUID__": str(uuid.uuid4()), "__TEXT2_UUID__": str(uuid.uuid4()),
              "__OUTLINE_UUID__": str(uuid.uuid4())}
    try:
        _make_project(ws, folder, tmpl, values, name, kicad, log)
    except BaseException:
        import shutil
        shutil.rmtree(folder, ignore_errors=True)          # no half-made project folder stays behind
        raise
    doc_id = f"pcba-{name}"
    reg = cfg.docs_registry
    if reg is not None:
        ddir = reg.parent / doc_folder(doc_id)
        ddir.mkdir(parents=True, exist_ok=True)
        rst_title = f"{title} ({doc_id})"
        dv = {**values, "__TITLE_RST__": f"{rst_title}\n{'=' * len(rst_title)}",
              "__BLOCK_DIAGRAM__": views_block(cfg, bdef["qualifiedName"], [
                  ("interconnection", "", f"The {title.lower()} and its ports")], log),
              "__VARIANTS_VIEW__": views_block(cfg, bdef["qualifiedName"], [
                  ("variants", "Variants", f"The variants of the {title.lower()} and what each serves")], log,
                  optional=True)}
        for f in ("conf.py", "index.rst"):
            (ddir / f).write_text(_subst((tmpl / "doc" / f).read_text(encoding="utf-8"), dv), encoding="utf-8")
        log(f"  wrote {ws.rel(ddir)}/ (conf.py, index.rst)")
        if add_registry_entry(reg, doc_id, title, repo.name, doc_folder(doc_id)):
            log(f"  added {doc_id} to {ws.rel(reg)}")
    else:
        log("  no docs section in checks.yaml: no board document made")
    if not eeprojects.patterns(cfg):
        log("  checks.yaml: add cad.projects: [\"pcba/*/*.kicad_pro\", \"proto/*/*.kicad_pro\"] (CK-F6, CK-F7)")
    log(f"  next: `curatrix gen cad-needs {repo.name}`, `curatrix check {repo.name} --stage local`")
    return folder
