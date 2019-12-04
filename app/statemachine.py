#!/usr/bin/env python
# coding=utf-8

"""
MARTAS - threshold state machine
################################

DESCRIPTION:
Threshold state machine facilitates user defined finite state machines
to set defined actions in dependecy of data behavior.

Data is read from a defined source (DB or file, eventually MQTT).
Certain criteria e.g. when thresholds are exceeded or undergone will change
the state and create an action like sending an email or actuate a switch.
Following states can prevent further actions and wait for signals that
e.g. reset the state machine into the initial state.

statemachine.py can be scheduled in crontab.


REQUIREMENTS:
pip install geomagpy (>= 0.3.99)

APPLICATION:
statemachine -m /path/to/statemachine.cfg


statemachine.cfg: (looks like)
##  ----------------------------------------------------------------
##           CONFIGURATION DATA for STATEMACHINE.PY
##  ----------------------------------------------------------------

# MARTAS directory
martasdir            :   /home/cobs/MARTAS/

# Define data source (file, db, ...)
source               :   file

# If source = db then define data base credentials created by addcred (MARTAS)
dbcredentials        :   None


# If source = file define the MARTAS buffer base path
bufferpath           :   /srv/mqtt/


# Statusfile (a json style dictionary, which contains states) 
statusfile              :   /var/log/magpy/status.log

# Notifications (uses martaslog class, one of email, telegram, mqtt, log) 
notification         :   email
notificationconfig   :   /etc/martas/notification.cfg


# Report level ("full" will report all changes, also within range states)
reportlevel          :   partial


# serial communication for switch commands (making use of ardcomm.py (MARTAS/app)
#port                :   device to which command is send - default is /dev/ttyACM0
#baudrate            :   default is 9600
#parity              :   default is "N"
#bytesize            :   default is 8
#stopbits            :   default is 1
#timeout             :   default is 2
#eol                 :   end of line - default is \r\n


#parameter (all given parameters are checked in the given order, use semicolons for parameter list):
# sensorid; timerange to check; key to check, value, function, state, statusmessage, switchcommand(optional)
# sensorid; timerange to check; key to check, value, function, operator, statusmessage, nextstatus, [action, args, action, args,...]
status  :  initial
1  :  DS18B20XX;1800;t1;5;average;below;temperature below 5;triggered;email;Temperatur unter 5 Grad gefallen;switch;swP:1:4
#1  :  DS18B20XX;1800;t1;5;average;below;default;triggered;email
2  :  DS18B20XX;1800;t1;5;average;below;none
3  :  DS18B20XZ;600;t2;10;max;below;ok
4  :  DS18B20XZ;600;t2;10;max;above;warning at week
5  :  DS18B20XZ;600;t2;20;max;above;alarm issued at date
6  :  DS18B20XZ;600;t2;3;stddev;above;flapping state
7  :  DS18B20XX;1800;t1;10;median;below;default;heating;swP:1:4

status  :  triggered
1  :  DS18B20XX;1800;t1;5;not average;below;temperature reentered to normal range;reentered;email
  
status  :  reentered
1  :  DS18B20XX;1800;t1;5;average;below;temperature seems to be flapping;flapping;email

status  :  flapping
1  :  DS18B20XX;1800;t1;5;average;below;date: temperature seems to be flapping;flapping;email

status  :  heating
7  :  DS18B20XX;1800;t1;11;median;below;default;initial;swP:0:4

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


## Description: Parameterset "1":  if temperature t1 (average of last 30 min (1800 sec)) is falling below 5 degrees
## then send default statusmessage to the notification system (e.g. email)
## and eventually send switchcommand to serial port
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
import json, copy

try:
    import paho.mqtt.client as mqtt
except:
    print ("MQTT not available")


if sys.version.startswith('2'):
    pyvers = '2'
else:
    pyvers = '3'


valuenamelist = ['sensorid','timerange','key','value','function','operator','statusmessage','nextstatus']


def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def readConfig(path):
    """
    DESCRIPTION:
        read configuration paths etc from a file
        this is stored in configdict
        read parameters and states of the state machines (1,2,3,...)
        complete info and behavior of the state machines is stored in statusdict
    """
    #try:
    if 1:
        status = ""
        # TODO backward compatibility? (-> default status, if not mentioned in the config file...)
        statusdict = {}
        configdict = {}
        config = open(path,'r')
        confs = config.readlines()

        for conf in confs:
            conflst = conf.split(' : ')
            if conf.startswith('#'): 
                continue
            elif conf.isspace():
                continue
            elif len(conflst) == 2:
                if conflst[0] == "status":
                    # get the status name for the following list
                    status = conflst[1].strip()
                if is_number(conflst[0]):
                    # extract parameterlist
                    key = conflst[0].strip()
                    values = conflst[1].strip().split(';')
                    valuedict = {}
                    if len(values) < len(valuenamelist):
                        # there must be entries in every field, additionally actions with args are possible
                        print ("PARAMETER: provided values differ from the expected amount - please check")
                    else:
                        for idx,valuename in enumerate(valuenamelist):
                            # mandatory parameters
                            valuedict[valuename] = values[idx].strip()
                        isAction = True
                        actionlist = []
                        for idx in range(len(valuenamelist),len(values)):
                            # optional parameters
                            if isAction:
                                action = values[idx].strip()
                                actionlist.append({'action':action})
                                isAction = False
                            else:
                                argument = values[idx].strip()
                                actionlist[-1]['argument'] = argument
                                isAction = True
                        if not actionlist == []:
                            valuedict['action'] = actionlist
                            # TODO important that len of action = argument?
                            #valuedict['argument'] = argumentlist
                        if not status in statusdict:
                            statusdict[status] = {}
                        if not key in statusdict[status]:
                            statusdict[status][key] = [copy.deepcopy(valuedict)]
                        else:
                            statusdict[status][key].append(copy.deepcopy(valuedict))
                else:
                    key = conflst[0].strip()
                    value = conflst[1].strip()
                    configdict[key] = value
    # status is not needed here
    del configdict['status']
    #except:
    if 0:
        print ("Problems when loading conf data from file...")
        #return ({}, {})
        print ("Could not obtain configuration data - aborting")
        sys.exit()

    return (configdict, statusdict)



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
        print ("Obtaining test value for key {} with function {}".format(key,function))
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


def CheckThreshold(testvalue, threshold, operator, debug=False):
    """
    DESCRIPTION:
     returns statusmessage
    """
    evaluate = False
    msg = ''
    if operator in ['below','Below','smaller']:
        comp = '<'
    elif operator in ['above','Above','greater']:
        comp = '>'
    elif operator in ['equal','Equal']:
        comp = '=='
    elif operator in ['equalabove']:
        comp = '>='
    elif operator in ['equalbelow']:
        comp = '<='
    else:
        msg = 'operator needs to be one of below, above or equal'
    tester = "{} {} {}".format(testvalue,comp,threshold)
    if debug:
        print ("Checking: {}".format(tester))
    try:
        if eval(tester):
            evaluate = True
            if debug:
                print (" ... positive")
        else:
            evaluate = False
            if debug:
                print (" ... negative - criteria not met")
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
    msg = msg.replace('none', '')
    msg = msg.replace('default', defaultline)
    msg = msg.replace('date', datetime.strftime(ct,"%Y-%m-%d"))
    msg = msg.replace('hour', datetime.strftime(ct,"%Y-%m-%d %H:%M"))
    msg = msg.replace('minute', datetime.strftime(ct,"%Y-%m-%d %H:%M"))
    msg = msg.replace('month', datetime.strftime(ct,"%Y-%m"))
    msg = msg.replace('year', datetime.strftime(ct,"%Y"))
    msg = msg.replace('week', 'week {}'.format(ct.isocalendar()[1]))

    return msg


def main(argv):

    #para = sp.parameterdict
    #conf = sp.configdict
    para = {}
    conf = {}
    # necessary configs (may be overwritten):
    conf['statusfile']='/var/log/magpy/statusfile.log'
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
            print ("Getting all parameters of the state machine from configuration file: {}".format(configfile))
            (conf, para) = readConfig(configfile)
        elif opt in ("-U", "--debug"):
            debug = True


    if debug:
        print ("Configuration dictionary: \n{}".format(conf))
        print ("Parameter dictionary: \n{}".format(para))

    if not (len(para)) > 0:
        print ("No parameters given to be checked - aborting") 
        sys.exit()

    statusdict = {}
    if os.path.isfile(conf['statusfile']):
        # read log if exists and exentually update changed information
        # return changes
        with open(conf['statusfile'], 'r') as file:
            statusdict = json.load(file)
        print ("Statusfile {} loaded".format(conf['statusfile']))
    
    # For each machine
    for i in range(0,1000): 
        valuedict = {}
        values = []
        if not str(i) in statusdict and str(i) in para['start']:
            # machine is not yet in the statusfile, let's add it to the dict
            statusdict[str(i)] = {}
            statusdict[str(i)]['status'] = 'start'
            #laststatusdict[str(i)]['sensorid'] = para['start'][str(i)]['sensorid']
            #laststatusdict[str(i)]['key'] = para['start'][str(i)]['key']
        if str(i) in statusdict:
            status = statusdict[str(i)]['status']
            # TODO handle deleted statuus!
            values = para[status].get(str(i),[])
        if not values == []:
            if debug:
                print ("Checking state machine {}".format(i))
            data = DataStream()
            testvalue = None
            # TODO do I need this? evaluate = {}
                
            # Obtain a magpy data stream of the respective data set
            if debug:
                print ("Accessing data from {} at {}: Sensor {} - Amount: {} sec".format(conf.get('source'),conf.get('bufferpath'),valuedict.get('sensorid'),valuedict.get('timerange') ))

            for valuedict in values:
                (data,msg1) = GetData(conf.get('source'), conf.get('bufferpath'), conf.get('database'), conf.get('dbcredentials'), valuedict.get('sensorid'),valuedict.get('timerange'), debug=debug , startdate=conf.get('startdate') )
                (testvalue,msg2) = GetTestValue( data, valuedict.get('key'), valuedict.get('function'), debug=debug) # Returns comparison value(e.g. mean, max etc)
                if is_number(testvalue):
                    (evaluate, msg) = CheckThreshold(testvalue, valuedict.get('value'), valuedict.get('operator'), debug=debug) # Returns statusmessage
                    if evaluate and msg == '':
                        # criteria are met - do something
                        # change status
                        if debug:
                            print ("changing status of machine "+str(i)+" from")
                            print (statusdict[str(i)]['status'])
                            print ("to")
                            print (valuedict['nextstatus'])
                        statusdict[str(i)]['status'] = valuedict['nextstatus']
                        if 'action' in valuedict:
                            for action in valuedict['action']:
                                sm_support_path = os.path.join(conf.get('martasdir'), 'app')
                                sys.path.insert(1, sm_support_path)
                                import sm_support
                                if action['action'] == 'email':
                                    dic = sm_support.readConfigFromFile(conf.get('emailconfig'))
                                    dic['Text'] = action['argument']
                                    sm_support.sendmail(dic)


                        # TODO handle content resp. errors
                        content = InterpreteStatus(valuedict,debug=debug)
                        # Perform switch and added "switch on/off" to content 
                        if not valuedict.get('switchcommand') in ['None','none',None]:
                            if debug:
                                print ("Found switching command ... eventually will send serial command (if not done already) after checking all other commands")
                            content = '{} - switch: {}'.format(content, valuedict.get('switchcommand'))
                            # remember the switchuing command and only issue it if statusdict is changing
                    elif not msg == '':
                        content =  msg
                    else:
                        content = ''
            else:
                content = msg1+' - '+msg2

            #if content:
            if 0:
                statuskeylist.append('Sensor {} and key {}'.format(valuedict.get('sensorid'),valuedict.get('key')))
                statusdict['Sensor {} and key {}'.format(valuedict.get('sensorid'),valuedict.get('key'))] = content

            if debug:
                print ("Finished state machine {}".format(i))

    with open(conf['statusfile'], 'w') as file:
        if debug:
            print ('writing to '+conf['statusfile']+' :')
            print (statusdict)
        file.write(json.dumps(statusdict)) # use `json.loads` to do the reverse
    exit()
    

    if conf.get('reportlevel') == 'full':
        # Get a unique status key list:
        statuskeylist = list(dict.fromkeys(statuskeylist))
        for elem in statuskeylist:
            cont = statusdict.get(elem,'')
            if cont == '':
                statusdict[elem] = "Everything fine"

    if debug:
        print ("Statusdict: {}".format(statusdict))

    receiver = conf.get('notification')
    cfg = conf.get('notificationconfig')
    logfile = conf.get('logfile')

    if debug:
        print ("New notifications will be send to: {} (Config: {})".format(receiver,cfg))

    martaslog = ml(logfile=logfile,receiver=receiver)
    if receiver == 'telegram':
        martaslog.telegram['config'] = cfg
    elif receiver == 'email':
        martaslog.email['config'] = cfg

    changes = martaslog.msg(statusdict)

    if not len(changes) > 0:
        print ("Nothing to report - threshold check successfully finished")

    for element in changes:
        line = changes.get(element)
        if debug:
            print ("Changes affecting:", element)
        l = line.split('switch:')
        if len(l) == 2:
            print (" ... now dealing with switching serial command:")
            comm = l[1].strip()
            script = os.path.join(conf.get('martasdir'),'app','ardcomm.py')
            pythonpath = sys.executable
            arg1 = "-c {}".format(comm)
            arg2 = "-p {}".format(conf.get('port'))
            arg3 = "-b {}".format(conf.get('baudrate'))
            arg4 = "-a {}".format(conf.get('parity'))
            arg5 = "-y {}".format(conf.get('bytesize'))
            arg6 = "-s {}".format(conf.get('stopbits'))
            arg7 = "-t {}".format(conf.get('timeout'))
            #arg8 = "-e {}".format(conf.get('eol')) # not used so far

            command = "{} {} {} {} {} {} {} {} {}".format(pythonpath,script,arg1, arg2, arg3, arg4, arg5, arg6, arg7) ## Too be checked
            command = "{} {} {}".format(pythonpath,script,arg1)
            if debug:
                print (" ... sending {}".format(command))


            try:
                import subprocess
                p = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
                (output, err) = p.communicate()
                mesg = "{}".format(output)
            except subprocess.CalledProcessError:
                mesg = "threshold: sending command didnt work"
            except:
                mesg = "threshold: sending command problem"

            print (mesg)

            print (" ... success")

if __name__ == "__main__":
   main(sys.argv[1:])


"""
class sp(object):
    # Structure for switch parameter
    configdict = {}
    configdict['bufferpath'] = '/srv/mqtt'
    configdict['dbcredentials'] = 'cobsdb'
    configdict['database'] = 'cobsdb'
    configdict['reportlevel'] = 'partial'
    configdict['notification'] = 'email'
    configdict['notification'] = 'log'
    valuenamelist = ['status','sensorid','timerange','key','value','function','operator','statusmessage','switchcommand']
    #valuedict = {'sensorid':'DS18B20','timerange':1800,'key':'t1','value':5,'function':'average','state':'below','message':'on','switchcommand':'None'}
    #parameterdict = {'1':valuedict}
    parameterdict = {}
    configdict['version'] = '1.0.0' # thresholdversion
    configdict['martasdir'] = '/home/cobs/MARTAS/'
    # Serial Comm
    configdict['port'] = '/dev/ttyACM0'
    configdict['baudrate'] = 9600
    configdict['parity'] = 'N'
    configdict['bytesize'] = 8
    configdict['stopbits'] = 1
    configdict['timeout'] = 2
    configdict['eol'] = '"\r\n"'

    #Testset
    #configdict['startdate'] = datetime(2018,12,6,13)
    #valuenamelist = ['sensorid','timerange','key','value','function','state','statusmessage','switchcommand']
    #valuedict = {'sensorid':'ENV05_2_0001','timerange':1800,'key':'t1','value':5,'function':'average','state':'below','message':'on','switchcommand':'None'}
"""
"""
def updateStatus(logfile,para):
        changes={}
        if os.path.isfile(logfile):
            # read log if exists and exentually update changed information
            # return changes
            with open(logfile, 'r') as file:
                exlogdict = json.load(file)
            print ("Logfile {} loaded".format(logfile))
            for el in logdict:
                if not el in exlogdict:
                    # Adding new sensor and state
                    print ("Not Existing:", el)
                    changes[el] = logdict[el]
                else:
                    print ("Existing:", el)
                    # Checking state
                    if not logdict[el] == exlogdict[el]:
                        # state changed
                        changes[el] = logdict[el]
            ## check for element in exlogdict which are not in logdict
            for el in exlogdict:
                if not el in logdict:
                    # Sensor has been removed
                    print ("Removed:", el)
                    changes[el] = "removed"

            if not len(changes) == 0:
                # overwrite prexsiting logfile
                print ("-------------")
                print ("Changes found")
                print ("-------------")
                with open(logfile, 'w') as file:
                    file.write(json.dumps(logdict)) # use `json.loads` to do the reverse
        else:
            # write logdict to file
            with open(logfile, 'w') as file:
                file.write(json.dumps(logdict)) # use `json.loads` to do the reverse
            print ("Logfile {} written successfully".format(logfile))

        return changes
"""
