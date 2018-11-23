#!/usr/bin/env python
# coding=utf-8

"""
Monitoring script to check for last buffer file

This script should be running on each martas machine.
It will produce a mqtt json statusmessage if any critical 
information is changing like disk size or buffer files are not 
written any more.

possible extensions:
- check for critical changes in martas/marcos log

################################

add crontag to regularly run monitor (root)
sudo crontab -e
PATH=/bin/sh
5  *  *  *  *  /usr/bin/python /path/to/monitor.py > /dev/NULL 2&>1
"""

from __future__ import print_function
from __future__ import unicode_literals

# Define packges to be used (local refers to test environment) 
# ------------------------------------------------------------
import os
import glob
from datetime import datetime
import paho.mqtt.client as mqtt
import json
import socket

from martas import martaslog as ml

logpath='/var/log/magpy/mm.log'
defaultpath='/srv'
threshold = 7200  # time in seconds at which new files need to be present
threshold = 18000000
status = {}
hostname = socket.gethostname()

def _latestfile(path, date=False, latest=True):
    list_of_files = glob.glob(path) # * means all if need specific format then *.csv
    if len(list_of_files) > 0:
        if latest:
            latest_file = max(list_of_files, key=os.path.getctime)
        else:
            latest_file = min(list_of_files, key=os.path.getctime)
        ctime = os.path.getctime(latest_file)
        if date:
            return datetime.fromtimestamp(ctime)
        else:
            return latest_file
    else:
        return ""

def getspace(path,warning=80,critical=90): # path = '/srv'
    statvfs = os.statvfs(path)
    total = (statvfs.f_frsize * statvfs.f_blocks / (1024.*1024.))     # Size of filesystem in bytes
    remain = (statvfs.f_frsize * statvfs.f_bavail / (1024.*1024.))     # Number of free bytes that ordinary users
    usedper=100-(remain/total*100.)
    #mesg = "status:\nDisk-size: {:.0f}MB\nDisk available: {:.0f}MB\nDisk occupied: {:.1f}%".format(total,remain, 100-(remain/total*100.))
    level = 'OK'
    if usedper >= warning:
        level = "warning: used > {}%".format(warning)
    if usedper >= critical:
        level = "critical: used > {}%".format(critical)
    return level

# - Walk through all subdirs of /srv and check for latest files in all subdirs
# - add active or inactive to a log file
# - if log file not exists: just add data
# - if existis: check for changes and create message with all changes

dirs=[x[0] for x in os.walk(defaultpath) if not x[0].find("archive")>0 and not x[0].find("products")>0 and not x[0].find("projects")>0]

for d in dirs:
        ld = _latestfile(os.path.join(d,'*'),date=True)
        lf = _latestfile(os.path.join(d,'*'))
        if os.path.isfile(lf):
            diff = (datetime.utcnow()-ld).total_seconds()
            dname = d.split('/')[-1]
            state = "active"
            if diff > threshold:
                state = "inactive"
            status[dname] = state
            print ("{}: {}".format(dname,state))
            #print (d, lf, ld, diff)
        status['diskspace'] = getspace(defaultpath)


martaslog = ml(logfile=logpath)
#martaslog.receiveroptions('mqtt',options={'user':'cobs','password':'pwd','stationid':'sgo'})
martaslog.msg(status)

