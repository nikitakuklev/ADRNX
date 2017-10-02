import sys,threading,warnings,serial,time,logging,queue,yaml,serial
#sys.path.append('/home/pi/Desktop/ADRNX/Utils')
#sys.path.append('/home/pi/Desktop/ADRNX')
import SIM_MOD,SIM_MOD_STREAMER,SIM921, SIM922, SIM960, SIM970
from timeit import default_timer as timer


class SIM900:
    debug = True
    input_thread_on = False
    output_thread_on = False

    sim900q_out = queue.Queue(1000) #FIFO queue OUT
    sim900q_in = queue.Queue(1000) #FIFO queue IN
    sim970q = queue.Queue(1000) #FIFO queue
    sim960q = queue.Queue(1000) #FIFO queue
    sim922q = queue.Queue(1000) #FIFO queue
    sim921q = queue.Queue(1000) #FIFO queue
    sim900q = queue.Queue(1000) #FIFO queue
    excq = queue.Queue(1000)

    modnumlist = []
    moddict = {}

    def __init__(self, config, debug=True):
        self.birthtime = timer()
        self.debug = debug
        with open(config, 'r') as f:
            cfgdict = yaml.load(f)
            self.sim900dev = cfgdict['sim900_device']
            if (self.debug): print("SIM mainframe device: {}".format(self.sim900dev))

    def init_mainframe(self):
        """ Initializes SIM900 mainframe """
        if self._check_for_old_threads(): raise Error("Old threads are still running - please restart kernel")
        ser = self._open_serial_port(self.sim900dev)
        ser.close()
        ser.open()
        ser.write("*CLS\n".encode('ascii'))
        ser.write("TERM D,LF\n".encode('ascii'))
        time.sleep(0.2)
        ser.write("MSGL 100\n".encode('ascii'))
        time.sleep(0.2)
        ser.write("FLOQ\n".encode('ascii'))
        ser.write("FLSH\n".encode('ascii'))
        self.clear_hw_queues()
        self.clear_virtual_queues()
        ser.flushInput()
        ser.flushOutput()
        time.sleep(0.2)
        self.clear_hw_queues()
        self.clear_virtual_queues()
        ser.read(10000)
        ser.flushInput()
        ser.flushOutput()
        ser.write("*IDN?\n".encode('ascii'))
        ans = ser.readline().decode('ascii').rstrip()
        if (self.debug): print("Response to IDN: " + ans)
        assert ans == 'Stanford_Research_Systems,SIM900,s/n130132,ver3.6'
        self.sim900ser = ser

    #flush our port
    def flush_port(self):
        self.sim900ser.flushInput()
        self.sim900ser.flushOutput()

    def _open_serial_port(self, device):
        """ Opens serial communications """

        ser = serial.Serial()
        ser.port = device
        ser.baudrate = 9600
        ser.bytesize = serial.EIGHTBITS #number of bits per bytes
        ser.parity = serial.PARITY_NONE #set parity check: no parity
        ser.stopbits = serial.STOPBITS_ONE #number of stop bits
        ser.timeout = 0.1
        ser.write_Timeout = 0.5
        ser.xonxoff = False
        ser.rtscts= True
        ser.dsrdtr = False
        return ser

    def _check_for_old_threads(self):
        for t in threading.enumerate():
            if t is not threading.currentThread():
                tname = t.getName()
                if 'sim' in tname: return True
        return False

    def register_and_init_mods(self, modlist):
        ser = self.sim900ser
        modnumlist = self.modnumlist
        moddict = self.moddict
        if (self.debug):print("Registering mods: "+str(modlist))
        for mod in modlist:
            if isinstance(mod,SIM_MOD.SIM_MOD):
                if mod.MODNUM in modnumlist or mod.MODNUM in moddict.keys():
                    raise ValueError("Module already registered")
                modnumlist.append(mod.MODNUM)
                moddict[mod.MODNUM] = mod
                if isinstance(mod,SIM_MOD_STREAMER.SIM_MOD_STREAMER):
                    #ser.write("SRST {}\n".format(mod.MODNUM).encode('ascii'))
                    time.sleep(0.02)
                    ser.write('SNDT {},"{}"\n'.format(mod.MODNUM,"TERM CR").encode('ascii'))
                    ser.write('SNDT {},"{}"\n'.format(mod.MODNUM,"*CLS").encode('ascii'))
                    ser.write('FLSH {}\n'.format(mod.MODNUM).encode('ascii'))
                if isinstance(mod,SIM922.SIM922):
                    self.sim922 = mod
                    ser.write('SNDT {},"{}"\n'.format(mod.MODNUM,"CURV 0,1;EXON 0,1").encode('ascii'))
                    if (self.debug): print("SIM 922 registered!")
                if isinstance(mod,SIM921.SIM921):
                    self.sim921 = mod
                    if (self.debug): print("SIM 921 registered!")
                if isinstance(mod,SIM970.SIM970):
                    self.sim970 = mod
                    if (self.debug): print("SIM 970 registered!")
                if isinstance(mod,SIM960.SIM960):
                    self.sim960 = mod
                    if (self.debug): print("SIM 960 registered!")
            else:
                raise ValueError("A module class must be supplied for registration")
        #if (self.debug): print(self._cmd_set_RPER(modnumlist))
        ser.write((self._cmd_set_RPER(modnumlist)+"\n").encode('ascii'))
        if (self.debug): print("Mod nums: "+str(modnumlist))

    def get_serial_object(self):
        return self.sim900ser

    def clear_virtual_queues(self):
        self.sim970q.queue.clear()
        self.sim960q.queue.clear()
        self.sim922q.queue.clear()
        self.sim921q.queue.clear()
        self.sim900q.queue.clear()

    def clear_hw_queues(self):
        self.sim900q_out.queue.clear()
        self.sim900q_in.queue.clear()

    def start_comm_threads(self):
        self._start_output_loop()
        self._start_input_loop()

    def stop_comm_threads(self):
        self._stop_output_loop()
        self._stop_input_loop()

    def shutdown(self):
        self.stop_comm_threads()
        time.sleep(2)
        if self._check_for_old_threads(): raise RuntimeError("FAILED TO STOP THREADS")
        if (self.debug): print("SRS is shut down")

    ######################################################################
    def _start_input_loop(self):
        if (not self.input_thread_on):
            self.input_thread_on = True
            thread = threading.Thread(name='srsinput',target=self._input_loop, args=(self.sim900ser,))
            thread.setDaemon(True)
            thread.start()
            if (self.debug): print("Input loop started")
        else:
            print("Input loop ALREADY ON")

    def _stop_input_loop(self):
        self.input_thread_on = False
        if (self.debug): print("Input loop stopping after next iteration")

    def _input_loop(self, ser):
        thread = threading.Thread(name='srsinputreadloop',target=self._mfc_in_t, args=(ser,))
        thread.setDaemon(True)
        thread.start()
        #self._sim900_input_read_thread(ser)
        while self.input_thread_on:
            #if (self.debug): print("Processing input")
            self._iq_process(ser)
            time.sleep(0.01)

    def _mfc_in_t(self, ser):
        debugl = self.debug
        ser.timeout = 0
        if (debugl): print("Input read thread is up!")
        resp = str()
        while (self.input_thread_on):
            while(ser.inWaiting()>0):
                #respchars = ser.read(ser.inWaiting()).decode('ascii')
                respchars = ser.read(ser.inWaiting()).decode('ascii')
                if (debugl): print("Read chars: |{}|".format(repr(respchars)))
                resp += respchars
                if ('\n' in resp):
                    if (resp == '\n'):
                        resp = str()
                        if (debugl): print("Blank line ignored!")
                    else:
                        respsp = resp.split('\n')
                        if (debugl):
                            print("Resp split result: ")
                            print(respsp)
                        if (len(respsp) == 2 and respsp[-1] == ''):
                            if (debugl): print("Read single line: " + repr(respsp[0]))
                            self.sim900q_in.put_nowait(respsp[0].rstrip('\n'))
                            resp = str()
                        else:
                            for respval in respsp[:-1]:
                                if respval != '':
                                    if (debugl): print("Read multiline: " + repr(respval))
                                    self.sim900q_in.put_nowait(respval.rstrip('\n'))
                                else:
                                    if (debugl): print("Blank line ignored!")
                            resp = respsp[-1]
                            if (debugl): print("Leftover response: " + repr(resp))
            time.sleep(0.02)

    def _iq_process(self, ser):
        debugl = self.debug
        while (not self.sim900q_in.empty()):
            resp = self.sim900q_in.get_nowait()
            #resp = resp.replace('\r','').replace('\n','')
            #resp = resp.rstrip()
            if (resp.startswith('MSG')):
                [source,message] = self._msg_parser(resp)
            else:
                source = 0
                message = resp

            #message = message
            if (debugl): print("GOT MSG -> S{}:{}".format(source,repr(message)))

            if len(message) == 0:
                continue
            elif (source == SIM970.SIM970.MODNUM):
                #if (debugl): print("Placed into sim960q")
                self.sim970q.put_nowait([message,timer()])
            elif (source == SIM960.SIM960.MODNUM):
                #if (debugl): print("Placed into sim960q")
                self.sim960q.put_nowait([message,timer()])
            elif (source == SIM921.SIM921.MODNUM):
                #if (debugl): print("Placed into sim921q")
                self.sim921q.put_nowait([message,timer()])
            elif (source == SIM922.SIM922.MODNUM):
                #if (debugl): print("Placed into sim922q")
                self.sim922q.put_nowait([message,timer()])
            else:
                #if (debugl): print("Placed into sim900q")
                self.sim900q.put_nowait([message,timer()])

    def _msg_parser(self, msg):
        debugl = self.debug
        #msg = msg.rstrip()
        #if (debugl): msg = 'MSG 5,#210blllaaaaaq'
        check1 = msg.startswith('MSG')
        if (not check1): raise IOError("Bad message header")
        msgs = msg.split(',',1)
        if (len(msgs) != 2): raise IOError("Bad message: " + repr(msg))
        modulenum = int(msgs[0][-1])
        msg2 = msgs[1]
        numdigit = int(msg2[1])
        if numdigit == 2:
            numchar = int(msg2[2:4])#numchar = int(msg2[2:4])-2
        elif numdigit == 3:
            numchar = int(msg2[2:5])-1#numchar = int(msg2[2:5])-3
        else:
            raise IOError("Bad message digit counter")

        msg3 = msg2[(2+numdigit):]
        #numchar -= 1 # TERM LF
        #if (debugl): print(msg3.count('\r'))
        if (debugl): print(msgs),
        if (debugl): print("| {} | {} | {} | {} | {} |".format(modulenum,numdigit,numchar,repr(msg),repr(msg3)))
        if len(msg3) != numchar:
            # if self.moddict[modulenum].message_parser_override():
            #     return (modulenum,msg3)
            #raise IOError("Bad message payload length({}): {} (want {})".format(msg,len(msg),numchar))
            warnings.warn("Bad message payload length - msg:|{}| len:|{}| (want |{}|)".format(repr(msg),len(msg3),numchar))
            #if(modulenum == SIM970.SIM970.MODNUM): msg = "" #very hacky
        return (modulenum,msg3)

    #####################################################################
    # Adds command to the queue
    # Types - 0=reg wait; 1=extra wait
    def oq_add(self, cmd, tp=0):
        if (not self.output_thread_on): warnings.warn("Commands placed into output queue but it is not running!")
        if self.debug: print("OQADD (t:{}): |{}|".format(tp,repr(cmd)))
        self.sim900q_out.put_nowait([cmd,tp])

    def _start_output_loop(self):
        if (not self.output_thread_on):
            self.output_thread_on = True
            thread = threading.Thread(target=self._mfc_out_t, args=(self.sim900ser,))
            thread.setDaemon(True)
            thread.start()
            if (self.debug): print("Output loop started")
        else:
            print("Output loop ALREADY ON")

    def _stop_output_loop(self):
        self.output_thread_on = False
        if (self.debug): print("Output loop stopping after next iteration")

    def _mfc_out_t(self, ser):
        while self.output_thread_on:
            #if (self.debug): print("Processing output")
            self._oq_process(ser)
            time.sleep(0.01)

    def _oq_process(self, ser):
        start = timer()
        while (not self.sim900q_out.empty() and (timer()-start)<1.0):
            [cmd, tp] = self.sim900q_out.get_nowait()
            if self.debug: print("OQSEND (t:{}): |{}|".format(tp,repr(cmd)))
            ser.write(cmd.encode('ascii'))
            if (tp == 1):
                time.sleep(0.2)
            else:
                time.sleep(0.01)

    #####################################################################
    #enumerate all modules
    # def enumerate_modules(ser):
    #     for i in range(1,9):
    #         ser.write('SNDT {},"*IDN?"\n'.format(i))
    #         time.sleep(0.3)
    #         ser.write('GETN? {},128\n'.format(i))
    #         time.sleep(0.3)
    #         # have to not use readline because empty slots return weird results otherwise
    #         response = ser.read(128).encode('unicode_escape')
    #         print("Slot {} - {}".format(i,response))

    def await_response(self):
        start = timer()
        if (not self.sim900q.empty):
            raise Error("Already have responses in queue")
        while (timer()-start)<2.0:
            if (not self.sim900q.empty()):
                [msg,tmr] = self.sim900q.get()
                print("GOT RESP IN {}".format(tmr-start))
                return msg
            time.sleep(0.01)
        return repr("<NO RESP>")

    def process_cmd_with_resp(self,cmd):
        self.send_CMD_mf(cmd)
        return self.await_response()

    def process_cmd_no_resp(self,cmd):
        self.send_CMD_mf(cmd)

    # BASIC COMMANDS
    #flush mainframe
    def flush_mf(self):
        self.oq_add("FLOQ\n")
        self.oq_add("FLSH\n")

    def reset_status_register(self):
        self.oq_add("*CLS\n")

    #get identity
    def get_IDN(self):
        self.oq_add(self.__cmd_IDN())
        return self.await_response()
    def __cmd_IDN(self):
        return ('*IDN?\n')

    #resets
    def reset(self):
        self.oq_add(self.__cmd_RST())
    def __cmd_RST(self):
        return ('*RST\n')

    #get message passthrough bits
    def get_RPER(self):
        self.oq_add(self._cmd_RPER())
        return self.await_response()
    def _cmd_get_RPER(self):
        return ('RPER?\n')

    #set message passthrough bits
    def set_RPER(self,ports):
        self.oq_add(self._cmd_set_RPER(ports))
    def _cmd_set_RPER(self,ports):
        portbin = 0
        for i in ports:
            portbin += int(1 << i)
        return ('RPER {}\n'.format(portbin))

    #reset message passthrough bits
    def reset_RPER(self):
        self.oq_add(self._cmd_reset_RPER())
    def _cmd_reset_RPER(self):
        return ('RPER 0\n')

    #send command to module
    def send_CMD_module(self, port, cmd):
        #self.oq_add('SNDT {},"{}"\n'.format(port, cmd))
        self.oq_add('SEND {},"{}\n"\n'.format(port, cmd))

    #send command to mainframe
    def send_CMD_mf(self, cmd):
        self.oq_add('{}\n'.format(cmd))

    #baud change of mainframe
    def set_baud_mf(self):
        self.oq_add("BAUD D,115200\n")

    #baud change of module
    def set_baud_module(self, mod, rate):
        self.send_CMD_module(mod,"BAUD {}".format(rate))
        self.send_CMD_mf("BAUD {},{}".format(mod,rate))

    #reset comms on one of the ports
    def reset_serial_module(self, mod):
        self.oq_add("SRST {}\n".format(mod))
