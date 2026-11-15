# Research: VAMOS and variant modeling for prototype vs. product

Date: 2026-11-14. Input for task 3.7 (variant model) and for revising D37, R6 and D74.
Marks: **[verified]** = I ran it or read the source file myself. **[read]** = I only read it on a web page, a
sample PDF or a search result.

All downloads, clones, models, scripts and logs are in `build/research-vamos/` (see §5).

## Summary

- **VAMOS** ("VAriant MOdeling with SysML") is Tim Weilkiens' method for variants. It is a **SysML v1 profile**
  (stereotypes in the SYSMOD v1 profile, for Cameo/MagicDraw) plus a book (Leanpub, 2016). Its ideas:
  **core**, **variation point**, **variation**, **variant**, **variant configuration**, **variant constraint**
  (XOR, REQUIRES), **binding time**, and a **feature tree** view. **[read]**
- **There is no SysML v2 version of VAMOS.** The SYSMOD v5 library (`mbse4u/sysmod-sysmlv2`) has no variant
  elements. **[verified, grep]** The SysML v2 successor from the same author is **PLEML**
  (`MBSE4U/PLEML`, MIT licence, v1.1.1, on Sysand), from the INCOSE IS 2025 paper by Weilkiens, Forlingieri and
  Molnár. It adds a **feature model** (feature tree, feature configurations, requires/xor/implies constraints) and
  **feature bindings** to SysML v2's own `variation`/`variant`. **[verified, source read]**
- **PLEML loads in our Pilot 0.63.1** with 0 errors (one warning inside the library), and so do its drone
  example and our robot-arm sketch. **[verified]**
- **No tool checks the variants for us.** The Pilot does not evaluate PLEML's constraints and does not check
  that a configuration picks a valid variant: 8 of 8 planted errors pass with 0 errors. Its `eval` even returns
  `true` for a violated variant constraint. PLEML's own README says OpenSysML cannot evaluate them either. **[verified]**
  MBSE4U's tooling for features (FeatureIDE plug-in) is Eclipse GUI only and archived. **[verified]**
- **Our own check is small.** A 200-line Python prototype on the Pilot JSON found every error I planted
  (wrong variant, non-variant, unbound variation, unknown configuration, broken requires/xor) and one real
  modeling mistake in my first sketch. **[verified]**
- **Proposal:** keep D37's idea, but model it the VAMOS/PLEML way: a variant-free **core** (logical
  architecture), a **feature model** with the build kinds (prototype, product) and later features (servo class,
  follower size), a **150 % product architecture** with `variation`/`variant`, and **one product model per
  configuration**. Do not invent our own variant library.
- **Replace the `variant: product|prototype|both` field** with a list of **configurations** (`configs`), derived
  from the model where possible, and add a **feature condition** (`where`) on variant-specific requirements.
  Make coverage **per configuration** and let each test result carry the configuration it ran on.
- **R6 becomes a set of rules** (F1–F2 on the feature model, V1–V5 on the product models, T1–T3 on the trace
  graph). One new ID kind `SYS-CFG` replaces `SYS-PROTO`.

## 1. What VAMOS is

### 1.1 Sources

| Source | What it is | Status |
|---|---|---|
| https://mbse4u.com/sysmod/ | SYSMOD v5 page. Its "Methods" menu links to VAMOS. | [read] |
| https://mbse4u.com/vamos/ | Short VAMOS page: profile mechanism, stereotypes in the SYSMOD profile, Cameo profile and samples on the download page, the book. No SysML v2 word. | [read] |
| https://leanpub.com/vamos — *Variant Modeling with SysML*, T. Weilkiens, 2016 (ISBN 978-3-9817875-7-3) | The method. Sample PDF: https://s3.amazonaws.com/samples.leanpub.com/vamos-sample.pdf (downloaded, `build/research-vamos/dl/vamos-sample.txt`) | [read, sample only] |
| Forlingieri, Weilkiens: *Two Variant Modeling Methods for MBPLE at Airbus*, INCOSE IS 2022, doi:10.1002/iis2.12984 | "Clean" method (inspired by VAMOS: member products by specialization and redefinition of a common model) vs. "Direct" (150 % model + model-to-model transformation). PDF blocked by Cloudflare; only abstracts and search summaries. | [read, abstract] |
| Weilkiens, Forlingieri, Molnár: *Next Generation MBPLE with SysML v2: Feature Modeling, Variability Modeling, and API Potentials*, INCOSE IS 2025, doi:10.1002/iis2.70058 | Basis of PLEML. PDF blocked (403). | [read, abstract] |
| https://github.com/MBSE4U/PLEML (MIT, v1.1.1, commit `b694648`, 2026-10-19) | SysML v2 library `PLEML.sysml`, drone example (feature model, shared assets, product model), constraint tests. | [verified, cloned and loaded] |
| https://github.com/MBSE4U/mbple-featureide (Apache-2.0, archived, moved to Open-MBEE) | Eclipse/FeatureIDE plug-in that imports features through the SysML v2 API. Server URL and project are hard-coded. GUI only. | [verified, README and files] |
| https://github.com/MBSE4U/sysmod-sysmlv2 (Apache-2.0) | SYSMOD v5 library. **No** variation, variant or feature elements (only a doc comment that mentions "drone variant"). | [verified, grep] |
| OMG issue SYSML21-365 "Optional Variation Point" (by the PLE side) | Open. SysML v2 variations can only hold variants; optional variation points need a workaround. | [read] |

### 1.2 Concepts (book, chapter 2) [read]

- **Core**: all elements used in every configuration. The core does not know the variants.
- **Variation point**: a core element marked as the docking point for variant elements. It has a
  **binding time** and refers to the variations that may dock there.
- **Variation**: the discriminator for variants, e.g. "engine kind".
- **Variant**: a complete set of variant elements for one variation, e.g. "diesel". "Also known as a feature."
  A variant may again contain variations (recursive structure).
- **Variant configuration**: a valid set of variants plus the core, i.e. one member product. It is itself a
  variant of a "configurations" variation.
- **Variant constraint**: rules for valid sets. Two are predefined: **XOR** (excludes) and **REQUIRES**.
- **Feature tree** and **matrix/table views** show the variations and configurations.

### 1.3 Method and structure (book, chapter 3) [read]

- Three top-level packages that are **orthogonal**: `<System>_Core`, `<System>_Variations` (one package per
  variation, one sub-package per variant), `<System>_Configurations`. Configurations depend on variants and
  core; variants depend only on the core; the core depends on nothing (except variation-point marks).
- Variants dock at variation points mostly by **generalization** (a variant block specializes the core block).
  A configuration is built by **specialization and redefinition** (the Airbus "Clean" method).
- VAMOS works with any standard SysML tool; it does not need a separate variant tool. The book admits that a
  real variant tool is better for "very ambitious" variant needs.
- Relation to SYSMOD: the VAMOS stereotypes are part of the SYSMOD (v1) profile, but can be used alone. The
  book's examples (forest fire detection, virtual museum tour) use SYSMOD's base, logical and product
  architecture, and put variants in the product architecture.

### 1.4 SysML v2 status

- **SysML v2 has variants built in**: `variation` (definition or usage) and `variant` (usage), stored as
  `VariantMembership`. A configuration binds a variation to one variant by redefinition
  (`part :>> controller = controller::prototype;`). This covers VAMOS' variation point / variation / variant
  **in the language itself**, so the VAMOS stereotypes are not needed any more. **[verified, earlier research
  and here]**
- What the language lacks is the **feature model** (tree, configurations, constraints, binding time) and a
  **link between model elements and features**. PLEML fills exactly this gap. **[verified, source]**
- **PLEML in short** (`PLEML.sysml`, 360 lines, MIT):
  - Keywords `#featureModel`, `#featureTree`, `#feature`, `#featureConfiguration` (semantic metadata over
    occurrence defs/usages).
  - Features are occurrence usages; nesting = hierarchy; `[0..1]` = optional; `:>` (subsetting) of a group
    feature = alternative; the group's multiplicity limits how many children may be chosen.
  - A **feature configuration** specializes the feature tree and sets the chosen features to `[1]`. Built-in
    `assert constraint`s say what a valid configuration is (only features; all non-root features set; binding
    time not later than the configuration's; all feature constraints hold).
  - Constraints `RequiresConstraint`, `XORConstraint`, `ImpliesConstraint` with `new FeatureOperand(A, B)`.
  - `LifeCycleKind` binding times: `Development`, `Production`, `Operation`.
  - `#FeatureBinding dependency from <shared asset element> to <feature>` (metadata `@FB`) binds a variant,
    an optional part or a **requirement variant** to a feature. `@FCFGB { featureConfiguration = "…"; }` binds a
    **product model** package to a configuration.
  - The drone example shows the full pattern: feature model → shared assets (150 % model with `variation part`,
    `variation requirement`, `variation action`) → product model per member product (a part def that
    specializes the 150 % def and binds each variation). The product model's doc comment says it "can be
    automatically generated" from the configuration and the bindings, but **no generator is published**.
- So, in SysML v2 terms: **VAMOS core = base/logical architecture; VAMOS variation point + variation + variant
  = SysML v2 `variation`/`variant`; VAMOS variant configuration = PLEML feature configuration + product model;
  VAMOS variant constraint = PLEML requires/xor/implies (or a plain `assert constraint` in the 150 % model).**

## 2. Our case in VAMOS terms

### 2.1 Mapping

| VAMOS concept | Robot arm | Where |
|---|---|---|
| Core | Logical architecture (`LogicalJoint`: angle sensor, joint controller, joint actuator; their ports, connections and `satisfy`) and the functional architecture (D85) | `logical.sysml`, `functional.sysml` |
| Variation (feature group) | `buildKind` = {`prototypeBuild`, `productBuild`}; later `servoClass` = {`microServo` (SG90), `standardServo`}; `followerSize` = {`sameSizeFollower`, `largeFollower`} | new `features.sysml` (PLEML) |
| Variant constraint | `prototypeBuild` xor `productBuild`; `largeFollower` requires `standardServo` | `features.sysml` |
| Variation point + variants | In the 150 % product architecture: `variation part controller` {`nucleoBreakouts` (NUCLEO-G474RE + PCA9685 + MCP3208 breakouts + jumpers), `customPcba`}; `variation part actuator` {`sg90`, `mg996r`}; `variation part mechanics` {`benchRig`, `printedArm`, `largePrintedArm`}. Pots are common. | `product.sysml` |
| Feature binding | `nucleoBreakouts` → `prototypeBuild`; `customPcba` → `productBuild`; `printedArm` → `productBuild` **and** `sameSizeFollower`; product-only requirement → `productBuild` | `product.sysml` |
| Variant configuration | Feature configurations `prototype`, `product` (later `bigBot`) + one product model each (`PrototypeJoint`, `ProductJoint`) | `features.sysml`, `configs.sysml` (replaces `prototype.sysml`) |

Assumption: the prototype has a bench rig, not the printed arm. If the prototype also uses the printed arm, the
`mechanics` binding changes; nothing else does.

### 2.2 SysML v2 sketch

Shortened from the files that I checked with the Pilot (`build/research-vamos/model/*.sysml`, 0 errors):

```sysml
package RobArmFeatures {                         // features.sysml
    private import PLEML::*;
    #featureModel occurrence def RobArmFeatureModel {
        #featureTree occurrence robArmFeatures :> featureTrees {
            #feature occurrence buildKind[1];
            #feature occurrence prototypeBuild[0..1] :> buildKind default null {
                assert constraint :>> xorFeatures {
                    in occurrence constrainedFeatures = new FeatureOperand(that, productBuild);
                }
            }
            #feature occurrence productBuild[0..1] :> buildKind default null;
            #feature occurrence servoClass[1];
            #feature occurrence microServo[0..1] :> servoClass default null;      // SG90
            #feature occurrence standardServo[0..1] :> servoClass default null;   // later
            #feature occurrence followerSize[1];
            #feature occurrence sameSizeFollower[0..1] :> followerSize default null;
            #feature occurrence largeFollower[0..1] :> followerSize default null { // later
                assert constraint :>> requiresFeatures {
                    in occurrence constrainedFeatures = new FeatureOperand(that, standardServo);
                }
            }
        }
        #featureConfiguration occurrence prototype :> robArmFeatures, featureConfigurations {
            #feature occurrence :>> buildKind[1] = (prototypeBuild);
            #feature occurrence :>> prototypeBuild[1];
            #feature occurrence :>> servoClass[1] = (microServo);
            #feature occurrence :>> microServo[1];
            #feature occurrence :>> followerSize[1] = (sameSizeFollower);
            #feature occurrence :>> sameSizeFollower[1];
        }
        #featureConfiguration occurrence product :> robArmFeatures, featureConfigurations { /* productBuild, … */ }
    }
}

package RobArmCore {                             // logical.sysml: the VAMOS core, no variations
    part def <'SYS-EL-0001'> LogicalJoint {
        part sensor : AngleSensor;  part controller : JointController;  part actuator : JointActuator;
        connect sensor.angleOut to controller.angleIn;
        connect controller.cmdOut to actuator.cmdIn;
        satisfy followLatency by controller;     // stub of SYS-REQ-0001
    }
}

package RobArmProductLine {                      // product.sysml: 150 % product architecture
    private import PLEML::*;  private import RobArmCore::*;  private import RobArmFeatures::*;
    part def <'SYS-EL-0002'> RobArmJoint :> LogicalJoint {
        part :>> sensor : Potentiometer;                          // common
        variation part :>> controller : JointController {
            variant part nucleoBreakouts : JointController {
                part nucleo : NucleoG474re;  part pwm : Pca9685Breakout;
                part adc : Mcp3208Breakout;  part wiring : JumperWiring;
            }
            variant part customPcba : JointController { part pcba : JointCtrlPcba; }
        }
        variation part :>> actuator : JointActuator {
            variant part sg90 : Sg90;  variant part mg996r : Mg996r;
        }
        variation part mechanics {
            variant part benchRig : BenchRig;
            variant part printedArm : PrintedArm;
            variant part largePrintedArm : PrintedArm;
        }
        assert constraint largeNeedsStrongServo {                 // a variant constraint in plain SysML v2
            mechanics == mechanics::largePrintedArm implies actuator == actuator::mg996r
        }
    }
    occurrence def RobArmProductLineProject {
        #featureModel occurrence fm : RobArmFeatureModel;
        part line : RobArmJoint;
        #FeatureBinding dependency from line::controller::nucleoBreakouts to fm::robArmFeatures::prototypeBuild;
        #FeatureBinding dependency from line::controller::customPcba      to fm::robArmFeatures::productBuild;
        #FeatureBinding dependency from line::mechanics::benchRig         to fm::robArmFeatures::prototypeBuild;
        #FeatureBinding dependency from line::mechanics::printedArm       to fm::robArmFeatures::productBuild;
        #FeatureBinding dependency from line::mechanics::printedArm       to fm::robArmFeatures::sameSizeFollower;
        #FeatureBinding dependency from line::actuator::sg90              to fm::robArmFeatures::microServo;
        #FeatureBinding dependency from RobArmCore::enclosure             to fm::robArmFeatures::productBuild;
        // … mg996r → standardServo, largePrintedArm → productBuild + largeFollower
    }
}

package RobArmConfigs {                          // configs.sysml: one product model per configuration
    private import RobArmProductLine::*;
    package <PROTO> PrototypeModel {
        @PLEML::FCFGB { featureConfiguration = "prototype"; }
        part def <'SYS-CFG-0001'> PrototypeJoint :> RobArmJoint {
            part :>> controller = controller::nucleoBreakouts;
            part :>> actuator   = actuator::sg90;
            part :>> mechanics  = mechanics::benchRig;
        }
    }
    package <PROD> ProductModel {
        @PLEML::FCFGB { featureConfiguration = "product"; }
        part def <'SYS-CFG-0002'> ProductJoint :> RobArmJoint {
            part :>> controller = controller::customPcba;
            part :>> actuator   = actuator::sg90;
            part :>> mechanics  = mechanics::printedArm;
        }
    }
}
```

Notes on the sketch:

- **Allocation `logical2product` comes for free.** A variant (`nucleoBreakouts : JointController`) is typed by
  (or specializes) the logical element it realizes. Our extractor can turn that into the `realizes` link.
- **Variant-specific requirements** stay in sphinx-needs (D6). In the model they are bound to a feature by a
  `#FeatureBinding` on the stub. SysML v2 also allows `variation requirement` (drone example: 60 min vs. 120 min
  flight time). For us, a requirement with **different values per configuration** is better written as two
  requirements, each with a feature condition.
- **A variant that depends on two features** (`printedArm` = product build **and** same-size follower) needs
  two bindings. PLEML gives `@FB` only one feature name and says nothing about several bindings. Our check
  reads several bindings as AND. Without that, my first sketch enabled two `mechanics` variants for the
  prototype (see §5, finding V5).

## 3. Comparison with D37, R6, D74 and proposed changes

### 3.1 What stays

- D37's core idea stays: prototype and product are variants of **one** logical architecture, and a prototype
  test may verify what the prototype has in common with the product. VAMOS says the same thing in other words
  (core vs. variant elements).
- D74 stays: the prototype wiring is EE content (a KiCad schematic) in robarm-ee.
- SysML v2 `variation`/`variant` stay the modeling means. VAMOS for v2 does not replace them; PLEML builds on them.

### 3.2 What is missing in the current plan

| Gap | Today | Effect |
|---|---|---|
| No feature model | `variant: product\|prototype\|both` is a closed enum | A third variant (stronger servo, larger follower) breaks the enum. "both" no longer means "all". |
| No configuration as an element | `SYS-PROTO` names a prototype setup, but there is no product configuration element | Nothing in the trace graph says "this test ran on configuration X". |
| Coverage is not per configuration | R2: "every requirement has a `verifies` link" | A product-only requirement looks covered by a prototype test. D37's rule is not checkable. |
| R6 is vague | "`realizes` joins elements of compatible variants" | No rule for unbound variations, wrong variants, invalid feature sets. |
| `prototype.sysml` as a "variant of the product context" | two separate contexts | VAMOS/PLEML put both into one 150 % model plus one small product model per configuration. |

### 3.3 Proposed changes to decisions (new rows; old rows stay)

- **D86 (revises D37 in part): variant modeling follows VAMOS as done in SysML v2 by PLEML.**
  The logical architecture is the variant-free core. A **PLEML feature model** (`features.sysml`) lists the
  features and the configurations. The product architecture is a **150 % model** with SysML v2
  `variation`/`variant`, and its variants are bound to features with `#FeatureBinding`. Each configuration has a
  **product model** (`@FCFGB`) that binds every variation. **PLEML is a west project** pinned at a commit (like
  D84; MIT licence). Configurations in iteration 1: `prototype`, `product`.
- **D87 (replaces the `variant` values of D37/trace-model §5): `configs` and `where`.**
  Design elements carry `configs: [prototype, product, …]`, the list of configurations they are part of. For
  generated needs the extractor **derives** it from the model (common element → all configurations; variant →
  the configurations whose product model picks it). For authored domain elements (KiCad, FreeCAD, SW) it is
  written by hand, or comes from the project/sheet the element lives in (D74: the prototype schematic →
  `configs: [prototype]`). Empty = all configurations. Requirements get an optional **`where`** field: a feature
  expression (`productBuild`, `largeFollower and standardServo`). It must match the EARS "Where …" clause
  (same check style as D83). No `where` = applies to every configuration.
- **D88 (refines D37's evidence rule): coverage is per configuration.**
  Every HIL setup / test bench belongs to one configuration, and every `TR` carries `config`. A requirement R
  is **covered in configuration C** when a `TR` with `config: C` verifies R through a passing test case.
  A requirement may say `verification_scope: logical` (default for SW requirements and for system requirements
  that are satisfied only by core elements): then a result from **any** configuration in which all elements
  that satisfy R are common elements counts for all configurations. Requirements satisfied by a variant need
  evidence from a configuration that contains that variant. The coverage report is a **requirement ×
  configuration matrix**.
- **D89 (replaces R6): the variant check** (rules in §3.4), our own tool on the Pilot JSON (D65), error level.
- **D90 (refines D27): documents are variant-aware, not one set per variant.** One system architecture document
  shows the 150 % model, a feature table, and a configuration matrix (variation × configuration →
  variant). Each configuration gets a short **configuration page** (generated: chosen variants, applicable
  requirements, coverage column). The existing "one doc per prototype setup" (D27) becomes the prototype
  configuration's page plus the prototype wiring doc in robarm-ee (D74). We do **not** use sphinx-needs'
  build-time `needs_variants` to build one document set per configuration: it would hide the other
  configurations and multiply builds.
- **D91 (ID scheme): new kind `SYS-CFG`** for a configuration (its product model part def), owner robarm-syseng,
  issued by the ledger and used as the SysML short name. `SYS-PROTO` is retired before any number is issued.
  Features keep their SysML names (they are not traced to by needs except through `where`); variants keep
  `SYS-EL` IDs with `layer: product`.

### 3.4 trace-model.md changes

- §1 principle 5 → "Variants follow D86: core = logical architecture; variants live in the 150 % product
  architecture; each element carries `configs` (D87)."
- §2: replace the `SYS-PROTO` row by `SYS-CFG` (configuration, generated from the product model). Add a
  "Feature (model only, no need)" note. `EE-CMP` with `variant: prototype` → `EE-CMP` with `configs: [prototype]`.
- §3 link table, new rows:

  | Link type | Owner | Targets | Min | Meaning |
  |---|---|---|---|---|
  | `configures` | `SYS-CFG` | `SYS-EL` (`layer: product`, the 150 % part def) | 1 | The configuration is a member product of this product line. |
  | `realizes` | `SYS-EL` (variant) | `SYS-EL` (`layer: logical`) | 1 | Unchanged meaning; now derived from the variant's type. |
  | `runs_on` | HIL setup / `INT-STC` run record, `TR` | `SYS-CFG` | 1 for HIL `TR` | The result was produced on this configuration. |

  Drop the row "`SYS-PROTO` realizes `SYS-EL`".
- §4 rules: R2 becomes "**per applicable configuration**" (D88). R6 is replaced by:

  | Rule | Checks |
  |---|---|
  | F1 | Each feature configuration only sets features of its tree, and each feature group has a number of chosen children inside the group's multiplicity. |
  | F2 | Every requires / xor / implies constraint holds in every configuration. |
  | V1 | Every product model (`@FCFGB`) names an existing feature configuration, and every configuration has exactly one product model. |
  | V2 | The product model binds every variation of the 150 % model (no variation left open). |
  | V3 | … to one of that variation's own variants. |
  | V4 | The chosen variant is enabled by the configuration (all features it is bound to are chosen). |
  | V5 | Exactly one variant of each variation is enabled per configuration (bindings are not ambiguous). |
  | V6 | `assert constraint`s of the 150 % model that compare variants hold in each product model (simple `==` / `implies` / `and` / `or` only). |
  | T1 | `configs` of a generated need equals what the model says. |
  | T2 | A `realizes` link from a domain element to a `SYS-EL` is allowed only if the domain element's `configs` is a subset of the target's `configs`. |
  | T3 | A `TR` counts for requirement R in configuration C only under D88. |
- §5 fields: replace the `variant` row by `configs` (list, values from the feature model) and add `where` and
  `verification_scope` on requirements; `config` on `TR`.

### 3.5 sysmod-work-products.md changes

- §1 principle 5: "Variants follow VAMOS (Weilkiens), in SysML v2 through PLEML (D86). SYSMOD v5 has no variant
  concept."
- §2: step 10c becomes "Product architecture (150 %) + allocation"; step 10d becomes "**Features and
  configurations**: feature model (`features.sysml`), product model per configuration (`configs.sysml`)",
  need types `SYS-CFG` and `SYS-EL` with `configs`.
- §3 files: `prototype.sysml` → `features.sysml` + `configs.sysml`; PLEML as a west project next to the SYSMOD
  library.
- §4: add `where` and `verification_scope` to the requirement fields.
- §5: task 5.5 = feature model + configurations + variant check.

### 3.6 id-scheme.md changes

- Add `SYS-CFG` (configuration, robarm-syseng, ledger, SysML short name). Retire `SYS-PROTO` (never issued).
- No IDs for features: their SysML names are stable enough, and needs refer to them only in `where`.
- The configuration name (`prototype`, `product`) is used in `configs`, `where`, `TR.config` and folder names;
  the `SYS-CFG` ID is used in links.

## 4. Tooling

- **VAMOS brings no tool.** Its v1 profile has OCL constraints (e.g. "a variant is owned by a variation"), which
  run only inside Cameo. **[read]**
- **PLEML brings no command-line tool.** Its constraints are SysML v2 `assert constraint`s that need an
  evaluator with `suboccurrences` support. Its README says OpenSysML 0.9.2 does not evaluate them conclusively.
  The Pilot also does not (see §5). The FeatureIDE plug-in is an Eclipse GUI and archived. **[verified]**
- **Configuration resolution** (turning a feature configuration into a product model) is only described in a
  doc comment of the drone example. Nobody publishes a generator. **[verified]**
- **So we write the check ourselves** (D89). It reads the Pilot JSON export (D65) and needs:
  1. Feature tree: features with `FeatureMetadata`, their multiplicity, group parent (subsetting), and their
     constraints (`xorFeatures`/`requiresFeatures`/`impliesFeatures`, operands from the `FeatureOperand`
     constructor; `that` = the owning feature).
  2. Feature configurations: the redefined features with lower bound 1.
  3. Feature bindings: `Dependency` elements with the `FeatureBinding` metadata, client → supplier; several
     bindings on one client = AND.
  4. Variations: `VariantMembership` (owner = variation, member = variant).
  5. Product models: packages with `FeatureConfigurationBinding` metadata (string literal value), their part
     defs, the `Redefinition` + `FeatureValue`/`FeatureReferenceExpression` per variation.
  6. Output: rule errors (F1–F2, V1–V6), the variation × configuration matrix, and `configs` per element for the
     needs extractor (T1).
  The prototype `build/research-vamos/tools/variant_check.py` does 1–5 and F1, F2, V1–V5 in about 200 lines.
  V6 needs a tiny expression evaluator for `==`, `implies`, `and`, `or` over variant references.
- Optional later: generate the product models from the configuration (the drone doc comment's algorithm), so
  people only edit the feature configuration. Not needed for two configurations.

## 5. Hands-on results [verified]

All commands ran from the workspace root under `.venv/bin/xd-limit` (Pilot: `-m 4G -t 10m`, jshell
`-J-Xmx3g`; Python: `-m 1G -t 5m`, `python -I`). The Pilot runner is a copy of the spike's `sysml_check.py`
with `-J-Xmx3g` (`build/research-vamos/tools/sysml_check.py`); the spike was not changed.

1. **Clones** (`build/research-vamos/`): `PLEML` (`b694648`), `mbple-featureide` (`8332484`),
   `sysmod-sysmlv2` (`621454a`), `the-sysmlv2-book-examples` (`e8c399f`).
2. **PLEML + drone example + constraint tests in Pilot 0.63.1** (this one run was started from
   `build/research-vamos/` by mistake, not from the workspace root; all later runs were from the root): all 5 files `ok`, 0 errors, 1 warning in the
   library (`Cast argument should have conforming types`, `PLEML.sysml` line 358, in `DeriveFeatureName`).
   Export: 2281 elements. Time 32 s. (`out/pleml-drone.json`)
3. **Robot-arm sketch** (`model/RobArmCore|Features|ProductLine|Configs.sysml`): 0 errors after one fix
   (a `requirement` usage cannot be typed by a requirement usage; I bound the stub itself instead). Export:
   5673 elements, about 38 s.
4. **Own check on the sketch:**
   - First version: **V5 error**: the prototype enabled both `benchRig` and `printedArm`, because `printedArm`
     was bound only to `sameSizeFollower`, which the prototype also has (`out/check-v0-ambiguous.log`). A real
     modeling mistake; fixed with a second binding (AND).
   - Fixed version: `variant-check: OK`, prints the chosen variant per variation and configuration, and
     "requirement enclosure applies: True" for `product`, "False" for `prototype` (`out/check-v1-ok.log`).
5. **Planted errors** (`neg/`, runner `tools/run-scenarios.sh`, logs `out/<case>-pilot.log`,
   `out/<case>-check.log`, summary `out/scenarios.log`):

   | Case | Planted error | Pilot | Our check |
   |---|---|---|---|
   | n1 | prototype product model picks `customPcba` | 0 errors | **V4** `customPcba` needs `productBuild` |
   | n2 | `controller = sensor` (not a variant) | 0 errors, only a warning "Bound features should have conforming types" | **V3** not one of its variants |
   | n3 | `mechanics` not bound | 0 errors | **V2** variation not bound |
   | n4 | `@FCFGB` names `"protoype"` (typo) | 0 errors | **V1** configuration does not exist |
   | n5 | configuration `largeFollower` + `microServo` | 0 errors | **F2** `largeFollower` requires `standardServo` |
   | n6 | configuration with `prototypeBuild` and `productBuild`, `buildKind[1] = (a, b)` | 0 errors (no multiplicity error either) | **F1** group has 2 of 1..1; **F2** xor |
   | p7 | valid future variant `bigBot` (large follower, MG996R, custom PCBA) | 0 errors | OK |
   | n8 | `bigBot` with SG90 (breaks `largeNeedsStrongServo` and the feature binding) | 0 errors | **V4** `sg90` needs `microServo` |

   So the Pilot catches **none** of the 8 planted variant errors (only a type warning in n2). Our check catches
   all of them. Pilot time per run: 45–66 s on a loaded machine (about 35 s when idle).

6. **Pilot expression evaluation** (`tools/eval.jsh`, `SysMLInteractive.eval(expr, target)`):

   - `largeNeedsStrongServo()` on the valid `BigBotJoint` → `true`; on the violating `BigBotBadServo` → also
     **`true`**. The direct expression `mechanics == mechanics::largePrintedArm implies …` and plain feature
     references → `Must be an accessible feature`. `1 + 2` → `3`. (`out/eval.log`)
   - So the Pilot's evaluator **cannot** check variant constraints. Rule V6 must be our own code.

7. **sphinx-needs variants** (`needs_variants`, `<<[expr]: value, …>>` in need options) exist in the installed
   sphinx-needs. They pick one option value per **build**. **[verified: source present; not tried]**

## 6. Risks and open questions

- **PLEML is young** (v1.0.0 and v1.1.0 in 2026, a breaking change in v1.1.0). Pin it by commit and keep our
  use small: keywords, configurations, `#FeatureBinding`, `@FCFGB`. Our check does not depend on PLEML's
  constraint semantics being evaluated by a tool.
- **AND semantics of several `#FeatureBinding`s** is our reading, not stated by PLEML. Ask upstream (issue on
  MBSE4U/PLEML) or bind to a derived feature instead.
- **No public VAMOS/PLEML method text for SysML v2 beyond the README and examples.** The IS 2025 paper was not
  reachable (403). I did not read the full VAMOS book (sample only).
- **Pilot renderer breaks on variations** (earlier research). Not a problem for drawio views we render
  ourselves, but our renderer must handle `variation` usages (show variants as alternatives, or render one
  product model at a time).
- **Generated-needs volume.** A 150 % model plus product models doubles some elements. The extractor should
  emit needs for the 150 % elements only, and give each a `configs` list, not emit copies per configuration.
- **Where does the prototype get its mechanics?** I assumed a bench rig. Decide in 5.5.
- **Binding time** (PLEML `Development`/`Production`/`Operation`) is not needed now (all our features are
  development time). Leave it at the default.
- **Open:** should the product model part defs (`SYS-CFG`) also be the HIL setup records, or should robarm-
  integration keep its own HIL setup description that links to `SYS-CFG` (`runs_on`)? I propose the latter.
- **Open:** do we want PLEML's keywords in the model at all, or only plain SysML v2 variations + our own
  `configs` metadata? PLEML costs one pinned library and gives us feature constraints and a standard shape that
  MBSE4U tools may support later. I recommend PLEML.
