import sys,time,os,datetime

def __init__(self, debug=True):
    self.debug = debug

def get_new_cryolog_path(self,logroot='/home/pi/Desktop/DataNX/cryologs/'):
    date = datetime.datetime.now()
    logdir = logroot+date.strftime('%Y%m%d')
    if not os.path.isdir(logdir):
        if (self.debug): print("Directory |{}| not there, making".format(logdir))
        os.mkdir(logdir+date.strftime('%Y%m%d'))
    dirs = os.listdir(logroot)
    if (self.debug): print(dirs)
    logfile = logdir+os.path.sep+date.strftime('cryo-%H-%M-%S.txt')
    if (self.debug): print(logfile)
    #fl = open(logfile, "w")
    
    
    with open("warmup_20170710.txt", "w") as f:
    for i in range(0,len(times)):
        f.write("{} {} {}\n".format(times[i],temps[i],dcs[i]))