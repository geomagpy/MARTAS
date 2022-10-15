
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

PROXY: add proxy in configuration file - currently it is hardcoded

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

Vers 1.0.3:

Additions:
    + added data request
Improvements:
    + running in py3
    + generalized all methods
    + prepared communication function with word lists
    + testet all methods except (TODO): reboot, martas update, cam

Vers 1.0.4:

Additions:
    + added getip request
    + added upload request
    + added cam options support

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
    version = '1.0.4'
    martasapp = '/home/cobs/MARTAS/app'
    purpose = 'MARTAS'


def GetConf(path, confdict={}):
    """
    Version 2020-10-28
    DESCRIPTION:
       can read a text configuration file and extract lists and dictionaries
    VARIBALES:
       path             Obvious
       confdict         provide default values
    SUPPORTED:
       key   :    stringvalue                                 # extracted as { key: str(value) }
       key   :    intvalue                                    # extracted as { key: int(value) }
       key   :    item1,item2,item3                           # extracted as { key: [item1,item2,item3] }
       key   :    subkey1:value1;subkey2:value2               # extracted as { key: {subkey1:value1,subkey2:value2} }
       key   :    subkey1:value1;subkey2:item1,item2,item3    # extracted as { key: {subkey1:value1,subkey2:[item1...]} }
    """
    exceptionlist = ['bot_id']

    def is_number(s):
        try:
            float(s)
            return True
        except ValueError:
            return False

    try:
        config = open(path,'r')
        confs = config.readlines()
        for conf in confs:
            conflst = conf.split(':')
            if conflst[0].strip() in exceptionlist or is_number(conflst[0].strip()):
                # define a list where : occurs in the value and is not a dictionary indicator
                conflst = conf.split(':',1)
            if conf.startswith('#'):
                continue
            elif conf.isspace():
                continue
            elif len(conflst) == 2:
                conflst = conf.split(':',1)
                key = conflst[0].strip()
                value = conflst[1].strip()
                # Lists
                if value.find(',') > -1:
                    value = value.split(',')
                    value = [el.strip() for el  in value]
                try:
                    confdict[key] = int(value)
                except:
                    confdict[key] = value
            elif len(conflst) > 2:
                # Dictionaries
                if conf.find(';') > -1 or len(conflst) == 3:
                    ele = conf.split(';')
                    main = ele[0].split(':')[0].strip()
                    cont = {}
                    for el in ele:
                        pair = el.split(':')
                        # Lists
                        subvalue = pair[-1].strip()
                        if subvalue.find(',') > -1:
                            subvalue = subvalue.split(',')
                            subvalue = [el.strip() for el  in subvalue]
                        try:
                            cont[pair[-2].strip()] = int(subvalue)
                        except:
                            cont[pair[-2].strip()] = subvalue
                    confdict[main] = cont
                else:
                    print ("Subdictionary expected - but no ; as element divider found")
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
                   'cam':'get a live picture from a connected camera using fswebcam\n  fswebcam options need to be defined in telegrambot.cfg',
                   'getip':'get the IP of network interfaces like eth0 and wlan0.\n Command options:\n add interface to search for like\ngetip eth1, eth2',
                   'upload':'upload data tp a remote machine using the MARTAS app file_upload and configuration data as defined in telegrambot.cfg',
                   'figure1':'open a preconfigured figure',
                   'figure2':'open an alternative figure',
                   'help':'print this list'}

travistestrun = False

hiddencommands = {'reboot':'reboot the remote computer'}

commandlist = {}
commandlist['sensor'] = {'commands': ['sensors','sensor','Sensors','Sensor'], 'combination' : 'any'}
commandlist['hello'] = {'commands': ['hello','Hello'], 'combination' : 'any'}
commandlist['imbot'] = {'commands': ['imbot','IMBOT'], 'combination' : 'any'}

commandlist['system'] = {'commands': ['System','system'], 'combination' : 'any'}
commandlist['martas'] = {'commands': ['Martas','martas','MARTAS'], 'combination' : 'any'}
commandlist['marcos'] = {'commands': ['Marcos','marcos','MARCOS'], 'combination' : 'any'}
commandlist['cam'] = {'commands': ['cam','Cam','picture','Picture','photo'], 'combination' : 'any'}
commandlist['status'] = {'commands': ['Status','status','Memory','memory','disk','space','Disk'], 'combination' : 'any'}
commandlist['upload'] = {'commands': ['upload','send data','Upload', 'nach Hause telefonieren'], 'combination' : 'any'}
commandlist['getip'] = {'commands': ['getIP',' IP ', 'IP ','getip'], 'combination' : 'any'}
commandlist['getlog'] = {'commands': ['getlog','get log','get the log', 'print log', 'print the log'], 'combination' : 'any'}
commandlist['getdata'] = {'commands': ['data'], 'combination' : 'any'}
commandlist['plot'] = {'commands': ['plot','Plot'], 'combination' : 'any'}
commandlist['switch'] = {'commands': ['switch','Switch'], 'combination' : 'any' ,'options' : {'swP:0:4' : ['P:0:4','swP:0:4','heating off','pin4 off','off'], 'swP:1:4' : ['P:1:4','swP:1:4','heating on','pin4 on','on'], 'swP:1:5' : ['P:1:5','swP:1:5','pin5 on'], 'swP:0:5' : ['P:0:5','swP:0:5','pin5 on'], 'swD' : ['swD','state','State'] }}
commandlist['badwords'] = {'commands': ['fuck','asshole'], 'combination' : 'any'}
#switchcommandoptions = {'swP:0:4' : ['P:0:4','swP:0:4','heating off','pin4 off','off'], 'swP:1:4' : ['P:1:4','swP:1:4','heating on','pin4 on','on'], 'swP:1:5' : ['P:1:5','swP:1:5','pin5 on'], 'swP:0:5' : ['P:0:5','swP:0:5','pin5 on'], 'swD' : ['swD','state','State'] }
#badwordcommands = ['fuck','asshole']
commandlist['figure1'] = {'commands': ['figure1','Figure1','fig1','Fig1'], 'combination' : 'any'}
commandlist['figure2'] = {'commands': ['figure2','Figure2','fig2','Fig2'], 'combination' : 'any'}



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
    opts, args = getopt.getopt(sys.argv[1:],"hc:T",["config=","Test="])
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
    elif opt in ("-T", "--Test"):
        travistestrun = True
        telegramcfg = 'telegrambot.cfg'


try:
    proxy = ''
    tgconf = GetConf(telegramcfg, confdict=confdict)
    tglogger = setuplogger(name='telegrambot',loglevel=tgconf.get('loglevel'),path=tgconf.get('bot_logging').strip())
    if travistestrun:
        tglogger = setuplogger(name='telegrambot',loglevel='DEBUG',path='stdout')
    tglogpath = tgconf.get('bot_logging').strip()
    bot_id = tgconf.get('bot_id').strip()
    purpose = tgconf.get('purpose')
    martasconfig = tgconf.get('martasconfig').strip()
    if martasconfig:
        martasconfig = martasconfig.strip()
    camport = tgconf.get('camport').strip()
    if camport:
        camport = camport.strip()
    martasapp = tgconf.get('martasapp')
    if martasapp:
        martasapp = martasapp.strip()
    martaspath = tgconf.get('martaspath')
    marcosconfig = tgconf.get('marcosconfig')
    if marcosconfig:
        marcosconfig = marcosconfig.strip()
    proxy = tgconf.get('proxy')
    if proxy:
        proxy = proxy.strip()
    proxyport = tgconf.get('proxyport')

    if proxy:
        print (" found proxy")
        import urllib3
        proxy_url="http://{}:{}".format(proxy,proxyport)
        telepot.api._pools = {'default': urllib3.ProxyManager(proxy_url=proxy_url, num_pools=3, maxsize=10, retries=False, timeout=30),}
        telepot.api._onetime_pool_spec = (urllib3.ProxyManager, dict(proxy_url=proxy_url, num_pools=1, maxsize=1, retries=False, timeout=30))
        print (" ... established to {}".format(proxy_url))

    # Extract command lists
    for command in stationcommands:
        tglogger.debug("Checking for alternative commands for {}".format(command))
        try:
            comlst = [el for el in tgconf.get(command,[]) if not el=='']
            if len(comlst) > 0:
                commandlist[command].get('commands').extend(comlst)
        except:
            pass
    if not camport=='None':
        stationcommands['cam'] = 'get a picture from the selected webcam\n  Command options:\n  camport (like 0,1)\n  will be extended to /dev/video[0,1]'
    tmppath = tgconf.get('tmppath').strip()
    tgpar.camport = camport
    tgpar.tmppath = tmppath
    tgpar.tglogpath = tglogpath
    tgpar.martasapp = martasapp
    tgpar.uploadconfig = tgconf.get('uploadconfig',"").strip()
    tgpar.uploadmemory = tgconf.get('uploadmemory',"").strip()
    tgpar.camoptions = tgconf.get('camoptions',"").strip()
    if purpose:
        tgpar.purpose = purpose
    allusers = tgconf.get('allowed_users')
    if isinstance(allusers, list):
        allowed_users =  [str(el) for el in allusers]
    else:
        allowed_users =  [str(tgconf.get('allowed_users'))]
    tglogger.debug('Successfully obtained parameters from telegrambot.cfg')
except:
    print ("error while reading config file or writing to log file - check content and spaces")

if tgpar.purpose in ['martas','Martas','MARTAS']:
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
    #print ("Configuration (martas.cfg) could not be extracted - aborting")
    if not travistestrun:
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

    # For old parse date versions
    def hasNumbers(inputString):
        return any(char.isdigit() for char in inputString)
    if not hasNumbers(text):
        return None

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
            print (s, data.length(), starttime, endtime)
            contentdict['keys'] = data._get_key_headers()
            st, et = data._find_t_limits()
            contentdict['starttime'] = st
            contentdict['endtime'] = et
            print ("here", st, et)
            for key in data._get_key_headers():
                print (key)
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

    return mesg

def jobprocess(typ='MARTAS'):
    # Status of MARTAS MARCOS jobs
    lines = []
    print (" -checking {}".format(typ))
    if typ in ['martas','Martas','MARTAS']:
        try:
            mesg = "MARTAS process(es):\n----------"
            proc = subprocess.Popen(['/etc/init.d/martas','status'], stdout=subprocess.PIPE)
            lines = proc.stdout.readlines()
        except:
            pass
    elif typ in ['marcos','Marcos','MARCOS']:
        try:
            mesg = "MARCOS process(es):\n----------"
            # get all collect-* files from init.d
            collectlist = glob.glob('/etc/init.d/collect-*')
            for coll in collectlist:
                proc = subprocess.Popen([coll,'status'], stdout=subprocess.PIPE)
                tmplines = proc.stdout.readlines()
                lines.extend(tmplines)
        except:
            pass
    else:
        mesg = "{} process(es):\n----------".format(typ)
        lines = ['Requested job type','is not yet supported']
    try:
        if vers=='3':
           lines = [line.decode() for line in lines]
    except:
        pass

    mesg += "\n{}".format(''.join(lines))

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

def upload():
    """
    DESCRIPTION:
        Command for uploading data using file_upload and the given configuration file
    """
    configpath = tgpar.uploadconfig
    memorypath = tgpar.uploadmemory
    if not memorypath:
         memorypath = "/tmp/martas_tgupload_memory.json"
    python = sys.executable
    path = os.path.join(tgpar.martasapp,'file_upload.py')
    optioncfg = '-j'
    optionmem = '-m'
    try:
        if configpath:
            call = "{} {} {} {} {} {}".format(python,path,optioncfg,configpath,optionmem,memorypath)
            tglogger.debug("Uploading data by calling {}".format(call))
            p = subprocess.Popen(call, stdout=subprocess.PIPE, shell=True)
            (output, err) = p.communicate()
            if vers=='3':
                output = output.decode()
            if output.find("not succesful") > 0:
                mesg  = "upload apparently failed"
            elif output.find("SUCCESS") > 0:
                mesg  = "upload apparently successfully"
            else:
                mesg  = "upload obviously failed"
        else:
            tglogger.debug("Upload command deactivated as no configuration is provided")
    except subprocess.CalledProcessError:
        mesg = "upload: check_call didnt work"
    except:
        mesg = "upload: check_call problem"
    return mesg

def getip(interfacelist=["eth0","wlan0"]):
    """
    DESCRIPTION:
        Getting th
    """
    mesg = "IP(s):\n"
    try:
        for interface in interfacelist:
            call = r"ifconfig {} | sed -En 's/127.0.0.1//;s/.*inet (addr:)?(([0-9]*\.){}[0-9]*).*/\2/p'".format(interface,"{3}")
            tglogger.debug("Requesting IP for {}:".format(interface))
            tglogger.debug("call: {}".format(call))
            p = subprocess.Popen(call, stdout=subprocess.PIPE, shell=True)
            (output, err) = p.communicate()
            if vers=='3':
                output = output.decode()
            if output.startswith("1"):
                mesg += "{}: {}".format(interface, output)
        if mesg == "IP(s):\n":
            mesg = "Did not find a valid IP address - search on a specific interface: getip eth1"
    except subprocess.CalledProcessError:
        mesg = "getip: check_call didnt work"
    except:
        mesg = "getip: check_call problem"
    return mesg

def reboot():
    """
    DESCRIPTION:
        Rebooting the system
    """
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
        if vers=='3':
            output = output.decode()
        mesg += "\n{}".format(output)
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

    if not str(chat_id) in allowed_users:
        bot.sendMessage(chat_id, "My mother told me not to speak to strangers, sorry...")
        tglogger.warning('--------------------- Unauthorized access -------------------------')
        tglogger.warning('!!! unauthorized access ({}) from ChatID {} (User: {}) !!!'.format(command,chat_id,firstname))
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
            elif any([word in command for word in commandlist['badwords'].get('commands')]):
               # -----------------------
               # JUST FOR FUN
               # -----------------------
               text = "Don't be rude.\nI am just a stupid program, not even an AI\n"
               bot.sendMessage(chat_id, text)
            elif any([word in command for word in commandlist['getlog'].get('commands')]):
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
            elif any([word in command for word in commandlist['status'].get('commands')]):
               # -----------------------
               # Status messages on memory and disk space
               # -----------------------
               mesg = getspace()
               bot.sendMessage(chat_id, mesg)
               mesg = jobprocess(typ=tgpar.purpose)
               bot.sendMessage(chat_id, mesg)
            elif any([word in command for word in commandlist['system'].get('commands')]):
               # -----------------------
               # System information, software versions and martas marcos jobs
               # -----------------------
               mesg = system()
               bot.sendMessage(chat_id, mesg)
            elif any([word in command for word in commandlist['hello'].get('commands')]):
               # -----------------------
               # Welcome statement
               # -----------------------
               mesg = "Hello {}, nice to talk to you.".format(firstname)
               bot.sendMessage(chat_id, mesg)
            elif any([word in command for word in commandlist['cam'].get('commands')]):
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
                       if tgpar.camoptions:
                           camoptions = tgpar.camoptions
                       else:
                           camoptions = ""
                       call = "/usr/bin/fswebcam -d {} {} {}".format(usedcamport, camoptions, os.path.join(tmppath,'webimage.jpg'))
                       subprocess.call(call)
                       tglogger.debug("Subprocess for image creation finished")
                       bot.sendPhoto(chat_id, open(os.path.join(tmppath,'webimage.jpg'),'rb'))
                   except:
                       mesg = "Cam image not available (fswebcam properly installed?)"
                       bot.sendMessage(chat_id, mesg)
            elif any([word in command for word in commandlist['figure1'].get('commands')]):
               # -----------------------
               # Send a figure
               # -----------------------
               bot.sendPhoto(chat_id, open(tgconf.get('fig1'),'rb'))
            elif any([word in command for word in commandlist['figure2'].get('commands')]):
               # -----------------------
               # Send a figure
               # -----------------------
               bot.sendPhoto(chat_id, open(tgconf.get('fig2'),'rb'))
            elif any([word in command for word in commandlist['imbot'].get('commands')]):
               # -----------------------
               # Send MARTAS process command
               # -----------------------
               bot.sendMessage(chat_id, "Sending result request to IMBOT...")
               cmd = command.replace('martas','').replace('MARTAS','')
               cmd = cmd.strip()
               yearl = re.findall(r'\d+', cmd)
               if len(yearl) > 0:
                   command = "/usr/bin/python3 /home/pi/Software/IMBOT/imbot/quickreport.py -m /srv/DataCheck/analysis{a}.json -l /srv/DataCheck/IMBOT/{a}/level".format(a=yearl[-1])
               else:
                   command = "/usr/bin/python3 /home/pi/Software/IMBOT/imbot/quickreport.py -m /srv/DataCheck/analysis2020.json -l /srv/DataCheck/IMBOT/2020/level"
               #subprocess.call([command])
               os.system(command)
            elif any([word in command for word in commandlist['martas'].get('commands')]):
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
                   if 'user' in rest:
                       idx = rest.index('user')
                       if len(rest) > idx:
                           user = rest[idx+1]
                   elif len(rest) == 1:
                       user = rest[0]
                   #print ("Updating for user {}".format(user))
                   mesg = martasupdate(user=user)
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
            elif any([word in command for word in commandlist['marcos'].get('commands')]):
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
            elif any([word in command for word in commandlist['upload'].get('commands')]):
               # -----------------------
               # Send upload  command
               # -----------------------
               bot.sendMessage(chat_id, "Obtained an upload data request ...")
               cmd = command.split(" ")
               mesg = upload()
               bot.sendMessage(chat_id, mesg)
            elif any([word in command for word in commandlist['getip'].get('commands')]):
               # -----------------------
               # Send GET IP  command
               # -----------------------
               bot.sendMessage(chat_id, "Requesting IP address...")
               cmd = command.split(" ")
               interfacelist = []
               for el in cmd:
                   el = el.strip()
                   if el in ['eth0','eth1','eth2','eth3','wlan0','wlan1','wlan2','usb0','usb1','usb2','usb3','lo','wlp4s0']:
                       interfacelist.append(el)
               if not interfacelist:
                   interfacelist = ['eth0','wlan0','wlp4s0']
               mesg = getip(interfacelist)
               bot.sendMessage(chat_id, mesg)
            elif command =='reboot':
               # -----------------------
               # Send REBOOT command
               # -----------------------
               bot.sendMessage(chat_id, "Rebooting ...")
               mesg = reboot()
               bot.sendMessage(chat_id, mesg)
            elif any([word in command for word in commandlist['plot'].get('commands')]):
               # -----------------------
               # Plot data, either recent or from a specific time interval
               # -----------------------
               cmd = command
               for word in commandlist['plot'].get('commands'):
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
            elif any([word in command for word in commandlist['sensor'].get('commands')]):
               # -----------------------
               # Obtain sensor information and broadcast it
               # -----------------------
               tcmd = command
               for word in commandlist['sensor'].get('commands'):
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
            elif any([word in command for word in commandlist['switch'].get('commands')]):
               # -----------------------
               # Send switch command for mircocontroller
               # -----------------------
               tglogger.info("Switching command received")
               cmd = None
               #if command.find('state') > -1 or command.find('State') > -1:
               #    cmd = 'swD'
               switchcommandoptions = commandlist['switch'].get('options')
               for opt in switchcommandoptions:
                   commlist = switchcommandoptions.get(opt)
                   #print ("Test", opt, commlist)
                   if any([command.find(word) > -1 for word in commlist]):
                       #print ("Found ", opt)
                       cmd = opt
                       break
               if not cmd:
                   cmd = 'swD'
               tglogger.info(" command extracted: {}".format(cmd))
               mesg = switch(cmd)
               bot.sendMessage(chat_id, mesg)
            elif any([word in command for word in commandlist['getdata'].get('commands')]):
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
                   #tglogger.info("  found sensors: {}".format(sensoridlist))
                   for sensorid in sensoridlist:
                       cmd = cmd.replace(sensorid,'')
                   starttime = _identifyDates(cmd) # dates is a list
                   for sensorid in sensoridlist:
                       valdict = getdata(sensorid=sensorid,starttime=starttime)
                       #tglogger.info("  got values ...")
                       #if debug:
                       #    print ("VALDICT", valdict)
                       mesg += CreateSensorMsg(valdict)
               else:
                   valdict = getdata()
                   mesg += CreateSensorMsg(valdict)
               bot.sendMessage(chat_id, mesg)

if travistestrun:
    print ("Test run successfully finished - existing")
    sys.exit(0)

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
