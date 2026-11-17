# Checklist: CI and tooling

For `checks.yaml`, `.github/workflows/`, `tools.yaml`, `requirements.txt`, `limits.yaml`, the
manifest, and curatrix itself. Background: `xdmod/claude/CLAUDE.md`, `curatrix/README.md`,
`framework/checks.md`.

## checks.yaml
- [ ] `expect:` lists exactly the checks the repo runs (CK-H6). A new built-in check is added to
      the `expect:` list of every repo that switches it on.
- [ ] A new checks.yaml key: xdmod is merged and **bumped in the manifest** before (or with) the
      repos that use it; better, the key starts optional.
- [ ] New `commands` have an ID, a `use:` from `limits.yaml`, the right `stages`, and `cad: true`
      if they need KiCad or FreeCAD.

## New or changed check (xdmod)
- [ ] It has an ID, stage and severity in `framework/checks.md`, and starts as a warning until it
      ran on the canary.
- [ ] `BUILTIN` row, catalogue entry in `data/checks.yaml` with an `XD-CHECK` ID from the ledger and
      the `XD-RULE` it enforces, `PLANTED` entry, README table row.
- [ ] `curatrix fixtures` passes (every planted error is caught).

## Tools and pins
- [ ] Tools that shape committed output are pinned exactly in `tools.yaml`; others by minimum
      version. `requirements.txt` lines pinned with `==` (CK-H3).
- [ ] `curatrix doctor` passes after the change.
- [ ] No `~/.config`, no global git config, no sudo, no system packages; KiCad and FreeCAD calls go
      through `curatrix launch` or `curatrix run --use kicad-cli|freecad` (workspace config).
- [ ] Limits are not raised to make a slow tool pass; the reason is found.

## Workflows
- [ ] `permissions:` are minimal (read-only token for checks).
- [ ] No robarm names in xdmod's reusable workflow; callers pass `manifest` explicitly.
- [ ] A failing fetch or missing base lets a check skip with a reason, never pass silently.

## Docs
- [ ] New `.rst` pages are in a toctree; the strict build passes (CK-A6).
- [ ] The manual, README and framework pages say the same thing as the code.
