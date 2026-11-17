# Checklist: KiCad

For `pcba/`, `proto/`, `harness/`, `lib/` in robarm-ee. Background: `robarm-ee/claude/CLAUDE.md`,
`robarm-ee/pcba/README.md`, skill `xd-kicad-authoring`. This list grows with tasks 5.12 and 5.17-5.22.

## Run
- [ ] The local check ran **with CAD content** and its table is posted (P5-11). It names the
      checks that needed KiCad or FreeCAD; today there are none (they come with tasks 5.17-5.27).

## Files
- [ ] No KiCad tool ran outside curatrix or its `.venv/bin` shims, not even `kicad-cli --version`
      (a bare call rewrites `~/.config/kicad`). A PR text or log showing a bare `/usr/bin/kicad-cli`,
      `pcbnew` or `eeschema` call is a must-fix: ask the owner to check `~/.config/kicad`.
- [ ] Every `.kicad_sch`, `.kicad_pcb`, `.kicad_pro` was saved by KiCad itself (the GUI through
      `curatrix launch kicad`, or KiCad's Python / `kicad-cli` through `curatrix run --use kicad-cli`).
      Hand-edited S-expressions are a must-fix unless the PR says why.
- [ ] No lock or backup files: `*.lck`, `*-backups/`, `fp-info-cache`.
- [ ] Library tables use only `${XD_KICAD_*}` and `${KIPRJMOD}` (D88). No absolute path, no global table.

## Trace fields
- [ ] Symbols and sheets that carry a trace ID have the hidden fields (`TraceID`, links, `Status`,
      `Configs`) with **real IDs** from the ledger. The project's ID is a project text variable.
- [ ] Links point to the right kinds: EE design to `SYS-REQ` / `SYS-IF` / `SYS-EL`, never to SW (D36).
- [ ] A sheet used several times has one ID; its usages appear as `instances` (D128).
- [ ] `curatrix gen cad-needs robarm-ee` was run and `generated/cad-needs.json` is committed and
      fresh (CK-D4).

## Findings
- [ ] ERC/DRC findings are fixed, excluded in KiCad with a comment, or proposed for
      `accepted.yaml`. An agent never writes the `Accepted-by:` commit (P5-4).
- [ ] The project's severities equal the template (once `curatrix new pcba` exists).
