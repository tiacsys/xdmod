// Test fixture: an external part with its own connector port def, and a cable def whose ends
// mate with a board port (ServoHeader) and the external part's port (task 5.22).
package EeCables {
    private import XdDomain::*;
    private import EePorts::*;

    // an external part: a port, no KiCad project, no part_of
    port def <'EE-PORT-0010'> ServoPlug :> ConnectorPort {
        :>> connector = "JST-XH-3 plug";
        inout port pwm : PinSignal { :>> pin = "1"; :>> net = "SERVO_PWM"; }
        inout port gnd : PinSignal { :>> pin = "3"; :>> net = "GND"; }
    }
    part def ServoMotor :> ExternalPart {
        port plug : ServoPlug;
    }
    // the cable connects the ports its ends mate with (EE-HAR connects EE-PORT)
    part def <'EE-HAR-0001'> ServoCable :> Cable {
        port boardEnd : ~ServoHeader;
        port servoEnd : ~ServoPlug;
    }
}
