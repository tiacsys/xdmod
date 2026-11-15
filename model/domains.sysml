// XDMOD self-model: domains, repos and the artifacts each repo holds.
// The model describes the framework itself; `curatrix views build xdmod` renders its views
// (model/views.sysml) into views/*.drawio.svg for the XDMOD manual.
// SPDX-License-Identifier: Apache-2.0
package XdmodDomains {
    doc /* The engineering domains of XDMOD, the repos that hold them, and the documents and
         * design files in each repo (repo layouts, D68, D71, D78). */
    private import XdTrace::*;
    private import ScalarValues::*;

    // ------------------------------------------------------------------ domains (ID scheme)
    enum def Domain {
        doc /* The DOMAIN part of every ID: <DOMAIN>-<KIND>-<NNNN>. */
        enum SYS;   // systems engineering
        enum SW;    // software
        enum EE;    // electrical engineering
        enum ME;    // mechanical engineering
        enum INT;   // integration and system test
        enum XD;    // the framework itself
        enum PRJ;   // project decisions
    }

    // ------------------------------------------------------------------ artifacts
    abstract item def Artifact {
        doc /* A file or a set of files in a repo. */
        attribute path : String;
    }
    abstract item def SourceArtifact :> Artifact {
        doc /* Written by people or agents. */
    }
    abstract item def GeneratedArtifact :> Artifact {
        doc /* Written by curatrix, committed, and compared by `curatrix check` (XD-RULE-0033). */
    }
    abstract item def BuildOutput :> Artifact {
        @See { needId = "XD-RULE-0040"; }
        doc /* Written under build/<area>/ by a build or check, never committed. */
    }
    abstract item def CadSource :> SourceArtifact {
        doc /* CAD files with trace fields (XD-ADR-0023). */
    }
    abstract item def CodeSource :> SourceArtifact {
        doc /* Firmware and test code with Doxygen groups and test IDs. */
    }

    // configuration that every repo has
    item def ChecksConfig :> SourceArtifact { doc /* checks.yaml: what `curatrix check` runs. */ }
    item def IdLedger :> SourceArtifact { doc /* ids.yaml: every ID ever issued, append-only. */ }
    item def ToolPins :> SourceArtifact { doc /* requirements.txt and tools.yaml. */ }
    item def DocRegistry :> SourceArtifact { doc /* docs/documents.yaml: own and upstream documents (zdocs). */ }
    item def AgentMaterial :> SourceArtifact { doc /* claude/: CLAUDE.md, skills, commands, checklists. */ }

    // documents and design sources
    item def Document :> SourceArtifact {
        doc /* One Sphinx document (rst) of the linked document set; it holds authored needs. */
        attribute docId : String;
    }
    item def SysmlModel :> SourceArtifact { doc /* model/*.sysml, one file per SYSMOD step. */ }
    item def KicadProject :> CadSource { doc /* pcba/<name>/: one KiCad project per PCBA. */ }
    item def PrototypeWiring :> CadSource { doc /* proto/<config>/: KiCad or WireViz. */ }
    item def FreecadFile :> CadSource { doc /* parts/ and assemblies/: uncompressed .FCStd. */ }
    item def ZephyrApp :> CodeSource { doc /* app/ and dts/bindings/: the firmware. */ }
    item def TestSuite :> CodeSource { doc /* tests/: test code with test IDs from the ledger. */ }
    item def HilSetup :> SourceArtifact { doc /* hil/<setup>/: hardware map, fixtures, runner config. */ }
    item def WestManifest :> SourceArtifact { doc /* west.yml and submanifests: the only place with pins. */ }
    item def NeedsConfig :> SourceArtifact { doc /* needs/needs_config.toml: need types and link types. */ }
    item def SysmlLibrary :> SourceArtifact { doc /* sysml/: trace and view metadata. */ }
    item def CuratrixTool :> SourceArtifact { doc /* curatrix/: the framework tool. */ }
    item def ReusableWorkflow :> SourceArtifact { doc /* workflows/: GitHub workflows the repos call. */ }

    // generated, committed
    item def NeedStubs :> GeneratedArtifact { doc /* model/generated/NeedStubs.sysml: requirement stubs. */ }
    item def ModelJson :> GeneratedArtifact { doc /* generated/model.json: compact Pilot export. */ }
    item def GeneratedNeeds :> GeneratedArtifact { doc /* generated/model-needs.json and cad-needs.json. */ }
    item def DrawioView :> GeneratedArtifact { doc /* views/<view>.drawio.svg: editable SVG. */ }
    item def RunRecord :> GeneratedArtifact { doc /* HIL run record on the orphan branch `evidence`. */ }

    // build output, not committed
    item def NeedsExport :> BuildOutput { doc /* needs.json of a document, written by its docs build. */ }
    item def HtmlSite :> BuildOutput { doc /* the linked HTML documents, with llms.txt for agents. */ }
    item def CheckReport :> BuildOutput { doc /* curatrix check results; each failure prints its reproduce command. */ }

    // ------------------------------------------------------------------ repos
    abstract part def Repository {
        doc /* Every repo follows one common layout. */
        attribute domain : Domain[0..*];
        item checks : ChecksConfig;
        item ledger : IdLedger;
        item pins : ToolPins;
        item registry : DocRegistry;
        item agentMaterial : AgentMaterial;
    }

    part def SysEngRepo :> Repository {
        @See { needId = "XD-ADR-0001"; }
        doc /* robarm-syseng: requirements and the SysML model. */
        attribute :>> domain = Domain::SYS;
        item model : SysmlModel[1..*];
        item stubs : NeedStubs;
        item modelJson : ModelJson;
        item modelNeeds : GeneratedNeeds;
        item views : DrawioView[0..*];
        item seReq : Document;
        item seArch : Document;
    }
    part def EeRepo :> Repository {
        @See { needId = "XD-ADR-0102"; }
        doc /* robarm-ee: KiCad projects and prototype wiring. */
        attribute :>> domain = Domain::EE;
        item pcba : KicadProject[0..*];
        item proto : PrototypeWiring[0..*];
        item tests : TestSuite[0..*];
        item cadNeeds : GeneratedNeeds;
        item eeDesign : Document[1..*];
    }
    part def MeRepo :> Repository {
        @See { needId = "XD-ADR-0056"; }
        doc /* robarm-me: FreeCAD parts and assemblies. */
        attribute :>> domain = Domain::ME;
        item parts : FreecadFile[0..*];
        item assemblies : FreecadFile[0..*];
        item tests : TestSuite[0..*];
        item cadNeeds : GeneratedNeeds;
        item meDesign : Document;
    }
    part def SwRepo :> Repository {
        @See { needId = "XD-ADR-0069"; }
        doc /* robarm-sw: Zephyr firmware. */
        attribute :>> domain = Domain::SW;
        item app : ZephyrApp;
        item tests : TestSuite[0..*];
        item swReq : Document;
        item swArch : Document;
        item swApi : Document;
        item swTestSpec : Document;
        item swTestReport : Document;
    }
    part def IntegrationRepo :> Repository {
        @See { needId = "XD-ADR-0066"; }
        doc /* robarm-integration: system and integration tests, HIL. */
        attribute :>> domain = Domain::INT;
        item tests : TestSuite[0..*];
        item hil : HilSetup[0..*];
        item evidence : RunRecord[0..*];
        item intTestSpec : Document;
        item intTestReport : Document;
    }
    part def ManifestRepo :> Repository {
        @See { needId = "XD-ADR-0011"; }
        doc /* robarm-manifest: pins, full-set registry, project decisions. */
        attribute :>> domain = Domain::PRJ;
        item manifest : WestManifest;
        item overview : Document;
    }
    part def FrameworkRepo :> Repository {
        @See { needId = "XD-ADR-0059"; }
        doc /* xdmod: the framework, in every workspace. */
        attribute :>> domain = Domain::XD;
        item needsConfig : NeedsConfig;
        item sysmlLibrary : SysmlLibrary;
        item curatrix : CuratrixTool;
        item workflows : ReusableWorkflow[1..*];
        item model : SysmlModel[1..*];
        item views : DrawioView[0..*];
        item manual : Document;
        item reference : Document;
    }

    // ------------------------------------------------------------------ the workspace
    // Ports: what a repo offers to and takes from its neighbours. Needs travel as needs.json
    // (zdocs imports upstream documents); pins travel through the manifest.
    port def NeedsPort {
        doc /* A document set's exported needs (needs.json). */
        out item needs : NeedsExport[0..*];
    }
    port def PinPort {
        doc /* The revision a repo is pinned to (west). */
        out attribute revision : String;
    }
    port def FrameworkPort {
        doc /* need types, Sphinx extensions, SysML library, curatrix, reusable workflows. */
        out item needsConfig : NeedsConfig;
    }

    part def Workspace {
        @See { needId = "XD-ADR-0061"; }
        doc /* One west topdir: xdmod, the manifest repo, the design repos, libraries and Zephyr. */
        part xdmod : FrameworkRepo {
            port framework : FrameworkPort;
        }
        part manifest : ManifestRepo {
            port pins : ~PinPort;
            port fullSet : ~NeedsPort;
            port framework : ~FrameworkPort;
        }
        part syseng : SysEngRepo {
            port needs : NeedsPort;
            port pin : PinPort;
            port framework : ~FrameworkPort;
        }
        part ee : EeRepo {
            port framework : ~FrameworkPort;
            port upstream : ~NeedsPort;
            port needs : NeedsPort;
            port pin : PinPort;
        }
        part me : MeRepo {
            port framework : ~FrameworkPort;
            port upstream : ~NeedsPort;
            port needs : NeedsPort;
            port pin : PinPort;
        }
        part sw : SwRepo {
            port framework : ~FrameworkPort;
            port upstream : ~NeedsPort;
            port needs : NeedsPort;
            port pin : PinPort;
        }
        part integration : IntegrationRepo {
            port framework : ~FrameworkPort;
            port upstream : ~NeedsPort;
            port needs : NeedsPort;
            port pin : PinPort;
        }

        // xdmod serves every repo (XD-ADR-0059)
        interface xdmod.framework to syseng.framework;
        interface xdmod.framework to ee.framework;
        interface xdmod.framework to me.framework;
        interface xdmod.framework to sw.framework;
        interface xdmod.framework to integration.framework;
        interface xdmod.framework to manifest.framework;
        // needs flow from the abstract to the concrete side; links point back (XD-RULE-0001)
        interface syseng.needs to ee.upstream;
        interface syseng.needs to me.upstream;
        interface syseng.needs to sw.upstream;
        interface syseng.needs to integration.upstream;
        interface ee.needs to integration.upstream;
        interface me.needs to integration.upstream;
        interface sw.needs to integration.upstream;
        interface integration.needs to manifest.fullSet;
        // the manifest pins every design repo
        interface syseng.pin to manifest.pins;
        interface ee.pin to manifest.pins;
        interface me.pin to manifest.pins;
        interface sw.pin to manifest.pins;
        interface integration.pin to manifest.pins;
    }
}
