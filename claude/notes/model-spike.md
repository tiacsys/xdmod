# Model spike: domain sub-models by specialization (task 5.11, P5-2)

Date 2026-11-17. Question: can a domain repo (robarm-ee) refine the system model (robarm-syseng)
in its own `model/` folder by SysML v2 specialization, and can curatrix derive the trace links
from it? Short answer: **yes**. The Pilot parses it with the system model as a library set, the
IDs survive `compact`, and a 100-line Python function derives `realizes` / `conforms` and the
conformance check. Two curatrix pitfalls must be fixed first (nested packages, file order).

## Setup

All scratch files are in `build/spike-model/` (not committed; IDs `*-0901..0906` exist only
there, never in a ledger). xdmod at `2844966` (origin/main), worktree set `spike/model`, Pilot 0.63.1.

- `sys/interfaces.sysml`, `sys/product.sysml` (stands for robarm-syseng): `port def <'SYS-IF-0901'>
  ServoIf` with signal ports `out pwm`, `out vcc`, `inout gnd` (typed `ElSignal`, SYS-IF-0902),
  `CanIf`, `MountIf`; `part def <'SYS-EL-0901'> JointController { port servoOut : ServoIf; port bus :
  CanIf; }`, `PowerBoard` (SYS-EL-0902, also has a port `servoOut`), and a nested package
  `SpikeSystem::SpikeSystemDetail` with `SensorBoard` (SYS-EL-0904).
- `ee/a_boards.sysml`, `ee/b_ports.sysml` (stands for robarm-ee/model/):
  - `port def <'EE-PORT-0901'> ServoHeader :> ServoIf` with `attribute connector = "JST-XH-3"` and
    `out port :>> pwm : PinSignal { :>> pin = 1; :>> net = "SERVO_PWM"; }` per signal;
  - `part def <'EE-PCBA-0901'> JointControllerBoard :> JointController { port :>> servoOut :
    ServoHeader; port :>> bus : CanHeader; }` (good);
  - `SensorBoardPcba :> SensorBoard {}` (planted: `bus` not redefined);
  - `WrongBoard :> JointController` with `servoOut : CanHeader` (planted: wrong port def);
  - `ComboBoard :> JointController, PowerBoard` (ME-1 style; both supers have `servoOut`, only one
    is redefined);
  - nested package `SpikeEePorts::SpikeEeDetail` with `TinyBoard` (EE-PCBA-0905).
- `ee2/`: the two EE files concatenated into one, plus `combo2.sysml` (`ComboBoard2` that redefines
  both `servoOut` in one port, and the `unit` name test with a stub-like `requirement`), and
  package `SpikeEeVariants`: `JointControllerBoardB :> JointControllerBoard` (a variant, no own
  redefinitions), `JointControllerBoardC` (variant that redefines `servoOut` with `CanHeader`),
  `OddBoard` (an `EE-PORT` ID on a def that specializes a `SYS-EL`).
- `ee_dir/b_ports.sysml`: `b_ports.sysml` without the directions on the redefined signal ports.
- `run.py`: calls `curatrix.pilot.run(ws, files, export, out, libraries=[XdTrace, system files])`,
  then `model.compact(data, model.top_packages(libs))`. `derive.py`: the link derivation and check.

Run from the set root `.worktrees/spike/model`:

```
PYTHONPATH=xdmod/curatrix/src ../../../.venv/bin/curatrix run -m 4G -t 10m -- \
  ../../../.venv/bin/python ../../../build/spike-model/run.py ee \
  sys/interfaces.sysml,sys/product.sysml ee/b_ports.sysml,ee/a_boards.sysml SpikeEeBoards,SpikeEePorts
.venv/bin/curatrix run --use script -- .venv/bin/python build/spike-model/derive.py \
  build/spike-model/out/ee.compact.json build/spike-model/out/sysonly.compact.json   # from the ws root
```

Evidence: every run below has its log in `build/spike-model/out/` (all Pilot runs under
`curatrix run -m 4G -t 10m`): `sysonly.log`, `sys-toppackages.log` (+ `sys-toppackages-json-tail.log`),
`ee-nameorder.log`, `ee-direction.log`, `ee.log`, `ee2.log`, `eefull.log`, `derive-ee.log`,
`derive-ee2.log`. The JSON exports (`*.json`, `*.compact.json`) are next to them.

## 1. Pilot with the system model as library set — works

```
FILE LIBRARY-SET [XdTrace.sysml, interfaces.sysml, product.sysml]: ok
FILE .../ee/b_ports.sysml: ok
FILE .../ee/a_boards.sysml: ok
WARNING:Duplicate of inherited member name 'servoOut' from PowerBoard (3.sysml line : 27 column : 9)
SYSML-RESULT errors=0      ok=True errors=0 seconds=12.8
```

(`out/ee.log`)

- **Missing redefinition** (`SensorBoardPcba`): the Pilot says nothing. Confirmed (P5-2).
- **Wrong port def** (`WrongBoard`, `servoOut : CanHeader` redefining a `ServoIf` port): the Pilot
  says nothing either (`out/ee.log`). It does not check that a redefining feature's type specializes the
  redefined one. So curatrix must check names **and** types.
- **Double specialization** (`ComboBoard`): parses; only a WARNING "Duplicate of inherited member
  name 'servoOut' from PowerBoard". `pilot.run` keeps `ok=True`, so the warning is easy to miss.
  `port :>> JointController::servoOut, PowerBoard::servoOut : ServoHeader;` (one port redefines
  both) removes the warning. Rule for ME-1: a clash must be resolved by one port that redefines all
  clashing ports.
- What the Pilot does check: names of redefined features, port typed by a port def, and
  **direction**: `port :>> pwm` inside `ServoHeader` fails with "Redefining feature must have a
  compatible direction" (`out/ee-direction.log`, 5 errors) until it is written `out port :>> pwm`. Good for signal-level conformance,
  but authors must repeat the direction.

## 2. Export, IDs after `compact`, derived links — works with this fallback

- Raw export: system elements are in it with `isLibraryElement: false` (the Pilot does not mark
  `si.process`ed library sets as library). `compact` turns them into stubs because their top
  package is in `top_packages(libs)`.
- **IDs survive**: stubs keep `declaredShortName`, e.g. `lib:SpikeSystem::JointController` has
  `SYS-EL-0901`, `lib:SpikeInterfaces::ServoIf` has `SYS-IF-0901`.
- **Superclassifiers**: a def has no `superclassifier` key itself. Path: `ownedRelationship` ->
  element with `@type: Subclassification` -> `superclassifier` (also `general`) -> `lib:<qn>` stub.
  Redefinitions the same way: port -> `Redefinition` -> `redefinedFeature`; the port's def from
  `type`. All these keys are already in `model.KEEP`.
- **What the stubs lose**: features and types. `lib:SpikeSystem::JointController` has no ports
  and `lib:...::servoOut` has no `type`, so "which ports must be redefined, with which def" cannot
  be answered from the domain JSON alone. Fallback used in `derive.py`: read the system model's own
  compact JSON (what syseng commits as `generated/model.json`) and join by qualified name
  (`lib:X` -> `X`). This runs without Java, so CI can run the check.

`derive.py` output on the export (`out/derive-ee.log`; all planted errors found, no false findings):

```
EE-PCBA-0903 realizes SYS-EL-0901    (SpikeEeBoards::ComboBoard :> SpikeSystem::JointController)
EE-PCBA-0903 realizes SYS-EL-0902    (SpikeEeBoards::ComboBoard :> SpikeSystem::PowerBoard)
EE-PCBA-0901 realizes SYS-EL-0901    (SpikeEeBoards::JointControllerBoard :> SpikeSystem::JointController)
EE-PCBA-0902 realizes SYS-EL-0904    (SpikeEeBoards::SensorBoardPcba :> SpikeSystem::SpikeSystemDetail::SensorBoard)
EE-PCBA-0904 realizes SYS-EL-0901    (SpikeEeBoards::WrongBoard :> SpikeSystem::JointController)
EE-PORT-0902 conforms SYS-IF-0903    (SpikeEePorts::CanHeader :> SpikeInterfaces::CanIf)
EE-PORT-0903 conforms SYS-IF-0904    (SpikeEePorts::MountHoles :> SpikeInterfaces::MountIf)
EE-PORT-0901 conforms SYS-IF-0901    (SpikeEePorts::ServoHeader :> SpikeInterfaces::ServoIf)
EE-PCBA-0905 realizes SYS-EL-0904    (SpikeEePorts::SpikeEeDetail::TinyBoard :> ...::SensorBoard)
conformance findings:
  ComboBoard: port servoOut (from SpikeSystem::PowerBoard) is not redefined
  ComboBoard: inherits port name 'servoOut' more than once (JointController::servoOut, PowerBoard::servoOut)
  SensorBoardPcba: port bus (from ...::SensorBoard) is not redefined
  WrongBoard: port servoOut (from SpikeSystem::JointController) is redefined by
              WrongBoard::servoOut with SpikeEePorts::CanHeader, which does not specialize
              SpikeInterfaces::ServoIf
  SpikeEePorts::PinSignal: specializes SYS-IF-0902 but has no ID of its own
9 links, 5 findings
```

After the review the check follows the whole chain (`out/derive-ee2.log`, 11 links, 7 findings):
`JointControllerBoardB` (variant without own redefinitions) gets no finding, because
`JointControllerBoard` redefines the ports; `JointControllerBoardC` gets "port servoOut ... is
redefined by ...JointControllerBoardC::servoOut with SpikeEePorts::CanHeader, which does not
specialize SpikeInterfaces::ServoIf"; `OddBoard` gets "EE-PORT-0907 specializes SYS-EL-0901, but
there is no trace link from EE-PORT to SYS-EL". The link table is keyed by (domain kind, system
kind), the kind is the ID up to the last `-` (so `SYS-FEAT`, `SYS-CFG` work), and a pair without a
link is a finding, never skipped.

The same rule applied to port defs gives the signal-level check: `ServoHeader` must redefine
`pwm`, `vcc`, `gnd` with defs that specialize `ElSignal` (no finding, it does). `ComboBoard2`
(one port redefines both) gives no finding. Today's `model.to_needs` on the same JSON produces
no needs and one finding per element: "kind EE-PCBA cannot be generated from the model (only
SYS-EL, ...)".

Links are derived from direct system supers only; a variant without an ID (`JointControllerBoardB`)
has no link of its own (its parent board holds it). Elements with a system super but no ID
(`PinSignal`) are reported; decide warning or allowed.

## 3. Known pitfalls

- **File order** — confirmed. The Pilot reads the files one by one in the given order (gen
  sorts by name); `a_boards.sysml` importing `SpikeEePorts` from `b_ports.sysml` fails:
  `ERROR:Couldn't resolve reference to Namespace 'SpikeEePorts'. (2.sysml line : 6 ...)` and 12
  follow-up errors (`out/ee-nameorder.log`). Passing the files in dependency order, or concatenating them into one input
  (`ee2/concat.sysml`), works. Fallback: process the repo's own files as one set too, like the
  libraries (the line remapping of `remap_libset` already exists).
- **`top_packages` and nested packages** — confirmed, and worse than a wrong name: the regex
  `^\s*package` also matches the indented `package SpikeSystemDetail`. `gen.model` passes it to
  `si.export`, which returns the string `ERROR:Couldn't resolve reference to Element
  'SpikeSystemDetail'`; that string is spliced into the JSON array, `pilot.run` still says
  `ok=True`, and `json.loads` fails (`Expecting value: line 1 column 2105839`; `out/sys-toppackages.log`, the
spliced text in `out/sys-toppackages-json-tail.log`). Nested packages are
  exported with their top package anyway. For `compact` (library side) the extra names do no harm
  (it compares only the first segment of the qualified name).
- **`unit` name resolution** — refuted as a Pilot bug; it is SysML scoping. With a package-level
  `attribute unit` and a `requirement r1 :> servoRate` (stub with `attribute unit`), `unit` in
  `Probe` resolves to the package attribute, but inside `r1` to the inherited
  `SpikeStubs::servoRate::unit`. Inherited members hide outer names. Rule: in elements that
  specialize stubs or system defs, refer to outer elements by qualified name.
- Also seen: the raw export of two packages has duplicates (660 entries, 378 distinct); `compact`
  removes them. Issues in the domain files are reported as `2.sysml line : N` (index, not name;
  the `FILE` line before them says which file).

## 4. Cost

| Run | Pilot time |
|---|---|
| system model alone (2 files), `sysonly.log` | 12.7 s, rerun 14.2 s |
| domain model, system as library set, `ee.log` | 15.0 s, rerun 12.8 s |
| domain model + combo/variant tests (3 exports), `ee2.log` | 21.4 s (first run 15.1 s) |
| domain model, library set = SYSMOD, SYSMOD15288, PLEML, NeedStubs, all of robarm-syseng/model, spike system, `eefull.log` | 15.9 s |

Times vary by a few seconds between runs (machine load). JVM start and the standard library dominate; the system model as a library set adds about
1 s. A domain model of real size will cost what syseng costs today (P4-11: about 45 s).

## Verdicts

| Point | Verdict |
|---|---|
| Domain model refines the system model by specialization, Pilot with system as library set | works |
| Pilot finds missing or wrong redefinitions | works with this fallback: curatrix checks names and types (the Pilot does neither) |
| Double specialization (ME-1) | works with this fallback: clash = warning only; curatrix makes it a finding unless one port redefines all clashing ports |
| System IDs after `compact` | works (stubs keep `declaredShortName`) |
| `realizes` / `conforms` from the export | works with this fallback: ports and types of system elements come from syseng's committed `generated/model.json`, joined by qualified name |
| Domain files in name order | works with this fallback: process the repo's files as one set |
| `top_packages` | must be fixed before 5.15 (breaks the export silently) |

## Input for 5.14 (decisions)

- Conformance is a curatrix check, not a Pilot result: "every inherited system port has a
  redefinition somewhere in the chain between the domain def and the system def, and the most
  specific redefinition's def specializes the inherited port's def"; the same rule for port defs
  at signal level. A variant of a board does not repeat the redefinitions of its parent board. Redefined ports repeat the direction (`out port :>> pwm`).
- ME-1 multiple specialization is allowed; inherited name clashes must be resolved by one port
  that redefines all (`port :>> A::p, B::p : X;`), else error.
- Link holder: the domain def with an ID; by (domain kind, system kind): `EE-PCBA`/`ME-ASM` ->
  `SYS-EL` = `realizes`, `EE-PORT`/`ME-PORT` -> `SYS-IF` = `conforms`; any other pair is a finding. Decide what a domain def that specializes a system
  element without an ID of its own means (here `PinSignal :> ElSignal`): allowed for helper defs
  below the port level, or a warning.
- The domain repo reads the upstream model twice: as `.sysml` library set (Pilot) and as the
  upstream's committed `generated/model.json` (checks without Java). Both come from the same
  west pin.
- Naming rule: inside elements that specialize stubs or system defs, outer names are referred to
  by qualified name (inherited members hide them).

## Input for 5.15 (implementation, curatrix)

- `model.py: top_packages`: count brace depth (or only column-0 `package`) so nested packages are
  not returned; keep a second helper for "all package names" if `compact` needs it.
- `pilot.py: script`: treat an export result that starts with `ERROR:` as an error (count it in
  `errs`, print it) instead of writing it into the JSON; optionally print WARNING lines into a
  separate count so `gen` can report the duplicate-name warning.
- `pilot.py: script/run`: an option to process the repo's own `files` as one set (like
  `libraries`), with `remap_libset` generalised to that set; or `gen.model_files` orders files by
  their `import`s. One set is simpler.
- `model.py`: `MODEL_KINDS` per repo (from `needs_config.toml`: `EE-PCBA`, `EE-PORT`, `ME-ASM`,
  `ME-PORT`), and a new step in `to_needs` that follows `Subclassification.superclassifier` to
  stubs with IDs and adds `realizes` / `conforms` by (source kind, target kind); kind from the ID
  split at the last `-`; an unmapped pair is a finding, not skipped. `LINK_BY_KINDS`
  gets `(EE-PCBA, SYS-EL): realizes`, `(EE-PORT, SYS-IF): conforms`, and the ME pairs.
- New `model.py: conformance(domain: Model, upstream: Model) -> findings` (the logic of
  `build/spike-model/derive.py`: whole super chain, most specific redefinition wins), with a test
  for a variant def, called by `gen.model` /
  `gen.model_needs_from_json`, with a new check ID in `checks.yaml` (model section: `upstream:
  "{ws}/robarm-syseng/generated/model.json"` in robarm-ee's `checks.yaml`; curatrix itself has no
  default for it, no robarm names in xdmod, task 5.6).
- `gen.py: model_files`: the domain repo's `checks.yaml` lists the syseng model files (and
  NeedStubs, SYSMOD, PLEML) as `libraries`; nothing else changes there.
- Alternative to the join (decide in 5.15): keep `type` and the `Subclassification` of library
  stubs in `compact`. That makes the domain JSON self-contained but bigger and couples it to
  syseng internals; the join is enough.
