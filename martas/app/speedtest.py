#!/usr/bin/env python
# coding=utf-8

"""
Speedtest:

Perform a speedtest based on speedtest-cli
(https://www.speedtest.net/de/apps/cli)

sudo apt install speedtest-cli


################################

add crontag to regularly run monitor (root)
sudo crontab -e
*/5  *  *  *  *  /usr/bin/python3 /path/to/speedtest.py -c /path/to/conf.cfg -n speed_starlink01_0001  > /dev/NULL 2&>1
"""

# Define packages to be used (local refers to test environment)
# ------------------------------------------------------------
import os, sys, getopt
from datetime import datetime
import paho.mqtt.client as mqtt
import json
import socket
from magpy.stream import DataStream
import magpy.database as mpdb
import magpy.opt.cred as mpcred
import numpy as np

import subprocess
import dateutil.parser
import csv


def getspeed(server=None, debug=False):

    # TODO test what happens if network is not avaiable 
    call = ["speedtest",'--csv']
    if debug:
        print ("Executing script ...")
    proc=subprocess.Popen(call, stdout=subprocess.PIPE)
    output = proc.stdout.read()
    outputstr = output.decode('utf-8')
    if debug:
        print (outputstr)
    result = outputstr.strip().split(',')
    print (result)
    return result
    
def write_basic_ascii(result,path='/srv/mqtt/',speedtestname='speed_666_0001', debug = False):
    success = True
    # Header
    header = ['DT_datatime','N_latency[ms]','N_download[Mbit/s]','N_upload[Mbit/s]','N_serverdistance[km]','S_sever','S_location']
    # Filename
    # makes use of datetime
    dat = dateutil.parser.isoparse(result[3])
    print (dat)
    datum = datetime.strftime(dat,"%Y-%m-%d")
    filename = "{}_{}.asc".format(speedtestname,datum)    
    print (filename)
    ### Create a simple ascii csv output
    # header contains DT=Datetime, N=Numeric, S=String
    #DT_datatime, N_latency[ms], N_download[Mbyte/s], N_upload[Mbyte/s], N_serverdistance[km], S_sever, S_location
    #
    outputlist = [result[3],float(result[5]),float(result[6])/1000000.,float(result[7])/1000000.,float(result[4]),result[1],result[2]]
    print (outputlist)
    # Write CSV
    filepath = os.path.join(path,speedtestname,filename)
    dirpath = os.path.join(path,speedtestname)
    if not debug:
        # 1. create directory if not existing
        if not os.path.exists(dirpath):
            os.makedirs(dirpath)
        # 2. write header if file not existing
        if not os.path.isfile(filepath):
            print ("creating new file")
            with open(filepath, 'w', newline='') as myfile:
                wr = csv.writer(myfile)
                wr.writerow(header)
        # 3. append data if file exists
        if os.path.exists(filepath):
            with open(filepath, 'a', newline='') as myfile:
                wr = csv.writer(myfile)
                wr.writerow(outputlist)
    else:
        print ("debug selected - skipping write")

    return success
    

def main(argv):
    version = '1.0.0'
    statusmsg = {}
    configpath = ''
    hostname = socket.gethostname().upper()
    debug = False
    travistestrun = False
    speedtestname = 'speed_starlink01_0001'
    outpath = '/srv/mqtt/'
    #testst = DataStream()

    try:
        opts, args = getopt.getopt(argv,"hc:n:p:vDT",["config=","name=","path=",])
    except getopt.GetoptError:
        print ('speedtest.py -c <config> -n <name> -p <path> -v <version>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print ('------------------------------------------------------------')
            print ('Description:')
            print ('-- speedtest.py to monitor internet bandwidth  --')
            print ('------------------------------------------------------------')
            print ('-------------------------------------')
            print ('Usage:')
            print ('speedtest.py -c <config> -n <name>  -p <path>')
            print ('-------------------------------------')
            print ('Options:')
            print ('-c (coming soon) : path to a configuration file')
            print ('-n            : virtual sensor name; default: speed_starlink01_0001 ')
            print ('-p            : path for file storage; default: /srv/mqtt/ ')
            print ('-v            : print the current version of speedtest.py')
            print ('-------------------------------------')
            print ('Application:')
            print ('python3 speedtest.py -c /etc/martas/appconf/monitor.cfg')
            sys.exit()
        elif opt in ("-c", "--config"):
            configpath = arg
        elif opt in ("-n", "--name"):
            speedtestname = arg
        elif opt in ("-p", "--path"):
            outpath = arg
        elif opt == "-v":
            print ("speed.py version: {}".format(version))
        elif opt in ("-D", "--debug"):
            debug = True
        elif opt in ("-T", "--test"):
            travistestrun = True

    result = getspeed(debug=debug)
    write_basic_ascii(result,path=outpath,speedtestname=speedtestname, debug=debug)

if __name__ == "__main__":
   main(sys.argv[1:])



