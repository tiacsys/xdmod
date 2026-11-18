"""KiCad projects of an EE repo (task 5.17): discovery, CK-F6 folder rule, CK-F7 1:1 with the
EE model, `curatrix new pcba`."""
import json
import shutil
import subprocess

import pytest

from curatrix import checkcfg, checks, eeprojects, model as modelmod, newpcba
from curatrix.ws import Repo, Workspace
from helpers import git_init

XDMOD = __import__("pathlib").Path(__file__).resolve().parents[2]
PROJECTS = 'cad: {projects: ["pcba/*/*.kicad_pro", "proto/*/*.kicad_pro"]}\n'


def _model(defs: dict[str, tuple[str, str]]) -> list[dict]:
    """A tiny model JSON: {name: (short ID, XdDomain super)} as part defs in package Ee."""
    data = [{"identity": {"@id": "Ee"}, "payload": {"@type": "Package", "name": "Ee", "qualifiedName": "Ee"}}]
    for sup in sorted({s for _, s in defs.values()}):
        data.append({"identity": {"@id": f"lib:{sup}"}, "payload": {
            "@type": "PartDefinition", "name": sup.split("::")[-1], "qualifiedName": sup, "isLibraryElement": True}})
    for name, (sid, sup) in defs.items():
        p = {"@type": "PartDefinition", "name": name, "qualifiedName": f"Ee::{name}",
             "ownedRelationship": [{"@id": f"Ee::{name}/sub"}]}
        if sid:
            p["declaredShortName"] = sid
        data.append({"identity": {"@id": f"Ee::{name}"}, "payload": p})
        data.append({"identity": {"@id": f"Ee::{name}/sub"}, "payload": {
            "@type": "Subclassification", "superclassifier": {"@id": f"lib:{sup}"}, "subclassifier": {"@id": f"Ee::{name}"}}})
    return data


BOARDS = {"CanaryBoard": ("EE-PCBA-0001", "XdDomain::Pcba"), "JointController": ("EE-PCBA-0002", "XdDomain::Pcba"),
          "ServoMotor": ("", "XdDomain::ExternalPart"), "Nucleo": ("EE-PCBA-0009", "XdDomain::ExternalPart")}


def _project(repo, kind, name, tid=None, extra=None):
    d = repo / kind / name
    d.mkdir(parents=True, exist_ok=True)
    tv = {"TraceID": tid} if tid else {}
    tv.update(extra or {})
    (d / f"{name}.kicad_pro").write_text(json.dumps({"text_variables": tv}))
    (d / f"{name}.kicad_sch").write_text("(kicad_sch (version 20260306))\n")
    return d


def _repo(tmp_path, yaml_text=PROJECTS + "model: {files: [model/*.sysml]}\n", defs=BOARDS):
    root = tmp_path / "ws"
    repo = git_init(root / "r")
    (repo / "checks.yaml").write_text("version: 1\n" + yaml_text)
    (repo / "generated").mkdir()
    (repo / "generated/model.json").write_text(json.dumps(_model(defs)))
    return root, repo


def _run(root, repo, cid, fn):
    (root / "out").mkdir(exist_ok=True)
    ctx = checks.Ctx(Workspace(root), Repo("r", repo, "r"), checkcfg.load(repo / "checks.yaml", root), "local",
                     False, None, root / "out")
    r = checks.Result(cid, cid, level="warning")
    getattr(checks, fn)(ctx, r)
    return r.findings


def test_kebab():
    assert eeprojects.kebab("JointController") == "joint-controller"
    assert eeprojects.kebab("CanaryBoard") == "canary-board"
    assert eeprojects.kebab("PCA9685Breakout") == "pca9685-breakout"


def test_discovery_and_root_sheets(tmp_path):
    root, repo = _repo(tmp_path)
    _project(repo, "pcba", "canary-board", "EE-PCBA-0001")
    _project(repo, "proto", "rig")
    cfg = checkcfg.load(repo / "checks.yaml", root)
    prs = eeprojects.discover(cfg)
    assert [(p.kind, p.name) for p in prs] == [("pcba", "canary-board"), ("proto", "rig")]
    assert [p.name for p in eeprojects.root_sheets(cfg)] == ["canary-board.kicad_sch", "rig.kicad_sch"]


def test_f6_folder_rule(tmp_path):
    """CK-F6 planted: two projects in one folder, a misnamed one, a folder without a project, a
    missing root sheet, a KiCad file outside the project folders, a uuid used twice. lib/ symbols are no project files."""
    root, repo = _repo(tmp_path)
    _project(repo, "pcba", "canary-board", "EE-PCBA-0001")
    assert _run(root, repo, "CK-F6", "c_ee_projects") == []
    (repo / "lib").mkdir()
    (repo / "lib/robarm.kicad_sym").write_text("(kicad_symbol_lib)")
    assert _run(root, repo, "CK-F6", "c_ee_projects") == []
    d = _project(repo, "pcba", "joint", "EE-PCBA-0002")
    (d / "other.kicad_pro").write_text("{}")
    (d / "joint.kicad_sch").unlink()
    (repo / "pcba/empty").mkdir()
    (repo / "pcba/empty/x.kicad_pcb").write_text("")
    (repo / "stray.kicad_sch").write_text("")
    (d / "joint.kicad_pcb").write_text('(kicad_pcb (property "a" "1" (uuid "u-1")) (property "b" "2" (uuid "u-1")))')
    f = _run(root, repo, "CK-F6", "c_ee_projects")
    text = "\n".join(f)
    assert "pcba/joint/: 2 projects" in text
    assert "pcba/joint/other.kicad_pro: the project file is named after its folder" in text
    assert "pcba/joint/joint.kicad_pro: its root sheet joint.kicad_sch is missing" in text
    assert "pcba/empty/: a project folder without a .kicad_pro" in text
    assert "stray.kicad_sch: a KiCad project file outside a project folder" in text
    assert "pcba/empty/x.kicad_pcb: a KiCad project file outside" in text
    assert "pcba/joint/joint.kicad_pcb: uuid used more than once: u-1" in text
    assert not any("canary-board" in x for x in f)


def test_f7_one_to_one(tmp_path):
    """CK-F7 planted: a board without a project, a project naming an external part, two projects
    for one board, a wrong folder name, an unknown ID, a link variable on the project."""
    root, repo = _repo(tmp_path)
    _project(repo, "pcba", "canary-board", "EE-PCBA-0001")
    _project(repo, "pcba", "joint-controller", "EE-PCBA-0002")
    _project(repo, "proto", "rig")                                     # proto/: not 1:1 checked yet
    assert _run(root, repo, "CK-F7", "c_ee_one_to_one") == []
    _project(repo, "pcba", "joint-controller", "EE-PCBA-0002", {"Realizes": "SYS-EL-0001"})
    _project(repo, "pcba", "jc2", "EE-PCBA-0002")
    _project(repo, "pcba", "nucleo", "EE-PCBA-0009")
    _project(repo, "pcba", "ghost", "EE-PCBA-0042")
    _project(repo, "pcba", "untraced")
    shutil.rmtree(repo / "pcba/canary-board")
    text = "\n".join(_run(root, repo, "CK-F7", "c_ee_one_to_one"))
    assert "Ee::CanaryBoard (EE-PCBA-0001): no KiCad project; create it with `curatrix new pcba CanaryBoard" in text
    assert "Ee::JointController (EE-PCBA-0002): 2 projects name it" in text
    assert "pcba/jc2/jc2.kicad_pro: the board def JointController (EE-PCBA-0002) gives the folder name pcba/joint-controller/" in text
    assert "pcba/nucleo/nucleo.kicad_pro: TraceID EE-PCBA-0009 is an external part" in text
    assert "pcba/ghost/ghost.kicad_pro: TraceID EE-PCBA-0042 names no board def" in text
    assert "pcba/untraced/untraced.kicad_pro: no TraceID" in text
    assert "joint-controller.kicad_pro: text variable Realizes on a project" in text


def test_f7_board_def_without_id(tmp_path):
    root, repo = _repo(tmp_path, defs={"Board": ("", "XdDomain::Pcba")})
    assert any("a board def (XdDomain::Pcba) without an EE-PCBA ID" in x for x in _run(root, repo, "CK-F7", "c_ee_one_to_one"))


def test_checks_are_off_without_projects(tmp_path):
    root, repo = _repo(tmp_path, yaml_text="cad: {kicad: [pcba/*/*.kicad_sch]}\n")
    cfg = checkcfg.load(repo / "checks.yaml", root)
    assert "CK-F6" not in checks.builtin_ids(cfg) and "CK-F7" not in checks.builtin_ids(cfg)
    root, repo = _repo(tmp_path / "b", yaml_text=PROJECTS)
    ids = checks.builtin_ids(checkcfg.load(repo / "checks.yaml", root))
    assert "CK-F6" in ids and "CK-F7" not in ids                      # CK-F7 needs the model


def test_registry_entry_keeps_comments(tmp_path):
    reg = tmp_path / "documents.yaml"
    reg.write_text("# head\ngroups:\n  - id: g-ee\n    title: E\ndocuments:\n  # own\n  ee-design:\n    title: \"EE\"\n"
                   "    group: g-ee\n\n  # upstream documents\n  se-req:\n    doc_dir: ../x\n")
    assert newpcba.add_registry_entry(reg, "pcba-x", "X", "r")
    t = reg.read_text()
    assert t.index("pcba-x:") < t.index("# upstream") and "# head" in t and "    group: g-ee\n    version_project: r" in t
    assert not newpcba.add_registry_entry(reg, "pcba-x", "X", "r")


def test_registry_entry_in_a_sub_folder(tmp_path):
    """A document in a sub-folder (xdmod#69 Q8) is an own document: its doc_dir stays inside docs/;
    the group comes from it, not from the upstream entries."""
    reg = tmp_path / "documents.yaml"
    reg.write_text("groups:\n  - id: g-ee\n    title: E\n  - id: g-sys\n    title: S\ndocuments:\n  pcba-a:\n"
                   "    title: A\n    group: g-ee\n    doc_dir: pcbas/pcba-a\n\n  # upstream\n  se-req:\n"
                   "    group: g-sys\n    doc_dir: ../../s/docs/se-req\n")
    assert newpcba.add_registry_entry(reg, "pcba-b", "B", "r", newpcba.doc_folder("pcba-b"))
    t = reg.read_text()
    assert "  pcba-b:\n    title: \"B\"\n    group: g-ee\n    doc_dir: pcbas/pcba-b\n" in t
    assert newpcba.doc_folder("asm-x") == "assemblies/asm-x" and newpcba.doc_folder("fw-x") == "firmware/fw-x"
    assert newpcba.doc_folder("ee-req") == "ee-req" and newpcba.doc_folder("harnesses") == "harnesses"
    assert newpcba.is_own({"doc_dir": "pcbas/pcba-a"}) and newpcba.is_own({}) and \
        not newpcba.is_own({"doc_dir": "../../s/docs/se-req"})


def test_repo_root_of_a_document_in_a_sub_folder(tmp_path):
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "xdmod_conf", XDMOD / "sphinx" / "xdmod_conf.py")
    xc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(xc)
    repo = tmp_path / "docs" / "ws" / "robarm-x"
    assert xc.repo_root(str(repo / "docs/ee-req/conf.py")) == repo.resolve()
    assert xc.repo_root(str(repo / "docs/pcbas/pcba-a/conf.py")) == repo.resolve()


def _new_pcba_repo(tmp_path):
    root, repo = _repo(tmp_path, yaml_text=PROJECTS + "model: {files: [model/*.sysml]}\ndocs: {registry: docs/documents.yaml}\n")
    (repo / "docs").mkdir()
    (repo / "docs/documents.yaml").write_text("documents:\n  ee-design:\n    title: \"EE\"\n    group: g-ee\n")
    return root, repo


def test_new_pcba(tmp_path):
    """`new pcba` without KiCad: the files, the variables, the document and its entry; CK-F6/F7 pass."""
    root, repo = _new_pcba_repo(tmp_path)
    ws, r = Workspace(root), Repo("r", repo, "r")
    cfg = checkcfg.load(repo / "checks.yaml", root)
    folder = newpcba.new_pcba(ws, r, cfg, "JointController", kicad=False, log=lambda *_: None)
    assert folder == repo / "pcba/joint-controller"
    assert sorted(x.name for x in folder.iterdir()) == [
        "fp-lib-table", "joint-controller.kicad_jobset", "joint-controller.kicad_pcb", "joint-controller.kicad_pro",
        "joint-controller.kicad_sch", "sym-lib-table"]
    pro = json.loads((folder / "joint-controller.kicad_pro").read_text())
    assert pro["text_variables"] == {"TraceID": "EE-PCBA-0002", "XD_BOARD": "joint-controller", "XD_VERSION": "unversioned"}
    assert pro["erc"]["rule_severities"] and pro["board"]["design_settings"]["rule_severities"]
    sch = (folder / "joint-controller.kicad_sch").read_text()
    root_uuid = pro["sheets"][0][0]
    assert f'(uuid "{root_uuid}")' in sch and '(rev "${XD_VERSION}")' in sch and "__" not in sch
    assert '(title "${XD_BOARD}")' in sch and "__" not in (folder / "joint-controller.kicad_pcb").read_text()
    from curatrix import cam, eeprojects
    pr = next(p for p in eeprojects.discover(cfg) if p.name == "joint-controller")
    assert cam.version_findings(pr) == []
    for t in ("sym-lib-table", "fp-lib-table"):
        uris = [u for u in (folder / t).read_text().split('(uri "')[1:]]
        assert uris and all(u.startswith("${XD_KICAD_") for u in uris)
    assert "pcba-joint-controller" in (repo / "docs/documents.yaml").read_text()
    idx = (repo / "docs/pcbas/pcba-joint-controller/index.rst").read_text()
    assert idx.startswith("Joint Controller (pcba-joint-controller)\n===") and "__" not in idx
    # no view of the board in the model yet: the document says what to add (no missing file)
    assert "The model has no interconnection view of ``JointController`` yet" in idx
    assert 'kind = "interconnection"; root = "Ee::JointController"' in idx and "\n.. sysml-view::" not in idx
    assert "views:`` section in ``checks.yaml``" in idx          # the repo has no views section: CK-D3 is off
    import yaml as _y
    ent = _y.safe_load((repo / "docs/documents.yaml").read_text())["documents"]["pcba-joint-controller"]
    assert ent["doc_dir"] == "pcbas/pcba-joint-controller"          # sub-folder (xdmod#69 Q8)
    assert '(REPO, "views/*.drawio.svg")' in (repo / "docs/pcbas/pcba-joint-controller/conf.py").read_text()
    assert _run(root, repo, "CK-F6", "c_ee_projects") == []
    f7 = _run(root, repo, "CK-F7", "c_ee_one_to_one")
    assert not any("JointController" in x for x in f7), f7
    with pytest.raises(newpcba.NewError, match="exists"):
        newpcba.new_pcba(ws, r, cfg, "JointController", kicad=False, log=lambda *_: None)
    with pytest.raises(newpcba.NewError, match="external part"):
        newpcba.new_pcba(ws, r, cfg, "ServoMotor", kicad=False, log=lambda *_: None)
    with pytest.raises(newpcba.NewError, match="no board def 'Nope'"):
        newpcba.new_pcba(ws, r, cfg, "Nope", kicad=False, log=lambda *_: None)


def test_new_pcba_embeds_the_board_views(tmp_path, monkeypatch):
    """With an interconnection and a variants view of the board in the model, the document embeds
    both (tiacsys/xdmod#69 finding 3)."""
    from curatrix import views
    root, repo = _new_pcba_repo(tmp_path)
    vd = [views.ViewDef(name=n, short_id=None, kind=k, root="Ee::JointController", layer=None, qualified_name=n)
          for n, k in (("jointController", "interconnection"), ("jointControllerVariants", "variants"),
                       ("other", "decomposition"))]
    monkeypatch.setattr(views, "discover", lambda m: vd)
    cfg = checkcfg.load(repo / "checks.yaml", root)
    newpcba.new_pcba(Workspace(root), Repo("r", repo, "r"), cfg, "JointController", kicad=False, log=lambda *_: None)
    idx = (repo / "docs/pcbas/pcba-joint-controller/index.rst").read_text()
    assert ".. sysml-view:: /views/jointController.drawio.svg" in idx
    assert "(view jointController)" in idx and "(view ``" not in idx      # the caption is not rst
    assert ".. sysml-view:: /views/jointControllerVariants.drawio.svg" in idx
    assert "other.drawio.svg" not in idx and "has no" not in idx and "__" not in idx


@pytest.mark.tools
def test_new_pcba_saved_by_kicad(tmp_path):
    """With KiCad: the schematic and the board are saved by kicad-cli, and stay loadable."""
    if shutil.which("kicad-cli") is None:
        pytest.skip("kicad-cli not installed")
    root, repo = _new_pcba_repo(tmp_path)
    ws = Workspace(root)
    folder = newpcba.new_pcba(ws, Repo("r", repo, "r"), checkcfg.load(repo / "checks.yaml", root), "CanaryBoard",
                              log=lambda *_: None)
    sch = (folder / "canary-board.kicad_sch").read_text()
    assert '(generator "eeschema")' in sch and '(rev "${XD_VERSION}")' in sch
    pcb = (folder / "canary-board.kicad_pcb").read_text()
    assert '(gr_text "${XD_VERSION}"' in pcb and '(gr_text "${XD_BOARD}"' in pcb
    assert subprocess.run(["git", "-C", str(repo), "status", "--porcelain"], capture_output=True, text=True).stdout


def test_b8_finds_projects_by_kicad_pro(tmp_path):
    """CK-B8 (variants across levels) finds the KiCad projects through cad.projects, without a
    cad.kicad glob (robarm-ee drops cad.kicad with task 5.17)."""
    from helpers import FIXTURES
    d = FIXTURES / "sysml" / "domain"
    root = tmp_path / "ws"
    repo = git_init(root / "r")
    (repo / "checks.yaml").write_text("version: 1\nmodel: {files: [model/a.sysml], upstream: up/model.json}\n"
                                      'cad: {projects: ["pcba/*/*.kicad_pro"]}\nvariants: true\n')
    for src, dst in (("ee-model.json", "generated/model.json"), ("sys-model.json", "up/model.json")):
        (repo / dst).parent.mkdir(parents=True, exist_ok=True)
        (repo / dst).write_text((d / src).read_text())
    _project(repo, "pcba", "ctrl", "EE-PCBA-0001")
    pro = repo / "pcba/ctrl/ctrl.kicad_pro"
    pro.write_text(json.dumps({"text_variables": {"TraceID": "EE-PCBA-0001"}, "schematic": {"variants": [{"name": "std"}]}}))
    f = _run(root, repo, "CK-B8", "c_domain_variants")
    assert any("CtrlFast: variant 'fast' is not in ctrl.kicad_pro" in x for x in f), f
    assert not any("CtrlStd" in x for x in f), f


def test_f7_board_variants_are_not_boards(tmp_path):
    """A board variant (`:> Board, DomainVariant`, XD-ADR-0136) and a def that specializes a board
    def are not board defs of their own: CK-F7 asks no project for them."""
    root, repo = _repo(tmp_path)
    data = _model({"CanaryBoard": ("EE-PCBA-0001", "XdDomain::Pcba"), "JointController": ("EE-PCBA-0002", "XdDomain::Pcba")})
    data.append({"identity": {"@id": "lib:XdDomain::DomainVariant"}, "payload": {
        "@type": "PartDefinition", "name": "DomainVariant", "qualifiedName": "XdDomain::DomainVariant", "isLibraryElement": True}})
    for name, supers in (("CanaryBoardAlt", ["Ee::CanaryBoard", "lib:XdDomain::DomainVariant"]),
                         ("CanaryBoardSub", ["Ee::CanaryBoard"])):
        rels = [f"Ee::{name}/sub{i}" for i in range(len(supers))]
        data.append({"identity": {"@id": f"Ee::{name}"}, "payload": {
            "@type": "PartDefinition", "name": name, "qualifiedName": f"Ee::{name}",
            "ownedRelationship": [{"@id": r} for r in rels]}})
        for r, s in zip(rels, supers):
            data.append({"identity": {"@id": r}, "payload": {"@type": "Subclassification", "superclassifier": {"@id": s},
                                                             "subclassifier": {"@id": f"Ee::{name}"}}})
    (repo / "generated/model.json").write_text(json.dumps(data))
    _project(repo, "pcba", "canary-board", "EE-PCBA-0001")
    _project(repo, "pcba", "joint-controller", "EE-PCBA-0002")
    assert _run(root, repo, "CK-F7", "c_ee_one_to_one") == []
    boards, _, _ = eeprojects.model_defs(modelmod.Model(data))
    assert sorted(boards) == ["EE-PCBA-0001", "EE-PCBA-0002"]


def test_new_pcba_failure_leaves_no_folder(tmp_path, monkeypatch):
    """If KiCad cannot save the new files, the half-made folder is removed, so a second run works."""
    from curatrix import limits
    root, repo = _new_pcba_repo(tmp_path)
    monkeypatch.setattr(limits, "run", lambda *a, **k: subprocess.CompletedProcess(a[0], 3, "", "boom"))
    with pytest.raises(newpcba.NewError, match="boom"):
        newpcba.new_pcba(Workspace(root), Repo("r", repo, "r"), checkcfg.load(repo / "checks.yaml", root),
                         "CanaryBoard", log=lambda *_: None)
    assert not (repo / "pcba/canary-board").exists()


def test_template_jobset_writes_under_build():
    """D46: the template jobset's output folder is ${XD_CAM_OUT} (the workspace env: build/cam), never
    a folder inside the repo."""
    js = json.loads((XDMOD / "templates/kicad-pcba/pcba.kicad_jobset").read_text())
    assert [o["settings"]["output_path"] for o in js["outputs"]] == ["${XD_CAM_OUT}/__NAME__"]
    assert Workspace(XDMOD.parent).env()["XD_CAM_OUT"].endswith("/build/cam")


def test_kicad_fixtures_have_unique_uuids():
    """Fixtures written by a script and re-saved by kicad-cli keep copied uuids (review of xdmod#74)."""
    from helpers import FIXTURES
    files = sorted((FIXTURES / "kicad").rglob("*.kicad_pcb")) + sorted((FIXTURES / "kicad").rglob("*.kicad_sch"))
    assert files
    assert {f.name: eeprojects.duplicate_uuids(f.read_text()) for f in files if eeprojects.duplicate_uuids(f.read_text())} == {}
