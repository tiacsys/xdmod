// Fixture: LibA and LibB refer to each other (like SYSMOD.sysml and SYSMOD15288.sysml).
library package LibA {
    private import LibB::*;
    part def A { part b : B; }
    part def A2;
}
