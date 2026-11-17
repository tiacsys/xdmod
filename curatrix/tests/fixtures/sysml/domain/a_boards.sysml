// Test fixture: an EE domain model. It imports b_ports.sysml, which comes later in name order:
// the repo's files are read as one set (XD-ADR-0130).
package EeBoards {
    private import XdDomain::*;
    private import Sys::*;
    private import EePorts::*;

    // good: every inherited port redefined with a connector port def
    part def <'EE-PCBA-0001'> ControllerBoard :> Controller, Pcba {
        port :>> servoOut : ServoHeader;
        port :>> bus : BusHeader;
    }
    // good: a variant does not repeat its parent's redefinitions
    part def ControllerBoardB :> ControllerBoard;
    // planted: a variant widens a redefined port back to the system type (the pin map is lost)
    part def ControllerBoardW :> ControllerBoard {
        port :>> servoOut : ServoIf;
    }
    // good: a conjugated system port, redefined by the conjugated connector
    part def <'EE-PCBA-0006'> ServoBoard :> Servo, Pcba {
        port :>> servoIn : ~ServoHeader;
    }
    // planted: the conjugation is lost
    part def <'EE-PCBA-0007'> FlatServoBoard :> Servo, Pcba {
        port :>> servoIn : ServoHeader;
    }
    // planted: `bus` is not redefined
    part def <'EE-PCBA-0002'> SensorBoard :> Sys::Detail::Sensor, Pcba;
    // planted: `servoOut` redefined with a port def that does not specialize ServoIf
    part def <'EE-PCBA-0003'> WrongBoard :> Controller, Pcba {
        port :>> servoOut : BusHeader;
        port :>> bus : BusHeader;
    }
    // planted: two supers declare `servoOut`, only one is redefined
    part def <'EE-PCBA-0004'> ComboBoard :> Controller, Driver, Pcba {
        port :>> Controller::servoOut : ServoHeader;
        port :>> bus : BusHeader;
    }
    // good: one port redefines both
    part def <'EE-PCBA-0005'> ComboBoard2 :> Controller, Driver, Pcba {
        port :>> Controller::servoOut, Driver::servoOut : ServoHeader;
        port :>> bus : BusHeader;
    }
    // planted: an EE-PORT ID on a def that specializes a SYS-EL (no link type)
    part def <'EE-PORT-0009'> OddBoard :> Driver {
        port :>> servoOut : ServoHeader;
    }
    // planted: specializes a SYS-EL without an ID of its own
    part def NoIdBoard :> Driver {
        port :>> servoOut : ServoHeader;
    }
}
