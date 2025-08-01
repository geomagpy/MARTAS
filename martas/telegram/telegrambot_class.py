
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

import unittest
from martas.core import methods as mm
from martas.version import __version__
from magpy.stream import *
from magpy.core import database
from magpy.core import plot as mp
import re
import os
import subprocess
#import telepot
#from telepot.loop import MessageLoop
import sys, getopt
import glob


class ActionHandler(object):
    """
    DESCRIPTION
        Action handler contains a command dictionary and will perform actions according to this
         dictionary dependend on any received command.
         In order to generate specific options, the Action handler needs also access to data and
         configurations of MARTAS/MARCOS
    METHODS

    APPLICATION
    """

    def __init__(self, configpath=None, commands=None, debug=False):
        # set some general parameters
        # read a "interpretation" dictionary from a file
        if not commands:
            commands = self.set_default_commands()
        else:
            # TODO eventually add new commands and replace defaults
            pass
        self.debug = debug
        # Now combine defauls with constructors provided
        if configpath:
            if debug:
                 print ("TelegramBot: Reading configuration")
            config = mm.get_conf(configpath)
        else:
            config = self.set_default_configuration()

        if debug:
            print ("Configuration:")
            print (config)
        # PLEASE NOTE: CONFIG should replace or extend contents of default dictionaries, not the whole dic
        self.configuration = config
        self.commanddict = commands
        self.logger = self.logger_setup(name=config.get('logname','telegrambot'),loglevel=config.get('loglevel','INFO'),path=config.get('logging','stdout'))
        self.inputcounter = 0
        self.quest = False
        self.cvals = {}
        # parameters will be filled by data and configuartion specific parameters for the requested actions
        self.parameters = {}

        #if configuration.get('purpose') in ['martas','Martas','MARTAS']:
        #    configuration = self.init_martas(configuration)

    def set_default_configuration(self):
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
        config['martasfile'] = '/home/cobs/.martas/conf/martas.cfg'
        config['martaspath'] = '/home/cobs/MARTAS'
        config['allowed_users'] = ''
        config['camport'] = 'None'
        config['logname'] = 'telegrambot'
        config['logging'] = 'stdout'
        config['loglevel'] = 'INFO'
        config['travistestrun'] = False
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
                       'getlog' : {'commands': ['getlog','get log','get the log', 'print log', 'print the log', ' log'],
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
                                   'combination' : 'any',
                                   'priority' : 1,
                                   'availability': ['hidden'],
                                   'description': ''},
                       'figure1': {'commands': ['figure1','Figure1','fig1','Fig1'],
                                   'combination' : 'any',
                                   'priority' : 1,
                                   'availability': ['all'],
                                   'description': 'open a preconfigured figure'},
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


    def interprete(self, input, exclude=None):
        """
        DESCRIPTION
            Receive any text and identify existing commands and priorities within a command dictionary. Select the
            appropriate command(s) and return them as action dictionary.
        PARAMETERS:
            input : any input request
            exclude :
        REQUIRES
            self.configuration
            self.interpreter
        APPLICATION
            the main program just
        """
        actiondict = {}
        if not exclude:
            exclude = []
        # Identify words, amount and positions of commandlist in input.
        for elem in self.commanddict:
            jobdic = self.commanddict.get(elem)
            jobname = elem
            jobpriority = jobdic.get('priority', 0)
            jobcommands = jobdic.get('commands', [jobname])
            availability = jobdic.get('availability', [])
            print (jobcommands)
            for jc in jobcommands:
                if jc in input and not any(x in exclude for x in availability):
                    ad = actiondict.get(jobname)
                    count = ad.get("count",0)
                    count += 1
                    ad[count] = count
                    ad['priority'] = jobpriority
                    actiondict[jobname] = ad

        """

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
        """

    def run_command(self, name, activedic):
        message = {}
        if name == 'hello':
            message['text'] = "Hello {}, nice to talk to you.".format(self.configuration.get('firstname'))
        elif name == 'help':
            message = self.help(activedic)
        elif name == 'statistics':
            message = self.statistics(activedic)
        return message


    def init_martas(self, martasconfig="", debug=False):
        """
        DESCRIPTION
            special initialization for martas machine
            -> reads martas config files (martas.cfg and sensors.cfg)
        APPLICATION:
            at the end of general init (after logger)
        """
        conf = mm.get_conf(martasconfig)

        sensorlist = mm.get_sensors(conf.get('sensorsconf'))
        ardlist = mm.get_sensors(conf.get('sensorsconf'),identifier='?')
        sensorlist.extend(ardlist)
        owlist = mm.get_sensors(conf.get('sensorsconf'),identifier='!')
        sensorlist.extend(owlist)
        sqllist = mm.get_sensors(conf.get('sensorsconf'),identifier='$')
        sensorlist.extend(sqllist)
        mqttpath = conf.get('bufferdirectory',"")
        self.parameters['mqttpath'] = mqttpath
        #self.logger("Successfully obtained parameters from martas.cfg")
        return conf



    def help(self, printhidden=False):
        """
        DESCRIPTION
            print dictionary of commands
        """
        printall = False
        message = {}
        mesg = ''

        for com in self.commanddict:
            cd = self.commanddict.get(com)
            print (cd)
            if 'all' in cd.get('availability') or printall:
                mesg += "COMMAND: *{}*\n".format(com)
                mesg += "{}\n\n".format(cd.get('description'))
                # options = self.extract_options(comdic.get('options'))

        message['text'] = mesg
        return message

    def plot(self, sensor, starttime, endtime, keys=None):
        """
        DESCRIPTION
           plotting subroutine
        """
        mqttpath = self.telegramparameters.get('mqttpath',"")
        tmppath = self.telegramparameters.get('tmppath',"")
        if mqttpath and tmppath:
            data = read(os.path.join(mqttpath,sensor,'*'),starttime=starttime, endtime=endtime)
            if len(data) > 0:
                matplotlib.use('Agg')
                p,a = mp.tsplot(data)
                # p.save


    def getspace(self):
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


    def jobprocess(self, typ='MARTAS'):
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
        lines = [line.decode() for line in lines]

        mesg += "\n{}".format(''.join(lines))

        return mesg

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



    def system(self):
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


    def tail(self, f, n=1):
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


    def read_interpreter(self, path):
        """
        DESCRIPTION
            reads a interpretation dictionary from file
        """
        pass

"""
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
"""


class TestActionHandler(unittest.TestCase):
    """
    Test environment for all methods
    """

    def test_interprete(self):
        act = ActionHandler()
        test = act.interprete("an incredibly long cry for help")
        self.assertTrue(db)



if __name__ == "__main__":
    unittest.main(verbosity=2)