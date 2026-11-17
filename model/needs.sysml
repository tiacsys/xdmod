// XDMOD self-model: need types and link types (the trace model).
// The short name of each item def is the sphinx-needs directive (`sys-req`); each link type is a
// `ref` feature on the need type that holds the link, i.e. on the concrete side (XD-RULE-0001,
// XD-RULE-0002). A link with several target types is one feature per target type, each subsetting
// the general link feature of Need. The curatrix test test_self_model.py compares this package
// with needs/needs_config.toml, so the two cannot drift apart.
// SPDX-License-Identifier: Apache-2.0
package XdmodNeeds {
    doc /* Need types and link types of XDMOD (trace-model.md, needs_config.toml). */
    private import XdTrace::*;
    private import ScalarValues::*;

    enum def NeedStatus {
        enum draft;
        enum valid;
        enum retired;
    }

    // ------------------------------------------------------------------ the general need
    abstract item def Need {
        @See { needId = "XD-RULE-0007"; }
        doc /* Every need has an ID <DOMAIN>-<KIND>-<NNNN> from the ledger and a status. The link
             * features are declared here once and specialised by the need types below. */
        attribute id : String;
        attribute status : NeedStatus;

        abstract ref item raised_by : Need[0..*];
        abstract ref item addresses : Need[0..*];
        abstract ref item refines : Need[0..*];
        abstract ref item satisfies : Need[0..*];
        abstract ref item realizes : Need[0..*];
        abstract ref item conforms : Need[0..*];
        abstract ref item implements : Need[0..*];
        abstract ref item part_of : Need[0..*];
        abstract ref item connects : Need[0..*];
        abstract ref item configures : Need[0..*];
        abstract ref item verifies : Need[0..*];
        abstract ref item result_of : Need[0..*];
        abstract ref item revises : Need[0..*];
        abstract ref item supersedes : Need[0..*];
        abstract ref item decided_by : Need[0..*];
        abstract ref item enforces : Need[0..*];
        abstract ref item follows : Need[0..*];
    }

    // ------------------------------------------------------------------ categories (place in the V)
    abstract item def Origin :> Need { doc /* Who wants what: stakeholders and their needs. */ }
    abstract item def Requirement :> Need { @See { needId = "XD-ADR-0039"; } doc /* EARS requirements. */ }
    abstract item def Architecture :> Need { @See { needId = "XD-ADR-0118"; } doc /* System model elements that became needs. */ }
    abstract item def DesignElement :> Need { doc /* Domain design: generated from code, KiCad and FreeCAD, or written in rst. */ }
    abstract item def TestCase :> Need { @See { needId = "XD-ADR-0104"; } doc /* Tests live by what they verify. */ }
    abstract item def TestResult :> Need { @See { needId = "XD-RULE-0013"; } doc /* Results of test runs and HIL evidence. */ }
    abstract item def Governance :> Need { @See { needId = "XD-ADR-0109"; } doc /* Decisions, rules and checks. */ }

    // ------------------------------------------------------------------ systems engineering
    package System {
        item def <'sys-sth'> Stakeholder :> Origin;
        item def <'sys-need'> StakeholderNeed :> Origin {
            ref item :>> raised_by : Stakeholder[0..*];
            ref item :>> addresses : StakeholderNeed[0..*];
        }
        item def <'sys-uc'> UseCase :> Architecture {
            ref item :>> addresses : StakeholderNeed[1..*];
        }
        item def <'sys-req'> SystemRequirement :> Requirement {
            ref item :>> refines : StakeholderNeed[1..*];
        }
        item def <'sys-if'> Interface :> Architecture;
        item def <'sys-el'> SystemModelElement :> Architecture {
            ref item :>> satisfies : SystemRequirement[0..*];
            ref item realizesUseCase : UseCase[0..*] :> realizes;
            ref item realizesElement : SystemModelElement[0..*] :> realizes;
        }
        item def <'sys-cfg'> Configuration :> Architecture {
            ref item :>> configures : SystemModelElement[1..*];
        }
        item def <'sys-feat'> Feature :> Architecture;
    }

    // ------------------------------------------------------------------ system-level verification
    package Verification {
        doc /* The INT domain: system and integration tests in robarm-integration (XD-ADR-0104). */
        item def <'int-stc'> SystemTestCase :> TestCase {
            ref item :>> verifies : System::SystemRequirement[1..*];
        }
        item def <'int-itc'> IntegrationTestCase :> TestCase {
            ref item :>> verifies [1..*];
            ref item verifiesRequirement : System::SystemRequirement[0..*] :> verifies;
            ref item verifiesInterface : System::Interface[0..*] :> verifies;
        }
    }

    // ------------------------------------------------------------------ software
    package Software {
        item def <'sw-req'> SwRequirement :> Requirement {
            ref item refinesRequirement : System::SystemRequirement[0..*] :> refines;
            ref item refinesInterface : System::Interface[0..*] :> refines;
        }
        item def <'sw-arch'> SwArchitectureElement :> DesignElement {
            ref item :>> realizes : System::SystemModelElement[0..*];
            ref item :>> satisfies : SwRequirement[0..*];
            ref item conformsInterface : System::Interface[0..*] :> conforms;
            // the one exception to the peer rule: SW may conform to the board model of EE (5.14)
            ref item conformsBoard : Electrical::Pcba[0..*] :> conforms;
            ref item conformsPort : Electrical::Port[0..*] :> conforms;
        }
        item def <'sw-dd'> SwDetailedDesignElement :> DesignElement {
            ref item :>> refines : SwArchitectureElement[1..*];
            ref item :>> satisfies : SwRequirement[0..*];
            ref item conformsInterface : System::Interface[0..*] :> conforms;
            // the one exception to the peer rule: SW may conform to the board model of EE (5.14)
            ref item conformsBoard : Electrical::Pcba[0..*] :> conforms;
            ref item conformsPort : Electrical::Port[0..*] :> conforms;
        }
        item def <'sw-impl'> CodeUnit :> DesignElement {
            @See { needId = "XD-ADR-0070"; }
            ref item :>> implements [1..*];
            ref item implementsDesign : SwDetailedDesignElement[0..*] :> implements;
            ref item implementsArchitecture : SwArchitectureElement[0..*] :> implements;
            ref item :>> satisfies : SwRequirement[0..*];
        }
        item def <'sw-tc'> SwTestCase :> TestCase {
            ref item :>> verifies [1..*];
            ref item verifiesRequirement : SwRequirement[0..*] :> verifies;
            ref item verifiesDesign : SwDetailedDesignElement[0..*] :> verifies;
        }
    }

    // ------------------------------------------------------------------ electrical
    package Electrical {
        item def <'ee-req'> EeRequirement :> Requirement {
            ref item refinesRequirement : System::SystemRequirement[0..*] :> refines;
            ref item refinesInterface : System::Interface[0..*] :> refines;
        }
        item def <'ee-pcba'> Pcba :> DesignElement {
            @See { needId = "XD-ADR-0023"; }
            ref item :>> realizes : System::SystemModelElement[0..*];
            ref item :>> satisfies : EeRequirement[0..*];
            ref item :>> conforms : System::Interface[0..*];
        }
        item def <'ee-port'> Port :> DesignElement {
            @See { needId = "XD-ADR-0133"; }
            doc /* A connector port with its pin map, generated from the EE model. */
            ref item :>> conforms : System::Interface[0..*];
            ref item :>> part_of : Pcba[0..*];
        }
        item def <'ee-har'> Harness :> DesignElement {
            @See { needId = "XD-ADR-0127"; }
            ref item :>> connects : Port[1..*];
            ref item :>> realizes : System::SystemModelElement[0..*];
            ref item :>> satisfies : EeRequirement[0..*];
            ref item :>> conforms : System::Interface[0..*];
        }
        item def <'ee-cmp'> CircuitBlock :> DesignElement {
            ref item :>> realizes : System::SystemModelElement[0..*];
            ref item :>> satisfies : EeRequirement[0..*];
            ref item :>> conforms : System::Interface[0..*];
            ref item :>> part_of : Pcba[0..*];
        }
        item def <'ee-tc'> EeTestCase :> TestCase {
            ref item :>> verifies : EeRequirement[1..*];
        }
    }

    // ------------------------------------------------------------------ mechanical
    package Mechanical {
        item def <'me-req'> MeRequirement :> Requirement {
            ref item refinesRequirement : System::SystemRequirement[0..*] :> refines;
            ref item refinesInterface : System::Interface[0..*] :> refines;
        }
        item def <'me-asm'> Assembly :> DesignElement {
            ref item :>> realizes : System::SystemModelElement[0..*];
            ref item :>> satisfies : MeRequirement[0..*];
            ref item :>> conforms : System::Interface[0..*];
        }
        item def <'me-port'> MechanicalPort :> DesignElement {
            @See { needId = "XD-ADR-0133"; }
            doc /* A mechanical interface of an assembly, generated from the ME model. */
            ref item :>> conforms : System::Interface[0..*];
            ref item :>> part_of : Assembly[0..*];
        }
        item def <'me-part'> MechanicalPart :> DesignElement {
            ref item :>> realizes : System::SystemModelElement[0..*];
            ref item :>> satisfies : MeRequirement[0..*];
            ref item :>> conforms : System::Interface[0..*];
            ref item :>> part_of : Assembly[0..*];
        }
        item def <'me-tc'> MeTestCase :> TestCase {
            ref item :>> verifies : MeRequirement[1..*];
        }
    }

    // ------------------------------------------------------------------ test results
    package Results {
        abstract item def AnyTestCaseResult :> TestResult {
            doc /* Results point to the test case they come from. */
            ref item :>> result_of [1..*];
            ref item resultOfSystemTest : Verification::SystemTestCase[0..*] :> result_of;
            ref item resultOfIntegrationTest : Verification::IntegrationTestCase[0..*] :> result_of;
            ref item resultOfSwTest : Software::SwTestCase[0..*] :> result_of;
            ref item resultOfEeTest : Electrical::EeTestCase[0..*] :> result_of;
            ref item resultOfMeTest : Mechanical::MeTestCase[0..*] :> result_of;
        }
        item def <'tr'> RunResult :> AnyTestCaseResult {
            @See { needId = "XD-RULE-0012"; }
            doc /* TR-<test ID>-<sha8>: one result of one run, with firmware hash and pinned SHAs. */
        }
        item def <'testcase'> ReportTestCase :> AnyTestCaseResult {
            doc /* A test case imported from a JUnit report (sphinx-test-reports). */
            ref item :>> result_of [0..*];
        }
        item def <'testsuite'> ReportTestSuite :> TestResult { doc /* sphinx-test-reports. */ }
        item def <'testfile'> ReportTestFile :> TestResult { doc /* sphinx-test-reports. */ }
    }

    // ------------------------------------------------------------------ decisions, rules, checks
    package Framework {
        item def <'xd-adr'> FrameworkDecision :> Governance {
            ref item :>> refines : FrameworkDecision[0..*];
            ref item :>> revises : FrameworkDecision[0..*];
            ref item :>> supersedes : FrameworkDecision[0..*];
        }
        item def <'xd-rule'> MethodRule :> Governance {
            @See { needId = "XD-ADR-0110"; }
            ref item :>> decided_by : FrameworkDecision[1..*];
        }
        item def <'xd-check'> CuratrixCheck :> Governance {
            ref item :>> enforces : MethodRule[1..*];
        }
        item def <'prj-dec'> ProjectDecision :> Governance {
            ref item :>> follows : FrameworkDecision[0..*];
            ref item :>> refines : ProjectDecision[0..*];
            ref item :>> revises : ProjectDecision[0..*];
            ref item :>> supersedes : ProjectDecision[0..*];
        }
    }
}
