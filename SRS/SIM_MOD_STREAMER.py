import time,datetime,threading,collections,warnings,sys,SIM_MOD
from timeit import default_timer as timer

class SIM_MOD_STREAMER(SIM_MOD.SIM_MOD):
    def _get_single_value(self, chan=1, vfunc=1):
        if vfunc == 1: vfunc=self._valuefunction1
        if vfunc == 2: vfunc=self._valuefunction2
        if (not self.streaming):
            try:
                if not self._ismultistreamer:
                    if self.debug: print("Not MS call: |{}|{}|".format(chan,vfunc))
                    val = self._process_cmd_with_resp(vfunc(1))
                else:
                    #val = self._process_cmd_with_resp(self.__cmd_qTVAL(chan,1))
                    if not chan > 0: return None
                    val = self._process_cmd_with_resp(vfunc(chan,1))
                    if self.debug: print("Not MS call: |{}|{}|".format(chan,vfunc))
                val = float(val)
                dt = datetime.datetime.fromtimestamp(timer())
                if self.debug: print("Got value: |{}|{}|".format(val,dt.strftime('%H:%M:%S.%f')))
                self.lastvalues[chan] = val
                self.lastdatatimes[chan] = dt.timestamp()
                return val
            except Exception as e:
                print(e)
                self.excq.put(sys.exc_info())
                raise e
                return None
        else:
            raise Error("Currently streaming")

    # Streaming commands
    def get_next_result(self, tm=1.1, channel=-1):
        if (self.streaming == True):
            self.newdataevent.clear();
            self.newdataevent.wait(tm);
            self.newdataevent.clear();
            if 'streaming_channel' in locals() and self.streaming_channel != 0:
                return self.lastvalues[self.streaming_channel]
            else:
                return self.lastvalues[channel]
        else:
            warnings.warn("Streaming output is not on!")
            return None

    def await_next_event(self, tm=1.1, clear_before=True, clear_after=True):
        if (self.streaming == True):
            if clear_before: self.newdataevent.clear();
            result = self.newdataevent.wait(tm);
            if clear_after: self.newdataevent.clear();
            return result
        else:
            warnings.warn("Streaming output is not on!")

    #Override parent methods
    def _streaming_chk(self):
        if (self.streaming):
            raise Exception("Currently streaming!!!")
        else:
            pass

    def _cmd_rdy_check_resp(self):
        self._streaming_chk()
        self._q_check()

    def _cmd_rdy_check_noresp(self):
        pass

    def _process_cmd_with_resp(self,cmd,channel=-1):
        self.sq.queue.clear()
        channel = int(channel)
        if (channel == -1):
            self._cmd_rdy_check_resp()
            self.send_cmd(cmd)
            return self.await_response()
        elif (channel >= 0 and channel <= 4):
            self._cmd_rdy_check_resp()
            self.send_cmd(cmd)
            return self.await_response()
        else:
            raise ValueError("WRONG CHANNEL {}".format(channel))

    def _process_cmd_no_resp(self,cmd,channel=-1):
        channel = int(channel)
        if (channel == -1):
            self._cmd_rdy_check_noresp()
            self.send_cmd(cmd)
        elif (channel >= 0 and channel <= 4):
            self._cmd_rdy_check_noresp()
            self.send_cmd(cmd)
        else:
            raise ValueError("WRONG CHANNEL {}".format(channel))

    def stop_data_stream(self):
        if (self.streaming == True):
            self.send_cmd(self._cmd_sSOUT())
            self.streaming = False
            time.sleep(0.05)        #in case something was still coming on wire
            with self.sq.mutex:
                self.sq.queue.clear()
        else:
            warnings.warn("There is no streaming to stop!")

    # Extra commands for multiplexed modules
    def _cmd_sSOUT(self):
        return ('SOUT')
