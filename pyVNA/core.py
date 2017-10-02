import serial,sys,time,math,datetime,os,warnings,struct,math,numpy as np
from timeit import default_timer as timer
from pyVNA import constants
#from .constants import VNA_MEAS

class VNA():    
    serial_name = "/dev/ttyUSB2"
    st = 0.55
    pt = 500
    startf = 0
    stopf = 0
    numpoints = 0
    ifbw = 0
    power = 0
    mode = ""
    meas = ""
    
    def __init__(self, dev="/dev/ttyUSB2",debug=False):
        self.serial_name = dev
        self.debug = debug
                    
    def init_and_setup(self):
        """Open serial connetion and setup GPIB adapter. """
        
        ser = serial.Serial()
        self.ser = ser
        ser.port = self.serial_name
        ser.baudrate = 115200
        ser.timeout = self.st
        ser.open()        
        time.sleep(0.2)        
        ser.flushInput()
        ser.flushOutput()
        ser.write('++savecfg 0\n'.encode('ascii'))
        ser.write('++auto 0\n'.encode('ascii'))
        ser.write('++addr 16\n'.encode('ascii'))
        self.set_tm(self.pt)        
        
    def preset(self,tm=5):
        """ Preset the VNA and wait until done (by default, to factory settings). """
        
        self.send_command_no_resp('OPC?;PRES;')
        self.await_completion(tm)
        #send_command_no_resp('LINFREQ;')        
        
    def read_line_gpib(self):
        """ Reads in a single line from GPIB (expects LF terminator). """
        ser = self.ser
        self.set_tm(self.pt*2) 
        ser.timeout = self.st*2
        ser.write('++read eoi\n'.encode('ascii'))
        resp = ser.readline().decode().rstrip()
        if (self.debug): print("Read line: got |{}|".format(repr(resp)))
        return resp

    def read_all_gpib_bytes(self, tm):
        """ Read in whatever comes along for specified time """
        
        ser = self.ser
        ser.write('++read eoi\n'.encode('ascii'))   
        resp = bytes()
        lentot = 0
        start = timer()
        while timer()-start < tm:
            resppart = ser.read(100000)
            time.sleep(0.01)
            print(len(resppart))
            lentot += len(resppart)
            resp += resppart
        if (self.debug): print('Read {} bytes'.format(lentot))
        return resp
    
    def flush_gpib(self,tm): 
        """ Read in and discard whatever comes for specified time """
        
        self.set_tm(self.pt)
        self.ser.timeout = self.st
        start = timer()
        while timer()-start < tm:
            self.ser.write('++read eoi\n'.encode('ascii'))
            self.ser.read(512000) #should time out in self.st

    def read_all_gpib_bytes_withtarget(self,amt,tm=20): 
        """
        Read GPIB in a loop until either timeout is exceeded
        or the specific number of bytes is read
        """
        
        ser = self.ser
        ser.timeout = 0.18   
        self.set_tm(150)
        resp = bytes()
        lentot = 0
        st = timer()
        st2 = timer()        
        while lentot < amt and timer()-st < tm:
            if (timer()-st2 > 0.45):
                ser.write('++read eoi\n'.encode('ascii'))
                st2 = timer()
            time.sleep(0.01)
            resppart = ser.read(amt)
            time.sleep(0.01)
            if (self.debug): print(len(resppart))
            if (len(resppart) != 0):
                lentot += len(resppart)
                resp += resppart
                st2 = timer()
                if (lentot>=amt):
                    break
        if (self.debug): print('Read {} bytes'.format(lentot))
        ser.timeout = self.st
        self.set_tm(self.pt)
        return resp

    def read_serial(self):   
        """ Read serial comm and return result"""
        return ser.read(128000).decode('ascii').rstrip()

    def send_command_with_resp(self,cmd,tm=1):
        """ Send command and then read a single line back """
        self.ser.write('{}\n'.format(cmd).encode('ascii'))
        time.sleep(0.02)
        return self.read_line_gpib()

    def send_command_no_resp(self,cmd):
        """ Send command and return """
        self.ser.write('{}\n'.format(cmd).encode('ascii'))

    def await_completion(self,tm):
        """ Used after OPC to wait for 1 response (or timeout) """
        start = timer()
        while (self.read_line_gpib() != '1' and timer()-start < tm):
            time.sleep(0.05)
        if timer()-start < tm:            
            if (self.debug): print("Confirmation received in {:3.2f}s".format(timer()-start))
            return timer()-start
        else:
            warnings.warn("Did not receive confirmation before timeout")
            return -1

    def print_current_state(self):
        self.update_current_state()
        print("Current settings: [{} to {}]Mhz with {} points, IFBW of {} at {} dBm".format(self.startf/1e6,self.stopf/1e6,\
                                                                                         self.numpoints,self.ifbw,self.power))
        
    def update_current_state(self):
        self.flush_gpib(0.3)
        time.sleep(0.01)
        [start,stop] = self.get_freq_range()
        self.startf = start
        self.stopf = stop
        time.sleep(0.01)
        self.numpoints = self.get_num_points()
        time.sleep(0.01)
        self.ifbw = self.get_ifbw()
        time.sleep(0.01)
        self.power = self.get_power()
                   
    # setters and getters
    def _set_parameter(self,cmd,val):
        try:
            self.send_command_no_resp(cmd.format(val))
        except Exception as e:
            print(e)
            warnings.warn("FAILED")
            
    def do_full_measurement(self,params):
        start = timer()
        if params["preset"]: self.preset(tm=5)            
        if not self.check_if_true(params["meas"]): self.set_meas_mode(params["meas"])
        if not self.check_if_true(params["mode"]): self.set_plot_mode(params["mode"])
        self.set_ifbw(params["ifbw"])
        self.set_num_points(params["numpoints"])
        self.set_freq_range(params["freqs"][0],params["freqs"][1],params["freqs"][2])
        self.set_power(params["power"])
        swt = self.get_actual_sweep_time()
        if (self.debug): self.print_current_state()
        sweep_parameters = self.start_sweep()
        timetaken = self.await_completion(swt+30.0)
        if timetaken < 0: raise ValueError("Sweep did not complete in time")
        data2 = self.retrieve_sweep_data(pause=0,form=2)   
        results = self.parse_vna_data(sweep_parameters, data2, form=2)   
        if (self.debug): print("Took {} for full measurement".format(timer()-start))
        return results
        
    def start_sweep(self,useopc=True):
        if useopc:
            self.send_command_no_resp('OPC?;SING;')
        else:
            self.send_command_no_resp('SING;') 
        params = {}
        params["ifbw"] = self.ifbw
        params["F"] = np.linspace(self.startf,self.stopf,self.numpoints)
        params["power"] = self.power
        params["sweeptime"] = datetime.datetime.now()
        return params
            
    def retrieve_sweep_data(self,pause=10,form=2):
        self.flush_gpib(0.3)
        if form==2:
            self.send_command_no_resp('FORM2;OUTPFORM;')
        elif form==4:
            self.send_command_no_resp('FORM4;OUTPFORM;')    
        time.sleep(pause)
        return self.read_all_gpib_bytes_withtarget(self.estimate_sweep_size(form))
            
    def estimate_sweep_time(self):
        if self.ifbw == 10:
            time = self.numpoints * 0.105
        else:
            time = self.numpoints * 0.105 / ((self.ifbw/10))
        return time
    
    def get_actual_sweep_time(self):
        try:
            return float(self.send_command_with_resp('SWET?;'))
        except Exception as e: 
            print(e)
            warnings.warn("SWEEP TIME FAILED")  
            
    def estimate_sweep_size(self,form=2):
        if form == 4:
            return self.numpoints * 50
        elif form == 2:
            return self.numpoints * 8 + 4
        else:
            raise ValueError("Bad form number")
        
    def set_tm(self,tm=3000):
        """ Set timeout of GPIB adapter reads in ms (max=3000, min=0) """
        self.ser.write('++read_tmo_ms {}\n'.format(tm).encode('ascii'))
        
    def get_power(self):
        try:
            return float(self.send_command_with_resp('POWE?;'))
        except Exception as e: 
            print(e)
            warnings.warn("POWER FAILED")            
    def set_power(self,val):
        assert float(val) >= -30 and float(val) <= 10
        self._set_parameter('POWE{};',float(val))
        self.power = float(val)
        
    def get_num_points(self):
        try:            
            return int(float(self.send_command_with_resp('POIN?;')))
        except Exception as e: 
            print(e)
            warnings.warn("NUM POINTS FAILED")            
    def set_num_points(self,val):
        assert int(val) in [3,11,26,51,101,201,401,801,1601]
        self._set_parameter('POIN{};',int(val))
        self.numpoints = int(val)
        
    def set_plot_mode(self,val):
        assert val in constants.VNA_MODE.allconsts
        self.send_command_no_resp(val)
        
    def set_meas_mode(self,val):
        assert val in constants.VNA_MEAS.allconsts        
        self.send_command_no_resp(val)
            
    def get_ifbw(self):
        try:
            return int(float(self.send_command_with_resp('IFBW?;')))
        except Exception as e:
            print(e)
            warnings.warn("IFBW FAILED")            
    def set_ifbw(self,val):
        assert int(val) in [10,30,100,300,1000,3000,3700]
        self._set_parameter('IFBW{};',int(val))
        self.ifbw = int(val)
            
    def get_freq_range(self):
        try:
            start = float(self.send_command_with_resp('STAR?;'))
            span = float(self.send_command_with_resp('SPAN?;'))
            return [start, start+span]   
        except Exception as e: 
            print(e)
            warnings.warn("FREQ RANGE FAILED")            
    def set_freq_range(self,start,end,units='MHZ'):
        try: 
            units = units.upper()
            if units == 'MHZ':
                factor = 1000000.0
            elif units == 'KHZ':
                factor = 1000.0
            elif units == 'GHZ':
                factor = 1000000000.0
            elif units == 'HZ':
                factor = 1.0
            else:
                raise ValueError("Wrong units")
            start = int(start*factor)
            end = int(end*factor)    
            assert start > 50000000 and start < end and end < 40000000000
            self._set_parameter('STAR{};',start)
            time.sleep(0.01)
            self._set_parameter('STOP{};',end)
            self.startf = start
            self.stopf = end
        except Exception as e:
            print(e)
            warnings.warn("FAILED")
            
    def check_if_true(self, cmd):
        assert cmd in constants.VNA_MEAS.allconsts or cmd in constants.VNA_MODE.allconsts 
        if cmd == constants.VNA_MODE.LOGMAG:
            return bool(int(self.send_command_with_resp("LOGM?;")))
        elif cmd == constants.VNA_MODE.POLAR:
            return bool(int(self.send_command_with_resp("POLA?;")))
        elif cmd == constants.VNA_MEAS.S11:
            return bool(int(self.send_command_with_resp("S11?;")))
        elif cmd == constants.VNA_MEAS.S12:
            return bool(int(self.send_command_with_resp("S12?;")))
        elif cmd == constants.VNA_MEAS.S21:
            return bool(int(self.send_command_with_resp("S21?;")))
        elif cmd == constants.VNA_MEAS.S22:
            return bool(int(self.send_command_with_resp("S22?;")))
            
    # File stuff            
    def save_results_to_file(self,data,folder='/home/pi/Desktop/DataNX/vna/',fullpath=None):
        """ Saves sweep data to log file """
        freqs = data["F"]
        il = data["I"]
        ql = data["Q"]
        date = data["sweeptime"]
        pwr = data["power"]
        ifbw = data["ifbw"]
        
        [date, logfile] = self._get_new_log_name(logroot=folder,date=date) 
        
        if fullpath is not None:
            logfile = fullpath
            
        if (self.debug): print("Log file name: " + logfile)

        if len(freqs) != len(il):
            raise IOError("Frequency list is not same size as I data")
            
        fl = open(logfile, "w")
        time.sleep(0.05)
        fl.write('DATE: {}\n'.format(date.strftime('%Y/%m/%d')))
        fl.write('TIME: {}\n'.format(date.strftime('%H:%M:%S')))
        fl.write('POWER: {}\n'.format(pwr))
        fl.write('IFBW: {}\n'.format(ifbw))
        fl.write('STIMULUS, REAL, IMAGINARY\n')
        fl.write('\n')
        for i in range(0,len(freqs)):
            try:
                fl.write('{:12.10E}, {:12.10E}, {:12.10E}\n'.format(freqs[i],il[i],ql[i]))
                #print(i)
            except Exception as e:
                print(e)
                raise e                
    
    def parse_vna_data(self,params,data,form=2):
        datadict = {}
        datadict["F"] = np.copy(params["F"])
        datadict["power"] = params["power"]  
        datadict["ifbw"] = params["ifbw"]    
        datadict["sweeptime"] = params["sweeptime"]
        if form == 4:
            try:
                ans3 = data.decode('ascii').split('\n')
                ilist = []
                qlist = []
                for s in ans3:
                    if s != '':
                        #print(s)
                        strarr = s.split(',')        
                        ilist.append(float(strarr[0]))
                        qlist.append(float(strarr[1]))
                datadict["I"] = np.array(ilist)
                datadict["Q"] = np.array(qlist)
                return datadict
            except Exception as e:
                print(e)
                raise ValueError("Bad ASCII packet")                
        elif form == 2:
            try:
                assert data[0:2] == b'#A'
                szint = int.from_bytes(data[2:4], byteorder='big')
                assert szint == len(data)-4
                dataparsed = []
                for i in range(4, len(data), 4):
                    dataparsed.append(self.__round_total_digits(struct.unpack('>f',data[i:i+4])[0]))
                datafinal = np.reshape(np.array(dataparsed),[len(dataparsed)//2,2])
                datadict["I"] = datafinal[:,0].flatten()
                datadict["Q"] = datafinal[:,1].flatten()
                return datadict
            except Exception as e:
                print(e)
                raise ValueError("Bad binary packet")
        else:
            raise ValueError("Bad form number")
            
    def __magnitude(self, x):
        return 0 if x==0 else int(math.floor(math.log10(abs(x)))) + 1

    def __round_total_digits(self, x, digits=7):
        return round(x, digits - self.__magnitude(x))        
                    
    def _get_new_log_name(self,logroot='/home/pi/Desktop/DataNX/vna/',date=None):
        """ Gets new log name based on current time """
        if date is None:
            date = datetime.datetime.now()
        #logdir = logroot+date.strftime('%Y%m%d')
        logdir = logroot
        #if not os.path.isdir(logdir):
        #    print("Directory |{}| not there, making".format(logdir))
        #    os.mkdir(logdir)
        dirs = os.listdir(logroot)
        #if (self.debug): print("Dir list: " + str(dirs))
        logfile = logdir+date.strftime('vnasweep-%Y-%m-%d-%H-%M-%S.txt')        
        return [date, logfile]