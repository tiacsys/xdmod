"""`curatrix new asm <AssemblyDef> [--repo REPO]`: the FreeCAD documents of an assembly def of the
ME model (task 5.23; XD-ADR-0128, XD-ADR-0137).

Makes ``assemblies/<name>/`` with the top document ``<name>.FCStd`` and ``<name>-skeleton.FCStd``, both
written by FreeCAD itself (``FreeCADCmd`` runs ``xdmod/templates/freecad-asm/new-asm.py`` under the
``freecad`` limits and the workspace-local config), then the document ``docs/assemblies/asm-<name>/`` and its
entry in the docs registry (it embeds the assembly's decomposition and interconnection views, or
says which views to add). ``<name>`` is the def's name in kebab case (``CanaryAssembly`` ->
``canary-assembly``).
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from curatrix import eeprojects, meassemblies, model as modelmod
from curatrix.newpcba import NewError, _subst, add_registry_entry, doc_folder, title_of, views_block


def find_assembly(cfg, element: str) -> dict:
    """The assembly def (model element) of a def name, qualified name or ME-ASM ID in the repo's
    committed model.json."""
    s = cfg.section("model")
    if s is None:
        raise NewError(f"{cfg.repo.name} has no model section in checks.yaml; an assembly document names an "
                       f"assembly def of the ME model (XD-ADR-0128)")
    mj = cfg.resolve(s.get("json", "generated/model.json"))
    if not mj.exists():
        raise NewError(f"{cfg.repo.name}/{mj.relative_to(cfg.repo)} missing; run `curatrix gen model {cfg.repo.name}`")
    asms, _ = meassemblies.model_defs(modelmod.Model.load(mj))
    for aid, p in asms.items():
        if element in (p.get("name"), p.get("qualifiedName"), aid):
            return p
    known = ", ".join(sorted(p.get("name") for p in asms.values())) or "none"
    raise NewError(f"no assembly def {element!r} in {cfg.repo.name}/{mj.relative_to(cfg.repo)} (assembly defs: "
                   f"{known}); add `part def <'ME-ASM-NEW-x'> {element} :> <system block>, XdDomain::Assembly` to "
                   f"the model, `curatrix ids fix`, `curatrix gen model`")


def run_script(ws, script: Path, env_vars: dict[str, str], result: Path, use: str = "freecad",
               exe: str = "FreeCADCmd") -> dict:
    """Run a FreeCADCmd script under curatrix limits with the workspace config. Inputs go by
    environment variables; success comes from the result file the script writes (FreeCADCmd exits
    0 when a script raises, FreeCAD spike). ``exe="FreeCAD"`` runs the GUI binary on Qt's offscreen
    platform instead (for view-provider data such as colours); such a script ends with ``os._exit``."""
    from curatrix import limits
    result.parent.mkdir(parents=True, exist_ok=True)
    result.unlink(missing_ok=True)
    env = ws.run_env({"QT_QPA_PLATFORM": "offscreen", **env_vars, "XD_RESULT": str(result)})
    r = limits.run([exe, str(script)], use, ws, capture_output=True, text=True, env=env)
    tail = (r.stdout + r.stderr)[-800:]
    if not result.is_file():
        raise NewError(f"{exe} {script.name}: no result file (exit {r.returncode} "
                       f"{limits.explain_rc(r.returncode)}): {tail}")
    out = json.loads(result.read_text())
    if not out.get("ok"):
        raise NewError(f"{exe} {script.name} failed: {out.get('error') or out}")
    return out


def new_asm(ws, repo, cfg, element: str, freecad: bool = True, log=print) -> Path:
    adef = find_assembly(cfg, element)
    name_el, aid = adef.get("name"), adef.get("declaredShortName") or adef.get("shortName") or ""
    name = eeprojects.kebab(name_el)
    folder = cfg.repo / "assemblies" / name
    if folder.exists():
        raise NewError(f"{ws.rel(folder)} exists")
    tmpl = ws.xdmod / "templates" / "freecad-asm"
    title = title_of(name_el)
    values = {"__NAME__": name, "__TITLE__": title, "__ID__": aid}
    folder.mkdir(parents=True)
    try:
        if freecad:
            out = run_script(ws, tmpl / "new-asm.py",
                             {"XD_ASM_DIR": str(folder.resolve()), "XD_ASM_NAME": name, "XD_ASM_ID": aid,
                              "XD_ASM_TITLE": title},
                             ws.build(cfg.area) / "new-asm" / f"{name}.result.json")
            log(f"  FreeCAD wrote {ws.rel(folder)}/ ({', '.join(out.get('files') or [])})")
            for bak in folder.glob("*.FCBak"):
                bak.unlink()
    except BaseException:
        shutil.rmtree(folder, ignore_errors=True)          # no half-made assembly folder stays behind
        raise
    doc_id = f"asm-{name}"
    reg = cfg.docs_registry
    if reg is not None:
        ddir = reg.parent / doc_folder(doc_id)
        ddir.mkdir(parents=True, exist_ok=True)
        rst_title = f"{title} ({doc_id})"
        dv = {**values, "__TITLE_RST__": f"{rst_title}\n{'=' * len(rst_title)}",
              "__BLOCK_DIAGRAMS__": views_block(cfg, adef["qualifiedName"], [
                  ("decomposition", "Parts", f"Parts of the {title.lower()}"),
                  ("interconnection", "", f"The {title.lower()} and its ports")], log)}
        for f in ("conf.py", "index.rst"):
            (ddir / f).write_text(_subst((tmpl / "doc" / f).read_text(encoding="utf-8"), dv), encoding="utf-8")
        log(f"  wrote {ws.rel(ddir)}/ (conf.py, index.rst)")
        if add_registry_entry(reg, doc_id, title, repo.name, doc_folder(doc_id)):
            log(f"  added {doc_id} to {ws.rel(reg)}")
    else:
        log("  no docs section in checks.yaml: no assembly document made")
    log(f"  next: link the parts in FreeCAD (one link per usage in the model, CK-F15), then "
        f"`curatrix gen all {repo.name}`, `curatrix check {repo.name} --stage local`")
    return folder
