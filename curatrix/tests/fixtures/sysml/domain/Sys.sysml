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
    // a nested package: not a top package (top_packages counts brace depth)
    package Detail {
        part def <'SYS-EL-0003'> Sensor {
            port bus : BusIf;
        }
    }
}
