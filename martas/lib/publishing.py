#!/usr/bin/env python

"""
Module containing publishing conversions

This module contains methods which convert topic, payload, config and sensors meta data into different MQTT
publishing formats.

The following methods are contained:
|     method      |  version |  tested  |              comment             | manual | *used by |
| --------------- |  ------- |  ------- |  ------------------------------- | ------ | -------- |
|  martas         |    2.0.0 |      yes |                                  | -       | lib     |
|  intermagnet    |    2.0.0 |       -  |                                  | -       | lib     |

"""

import unittest
import os
import sys
from datetime import datetime
import json

def martas(pubdict=None, topic="", data="", head="", count=0, changecount=10, imo="TST", meta=None):
    """
    DESCRIPTION
        martas publishing format will create a CSV like output and sends meta information in a reduced cadence
    APPLICATION
        pubdict, count = martas(None, topic=topic, data=data, head=head, count=self.count, changecount=self.metacnt,
                imo="self.confdict.get('station', ''), meta=self.sensordict)
        self.count = count
    """
    if not meta:
        meta = {}
    if not pubdict:
        pubdict = {}

    topic = topic + "/data"
    pubdict[topic] = data
    if count == 0:
        ## 'Add' is a string containing dict info like:
        ## SensorID:ENV05_2_0001,StationID:wic, PierID:xxx,SensorGroup:environment,...
        add = "SensorID:{},StationID:{},DataPier:{},SensorModule:{},SensorGroup:{},SensorDecription:{},DataTimeProtocol:{}".format(
            meta.get('sensorid', ''), imo, meta.get('pierid', ''), meta.get('protocol', ''), meta.get('sensorgroup', ''),
            meta.get('sensordesc', ''), meta.get('ptime', ''))

        pubdict[topic + "/dict"] = add
        pubdict[topic + "/meta"] = head
    count += 1
    if count >= changecount:
        count = 0
    return pubdict, count


def intermagnet(pubdict=None, topic="", data="", head="", imo="TST", meta=None):
    """
    DESCRIPTION
        intermagnet publishing format will create a json style output as defined here

        # Topic
        # impf/<iaga-code>/<cadence>/<publication-level>/<elements-recorded>
        # impf/esk/pt1m/1/hdzs
        # Payload
        # {
        #     "startDate": "2023-01-01T00:00",
        #     "geomagneticFieldX": [ 17595.02, null, 17594.99 ],
        #     "geomagneticFieldY": [ -329.19, -329.18, -329.21 ],
        #     "geomagneticFieldZ": [ 46702.70, 46703.01, 46703.24 ]
        # }
        # "ginCode": (IMF)
        # "decbas": (IMF)
        # "latitude": (IMF, IAGA-2002, ImagCDF)
        # "longitude": (IMF, IAGA-2002, ImagCDF)
        # "elevation": (IAGA-2002, ImagCDF)
        # "institute": (IAGA-2002, ImagCDF - called "Source of data" in IAGA-2002)
        # "name": (IAGA-2002, ImagCDF - called "ObservatoryName" in ImagCDF)
        # "sensorOrientation": (IAGA-2002, ImagCDF - called "VectorSensOrient in CDF)
        # "digitalSampling": (IAGA-2002)
        # "dataIntervalType": (IAGA-2002)
        # "publicationDate": (IAGA-2002, ImagCDF)
        # "standardLevel": (ImagCDF)
        # "standardName": (ImagCDF)
        # "standardVersion": (ImagCDF)
        # "partialStandDesc": (ImagCDF)
        # "source": (ImagCDF)
        # "termsOfUse": (ImagCDF)
        # "uniqueIdentifier": (ImagCDF)
        # "parentIdentifiers": (ImagCDF)
        # "referenceLinks": (ImagCDF)
        # "comments": (IAGA-2002)
    APPLICATION
        pubdict = intermagnet(None, topic=topic, data=data, head=head, count=self.count, changecount=self.metacnt,
                imo="self.confdict.get('station', ''), meta=self.sensordict)
        self.count = count
    """
    datablock = {}
    cadence = "pt1m"
    publevel = "1"
    components = "hdzs"
    dtformat = "%Y-%m-%d"

    topic = "impf/{}/{}/{}/{}".format(imo.lower(), cadence, publevel, components)
    lines = data.split(";")
    # Get the startdate
    dateext = lines[0].split(",")[:7]
    dateline = list(map(int, dateext))
    dt = datetime(*dateline)
    d = datetime.strptime(dateline[:6], "%Y,%m,%d,%H,%M,%S,%f")
    if cadence == "pt1s":
        dtformat = "%Y-%m-%dT%H:%M:%S"
    elif cadence == "pt1m":
        dtformat = "%Y-%m-%dT%H:%M"
    elif cadence == "pt1h":
        dtformat = "%Y-%m-%dT%H"
    starttime = dt.strftime(dtformat)
    datablock["startDate"] = starttime

    xdat = []
    for line in lines:
        data = line.split(",")
        xdat.append(data[7])
        # replace NaN with null

    #datablock["geomagneticFieldX"] = [ 17595.02, null, 17594.99 ],
    #datablock["geomagneticFieldY"] = [ -329.19, -329.18, -329.21 ],
    #datablock["geomagneticFieldZ"] = [ 46702.70, 46703.01, 46703.24 ]

    # convert datablock to json

    #pubdict[topic] = datajson

    return pubdict