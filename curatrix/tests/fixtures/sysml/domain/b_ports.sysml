// Test fixture: EE connector port defs with pin maps.
package EePorts {
    private import XdDomain::*;
    private import Sys::*;

    // below the port level: no ID needed
    port def Pin :> ElSignal, PinSignal;

    port def <'EE-PORT-0001'> ServoHeader :> ServoIf, ConnectorPort {
        :>> connector = "JST-XH-3";
        out port :>> pwm : Pin { :>> pin = "1"; :>> net = "SERVO_PWM"; }
        inout port :>> gnd : Pin { :>> pin = "3"; :>> net = "GND"; }
    }
    port def <'EE-PORT-0002'> BusHeader :> BusIf, ConnectorPort {
        :>> connector = "JST-GH-2";
        inout port :>> data : Pin { :>> pin = "1"; :>> net = "DATA"; }
    }
}
