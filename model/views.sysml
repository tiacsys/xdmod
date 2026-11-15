// Views of the XDMOD self-model (D94). `curatrix views build xdmod` renders each view to
// views/<view>.drawio.svg; the XDMOD manual shows them with the sysml-view directive.
// Kinds follow the SysML v2 standard views: general (GeneralView), interconnection
// (InterconnectionView), actionflow (ActionFlowView), statetransition (StateTransitionView),
// and usecases (a general view of use cases and actors).
// `show` limits the relationships drawn in a general view; `compartments = "none"` hides them.
// SPDX-License-Identifier: Apache-2.0
package XdmodViews {
    doc /* The diagrams of the XDMOD manual. */
    private import XdTrace::*;

    // ------------------------------------------------------------------ domains and repos
    view workspaceRepos {
        doc /* The repos of a workspace, their domains, documents and design files. */
        @XdView { kind = "general"; direction = "DOWN"; }
        expose XdmodDomains::Workspace;
        expose XdmodDomains::Repository;
        expose XdmodDomains::SysEngRepo;
        expose XdmodDomains::EeRepo;
        expose XdmodDomains::MeRepo;
        expose XdmodDomains::SwRepo;
        expose XdmodDomains::IntegrationRepo;
        expose XdmodDomains::ManifestRepo;
        expose XdmodDomains::FrameworkRepo;
    }
    view workspaceInterconnection {
        doc /* How needs, pins and the framework flow between the repos of a workspace. */
        @XdView { kind = "interconnection"; root = "XdmodDomains::Workspace"; }
    }
    view artifactKinds {
        doc /* The kinds of files XDMOD knows: sources and committed generated files. */
        @XdView { kind = "general"; direction = "RIGHT"; show = "specialization"; compartments = "root"; }
        expose XdmodDomains::*;
        filter @SysML::ItemDefinition and not (@SysML::PartDefinition);
    }

    // ------------------------------------------------------------------ need types and trace links
    view needKinds {
        doc /* Every need type, grouped by its place in the V. */
        @XdView { kind = "general"; direction = "RIGHT"; show = "specialization"; compartments = "root"; }
        expose XdmodNeeds::**;
        filter @SysML::ItemDefinition;
    }
    view traceSystem {
        doc /* Trace links of systems engineering and integration tests (right to left). */
        @XdView { kind = "general"; direction = "LEFT"; show = "reference"; compartments = "none"; }
        expose XdmodNeeds::System::*;
        expose XdmodNeeds::Integration::*;
        filter @SysML::ItemDefinition;
    }
    view traceSoftware {
        doc /* Trace links of the software domain to the system level. */
        @XdView { kind = "general"; direction = "LEFT"; show = "reference"; compartments = "none"; }
        expose XdmodNeeds::Software::*;
        expose XdmodNeeds::System::SystemRequirement;
        expose XdmodNeeds::System::Interface;
        expose XdmodNeeds::System::SystemModelElement;
        filter @SysML::ItemDefinition;
    }
    view traceHardware {
        doc /* Trace links of the electrical and mechanical domains to the system level. */
        @XdView { kind = "general"; direction = "LEFT"; show = "reference"; compartments = "none"; }
        expose XdmodNeeds::Electrical::*;
        expose XdmodNeeds::Mechanical::*;
        expose XdmodNeeds::System::SystemRequirement;
        expose XdmodNeeds::System::Interface;
        expose XdmodNeeds::System::SystemModelElement;
        filter @SysML::ItemDefinition;
    }
    view traceResults {
        doc /* Test results point to the test cases they come from. */
        @XdView { kind = "general"; direction = "LEFT"; show = "reference,specialization"; compartments = "none"; }
        expose XdmodNeeds::Results::*;
        expose XdmodNeeds::Integration::*;
        expose XdmodNeeds::Software::SwTestCase;
        expose XdmodNeeds::Electrical::EeTestCase;
        expose XdmodNeeds::Mechanical::MeTestCase;
        filter @SysML::ItemDefinition;
    }
    view traceGovernance {
        doc /* Decisions, rules and checks of the framework and the project. */
        @XdView { kind = "general"; direction = "LEFT"; show = "reference"; compartments = "none"; }
        expose XdmodNeeds::Framework::*;
        filter @SysML::ItemDefinition;
    }

    // ------------------------------------------------------------------ behaviour
    view buildAndCheck {
        doc /* From sources to needs, views, documents and check results. */
        @XdView { kind = "actionflow"; root = "XdmodToolchain::BuildAndCheck"; direction = "RIGHT"; }
    }
    view changeProcess {
        doc /* A change from the first branch to the published documents. */
        @XdView { kind = "actionflow"; root = "XdmodWorkflow::ChangeProcess"; direction = "DOWN"; }
    }
    view needStatus {
        @XdView { kind = "statetransition"; root = "XdmodLifecycle::NeedStatus"; direction = "RIGHT"; }
    }
    view decisionStatus {
        @XdView { kind = "statetransition"; root = "XdmodLifecycle::DecisionStatus"; direction = "RIGHT"; }
    }
    view traceLinkStatus {
        @XdView { kind = "statetransition"; root = "XdmodLifecycle::TraceLink"; direction = "RIGHT"; }
    }
    view evidenceStatus {
        @XdView { kind = "statetransition"; root = "XdmodLifecycle::Evidence"; direction = "RIGHT"; }
    }

    // ------------------------------------------------------------------ roles
    view rolesAndUseCases {
        doc /* Who does what: people, agents and automation. */
        @XdView { kind = "usecases"; root = "XdmodRoles"; direction = "RIGHT"; }
    }
    view roleKinds {
        doc /* People and agents. */
        @XdView { kind = "general"; direction = "RIGHT"; }
        expose XdmodRoles::*;
        filter @SysML::PartDefinition;
    }
}
