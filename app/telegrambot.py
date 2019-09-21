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


Tool for interaction with remote systems:
Commands: external stations: - status, getlog (amount of lines), martas (restart martas), healthstate (disk status, processor), type

Commands: cobs:              - checkDB, get nagios infi

telegrambot.cfg needs to be in the same directory as the bot
"""

from __future__ import print_function
from __future__ import unicode_literals

# Define packges to be used (local refers to test environment) 
# ------------------------------------------------------------
from magpy.stream import *   
from magpy.database import *
import magpy.mpplot as mp
import magpy.opt.cred as mpcred
from magpy.acquisition import acquisitionsupport as acs
from pickle import load as pload
import os
from os import listdir
from os.path import isfile, join
import glob
import subprocess
from subprocess import check_call
import telepot
from telepot.loop import MessageLoop

class tgpar(object):
    logpath = '/var/log/magpy/martas.log'
    tmppath = '/tmp'
    camport = 'None'
    tglogpath = '/var/log/magpy/telegrambot.log'
    version = '1.0.1'

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

stationcommands = {'getlog':'obtain last n lines of a log file\n  Command options:\n  getlog  \n  getlog 10  (last 10 lines)  \n  getlog 10 syslog  (telegrambot, martas, syslog, dmesg)', 
                   'martasrestart':'restart MARTAS process',
                   'martasupdate':'update MARTAS',
                   'status':'get basic information on pc like disk space, memory, usage', 
                   'hello':'say hello, bot', 
                   'system':'get some basic information an the remote system and its software (hardware, magpy version, MARTAS state)', 
                   'switch':'otional: turn on/off remote switches if supported by the hardware (work in progress)', 
                   'plot sensorid':'get diagram of specific sensor by default of the last 24 h \n  Command options:\n  plot sensorid\n  plot sensorid starttime\n  plot sensorid starttime endtime', 
                   'sensors':'get sensors from config and check whether recent buffer data are existing\n  Command options:\n  sensors\n  sensors sensorid  (provides some details on the selected sensor)',
                   'help':'print this list'}


scriptpath = os.path.realpath(__file__)
telegramcfg = os.path.join(os.path.dirname(scriptpath),"telegrambot.cfg")


try:
    tgconf = GetConf(telegramcfg)
    tglogger = setuplogger(name='telegrambot',loglevel=tgconf.get('loglevel'),path=tgconf.get('bot_logging').strip())
    tglogpath = tgconf.get('bot_logging').strip()
    bot_id = tgconf.get('bot_id').strip()
    martasconfig = tgconf.get('martasconfig').strip()
    camport = tgconf.get('camport').strip()
    if not camport=='None':
        stationcommands['cam'] = 'get a picture from the selected webcam\n  Command options:\n  camport (like 0,1)\n  will be extended to /dev/video[0,1]'
    tmppath = tgconf.get('tmppath').strip()
    tgpar.camport = camport
    tgpar.tmppath = tmppath
    tgpar.tglogpath = tglogpath
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
    apppath = conf.get('initdir').replace('init','app')
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
        path = os.path.join(apppath,'ardcomm.py')
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

