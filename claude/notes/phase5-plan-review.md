# Review of the Phase 5 plan (domain structure, interaction and tooling)

Reviewer: Fable agent, 2026-11-17. Read-only review; nothing was changed in any repo.

Short names used below:

- **plan** = `.worktrees/docs/plan-phase5-domains/xdmod/claude/plan.md`
- **exp** = `.worktrees/docs/plan-phase5-domains/xdmod/claude/notes/phase5-expectations.md`
- **help** = `build/review-phase5-plan/kicad-cli-help.txt` (the `--help` text of kicad-cli 10.0.8 on
  this machine, captured for this review)

## Verdict

The direction is right, and the owner's decisions fit together better than I expected: one pattern
for EE and ME (model element 1:1 with a CAD entry point, ports named in the CAD file, one document
per board or assembly). The plan is not ready to start as written, for three reasons.

1. **Size and order.** Phase 5 has 29 tasks; phases 6 and 7 together have about 20. Twenty-one of
   the 29 build tooling (about 20 new checks, 12 directives, 6 commands, 4 need kinds, one new
   repo, two new tools) before any real board or assembly exists. The canary, which was the first
   item of the agreed "Phase 5.0", is now task 5.27 of 29. This repeats the Phase 4 pattern that
   P4-1 criticised: tooling proven only on empty input.
2. **Three tool assumptions are wrong or unproven for the installed versions**, and tasks are
   written on top of them: `kicad-cli jobset run` cannot set a version variable or a variant
   (P5-3); FreeCAD 1.1.4 has no suppressed state for parts in an assembly (P5-5); the exploded
   view and StepUp are GUI code (P5-5, P5-6).
3. **The tooling for SW and integration agreed in the Phase 4 response has no task** (P5-9),
   although the canary needs it.

None of this needs an owner decision to be reversed. It needs a different order, a few explicit
fallbacks, and written limits on what "done" means per task.

What I verified, and how:

| Claim | Result | How |
|---|---|---|
| `kicad-cli jobset run` takes a variable or a variant | **No.** Only `--stop-on-error`, `--file`, `--output` | run locally, help:1-13; KiCad 10 manual, <https://docs.kicad.org/10.0/en/kicad/kicad.html> (jobsets: no way to set a variable or variant per job) |
| Single exports take `--define-var` and `--variant` | Yes: render, pdf, gerbers, step, bom, netlist, pos take `--variant`; render, pdf, gerbers, step, drc, erc take `-D` | help:15-29, 92-105, 122-135, 189-191, 209-224, 236-253, 276-308 |
| Orthographic rendering | Yes, it is the default (`--perspective` switches it off); `--side top/bottom/left/right/front/back` | help:32-38 |
| ERC/DRC JSON with exclusions | `--format json`, `--severity-exclusions` exist; no `--variant` on ERC/DRC. Whether the comment is in the JSON: not verified | help:48-91 |
| Native stackup or design-rule export | None. Only `pcb export stats` (board statistics) | subcommand list, help:137-168 |
| Jobs can run a shell command | Yes: job type "Execute Command", run in the platform shell | KiCad 10 manual (URL above) |
| Script writes a spreadsheet cell, small diff, headless recompute | Yes in one document: a 2-line diff in `Document.xml` of 1477 lines; the bound length followed | FreeCADCmd 1.1.4 probe under `curatrix run --use freecad`; files in `build/review-phase5-plan/probe/` |
| Suppressed state for parts per variant | **No.** `Suppressed` exists only on PartDesign features (e.g. `Pad`). `App::Link`, `App::Part`, `PartDesign::Body`, `Part::Feature`, `Assembly::AssemblyObject`, `Assembly::AssemblyLink` have none | same probe |
| Exploded view headless | **Unlikely as planned.** `CommandCreateView` fails to import in FreeCADCmd (`QtCore` not defined). The wiki says exploded positions show only while editing and in TechDraw views | same probe; <https://wiki.freecad.org/Assembly_CreateView/en> |
| LCS with a `Port` property; collision by boolean common | Works headless | same probe |
| Master sketch across documents, configuration tables | **Not verified.** My cross-document test was wrong (bad document name), so it proves nothing | — |
| KiCad StepUp with FreeCAD 1.1 and KiCad 10 | README lists KiCad up to 10.x but FreeCAD only up to 1.0; no releases (pin by commit); AGPL-3.0; a GUI workbench. Push of keep-outs and holes is not described | <https://github.com/easyw/kicadStepUpMod> |
| WireViz | 0.4.1 is the latest version, GPL-3.0. Upstream activity not verified | <https://tracker.debian.org/pkg/wireviz>, <https://packages.guix.gnu.org/packages/wireviz/0.4.1> |

## Findings

### P5-1 The canary is last; it should be the spine of the phase — blocking

Evidence: plan:190-191 (5.27 under "Proof", after all tooling); `build/review-phase4/response.md`
"Proposed Phase 5.0" item 1 (the canary was 5.0a, first); plan:150-152 ("By the end of this phase
the checks bite"; D140 ends with 5.1–5.8, which now contain no canary).

Tasks 5.15–5.26 will be written and tested against hand-made fixtures, because no KiCad or FreeCAD
file exists in robarm-ee or robarm-me until 5.27. That is finding P4-1 and P4-13 again. The
"checks that bite" block also ends (and with it D140) without the one task that proves the checks
bite.

Suggestion: split 5.27 into steps and build each tool against the step it needs.

- **C0** (right after 5.2, before any EE/ME tooling): the chain from the Phase 4 response as it
  was agreed, with one KiCad sheet and one FreeCAD part saved by the real tools, plus the
  planted-error fixture for the rules that exist today. D140 ends when C0 and 5.1–5.7 are done.
- **C1** EE: the canary board grows with 5.15 → 5.17 → 5.18 → 5.16 → 5.21. A tooling task is done
  when the canary uses it, not before.
- **C2** ME: the same for 5.22 → 5.23 → 5.25 → 5.24 → 5.26.
- **C3** co-design and library (5.12, 5.19), last.

### P5-2 Decisions are frozen before the spikes that test them — blocking

Evidence: plan:165 (5.9 writes the `XD-ADR`s and changes `needs_config.toml` and four framework
pages) comes before plan:166-168 (spikes 5.10–5.12). There is **no spike for the domain sub-model**
(5.13), which the owner called "exactly at the heart of what we try to realize with xdmod"
(exp:339-340).

What the sub-model needs and does not have today:

- `model.py:41` generates needs only for `SYS-*` kinds; `LINK_BY_KINDS` (model.py:43-49) has no
  entry from specialization; `to_needs` (model.py:299-412) reads satisfy, dependency and
  allocation, not `superclassifier`.
- exp:357-359 says inherited ports "must be redefined, so the Pilot checks names and types
  (conformance at signal level for free)". SysML v2 does not force a redefinition: a
  specialization simply inherits the ports. The Pilot checks a redefinition only if someone writes
  one. So conformance is **not** free; curatrix must check "every inherited port is redefined by a
  port whose def specializes the interface def".
- The Pilot driver loads `libraries` as one set and then each file (pilot.py:79-110). The syseng
  model can be given to the EE model as a library set, which is cheap. What then happens to
  syseng IDs after `compact` strips library packages (gen.py:87) is untested.
- ME-1 answer 3 wants one ME element to specialize several system blocks (exp:583-585). Inherited
  feature names can then clash.

Suggestion: add a **model spike (new 5.9a)** in front of 5.9: two tiny `.sysml` files in two
folders, `part def Board :> JointController`, a port def that specializes an interface def, one
missing redefinition, one multiple specialization; run the Pilot with the upstream as library set;
derive `realizes` and `conforms` from the export. Write the `XD-ADR`s as *proposed* first, and
accept them after spikes 5.9a–5.12 report. One day of work; it protects everything after it.

### P5-3 KiCad output jobs cannot carry the version or the variant — blocking for 5.16

Evidence: plan:166 and 176; exp:112, 136-138 ("to check for `jobset run`"); help:1-13.

The owner asked for native output jobs (EE-3) and for a version pinned at generation time (EE-3),
and for variants (EE-2/EE-8). `jobset run` supports neither on the command line, and the manual
describes no per-job variable or variant. The single `kicad-cli` commands support both.

The decisions conflict in the tool, so the plan must say which way it resolves:

- A. Keep the jobset; curatrix copies the project into `build/robarm-ee/cam/<project>/work/`,
  writes the version into the copy's `.kicad_pro` text variables, and runs the jobset there.
  Variants: one jobset run per variant only if KiCad 10 lets a job name a variant (spike).
- B. curatrix calls the single exports with `-D` and `--variant`; the jobset stays as the file a
  human uses in the GUI.

I suggest A for the version and B as the fallback for variants, decided by spike 5.10 with a
written go/no-go. Either way, run on a copy: it also keeps KiCad's side files (`.kicad_prl`,
caches, backups) out of the repo (rule 3).

Two more points for 5.10/5.16:

- A jobset may contain "Execute Command" jobs, that is, shell commands from a repo file. Add a
  plain-Python check that forbids this job type (and "Copy Files" outside the output folder).
- The stackup "picture" (exp:114) has no native export. Say in 5.16 that iteration 1 delivers a
  table (already the plan for the docs, plan:181), not a picture.

### P5-4 Acceptance by git history has three holes — should-fix

Evidence: plan:178, 187; exp:444-455, 688-690; CLAUDE.md rule 8 (agents commit under the owner's
identity).

1. **"No agent trailer = human" fails open.** An agent commit that forgets the trailer becomes a
   human acceptance. CK-H4 cannot catch it, because it has the same problem (it must first know
   which commits are agent commits). A positive marker fails closed: a human acceptance is a
   commit with an explicit trailer such as `Accepted-by: <name>`, which agents are forbidden to
   write, on a commit that touches only acceptance entries.
2. **KiCad rule severities are an unguarded way around the rule.** "Warnings are listed only"
   (exp:446). The severity of every ERC/DRC rule is a setting in the `.kicad_pro`. Anyone, also an
   agent, can turn an error into a warning or "ignore", and the check passes. Add a plain-Python
   check: the project's severities equal the template from `curatrix new pcba`; any difference is
   a finding that needs acceptance.
3. **The whole-board acceptance of unrouted nets has no home in KiCad.** KiCad exclusions are per
   violation and carry positions and item IDs; an unrouted board has one per unconnected pad pair,
   and they change with every placement move. "One human-committed entry" (plan:178) therefore
   needs a file of ours. Use the same file for EE as for ME: `pcba/<name>/accepted.yaml` beside
   `assemblies/<name>/accepted.yaml`, same format, same check code. KiCad's own exclusions stay
   for single findings.

Also say what a moved part does: a KiCad exclusion's text changes when its items move, so the
acceptance is lost. That is defensible, but it should be a stated rule, not a surprise.

### P5-5 FreeCAD: suppression, exploded view and renderings will not work as written — should-fix

Evidence: plan:167, 186, 188; exp:619-621, 706-708; probe results in the verdict table;
`freecad-storage.md:44` (full-page export already needs the GUI binary offscreen).

- **Part presence per variant** cannot use a suppressed state on parts or links in 1.1.4. A
  mechanism that exists: a `Configs` property on the link (the trace field already exists,
  `cad.py:32`), read by curatrix; export, BOM, collision check and usage count filter by it.
  FreeCAD itself then shows the 150 % assembly. The spike should confirm this and nothing more.
- **Exploded view** is GUI code and shows only in edit mode or through TechDraw. Budget it as
  "TechDraw view of an exploded view, exported offscreen", with a stop rule (P5-13). It is the
  best single cut candidate in ME.
- **Renderings** (front, top, side, 3D) need a 3D viewer; with `QT_QPA_PLATFORM=offscreen` OpenGL
  output is often empty. Fallback that is known to work headless: TechDraw or `Draft`
  projections as SVG, or GLB plus a note. Put the fallback in 5.24.
- The **master sketch across documents** and **configuration tables** remain the two real unknowns
  of 5.11. They decide the shape of 5.22–5.24, so 5.11 must finish before those start.

### P5-6 StepUp carries three tasks, but it is a GUI workbench with unclear version support — should-fix

Evidence: plan:167, 168, 179; exp:256-257, 628-630; <https://github.com/easyw/kicadStepUpMod>
(FreeCAD "0.19 … 1.0", no releases, AGPL-3.0); `xdmod/tools.yaml` last lines (FreeCADCmd only for
roles me, integration, full; kicad-cli only for ee, integration, full).

Consequences of the owner's decisions that the plan does not state:

- 5.19 says the **EE agent** exports the board through StepUp. An agent has no GUI. Unless the
  spike shows that StepUp's functions run from a script, 5.19 is a human-only step. Fallback that
  is fully scriptable and verified to exist: `kicad-cli pcb export step` (takes `--variant`, `-D`,
  `--no-dnp`; help:236-253) plus a FreeCAD headless import that adds the `EE-PCBA` ID and version
  properties. I suggest: StepUp for the interactive push (ME → KiCad), the STEP path for the
  automated export into the library, decided in 5.11.
- The **EE role needs FreeCAD** and the **ME role needs KiCad files and libraries**. Roles, west
  groups, `tools.yaml` and `doctor` must change. No task says so.
- StepUp writes `.kicad_pcb` itself. Limit the push in iteration 1 to the board outline and
  mounting holes, and require that the pushed file is opened and saved by KiCad 10 (or passes
  `kicad-cli pcb drc`) before commit, so the committed file is always KiCad's own output.
- AGPL as a tool is fine, but record the licence check, as was done for the FreeCAD library.

### P5-7 The new repo `robarm-freecad-pcba` is listed as an admin action only — should-fix

Evidence: plan:162 (created in 5.8), plan:179 (used in 5.19).

An eighth repo needs what 4.9 gave the others: west project and group for the ee and me roles,
`checks.yaml` with `expect:`, CI, ruleset, `claude/CLAUDE.md`, licence, a place in the bump bot and
in the full set. Also undefined: file format and size. One `.FCStd` per board version with
component models can be tens of MB, and git keeps every version.

Suggestion: a task "skeleton of robarm-freecad-pcba" next to 5.19; a size limit per file (for
example 5 MB: board body plus connectors and parts above a height threshold, no tracks); a check
that every file names an existing board tag. Also move its creation out of 5.8, so that D140's end
does not wait for a decision that belongs to 5.19.

### P5-8 Two generators will emit the same need — should-fix

Evidence: exp:363-365 ("The EE model element owns `EE-PCBA-nnnn`; the KiCad project's TraceID must
equal it"); `cad.py:14, 149` (the PCBA need is generated today from the `.kicad_pro` text
variables into `cad-needs.json`); plan:171 ("model needs with `realizes` / `conforms` derived").

After 5.13 the same `EE-PCBA` ID comes from `model-needs.json` and from `cad-needs.json`;
sphinx-needs rejects duplicate IDs. The same holds for `ME-ASM`. Decide in 5.9: the model emits
the need; the CAD file only carries the ID as a reference (and its `Realizes`, `Conforms` fields
on the project go away, since they are derived). CK-D4 changes with it. `EE-CMP` and `ME-PART`
stay CAD-owned.

### P5-9 The SW and integration tooling agreed after Phase 4 has no task — blocking for the canary

Evidence: `response.md`, row P4-2 ("keep CK-F2, SW-IMPL/SW-TC extraction, test results in docs and
a minimal trace report … tooling tasks … each next to the content task that needs it"); plan:211-213
(6.11–6.13 name no tooling); plan:191 (the canary needs "one SW-DD with code → one test case → one
HIL result, through the real registries").

The owner has no further expectations for SW and integration (exp:28-29), but the EE decisions
create work there:

- CK-F2 now compares the devicetree with the **EE model**, not syseng (exp:400-401). 5.13 adds
  the upstream registry and the `eeSw` view; nobody builds CK-F2. 5.14 calls board variants only
  an "input to CK-F2".
- SW-IMPL and SW-TC extraction, test results in the docs, the minimal trace report: no task.
- The vertical bar is the prototype (Nucleo). A Zephyr board for the product board, with
  variants, is not needed in iteration 1. Say that the board-variant ↔ Zephyr check is exercised
  only on the canary by name, or defer it.

Suggestion: one short block "SW and integration tooling" (CK-F2 against the EE model, SW-IMPL and
SW-TC extraction, test results in docs, minimal trace report), sized for the canary only.

### P5-10 Variant picking across levels sits on the wrong side of the trace rule — should-fix

Evidence: plan:172; exp:709-712; CLAUDE.md rule 5; exp:350-352 (domain models import syseng, never
the reverse).

"Each system configuration picks one domain variant per usage." If that table lives in syseng,
syseng names EE and ME variant names it cannot import or check; the check can only run in the full
set, and a renamed board variant breaks syseng from downstream. The decision can be kept without
this: the **domain variant names the system configurations and usages it serves** (the `Configs`
field exists for exactly this), and the table "configuration → variant per usage" is computed,
like every backlink. The check "exactly one variant per usage and configuration" then runs in the
domain repo against the published syseng needs.

Also unclear: the usages live in syseng (`shoulder : JointController`), but ME-2 counts usages "in
the ME model" (exp:596-597). The ME model must then repeat the decomposition. Say which model owns
the instance count, or the two will drift.

### P5-11 Local-only outputs leave the published site and the reviewer blind — should-fix

Evidence: plan:181, 188 ("local, placeholder in CI"); exp:201-203, 443; D56; `response.md` P4-14.

These are owner decisions and I do not question them. Their consequences are not in the plan:

- The Pages site, also for a baseline, shows placeholders for schematic, renderings, ERC/DRC
  findings, drawings, mass, exploded view. The directive only warns when local output is missing
  or old (exp:209-211).
- ERC, DRC, recompute and collision checks never run in CI, so a green PR says nothing about
  them. With rulesets binding everyone, the required checks are still the non-CAD ones.

Suggestions that stay inside the decisions:

- `/review-pr` for robarm-ee and robarm-me re-runs `curatrix check --stage local` with CAD content
  and posts the result table in the review. This is the only second run these checks get.
- At the baseline stage, missing or stale local output is an error, not a warning.
- The owner reviews EE and ME PRs from a local docs build; say so in the how-to (5.29).

### P5-12 Open questions from the expectations that no task picks up — should-fix

- `proto/` projects: which model element do they correspond to (exp:63-66, never answered)? 5.15
  applies the 1:1 rule to `proto/*` too (plan:175). The Nucleo and the breakout modules are bought
  boards: are they PCBA defs, external parts, or outside the rule?
- Harness ends that are not our boards. The joint's cables go to a servo and a pot (plan:207-208).
  "Both ends name their `EE-PORT`; CK-F1 checks pin to pin against both boards" (plan:180) cannot
  hold for them. Bought parts need port defs in the EE model, or the rule needs an "external end".
- Who may create board, assembly and harness tags (exp:161-162: "decided with the release tasks";
  there is no such task)? The library accepts only tagged boards, so the canary needs a tag before
  ME can link a board. Also: does a tag on a board without routing make sense to the owner?
- Can SW add Zephyr board variants of its own (exp:106-107)?
- Name of the harness need kind (plan:165: "and one for harnesses").
- Who authors the canary's CAD files? The research says agents cannot reliably create a readable
  schematic from scratch (`xdmod/claude/research/kicad.md:153-157`), and FreeCAD authoring was
  verified only for a simple part (`freecad.md:38`). A layout with placement and a master-sketch
  assembly are harder. If the owner draws them, that is owner time the plan should show.
- New check IDs. 5.9 says "CK-F1 to CK-F4" (plan:165), but CK-F5 exists (`checks.md:76`) and
  Phase 5 adds about 20 rules without IDs, stages or severities.

### P5-13 "Every rule fails on a planted error" cannot be met in CI for tool-backed rules — should-fix

Evidence: plan:150-151, 191; D56.

The fixture workspace runs in xdmod CI, which has no KiCad or FreeCAD. ERC, DRC, recompute,
collision, StepUp and CAM rules cannot fail there. Split the exit criterion: plain-Python rules
fail in the CI fixture; tool-backed rules fail in a local fixture run whose result (rule, tool
version, date) is recorded in the Phase 5 review. Otherwise the phase cannot be closed honestly.

### P5-14 Review and merge load — should-fix

Evidence: plan:160 ("one SYSMOD step or one tool feature per PR"); D126; plan:152 (D140 ends after
5.1–5.8).

By the plan's own rule, 5.9–5.29 are roughly 60 to 90 PRs over eight repos, each with an agent
review and then the owner's review, with no agent merge after 5.8. The owner is the bottleneck,
and most EE/ME PRs cannot be judged from the PR page (P5-11). Suggestion: the owner reviews per
block (model, EE, ME, co-design) against the canary, with a demo script per block; agent reviews
stay per PR. Decide this now, since it is the same question as D140.

### P5-15 Two readers for one KiCad format — nice-to-have

Evidence: plan:181; exp:463-467 ("cross-check … once, in a test").

Assembly variants are new in KiCad 10. A plain-Python BOM reader with variants is a second
implementation of a young format. Keep the cross-check against `kicad-cli sch export bom
--variant` (help:92-105) as a permanent local check on every board, not a one-time test. The same
for the connector extraction against the XML netlist.

### P5-16 The canary and the joint overlap — nice-to-have

Evidence: plan:191 (canary board with connector, jumper, shunt, two variants; "stay after Phase 7,
marked as canary"); plan:209 (the joint's product board); `response.md` P4-1 (owner agreed: canary
in the robarm repos, "doubles as the first joint").

5.27 now reads like a separate small board. Then robarm keeps a second board, assembly and harness
forever, in the BOMs, the trace report and the coverage numbers. Decide: the canary is the seed of
the joint (6.9 and 6.10 extend it), or it is separate and every report filters `canary`.

## What to constrain

Order (replaces the order of plan:154-193):

1. 5.1, 5.2, 5.4, 5.5, 5.7 and canary step C0 → D140 ends here.
2. Spikes, in parallel, each at most two days and with a written go/no-go and fallback: model
   (new), KiCad (5.10), FreeCAD (5.11). Then 5.9 as accepted decisions. 5.12 after 5.11.
3. EE block on the canary, then ME block on the canary, then co-design and the library.
4. 5.3, 5.6, 5.8 and the SW/INT block run beside 2 and 3.

Limits per area:

| Area | Limit for iteration 1 |
|---|---|
| Phase size | A tooling task is done when the canary uses it and its planted error fails. No task is closed on unit tests alone. |
| Spikes | Time-boxed. Each ends with "works / works with this fallback / cut". No tooling task starts before its spike reports. |
| KiCad output | One shared jobset template in xdmod, copied by `curatrix new pcba`; no "Execute Command" jobs; always run on a copy under `build/`; stackup as a table. Render: one size, quality `basic`, inside the existing 2G / 5m limit. |
| Variants | At most two variants per board and per assembly. Presence by `Configs`, not by a suppressed state. Zephyr board-variant check by name only. |
| Acceptance | One `accepted.yaml` format for EE and ME; positive human marker; KiCad severities pinned to the template. |
| Co-design | The `SYS-IF` budget is a box (width, depth, height above and below the board), a hole list (x, y, diameter) and connector positions. No free outline in SysML. StepUp pushes outline and holes only; nothing back from EE in iteration 1. One written scenario, run once on the canary. |
| Library repo | Tagged boards only, a size cap per file, STEP path as the scripted route. |
| FreeCAD | Master sketch only in the top-level assembly, with at most ten driving parameters. Collision check only between direct children of one assembly, inside the 4G / 10m limit. Exploded view: one day; if it does not export offscreen, it moves to iteration 2. |
| Harness | One harness in iteration 1. WireViz diagram and BOM only. Length is one number from the model; no route geometry. |
| Documents | One directive set per document type; a section with no data prints one fixed sentence. No per-board layout options. |
| Domain models | Board, connector ports and pin maps (EE); assembly, sub-assemblies and ports (ME). No circuit block diagrams inside a board in iteration 1. |
| Checks | Every new rule gets an ID, a stage and a severity in `checks.md` before its code; new rules start as warnings until they ran on the canary. |
| Pilot time | Measure after 5.13 (three models). If one local check of robarm-ee passes five minutes, 5.28 is no longer optional. |

Candidates to defer to iteration 2 without losing the owner's goals: exploded view; GLB; mass and
center of gravity in the document; version embossing on printed parts (keep the `VersionFace` rule
as a warning); the harness length/route co-design (keep the board space budget); EE pushing back
through StepUp; `curatrix new asm` (keep `new pcba`, copy the pattern later); unused-variant
warnings.

Exit criteria I would write under the Phase 5 heading:

1. The canary chain is green locally with CAD content and in CI without it.
2. Every rule in `checks.md` has a planted error that fails: plain-Python rules in CI, tool-backed
   rules in a recorded local run.
3. `curatrix cam` ran for the canary board (both variants) and the canary assembly, from a tag and
   from a dirty tree, and the preview marking is visible in both.
4. One co-design change went through three repos on one branch name.
5. The author loop is measured, and the numbers are in the review.
6. A list of what moved to iteration 2, agreed by the owner.

## Done well

- The expectations file records question, answer and consequence for every point. It made this
  review possible, and it shows where a decision changes an older rule (D36, D43) instead of
  hiding it.
- One pattern for both domains: model element 1:1 with a CAD entry point, definition vs usage for
  instances, ports named inside the CAD file, one document per board or assembly.
- The split by "who can make the output" (plain Python everywhere, tool output local) is
  consistent across EE-4, EE-6, EE-7, EE-8 and ME-4, and honest about D56.
- Dedicated spikes for KiCad, FreeCAD and co-design, with "to verify" marked in the notes. The
  marked items are the right ones; this review only confirms that several of them fail.
- Per-project tags with `git describe --match`, preview marking, and "only tagged versions enter
  the library" give a clean version story.
- The two exceptions to the peer rule keep the graph acyclic (syseng → EE → SW; ME → EE only
  inside a co-design change) and get their own decisions and a pair view.
- The model driving the FreeCAD spreadsheet, with CK-F3 kept as the check, is sound: my probe
  shows a script cell write gives a two-line diff and recomputes headless.
- 5.1–5.8 map one to one to the agreed Phase 4 response, and the iteration-2 backlog was updated
  with what Phase 5 defers.
