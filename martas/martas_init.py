#!/usr/bin/env python3
# coding=utf-8

"""
MARTAS - MagPy's automatic real time acquisition system

martas_init will create folders, setup all configuration files, eventually install dependencies

"""

import shutil
import getopt
import sys
import os
from magpy.opt import cred
from pathlib import Path
from crontab import CronTab
import martas
from martas.version import __version__
import getpass

def main(argv):
    debug = False
    dir = ".martas"
    redo = False
    update = False
    minimalupdate = False

    try:
        opts, args = getopt.getopt(argv,"hd:ruUD",["path=","redo=","update=","UPADTE=","debug=",])
    except getopt.GetoptError:
        print ('martas_init')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print ('-------------------------------------')
            print ('Description:')
            print ('-- martas_init will initialize imbot configuration --')
            print ('-----------------------------------------------------------------')
            print ('martas_init will perform the following tasks:')
            print ('- program files will always be stored within your home directory')
            print ('- default directory is .martas, change that using -d option')
            print ('- will create a ~/.martas directory')
            print ('- copy skeleton configuration files to .martas/conf/')
            print ('- copy bash scripts to .martas/scripts/')
            print ('- copy python applications to .martas/app/')
            print ('')
            print ('Options:')
            print ('-d, --directory : define the main configuration directory')
            print ('                : i.e. -d MARTAS will store everything within /hone/user/MARTAS')
            print ('-u, --update : will update applications (app, doc, web) folder with new version.')
            print ('             : Then you will asked to input your new job or update an exsiting.')
            print ('             : A backup is advisable before updating')
            print ('-U, --UPDATE : will ONLY update applications (app, doc, web) folder with new version')
            print ('-r, --redo   : replace all already existing configuration files.')
            print ('             : ATTENTION: redo will delete all previous configurations')
            print ('-------------------------------------')
            print ('Application:')
            print ('-------------------------------------')
            print ('python3 martas_init.py')
            sys.exit()
        elif opt in ("-d", "--directory"):
            dir = arg
        elif opt in ("-r", "--redo"):
            redo = True
        elif opt in ("-u", "--update"):
            update = True
        elif opt in ("-U", "--UPDATE"):
            minimalupdate = True
        elif opt in ("-D", "--debug"):
            debug = True

    # get home directory of current user
    homedir = os.getenv("HOME")

    envact = ""
    # get the environment
    try:
        # Scan for conda environment
        env = os.environ["CONDA_PREFIX"]
        # will cause a KEY ERROR if not existing
        envname = os.path.basename(os.path.normpath(env))
        if env.endswith("envs/{}".format(envname)):
            envact = "conda activate {}".format(envname)
        else:
            envact = "conda activate base"
    except:
        # No conda environment - test for virtualenv
        try:
            env = os.environ["VIRTUAL_ENV"]
            envact = "source {}".format(os.path.join(env,"bin","activate"))
        except:
            pass

    # get the martas package path
    file_path = os.path.dirname(martas.__file__)
    if not debug:
        os.makedirs(os.path.join(homedir,dir), exist_ok=True)
        # create sudirs
        os.makedirs(os.path.join(homedir,dir,"log"), exist_ok=True)
    #
    # copy files into subdirs
    if update or minimalupdate:
        print ("Updating app, doc and web to MARTAS version {}".format(__version__))
        shutil.rmtree(os.path.join(homedir, dir, "app"),ignore_errors=True)
        shutil.rmtree(os.path.join(homedir, dir, "doc"),ignore_errors=True)
        shutil.rmtree(os.path.join(homedir, dir, "web"),ignore_errors=True)
    if redo:
        shutil.rmtree(os.path.join(homedir, dir, "app"),ignore_errors=True)
        shutil.rmtree(os.path.join(homedir, dir, "conf"),ignore_errors=True)
        shutil.rmtree(os.path.join(homedir, dir, "doc"),ignore_errors=True)
        shutil.rmtree(os.path.join(homedir, dir, "init"),ignore_errors=True)
        shutil.rmtree(os.path.join(homedir, dir, "logrotate"),ignore_errors=True)
        shutil.rmtree(os.path.join(homedir, dir, "web"),ignore_errors=True)
    if not os.path.isdir(os.path.join(homedir,dir,"conf")):
        shutil.copytree(os.path.join(file_path, "conf"), os.path.join(homedir, dir, "conf"))
    if not os.path.isdir(os.path.join(homedir,dir,"app")):
        shutil.copytree(os.path.join(file_path, "app"), os.path.join(homedir, dir, "app"))
    if not os.path.isdir(os.path.join(homedir,dir,"doc")):
        shutil.copytree(os.path.join(file_path, "doc"), os.path.join(homedir, dir, "doc"))
    if not os.path.isdir(os.path.join(homedir,dir,"init")):
        shutil.copytree(os.path.join(file_path, "init"), os.path.join(homedir, dir, "init"))
    if not os.path.isdir(os.path.join(homedir,dir,"logrotate")):
        shutil.copytree(os.path.join(file_path, "logrotate"), os.path.join(homedir, dir, "logrotate"))
    if not os.path.isdir(os.path.join(homedir,dir,"scripts")):
        shutil.copytree(os.path.join(file_path, "scripts"), os.path.join(homedir, dir, "scripts"))
    if not os.path.isdir(os.path.join(homedir,dir,"web")):
        shutil.copytree(os.path.join(file_path, "web"), os.path.join(homedir, dir, "web"))
    #shutil.copyfile(os.path.join(file_path, "collector.py"), os.path.join(homedir, dir, "collector.py"))
    #shutil.copyfile(os.path.join(file_path, "acquisition.py"), os.path.join(homedir, dir, "acquisition.py"))
    #
    confpath = "/tmp"
    initpath = "/tmp"
    logpath = "/tmp"
    malogpath = "/tmp/martas.log"
    jobname = "martas"
    marcosjob = "marcos"
    initjob = "MARTAS"
    stationname = "WIC"
    mqttbroker = "localhost"
    mqttport = "1883"
    mqttqos = "1"
    mqttcred = ""
    backuppath = os.path.join(homedir, "backups")
    bufferpath = os.path.join(homedir, "MARTAS", "mqtt")
    archivepath = os.path.join(homedir, "MARCOS", "archive") # i.e. /home/USER/MARCOS/archive
    archivelog = "/tmp/archivestatus.log"
    monitorlog = "/tmp/monitorstatus.log"
    thresholdlog = "/tmp/thresholdstatus.log"
    thresholdsource = "file"
    destination = "stdout"
    filepath = "/tmp"
    databasecredentials = "mydb"
    payloadformat = "martas"
    noti = "telegram"
    mailcred = "mymailcred"
    mainpath = os.path.join(homedir,dir) # i.e. /home/USER/.martas
    pskcredentials = ""
    mqttcert = ""
    addtelegrambot = False


    if minimalupdate:
        print (" ------------------------------------------- ")
        print (" application, web and documentfolder have been updated")
        print (" ------------------------------------------- ")
        sys.exit(0)

    cronlist = []
    print (" ------------------------------------------- ")
    print ("""               You started the MARTAS initialization routine.
               Please provide some additional information so
               that MARTAS or MARCOS can be set up correctly.
               BEFORE CONTINUING:
               - MARTAS/MARCOS: make sure you have e-mail/telegram credentials
               - MARTAS/MARCOS: make sure you have MQTT credentials
               - MARTAS: accessible buffer directory
               - MARCOS: archiving requires accessible directory path
               - MARCOS: if you want to use a MySQL/Maria database
                         * install MariaDB and create an empty DB (see manual)
                         * credentials
                         * percona installed (apt install percona)
               - MARTAS: sensors need to be setup manually after init
               PLEASE NOTE: After finishing the setup you
               can modify all configurations manually anytime.
               Please consult the manual. """)

    print (" ------------------------------------------- ")
    print (" Please insert a path for the main configuration files:")
    print (" (press return for accepting the default: {})".format(os.path.join(homedir,dir,"conf")))
    newconfpath = input()
    if newconfpath:
        if not os.path.isdir(newconfpath):
            print ("  ! the selected directory is not yet existing - aborting")
            sys.exit()
        if not os.access(newconfpath, os.W_OK):
            print (" ! you don't have write access to the specific directory - aborting")
            sys.exit()
        confpath = newconfpath
        shutil.copytree(os.path.join(homedir, dir, "conf"), confpath)
    else:
        confpath = os.path.join(homedir,dir,"conf")
    shutil.copyfile(os.path.join(confpath, "archive.cfg"), os.path.join(confpath, "archive.bak"))
    shutil.copyfile(os.path.join(confpath, "basevalue.cfg"), os.path.join(confpath, "basevalue.bak"))
    shutil.copyfile(os.path.join(confpath, "download-source.cfg"), os.path.join(confpath, "download-source.bak"))
    shutil.copyfile(os.path.join(confpath, "fileuploadjobs.json"), os.path.join(confpath, "fileuploadjobs.bak"))
    shutil.copyfile(os.path.join(confpath, "filter.cfg"), os.path.join(confpath, "filter.bak"))
    shutil.copyfile(os.path.join(confpath, "gamma.cfg"), os.path.join(confpath, "gamma.bak"))
    shutil.copyfile(os.path.join(confpath, "mail.cfg"), os.path.join(confpath, "mail.bak"))
    shutil.copyfile(os.path.join(confpath, "monitor.cfg"), os.path.join(confpath, "monitor.bak"))
    shutil.copyfile(os.path.join(confpath, "martas.cfg"), os.path.join(confpath, "martas.bak"))
    shutil.copyfile(os.path.join(confpath, "marcos.cfg"), os.path.join(confpath, "marcos.bak"))
    shutil.copyfile(os.path.join(confpath, "obsdaq.cfg"), os.path.join(confpath, "obsdaq.bak"))
    shutil.copyfile(os.path.join(confpath, "sensors.cfg"), os.path.join(confpath, "sensors.bak"))
    shutil.copyfile(os.path.join(confpath, "telegram.cfg"), os.path.join(confpath, "telegram.bak"))
    shutil.copyfile(os.path.join(confpath, "threshold.cfg"), os.path.join(confpath, "threshold.bak"))
    shutil.copyfile(os.path.join(confpath, "telegrambot.cfg"), os.path.join(confpath, "telegrambot.bak"))
    shutil.copyfile(os.path.join(homedir, dir, "scripts", "cleanup.sh"), os.path.join(homedir, dir, "scripts", "cleanup.bak"))

    print (" ------------------------------------------- ")
    print (" Please insert a path for log files:")
    print (" (press return for accepting default: {})".format(os.path.join(homedir,dir,"log")))
    newlogpath = input()
    if newlogpath:
        if not os.path.isdir(newlogpath):
            print ("  ! the selected directory is not yet existing - aborting")
            sys.exit()
        if not os.access(newlogpath, os.W_OK):
            print (" ! you don't have write access to the specific directory - aborting")
            sys.exit()
        logpath = newlogpath
        shutil.copytree(os.path.join(homedir, dir, "log"), logpath)
    else:
        logpath = os.path.join(homedir,dir,"log")

    print (" ------------------------------------------- ")
    print (" Please insert a station ID (i.e. the three letter observatory code, like WIC)")
    print (" (please note: station code is converted to lower case for martas mqtt topics)")
    print (" (press return for accepting default: {})".format(stationname))
    newstationname = input()
    if newstationname:
        stationname = ''.join(filter(str.isalnum, newstationname))
    print (" -> Station ID: {}".format(stationname))

    print (" ------------------------------------------- ")
    print (" Please insert a destination path for regular backups (default is ~/backups)")
    print (' (please insert "none" if you do not want regular backups of the martas system)')
    print (" (press return for accepting default: {})".format(os.path.join(homedir,"backups")))
    newbackuppath = input()
    if newstationname and not newstationname in ["NONE","none","no","n","NO","None","N"]:
        backupath = newbackuppath
    elif newstationname in ["NONE","none","no","n","NO","None","N"]:
        backuppath = ""
    print (" -> Station ID: {}".format(stationname))

    print (" ------------------------------------------- ")
    print (" Please insert the address of the MQTT broker:")
    print ("  MARTAS: the brocker on which you publish data")
    print ("  MARCOS: the broker to which you subscribe")
    print (" (press return for accepting default: {})".format(mqttbroker))
    newmqttbroker = input()
    if newmqttbroker:
        mqttbroker = newmqttbroker
    print (" -> MQTT broker address: {}".format(mqttbroker))

    print(" ------------------------------------------- ")
    print(" Port of MQTT broker (default = {}):".format(mqttport))
    newmqttport = input()
    if newmqttport:
        mqttport = newmqttport
    if int(mqttport) >= 8883:
        print(" MQTT security based on TLS:")
        print(" please choose: (1) TLS-PSK encryption, (2) TLS on certificate basis")
        print(" (1) requires an available PSK identity and password - AND - pip install sslpsk2")
        print(" (2) to be used for IM MQTT service")
        secsel = input()
        if secsel in ["1"]:
            print("  TLS-PSK: please insert a credential shortcut for a valid psk identity.")
            print("           Needs to be different to user credentials.")
            newpskcred = input()
            if newpskcred:
                # check whether existing
                pskcredentials = newpskcred
                # if not create
            val = cred.lc(pskcredentials, "user")
            if not val:
                print("  ---- ")
                print("  PSK Shortcut not yet existing - creating it: ")
                print("  Insert your PSK identity:")
                pskuser = input()
                print("  Insert PSK:")
                pskpwd = getpass.getpass()
                cred.cc("transfer", pskcredentials, user=pskuser, passwd=pskpwd, address=mqttbroker, port=int(mqttport))
            print(" -> MQTT psk identifier: {}".format(pskcredentials))
        elif secsel in ["2"]:
            print("  TLS with certificate: please insert path to ca.cert; leave empty for IM MQTT service")
            newmqttcert = input()
            if newmqttcert:
                if not os.path.isfile(newmqttcert):
                    print("  ! the selected ca.cert file is not existing")
                    print("  ! please update martas.cfg afterwards")
                mqttcert = newmqttcert
            print(" -> MQTT certificate: {}".format(mqttcert))

    print(" -> MQTT broker port: {}".format(mqttport))

    print (" ------------------------------------------- ")
    print (" MQTT transmission using quality of service (QOS): (default=1)".format(mqttqos))
    print ( " (can be 0,1,2 )")
    newmqttqos = input()
    if newmqttqos:
        if not newmqttqos in ["0","1","2"]:
            newmqttqos = "1"
        mqttqos = newmqttqos
    print (" -> MQTT QOS: {}".format(mqttqos))

    print (" ------------------------------------------- ")
    print (" MQTT authentication shortcut (default emtpy ='not required'):")
    print (" (authentication credentials are created/provided by MagPy's cred module)")
    newmqttcred = input()
    if newmqttcred:
        # check whether existing
        mqttcred = newmqttcred
        # if not create
        val = cred.lc(newmqttcred, "user")
        if not val:
            print("  ---- ")
            print("  Shortcut not yet existing - creating it: ")
            print("  Insert username of MQTT broker:")
            mqttuser = input()
            print("  Insert password of MQTT broker:")
            mqttpwd = getpass.getpass()
            #mqttpwd = input()
            cred.cc("transfer",newmqttcred,user=mqttuser,passwd=mqttpwd,address=mqttbroker,port=int(mqttport))
    print (" -> MQTT credentials: {}".format(mqttcred))


    print (" ------------------------------------------- ")
    print (" Notifications preference:")
    print ("  Select one of the following notification techniques: log, email, telegram.")
    print ("  Default is telegram.")
    newnot = input()
    notipath = os.path.join(confpath, "telegram.cfg")
    if newnot and newnot in ["log","email","telegram"]:
        # check whether existing
        noti = newnot
        print (" -> notification by: {}".format(noti))

    if noti == "email":
        print (" ------------------------------------------- ")
        print (" E-mail notifications:")
        print ("  Provide the addcred credential shortcut:")
        newmailcred = input()
        if newmailcred:
            # check whether existing
            mailcred = newmailcred
            val = cred.lc(newmailcred, "user")
            if not val:
                print (" ! Mail credentials do not yet exist - please create them to use email notifications")
            print (" -> E-mail credentials: {}".format(mailcred))
        notipath = os.path.join(confpath, "mail.cfg")
        print("  For email notification please update mail.cfg in your configuration directory.")
    elif noti == "telegram":
        print(" ------------------------------------------- ")
        print(" Telegram notifications:")
        print("  For telegram notification please update telegram.cfg in your configuration directory.")
        notipath = os.path.join(confpath, "telegram.cfg")
    else:
        pass

    print (" ------------------------------------------- ")
    print (" Two-way communication:")
    print ("  Do you want to establish a two-way communication using telegram?")
    print ("  Yes[y] or No[n] (default)")
    print ("  Please consider the manual for secure configuration and then update conf/telegrambot.cfg")
    print ("  You will also need to install telepot: pip install telepot")
    print ("  before using two communication.")
    newaddtelegrambot = input()
    if newaddtelegrambot in ["Yes", "YES", "Y", "y"]:
        addtelegrambot = True
        print(" -> creating a TELEGRAM BOT run time script (requires inputs in conf/telegrambot.cfg before running)")
        runscript = []
        runscript.append("#! /bin/bash")
        runscript.append("# TELEGRAM communication program")
        runscript.append("")
        runscript.append("{}".format(envact))
        runscript.append("")
        runscript.append('PYTHON={}'.format(sys.executable))
        runscript.append('BOT="telegrambot.py"')
        runscript.append('BOTPATH={}'.format(os.path.join(homedir, dir, "app")))
        runscript.append("")
        runscript.append('check_process()')
        runscript.append("{")
        runscript.append("    result=`/bin/ps aux | grep \"$BOT\" | grep -v grep | wc -l`")
        runscript.append("}")
        runscript.append('get_pid()')
        runscript.append("{")
        runscript.append("    pid=`/bin/ps -ef | grep \"$BOT\" | grep -v \"grep\" | awk '{print $2}'`")
        runscript.append("}")
        runscript.append("")
        runscript.append("check_process")
        runscript.append("# Run it")
        runscript.append("# ######")
        runscript.append("case \"$1\" in")
        runscript.append("  start)")
        runscript.append("    echo \"Starting $BOT ...\"")
        runscript.append("    check_process")
        runscript.append("    if [ \"$result\" = \"0\" ]; then")
        runscript.append("        echo \" $BOT is not running\"")
        runscript.append("        echo \" Starting $BOT\"")
        runscript.append("        echo \" --------------------\"")
        runscript.append("        sleep 2")
        runscript.append("        $PYTHON --version")
        runscript.append("        $PYTHON $BOTPATH/$BOT")
        runscript.append("    else")
        runscript.append("        echo \"$BOT is running already\"")
        runscript.append("    fi")
        runscript.append("    ;;")
        runscript.append("  stop)")
        runscript.append("    echo \"Stopping $BOT ...\"")
        runscript.append("    check_process")
        runscript.append("    if [ \"$result\" = \"0\" ]; then")
        runscript.append("        echo \" $BOT is not running\"")
        runscript.append("    else")
        runscript.append("        echo \" Stopping $BOT\"")
        runscript.append("        echo \" --------------------\"")
        runscript.append("        get_pid")
        runscript.append("        kill -9 $pid")
        runscript.append("        echo \" ... stopped\"")
        runscript.append("    fi")
        runscript.append("    ;;")
        runscript.append("  restart)")
        runscript.append("    echo \"Restarting $BOT ...\"")
        runscript.append("    check_process")
        runscript.append("    if [ \"$result\" = \"1\" ]; then")
        runscript.append("        echo \" Stopping $BOT\"")
        runscript.append("        get_pid")
        runscript.append("        kill -9 $pid")
        runscript.append("        echo \" ... stopped\"")
        runscript.append("    fi")
        runscript.append("    echo \" Starting $BOT\"")
        runscript.append("    echo \"--------------------\"")
        runscript.append("    sleep 2")
        runscript.append("    $PYTHON --version")
        runscript.append("    $PYTHON $BOTPATH/$BOT")
        runscript.append("    ;;")
        runscript.append("  status)")
        runscript.append("    check_process")
        runscript.append("    if [ \"$result\" = \"0\" ]; then")
        runscript.append("        echo \"$BOT is dead\"")
        runscript.append("    else")
        runscript.append("        echo \"$BOT is running\"")
        runscript.append("    fi")
        runscript.append("    ;;")
        runscript.append("  *)")
        runscript.append("    echo \"Usage: bash runbot.sh {start|stop|restart|status}\"")
        runscript.append("    ;;")
        runscript.append("esac")
        runscript.append("exit 0")
        with open(os.path.join(homedir, dir, "runbot.sh"), "wt") as fout:
            for line in runscript:
                fout.write(line+"\n")

    print (" ------------------------------------------- ")
    print (" Please select - you are initializing (A) a acquisition/MARTAS or (B) a collector/MARCOS")
    print (" ( select either A (default) or B )")
    initselect = input()
    if initselect in ["B","b"]:
        initjob = "MARCOS"
        print("  -> selected MARCOS")
    else:
        print("  -> selected MARTAS")

    monitorlog = os.path.join(os.path.join(logpath, "monitorstatus.log"))

    if initjob == "MARTAS":
        print (" ------------------------------------------- ")
        print (" Please insert a path for the sensor initialization files:")
        print (" (press return for accepting the default: {})".format(os.path.join(homedir,dir,"init")))
        newinitpath = input()
        if newinitpath:
            if not os.path.isdir(newinitpath):
                print("  ! the selected directory is not yet existing - aborting")
                sys.exit()
            if not os.access(newinitpath, os.W_OK):
                print(" ! you don't have write access to the specific directory - aborting")
                sys.exit()
            initpath = newinitpath
            shutil.copytree(os.path.join(homedir, dir, "init"), initpath)
        else:
            initpath = os.path.join(homedir, dir, "init")

        print (" ------------------------------------------- ")
        print (" Please insert a path for buffer files:")
        print (" (make sure it is existing and you have write permissions)".format(bufferpath))
        print (" (press return for accepting the default: {})".format(bufferpath))
        newbufferpath = input()
        if newbufferpath:
            bufferpath = newbufferpath
        if not os.path.isdir(bufferpath):
            print("  the selected directory is not yet existing - trying to create it...")
            try:
                Path(bufferpath).mkdir(parents=True, exist_ok=True)
                print("  done")
            except:
                print("  ! failed, check permissions - aborting")
                sys.exit()
        if not os.access(bufferpath, os.W_OK):
            print(" ! you don't have write access to the specific directory - aborting")
            sys.exit()

        print (" ------------------------------------------- ")
        print (" Please specify the MQTT payload format:")
        print (" (currently supported are 'martas' and 'intermagnet')")
        print (" ('intermagnet' is only available for mysql and imfile libraries)")
        print (" (default is 'martas')")
        newpayloadformat = input()
        if newpayloadformat == 'intermagnet':
            payloadformat = 'intermagnet'

        malogpath = os.path.join(logpath, "martas.log")

        print(" ------------------------------------------- ")
        print(" Creating the MARTAS run time script")
        runscript = []
        runscript.append("#! /bin/bash")
        runscript.append("# MARTAS acquisition program")
        runscript.append("")
        runscript.append("{}".format(envact))
        runscript.append("")
        runscript.append('PYTHON={}'.format(sys.executable))
        runscript.append('BOT="acquisition"')
        runscript.append('OPT="-m {}"'.format(os.path.join(confpath, "martas.cfg")))
        runscript.append("")
        runscript.append('check_process()')
        runscript.append("{")
        runscript.append("    result=`/bin/ps aux | grep \"$BOT $OPT\" | grep -v grep | wc -l`")
        runscript.append("}")
        runscript.append('get_pid()')
        runscript.append("{")
        runscript.append("    pid=`/bin/ps -ef | grep \"$BOT $OPT\" | grep -v \"grep\" | awk '{print $2}'`")
        runscript.append("}")
        runscript.append("")
        runscript.append("check_process")
        runscript.append("# Run it")
        runscript.append("# ######")
        runscript.append("case \"$1\" in")
        runscript.append("  start)")
        runscript.append("    echo \"Starting $BOT ...\" ")
        runscript.append("    check_process")
        runscript.append("    if [ \"$result\" = \"0\" ]; then")
        runscript.append("        echo \" $BOT is not running\" ")
        runscript.append("        echo \" Starting $BOT\"")
        runscript.append("        echo \" --------------------\"")
        runscript.append("        sleep 2")
        runscript.append("        $PYTHON --version")
        runscript.append("        $BOT $OPT")
        runscript.append("    else")
        runscript.append("        echo \"$BOT is running already\" ")
        runscript.append("    fi")
        runscript.append("    ;;")
        runscript.append("  stop)")
        runscript.append("    echo \"Stopping $BOT $OPT ...\" ")
        runscript.append("    check_process")
        runscript.append("    if [ \"$result\" = \"0\" ]; then")
        runscript.append("        echo \" $BOT is not running\" ")
        runscript.append("    else")
        runscript.append("        echo \" Stopping $BOT\"")
        runscript.append("        echo \" --------------------\"")
        runscript.append("        get_pid")
        runscript.append("        kill -9 $pid")
        runscript.append("        echo \" ... stopped\"")
        runscript.append("    fi")
        runscript.append("    ;;")
        runscript.append("  restart)")
        runscript.append("    echo \"Restarting $BOT $OPT ...\" ")
        runscript.append("    check_process")
        runscript.append("    if [ \"$result\" = \"1\" ]; then")
        runscript.append("        echo \" Stopping $BOT\" ")
        runscript.append("        get_pid")
        runscript.append("        kill -9 $pid")
        runscript.append("        echo \" ... stopped\"")
        runscript.append("    fi")
        runscript.append("    echo \" Starting $BOT\"")
        runscript.append("    echo \"--------------------\"")
        runscript.append("    sleep 2")
        runscript.append("    $PYTHON --version")
        runscript.append("    $BOT $OPT")
        runscript.append("    ;;")
        runscript.append("  status)")
        runscript.append("    check_process")
        runscript.append("    if [ \"$result\" = \"0\" ]; then")
        runscript.append("        echo \"$BOT $OPT is dead\" ")
        runscript.append("    else")
        runscript.append("        echo \"$BOT $OPT is running\" ")
        runscript.append("    fi")
        runscript.append("    ;;")
        runscript.append("  *)")
        runscript.append("    echo \"Usage: $BOT {start|stop|restart|status}\"")
        runscript.append("    ;;")
        runscript.append("esac")
        runscript.append("exit 0")
        with open(os.path.join(homedir, dir, "runmartas.sh"), "wt") as fout:
            for line in runscript:
                fout.write(line+"\n")

        print(" ------------------------------------------- ")
        print(" Creating the MARTAS viewer")
        viewscript = []
        viewscript.append("#! /bin/bash")
        viewscript.append("# MARTAS viewer")
        viewscript.append("")
        viewscript.append("pkill -f martas_view.py")
        viewscript.append('cd {}'.format(os.path.join(homedir,dir,"web")))
        viewscript.append('PYTHON={}'.format(sys.executable))
        viewscript.append('VIEW="{}"'.format(os.path.join(homedir,dir,"web","martas_view.py")))
        viewscript.append("$PYTHON $VIEW")
        viewscript.append("xdg-open http://127.0.0.1:8050")
        with open(os.path.join(homedir, dir, "martas_view"), "wt") as fout:
            for line in viewscript:
                fout.write(line+"\n")

        cronlist.append("# Running MARTAS ")
        cronlist.append("15  0,6,12,18  * * *    /usr/bin/bash -i {} start > {} 2>&1".format(os.path.join(homedir, dir,"runmartas.sh"),os.path.join(homedir, dir, "log","runmartas.log")))
        cronlist.append("# Monitoring {} - hourly".format(jobname)) # jobname only for MARTAS

        with CronTab(user=True) as cron:
            comment = 'Running MARTAS'
            line = "/usr/bin/bash -i {} start > {} 2>&1".format(os.path.join(homedir, dir, "runmartas.sh"),
                                                          os.path.join(logpath, "runmartas.log"))
            if not list(cron.find_comment(comment)):
                job = cron.new(command=line, comment=comment)
                job.setall('15 0 * * *')
            macomment2 = "Start MARTAS viewer"
            maline2 = "/usr/bin/bash -i {} > {} 2>&1".format(os.path.join(homedir, dir, "martas_view"),
                                                          os.path.join(logpath, "martas_view.log"))
            if not list(cron.find_comment(macomment2)):
                job2 = cron.new(command=maline2, comment=macomment2)
                job2.setall('16 0 * * *')
                job2.enable(False)

        #print('cron.write() was just executed')

    elif initjob == "MARCOS":
        print (" You can have multiple collector jobs on one machine.")
        print (" Make sure they have different names.")
        print (" ------------------------------------------- ")
        print (" Please insert a name for the collector:")
        print (" (press return for accepting default: {})".format(jobname))
        print (" (the given name will be extended 'collect-NAME')")
        print (" (ideally you provide the name of the MARTAS from which you are collecting data)")
        newjobname = input()
        if newjobname:
            jobname = ''.join(filter(str.isalnum, newjobname))
        print (" -> MARCOS job name: {}".format(jobname))
        marcosjob = "collect-{}".format(jobname)

        print (" ------------------------------------------- ")
        print (" Please specify an output destination:")
        print (" (choose from stdout, db, file, websocket, diff)")
        print (" (multiple selections i.e. file,db are possible)")
        newdestination = input()
        if newdestination:
            valid = ["stdout", "db", "file", "websocket", "diff"]
            if any(s in newdestination for s in valid):
                pass
            else:
                print("  ! invalid destination - aborting")
                sys.exit()
            destination = newdestination

        if destination.find("file") >= 0:
            print (" ------------------------------------------- ")
            print (" Please specify a path to store files:")
            filepath = input()
            if not os.path.isdir(filepath):
                print ("  ! the selected directory is not yet existing - please create and re-run martas-init - aborting now")
                sys.exit()
            if not os.access(filepath, os.W_OK):
                print (" ! you don't have write access - aborting")
                sys.exit()

        if destination.find("db") >= 0:
            print (" ------------------------------------------- ")
            print (" Please specify credentials (see addcred) for database:")
            newdatabasecredentials = input()
            if newdatabasecredentials:
                val = cred.lc(newdatabasecredentials, "user")
                if not val:
                    print (" ! Database credentials do not exist")
                databasecredentials = newdatabasecredentials

        print (" ------------------------------------------- ")
        print (" MARCOS will archive database contents in CDF files by default.")
        print(" Please provide a path for the data archive (default: {}):".format(archivepath))
        newarchivepath = input()
        if newarchivepath:
            archivepath = newarchivepath
        if not os.path.isdir(archivepath):
            print("  the selected directory is not yet existing - trying to create it...")
            try:
                Path(archivepath).mkdir(parents=True, exist_ok=True)
                print("  done")
            except:
                print("  ! failed, check permissions and re-run martas-init - aborting")
                sys.exit()
        if not os.access(archivepath, os.W_OK):
            print (" ! you don't have write access - select an appropriate path and re-run martas-init - aborting")
            sys.exit()

        print(" ------------------------------------------- ")
        print(" Threshold tester can be used on archive or db.")
        defaultsource = "db"
        if not destination.find("db") >= 0:
            defaultsource = "file"
            print(" Please enter 'db' or 'file' (default):")
        else:
            print(" Please enter 'db' (default) or 'file':")
        newthresholdsource = input()
        if newthresholdsource in ['db','file']:
            thresholdsource = newthresholdsource
        else:
            thresholdsource = defaultsource

        malogpath = os.path.join(logpath, "{}.log".format(marcosjob))
        archivelog = os.path.join(logpath, "archivestatus.log")

        print(" ------------------------------------------- ")
        print(" Creating the MARCOS run time script for {}".format(jobname))
        runscript = []
        runscript.append("#! /bin/bash")
        runscript.append("# MARCOS acquisition program")
        runscript.append("")
        runscript.append("{}".format(envact))
        runscript.append("")
        runscript.append('PYTHON={}'.format(sys.executable))
        runscript.append('BOT="collector"')
        runscript.append('OPT="-m {}"'.format(os.path.join(confpath, "{}.cfg".format(marcosjob))))
        runscript.append("")
        runscript.append('check_process()')
        runscript.append("{")
        runscript.append("    result=`ps aux | grep \"$BOT $OPT\" | grep -v grep | wc -l`")
        runscript.append("}")
        runscript.append('get_pid()')
        runscript.append("{")
        runscript.append("    pid=`/bin/ps -ef | grep \"$BOT $OPT\" | grep -v \"grep\" | awk '{print $2}'`")
        runscript.append("}")
        runscript.append("")
        runscript.append("check_process")
        runscript.append("# Run it")
        runscript.append("# ######")
        runscript.append("case \"$1\" in")
        runscript.append("  start)")
        runscript.append("    echo \"Starting $BOT $OPT ...\" ")
        runscript.append("    check_process")
        runscript.append("    if [ \"$result\" = \"0\" ]; then")
        runscript.append("        echo \" $BOT is not running\" ")
        runscript.append("        echo \" Starting $BOT\"")
        runscript.append("        echo \" --------------------\"")
        runscript.append("        sleep 2")
        runscript.append("        $PYTHON --version")
        runscript.append("        $BOT $OPT")
        runscript.append("    else")
        runscript.append("        echo \"$BOT is running already\" ")
        runscript.append("    fi")
        runscript.append("    ;;")
        runscript.append("  stop)")
        runscript.append("    echo \"Stopping $BOT $OPT ...\" ")
        runscript.append("    check_process")
        runscript.append("    if [ \"$result\" = \"0\" ]; then")
        runscript.append("        echo \" $BOT is not running\" ")
        runscript.append("    else")
        runscript.append("        echo \" Stopping $BOT\"")
        runscript.append("        echo \" --------------------\"")
        runscript.append("        get_pid")
        runscript.append("        kill -9 $pid")
        runscript.append("        echo \" ... stopped\"")
        runscript.append("    fi")
        runscript.append("    ;;")
        runscript.append("  restart)")
        runscript.append("    echo \"Restarting $BOT $OPT ...\" ")
        runscript.append("    check_process")
        runscript.append("    if [ \"$result\" = \"1\" ]; then")
        runscript.append("        echo \" Stopping $BOT\" ")
        runscript.append("        get_pid")
        runscript.append("        kill -9 $pid")
        runscript.append("        echo \" ... stopped\"")
        runscript.append("    fi")
        runscript.append("    echo \" Starting $BOT\"")
        runscript.append("    echo \"--------------------\"")
        runscript.append("    sleep 2")
        runscript.append("    $PYTHON --version")
        runscript.append("    $BOT $OPT")
        runscript.append("    ;;")
        runscript.append("  update)")
        runscript.append("    echo \"Starting $BOT $OPT with meta information update...\" ")
        runscript.append("    check_process")
        runscript.append("    if [ \"$result\" = \"1\" ]; then")
        runscript.append("        echo \" Stopping $BOT\" ")
        runscript.append("        get_pid")
        runscript.append("        kill -9 $pid")
        runscript.append("        echo \" ... stopped\"")
        runscript.append("    fi")
        runscript.append("    echo \" Starting $BOT\"")
        runscript.append("    echo \"--------------------\"")
        runscript.append("    sleep 2")
        runscript.append("    $PYTHON --version")
        runscript.append("    $BOT $OPT -v")
        runscript.append("    ;;")
        runscript.append("  status)")
        runscript.append("    check_process")
        runscript.append("    if [ \"$result\" = \"0\" ]; then")
        runscript.append("        echo \"$BOT $OPT is dead\" ")
        runscript.append("    else")
        runscript.append("        echo \"$BOT $OPT is running\" ")
        runscript.append("    fi")
        runscript.append("    ;;")
        runscript.append("  *)")
        runscript.append("    echo \"Usage: $BOT {start|stop|restart|status|update}\"")
        runscript.append("    ;;")
        runscript.append("esac")
        runscript.append("exit 0")
        with open(os.path.join(homedir, dir, "{}.sh".format(marcosjob)), "wt") as fout:
            for line in runscript:
                fout.write(line+"\n")

        print(" ------------------------------------------- ")
        print(" Creating the MARCOS viewer")
        viewscript = []
        viewscript.append("#! /bin/bash")
        viewscript.append("# MARCOS viewer")
        viewscript.append("")
        viewscript.append("pkill -f marcos_view.py")
        viewscript.append('cd {}'.format(os.path.join(homedir,dir,"web")))
        viewscript.append('PYTHON={}'.format(sys.executable))
        viewscript.append('VIEW="{}"'.format(os.path.join(homedir,dir,"web","marcos_view.py")))
        viewscript.append("$PYTHON $VIEW")
        viewscript.append("xdg-open http://127.0.0.1:8050")
        with open(os.path.join(homedir, dir, "marcos_view"), "wt") as fout:
            for line in viewscript:
                fout.write(line+"\n")


        with CronTab(user=True) as cron:
            comment1 = "Running MARCOS process {}".format(jobname)
            line1 = "/usr/bin/bash -i {} start > {} 2>&1".format(os.path.join(homedir, dir, marcosjob+".sh"),os.path.join(logpath, marcosjob+".log"))
            if not list(cron.find_comment(comment1)):
                job1 = cron.new(command=line1, comment=comment1)
                job1.setall('17 0 * * *')
            comment2 = "Archiving"
            line2 = "{} {} -c {} > {} 2>&1".format(sys.executable, os.path.join(homedir, dir,"app","archive.py"),os.path.join(confpath,"archive.cfg"), os.path.join(logpath,"archive.log"))
            if not list(cron.find_comment(comment2)):
                job2 = cron.new(command=line2, comment=comment2)
                job2.setall('20 0 * * *')
            comment2b = "Truncating old and none-DATAINFO tables"
            line2b = "{} {} -c {} > {} 2>&1".format(sys.executable, os.path.join(homedir, dir,"app","db_truncate.py"),os.path.join(confpath,"archive.cfg"), os.path.join(logpath,"db_truncate.log"))
            if not list(cron.find_comment(comment2b)):
                job2b = cron.new(command=line2b, comment=comment2b)
                job2b.setall('20 2 * * *')
            comment2a = "Filtering"
            line2a = "{} {} -c {} > {} 2>&1".format(sys.executable, os.path.join(homedir, dir,"app","filter.py"),os.path.join(confpath,"filter.cfg"), os.path.join(logpath,"filter.log"))
            if not list(cron.find_comment(comment2a)):
                job2a = cron.new(command=line2a, comment=comment2a)
                job2a.minute.every(2)
                job2a.enable(False)
            if destination.find("db") >= 0:
                comment3 = "Optimizing database"
                line3 = "{} {} -c {} -s sqlmaster > {} 2>&1".format(sys.executable, os.path.join(homedir, dir,"app","optimizetables.py"), os.path.join(confpath,"archive.cfg"), os.path.join(logpath,"optimizetables.log"))
                if not list(cron.find_comment(comment3)):
                    job3 = cron.new(command=line3, comment=comment3)
                    job3.setall('2 0 * * 2')
            mvcomment2 = "Start MARCOS viewer"
            mvline2 = "/usr/bin/bash -i {} > {} 2>&1".format(os.path.join(homedir, dir, "marcos_view"),
                                                          os.path.join(logpath, "marcos_view.log"))
            if not list(cron.find_comment(mvcomment2)):
                jobmv2 = cron.new(command=mvline2, comment=mvcomment2)
                jobmv2.setall('16 0 * * *')
                jobmv2.enable(False)
            mvcomment3 = "Optional: Regular download of buffer from MARCOS {}".format(jobname)
            mvline3 = "{} {} -c {} > {} 2>&1".format(sys.executable, os.path.join(homedir, dir,"app","file_download.py"),os.path.join(confpath,"download-{}.cfg".format(jobname)), os.path.join(logpath,"download-{}.log".format(jobname)))
            if not list(cron.find_comment(mvcomment3)):
                jobmv3 = cron.new(command=mvline3, comment=mvcomment3)
                jobmv3.setall('16 0 * * *')
                jobmv3.enable(False)

    with CronTab(user=True) as cron:
        if initjob == "MARCOS":
            comment4 = "Monitoring MARCOS - hourly"
        else:
            comment4 = "Monitoring MARTAS {} - hourly".format(jobname)
        line4 = "{} {} -c {} > {} 2>&1".format(sys.executable, os.path.join(homedir, dir,"app","monitor.py"),os.path.join(confpath,"monitor.cfg"), os.path.join(logpath,"monitor.log"))
        if not list(cron.find_comment(comment4)):
            job4 = cron.new(command=line4, comment=comment4)
            job4.setall('30 * * * *')
        comment5 = "Running cleanup"
        line5 = "/usr/bin/bash -i {} > {} 2>&1".format(os.path.join(homedir, dir, "scripts", "cleanup.sh"),
                                                                              os.path.join(logpath,
                                                                                           "cleanup.log"))
        if not list(cron.find_comment(comment5)):
            job5 = cron.new(command=line5, comment=comment5)
            job5.setall('9 0 * * *')

        if backuppath:
            comment6 = "Backup of MARTAS"
            line6 = "{} {} -b {} -d {} > {} 2>&1".format(sys.executable, os.path.join(homedir, dir,"app","backup.py"), os.path.join(homedir, dir), backuppath, os.path.join(logpath,"backup.log"))
            if not list(cron.find_comment(comment6)):
                job6 = cron.new(command=line6, comment=comment6)
                job6.setall('7 0 * * 1')
        comment7 = "Threshold testing - please configure before enabling"
        line7 = "{} {} -m {}".format(sys.executable, os.path.join(homedir, dir,"app","threshold.py"), os.path.join(confpath,"threshold.cfg"))
        if not list(cron.find_comment(comment7)):
            job7 = cron.new(command=line7, comment=comment7)
            job7.minute.every(10)
            job7.enable(False)
        comment8 = "Log rotation for {}".format(jobname)
        line8 = "/usr/sbin/logrotate -s {} {} > /dev/null 2>&1".format(os.path.join(homedir, dir, "logrotate", "logstate"), os.path.join(homedir, dir, "logrotate", "{}.logrotate".format(jobname)))
        if not list(cron.find_comment(comment8)):
            job8 = cron.new(command=line8, comment=comment8)
            job8.setall('3 1 * * *')

        if addtelegrambot:
            comment10 = "Telegram two-way communication bot"
            line10 = "/usr/bin/bash -i {} start 2>&1".format(os.path.join(homedir, dir, "runbot.sh"))
            if not list(cron.find_comment(comment10)):
                job10a = cron.new(command=line10, comment=comment10)
                job10a.setall('0 8 * * *')
                job10b = cron.new(command=line10, comment=comment10)
                job10b.setall('0 16 * * *')


    replacedict = { "/logpath" : malogpath,
                    "/sensorpath" : os.path.join(confpath, "sensors.cfg"),
                    "/initdir" : initpath,
                    "/mainpath" : os.path.join(homedir,dir),
                    "/homedirectory" : homedir,
                    "/srv/mqtt" : bufferpath,
                    "/obsdaqpath" : os.path.join(confpath, "obsdaq.cfg"),
                    "myhome" : stationname,
                    "outputdestination" : destination,
                    "filepath  :  /tmp" : "filepath  :  {}".format(filepath),
                    "/archivepath" : archivepath,
                    "archivelog" : archivelog,
                    "monitorlog" : monitorlog,
                    "thresholdlog" : os.path.join(logpath,"thresholdstatus.log"),
                    "collectlog" : os.path.join(logpath,"download-source.log"),
                    "filterlog" : os.path.join(logpath,"filterstatus.log"),
                    "basevaluelog" : os.path.join(logpath,"basevaluestatus.log"),
                    "/telegrambotlogpath" : os.path.join(logpath,"telegrambot.log"),
                    "thresholdsource" : thresholdsource,
                    "mynotificationtype" : noti,
                    "notificationcfg" : notipath,
                    "mymailcred" : mailcred,
                    "mydb" : databasecredentials,
                    "./web" : "{}".format(os.path.join(homedir, dir,"web")),
                    "brokeraddress" : mqttbroker,
                    "1883"  :  mqttport,
                    "mqttqos  :  0": "mqttqos  :  {}".format(mqttqos),
                    "payloadformat  :  martas": "payloadformat  :  {}".format(payloadformat),
                    "/home/username/.magpycred" : os.path.join(homedir, ".magpycred"),
                    }
    if mqttcred:
        replacedict["#mqttcred  :  shortcut"] = "mqttcred  :  {}".format(mqttcred)
    if mqttcert:
        replacedict["#mqttcert  :  /path/to/ca.crt"] = "mqttcert  :  {}".format(mqttcert)
    if pskcredentials:
        replacedict["#mqttpsk  :  pskcredentials"] = "mqttpsk  :  {}".format(pskcredentials)
    if backuppath:
        replacedict["/backuppath"] = backuppath

    files_to_change = {}
    if initjob == "MARTAS":
        replacedict["/mybasedir"] = bufferpath
        replacedict["space,martas,marcos,logfile"] = "space,martas,logfile"
        files_to_change["martasconf"] = {"source" : os.path.join(confpath, "martas.bak") ,
                                        "dest" : os.path.join(confpath, "martas.cfg") }

    if initjob == "MARCOS":
        replacedict["/mybasedir"] = archivepath
        replacedict["space,martas,marcos,logfile"] = "space,marcos"
        files_to_change["marcosconf"] = {"source" : os.path.join(confpath, "marcos.bak") ,
                                        "dest" : os.path.join(confpath, "{}.cfg".format(marcosjob)) }
        files_to_change["archiveconf"] = {"source": os.path.join(confpath, "archive.bak"),
                                     "dest": os.path.join(confpath, "archive.cfg")}
        files_to_change["basevalueconf"] = {"source": os.path.join(confpath, "basevalue.bak"),
                                     "dest": os.path.join(confpath, "basevalue.cfg")}
        files_to_change["filterconf"] = {"source": os.path.join(confpath, "filter.bak"),
                                         "dest": os.path.join(confpath, "filter.cfg")}
        files_to_change["downloadconf"] = {"source": os.path.join(confpath, "download-source.bak"),
                                           "dest": os.path.join(confpath, "download-{}.cfg".format(jobname))}
        # file for which replacements will happen and new names
    files_to_change["skeletonlogrotate"] = {"source": os.path.join(homedir, dir, "logrotate", "skeleton.logrotate"),
                              "dest": os.path.join(homedir, dir, "logrotate", "{}.logrotate".format(jobname))}
    files_to_change["fileuploadconf"] = {"source": os.path.join(confpath, "fileuploadjobs.bak"),
                        "dest": os.path.join(confpath, "fileuploadjobs.json")}
    files_to_change["monitorconf"] = {"source": os.path.join(confpath, "monitor.bak"),
                        "dest": os.path.join(confpath, "monitor.cfg")}
    files_to_change["thresholdconf"] = {"source": os.path.join(confpath, "threshold.bak"),
                        "dest": os.path.join(confpath, "threshold.cfg")}
    files_to_change["mailconf"] = {"source": os.path.join(confpath, "mail.bak"),
                        "dest": os.path.join(confpath, "mail.cfg")}
    files_to_change["gammaconf"] = {"source": os.path.join(confpath, "gamma.bak"),
                        "dest": os.path.join(confpath, "gamma.cfg")}
    files_to_change["cleanup"] = {"source": os.path.join(homedir, dir, "scripts", "cleanup.bak"),
                        "dest": os.path.join(homedir, dir, "scripts", "cleanup.sh")}
    files_to_change["telegrambot"] = {"source": os.path.join(confpath, "telegrambot.bak"),
                        "dest": os.path.join(confpath, "telegrambot.cfg")}


    for f in files_to_change:
        d = files_to_change.get(f)
        with open(d.get("source"), "rt") as fin:
            with open(d.get("dest"), "wt") as fout:
                for line in fin:
                    for el in replacedict:
                        if debug:
                            print ("Replacing", el, replacedict.get(el))
                        line = line.replace(el, replacedict.get(el))
                    fout.write(line)

    print("Crontab looks like:")
    print("\n".join(cronlist))
    print("Setup finished. SUCCESS")  # used for monitoring of logfile
    # end of init
    print("")  # used for monitoring of logfile
    print("Things to do:")
    if initjob == "MARTAS":
        print("- update sensors.cfg and add your connected sensors in {}".format(os.path.join(homedir,dir,"conf")))
        print("- eventually update your sensors initialization script if required")
    print("- check configuration files in {}".format(os.path.join(homedir,dir,"conf")))
    if initjob == "MARCOS":
        print("- update filter.cfg and activate filter job in crontab in case of > 1Hz data")
        print("- read the manual (again) for monitoring and threshold - activate/configure")
        print("- if you want regular downloads of buffer files in addition to MQTT then update the download job")
        print("- your collector job will be started tonight. Please start manually with upload option:")
        print("  bash collect-{}.sh update".format(jobname))
        print("  keep running for a few minutes. This will update the meta information in your database.")
    print("- you might want to add job restarts after rebooting into crontab:")
    print("  @reboot sleep 60 && bash -i /jobpath/runmartas.sh start > /logpath/runmartas.log 2>&1")

if __name__ == "__main__":
   main(sys.argv[1:])
