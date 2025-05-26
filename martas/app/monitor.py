#!/usr/bin/env python
# coding=utf-8

"""
Monitoring script:

allows for:
1) to check actuality for last buffer file
2) check actuality of data base tables
3) check disk space and memory
4) check database size
5) check LogFile for frequent messages
6) trigger the execution of external scripts if one of 1 to 4 happens

This script should be running on each martas machine.
It will produce a mqtt json statusmessage if any critical 
information is changing like disk size or buffer files are not 
written any more.

This script can also check for log file changes. If logfile differences contain repeated similar messages
(too be defined in the config) then it is possible to trigger the execution of an external bash script.

################################

add crontag to regularly run monitor (root)
sudo crontab -e
5  *  *  *  *  /usr/bin/python3 /path/to/monitor.py -c /path/to/conf.cfg -n MARCOS -j marcos  > /dev/NULL 2&>1
"""
# Define packges to be used (local refers to test environment)
# ------------------------------------------------------------
import os, sys, getopt
import glob
from datetime import datetime, timezone
import paho.mqtt.client as mqtt
import json
import socket
from magpy.stream import DataStream
from magpy.core import database
from magpy.core import methods as mpmeth
import magpy.opt.cred as mpcred
import numpy as np
import filecmp, shutil
import subprocess

from martas.core.methods import martaslog as ml
from martas.core import methods as mm
from martas.version import __version__

"""
monitorconf = {'logpath' : '/var/log/magpy/mm-monitor.log',		# path to log file
               'basedirectory' : '/srv', 			# base directory of buffer (MARTAS) and archive (MARCOS)
               'dbcredentials' : 'cobsdb', 			# where to find database credentials
               'defaultthreshold' : '600',  			# accepted age of data in file or database (in seconds)
               'ignorelist' : ['BASELINE','QUAKES','IPS','PIERS','DATAINFO','SENSORS','STATIONS','DIDATA_WIC','FLAGS'],  # sensors not too be checked
               'thresholds' : {'RCS':180000,'TILT':100000,'METEO':10800,'WIC':20000,'GAMMA':10800,'GWR':10800, 'LEMI036_3':180000, 'GSM90_6107632':180000, 'BMP085_10085004':180000, 'SHT75_RASHT004':180000, 'GSM90_7':180000, 'GP20S3EWstatus': 180000}, 		# threshold definitions
               'tmpdir' : '/tmp',			 	# for log file to check
               'logfile' : '/var/log/magpy/marcos.log', 	# log file to check
               'logtesttype' : 'repeat', 			# checks on log file: NEW (new input), REPEATed, LAST message (if a certain message is repeated more than x times)
               'logsearchmessage' : 'writeDB: unknown MySQL error when checking for existing tables!',
               'tolerance'  :  20,  				# tolerated amount of repeated messages
               'joblist' : ['space','martas','marcos','logfile'], 			# basic job list (can be space (only disk space), martas (buffer files), marcos (tables), logfile (logfiles)
               'execute'  :  '/path/execute.sh',  		# bash script to be executed if critical error is found (message contains 'execute'), add execution date to log
               'executecriteria'  :  'alternating',  	        # day (every day), week (once per week), alternating (try immidiatly, then one day later, finally one week later),
               'notification'  :  'telegram',  	        	# none,mail,telegram
               'notificationconf' : '/etc/martas/telegram.cfg', # configuration for notification
               'level'   :   3 }
"""

def _latestfile(path, date=False, latest=True):
    """
    DESCRIPTION
        get latest file
    """
    list_of_files = glob.glob(path) # * means all if need specific format then *.csv
    if len(list_of_files) > 0:
        if latest:
            latest_file = max(list_of_files, key=os.path.getctime)
        else:
            latest_file = min(list_of_files, key=os.path.getctime)
        ctime = os.path.getctime(latest_file)
        if date:
            return datetime.fromtimestamp(ctime)
        else:
            return latest_file
    else:
        return ""

def getspace(path,warning=80,critical=90): # path = '/srv'
    """
    DESCRIPTION
        get space
    """
    statvfs = os.statvfs(path)
    total = (statvfs.f_frsize * statvfs.f_blocks / (1024.*1024.))     # Size of filesystem in bytes
    remain = (statvfs.f_frsize * statvfs.f_bavail / (1024.*1024.))     # Number of free bytes that ordinary users
    usedper=100-(remain/total*100.)
    print ("Disk containing {} currently uses: {}%".format(path,usedper))
    #mesg = "status:\nDisk-size: {:.0f}MB\nDisk available: {:.0f}MB\nDisk occupied: {:.1f}%".format(total,remain, 100-(remain/total*100.))
    level = 'OK'
    if usedper >= warning:
        level = "warning: used > {}%".format(warning)
    if usedper >= critical:
        level = "critical: used > {}%".format(critical)
    return level


def _testJobs(joblist, allowedjobs):
    joblist = list(set([job for job in joblist if job in allowedjobs]))
    if len(joblist) == 0:
        print ("No valid jobs found")
        joblist = None
    return joblist


def check_martas(testpath='/srv', threshold=600, jobname='JOB', statusdict=None, ignorelist=None, thresholddict=None, debug=False):
    """
    DESCRIPTION:
        Walk through all subdirs of /srv and check for latest files in all subdirs
        add active or inactive to a log file
        if log file not exists: just add data
        if existis: check for changes and create message with all changes
    """
    if not statusdict:
        statusdict = {}
    if not ignorelist:
        ignorelist = []
    if not thresholddict:
        thresholddict = {}
    defaultthreshold = threshold
    # neglect archive, products and projects directories of MARCOS
    dirs=[x[0] for x in os.walk(testpath) if not x[0].find("archive")>-1 and not x[0].find("products")>-1 and not x[0].find("projects")>-1]
    for d in dirs:
        ld = _latestfile(os.path.join(d,'*'),date=True)
        lf = _latestfile(os.path.join(d,'*'))
        if os.path.isfile(lf):
            if debug:
                print ("Ckecking {} ...".format(lf))
            # check white and blacklists
            performtest = False
            if not any([lf.find(ig) > -1 for ig in ignorelist]):
                if debug:
                   print ("  not in ignorelist")
                now = datetime.now(timezone.utc).replace(tzinfo=None)
                diff = (now-ld).total_seconds()
                dname = d.split('/')[-1]
                state = "active"
                if any([lf.find(th) > -1 for th in thresholddict]):
                    matches = list(set([th for th in thresholddict if lf.find(th) > -1]))
                    try:
                        thresholds = [float(thresholddict.get(match)) for match in matches]
                        threshold = max(thresholds)
                        if debug:
                            print ("  using defined threshold of {}".format(threshold))
                    except:
                        pass
                if diff > threshold:
                    state = "inactive"
                threshold = defaultthreshold
                msgname = "{}-{}".format(jobname,dname.replace('_',''))
                statusdict[msgname] = state
                if debug:
                    print ("{}: {}".format(dname,state))
    return statusdict


def check_datafile(testpath='/srv/products/raw', threshold=600, jobname='JOB', statusdict=None, ignorelist=None, thresholddict=None, debug=False):
    """
    DESCRIPTION:
        Git to the directory testpath and check for latest files
        add active or inactive to a log file
        if log file not exists: just add data
        if exists: check for changes and create message with all changes
    """
    if not statusdict:
        statusdict = {}
    if not ignorelist:
        ignorelist = []
    if not thresholddict:
        thresholddict = {}

    ld = _latestfile(testpath,date=True)
    lf = _latestfile(testpath)
    if os.path.isfile(lf):
        if debug:
            print (" Latest file: {} ...".format(lf))

        # check white and blacklists
        performtest = False
        if not any([lf.find(ig) > -1 for ig in ignorelist]):
            if debug:
                print ("   -> not containd in ignorelist - continuing")
            now = datetime.now(timezone.utc).replace(tzinfo=None)
            diff = (now-ld).total_seconds()
            dname = testpath.split('/')[-1]
            state = "recent file found"
            if diff > threshold:
                state = "no recent file"
            msgname = "{}-{}".format(jobname,dname.replace('_','').replace('*',''))
            statusdict[msgname] = state
            if debug:
                print ("{}: {}".format(dname,state))
        else:
            print ("    -> containd in ignorelist - passing")

    return statusdict


def check_marcos(db,threshold=600, statusdict=None,jobname='JOB',excludelist=None,acceptedoffsets=None,debug=False):
    """
    DESCRIPTION
        add text
    """
    if not statusdict:
        statusdict = {}
    if not excludelist:
        excludelist = []
    if not acceptedoffsets:
        acceptedoffsets = {}

    testst = DataStream()
    offset = {}
    testname = '{}-DBactuality'.format(jobname)
    tables = []
    lasttime = None
    cursor = db.db.cursor()
    ok = True

    if debug:
        print ("1. Get all tables")
        print ("-----------------------------------")
    tablessql = 'SHOW TABLES'
    message = db._executesql(cursor,tablessql)
    if message:
        ok = False
        print (message)
    if ok:
        tables = cursor.fetchall()
        tables = [el[0] for el in tables]
        if not len(tables) > 0:
            print ('check table: no tables found - stopping')
            ok = False
    else:
        print ('check table: aborting')
        #cursor.close()
        ok = False

    if ok:
        if debug:
            print ("2. Extract tables to be examined")
            print ("-----------------------------------")
        if debug:
            print ("Data to be excluded: {}".format(excludelist))
        newtables = []
        for el in tables:
            drop = False
            for ex in excludelist:
                if el.startswith(ex):
                    drop = True
            if not drop:
                newtables.append(el)
        tables = newtables
        if debug:
            print ("Remaining tables: {}".format(tables))

    if ok:
        if debug:
            print ("3. Delete any existing timestamps which are in the future")
            # classic problem of IWT
            print ("-----------------------------------")
        delsql = "DELETE FROM IWT_TILT01_0001_0001 WHERE time > NOW()"
        if ok:
            message = db._executesql(cursor, delsql)
            if message:
                print(message)
        # eventually an execute is necessary here

    if ok:
        if debug:
            print ("4. Getting last input in each table")
            print ("-----------------------------------")
        for table in tables:
            if debug:
                print (' -> running for {}'.format(table))
            lastsql = 'SELECT time FROM {} ORDER BY time DESC LIMIT 1'.format(table)
            message = db._executesql(cursor, lastsql)
            if message:
                print(message)
            value = cursor.fetchall()
            try:
                lasttime = value[0][0]
                timetest = True
            except:
                timetest = False
                pass
            if timetest:
                lastt = mpmeth.testtime(lasttime)
                # Get difference to current time
                now = datetime.now(timezone.utc).replace(tzinfo=None)
                tdiff = np.abs((now-lastt).total_seconds())
                offset[table] = tdiff
                if debug:
                    print ("Difference: {}".format(tdiff))

    if ok:
        if debug:
            print ("5. Check threshold information")
            print ("-----------------------------------")
        statusdict[testname] = 'possible'
        for el in offset:
            # determine threshold
            usedthreshold = threshold
            name = "{}-{}".format(testname,el.replace('_',''))
            for elem in acceptedoffsets:
                if el.find(elem) > -1:
                    usedthreshold = acceptedoffsets[elem]
            if offset[el] > usedthreshold:
                if debug:
                    print ("{} : data too old by {} seconds".format(el,offset[el]))
                statusdict[name] = 'latest input older than {} sec'.format(usedthreshold)
            else:
                statusdict[name] = 'actual'
    else:
        statusdict[testname] = 'failure'
    cursor.close()

    return statusdict


def dbsize():
    # put that to a interactive command
    #    print ("1. Get initial database information")
    #    print ("-----------------------------------")
    #    dbinfo(db,destination='stdout',level='full')
    pass


def check_logfile(logfilepath, tmpdir='/tmp', statusdict=None, jobname='JOB', testtype='new', logsearchmessage='Error', tolerance=20, debug=False):
    """
    DESCRIPTION:
        read a log file and compare it with a copy in tmp (created in the last call)
    """
    # 1 Read log file
    # 2 Read copy in tmp
    # 3 Compare both files
    # or
    # 4 check for specific messages and occurrences (if not present in last 4 lines -> ignore)
    # 5 Save log to tmp
    if not statusdict:
        statusdict = {}

    def compare(f1,f2):
        diff = []
        with open(f1,'r') as f:
            d=f.readlines()
        with open(f2,'r') as f:
            e=f.readlines()
        lengthdiff = len(d)-len(e)
        if lengthdiff > 0:
            # new log is larger than old log
            # else do not return a difference (because of logrotate)
            diff = d[-lengthdiff:]
        return diff

    def last(f1, lines=None):
        with open(f1,'r') as f:
            d=f.readlines()
        if not lines:
            return d
        if lines and len(d) > lines:
            return d[-lines:]
        elif lines and len(d) < lines:
            return d
        else:
            return d

    testname = "{}-checklog".format(jobname)
    tmplogfilename = "monitor-{}.tmp".format(os.path.basename(logfilepath))
    tmplogfile = os.path.join(tmpdir,tmplogfilename)

    if not os.path.isfile(logfilepath):
        statusdict[testname] = "failed to find logfile"
        return statusdict

    if os.path.isfile(tmplogfile):
        # temporary file existing - running comparison
        res = filecmp.cmp(logfilepath, tmplogfile)
        checkname = "{}-content".format(testname)
        statusdict[checkname] = "log file ok"
        if res:
            if debug:
                print ("Log file did not change")
        else:
            if debug:
                print ("Log file changed")
            diff = compare(logfilepath, tmplogfile)
            if testtype == 'new' and len(diff) > 0:
                statusdict[checkname] = "new content: {}".format(diff[-3:])
            if testtype == 'repeat' and len(diff) > 0:
                # change of file is not important, only content in diff
                # analyse diff
                if len(diff) >= tolerance:
                    testamount = sum([el.find(logsearchmessage) > -1 for el in diff])
                    if testamount >= tolerance:
                        statusdict[checkname] = "CRITICAL: execute script"
        if testtype == 'last':
            # just check last line - independent from changes
            #  REQUIRES logsearchmessage to be success
            lines = last(logfilepath,2)
            if any([el.find(logsearchmessage) > -1 for el in lines]):
                if debug:
                    print ("Fine - found success message")
            else:
                statusdict[checkname] = "Did not find SUCCESS in {}".format(os.path.basename(logfilepath).replace("_",""))
        elif testtype == 'contain':
            # check all lines - independent from changes
            #  REQUIRES logsearchmessage to be success
            lines = last(logfilepath)
            if any([el.find(logsearchmessage) > -1 for el in lines]):
                if debug:
                    print ("Fine - found message {}".format(logsearchmessage))
            else:
                statusdict[checkname] = "Did not find {} in {}".format(logsearchmessage.replace("_",""), os.path.basename(logfilepath).replace("_",""))

    else:
        # Nothing to do ... create log file first
        pass

    # save logfile to tmp
    shutil.copy(logfilepath,tmpdir) # copy the logfile to destination dir
    tmplogtorename = os.path.join(tmpdir,os.path.basename(logfilepath))
    os.rename(tmplogtorename, tmplogfile) # rename

    return statusdict


def execute_script(call,statusdict=None,jobname='JOB',debug=True):
    """
    DESCRIPTION:
        find execute command in statusdict and execute the corresponding script
    """
    if not statusdict:
        statusdict = {}

    testname = "{}-execute".format(jobname)
    if debug:
        print ("Executing script ...")
    subprocess.call(call, shell=True)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    statusdict[testname] = now.strftime('%Y-%m-%d %H:%M')

    return statusdict

def main(argv):
    version = __version__
    statusmsg = {}
    jobs = ''
    joblist = []
    configpath = ''
    jobname = 'MARTASMONITOR'
    hostname = socket.gethostname().upper()
    allowedjobs = ['martas','space','marcos','logfile','datafile']
    debug = False
    travistestrun = False
    #testst = DataStream()
    monitorconf = {'logpath' : '/var/log/magpy/mm-monitor.log',		# path to log file
               'basedirectory' : '/srv', 			# base directory of buffer (MARTAS) and archive (MARCOS)
               'dbcredentials' : 'cobsdb', 			# where to find database credentials
               'defaultthreshold' : '600',  			# accepted age of data in file or database (in seconds)
               'ignorelist' : ['BASELINE','QUAKES','IPS','PIERS','DATAINFO','SENSORS','STATIONS','DIDATA_WIC','FLAGS'],  # sensors not too be checked
               'thresholds' : {'RCS':180000,'TILT':100000,'METEO':10800,'WIC':20000,'GAMMA':10800,'GWR':10800, 'LEMI036_3':180000, 'GSM90_6107632':180000, 'BMP085_10085004':180000, 'SHT75_RASHT004':180000, 'GSM90_7':180000, 'GP20S3EWstatus': 180000}, 		# threshold definitions
               'tmpdir' : '/tmp',			 	# for log file to check
               'logfile' : '/var/log/magpy/marcos.log', 	# log file to check
               'logtesttype' : 'repeat', 			# checks on log file: new, contain, last, repeat
               'logsearchmessage' : 'writeDB: unknown MySQL error when checking for existing tables!',
               'tolerance'  :  20,  				# tolerated amount of repeated messages
               'joblist' : ['space','martas','marcos','logfile'], 			# basic job list (can be space (only disk space), martas (buffer files), marcos (tables), logfile (logfiles)
               'execute'  :  '/path/execute.sh',  		# bash script to be executed if critical error is found (message contains 'execute'), add execution date to log
               'executecriteria'  :  'alternating',  	        # day (every day), week (once per week), alternating (try immidiatly, then one day later, finally one week later),
               'notification'  :  'telegram',  	        	# none,mail,telegram
               'notificationconf' : '/etc/martas/telegram.cfg', # configuration for notification
               'level'   :   3 }


    try:
        opts, args = getopt.getopt(argv,"hc:n:j:vDT",["config=","jobname=","joblist=",])
    except getopt.GetoptError:
        print ('monitor.py -c <config> -n <jobname> -j <joblist> -v <version>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print ('------------------------------------------------------------')
            print ('Description:')
            print ('-- monitor.py to monitor MARTAS/MARCOS machines and logs  --')
            print ('------------------------------------------------------------')
            print ('monitor.py is a python program for testing data actuality,')
            print ('get changes in log files, and get warnings if disk space is')
            print ('getting small.')
            print ('Therefore is is possible to monitor most essential aspects')
            print ('of data acquisition and storage. Besides, monitor.py can ')
            print ('be used to trigger external scripts in case of an observed')
            print ('"CRITICAL: execute script." state.')
            print ('monitor requires magpy >= 2.0.0.')
            print ('Jobs:')
            print ('space    : testing for disk size of basedirectory (i.e. /srv/mqtt or srv/archive)')
            print ('martas   : check for latest file updates in basedirectory and subdirs')
            print ('datafile : check for latest file updates only in basedirectory, not in subdirs')
            print ('marcos   : check for latest timestamp in data tables')
            print ('logfile  : log-test-types are: new or repeat, last, contains;')
            print ('         : new -> logfile has been changed since last run')
            print ('         : repeat -> checks for repeated logsearchmessage in changed logs')
            print ('         :           if more than tolerance then through execute script msg')
            print ('         : last -> checks for logsearchmessage in last two lines')
            print ('         : contains -> checks for logsearchmessage in full logfile')
            print ('-------------------------------------')
            print ('Usage:')
            print ('monitor.py -c <config> -n <jobname> -j <joblist>')
            print ('-------------------------------------')
            print ('Options:')
            print ('-c (required) : path to a configuration file')
            print ('-n            : give a name to the monitoring job')
            print ('-j            : override the joblist in conf')
            print ('-v            : print the current version of monitor.py')
            print ('-------------------------------------')
            print ('Application:')
            print ('python3 monitor.py -c /etc/martas/appconf/monitor.cfg')
            print ('python3 monitor.py -c /etc/martas/appconf/monitor.cfg -n DATABASE -j marcos')
            print ('python3 monitor.py -c /etc/martas/appconf/monitor.cfg -n MARTAS -j martas,space')
            print ('python3 monitor.py -c /etc/martas/appconf/monitor.cfg -n MARCOSLOG -j log')
            print ('python3 monitor.py -c /etc/martas/appconf/monitor.cfg -n AGEOFDATAFILE -j datafile')
            sys.exit()
        elif opt in ("-c", "--config"):
            configpath = arg
        elif opt in ("-n", "--jobname"):
            jobname = arg
        elif opt in ("-j", "--joblist"):
            jobs = arg
        elif opt == "-v":
            print ("monitor.py version: {}".format(version))
        elif opt in ("-D", "--debug"):
            debug = True
        elif opt in ("-T", "--test"):
            travistestrun = True

    # Testing inputs
    # --------------------------------
    if configpath == '':
        # create a config file in /etc/martas/appconf/monitor.cfg
        # use default monitorconf
        joblist = monitorconf.get('joblist')
        if not isinstance(joblist,list):
            joblist = [joblist]
        joblist = _testJobs(joblist,allowedjobs)
    else:
        if os.path.isfile(configpath):
            print ("read file with GetConf")
            monitorconf = mm.get_conf(configpath)
            # directly get the joblist
            joblist = monitorconf.get('joblist')
            if not isinstance(joblist,list):
                joblist = [joblist]
            joblist = _testJobs(joblist,allowedjobs)
        else:
            print ('Specify a valid path to a configuration file')
            print ('-- check monitor.py -h for more options and requirements')
            sys.exit()
    if jobname == '':
        print ('An empty jobname is not allowed - using MARTASMONITOR')
        jobname = 'MARTASMONITOR'
    else:
        jobname = str(jobname)

    if jobs:
        tjoblist = jobs.split(',')
        tjoblist = _testJobs(tjoblist,allowedjobs)
        if tjoblist:
           joblist = tjoblist
    if not joblist:
        print ('Specify a valid job within the joblist of the conf file or dierctly')
        print ('-- check monitor.py -h for more options and requirements')
        sys.exit()

    # Preconfigure logging
    # --------------------------------
    testname = "{}-{}-monitor".format(hostname, jobname)
    logpath = monitorconf.get('logpath')
    if debug:
        print (testname, logpath)

    # Extract configuration data
    # --------------------------------
    receiver = monitorconf.get('notification')
    receiverconf = monitorconf.get('notificationconf')
    basedirectory = monitorconf.get('basedirectory')
    defaultthreshold = int(monitorconf.get('defaultthreshold'))
    ignorelist = monitorconf.get('ignorelist')
    thresholddict = monitorconf.get('thresholds')
    dbcred = monitorconf.get('dbcredentials')
    tmpdir = monitorconf.get('tmpdir')
    logfile = monitorconf.get('logfile')
    logtesttype = monitorconf.get('logtesttype')
    testamount = int(monitorconf.get('tolerance'))
    logsearchmessage = monitorconf.get('logsearchmessage')
    execute = monitorconf.get('execute',None)

    if execute == "/path/execute.sh":
        execute = None

    if not isinstance(ignorelist, list):
        ignorelist = []
    if debug:
        print (receiver, receiverconf, basedirectory, defaultthreshold)
        print (ignorelist)

    # Run the main program
    # --------------------------------
    if debug:
        print ("Running the following jobs: {}".format(joblist))
    try:
        if 'space' in joblist:
            if debug:
                print ("Running space job")
            try:
                spacename = "{}-{}-diskspace".format(hostname,jobname)
                statusmsg[spacename] = getspace(basedirectory)
            except:
                statusmsg['diskspace'] = "Checking disk space failed"
        if 'martas' in joblist:
            if debug:
                print ("Running martas job")
            statusmsg = check_martas(testpath=basedirectory, threshold=defaultthreshold, jobname=jobname, statusdict=statusmsg, ignorelist=ignorelist,thresholddict=thresholddict, debug=debug)
        elif 'datafile' in joblist:
            if debug:
                print ("Running datafile job on {}".format(basedirectory))
            statusmsg = check_datafile(testpath=basedirectory, threshold=defaultthreshold, jobname=jobname, statusdict=statusmsg, ignorelist=ignorelist,thresholddict=thresholddict, debug=debug)
        if 'marcos' in joblist:
            if debug:
                print ("Running marcos job")
            db = mm.connect_db(dbcred)
            statusmsg = check_marcos(db, threshold=defaultthreshold, jobname=jobname, statusdict=statusmsg, excludelist=ignorelist,acceptedoffsets=thresholddict, debug=debug)
        if 'logfile' in joblist:
            if debug:
                print ("Running logfile job on {}".format(logfile))
            statusmsg = check_logfile(logfile, tmpdir=tmpdir, jobname=jobname, statusdict=statusmsg, testtype=logtesttype, logsearchmessage=logsearchmessage, tolerance=testamount, debug=debug)
        if execute:
            # scan statusmessages for execute call
            if any([statusmsg.get(stat).find('CRITICAL: execute script')>-1 for stat in statusmsg]):
                # Found a critical execution message
                if debug:
                    print ("Running execute job")
                statusmsg = execute_script(execute,jobname=jobname, statusdict=statusmsg)

        statusmsg[testname] = "monitoring application running successful"
    except:
        statusmsg[testname] = "error when running monitoring application - please check"

    if debug:
        print (statusmsg)
    else:
        martaslog = ml(logfile=logpath,receiver=receiver)
        martaslog.telegram['config'] = receiverconf
        martaslog.msg(statusmsg)

    print ("----------------------------------------------------------------")
    print ("monitoring app finished")
    print ("----------------------------------------------------------------")
    print ("SUCCESS")
    if travistestrun:
        return True

if __name__ == "__main__":
   main(sys.argv[1:])



"""
# EXAMPLE MONITOR CONFIGURATION FILE CONTENT:
# ###########################################

# path to log file
logpath   :   /var/log/magpy/mm-monitor.log

# base directory of buffer (MARTAS) and archive (MARCOS; or directory to check for file dates
basedirectory   :   /srv

# where to find database credentials
dbcredentials   :   cobsdb

# accepted age of data in file or database (in seconds)
defaultthreshold   :   600

# sensors not too be checked
ignorelist   :   BASELINE,QUAKES,IPS,PIERS,DATAINFO,SENSORS,STATIONS,DIDATA_WIC,FLAGS

# threshold definitions
#thresholds   :   {'RCS':180000,'TILT':100000,'METEO':10800,'WIC':20000,'GAMMA':10800,'GWR':10800, 'LEMI036_3':180000, 'GSM90_6107632':180000, 'BMP085_10085004':180000, 'SHT75_RASHT004':180000, 'GSM90_7':180000, 'GP20S3EWstatus': 180000}

# for log file to check
tmpdir   :   /tmp

# log file to check
logfile   :   /var/log/magpy/marcos.log

# checks on log file: NEW (new input), REPEATed message (if a certain message is repeated more than x times)
logtesttype   :   repeat

logsearchmessage   :   writeDB: unknown MySQL error when checking for existing tables!

# tolerated amount of repeated messages
tolerance   :   20

# basic job list (can be space (only disk space), martas (buffer files), marcos (tables), logfile (logfiles), datafile (age of file in directory)
joblist   :   space,martas,marcos,logfile

# bash script to be executed if critical error is found (message contains 'execute'), add execution date to log
execute   :   /path/execute.sh	

# day (every day), week (once per week), alternating (try immidiatly, then one day later, finally one week later)
executecriteria   :   alternating

# none,mail,telegram
notification   :   telegram

# configuration for notification
notificationconf   :   /etc/martas/telegram.cfg
"""
