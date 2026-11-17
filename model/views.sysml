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

    // ------------------------------------------------------------------ one domain at a time
    // Each of the five domains has two views: its repo with the documents and design files it
    // holds, and its need types with the trace links inside the domain. A type's category (its
    // general type) is written in its header as `:> Requirement`.
    view sysRepo {
        doc /* The repo of systems engineering (SYS): its documents and design files. */
        @XdView { kind = "general"; direction = "RIGHT"; show = "composition"; compartments = "all,doc"; }
        expose XdmodDomains::SysEngRepo;
        expose XdmodDomains::SysmlModel;
        expose XdmodDomains::NeedStubs;
        expose XdmodDomains::ModelJson;
        expose XdmodDomains::GeneratedNeeds;
        expose XdmodDomains::DrawioView;
        expose XdmodDomains::Document;
    }
    view sysNeeds {
        doc /* The need types of systems engineering (SYS) and the trace links inside the domain. */
        @XdView { kind = "general"; direction = "LEFT"; show = "reference"; compartments = "none"; }
        expose XdmodNeeds::System::*;
        filter @SysML::ItemDefinition;
    }
    view eeRepo {
        doc /* The repo of electrical engineering (EE): its documents and design files. */
        @XdView { kind = "general"; direction = "RIGHT"; show = "composition"; compartments = "all,doc"; }
        expose XdmodDomains::EeRepo;
        expose XdmodDomains::KicadProject;
        expose XdmodDomains::PrototypeWiring;
        expose XdmodDomains::TestSuite;
        expose XdmodDomains::GeneratedNeeds;
        expose XdmodDomains::Document;
    }
    view eeNeeds {
        doc /* The need types of electrical engineering (EE) and the trace links inside the domain. */
        @XdView { kind = "general"; direction = "LEFT"; show = "reference"; compartments = "none"; }
        expose XdmodNeeds::Electrical::*;
        expose XdmodNeeds::Results::AnyTestCaseResult;
        filter @SysML::ItemDefinition;
    }
    view meRepo {
        doc /* The repo of mechanical engineering (ME): its documents and design files. */
        @XdView { kind = "general"; direction = "RIGHT"; show = "composition"; compartments = "all,doc"; }
        expose XdmodDomains::MeRepo;
        expose XdmodDomains::FreecadFile;
        expose XdmodDomains::TestSuite;
        expose XdmodDomains::GeneratedNeeds;
        expose XdmodDomains::Document;
    }
    view meNeeds {
        doc /* The need types of mechanical engineering (ME) and the trace links inside the domain. */
        @XdView { kind = "general"; direction = "LEFT"; show = "reference"; compartments = "none"; }
        expose XdmodNeeds::Mechanical::*;
        expose XdmodNeeds::Results::AnyTestCaseResult;
        filter @SysML::ItemDefinition;
    }
    view swRepo {
        doc /* The repo of software (SW): its documents and design files. */
        @XdView { kind = "general"; direction = "RIGHT"; show = "composition"; compartments = "all,doc"; }
        expose XdmodDomains::SwRepo;
        expose XdmodDomains::ZephyrApp;
        expose XdmodDomains::TestSuite;
        expose XdmodDomains::Document;
    }
    view swNeeds {
        doc /* The need types of software (SW) and the trace links inside the domain. */
        @XdView { kind = "general"; direction = "LEFT"; show = "reference"; compartments = "none"; }
        expose XdmodNeeds::Software::*;
        expose XdmodNeeds::Results::AnyTestCaseResult;
        filter @SysML::ItemDefinition;
    }
    view intRepo {
        doc /* The repo of system-level verification (INT): its documents and design files. */
        @XdView { kind = "general"; direction = "RIGHT"; show = "composition"; compartments = "all,doc"; }
        expose XdmodDomains::IntegrationRepo;
        expose XdmodDomains::TestSuite;
        expose XdmodDomains::HilSetup;
        expose XdmodDomains::RunRecord;
        expose XdmodDomains::Document;
    }
    view intNeeds {
        doc /* The need types of system-level verification (INT) and the trace links inside the domain. */
        @XdView { kind = "general"; direction = "LEFT"; show = "reference"; compartments = "none"; }
        expose XdmodNeeds::Verification::*;
        expose XdmodNeeds::Results::AnyTestCaseResult;
        filter @SysML::ItemDefinition;
    }

    // ------------------------------------------------------------------ two domains at a time
    // Only the relations between the two domains are drawn. By the trace rule, the engineering
    // domains and system-level verification link to systems engineering; peer domains (EE, ME,
    // SW) do not link to each other but meet at a shared SYS-IF (XD-RULE-0001).
    view sysSw {
        doc /* Trace links from software to systems engineering. */
        @XdView { kind = "general"; direction = "LEFT"; show = "reference"; compartments = "none";
                  between = "XdmodNeeds::System, XdmodNeeds::Software"; }
        expose XdmodNeeds::System::*;
        expose XdmodNeeds::Software::*;
        filter @SysML::ItemDefinition;
    }
    view sysEe {
        doc /* Trace links from electrical engineering to systems engineering. */
        @XdView { kind = "general"; direction = "LEFT"; show = "reference"; compartments = "none";
                  between = "XdmodNeeds::System, XdmodNeeds::Electrical"; }
        expose XdmodNeeds::System::*;
        expose XdmodNeeds::Electrical::*;
        filter @SysML::ItemDefinition;
    }
    view sysMe {
        doc /* Trace links from mechanical engineering to systems engineering. */
        @XdView { kind = "general"; direction = "LEFT"; show = "reference"; compartments = "none";
                  between = "XdmodNeeds::System, XdmodNeeds::Mechanical"; }
        expose XdmodNeeds::System::*;
        expose XdmodNeeds::Mechanical::*;
        filter @SysML::ItemDefinition;
    }
    view sysInt {
        doc /* Trace links from system-level verification to systems engineering. */
        @XdView { kind = "general"; direction = "LEFT"; show = "reference"; compartments = "none";
                  between = "XdmodNeeds::System, XdmodNeeds::Verification"; }
        expose XdmodNeeds::System::*;
        expose XdmodNeeds::Verification::*;
        filter @SysML::ItemDefinition;
    }

    // ------------------------------------------------------------------ the whole workspace
    view workspaceNeeds {
        doc /* How needs flow between the repos: from the abstract to the concrete side. */
        @XdView { kind = "interconnection"; root = "XdmodDomains::Workspace"; direction = "DOWN";
                  show = "needs, upstream, fullSet"; }
    }
    view workspacePins {
        doc /* The framework serves every repo; the manifest pins every repo. */
        @XdView { kind = "interconnection"; root = "XdmodDomains::Workspace"; direction = "DOWN";
                  show = "framework, pin, pins"; }
    }
    view repoLayout {
        doc /* What every repo has, whatever its domain. */
        @XdView { kind = "general"; direction = "RIGHT"; show = "composition"; compartments = "doc"; }
        expose XdmodDomains::Repository;
        expose XdmodDomains::ChecksConfig;
        expose XdmodDomains::IdLedger;
        expose XdmodDomains::ToolPins;
        expose XdmodDomains::DocRegistry;
        expose XdmodDomains::AgentMaterial;
    }
    view frameworkRepos {
        doc /* The two repos outside the domains: the framework and the manifest. */
        @XdView { kind = "general"; direction = "RIGHT"; show = "composition"; compartments = "all,doc"; }
        expose XdmodDomains::FrameworkRepo;
        expose XdmodDomains::ManifestRepo;
        expose XdmodDomains::NeedsConfig;
        expose XdmodDomains::SysmlLibrary;
        expose XdmodDomains::CuratrixTool;
        expose XdmodDomains::ReusableWorkflow;
        expose XdmodDomains::SysmlModel;
        expose XdmodDomains::DrawioView;
        expose XdmodDomains::Document;
        expose XdmodDomains::WestManifest;
    }
    view artifactKinds {
        doc /* The kinds of files: sources, committed generated files, build output. The plain source
             * kinds (documents, models, configuration) are in the repo views. */
        @XdView { kind = "general"; direction = "RIGHT"; show = "specialization"; compartments = "doc"; }
        expose XdmodDomains::Artifact;
        expose XdmodDomains::SourceArtifact;
        expose XdmodDomains::GeneratedArtifact;
        expose XdmodDomains::BuildOutput;
        expose XdmodDomains::CadSource;
        expose XdmodDomains::CodeSource;
        expose XdmodDomains::NeedStubs;
        expose XdmodDomains::ModelJson;
        expose XdmodDomains::GeneratedNeeds;
        expose XdmodDomains::DrawioView;
        expose XdmodDomains::RunRecord;
        expose XdmodDomains::NeedsExport;
        expose XdmodDomains::HtmlSite;
        expose XdmodDomains::CheckReport;
    }
    view needCategories {
        doc /* The general need with its link types, and the categories of need types (place in the V). */
        @XdView { kind = "general"; direction = "DOWN"; show = "specialization"; compartments = "root"; }
        expose XdmodNeeds::Need;
        expose XdmodNeeds::Origin;
        expose XdmodNeeds::Requirement;
        expose XdmodNeeds::Architecture;
        expose XdmodNeeds::DesignElement;
        expose XdmodNeeds::TestCase;
        expose XdmodNeeds::TestResult;
        expose XdmodNeeds::Governance;
    }
    view testResults {
        doc /* The kinds of test results: run results and imported JUnit reports. */
        @XdView { kind = "general"; direction = "DOWN"; show = "specialization"; compartments = "none"; }
        expose XdmodNeeds::TestResult;
        expose XdmodNeeds::Results::*;
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
    view pinBump {
        doc /* The scheduled bump of the manifest pins, and publishing. */
        @XdView { kind = "actionflow"; root = "XdmodWorkflow::PinBump"; direction = "DOWN"; }
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
