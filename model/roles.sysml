// XDMOD self-model: roles of people, agents and automation, and what they do.
// SPDX-License-Identifier: Apache-2.0
package XdmodRoles {
    doc /* Humans and agents (humans-and-agents.rst, workflow.md §2, D3, D58, D126). */
    private import XdTrace::*;

    abstract part def Person;
    abstract part def Agent { @See { needId = "XD-ADR-0003"; } }
    part def Owner :> Person { doc /* sets goals, decides, merges, affirms, makes baselines */ }
    part def DomainEngineer :> Person { doc /* SE, EE, ME, SW or integration */ }
    part def AgentAuthor :> Agent;
    part def AgentReviewer :> Agent;
    part def CoordinatorAgent :> Agent;
    part def CiRunner { doc /* GitHub Actions */ }
    part def BumpBot { doc /* scheduled workflow of the manifest repo */ }

    use case def 'Plan and split work' {
        subject ws : XdmodDomains::Workspace;
        actor owner : Owner;
        actor coordinator : CoordinatorAgent;
    }
    use case def 'Run checks' {
        @See { needId = "XD-RULE-0032"; }
        subject ws : XdmodDomains::Workspace;
        actor ci : CiRunner;
    }
    use case def 'Change design content' {
        subject ws : XdmodDomains::Workspace;
        actor author : AgentAuthor;
        actor engineer : DomainEngineer;
        include use case 'run checks' : 'Run checks';
    }
    use case def 'Review a pull request' {
        @See { needId = "XD-ADR-0115"; }
        subject ws : XdmodDomains::Workspace;
        actor reviewer : AgentReviewer;
        actor owner : Owner;
    }
    use case def 'Merge a pull request' {
        subject ws : XdmodDomains::Workspace;
        actor owner : Owner;
        include use case 'run checks' : 'Run checks';
    }
    use case def 'Affirm a suspect link' {
        @See { needId = "XD-ADR-0051"; }
        subject ws : XdmodDomains::Workspace;
        actor engineer : DomainEngineer;
        actor owner : Owner;
    }
    use case def 'Record HIL evidence' {
        @See { needId = "XD-ADR-0053"; }
        subject ws : XdmodDomains::Workspace;
        actor author : AgentAuthor;
        actor engineer : DomainEngineer;
    }
    use case def 'Bump pins' {
        @See { needId = "XD-ADR-0054"; }
        subject ws : XdmodDomains::Workspace;
        actor bot : BumpBot;
        include use case 'run checks' : 'Run checks';
    }
    use case def 'Make a baseline' {
        subject ws : XdmodDomains::Workspace;
        actor owner : Owner;
    }
}
