// XDMOD self-model: the change workflow, from a branch to the published documents.
// SPDX-License-Identifier: Apache-2.0
package XdmodWorkflow {
    doc /* Trunk-based change process with agent review and a person's merge (workflow.md §3,
         * D43, D52, D58, D89, D115, D126). */
    private import XdTrace::*;
    private import ScalarValues::*;

    // Kinds of task. Each action below is typed by one of them: the action definition says what
    // kind of task the action is, and so who may do it.
    action def AgentWork { doc /* authoring work, by an agent or a person, on a branch */ }
    action def AgentReview { doc /* first-pass review by an agent that did not author the change */ }
    action def PersonDecision {
        @See { needId = "XD-ADR-0051"; }
        doc /* a decision only a person makes: the owner or a domain engineer (review, merge, affirm) */
    }
    action def OwnerDecision { doc /* a decision only the owner makes */ }
    action def CiRun { doc /* run by GitHub Actions */ }
    action def BotRun { doc /* run by the scheduled bump bot */ }

    action def ChangeProcess {
        @See { needId = "XD-ADR-0043"; }
        doc /* One change across one or more repos, with one branch name in every repo. */
        attribute localChecksPass : Boolean;
        attribute ciPasses : Boolean;
        attribute reviewClean : Boolean;
        attribute approved : Boolean;
        attribute linksSuspect : Boolean;

        action 'start work set' : AgentWork {
            @See { needId = "XD-ADR-0114"; }
            doc /* curatrix work start: worktrees, the same branch name in every repo (D52). */
        }
        action 'edit, gen, ids fix' : AgentWork {
            @See { needId = "XD-RULE-0017"; }
            doc /* Edit content, regenerate generated files, give placeholder IDs their numbers. */
        }
        action 'check --stage local' : AgentWork {
            @See { needId = "XD-RULE-0032"; }
        }
        action 'open PRs' : AgentWork {
            @See { needId = "XD-ADR-0065"; }
            doc /* One PR per repo, with sibling PRs, affected needs and the provenance trailer. */
        }
        action 'CI check' : CiRun {
            @See { needId = "XD-ADR-0116"; }
            doc /* Required checks; sibling repos resolved to the same branch. */
        }
        action 'agent review' : AgentReview {
            @See { needId = "XD-ADR-0115"; }
        }
        action 'human review' : PersonDecision;
        action 'merge, upstream first' : PersonDecision;
        action 'prepare affirmations' : AgentWork {
            @See { needId = "XD-ADR-0121"; }
            doc /* Reason and diff for each link the change made suspect. */
        }
        action 'affirm suspect links' : PersonDecision {
            @See { needId = "XD-RULE-0014"; }
        }

        first start then 'start work set';
        first 'start work set' then 'edit, gen, ids fix';
        first 'edit, gen, ids fix' then 'check --stage local';
        first 'check --stage local' then localGate;
        decide localGate;
            if localChecksPass then 'open PRs';
            else 'edit, gen, ids fix';
        first 'open PRs' then 'CI check';
        first 'CI check' then ciGate;
        decide ciGate;
            if ciPasses then 'agent review';
            else 'edit, gen, ids fix';
        first 'agent review' then reviewGate;
        decide reviewGate;
            if reviewClean then 'human review';
            else 'edit, gen, ids fix';
        first 'human review' then mergeGate;
        decide mergeGate;
            if approved then 'merge, upstream first';
            else 'edit, gen, ids fix';
        first 'merge, upstream first' then suspectGate;
        decide suspectGate;
            if linksSuspect then 'prepare affirmations';
            else done;
        first 'prepare affirmations' then 'affirm suspect links';
        first 'affirm suspect links' then done;
    }

    action def PinBump {
        @See { needId = "XD-ADR-0081"; }
        doc /* Scheduled, independent of any single change: the bump bot moves the manifest pins. */
        attribute fullSetPasses : Boolean;

        action 'collect new SHAs, bump PR' : BotRun {
            @See { needId = "XD-ADR-0054"; }
        }
        action 'full-set check' : CiRun;
        action 'merge bump PR' : OwnerDecision;
        action 'publish latest' : CiRun {
            @See { needId = "XD-ADR-0048"; }
        }
        action 'fix in a change' : AgentWork {
            doc /* A failing full set is fixed by a normal change in the repo that broke it. */
        }

        first start then 'collect new SHAs, bump PR';
        first 'collect new SHAs, bump PR' then 'full-set check';
        first 'full-set check' then fullSetGate;
        decide fullSetGate;
            if fullSetPasses then 'merge bump PR';
            else 'fix in a change';
        first 'merge bump PR' then 'publish latest';
        first 'publish latest' then done;
        first 'fix in a change' then done;
    }
}
