# Issue drafts for tiacsys/zdocs

Status: **POSTED 2026-11-14** (all 10, approved by the user). Each `## Z<n>` section is one issue. The line `Labels:` is applied on posting.
Sources: `claude/research/zdocs.md` (findings 1–12), `claude/notes/spike.md` §5 and §10.
Context in every issue: a multi-repo workspace (west) where downstream repos build their upstream documents locally (D35).

---

## Z1: `version_project` is ignored for Sphinx documents

Posted: https://github.com/tiacsys/zdocs/issues/25

Labels: bug

**Problem**
For Sphinx documents, `zdocs_conf.py` resolves the version with `docrefs.resolve_version(scope=version_scope, repo_root=project_base)`. `version_project` from the registry is never passed. Doxygen documents honour `version_project`, so the two toolchains can show different versions for the same repository.

This matters when a document is built from another west project (for example, a downstream repo builds an upstream repo's documents locally through `doc_dir`). The document then shows the **consuming** repo's version, not the version of the repo it comes from.

**Also seen**
- The `version_project` result keeps the tag namespace (e.g. `sysreq/v1.0`). `version_scope` strips it.
- `version_scope` of a document built from another repo describes the consumer's repo.

**Proposal**
Pass `version_project` through for Sphinx documents too. Better still, resolve a per-document "repo root", either from the git root of `doc_dir` or from the west project. That fixes both points above.

**Acceptance**
- A Sphinx document with `version_project: <west project>` shows that project's `git describe`, with the namespace stripped.
- Sphinx and Doxygen show the same version for the same repository.

---

## Z2: Per-document needs imports instead of all-to-all

Posted: https://github.com/tiacsys/zdocs/issues/26

Labels: enhancement

**Problem**
Needs import is all-to-all among the documents of a registry. A downstream registry that builds upstream documents locally has to list **every indirect upstream document** by hand. Otherwise those upstream documents end up with dangling links. Every needs warning is also repeated once per importing document.

**Proposal**
Add an optional per-document `imports:` list, naming the documents whose needs it imports. Optionally, resolve indirect imports automatically, from the upstream registry or a transitive closure.

**Acceptance**
- A document imports needs only from the documents it lists.
- An upstream document's own imports are resolved without being re-listed downstream.

---

## Z3: Placeholder for west project paths in `doc_dir`

Posted: https://github.com/tiacsys/zdocs/issues/27

Labels: enhancement

**Problem**
To build an upstream document from another west project, `doc_dir` must hold a relative path such as `../../syseng/docs/<id>`. That path breaks when the west layout changes.

Also, the default `doc_dir` (the caller's directory) and a relative `doc_dir` (relative to the registry directory) use different bases.

**Proposal**
- Support a placeholder such as `{west:robarm-syseng}/docs/se-req` that is resolved through `west list`.
- Use one base for relative paths.

---

## Z4: "Import-only" document kind

Posted: https://github.com/tiacsys/zdocs/issues/28

Labels: enhancement

**Problem**
To link to an upstream document's needs, a downstream set must fully render that document as HTML just to get its `needs.json`. That costs build time and repeats the upstream document's warnings.

**Proposal**
Add a document kind (or flag) that runs only what is needed to produce `needs.json` and `objects.inv`, for example stage 1 only, and does not deploy HTML. A variant could read a published `needs.json` from a pinned release.

---

## Z5: A documented strict mode

Posted: https://github.com/tiacsys/zdocs/issues/29

Labels: enhancement

**Problem**
By default, dangling links and sphinx-needs schema violations do not fail the build, and `doccheck` passes. To get a strict build we pass `-DZDOCS_SPHINXOPTS_EXTRA="-W;--keep-going"`.

In strict mode, ninja then stops at the **first** failing document. With a dangling link imported from upstream, that is often an innocent upstream document, so the real culprit never reports.

**Proposal**
- A documented strict switch, e.g. `ZDOCS_STRICT=ON`. It turns warnings into errors and makes the build keep going (`-k 0`), so every document reports.
- Optionally, `doccheck` reads `schema_violations.json` and the needs warnings.

**Acceptance**
A wrong-direction link (schema violation) and a dangling link both fail the build, and every affected document is named in the output.

---

## Z6: `needflow` warns in the stage-1 `xref` builder and fails strict builds

Posted: https://github.com/tiacsys/zdocs/issues/30

Labels: bug

**Problem**
In strict builds, `needflow` warns "only supported for HTML" in zdocs' stage-1 `xref` builder, and `-W` turns that warning into an error. The workaround is to wrap every `needflow` in `.. only:: html`.

**Proposal**
Skip or silence HTML-only directives in the stage-1 builder, or document the `only:: html` pattern.

---

## Z7: Extra and generated input files per document

Posted: https://github.com/tiacsys/zdocs/issues/31

Labels: enhancement

**Problem**
Some documents need input files from outside their folder, for example generated needs files (from a model or CAD extractor) used with `needimport`. zdocs copies only the document folder into the source tree, so absolute paths in `needimport` fail (`relfn2path`). Today each document adds files through `external_content_contents` in its `conf.py`.

When a downstream set builds an upstream document, the **generated inputs** of that upstream document must also exist downstream.

**Proposal**
- A registry key for extra input files per document, e.g. `inputs:`.
- A variable for "generated inputs of project X".
- Document the `needimport` pattern for copied source trees.

---

## Z8: README build recipe fails `doc-check`; `ZEPHYR_BASE` not mentioned

Posted: https://github.com/tiacsys/zdocs/issues/32

Labels: documentation

**Problem**
- The README points to `doc/requirements.txt`. With the current unpinned Pygments (2.21), `doc-check` fails. Only `requirements-ci.txt` works. `HREF_RE` should also skip code blocks.
- The README's `cmake -S doc -B <build> -DEXTRA_ZEPHYR_MODULES=$PWD` does not mention that `ZEPHYR_BASE` (or `west zephyr-export`) is needed. The `..` hint in `find_package(Zephyr …)` did not find a sibling `zephyr/`.
- `ZDOCS_NEEDS_CONFIG` is missing from the consumer block comment in `cmake/zdocs.cmake`.

**Proposal**
Fix the README recipe and the comment. Also, a minimal non-SW consumer only needs a small Zephyr subset (`cmake share scripts modules doc/_extensions VERSION`, about 13 MB). Documenting that would help repos that contain no firmware.

---

## Z9: Hosting several versions of a document set

Posted: https://github.com/tiacsys/zdocs/issues/33

Labels: enhancement

**Problem**
zdocs builds one version of a set. Publishing `latest` plus one folder per release (e.g. on GitHub Pages) needs a version switcher and a versions list.

**Proposal**
Follow the pattern used by bridle's documentation:
- one folder per version
- a `versions.json` at the root
- a small version-switcher script

zdocs' relative links make this work across a whole set. A CMake or CLI step could write or merge `versions.json` and add the switcher to every document.

---

## Z10: Move the sphinx-needs pin to 9.2; small consistency checks

Posted: https://github.com/tiacsys/zdocs/issues/34

Labels: enhancement

**Notes**
- A spike ran zdocs with **sphinx-needs 9.2.0** (pin is 8.3.0) without problems. 9.2 brings schema rules per need type and per link type, `fields.status` enums (`needs_statuses` is deprecated), and hash/fingerprint fields.
- Not validated today: unique `prefix` values, and group ids that clash with document ids. Both are documented as known.

**Proposal**
Move the pin to 9.2.x, after checking the test suite. Add the two validations at configure time.
