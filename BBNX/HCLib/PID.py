import timeit,time
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import spline
from timeit import default_timer as timer

class stockPID():
    def __init__(self, P, I, D, debug=False,winduplim=None,slewrate=None):
        self.Kp = P
        self.Ki = I
        self.Kd = D
        
        self.debug = debug

        self.current_time = timer()
        self.last_time = self.current_time

        self.clear()
        
        if winduplim is not None: self.windup_guard = winduplim
        if slewrate is not None: self.slewrate = slewrate

    def clear(self):
        """Clears PID computations and coefficients"""
        self.SetPoint = 0.0
        self.PTerm = 0.0
        self.ITerm = 0.0
        self.DTerm = 0.0
        self.last_error = 0.0
        self.last_output = 0.0
        self.int_error = 0.0
        self.windup_guard = 0.0
        self.slewrate = 0.0
        self.output = 0.0

    def update(self, feedback_value):
        """Calculates PID value for given reference feedback
        .. math::
            u(t) = K_p e(t) + K_i \int_{0}^{t} e(t)dt + K_d {de}/{dt}
        .. figure:: images/pid_1.png
           :align:   center
           Test PID with Kp=1.2, Ki=1, Kd=0.001 (test_pid.py)
        """
        error = self.SetPoint - float(feedback_value)
        delta_error = error - self.last_error
        
        self.current_time = timer()
        delta_time = self.current_time - self.last_time        

        self.PTerm = self.Kp * error
        self.ITerm += error * delta_time
        
        if (self.windup_guard > 0.0):
            if (self.ITerm < -self.windup_guard):
                self.ITerm = -self.windup_guard
            elif (self.ITerm > self.windup_guard):
                self.ITerm = self.windup_guard

        self.DTerm = 0.0
        if (delta_time > 0.0):
            self.DTerm = delta_error / delta_time      
        
        output_raw = self.PTerm + (self.Ki * self.ITerm) + (self.Kd * self.DTerm)
        if (self.slewrate > 0.0) :
            slew_scaled = min(self.slewrate*delta_time, self.slewrate) # so slew rate can only be reduced
            if (output_raw - self.last_output > slew_scaled):
                if (self.debug): print("Slew rate up limited to {:.3f} from {:.3f}".format(slew_scaled,output_raw - self.last_output))
                self.output = self.last_output + slew_scaled
            elif (output_raw - self.last_output < -slew_scaled):
                if (self.debug): print("Slew rate down limited to {:.3f} from {:.3f}".format(-slew_scaled,output_raw - self.last_output))
                self.output = self.last_output - slew_scaled
            else:
                if (self.debug): print("No slew rate limit - {}".format(output_raw))
                self.output = output_raw  
        else:
            if (self.debug): print("Slew limiter off - {}".format(output_raw))
            self.output = output_raw
            
        if (self.debug): print("P:{:.3f}|I:{:.3f}|D:{:.3f}|sp:{:.2f}".format(self.PTerm,self.Ki * self.ITerm,self.Kd * self.DTerm,self.SetPoint))
        
        # Remember things for next calculation
        self.last_output = self.output
        self.last_time = self.current_time
        self.last_error = error

    def setKp(self, proportional_gain):
        """Determines how aggressively the PID reacts to the current error with setting Proportional Gain"""
        self.Kp = proportional_gain

    def setKi(self, integral_gain):
        """Determines how aggressively the PID reacts to the current error with setting Integral Gain"""
        self.Ki = integral_gain

    def setKd(self, derivative_gain):
        """Determines how aggressively the PID reacts to the current error with setting Derivative Gain"""
        self.Kd = derivative_gain

    def setWindup(self, windup):
        """Integral windup, also known as integrator windup or reset windup,
        refers to the situation in a PID feedback controller where
        a large change in setpoint occurs (say a positive change)
        and the integral terms accumulates a significant error
        during the rise (windup), thus overshooting and continuing
        to increase as this accumulated error is unwound
        (offset by errors in the other direction).
        The specific problem is the excess overshooting.
        """
        self.windup_guard = windup
        
    def setSlewLimit(self, slew):
        """Slew rate limits serves to limit the output change to the rate specified per second
        """
        self.slewrate = slew