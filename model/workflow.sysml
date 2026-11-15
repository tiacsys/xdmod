// XDMOD self-model: the change workflow, from a branch to the published documents.
// SPDX-License-Identifier: Apache-2.0
package XdmodWorkflow {
    doc /* Trunk-based change process with agent review and owner merge (workflow.md, D43,
         * D52, D115, D126). Each action is typed by who performs it. */
    private import XdTrace::*;
    private import ScalarValues::*;

    // who performs an action
    action def AgentTask { doc /* done by an agent (or a person) on its own branch */ }
    action def ReviewerTask { doc /* done by an agent that did not author the change */ }
    action def OwnerTask { doc /* done only by the owner: decide, merge, affirm */ }
    action def CiTask { doc /* done by GitHub Actions */ }
    action def BotTask { doc /* done by the scheduled bump bot */ }

    action def ChangeProcess {
        @See { needId = "XD-ADR-0043"; }
        doc /* One change across one or more repos, with one branch name in every repo. */
        attribute localChecksPass : Boolean;
        attribute reviewClean : Boolean;
        attribute approved : Boolean;

        action 'start work set' : AgentTask {
            @See { needId = "XD-ADR-0114"; }
            doc /* curatrix work start: worktrees, the same branch name in every repo (D52). */
        }
        action 'edit on branch' : AgentTask;
        action 'ids fix' : AgentTask {
            @See { needId = "XD-RULE-0017"; }
            doc /* Placeholder IDs in new needs get their numbers from the ledger. */
        }
        action 'check --stage local' : AgentTask {
            @See { needId = "XD-RULE-0032"; }
        }
        action 'push, open PR' : AgentTask {
            @See { needId = "XD-ADR-0065"; }
            doc /* Commit trailer and provenance line on everything posted. */
        }
        action 'CI check' : CiTask {
            @See { needId = "XD-ADR-0116"; }
            doc /* Required checks; sibling repos resolved to the same branch. */
        }
        action 'agent review' : ReviewerTask {
            @See { needId = "XD-ADR-0115"; }
        }
        action 'owner review' : OwnerTask {
            @See { needId = "XD-ADR-0051"; }
        }
        action 'rebase merge' : OwnerTask;
        action 'bump pins' : BotTask {
            @See { needId = "XD-ADR-0081"; }
            doc /* Scheduled poll; opens a bump PR on the manifest repo. */
        }
        action 'full-set check' : CiTask;
        action 'merge bump PR' : OwnerTask;
        action 'publish latest' : CiTask {
            @See { needId = "XD-ADR-0048"; }
        }

        first start then 'start work set';
        first 'start work set' then 'edit on branch';
        first 'edit on branch' then 'ids fix';
        first 'ids fix' then 'check --stage local';
        first 'check --stage local' then localGate;
        decide localGate;
            if localChecksPass then 'push, open PR';
            else 'edit on branch';
        first 'push, open PR' then 'CI check';
        first 'CI check' then 'agent review';
        first 'agent review' then reviewGate;
        decide reviewGate;
            if reviewClean then 'owner review';
            else 'edit on branch';
        first 'owner review' then ownerGate;
        decide ownerGate;
            if approved then 'rebase merge';
            else 'edit on branch';
        first 'rebase merge' then 'bump pins';
        first 'bump pins' then 'full-set check';
        first 'full-set check' then 'merge bump PR';
        first 'merge bump PR' then 'publish latest';
        first 'publish latest' then done;
    }
}
