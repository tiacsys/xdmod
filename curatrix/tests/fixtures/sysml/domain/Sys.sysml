// Test fixture: a system model (stands for the systems engineering repo). Upstream of the
// domain fixture (a_boards.sysml, b_ports.sysml).
package Sys {
    private import XdTrace::*;
    port def <'SYS-IF-0001'> ElSignal;
    port def <'SYS-IF-0002'> ServoIf {
        out port pwm : ElSignal;
        inout port gnd : ElSignal;
    }
    port def <'SYS-IF-0003'> BusIf {
        inout port data : ElSignal;
    }
    part def <'SYS-EL-0001'> Controller {
        port servoOut : ServoIf;
        port bus : BusIf;
    }
    part def <'SYS-EL-0002'> Driver {
        port servoOut : ServoIf;
    }
    part def <'SYS-EL-0004'> Servo {
        port servoIn : ~ServoIf;
    }
    // a configuration that configures Controller only
    part def <'SYS-CFG-0001'> Basic;
    dependency from Basic to Controller;
    // a second configuration that configures Controller, and the usages the variants serve
    // (c_variants.sysml, CK-B8)
    part def <'SYS-CFG-0002'> Full;
    dependency from Full to Controller;
    part def Arm {
        part ctrlA : Controller;
        part ctrlB : Controller;
        part servo1 : Servo;
        part drv1 : Driver;
    }
    // Basic also configures Driver, Full does not: pairs are per realized def (ComboBoard)
    dependency from Basic to Driver;
    // a nested package: not a top package (top_packages counts brace depth)
    package Detail {
        part def <'SYS-EL-0003'> Sensor {
            port bus : BusIf;
        }
    }
}
