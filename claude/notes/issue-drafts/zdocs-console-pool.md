# Issue draft for tiacsys/zdocs: Sphinx runs are serialised through Ninja's console pool

Status: **DRAFT, not posted.** Posting on zdocs needs the owner's approval of this text (D124).
Source: the author-loop measurement of task 5.31 (`claude/notes/author-loop.md`, "Where the time
goes", item 4), zdocs at c66f436.

---

## Sphinx stages run one at a time: `USES_TERMINAL` puts them in Ninja's console pool

Labels: enhancement, performance

**Problem**
Every Sphinx target that zdocs creates is declared with `USES_TERMINAL`:

- the stage-1 cross-reference index, `add_custom_target(${doc_name}-index ... USES_TERMINAL)` in
  `cmake/sphinx.cmake` (around line 267);
- the stage-2 builder runs (`html`, ...), `cmake/sphinx.cmake` (around line 404);
- `doc-check` and the `all-docs` post-build doccheck in `cmake/common.cmake` (lines 205 and 212).

With the Ninja generator, `USES_TERMINAL` assigns the command to the `console` pool, which has depth
1. So Ninja never runs two of these commands at the same time, even when the dependency graph
allows it: the stage-1 indexes of independent documents, and the stage-2 builds of documents whose
indexes are done, all run one after another. Sphinx itself uses one core per run.

**Measured** (a downstream workspace with 28 Sphinx documents and Doxygen in one registry, 8 cores /
16 threads at 1.7 GHz): a full build takes about 70 s, of which Sphinx is 66 s of serial runs; 15 of
16 hardware threads stay idle. A small document costs about 2 x 1 s (stage 1 and stage 2) whatever
its size, so the build time grows linearly with the number of documents.

**Proposal**
- Drop `USES_TERMINAL` from the Sphinx stage targets, or make it an option
  (`ZDOCS_SPHINX_USES_TERMINAL`, default off), and put them into a `JOB_POOL` of their own
  (`set_property(GLOBAL APPEND PROPERTY JOB_POOLS zdocs_sphinx=<n>)`, `JOB_POOL zdocs_sphinx` on the
  targets; `<n>` from a cache variable, default the number of cores, so memory stays bounded).
- Keep `doc-check` and the post-build doccheck in the console pool (they run once, at the end).
- Sphinx output then interleaves. Each run already writes its warnings to its own `-w` log file
  (`xref.log`, `<builder>.log`), so nothing is lost; the console can show one line per finished
  target.

**Acceptance**
- With Ninja, the stage-1 indexes of documents that do not depend on each other run in parallel, and
  so do the stage-2 builds whose inputs are ready.
- A full build of a registry with many small documents gets faster roughly with the pool size; the
  strict mode and the doccheck results are unchanged.
- The pool size can be limited (machines with little memory, CI).

**Context**
A multi-repo workspace (west) where downstream repos build their upstream documents locally; the
manifest repo builds the full set. Today this is not a blocker (70 s for the full set), but it is
the largest avoidable item of the docs build and grows with every document.
