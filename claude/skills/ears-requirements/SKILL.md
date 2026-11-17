---
name: xd-ears-requirements
description: Use when you write or change requirements (SYS-REQ in robarm-syseng, plan task 6.3, SYSMOD step 09; also SW-REQ, EE-REQ, ME-REQ) - EARS sentence patterns, the value fields min/max/nominal/unit and what CK-E2 and CK-E3 check, and the refines links.
---

# EARS requirements with value fields

Read first: `robarm-syseng/claude/CLAUDE.md`, `xdmod/claude/framework/sysmod-work-products.md` §4,
`xdmod/claude/framework/trace-model.md`, the type `sys-req` and the requirement fields in
`xdmod/needs/needs_config.toml`, and `SYS-REQ-0001` in `robarm-syseng/docs/se-req/canary.rst`.
Review list: `xdmod/claude/checklists/requirements.md`.

## EARS patterns (field `ears`)

| `ears` | Sentence starts with | Template |
|---|---|---|
| `ubiquitous` | The / A / An / Each / Every | The `<system>` shall `<response>`. |
| `event` | When | When `<trigger>`, the `<system>` shall `<response>`. |
| `state` | While | While `<state>`, the `<system>` shall `<response>`. |
| `optional` | Where | Where `<feature is included>`, the `<system>` shall `<response>`. |
| `unwanted` | If | If `<unwanted event>`, then the `<system>` shall `<response>`. |
| `complex` | any | a combination, e.g. "While ..., when ..., the ... shall ...". |

One requirement = one sentence with one "shall". Two behaviours = two requirements.

## Value fields

| Field | Example | Rule |
|---|---|---|
| `category` | `performance` | `functional`, `performance`, `interface`, `constraint` |
| `quantity` | `latency` | what is measured |
| `unit` | `ms` | symbol (or a name the check knows) |
| `min`, `max`, `nominal` | `max: 50` | numbers only; set those the sentence states |
| `verification_method` | `test` | `test`, `analysis`, `inspection`, `demonstration` |
| `verification_scope` | `logical` | `logical` (any configuration counts) or `config` (per configuration, D104) |
| `configs`, `where` | `SYS-CFG-0002`, `SYS-FEAT-0003` | only if the requirement holds for some configurations / a feature |

The stub generator copies these fields into the SysML `requirement` stub as attributes (D83).

```rst
.. sys-req:: Mirror latency
   :id: SYS-REQ-NEW-latency
   :status: draft
   :refines: SYS-NEED-0002
   :category: performance
   :ears: event
   :quantity: latency
   :unit: ms
   :max: 50
   :verification_method: test
   :verification_scope: logical

   When the leader joint angle changes, the follower joint shall reach the new angle within 50 ms.
```

## What the checks do

- **CK-E3** (warning): for each requirement with `ears`, the sentence contains "shall" and starts
  like the pattern (table above; `complex` is not checked).
- **CK-E2** (warning until it ran on real requirements): each of `min`, `max`, `nominal` occurs in
  the sentence **as a number** (any format: `1000`, `1,000`, `1 000`, `0.5`, ranges like
  "between 0.5 and 2.5 ms" or "10-20 Hz", `a ± b`), and `unit` stands right after it, or after
  the end of its range. Digits inside IDs do not count. Known gaps: `1e3`, `.5` and
  "2 × 10^6" are not read; a space as thousands separator can glue two numbers.
- Both run on requirements of the repo itself (not imported ones), skip `retired` ones.
- Messages: `max = 20 does not appear as a number in the sentence`, `... is in the sentence, but
  not followed by its unit 'ms'`, `ears=event but the sentence does not start like that pattern`.

Warnings do not fail the check, but a reviewer reports every new one as should-fix.

## Links

- `SYS-REQ :refines: SYS-NEED` (at least one; SYSMOD's "frame"). The requirement holds the link;
  the need never lists its requirements (D5).
- Domain requirements (`SW-REQ`, `EE-REQ`, `ME-REQ`) refine a `SYS-REQ` or `SYS-IF`, or are
  `derived: true` with a `rationale`.
- Nobody links to a requirement from it: the model `satisfy`s it through the stub, a test case
  `verifies` it. CK-B1 (full stage) wants every `SYS-REQ` refined or satisfied, CK-B2 verified.

## Good requirements

- Verifiable: a number and unit, or a clear yes/no. No "fast", "user-friendly", "as needed".
- Solution-free unless it is a `constraint`.
- Interfaces and performance (latency, update rate, accuracy) get their own requirements, each
  with values (plan 6.3).
- Use the same unit symbol everywhere (`ms`, `Hz`, `deg`, `mm`).

## Steps

1. Write the requirements with placeholder IDs, then `curatrix ids fix robarm-syseng`.
2. `curatrix docs robarm-syseng`, `curatrix gen stubs robarm-syseng` (or `gen all`).
3. `curatrix check robarm-syseng --stage local`; fix every CK-E2/CK-E3 warning you introduced.
4. One SYSMOD step per PR: requirements of one area per PR, stacked if there are many.
