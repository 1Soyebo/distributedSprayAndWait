--------------------------------------------------------------------
Background Info
--------------------------------------------------------------------

Demo for showing coordination between a number of UAVs regarding tracking an equal number of targets.
In the ideal case, each UAV tracks one target, different than the one tracked by any other UAV.

Sample Mission Scenario:
	- Each UAV can track only one target at a time
	- Once tracking a target, a UAV “locks” on it
	- Does not switch targets unless the current one gets out of range

(Very) Simple Algorithm:
	- Find a target
	- If the target is already tracked, then search for another one
	- If the target is not tracked, then advertise to others that the target is now tracked
	- Start tracking the target

--------------------------------------------------------------------
Software dependencies for running test script
--------------------------------------------------------------------

Install NRL software (mgen and trpr) for plotting:

	$ git clone https://github.com/USNavalResearchLaboratory/mgen.git
	$ cd mgen
	$ git clone https://github.com/USNavalResearchLaboratory/protolib.git
	$ cd makefiles
	$ make -f Makefile.linux
	$ sudo mv mgen /usr/local/sbin

	$ git clone https://github.com/USNavalResearchLaboratory/trpr.git
	$ cd trpr
	$ make -f Makefile.linux
	$ sudo mv trpr /usr/local/sbin

Other dependencies: 

	$ sudo apt install gnuplot
	$ sudo apt install eog
	$ sudo apt install libpcap0.8-dev

--------------------------------------------------------------------
Installing CORE
--------------------------------------------------------------------

Download and install CORE emulation environment:

	- Instructions: https://coreemu.github.io/core/ 
	- Core Git: 	https://github.com/coreemu/core 


Allow CORE daemon to listen on the control interface:

    - edit /etc/core/core.conf

		$ sudo vi /etc/core/core.conf

    - change "grpcaddress = localhost" to "grpcaddress = [::]"

--------------------------------------------------------------------
Creating the emulation testbed
--------------------------------------------------------------------

Running CORE

  	1. start core daemon
		$ sudo core-daemon

  	2. start core GUI (beta version)
		$ core-pygui
        Note: To use old gui, use command "core-gui"

  	3. create or load scenario uav8-notrack-new-gui.xml

--------------------------------------------------------------------
Running the swarm scenario
--------------------------------------------------------------------

Create directory /data/uas-core

    $ mkdir /data/uas-core

Create a soft link to icons folder and move_node_grpc.py script 

    $ cd /data/uas-core
    $ ln -s <UAV-SWARM-SCENARIO-DIRECTORY>/icons .
    $ ln -s <UAV-SWARM-SCENARIO-DIRECTORY>/move_node_grpc.py . 

Note:   The scenario uav8-notrack-new-gui.xml contains hard links to the icons folder and move node script. 
        To run the scenario without creating the /data/uas-core directory, edit the uav8-notrack.xml to change these hard links.

To run the scenario, start the .xml file in CORE. Then, on a terminal on the host machine,
run ./start_tracking_grpc.sh <service> where <service> is:
    - none 
    - udp 

    $ cd <UAV-SWARM-SCENARIO-DIRECTORY>
    $ ./start_tracking_grpc.sh udp 

	**Note: When you make code changes to "track_target_grpc.py", you can just re-run the "start_tracking_grpc.sh" script. 
			You do not need to restart the CORE scenario every time you update the "track_target_grpc.py" script. 

--------------------------------------------------------------------
Running the test script
--------------------------------------------------------------------

Make sure to start the .xml file in CORE and running start_tracking_grpc.sh script.
Then, on a terminal on the host machine, run ./start_test_grpc.sh <service> where <service> is: 
	- none
	- udp

	$ cd <UAV-SWARM-SCENARIO-DIRECTORY>
	$ cd test
	$ ./start_testing_grpc.sh udp

To run without the plots, run only the python script: 

	$ cd <UAV-SWARM-SCENARIO-DIRECTORY> 
	$ cd test
	$ core-python test_uavs_grpc.py udp


--------------------------------------------------------------------
How to run or install python scripts in CORE environment
--------------------------------------------------------------------

CORE uses Python Poetry. 

If you wish to run or install any Python software in the CORE environment, 
you would run "core-python" instead of "python". 

Example: 

	$ core-python test.py

Example:

	$ core-python setup.py install 


		









