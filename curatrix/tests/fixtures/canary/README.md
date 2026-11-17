The canary of the reference project, as the fixture of `test_variantlist.py` (`curatrix variants list`):

- `ee-model.json.gz`: the EE domain model's committed `generated/model.json` (compact, gzipped), with
  the board `EE-PCBA-0001` and its two domain variants `default` (serves `SYS-CFG-0001` and the
  usage `canaryUnit`) and `alt` (serves no pair);
- `sys-model.json.gz`: the system model's committed `generated/model.json` (the upstream);
- `pcba/canary-board/`: the KiCad project (`.kicad_pro` with `schematic.variants`, the root
  schematic, where R1 is DNP in `alt`).

Copied from the canary at EE 4078b4c and system d5ca703 (2026-11-17). Plain data; no tool reads it.
