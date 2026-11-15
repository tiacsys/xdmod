// XDMOD self-model: how sources become needs, views, documents and check results.
// SPDX-License-Identifier: Apache-2.0
package XdmodToolchain {
    doc /* The build and check pipeline that `curatrix gen`, `views build`, `docs` and `check`
         * run, locally and in CI (D40, D46, D65, D96). */
    private import XdTrace::*;
    private import ScalarValues::*;
    private import XdmodDomains::*;

    item def HtmlSite { doc /* the linked HTML documents, with llms.txt for agents */ }
    item def CheckReport { doc /* curatrix check results; each failure prints its reproduce command */ }
    item def CadSource { doc /* KiCad projects and FreeCAD files, with trace fields */ }
    item def CodeSource { doc /* Zephyr application and tests, with Doxygen and ZTEST IDs */ }

    action def BuildAndCheck {
        @See { needId = "XD-ADR-0040"; }
        doc /* One pass over a repo or the full set. The same steps run locally and in CI. */
        attribute passed : Boolean;

        action 'author content' {
            doc /* People and agents edit sources on a branch. */
            out item rst : Document;
            out item sysml : SysmlModel;
            out item cad : CadSource;
            out item code : CodeSource;
        }
        action 'docs build: export needs' {
            doc /* sphinx-needs writes each document's needs.json. */
            in item rst : Document;
            out item needs : NeedsJson;
        }
        action 'gen stubs' {
            @See { needId = "XD-ADR-0036"; }
            doc /* Read-only SysML stubs of the requirements. */
            in item needs : NeedsJson;
            out item stubs : NeedStubs;
        }
        action 'gen model (Pilot)' {
            @See { needId = "XD-ADR-0058"; }
            in item sysml : SysmlModel;
            in item stubs : NeedStubs;
            out item modelJson : ModelJson;
            out item modelNeeds : NeedsJson;
        }
        action 'gen cad-needs' {
            @See { needId = "XD-ADR-0100"; }
            in item cad : CadSource;
            out item cadNeeds : NeedsJson;
        }
        action 'extract code needs' {
            doc /* Doxygen groups and ZTEST annotations become SW-IMPL and SW-TC needs. */
            in item code : CodeSource;
            out item codeNeeds : NeedsJson;
        }
        action 'views build (elkjs, drawio)' {
            @See { needId = "XD-ADR-0087"; }
            in item modelJson : ModelJson;
            out item views : DrawioView;
        }
        action 'docs build: strict, linked' {
            @See { needId = "XD-RULE-0034"; }
            in item modelNeeds : NeedsJson;
            in item cadNeeds : NeedsJson;
            in item codeNeeds : NeedsJson;
            in item views : DrawioView;
            out item site : HtmlSite;
        }
        action 'curatrix check' {
            @See { needId = "XD-RULE-0032"; }
            doc /* Generated files fresh, IDs, graph rules, model, views, tests. */
            in item site : HtmlSite;
            out item report : CheckReport;
        }
        action 'publish (Pages)' {
            @See { needId = "XD-ADR-0048"; }
            in item site : HtmlSite;
        }

        first start then 'author content';
        flow 'author content'.rst to 'docs build: export needs'.rst;
        flow 'author content'.sysml to 'gen model (Pilot)'.sysml;
        flow 'author content'.cad to 'gen cad-needs'.cad;
        flow 'author content'.code to 'extract code needs'.code;
        flow 'docs build: export needs'.needs to 'gen stubs'.needs;
        flow 'gen stubs'.stubs to 'gen model (Pilot)'.stubs;
        flow 'gen model (Pilot)'.modelJson to 'views build (elkjs, drawio)'.modelJson;
        flow 'gen model (Pilot)'.modelNeeds to 'docs build: strict, linked'.modelNeeds;
        flow 'gen cad-needs'.cadNeeds to 'docs build: strict, linked'.cadNeeds;
        flow 'extract code needs'.codeNeeds to 'docs build: strict, linked'.codeNeeds;
        flow 'views build (elkjs, drawio)'.views to 'docs build: strict, linked'.views;
        flow 'docs build: strict, linked'.site to 'curatrix check'.site;
        flow 'docs build: strict, linked'.site to 'publish (Pages)'.site;
        first 'curatrix check' then gate;
        decide gate;
            if passed then 'publish (Pages)';
            else 'author content';
        first 'publish (Pages)' then done;
    }
}
