# Variant model (task 3.7)

Status: **AGREED 2026-11-14** (D102–D107). Built on `../research/vamos.md` (VAMOS, PLEML, hands-on in the Pilot),
D37, D74, D78, D85 (`../decisions.md`), and the other drafts in this folder.

## 1. Method

- **VAMOS** (Weilkiens) is the method. It is a SysML v1 profile, so we use **PLEML** (MBSE4U, MIT), its SysML v2 successor (D102).
- PLEML is a **west project pinned at a commit**, next to the SYSMOD library under `libs/` (D84, D91). SYSMOD v5 itself has no variant concept.

| VAMOS concept | Robot arm | File in robarm-syseng/model |
|---|---|---|
| Core (variant-free) | functional and logical architecture (D85) | `functional.sysml`, `logical.sysml` |
| Feature model | `buildKind` = {`prototypeBuild`, `productBuild`}; later `servoClass` = {`microServo`, `standardServo`}, `followerSize` = {`sameSizeFollower`, `largeFollower`} | `features.sysml` |
| Variant constraints | `prototypeBuild` xor `productBuild`; `largeFollower` requires `standardServo` | `features.sysml` |
| 150 % product architecture | `variation part controller` {`nucleoBreakouts`, `customPcba`}; `variation part actuator` {`sg90`, later `mg996r`}; `variation part mechanics` {`benchRig`, `printedArm`}; common parts (pots) | `product.sysml` |
| Feature bindings | e.g. `nucleoBreakouts` → `prototypeBuild`; `customPcba` → `productBuild` | `product.sysml` |
| Configurations | `prototype` (`SYS-CFG-0001`), `product` (`SYS-CFG-0002`), each with one product model | `configs.sysml` |

The old `prototype.sysml` and the kind `SYS-PROTO` are dropped. A prototype setup is now simply the prototype configuration.

## 2. Needs and fields (D103)

| Field | On | Meaning |
|---|---|---|
| `configs` | product-layer `SYS-EL`, domain design elements (`EE-PCBA`, `EE-CMP`, `ME-ASM`, `ME-PART`, `SW-ARCH`, `SW-DD`), test cases | List of `SYS-CFG` IDs the element belongs to. Derived from the model, CAD or build where possible (rule T1). Empty = all configurations. |
| `where` | requirements | Feature condition, e.g. `buildKind=productBuild`. Matches the EARS "Where <feature>, the system shall …" pattern. Empty = all configurations. |
| `verification_scope` | requirements | `logical`: evidence from any configuration counts (e.g. SW logic tested on the prototype). `config`: evidence is needed in every configuration the requirement applies to (D104). |
| `config` | test results (`TR`) | The single `SYS-CFG` the run was made on. |

These replace the `variant` field of D37. Prototype wiring in robarm-ee (D74) carries `configs: [SYS-CFG-0001]`.

## 3. Rules (D105, all errors; checked by `curatrix check variants`)

They are rule R6 of `trace-model.md` §4. They run locally, in PR CI (robarm-syseng) and in the full set.

| Rule | Checks |
|---|---|
| F1 | A configuration sets only features of its tree, and every feature group keeps its multiplicity. |
| F2 | Every requires / xor / implies constraint holds in every configuration. |
| V1 | Every product model names an existing configuration, and every configuration has exactly one product model. |
| V2 | The product model binds every variation of the 150 % model. |
| V3 | … to one of that variation's own variants. |
| V4 | The chosen variant is enabled by the configuration: all features it is bound to are chosen. **Several bindings on one element mean AND** (all are needed). PLEML doesn't say this, so it's our convention. |
| V5 | Exactly one variant of each variation is enabled per configuration. |
| V6 | `assert constraint`s of the 150 % model hold in each product model (simple `==`, `implies`, `and`, `or` only). |
| T1 | `configs` of a generated need equals what the model, CAD or build says. |
| T2 | A `realizes` link is allowed only if the source's `configs` is a subset of the target's `configs`. |
| T3 | A `TR` counts for requirement R in configuration C only under the coverage rule in §4. |

**Iteration 1 subset (D135):** one feature group (`buildKind`) and rules F1, F2 and V1–V5. V6, the derivation of `configs` for T1, and the per-configuration pages (§5) come when the product configuration has real content.

The Pilot checks none of these. In the research it accepted 8 planted errors. The research prototype (`build/research-vamos/tools/variant_check.py`, about 200 lines on the Pilot JSON) caught all 8, and becomes the starting point in curatrix.

## 4. Coverage per configuration (D104)

The coverage report is a **requirement × configuration matrix**. A cell is covered when:
- `verification_scope: logical`: at least one `TR` from **any** configuration verifies the requirement;
- `verification_scope: config`: at least one `TR` with `config = C` verifies it, for each configuration C that the requirement's `where` selects.

Rule B2 (D99) applies per cell.

## 5. Documents (D106)

There is **one variant-aware doc set**. Docs show the 150 % content with configuration badges. A generated page per configuration lists:
- the elements that apply to that configuration
- the requirements selected by `where`
- that configuration's column of the coverage matrix

Bundles in iteration 2 can filter by configuration.

## 6. IDs (D107)

- `SYS-CFG-nnnn`: configurations, used in `configs`, `TR.config` and links. They are written as SysML short names.
- `SYS-FEAT-nnnn`: features of the feature model, used in `where` conditions (e.g. `where: SYS-FEAT-0002`). They are written as SysML short names.
- `SYS-PROTO` is dropped. It was never issued.

## 7. To confirm in task 6.5

- **Prototype mechanics.** The research assumed the prototype uses a bench rig, not the printed arm. If the prototype uses the printed arm too, only the `mechanics` binding changes.
