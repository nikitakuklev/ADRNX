import sys,time,datetime,threading,collections,warnings,queue,SIM_MOD_STREAMER
from timeit import default_timer as timer

class SIM970(SIM_MOD_STREAMER.SIM_MOD_STREAMER):
    MODNUM = 7
    streaming_channel = 1
    _ismultistreamer = True
    lastvalues = {}
    lastdatatimes = {}
    excq = queue.Queue(1000)

    def __init__(self, mf, name, debug=1):
        self.mfc = mf
        self.sq = mf.sim970q
        self.name = name
        self.debug = debug
        self.streaming = False
        self.newdataevent = threading.Event()
        
    def tellastory(self):
        print("My name is {} (ID: {})".format(self.name,self.get_IDN()))
        print("Status is {}".format(str(bin(int(self.get_status_byte())))))
        print("Trigger mode is     {} (LOCAL 0, EXTERNAL 1, REMOTE 2)".format(self.get_trigger_mode()))
        for i in range(1,5):
            print(" Channel {} settings:".format(i))
            print("  Autocal mode is     {} (NONE 0, GND 1, GNDREF4 2, or GNDREF3 3)".format(self.get_autocal_mode(i)))
            print("  Autorange mode is   {} (see manual)".format(self.get_autorange_mode(i)))
            print("  Attenuator mode is  {} (OFF 0, ON 1, or OUT 2)".format(self.get_attenuator_mode(i)))
            print("  Filter mode is      {} (OFF 0, ON 1)".format(self.get_filter_mode(i)))

        #'MSG 7,#204 0.0\r\n'
        #'MSG 7,#208000088\r\n'
        #'MSG 7,#204 0.0\r\n'
        #'MSG 7,#208000105\r\n'
    # def get_single_voltage(self, chan):
    #     self._cmd_rdy_check_resp()
    #     chan = int(chan)
    #     self.send_cmd(self._cmd_qVOLT(chan,1))
    #     try:
    #         val = float(self.await_response())
    #         dt = datetime.datetime.fromtimestamp(timer())
    #         if (self.debug): print("Got voltage: |{}|{}|".format(val,dt.strftime('%H:%M:%S.%f')))
    #         lastvalues[chan - 1] = val
    #         lastdatatimes[chan - 1] = timer()
    #         return val
    #     except Exception as e:
    #         print(e)
    #         return None

    def get_single_voltage(self, chan=1):
        return self._get_single_value(chan=chan,vfunc=1)

    def start_data_stream(self, channel=1):
        if not self.streaming:
            self.excq.queue.clear()
            channel = int(channel)
            if channel == 0:
                self.multistream = True
            else:
                self.multistream = False
            self.send_cmd(self._cmd_qVOLT(channel,0))
            self.streaming = True
            self.streaming_channel = channel
            thread = threading.Thread(name='sim970t',target=self._sim970_thread, args=())
            thread.setDaemon(True)
            thread.start()
        else:
            warnings.warn("Streaming output is already running!")

    def _sim970_thread(self):
        try:
            debugl = self.debug
            if (debugl): print("SIM970 stream thread up")
            sq = self.sq
            count = 0
            buf = str()
            while (self.streaming):    
                while (not sq.empty()):                   
                    [val, tm] = sq.get()
                    if '\r' not in val:
                        if (debugl): print("Missing CR")
                        if count == 0:
                            buf = val
                            if (debugl): warnings.warn("SIM970 BUFFERING: |{}|".format(val))
                            count = 1
                            break
                        else:
                            count = 0
                            buf = str()
                            break
                    else:
                        if count == 1:
                            val = buf + val
                            count = 0
                            buf = str()
                            if (debugl): warnings.warn("SIM970 RESCUED FRAGMENT: |{}|".format(val))
                        else:
                            count = 0
                    dt = datetime.datetime.fromtimestamp(tm)
                    if (debugl): print("Final val: {}".format(repr(val)))
                    val = val.rstrip()
                    if (self.multistream):
                        if len(val) != 43:
                            if (debugl): warnings.warn("SIM970M BAD LENGTH: |{}|({})".format(val,len(val)))
                            break
                        vals = val.split(',')
                        if len(vals) != 4:
                            if (debugl): warnings.warn("SIM970M BAD MULTISTREAM - |{}|".format(repr(val)))
                            break
                        b = False
                        for i in range(0,4):
                            val1 = vals[i]
                            if val1 == 'E+00' or val1 == 'E+01' or val == 'E+02':
                                if (debugl): warnings.warn("SIM970MI BAD MSG: |{}|".format(val1))
                                b = True; break
                            if len(val1) != 10:
                                if (debugl): warnings.warn("SIM970MI BAD LENGTH: |{}|".format(val1))
                                b = True; break
                            if '.' not in val1[0:4]:
                                if (debugl): warnings.warn("SIM970MI BAD MSG: |{}|".format(val1))
                                b = True; break
                            try:
                                valf = float(val1)
                                if valf > 500.1:
                                    #raise ValueError("SIM922 TEMP WTF!!!")
                                    if (debugl): warnings.warn("SIM970M WTF TEMP - |{}|{}|".format(valf,repr(val1)))
                                    b = True; break
                                else:
                                    self.lastvalues[i] = valf
                                    self.lastdatatimes[i] = tm
                            except Exception as e:
                                if (debugl): print("OOPS")
                                if (debugl): print(e)
                                b = True;
                        if not b: self.newdataevent.set()
                    else:
                        if len(val) != 10:
                            if (debugl): warnings.warn("SIM970 BAD LENGTH: |{}|".format(val))
                            break
                        if '.' not in val[0:4]:
                            if (debugl): warnings.warn("SIM970 BAD MSG: |{}|".format(val))
                            break
                        try:
                            if (debugl): print("Got voltage: |{}|{}|".format(val,dt.strftime('%H:%M:%S.%f')))
                            valf = float(val)
                            if valf > 20.0 or valf < -20.0:
                                raise ValueError("{}: VALUE OUT OF BOUNDS".format(self.name));
                            else:
                                self.lastvalues[self.streaming_channel] = valf
                                self.lastdatatimes[self.streaming_channel] = tm
                                self.newdataevent.set()
                        except Exception as e:
                            if (debugl): print(e)
                            if (debugl): warnings.warn("{}: BAD VALUE |{}|".format(self.name,valf))
                            break
                time.sleep(0.01)
        except Exception as e:
            self.excq.put(sys.exc_info())

    ### SIM970 COMMANDS
    def _cmd_qVOLT(self, channel, amt):
        return ('VOLT? {},{}'.format(channel,amt))
    _valuefunction1 = _cmd_qVOLT

    def get_attenuator_mode(self, channel):
        return self._process_cmd_with_resp(self._cmd_qDVDR(channel),channel)
    def _cmd_qDVDR(self, channel):
        return ('DVDR? {}'.format(channel))

    def get_autocal_mode(self, channel):
        return self._process_cmd_with_resp(self._cmd_qCHOP(channel),channel)
    def _cmd_qCHOP(self, channel):
        return ('CHOP? {}'.format(channel))

    def get_autorange_mode(self, channel):
        return self._process_cmd_with_resp(self._cmd_qAUTO(channel),channel)
    def _cmd_qAUTO(self, channel):
        return ('AUTO? {}'.format(channel))

    def get_filter_mode(self, channel):
        return self._process_cmd_with_resp(self._cmd_qFLTR(channel),channel)
    def _cmd_qFLTR(self, channel):
        return ('FLTR? {}'.format(channel))

    def get_trigger_mode(self):
        return self._process_cmd_with_resp(self._cmd_qTMOD())
    def _cmd_qTMOD(self):
        return ('TMOD?')

class CHANNELS:
    MAGEMF = 1
