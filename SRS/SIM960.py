import time,datetime,threading,collections,warnings,queue,SIM_MOD_STREAMER
from timeit import default_timer as timer

class SIM960(SIM_MOD_STREAMER.SIM_MOD_STREAMER):
    MODNUM = 3
    streaming_channel = -1
    manlim_low = 0.0
    manlim_high = 1.0
    splim_low = 0.0
    splim_high = 1.0
    ramplim_low = 0.0
    ramplim_high = 0.01
    lastvalues = {}
    lastdatatimes = {}
    excq = queue.Queue(1000)

    def __init__(self, mf, name, debug=1,MODNUM=3):
        self.mfc = mf
        self.sq = mf.sim960q
        self.name = name
        self.debug = debug
        self.MODNUM = MODNUM
        self.streaming = False
        self.newdataevent = threading.Event()  

    def tellastory(self):
        print("My name is {} (ID: {})".format(self.name,self.get_IDN()))
        print("Status is  {}".format(str(bin(int(self.get_status_byte())))))
        print(" Settings:")
        print("  PID mode is       {} (MAN 0, PID 1)".format(self.get_PID_mode()))
        print("  Setpt source is   {} (INT 0, EXT 1)".format(self.get_setpoint_mode()))
        print("  RAMP mode is      {} (OFF 0, ON 1)".format(self.get_ramp_onoff()))
        print("  RAMP rate is      {} (V/s)".format(self.get_ramp_rate()))
        print("  RAMP status is    {} (IDLE 0, PENDING 1, RAMPING 2, PAUSED 3)".format(self.get_ramp_state()))
        print(" PID:")
        print("  P term is         {:<+10.2E} [state: {} (OFF 0, ON 1)]".format(self.get_PID_P(),self.get_PID_P_onoff()))
        print("  I term is         {:<+10.2E} [state: {} (OFF 0, ON 1)]".format(self.get_PID_I(),self.get_PID_I_onoff()))
        print("  D term is         {:<+10.2E} [state: {} (OFF 0, ON 1)]".format(self.get_PID_D(),self.get_PID_I_onoff()))
        print(" Setpoints:")
        print("  Manual output is  {} (V)".format(self.get_manual_output()))
        print("  PID setpoint is   {} (V)".format(self.get_setpoint()))
        print("  Offset is         {} (V)    [state: {} (OFF 0, ON 1)]".format(self.get_offset(),self.get_offset_onoff()))
        print("  Limits are        {}<->{} (V)".format(self.get_lower_lim(),self.get_upper_lim()))
        print(" Voltages:")
        print("  Output V is       {:<+10.6f}".format(self.get_output_voltage()))
        print("  Measure V is      {:<+10.6f}".format(self.get_measure_voltage()))
        print("  Setpoint V is     {:<+10.6f}".format(self.get_setpoint_voltage()))

    ### SIM960 COMMANDS
    def set_PID_mode(self, val):
        val = int(val)
        if (val != 0 and val != 1):
            raise ValueError("NO SUCH MODE - {}".format(val))
        return self._process_cmd_no_resp(self._cmd_sAMAN(val))
    def _cmd_sAMAN(self, val):
        return ('AMAN {}'.format(val))
    def get_PID_mode(self):
        return int(self._process_cmd_with_resp(self._cmd_qAMAN()))
    def _cmd_qAMAN(self):
        return ('AMAN?')

    def set_setpoint_mode(self, val):
        val = int(val)
        if (val != 0 and val != 1):
            raise ValueError("NO SUCH MODE - {}".format(val))
        return self._process_cmd_no_resp(self._cmd_sINPT(val))
    def _cmd_sINPT(self, val):
        return ('INPT {}'.format(val))
    def get_setpoint_mode(self):
        return int(self._process_cmd_with_resp(self._cmd_qINPT()))
    def _cmd_qINPT(self):
        return ('INPT?')

    def set_manual_output(self, val):
        val = float(val)
        if (val < -10.0 or val > 10.0):
            raise ValueError("MANUAL OUTPUT {} OUT OF BOUNDS".format(val))
        elif (val < self.manlim_low or val > self.manlim_high):
            raise ValueError("MANUAL OUTPUT {} OUT OF LIMITS".format(val))
        else:
            return self._process_cmd_no_resp(self._cmd_sMOUT(val))
    def _cmd_sMOUT(self, val):
        return ('MOUT {:+6.3f}'.format(val))
    def get_manual_output(self):
        return float(self._process_cmd_with_resp(self._cmd_qMOUT()))
    def _cmd_qMOUT(self):
        return ('MOUT?')

    def set_setpoint(self, val):
        val = float(val)
        if (val < -10.0 or val > 10.0):
            raise ValueError("SETPOINT {} OUT OF BOUNDS".format(val))
        if (val < self.splim_low or val > self.splim_high):
            raise ValueError("SETPOINT {} OUT OF LIMITS".format(val))
        return self._process_cmd_no_resp(self._cmd_sSETP(val))
    def _cmd_sSETP(self, val):
        return ('SETP {:+6.3f}'.format(val))
    def get_setpoint(self):
        return float(self._process_cmd_with_resp(self._cmd_qSETP()))
    def _cmd_qSETP(self):
        return ('SETP?')

    def set_offset(self, val):
        val = float(val)
        if (val < -10.0 or val > 10.0):
            raise ValueError("SETPOINT {} OUT OF BOUNDS".format(val))
        return self._process_cmd_no_resp(self._cmd_sOFST(val))
    def _cmd_sOFST(self, val):
        return ('SETP {:+6.3f}'.format(val))
    def get_offset(self):
        return float(self._process_cmd_with_resp(self._cmd_qOFST()))
    def _cmd_qOFST(self):
        return ('OFST?')

    def set_upper_lim(self, val):
        val = float(val)
        if (val < -10.0 or val > 10.0):
            raise ValueError("ULIM {} OUT OF BOUNDS".format(val))
        return self._process_cmd_no_resp(self._cmd_sULIM(val))
    def _cmd_sULIM(self, val):
        return ('ULIM {:+6.2f}'.format(val))
    def get_upper_lim(self):
        return float(self._process_cmd_with_resp(self._cmd_qULIM()))
    def _cmd_qULIM(self):
        return ('ULIM?')

    def set_lower_lim(self, val):
        val = float(val)
        if (val < -10.0 or val > 10.0):
            raise ValueError("LLIM {} OUT OF BOUNDS".format(val))
        return self._process_cmd_no_resp(self._cmd_sLLIM(val))
    def _cmd_sLLIM(self, val):
        return ('LLIM {:+6.2f}'.format(val))
    def get_lower_lim(self):
        return float(self._process_cmd_with_resp(self._cmd_qLLIM()))
    def _cmd_qLLIM(self):
        return ('LLIM?')

    def set_offset_onoff(self, val):
        val = int(val)
        if (val != 0 and val != 1):
            raise ValueError("NO SUCH MODE - {}".format(val))
        return self._process_cmd_no_resp(self._cmd_sOCTL(val))
    def _cmd_sOCTL(self, val):
        return ('OCTL {}'.format(val))
    def get_offset_onoff(self):
        return int(self._process_cmd_with_resp(self._cmd_qOCTL()))
    def _cmd_qOCTL(self):
        return ('OCTL?')

    def set_ramp_onoff(self, val):
        val = int(val)
        if (val != 0 and val != 1):
            raise ValueError("NO SUCH MODE - {}".format(val))
        return self._process_cmd_no_resp(self._cmd_sRAMP(val))
    def _cmd_sRAMP(self, val):
        return ('RAMP {}'.format(val))
    def get_ramp_onoff(self):
        return int(self._process_cmd_with_resp(self._cmd_qRAMP()))
    def _cmd_qRAMP(self):
        return ('RAMP?')

    def set_ramp_rate(self, val):
        val = float(val)
        if (val < 1e-3 or val > 1e4):
            raise ValueError("RAMP RATE {} OUT OF BOUNDS".format(val))
        if (val < self.ramplim_low or val > self.ramplim_high):
            raise ValueError("RAMP RATE {} OUT OF LIMITS".format(val))
        return self._process_cmd_no_resp(self._cmd_sRATE(val))
    def _cmd_sRATE(self, val):
        return ('RATE {:.1E}'.format(val))
    def get_ramp_rate(self):
        return float(self._process_cmd_with_resp(self._cmd_qRATE()))
    def _cmd_qRATE(self):
        return ('RATE?')

    def set_ramp_startpause(self, val):
        val = int(val)
        if (val != 0 and val != 1):
            raise ValueError("NO SUCH STATE - {}".format(val))
        return self._process_cmd_no_resp(self._cmd_sSTRT(val))
    def _cmd_sSTRT(self, val):
        return ('STRT {}'.format(val))

    def get_ramp_state(self):
        return int(self._process_cmd_with_resp(self._cmd_qRMPS()))
    def _cmd_qRMPS(self):
        return ('RMPS?')

    ### PID
    def set_PID_P(self, val):
        val = float(val)
        if (abs(val) < 1e-1 or abs(val) > 1e3):
            raise ValueError("GAIN {} OUT OF BOUNDS".format(val))
        return self._process_cmd_no_resp(self._cmd_sGAIN(val))
    def _cmd_sGAIN(self, val):
        return ('GAIN {:+.1E}'.format(val))
    def get_PID_P(self):
        return float(self._process_cmd_with_resp(self._cmd_qGAIN()))
    def _cmd_qGAIN(self):
        return ('GAIN?')

    def set_PID_P_onoff(self, val):
        val = int(val)
        if (val != 0 and val != 1):
            raise ValueError("NO SUCH MODE - {}".format(val))
        return self._process_cmd_no_resp(self._cmd_sPCTL(val))
    def _cmd_sPCTL(self, val):
        return ('PCTL {}'.format(val))
    def get_PID_P_onoff(self):
        return int(self._process_cmd_with_resp(self._cmd_qPCTL()))
    def _cmd_qPCTL(self):
        return ('PCTL?')

    def set_PID_I(self, val):
        val = float(val)
        if (val < 1e-2 or val > 5e5):
            raise ValueError("INTG {} OUT OF BOUNDS".format(val))
        return self._process_cmd_no_resp(self._cmd_sINTG(val))
    def _cmd_sINTG(self, val):
        return ('INTG {:.1E}'.format(val))
    def get_PID_I(self):
        return float(self._process_cmd_with_resp(self._cmd_qINTG()))
    def _cmd_qINTG(self):
        return ('INTG?')

    def set_PID_I_onoff(self, val):
        val = int(val)
        if (val != 0 and val != 1):
            raise ValueError("NO SUCH MODE - {}".format(val))
        return self._process_cmd_no_resp(self._cmd_sICTL(val))
    def _cmd_sICTL(self, val):
        return ('ICTL {}'.format(val))
    def get_PID_I_onoff(self):
        return int(self._process_cmd_with_resp(self._cmd_qICTL()))
    def _cmd_qICTL(self):
        return ('ICTL?')

    def set_PID_D(self, val):
        val = float(val)
        if (val < 1e-6 or val > 10):
            raise ValueError("DERV {} OUT OF BOUNDS".format(val))
        return self._process_cmd_no_resp(self._cmd_sDERV(val))
    def _cmd_sDERV(self, val):
        return ('DERV {:.1E}'.format(val))
    def get_PID_D(self):
        return float(self._process_cmd_with_resp(self._cmd_qDERV()))
    def _cmd_qDERV(self):
        return ('DERV?')

    def set_PID_D_onoff(self, val):
        val = int(val)
        if (val != 0 and val != 1):
            raise ValueError("NO SUCH MODE - {}".format(val))
        return self._process_cmd_no_resp(self._cmd_sDCTL(val))
    def _cmd_sDCTL(self, val):
        return ('DCTL {}'.format(val))
    def get_PID_D_onoff(self):
        return int(self._process_cmd_with_resp(self._cmd_qDCTL()))
    def _cmd_qDCTL(self):
        return ('DCTL?')

    ### VOLTAGES
    def get_output_voltage(self):
        return float(self._process_cmd_with_resp(self._cmd_qOMON()))
    def _cmd_qOMON(self):
        return ('OMON?')

    def get_measure_voltage(self):
        return float(self._process_cmd_with_resp(self._cmd_qMMON()))
    def _cmd_qMMON(self):
        return ('MMON?')

    def get_setpoint_voltage(self):
        return float(self._process_cmd_with_resp(self._cmd_qSMON()))
    def _cmd_qSMON(self):
        return ('SMON?')
