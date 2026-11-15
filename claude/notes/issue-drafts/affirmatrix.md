# Issue drafts for tiacsys/affirmatrix

Status: **POSTED 2026-11-14** (all 9, approved by the user; some overlap the owner's unpublished roadmap, posted for comparison). Each `## A<n>` section is one issue. The line `Labels:` is applied on posting.
Sources: `claude/research/affirmatrix.md` (gaps G1–G12, questions Q1–Q4), `claude/notes/spike.md` §6 and §10.
Context in every issue: a multi-repo project (west + zdocs) where requirements, model elements, CAD parts and test results are sphinx-needs, and links are typed per need type.

---

## A1: Read several `needs.json` files, including needs imported from other documents

Posted: https://github.com/tiacsys/affirmatrix/issues/10

Labels: enhancement

**Problem**
affirmatrix reads one `requirements` export and one parent-link field. With zdocs, each document writes its own `needs.json`, and needs imported from other documents (external needs) are **not** in it. So every cross-document or cross-repo link shows as `broken`. This was verified in a test.

**Proposal**
- Accept a list of `needs.json` files, or a glob.
- Alternatively, accept a merged full-set export, and document how to produce one.
- Resolve link targets across all of them.

**Acceptance**
A link from a need in document B to a need in document A, where B imports A as external needs, is `active`, not `broken`.

---

## A2: Configurable link vocabulary and need types

Posted: https://github.com/tiacsys/affirmatrix/issues/11

Labels: enhancement

**Problem**
The vocabulary is closed. Only `refines`, `implements` (from `satisfies`) and `verifies` are checked. Other link types are ignored, for example `satisfies` from a model element, `realizes` from a CAD part, allocation and interface links. Need types are also flattened: model elements, EE components and test cases all become "Requirement".

**Proposal**
Let the project declare its link types and need types in `affirmatrix.yaml`, or read them from the sphinx-needs config (TOML). Map each link type to a drift rule, or to "not checked".

**Acceptance**
A link of a project-defined type (e.g. `realizes`) becomes `directlyOutdated` when its target's content changes. Node kinds keep their need type.

---

## A3: Choose which need fields are hashed (e.g. `status`)

Posted: https://github.com/tiacsys/affirmatrix/issues/12

Labels: enhancement

**Problem**
A need's hash covers its title, content and parent links. A change to other fields does not make links suspect. That includes rationale, verification method, values stored in fields, and **status** (e.g. a requirement set to `retired`). Verified for tags and for `status`.

**Proposal**
Add a per-type list of hashed fields in the config. The default stays as it is today.

---

## A4: `graph status` passes on vanished edges and uncommitted case drafts

Posted: https://github.com/tiacsys/affirmatrix/issues/13

Labels: bug

**Problem**
`graph status` exits 0 when edges have `vanished` and when the `case` worktree holds uncommitted affirmations. In CI, both should be visible and, by choice, fail.

**Proposal**
Add an option such as `--fail-on vanished,uncommitted`, or a non-zero exit code class for them, and show both in `--json`.

---

## A5: Inputs beyond C/Doxygen through a generic needs-based producer

Posted: https://github.com/tiacsys/affirmatrix/issues/14

Labels: enhancement

**Problem**
The only code reader is C, located through Doxygen. Projects that trace Python, devicetree, Kconfig, SysML v2 models, KiCad symbols or FreeCAD objects need their own readers.

**Proposal**
Accept node records from any producer that writes `needs.json`-like files with a **canonical content** field. The project then supplies the producers: a SysML element's text, a KiCad symbol's fields plus pins and nets, a FreeCAD object's properties and spreadsheet values. affirmatrix stays tool-agnostic.

---

## A6: Agents preparing affirmations, and the `Co-Authored-By` trailer (ADR-0009)

Posted: https://github.com/tiacsys/affirmatrix/issues/15

Labels: question

**Context**
In our project, agents analyse suspect links and prepare affirmations, but only a human's commit counts as the affirmation. Our general rule also asks that every commit an agent helped with carries a `Co-Authored-By` trailer. ADR-0009 forbids that trailer on case commits.

**Questions**
1. Is "agent proposes (runs `edge show`, writes the reason, prepares `edge affirm` on a branch), human commits" acceptable under ADR-0009?
2. How should agent help be recorded, if not with the trailer? For example, a `--role agent-reviewer`, or a field in the review event.
3. Is the authorised committer list (ADR-0009, open question 3) planned?

---

## A7: Accept `source` paths relative to the repository

Posted: https://github.com/tiacsys/affirmatrix/issues/16

Labels: bug

**Problem**
In a test, `source` had to be an absolute path. Relative paths, resolved from the repository root or the config file, would let the same `affirmatrix.yaml` work on every machine and in CI.

---

## A8: Removing nodes of deleted requirements

Posted: https://github.com/tiacsys/affirmatrix/issues/17

Labels: enhancement

**Problem**
When a requirement is deleted, its node records stay in the case. There is no verb to remove or retire a node.

**Proposal**
Add `node retire` / `node remove` with a reason. The node's links then end as `vanished` with a record of why.

---

## A9: Show the need, not the whole file, in before/after content

Posted: https://github.com/tiacsys/affirmatrix/issues/18

Labels: enhancement

**Problem**
The before-content view shows the whole source file, not just the changed need. In a large requirements document, the change is hard to find during review.

**Proposal**
Show the need's own content (title, body, hashed fields) before and after, with a diff.
