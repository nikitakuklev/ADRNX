import sys,time,datetime,threading,collections,warnings,queue,SIM_MOD_STREAMER
from timeit import default_timer as timer

class SIM922(SIM_MOD_STREAMER.SIM_MOD_STREAMER):
    MODNUM = 6
    streaming_channel = -1
    _ismultistreamer = True
    lastvalues = {}
    lastdatatimes = {}
    excq = queue.Queue(1000)
    
    def __init__(self, mf, name, debug=1, MODNUM=6):
        self.mfc = mf
        self.sq = mf.sim922q
        self.name = name
        self.debug = debug
        self.MODNUM = MODNUM
        self.streaming = False
        self.newdataevent = threading.Event()        

    def tellastory(self):
        print("My name is {} (ID: {})".format(self.name,self.get_IDN()))
        print("Status is {}".format(str(bin(int(self.get_status_byte())))))
        for i in range(1,5):
            print(" Channel {} settings:".format(i))
            print("  Cal curve mode is   {} (STAN 0, USER 1)".format(self.get_curvecal(i)))
            print("  Exitation is        {} (OFF 0, ON 1)".format(self.get_exitation(i)))
            print("  Voltage is          {} (V)".format(self.get_single_voltage(i)))
            print("  Temperature is      {} (K)".format(self.get_single_temperature(i)))

    # def get_single_value(self, chan=1):
    #     if (not self.streaming):
    #         try:
    #             if not self._ismultistreamer:
    #                 val = self._process_cmd_with_resp(self._valuefunction(1))
    #             else:
    #                 #val = self._process_cmd_with_resp(self.__cmd_qTVAL(chan,1))
    #                 assert chan > 0
    #                 val = self._process_cmd_with_resp(self._valuefunction(chan,1))
    #             val = float(val)
    #             dt = datetime.datetime.fromtimestamp(timer())
    #             if self.debug: print("Got value: |{}|{}|".format(val,dt.strftime('%H:%M:%S.%f')))
    #             lastvalues[chan] = val
    #             lastdatatimes[chan] = dt.timestamp()
    #             return float(val)
    #         except Exception as e:
    #             print(e)
    #             return None
    #     else:
    #         raise Error("Currently streaming")

    def get_single_voltage(self, chan=1):
        return self._get_single_value(chan=chan,vfunc=2)

    def get_single_temperature(self, chan=1):
        return self._get_single_value(chan=chan,vfunc=1)

    def start_data_stream(self, channel=1):
        if not self.streaming:
            self.excq.queue.clear()
            channel = int(channel)
            if channel == 0:
                self.multistream = True
            else:
                self.multistream = False
            self.send_cmd(self._cmd_qTVAL(channel,0))
            self.streaming = True
            self.streaming_channel = channel
            thread = threading.Thread(name='sim922t',target=self._sim922_thread, args=())
            thread.setDaemon(True)
            thread.start()
        else:
            warnings.warn("Streaming output is already running!")

    def _sim922_thread(self):
        try:
            debugl = self.debug
            if (debugl): print("SIM922 stream thread up")
            sq = self.sq
            while (self.streaming):
                #if self.debug: print("Beep")
                while (not sq.empty()):
                    if (debugl): print("SIM922 PROCESSING QUEUE")
                    #if debugl:
                    #    print("Processing queue")
                    [val, tm] = sq.get()
                    val = val.rstrip()
                    dt = datetime.datetime.fromtimestamp(tm)
                    #if debugl:
                    #    print("S922: DATA |{}|{}|".format(val,dt.strftime('%H:%M:%S.%f')))
                    if (self.multistream):
                        if len(val) != 54:
                            warnings.warn("SIM922M BAD TEMP LENGTH: |{}|".format(repr(val)))
                        else:
                            vals = val.split(',')
                            if (len(vals) != 4):
                                warnings.warn("BAD MULTISTREAM - |{}|".format(repr(val)))
                            else:
                                for i in range(0,4):
                                    val1 = vals[i]
                                    if val1 == 'E+00' or val1 == 'E+01' or val == 'E+02':
                                        warnings.warn("SIM922M BAD TEMP MSG: |{}|".format(val1))
                                    else:
                                        try:
                                            valf = float(val1)
                                            if valf > 500.1:
                                                #raise ValueError("SIM922 TEMP WTF!!!")
                                                warnings.warn("SIM922M WTF TEMP - |{}|{}|".format(valf,repr(val1)))
                                            else:
                                                if (debugl): print("SIM922M GOOD VALUE: |{}|".format(valf))
                                                self.lastvalues[i+1] = valf
                                                self.lastdatatimes[i+1] = tm
                                        except Exception as e:
                                            print("OOPS")
                                            print(e)
                                            raise e
                                self.newdataevent.set()
                    else:
                        if val == 'E+00' or val == 'E+01' or val == 'E+02':
                            warnings.warn("SIM922 BAD TEMP MSG: |{}|".format(repr(val)))
                        elif len(val) != 12:
                            warnings.warn("SIM922 BAD TEMP LENGTH: |{}|".format(repr(val)))
                        else:
                            try:
                                valf = float(val)
                                if valf > 500.1:
                                    #raise ValueError("SIM922 TEMP WTF!!!")
                                    warnings.warn("SIM922 WTF TEMP - |{}|{}|".format(valf,repr(val)))
                                else:
                                    if (debugl): print("SIM922 GOOD VALUE: |{}|".format(valf))
                                    self.lastvalues[self.streaming_channel] = valf
                                    self.lastdatatimes[self.streaming_channel] = tm
                                    #self.datalist.append(valf)
                                    #self.timelist.append(tm)
                                    self.newdataevent.set()
                            except Exception as e:
                                print("OOPS")
                                print(e)
                                raise e
                time.sleep(0.02)
        except Exception as e:
            self.excq.put(sys.exc_info())
            raise e

    # MODULE SPECIFIC COMMANDS

    def _cmd_qTVAL(self, channel, amt):
        return ('TVAL? {},{}'.format(channel,amt))
    _valuefunction1 = _cmd_qTVAL
    def _cmd_qVOLT(self, channel, amt):
        return ('VOLT? {},{}'.format(channel,amt))
    _valuefunction2 = _cmd_qVOLT

    def set_exitation(self, chan, val):
        val = int(val)
        if (val != 0 and val != 1):
            raise ValueError("NO SUCH MODE - {}".format(val))
        chan = int(chan)
        if (chan > 4 or chan < 0):
            raise ValueError("NO SUCH CHAN - {}".format(chan))
        return self._process_cmd_no_resp(self._cmd_sEXON(chan, val))
    def _cmd_sEXON(self, chan, val):
        return ('EXON {},{}'.format(chan, val))

    def get_exitation(self, chan):
        if (chan > 4 or chan < 0):
            raise ValueError("NO SUCH CHAN - {}".format(chan))
        return int(self._process_cmd_with_resp(self._cmd_qEXON(chan)))
    def _cmd_qEXON(self, chan):
        return ('EXON? {}'.format(chan))

    def set_curvecal(self, chan, val):
        val = int(val)
        if (val != 0 and val != 1):
            raise ValueError("NO SUCH MODE - {}".format(val))
        chan = int(chan)
        if (chan > 4 or chan < 0):
            raise ValueError("NO SUCH CHAN - {}".format(chan))
        return self._process_cmd_no_resp(self._cmd_sCURV(chan, val))
    def _cmd_sCURV(self, chan, val):
        return ('CURV {},{}'.format(chan, val))

    def get_curvecal(self, chan):
        if (chan > 4 or chan < 0):
            raise ValueError("NO SUCH CHAN - {}".format(chan))
        return int(self._process_cmd_with_resp(self._cmd_qCURV(chan)))
    def _cmd_qCURV(self, chan):
        return ('CURV? {}'.format(chan))

class CHANNELS:
    PLATE50K = 1
    MAGNET = 2
    PLATE4K = 3
    BB = 4
