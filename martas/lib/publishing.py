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
from json import JSONEncoder, dumps
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

    pubdict[topic + "/data"] = data
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
    debug = True
    datelist = []
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

    def _get_components(head,meta):
        components = None
        component1 = meta.get("SensorElements", None)
        component2 = meta.get("DataComponents", None)
        try:
            component3 = head.split()[4].strip("[").strip("]").replace(",", "")
        except:
            component3 = None
        if not components:
            components = component3
        if not components:
            components = component2
        if not components:
            components = component1
        return components.lower()

    def nan_to_none(obj):
        if isinstance(obj, dict):
            return {k: nan_to_none(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [nan_to_none(v) for v in obj]
        elif isinstance(obj, float) and np.isnan(obj):
            return None
        return obj

    class NanConverter(JSONEncoder):
        def encode(self, obj, *args, **kwargs):
            return super().encode(nan_to_none(obj), *args, **kwargs)

    # get the following info from file header
    if debug:
        print ("HEADER", head, meta)
    multilist = list(map(float, head.split()[6].strip('[').strip(']').split(',')))
    samplingperiod = float(meta.get("DataSamplingRate",1.0))
    publevel = meta.get("DataPublicationLevel", 1)
    components = _get_components(head,meta)
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
    if meta.get("DataElevation", None):
        datablock["elevation"] = meta.get("DataElevation")
    if meta.get('StationInstitution'):
        datablock["institute"] = meta.get("StationInstitution")
    # "institute": (IAGA-2002, ImagCDF - called "Source of data" in IAGA-2002)
    if meta.get('StationName'):
        datablock["name"] = meta.get("StationName")
    # "name": (IAGA-2002, ImagCDF - called "ObservatoryName" in ImagCDF)
    if meta.get('DataSensorOrientation'):
        datablock["sensorOrientation"] = meta.get("DataSensorOrientation")
    # "sensorOrientation": (IAGA-2002, ImagCDF - called "VectorSensOrient in CDF)
    if meta.get('DataDigitalSampling'):
        datablock["digitalSampling"] = meta.get("DataDigitalSampling")
    # "digitalSampling": (IAGA-2002)
    if meta.get('DataSamplingFilter'):
        datablock["dataIntervalType"] = meta.get("DataSamplingFilter")
    # "dataIntervalType": (IAGA-2002)
    if meta.get('DataPublicationDate'):
        datablock["publicationDate"] = meta.get("DataPublicationDate")
    # "publicationDate": (IAGA-2002, ImagCDF)
    if meta.get('DataStandardLevel'):
        datablock["standardLevel"] = meta.get("DataStandardLevel")
    # "standardLevel": (ImagCDF)
    if meta.get('DataStandardName'):
        datablock["standardName"] = meta.get("DataStandardName")
    # "standardName": (ImagCDF)
    if meta.get('DataStandardVersion'):
        datablock["standardVersion"] = meta.get("DataStandardVersion")
    # "standardVersion": (ImagCDF)
    if meta.get('DataPartialStandDesc'):
        datablock["partialStandDesc"] = meta.get("DataPartialStandDesc")
    # "partialStandDesc": (ImagCDF)
    if meta.get('DataSource'):
        datablock["source"] = meta.get("DataSource")
    # "source": (ImagCDF)
    if meta.get('DataTerms'):
        datablock["termsOfUse"] = meta.get("DataTerms")
    # "termsOfUse": (ImagCDF)
    if meta.get('DataID'):
        datablock["uniqueIdentifier"] = meta.get("DataID")
    # "uniqueIdentifier": (ImagCDF)
    if meta.get('SensorID'):
        datablock["ParentIdentifiers"] = meta.get("SensorID")
    # "parentIdentifiers": (ImagCDF)
    if meta.get('StationWebInfo'):
        datablock["referenceLinks"] = meta.get("StationWebInfo")
    # "referenceLinks": (ImagCDF)
    if meta.get('DataComments'):
        datablock["comments"] = meta.get("DataComments")
    # "comments": (IAGA-2002)
    #if meta.get('StationK9'):
    #    datablock["k9level"] = meta.get("StationK9")

    lines = data.split(";")
    # Get the startdate
    dateext = lines[0].split(",")[:7]
    dateline = list(map(int, dateext))
    startdt = datetime(*dateline)

    for line in lines:
        data = line.split(",")
        # times and data
        if len(data)>7:
            dt = data[:7]
            dtn = list(map(int, dt))
            datelist.append(datetime(*dtn))
            #add all dates to a list
            dat = data[7:]
            if debug:
                print ("DATA", dat)
                print ("LEN", len(dat))
                print ("LEN Comp", len(components))
            if len(dat) >= len(components):
                pass
            else:
                components = components[:len(dat)]
            # Limit the amount of components to 4
            components = components[:4]
            for idx,el in enumerate(components):
                mu = 1.0
                if len(multilist) >= idx:
                   mu = multilist[idx]
                   if not is_number(mu):
                       mu = 1.0
                   mu = float(mu)
                val = dat[idx]
                blockname = f"geomagneticField{el.upper()}"
                if debug:
                    print(blockname)
                l = datablock.get(blockname, [])
                if is_number(val) and np.isnan(float(val)):
                    val = None
                l.append(float(val)/mu)
                datablock[blockname] = l
        else:
            # no data
            pass
    # determine increment of date list and eventually update cadence
    if len(datelist) > 1 and not samplingperiod:
        meand = np.mean(np.diff(datelist))
        samplingperiod = meand.total_seconds()
    cadence, dtformat = _get_cadence(samplingperiod)
    starttime = startdt.strftime(dtformat)
    datablock["startDate"] = starttime

    topic = "impf/{}/{}/{}/{}".format(imo.lower(), cadence, publevel, components)

    # replace NaN with null - Test set
    #datablock["geomagneticFieldX"] = [ 17595.02, np.nan, 17594.99 ]
    #datablock["geomagneticFieldY"] = [ -329.19, -329.18, -329.21 ]
    #datablock["geomagneticFieldZ"] = [ 46702.70, 46703.01, 46703.24 ]

    # convert datablock to json
    datajson = dumps(datablock, cls=NanConverter)
    pubdict[topic] = datajson

    return pubdict