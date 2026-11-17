"""Code-derived needs: @xdid code units and test cases above ZTEST (task 5.10)."""
import json

from curatrix import code

HEADER = """/**
 * @file
 * @brief A module.
 */

#include <stdint.h>

/**
 * @brief Return the new output.
 *
 * @xdid{SW-IMPL-0001}
 * Implements SW-DD-0001.
 * Satisfies SW-REQ-0001, SW-REQ-0002.
 * Configs: SYS-CFG-0001.
 *
 * @param input The input.
 */
int32_t canary_update(int32_t input);

/** @brief Not traced. */
int other(void);

/**
 * @xdid{SW-IMPL-0002}
 * Implements SW-DD-0002.
 * Status: draft.
 */
struct thing {
	int x;
};
"""

TEST = """#include <zephyr/ztest.h>

ZTEST_SUITE(canary, NULL, NULL, NULL, NULL, NULL);

/**
 * @brief The output follows
 * the input.
 *
 * Test case: SW-TC-0001. Verifies SW-REQ-0001.
 */
ZTEST(canary, test_output_follows_input)
{
}

/* no ID here */
ZTEST(canary, test_untraced)
{
}

/** Test case: SW-TC-0002. Implements SW-DD-0001. */
ZTEST(canary, test_bad_link)
{
}
"""


def test_code_units(tmp_path):
    f = tmp_path / "a.h"
    f.write_text(HEADER)
    needs, findings = code.code_units(f, "src/a.h")
    assert findings == []
    assert sorted(needs) == ["SW-IMPL-0001", "SW-IMPL-0002"]
    n = needs["SW-IMPL-0001"]
    assert n["type"] == "sw-impl" and n["title"] == "canary_update()" and n["status"] == "valid"
    assert n["implements"] == ["SW-DD-0001"] and n["satisfies"] == ["SW-REQ-0001", "SW-REQ-0002"]
    assert n["configs"] == ["SYS-CFG-0001"] and n["source_file"] == "src/a.h"
    assert "Return the new output." in n["content"] and "int32_t canary_update(int32_t input)" in n["content"]
    assert needs["SW-IMPL-0002"]["title"] == "thing" and needs["SW-IMPL-0002"]["status"] == "draft"


def test_test_cases(tmp_path):
    d = tmp_path / "tests" / "canary"
    (d / "src").mkdir(parents=True)
    (d / "testcase.yaml").write_text("tests:\n  robarm.canary:\n    platform_allow: [native_sim]\n")
    f = d / "src" / "main.c"
    f.write_text(TEST)
    needs, findings = code.test_cases(f, "tests/canary/src/main.c")
    assert sorted(needs) == ["SW-TC-0001", "SW-TC-0002"]
    n = needs["SW-TC-0001"]
    assert n["type"] == "sw-tc" and n["title"] == "The output follows the input"
    assert n["verifies"] == ["SW-REQ-0001"]
    assert "``robarm.canary.canary.output_follows_input``" in n["content"]
    # a link the need type does not declare is a finding, and is left out
    assert len(findings) == 1 and "no link 'implements'" in findings[0]
    assert "implements" not in needs["SW-TC-0002"]


def test_gen_code_needs_through_cli(tmp_path, monkeypatch):
    from curatrix import cli
    from helpers import git_init, make_ws
    root = make_ws(tmp_path, monkeypatch)
    repo = git_init(root / "sw")
    (repo / "src").mkdir()
    (repo / "src" / "a.h").write_text(HEADER)
    (repo / "checks.yaml").write_text("version: 1\ncode: {sources: ['src/**/*.[ch]'], tests: ['tests/**/*.c']}\n")
    monkeypatch.chdir(root)
    assert cli.main(["check", "sw", "--only", "CK-D6"]) == 1             # not generated yet
    assert cli.main(["gen", "code-needs", "sw"]) == 0
    doc = json.loads((repo / "generated" / "code-needs.json").read_text())
    assert doc["project"] == "sw-code" and sorted(doc["versions"][""]["needs"]) == ["SW-IMPL-0001", "SW-IMPL-0002"]
    assert cli.main(["check", "sw", "--only", "CK-D6"]) == 0


def _units(tmp_path, text):
    f = tmp_path / "x.h"
    f.write_text(text)
    return code.code_units(f, "src/x.h")


def test_xdid_with_several_or_bad_ids_is_a_finding(tmp_path):
    needs, f = _units(tmp_path, "/** @xdid{SW-IMPL-0001, SW-IMPL-0002} */\nint a(void);\n"
                                "/** @xdid{ sw-impl-0003 } */\nint b(void);\n/** @xdid{} */\nint c(void);\n")
    assert needs == {} and len(f) == 3
    assert "exactly one ID" in f[0] and "not a valid ID" in f[1] and "exactly one ID" in f[2]


def test_titles_of_declarations(tmp_path):
    needs, f = _units(tmp_path, (
        "/** @xdid{SW-IMPL-0001} */\n#define LIMIT 10\nint other(void);\n"
        "/** @xdid{SW-IMPL-0002} */\ntypedef int (*cb_t)(int);\n"
        "/** @xdid{SW-IMPL-0003} */\n// helper (old)\nint real(void);\n"
        "/**\n * @file\n * @xdid{SW-IMPL-0004}\n */\nstruct s { int x; };\n"
        "/** @brief One line. Verifies nothing.\n * @xdid{SW-IMPL-0005}\n */\nstatic const int table[3] = {1, 2, 3};\n"
        'const char *s = "/** @xdid{SW-IMPL-0006} Implements SW-DD-0009. */";\n'))
    assert f == []
    assert {k: n["title"] for k, n in needs.items()} == {
        "SW-IMPL-0001": "LIMIT", "SW-IMPL-0002": "cb_t", "SW-IMPL-0003": "real()", "SW-IMPL-0004": "x.h",
        "SW-IMPL-0005": "table"}                                       # SW-IMPL-0006 is in a string
    assert needs["SW-IMPL-0005"]["content"].startswith("One line.\n")


def test_block_without_declaration_is_a_finding(tmp_path):
    needs, f = _units(tmp_path, "int a;\n/** @xdid{SW-IMPL-0001} */\n")
    assert needs["SW-IMPL-0001"]["title"] == "x.h" and "no declaration" in f[0]


def _tests(tmp_path, text):
    d = tmp_path / "repo" / "tests" / "t"
    (d / "src").mkdir(parents=True)
    (d / "testcase.yaml").write_text("tests:\n  a.t:\n    tags: x\n")
    f = d / "src" / "main.c"
    f.write_text(text)
    return code.test_cases(f, "tests/t/src/main.c")


def test_ztest_variants_and_comment_forms(tmp_path):
    needs, f = _tests(tmp_path, (
        "/** Test case: SW-TC-0001. */\nZTEST_F(s, test_f) {}\n"
        "/** Test case: SW-TC-0002. */\nZTEST_USER(s, test_u) {}\n"
        "/** Test case: SW-TC-0003. */\nZTEST_USER_F(s, test_uf) {}\n"
        "/** Test case: SW-TC-0004. */\nZTEST_P(s, test_p) {}\n"
        "/** Test case: SW-TC-0005. */\n// a line comment in between\nZTEST(\n\ts,\n\ttest_multi)\n{}\n"
        "/** Verifies SW-REQ-0001. Similar to SW-TC-0007. */\nZTEST(s, test_no_label) {}\n"
        "/** Test case: SW-TC-0009, SW-TC-0010. */\nZTEST(s, test_two) {}\n"
        "/** Test case: sw-tc-0011. */\nZTEST(s, test_lower) {}\n"
        "MYTEST(1)\n"))
    assert sorted(needs) == ["SW-TC-0001", "SW-TC-0002", "SW-TC-0003", "SW-TC-0004", "SW-TC-0005"]
    assert "``a.t.s.p``" in needs["SW-TC-0004"]["content"] and "``a.t.s.multi``" in needs["SW-TC-0005"]["content"]
    assert len(f) == 3
    assert "without 'Test case:'" in f[0] and "one test case ID per test" in f[1] and "not a valid test case ID" in f[2]


def test_evidence_maps_ztest_p(tmp_path):
    from curatrix import evidence
    (tmp_path / "main.c").write_text("/** Test case: SW-TC-0004. */\nZTEST_P(s, test_p) {}\n")
    assert evidence.test_case_map([tmp_path]) == {"s.p": "SW-TC-0004"}


def test_bad_testcase_yaml_is_a_finding(tmp_path):
    d = tmp_path / "repo" / "tests"
    d.mkdir(parents=True)
    (d / "testcase.yaml").write_text("tests: [unclosed\n")
    (d / "main.c").write_text("/** Test case: SW-TC-0001. */\nZTEST(s, test_a) {}\n")
    needs, f = code.test_cases(d / "main.c", "tests/main.c")
    assert "SW-TC-0001" in needs and "not valid YAML" in f[0]
