import sys,time,datetime,threading,collections,warnings,queue,SIM_MOD_STREAMER
from timeit import default_timer as timer

class SIM921(SIM_MOD_STREAMER.SIM_MOD_STREAMER):
    MODNUM = 1
    _ismultistreamer = False
    lastvalues = {}
    lastdatatimes = {}
    excq = queue.Queue(1000)
    
    def __init__(self, mf, name, debug=1, MODNUM=1):
        self.mfc = mf
        self.sq = mf.sim921q
        self.name = name
        self.debug = debug
        self.MODNUM = MODNUM
        self.streaming = False
        self.newdataevent = threading.Event()
        
    def tellastory(self):
        print("My name is {} (ID: {})".format(self.name,self.get_IDN()))
        print("Status is {}".format(str(bin(int(self.get_status_byte())))))
        print("Rest is not implemented yet...")

    def set_data_period(self, per):
        if (not self.streaming):
            self._process_cmd_no_resp(self._cmd_sTPER(per))
        else:
            raise Error("Currently streaming")

    def get_single_value(self):
        if (not self.streaming):
            val = self._process_cmd_with_resp(self._cmd_qTVAL(1))
            try:
                val = float(val)
                dt = datetime.datetime.fromtimestamp(timer())
                if self.debug: print("Got temp: |{}|{}|".format(val,dt.strftime('%H:%M:%S.%f')))
                self.lastvalues[1] = val
                self.lastdatatimes[1] = dt.timestamp()
                return float(val)
            except Exception as e:
                print(e)
                return None
        else:
            raise Error("Currently streaming")

    def start_data_stream(self):
        if not self.streaming:
            self.excq.queue.clear()
            self.send_cmd(self._cmd_qTVAL(0))
            self.streaming = True
            thread = threading.Thread(name='sim921t',target=self._sim921_thread, args=())
            thread.setDaemon(True)
            thread.start()
        else:
            warnings.warn("Streaming output is already running!")

    def _sim921_thread(self):
        try:
            debugl = self.debug
            if (debugl): print("SIM921 stream thread up")
            sq = self.sq
            count = 0
            buf = str()            
            while (self.streaming):
                while (not sq.empty()):
                    #print("test")
                    #[val, tm] = sq.get()
                    #val = val.rstrip()
                    #dt = datetime.datetime.fromtimestamp(tm)
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
                            print("{} | Recovered: |{}|, buf |{}|".format(self.name,repr(val),buf))
                            count = 0
                            buf = str()
                            if (debugl): warnings.warn("SIM970 RESCUED FRAGMENT: |{}|".format(val))                           
                        else:
                            #print("test2")
                            count = 0
                    #print("test2b")
                    dt = datetime.datetime.fromtimestamp(tm)
                    #print("test3")
                    if (debugl): print("Final val: {}".format(repr(val)))
                    val = val.rstrip()                    
                    if (debugl): print("Got temperature data: |{}|{}|".format(val,dt.strftime('%H:%M:%S.%f')))
                    if val == 'E+00' or val == 'E+01' or val == 'E+02':
                        #if (debugl): print("SIM921 BAD TEMP MSG: |{}|".format(val))
                        if (debugl): warnings.warn("SIM921 BAD TEMP MSG: |{}|".format(repr(val)))
                        continue
                    elif len(val) != 13:
                        if (debugl): warnings.warn("SIM921 BAD TEMP LENGTH: |{}|".format(repr(val)))
                    elif '.' not in val[0:4]:
                        if (debugl): warnings.warn("SIM921 BAD MSG: |{}|".format(val))
                    else:
                        try:
                            valf = float(val)
                            if valf > 300.0 or valf < 0.0:
                                #raise ValueError("SIM922 TEMP WTF!!!")
                                if (debugl): print("SIM921 WTF TEMP - {}".format(self.lastvalue))
                            else:
                                if (debugl): print("SIM921 GOOD VALUE: |{}|".format(valf))
                                self.lastvalues[1] = valf
                                self.lastdatatimes[1] = tm
                                #self.templist.append(self.lasttemperature)
                                #self.timelist.append(tm)
                                self.newdataevent.set()
                        except Exception as e:
                            print(e)
                            #raise e
                time.sleep(0.02)
        except Exception as e:
            self.excq.put(sys.exc_info())
            raise e

    def _cmd_sTPER(self, per):
        return ('TPER {}'.format(per))
    def _cmd_qTVAL(self, amt):
        return ('TVAL? {}'.format(amt))
