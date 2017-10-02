import serial,time,warnings

def relay_switch_magcycle():
    ser = serial.Serial('/dev/ADR_magcontrol',9600,timeout=1)
    time.sleep(5)
    ser.write('5'.encode()) #5 is to change to Magcycle
    time.sleep(1)
    ser.close()

def relay_switch_regulation():
    ser = serial.Serial('/dev/ADR_magcontrol',9600,timeout=1)
    time.sleep(5)
    ser.write('6'.encode()) #6 is to change to Regulation
    time.sleep(1)
    ser.close()

def heatswitch_close():
    try:
        ser = serial.Serial('/dev/ADR_magcontrol',9600,timeout=1)
        time.sleep(5)
        ser.write('2'.encode()) #2 is to close
        time.sleep(1)
        print('Heat Switch closing')
        time.sleep(5)

        j1 = _queryLED(ser,'B','4K-GGG')
        j2 = _queryLED(ser,'A','4K-FAA')
        j3 = _queryLED(ser,'C','GGG-FAA')

        if j1==j2==j3==0:
            print('Heat Switch is closed')
        else:
            warnings.warn('NOT CLOSED...that is really bad')
    except Exception:
        raise
    finally:
        ser.close()

def _queryLED(ser,num,text):
    ser.write(num.encode())
    time.sleep(1)
    jj = ser.read(16).decode().rstrip()
    j=int(jj)
    if j==1:
        print(text+' LED OFF')
    elif j==0:
        print(text+' LED ON')
    else:
        raise RuntimeError("Response unrecognized")
    return j
                               
def heatswitch_open():
    try:
        ser = serial.Serial('/dev/ADR_magcontrol',9600,timeout=1)
        time.sleep(5)
        ser.write('3'.encode('ascii')) #3 is to open
        time.sleep(1)
        print('Heat Switch opening')
        time.sleep(5)

        j1 = _queryLED(ser,'B','4K-GGG')
        j2 = _queryLED(ser,'A','4K-FAA')
        j3 = _queryLED(ser,'C','GGG-FAA')

        if j1==j2==j3==1:
            print('Heat Switch is opened')
        elif (j1==0) and (j2==j3==1):
            print('Heat Switch almost open - this should be ok and will probably go away at lower currents')
        else:
            warnings.warn('NOT OPEN...perhaps try again?')
    except Exception:
        raise
    finally:
        ser.close()