library package NeedStubs {
    private import ScalarValues::*;
    private import XdTrace::*;

    part <'SYS-STH-0001'> sys_sth_0001 {
        doc /* Operator */
        @NeedRef { needId = "SYS-STH-0001"; status = "valid"; }
    }
    concern <'SYS-NEED-0002'> sys_need_0002 {
        doc /* Mirror the leader */
        @NeedRef { needId = "SYS-NEED-0002"; status = "valid"; }
    }
    requirement <'SYS-REQ-0001'> sys_req_0001 {
        doc /* Follow latency. When the leader joint moves, the follower joint shall follow within 50 ms. */
        @NeedRef { needId = "SYS-REQ-0001"; status = "valid"; }
        attribute ears : String = "event";
        attribute quantity : String = "latency";
        attribute unit : String = "ms";
        attribute max : Real = 50.0;
        frame sys_need_0002;
    }
}
