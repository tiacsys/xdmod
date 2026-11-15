// Fixture: refers back to LibA.
library package LibB {
    private import LibA::*;
    part def B { part a2 : A2; }
}
