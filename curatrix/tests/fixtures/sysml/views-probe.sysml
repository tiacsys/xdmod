// Small model for the SysML standard views (test_views_sysml.py).
// views-probe-model.json is its compact Pilot export; test_views_sysml.py says how to rebuild it.
package VP {
    private import XdTrace::*;
    private import ScalarValues::*;

    abstract item def N { abstract ref item link : N[0..*]; }
    item def <'a-t'> A :> N;
    item def <'b-t'> B :> N;
    item def <'c-t'> C :> N {
        @See { needId = "XD-ADR-0004"; }
        ref item :>> link [1..*];
        ref item linkA : A[0..*] :> link;
        ref item linkB : B[0..*] :> link;
        attribute size : Integer = 3;
        item part1 : A;
    }

    action def Flow {
        attribute ok : Boolean;
        action produce { out item a : A; }
        action consume { in item a : A; }
        flow produce.a to consume.a;
        first start then produce;
        first consume then gate;
        decide gate;
            if ok then done;
            else produce;
    }

    item def Go;
    state def Life {
        attribute flag : Boolean;
        entry; then s1;
        state s1;
        state s2;
        transition first s1 accept Go then s2;
        transition first s2 if not flag then s1;
    }

    part def Ws1;
    part def Ws2;
    part def Person;
    use case def U1 { subject w : Ws1; actor p : Person; include use case u3 : U3; }
    use case def U2 { subject w : Ws2; actor p : Person; }
    use case def U3 { subject w : Ws1; }

    view vGeneral { @XdView { kind = "general"; direction = "LEFT"; } expose VP::*; filter @SysML::ItemDefinition; }
    view vFlow { @XdView { kind = "actionflow"; root = "VP::Flow"; direction = "RIGHT"; } }
    view vLife { @XdView { kind = "statetransition"; root = "VP::Life"; } }
    view vUc { @XdView { kind = "usecases"; root = "VP"; } }
}
