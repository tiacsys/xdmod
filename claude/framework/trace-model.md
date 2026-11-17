# Trace model and link-type table (task 3.1)

Status: **AGREED 2026-11-14** (answers D73–D80; later changes D81–D85, D102–D107, D120–D121, Phase 3 review fixes). Built on D5, D6, D29, D36, D37, D42, D45, D57, D64 (see `../decisions.md`),
the spike (`../notes/spike.md`), `../research/traceability.md`, and the `safety` repo's `needs_config.toml`.
IDs follow the scheme in `id-scheme.md` (task 3.2).

## 1. Principles

1. **The more concrete side holds the link** (D5). In the V-model, links point right to left and from concrete to abstract.
   Backlinks ("refined by", "verified by") are only ever computed.
2. **Every link type is declared only on the need type that owns it** (D36, D64h). There is no global link table.
   A link written on the wrong side is a build error, and so is a link to an unknown ID or a wrong target type. The spike proved all three.
3. **Interfaces between peer domains live in syseng** as interface needs (`SYS-IF`). Both domains link to them; neither domain links to the other (D36). Two exceptions (Phase 5): **SW reads the board pin maps from the EE model** and may link to `EE-PCBA` / `EE-PORT`, EE never links to SW (XD-ADR-0131); **ME writes board geometry into EE's KiCad project**, only inside a co-design change and without any trace link (XD-ADR-0134).
4. **Allocation is stored on the concrete side.** A product-layer element `realizes` the logical element it was allocated from (D36, D102).
5. **Variants follow VAMOS through PLEML** (D102, `variants.md`). The core is the functional and logical architecture. Variants live in the 150 % product architecture. Elements carry `configs`, and requirements carry `where` (D103).
6. **Generated needs** (from SysML, KiCad, FreeCAD, code and test results) follow the same rules as authored needs.
   Their links come from the source files: SysML `satisfy`, KiCad fields, FreeCAD properties, Doxygen `\satisfies`, and ZTEST `\verifies`.
7. **One shared module** in xdmod defines all need types and link types (`needs_config.toml` plus schema rules). Every repo uses it, and a table document is generated from it.
8. **Domain repos refine the system model in their own `model/` by specialization** (XD-ADR-0130). The domain model owns the IDs of boards, assemblies, ports and harnesses; CAD files carry them only as references (XD-ADR-0128). See §2a.

## 2. Need types per domain

Columns: the need type, its ID kind (`id-scheme.md`), its home repo, whether it is authored or generated (and from what), and which document it appears in.

### Systems engineering (robarm-syseng)

| Need type | ID kind | Authored / generated | Document (D21, D27) |
|---|---|---|---|
| Stakeholder | `SYS-STH` | authored (rst) | Stakeholder & system requirements spec |
| Stakeholder need | `SYS-NEED` | authored (rst); `concern` stub in SysML (D42, D64b) | Stakeholder & system requirements spec |
| Use case | `SYS-UC` | authored in SysML → generated need | Stakeholder & system requirements spec |
| System requirement | `SYS-REQ` | authored (rst, EARS, D45); `requirement` stub in SysML | Stakeholder & system requirements spec |
| Interface (peer domains) | `SYS-IF` | authored in SysML (`interface def`/`port def`) → generated need | System architecture |
| System model element (functional / logical / product, D85) | `SYS-EL` | authored in SysML → generated need | System architecture |
| Configuration | `SYS-CFG` | authored in SysML (`configs.sysml`, PLEML) → generated need | System architecture; one generated page per configuration (D106) |
| Feature (feature model) | `SYS-FEAT` | authored in SysML (`features.sysml`) → generated need | System architecture |

### Integration (robarm-integration, D73)

| Need type | ID kind | Authored / generated | Document |
|---|---|---|---|
| System test case | `INT-STC` | authored (rst) | System & integration test spec |
| Integration test case | `INT-ITC` | authored (rst) | System & integration test spec |
| HIL setup | (described in the docs; runs on a `SYS-CFG`) | authored | System & integration test spec |

### Software (robarm-sw)

| Need type | ID kind | Authored / generated | Document |
|---|---|---|---|
| SW requirement | `SW-REQ` | authored (rst, EARS) | SW requirements spec |
| SW architecture element | `SW-ARCH` | authored (rst, or SysML later) | SW architecture & design |
| SW detailed design element | `SW-DD` | authored (rst or Doxygen group) | SW architecture & design |
| Code unit (function, module) | `SW-IMPL` | generated from Doxygen (`@xdid`, `\satisfies`) | SW architecture & design (API part) |
| SW test case | `SW-TC` | generated from ZTEST annotations (`\verifies`, test ID ledger) | SW test spec |

### Electrical (robarm-ee)

| Need type | ID kind | Authored / generated | Document |
|---|---|---|---|
| EE requirement | `EE-REQ` | authored (rst, EARS) | EE requirements spec |
| PCBA | `EE-PCBA` | authored in the EE model (board def that specializes a system block) → generated need; the KiCad project's `TraceID` refers to it (XD-ADR-0128) | `pcba-<name>` (one per PCBA) |
| Port (connector, or port of an external part) | `EE-PORT` | authored in the EE model (port def that specializes a `SYS-IF`) → generated need; the KiCad connector's `Port` field refers to it (XD-ADR-0133) | `pcba-<name>` |
| Wiring harness | `EE-HAR` | authored in the EE model (cable def) → generated need; the WireViz YAML in `harness/<name>/` refers to it (XD-ADR-0127) | `harness-<name>` |
| Circuit block / component | `EE-CMP` | generated from KiCad hidden symbol or sheet fields (D29); stays CAD-owned | `pcba-<name>` |
| Prototype wiring (modules, jumpers) | `EE-CMP` with `configs: [SYS-CFG-0001]` | generated from a KiCad schematic of the prototype (D74) | Prototype doc (one per setup) |
| EE test case | `EE-TC` | authored (rst) or generated from scripted checks | EE test spec |

### Mechanical (robarm-me)

| Need type | ID kind | Authored / generated | Document |
|---|---|---|---|
| ME requirement | `ME-REQ` | authored (rst, EARS) | ME requirements spec |
| Assembly | `ME-ASM` | authored in the ME model (assembly or sub-assembly def) → generated need; the top FreeCAD document's `TraceID` refers to it (XD-ADR-0128) | `asm-<name>` (one per top-level assembly) |
| Port (mechanical interface) | `ME-PORT` | authored in the ME model (port def that specializes a `SYS-IF`, with geometry) → generated need; a FreeCAD LCS with a `Port` property refers to it (XD-ADR-0133) | `asm-<name>` |
| Part | `ME-PART` | generated from FreeCAD object properties; stays CAD-owned | `asm-<name>` |
| ME test case | `ME-TC` | authored (rst) or generated from scripted checks | ME test spec |

### Framework and project items (D120, D121)

| Need type | ID kind | Authored / generated | Document |
|---|---|---|---|
| Framework decision | `XD-ADR` | authored (rst) | XDMOD manual, explanation/decisions |
| Method rule | `XD-RULE` | authored (rst) | XDMOD manual, explanation/rules |
| curatrix check | `XD-CHECK` | generated from curatrix | curatrix reference |
| Project decision | `PRJ-DEC` | authored (rst) | `robarm` overview (robarm-manifest) |

### Verification results (all repos)

| Need type | ID kind | Source | Document |
|---|---|---|---|
| Test result | `TR` | generated from Twister / JUnit / scripted-check output; for HIL from the evidence branch in robarm-integration (D57, D73) | Test report of the repo that owns the test case |

### Definitions, instances and which model elements become needs (D128, D129)

- **The definition holds the ID.** A SysML `part def`, a KiCad sheet file and a FreeCAD part file each carry one trace ID. Their usages (e.g. six joints, two arms) are **not** separate needs. The extractor lists them in an `instances` field, e.g. `instances: [leader.joint1, …, follower.joint6]`. A KiCad sheet used six times therefore doesn't repeat its ID as six needs.
- **Usage IDs only when needed.** If one usage has its own requirement (e.g. "joint 1 shall …"), that usage gets an ID of the form `<definition ID>.<n>` (e.g. `SYS-EL-0012.1`), written on the usage.
- **Only model elements with links become `SYS-EL` needs.** A model element becomes a need only if it takes part in a trace link: `satisfy`, `allocate`, or a link from another repo. Other model elements stay model-only. When an element gets its first link, `curatrix ids fix` gives it a short-name ID.
- **`layer: context`** is added for actors, system ports and the system of interest in the specification context (SYSMOD step 07). Interfaces stay `SYS-IF`.

## 2a. Levels of detail (Phase 5, XD-ADR-0130 to XD-ADR-0138)

| Level | Where | Holds | IDs it owns |
|---|---|---|---|
| System model | `robarm-syseng/model/` | what crosses a domain boundary: blocks down to the product level (one part def per board, assembly, SW component), their ports, interface defs at signal level (names, direction, kind, values). No connector types, pin numbers or part numbers | `SYS-EL`, `SYS-IF`, `SYS-CFG`, ... |
| Domain model | `robarm-ee/model/`, `robarm-me/model/` | how a domain realizes a block. EE: board defs, connector port defs with connector type and pin map, cable defs, external parts, board variants (with shunt settings). ME: assembly and sub-assembly defs, mechanical port defs with geometry, assembly variants. No circuit block diagrams inside a board in iteration 1 | `EE-PCBA`, `EE-PORT`, `EE-HAR`, `ME-ASM`, `ME-PORT` |
| Implementation | `pcba/`, `proto/`, `harness/`, `assemblies/`, `parts/` | KiCad projects, WireViz YAML, FreeCAD documents; they name the domain model elements by ID | `EE-CMP`, `ME-PART` |

- **Specialization:** a domain def specializes the system def it realizes (`part def JointControllerBoard :> JointController`) and redefines every inherited port with a port whose def specializes the interface def. curatrix checks this (CK-E4, XD-ADR-0132) and derives the links by kind pair: `EE-PCBA` / `ME-ASM` / `EE-HAR` → `SYS-EL` = `realizes`; `EE-PORT` / `ME-PORT` → `SYS-IF` = `conforms`; any other pair is a finding.
- **1:1:** each board def has one KiCad project, each cable def one harness folder, each assembly or sub-assembly def one FreeCAD document, each block of the prototype configuration one `proto/` project; external parts (bought boards, servos, pots) have ports but no project (XD-ADR-0128, XD-ADR-0135).
- **Instances:** syseng owns the usages it sees; the domain model owns its internal usages (XD-ADR-0138). Instances differ only through variants; the domain variant names the configurations and usages it serves, the table is computed (XD-ADR-0136).

## 3. Link-type table

The **owner** is the need type that holds the link (the source). The **targets** are the types it may point to.
"Min" is the minimum number of targets that the schema enforces.

| Link type | Owner (source) | Targets | Min | Meaning |
|---|---|---|---|---|
| `refines` | `SYS-REQ` | `SYS-NEED` | 1 | The requirement answers this need. This is SYSMOD's `frame`, kept in sphinx-needs. |
| `refines` | `SW-REQ`, `EE-REQ`, `ME-REQ` | `SYS-REQ`, `SYS-IF` | 1 ¹ | The domain requirement is derived from a system requirement or an interface. |
| `raised_by` | `SYS-NEED` | `SYS-STH` | 1 ⁴ | The stakeholder who raised the need (not required for `category: problem`). |
| `addresses` | `SYS-UC` | `SYS-NEED` | 1 | The use case addresses this need. |
| `addresses` | `SYS-NEED` (`category: need` or `objective`) | `SYS-NEED` (`category: problem`) | 0 | The need or objective addresses the problem statement (D81). |
| `realizes` | `SYS-EL` (`layer: functional`) | `SYS-UC` | 1 | The function realizes (part of) a use case (D85). |
| `satisfies` | `SYS-EL` | `SYS-REQ` | 0 ² | The model element satisfies the requirement (SysML `satisfy` through a stub). |
| `realizes` | `SYS-EL` (`layer: logical`) | `SYS-EL` (`layer: functional`) | 0 ² | Allocation `functional2logical`, stored on the concrete side (D85). |
| `realizes` | `SYS-EL` (`layer: product`, any variant) | `SYS-EL` (`layer: logical`) | 0 ² | Allocation `logical2product`, stored on the concrete side. |
| `configures` | `SYS-CFG` | `SYS-EL` (`layer: product`, the 150 % architecture) | 1 | The configuration is one product of this product line. |
| `realizes` | `SW-ARCH`, `EE-PCBA`, `EE-CMP`, `EE-HAR`, `ME-ASM`, `ME-PART` | `SYS-EL` | 1 ³ | The domain element realizes a product-layer system element. |
| `satisfies` | `SW-ARCH`, `SW-DD`, `EE-PCBA`, `EE-CMP`, `EE-HAR`, `ME-ASM`, `ME-PART` | the same domain's `*-REQ` | 0 ³ | The design element satisfies a domain requirement. |
| `conforms` | `SW-ARCH`, `SW-DD`, `EE-CMP`, `ME-PART`, `ME-ASM`, `EE-PCBA`, `EE-PORT`, `ME-PORT`, `EE-HAR` | `SYS-IF` | 0 | The element meets a peer interface (pin map, connector, mounting). For ports it is derived from specialization. |
| `conforms` | `SW-ARCH`, `SW-DD` | `EE-PCBA`, `EE-PORT` | 0 | SW meets the board's pin map in the EE model (exception to the peer rule, XD-ADR-0131). |
| `connects` | `EE-HAR` | `EE-PORT` | 2 | The ports the harness ends mate with, also ports of external parts (XD-ADR-0133). |
| `refines` | `SW-DD` | `SW-ARCH` | 1 | The detailed design element belongs to this architecture element. |
| `part_of` | `EE-CMP` → `EE-PCBA`; `ME-PART` → `ME-ASM` | as listed | 1 | Structure of the domain design. |
| `part_of` | `EE-PORT` → `EE-PCBA`; `ME-PORT` → `ME-ASM` | as listed | 0 | The board or assembly that has the port. Ports of external parts have none. |
| `implements` | `SW-IMPL` | `SW-DD`, `SW-ARCH` | 1 | The code unit implements this design element. |
| `satisfies` | `SW-IMPL` | `SW-REQ` | 0 | Optional direct link from code to a requirement (Doxygen `\satisfies`, as in safety). `implements` is still required (D77). |
| `verifies` | `INT-STC` | `SYS-REQ` | 1 | |
| `verifies` | `INT-ITC` | `SYS-REQ`, `SYS-IF` | 1 | |
| `verifies` | `SW-TC` | `SW-REQ` (and `SW-DD` for unit tests) | 1 | |
| `verifies` | `EE-TC` | `EE-REQ` | 1 | Tests of `SYS-IF` are `INT-ITC` (D115). |
| `verifies` | `ME-TC` | `ME-REQ` | 1 | Tests of `SYS-IF` are `INT-ITC` (D115). |
| `decided_by` | `XD-RULE` | `XD-ADR` | 1 | The rule was introduced by this decision. |
| `enforces` | `XD-CHECK` | `XD-RULE` | 1 | The check enforces this rule. |
| `follows` | `PRJ-DEC` | `XD-ADR` | 0 | The project decision applies or tailors a framework decision. |
| `result_of` | `TR` | `INT-STC`, `INT-ITC`, `SW-TC`, `EE-TC`, `ME-TC` | 1 | The result belongs to this test case. |

¹ A domain requirement with no upstream link must have `derived: true` and a `rationale` field (a "derived requirement").
² The minimum is enforced by the coverage rules in §4, not on the single element, because not every model element satisfies something.
⁴ Enforced for needs with `category: need` or `objective`.
³ Every domain design element needs at least one `realizes` **or** `satisfies`. Otherwise it is an orphan (§4, spike lesson 1).

## 4. Rules beyond the link table

The schema (per need type) checks the shape of each single need. These rules check the graph. Rules that need upstream (external) needs can't run as sphinx-needs warnings (research: traceability, risk 1). They run in our own check, and always in the full-set build.

| Rule | Checked by | Level |
|---|---|---|
| R1 Every `SYS-REQ` is refined by at least one domain requirement or satisfied by at least one `SYS-EL`. | own coverage check, full set | error in the full set |
| R2 Every requirement (`SYS-REQ`, `*-REQ`) has at least one `verifies` link pointing at it, **per applicable configuration** (D104, `variants.md` §4). | own coverage check | warning in iteration 1, error later |
| R3 No orphans: every product-layer `SYS-EL`, `SW-ARCH`, `EE-PCBA`, `EE-CMP`, `EE-HAR`, `ME-ASM` and `ME-PART` has a `realizes` or `satisfies` link. Ports (`EE-PORT`, `ME-PORT`) are not in this rule: a port of an external part may conform to nothing. | schema rule (local) | error |
| R4 A link to a need with `status: retired` is reported (D64e). | own check (non-failing on `main`); baseline gate | **Grace until the next baseline (D75):** on `main` and in PRs it is a reported warning that does not fail the build. The baseline build (manifest tag `baseline/vX.Y.Z`) fails while any such link remains. So the schema rule must not use a severity that `-W` turns into an error. |
| R5 Every `TR` from a HIL run carries `firmware_sha256` and the SHAs of all pinned repos it depends on (run-record schema, task 4.5a; D57, D60). | schema rule | error |
| R5a **Evidence validity (D131):** a `TR` counts only if its recorded SHAs (and firmware sha256) match the current manifest pins on `main`, or the baseline being built. Otherwise it is shown as `stale` and doesn't count for coverage. | own check | stale results: report; at baseline: they don't count |
| R6 Variant rules F1–F2, V1–V6, T1–T3 (D105, `variants.md` §3) | `curatrix check variants` | error |
| R7 Suspect links: a link whose target changed after the link was last confirmed. Until affirmatrix is adapted (D59), "last confirmed" is the **`needs.json` of the last baseline** (for PRs: of `main`). A change means a change in the hashed fields: title, content, `status`, value fields and links (D132). At each baseline, all reviewed links count as confirmed. | `needs-diff` now; affirmatrix later | report in PRs; gate before a baseline |

## 5. Fields shared by all need types

| Field | Values | Notes |
|---|---|---|
| `status` | `draft`, `valid`, `retired` | Enum in the schema (`needs.fields.status`). **`draft`** needs take part in all structure checks, but don't count as coverage and may not be the only target of a `verifies` link at a baseline. **Generated needs take their status from the source (D130):** SysML metadata (`@Trace { status = "retired"; }`), KiCad field `Status`, FreeCAD property `Status`, Doxygen tag. If a source element is deleted without being retired first, curatrix keeps a **tombstone** (ID, title, date) in `generated/retired-needs.json` until the next baseline, so downstream links resolve to a retired need and get the grace period (R4). |
| `configs` | list of `SYS-CFG` IDs; empty = all | On product-layer `SYS-EL`, domain design elements and test cases (D103). |
| `where`, `verification_scope` | feature condition; `logical` / `config` | On requirements (D103, D104). |
| `config` | one `SYS-CFG` ID | On test results (D103). This is the only place a result records its configuration (no separate link). |
| `layer` | `context`, `functional`, `logical`, `product` | Only on `SYS-EL` (SYSMOD steps 07, 10a–10d; D85, D129). |
| `instances` | list of usage paths | On definition needs that are used several times (D128). |
| `category` | `problem`, `objective`, `need` on `SYS-NEED` (D81, D82); `functional`, `performance`, `interface`, `constraint` on requirements | |
| `ears`, `quantity`, `unit`, `min`, `max`, `nominal` | see `sysmod-work-products.md` §4 | On requirements (D83). |
| `derived` / `rationale` | bool / text | Only on requirements without an upstream link. |
| `source_file` | path relative to the repo | On generated needs, so that reviewers can find the source. |
| `verification_method` | `test`, `analysis`, `inspection`, `demonstration` | On requirements (29148 style). |

## 6. Picture (V-model, links point left / up)

```
 SYS-STH  SYS-NEED ◄─addresses── SYS-UC
             ▲ refines
          SYS-REQ ◄─────────────verifies───────────── INT-STC ◄─result_of─ TR
             ▲ satisfies     ▲ refines
          SYS-EL (logical)   │              SYS-IF ◄─verifies── INT-ITC ◄─result_of─ TR
             ▲ realizes      │                 ▲ conforms
          SYS-EL (product /  SW-REQ / EE-REQ / ME-REQ ◄─verifies── SW-TC / EE-TC / ME-TC ◄─result_of─ TR
                  150 %)          ▲ satisfies
             ▲ realizes        │
          SW-ARCH / EE-PCBA / EE-CMP / ME-ASM / ME-PART ◄─refines / part_of─ SW-DD / EE-CMP / ME-PART
                                                          ▲ implements (+ optional satisfies → SW-REQ)
                                                       SW-IMPL (code)
```

## 7. Answered review questions (2026-11-14)

1. **Integration and system tests** live in a new repo **robarm-integration**, together with the HIL setups and their evidence branch (D73).
2. **Prototype wiring** is EE content in robarm-ee: a KiCad schematic of the prototype, whose elements are `EE-CMP` with `configs: [SYS-CFG-0001]` (D74, D103) (D74).
3. **Retired needs** get a grace period until the next baseline (D75, rule R4).
4. **SW architecture** stays in rst for iteration 1. A SysML SW sub-model is tried in iteration 2 (D76).
5. **Code links:** `SW-IMPL` must `implements` a design element and may also `satisfies` a `SW-REQ` directly (D77).
