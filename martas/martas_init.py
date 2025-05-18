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
        print ('martas_init.py')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print ('-------------------------------------')
            print ('Description:')
            print ('-- martas_init.py will initialize imbot configuration --')
            print ('-----------------------------------------------------------------')
            print ('martas_init.py will perform the following tasks:')
            print ('- default directory is .martas, change using -d option, i.e. MARTAS')
            print ('- will create a ~/.martas directory')
            print ('- copy skeleton configuration files to .martas/conf/')
            print ('- copy bash scripts to .martas/scripts/')
            print ('- copy python applications to .martas/app/')
            print ('')
            print ('Options:')
            print ('-d, --directory : define the main configuration directory')
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
        shutil.rmtree(os.path.join(homedir, dir, "app"))
        shutil.rmtree(os.path.join(homedir, dir, "conf"))
        shutil.rmtree(os.path.join(homedir, dir, "doc"))
        shutil.rmtree(os.path.join(homedir, dir, "init"))
        shutil.rmtree(os.path.join(homedir, dir, "install"))
        shutil.rmtree(os.path.join(homedir, dir, "logrotate"))
        shutil.rmtree(os.path.join(homedir, dir, "telegram"))
        shutil.rmtree(os.path.join(homedir, dir, "web"))
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
    initjob = "MARTAS"
    stationname = "WIC"
    mqttbroker = "localhost"
    mqttport = "1883"
    mqttqos = "1"
    mqttcred = ""
    bufferpath = "/srv/mqtt"
    cronlist = []
    print (" ------------------------------------------- ")
    print ("""               You started the MARTAS initialization routine.
               Please provide some additional information so
               that MARTAS or MARCOS can be set up correctly.
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
    shutil.copyfile(os.path.join(confpath, "obsdaqr.cfg"), os.path.join(confpath, "obsdaq.bak"))
    shutil.copyfile(os.path.join(confpath, "sensors.cfg"), os.path.join(confpath, "seonsors.bak"))
    shutil.copyfile(os.path.join(confpath, "telegram.cfg"), os.path.join(confpath, "telegram.bak"))
    shutil.copyfile(os.path.join(confpath, "threhold.cfg"), os.path.join(confpath, "threhold.bak"))

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
    logpath = os.path.join(logpath,"martas.log")

    print (" ------------------------------------------- ")
    print (" Please insert a station ID (i.e. the three letter observatory code, like WIC)")
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
            mqttpwd = input()
            cred.cc("transfer",newmqttcred,user=mqttuser,passwd=mqttpwd,address=mqttbroker,port=int(mqttport))
    print (" -> MQTT credentials: {}".format(mqttcred))

    print (" ------------------------------------------- ")
    print (" Please select - you are initializing (A) a acquisition/MARTAS or (B) a collector/MARCOS")
    print (" ( select either A (default) or B )")
    initselect = input()
    if initselect in ["B","b"]:
        initjob = "MARCOS"
        print("  -> selected MARCOS")
    else:
        print("  -> selected MARTAS")

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

        # TODO drop this block
        print (" ------------------------------------------- ")
        print (" Please insert a name for the MARTAS job:")
        print (" (press return for accepting default: {})".format(jobname))
        newjobname = input()
        if newjobname:
            jobname = ''.join(filter(str.isalnum, newjobname))
        print (" -> MARTAS job name: {}".format(jobname))


    elif initjob == "MARCOS":
        print (" You can have multiple collector jobs on one machine.")
        print (" Make sure they have different names.")
        print (" ------------------------------------------- ")
        print (" Please insert a name for the collector:")
        print (" (press return for accepting default: {})".format(marcosjob))
        print (" (the given name will be extended by '...-collect')")
        print (" (ideally you provide the name of the MARTAS from which you are collecting data)")
        newjobname = input()
        if newjobname:
            jobname = ''.join(filter(str.isalnum, newjobname))
        print (" -> MARCOS job name: {}".format(jobname))

    cronlist.append("# Log rotation for {}".format(jobname))
    cronlist.append("30 2 * * * /usr/sbin/logrotate -s {} {} > /dev/null 2>&1".format(os.path.join(homedir, dir, "logrotate", "status"), os.path.join(homedir, dir, "logrotate", "{}.logrotate".format(jobname))))

    replacedict = { "/logpath" : logpath,
                    "/sensorpath" : os.path.join(confpath, "sensors.cfg"),
                    "/initdir/" : initpath,
                    "myhome" : stationname,
                    "brokeraddress" : mqttbroker,
                    "1883"  :  mqttport,
                    "mqttqos  :  0": "mqttqos  :  {}".format(mqttqos),
                    }

    # file for which replacements will happen and new names
    files_to_change = { "martasconf" : {"source" : os.path.join(homedir, dir, "conf", "martas.bak") ,
                                        "dest" : os.path.join(homedir, dir, "conf", "martas.cfg") },
                        "skeletonlogrotate": {"source" : os.path.join(homedir, dir, "logrotate", "skeleton.logrotate"),
                                              "dest" : os.path.join(homedir, dir, "logrotate", "{}.logrotate".format(jobname)) }
                        }
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
