## ADRNX (ADR Next)
As the name suggests, ADRNX was born as a complete rewrite of cryostat control/automation framework for HPD ADR 104 Olympus cryostat in typical SRS 900 mainframe + breakout panel configuration. It is designed to allow for pseudo-asynchronous, queue-based communication with the various modules in the mainframe (over shared serial port) as well as additional equipment (heaters, VNA, etc.). Additional modules can easily be added to adapt it for other configurations.


### Architecture
The core problem with using SRS900 mainframe is that extreme care is needed to address and listen to responses from multiple modules over shared serial port. Instead of 'connecting' to each module in sequence, ADRNX utilizes message packet features to abstract this task, presenting 'virtual' queues to user code, as if each had a dedicated serial connection. Furthermore, for the modules used in our particular setup, most typical commands are implemented as simple function calls.

For most measurement devices, two DAQ approaches are provided - a single shot query, and continuous streaming. In case of latter, modules are instructed to continuously stream data, which is buffered by ADRNX in the background. User code can then asynchronously query last result or await next data event. 

It has to be noted that there are a number of quircks with messaging protocol - from occasional loss/fragmentation of messages to incorrect header lengths to weird LF/CR behaviour. As such, each module has extensive custom handling section which rejects impossible values, does various manipulations to recover data, and ultimately tries to only let valid messages pass. If you are having communication errors, this would be the place to check for known issues.



Other parts of ADRNX are relatively straightforward:

**HCLib** - Comms library for dedicated arduino black body heater (see [here](https://github.com/nikitakuklev/BBDuino) for FW)

**pyVNA** - Control library for HP87XXD series of VNAs (via prologix USB-GPIB adapter)

**Switchduino.py** - A port of library used to communicate with arduino relay/heat switch controller



### Usage
A basic example of a complete magcycle is given in the tutotial notebook



### Licensing
See [license](LICENSE)

