---
name: xd-issue-ids
description: Use whenever you add a need, model element, CAD trace ID, test case, decision or check that needs an ID (<DOMAIN>-<KIND>-<NNNN>) - placeholders, curatrix ids fix / ids new, real IDs in CAD files, append-only ledgers, and retiring before deleting.
---

# Issuing and retiring IDs

Read first: `xdmod/claude/framework/id-scheme.md`, `xdmod/curatrix/README.md` ("ids.yaml (the
ledger)"). Rule 6 of the workspace `CLAUDE.md`: **never type a number yourself.**

## The ledger

- Each repo owns some kinds and lists them in its `ids.yaml`: every number ever issued, one per
  line. `KIND: []` makes the repo the owner of a kind before anything is issued.
- **Append-only.** A number in the ledger is never issued again, even after the need is deleted.
  Never edit `ids.yaml` by hand: only `curatrix ids new` / `ids fix` write it.
- IDs of kinds the repo does not own are references to upstream needs (CK-C2 ignores them).
- Format: `<DOMAIN>-<KIND>-<NNNN>` (`SYS-REQ-0012`), usages `<ID>.<n>` (D128), test results
  `TR-<test case ID>-<8 hex>` (made by tools).

## Text sources: placeholders + `ids fix`

Write a placeholder `<KIND>-NEW-<tag>` wherever the ID goes (rst, `.sysml` short names, code,
YAML, KiCad text files):

```rst
.. sys-req:: Mirror latency
   :id: SYS-REQ-NEW-latency
```

Links use the same placeholder (`:refines: SYS-NEED-NEW-teach`); the same tag becomes the same ID
in every file. Then, from the workspace (or set) root:

```sh
curatrix ids fix robarm-syseng --dry-run    # shows  SYS-REQ-NEW-latency -> SYS-REQ-0007
curatrix ids fix robarm-syseng              # writes the sources and the ledger
```

`ids fix` issues `max(ledger, IDs in the sources) + 1` per kind. Run it **before** the docs build:
a placeholder does not match the ID regex, so the strict build (CK-A6) fails, and CK-C1 fails too.
`curatrix ids check <repo>` runs CK-C1 and CK-C2 alone.

## CAD files: real IDs

- **FreeCAD:** placeholders inside `.FCStd` are refused. Ask for a real ID and set it in FreeCAD
  (property `TraceID`, group `Trace`):
  ```sh
  curatrix ids new ME-PART           # prints e.g. ME-PART-0004 and records it in robarm-me/ids.yaml
  ```
- **KiCad:** take a real ID the same way (`curatrix ids new EE-CMP`) and set the hidden field in
  KiCad, so the file stays as KiCad wrote it. `ids fix` can replace a placeholder in KiCad text
  files, but then the file was not saved by KiCad (see skill `xd-kicad-authoring`).
- `ids new KIND FILE` replaces the first placeholder of that kind in FILE; `--repo R` picks the
  ledger if several repos could own the kind.
- An ID you took with `ids new` and then did not use is still spent. That is fine; do not give it back.

## Retire, then delete

- A need that is no longer wanted gets `status: retired` (D64e, D130). Its ID stays in the ledger.
- Links to a retired need warn (CK-B3) until the baseline stage, where they fail. Move or drop
  those links in the downstream repos.
- Generated needs (model, CAD) that disappear leave a tombstone in `generated/retired-needs.json`
  (CK-B7); retire the element in the source first.
- Delete the need only in a later change, after a baseline shows nothing links to it. The number
  is never issued again.

## xdmod's own IDs

`XD-ADR`, `XD-RULE`, `XD-CHECK` are issued the same way from `xdmod/ids.yaml`
(`curatrix ids fix xdmod`). A retired check keeps its catalogue entry with `retired:`.

## Do not

- invent, guess or copy a number from another branch. Two branches can issue the same number;
  the branch merged second keeps both sides of `ids.yaml` in the rebase, puts placeholders back
  for its own new needs and runs `ids fix` again;
- reuse the number of a deleted need;
- edit `ids.yaml` to "fill a gap".
