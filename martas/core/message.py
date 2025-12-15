
#!/usr/bin/env python
# coding=utf-8


import sys
from os import WCONTINUED

sys.path.insert(1, '/home/leon/Software/magpy/')  # should be magpy2

import unittest
from martas.core import methods as mm
from martas.version import __version__
from martas.app.monitor import _latestfile
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
import psutil
import signal
from crontab import CronTab
from pathlib import Path
from dateutil.parser import parse


class ActionHandler(object):
    """
    DESCRIPTION
        Action handler contains a command dictionary and will perform actions according to this
         dictionary dependend on any received command.
         In order to generate specific options, the Action handler needs also access to data and
         configurations of MARTAS/MARCOS
    METHODS

| class           |    method          |  version |  tested  |              comment       | manual | *used by |
| --------------- |  ----------------- |  ------- |  ------- |  ------------------------- | ------ | ---------- |
|  **ActionHandler**  |                |          |          |                            |        | telegrambot |
|  ActionHandler  |  __init__          |  2.0.0   |      yes |                            | -      |          |
|  ActionHandler  |  _getcam           |  2.0.0   |     *yes |                            | -      |          |
|  ActionHandler  |  _getspcae         |  2.0.0   |     *yes | by action_status           | -      |          |
|  ActionHandler  |  _identify_sensors |  2.0.0   |     *yes | by action_getdata          | -      |          |
|  ActionHandler  |  _identify_dates   |  2.0.0   |     *yes | by action_getdata          | -      |          |
|  ActionHandler  |  _jobprocess       |  2.0.0   |     *yes | by action_status           | -      |          |
|  ActionHandler  |  _tail             |  2.0.0   |     *yes | by action_getlog           | -      |          |
|  ActionHandler  |  set_default_configuration | 2.0.0 | yes |                            | -      |          |
|  ActionHandler  |  set_default_commands | 2.0.0 |      yes |                            | -      |          |
|  ActionHandler  |  init_martas       |  2.0.0   |     *yes | by __init__                | -      |          |
|  ActionHandler  |  interpret         |  2.0.0   |      yes |                            | -      |          |
|  ActionHandler  |  execute_command   |  2.0.0   |      yes |                            | -      |          |
|  ActionHandler  |  action_help       |  2.0.0   |     *yes |                            | -      |          |
|  ActionHandler  |  action_hello      |  2.0.0   |     *yes |                            | -      |          |
|  ActionHandler  |  action_martas     |  2.0.0   |      yes |                            | -      |          |
|  ActionHandler  |  action_marcos     |  2.0.0   |      yes |                            | -      |          |
|  ActionHandler  |  action_cam        |  2.0.0   |     *yes |                            | -      |          |
|  ActionHandler  |  action_reboot     |  2.0.0   |     *yes |                            | -      |          |
|  ActionHandler  |  action_martasupgrade | 2.0.0  |     *yes |                            | -      |          |
|  ActionHandler  |  action_system     |  2.0.0   |     *yes |                            | -      |          |
|  ActionHandler  |  action_martas_sensors | 2.0.0 |    *yes |                            | -      |          |
|  ActionHandler  |  action_figure     |  2.0.0   |     *yes |                            | -      |          |
|  ActionHandler  |  action_status     |  2.0.0   |     *yes |                            | -      |          |
|  ActionHandler  |  action_getlog     |  2.0.0   |     *yes |                            | -      |          |
|  ActionHandler  |  action_getdata    |  2.0.0   |     *yes |                            | -      |          |
|  ActionHandler  |  action_upload     |  2.0.0   |     *yes |                            | -      |          |
|  ActionHandler  |  action_getip      |  2.0.0   |     *yes |                            | -      |          |
|  ActionHandler  |  action_tmate      |  2.0.0   |     *yes |                            | -      |          |
|  ActionHandler  |  action_plot       |  2.0.0   |     *yes |                            | -      |          |

* all action_ methods are tested by execute_command
    APPLICATION

    RETURN
        will create a dictionary with
        {call :  {'message' : {'text': xxx, 'pic...
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
        #self.logger = self.logger_setup(name=config.get('logname','telegrambot'),loglevel=config.get('loglevel','INFO'),path=config.get('logging','stdout'))
        self.inputcounter = 0
        self.quest = False
        self.cvals = {}
        # some cleanups for later
        self.configuration['purpose'] = self.configuration.get('purpose').upper()
        # parameters will be filled by data and configuartion specific parameters for the requested actions
        self.messageconfig = {}
        if 'MARTAS' in self.configuration.get('purpose'):
            self.init_martas(self.configuration.get('martasconfig',""))
        self.messageconfig['tmppath'] = "/tmp"


    def _getcam(self, camport):
        """
        DESCRIPTION
            obtain device call for cam port
        """
        po = re.search(r'\d+', camport).group()
        if po and int(po) < 10:
            camport = "/dev/video{}".format(po)
        return camport


    def _getspace(self):
        """
        DESCRIPTION
            get some memory information and process status reports
        """
        statvfs = os.statvfs('/home')
        total = (statvfs.f_frsize * statvfs.f_blocks / (1024.*1024.))     # Size of filesystem in bytes
        remain = (statvfs.f_frsize * statvfs.f_bavail / (1024.*1024.))     # Number of free bytes that ordinary users
        mesg = "MEMORY status:\n----------\nDisk-size: {:.0f}MB\nDisk available: {:.0f}MB\nDisk occupied: {:.1f}%".format(total,remain, 100-(remain/total*100.))
        try:
            mem = psutil.virtual_memory()
            cpu = psutil.cpu_percent(interval=1)
            avail = mem.available / (1024*1024)
            total = mem.total / (1024*1024)
            mesg += "\nMemory total: {}MB\nMemory available: {}MB\nCPU usage: {}%\n".format(total,avail,cpu)
        except:
            pass

        return mesg

    def _identify_sensor(self, text):
        """
        DESCRIPTION
            check whether the text contains valid sensorid and returns a list of them
        """
        sensorlist = self.messageconfig.get("sensorlist",[])

        senslist = []
        if not text:
            return []
        splittext = text.split()
        validsensors = [s.get('sensorid').replace('$', '').replace('?', '').replace('!', '') for s in sensorlist]
        for element in splittext:
            if element in validsensors:
                # found a sensorid in within the text
                senslist.append(element)
        validnames = list(set([s.get('name') for s in sensorlist]))
        for element in splittext:
            if element in validnames:
                # found a sensorname in the text
                correspondingids = [s.get('sensorid').replace('$', '').replace('?', '').replace('!', '') for s in
                                    sensorlist if s.get('name') == element]
                if len(correspondingids) > 0:
                    for el in correspondingids:
                        senslist.append(el)
        if len(senslist) > 0:  # remove duplicates
            senslist = list(set(senslist))
        return senslist

    def _identify_dates(self, text):
        """
        DESCRIPTION
            extract dates from a text
        """
        # For old parse date versions
        def hasNumbers(inputString):
            return any(char.isdigit() for char in inputString)

        if not hasNumbers(text):
            return None

        try:
            dt = parse(text, fuzzy=True)
            dt = dt.replace(tzinfo=None)
        except:
            dt = None
        return dt

    def _jobprocess(self, debug=False):
        """
        DESCRIPTION
            Identify PIDs of MARTAS and MARCOS processes
        """
        lines = []
        # Status of MARTAS MARCOS jobs
        mycron = CronTab(user=True)
        for job in mycron:
            if debug:
                print("Testing job:", job)
            comm = job.comment
            cand = job.command
            en = job.is_enabled()
            cl = cand.split()
            if comm.find("MARCOS") >= 0 or comm.find("MARTAS") >= 0:
                if debug:
                    print (comm)
                active = "inactive"
                k = comm.replace("Running MARCOS process ", "")
                pidname = Path(cl[2]).stem
                if debug:
                    print("Testing pid", pidname)
                p = self.get_pid(pidname)
                if debug:
                    print (" - got pid", p)
                if p > 0:
                    active = "active"
                line = "{} : {}\n----------".format(comm, active)
                lines.append(line)

        mesg = "\n".join(lines)
        return mesg


    def _tail(self, path, lines=1, _buffer=4098):
        """
        DESCRIPTION:
            Obtain the last n line of a file f
            see: https://stackoverflow.com/questions/136168/get-last-n-lines-of-a-file-similar-to-tail
        """
        lines_found = []
        mesg = ""

        # block counter will be multiplied by buffer
        # to get the block size from the end
        block_counter = -1

        with open(path, "rb") as f:
            # loop until we find X lines
            while len(lines_found) < lines:
                try:
                    f.seek(block_counter * _buffer, os.SEEK_END)
                except IOError:  # either file is too small, or too many lines requested
                    f.seek(0)
                    lines_found = f.readlines()
                    break
                lines_found = f.readlines()
                # we found enough lines, get out
                # Removed this line because it was redundant the while will catch
                # it, I left it for history
                # if len(lines_found) > lines:
                #    break
                # decrement the block counter to get the
                # next X bytes
                block_counter -= 1

            mesg = "\n".join([x.decode() for x in lines_found[-lines:]])
        return mesg


    def set_default_configuration(self):
        """
        DESCRIPTION
            some defaults for configuration parameters
        """
        config = {}
        config['bot_id'] = ''
        config['allowed_users'] = ''
        config['purpose'] = 'MARTAS'
        config['base'] = '/home/leon/.martas'
        config['martasapp'] = '/home/leon/.martas/app'
        config['martaslog'] = '/home/leon/.martas/log'
        config['martasconfig'] = '/home/leon/.martas/conf/martas.cfg'
        config['marcosconfig'] = '/home/leon/.martas/conf/marcos.cfg'
        config['dbcredentials'] =  'cobsdb'
        config['proxy'] = None
        config['proxyport'] = None
        config['currentdatapath'] =  '/srv/products/data/current.data'
        config['defaultplot'] =  "/tmp/martas-demo.jpg"
        config['fig1'] =  "/tmp/Spectra.png"
        config['outlier'] = {"threshold" : 4}
        config['imbotoverview'] =  '/home/leon/.imbot/quickreport.py'
        config['imbotmemory'] =  '/second'
        config['imbotarchive'] =  '/srv/imbot'
        config['tmppath'] =  "/tmp"
        config['camport'] =  None
        config['camoptions'] = "-r 1280x720 -S 100 -F 1 -D 5 --no-banner"
        config['uploadmemory'] = '/home/leon/.martas/memory/uploadmemory.json'
        config['uploadconfig'] = ''
        config['bot_logging'] =  '/home/leon/.martas/log/telegrambot.log'
        config['loglevel'] =  'INFO'

        # Move those to commands dict
        config['figure1'] =  ["spectrum", "spectra"]
        config['cam'] =  ["snapshot", "picture", "cheese"]
        config['getlog'] =  ["getthelog"]

        # NOT IN telegrambot.cfg
        config['logname'] = 'telegrambot'
        config['logging'] = 'stdout'
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
                                   'description': 'optional: turn on/off remote switches if supported by the hardware (work in progress). switch without options will return the switch status. switch swP:1:4  will turn on port 4 from a attached microcontroller'},
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
                       'martasupgrade': {'commands': ['upgrade'],
                                   'combination' : 'any',
                                   'priority' : 1,
                                   'availability': ['hidden'],
                                   'description': 'upgrade MARTAS to its newest version'},
                       'version': {'commands': ['version'],
                                        'combination': 'any',
                                        'priority': 1,
                                        'availability': ['all'],
                                        'description': 'library version 2.0.0'},
                       'martas' : {'commands': ['Martas','martas','MARTAS'],
                                   'combination' : 'any',
                                   'availability': ['MARTAS'],
                                   'priority' : 2,
                                   'options' : {'restart':['restart'],'start':['start'],'stop':['stop'],'status':['status']},
                                   'description': 'restart-stop-start-update-status : e.g. restart MARTAS process: send - martas restart - to restart a martas process'},
                       'marcos' : {'commands': ['Marcos','marcos','MARCOS'],
                                   'combination' : 'any',
                                   'availability': ['MARCOS'],
                                   'priority' : 2,
                                   'options' : {'restart':['restart'],'start':['start'],'stop':['stop'],'status':['status']},
                                   'description': 'restart-stop-start-status : e.g. restart MARCOS processes: if you have a collector called collect-local then - marcos local restart - will restart this process'},
                       'aperta': {'commands': ['aperta', 'Aperta', 'Sesam öffne dich'],
                                        'combination': 'any',
                                        'priority': 1,
                                        'availability': ['hidden'],
                                        'description': 'Open secret door'},
                       'upload': {'commands': ['upload', 'send data', 'Upload', 'nach Hause telefonieren'],
                                        'combination': 'any',
                                        'priority': 1,
                                        'availability': ['hidden'],
                                        'description': 'Upload data to server'},
                       'getip': {'commands': ['getIP', ' IP ', 'IP ', 'getip', 'Getip', 'GetIP'],
                                        'combination': 'any',
                                        'priority': 1,
                                        'availability': ['hidden'],
                                        'description': 'send current IP address'},
                       }
        return commanddict


    def init_martas(self, martasconfig="", debug=False):
        """
        DESCRIPTION
            special initialization for martas machine
            -> reads martas config files (martas.cfg and sensors.cfg)
        APPLICATION:
            at the end of general init (after logger)
        """
        if not martasconfig:
            return
        conf = mm.get_conf(martasconfig)

        sensorlist = mm.get_sensors(conf.get('sensorsconf'))
        ardlist = mm.get_sensors(conf.get('sensorsconf'),identifier='?')
        sensorlist.extend(ardlist)
        owlist = mm.get_sensors(conf.get('sensorsconf'),identifier='!')
        sensorlist.extend(owlist)
        sqllist = mm.get_sensors(conf.get('sensorsconf'),identifier='$')
        sensorlist.extend(sqllist)
        self.messageconfig['mqttpath'] = conf.get('bufferdirectory','')
        self.messageconfig['sensorlist'] = sensorlist
        self.messageconfig['martaslog'] = conf.get('logging','')


    def interpret(self, input, exclude=None, debug=False):
        """
        DESCRIPTION
            Receive any text and identify existing commands and priorities within a command dictionary. Select the
            appropriate command(s) and return them as action dictionary.
        PARAMETERS:
            input : any input request
            exclude : a list of availability options to exclude (i.e. hidden)
        REQUIRES
            self.configuration
        RETURNS:
            a list of action items from commanddict in applictaion order
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
            if debug:
                print ("Analysing {} with {}".format(elem, jobcommands))
            for jc in jobcommands:
                if jc in input and not any([x in exclude for x in availability]):
                    if debug:
                        print ("  -> found")
                    ad = actiondict.get(jobname,{})
                    ad['count'] = input.count(jc)
                    ad['priority'] = jobpriority
                    ad['position'] = input.find(jc)
                    actiondict[jobname] = ad

        actiondict = dict(sorted(actiondict.items(), key=lambda x: x[1]['position'], reverse=False))
        actiondict = dict(sorted(actiondict.items(), key=lambda x: x[1]['count'], reverse=True))
        actiondict = dict(sorted(actiondict.items(), key=lambda x: x[1]['priority'], reverse=False))
        actionlist = [el for el in actiondict]

        return actionlist

    def execute_action(self, actionlist, input="", debug=False):
        """
        DESCRIPTION
            Takes the action list and performs the requested actions. It will then recieve a result (message)
            dictionary from each action.
        PARAMETERS:
            actionlist : an actionlist as determined by interpret
            input : the original input to identify additional parameters for specific jobs
        RETURNS:
            message dictionary with results for each action
            messagedict : {'action' : {'message' : {'text' : "hello"},
                                                   {'pictures' : "hello"},
                                      }
        """
        messagedict = {}

        for action in actionlist:
            adict = {}
            msg = {}
            if action == "help":
                msg = self.action_help(input)
            elif action == "hello":
                msg['text'] = "Hello {}, nice to talk to you.".format(self.messageconfig.get('firstname',''))
            elif action == 'sensor':
                if 'MARTAS' in self.configuration.get('purpose'):
                    msg['text'] = self.action_martas_sensors(debug=False)
                if 'MARCOS' in self.configuration.get('purpose'):
                    pass
            elif action == 'imbot':
                msg = self.action_imbot(input)
            elif action == 'system':
                msg['text'] = self.action_system()
            elif action == 'martas':
                msg = self.action_martas(input,debug=debug)
            elif action == 'marcos':
                msg = self.action_marcos(input,debug=debug)
            elif action == 'cam':
                msg = self.action_cam(debug=debug)
            elif action == 'status':
                msg['text'] = self.action_status(debug=debug)
            elif action == 'getlog':
                msg['text'] = self.action_getlog(input, debug=debug)
            elif action == 'getdata':
                msg['text'] = self.action_getdata(input, debug=debug)
            elif action == 'plot':
                msg = self.action_plot(input, debug=debug)
            elif action == 'switch':
                msg = self.action_switch(input, debug=debug)
            elif action == 'upload':
                msg = self.action_upload()
            elif action == 'aperta':
                #msg['text'] = self.action_tmate(input)
                msg = self.action_upterm()
            elif action == 'getip':
                msg = self.action_getip(input, debug=debug)
            elif action == 'badwords':
                msg['text'] = self.action_badwords()
            elif action == 'figure1':
                msg = self.action_figure(figure="fig1")
            elif action == 'figure2':
                msg = self.action_figure(figure="fig2")
            elif action == 'reboot':
                msg = self.action_reboot(debug=debug)
            elif action == 'martasupgrade':
                msg = self.action_martasupgrade(debug=debug)
            elif action == 'version':
                msg['text'] = self.commanddict['version'].get('description','')

            adict['message'] = msg
            messagedict[action] = adict
        if debug:
            print (" Obtained the following messages:", messagedict)
        return messagedict

    def action_help(self, printhidden=False):
        """
        DESCRIPTION
            print dictionary of commands
        """
        printall = False
        message = {}
        mesg = ''

        for com in self.commanddict:
            cd = self.commanddict.get(com)
            if 'all' in cd.get('availability') or printall:
                mesg += "COMMAND: *{}*\n".format(com)
                mesg += "{}\n\n".format(cd.get('description'))
                # options = self.extract_options(comdic.get('options'))
            if 'MARTAS' in cd.get('availability') and 'MARTAS' in self.configuration.get('purpose'):
                mesg += "COMMAND: *{}*\n".format(com)
                mesg += "{}\n\n".format(cd.get('description'))
                # options = self.extract_options(comdic.get('options'))
            if 'MARCOS' in cd.get('availability') and 'MARCOS' in self.configuration.get('purpose'):
                mesg += "COMMAND: *{}*\n".format(com)
                mesg += "{}\n\n".format(cd.get('description'))
                # options = self.extract_options(comdic.get('options'))
            if 'IMBOT' in cd.get('availability') and 'IMBOT' in self.configuration.get('purpose'):
                mesg += "COMMAND: *{}*\n".format(com)
                mesg += "{}\n\n".format(cd.get('description'))
                # options = self.extract_options(comdic.get('options'))

        message['text'] = mesg
        return message


    def action_martas_sensors(self, debug=False):
        """
        DESCRIPTION
            provide basic sensorlist and show whether they are active or not
        """
        sensorlist = self.messageconfig.get("sensorlist",[])
        mqttpath = self.messageconfig.get("mqttpath","")
        mesg = "Sensors:\n"
        for s in sensorlist:
            se = s.get('sensorid').replace('$','').replace('?','').replace('!','')
            try:
                lf = _latestfile(os.path.join(mqttpath,se,'*'),date=True)
                diff = (datetime.now(timezone.utc).replace(tzinfo=None)-lf).total_seconds()
                flag = "active"
                if diff > 300:
                    flag = "inactive since {:.1f} hours".format(diff/3600.)
            except:
                flag = "no buffer found"
            mesg += "{}: {}\n".format(se,flag)
        return mesg


    def action_system(self):
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
        #mesg += "\nTelegramBot Version: {}".format(tgpar.version)
        mesg += "\nMARTAS/MARCOS Version: {}".format(__version__)
        mesg += "\nPython Version: {}".format(sys.version)

        return mesg


    def action_martas(self, input, debug=False):
        """
        DESCRIPTION:
           issue commend for MARTAS/MARCOS jobs i.e. restart martas process
        """
        message = {}
        if debug:
            print("Running ACTION martas")
            print("-----------------------")
        mainjob = "{}".format(os.path.join(self.configuration.get('base'),'runmartas.sh'))
        if not os.path.isfile(mainjob):
            mesg = "martas: could not find martas call\n"
            return mesg
        command = ""

        comms = ["start","stop","restart","update","status"]
        for jc in comms:
            searchterm = "martas {}".format(jc)
            if searchterm in input:
                command = jc
        if not command:
            if debug:
                print ("Did not find start, stop, restart command - skipping")
            return ""

        call = 'bash {} {} &'.format(mainjob, command)
        message['call'] = [call]
        message['text'] = "Sending MARTAS call: {}\n".format(command)
        return message


    def action_marcos(self, input, debug=False):
        """
        DESCRIPTION:
            restarting marcos process
        """
        message = {}
        command = ""
        cleaninput = ""
        if debug:
            print("Running ACTION marcos")
            print("-----------------------")
        collectorpath = os.path.join(self.configuration.get('base'),"collect-*")
        if debug:
            print (" collector jobs:", collectorpath)
        collectlist = glob.glob(collectorpath)
        if debug:
            print (" collector jobs:", collectlist)

        comms = ["start","stop","restart","status"]
        for jc in comms:
            if jc in input:
                command = jc
        if debug:
            print (" found command", command)
        if not command:
            if debug:
                print (" did not find start, stop, restart command - skipping")
            message['text'] = "did not find start, stop, restart command - skipping"
            return message
        else:
            cleaninput = input.replace("marcos","").replace(command,"").strip()

        if debug:
            print (" found specific brocker", cleaninput)

        # now renmove marcos and startcommand. Check if remaining text corresponds to a collector
        if cleaninput:
            collectlist = [coll for coll in collectlist if coll.find(cleaninput) > -1]

        if debug:
            print (" collector jobs remaining:", collectlist)
        calls = []
        mesg = ""
        if collectlist and len(collectlist)>0:
            for coll in collectlist:
                call = "bash {} {} &".format(coll,command)
                calls.append(call)
                mesg += "sending {} command to {}...\n".format(command,coll)
        message['text'] = mesg
        message['call'] = calls
        return message


    def action_reboot(self, debug=True):
        """
        DESCRIPTION:
            Rebooting the system
        """
        message = {}
        message['call'] = ["/sbin/reboot"]
        message['text'] = "rebooting...\n"
        return message


    def action_martasupgrade(self, debug=True):
        """
        DESCRIPTION:
            updating martas using pip - requires martas 2 to be published on pypi
        """
        message = {}
        message['call'] = ["pip install -U martas", "martas_init -U"] # "pip install -U martas",
        message['text'] = "updating martas...\n"
        return message


    def action_cam(self, debug=False):
        """
        DESCRIPTION:
            accessing webcam(s) and taking snapshots
        """
        message = {}
        tmppath = self.messageconfig.get("tmppath","")
        camport = self.configuration.get("camport","")
        camoptions = self.configuration.get("camoptions","")
        usedcamport = None
        calls = []

        if camport:
            usedcamport = self._getcam(camport)

        if not usedcamport:
            mesg = "No camport identified\n"
        else:
            mesg = "Taking snapshot using fswebcam\n"
            if debug:
                print("Creating image...")
                print("Selected cam port: {} and temporary path {}".format(usedcamport, tmppath))
            call = "/usr/bin/fswebcam -d {} {} {}".format(usedcamport, camoptions,
                                                              os.path.join(tmppath, 'webimage.jpg'))
            calls.append(call)

        message['text'] = mesg
        message['call'] = calls
        return message


    def action_figure(self, figure="fig1"):
        message = {}
        message['pictures'] = [self.configuration.get(figure)]
        return message


    def action_status(self, debug=False):
        """
        DESCRIPTION:
            status
        """
        msg = self._getspace()
        if debug:
            print ("Status from getspace", msg)
        msg += self._jobprocess(debug=debug)
        if debug:
            print ("Status from sobprocess", msg)
        return msg


    def action_badwords(self):
        return "Don't be rude.\nI am just a program, acting as mirror now.\n"


    def action_getlog(self, input, debug=False):
        """
        DESCRIPTION:
            get logging information
        """
        logpath = ""
        tmppath = ""
        cmd = input.replace('getlog', '').replace('print log', '').replace('send log', '').replace('get log', '')
        try:
            N = int(re.search(r'\d+', cmd).group())
            cmd = cmd.replace(str(N), '')
        except:
            N = 10
        if not N:
            N = 10

        cmd = cmd.strip()
        syslogfiles = ['syslog', 'dmesg', 'messages', 'faillog']
        telegramlog = self.configuration.get('bot_logging','')
        martaspath = self.configuration.get('martaspath','')
        martaslog = os.path.join(martaspath,"log")

        martaslogfiles = glob.glob(os.path.join(martaslog, '*.log'))
        martaslogfiles = [os.path.basename(ma) for ma in martaslogfiles]
        tmppath = os.path.join(martaslog, "martas.log")

        if debug:
            print ("Logging command looks like", cmd, martaslogfiles)

        if len(cmd) > 3:  # at least three characters remaining
            for logfile in syslogfiles:
                if cmd.find(logfile) > -1:
                    tmppath = os.path.join('/var/log', logfile)
            for logfile in martaslogfiles:
                if logfile.find("{}.".format(cmd)) > -1:
                    tmppath = os.path.join(martaslog, logfile)
            if cmd.find('telegrambot') > -1:
                tmppath = telegramlog
            if debug:
                print(" identified logfile", tmppath)
            if os.path.isfile(tmppath):
                logpath = tmppath
        if not logpath:
            logpath = os.path.join(martaslog, "martas.log")
        if os.path.isfile(logpath):
            if debug:
                print("Checking logfile {}".format(logpath))
            mesg = self._tail(logpath, lines=N)
        else:
            mesg = "getlog:\nlogfile not existing\n"

        return mesg


    def action_switch(self, command, debug=False):
        """
        DESCRIPTION
            send switching command to  a connected microcontroller
            Possible switch commands are:
            swP:0:4   = switch - off - port 4
            swP:1:4   = switch - on - port 4
            swP:1:5   = switch - on - port 4
            swS, Status = get status
        """
        message = {}
        call = ''
        martasconf = self.configuration.get('martasconfig','')
        command = command.replace("switch","").replace("heating ","swP:").replace("on ","1:4").replace("off ","0:4").strip()
        if command.find('swP') > -1:
            pass
        else:
            # Show switch status if no specific switch command is given
            command = "swS"

        try:
            if debug:
                print("Running switch command...")
            python = sys.executable
            #path = '/home/cobs/MARTAS/app/ardcomm.py'
            path = os.path.join(self.configuration.get('martasapp',''),'ardcomm.py')
            if debug:
                print("tpath: {}".format(path))
            option = '-c'
            call = "{} {} {} {} -m {}".format(python,path,option,command,martasconf)
            mesg = "Running command {}\n".format(command)
        except:
            mesg = "martas: check_call problem\n"
        message['call'] = [call]
        message['text'] = mesg
        return message


    # TODO deprecated
    def action_tmate(self, command, debug=False):
        """
        DESCRIPTION
           Open a tmate access for a specific time
           This method is solely to be activated on remote sensor stations in mobile networks.
        REQUIREMENTS
           tmate installation
           tmate api key and a named session (https://tmate.io/#api_key)
           and tmate.conf preconfigured on the remote machine
        """
        # 0. check if psutil and tmate are existing. If not return fail
        try:
            if os.path.isfile("/usr/local/bin/tmate"):
                pass
            else:
                return ("check requirements")
        except:
            return ("check requirements")

        # 1. step check whether tmate is running and stop this process
        def _find_process(name):
            procs = list()
            # Iterate over the all the running process
            for proc in psutil.process_iter():
                try:
                    pid = 0
                    if proc.name() == name:
                        pid = proc.pid
                    if pid:
                        procs.append(pid)
                except:
                    pass
            return procs

        def _kill_processes(pids, debug=False):
            for pid in pids:
                os.kill(pid, signal.SIGTERM)  # or signal.SIGKILL
                if debug:
                    print('killed process with pid: {}'.format(pid))

        try:
            if debug:
                print("Killing existing tmate processes")
            processes = _find_process("tmate")
            _kill_processes(processes, debug=debug)
            if debug:
                print("... done")
        except:
            pass
        # 2. Run tmate accecc - do not broadcast login (pwd needs to be known by user)
        mesg = "Opening secret entrance door....\n"
        try:
            #proc2 = subprocess.Popen(['sudo', '-u', user, 'tmate', '-F', 'new-session'], stdout=subprocess.PIPE)
            proc2 = subprocess.Popen(['tmate', '-F', 'new-session'], stdout=subprocess.PIPE)
            mesg += "success - door open for one session\n"
        except:
            mesg += "failed\n"

        # 3. (optional) start a scheduler to kill tmate process after duration

        return mesg


    def action_imbot(self, input):
        message = {}
        cmd = input.replace('imbot', '').replace('IMBOT', '')
        cmd = cmd.strip()
        call = ""
        year = ""
        imo = ""
        yearl = re.findall(r'\d+', cmd)
        print ("got year", yearl)
        if yearl and len(yearl) > 0:
            for y in yearl:
                cmd = cmd.replace(y,"")
            cmd = cmd.strip()
            if 1900 < int(yearl[-1]) < 2177:
                year = "-y {}".format(int(yearl[-1]))
        if cmd.find('minute') > -1:
            cmd = cmd.replace('minute','')
            cmd = cmd.strip()
            res = 'minute'
        else:
            cmd = cmd.replace('second','')
            cmd = cmd.strip()
            res = 'second'
        print ("remaining command:", cmd)
        if cmd.find('bar') > -1:
            cmd = cmd.replace('bar','')
            cmd = cmd.strip()
            typ = 'bar'
        elif cmd.find('imo') > -1:
            cmd = cmd.replace('imo','')
            cmd = cmd.strip()
            typ = 'imo'
            # get IMO from remaining stream
            print ("remaining imo", cmd, len(cmd))
            if len(cmd) == 3:
                imo = "-i {}".format(cmd.upper())
        else:
            cmd = cmd.replace('list','')
            cmd = cmd.strip()
            typ = 'list'

        imbotconfig = self.configuration.get("imbotconfig","")

        call = "imbot_chart -c {a} -t {b} {c} -r {d} {e}".format(
                a=imbotconfig, b=typ, c=year, d=res, e=imo)
        message['call'] = [call]
        message["text"] = "Requesting IMBOT report of typ {}...\n".format(typ)
        if typ == 'bar':
            message["pictures"] = ['/tmp/bar_levels.png']
        return message


    def action_upload(self):

        message = {}
        calls = []
        configpath = self.configuration.get('uploadconfig','')
        memorypath = self.configuration.get('uploadmemory','')
        if not configpath:
            message['text'] = "Upload not configured - aborting\n"
        else:
            if not memorypath:
                memorypath = "/tmp/martas_tgupload_memory.json"
            python = sys.executable
            path = os.path.join(self.configuration.get('martasapp',''),'file_upload.py')
            optioncfg = '-j'
            optionmem = '-m'
            if configpath:
                call = "{} {} {} {} {} {}".format(python,path,optioncfg,configpath,optionmem,memorypath)
                calls.append(call)
            message['call'] = calls
            message['text'] = "Requesting upload...\n"
        return message


    def action_upterm(self, debug=False):
        """
        DESCRIPTION
           Open a ssh connection to a existing upterm terminal
           This method is solely to be activated on remote sensor stations in mobile networks.
        REQUIREMENTS
           upterm host, which provides secure ssh link
        """
        message = {}
        message['call'] = ["upterm host --accept"]
        message["text"] = "Requesting ssh connection...\n"
        return message
        #import paramiko

        # ssh
        #ssh = paramiko.SSHClient()
        #ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())  # this will automatically add the keys
        #ssh.connect(machineHostName, username=user, password=password)

        pass


    def action_getip(self, input, debug=False):
        """
        DESCRIPTION
           getting the current IP
        """
        message = {}
        calls = []
        call = r"ip -br a"
        calls.append(call)
        message['call'] = calls
        message['text'] = "Requesting IP...\n"
        return message


    def action_plot(self, input, debug=False):
        """
        DESCRIPTION
           plotting subroutine
        """
        mesg = ""
        message = {}
        mqttpath = self.messageconfig.get('mqttpath',"")
        tmppath = self.messageconfig.get('tmppath',"")

        cmd = input
        for word in self.commanddict['plot'].get('commands'):
            cmd = cmd.replace(word, '')
        if debug:
            print (" Plotting...")
            print(" reduced command", cmd)
        sensoridlist = self._identify_sensor(cmd)
        if len(sensoridlist) > 1:
            print("Too many sensors selected - using only {}".format(sensoridlist[0]))
        elif len(sensoridlist) == 0:
            mesg = "You need to specify a sensorid - check 'sensors' to get IDs"
        else:
            sensorid = sensoridlist[0]
            cmd = cmd.replace(sensorid, '')
            # Getting time interval
            cmd = cmd.split()
            # default start and endtime
            endtime = datetime.now(timezone.utc).replace(tzinfo=None)
            starttime = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
            datelist = []
            if len(cmd) >= 1:
                for el in cmd:
                    newdate = self._identify_dates(el)
                    if newdate:
                        datelist.append(newdate)
                if len(datelist) > 0:
                    starttime = min(datelist)
                if len(datelist) > 1:
                    endtime = max(datelist)

            if debug:
                print("Now create plot for", sensorid, starttime, endtime)
            # and save to temporary directory
            data = read(os.path.join(mqttpath, sensorid, '*'), starttime=starttime, endtime=endtime)
            matplotlib.use('Agg')
            f, a = mp.tsplot(data)
            f.savefig(os.path.join(tmppath,'tmp.png'))
            mesg = "Plotting {}\n".format(sensorid)
            message['pictures'] = [os.path.join(tmppath,'tmp.png')]

        message['text'] = mesg
        return message


    def action_getdata(self, command, debug=False):
        """
        DESCRIPTION
           get data
        """
        def CreateSensorMsg(valdict):
            mesg = ''
            for sensor in valdict:
                mesg += "Sensor: {}\n".format(sensor)
                contentdict = valdict.get(sensor)
                keys = contentdict.get('keys')
                for key in keys:
                    keydict = contentdict.get(key)
                    mesg += "  {}: {} {} (key: {})\n".format(keydict.get('element'), keydict.get('value'),
                                                             keydict.get('unit', ''), key)
                    mesg += "  at {}\n".format(contentdict.get('starttime').strftime("%Y-%m-%d %H:%M:%S"))
            return mesg

        cmd = command.replace('data', '').replace('get', '')
        cmdsplit = cmd.split()
        mesg = "Data:\n-----------\n"
        if len(cmdsplit) > 0:
            sensoridlist = self._identify_sensor(cmd)
            # tglogger.info("  found sensors: {}".format(sensoridlist))
            for sensorid in sensoridlist:
                cmd = cmd.replace(sensorid, '')
            if len(sensoridlist) == 0:  # if only dates are provided
                sensoridlist = [None]
            starttime = self._identify_dates(cmd)  # dates is a list
            for sensorid in sensoridlist:
                if debug:
                    print (" Obtaining data for {} starting at {}".format(sensorid, starttime))
                valdict = self.getdata(sensorid=sensorid, starttime=starttime)
                mesg += CreateSensorMsg(valdict)
        else:
            valdict = self.getdata()
            mesg += CreateSensorMsg(valdict)
        return mesg

    def execute_call(self, call, text="", searchcrit="", debug=False):
        """
        DESCRIPTION
            executes the calls as provided within the message dictionaries
            Actions with calls:
            getip ??, upload, imbot, cam, martasupgrade, reboot, switch, martas, marcos
            Methods issueing call already: tmate,
        """
        try:
            if debug:
                print ("Executing call", call)
            if call.find("upterm") > -1:
                # Special treatment required - as terminal needs to be kept open (p.communicate() would close the terminal
                p = subprocess.Popen([call], stdout=subprocess.PIPE, stdin=subprocess.PIPE, shell=True)
                oput = []
                count = 0
                line = p.stdout.readline().decode()
                while count < 10:
                    if line.find("SSH Command") > -1:
                        oput.append(line)
                        break
                    line = p.stdout.readline().decode()
                    count += 1
                output = "".join(oput)
            else:
                p = subprocess.Popen(call, stdout=subprocess.PIPE, shell=True)
                (output, err) = p.communicate()
                output = output.decode()
            mesg = output
            print (" ... got:", mesg)
            print (" length:", len(mesg))
            if len(mesg) > 4000:
                mesg = "Message too long - showing only last part:\n\n... " + mesg[-3800:]
        except subprocess.CalledProcessError:
            mesg = " check: call {} did not work".format(call)
        except:
            mesg = "getip: check_call problem"
        return mesg


    def getdata(self, starttime=None, sensorid=None, interval=300, mean='mean'):
        """
        DESCRIPTION
            returns by default a 5 min mean of last values of each sensor
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
        sensorlist = self.messageconfig.get("sensorlist",[])
        mqttpath = self.messageconfig.get("mqttpath","")

        def GetVals(header, key):
            keystr = "col-{}".format(key)
            element = header.get(keystr, 'unkown')
            unit = header.get('unit-' + keystr, 'arb')
            return element, unit

        if not starttime:
            starttime = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=interval)
            endtime = None
        else:
            endtime = starttime + timedelta(seconds=interval)

        senslist = [s.get('sensorid').replace('$', '').replace('?', '').replace('!', '') for s in sensorlist]
        if sensorid and sensorid in senslist:
            senslist = [sensorid]
        returndict = {}
        for s in senslist:
            print(" dealing with sensor:", s)
            print(" between:", starttime, endtime)
            contentdict = {}
            if os.path.isdir(os.path.join(mqttpath, s)):
                try:
                    data = read(os.path.join(mqttpath, s, '*'), starttime=starttime, endtime=endtime)
                except:
                    data = DataStream()
                if len(data) > 0:
                    print(s, data.length(), starttime, endtime)
                    contentdict['keys'] = data._get_key_headers()
                    st, et = data._find_t_limits()
                    contentdict['starttime'] = st
                    contentdict['endtime'] = et
                    print("here", st, et)
                    for key in data._get_key_headers():
                        print(key)
                        valuedict = {}
                        element, unit = GetVals(data.header, key)
                        value = data.mean(key)
                        valuedict['value'] = value
                        valuedict['unit'] = unit
                        valuedict['element'] = element
                        contentdict[key] = valuedict
                    returndict[s] = contentdict
                else:
                    contentdict['keys'] = ['all']
                    contentdict['starttime'] = starttime
                    contentdict['endtime'] = endtime
                    valuedict = {}
                    valuedict['value'] = 'no data within last {} secs'.format(interval)
                    contentdict['all'] = valuedict
                    returndict[s] = contentdict

        return returndict

    def get_pid(self, name):
        """
        DESCRIPTION
            obtain the PID of given call

        An identical method is used marcos_view
        """
        pid = 0
        for proc in psutil.process_iter(attrs=["pid", "name", "exe", "cmdline"]):
            if isinstance(proc.info.get('cmdline'), (list, tuple)):
                for cmd in proc.info.get('cmdline'):
                    if name in cmd:
                        pid = proc.pid
                        break
                if pid:
                    break
        return pid



class TestActionHandler(unittest.TestCase):
    """
    Test environment for all methods
    """

    def test_interpret(self):
        act = ActionHandler()
        test = act.interpret("well: an incredibly loud cry for martas help and logging, but preferebly help")
        self.assertEqual(len(test), 3)

    def test_execute_action(self):
        act = ActionHandler()
        mytext = "hello help sensor imbot system martas marcos cam status getlog getdata plot switch fuck figure1 figure2 reboot martasupgrade getip aperta upload"
        al = act.interpret(mytext)
        msg = act.execute_action(al, input=mytext, debug=True)


    def test_action_martas(self):
        act = ActionHandler()
        mytext = ("martas restart")
        al = act.interpret(mytext)
        msg = act.execute_action(al, input=mytext, debug=True)
        td = msg.get('martas',{})
        self.assertTrue(isinstance(td['message'].get('call'), (list,tuple)))

    def test_action_marcos(self):
        act = ActionHandler()
        mytext = ("marcos janus restart")
        al = act.interpret(mytext)
        msg = act.execute_action(al, input=mytext, debug=True)
        td = msg.get('marcos',{})
        self.assertTrue(isinstance(td['message'].get('call'), (list,tuple)))

    def test_action_getlog(self):
        act = ActionHandler()
        mytext = ("getlog martas 20")
        al = act.interpret(mytext)
        msg = act.execute_action(al, input=mytext, debug=True)
        td = msg.get('getlog',{})
        self.assertTrue(td['message'].get('text'))

    def test_action_getdata(self):
        act = ActionHandler()
        mytext = ("data TEST_1234_0001")
        al = act.interpret(mytext)
        msg = act.execute_action(al, input=mytext, debug=True)
        td = msg.get('getdata',{})
        print ("GET data", td)
        self.assertTrue(td['message'].get('text'))

    def test_zaction_plot(self):
        act = ActionHandler()
        mytext = ("plot TEST_1234_0001 2025-07-31")
        al = act.interpret(mytext)
        msg = act.execute_action(al, input=mytext, debug=True)
        td = msg.get('plot',{})
        print ("Plotting", td)
        #self.assertTrue(td['message'].get('text'))


    def test_execute_call(self):
        act = ActionHandler()
        #upload, imbot, cam, martasupgrade, reboot, switch, martas, marcos
        callcommands = {"getip" : "getip wlp0s20f3"} #, "marcos" : "marcos local restart"}
        for comm in callcommands:
            fc = callcommands.get(comm)
            lines = []
            msg = ""
            al = act.interpret(fc)
            msg = act.execute_action(al, input=fc, debug=True)
            td = msg.get(comm,{})
            print ("Call command:", td['message'].get('call'))
            calls = td['message'].get('call',[])
            for call in calls:
                msg = act.execute_call(call)
                if msg:
                    lines.append(msg)
            if lines:
                msg = "\n".join(lines)
            if msg:
                print ("Result for {}: Obtained {}".format(comm,msg))


if __name__ == "__main__":
    unittest.main(verbosity=2)