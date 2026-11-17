// XDMOD self-model: life cycles of needs, decisions, trace links and HIL evidence.
// SPDX-License-Identifier: Apache-2.0
package XdmodLifecycle {
    doc /* States that the checks read: need status, decision status, suspect links and
         * evidence validity (D58, D60, D64e, D120, D130). */
    private import XdTrace::*;
    private import ScalarValues::*;

    // signals (what makes a transition fire)
    item def SetValid { doc /* a merged change sets status: valid (the merge is the approval, D51) */ }
    item def Retire { doc /* a merged change sets status: retired, before the need is deleted */ }
    item def Delete { doc /* the need is removed; its ID is never issued again */ }
    item def Revise { doc /* a newer decision changes part of this one */ }
    item def Supersede { doc /* a newer decision replaces this one */ }
    item def TargetChanged { doc /* the link target changed after the link was confirmed */ }
    item def HumanAffirmation { doc /* a person's commit confirms the link (agents only propose) */ }
    item def LinkRemoved { doc /* the link is deleted or retargeted instead */ }
    item def PinsChanged { doc /* the pinned SHAs or the firmware hash differ from the run */ }
    item def PinsMatch { doc /* the pins are back at the SHAs of the run (e.g. a revert) */ }

    state def NeedStatus {
        @See { needId = "XD-RULE-0020"; }
        doc /* The status field of every need. */
        entry; then draft;
        state draft { doc /* structure checks only, no coverage */ }
        state valid { doc /* all checks, counts for coverage */ }
        state retired { doc /* kept for the grace period; links to it are reported (XD-RULE-0011) */ }
        state deleted { doc /* gone from the sources; a generated need keeps a tombstone until the next baseline */ }
        transition first draft accept SetValid then valid;
        transition first valid accept Retire then retired;
        transition first draft accept Retire then retired;
        transition first retired accept Delete then deleted;
    }

    state def DecisionStatus {
        @See { needId = "XD-ADR-0109"; }
        doc /* decision_status of XD-ADR and PRJ-DEC; the newer decision holds the link. */
        entry; then accepted;
        state accepted;
        state revised;
        state superseded;
        transition first accepted accept Revise then revised;
        transition first accepted accept Supersede then superseded;
        transition first revised accept Supersede then superseded;
    }

    state def TraceLink {
        @See { needId = "XD-ADR-0121"; }
        doc /* A link held by the concrete need; suspect links block a baseline (XD-RULE-0014). */
        entry; then confirmed;
        state confirmed;
        state suspect;
        state removed;
        transition first confirmed accept TargetChanged then suspect;
        transition first suspect accept HumanAffirmation then confirmed;
        transition first suspect accept LinkRemoved then removed;
    }

    state def Evidence {
        @See { needId = "XD-ADR-0120"; }
        doc /* A HIL run record on the evidence branch (XD-RULE-0012, XD-RULE-0013). A new run
             * writes a new record; a record never changes. */
        attribute fromMainOrBaseline : Boolean;
        entry; then recorded;
        state recorded;
        state preview { doc /* from a PR branch: shown, never counted */ }
        state valid { doc /* counts as a test result */ }
        state stale { doc /* SHAs differ: a new run is needed */ }
        transition first recorded if fromMainOrBaseline then valid;
        transition first recorded if not fromMainOrBaseline then preview;
        transition first valid accept PinsChanged then stale;
        transition first stale accept PinsMatch then valid;
    }
}
