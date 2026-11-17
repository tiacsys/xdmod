# Author loop on the canary (task 5.31)

Agent measurement, 2026-11-17, about 1.5 hours (19:11 to 20:10, 126 measured commands). It answers the plan's "Pilot time" limit (P4-11, Phase 4
review: "about 45 s per Pilot run") and exit criterion 5 of Phase 5. Raw data, scripts and logs are
under `build/author-loop/` (not committed): `bin/measure.py` (the sampler), `bin/round.sh` and
`bin/edit-round.sh` (the loops), `bin/table.py` (the tables below), `raw/<command>-<state><n>.{json,log}`
and, for every check run, `raw/*.summary.json` (curatrix's own per-check seconds).

## Verdict

**No caching now.** The plan's rule makes caching mandatory if one local check of robarm-ee takes more
than five minutes. It takes **28 s** (median, with CAD), about a tenth of the limit. No other command
of the author loop takes more than 80 s, and a whole role loop takes 0.5 to 1.5 minutes. The numbers do
not ask for caching. Two cheap wins are on record below for when the canary grows (Pilot result
reuse, parallel Sphinx in zdocs); neither is needed for Phase 5.

## Numbers

Wall time in seconds (median of three runs; cold: one run). Command keys: `syseng-gen` = `curatrix gen
model robarm-syseng`, `*-check` = `curatrix check <repo> --stage local --json` (with CAD), `*-docs` =
`curatrix docs <repo>`, `ee-cam` = `curatrix cam robarm-ee canary-board` (one jobset run makes both
variants, `default` and `alt`), `me-cam` = `curatrix cam robarm-me canary-assembly` (Blender),
`me-camnb` = the same with `--no-blender`, `man-check` = `curatrix check robarm-manifest --stage local`
(its docs section is the full linked set, area `full`; there is no `curatrix check full`), `full-docs` =
`curatrix docs full`. Every run exited 0.

| Command | cold | fresh | warm | edit | n (c/f/w/e) | peak tree RSS MB | peak process MB | rc |
|---|---|---|---|---|---|---|---|---|
| syseng-gen | 34.5 | 34.8 | 34.4 | 35.3 | 1/3/3/3 | 2102 | 1801 | 0 |
| syseng-check | 39.4 | 40.2 | 40.0 | 39.7 | 1/3/3/3 | 1893 | 1592 | 0 |
| syseng-docs | 5.7 | 5.8 | 5.8 | 5.9 | 1/3/3/3 | 317 | 104 | 0 |
| ee-check | 28.7 | 29.2 | 28.4 | 28.7 | 1/3/3/3 | 1357 | 1059 | 0 |
| ee-cam | 12.4 | 12.5 | 12.5 | 12.5 | 1/3/3/3 | 407 | 377 | 0 |
| ee-docs | 11.4 | 11.7 | 11.4 | 11.5 | 1/3/3/3 | 320 | 106 | 0 |
| me-check | 25.6 | 25.8 | 25.0 | 25.0 | 1/3/3/3 | 1512 | 1204 | 0 |
| me-cam | 35.8 | 36.2 | 36.0 | 36.4 | 1/3/3/3 | 734 | 704 | 0 |
| me-camnb | 5.6 | 5.6 | 5.6 | 5.5 | 1/3/3/3 | 646 | 615 | 0 |
| me-docs | 9.5 | 9.6 | 9.6 | 9.7 | 1/3/3/3 | 248 | 105 | 0 |
| sw-check | 35.2 | 36.2 | 25.5 | 26.0 | 1/3/3/3 | 1932 | 108 | 0 |
| man-check | 75.4 | 74.0 | 76.4 | - | 1/3/3/0 | 1474 | 144 | 0 |
| full-docs | 70.6 | 71.6 | 71.0 | - | 1/3/3/0 | 1591 | 140 | 0 |

The loop per role (sum of the medians):

| Role | Loop | warm | after a one-line edit |
|---|---|---|---|
| syseng | `gen model` + `check` + `docs` | 80 s | 81 s |
| EE | `check` + `cam canary-board` + `docs` | 52 s | 53 s |
| ME | `check` + `cam canary-assembly` + `docs` | 71 s (41 s with `--no-blender`) | 71 s (40 s) |
| SW | `check` (firmware build CK-F5a, Twister CK-F5b, docs) | 26 s | 26 s |
| Full set | `check robarm-manifest` + `docs full` | 147 s | - |

**The robarm-ee local check with CAD: 28.4 s warm, 28.7 s after an edit, 29.2 s from an empty build
area.** The plan's limit is 300 s.

## Machine

| Item | Value |
|---|---|
| CPU | AMD Ryzen 7 PRO 4750U (laptop), 8 cores / 16 threads; **clock capped at 1.7 GHz** (`scaling_max_freq` = `cpuinfo_max_freq` = 1.7 GHz on this machine, governor `schedutil`, power profile `performance`, on AC) |
| RAM | 29 GiB (swap 61 GiB, unused) |
| Disk | NVMe, btrfs |
| OS | CachyOS, Linux 7.3.4 |
| Load | quiet: no other agent, no parallel job; 1-min load average 0.2 before the first run, 1 to 5 during the runs (the tools themselves: Cycles uses 8 threads, ninja and Twister run parallel jobs) |
| Limits backend | systemd user scopes (`curatrix limits`); every run under `curatrix run -m 12G -t 60m`, the tools inside under their own limits |
| Tools | Python 3.14.10, JDK 21.0.13, SysML v2 Pilot 0.63.1, KiCad 10.0.8, FreeCAD 1.1.4, Blender 5.2.3 (Cycles CPU), Sphinx 9.1.0, sphinx-needs 9.2.0, zdocs c66f436, CMake 4.5.0, Ninja 1.13.2, Zephyr SDK 1.0.1, gcc 16.2.1 |
| Pins | xdmod 83578e4, robarm-syseng d5ca703, robarm-ee 4078b4c, robarm-me 41cf477, robarm-sw 1f74b98 (all = origin/main, just after `curatrix update`) |

The clock cap makes every CPU-bound number here slower than on an uncapped machine of the same kind;
treat the numbers as an upper bound for an author's laptop.

## Method

Each command ran from the workspace root (or the root of a worktree set), one at a time, through
`bin/measure.py` inside `curatrix run -m 12G -t 60m`. The sampler polls `/proc` every 0.2 s for the
process tree of the command and records:

- **wall time**;
- **peak tree RSS**: the largest sum of the resident memory of all processes of the tree at one sample
  (the memory the command needs at once), and the largest single process;
- **tool busy time**: per tool (Pilot/Java, kicad-cli, FreeCADCmd, Blender, Sphinx, CMake/Ninja/compiler,
  Twister), the wall time during which at least one of its processes was alive, and how many distinct
  processes it started. Processes shorter than 0.2 s can be missed in the count;
- for `curatrix check ... --json`: the per-check seconds that curatrix already writes into
  `build/<area>/checks/summary.json` (and prints after each check). No new timing option was needed.

States:

- **cold**: the first run of each command after `curatrix update`, in the main checkouts (n = 1; the
  build areas `build/<repo>/` held outputs of earlier days).
- **fresh**: the same commands in a new worktree set (`scratch/author-loop`, local branch, never pushed)
  with an **empty** build area (`build/wt-scratch-author-loop/`); repeated three times, the build area
  moved aside before each repeat. This is the real "cold" for the build folders.
- **warm**: the same command again, nothing changed (main checkouts, three rounds).
- **edit**: in the scratch set, a one-line edit, then the role's loop, then `git checkout` (three
  rounds, a different edit text each round):
  - syseng: `heightAbove default 10 [mm]` in `model/product.sysml` to 11, 12, 13 mm -> `gen model`,
    `check`, `docs`;
  - EE: one line of the header comment of `model/canary.sysml` -> `check`, `cam canary-board`, `docs`
    (KiCad files are saved through KiCad, not edited by hand, so the model stands in; the KiCad
    steps run in full anyway, see below);
  - ME: the same in `robarm-me/model/canary.sysml` -> `check`, `cam canary-assembly` with and without
    Blender, `docs`;
  - SW: one comment line in `app/src/canary.c` -> `check` (it builds the firmware and runs Twister).

All values are medians of three runs (cold: one run). Wall times varied by less than 3 % between the
runs of one state, except the first fresh SW check (44 s against 36 s: the first build of the Zephyr
app into an empty folder).

## Where the time goes

Medians over the warm and edit runs. Tool busy time = wall time with at least one process of the tool alive (processes started); the slowest checks from curatrix's per-check seconds.

| Command | tool busy time (s) | slowest checks (s) |
|---|---|---|
| syseng-gen | pilot-java 33.2 (2 proc) | - |
| syseng-check | pilot-java 33.1 (2 proc), cmake/ninja/cc 5.1 (7 proc), sphinx 3.2 (4 proc) | CK-E1 33.8, CK-A6 5.2 |
| syseng-docs | cmake/ninja/cc 5.1 (7 proc), sphinx 3.0 (4 proc) | - |
| ee-check | pilot-java 13.6 (2 proc), cmake/ninja/cc 10.8 (13 proc), sphinx 8.2 (12 proc) | CK-E1 13.9, CK-A6 10.9, CK-D9 1.0 |
| ee-cam | kicad-cli 11.2 (5 proc) | - |
| ee-docs | cmake/ninja/cc 10.8 (13 proc), sphinx 8.7 (13 proc) | - |
| me-check | pilot-java 14.6 (2 proc), cmake/ninja/cc 8.8 (11 proc), sphinx 6.9 (9 proc) | CK-E1 14.8, CK-A6 8.9, CK-F4c 0.3 |
| me-cam | blender 33.0 (1 proc), freecadcmd 2.0 (4 proc) | - |
| me-camnb | freecadcmd 4.7 (4 proc) | - |
| me-docs | cmake/ninja/cc 8.9 (11 proc), sphinx 6.7 (9 proc) | - |
| sw-check | cmake/ninja/cc 22.2 (171 proc), sphinx 11.0 (15 proc), twister 10.7 (145 proc) | CK-A6 13.8, CK-F5b 10.6, CK-F5a 0.4 |
| man-check | cmake/ninja/cc 75.8 (33 proc), sphinx 71.4 (106 proc) | CK-A6 75.8 |
| full-docs | cmake/ninja/cc 70.3 (33 proc), sphinx 66.3 (68 proc) | - |

What the tables show:

1. **Nothing is cached, and nothing needs to be.** Cold, fresh, warm and edit cost the same within a
   few percent for every command except the SW firmware build: CK-F5a takes 10.5 s from an empty build
   folder (16 s the first time), 8 s on the first run after `curatrix update` (`--pristine auto` reconfigures), 0.4 s warm or
   after a one-line edit (Ninja). Every other check, CAM and docs run does its full work every time; an
   empty build area adds nothing measurable (CMake configure of a docs build is under a second).
2. **The Pilot is the largest single item of the model checks**: 33 s in robarm-syseng, 14 to 15 s in
   robarm-ee and robarm-me. P4-11 expected about 45 s per Pilot run; the largest run today is 33 s. The
   syseng run is more than twice the domain runs although the domain runs load the whole system model as
   a library set; the difference is most likely the **export**: syseng exports 59 packages into a 57 MB JSON
   (`build/robarm-syseng/model/pilot-export.json`), EE and ME 5 packages into 4 MB (not timed apart: the Pilot runs as one jshell script).
3. **The syseng loop runs the Pilot twice**: `gen model` and CK-E1 (`check` calls the same `gen.model`
   and compares). That is 33 s of the 80 s loop spent on a result that was just computed.
4. **Docs builds are serial Sphinx starts.** zdocs runs a stage-1 xref index and a stage-2 HTML build per
   document; its custom targets are `USES_TERMINAL`, which puts them in Ninja's console pool (one job at
   a time). A document costs about 2 x 1 s on this machine whatever its size. `docs full` and the
   manifest check are 28 Sphinx runs plus Doxygen one after another (70 s); Sphinx uses one core, so
   15 of 16 hardware threads stay idle.
   CK-A6 in every repo check is the same docs build again (the repo check and `curatrix docs` each build).
   Twister (CK-F5b) also rebuilds its test image each time: 10.6 s.
5. **CAD tools are cheap on the canary**: KiCad's jobset (18 jobs, both variants) 11 s, the FreeCAD
   checks one FreeCADCmd run under 0.5 s, the ME CAM without Blender 6 s. **Blender is the largest CAD
   item**: 33 s of Cycles CPU rendering (8 threads, fixed samples) for the canary assembly, 30 s more
   than the z-buffer fallback (`--no-blender`).
6. **Memory is not a constraint**: the peak is the Pilot's JVM (1.4 to 1.8 GB process, 2.1 GB tree in
   syseng); everything else stays under 1 GB per process. All limits in `limits.yaml` have room (Pilot
   4 G, docs 4 G, kicad-cli 2 G, freecad 4 G, blender 4 G).

## Caching options, if the numbers grow (not done)

| Option | Saves today | Cost | When |
|---|---|---|---|
| Reuse the Pilot result inside a loop: key = Pilot version + content hash of library and model files + export list; `check` reuses `gen model`'s export under `build/<area>/model/` | 33 s of the 80 s syseng loop; 14 s per domain check when the model did not change | small (one file, `gen.model`), but a cache key that misses an input gives a stale pass of CK-E1/CK-D2; the key must include xdmod's own `sysml/*.sysml` | when a model check passes about 2 minutes |
| Export only what curatrix reads (syseng exports 59 packages, 57 MB) | an estimated 15-20 s per syseng Pilot run | needs a look at what the readers use; no cache-key risk | first, before any cache |
| Parallel Sphinx in zdocs (job pool instead of the console pool, stage 1 and stage 2 each in parallel where the DAG allows) | `docs full` from 70 s towards 15-20 s | upstream change in zdocs (a draft for the owner, D124) | when the full set has more documents |
| Skip CK-A6 in `check` when `curatrix docs` just built the same tree | 5-75 s per repo | a staleness key over the whole docs input set (registry, upstream needs) | not worth it now |

## User configuration

`~/.config/{kicad,FreeCAD,blender}`, `~/.cache/{kicad,FreeCAD,blender}` and `~/.local/share/{kicad,FreeCAD}`
were listed (path, size, modification time) before the first and after the last run
(`build/author-loop/userconfig-{before,after}.txt`). **The two listings are identical**: 126 measured
commands (with their Pilot, kicad-cli, FreeCADCmd and Blender runs) through curatrix wrote nothing into the user's
configuration. The newest entries are from before the measurement (`kicad_common.json` 06:29,
FreeCAD `user.cfg` 00:23 of the same day).
