package Probe {
    private import XdTrace::*;
    private import NeedStubs::*;
    @Trace { layer = "logical"; }

    use case def <'SYS-UC-0001'> Teleoperate;
    part def <'SYS-EL-0001'> Follow { @Trace { layer = "functional"; } }
    dependency from Follow to Teleoperate;

    port def AngleOut { out attribute angle : ScalarValues::Real; }
    part def Sensor { port angleOut : AngleOut; }
    part def <'SYS-EL-0002'> JointController { port angleIn : ~AngleOut; @Trace { status = "draft"; } }

    part def <'SYS-EL-0003'> LogicalJoint {
        part sensor : Sensor;
        part ctrl : JointController;
        connect sensor.angleOut to ctrl.angleIn;
        satisfy sys_req_0001 by ctrl;
    }
    part arm {
        part joint1 : LogicalJoint;
        part joint2 : LogicalJoint;
        part f : Follow;
        part c : JointController;
        allocate f to c;
    }
    view <'SYS-VIEW-0001'> jointView {
        @XdView { kind = "interconnection"; root = "Probe::LogicalJoint"; }
        expose Probe::LogicalJoint::**;
    }
}
