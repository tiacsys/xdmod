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
