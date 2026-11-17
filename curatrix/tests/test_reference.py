"""The check catalogue (curatrix/data/checks.yaml) and the reference directives of xdmod_sphinx
(sphinx/xdmod_sphinx/reference.py): XD-CHECK needs, generated tables, the CLI page (D121)."""
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from helpers import FIXTURES

XDMOD = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(XDMOD / "sphinx"))
from xdmod_sphinx import reference  # noqa: E402

from curatrix import checks, ids  # noqa: E402

RULES_DIR = XDMOD / "docs" / "xdmod-manual" / "explanation" / "rules"


def catalogue():
    return yaml.safe_load((XDMOD / "curatrix" / "src" / "curatrix" / "data" / "checks.yaml").read_text())["checks"]


def test_catalogue_matches_builtin_checks():
    cat = catalogue()
    builtin = [b[0] for b in checks.BUILTIN]
    assert sorted(k for k, c in cat.items() if not c.get("retired")) == sorted(builtin)
    needs = [c["need"] for c in cat.values()]
    assert len(set(needs)) == len(needs)
    assert all(re.fullmatch(r"XD-CHECK-\d{4}", n) for n in needs)
    assert all(c["enforces"] and c["description"] for c in cat.values())


def test_catalogue_ids_are_in_the_ledger():
    ledger = ids.Ledger.load(XDMOD / "ids.yaml")
    for c in catalogue().values():
        n = int(c["need"].rsplit("-", 1)[1])
        assert n in ledger.kinds["XD-CHECK"], c["need"]


def test_enforced_rules_exist():
    if not RULES_DIR.is_dir():
        pytest.skip("no rules pages")
    defined = set(re.findall(r":id: (XD-RULE-\d{4})", "".join(p.read_text() for p in RULES_DIR.glob("*.rst"))))
    for cid, c in catalogue().items():
        assert set(c["enforces"]) <= defined, cid


def test_tables_from_needs_config():
    cfg = reference.needs_config()
    types = reference.need_types_rows(cfg)
    assert len(types) == len(cfg["types"])
    assert any("``sys-req``" in r[0] for r in types)
    links = reference.link_rows(cfg)
    assert ["``enforces``", "``xd-check``", "``xd-rule``", "1"] == links[[r[0:2] for r in links].index(["``enforces``", "``xd-check``"])][:4]
    fields = {r[0]: r for r in reference.field_rows(cfg)}
    assert "``draft``" in fields["``status``"][1]
    kinds = {r[0]: r for r in reference.id_kind_rows(cfg)}
    assert kinds["``SYS-VIEW``"][1].startswith("(reserved")
    assert kinds["``XD-CHECK``"][2] == "``xd-check``"


def test_check_lines_and_cli():
    lines = "\n".join(reference.check_need_lines())
    assert lines.count(".. xd-check::") == len(checks.BUILTIN) + lines.count(":status: retired")
    assert ":check_id: CK-A6" in lines
    cli = "\n".join(reference.cli_lines())
    assert "curatrix check" in cli and ".. _cli-ids:" in cli and "hook" not in re.findall(r"_cli-(\w+)", cli)


def test_list_table_escapes_cells():
    out = reference.list_table(["a"], [["x|y*z"]])
    assert out[0] == ".. list-table::" and "     - " not in out[-2]
    assert reference.esc("x|y*z") == "x\\|y\\*z"


@pytest.mark.sphinx
def test_directives_in_strict_build(tmp_path):
    src = tmp_path / "src"
    shutil.copytree(FIXTURES / "sphinxdoc", src)
    rules = sorted({r for c in catalogue().values() for r in c["enforces"]})
    rst = ["Reference test", "==============", "", ".. xd-adr:: A decision", "   :id: XD-ADR-0001", "   :status: valid", ""]
    for r in rules:
        rst += [f".. xd-rule:: Rule {r}", f"   :id: {r}", "   :status: valid", "   :decided_by: XD-ADR-0001", ""]
    for d in ("xd-need-types", "xd-link-types", "xd-need-fields", "xd-id-kinds", "xd-check-table", "xd-check-needs"):
        rst += [d.title(), "-" * len(d), "", f".. {d}::", ""]
    rst += ["CLI", "---", "", ".. xd-cli::", ""]
    (src / "index.rst").write_text("\n".join(rst))
    out = tmp_path / "out"
    r = subprocess.run([sys.executable, "-m", "sphinx", "-W", "--keep-going", "-q", "-b", "html", str(src), str(out)],
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr
    import json
    d = json.loads((out / "needs.json").read_text())
    needs = d["versions"][d["current_version"]]["needs"]
    xc = [n for n in needs.values() if n["type"] == "xd-check" and n["status"] == "valid"]
    assert len(xc) == len(checks.BUILTIN)
    retired = {n["check_id"] for n in needs.values() if n["type"] == "xd-check" and n["status"] == "retired"}
    assert retired == {k for k, c in catalogue().items() if c.get("retired")}
    a6 = next(n for n in xc if n["check_id"] == "CK-A6")
    assert a6["enforces"] and all(e in needs for e in a6["enforces"])
    html = (out / "index.html").read_text()
    assert "curatrix check" in html and "sys-req" in html
