# ID prefix scheme (task 3.2)

Status: **AGREED 2026-11-14** (D78–D80). Built on D17 (new scheme, SEG IDs not reused), D64e (never reuse IDs) and
`trace-model.md` (need types). The ledger pattern follows the `safety` repo (`testids.yaml`, `assign_testids.py`).

## 1. Goals

- **Stable.** An ID never changes when its need is renamed, moved, or reworded.
- **Never reused.** A retired or deleted ID is never issued again.
- **Readable.** The ID says what kind of artifact it is.
- **Unique across the whole workspace.** Checked in the full-set build.
- **Works for humans and agents** in parallel PRs, with few merge conflicts.
- **Works inside every tool:** sphinx-needs IDs, SysML short names, KiCad field values, FreeCAD property values, Doxygen commands, test-report IDs.

## 2. Format

```
<DOMAIN>-<KIND>-<NNNN>   e.g.  SYS-REQ-0012, SW-TC-0103, EE-CMP-0007, INT-ITC-0003
TR-<TESTCASE-ID>-<RUN>   e.g.  TR-SW-TC-0103-3f9a1c2e   (test results only)
```

- `DOMAIN`: `SYS`, `SW`, `EE`, `ME` or `INT` (integration and system verification, D73); `XD` for the framework's own items and `PRJ` for project-level items (D120).
- `KIND`: 2–5 capital letters naming the need type within the domain (table below). Domain + kind together name the need type (D78).
- `NNNN`: a 4-digit number, zero-padded, issued per kind. Above 9999 it simply grows to 5 digits.
- `RUN`: the first 8 hex digits of the run record's hash (HIL run on the evidence branch in robarm-integration, D57, D73) or of the JUnit file. A test result is therefore unique per run.
- Regex: `^((SYS|SW|EE|ME|INT|XD|PRJ)-[A-Z]{2,5}-[0-9]{4,}|TR-(SYS|SW|EE|ME|INT)-[A-Z]{2,5}-[0-9]{4,}-[0-9a-f]{8})$`.
- **No project code in the sources** (D79). All robarm repos share one ID space. Where IDs leave the workspace (bundles, published `needs.json`, shared affirmatrix cases), a project code is put in front by the exporting tool, e.g. `RA:SYS-REQ-0012`. The separator is `:` (decided 2026-11-14).

## 3. Kinds

| Kind | Need type | Owner repo | Issued by |
|---|---|---|---|
| `SYS-STH` | Stakeholder | robarm-syseng | ledger (author) |
| `SYS-NEED` | Stakeholder need | robarm-syseng | ledger (author) |
| `SYS-UC` | Use case | robarm-syseng | ledger; written as the SysML short name |
| `SYS-REQ` | System requirement | robarm-syseng | ledger (author) |
| `SYS-IF` | Interface | robarm-syseng | ledger; SysML short name |
| `SYS-EL` | System model element | robarm-syseng | ledger; SysML short name `<'SYS-EL-0012'>` |
| `SYS-CFG` | Configuration (D107) | robarm-syseng | ledger; SysML short name |
| `SYS-FEAT` | Feature of the feature model (D107) | robarm-syseng | ledger; SysML short name |
| `INT-STC` | System test case | robarm-integration | ledger (author) |
| `INT-ITC` | Integration test case | robarm-integration | ledger (author) |
| `SW-REQ` | SW requirement | robarm-sw | ledger (author) |
| `SW-ARCH` | SW architecture element | robarm-sw | ledger (author) |
| `SW-DD` | SW detailed design element | robarm-sw | ledger (author) |
| `SW-IMPL` | Code unit | robarm-sw | ledger; written by a tool into a Doxygen tag, like safety's `@testid` |
| `SW-TC` | SW test case | robarm-sw | ledger; written by a tool into the ZTEST comment, like safety's `@testid` (D80) |
| `EE-REQ` | EE requirement | robarm-ee | ledger (author) |
| `EE-PCBA` | PCBA | robarm-ee | ledger; SysML short name in the EE model; the KiCad project refers to it (XD-ADR-0128) |
| `EE-PORT` | Connector port, port of an external part | robarm-ee | ledger; SysML short name in the EE model; KiCad connector field `portTypeID` refers to it (with `portName`, `portType`) |
| `EE-HAR` | Wiring harness | robarm-ee | ledger; SysML short name in the EE model; the WireViz YAML refers to it |
| `EE-CMP` | Circuit block / component | robarm-ee | ledger; KiCad hidden field `TraceID` |
| `EE-TC` | EE test case | robarm-ee | ledger (author) |
| `ME-REQ` | ME requirement | robarm-me | ledger (author) |
| `ME-ASM` | Assembly | robarm-me | ledger; SysML short name in the ME model; FreeCAD property `TraceID` refers to it (XD-ADR-0128) |
| `ME-PORT` | Mechanical interface | robarm-me | ledger; SysML short name in the ME model; FreeCAD LCS property `Port` refers to it |
| `ME-PART` | Part | robarm-me | ledger; FreeCAD property `TraceID` |
| `ME-TC` | ME test case | robarm-me | ledger (author) |
| `XD-ADR` | Framework decision (D120) | xdmod | ledger (author) |
| `XD-RULE` | Method rule (D121) | xdmod | ledger (author) |
| `XD-CHECK` | curatrix check (D121) | xdmod | ledger; written into the check's definition |
| `PRJ-DEC` | Project (robot-arm) decision (D120) | robarm-manifest | ledger (author) |
| `TR` | Test result | repo of the test case | derived from the test case ID + run hash; no ledger |

**Reserved non-need kind:** `SYS-VIEW` is used only as a SysML short name for views (D94). It is not a need, has no row in the trace model, and is skipped by check CK-A3; its numbers still come from the ledger.

## 4. Issuing IDs: the ledger

- Each repo keeps **one ledger file**, `ids.yaml`, with **every number issued per kind** that the repo owns, one per line (D133). It is append-only, like safety's `testids.yaml`. Listing every number (not just the last) means that two PRs issuing the same number touch the same line, so git reports a conflict:

  ```yaml
  # Every number issued per kind, one per line. Append-only: a number here is never issued again.
  SYS-REQ:
    - 41
    - 42
  SYS-NEED:
    - 17
  ```

- `curatrix ids` (D98) issues new IDs. It reads the ledger and the IDs already used in the sources, takes the next free number, writes it into the source (rst directive, SysML short name, Doxygen tag, KiCad field or FreeCAD property), and bumps the ledger.
- **Placeholders.** An author or agent may write a need with a placeholder ID such as `SYS-REQ-NEW-a`. The tool replaces placeholders with real IDs. The local check (D46) rejects placeholders, so they never reach `main`.
- **Parallel PRs.** Two PRs may issue the same number. The second one to rebase gets a ledger conflict. The fix is to rerun the tool, which renumbers that PR's new IDs. Rulesets also **require PRs to be up to date with `main` before merge** (D133), so CI's duplicate check runs on the combined state. The full-set build checks for duplicates across all repos.
- **Retiring.** A retired need keeps its ID with `status: retired` (D64e, D130 for generated needs). When the need is finally deleted, the ledger still holds its number, so the number is never issued again.

## 5. Where the ID lives in each tool

| Tool | Where the ID is written | Read by |
|---|---|---|
| sphinx-needs (rst) | `:id:` of the directive | Sphinx |
| SysML v2 | short name: `part def <'SYS-EL-0012'> ArmController { … }`; stubs use the requirement's ID | Pilot JSON → extractor |
| KiCad | hidden symbol or sheet field `TraceID`; links in further hidden fields (`Realizes`, `Satisfies`, `Conforms`) | `kicad-cli` XML netlist → extractor |
| FreeCAD | object properties `TraceID`, `Realizes`, `Satisfies`, `Conforms` | `Document.xml` → extractor |
| Doxygen / C | `@xdid{SW-IMPL-0004}`, `\satisfies`, `\verifies`; test IDs like safety's `@testid` | Doxygen XML → zdocs |
| Twister / JUnit | the test case's `SW-TC` ID in the test name or a property | sphinx-test-reports / run record → `TR` |
| Devicetree | `trace-id` property of our own binding (D64f) | `edt.pickle` → check |

## 6. Rules the check enforces

1. The ID matches the regex, and its kind matches the need type.
2. Each ID is unique within the repo (local check) and across the workspace (full-set build).
3. No placeholders on `main`.
4. Every ID in the sources is at most the ledger's number for its kind. So the ledger is never behind the sources.
5. A test-report ID uses lowercase `tr_` as zdocs/test-reports produce it today. It is mapped to `TR-…` by our extractor. (The spike found that test-reports IDs are lowercase.)

## 7. Answered review questions (2026-11-14)

1. **Number width:** 4 digits (D78).
2. **Kind codes:** two parts, domain + kind, e.g. `SYS-REQ`, `SW-TC`, `EE-CMP`, `ME-PART` (D78).
3. **Project code:** not in the sources; added only where IDs leave the workspace (D79).
4. **SW test IDs:** issued from the ledger and written into the ZTEST comment (D80).

5. **Project code separator:** `:`, e.g. `RA:SYS-REQ-0012`, so it can't be confused with the domain part.
