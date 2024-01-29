
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
       key   :    item1,item2,it                       'martasupdate': {'commands': ['martasupdate'],
                                   'combination' : 'any',
                                   'priority' : 1,
                                   'availability': ['hidden'],
                                   'description': 'update MARTAS'}
em3                           # extracted as { key: [item1,item2,item3] }
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


class telegrambot(object):
    """
    DESCRIPTION
        telegrambot class
    METHODS

    APPLICATION
    """

    def __init__(self, configsource=None, commandsource=None, debug=False):
        # set some general parameters
        # read a "interpretation" dictionary from a file
        commanddict = self.set_default_commands()
        configuration = self.set_default_configuration()
        self.debug = debug
        # Now combine defauls with constructors provided
        if configsource:
            if debug:
                 print ("Reading configuration")
            configuration = GetConf(configsource, confdict=configuration)
        if debug:
            print ("Configuration:")
            print (configuration)
        # PLEASE NOTE: CONFIG should replace or extend contents of default dictionaries, not the whole dic
        self.configuration = configuration
        self.commanddict = commanddict
        self.logger = self.logger_setup(name==configuration.get('logname','telegrambot'),loglevel=configuration.get('loglevel','INFO'),path=configuration.get('logging','stdout'))
        self.inputcounter = 0
        self.quest = False
        self.cvals = {}

        #if configuration.get('purpose') in ['martas','Martas','MARTAS']:
        #    configuration = self.init_martas(configuration)


    def set_default_configuration():
        """
        DESCRIPTION
            some defaults for configuration parameters
        """
        config = {}
        config['logpath'] = '/var/log/magpy/martas.log'
        config['marcoslogpath'] = '/var/log/magpy/marcos.log'
        config['tmppath'] = '/tmp'
        config['camport'] = 'None'
        config['tglogpath'] = '/var/log/magpy/telegrambot.log'
        config['version'] = '1.0.3'
        config['martasapp'] = '/home/cobs/MARTAS/app'
        config['purpose'] = 'MARTAS'

        config['bot_id'] = ''
        config['tmppath'] = '/tmp'
        config['martasfile'] = '/home/cobs/martas.cfg'
        config['martaspath'] = '/home/cobs/MARTAS'
        config['allowed_users'] = ''
        config['camport'] = 'None'
        config['logname'] = 'telegrambot'
        config['logging'] = 'stdout'
        config['loglevel'] = 'INFO'
        config['travistestrun' = False
        return config

    def set_default_commands(self):
        """
        DESCRIPTION
            some defaults for configuration parameters
        """
        
        commanddict = {'hello' :  {'commands': ['hello','Hello'],
                                   'combination' : 'any',
                                   'priority' : 1,
                                   'method' : 'hello',
                                   'availability': ['all'],
                                   'description': 'say hello, bot'},
                       'help'  :  {'commands': ['help','Help'],
                                   'combination' : 'any',
                                   'priority' : 1,
                                   'availability': ['all'],
                                   'description': 'print descriptions'},
                       'sensor' : {'commands': ['sensors','sensor','Sensors','Sensor'],
                                   'combination' : 'any',
                                   'priority' : 1,
                                   'options' : {'variable':True},
                                   'availability': ['MARTAS'],
                                   'description': 'get sensors from config and check whether recent buffer data are existing\n  Command options:\n  sensors\n  sensor sensorid or sensors sensorname (provides some details on the selected sensor)'},
                       'imbot' :  {'commands': ['imbot','IMBOT'],
                                   'availability': ['IMBOT'],
                                   'priority' : 1,
                                   'options' : {'variable':True},
                                   'combination' : 'any',
                                   'description': 'get some IMBOT status messages:'},
                       'system' : {'commands': ['System','system'], 
                                   'availability': ['all'],
                                   'combination' : 'any',
                                   'priority' : 1,
                                   'description': 'get some basic information an the remote system and its software (hardware, magpy version)'},
                       'martas' : {'commands': ['Martas','martas','MARTAS'], 
                                   'combination' : 'any',
                                   'availability': ['MARTAS'],
                                   'priority' : 1,
                                   'options' : {'restart':['restart'],'start':['start'],'stop':['stop'],'status':['status']},
                                   'description': 'restart-stop-start : e.g. restart MARTAS process'},
                       'marcos' : {'commands': ['Marcos','marcos','MARCOS'], 
                                   'combination' : 'any',
                                   'availability': ['MARCOS'],
                                   'priority' : 1,
                                   'options' : {'restart':['restart'],'start':['start'],'stop':['stop'],'status':['status']},
                                   'description': 'restart-stop-start : e.g. restart MARCOS processes'},
                       'cam' :    {'commands': ['cam','Cam','picture','Picture','photo'],
                                   'combination' : 'any',
                                   'priority' : 1,
                                   'options' : {'device':True},
                                   'availability': ['all'],
                                   'description': 'get a live picture from a connected camera'},
                       'status' : {'commands': ['Status','status','Memory','memory','disk','space','Disk'],
                                   'combination' : 'any',
                                   'priority' : 1,
                                   'availability': ['all'],
                                   'description': 'get information on disk space, memory, and martas-marcos processes'},
                       'getlog' : {'commands': ['getlog','get log','get the log', 'print log', 'print the log'],
                                   'combination' : 'any',
                                   'priority' : 1,
                                   'options' : {'logfile':True},
                                   'availability': ['all'],
                                   'description': 'obtain last n lines of a log file\n  Command options:\n  getlog  \n  getlog 10  (last 10 lines)  \n  getlog 10 syslog  (telegrambot, martas, syslog, messages)'},
                       'getdata': {'commands': ['data'],
                                   'combination' : 'any',
                                   'priority' : 1,
                                   'options' : {'variable':True},
                                   'availability': ['MARTAS'],
                                   'description': 'get sensor data\n Command options:\n  use datetime and sensorid\n  e.g. get data from 2020-11-22 11:22 of LEMI025_22_0003'},
                       'plot' :   {'commands': ['plot','Plot'],
                                   'combination' : 'any',
                                   'priority' : 1,
                                   'options' : {'variable':True},
                                   'availability': ['MARTAS'],
                                   'description': 'provide sensorid : get diagram of specific sensor by default of the last 24 h \n  Command options:\n  plot sensorid\n  plot sensorid starttime\n  plot sensorid starttime endtime'},
                       'switch' : {'commands': ['switch','Switch'],
                                   'combination' : 'any',
                                   'priority' : 1,
                                   'availability': ['MARTAS'],
                                   'options' : {'swP:0:4' : ['P:0:4','swP:0:4','heating off','pin4 off','off'], 'swP:1:4' : ['P:1:4','swP:1:4','heating on','pin4 on','on'], 'swP:1:5' : ['P:1:5','swP:1:5','pin5 on'], 'swP:0:5' : ['P:0:5','swP:0:5','pin5 on'], 'swD' : ['swD','state','State'] },
                                   'description': 'otional: turn on/off remote switches if supported by the hardware (work in progress)'},
                       'badwords':{'commands': ['fuck','asshole'],
                                   'combination' : 'any'
                                   'priority' : 1,
                                   'availability': ['hidden'],
                                   'description': ''},
                       'figure1': {'commands': ['figure1','Figure1','fig1','Fig1'],
                                   'combination' : 'any',
                                   'priority' : 1,
                                   'availability': ['all'],
                                   'description': 'open a preconfigured figure'}
                       'figure2': {'commands': ['figure2','Figure2','fig2','Fig2'],
                                   'combination' : 'any',
                                   'priority' : 1,
                                   'availability': ['all'],
                                   'description': 'open a preconfigured figure'},
                       'reboot': {'commands': ['reboot'],
                                   'combination' : 'any',
                                   'priority' : 1,
                                   'availability': ['hidden'],
                                   'description': 'reboot the remote computer'},
                       'martasupdate': {'commands': ['martasupdate'],
                                   'combination' : 'any',
                                   'priority' : 1,
                                   'availability': ['hidden'],
                                   'description': 'update MARTAS'}
        }
        return commanddict


    def init_martas(self, config={}):
        """
        DESCRIPTION
            special init for martas machine
            -> reads martas config files (martas.cfg and sensors.cfg)
        APPLICATION:
            at the end of general init (after logger)
        """
        #if tgpar.purpose in ['martas','Martas','MARTAS']:
        # requires the GetConf function 
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
            #TODO
            # add sensorlist and paths to confiuration dic
        except:
            #print ("Configuration (martas.cfg) could not be extracted - aborting")
        if not travistestrun:
            tglogger.warning("Configuration (martas.cfg) could not be extracted - aborting")
            sys.exit()
        return configuration
    

    def read_interpreter(self, path):
        """
        DESCRIPTION
            reads a interpretation dictionary from file
        """
        pass

    def logger_setup(self, name='telegrambot', loglevel='DEBUG', path='stdout'):

        logpath = None
        try:
            level = eval("logging.{}".format(loglevel))
        except:
            level = logging.DEBUG

        if not path in ['sys.stdout', 'stdout']:
            logpath = path
        # create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s : %(message)s',
                                      "%Y-%m-%d %H:%M:%S")

        logger = logging.getLogger(name)
        logger.setLevel(level)
        if logpath:
            print("telegrambot: Creating log file")
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
            print("telegrambot: logging to stdout")
            ch = logging.StreamHandler()
            ch.setLevel(level)
            ch.setFormatter(formatter)
            logger.addHandler(ch)

        return logger

    def command(self, bot, command, chat_id, firstname=None):
        """
        DESCRIPTION
            send a command to the bot and return a message
        REQUIRES
            self.configuration
            self.interpreter
        APPLICATION
            the main program just
        """
        # identify command in command-dict and obtain possible options
        joblist = []
        message = ''
        if self.debug:
            print(self.commanddict)
        for elem in self.commanddict:
            jobdic = self.commanddict.get(elem)
            jobname = elem
            jobpriority = jobdic.get('priority', 0)
            jobcommands = jobdic.get('commands', [jobname])
            jobcombination = jobdic.get('combination', 'any')
            #  if command is found in one of the commandlists then add this job to a list
            if jobcombination == 'any':
                if any([word in command for word in jobcommands]):
                    # sort according to priority
                    joblist.append([jobpriority, jobname, jobdic])

        if self.debug:
            print("Found command", joblist)
            print("Inputcounter", self.inputcounter)
            print("quest", self.quest)

        # then call the appropriate method to execute the command
        if len(joblist) > 0:
            # Found the job
            # select the last one (with highest priority)
            activejob = joblist[-1]
            activename = activejob[1]
            activedic = activejob[-1]
            activedic['call'] = command  # add this to extract options from call
            activedic['chat_id'] = chat_id  # add this
            activedic['firstname'] = firstname  # add this
            message = self.run_command(activename, activedic)
            if self.debug:
                print("Message", message)
            # message consists of message['text'] = [''], message['pictures'] = ['list od paths'], message['commands'] = shell script to execute etc
            if message.get('text'):
                text = message.get('text')
                bot.sendMessage(chat_id, text, parse_mode='Markdown')
            if message.get('pictures'):
                piclist = message.get('pictures')
                for pic in piclist:
                    if os.path.isfile(pic):
                        bot.sendPhoto(chat_id, open(pic, 'rb'))
            if message.get('commands'):
                pass
        elif command == 'dailyquestionary' or self.quest == True:
            self.inputcounter += 1
            self.quest = True
            self.send_questionary(bot, chat_id, command, self.inputcounter)
            if self.inputcounter == 7:
                print("You are done - thanks for your inputs")
                self.quest = False
                self.inputcounter = 0
        elif self.quest == True and command in ['skip', 'Skip', 'Quit', 'quit', 'exit', 'Exit']:
            print("You don't want to continue?")
            self.quest = False
            self.inputcounter = 0
        else:
            message = "no command not found"
        # obtain the result in form of a dictionary

        return message

    def run_command(self, name, activedic):
        message = {}
        if name == 'hello':
            message['text'] = "Hello {}, nice to talk to you.".format(self.configuration.get('firstname'))
        elif name == 'help':
            message = self.help(activedic)
        elif name == 'statistics':
            message = self.statistics(activedic)
        return message

    def help(self, comdic={}):
        """
        DESCRIPTION
            print dictionary of commands
        """
        printall = False
        printhidden = False
        mesg = ''

        for com in comdict:
            cd = comdict.get(com)
            if 'all' in cd.get('availability') or printall:
                mesg += "COMMAND: *{}*\n".format(com)
                mesg += "{}\n\n".format(cd.get('description'))
                # options = self.extract_options(comdic.get('options'))

        message['text'] = mesg
        return message


    def plot(sensor, starttime, endtime, keys=None):
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


    def runtmate(command):
        """
        DESCRIPTION
            open a ssh channel based on tmate
        """
        try:
            tglogger.debug("Opening SSH access...")
            call1 = 'cd /home/cobs' # get this path
            call2 = 'tmate -F new-session'
            tglogger.debug("Call2: {}".format(call))
            tglogger.debug(" - tmate requires tmate >= 2.4 and configuratiuon for named access")
            p = subprocess.Popen(call1, stdout=subprocess.PIPE, shell=True)
            (output, err) = p.communicate()
            p = subprocess.Popen(call2, stdout=subprocess.PIPE, shell=True)
            (output, err) = p.communicate()
            if debug:
                print (output)
            if vers == '3':
                output = output.decode()
            mesg = "{}".format(output)
        except subprocess.CalledProcessError:
            mesg = "martas: check_call didnt work"
        except:
            mesg = "martas: check_call problem"
        return mesg

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


    def _latestfile(self, path, date=False, latest=True):
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

class hconf(object):
    bot = None
    lwb = None
    chat_id = None
    debug = False


def handle(msg):
    lwbot = hconf.lwb
    bot = hconf.bot
    debug = hconf.debug
    content_type, chat_type, chat_id = telepot.glance(msg)
    hconf.chat_id = chat_id
    allowed_users = lwbot.configuration.get('allowed_users')
    if not isinstance(allowed_users,list):
        allowed_users = [allowed_users]
    if debug:
        print ("allowed users:", allowed_users)
    if lwbot.logger:
        lwbot.logger.info("Bot -> ContentType: {}; ChatType: {}".format(content_type, chat_type))
    firstname = msg['from']['first_name']
    userid = msg['from']['id']
    chat_id = msg['chat']['id']
    command = msg['text'].replace('/','')
    lwbot.configuration['firstname'] = firstname

    if not str(chat_id) in allowed_users:
        bot.sendMessage(chat_id, "My mother told me not to speak to strangers, sorry...")
        rep = '--------------------- Unauthorized access -------------------------\n!!! unauthorized access from ChatID {} (User: {}) !!!\n-------------------------------------------------------------------'.format(chat_id,firstname)
        if lwbot.logger:
            lwbot.logger.info(rep)
        if debug:
            print (rep)
    else:
        if content_type == 'text':
            rep = 'Received command "{}" from ChatID {} (User: {})'.format(command,chat_id,firstname)
            if lwbot.logger:
                lwbot.logger.info(rep)
            if debug: - requires the correct user i.e. martas update user debian
                print (rep)
            message = lwbot.command(bot, command, chat_id)
            print (message)
            #tg.send_message(message)


def main(argv):
    conf = ''
    debug=False
    try:
        opts, args = getopt.getopt(argv,"hc:D",["config=","debug=",])
    except getopt.GetoptError:
        print ('telegrambot.py -c <config>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print ('-------------------------------------')
            print ('Description:')
            print ('-------------------------------------')
            print ('Usage:')
            print ('telegrambot.py -c <config>')
            print ('-------------------------------------')
            print ('Options:')
            print ('-c (required) : provide a path to a configuartion file')
            print ('-------------------------------------')
            print ('Example:')
            sys.exit()
        elif opt in ("-c", "--config"):
            conf = os.path.abspath(arg)
        elif opt in ("-D", "--debug"):
            debug = True

    # get configuration data
    lwbot = tbot(configsource=conf, debug=debug)
    hconf.lwb = lwbot
    hconf.debug = debug
    bot = telepot.Bot(lwbot.configuration.get('bot_id'))
    au = lwbot.configuration.get('allowed_users')
    # Get chat id from users configuration file
    if isinstance(au, list):
        chat_id = au[0]
    else:
        chat_id = au
    hconf.bot = bot
    MessageLoop(bot, handle).run_as_thread()
    lwbot.logger.info('Listening ...')

    # Keep the program running.
    while 1:
        try:
            time.sleep(5)
            t = datetime.now()
            wd = t.weekday()
            h = t.hour
            m = t.minute
            s = t.second
            if h == 7 and m == 30 and s >= 2 and s < 7:
                lwbot.command(bot,'dailyquestionary',chat_id)
            if h == 20 and m == 0 and s >= 2 and s < 7:
                ad = int(self.configuration.get('weightday',2))
                if ad == wd:
                    lwbot.command(bot,'summary',chat_id)
        except KeyboardInterrupt:
            lwbot.logger.info('\n Program interrupted')
            exit()
        except:
            lwbot.logger.error('Other error or exception occured!')
            sys.exit()

if __name__ == "__main__":
   main(sys.argv[1:])

