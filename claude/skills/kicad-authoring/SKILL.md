---
name: xd-kicad-authoring
description: Use when you create or change KiCad files in robarm-ee (pcba/, proto/, lib/) - workspace-local config, saving through KiCad itself, trace fields, generated cad-needs. Placeholder skill - completed after the KiCad spike (task 5.12).
---

# KiCad authoring (placeholder)

**Status:** what is known today. This skill is completed after the KiCad 10 spike (plan task
5.12, result in `xdmod/claude/notes/kicad-spike.md`) and tasks 5.17-5.22 (`curatrix new pcba`,
connectors, ERC/DRC, CAM). The spike also decides which MCP servers may drive KiCad.

Read first: `robarm-ee/claude/CLAUDE.md`, `robarm-ee/pcba/README.md`, `xdmod/curatrix/README.md`
("CAD trace fields", "Launchers"), review list `xdmod/claude/checklists/kicad.md`.

## Rules known today

- **Workspace-local config only.** Start KiCad with `curatrix launch kicad`; run `kicad-cli` and
  KiCad's Python (`pcbnew`) with `curatrix run --use kicad-cli -- ...`. Both set the `.xdmod/`
  KiCad config and the `XD_KICAD_*` library variables. A bare call writes to `~/.config/kicad`
  (rule 4 incident in canary C0). Never touch `~/.config`.
- **Files are saved by KiCad**, not written by hand. `kicad-cli` cannot save a project: canary C0
  saved its `.kicad_pro` through the `pcbnew` Python module, which also writes an empty
  `.kicad_pcb`. KiCad 10 has no IPC write API for schematics, so scripted schematic changes are
  limited; the spike decides the route.
- **Libraries:** only the workspace libraries, through the project's library tables with
  `${XD_KICAD_SYMBOLS}`, `${XD_KICAD_FOOTPRINTS}`, `${XD_KICAD_3DMODELS}`, `${XD_KICAD_TEMPLATES}`,
  `${KIPRJMOD}` (D88).
- **Trace fields:** hidden symbol or sheet fields `TraceID`, `Realizes`, `Satisfies`, `Conforms`,
  `Status`, `Configs`; the PCBA ID is a project text variable. Use real IDs (`curatrix ids new
  EE-CMP`, skill `xd-issue-ids`). After task 5.14 the project carries the model's `EE-PCBA` ID only
  as a reference and `Realizes` / `Conforms` go away (P5-8).
- After every change: `curatrix gen cad-needs robarm-ee`, commit `generated/cad-needs.json`
  (CK-D4; PR CI sees KiCad content only through this file).
- Never commit `*.lck`, `*-backups/`, `fp-info-cache`.
- Run `curatrix check robarm-ee --stage local` **with CAD content**; the reviewer runs it again
  (P5-11).

## Example: canary C0

The canary board `robarm-ee/pcba/canary-board/` on main is the smallest complete
example: one sheet, one traced symbol, the project saved by KiCad, `generated/cad-needs.json`
committed. It belongs to the configuration `canary` (`Configs` field).

`curatrix variants list robarm-ee` shows the board variants on every level: the model def, the
KiCad variant and its description, the parts DNP or fitted per variant, and the configuration
and usage each one serves (`--json` for tools). The PLEML feature rules are `curatrix pleml check`.

## To be added after the spike

Jobset template and `curatrix new pcba`; variants (`--variant`); ERC/DRC with exclusions and
`accepted.yaml` (only humans write `Accepted-by:`); connector `Port` fields; CAM output;
the MCP server and how to use it under limits.
