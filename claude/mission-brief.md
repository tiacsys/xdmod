# Mission Brief

## Goals of this project

This project is supposed to define a framework in which 
embedded projects comprising mechanical, electrical and software elements
can be realized. A framework is understood as a set of methods and tools
that would help human and agentic engineers in defining, designing and verifying 
a given engineering problem.

The domains the work needs to look at can be split into four domains that 
where necessary need to exchange information in a reliable way. The four domains
are systems engineering, electrical engineering, mechanical engineering and software 
engineering. 

One of the key results this project should deliver is how these domains can be connected
with the help of a consistent modeling approach starting in the systems engineering domain
with the capture of user needs and system requirements, following the Sysmodv5 MBSE methodology
to derive and design a system model against the stated problem. Then refining and linking 
this system model to downstream models that can be taken on in the ME, EE and SW domains
respectively.

A second key result is to show a way how this information can be presented to human and agentic
reviewers by rendering views of the underlying models into either human or machine readable formats 
including html, pdf, svg or json to name just a few relevant file formats.

Thirdly, the framework should demonstrate how to deal with iterative and incremental design work, ie.
how requirements can be added/removed, design changes be propagated and consistency be checked. 

The project should demonstrate and explore iteratively its framework with the help of a small
example, which serves to create real content from the methods and using actual tools.

All tools the projects uses are open source and offer extension points where within the project
custom extensions can be created to allow a specific step or task within a method.

Notes about the progress will be kept in this folder. For each domain at least one repository
will be created to hold design artifacts of that particular domain. If the project discovers
that more repositories are needed within a particular domain then this will be allowed, too.


## The example

The example by which the framework shall be defined and applied is a robotic application comprising two 
6Dof robotic arms, called the leader and the follower. The leader can be moved by the user along 
all its axis. The angles of the axis are measured and relayed to the follower so that the (larger) follower
synchronously is in the same pose as the leader. The user can also store a particular position to command the follower 
later to go back to this position. 

Refining this initial idea continuously is part of what the framework needs to allow.
 

## Tools

As tools the following is defined for use in this project:

* Freecad
* Kicad
* Zephyr RTOS as the Software framework including its SDK
* Sphinx + Sphinxneeds for Project documentation across all domains
* Git for version control across all domains


## Design notes 


Besides the initial idea, the following shall be used as starting notes for the actual design:

the leader arm shall make use of potentiometers to measure angles
the follower shall use microservo motors as its actuators
a STM32G4 shall be the central controller 
PWMs for the servos shall be provided by an external multi-channel PWM generator
ADC readings shall be taken by an external multi-channel ADC chip 
mechanical parts will be 3-printed or are standard parts (nuts, bolts, threads)

