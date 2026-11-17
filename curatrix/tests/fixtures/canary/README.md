The canary of the reference project, as the fixture of `test_variantlist.py` (`curatrix variants list`).
No curatrix check collects these files (xdmod's checks.yaml has no `cad` or `model` section); only
the test reads them.

- `ee-model.json.gz`: the EE domain model's committed `generated/model.json` (compact, gzipped), with
  the board `EE-PCBA-0001` and its two domain variants `default` (serves `SYS-CFG-0001` and the
  usage `canaryUnit`) and `alt` (serves no pair);
- `sys-model.json.gz`: the system model's committed `generated/model.json` (the upstream);
- `pcba/canary-board/`: the KiCad project, cut down to what the listing reads: the `.kicad_pro`
  with only `text_variables.TraceID` and `schematic.variants`; the root schematic as it is (R1 is
  DNP in `alt` at its instance); the `.kicad_pcb` with only each footprint's Reference, `(attr ..)`
  and own `(variant ..)` blocks (R1 is DNP in `alt` on the board too).

Copied from the canary at EE 4078b4c and system d5ca703 (2026-11-17). To refresh, from the
workspace root:

```sh
F=xdmod/curatrix/tests/fixtures/canary
gzip -9 -n -c robarm-ee/generated/model.json > $F/ee-model.json.gz
gzip -9 -n -c robarm-syseng/generated/model.json > $F/sys-model.json.gz
cp robarm-ee/pcba/canary-board/canary-board.kicad_sch $F/pcba/canary-board/
curatrix run -- .venv/bin/python -c "import json; d = json.load(open('robarm-ee/pcba/canary-board/canary-board.kicad_pro')); \
  print(json.dumps({'text_variables': {'TraceID': d['text_variables']['TraceID']}, \
  'schematic': {'variants': d['schematic']['variants']}}, indent=2))" > $F/pcba/canary-board/canary-board.kicad_pro
curatrix run -- .venv/bin/python $F/cut_board.py robarm-ee/pcba/canary-board/canary-board.kicad_pcb \
  $F/pcba/canary-board/canary-board.kicad_pcb
```

The schematic embeds the `Device:R` and `Connector_Generic:Conn_01x02` symbols of the KiCad library
(CC-BY-SA 4.0 with the design exception, which covers symbols embedded in a design file; as in
`tests/fixtures/kicad/`).
