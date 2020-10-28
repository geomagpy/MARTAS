
#!/usr/bin/env python
# coding=utf-8

"""
MagPy - telegram bot interaction
################################

Package requirements:
pip install geomagpy (>= 0.3.99)
pip install telepot (>= )

Optional python packages:
pip install psutil    # status memory, cpu
pip install platform  # system definitions

Optional linux packages
sudo apt-get install fswebcam   # getting cam pictures

TODO:

add cronstop to regularly restart the bot (root)
sudo crontab -e
PATH=/bin/sh
0  6  *  *  *  /etc/init.d/telegrambot restart > /dev/NULL 2&>1
0  14  *  *  *  /etc/init.d/telegrambot restart > /dev/NULL 2&>1
0  22  *  *  *  /etc/init.d/telegrambot restart > /dev/NULL 2&>1


# ADD Option to locate configuration file

Tool for interaction with remote systems:
Commands: external stations: - status, getlog (amount of lines), martas (restart martas), healthstate (disk status, processor), type

Commands: cobs:              - checkDB, get nagios infi

telegrambot.cfg needs to be in the same directory as the bot



CHANGES:
Vers 1.0.2:

Additions:
    + added method to obtain last data inputs
Improvements:
    + hidden reboot function modified - should work now

"""

from __future__ import print_function
from __future__ import unicode_literals

# Define packges to be used (local refers to test environment)
# ------------------------------------------------------------
from magpy.stream import *
from magpy.database import *
import magpy.mpplot as mp
import magpy.opt.cred as mpcred
from pickle import load as pload
import re
import os
from os import listdir
from os.path import isfile, join
import glob
import subprocess
from subprocess import check_call
import telepot
from telepot.loop import MessageLoop
import sys, getopt
import glob

# Relative import of core methods as long as martas is not configured as package
scriptpath = os.path.dirname(os.path.realpath(__file__))
coredir = os.path.abspath(os.path.join(scriptpath, '..', 'core'))
sys.path.insert(0, coredir)
import acquisitionsupport as acs

# Default configuration path - modified using options
telegramcfg = os.path.join(os.path.dirname(scriptpath),"telegrambot.cfg")


class tgpar(object):
    logpath = '/var/log/magpy/martas.log'
    marcoslogpath = '/var/log/magpy/marcos.log'
    tmppath = '/tmp'
    camport = 'None'
    tglogpath = '/var/log/magpy/telegrambot.log'
    version = '1.0.3'
    martasapp = '/home/cobs/MARTAS/app'


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
    # Init values:
    confdict = {}
    confdict['bot_id'] = ''
    confdict['tmppath'] = '/tmp'
    confdict['martasfile'] = '/home/cobs/martas.cfg'
    confdict['martaspath'] = '/home/cobs/MARTAS'
    confdict['allowed_users'] = ''
    confdict['camport'] = 'None'
    confdict['logging'] = 'stdout'
    confdict['loglevel'] = 'INFO'

    try:
        config = open(path,'r')
        confs = config.readlines()

        for conf in confs:
            conflst = conf.split('  :  ')
            if conf.startswith('#'):
                continue
            elif conf.isspace():
                continue
            elif len(conflst) == 2:
                conflst = conf.split('  :  ')
                key = conflst[0].strip()
                value = conflst[1].strip()
                confdict[key] = value
    except:
        print ("Problems when loading conf data from file. Using defaults")

    return confdict


def setuplogger(name='telegrambot',loglevel='DEBUG',path='stdout'):

    logpath = None
    try:
        level = eval("logging.{}".format(loglevel))
    except:
        level = logging.DEBUG
    if not path in ['sys.stdout','stdout']:
        logpath = path
    # create formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s : %(message)s',
                              "%Y-%m-%d %H:%M:%S")

    logger = logging.getLogger(name)
    logger.setLevel(level)
    if logpath:
        print ("telegrambot: Creating log file")
        # create file handler which logs even debug messages
        fh = logging.FileHandler(logpath)
        fh.setLevel(level)
        # create console handler with a higher log level
        ch = logging.StreamHandler()
        ch.setLevel(logging.ERROR)
        fh.setFormatter(formatter)
        ch.setFormatter(formatter)
        logger.addHandler(fh)
        logger.addHandler(ch)
    else:
        print ("telegrambot: logging to stdout")
        ch = logging.StreamHandler()
        ch.setLevel(level)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    return logger


if sys.version.startswith('2'):
    vers = '2'
else:
    vers = '3'

"""
Available commands:
"""
#avcommands = {'getmagstat':'statusplot', 'checkDB':'get database information of primary database', 'getgravstat':'get gravity status'}

stationcommands = {'getlog':'obtain last n lines of a log file\n  Command options:\n  getlog  \n  getlog 10  (last 10 lines)  \n  getlog 10 syslog  (telegrambot, martas, syslog, messages)',
                   'martas restart-stop-start':'e.g. restart MARTAS process',
                   'marcos restart-stop-start':'e.g. restart MARCOS process',
                   'martasupdate':'update MARTAS',
                   'status':'get information on disk space, memory, and martas-marcos processes',
                   'hello':'say hello, bot',
                   'getdata':'get sensor data\n Command options:\n  use datetime and sensorid\n  e.g. get data from 2020-11-22 11:22 of LEMI025_22_0003',
                   'system':'get some basic information an the remote system and its software (hardware, magpy version)',
                   'switch':'otional: turn on/off remote switches if supported by the hardware (work in progress)',
                   'plot sensorid':'get diagram of specific sensor by default of the last 24 h \n  Command options:\n  plot sensorid\n  plot sensorid starttime\n  plot sensorid starttime endtime', 
                   'sensors':'get sensors from config and check whether recent buffer data are existing\n  Command options:\n  sensors\n  sensor sensorid or sensors sensorname (provides some details on the selected sensor)',
                   'cam':'get a live picture from a connected camera',
                   'help':'print this list'}

hiddencommands = {'reboot':'reboot the remote computer'}

sensorcommandlist = ['sensors','sensor','Sensors','Sensor'] # any
hellocommandlist = ['hello','Hello'] # any
systemcommandlist = ['System','system'] # any
martascommandlist = ['Martas','martas','MARTAS'] # any
marcoscommandlist = ['Marcos','marcos','MARCOS'] # any
camcommandlist = ['cam','Cam','picture','Picture'] # any
statuscommandlist = ['Status','status','Memory','memory','disk','space','Disk'] # any
getlogcommandlist = ['getlog','get log','get the log', 'print log', 'print the log'] # any
getdatacommandlist = ['data', 'get'] # all
plotcommandlist = ['plot','Plot'] # any
switchcommandlist = ['switch','Switch'] # any
switchcommandoptions = {'swP:0:4' : ['P:0:4','swP:0:4','heating off','pin4 off','off'], 'swP:1:4' : ['P:1:4','swP:1:4','heating on','pin4 on','on'], 'swP:1:5' : ['P:1:5','swP:1:5','pin5 on'], 'swP:0:5' : ['P:0:5','swP:0:5','pin5 on'], 'swD' : ['swD','state','State'] }

try:
    opts, args = getopt.getopt(sys.argv[1:],"hc:",["config="])
except getopt.GetoptError:
    print ('telegrambot.py -c <config>')
    sys.exit(2)
for opt, arg in opts:
    if opt == '-h':
        print ('usage:')
        print ('telegrambot.py -c <config>')
        sys.exit()
    elif opt in ("-c", "--config"):
        telegramcfg = arg

try:
    tgconf = GetConf(telegramcfg)
    tglogger = setuplogger(name='telegrambot',loglevel=tgconf.get('loglevel'),path=tgconf.get('bot_logging').strip())
    tglogpath = tgconf.get('bot_logging').strip()
    bot_id = tgconf.get('bot_id').strip()
    martasconfig = tgconf.get('martasconfig').strip()
    camport = tgconf.get('camport').strip()
    martasapp = tgconf.get('martasapp').strip()
    marcosconfig = tgconf.get('marcosconfig').strip()
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
    print ("error while reading config file or writing to log file - check content and spaces")

try:
    conf = acs.GetConf(martasconfig)
    logpath = '/var/log/syslog'
    if not conf.get('logging').strip() in ['sys.stdout','stdout']:
        logpath = conf.get('logging').strip()
    tgpar.logpath = logpath
    # assume marcoslogpath to be in the same directory
    tgpar.marcoslogpath = os.path.join(os.path.dirname(logpath),'marcos.log')
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
    """
    DESCRIPTION
        provide basic sensorlist and show whether they are active or not
    """
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


def _identifySensor(text):
    """
    DESCRIPTION
        check whether the text contains valid sensorid and returns a list of them
    """
    senslist = []
    if not text:
        return []
    splittext = text.split()
    validsensors = [s.get('sensorid').replace('$','').replace('?','').replace('!','') for s in sensorlist]
    for element in splittext:
        if element in validsensors:
            # found a sensorid in within the text
            senslist.append(element)
    validnames = list(set([s.get('name') for s in sensorlist]))
    for element in splittext:
        if element in validnames:
            # found a sensorname in the text
            correspondingids = [s.get('sensorid').replace('$','').replace('?','').replace('!','') for s in sensorlist if s.get('name') == element]
            if len(correspondingids) > 0:
                for el in correspondingids:
                    senslist.append(el)
    if len(senslist) > 0: # remove duplicates
        senslist = list(set(senslist))
    return senslist


def _identifyDates(text):
    """
    DESCRIPTION
        extract dates from a text
    """
    from dateutil.parser import parse
    try:
        dt = parse(text, fuzzy=True)
    except:
        dt = None
    return dt

def getdata(starttime=None,sensorid=None,interval=60, mean='mean'):
    """
    DESCRIPTION
        get last values of each sensor
    OPTIONS
        startdate (datetime) : define a specific time
        intervals (int) : define an interval to average values (default one minute)
        mean (string)   : type of average (mean, median)
        sensorid (string) : if no sensorid is given all sensors from sensorlist are used
    RETURN
        a dictionary looking like {'SensorID' : {'keys': 't1,t2,var1',
                                                 't1' : {'element': 'T', 'value': 23.31, 'unit': 'deg C'},
                                                 ...
                                                 }
                                   ...
                                  }
    """

    def GetVals(header,key):
         keystr = "col-{}".format(key)
         element = header.get(keystr,'unkown')
         unit = header.get('unit-'+keystr,'arb')
         return element,unit

    if not starttime:
        starttime = datetime.utcnow() - timedelta(seconds=interval)
        endtime = None
    else:
        endtime = starttime + timedelta(seconds=interval)

    senslist = [s.get('sensorid').replace('$','').replace('?','').replace('!','') for s in sensorlist]
    if sensorid and sensorid in senslist:
        senslist = [sensorid]
    returndict = {}
    for s in senslist:
        contentdict = {}
        try:
            data = read(os.path.join(mqttpath,s,'*'),starttime=starttime,endtime=endtime)
            contentdict['keys'] = data._get_key_headers()
            st, et = data._find_t_limits()
            contentdict['starttime'] = st
            contentdict['endtime'] = et
            for key in data._get_key_headers():
                valuedict = {}
                element, unit = GetVals(data.header, key)
                value = data.mean(key)
                valuedict['value'] = value
                valuedict['unit'] = unit
                valuedict['element'] = element
                contentdict[key] = valuedict
            returndict[s] = contentdict
        except:
            # e.g. no readable files
            pass

    return returndict


def tgplot(sensor, starttime, endtime, keys=None):
    """
    DESCRIPTION
       plotting subroutine
    """
    try:
        data = read(os.path.join(mqttpath,sensor,'*'),starttime=starttime, endtime=endtime)
        matplotlib.use('Agg')
        mp.plot(data, confinex=True, outfile=os.path.join(tmppath,'tmp.png'))
        return True
    except:
        return False


def getspace():
    """
    DESCRIPTION
        get some memory information and process status reports
    """
    statvfs = os.statvfs('/home')
    total = (statvfs.f_frsize * statvfs.f_blocks / (1024.*1024.))     # Size of filesystem in bytes
    remain = (statvfs.f_frsize * statvfs.f_bavail / (1024.*1024.))     # Number of free bytes that ordinary users
    mesg = "MEMORY status:\n----------\nDisk-size: {:.0f}MB\nDisk available: {:.0f}MB\nDisk occupied: {:.1f}%".format(total,remain, 100-(remain/total*100.))
    try:
        import psutil
        mem = psutil.virtual_memory()
        cpu = psutil.cpu_percent(interval=1)
        avail = mem.available / (1024*1024)
        total = mem.total / (1024*1024)
        mesg += "\nMemory total: {}MB\nMemory available: {}MB\nCPU usage: {}%".format(total,avail,cpu)
    except:
        pass

    # Status of MARTAS MARCOS jobs
    try:
        mesg += "\n\nMARTAS process(es):\n----------"
        proc = subprocess.Popen(['/etc/init.d/martas','status'], stdout=subprocess.PIPE)
        lines = proc.stdout.readlines()
        if vers=='3':
            lines = [line.decode() for line in lines]
        try:
            # get all collect-* files from init.d
            collectlist = glob.glob('/etc/init.d/collect-*')
            for coll in collectlist:
                proc = subprocess.Popen([coll,'status'], stdout=subprocess.PIPE)
                tmplines = proc.stdout.readlines()
                if vers=='3':
                    tmplines = [line.decode() for line in tmplines]
                lines.extend(tmplines)
        except:
            pass
        mesg += "\n{}".format(''.join(lines))
    except:
        pass

    return mesg


def system():
    """
    DESCRIPTION
        get system information on hardware and software versions
    """
    mesg = ''
    try:
        import platform
        sysls = platform.uname()
        mesg += "System:\n----------\nName: {}\nOperating system: {} ({})\nKernel: {}\nArchitecture: {}".format(sysls[1],sysls[0],sysls[3],sysls[2],sysls[4])
    except:
        pass
    mesg += "\n\nSoftware versions:\n----------\nMagPy Version: {}".format(magpyversion)
    mesg += "\nTelegramBot Version: {}".format(tgpar.version)
    try:
        # get MARTAS version number from logfile
        command = "cat {} | grep 'MARTAS acquisition version' | tail -1 | grep -oE '[^ ]+$'".format(tgpar.logpath)
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
        lines = proc.stdout.readlines()
        if vers=='3':
            lines = [line.decode() for line in lines]
        mesg += "\nMARTAS Version: {}".format(lines[0].strip())
    except:
        pass
    try:
        # get MARCOS version number from logfile
        command = "cat {} | grep 'Starting collector' | tail -1 | grep -oE '[^ ]+$'".format(tgpar.marcoslogpath)
        proc = subprocess.Popen(command, stdout=subprocess.PIPE, shell=True)
        lines = proc.stdout.readlines()
        if vers=='3':
            lines = [line.decode() for line in lines]
        mesg += "\nMARCOS Version: {}".format(lines[0].strip())
    except:
        pass

    return mesg


def tail(f, n=1):
    """
    DESCRIPTION:
        Obtain the last n line of a file f
    """
    mesg = "getlog:\n"
    try:
        num_lines = sum(1 for line in open(f))
        if num_lines < n:
            n = num_lines
        proc = subprocess.Popen(['/usr/bin/tail', '-n', str(n), f], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        lines = proc.stdout.readlines()
        if vers=='3':
            lines = [line.decode() for line in lines]
        mesg += ''.join(lines)
    except:
        mesg += "An error occured - logfile existing?"
    return mesg

def sensorstats(sensorid):
    """
    DESCRIPTION:
       details on sensors
    """
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


def martas(job='martas', command='restart'):
    """
    DESCRIPTION:
       restart martas process
    """
    try:
        # For some reason restart doesn't work?
        tglogger.debug("Sending MARATS call:".format(command))
        call = '/etc/init.d/{} {}'.format(job,command)
        subprocess.call(call, shell=True)
        tglogger.debug("{} sent - getlog for further details".format(command))
        mesg = "Restart command send - check getlog for details (please wait some secs)\n"
    except subprocess.CalledProcessError:
        mesg = "martas: check_call didnt work"
    except:
        mesg = "martas: check_call problem"
    return mesg


def marcos(broker='', command='restart'):
    """
    DESCRIPTION:
        restarting marcos process
    """
    try:
        # For some reason restart doesn't work?
        tglogger.debug("Sending collector call: {}".format(command))
        mesg = ''
        # identify all collector jobs
        collectlist = glob.glob('/etc/init.d/collect-*')
        if broker:
            collectlist = [coll for coll in collectlist if coll.find(broker) > -1]
        if collectlist and len(collectlist)>0:
            for coll in collectlist:
                call = "{} {}".format(coll,command)
                subprocess.call(call, shell=True)
                tglogger.debug("Sent {} - check getlog for details".format(call))
                mesg += "{} command sent to {} - check getlog for further details (please wait some secs)\n".format(command,coll)
    except subprocess.CalledProcessError:
        mesg = "martas: check_call didnt work"
    except:
        mesg = "martas: check_call problem"
    return mesg


def reboot():
    # Rebooting the system
    try:
        tglogger.debug("Rebooting...")
        command = "/sbin/reboot"
        subprocess.call(command, shell = True)
    except subprocess.CalledProcessError:
        mesg = "martas: check_call didnt work"
    except:
        mesg = "martas: check_call problem"
    return mesg


def martasupdate(user='cobs'):
    # update martas from git
    # check_call(['git -C /home/cobs/MARTAS'],['pull'])
    martaspath = tgconf.get('martaspath').strip()
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
    """
    DESCRIPTION
        obtain device call for cam port
    """
    camport = tgpar.camport
    try:
        po = int(re.search(r'\d+', command).group())
        if po < 10:
            camport = "/dev/video{}".format(po)
    except:
        tglogger.warning("No cam port provided or not recognized. Should be 0,1,etc - using default camport from configuration")
    return camport


def switch(command):
    """
    DESCRIPTION
        send switching command to  a connected microcontroller
    """
    try:
        tglogger.debug("Running switch command...")
        python = sys.executable
        #path = '/home/cobs/MARTAS/app/ardcomm.py'
        path = os.path.join(tgpar.martasapp,'ardcomm.py')
        tglogger.debug("tpath: {}".format(path))
        option = '-c'
        call = "{} {} {} {}".format(python,path,option,command)
        tglogger.debug("Call: {}".format(call))
        #print ("Sending", call)
        p = subprocess.Popen(call, stdout=subprocess.PIPE, shell=True)
        (output, err) = p.communicate()
        #print (output)
        if vers == '3':
            output = output.decode()
        mesg = "{}".format(output)
    except subprocess.CalledProcessError:
        mesg = "martas: check_call didnt work"
    except:
        mesg = "martas: check_call problem"
    return mesg


def help(hidden=False):
    """
    DESCRIPTION
        print dictionary of commands
    """
    mesg = ''
    for key in stationcommands:
        mesg += "COMMAND: '/{}'\n".format(key)
        mesg += "{}\n\n".format(stationcommands[key])
    if hidden:
        for key in hiddencommands:
            mesg += "SPECIAL COMMAND: '/{}'\n".format(key)
            mesg += "{}\n\n".format(hiddencommands[key])
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

            if command.find('help') > -1:
               # -----------------------
               # HELP
               # -----------------------
               hidden = False
               if command.replace('help','').find('hidden') > -1:
                   hidden = True
               bot.sendMessage(chat_id, help(hidden=hidden))
            elif any([word in command for word in getlogcommandlist]):
               #command.find('getlog') > -1 or command.find('print log') > -1 or command.find('send log') > -1 or command.find('get log') > -1 or command.find('print the log') > -1 or command.find('get the log') > -1:
               # -----------------------
               # OBTAINNING LOGS
               # -----------------------
               cmd = command.replace('getlog','').replace('print log','').replace('send log','').replace('get log','')
               try:
                   N = int(re.search(r'\d+', cmd).group())
                   cmd = cmd.replace(str(N),'')
               except:
                   N = 10
               if not N:
                   N = 10
               cmd = cmd.strip()
               syslogfiles = ['syslog', 'dmesg', 'messages', 'faillog']
               martaslog = os.path.dirname(tgpar.logpath)
               martaslogfiles = glob.glob(os.path.join(martaslog,'*.log'))
               martaslogfiles = [os.path.basename(ma) for ma in martaslogfiles]
               if len(cmd) > 3: # at least three characters remaining
                   tmpname = cmd
                   for logfile in syslogfiles:
                       if cmd.find(logfile) > -1:
                          tmppath = os.path.join('/var/log', logfile)
                   for logfile in martaslogfiles:
                       if cmd.find(logfile) > -1:
                          tmppath = os.path.join(martaslog, logfile)
                   if cmd.find('telegrambot') > -1:
                       tmppath = tgpar.tglogpath
                   elif cmd.find('martas') > -1:
                       tmppath = tgpar.logpath
                   elif cmd.find('marcos') > -1:
                       tmppath = tgpar.marcoslogpath
                   if os.path.isfile(tmppath):
                       logpath = tmppath
               if os.path.isfile(logpath):
                   tglogger.debug("Checking logfile {}".format(logpath))
                   mesg = tail(logpath,n=N)
               else:
                   mesg = "getlog:\nlogfile not existing"
               bot.sendMessage(chat_id, mesg)
            elif any([word in command for word in statuscommandlist]):
               # -----------------------
               # Status messages on memory and disk space
               # -----------------------
               mesg = getspace()
               bot.sendMessage(chat_id, mesg)
            elif any([word in command for word in systemcommandlist]):
               # -----------------------
               # System information, software versions and martas marcos jobs
               # -----------------------
               mesg = system()
               bot.sendMessage(chat_id, mesg)
            elif any([word in command for word in hellocommandlist]):
               # -----------------------
               # Welcome statement
               # -----------------------
               mesg = "Hello {}, nice to talk to you.".format(firstname)
               bot.sendMessage(chat_id, mesg)
            elif any([word in command for word in camcommandlist]):
               # -----------------------
               # Get cam picture
               # -----------------------
               #cmd = command
               #for word in camcommandlist:
               #    cmd = cmd.replace(word,'')
               #camport = int(re.search(r'\d+', command).group())
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
            elif any([word in command for word in martascommandlist]):
               # -----------------------
               # Send MARTAS process command
               # -----------------------
               bot.sendMessage(chat_id, "Sending acquisition process command...")
               cmd = command.replace('martas','').replace('MARTAS','')
               cmd = cmd.strip()
               if cmd.find('update') > -1:
                   bot.sendMessage(chat_id, "Updating MARTAS ...")
                   rest = cmd.replace('update','').strip().split()
                   user = "cobs"
                   if len(rest) == 1:
                       user = rest[0]
                   mesg = martasupdate(user=user)
                   bot.sendMessage(chat_id, mesg)
               else:
                   commds = ['status', 'restart', 'stop', 'start']
                   for comm in commds:
                       if cmd.find(comm) > -1:
                           rest = cmd.replace(comm,'').strip()
                           job = "martas"
                           if len(rest) > 2:
                               job = rest
                           mesg = martas(job=job,command=comm)
                           break
               bot.sendMessage(chat_id, mesg)
            elif any([word in command for word in marcoscommandlist]):
               # -----------------------
               # Send MARCOS process command
               # -----------------------
               bot.sendMessage(chat_id, "Sending collector process command...")
               cmd = command.replace('marcos','').replace('MARCOS','')
               cmd = cmd.strip()
               commds = ['status', 'restart', 'stop', 'start']
               for comm in commds:
                   if cmd.find(comm) > -1:
                       print ("Found", comm)
                       rest = cmd.replace(comm,'').strip().split()
                       broker = ""
                       if len(rest) == 1:
                           broker = rest[0]
                       mesg = marcos(broker=broker,command=comm)
                       break
               bot.sendMessage(chat_id, mesg)
            elif command =='reboot':
               # -----------------------
               # Send REBOOT command
               # -----------------------
               bot.sendMessage(chat_id, "Rebooting ...")
               mesg = reboot()
               bot.sendMessage(chat_id, mesg)
            elif any([word in command for word in plotcommandlist]):
               # -----------------------
               # Plot data, either recent or from a specific time interval
               # -----------------------
               cmd = command
               for word in plotcommandlist:
                   cmd = cmd.replace(word,'')
               sensoridlist = _identifySensor(cmd)
               if len(sensoridlist) > 1:
                   print ("Too many sensors selected - using only {}".format(sensoridlist[0]))
               elif len(sensoridlist) == 0:
                   bot.sendMessage(chat_id, "You need to specify a sensorid - check 'sensors' to get IDs")
               else:
                   sensorid = sensoridlist[0]
                   cmd = cmd.replace(sensorid,'')
                   # Getting time interval
                   cmd = cmd.split()
                   l = len(cmd)

                   # default start and endtime
                   endtime = datetime.utcnow()
                   starttime = datetime.utcnow()-timedelta(days=1)
                   datelist = []
                   if len(cmd) >=1:
                       for el in cmd:
                           newdate = _identifyDates(el)
                           if newdate:
                               datelist.append(newdate)
                       if len(datelist) > 0:
                           starttime = min(datelist)
                       if len(datelist) > 1:
                           endtime = max(datelist)

                   suc = tgplot(sensorid,starttime,endtime)
                   if suc:
                       bot.sendPhoto(chat_id, open(os.path.join(tmppath,'tmp.png'),'rb'))
                   else:
                       mesg = "Plot could not be created" # tgplot
                       bot.sendMessage(chat_id, mesg)
            elif any([word in command for word in sensorcommandlist]):
               # -----------------------
               # Obtain sensor information and broadcast it
               # -----------------------
               tcmd = command
               for word in sensorcommandlist:
                   tcmd = tcmd.replace(word,'')
               #tcmd = command.replace('sensors','').replace('sensor','').replace('Sensors','')
               cmd = tcmd.split()
               if len(cmd) > 0:
                   # check whether a sensor of the sensorlist is contained in the remaining text
                   mesg = ''
                   sensordict = {}
                   for se in sensorlist:
                       se1 = se.get('sensorid').replace('$','').replace('?','').replace('!','')
                       se2 = se.get('name')
                       sensordict[se1] = se2
                   for el in cmd:
                       if el in sensordict:
                           tglogger.debug("Returning Sensor statistics for {}".format(el))
                           mesg += sensorstats(el)
                       sensorval = list(set([sensordict[ele] for ele in sensordict]))
                       if el in sensorval:
                           # get all ids for this name
                           for ele in sensordict:
                               if sensordict[ele] == el:
                                   tglogger.debug("Returning Sensor statistics for {}".format(ele))
                                   mesg += sensorstats(ele)
                   if mesg == '':
                       mesg = sensors()
               else:
                   mesg = sensors()
               bot.sendMessage(chat_id, mesg)
            elif any([word in command for word in switchcommandlist]):
               # -----------------------
               # Send switch command for mircocontroller
               # -----------------------
               tglogger.info("Switching command received")
               cmd = None
               #if command.find('state') > -1 or command.find('State') > -1:
               #    cmd = 'swD'
               for opt in switchcommandoptions:
                   commlist = switchcommandoptions.get(opt)
                   if any([command.find(word) > -1 for word in commlist]):
                       #print ("Found ", opt)
                       cmd = opt
                       break
               if not cmd:
                   cmd = 'swD'
               tglogger.info(" command extracted: {}".format(len(cmd)))
               mesg = switch(cmd)
               bot.sendMessage(chat_id, mesg)
            elif command.find('data') > -1 and command.find('get') > -1:
               # -----------------------
               # Get data, either recent or from a specific time
               # -----------------------
               def CreateSensorMsg(valdict):
                   mesg = ''
                   for sensor in valdict:
                       mesg += "Sensor: {}\n".format(sensor)
                       contentdict = valdict.get(sensor)
                       keys = contentdict.get('keys')
                       for key in keys:
                           keydict = contentdict.get(key)
                           mesg += "  {}: {} {} (key: {})\n".format(keydict.get('element'),keydict.get('value'),keydict.get('unit',''),key)
                           mesg += "  at {}\n".format(contentdict.get('starttime').strftime("%Y-%m-%d %H:%M:%S") )
                   return mesg

               tglogger.info("Got a data request")
               cmd = command.replace('data','').replace('get','')
               cmdsplit = cmd.split()
               mesg = "Data:\n-----------\n"
               if len(cmdsplit) > 0:
                   sensoridlist = _identifySensor(cmd)
                   for sensorid in sensoridlist:
                       cmd = cmd.replace(sensorid,'')
                   starttime = _identifyDates(cmd) # dates is a list
                   for sensorid in sensoridlist:
                       valdict = getdata(sensorid=sensorid,starttime=starttime)
                       mesg += CreateSensorMsg(valdict)
               else:
                   valdict = getdata()
                   mesg += CreateSensorMsg(valdict)
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

