// XDMOD SysML v2 library: the base defs of the domain models (XD-ADR-0130, XD-ADR-0135).
// A domain def specializes the system def it realizes AND one of these, e.g.
//   part def <'EE-PCBA-0012'> JointControllerBoard :> MyProduct::JointController, XdDomain::Pcba { ... }
// Specializing an XdDomain def makes no trace link; it says what the def is (board, external
// part, assembly), for the 1:1 rules between model and CAD files (CK-F7, CK-F14).
// curatrix loads every file in xdmod/sysml/ first (checks.yaml model.libraries).
// SPDX-License-Identifier: Apache-2.0
library package XdDomain {
    private import ScalarValues::*;

    // ------------------------------------------------------------------ EE (XD-ADR-0130, XD-ADR-0135)
    // A board designed in this repo: exactly one KiCad project pcba/<name>/ (EE-PCBA).
    part def Pcba;
    // A bought board or part (MCU board, breakout, servo, potentiometer): ports, no KiCad project.
    part def ExternalPart;
    // A cable: exactly one harness/<name>/ (EE-HAR).
    part def Cable;

    // A connector of a board or an external part (EE-PORT). It redefines the signals of the
    // interface def it specializes with PinSignal ports: the pin map.
    port def ConnectorPort {
        attribute connector : String;       // connector type, e.g. "JST-XH-3"
    }
    // One pin of a connector: pin number (as KiCad writes it) and net name.
    //   out port :>> pwm : MyPin { :>> pin = "1"; :>> net = "SERVO_PWM"; }
    port def PinSignal {
        attribute pin : String;
        attribute net : String;
    }

    // ------------------------------------------------------------------ ME (XD-ADR-0130, XD-ADR-0137)
    // An assembly or sub-assembly: exactly one FreeCAD document (ME-ASM).
    part def Assembly;
    // A mechanical interface of an assembly (ME-PORT); in FreeCAD an LCS with a Port property.
    port def MechanicalPort;
}
