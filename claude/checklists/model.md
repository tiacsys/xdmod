# Checklist: SysML model and views

For `model/*.sysml`, `model/generated/`, `generated/model*.json`, `views/`. Background:
`framework/sysmod-work-products.md`, `framework/trace-model.md`, `framework/views.md`,
`framework/variants.md`, `curatrix/README.md` ("SysML model conventions").

## Elements and IDs
- [ ] A model element becomes a need only when its short name is an ID (`<'SYS-EL-0007'>`) and it
      has a trace link (D129). The definition holds the ID, not the usage (D128).
- [ ] Every `SYS-EL` has a layer (`@Trace { layer = ...; }` on the element or its package).
- [ ] New IDs from the ledger (placeholders + `curatrix ids fix`), none typed by hand.

## Links
- [ ] Requirements are referenced only through the generated stubs (`model/generated/NeedStubs.sysml`,
      `sys_req_nnnn`); that file is not edited by hand.
- [ ] **Name clash:** the target of a `satisfy ... by <x>` is a part, not an attribute or other
      feature of the same name. A usage named like a stub attribute (`unit`, `quantity`, `max`)
      silently resolves to it and the `satisfies` link goes missing. Check that the link appears in
      `generated/model-needs.json`.
- [ ] `realizes` follows the layers: functional -> use case, logical -> functional, product -> logical.
- [ ] Allocations and `satisfy` statements point from the concrete side (D5).

## Files and order
- [ ] **No forward references across files:** the Pilot reads model files one by one in name
      order. A file may use only names from files before it (or from the libraries). Example:
      the `configures` dependency of the canary lives in `product.sysml`, not `configs.sysml`.
- [ ] One SYSMOD step group per file, as in `sysmod-work-products.md` §3.
- [ ] A nested package is written `public package X`: curatrix takes every line that starts with
      `package` for a top-level package.

## Variants
- [ ] Features and configurations follow PLEML (D102); `curatrix variants <repo>` is clean (CK-B4).
- [ ] Elements that belong to only some configurations carry `configs`.

## Generated and views
- [ ] `curatrix gen all <repo>` was run after the docs build, and `generated/model.json`,
      `generated/model-needs.json`, `model/generated/NeedStubs.sysml` are committed and fresh
      (CK-D1, CK-D2).
- [ ] `generated/provenance.json` names the pinned Pilot and JDK (CK-D5).
- [ ] Changed views were rebuilt with `curatrix views build` (CK-D3); hand edits went through
      `curatrix views normalize`.
- [ ] CK-E1 (the Pilot parses the model with 0 errors) passed in the local run.
