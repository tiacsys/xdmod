# Checklist: needs and requirements

For rst needs: `SYS-STH`, `SYS-NEED`, `SYS-REQ`, domain requirements (`SW-REQ`, `EE-REQ`,
`ME-REQ`), test cases. Background: `framework/trace-model.md`, `framework/sysmod-work-products.md`,
`needs/needs_config.toml`, skills `xd-ears-requirements` and `xd-sysmod-stakeholders-and-needs`.

## IDs and status
- [ ] Every new ID is in the repo's `ids.yaml`, the ledger only grew (no number removed or reused).
- [ ] No placeholder (`*-NEW-*`) is left (CK-C1).
- [ ] A need that is no longer wanted is `status: retired`, not deleted (D130).
- [ ] `status: valid` only for content that is meant to count; work in progress is `draft`.

## Links (trace rule, D5)
- [ ] The concrete need holds the link: `SYS-REQ :refines: SYS-NEED`, `SYS-NEED :raised_by: SYS-STH`,
      a need or objective `:addresses:` the problem statement, a test case `:verifies:` the requirement.
      Never a backlink.
- [ ] A domain requirement refines an upstream need or is `derived: true` with a `rationale`.
- [ ] EE and SW never link to each other; both link to `SYS-IF` (D36).

## One requirement
- [ ] One statement with one "shall". No "and" joining two behaviours.
- [ ] The sentence starts like its `ears` pattern (CK-E3): ubiquitous "The ...", event "When ...",
      state "While ...", optional "Where ...", unwanted "If ... then ...".
- [ ] Verifiable: a number with a unit, or a yes/no outcome. No "fast", "easy", "as needed".
- [ ] `min` / `max` / `nominal` appear as numbers in the sentence, followed by `unit` (CK-E2), and
      agree with the sentence (CK-E2 only warns).
- [ ] `quantity` names what is measured; `category` and `verification_method` are set.
- [ ] `verification_scope` (`logical` or `config`) and `configs` / `where` match the variants.
- [ ] Solution-free: says what, not how (no part numbers, unless it is a constraint).

## Stakeholders and needs
- [ ] Every `category: need` / `objective` has `raised_by`.
- [ ] Exactly one need has `category: problem`; other needs `addresses` only that one.
- [ ] A need speaks in the stakeholder's words, not as a system requirement.

## Build
- [ ] The strict docs build passes (CK-A6) and the model stubs were regenerated if needs changed
      (`curatrix gen stubs <repo>`, CK-D1).
