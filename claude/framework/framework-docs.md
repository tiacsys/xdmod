# Framework documentation (task 3.10)

Status: **AGREED 2026-11-14** (review answers → D120–D122). Built on D13, D20, D25, D98, D111 (`../decisions.md`), `doc-architecture.md` (`xdmod-manual`, `xdmod-ref`),
and the zdocs and firmhold manuals (Diátaxis, ADR folders) as models.

## 1. Goals

- Explain **XDMOD as a method plus tools**, like SYSMOD and Diátaxis explain theirs: what to do, in which order, why, and with which tool.
- Be **usable without the robot arm.** Examples come from the robot arm, but every page reads on its own.
- Be **written for people and agents alike**: plain, simple English (D20), short pages, one topic per page, stable anchors.
- Be **checked like everything else**: strict build, needs for method rules (question 2), and generated reference pages that can't drift from the code.

## 2. Structure (Diátaxis)

```
xdmod-manual/
  index                         what XDMOD is; the three key results of the brief; how to read this manual
  tutorials/
    first-workspace             bootstrap a workspace with a role, run checks, open the docs
    first-requirement           one need → requirement → model element → test, end to end (from the spike)
    first-change                change and retire a requirement; read needs-diff; fix downstream; affirm
  howto/
    add-a-requirement           EARS, value fields, ID placeholders, stubs
    add-a-model-element         SysML file per SYSMOD step, satisfy/allocate, regenerate needs
    add-a-view                  SysML view + @XdView, build, arrange in drawio, check
    add-a-pcba / add-a-part     KiCad / FreeCAD with trace fields, library rules, review report
    add-a-configuration         PLEML feature, binding, configuration, variant check
    add-a-test                  where it lives (D115), verifies links, results, HIL evidence
    cross-repo-change           branch names, PR order, bump PR, baseline
    work-as-an-agent            what agents may do, skills, limits, proposing affirmations
    make-a-baseline             gates, tag, release
  reference/
    trace-model                 need types, link-type table, rules R1–R7   (generated from needs_config.toml + text)
    id-scheme                   kinds, format, ledger                       (kind table generated)
    variant-rules               F1–F2, V1–V6, T1–T3
    checks                      check catalogue, stages, levels             (generated from curatrix)
    sysmod-mapping              SYSMOD steps → work products → files → docs
    repo-layouts                common pattern + per-repo layouts
    workspace                   paths, roles, group filters, environment
    glossary
  explanation/
    principles                  why concrete-holds-the-link, generated-committed-checked, text-first for agents
    v-model-and-traces          the V, link ownership, suspect links, coverage per configuration
    sysmod-and-sysml            how SYSMOD v5 is used with SysML v2 textual, stubs, contexts
    variants                    VAMOS/PLEML, 150 % models, configurations
    multi-repo                  west, submanifests, roles, bump bot, baselines
    humans-and-agents           roles, propose vs. affirm, provenance
    decisions/                  framework decisions as needs `XD-ADR-nnnn` (D120)
    rules/                      method rules as needs `XD-RULE-nnnn` (D121)
xdmod-ref/
  curatrix CLI                  generated from the argument parser
  curatrix API                  generated from docstrings (Sphinx autodoc)
  sphinx extensions             directives and options
  checks                        one `XD-CHECK` need per curatrix check, generated, each `enforces` an `XD-RULE` (D121)
  needs config                  rendered needs_config.toml
  SysML library                 XdView, trace metadata
```

## 3. Where the content comes from

| Manual part | Source today |
|---|---|
| explanation/principles, v-model-and-traces | `trace-model.md` §1, `checks.md` §1 |
| reference/trace-model, id-scheme, variant-rules | `trace-model.md`, `id-scheme.md`, `variants.md` |
| reference/sysmod-mapping, explanation/sysmod-and-sysml | `sysmod-work-products.md` |
| reference/checks | `checks.md` |
| explanation/multi-repo, reference/workspace | `repo-topology.md`, `command-layer.md` |
| reference/repo-layouts | `repo-layouts.md` |
| howto/add-a-view | `views.md` |
| howto/add-a-part | `freecad-storage.md` |
| explanation/humans-and-agents, howto/work-as-an-agent | `workflow.md` (3.11) |
| tutorials | the spike (`../notes/spike.md`), redone on the real repos in Phase 5 |

The `claude/framework/*.md` drafts are converted to rst pages when xdmod is created (Phase 4, task 4.2b). After that, **the manual is the master**, and the drafts are not kept up to date.

## 4. Rules for writing the manual

- Plain, simple English. One topic per page. Examples from the robot arm, marked as examples.
- Every rule the tools enforce links to the check that enforces it (`checks.md` IDs).
- Reference tables that come from code or config are **generated**, never typed.
- The manual builds strict with zdocs (D64c), and its links are checked.
- **Every mention of a decision, rule or check is a real reference** (`:need:` role), never bare text like "D37" (D120). This applies to all rst in every repo.
- Agent-readable output: the **sphinx-llm** extension (llms.txt / Markdown output) is tried in Phase 4 (D122).

## 5. Answered review questions (2026-11-14)

1. **Decisions become sphinx-needs** (D120). Framework decisions are `XD-ADR-nnnn` in the xdmod manual. Robot-arm decisions are `PRJ-DEC-nnnn` in the `robarm` overview doc in robarm-manifest. The old D-number is kept in a `legacy_id` field. In rst, every mention of a decision is a real `:need:` reference.
2. **Method rules are needs** `XD-RULE-nnnn` (D121). Each curatrix check is a generated `XD-CHECK` need that `enforces` a rule. ADRs link to the rules they introduce.
3. **Agent-readable docs:** try the **sphinx-llm** extension (D122).
