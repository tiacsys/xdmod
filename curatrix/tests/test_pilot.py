"""Pilot script and log handling without Java."""
from pathlib import Path

from curatrix import pilot


def test_script_loads_libraries_as_one_input(tmp_path):
    a, b, m = tmp_path / "A.sysml", tmp_path / "B.sysml", tmp_path / "M.sysml"
    for f in (a, b, m):
        f.write_text("package X;\n")
    s = pilot.script([m], tmp_path / "lib", [], None, [a, b])
    assert s.count("si.process(") == 2                       # one for the set, one for M
    assert f'Files.readString(Path.of("{a.resolve()}")) + "\\n" + Files.readString(Path.of("{b.resolve()}"))' in s
    assert f"FILE {pilot.LIBSET} [A.sysml, B.sysml]" in s


def test_remap_libset_lines(tmp_path):
    a, b = tmp_path / "A.sysml", tmp_path / "B.sysml"
    a.write_text("l1\nl2\nl3\n")          # lines 1-4 of the set (trailing newline + joiner)
    b.write_text("m1\nm2")                # lines 5-6
    log = "\n".join([
        f"FILE {pilot.LIBSET} [A.sysml, B.sysml]: ERRORS",
        "ERROR:x (7.sysml line : 6 column : 3)",
        "ERROR:y (7.sysml line : 2 column : 1)",
        "FILE /m.sysml: ERRORS",
        "ERROR:z (8.sysml line : 6 column : 3)",
    ])
    out = pilot.remap_libset(log, [a, b]).splitlines()
    assert out[1] == f"ERROR:x ({b.resolve()} line : 2 column : 3)"
    assert out[2] == f"ERROR:y ({a.resolve()} line : 2 column : 1)"
    assert out[4] == "ERROR:z (8.sysml line : 6 column : 3)"   # outside the set: unchanged
    assert pilot.remap_libset(log, []) == log


def test_script_one_set_and_export_errors(tmp_path):
    a, b = tmp_path / "a.sysml", tmp_path / "b.sysml"
    for f in (a, b):
        f.write_text("package X;\n")
    s = pilot.script([a, b], tmp_path / "lib", ["X", "Y"], tmp_path / "o.json", one_set=True)
    assert s.count("si.process(") == 1 and f"FILE {pilot.MODELSET} [a.sysml, b.sysml]" in s
    assert 'if (ex1.startsWith("ERROR:")) { System.out.println("EXPORT Y: " + ex1); errs++; }' in s
    log = f"FILE {pilot.MODELSET} [a.sysml, b.sysml]: ERRORS\nERROR:x (3.sysml line : 3 column : 1)"
    assert pilot.remap_libset(log, [a, b], pilot.MODELSET).splitlines()[1] == f"ERROR:x ({b.resolve()} line : 1 column : 1)"
