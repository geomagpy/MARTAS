#!/usr/bin/env python
# coding=utf-8

"""
MARTAS - threshold application
################################

DESCRIPTION:
Threshold application reads data from a defined source 
(DB or file, eventually MQTT).
Threshold values can be defined for keys in the data file,
notifications can be send out when ceratin criteria are met, 
and switching commands can be send if thresholds are exceeded 
or undergone.
All threshold processes can be logged and  can be monitored
by nagios, icinga or martas.
Threshold.py can be scheduled in crontab.

REQUIREMENTS:
pip install geomagpy (>= 0.3.99)


APPLICATION:
threshold -m /path/to/threshold.cfg


switch.cfg: (looks like)
##  ----------------------------------------------------------------
##           CONFIGURATION DATA for THRESHOLD.PY
##  ----------------------------------------------------------------

# MARTAS directory
martasdir            :   /home/cobs/MARTAS/

# Define data source (file, db, ...)
source               :   file

# If source = db then define data base credentials created by addcred (MARTAS)
dbcredentials        :   None


# If source = file define the MARTAS buffer base path
bufferpath           :   /srv/mqtt/


# Logfile (a json style dictionary, which contains statusmessages) 
#logfile              :   /var/log/magpy/threshold.log
logfile              :   /home/leon/Tmp/threshold.log


# Notifaction (uses martaslog class, one of email, telegram, mqtt, log) 
notification         :   email
notificationconfig   :   /etc/martas/notification.cfg


# Report level ("full" will report all changes, also within range states)
reportlevel          :   partial


# serial communication for switch commands (based on ardcomm.py (MARTAS/app)
serialcfg            :   None


#parameter (all given parameters are checked in the given order, use semicolons for parameter list):
# sensorid; timerange to check; key to check, value, function, state,statusmessage,switchcommand(optional)
1  :  DS18B20XX;1800;t1;5;average;below;default;swP:4:1
2  :  DS18B20XX;1800;t1;10;median;above;default;swP:4:0
3  :  DS18B20XZ;600;t2;10;max;below;ok
4  :  DS18B20XZ;600;t2;10;max;above;warning at week
5  :  DS18B20XZ;600;t2;20;max;above;alarm issued at date
6  :  DS18B20XZ;600;t2;3;stddev;above;flapping state

#to be continued...

# SensorID, key:  if sensorid and key of several lines are identical, always the last valid test line defines the message
#                 Therefore use warning thresholds before alert thresholds   
# Function:       can be one of max, min, median, average(mean), stddev 
# State:          can be one below, above, equal 
# Statusmessage:  default is replaced by "Current 'function' 'state' 'value', e.g. (1) "Current average below 5"
#                 the following words (last occurrence) are replace by datetime.utcnow(): date, month, year, (week), hour, minute
#                 "date" is replaced by current date e.g. 2019-11-22
#                 "month" is replaced by current month e.g. 2019-11
#                 "week" is replaced by current calender week e.g. 56
#                 "minute" looks like 2019-11-22 13:10
#                 -> "date" changes the statusmessage every day and thus a daily notification is triggered as long a alarm condition is active


#TODO:
- flapping states -----> use stddev (higher order than regular test, will overwrite message
- minimum benachrichtigungswiederholung -----> use date
- moeglichkeit zu quittieren (ueber telegram?)   ------> interact with json, telegram, change config to remove date, etc 

## Description: Parameterset "1":  if t1 average of last 30 min (1800 sec) is falling below 5 degrees
## then use statusmessage and eventually send switchcommand to serial port
## IMPORTANT: statusmessage should not contain semicolons, colons and commas; generally avoid special characters
 
"""

from __future__ import print_function
from __future__ import unicode_literals

# Define packges to be used (local refers to test environment) 
# ------------------------------------------------------------
from magpy.stream import DataStream, KEYLIST, NUMKEYLIST, read
from magpy.database import mysql,readDB
from datetime import datetime, timedelta
import magpy.opt.cred as mpcred
import sys, getopt, os
try:
    import paho.mqtt.client as mqtt
except:
    print ("MQTT not available")


#from magpy.acquisition import acquisitionsupport as acs
#import magpy.mpplot as mp


if sys.version.startswith('2'):
    pyvers = '2'
else:
    pyvers = '3'


class sp(object):
    # Structure for switch parameter
    configdict = {}
    configdict['bufferpath'] = '/srv/mqtt'
    configdict['dbcredentials'] = 'cobsdb'
    configdict['database'] = 'cobsdb'
    configdict['reportlevel'] = 'partial'
    configdict['notification'] = 'email'
    configdict['notification'] = 'log'
    valuenamelist = ['sensorid','timerange','key','value','function','state','statusmessage','switchcommand']
    valuedict = {'sensorid':'DS18B20','timerange':1800,'key':'t1','value':5,'function':'average','state':'below','message':'on','switchcommand':'None'}
    parameterdict = {'1':valuedict}
    configdict['version'] = '1.0.0' # thresholdversion
    configdict['martasdir'] = '/home/cobs/MARTAS/'

    #Testset
    configdict['startdate'] = datetime(2018,12,6,13)
    valuenamelist = ['sensorid','timerange','key','value','function','state','statusmessage','switchcommand']
    valuedict = {'sensorid':'ENV05_2_0001','timerange':1800,'key':'t1','value':5,'function':'average','state':'below','message':'on','switchcommand':'None'}


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def GetConf(path):
    """
    DESCRIPTION:
        read default configuration paths etc from a file
        Now: just define them by hand
    PATH:
        defaults are stored in magpymqtt.conf

        File looks like:
        # Configuration data for data transmission using MQTT (MagPy/MARTAS)
    """
    # Init values
    try:
        config = open(path,'r')
        confs = config.readlines()

        for conf in confs:
            conflst = conf.split(' : ')
            if conf.startswith('#'): 
                continue
            elif conf.isspace():
                continue
            elif len(conflst) == 2:
                if is_number(conflst[0]):
                    # extract parameterlist
                    key = conflst[0].strip()
                    values = conflst[1].strip().split(';')
                    valuedict = {}
                    if not len(values) in [len(sp.valuenamelist), len(sp.valuenamelist)-1]:
                        print ("PARAMETER: provided values differ from the expected amount - please check")
                    else:
                        for idx,val in enumerate(values):
                            valuedict[sp.valuenamelist[idx]] = val.strip()
                        sp.parameterdict[key] = valuedict
                else:
                    key = conflst[0].strip()
                    value = conflst[1].strip()
                    sp.configdict[key] = value
    except:
        print ("Problems when loading conf data from file...")
        #return ({}, {})
        return (sp.configdict, sp.parameterdict)

    return (sp.configdict, sp.parameterdict)


def GetData(source, path, db, dbcredentials, sensorid, amount, startdate=None, debug=False):
    """
    DESCRIPTION:
    read the appropriate amount of data from the data file, database or mqtt stream
    """
 
    data = DataStream()
    msg = ''
    if not startdate:
        startdate = datetime.utcnow()
        endtime = None
    else:
        endtime = startdate

    starttime = startdate-timedelta(seconds=int(amount))

    if source in ['file','File']:
        filepath = os.path.join(path,sensorid)
        # TODO eventually check for existance and look for similar names
        # expath = CheckPath(filepath)
        # if expath:
        if debug:
            print ("Trying to access files in {}: Timerange: {} to {}".format(filepath,starttime,endtime))
        try:
            data = read(os.path.join(filepath,'*'), starttime=starttime, endtime=endtime)
        except:
            msg = "Could not access data for sensorid {}".format(sensorid)
            if debug:
                print (msg)
    elif source in ['db','DB','database','Database']:
        db = mysql.connect()
        data = readDB(db, sensorid, starttime=starttime)        

    if debug:
        print ("Got {} datapoints".format(data.length()[0]))

    return (data, msg) 

def GetTestValue(data=DataStream(), key='x', function='average', debug=False):
    """
    DESCRIPTION
    Returns comparison value(e.g. mean, max etc)
    """
    if debug:
        print ("Obtaining tested value for key {} with function {}".format(key,function))
    func = 'mean'
    testvalue = None
    msg = ''
    n = data.length()[0]
    keys = data._get_key_headers()

    if not key in keys:
        print ("Requested key not found")
        return (testvalue, 'failure')
    if function in ['mean','Mean','average', 'Average','Median','median']:
        if n < 3:
            print ("not enough data points --- {} insignificant".format(function))
        if function in ['mean','Mean','average', 'Average']:
            func = 'mean'
        elif function in ['Median','median']:
            func = 'median'
        testvalue = data.mean(key,meanfunction=func)
    elif function in ['max','Max']:
        testvalue = data._get_max(key)
    elif function in ['min','Min']:
        testvalue = data._get_min(key)
    elif function in ['stddev','Stddev']:
        mean,testvalue = data.mean(key,std=True)
    else:
        msg = 'selected test function not available'

    if debug:
        print (" ... got {}".format(testvalue))

    return (testvalue, msg)


def CheckThreshold(testvalue, threshold, state, debug=False):
    """
    DESCRIPTION:
     returns statusmessage
    """
    evaluate = False
    msg = ''
    if state in ['below','Below','smaller']:
        comp = '<'
    elif state in ['above','Above','greater']:
        comp = '>'
    elif state in ['equal','Equal']:
        comp = '=='
    elif state in ['equalabove']:
        comp = '>='
    elif state in ['equalbelow']:
        comp = '<='
    else:
        msg = 'state needs to be one of below, above or equal'
    tester = "{} {} {}".format(testvalue,comp,threshold)
    if debug:
        print ("Checking: {}".format(tester))
    try:
        if eval(tester):
            evaluate = True
            if debug:
                print (" ... valid")
        else:
            evaluate = False
            if debug:
                print (" ... not valid")
    except:
        msg = "Comparison {} failed".format(tester)

    return (evaluate, msg)

def InterpreteStatus(valuedict, debug=False):
    """
    DESCRIPTION:
    checks the message and replace certain keywords with predefined test
    """
    msg = valuedict.get('statusmessage')
    defaultline =  'Current {} {} {}'.format(valuedict.get('function'),valuedict.get('state'),valuedict.get('value'))
    ct = datetime.utcnow()
    msg = msg.replace('default', defaultline)
    msg = msg.replace('date', datetime.strftime(ct,"%Y-%m-%d"))
    msg = msg.replace('hour', datetime.strftime(ct,"%Y-%m-%d %H:%M"))
    msg = msg.replace('minute', datetime.strftime(ct,"%Y-%m-%d %H:%M"))
    msg = msg.replace('month', datetime.strftime(ct,"%Y-%m"))
    msg = msg.replace('year', datetime.strftime(ct,"%Y"))
    msg = msg.replace('week', 'week {}'.format(ct.isocalendar()[1]))

    return msg


def main(argv):

    para = sp.parameterdict
    conf = sp.configdict
    debug = False
    configfile = None
    statusdict = {}
    statuskeylist = []

    usagestring = 'threshold.py -h <help> -m <configpath>'
    try:
        opts, args = getopt.getopt(argv,"hm:U",["configpath="])
    except getopt.GetoptError:
        print ('Check your options:')
        print (usagestring)
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print ('------------------------------------------------------')
            print ('Usage:')
            print (usagestring)
            print ('------------------------------------------------------')
            print ('Options:')
            print ('-h            help')
            print ('-m            Define the path for the configuration file.')
            print ('              Please note: a configuration file is obligatory')
            print ('              ----------------------------')
            print ('              configurationfile')
            print ('              ----------------------------')
            print ('              threhold.cfg: (looks like)')
            print ('              # MARTAS directory')
            print ('              martasdir            :   /home/cobs/MARTAS/')
            print ('              # Define data source (file, db)')
            print ('              source               :   file')
            print ('              # If source = db then define data base credentials created by addcred (MARTAS)')
            print ('              dbcredentials        :   None')
            print ('              # If source = file define the base path')
            print ('              sensorpath           :   /srv/mqtt/')
            print ('              # Notifaction (uses martaslog class, one of email, telegram, mqtt, log) ')
            print ('              notification         :   email')
            print ('              notificationconfig   :   /etc/martas/notification.cfg')
            print ('              # serial communication for switch commands (based on ardcomm.py (MARTAS/app)')
            print ('              serialcfg            :   None')
            print ('              #parameter (all given parameters are checked in the given order, use semicolons for parameter list):')
            print ('              # sensorid; timerange to check; key to check, value, lower or upper bound,statusmessage,resetby,switchcommand(optional)')
            print ('              1  :  DS18B20XX;1800;t1;5;low;average;on;swP:4:1')
            print ('              2  :  DS18B20XY;1800;t1;10;high;median;off;swP:4:0')
            print ('              3  :  DS18B20XZ;600;t2;20;high;max;alarm at date;None')
            print ('              #to be continued...')

            print ('------------------------------------------------------')
            print ('Example:')
            print ('   python threshold.py -m /etc/martas/threshold.cfg')
            sys.exit()
        elif opt in ("-m", "--configfile"):
            configfile = arg
            print ("Getting all parameters from configration file: {}".format(configfile))
            (conf, para) = GetConf(configfile)
        elif opt in ("-U", "--debug"):
            debug = True

        # TODO activate in order prevent default values
        #if not configfile or conf == {}:
        #    print (' !! Could not read configuration information - aborting')
        #    sys.exit()

    if debug:
        print ("Configuration dictionary: \n{}".format(conf))
        print ("Parameter dictionary: \n{}".format(para))

    if not (len(para)) > 0:
        print ("No paarmeters given too be checked - aborting") 
        sys.exit()


    try:
        martaslogpath = os.path.join(conf.get('martasdir'), 'doc')
        sys.path.insert(1, martaslogpath)
        from martas import martaslog as ml
        logpath = conf.get('bufferpath')
    except:
        print ("Could not import martas logging routines - check MARTAS directory path")

 
    # For each parameter
    for i in range(0,1000):
            valuedict = para.get(str(i),{})
            content = ''
            if not valuedict == {}:
                if debug:
                    print ("Checking parameterset {}".format(i))
                data = DataStream()
                testvalue = None
                evaluate = {}
                
                # Obtain a magpy data stream of the respective data set
                if debug:
                    print ("Accessing data from {} at {}: Sensor {} - Amount: {} sec".format(conf.get('source'),conf.get('bufferpath'),valuedict.get('sensorid'),valuedict.get('timerange') ))

                (data,msg1) = GetData(conf.get('source'), conf.get('bufferpath'), conf.get('database'), conf.get('dbcredentials'), valuedict.get('sensorid'),valuedict.get('timerange'), debug=debug , startdate=conf.get('startdate') )
                (testvalue,msg2) = GetTestValue( data, valuedict.get('key'), valuedict.get('function'), debug=debug) # Returns comparison value(e.g. mean, max etc)
                if testvalue:
                    (evaluate, msg) = CheckThreshold(testvalue, valuedict.get('value'), valuedict.get('state'), debug=debug) # Returns statusmessage
                    if evaluate and msg == '':
                        content = InterpreteStatus(valuedict,debug=debug)
                        # Perform switch and added "switch on/off" to content 
                        if not valuedict.get('switchcommand') in ['None','none',None]:
                            if debug:
                                print ("Found switching command ... running ardcom")
                            content = content + ' - switch: {}'.format(valuedict.get('switchcommand'))
                            # remember the switchuing command and only issue it if statusdict is changing
                            #switch = SendSwitchCommand()
                    elif not msg == '':
                        content =  msg
                    else:
                        content = ''
                else:
                    content = msg1+msg2

                statuskeylist.append('Sensor {} and key {}'.format(valuedict.get('sensorid'),valuedict.get('key')))
                if content:
                    statusdict['Sensor {} and key {}'.format(valuedict.get('sensorid'),valuedict.get('key'))] = content

                if debug:
                    print ("Finished parameterset {}".format(i))

            #notify = SendNotification(logpath, evaluate, statusmessage, notification, notificationconfig)
            # notify contains all new statusmessages (eventually reset)
            #if not para.get('switchcommand') in ['None','none',None]:
            #    switch = SendSwitchCommand()

    if conf.get('reportlevel') == 'full':
        # Get a unique status key list:
        statuskeylist = list(dict.fromkeys(statuskeylist))
        for elem in statuskeylist:
            cont = statusdict.get(elem,'')
            if cont == '':
                statusdict[elem] = "Everything fine"

    print (statusdict)

    receiver = conf.get('notification')
    cfg = conf.get('notificationconfig')
    logfile = conf.get('logfile')

    if debug:
        print ("Notifications send to: {}, {}".format(receiver,cfg))

    receiver = 'telegram'

    martaslog = ml(logfile=logfile,receiver=receiver)
    #if receiver == 'telegram':
    #    martaslog.telegram['config'] = cfg
    #elif receiver == 'email':
    #    martaslog.email['config'] = cfg

    martaslog.msg(statusdict)

    #scriptpath = os.path.realpath(__file__)
    #telegramcfg = os.path.join(os.path.dirname(scriptpath),"telegrambot.cfg")


if __name__ == "__main__":
   main(sys.argv[1:])


































"""
try:
    tgconf = GetConf(telegramcfg)
    tglogger = setuplogger(name='telegrambot',loglevel=tgconf.get('loglevel'),path=tgconf.get('bot_logging').strip())
    tglogpath = tgconf.get('bot_logging').strip()
    bot_id = tgconf.get('bot_id').strip()
    martasconfig = tgconf.get('martasconfig').strip()
    camport = tgconf.get('camport').strip()
    martasapp = tgconf.get('martasapp').strip()
    if not camport=='None':
        stationcommands['cam'] = 'get a picture from the selected webcam\n  Command options:\n  camport (like 0,1)\n  will be extended to /dev/video[0,1]'
    tmppath = tgconf.get('tmppath').strip()
    tgpar.camport = camport
    tgpar.tmppath = tmppath
    tgpar.tglogpath = tglogpath
    tgpar.martasapp = martasapp
    allowed_users =  [int(el) for el in tgconf.get('allowed_users').replace(' ','').split(',')]
    tglogger.debug('Successfully obtained parameters from telegrambot.cfg')
except:
    print ("error while reading config file - check content and spaces")

try:
    conf = acs.GetConf(martasconfig)
    logpath = '/var/log/syslog'
    if not conf.get('logging').strip() in ['sys.stdout','stdout']:
        logpath = conf.get('logging').strip()
    tgpar.logpath = logpath
    sensorlist = acs.GetSensors(conf.get('sensorsconf'))
    ardlist = acs.GetSensors(conf.get('sensorsconf'),identifier='?')
    sensorlist.extend(ardlist)
    owlist = acs.GetSensors(conf.get('sensorsconf'),identifier='!')
    sensorlist.extend(owlist)
    sqllist = acs.GetSensors(conf.get('sensorsconf'),identifier='$')
    sensorlist.extend(sqllist)
    mqttpath = conf.get('bufferdirectory')
    #apppath = conf.get('initdir').replace('init','app')
    tglogger.debug("Successfully obtained parameters from martas.cfg")
except:
    print ("Configuration (martas.cfg) could not be extracted - aborting")
    tglogger.warning("Configuration (martas.cfg) could not be extracted - aborting")
    sys.exit()


def _latestfile(path, date=False, latest=True):
    list_of_files = glob.glob(path) # * means all if need specific format then *.csv
    if latest:
        latest_file = max(list_of_files, key=os.path.getctime)
    else:
        latest_file = min(list_of_files, key=os.path.getctime)
    ctime = os.path.getctime(latest_file)
    if date:
        return datetime.fromtimestamp(ctime)
    else:
        return latest_file

def sensors():
    mesg = "Sensors:\n"
    for s in sensorlist:
        se = s.get('sensorid').replace('$','').replace('?','').replace('!','')
        try:
            lf = _latestfile(os.path.join(mqttpath,se,'*'),date=True)
            diff = (datetime.utcnow()-lf).total_seconds()
            flag = "active"
            if diff > 300:
                flag = "inactive since {:.0f} sec".format(diff)
        except:
            flag = "no buffer found"

        mesg += "{}: {}\n".format(se,flag)

    return mesg


def tgplot(sensor, starttime, endtime, keys=None):
    try:
        data = read(os.path.join(mqttpath,sensor,'*'),starttime=starttime, endtime=endtime)
        #print (os.path.join(mqttpath,sensor,'*'))
        #if not keys:
        #    keys = data._get_key
        mp.plot(data, outfile=os.path.join(tmppath,'tmp.png'))
        return True
    except:
        return False


def getspace():
    statvfs = os.statvfs('/home')

    total = (statvfs.f_frsize * statvfs.f_blocks / (1024.*1024.))     # Size of filesystem in bytes
    remain = (statvfs.f_frsize * statvfs.f_bavail / (1024.*1024.))     # Number of free bytes that ordinary users
    mesg = "status:\nDisk-size: {:.0f}MB\nDisk available: {:.0f}MB\nDisk occupied: {:.1f}%".format(total,remain, 100-(remain/total*100.))
    try:
        import psutil
        mem = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=1)
        avail = mem.available / (1024*1024)
        total = mem.total / (1024*1024)
        mesg += "\nMemory total: {}MB\nMemory available: {}MB\nCPU usage: {}%".format(total,avail,cpu)
    except:
        pass
    
    return mesg


def system():
    mesg = ''
    try:
        import platform
        sysls = platform.uname()
        mesg += "System:\n----------\nName: {}\nOperating system: {} ({})\nKernel: {}\nArchitecture: {}".format(sysls[1],sysls[0],sysls[3],sysls[2],sysls[4])
    except:
        pass
    # Geht nicht -> liefert immer dead --- checken
    #try:
    #    mesg += "\n\nMARTAS Process:\n----------"
    #    proc = subprocess.Popen(['/etc/init.d/martas','status'], stdout=subprocess.PIPE)
    #    lines = proc.stdout.readlines()
    #    #lines = proc.communicate()
    #    mesg += "\n{}".format(''.join(lines))
    #except:
    #    pass
    mesg += "\n\nSoftware versions:\n----------\nMagPy Version: {}".format(magpyversion)
    mesg += "\nTelegramBot Version: {}".format(tgpar.version)

    return mesg


def tail(f, n=1):
    mesg = "getlog:\n"
    try:
        proc = subprocess.Popen(['/usr/bin/tail', '-n', str(n), f], stdout=subprocess.PIPE)
        lines = proc.stdout.readlines()
        mesg += ''.join(lines)
    except:
        mesg += "Not enough lines in file"
    return mesg

def sensorstats(sensorid):
    lf = _latestfile(os.path.join(mqttpath,sensorid,'*'))
    data = read(lf)
    mesg = "Sensor info for {}:\n".format(sensorid)
    mesg += "Samplingrate: {} seconds\n".format(data.samplingrate())
    mesg += "Keys: {}\n".format(data.header.get('SensorKeys'))
    mesg += "Elements: {}\n".format(data.header.get('SensorElements'))
    start = datetime.strftime(_latestfile(os.path.join(mqttpath,sensorid,'*'),date=True, latest=False),"%Y-%m-%d")
    end = datetime.strftime(_latestfile(os.path.join(mqttpath,sensorid,'*'),date=True),"%Y-%m-%d")
    if start==end:
        mesg += "Available data: {}\n".format(start)
    else:
        mesg += "Available data: {} to {}\n".format(start,end)
    return mesg


def martas():
    # restart martas process
    # check_call(['/etc/init.d/martas'],['restart'])
    try:
        # For some reason restart doesn't work?
        tglogger.debug("Running check_call...")
        call = '/etc/init.d/martas restart'
        p = subprocess.Popen(call, stdout=subprocess.PIPE, shell=True)
        tglogger.debug("Restart send - getlog for details")
        mesg = "Restart command send - check getlog for details (please wait some secs)"
        #try:
        #    (output, err) = p.communicate()
        #    tglogger.debug("Error codes: {}".format(err))
        #except:
        #    pass
    except subprocess.CalledProcessError:
        mesg = "martas: check_call didnt work"
    except:
        mesg = "martas: check_call problem"
    return mesg


def reboot():
    # Rebooting the system
    try:
        # For some reason restart doesn't work?
        tglogger.debug("Rebooting...")
        call = 'reboot'
        p = subprocess.Popen(call, stdout=subprocess.PIPE, shell=True)
        tglogger.debug("Restart send - getlog for details")
        mesg = "Reboot command send "
        #try:
        #    (output, err) = p.communicate()
        #    tglogger.debug("Error codes: {}".format(err))
        #except:
        #    pass
    except subprocess.CalledProcessError:
        mesg = "martas: check_call didnt work"
    except:
        mesg = "martas: check_call problem"
    return mesg



def martasupdate():
    # update martas from git
    # check_call(['git -C /home/cobs/MARTAS'],['pull'])
    martaspath = tgconf.get('martaspath').strip()
    user = 'cobs'
    try:
        # For some reason restart doesn't work?
        mesg = "Sending update command ..."
        tglogger.debug("Running subprocess call ...")
        call = "su - {} -c '/usr/bin/git -C {} pull'".format(user,martaspath)
        mesg = "Sending update command ... {}".format(call)
        p = subprocess.Popen(call, stdout=subprocess.PIPE, shell=True)
        tglogger.debug("Update command send ...")
        (output, err) = p.communicate()
        mesg += "{}".format(output)
        mesg += "... done"
    except subprocess.CalledProcessError:
        mesg = "martas: check_call didnt work"
    except:
        mesg = "martas: check_call problem"
    return mesg

def getcam(command):
    camport = tgpar.camport
    cmd = command.split()
    l = len(cmd)
    if l > 1:
        try:
            po = int(cmd[1].replace(' ','').strip())
            camport = "/dev/video{}".format(po)
        except:
            tglogger.warning("Provided cam port not recognized. Should be 0,1,etc")
    return camport


def switch(command):
    # restart martas process
    try:
        tglogger.debug("Running check_call to start switch...")
        python = sys.executable
        #path = '/home/cobs/MARTAS/app/ardcomm.py'
        path = os.path.join(tgpar.martasapp,'ardcomm.py')
        tglogger.debug("tpath: {}".format(path))
        option = '-c'
        call = "{} {} {} {}".format(python,path,option,command)
        tglogger.debug("Call: {}".format(call))
        p = subprocess.Popen(call, stdout=subprocess.PIPE, shell=True)
        (output, err) = p.communicate()
        mesg = "{}".format(output)
    except subprocess.CalledProcessError:
        mesg = "martas: check_call didnt work"
    except:
        mesg = "martas: check_call problem"
    return mesg


def help():
    # print dictionary of commands
    mesg = ''
    for key in stationcommands:
        mesg += "COMMAND: '/{}'\n".format(key)
        mesg += "{}\n\n".format(stationcommands[key])
    #print ("help called", mesg)
    return mesg


def handle(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    tglogger.info("Bot -> ContentType: {}; ChatType: {}".format(content_type, chat_type))
    firstname = msg['from']['first_name']
    userid = msg['from']['id']

    chat_id = msg['chat']['id']
    command = msg['text'].replace('/','')

    logpath = tgpar.logpath
    camport = tgpar.camport
    tmppath = tgpar.tmppath

    if not chat_id in allowed_users:
        bot.sendMessage(chat_id, "My mother told me not to speak to strangers, sorry...")
        tglogger.warning('--------------------- Unauthorized access -------------------------') 
        tglogger.warning('!!! unauthorized access from ChatID {} (User: {}) !!!'.format(command,chat_id,firstname)) 
        tglogger.warning('-------------------------------------------------------------------') 
    else:
        if content_type == 'text':
            tglogger.info('Received command "{}" from ChatID {} (User: {})'.format(command,chat_id,firstname))

            if command.startswith('help'): # == 'help':
               bot.sendMessage(chat_id, help())
            elif command.startswith('getlog'):
               cmd = command.split()
               if len(cmd) > 1:
                   try:
                       N = int(cmd[1])
                   except:
                       N = 10
               else:
                   N = 10
               if len(cmd) > 2:
                   tmpname = cmd[2]
                   if tmpname in ['syslog', 'dmesg']:
                       tmppath = os.path.join('/var/log', tmpname)
                   elif tmpname == 'telegrambot':
                       tmppath = tgpar.tglogpath
                   elif tmpname == 'martas':
                       tmppath = tgpar.logpath
                   if os.path.isfile(tmppath):
                       logpath = tmppath
               if os.path.isfile(logpath):
                   tglogger.debug("Checking logfile {}".format(logpath))
                   mesg = tail(logpath,n=N)
               else:
                   mesg = "getlog:\nlogfile not existing"
               bot.sendMessage(chat_id, mesg)
            elif command.startswith('status'):
               mesg = getspace()
               bot.sendMessage(chat_id, mesg)
            elif command.startswith('system'):
               mesg = system()
               bot.sendMessage(chat_id, mesg)
            elif command.startswith('hello'):
               mesg = "Hello {}, nice to talk to you.".format(firstname)
               bot.sendMessage(chat_id, mesg)
            elif command.startswith('cam'):
               usedcamport = getcam(command)
               if usedcamport == 'None':
                   mesg = "No camport  (fswebcam properly installed?)"
                   bot.sendMessage(chat_id, mesg)
               else:
                   try:
                       tglogger.debug("Creating image...")
                       tglogger.debug("Selected cam port: {} and temporary path {}".format(usedcamport,tmppath))
                       subprocess.call(["/usr/bin/fswebcam", "-d", usedcamport, os.path.join(tmppath,'webimage.jpg')])
                       tglogger.debug("Subprocess for image creation finished")                       
                       bot.sendPhoto(chat_id, open(os.path.join(tmppath,'webimage.jpg'),'rb'))
                   except:
                       mesg = "Cam image not available (fswebcam properly installed?)"
                       bot.sendMessage(chat_id, mesg)
            elif command =='martasrestart':
               bot.sendMessage(chat_id, "Restarting acquisition process ...")
               mesg = martas()
               bot.sendMessage(chat_id, mesg)
            elif command =='martasupdate':
               bot.sendMessage(chat_id, "Updating MARTAS ...")
               mesg = martasupdate()
               bot.sendMessage(chat_id, mesg)
            elif command =='reboot':
               bot.sendMessage(chat_id, "Rebooting ...")
               mesg = reboot()
               bot.sendMessage(chat_id, mesg)
            elif command.startswith('plot'):
               cmd = command.split()
               l = len(cmd)
               endtime = datetime.utcnow()
               starttime = datetime.utcnow()-timedelta(days=1)
               if l >= 2:
                   sensorid = cmd[1]
               else:
                   bot.sendMessage(chat_id, "you need to specify a sensorid")
                   return
               if l >= 3:
                   tglogger.debug("Found three parameter")
                   try:
                       st = cmd[2]
                       if vers=='2':
                           st = str(st)
                       starttime = DataStream()._testtime(st)
                   except:
                       print ("starttime does not have a appropriate format")
                       pass
               if l >= 4:
                   tglogger.debug("Found four parameter")
                   try:
                       et = cmd[3]
                       if vers=='2':
                           et = str(et)
                       endtime = DataStream()._testtime(et)
                   except:
                       print ("endtime does not have a appropriate format")
                       pass
               if l == 5:
                   k = cmd[4].split(',')
                   tglogger.debug(k)

               suc = tgplot(sensorid,starttime,endtime)
               if suc:
                   # ASCII error (python 3.xx)
                   bot.sendPhoto(chat_id, open(os.path.join(tmppath,'tmp.png'),'rb'))
               else:
                   mesg = "Plot could not be created" # tgplot
                   bot.sendMessage(chat_id, mesg)
            elif command.startswith('sensors'):
               cmd = command.split()
               l = len(cmd)
               if l > 1:
                   # read latest file of selected sensor and return some statistics
                   tglogger.debug("Returning Sensor statistics")
                   mesg = sensorstats(cmd[1])
               else:
                   mesg = sensors()
               bot.sendMessage(chat_id, mesg)
            elif command.startswith('switch'):
               tglogger.info("Switching received")
               cmd = command.split()
               tglogger.info("Switching received: {}".format(len(cmd)))
               l = len(cmd)
               if l > 1:
                   # read latest file of selected sensor and return some statistics
                   tglogger.debug("Switching ... {}".format(cmd[1]))
                   #if cmd[1].strip() in [u'P:0:4',u'P:1:4',u'P:0:5',u'P:1:5',u'Status']:
                   command = cmd[1].strip()
                   print (command)
                   #else:
                   #    command = 'Status'
               else:
                   command = 'Status'
               mesg = switch(command)
               bot.sendMessage(chat_id, mesg)

if vers=='2':
    bot = telepot.Bot(str(bot_id))
else:
    bot = telepot.Bot(bot_id)
MessageLoop(bot, handle).run_as_thread()
tglogger.info('Listening ...')

# Keep the program running.
while 1:
    try:
        time.sleep(10)
    except KeyboardInterrupt:
        tglogger.info('\n Program interrupted')
        exit()
    except:
        tglogger.error('Other error or exception occured!')

"""
