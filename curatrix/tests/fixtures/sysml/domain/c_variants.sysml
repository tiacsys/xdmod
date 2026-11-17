// Test fixture: board variants (XD-ADR-0136, CK-B8). ControllerBoard (EE-PCBA-0001) realizes
// Controller, which Basic and Full configure; Sys::Arm has two Controller usages. ServoBoard
// (EE-PCBA-0006) realizes Servo, which no configuration configures: it is in both.
package EeVariants {
    private import XdDomain::*;
    private import Sys::*;
    private import EeBoards::*;

    // good: every (configuration, usage) of ControllerBoard has exactly one variant
    part def CtrlStd :> ControllerBoard, DomainVariant { :>> variantName = "std"; }
    dependency from CtrlStd to Basic, Arm::ctrlA, Arm::ctrlB;
    dependency from CtrlStd to Full, Arm::ctrlA;
    part def CtrlFast :> ControllerBoard, DomainVariant { :>> variantName = "fast"; }
    dependency from CtrlFast to Full, Arm::ctrlB;

    // good: ComboBoard2 (EE-PCBA-0005) realizes Controller (Basic, Full) and Driver (Basic only):
    // drv1 needs a variant in Basic only, not in Full
    part def ComboX :> ComboBoard2, DomainVariant { :>> variantName = "x"; }
    dependency from ComboX to Basic, Full, Arm::ctrlA, Arm::ctrlB;
    dependency from ComboX to Basic, Arm::drv1;

    // planted: two variants for (Basic, servo1), none for (Full, servo1)
    part def ServoA :> ServoBoard, DomainVariant { :>> variantName = "a"; }
    dependency from ServoA to Basic, Arm::servo1;
    part def ServoB :> ServoBoard, DomainVariant { :>> variantName = "b"; }
    dependency from ServoB to Basic, Arm::servo1;
    // planted: a third variant, a usage of another def, and no variantName
    part def ServoC :> ServoBoard, DomainVariant;
    dependency from ServoC to Basic, Arm::ctrlA;
    // planted: a dependency with a usage but no configuration
    dependency from ServoA to Arm::servo1;
}
