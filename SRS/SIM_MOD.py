import sys,time,datetime,threading,collections,warnings
from timeit import default_timer as timer

class SIM_MOD:
    def send_cmd(self, cmd):
        self.mfc.oq_add('SNDT {},"{}"\n'.format(self.MODNUM,cmd))

    def flush_queue(self):
        self.sq.queue.clear()

    def await_response(self):
        start = timer()
        count = 0
        buf = str()
        try:
            while (timer()-start)<2.0:
                if (not self.sq.empty()):                    
                    [msg,tmr] = self.sq.get() 
                    if (self.debug): print("Await resp res {}".format(repr(msg)))
                    if '\r' not in msg:
                        #if (self.debug): print("Missing CR")
                        if (self.debug): print("AWresp missing CR")
                        if count == 0:
                            buf = msg
                            count = 1
                            if (self.debug): print("{} | AWRESP BUFFERING: |{}|".format(self.name,msg))
                            if (self.debug): warnings.warn("{} | AWRESP BUFFERING: |{}|".format(self.name,msg))                             
                        else:
                            count = 0
                            raise RuntimeError("BAD MESSAGE RESPONSE from {}".format(self.name))
                    else:
                        if count == 1:
                            msg = buf + msg                            
                            print("{} | Recovered: |{}|, buf |{}|".format(self.name,repr(msg),buf))
                            if (self.debug): warnings.warn("{} | Recovered: |{}|, buf |{}|".format(self.name,repr(msg),buf))
                            return msg.rstrip()                        
                        else:
                            count = 0
                            return msg.rstrip()
                    #print ("GOT RESP IN {}".format(tmr-start))                
                time.sleep(0.01)
        except Exception as e:
            print(e)
            self.excq.put(sys.exc_info())
        #return "NO RESPONSE FROM MODULE {}".format(self.name)
        raise RuntimeError("NO RESPONSE FROM MODULE {}".format(self.name))

    def _q_check(self):
        if (not self.sq.empty()):
            time.sleep(0.05) #try to give threads time to pick it up
            if (not self.sq.empty()):
                #self.sq.queue.clear()
                raise Exception("Already have responses in queue!")

    def _cmd_rdy_check_resp(self):
        self._q_check()

    def _cmd_rdy_check_noresp(self):
        pass

    ### COMMON COMMANDS
    def get_IDN(self):
        self._cmd_rdy_check_resp()
        self.send_cmd(self._cmd_IDN())
        return self.await_response()
    def _cmd_IDN(self):
        return ('*IDN?')

    #resets
    def reset(self):
        self.send_cmd(self._cmd_RST())
    def _cmd_RST(self):
        return ('*RST')

    def get_status_byte(self):
        self._cmd_rdy_check_resp()
        self.send_cmd(self._cmd_qSTB())
        return self.await_response()
    def _cmd_qSTB(self):
        return ('*STB?')

    def get_selftest(self):
        self._cmd_rdy_check_resp()
        self.send_cmd(self._cmd_qTST())
        return self.await_response()
    def _cmd_qTST(self):
        return ('*TST?')
