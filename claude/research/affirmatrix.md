# Research 1.2 — affirmatrix (stale and suspect links, D44)

Date: 2026-11-14. Source: https://github.com/tiacsys/affirmatrix, branch `main`, HEAD `fb3f4dc`
(shallow clone of 50 commits; the repo has 139 commits, created 2026-10-02, last push 2026-10-08,
Apache-2.0, version `0.0.1.dev0`, "pre-alpha scaffold, API not stable").

Paths below like `doc/…` or `src/…` are inside the affirmatrix repo.
Markers: **[verified]** = I ran it on this machine. **[read]** = I only read code or docs.
**[memory]** = from general knowledge, not checked here.

## Summary

- affirmatrix is much more than a suspect-link checker. It builds a "safety evidence graph"
  (requirements, C code, tests, test results), detects drift, and can seal a proof package.
  Suspect-link detection is one of its three core workflows. **[read]**
- A link target's state is a **SHA-256 content hash**. For a sphinx-needs requirement the hash
  covers only `title`, `content` and the parent links (RFC 8785 JSON). Status, tags and extra
  fields are not hashed. For C code it hashes the verbatim source byte span that Doxygen locates. **[verified]**
- An **affirmation** is a review event with role, reason, both endpoints' hashes and the git
  revision of each endpoint. Edge states are derived on every run: `pending`, `active`,
  `directlyOutdated`, `transitivelySuspect`, `doublyOutdated`, `broken`, plus "vanished". **[verified]**
- Affirmations live in a **separate "case" store**: an orphan git branch (`case`), checked out as a
  worktree. They are **not** stored on the concrete side of the link. The link itself is still
  read from the concrete need's forward field, which matches D5. **[verified]**
- Input today: sphinx-needs `needs.json` (must be built with `needs_reproducible_json = True`),
  C via Doxygen XML, Twister run bundles. No SysML, KiCad or FreeCAD readers. The node and edge
  vocabulary is closed and built in. **[verified/read]**
- CLI is CI-friendly: exit 0 / 1 / 2 (positive / negative / could not judge) and `--json`. **[verified]**
- Hands-on: the full loop works (two needs, affirm, change target → `directlyOutdated`, exit 1,
  re-affirm → `active`, remove target → `broken`). The 1519-test suite passes on Python 3.14. **[verified]**
- Biggest gaps for us: only **one** requirements export and **one** parent-link field; links to needs
  from other repos are **broken**, because `needs.json` does not contain external needs. There is
  no reader for SysML, CAD or Python code. The "human only" affirmation rule clashes with D3. **[verified/read]**
- Direct conflicts with plan.md: affirmations stored centrally (tension with D5/D36), affirmation
  must be human-only and never from CI (tension with D3), and the case lineage is a second review
  path beside PRs (affects D15/D39).

## What affirmatrix is and how it works

### Purpose and scope [read]

README: "binds requirements, code, tests, and results into a safety evidence graph:
content-anchored nodes …, human affirmations recorded against exact content states, drift detection
with derived suspicion, … a sealed, recomputable commitment" (`README.md:3-9`).
The repo dogfoods itself: its own requirements (`SEG-SYS-*`, `SEG-SREQ-*`) are written in
sphinx-needs under `doc/requirement-specification/`, with a manual in `doc/manual/` (tutorials,
ADR-0001 to ADR-0016).

Three workflows (`doc/manual/explanation/architecture/iteration-0-backlog.rst`): consistency
(`graph check`), suspect detection (`graph status`, `edge show/affirm`), proof generation (`proof …`).

### Data model [read]

- Node kinds (closed set, `src/affirmatrix/taxonomy/__init__.py:39-47`):
  `Requirement` (`contentHash`), `Implementation` (`apiHash`, `bodyHash`),
  `TestSpecification` (`specHash`, `implHash`), `TestOutcome`, `Waiver`.
  Two hashes per code node let it say *which half* moved (interface vs. body).
- Edge kinds (`taxonomy/__init__.py:49-65`): `Refines`, `Verifies`, `Implements` ("strong",
  they carry suspicion), plus evidence edges `Confirms`, `Witnesses`, `Excuses`, `Calls`.
  "No configuration redefines" the vocabulary (`doc/requirement-specification/system-requirements.rst:68`, SEG-SYS-009).
- Where edges come from: `refines` (or one configured parent field) between requirements;
  `satisfies` → `Implements`; `verifies` → `Verifies` (`content-extractor.rst`, SEG-SREQ-156/157).
  Only forward links are read; back-links are ignored (`src/affirmatrix/sources/reqs.py:9-12`, SEG-SREQ-149).

### How the target's state is stored [verified]

- Requirement hash = SHA-256 of canonical JSON `{"content", "refines": sorted parents, "title"}`
  (`src/affirmatrix/sources/reqs.py:71-106`, SEG-SREQ-147). So a change of the parent links also
  changes the child's hash.
- C code hash = SHA-256 of the verbatim byte span (`content-extractor.rst:13`, SEG-SREQ-001), span
  located by Doxygen XML (ADR-0011).
- Each hash carries an **anchor**: repository *name* (not path), file path, locator
  (`need:<ID>` for needs). Node records also carry the "extraction revision" (git SHA per repo).
- The store holds **only hashes and references, never content** (SEG-SYS-007).
- An export with a build timestamp is refused: `needs_reproducible_json = True` is required
  (SEG-SREQ-150; I hit this refusal, exit 2).
- No signatures. Who affirmed is taken from the git commit in the case history, "never verified"
  (`command-line-interface.rst`, SEG-SREQ-347; ADR-0009 open question 3).

### Suspect states [verified]

From `doc/requirement-specification/suspect-detector.rst:14-60`:

| State | Meaning |
|---|---|
| `pending` | never affirmed; does **not** fail `graph status` (SEG-SREQ-082) |
| `active` | both endpoint hashes match the last affirmation, and all edges it depends on are active |
| `directlyOutdated` | an endpoint hash changed |
| `transitivelySuspect` | own hashes match, but a strong edge it depends on is not active |
| `doublyOutdated` | both of the above |
| `broken` | an endpoint is missing from the current records (SEG-SREQ-017) |
| vanished | the case holds the edge, the current stream no longer has it; reported, does **not** fail (SEG-SREQ-137) |

Propagation goes upward: if code under `SREQ-030` changes, `Implements(code→SREQ-030)` is
directly outdated and `Refines(SREQ-030→SYS-009)` becomes transitively suspect
(`doc/manual/tutorials/detect-drift.rst`). Transitive suspicion is never affirmed. It clears by
itself once the cause is re-affirmed. Suspicion is computed on every run and never stored.

### How to affirm ("re-confirm") [verified]

```
affirmatrix edge show   --kind Refines --from SWREQ_001 --to SYS_001 [-v]
affirmatrix edge affirm --kind Refines --from SWREQ_001 --to SYS_001 --role SystemEngineer --reason "…"
git -C case add -A && git -C case commit -m "…"     # the commit IS the affirmation (ADR-0009)
```

- Selection grammar: `--kind`, `--from`, `--to`, `--below <req>` (subtree). No selector → exit 2.
  There is no "affirm everything" by default.
- `--role` and `--reason` are mandatory (the reason may be empty). An optional role list can be
  enforced (SEG-SREQ-113).
- The revision of each endpoint is discovered from git. If the anchored file is dirty, affirm is
  refused (SEG-SREQ-108; I saw exit 2).
- Only `pending`, `directlyOutdated` or `doublyOutdated` strong edges can be affirmed.
- The tool never runs `git commit`. ADR-0009 (`doc/manual/explanation/decisions/0009-store-as-repository.rst:52`)
  makes the case an orphan branch "never merged" into code. Line 124: "CI must never hold write
  access to the lineage — a headless commit would be a headless affirmation". Line 156:
  "affirmatrix must never appear as the author or committer … and must add no co-authorship trailer".

### Where the confirmation is stored, and D5/D36 [verified]

- `case/` layout (`src/affirmatrix/case/_layout.py:27-71`): `nodes/*.jsonld`, `edges/<kind>.jsonld`,
  `events/review_events.jsonld`, `proofs/`, `schema/`, `context.jsonld` (JSON-LD, schema-validated).
- The **link** comes from the concrete need (`:refines:` on SWREQ). That follows D5.
- The **confirmation state** (review event + affirmed edge hash) lives in one central case store,
  not in the concrete artifact. Doorstop puts it into the child item (see the comparison below).
  So affirmatrix does **not** follow "the more concrete side owns the link" for the affirmation
  part. The design reason is deliberate: one commit = one authorised act, and it can never mix with
  a content change (ADR-0009 "Consequences").

### Inputs and outputs [verified/read]

- Config `affirmatrix.yaml`: `case`, `repositories` (name → path), `roles`, `implementation`,
  `producer` with blocks `requirements` (`export`, `types`, `source`|`source-map`, `parent-field`,
  `repository`), `specifications` and `implementations` (`export`, `doxygen`, `types`,
  `doxygen-prefix`, `path-root`, `repository`, `need-ids`). Unknown keys are refused
  (`configuration-loader.rst`, "The names of the keys"). There is **one** `requirements` block
  (`src/affirmatrix/config/__init__.py:174`).
- Test evidence: Twister run bundles, given with `--bundle` (`outcome-extractor.rst`). This matches D8/D38.
- Outputs: text and `--json` for read-only verbs. Exit codes `0` positive, `1` negative, `2` could not
  judge (`command-line-interface.rst:717`, SEG-SREQ-096). `graph status` exits 1 on any
  outdated / suspect / broken edge (SEG-SREQ-083). Pending and vanished edges do not fail it.
- A generic producer format exists (the "would-be store": `nodes/*.toml`, `edges/*.toml`,
  `content/…`), but its README calls it scaffolding that "is deleted" once the real readers exist
  (`tests/fixtures/would_be_store/README.md`, `src/affirmatrix/sources/store.py:1-10`).

### Maturity [read/verified]

Pre-alpha, single author, very well specified (about 370 EARS-style requirements, ADRs, acceptance
tests). 12.7k lines of code and 34.7k lines of tests. `pytest`: **1519 passed in 101 s** on
Python 3.14 [verified]. It is not on PyPI. Install with `pip install -e .`. Runtime deps: `jsonschema`,
`referencing`, `pyyaml`. The history is all from Oct 2026 and grows feature by feature: provenance,
node show, extraction revisions, subtree selection. A branch `zephyr-first-proof` exists and
shows the direction (Zephyr/Twister as the first real target).

## Fit with this project's decisions

| Decision | Fit | Notes |
|---|---|---|
| D6, D25, D35 sphinx-needs + zdocs | Partial | Reads `needs.json` well. But it reads **one** export. zdocs builds one `needs.json` per document (StRS, SyRS, SW req, …). Upstream needs imported through `needs_external_needs` are **not** written to the downstream `needs.json` [verified], so a cross-document link like `EE_001 → SYS_001` shows as **broken** [verified]. We need a merged export (e.g. the manifest repo's "full set" build, D26) or multi-export support in affirmatrix. |
| D36 link-type table | Weak | Only `Refines`/`Implements`/`Verifies` carry suspicion. Only one parent field is read for requirement→requirement links. Allocation, interface (peer) links and `derives` cannot be expressed. The vocabulary is closed by design (SEG-SYS-009); the backlog says "user-definable vocabulary … later". |
| D5 concrete side owns the link | Mixed | Links: yes (forward fields only). Affirmation state: no, it sits in a central `case` branch. |
| D42 SysML requirement stubs | Indirect | Stubs are generated from `needs.json`, so the requirement side is covered. A SysML element is not a node kind. To check "SysML part satisfies REQ" we need a SysML reader (hash of the element's text span). Stubs must not be treated as nodes themselves: they are derived, and hashing them would double-count. |
| D29 trace IDs in KiCad/FreeCAD | Not covered | No reader. A KiCad symbol would have to pose as an `Implementation` (`apiHash`/`bodyHash`), which is a misfit. Byte-span hashing of `.kicad_sch` would flag layout noise. `.FCStd` is a zip, so hashing its bytes is useless. We need canonical forms (e.g. the symbol's fields plus its net connections; FreeCAD object properties plus key dimensions). |
| D39 west pins revisions | Good basis | Anchors use repository *names*. `repositories:` maps name → path, which fits a west workspace. Revisions are discovered per repo and the dirty-tree check fits "manifest pins". Open: where the case lives (manifest repo?), and how a case affirmation relates to a manifest bump. |
| D15 PR review | Friction | The affirmation is a commit on a separate orphan branch, not part of the content PR. The recorded revision is the local commit SHA. With squash merge on GitHub that SHA disappears, so "before-content" display can no longer find it. Hash comparison still works. |
| D3 agents first-class | **Conflict** | affirmatrix defines affirmation as a *human* judgement. The tool and CI must never commit it, and there must be no co-author trailer (ADR-0009:124, :156). An agent can run `edge affirm` (nothing stops it technically), but the project rules say only a human's commit makes it count. |
| D46/D47 local check + CI | Good | One command (`affirmatrix graph status`) with clear exit codes and JSON. It needs a fresh `needs.json` build and the `case` branch fetched as a worktree first. |
| 2.3 / 6.1 add, change, remove | Mostly | Add → `pending` (no failure). Change → `directlyOutdated` (fails). Remove target → `broken` (fails). Removing the link → "vanished" (reported, exit 0), cleaned up with `case remove`. Node records of removed requirements stay in the case (count stayed 3 after removal) [verified]. No check against reusing retired IDs (the repo keeps that as a manual table: `retired-identifiers.rst`). |

## Comparison

| Tool | Mechanism | Where the stamp lives | Notes |
|---|---|---|---|
| **affirmatrix** | SHA-256 over canonical content per node; review event binds both ends | central `case` orphan branch | Two-sided (source *and* target change), transitive suspicion, git identity as authority, proof packages. |
| **Doorstop** 3.2 | Each link stores the parent's fingerprint (`links: - SYS001: <stamp>`), each item has `reviewed: <stamp>` | in the **child** item's YAML (concrete side) | [verified] After I changed SYS001, `doorstop` printed `WARNING: SW: SW001: suspect link: SYS001` and `SYS001: unreviewed changes`, but exited 0. `doorstop clear SW001` wrote the new stamp into `sw/SW001.yml`. One-sided: only target changes make a link suspect. Child changes are covered by `reviewed`. |
| **sphinx-needs** 9.2.0 | No suspect-link feature found. It has *derived fields* with kinds `hash` and `fingerprint` (SHA-256 over a need's authored fields) | n/a | [verified in installed code: `sphinx_needs/derive.py:55,1362`, `FINGERPRINT_CORE` = id, type, title, status, tags, content plus project fields] This is a usable building block for a Doorstop-like scheme: a child stores `refines_fp`, and a constraint or warning compares it to the parent's `fingerprint`. |
| **StrictDoc** | No built-in suspect links that I know of [memory, not verified; a web search found nothing] | — | It has MIDs (machine IDs) and source-file relations. |
| **DOORS / Polarion / Cameo / Jama** | Tool database flags a link "suspect" when either end changes after the link was made. A user clears the flag. | tool database, on the link | [memory] Polarion: per link role, triggered by fields chosen in config. Cameo uses a stereotype with a fingerprint tag on the relationship ([docs.nomagic.com](https://docs.nomagic.com/MT/latest/magic-software-architect---magicdraw/suspect-links-303995609.html)). Jama: configurable per item type field ([jamasoftware.com](https://www.jamasoftware.com/blog/tag/compare-view/)). |

affirmatrix is closest to the commercial tools (two-sided, with an explicit clearing act) and stronger
on audit: content-bound, the commit gives identity, and anyone can recompute it. Doorstop is closest
to D5 (the stamp sits in the child file, so it is reviewed in the same PR as the content).

## Hands-on results

Scratch dir: `/tmp/claude-1000/-home-tobias-z-wrk-ws-syseng/cc4a5268-5423-4e94-be0d-4c1055bbe07f/scratchpad/research-affirmatrix`
(venv with affirmatrix -e, Sphinx 9.2.0, sphinx-needs 9.2.0, doorstop 3.2; Python 3.14.10).

1. Demo repo `demo/`: `docs/index.rst` with `SYS_001` (sys) and `SWREQ_001` (swreq, `:refines: SYS_001`),
   `needs_build_json = True`, `needs_reproducible_json = True`. Config:
   ```yaml
   case: ./case
   repositories: {demo: .}
   producer:
     repository: demo
     requirements: {export: build/needs/needs.json, types: [sys, swreq], source: docs}
   ```
2. Case: `git switch --orphan case; git commit --allow-empty …; git switch main; git worktree add case case`,
   then `affirmatrix case init` → `case sync` → `graph check` (`Requirement 2, Refines 1, pending: 1`, exit 0).
3. `graph status` → `SWREQ_001 --[Refines]--> SYS_001 (pending)`, exit 0.
4. `edge affirm … --role SystemEngineer --reason "…"` → `affirmed`. `git -C case commit`.
   `edge show` now names the commit, the committer and the date, and shows `matching` for both hashes.
5. Added `:tags: demo` to SYS_001 → still `active`, exit 0 (tags are not hashed).
6. Changed "50 ms" → "20 ms" in SYS_001, committed, rebuilt → `(directlyOutdated)`, **exit 1**.
   `edge show` → `to contentHash: 10b4…d0b9 → 7cdf…9c4c (differing)`. `edge show -v` shows the
   old content, but as the **whole file** `docs/index.rst` at the old revision, not just the need.
   `node show SYS_001` shows the canonical JSON that was hashed.
7. Uncommitted edit, then affirm → refused: "content at docs/index.rst differs from what is committed …", exit 2.
8. Re-affirmed after revert → `active`, exit 0. Note: `graph status` was green **before** I committed
   the case. It reads the working tree, so drafts count locally.
9. Added SWREQ_002 → `pending`, exit 0. Removed SYS_001 → both edges `broken`, exit 1. Affirming a broken
   edge → "an endpoint is missing", exit 1. Removed the `:refines:` lines → "vanished from the current
   stream", exit 0. `case remove --kind Refines --from SWREQ_001 --to SYS_001` removes it.
   `graph check` still counts 3 requirement nodes in the case.
10. Built `needs.json` without `needs_reproducible_json` → "carries a build timestamp ('created')", exit 2.
11. Cross-repo: in a second repo `down/`, `EE_001 :refines: SYS_001`, with SYS_001 pulled in through
    `needs_external_needs`. The downstream `needs.json` contains only `EE_001`, so affirmatrix reports
    `EE_001 --[Refines]--> SYS_001 (broken)`, exit 1.
12. `pytest` on affirmatrix: 1519 passed.
13. Doorstop comparison: see the table above.

## Recommendations

1. **Use affirmatrix for suspect detection in iteration 1, on the requirement layer first**
   (StRS → SyRS → domain requirements). It works today and the exit codes fit D46/D47.
2. **One merged export.** Let the manifest repo's full-set build (D26) write one `needs.json` that
   holds all needs, and point affirmatrix there. Alternatively, write a small pre-step that merges the
   per-document `needs.json` files. Without this, cross-repo links are `broken`.
3. **One case, in the manifest repo** (orphan `case` branch), with `repositories:` matching the west
   layout. Then a baseline (D40) = manifest tag + case commit. Write down the rule: affirm only
   revisions that are on `main` (after merge), so recorded SHAs survive squash merges.
4. **Agents (D3):** let agents run `edge show`, write the review (reason text) and run `edge affirm`
   on a branch of `case`. A human approves by merging or committing. Record the agent in `--role`
   (e.g. `agent-reviewer`), with a `roles:` list in the config. Ask the owner whether ADR-0009's
   "human only" should allow "agent proposes, human enacts". This is a decision for us, not a workaround.
5. **Link-type table (3.1):** map our link types onto Refines/Implements/Verifies for now. Mark the
   rest (allocation, interface) as "not drift-checked in iteration 1".
6. **SysML and CAD (D29, D42):** write our own producers that emit node records with a *canonical*
   content form: a SysML element's text span; KiCad symbol fields + pins/nets; FreeCAD properties and
   spreadsheet values. Today this needs either the scaffold store format or new readers inside
   affirmatrix. Prefer contributing readers upstream.
7. **CI:** run `graph status --json`. Fail on exit 1. Also fail (or warn) on "vanished" and on a dirty
   `case` worktree, because affirmatrix itself does not fail on these.
8. **Change scenario (2.3/6.1):** demo it exactly like hands-on steps 5–9. It shows all states.
9. As a fallback or for comparison: sphinx-needs 9.2 `fingerprint` derived fields could give a
   Doorstop-like, D5-conform stamp inside the child need. Worth a short spike in Phase 2.

## Gaps, risks, open questions

Findings for affirmatrix itself (not changed, no issues opened):

- G1: Only one `requirements` export and one parent field. There is no way to read several zdocs documents. [verified]
- G2: External needs are not in `needs.json`, so all cross-document links are `broken`. A merge or
  "read external needs" option is needed. [verified]
- G3: Closed vocabulary. No allocation, interface, satisfy-by-model or CAD kinds. [read]
- G4: Only C (Doxygen) code readers. No Python, devicetree, Kconfig, SysML, KiCad or FreeCAD. [read]
- G5: The requirement hash ignores extra fields (rationale, verification method, EARS parts, values
  like "50 ms" if stored in fields). A change there does not make links suspect. [verified for tags]
- G6: Before-content display shows the whole file, not the need. Hard to review in a big document. [verified]
- G7: `graph status` passes on vanished edges and on uncommitted case drafts. [verified]
- G8: Node records of removed requirements stay in the case. There is no node remove verb. [verified]
- G9: Identity is the git committer, unsigned and not verified (ADR-0009 open question 3). The
  authorised committer list is not implemented yet. [read]
- G10: The case is a separate branch, so content review (PR) and affirmation review are two acts.
  Squash merges lose the recorded revisions. [read; squash impact inferred]
- G11: Pre-alpha, single maintainer, not on PyPI, API "not stable". Hash encoding changes would make
  every edge suspect (`taxonomy/__init__.py:14-18`). Pin a commit in the west manifest. [read]
- G12: Downward impact is not transitive: a SYS change marks `Refines(SWREQ→SYS)` outdated, but not
  the code under SWREQ until SWREQ itself is edited. This is consistent, but impact analysis (1.1)
  must add the "who is below" view. [read; inferred from SEG-SREQ-011/012]

Open questions for the owner:

- Q1: Is "agent proposes, human commits" acceptable under ADR-0009? (D3)
- Q2: One case per baseline in the manifest repo, or one case per repo?
- Q3: Will multi-export input and a pluggable vocabulary come soon, or should we build producers outside?
- Q4: Should affirmation state move toward the concrete side (D5), or is the central case an accepted exception to D5/D36?

## Contradictions with plan.md

- **D3** (agents review like humans) vs. ADR-0009: the affirmation is human-only, and CI or bots must
  never commit it.
- **D5/D36** (the concrete side holds the link): affirmatrix holds the *confirmation* centrally. The
  link declaration itself still conforms.
- **D44 scope note:** plan 1.2 assumes the tool works with zdocs cross-repo needs (D35). In practice it
  needs one merged export (G1/G2).
- **D15/D39:** the affirmation is a commit on a separate orphan branch, outside the per-repo PR plus
  manifest-bump flow. The workflow must add a step for it.
