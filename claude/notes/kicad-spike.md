# KiCad 10 spike (plan task 5.12)

Date: 2026-11-17. KiCad 10.0.8 (`/usr/bin/kicad-cli`, pcbnew Python 10.0.8). Time used: about 1.5 h.
Work dir: `build/spike-kicad/` (not committed). Source read at tag `10.0.8` of
`gitlab.com/kicad/code/kicad` (sparse clone in `build/spike-kicad/src/kicad`).

## 0. Summary

| Question | Verdict |
|---|---|
| 1. Jobset with version, EE-3 outputs | **Works.** The version written into the copy's `.kicad_pro` reaches schematic frames, PCB frames, silkscreen and the Gerber header. Jobs **can** name a variant (P5-3 was wrong on this). Stackup and design rules: plain Python (fallback, as planned) |
| 2. Assembly variants | **Works.** DNP and any field value can differ per variant, stored in `.kicad_sch` and `.kicad_pcb`; BOM, position, netlist, plots per variant. Render per variant not provable without 3D models |
| 3. ERC/DRC JSON with exclusions | **Works with this fallback**: exclusions and their comments are in the JSON. But an exclusion that no longer matches shows as an excluded *phantom* entry in ERC, and the exclusion key is an opaque string with positions. Use our `accepted.yaml` for anything not single and stable (P5-4 confirmed) |
| 4. Connector extraction from the XML netlist | **Works.** Pin number, pin name, net, all hidden fields (`Port`, `TraceID`), and variant overrides |
| 5. MCP servers | **Cut for iteration 1.** Several exist and are active; none is needed for 5.17–5.21, and all assume user-global paths |
| Isolation of the user's config | **Works with extra variables**: `KICAD_CONFIG_HOME` alone is not enough; KiCad also writes a cache dir and a documents dir in `$HOME` (see §6; fixed in curatrix by xdmod#41) |

Corrections to the plan review and the plan:

- P5-3: a jobset job **can** name a variant (10.0.8). Fallback B (single exports per variant) is not needed;
  plan 5.12/5.20 can drop "single exports per variant where needed". The version still goes through the
  copy's `.kicad_pro` (option A).
- P5-3, stackup: confirmed, no native export; a table from plain Python.
- P5-4.2 (severities as a bypass) and P5-4.3 (unrouted nets need our own `accepted.yaml`): confirmed.
- P5-15: both cross-checks (BOM per variant, XML netlist) are workable.
- New: `libs/kicad/packages3D` is missing (a `doctor` item); `jobset run` needs a job-count check (§2.4).
- New: the title-block `Rev` field cuts off a long version (§2.1).

## 1. Setup

All KiCad runs went through two wrappers in `build/spike-kicad/` (`kc.sh` for `kicad-cli`, `kpy.sh` for
system `python3 -I` with `pcbnew`). The command they run:

```
env -u XDG_CONFIG_HOME -u XDG_CACHE_HOME -u XDG_DATA_HOME -u XDG_STATE_HOME \
  HOME=$B/fakehome2 \
  KICAD_CONFIG_HOME=$R/.xdmod/kicad KICAD_CACHE_HOME=$B/xd-cache KICAD_DOCUMENTS_HOME=$B/xd-docs \
  KICAD10_SYMBOL_DIR=$R/libs/kicad/symbols KICAD10_FOOTPRINT_DIR=$R/libs/kicad/footprints \
  KICAD10_3DMODEL_DIR=$R/libs/kicad/packages3D KICAD10_TEMPLATE_DIR=$R/libs/kicad/templates \
  TMPDIR=$B/tmp \
  .venv/bin/curatrix run --use kicad-cli -- kicad-cli "$@"
```

(`R` = workspace root, `B` = `build/spike-kicad`.) `HOME` points to an empty folder as a tripwire:
it stayed empty for the whole spike.

The canary of `feat/canary-c0` has one resistor and an empty board, too little for the questions. On
the copy (`build/spike-kicad/canary/`) two plain-Python scripts (`gen/gen_sch.py`, `gen/gen_pcb.py`)
made a test design without the GUI:

- J1 `Conn_01x04` (fields `Port=servoOut`, `TraceID`, `Manufacturer`, `MPN`), R1 10k, R2 0R link,
  JP1 `SolderJumper_2_Open`, J2 `Conn_01x03` as a shunt header (field `Setting=1-2`); nets by local labels
- variants `addr40` (= base: JP1 and R2 DNP, shunt 1-2) and `addr41` (JP1 and R2 fitted, R1 = 4k7,
  shunt 2-3)
- title block `rev "${XD_VERSION}"` and `comment 2 "Version ${XD_VERSION}"`, a schematic text with
  `${XD_VERSION}`, a silkscreen text `${XD_VERSION}` on `F.SilkS`; text variable
  `XD_VERSION = "unversioned"` in `.kicad_pro`
- the board: footprints placed with `pcbnew` Python (linked to symbols by `SetPath("/<symbol uuid>")`),
  nets assigned to pads, outline on `Edge.Cuts`, **no tracks**

Side note: `gen_pcb.py` shows that `pcbnew` Python can build a board from a netlist headless, including
variants (`BOARD.AddVariant`, `FOOTPRINT.AddVariant(...).SetDNP/SetFieldValue`). KiCad 10 has no
`kicad-cli` "update PCB from schematic".

## 2. Design output (EE-3, P5-3)

### 2.1 Version through the jobset

curatrix writes the version into the copy's `.kicad_pro` (`text_variables.XD_VERSION =
"canary-board/v0.0.0-1-gabc1234-preview"`) and runs the jobset there:

```
kc.sh jobset run -f build/spike-kicad/canary/canary-board.kicad_jobset build/spike-kicad/canary/canary-board.kicad_pro
...  17 jobs succeeded, 1 job failed      (the failure is the DRC job, see 2.4)
```

Where the version shows (output in `build/spike-kicad/out-jobset/`):

| Output | Evidence |
|---|---|
| Schematic PDF | `pdftotext -layout`: `Rev: canary-board/v0.0.0-1-` (**cut off**, see below), `Version canary-board/v0.0.0-1-gabc1234-preview`, `Board version: canary-board/v0.0.0-1-gabc1234-preview` |
| Schematic SVG | 6 occurrences of the version string |
| PCB silkscreen | SVG of `F.SilkS`: 2 occurrences; visible in the top rendering |
| PCB PDF (with frame) | silkscreen text `canary-board/v0.0.0-1-gabc1234-preview`; frame `Rev: canary-board/v0.0.0-1` (**cut off**) |
| Gerber | header `%TF.ProjectId,canary-board,<uuid>,canary-board/v0.0.0-1-gabc1234-preview*%` in every layer |

**The title-block `Rev` field cuts off the version** in both PDFs: `Rev: canary-board/v0.0.0-1-`. The hash
and the `-preview` mark are lost, so a preview build can look like a release in the Rev box. Only the
comment line and free texts show the full string. Input for 5.17/5.20: put the full version into a
title-block comment line (`comment 2 "Version ${XD_VERSION}"`, which fits) and let the 5.20 check look
there; keep `rev` empty or short (for example only the `vX.Y.Z` part, a second variable
`XD_REV`), or widen the Rev field in a workspace drawing sheet (`.kicad_wks`) of the template.

Important detail: `pcbnew` also writes the project text variables into the `.kicad_pcb` as board
properties (`(property "XD_VERSION" "unversioned")`). The `.kicad_pro` value wins: the silkscreen showed
the version from `.kicad_pro`, not "unversioned". So writing only the `.kicad_pro` is enough.

Single exports with `-D`: `-D XD_VERSION=canary-board/v9.9.9-D-override` overrides the `.kicad_pro`
value in `sch export pdf`, `pcb export svg`, `pcb export gerbers` (checked the same way). Jobs have no
per-job variable: `JOB::m_varOverrides` exists in the code but is not read from the jobset JSON. So:
version in `.kicad_pro` for the jobset (option A of P5-3), `-D` only for single exports.

### 2.2 Jobs and variants

**A job can name a variant.** In 10.0.8 these job types read a variant from the jobset JSON
(source `common/jobs/*.cpp`): `pcb_export_gerbers`/`pdf`/`svg`/`dxf` (`"variant"`), `pcb_export_pos`
(`"variant"`), `pcb_export_3d` (`"variant"`), `pcb_render` (`"variant"`), `pcb_export_ipc2581`, `pcb_export_odb`,
`sch_export_plot_*` (`"variant_name"`, `"variant_names"`), `sch_export_bom` and `sch_export_netlist`
(`"variant_names"`). Run in the spike: `bom-addr41` (`"variant_names": ["addr41"]`), `pos-addr41`
(`"variant": "addr41"`) and `render-top-addr41` (`"variant": "addr41"`) all ran, and BOM and position
differ as expected (§3). ERC and DRC take no variant.

So P5-3 "jobs cannot carry the variant" is wrong for 10.0.8: the shared jobset can hold one job per
output and variant. Nothing in KiCad ties these jobs to `schematic.variants`: a variant added to the
`.kicad_pro` but not to the jobset silently gets no outputs, and a job naming a removed variant was not
tested. Input: `curatrix new pcba` (5.17) writes one job per variant and variant-dependent output, and a
5.20 plain-Python check compares the variant names in the jobs with `schematic.variants` (and the
`.kicad_pcb` `(variants ...)` list).

### 2.3 Which EE-3 outputs work natively

| Output | Job type / command | Result |
|---|---|---|
| Gerber + drill | `pcb_export_gerbers` (`"layers": ["F.Cu",...]`), `pcb_export_drill` | works; job file `.gbrjob` too |
| Pick-and-place | `pcb_export_pos` (csv, mm, both sides, single file) | works; the file is named `pos-all-pos.csv` (KiCad appends `-all-pos`) |
| Netlist | `sch_export_netlist` (`"format": "xml"`) | works |
| STEP | `pcb_export_3d` (`"format": "step"`) | works, but **no part models**: `libs/kicad/packages3D` does not exist in the workspace (`File not found: ${KICAD10_3DMODEL_DIR}/...step`). Bare board only |
| Top / bottom render, orthographic | `pcb_render` with `"perspective": false`, `"side": "top"/"bottom"` | works |
| One 3D render | `pcb_render` with `"perspective": true`, `"rotation_x": -45, "rotation_z": 30`, `"quality": "high"` | works |
| Schematic PDF and SVG | `sch_export_plot_pdf`, `sch_export_plot_svg` | works |
| BOM CSV | `sch_export_bom` | works, **but** the delimiters must be set in the job (see pitfalls) |
| Board statistics | `kicad-cli pcb export stats --format json` | works on the CLI; **the `pcb_export_stats` job breaks the jobset** (see pitfalls) |
| Stackup | — | **not exported** by any command. Read from `.kicad_pcb` `(setup (stackup ...))` in plain Python; the canary has no stackup block at all until someone opens Board Setup, so the reader needs a default (2 layers, `general.thickness`) |
| Design rules | — | **not exported**. Read from `.kicad_pro` `board.design_settings.rules`, `net_settings.classes` and the `.kicad_dru` file (custom rules) in plain Python |

Run time of the whole jobset on the canary: 4.4 s wall (37 s CPU, mostly the high-quality render).

### 2.4 Pitfalls found (input for 5.20)

1. **One job that cannot be parsed drops all jobs, with exit code 0.** A `pcb_export_stats` job with
   `"output_format": "json"` made `jobset run` print `0 jobs succeeded, 0 job failed` and return 0.
   curatrix must compare the number of jobs run with the number in the jobset and fail otherwise.
   Leave the stats job out of the jobset; run `pcb export stats` as a single export if needed.
2. **BOM job without delimiters writes a CSV without separators** (`RefsValueFootprintQty...`). The
   template must set `"field_delimiter": ","`, `"string_delimiter": "\""`, `"ref_delimiter": ","`,
   `"ref_range_delimiter": "-"`.
3. **Variant jobs must copy the base job's settings.** In the spike `bom-addr41` had a shorter
   `fields_ordered` than `bom` (no `Manufacturer`, `MPN`), so the variant BOM lost those columns. That
   would break the per-variant cross-check (P5-15) and the MPN warning of 5.21. Rule for the template:
   a variant job equals its base job except for the variant name and the output file name; the 5.20
   check compares them.
4. **ERC and DRC jobs fail the jobset when there are violations** (`fail_on_error` defaults to true in
   jobs; `jobset run` exit code 6). Either set `"fail_on_error": false` in the template and evaluate
   the JSON in curatrix (recommended: 5.19 does the evaluation), or keep ERC/DRC out of the CAM jobset.
5. `"output_filename": "sch/"` (a folder) fails for the schematic PDF job (`Failed to create file`);
   give a file name. The SVG job writes one file per sheet named after the sheet, whatever you give.
6. `jobset run` writes into `$TMPDIR/<uuid>/` and does not clean it up; it also creates
   `$TMPDIR/org.kicad.kicad/instances`. curatrix must set `TMPDIR` under `build/`.
7. Destination `"output_path"` is relative to the project folder (`"../out-jobset"` worked).
8. Locale: with the user's `LC_NUMERIC=de_DE.UTF-8`, `pcb export stats` writes `"34,0000 mm"`;
   with `LC_ALL=C.UTF-8` it writes `"34.0000 mm"`. xdmod#41 sets `LC_ALL=C.UTF-8` for KiCad batch runs.
9. The DRC job with `"parity": true` printed `Failed to fetch schematic netlist for parity tests` on
   the first run (before the schematic was complete); later runs were fine. Not followed further.

## 3. Assembly variants (EE-2, EE-8)

### 3.1 How they are stored

`.kicad_pro`, the names and descriptions:

```json
"schematic": { ... "variants": [ {"name": "addr40", "description": "..."}, {"name": "addr41", ...} ] }
```

`.kicad_sch`, per symbol instance, only the differences from the base symbol:

```
(instances (project "canary-board" (path "/<root uuid>" (reference "R1") (unit 1)
  (variant (name "addr41") (field (name "Value") (value "4k7"))))))
(... (reference "JP1") (unit 1) (variant (name "addr41") (dnp no)))
```

Possible keys in a variant: `dnp`, `exclude_from_sim`, `in_bom`, `on_board`, `in_pos_files`, and any
number of `(field (name ..) (value ..))`. A variant without differences is not written.

`.kicad_pcb`: a board list `(variants (variant (name "addr40") (description ...)) ...)` and per
footprint `(variant (name "addr41") (dnp no))` or `(field (name "Setting") (value "2-3"))`. The PCB keeps
its own copy; KiCad syncs it on "Update PCB from schematic" in the GUI. A plain-Python check should
compare the two (variant names and per-reference overrides).

### 3.2 What the exports produce

| Export | Base (`addr40`) | `--variant addr41` / job `"addr41"` |
|---|---|---|
| BOM (`sch export bom`) | JP1 and R2 marked `DNP`, R1 `10k`, J2 `Setting` `1-2` | JP1, R2 fitted, R1 `4k7`, J2 `Setting` `2-3` |
| Position file | J1, J2, R1 | J1, J2, R1 `4k7`, **R2** |
| XML netlist | has `<variants><variant name="addr41">` per component with the overrides | (same file) |
| Render | identical PNGs for both variants | — |

Notes:
- Solder jumpers never appear in position files: the library footprint has
  `(attr exclude_from_pos_files ...)`. Right for a solder blob; "fitted" for a solder jumper means
  "bridged", visible in the BOM only. A 0R link (R2) shows the variant in the position file.
- Render per variant: not provable here, because no 3D models are installed (§2.3). The render job
  accepts the variant.
- `--variant` with several names and `${VARIANT}` in the output path gives one file per variant in one
  call (help text; not run).

### 3.3 Field per variant for shunt positions

**Yes.** Any field can be overridden per variant (`Setting` = `1-2` / `2-3` in the spike), and the
override shows in the BOM column and in the netlist. So the shunt position *can* live in KiCad. The
agreed design (EE-2/EE-8 answer: shunt positions in the EE model, checked against KiCad) still holds;
the check now has a KiCad side to compare with: field `Setting` per variant.

## 4. ERC and DRC (EE-7, P5-4)

### 4.1 Commands

```
kc.sh sch erc --format json --severity-all -o erc.json canary-board.kicad_sch
kc.sh pcb drc --format json --severity-all -o drc.json canary-board.kicad_pcb
```

`--severity-all` includes excluded findings. `--severity-error` alone leaves them out (DRC: 9 → 7).

### 4.2 Exclusions in the JSON: yes, with the comment

```json
{"comment": "unrouted in iteration 1 (spike test)", "excluded": true,
 "description": "Missing connection between items",
 "items": [{"description": "PTH pad 1 [/+5V] of J1", "pos": {...}, "uuid": "..."}, ...],
 "severity": "error", "type": "unconnected_items"}
```

Not excluded entries have no `excluded` / `comment` key. Rules switched off are listed in
`ignored_checks` (key and description).

### 4.3 Storage in `.kicad_pro`

- ERC: `erc.erc_exclusions` = list of `[key, comment]`; DRC: `board.design_settings.drc_exclusions`
  = list of `[key, comment]` (a plain string without comment is also read).
- The key is an opaque string with the rule, the marker position in internal units and item UUIDs:
  - DRC unconnected: `unconnected_items|108000000|98000000|F.Cu|4|<pad uuid>|<pad uuid>` (nm; 4 = ratsnest marker)
  - ERC dangling label: `label_dangling|635000|762000|<label uuid>|00000000-...|/<root uuid>||/<root uuid>`
    (units of 100 nm; the three sheet-path fields are filled in a way that took six tries to match)
- Writing exclusions by hand is possible but fragile; they should be made in the GUI.

### 4.4 Behaviour that matters for 5.19

- **DRC, moved part:** J1 moved by 1 mm → its exclusion no longer matches; the finding comes back
  as not excluded; the stale exclusion silently disappears from the report. Fails safe.
- **ERC, stale exclusion:** an exclusion that matches no current finding is **turned into an
  excluded phantom finding in the JSON**, identical in form to a real excluded one. With a wrong key,
  the report showed the real finding (not excluded) *plus* an excluded copy. A rule set to `ignore`
  turned its exclusion into a phantom with `"severity": ""`. So a reader cannot tell "accepted" from
  "stale" by the JSON alone. Fallback for 5.19: count an ERC exclusion as accepted only if a
  non-excluded finding with the same type and item UUIDs does *not* exist, and warn on excluded
  entries with empty severity; or keep KiCad exclusions only for DRC.
- The positions in the key are the reason why moving anything loses the acceptance (the stated rule
  in 5.19 is correct).

### 4.5 Unrouted board

A board with placed footprints and no tracks reports only `unconnected_items` (0 other violations here):
one entry per missing ratsnest edge, that is **pads − 1 per net**. The spike board: nets with 2, 4, 4 and 3
pads → 1 + 3 + 3 + 2 = **9 entries** (7 before R2 was added). A real board gives hundreds, and each entry
changes with placement. One `accepted.yaml` entry "all `unconnected_items` of this board" (P5-4.3) is the
right shape; KiCad exclusions are not.

### 4.6 Severities

- DRC: `.kicad_pro` `board.design_settings.rule_severities` (all rules written, e.g.
  `"unconnected_items": "error"`), plus `(severity ...)` inside custom rules in `.kicad_dru`.
- ERC: `.kicad_pro` `erc.rule_severities`. **The canary's `.kicad_pro` has no `erc` section at all**
  (written only when ERC settings are saved in the GUI), so the defaults apply.
- The bypass in P5-4.2 is real: `unconnected_items: "warning"` in `.kicad_pro` → `--severity-error`
  reports 0 unconnected items; `label_dangling: "ignore"` → the rule moves to `ignored_checks`.
- Input for 5.17/5.19: the template must contain a full `erc` section (all `rule_severities`) so that
  the "severities equal the template" check has something to compare; a missing section must count as
  "defaults of KiCad 10.0.8", which the check needs as a list.

## 5. Connector extraction (EE-6)

`kc.sh sch export netlist --format kicadxml -o netlist.xml canary-board.kicad_sch`

- Per component: `ref`, `value`, `footprint`, `<fields>` with **all fields, hidden ones included**
  (`Port`, `TraceID`, `PartOf`, `Manufacturer`, `MPN`, `Setting`), `<property>` copies, `<libsource>`,
  `<variants>` with per-variant overrides (`<field name="Setting">2-3</field>`, `<property name="dnp" value="0"/>`).
- Per net: `<net code name class>` with `<node ref pin pinfunction pintype>`.
- **Pin name:** `pinfunction` is `<pin name>_<pin number>` in KiCad 10 (`Pin_1_1`, `A_1`), and absent if
  the pin has no name. The plain pin name is in `<libparts><libpart><pins><pin num name type>`. The
  extractor should take the name from `libparts`, not split `pinfunction`.
- **Net names:** local labels give `/+5V`, `/SERVO_PWM` (sheet path prefix). Global labels and power
  symbols give names without the prefix. CK-F1 matching by net name must strip the leading `/` of
  root-sheet nets, or the boards must use global labels for connector signals. Hierarchical sheets give
  `/<sheet>/<net>`.
- Verdict: works; the cross-check in 5.18 (plain Python vs XML netlist) is straightforward.

## 6. Keeping KiCad off the user's config

Finding: **`KICAD_CONFIG_HOME` is not enough.** A run with only `KICAD_CONFIG_HOME` set and `HOME`
pointed at an empty folder created:

```
fakehome/.cache/kicad/10.0/3d                       <- 3D model cache (render, STEP)
fakehome/.local/share/kicad/10.0/{plugins,scripting,template,projects,symbols,footprints,3dmodels,3rdparty}
```

So with the real `HOME`, every `kicad-cli` render or STEP export would write into the user's
`~/.cache/kicad/10.0/3d`, and every run creates `~/.local/share/kicad/10.0/*` folders if missing.
Two variables move them (verified, the fake `HOME` stayed empty):

- `KICAD_CACHE_HOME=<dir>` → `<dir>/kicad/10.0/3d`
- `KICAD_DOCUMENTS_HOME=<dir>` → `<dir>/kicad/10.0/...`

Without them KiCad falls back to `XDG_CACHE_HOME` / `XDG_DATA_HOME`, which are set to the user's dirs
in this desktop session. The spike unset `XDG_*` and used a fake `HOME`; the result carries over to
curatrix, which keeps the real ones, because both variables win over the platform paths in the source
(`common/paths.cpp:39` for `KICAD_DOCUMENTS_HOME`, `:468` for `KICAD_CACHE_HOME`).

What curatrix does with this (xdmod#41):

- `launch_env` sets `KICAD_CACHE_HOME` and `KICAD_DOCUMENTS_HOME` under `.xdmod/`; through
  `limits.tool_env` they reach the GUI and every scripted run.
- KiCad batch runs (`kicad-cli`, pcbnew/eeschema scripts) get `LC_ALL=C.UTF-8`; the GUI keeps the
  user's locale.
- `TMPDIR` under `build/` for `jobset run` is still open (§2.4, pitfall 6).

Side effect, intended by rule 4: `KICAD_DOCUMENTS_HOME` also moves the GUI's `plugins`, `scripting`,
`3rdparty` (plugin and content manager) and the default user library and template folders. Under
`curatrix launch kicad` the owner's PCM plugins and personal libraries from `~/.local/share/kicad` do
not show up. This is on purpose; do not "fix" it, install what a board needs through the workspace.

KiCad also writes into `KICAD_CONFIG_HOME` on every run (`kicad_common.json`, `pcbnew.json`,
`3d_viewer.json`, `cvpcb.json`, `fpedit.json` in `.xdmod/kicad/10.0` were rewritten), which is fine
because it is workspace-local. But parallel runs (checks over several boards in 5.19/5.20) can race on
these shared JSON files: run KiCad jobs one after the other, or give each run its own copy of the config.

`libs/kicad/packages3D` is missing: `XD_KICAD_3DMODELS` points to it, but it does not exist. Without it
STEP and renderings have no parts (5.20, 5.21, EE-5).

Before/after record of the user's dirs: see the PR text. Summary: `~/.local/share/kicad` and
`~/.cache/kicad` unchanged; in `~/.config/kicad/10.0/` the file `kicad_common.json` changed at
02:30:43, 46 s **before** the first KiCad run of this spike (02:31:29, under the fake `HOME`) and while
no KiCad run of mine had started; nothing changed after that (`find -newer` gives 0 files). This write is
**unexplained and was not caused by the spike's runs**. It is the same kind of leak as the task 5.3
incident; it needs a follow-up (find the process, for example another agent's unisolated KiCad run).

## 7. MCP servers for KiCad

| Server | Licence | Last push | Version pin | How it drives KiCad | Notes |
|---|---|---|---|---|---|
| [mixelpixx/KiCAD-MCP-Server](https://github.com/mixelpixx/KiCAD-MCP-Server) | MIT | 2026-11-16 | releases, v2.9.0 (2026-11-12) | `kicad-cli`, IPC API (`kipy`), SWIG `pcbnew` fallback; Node + Python | most used (≈3.4k stars); hard-coded `~/Documents/KiCad/{9,10}.0/footprints`; schematic and PCB editing, export, freerouting |
| [oaslananka/kicad-mcp-pro](https://github.com/oaslananka/kicad-mcp-pro) | **AGPL-3.0** | 2026-11-17 | releases, mcp-server v4.16.0 (2026-11-15), PyPI-style package | `kicad-cli`, IPC (`KICAD_API_SOCKET`), some `pcbnew` | ERC/DRC validation, very active; reads `XDG_DATA_HOME` (user's) for its bridge |
| [lamaalrajih/kicad-mcp](https://github.com/lamaalrajih/kicad-mcp) | MIT | 2025-10-17 | no tags | `kicad-cli` | project listing, DRC history; `KICAD_USER_DIR = ~/Documents/KiCad`; inactive for a year |
| [Seeed-Studio/kicad-mcp-server](https://github.com/Seeed-Studio/kicad-mcp-server) | **none** | 2026-10-22 | no tags | `kicad-cli`, a little `pcbnew` | schematic/PCB analysis, pin tracing; no licence = not usable |
| claynicholson/copper-kicad-mcp, blwfish/kicad-mcp, Netlist-Studio/kicad-mcp, ProductOfAmerica/mcp-server-kicad (GPL-3.0, maintenance mode), ShamanAndrey/kicad-mcp-layer | mixed | 2026 | — | — | smaller; not read |

(Cloned read-only into `build/spike-kicad/mcp/` and searched; none was run.)

Verdict: **cut for iteration 1.** Everything 5.17–5.21 needs is `kicad-cli` plus plain Python (and
`pcbnew` for scripted board changes). The IPC-based tools need a running KiCad GUI. A server could
be used later with a pinned release (mixelpixx v2.9.0, MIT) if it is started through curatrix with the
environment of §6; its hard-coded `~/Documents/KiCad` paths would then point at nothing, which is
harmless but would need a patch to use the workspace libraries. Not worth it now.

## 8. Input for the tasks

**5.14 (decisions):**
- P5-3 resolves to "A for both": version in the copy's `.kicad_pro`, variants as named jobs in the
  shared jobset (one job per variant-dependent output). Single exports with `-D`/`--variant` are not
  needed for CAM. Record this in the ADR.
- Stackup and design-rule tables come from plain Python (confirmed: no native export).
- Shunt positions: KiCad can hold them as a per-variant field; the EE model stays the source, KiCad's
  `Setting` field is checked against it.
- `tools.yaml`/`doctor`: the KiCad 3D model library (`packages3D`) is needed for STEP and renderings.

**5.17 (projects, `curatrix new pcba`):**
- Template `.kicad_pro`: `text_variables.XD_VERSION = "unversioned"`, a full `erc` section with all
  `rule_severities`, `board.design_settings.rule_severities`, `schematic.variants` (empty or the board's
  variants).
- curatrix env for KiCad: as in xdmod#41 (§6); `TMPDIR` for batch runs still to add.
- Title block: full version in a comment line, `rev` short or empty (§2.1).
- `curatrix new pcba` writes one job per variant and output, copied from the base job (§2.2, §2.4).

**5.18 (connectors):** read `Port`/`TraceID` from `<comp><fields>`; pin names from `<libparts>`;
nets from `<nets>`, strip the leading `/` of root-sheet net names (or require global labels on
connector nets); variants from `<comp><variants>`.

**5.19 (ERC/DRC):**
- run ERC/DRC as single commands with `--format json --severity-all`, evaluate in Python;
- an exclusion counts if `excluded: true`; its comment is in the JSON; the commit that added it comes
  from git on `.kicad_pro`;
- ERC phantom entries (stale exclusions) need the extra rule of §4.4;
- unrouted nets: one `accepted.yaml` entry for `type == "unconnected_items"`; expect pads − 1 per net;
- severities check against the template, with KiCad's defaults when the `erc` section is missing.

**5.20 (CAM):**
- shared jobset with the outputs of §2.3, `fail_on_error: false` or no ERC/DRC jobs, BOM delimiters
  set, no `pcb_export_stats` job, file names not folders, one variant-named job per variant;
- checks: the variant names in the jobs equal `schematic.variants`; each variant job equals its base
  job except variant and file name; the version check looks at the comment line, not `rev`;
- run KiCad jobs one after the other (shared `.xdmod/kicad` JSON);
- after `jobset run`: check the "N jobs succeeded" count equals the job count (pitfall 1), and the
  exit code;
- the plain-Python checks planned (no `special_execute`, no `special_copyfiles` outside the output)
  read `jobs[].type` from the JSON; also check that title block `rev`/`comment` and one `F.SilkS`/`B.SilkS`
  `gr_text` contain `${XD_VERSION}`;
- `TMPDIR` under `build/`; remove `$TMPDIR/<uuid>` after the run.

**5.21 (board document):** variant BOMs only carry `Manufacturer`/`MPN` if the variant job copies the
base job's fields (§2.4). The BOM CSV per variant from the jobset can serve as the cross-check for the
plain-Python BOM reader (P5-15); variant overrides are in the netlist too, so one reader can serve both.

## 9. Not done in the time box

- The schematic PDF per variant (how DNP is drawn), and a render per variant with real 3D models.
- A real KiCad GUI round trip (does the GUI keep the hand-written variants and exclusions on save).
- Hierarchical sheets (net names, variant overrides per sheet instance).

## 7a. Addendum 2026-11-18: the KiCad MCP server as a curated tool

xdmod#69 finding 19, owner decisions Q1, Q2, Q3; research: `build/research-kicad-mcp/report.md`.
The verdict of §7 ("cut for iteration 1") is replaced: mixelpixx/KiCAD-MCP-Server v2.9.0 (MIT) runs
workspace-local through the fork **tiacsys/KiCAD-MCP-Server** (branch `xd/main` = tag `v2.9.0` + PRs:
#1 CI and release asset with a hashed lock file without pymupdf, #2 `KICAD_MCP_HOME` /
`KICAD_MCP_LOG_DIR`, #3 review fixes, #4 `KICAD_DOCUMENTS_HOME` / `KICAD_CONFIG_HOME` honoured and
`KICAD_MCP_STRICT_PATHS`, #5 `KICAD_API_SOCKET` / `KICAD_API_TOKEN`). The upstream PR drafts wait for
the owner's OK (D124): `build/kicad-mcp-fork/upstream-drafts/`.

Curated as tools.yaml `kicad-mcp` (tarball + new `python_venv`), started by `curatrix mcp-server kicad`
(curatrix/README.md, tools.yaml). Trial of research report §7 on scratch copies of the canary board
(`build/kicad-mcp/trial*/`, never the repo), with a preview asset of the patch stack (c4d3b0d; the
`v2.9.0-xd.1` tag waits for the fork reviews):

| Step | Result |
|---|---|
| Install (`python_venv`: own venv, `pip --require-hashes --only-binary`, pcbnew linked) | works; pcbnew 10.0.8 from `/usr/lib/python3.14/site-packages` |
| doctor handshake (initialize, tools/list, worker READY, strict paths) | ok: 38 tools in readonly with toolboxes core, schematic, board, drc; user folders unchanged |
| Readonly session: `open_project`, `get_project_info`, `list_schematic_components`, `get_schematic_component J1` (all fields incl. hidden `Port`, `MPN`, `TraceID`) | works (SWIG backend) |
| `run_erc` / `run_drc` vs `curatrix check robarm-ee --only CK-F4a` / `CK-F4b` | same result: ERC 0; DRC 2 `unconnected_items` J1–R1, the two findings of the open `accepted.yaml` proposal |
| Readonly refuses writes | `set_schematic_component_property` -> "Tool ... disabled" |
| Readonly `run_drc` wrote `<board>_drc_violations.json` next to the board (trial build) | **fixed in `v2.9.0-xd.2`** (fork #6): in readonly and manufacturing mode the report, a caller's `reportPath` and the 2D-view file go to `.xdmod/kicad-mcp/reports/`; the board folder stays unchanged (checked again on xd.2) |
| Write mode: `set_schematic_component_property` (hidden field), `move_component R1`, `save_board` | board saved through pcbnew: 1 line changed (the `at`); schematic written as text: 5 lines, non-canonical (`) (hide yes))` on one line) |
| `curatrix run --use kicad-cli -- kicad-cli sch upgrade --force` on the edited schematic | canonical again: only the field value line differs from the original. So: schematic edits through the server must be re-saved by kicad-cli before a commit (rule 4) |
| With `curatrix launch kicad` open (IPC server switched on in `.xdmod/kicad/10.0/kicad_common.json` for the trial only, restored afterwards) | `check_kicad_ui`: running, `ipc_connected: true` on `/tmp/kicad/api.sock`. With only the project manager open, the session stays on SWIG (the GUI does not hold the board); live board edits need the PCB editor open. IPC tools (`ipc_*`) are not in the default toolboxes |
| User folders (`~/.config/kicad`, `~/.local/share/kicad`, `~/.cache/kicad`, `~/.kicad-mcp`, `~/.cache/pip`, FreeCAD and Blender folders) | unchanged during install, doctor and trial (`find -newer`). Writes below HOME of the night, all by the **unpatched upstream** test suite (vitest and pytest, 2026-11-17 23:56-23:57, before the fork patches and before the suites ran with a fake HOME): `~/.kicad-mcp/logs` (5 files), `~/.config/kicad-mcp/logs/` (empty), `~/.cache/kicad-mcp/` (empty), `~/.local/share/kicad-mcp/jlcpcb_parts.db` (48 KB). Moved to `build/kicad-mcp-fork/evidence/` and `.../evidence/home-leak-2026-11-17/`; `doctor` now warns when any of these folders exists |

Release check (same night): with the released `v2.9.0-xd.1` asset (sha256 `96bee2f6…`) the doctor
handshake FAILED: strict mode refused `XDG_*_HOME` below `$HOME`, and this workspace lives below
`$HOME` (a rule added in fork #4 after the trial build). Fork PR #7 limits the rule to the desktop
folders; the handshake with that fix (scratch copy of the release) passes, user folders unchanged.
Pinned now to `v2.9.0-xd.2` (fork `xd/main` 9bd4d68, with #6 and #7): installed from the release
asset, doctor handshake ok (38 tools, worker ready, user folders unchanged); a readonly `run_drc` on a
scratch copy writes its report to `.xdmod/kicad-mcp/reports/`, the board folder stays unchanged.
`curatrix mcp-server kicad` (aligned with #80's `mcp-server freecad`) also sets `HOME` to
`.xdmod/kicad-mcp/home` for the server and its child processes (kicad-cli, Java).

Open: the IPC server is off in the workspace KiCad config; switching it on for `curatrix launch
kicad` is a decision for the owner (socket without auth, report §3). The server needs more than 30 s
to exit after its stdin closes when the worker is still warming up (the doctor kills it after 15 s).
While a session has a project open, KiCad's lock file `~<project>.kicad_pro.lck` sits next to the
project; a clean exit removes it, a killed server (doctor timeout, memory limit) leaves it behind, and
it then shows up in `git status`: delete it by hand.
