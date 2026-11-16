# SYSMOD work products and their formats (task 3.3)

Status: **AGREED 2026-11-14** (review answers → D81–D85). Built on D1, D6, D9, D37, D42, D45, D64b, D65, D73, D78 (see `../decisions.md`),
`../research/sysml-sysmod.md` §6–7, the spike, and `trace-model.md` / `id-scheme.md`.
SYSMOD source: https://mbse4u.com/sysmod/ and the library `mbse4u/sysmod-sysmlv2` (Apache-2.0).

## 1. Principles

1. **Follow SYSMOD's order and names.** We keep its steps and work products, so that the SYSMOD website and examples apply directly.
2. **Text that people review lives in sphinx-needs.** That means needs, requirements and test specs (D6). **Structure and behaviour live in SysML** (`.sysml`): context, use cases, architecture, allocations, variants.
3. **The two worlds meet through generated stubs.** Needs become `concern` stubs and requirements become `requirement` stubs (D42, D64b). Model elements come back to sphinx-needs through the model extractor. Both outputs are generated, committed and checked (spike lesson 2).
4. **Use SYSMOD's chain of contexts.** Each context specialises the one before it (idea → specification → logical → product), so later contexts inherit actors and ports.
5. **Variants follow VAMOS (Weilkiens), in SysML v2 through PLEML** (D102, `variants.md`). SYSMOD v5 has no variant concept.
6. **The SYSMOD library is a pinned dependency.** It is not copied into our repos.

## 2. Work products

Columns: SYSMOD step, its work product, where it is authored, its need type and ID kind (`trace-model.md`), and the document it appears in (D21/D27).

| # | SYSMOD step / work product | Authored in | Need type (ID kind) | Document | Iteration 1 |
|---|---|---|---|---|---|
| 01 | Project (owner, purpose, process) | `.sysml` (`#project`), short | — | Stakeholder & system requirements spec, intro | yes, minimal |
| 02 | Brownfield architecture | — | — | — | **skipped** (greenfield) |
| 03 | Problem statement | rst, one need with `category: problem`; `concern` stub generated (D81) | `SYS-NEED` | Stakeholder & system requirements spec | yes |
| 04 | Stakeholders | rst (`SYS-STH`, with SYSMOD's fields: categories, risk, effort); `part` stubs generated | `SYS-STH` | Stakeholder & system requirements spec | yes |
| 05 | Stakeholder needs | rst; `concern` stubs generated | `SYS-NEED` | Stakeholder & system requirements spec | yes |
| 06 | System idea and system objectives | idea: `.sysml` (`systemIdeaContext`); objectives: rst, needs with `category: objective` (D82) | `SYS-NEED` | Stakeholder & system requirements spec | yes |
| 07 | System context (actors, system ports, interfaces) | `.sysml` (`specificationContext`) | `SYS-EL` (actors, ports), `SYS-IF` (interfaces) | System architecture | yes |
| 08 | Use cases (and flows) | `.sysml` (`use case … : SystemUseCase`) | `SYS-UC` | Stakeholder & system requirements spec | yes (mirror, store pose, recall pose, …) |
| 09 | System requirements | rst, EARS (D45), fields per §4; `requirement` stubs generated | `SYS-REQ` | Stakeholder & system requirements spec | yes |
| 10a | Functional architecture | `.sysml` (`functionalContext`): main functions such as sense pose, transfer pose, actuate, store pose, recall pose (D85) | `SYS-EL` with `layer: functional` | System architecture | yes, short |
| 10b | Logical architecture | `.sysml` (`logicalContext`), `allocate functional2logical` | `SYS-EL` with `layer: logical` | System architecture | yes |
| 10c | Product architecture (150 %, with variation points) + allocation | `.sysml` (`productContext`), `allocate logical2product` | `SYS-EL` with `layer: product` and `configs`, links `realizes`, `satisfies` | System architecture | yes |
| 10d | **Features and configurations** (VAMOS/PLEML, D102) | `.sysml`: feature model (`features.sysml`), one product model per configuration (`configs.sysml`) | `SYS-FEAT`, `SYS-CFG`; product `SYS-EL` with `configs` | System architecture; one page per configuration (D106) | yes (vertical bar: prototype configuration) |
| 11 | Verification and validation | rst test specs in robarm-integration (D73); SysML `verificationContext` later | `INT-STC`, `INT-ITC` | System & integration test spec | yes, rst only |

**Links between these products** follow the link table in `trace-model.md`. Some examples:
- `SYS-REQ` refines `SYS-NEED` (SYSMOD's `frame`, kept in sphinx-needs).
- `SYS-UC` addresses `SYS-NEED`.
- A product `SYS-EL` satisfies `SYS-REQ` (SysML `satisfy` on the stub) and realizes a logical `SYS-EL` (from `allocate`).

## 3. Files in robarm-syseng (input for task 3.12)

```
robarm-syseng/
  model/                       SysML sources (authored)
    project.sysml              01
    context.sysml              06, 07: idea + specification context, actors, ports, interfaces
    usecases.sysml             08
    functional.sysml           10a
    logical.sysml              10b
    product.sysml              10c: product context + allocations
    features.sysml             10d: feature model (PLEML)
    configs.sysml              10d: configurations, one product model each
    views.sysml                view definitions (D94)
    generated/                 stubs from needs (committed, checked): needs.sysml (concern, requirement, stakeholder stubs)
  docs/
    se-req/                    stakeholder & system requirements spec: 01, 03, 04, 05, 06, 08 (generated), 09
    se-arch/                   system architecture: 07, 10 (from the model) + views
  generated/                   model-needs.json, model.json (Pilot export), interfaces.json (committed, checked)
  views/                       *.drawio.svg (committed, checked for content, D64a, D96)
  ids.yaml                     ID ledger (D78)
  claude/                      agent material (D69)
  requirements.txt, tools.yaml
```

The SYSMOD library (`mbse4u/sysmod-sysmlv2`) and **PLEML** (`MBSE4U/PLEML`, D102) are **west projects** at pinned commits (D84). The Pilot loads it from its west path. Sysand stays optional.

## 4. System requirement fields

SYSMOD's requirement boilerplates (`MaxValue`, `RangeValue`, …) give requirements machine-readable values. We keep the EARS sentence for people, and add fields that tools can read:

| Field | Example | Use |
|---|---|---|
| `ears` | `ubiquitous`, `event`, `state`, `optional`, `unwanted` | The EARS pattern, checked against the sentence |
| `quantity`, `unit`, `min`, `max`, `nominal` | `latency`, `ms`, —, `50`, — | Values that model attributes and tests can be checked against |
| `verification_method` | `test` | From `trace-model.md` §5 |
| `category` | `functional`, `performance`, `interface`, `constraint` | Grouping in the spec |

The `requirement` stub carries the values as attributes, so a model constraint or a test can read them (D83). A check compares the fields with the EARS sentence, e.g. that the number and unit in the text match `max` and `unit`.

## 5. How SYSMOD steps map to the Phase 6 tasks

| Phase 6 task | SYSMOD steps |
|---|---|
| 6.1 Problem statement, stakeholders, system context | 01, 03, 04, 06, 07 |
| 6.2 Stakeholder needs and use cases | 05, 08 |
| 6.3 System requirements | 09 |
| 6.4 Functional, logical and product architecture, PCBA trade study | 10a, 10b, 10c |
| 6.5 Prototype and product variants | 10d |
| 6.6 Generated views | views over 07–10 |
| 6.12 Verification | 11 |

## 6. Agent support (input for task 3.11)

SYSMOD4AI attaches prompts to each step as metadata (`create_prompt`, `validation_prompt`). We can write one skill per SYSMOD step, kept in `xdmod/claude/skills/` (D69). Each skill would say what to read, what to produce, and which checks must pass.

## 7. Answered review questions (2026-11-14)

1. **Problem statement:** a `SYS-NEED` with `category: problem`, which other needs and objectives link to (D81).
2. **System objectives:** `SYS-NEED` with `category: objective` (D82).
3. **Requirement values:** fields next to the EARS text, copied into the stubs as attributes, and checked against the sentence (D83).
4. **SYSMOD library:** a west project at a pinned commit (D84).
5. **Functional architecture:** a short functional model in iteration 1, allocated to the logical architecture (D85).
