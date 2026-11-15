Needs config test
=================

.. sys-sth:: Operator
   :id: SYS-STH-0001
   :status: valid

.. sys-need:: Problem statement
   :id: SYS-NEED-0001
   :status: valid
   :category: problem

.. sys-need:: Mirror the leader
   :id: SYS-NEED-0002
   :status: valid
   :category: need
   :raised_by: SYS-STH-0001
   :addresses: SYS-NEED-0001

.. sys-uc:: Teleoperate
   :id: SYS-UC-0001
   :status: valid
   :addresses: SYS-NEED-0002

.. sys-req:: Follow latency
   :id: SYS-REQ-0001
   :status: valid
   :refines: SYS-NEED-0002
   :category: performance
   :ears: event
   :quantity: latency
   :unit: ms
   :max: 50
   :verification_method: test
   :verification_scope: logical

   When the leader joint moves, the follower joint shall follow within 50 ms.

.. sys-req:: Old requirement
   :id: SYS-REQ-0002
   :status: retired
   :refines: SYS-NEED-0002

.. sys-if:: Joint servo pin map
   :id: SYS-IF-0001
   :status: valid

.. sys-el:: Follow function
   :id: SYS-EL-0001
   :status: valid
   :layer: functional
   :realizes: SYS-UC-0001

.. sys-el:: Joint controller
   :id: SYS-EL-0002
   :status: valid
   :layer: logical
   :realizes: SYS-EL-0001
   :satisfies: SYS-REQ-0001
   :instances: leader.joint1, follower.joint1

.. sys-el:: Nucleo board
   :id: SYS-EL-0003
   :status: valid
   :layer: product
   :realizes: SYS-EL-0002
   :configs: SYS-CFG-0001
   :satisfies: SYS-REQ-0002

.. sys-cfg:: Prototype
   :id: SYS-CFG-0001
   :status: valid
   :configures: SYS-EL-0003

.. sys-feat:: Prototype build
   :id: SYS-FEAT-0001
   :status: valid

.. int-stc:: Latency test
   :id: INT-STC-0001
   :status: valid
   :verifies: SYS-REQ-0001

.. int-itc:: Pin map test
   :id: INT-ITC-0001
   :status: valid
   :verifies: SYS-IF-0001

.. sw-req:: Control loop rate
   :id: SW-REQ-0001
   :status: valid
   :refines: SYS-REQ-0001

.. sw-req:: Watchdog
   :id: SW-REQ-0002
   :status: draft
   :derived: true
   :rationale: Safety practice.

.. sw-arch:: Control task
   :id: SW-ARCH-0001
   :status: valid
   :realizes: SYS-EL-0003
   :satisfies: SW-REQ-0001
   :conforms: SYS-IF-0001

.. sw-dd:: PID
   :id: SW-DD-0001
   :status: valid
   :refines: SW-ARCH-0001

.. sw-impl:: pid.c
   :id: SW-IMPL-0001
   :status: valid
   :implements: SW-DD-0001
   :satisfies: SW-REQ-0001

.. sw-tc:: PID unit test
   :id: SW-TC-0001
   :status: valid
   :verifies: SW-REQ-0001, SW-DD-0001

.. ee-req:: Servo supply
   :id: EE-REQ-0001
   :status: valid
   :refines: SYS-IF-0001

.. ee-pcba:: Joint board
   :id: EE-PCBA-0001
   :status: valid
   :realizes: SYS-EL-0003

.. ee-cmp:: Servo connector
   :id: EE-CMP-0001
   :status: valid
   :satisfies: EE-REQ-0001
   :part_of: EE-PCBA-0001
   :conforms: SYS-IF-0001

.. ee-tc:: Supply test
   :id: EE-TC-0001
   :status: valid
   :verifies: EE-REQ-0001

.. me-req:: Link length
   :id: ME-REQ-0001
   :status: valid
   :refines: SYS-REQ-0001

.. me-asm:: Arm
   :id: ME-ASM-0001
   :status: valid
   :realizes: SYS-EL-0003

.. me-part:: Link
   :id: ME-PART-0001
   :status: valid
   :satisfies: ME-REQ-0001
   :part_of: ME-ASM-0001

.. me-tc:: Length inspection
   :id: ME-TC-0001
   :status: valid
   :verifies: ME-REQ-0001

.. xd-adr:: SysML v2 textual
   :id: XD-ADR-0001
   :status: valid
   :legacy_id: D1

.. xd-rule:: Concrete side holds the link
   :id: XD-RULE-0001
   :status: valid
   :decided_by: XD-ADR-0001

.. xd-check:: CK-A1
   :id: XD-CHECK-0001
   :status: valid
   :enforces: XD-RULE-0001

.. prj-dec:: Board choice
   :id: PRJ-DEC-0001
   :status: valid
   :follows: XD-ADR-0001

.. tr:: Latency run
   :id: TR-INT-STC-0001-3f9a1c2e
   :status: valid
   :result_of: INT-STC-0001
   :config: SYS-CFG-0001
   :method: hil
   :verdict: passed
   :firmware_sha256: 0000000000000000000000000000000000000000000000000000000000000000
   :shas: robarm-sw=abc1234, xdmod=def5678
