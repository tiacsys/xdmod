---
name: xd-sysmod-stakeholders-and-needs
description: Use when you write the front of the SYSMOD chain in robarm-syseng (plan tasks 6.1 and 6.2) - project, problem statement, stakeholders, stakeholder needs, system objectives, system context and use cases (SYSMOD steps 01, 03-08) - as SYS-STH / SYS-NEED rst needs and SYS-EL / SYS-IF / SYS-UC model elements.
---

# SYSMOD steps 01-08: stakeholders, needs, context, use cases

Read first: `robarm-syseng/claude/CLAUDE.md`, `xdmod/claude/framework/sysmod-work-products.md`
(§2 table, §5 mapping), `xdmod/claude/framework/trace-model.md`, the need types `sys-sth`,
`sys-need`, `sys-uc` in `xdmod/needs/needs_config.toml`, and the canary in
`robarm-syseng/docs/se-req/canary.rst` and `model/product.sysml` as a worked example.
SYSMOD itself: https://mbse4u.com/sysmod/ (keep its step names).

Work in a worktree set (`curatrix work start <branch> robarm-syseng`). **One SYSMOD step per PR**
(CK-H7 warns on size); stack the steps (`--base <previous step branch>`, `workflow.md` §3a).

## Where each step goes

| Step | Work product | Where | Need |
|---|---|---|---|
| 01 | Project: owner, purpose | `model/project.sysml`, short | - |
| 03 | Problem statement | `docs/se-req/`, one `sys-need` with `category: problem` | `SYS-NEED` |
| 04 | Stakeholders | `docs/se-req/`, `sys-sth` | `SYS-STH` |
| 05 | Stakeholder needs | `docs/se-req/`, `sys-need` with `category: need` | `SYS-NEED` |
| 06 | System idea, objectives | idea in `model/context.sysml`; objectives as `sys-need` with `category: objective` | `SYS-NEED` |
| 07 | System context: actors, system ports, interfaces | `model/context.sysml` | `SYS-EL` (`layer: context`), `SYS-IF` |
| 08 | Use cases | `model/usecases.sysml`: a `use case def` with the ID that specializes `SYSMOD::SystemUseCase` | `SYS-UC` |

Task 6.1 = steps 01, 03, 04, 06, 07. Task 6.2 = steps 05, 08. Step 02 (brownfield) is skipped.

## Need types and links (needs_config.toml)

| Type | Required fields | Links it holds |
|---|---|---|
| `sys-sth` | `status` | none (it is the root) |
| `sys-need` | `status`, `category` (`problem`, `objective`, `need`) | `raised_by` -> `sys-sth` (required for `need` and `objective`); `addresses` -> the `problem` need only |
| `sys-uc` | (from the model) | `addresses` -> `sys-need`, at least one |

The concrete side holds the link (D5): a need says who raised it; a stakeholder never lists its
needs. Backlinks are computed.

## rst pattern (docs/se-req)

```rst
.. sys-sth:: Hobby builder
   :id: SYS-STH-NEW-hobby
   :status: draft

   A person who builds and programs the arm at home. Categories, risk, effort: ...

.. sys-need:: Teach a pose by hand
   :id: SYS-NEED-NEW-teach
   :status: draft
   :category: need
   :raised_by: SYS-STH-NEW-hobby
   :addresses: SYS-NEED-NEW-problem

   The hobby builder wants to move the leader arm by hand and see the follower copy it.
```

- Write a need in the stakeholder's words: a want or a problem, not a "shall".
- Use SYSMOD's stakeholder fields (categories, risk, effort) in the text.
- Placeholders and then `curatrix ids fix robarm-syseng` (skill `xd-issue-ids`). Same tag = same
  ID in every file, so `:raised_by: SYS-STH-NEW-hobby` resolves too.
- Start new needs as `status: draft`; set `valid` when the owner agreed the content.
- Content for the robot arm only; the canary belongs to the configuration `canary` (P5-16).

## Model pattern (context and use cases)

```sysml
package RobArmUseCases {
    private import XdTrace::*;
    private import NeedStubs::*;
    use case def <'SYS-UC-NEW-mirror'> MirrorPose :> SYSMOD::SystemUseCase {
        doc /* The follower copies the leader. */
    }
    dependency from MirrorPose to sys_need_0002;   // SYS-UC addresses SYS-NEED
}
```

- An element becomes a need only when its short name is an ID **and** it has a trace link (D129).
  The definition holds the ID, not the usage (D128). So a use case is always a `use case def`
  with the ID, specializing `SYSMOD::SystemUseCase`; the context uses it
  (`use case mirror : MirrorPose;`) without an ID.
- Needs are referenced through the generated stubs (`sys_need_nnnn`, `sys_sth_nnnn` in
  `model/generated/NeedStubs.sysml`). Never edit that file.
- Context elements carry `@Trace { layer = "context"; }` (on the element or the package).
- Interfaces between domains (`SYS-IF`) live in `context.sysml`, so EE, ME and SW can link to them.

## Pitfalls (from the canary)

- **Name clashes:** do not name a usage like a stub attribute (`unit`, `quantity`, `max`, `ears`).
  `satisfy ... by unit` resolved to the stub's `unit` attribute and the link went missing silently.
- **File order:** the Pilot reads model files one by one in name order. `context.sysml` cannot use
  a name from `usecases.sysml`. Put a dependency in the later file.
- **Nested packages** are written `public package X` (curatrix reads lines starting with `package`
  as top-level packages).
- `raised_by` stays an rst link; concern stubs have no stakeholder parameter.

## Order of work and checks

1. Write the rst needs with placeholders, then the model elements.
2. `curatrix ids fix robarm-syseng` (placeholders fail the strict docs build).
3. `curatrix docs robarm-syseng`, then `curatrix gen all robarm-syseng` (stubs from the built needs,
   then model JSON and model needs).
4. `curatrix views build robarm-syseng` if a view shows the changed elements.
5. `curatrix check robarm-syseng --stage local`. Commit the generated files with the change.
6. PR text: the SYSMOD step, the new needs, and that review uses `checklists/requirements.md` and
   `checklists/model.md`.
