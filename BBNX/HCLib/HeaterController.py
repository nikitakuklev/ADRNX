"""
HeaterController class provides all the methods
required to control HC module. It looks through any ports
in appropriate devicelist, listening for key hello messages.

06/15/2017 Nikita Kuklev
"""

import serial, threading, sys, time, numbers
import numpy as np

class Core:
    devicelist_win = ['COM4','COM3'] # List of devices that will be attempted, in order
    devicelist_unix = ['/dev/ADR_hc','/dev/ttyUSB2']
    devicekey = 'HCA011' # HeaterControl type A0 and serial number 11
    devicelist = []
    
    def __init__(self,debug=False,override_device=None):
        self.debug = debug
        if override_device is not None: self.devicelist = [override_device]

    # Detect opeating system and choose right device list
    def _get_device_list(self):
        if not self.devicelist:
            if sys.platform.startswith('win'):
                self.devicelist = self.devicelist_win
            elif sys.platform.startswith('linux') or sys.platform.startswith('cygwin'):
                self.devicelist = self.devicelist_unix
            else:
                raise EnvironmentError('Unsupported platform')

        if(self.debug): print('HCDBG: Platform ({}) -> device list is {}'.format(sys.platform,self.devicelist))

    # Prepares serial port but does not open it
    def _prepare_serial_port(self):
        ser = serial.Serial()
        ser.baudrate = 9600
        ser.timeout = 0.2
        ser.write_Timeout = 0.5
        ser.bytesize = serial.EIGHTBITS #number of bits per bytes
        ser.parity = serial.PARITY_NONE #set parity check: no parity
        ser.stopbits = serial.STOPBITS_ONE #number of stop bits
        ser.xonxoff = False
        ser.rtscts= False
        ser.dsrdtr = False

        if(self.debug): print('HCDBG: Port ready: {}'.format(ser))
        self.serport = ser

    def establish_comms(self):
        debugl = self.debug
        self._prepare_serial_port()
        self._get_device_list()
        ser = self.serport
        devicelist = self.devicelist
        devicefound = False
        linelim = 20
        if(debugl): print('HCDBG: Starting device search')
        for device in devicelist:
            try:
                ser.port = device
                if (ser.isOpen()):
                    if(debugl): print('HCDBG: Port {} already open, skipping'.format(device))
                    #ser.close()
                else:
                    ser.open()
                    time.sleep(1)
                    for i in range(1,linelim):
                        ln = ser.readline().decode('ASCII').rstrip()
                        time.sleep(0.1)
                        if(ln == self.devicekey):
                            devicefound = True
                            self.deviceportname = device
                            if(debugl): print('HCDBG: Port {} CORRECT msg: {}'.format(device, ln))
                            break
                        else:
                            if(debugl): print('HCDBG: Port {} incorrect msg: {}'.format(device, ln))

            except serial.SerialException as err:
                if(debugl): print('HCDBG: Port {} did not work, exception: {}'.format(device, err))

            finally:
                if (not devicefound):
                    ser.close()
                else:
                    break

        if(not devicefound):
            print('HC: Did not find any suitable ports -> terminating')
            raise EnvironmentError('No appropriate devices found!')
        else:
            if(debugl): print('HCDBG: Found device on port {} -> connected!'.format(device))

        # Reply with greeting
        time.sleep(0.05)
        ser.write((self.devicekey+'\n').encode('ASCII'))
        time.sleep(0.01)
        ser.flushInput()
        ser.flushOutput()
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        time.sleep(0.1)
        rdyresp = ser.readline().decode('ASCII').rstrip()
        if(rdyresp == "RDY"):
            if(debugl): print('HCDBG: Device READY!')
        else:
            if(debugl): print('HCDBG: Device rdy reply was {}'.format(rdyresp))
            raise EnvironmentError('Device did not reply it was ready')

    def send_command(self,msg):
        msg = msg+'\n'
        msg = msg.encode('ASCII')
        if(self.debug): print("Sending command: |{}|".format(repr(msg)))
        self.serport.write(msg)
        time.sleep(0.02)
        return self.serport.readline().decode('ASCII').rstrip()

    def flush_serial(self):
        self.serport.reset_input_buffer()
        self.serport.reset_output_buffer()

    def get_type(self):
        return self.send_command('TYPE??')

    def get_serialnum(self):
        return self.send_command('SN????')

    def get_onoff(self):
        return self.send_command('QS????')

    def set_onoff(self, st):
        if st == 1:
            resp = self.send_command('ON0000')
        elif st==0:
            resp = self.send_command('OFF000')
        else:
            raise IOError("HC: Unexpected status requested")
        if resp != 'OK':
            raise IOError("HC: Unexpected ONOFF command response")

    def get_dutycycle(self):
        return self.send_command('QC????')

    def set_dutycycle(self, duty):
        try:
            duty = float(duty)
        except Exception as e:
            raise ValueError("HC: can't convert duty to float")
        if (duty <0.0 or duty >100.0):
            raise ValueError("HC: duty cycle outside 0-100 -> {}".format(duty))
        val = int(9999.0*duty/100.0)
        resp = self.send_command('SC{:04d}'.format(val))
        if resp != 'OK':
            raise IOError("HC: Unexpected DCYCLE command response")
