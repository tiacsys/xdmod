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

    // ------------------------------------------------------------------ variants (XD-ADR-0136)
    // A board or assembly variant: a def that specializes the board or assembly def and
    // DomainVariant. `variantName` is the variant's name in KiCad (`.kicad_pro`
    // schematic.variants) or FreeCAD (a row of the configuration table). A dependency from the
    // variant names the configurations (SYS-CFG) and the usages of the system model it serves;
    // curatrix computes the table "configuration -> variant per usage" from them (CK-B8):
    //   part def JointBoardAlt :> JointBoard, DomainVariant { :>> variantName = "alt"; }
    //   dependency from JointBoardAlt to MyConfigs::proto, MyProduct::Arm::joint1;
    // A variant has no ID of its own in iteration 1. At most two variants per board or assembly.
    part def DomainVariant {
        attribute variantName : String;
    }

    // ------------------------------------------------------------------ ME (XD-ADR-0130, XD-ADR-0137)
    // An assembly or sub-assembly: exactly one FreeCAD document (ME-ASM).
    part def Assembly;
    // A mechanical interface of an assembly (ME-PORT); in FreeCAD an LCS with a Port property.
    // Its placement in the assembly (the LCS in the skeleton) by optional attributes: position
    // x, y, z and the angles yaw, pitch, roll (FreeCAD's order: about z, then y, then x). A port
    // usage gives the values (`:>> x = 10 [mm];`); other attributes of the port def or usage with a
    // value are parameters too. Each becomes the alias <usage>_<attribute> in the skeleton's
    // spreadsheet Params (`curatrix gen freecad-params`, CK-F3, XD-ADR-0137, XD-ADR-0146).
    port def MechanicalPort {
        attribute x : ISQ::LengthValue[0..1];
        attribute y : ISQ::LengthValue[0..1];
        attribute z : ISQ::LengthValue[0..1];
        attribute yaw : ISQ::AngularMeasureValue[0..1];
        attribute pitch : ISQ::AngularMeasureValue[0..1];
        attribute roll : ISQ::AngularMeasureValue[0..1];
    }
    // How far the value in the FreeCAD file may differ from the model value of one attribute
    // (CK-F3), in the attribute's own unit. It is the model-to-CAD agreement of a copied number,
    // NOT a manufacturing or print tolerance of the part: keep it small. Without it the default
    // per kind applies (lengths 0.001 mm, angles 0.001 deg):
    //   :>> holeSpacing = 16 [mm] { @XdDomain::ModelMatchTolerance { value = 0.01; } }
    metadata def ModelMatchTolerance {
        attribute value : Real;
    }
}
