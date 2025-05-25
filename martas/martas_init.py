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


def main(argv):
    debug = False
    dir = ".martas"
    redo = False

    try:
        opts, args = getopt.getopt(argv,"hd:rD",["path=","redo=","debug=",])
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
            print ('-r, --redo : replace already existing configuration files')
            print ('           : ATTENTION: redo will delete all previous configurations')
            print ('-------------------------------------')
            print ('Application:')
            print ('-------------------------------------')
            print ('python3 martas_init.py')
            sys.exit()
        elif opt in ("-d", "--directory"):
            dir = arg
        elif opt in ("-r", "--redo"):
            redo = True
        elif opt in ("-D", "--debug"):
            debug = True

    # get home directory of current user
    homedir = os.getenv("HOME")

    import martas
    file_path = os.path.dirname(martas.__file__)
    print(file_path)
    if not debug:
        os.makedirs(os.path.join(homedir,dir), exist_ok=True)
        # create sudirs
        os.makedirs(os.path.join(homedir,dir,"log"), exist_ok=True)
    #
    # copy files into subdirs
    if redo:
        shutil.rmtree(os.path.join(homedir, dir, "app"),ignore_errors=True)
        shutil.rmtree(os.path.join(homedir, dir, "conf"),ignore_errors=True)
        shutil.rmtree(os.path.join(homedir, dir, "doc"),ignore_errors=True)
        shutil.rmtree(os.path.join(homedir, dir, "init"),ignore_errors=True)
        shutil.rmtree(os.path.join(homedir, dir, "install"),ignore_errors=True)
        shutil.rmtree(os.path.join(homedir, dir, "logrotate"),ignore_errors=True)
        shutil.rmtree(os.path.join(homedir, dir, "telegram"),ignore_errors=True)
        shutil.rmtree(os.path.join(homedir, dir, "web"),ignore_errors=True)
    if not os.path.isdir(os.path.join(homedir,dir,"conf")):
        shutil.copytree(os.path.join(file_path, "conf"), os.path.join(homedir, dir, "conf"))
    if not os.path.isdir(os.path.join(homedir,dir,"app")):
        shutil.copytree(os.path.join(file_path, "app"), os.path.join(homedir, dir, "app"))
    if not os.path.isdir(os.path.join(homedir,dir,"telegram")):
        shutil.copytree(os.path.join(file_path, "telegram"), os.path.join(homedir, dir, "telegram"))
    if not os.path.isdir(os.path.join(homedir,dir,"doc")):
        shutil.copytree(os.path.join(file_path, "doc"), os.path.join(homedir, dir, "doc"))
    if not os.path.isdir(os.path.join(homedir,dir,"init")):
        shutil.copytree(os.path.join(file_path, "init"), os.path.join(homedir, dir, "init"))
    if not os.path.isdir(os.path.join(homedir,dir,"install")):
        shutil.copytree(os.path.join(file_path, "install"), os.path.join(homedir, dir, "install"))
    if not os.path.isdir(os.path.join(homedir,dir,"logrotate")):
        shutil.copytree(os.path.join(file_path, "logrotate"), os.path.join(homedir, dir, "logrotate"))
    if not os.path.isdir(os.path.join(homedir,dir,"web")):
        shutil.copytree(os.path.join(file_path, "web"), os.path.join(homedir, dir, "web"))
    #shutil.copyfile(os.path.join(file_path, "collector.py"), os.path.join(homedir, dir, "collector.py"))
    #shutil.copyfile(os.path.join(file_path, "acquisition.py"), os.path.join(homedir, dir, "acquisition.py"))
    #
    confpath = "/tmp"
    initpath = "/tmp"
    logpath = "/tmp"
    jobname = "martas"
    marcosjob = "marcos"
    mailcred = ""
    initjob = "MARTAS"
    stationname = "WIC"
    mqttbroker = "localhost"
    mqttport = "1883"
    mqttqos = "1"
    mqttcred = ""
    bufferpath = "/srv/mqtt"
    archivepath = "/srv/archive"
    archivelog = "/tmp/archivestatus.log"
    monitorlog = "/tmp/monitor.log"
    destination = "stdout"
    filepath = "/tmp"
    databasecredentials = "mydb"
    payloadformat = "martas"
    noti = "telegram"

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
    shutil.copyfile(os.path.join(confpath, "gamma.cfg"), os.path.join(confpath, "gamma.bak"))
    shutil.copyfile(os.path.join(confpath, "monitor.cfg"), os.path.join(confpath, "monitor.bak"))
    shutil.copyfile(os.path.join(confpath, "martas.cfg"), os.path.join(confpath, "martas.bak"))
    shutil.copyfile(os.path.join(confpath, "marcos.cfg"), os.path.join(confpath, "marcos.bak"))
    shutil.copyfile(os.path.join(confpath, "obsdaq.cfg"), os.path.join(confpath, "obsdaq.bak"))
    shutil.copyfile(os.path.join(confpath, "sensors.cfg"), os.path.join(confpath, "sensors.bak"))
    shutil.copyfile(os.path.join(confpath, "telegram.cfg"), os.path.join(confpath, "telegram.bak"))
    shutil.copyfile(os.path.join(confpath, "threshold.cfg"), os.path.join(confpath, "threshold.bak"))

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
    print (" Please insert the address of the MQTT broker:")
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
            import getpass
            mqttpwd = getpass.getpass()
            #mqttpwd = input()
            cred.cc("transfer",newmqttcred,user=mqttuser,passwd=mqttpwd,address=mqttbroker,port=int(mqttport))
    print (" -> MQTT credentials: {}".format(mqttcred))


    print (" ------------------------------------------- ")
    print (" Notifications preference:")
    print ("  Select one of the following notification techniques: log, email, telegram.")
    print ("  Default is telegram.")
    print ("  For telegram notification please update telegram.cfg in your configuration directory.")
    newnot = input()
    if newnot and newnot in ["log","email","telegram"]:
        # check whether existing
        noti = newnot
        print (" -> notification by: {}".format(noti))


    print (" ------------------------------------------- ")
    print (" E-mail notifications:")
    print ("  Provide the credential shortcut of MagPy's cred module.")
    print ("  Otherwise press return.")
    newmailcred = input()
    if newmailcred:
        # check whether existing
        mailcred = newmailcred
        val = cred.lc(newmailcred, "user")
        if not val:
            print (" ! Mail cerdential do not exist")
        print (" -> E-mail credentials: {}".format(mailcred))


    print (" ------------------------------------------- ")
    print (" Please select - you are initializing (A) a acquisition/MARTAS or (B) a collector/MARCOS")
    print (" ( select either A (default) or B )")
    initselect = input()
    if initselect in ["B","b"]:
        initjob = "MARCOS"
        print("  -> selected MARCOS")
    else:
        print("  -> selected MARTAS")

    monitorlog = os.path.join(os.path.join(homedir, dir, "log", "monitor.log"))

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
            if not os.path.isdir(newbufferpath):
                print("  the selected directory is not yet existing - trying to create it...")
                try:
                    Path(newbufferpath).mkdir(parents=True, exist_ok=True)
                    print("  done")
                except:
                    print("  ! failed, check permissions - aborting")
                    sys.exit()
            if not os.access(newbufferpath, os.W_OK):
                print(" ! you don't have write access to the specific directory - aborting")
                sys.exit()
            bufferpath = newbufferpath

        print (" ------------------------------------------- ")
        print (" Please specify the MQTT payload format:")
        print (" (currently supported are 'martas' and 'intermagnet')")
        print (" ('intermagnet' is only available for mysql and imfile libraries)")
        print (" (default is 'martas')")
        newpayloadformat = input()
        if newpayloadformat == 'intermagnet':
            payloadformat = 'intermagnet'

        logpath = os.path.join(logpath, "martas.log")

        print(" ------------------------------------------- ")
        print(" Creating the MARTAS run time script")
        runscript = []
        runscript.append("#! /bin/bash")
        runscript.append("# MARTAS acquisition program")
        runscript.append("")
        runscript.append('PYTHON={}'.format(sys.executable))
        runscript.append('BOT="acquisition"')
        runscript.append('OPT="-m {}"'.format(os.path.join(confpath, "martas.cfg")))
        runscript.append("")
        runscript.append('check_process()')
        runscript.append("{")
        runscript.append("    result=`ps aux | grep \"$BOT\" | grep -v grep | wc -l`")
        runscript.append("}")
        runscript.append('get_pid()')
        runscript.append("{")
        runscript.append("    pid=`ps -ef | awk -v pattern=\"$BOT\" \"$0 ~ pattern{print $2}\"`")
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
        runscript.append("    echo \"Stopping $BOT ...\" ")
        runscript.append("    check_process")
        runscript.append("    if [ \"$result\" = \"0\" ]; then")
        runscript.append("        echo \" $BOT is not running\" ")
        runscript.append("    else")
        runscript.append("        echo \" Stopping $BOT\"")
        runscript.append("        echo \" --------------------\"")
        runscript.append("        pkill -f $BOT")
        runscript.append("    fi")
        runscript.append("    ;;")
        runscript.append("  restart)")
        runscript.append("    echo \"Restarting $BOT ...\" ")
        runscript.append("    check_process")
        runscript.append("    if [ \"$result\" = \"1\" ]; then")
        runscript.append("        echo \" Stopping $BOT\" ")
        runscript.append("        pkill -f $BOT")
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
        runscript.append("        echo \"$BOT is dead\" ")
        runscript.append("    else")
        runscript.append("        echo \"$BOT is running\" ")
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

        cronlist.append("# Running MARTAS ")
        cronlist.append("15  0,6,12,18  * * *    /usr/bin/bash -i {} > {} 2>&1".format(os.path.join(homedir, dir,"runmartas.sh"),os.path.join(homedir, dir, "log","runmartas.log")))

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
            print (" Please specify a filepath:")
            filepath = input()
            if not os.path.isdir(filepath):
                print ("  ! the selected directory is not yet existing - aborting")
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
        print(" Please provide a path for the data archive (default: /srv/archive):")
        newarchivepath = input()
        if newarchivepath:
            if not os.path.isdir(newarchivepath):
                print("  the selected directory is not yet existing - trying to create it...")
                try:
                    Path(newarchivepath).mkdir(parents=True, exist_ok=True)
                    print("  done")
                except:
                    print("  ! failed, check permissions - aborting")
                    sys.exit()
            if not os.access(newarchivepath, os.W_OK):
                print (" ! you don't have write access - aborting")
                sys.exit()
            archivepath = newarchivepath

        logpath = os.path.join(logpath, "{}.log".format(marcosjob))
        archivelog = os.path.join(homedir, dir, "log", "archivestatus.log")

        print(" ------------------------------------------- ")
        print(" Creating the MARCOS run time script for {}".format(jobname))
        runscript = []
        runscript.append("#! /bin/bash")
        runscript.append("# MARCOS acquisition program")
        runscript.append("")
        runscript.append('PYTHON={}'.format(sys.executable))
        runscript.append('BOT="collector"')
        runscript.append('OPT="-m {}"'.format(os.path.join(confpath, "{}.cfg".format(marcosjob))))
        runscript.append("")
        runscript.append('check_process()')
        runscript.append("{")
        runscript.append("    result=`ps aux | grep \"$BOT\" | grep -v grep | wc -l`")
        runscript.append("}")
        runscript.append('get_pid()')
        runscript.append("{")
        runscript.append("    pid=`ps -ef | awk -v pattern=\"$BOT\" \"$0 ~ pattern{print $2}\"`")
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
        runscript.append("    echo \"Stopping $BOT ...\" ")
        runscript.append("    check_process")
        runscript.append("    if [ \"$result\" = \"0\" ]; then")
        runscript.append("        echo \" $BOT is not running\" ")
        runscript.append("    else")
        runscript.append("        echo \" Stopping $BOT\"")
        runscript.append("        echo \" --------------------\"")
        runscript.append("        pkill -f $BOT")
        runscript.append("    fi")
        runscript.append("    ;;")
        runscript.append("  restart)")
        runscript.append("    echo \"Restarting $BOT ...\" ")
        runscript.append("    check_process")
        runscript.append("    if [ \"$result\" = \"1\" ]; then")
        runscript.append("        echo \" Stopping $BOT\" ")
        runscript.append("        pkill -f $BOT")
        runscript.append("    fi")
        runscript.append("    echo \" Starting $BOT\"")
        runscript.append("    echo \"--------------------\"")
        runscript.append("    sleep 2")
        runscript.append("    $PYTHON --version")
        runscript.append("    $BOT $OPT")
        runscript.append("    ;;")
        runscript.append("  update)")
        runscript.append("    echo \"Starting $BOT with meta information update...\" ")
        runscript.append("    check_process")
        runscript.append("    if [ \"$result\" = \"1\" ]; then")
        runscript.append("        echo \" Stopping $BOT\" ")
        runscript.append("        pkill -f $BOT")
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
        runscript.append("        echo \"$BOT is dead\" ")
        runscript.append("    else")
        runscript.append("        echo \"$BOT is running\" ")
        runscript.append("    fi")
        runscript.append("    ;;")
        runscript.append("  *)")
        runscript.append("    echo \"Usage: $BOT {start|stop|restart|status}\"")
        runscript.append("    ;;")
        runscript.append("esac")
        runscript.append("exit 0")
        with open(os.path.join(homedir, dir, "{}.sh".format(marcosjob)), "wt") as fout:
            for line in runscript:
                fout.write(line+"\n")

        cronlist.append("# Archiving ")
        cronlist.append("20  0  * * *    $PYTHON {} -c {} > {} 2>&1".format(os.path.join(homedir, dir,"app","archive.py"),os.path.join(homedir, dir,"conf","archive.cfg"), os.path.join(homedir, dir, "log","archive.log")))
        cronlist.append("# Running MARCOS process {} ".format(jobname))
        cronlist.append("17  0,6,12,18  * * *    /usr/bin/bash -i {} > {} 2>&1".format(os.path.join(homedir, dir, marcosjob+".sh"),os.path.join(homedir, dir, "log",marcosjob+".log")))
        # optimizetable

    cronlist.append("# Log rotation for {}".format(jobname))
    cronlist.append("30  2     * * *    /usr/sbin/logrotate -s {} {} > /dev/null 2>&1".format(os.path.join(homedir, dir, "scripts", "status"), os.path.join(homedir, dir, "logrotate", "{}.logrotate".format(jobname))))
    cronlist.append("# Running cleanup")
    cronlist.append("9  0  * * *    /usr/bin/bash -i {} > {} 2>&1".format(os.path.join(homedir, dir, "scripts", "cleanup.sh"),
                                                                  os.path.join(homedir, dir, "log",
                                                                               "cleanup.log")))
    cronlist.append("# Running backup")
    cronlist.append("7  0  * * 1    /usr/bin/bash -i {} > {} 2>&1".format(os.path.join(homedir, dir, "scripts", "backup.sh"),
                                                                  os.path.join(homedir, dir, "log",
                                                                               "backup.log")))
    # threshold
    # monitor


    replacedict = { "/logpath" : logpath,
                    "/sensorpath" : os.path.join(confpath, "sensors.cfg"),
                    "/initdir" : initpath,
                    "/srv/mqtt" : bufferpath,
                    "/obsdaqpath" : os.path.join(confpath, "obsdaq.cfg"),
                    "myhome" : stationname,
                    "outputdestination" : destination,
                    "filepath  :  /tmp" : "filepath  :  {}".format(filepath),
                    "archivepath" : archivepath,
                    "archivelog" : archivelog,
                    "monitorlog" : monitorlog,
                    "mynotificationtype" : noti,
                    "notificationcfg" : os.path.join(confpath, "telegram.cfg"),
                    "mydb" : databasecredentials,
                    "./web" : "{}".format(os.path.join(homedir, dir,"web")),
                    "brokeraddress" : mqttbroker,
                    "1883"  :  mqttport,
                    "mqttqos  :  0": "mqttqos  :  {}".format(mqttqos),
                    "payloadformat  :  martas": "payloadformat  :  {}".format(payloadformat),
                    "home/username/.magpycred" : os.path.join(homedir, ".magpycred"),
                    }
    if mqttcred:
        replacedict["#mqttcred  :  shortcut"] = "mqttcred  :  {}".format(mqttcred)

    files_to_change = {}
    if initjob == "MARTAS":
        replacedict["/mybasedir"] = bufferpath
        replacedict["space,martas,marcos,logfile"] = "space,martas,logpfile"
        files_to_change["martasconf"] = {"source" : os.path.join(homedir, dir, "conf", "martas.bak") ,
                                        "dest" : os.path.join(homedir, dir, "conf", "martas.cfg") }

    if initjob == "MARCOS":
        replacedict["/mybasedir"] = archivepath
        replacedict["space,martas,marcos,logfile"] = "space,marcos"
        files_to_change["marcosconf"] = {"source" : os.path.join(homedir, dir, "conf", "marcos.bak") ,
                                        "dest" : os.path.join(homedir, dir, "conf", "{}.cfg".format(marcosjob)) }
        files_to_change["archiveconf"] = {"source": os.path.join(homedir, dir, "conf", "archive.bak"),
                                     "dest": os.path.join(homedir, dir, "conf", "archive.cfg")}

        # file for which replacements will happen and new names
    files_to_change["skeletonlogrotate"] = {"source": os.path.join(homedir, dir, "logrotate", "skeleton.logrotate"),
                              "dest": os.path.join(homedir, dir, "logrotate", "{}.logrotate".format(jobname))}
    files_to_change["monitorconf"] = {"source": os.path.join(homedir, dir, "conf", "monitor.bak"),
                        "dest": os.path.join(homedir, dir, "conf", "monitor.cfg")}

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

if __name__ == "__main__":
   main(sys.argv[1:])
