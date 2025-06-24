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
import numpy as np
from magpy.core.methods import is_number


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
    if not pubdict:
        pubdict = {}

    def _get_cadence(samplingperiod):
        if 0.9 < samplingperiod < 1.1:
            cadence = "pt1s"
            dtformat = "%Y-%m-%dT%H:%M:%S"
        elif 58 < samplingperiod < 62:
            cadence = "pt1m"
            dtformat = "%Y-%m-%dT%H:%M"
        elif 3500 < samplingperiod < 3700:
            cadence = "pt1h"
            dtformat = "%Y-%m-%dT%H"
        elif 86000 < samplingperiod < 87000:
            cadence = "pt1d"
            dtformat = "%Y-%m-%d"
        else:
            print ("Samplingperiod {} not supported by INTERMAGNET MQTT payload format")
            cadence = "{:.1f}S".format(samplingperiod)
            dtformat = "%Y-%m-%dT%H:%M:%S"
        return cadence, dtformat

    # get the following info from file header
    print ("HEADER", head, meta)
    samplingperiod = meta.get("DataSamplingRate",1.0)
    publevel = meta.get("DataPublicationLevel", 1)
    #cadence = "pt1m"
    #publevel = "1"
    component1 = meta.get("SensorElements", None)
    #component2 = head.replace(".get("SensorElements", None)
    components = "h"
    # fill in header info
    if meta.get("ginCode", None):
        datablock["ginCode"] = meta.get("ginCode")
    if meta.get("decbas", None):
        datablock["decbas"] = meta.get("decbas")
    # "latitude": (IMF, IAGA-2002, ImagCDF)
    if meta.get("DataAcquisitionLatitude", None):
        datablock["latitude"] = meta.get("DataAcquisitionLatitude")
    # "longitude": (IMF, IAGA-2002, ImagCDF)
    if meta.get("DataAcquisitionLongitude", None):
        datablock["longitude"] = meta.get("DataAcquisitionLongitude")
    # "elevation": (IAGA-2002, ImagCDF)
    if meta.get("DataElevation", None):
        datablock["elevation"] = meta.get("DataElevation")
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

    lines = data.split(";")
    # Get the startdate
    dateext = lines[0].split(",")[:7]
    dateline = list(map(int, dateext))
    startdt = datetime(*dateline)

    for line in lines:
        data = line.split(",")
        # times and data
        if len(data)>7:
            dt = data[:6]
            #add all dates to a list
            dat = data[7:]
            #print ("DATA", dat)
            #print ("LEN", len(dat))
            #print ("LEN Comp", len(components))
            if len(dat) >= len(components):
                continue
            else:
                components = components[:len(dat)]
            for idx,el in enumerate(components):
                    val = dat[idx]
                    blockname = f"geomagneticField{el.upper()}"
                    print(blockname)
                    l = datablock.get(blockname, [])
                    if is_number(val) and np.isnan(float(val)):
                        val = None
                    l.append(float(val))
                    datablock[blockname] = l
        else:
            # no data
            pass
    # determine increment of datelist and eventually update cadence
    # cadence = ...
    cadence, dtformat = _get_cadence(samplingperiod)
    starttime = startdt.strftime(dtformat)
    datablock["startDate"] = starttime


    topic = "impf/{}/{}/{}/{}".format(imo.lower(), cadence, publevel, components)

    # replace NaN with null

    #datablock["geomagneticFieldX"] = [ 17595.02, null, 17594.99 ],
    #datablock["geomagneticFieldY"] = [ -329.19, -329.18, -329.21 ],
    #datablock["geomagneticFieldZ"] = [ 46702.70, 46703.01, 46703.24 ]

    # convert datablock to json
    datajson = json.dumps(datablock)
    #print (datajson)

    pubdict[topic] = datajson

    return pubdict, 0