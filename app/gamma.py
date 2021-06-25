#!/usr/bin/env python
# coding=utf-8

"""
Working with Spectral radiometric data:
################################
The gamma script can be used to extract spectral measurements, reorganize the data and to analyze such spectral data as obtained by a DIGIBASE RH. 

Prerequisites are a DIGIBASE MCA and the appropriate linux software to run it.

1) Please install linux drivers as provided and described here:

2) Use a script to measure spectral data periodically (almost 1h)

#!/bin/bash
DATUM=$(date '+%Y-%m-%d')
SN=$(/home/pi/Software/digibase/dbaserh -l | grep : | cut -f 2)
NAME="/srv/mqtt/DIGIBASE_16272059_0001/raw/DIGIBASE_"$SN"_0001.Chn"
/home/pi/Software/digibase/dbaserh -set hvt 710
/home/pi/Software/digibase/dbaserh -q -hv on -start -i 3590 -t 3590 >> $NAME

3) Use crontab to run this script every hour

0  *  *  *  *  root  bash /home/pi/Software/gammascript.sh > /var/log/magpy/gamma.log

4) use gamma.py to extract spectral data and store it in daily json structures

58 5   *  *  *  root  $PYTHON /home/pi/SCRIPTS/gamma.py -p /srv/mqtt/DIGIBASE_16272059_0001/raw/DIGIBASE_16272059_0001.Chn  -c /home/pi/SCRIPTS/gamma.cfg -j extract,cleanup -o /srv/mqtt/DIGIBASE_16272059_0001/raw/ > /var/log/magpy/digiextract.log  2>&1

4) use gamma.py to analyse spectral data and create graphs

30 6   *  *  *  root  $PYTHON /home/pi/SCRIPTS/gamma.py -p /srv/mqtt/DIGIBASE_16272059_0001/raw/ -j load,analyze -c /home/pi/SCRIPTS/gamma.cfg  > /var/log/magpy/digianalyse.log 2>&1

"""

from __future__ import print_function
from __future__ import unicode_literals

# Define packges to be used (local refers to test environment) 
# ------------------------------------------------------------
import os, sys, getopt
from datetime import datetime, timedelta
import dateutil.parser as dparser
import paho.mqtt.client as mqtt
import json
import socket
from magpy.stream import *
import magpy.database as mpdb
import magpy.mpplot as mp
import magpy.opt.cred as mpcred
import numpy as np
import filecmp, shutil
import copy
import glob

from scipy.interpolate import interp1d
from scipy import interpolate
from scipy.optimize import curve_fit, minimize
from scipy.special import factorial
import pylab
import numpy.polynomial.polynomial as poly
import scipy.ndimage.filters as filters
import scipy.ndimage.morphology as morphologyimport
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import matplotlib.dates as mdates
import matplotlib.image as mpimg
#matplotlib.use('Agg')


def get_sensors(mqttpath):
    """
    DESCRIPTION
        provide names of all subdirectories
    """
    sensordirs = [x[0].split('/')[-1] for x in os.walk(mqttpath)]
    return sensordirs

def GetConf2(path, confdict={}):
    """
    Version 2020-10-28
    DESCRIPTION:
       can read a text configuration file and extract lists and dictionaries
    VARIBALES:
       path             Obvious
       confdict         provide default values
    SUPPORTED:
       key   :    stringvalue                                 # extracted as { key: str(value) }
       key   :    intvalue                                    # extracted as { key: int(value) }
       key   :    item1,item2,item3                           # extracted as { key: [item1,item2,item3] }
       key   :    subkey1:value1;subkey2:value2               # extracted as { key: {subkey1:value1,subkey2:value2} }
       key   :    subkey1:value1;subkey2:item1,item2,item3    # extracted as { key: {subkey1:value1,subkey2:[item1...]} }
    """
    exceptionlist = ['bot_id']

    def is_number(s):
        try:
            float(s)
            return True
        except ValueError:
            return False

    try:
        config = open(path,'r')
        confs = config.readlines()
        for conf in confs:
            conflst = conf.split(':')
            if conflst[0].strip() in exceptionlist or is_number(conflst[0].strip()):
                # define a list where : occurs in the value and is not a dictionary indicator
                conflst = conf.split(':',1)
            if conf.startswith('#'):
                continue
            elif conf.isspace():
                continue
            elif len(conflst) == 2:
                conflst = conf.split(':',1)
                key = conflst[0].strip()
                value = conflst[1].strip()
                # Lists
                if value.find(',') > -1:
                    value = value.split(',')
                    value = [el.strip() for el  in value]
                try:
                    confdict[key] = int(value)
                except:
                    confdict[key] = value
            elif len(conflst) > 2:
                # Dictionaries
                if conf.find(';') > -1 or len(conflst) == 3:
                    ele = conf.split(';')
                    main = ele[0].split(':')[0].strip()
                    cont = {}
                    for el in ele:
                        pair = el.split(':')
                        # Lists
                        subvalue = pair[-1].strip()
                        if subvalue.find(',') > -1:
                            subvalue = subvalue.split(',')
                            subvalue = [el.strip() for el  in subvalue]
                        try:
                            cont[pair[-2].strip()] = int(subvalue)
                        except:
                            cont[pair[-2].strip()] = subvalue
                    confdict[main] = cont
                else:
                    print ("Subdictionary expected - but no ; as element divider found")
    except:
        print ("Problems when loading conf data from file. Using defaults")

    return confdict


def read_linux_gamma(path, debug=False):

    def roundSeconds(dateTimeObject):
        newDateTime = dateTimeObject + timedelta(seconds=.5)
        return newDateTime.replace(microsecond=0)

    def getName(path):
        nameinfo={}
        name = 'dummy'
        sn = ''
        srevision = '0001'
        drevision = '0001'
        fname = os.path.basename(path)
        p,t = os.path.split(fname)
        tn = t.split('.')
        tl = tn[0].split('_')
        if len(tl) > 0:
            name = tl[0]
        if len(tl) > 1:
            sn = tl[1]
        if len(tl) > 2:
            srevison = tl[2]
        sensorid = "{}_{}_{}".format(name,sn,srevision)

        nameinfo['SensorID'] = sensorid
        nameinfo['SensorName'] = name
        nameinfo['SensorRevision'] = srevision
        nameinfo['SensorSerialNumber'] = sn
        return nameinfo

    getdate = False
    starttime = None
    endtime = None
    samprate = ''
    data = []
    resultdict = {}
    fullcontent = {}
    times = []
    spectraldata = []

    if debug:
        print (" Reading Gamma raw data file: {}".format(path))
    fi = open(path, 'rt')
    # Read all lines and obtain Times, average time and data
    contentdict = getName(path)
    contentdict['DataType'] = 'SpectralTimeseries'
    for line in fi:
        linefinished = False
        linedict = {}
        if line.isspace():
            continue
        if line.startswith('Start'):
            getdata = False
            starttime = dparser.parse(line,fuzzy=True)
        elif line.startswith('Getting'):
            getdata = False
        elif line.startswith('End'):
            getdata = True
            endtime = dparser.parse(line,fuzzy=True)
        elif line.startswith('Counting'):
            # get sampling rate
            vals = line.split(':')
            samprate = vals[1].replace(' ','').strip()
        elif getdata:
            data = line.split()
            print ("Extracting timerange:", starttime, endtime)
            try:
                chan = [int(el) for el in data]
                while len(chan) < 1024:
                    chan.append(0)
                getdate = False
                linefinished = True
            except:
                print ("ERROR: could not interprete channels")
                pass
        if linefinished:
            linedict['starttime'] = starttime.isoformat()
            linedict['endtime'] = endtime.isoformat()
            linedict['samplingrate'] = samprate
            linedict['channels'] = len(chan)
            linedict['data'] = chan
            meantime = roundSeconds((starttime + (endtime-starttime)/2.))
            times.append(meantime.isoformat())
            spectraldata.append(linedict)

    resultdict['time'] = times
    resultdict['spectraldata'] = spectraldata
    contentdict['DataContent'] = resultdict
    fi.close()

    return contentdict


def addToContentdict(contentdict):
    return contentdict


def joinDataDict(d1, d2):
    if d1.get('SensorID') == d2.get('SensorID'):
        cont1 = d1.get('DataContent')
        cont2 = d2.get('DataContent')
        tlen = len(cont1.get('time'))
        for k, v in cont1.items():
            if k in cont2.keys():
                cont2[k] += v
            else:
                cont2[k] = [np.nan]*tlen + v
        return d2
    else:
        print ("SensorIDs dont match - aborting")
        return d1

def removeDuplicateTime(d):
    cont = d.get('DataContent')
    times = cont.get('time')
    tlist = [t for t in times]
    indicies = []
    seen = set()
    for i, el in enumerate(tlist):
        if el not in seen:
            indicies.append(i)
        seen.add(el)

    for k, v in cont.items():
        cont[k] = [v[i] for i in indicies]
    return d


def timerangeDataDict(d1):
    cont = d1.get('DataContent')
    times = cont.get('time')
    tlist = []
    for t in times:
        dt = dparser.parse(t)
        tlist.append(dt)
    s = min(tlist)
    e = max(tlist)
    return s,e


def extractDataDict(d1, startdate, enddate=None):
    cont = d1.get('DataContent')
    #print ("DEBUG", cont)
    times = cont.get('time')
    sdate = dparser.parse(startdate)
    tlist = []
    for t in times:
        dt = dparser.parse(t)
        tlist.append(dt)
    l = len(tlist)
    if not enddate:
        #get same day as startdate
        indicies = [idx for idx, element in enumerate(tlist) if element.date() == sdate.date()]
    else:
        edate = dparser.parse(enddate)
        indicies = [idx for idx, element in enumerate(tlist) if element>= sdate and element<edate]

    subd = copy.deepcopy(d1)

    subcont = subd.get('DataContent')
    for k, v in cont.items():
        if len(v) == l:
            subcont[k] = [v[i] for i in indicies]

    return subd


def daylist(start,end):
    days = []
    delta = end.date()-start.date()
    for i in range(delta.days + 1):
        day = start + timedelta(days=i)
        print(day)
        days.append(day.date())
    return days


def writeJson(d, path, mode='append'):

    if os.path.isfile(path):
        if mode == 'append':
            # path exists - create a new d including already existing data
            print ("    - file exists")
            existd = read_data_dict(path)
            print ("    - read data")
            d = joinDataDict(d, existd)
            print ("    - join data")
            d = removeDuplicateTime(d)
            print ("    - remove duplicates")
    with open(path, 'w') as outfile:
        json.dump(d, outfile)


def write_data_dict(contentdict,path,name='default',format='JSON',debug=False):
    """
    write the dictionary as Json
    { "SensorID":"",
      "SensorName":"",
      "DataRevisionNumber":"",
      "etc":"",
      "DataType": "",
      "DataContent": { times : array,
                       spectralarray : array of dicts,
                       temp  : array
                       etc...
                     }
    """
    try:
        if debug:
            print ("Writing json data:")
            print ("--------------------")
        if name == 'default':
            # create filename from times in contentdict
            s,e = timerangeDataDict(contentdict)
            if debug:
                print (" data dictionary covers data from :", s,e)
            days = daylist(s,e)
            for day in days:
                savecontentdict = {}
                sdate = datetime.strftime(day,"%Y-%m-%d")
                fname = "{}_{}.json".format(contentdict.get('SensorID'),sdate)
                if os.path.isfile(path):
                    path = os.path.dirname(path)
                path = os.path.join(path,fname)
                print (" Saving to {}".format(path))
                savecontentdict = extractDataDict(contentdict, sdate)
                print ("  -> extracted contentdict")
                writeJson(savecontentdict, path)
                print ("  -> Done")
        else:
            # write everything to the given path
            if os.path.isdir(path):
                fname = "{}.json".format(contendict.get('SensorID'))
                path = os.path.join(path,fname)
            writeJson(contentdict, path)
        return days[-1]
    except:
        return False


def read_data_dict(path,format='JSON'):
    """
    write the dictionary as Json
    { "SensorID":"",
      "SensorName":"",
      "DataRevisionNumber":"",
      "etc":"",
      "DataType": "",
      "DataContent": { times : array,
                       spectralarray : array of dicts,
                       temp  : array
                       etc...
                     }
    """

    try:
        with open(path, 'r') as infile:
            contentdict = json.load(infile)
        return contentdict
    except:
        return {}


def cleanup(path, deldate, backup=True, debug=False):

    fi = open(path, 'rt')
    # Read all lines and obtain Times, average time and data
    starttime = None
    newfi = []
    bakfi = []
    for line in fi:
        linefinished = False
        linedict = {}
        if line.startswith('Start'):
            getdata = False
            starttime = dparser.parse(line,fuzzy=True)
        if starttime and starttime >= deldate:
            newfi.append(line)
        elif starttime:
            bakfi.append(line)
    fi.close()
    if backup:
        print ("Backing up old data")
        with open(path+'.bak','wt') as fi:
            for line in bakfi:
                fi.write(line)
    if not debug:
        print ("Writing cleaned file")
        with open(path,'wt') as fi:
            for line in newfi:
                fi.write(line)
    return True

def create_datastream(datadictionary, resultlist, config={}):

    datastream = DataStream()
    datastream.header['SensorName'] = datadictionary.get('SensorName')
    datastream.header['SensorID']  = datadictionary.get('SensorID')
    array = [[] for el in KEYLIST]
    roi = config.get('roi',[])
    energylist = config.get('energylist',[])
    timestamps = times(datadictionary)

    array[0] = [mdates.date2num(dparser.parse(el,fuzzy=True)) for el in timestamps]

    for i,el in enumerate(roi):
        ar = []
        #print (el)
        if isinstance(el,list):
            el = "{}-{}".format(el[0],el[1])
        for result in resultlist:
            ar.append(result[str(el)][3])
        key = KEYLIST[i+1]
        #print (key)
        datastream.header['col-{}'.format(key)] = str(energylist[i])
        datastream.header['unit-col-{}'.format(key)] = 'KeV'
        array[i+1] = ar

    #print ("Array", array)
    datastream.ndarray = np.asarray([np.asarray(el, dtype='object') for el in array], dtype='object')
    #print ("Header", datastream.header)
    #print (resultlist)
    return datastream


def analyze_gamma_data(datadictionary, config={}, debug=False):
    """
    DESCRIPTION
        main function for analyzing data. is calling singlespecanalysis for all timesteps
    """
    resultlist=[]
    timestamps = times(datadictionary)
    for time in timestamps:
        name, data = get_spectraldata(time,datadictionary)
        if debug:
            print (" Obtained: ", name, data)
            print (" ---------------------------")
        if time == timestamps[-1]:
            sresult = singlespecanalysis(data,config=config,plot=True,name=name,debug=debug)
        else:
            sresult = singlespecanalysis(data,config=config,plot=False,name=name,debug=debug)
        resultlist.append(sresult)
        if debug:
            print (" DONE")
            print (" ---------------------------")
    if debug:
        print (" ---------------------------")
        print (" All time steps finished")
        print (" ---------------------------")
    datastream = create_datastream(datadictionary, resultlist,config=config)
    return datastream

def hl_envelopes_idx(s, dmin=1, dmax=1, split=False):
    """
    Input :
    s: 1d-array, data signal from which to extract high and low envelopes
    dmin, dmax: int, optional, size of chunks, use this if the size of the input signal is too big
    split: bool, optional, if True, split the signal in half along its mean, might help to generate the envelope in some cases
    Output :
    lmin,lmax : high/low envelope idx of input signal s
    """

    # locals min
    lmin = (np.diff(np.sign(np.diff(s))) > 0).nonzero()[0] + 1 
    # locals max
    lmax = (np.diff(np.sign(np.diff(s))) < 0).nonzero()[0] + 1 


    if split:
        # s_mid is zero if s centered around x-axis or more generally mean of signal
        s_mid = np.mean(s)
        # pre-sorting of locals min based on relative position with respect to s_mid 
        lmin = lmin[s[lmin]<s_mid]
        # pre-sorting of local max based on relative position with respect to s_mid 
        lmax = lmax[s[lmax]>s_mid]


    # global max of dmax-chunks of locals max 
    lmin = lmin[[i+np.argmin(s[lmin[i:i+dmin]]) for i in range(0,len(lmin),dmin)]]
    # global min of dmin-chunks of locals min 
    lmax = lmax[[i+np.argmax(s[lmax[i:i+dmax]]) for i in range(0,len(lmax),dmax)]]

    return lmin,lmax

def get_envelope(signal):

    N=10
    s = np.array(signal)
    q_u = np.zeros(s.shape)
    q_l = np.zeros(s.shape)

    #Prepend the first value of (s) to the interpolating values. This forces the model to use the same starting point for both the upper and lower envelope models.

    u_x = [0,]
    u_y = [s[0],]

    l_x = [0,]
    l_y = [s[0],]

    #Detect peaks and troughs and mark their location in u_x,u_y,l_x,l_y respectively.

    for k in range(1,len(s)-1):
        if (np.sign(s[k]-s[k-1])==1) and (np.sign(s[k]-s[k+1])==1):
            u_x.append(k)
            u_y.append(s[k])

        if (np.sign(s[k]-s[k-1])==-1) and ((np.sign(s[k]-s[k+1]))==-1):
            l_x.append(k)
            l_y.append(s[k])

    #Append the last value of (s) to the interpolating values. This forces the model to use the same ending point for both the upper and lower envelope models.

    u_x.append(len(s)-1)
    u_y.append(s[-1])

    l_x.append(len(s)-1)
    l_y.append(s[-1])

    #Fit suitable models to the data. Here I am using cubic splines, similarly to the MATLAB example given in the question.

    u_p = interp1d(u_x,u_y, kind = 'cubic',bounds_error = False, fill_value=0.0)
    l_p = interp1d(l_x,l_y,kind = 'cubic',bounds_error = False, fill_value=0.0)

    #Evaluate each model over the domain of (s)
    for k in range(0,len(s)):
        q_u[k] = u_p(k)
        q_l[k] = l_p(k)

    return q_u, q_l

def clean_counts(data):
    """
        DESCRIPTION
        removes leading zeros (except one) and fills up to 1024 channels
    """
    # drop zeros
    cleandata = np.trim_zeros(data,'f')
    # remove the last 10 channels (as there might be some error counts)
    cleandata = cleandata[:-14]
    # add one zero again
    cleandata = [0] + list(cleandata)
    # fill with zeros until 1024 channels
    while not len(cleandata) == 1024:
        cleandata.append(0)

    return cleandata

def despike(yi, th=100000):
   """
   DESCRIPTION
   Remove spike from array yi, the spike area is where the difference between 
   the neigboring points is higher than th.
   https://stackoverflow.com/questions/37556487/remove-spikes-from-signal-in-python
   """

   y = np.copy(yi) # use y = y1 if it is OK to modify input array
   n = len(y)
   x = np.arange(n)
   c = np.argmax(y)
   d = abs(np.diff(y))
   try:
     l = c - 1 - np.where(d[c-1::-1]<th)[0][0]
     r = c + np.where(d[c:]<th)[0][0] + 1
   except: # no spike, return unaltered array
     return y
   # for fit, use area twice wider then the spike
   if (r-l) <= 3:
     l -= 1
     r += 1
   s = int(round((r-l)/2.))
   lx = l - s
   rx = r + s
   # make a gap at spike area
   xgapped = np.concatenate((x[lx:l],x[r:rx]))
   ygapped = np.concatenate((y[lx:l],y[r:rx]))
   # quadratic fit of the gapped array
   z = np.polyfit(xgapped,ygapped,2)
   p = np.poly1d(z)
   y[l:r] = p(x[l:r])
   return y

def smooth_data(y,N=10):
   N=10
   #print (len(y))
   s = np.convolve(y, np.ones((N,))/float(N))
   s = s[int(N/2):]
   #print (len(s))
   return s

def plot_background(data,maxx,interp):
        """
    DESCRIPTION
        plot background fit and dataset
    CALL:
        by fit_between_intervals
        """
        fig = plt.figure()
        ax = fig.add_subplot(1,1,1)
        #ax.set_yscale('log')
        #plt.title("Spectra comparison")
        plt.ylabel("counts per hour [1/h]")
        plt.xlabel("channel [number]")
        #plt.plot(range(0,len(data)),data,np.arange(0,maxx), interp,color='purple',linewidth=0.6)
        plt.plot(range(0,len(data)),data,color='black',linewidth=0.6)
        plt.plot(np.arange(0,maxx), interp,color='purple',linewidth=0.6)
        plt.show()

def fit_between_intervals(data,indices,debug=False):
        """
        DESCRIPTION
            x=indicies, y = values
        CALL
            by fit_background
        """
        y = [data[i] for i in indices]
        x = indices
        if debug:
            print ("data", x,y)
        interfunc = interp1d(x, y, kind='linear')
        xnew = np.arange(0,max(x))
        ynew = interfunc(xnew)
        if debug:
            plot_background(data[0:max(x)],max(x),interfunc(range(0,max(x))))
        datacorr = data[0:max(x)]-interfunc(range(0,max(x)))
        return datacorr, interfunc(range(0,max(x))), max(x)


def fit_background(data,startstep=100,steps=3,channels=1024, debug=False):
        # get position of max
        #######################
        # step 1: get some stuetzstellen for an initial fit 
        data=list(data)
        mind = data.index(max(data))
        intlist = [0,mind]
        startintervals = [mind+(i*startstep) for i in range(int(channels/startstep)+1) if mind+(i*startstep) < channels-1]
        intervals = [0] + startintervals + [channels-1]
        if debug:
            print ("Length", len(data))
            print (intervals)

        datacorr, interp, maxx = fit_between_intervals(data,intervals,debug=debug)
        if debug:
            print ("Max ini", mind)
            print ("Int ini", intervals)

        #######################
        # step 2: get some stuetzstellen for an initial fit 
        add = intervals[:2] + [intervals[-1]]
        if debug:
            print ("Adding", add)
            print ("Length", len(datacorr))
        datacorr, newintervals, interp, maxx = append_intervals(intervals, datacorr, extend=False,add=add,debug=debug)
        if debug:
            print ("Length", len(datacorr), len(newintervals))

        #######################
        # step 3: add an additional step to get max
        # removed this step because of problem with peak fits
        #datacorr, newintervals, interp, maxx = append_intervals(newintervals, datacorr, extend=True,add=[list(datacorr).index(max(datacorr))],debug=debug)

        #######################
        # step 4: iterate until length stays constant
        oldlength = len(newintervals)
        newlength = 9999
        count = 1
        while oldlength<newlength:
            count += 1
            oldlength = len(newintervals)
            datacorr, newintervals, interp, maxx = append_intervals(newintervals, datacorr, extend=True,add=None,debug=debug)
            newlength = len(newintervals)

        if debug:
            print ("Optimal Background after {} iteration steps".format(count))
        return datacorr, interp, maxx, newintervals


def append_intervals(intervals, dataset, extend=True, add=[], minwindow = 20, debug=False):
        """
        DESCRIPTION
            create index lists for minima
        CALL
            by fit_background
        """
        newintervals = []
        for idx,el in enumerate(intervals):
            if idx < len(intervals)-1:
                nextel = intervals[idx+1]
                #print (el, nextel)
                if (nextel - el) > minwindow:
                    datasequ = list(dataset[el:nextel])
                    try:
                        minidx = datasequ.index(min(datasequ))+el-1
                    except:
                        minidx = el
                    newintervals.append(minidx)
        if len(newintervals) > 0:
            if extend:
                newintervals += intervals
            if add:
                newintervals += add
            newintervals = [el if el<len(dataset) else len(dataset)-1 for el in newintervals]
            newintervals = list(set(newintervals))
            newintervals = sorted(newintervals)
            if debug:
                print ("New intervals:", newintervals)
            datacorr, interp, maxx = fit_between_intervals(dataset,newintervals,debug=debug)
            #plot_background(datacorr,maxx,interp)
            return datacorr, newintervals, interp, maxx
        else:
            return dataset, intervals, interp, maxx


def singlespecanalysis(data, config={}, plot=False, name='example', background=None, energycalib=True, plotname='Spectra', debug=False):
    """
    Takes data of a single spectrum and calculates compton background, corrected curve.
    Identifies maxima in +-10 channels of given roi and defines rois.
    If energy levels are provided, a enenrgy calibration curve is determined.
    Returns a dictionary containing Roi: [Center, width, peakcount, roicount], ResiudalCompt:[], CalibrationFit:, 

    check interpolation for Spectral_401188.Chn

    """ 
    result = {}
    roi = config.get('roi',[])
    colorlst = config.get('colorlst',[])
    isotopelst = config.get('isotopelst',[])
    energylist = config.get('energylist',[])
    graphdir = config.get('graphdir',[])
    initialstep = config.get('initialstep',100)

    if not roi:
        print ("please provide a list of roi s like [63, 114, 231, 291, 363, [197,398]]")

    searchrange = 10
    channellist = []
    xs, ys = 0., 0.

    # 1. clean leading zeros and fill to correct length
    data = clean_counts(data)
    # 2. eventually drop individual spikes
    data = despike(data, max(data)*2)
    result[name] = data

    # 2b. Create a basic data plot
    if debug:
        s = smooth_data(data)
        u,l = get_envelope(data)

        fig = plt.figure()
        ax = fig.add_subplot(1,1,1)
        ax.set_yscale('log')
        plt.title("Basic spectrum")
        plt.ylabel("counts per hour [1/h]")
        plt.xlabel("channel [number]")
        plt.plot(range(0,len(data)),data,color='black',linewidth=0.6)
        plt.plot(range(0,len(s)),s,color='yellow',linewidth=0.6)
        plt.plot(range(0,len(l)),l,color='blue',linewidth=0.6)
        plt.plot(range(0,len(u)),u,color='red',linewidth=0.6)
        plt.show()

    # 3. determine dataset corrected for background
    if not background:
        s = smooth_data(data)
        datacorr, interp, maxx, newintervals = fit_background(s,startstep=initialstep,channels=len(s),debug=debug)

    else:
        # background is a list with two arrays: [mean,stddev]
        #print ("Using backgroud subtraction")
        #print (len(data), len(background[0]))
        datacorr = data-background[0]
        maxx = len(datacorr)

    if debug:
        dc, intp, maxxx = fit_between_intervals(s,newintervals)
        fig = plt.figure()
        ax = fig.add_subplot(1,1,1)
        ax.set_yscale('log')
        #plt.title("Background fit ")
        plt.ylabel("counts per hour [1/h]")
        plt.xlabel("channel [number]")
        plt.plot(range(0,len(data)),data,color='black',linewidth=0.6)
        plt.plot(range(0,maxx),intp,color='green',linewidth=0.6)
        plt.show()

    if debug:
        print (" continue with roi")
    # 4. ROIS
    for elem in roi:
        #print ("ROI", elem)
        if isinstance(elem, int):
            peak = max(datacorr[elem-searchrange:elem+searchrange+1])
            # Fit peak
            #print (peak, datacorr)
            xw,yw = getdatawin(datacorr, peak)
            # store xw and yw for rectangle in datacorr plot
            if elem == 291:
                xs = xw
                ys = yw
            #print (len(xw), len(yw))
            max_x, max_y, I, Iuncert, wi = fitpeak(xw,yw,n=4,plot=plot)
            width = 5 # the practical measure of resolution is the width of the photopeak at  half  its  amplitude  known  as  the  Full  Width  at  Half  Ma
            count = sum(datacorr[elem-width:elem+width])
            #result[str(elem)] = [list(datacorr).index(peak), width, peak, count, 0]
            result[str(elem)] = [max_x, wi, max_y, I, Iuncert, datacorr[elem], 293-max_x]
            channellist.append(max_x)
        else:
            try:
                if len(elem) == 2:
                    peak = max(datacorr[elem[0]:elem[1]])
                    width = int((elem[1]-elem[0])/2.)
                    count = sum(datacorr[elem[0]:elem[1]])
                    result[str(elem[0])+'-'+str(elem[1])] = [list(datacorr).index(peak), width, peak, count, 0, datacorr[elem[0]],0]
            except:
                print ("Failure")

    if debug:
        print ("     -> done")
        #print ("result", result)

    if debug:
        print ("  Step 3: energy calibration")

    #print (len(range(0,1025)), len(data))
    if energycalib:
        data_new, coefs = energycalibration(range(0,len(data)), data, ch=channellist, e=energylist, n=2, use=5, plot=plot,addzero=True, plotmax = maxx, config=config, debug=debug)
        try:
            newtime = mdates.date2num(datetime.utcfromtimestamp(int(name)*3600.)) # - datetime.timedelta(days=1)
        except:
            newtime = mdates.date2num(dparser.parse(name,fuzzy=True))
        result[newtime] = data_new
        result[str(newtime)+'_'+str(coefs)] = coefs
        if debug:
            print ("     -> done")
    else:
        if debug:
            print ("     -> skipped")

    if debug:
        print ("  Step 4: plotting")

    if plot:
        # Plot spectra
        if not plotname:
            plotname = 'Spectra'
        fig = plt.figure(2)
        ax = fig.add_subplot(1,1,1)
        ax.set_yscale('log')
        plt.title(name)
        plt.ylabel("counts per hour [1/h]")
        if not background:
            dc, intp, maxxx = fit_between_intervals(s,newintervals)
            plt.xlabel("channel [number]")
            plt.plot(range(0,maxx),intp,color='green',linewidth=0.6)
        else:
            plt.xlabel("energy [KeV]")
            ax.fill_between(range(0,len(data)), data, background[0], alpha=.1, color='brown')
            ax.fill_between(range(0,len(data)), background[0]+background[1], background[0]-background[1], alpha=.25, color='green')
            ax.plot(range(0,len(data)),background[0], '-', color='green')
        plt.plot(data[:maxx],color='orange',linewidth=0.6)
        if not background:
            plt.legend(('Interpolated/linear function','Spectrum'),loc=3)
        else:
            plt.legend(('Background determination','Spectrum'),loc=3)
        x1,x2,y1,y2 = plt.axis()
        # Add ROIs
        #patchlst = [item for item in roi]
        patchlst = [[result[str(item)][0]-result[str(item)][1],result[str(item)][1]] for item in roi if isinstance(item, int)]
        #colorlst = ['red','blue','yellow','green'] #,'brown']
        #isotoplst = ['Ba','Cs','Ka','Bi'] #,'Tl']
        for idx, p in enumerate([patches.Rectangle((pa[0], y1), 2*pa[1], y2-y1,facecolor=colorlst[i],alpha=0.1,) for i,pa in enumerate(patchlst)]):
            ax.add_patch(p)
            ax.text(patchlst[idx][0], y2-0.8*(y2-y1), '(${}$)'.format(isotopelst[idx]), horizontalalignment='left', color=colorlst[idx], verticalalignment='bottom')
        #plt.plot(x,y,np.arange(0,maxx), interp, color='green',linewidth=0.6)
        plt.grid()
        pylab.savefig(os.path.join(graphdir,'{}.png'.format(plotname)))
        #pylab.savefig(os.path.join(graphdir,'{}_{}.png'.format(plotname,name))) # Speichert den spectra-plot als png-Datei

        fig = plt.figure(3)
        ax = fig.add_subplot(1,1,1)
        plt.ylabel("counts per hour [1/h]")
        ax.set_yscale('log')
        difffunc = datacorr
        if not background:
            plt.xlabel("channel [number]")
            ax.set_xlim([30,len(datacorr)])
            #difffunc = data[:maxx]-interp
        else:
            plt.xlabel("energy [KeV]")
            #difffunc = datacorr
        plt.plot(difffunc, color='blue',linewidth=0.6) # Plottet die Differenz aus spec1 und der interpolierten Funktion
        x1,x2,y1,y2 = plt.axis()
        # Add ROIs
        #patchlst = [item for item in roi]
        patchlst = [[result[str(item)][0]-result[str(item)][1],result[str(item)][1]] for item in roi if isinstance(item, int)]
        for idx, p in enumerate([patches.Rectangle((pa[0], y1), 2*pa[1], y2-y1,facecolor=colorlst[i],alpha=0.1,) for i,pa in enumerate(patchlst)]):
            ax.add_patch(p)
            ax.text(patchlst[idx][0], y2-0.8*(y2-y1), '(${}$)'.format(isotopelst[idx]), horizontalalignment='left', color=colorlst[idx], verticalalignment='bottom')
        #plt.legend(('Difference'),loc=6)
        plt.grid()
        pylab.savefig(os.path.join(graphdir,'{}_corrected_{}.png'.format(plotname,name))) # Speichert den spectra-plot als pdf-Datei
        print ("Graphs created and stored to {} (will be plotted with DEBUG option)".format(graphdir))
        if debug:
            plt.show()
        plt.close()

    return result

def getAverage(result, filerange, plot=True):
    """
    calculates the mean of the provided filerange
    returns mean array [[mean],[sd]]
    """
    allarrays = []
    for i in filerange:
        newtime = mdates.date2num(datetime.datetime.utcfromtimestamp(int(i)*3600.))
        ar = result.get(newtime,[])
        if len(ar) > 0:
            allarrays.append(ar)

    me = np.mean(allarrays, axis=0)
    st = np.std(allarrays, axis=0)

    if plot and debug:
        # Determine the following channel energy relation from each analysis
        fig, ax = plt.subplots(1, 1)
        ax.set_yscale('log')
        x = range(0,len(me),1)
        ax.set_xlim([0,3000])
        ax.fill_between(x, me+st, me-st, alpha=.25)
        ax.plot(x,me, '-')
        plt.xlabel("energy [KeV]")
        plt.ylabel("counts per hour [1/h]")
        plt.grid()
        plt.show()

    return [me,st]


# Detect local minima
def comptoncorr(spectrum, intervallist=[]):
    minlist = []

    for idx,el in enumerate(intervallist):
        if idx > 0:
            spectemp = spectrum[lastel:el]
            minspectemp = min(spectemp)
            #minindex = list(spectrum).index(minspectemp)
            minindex = lastel+list(spectemp).index(minspectemp)
            print (len(spectemp), minspectemp, minindex)
            minlist.append([minindex, minspectemp])
        lastel = el
        #print el
    x = [elem[0] for elem in minlist]
    y = [elem[1] for elem in minlist]
    #print max(x)
    interfunc = interp1d(x, y, kind='linear')
    xnew = np.arange(0,max(x))
    ynew = interfunc(xnew)
    return interfunc(range(0,max(x))), max(x), x, y

    #diffunc = (spec1[0:max(x)] - interfunc(range(0,max(x))))

def fitpeak(x,y,n=4,plot=False):
    """
    Fitting a polynomial function to peaks
    """
    I, Iuncert = 0,0
    coefs, C_p = np.polyfit(x, y, n, cov=True)
    x_new = np.linspace(x[0], x[-1], num=len(x)*10)
    TT = np.vstack([x_new**(n-i) for i in range(n+1)]).T
    yi = np.dot(TT, coefs)  # matrix multiplication calculates the polynomial values
    C_yi = np.dot(TT, np.dot(C_p, TT.T)) # C_y = TT*C_z*TT.T
    sig_yi = np.sqrt(np.diag(C_yi))  # Standard deviations are sqrt of diagonal
    max_x = x_new[list(yi).index(max(yi))]
    max_y = max(yi)
    area = True
    if area:
        # get x range
        #halfrange = 3 # given in channels
        halfrange = 2 + int(max_x/50.)
        x_win = [el for el in x_new if el > max_x-halfrange and el <= max_x+halfrange]
        y_win = yi[list(x_new).index(x_win[0]):list(x_new).index(x_win[-1])+1]
        t_y = yi+sig_yi
        y_winmax = t_y[list(x_new).index(x_win[0]):list(x_new).index(x_win[-1])+1]
        t_y = yi-sig_yi
        y_winmin = t_y[list(x_new).index(x_win[0]):list(x_new).index(x_win[-1])+1]
        if not len(x_win) == len(y_win):
            print ("------------------------------------------- Check it!!!!!!!!!!!!!!!!!!!")
        I = np.trapz(y_win, x_win)
        Imax = np.trapz(y_winmax, x_win)
        Imin = np.trapz(y_winmin, x_win)
        Iuncert = (Imax-Imin)/2.
    if plot:
        fg, ax = plt.subplots(1, 1)
        #ax.set_title("Fit for Polynomial (degree {}) with $\pm1\sigma$-interval".format(n))
        plt.xlabel("channel [number]")
        plt.ylabel("counts per hour [1/h]")
        ax.fill_between(x_win, 0, y_win, alpha=.25, facecolor='green')
        ax.fill_between(x_new, yi+sig_yi, yi-sig_yi, alpha=.25)
        #ax.text(x_win, ,'I',horizontalalignment='center',color='black',verticalalignment='bottom')
        ax.plot(x_new, yi,'-')
        ax.plot(x, y, 'ro')
        ax.axis('tight')
        fg.canvas.draw()
        if x_win[0] < 290 and 290 < x_win[-1]:
            pylab.savefig(os.path.join(graphdir,'fitpeak.png')) # Speichert den fitpeak als pdf-Datei
            plt.show()
        plt.close()
    return max_x, max_y, I, Iuncert, halfrange


def getdatawin(data, peak, width=None):
    """
    Extract data within a specfic range
    """
    xmid = list(data).index(peak)
    if not width:
        w = 2 + int(xmid/25.)
    else:
        w = width
    y = data[xmid-w:xmid+w+1]
    x = range(xmid-w,xmid+w+1)
    return x,y


def energycalibration(x, count, ch=[], e=[], n=1,  use= 2, plot=False, addzero=False, plotmax=None, config={}, debug=False):
    """
    Do a energy calibration uing the provided channel/energy relation
    Default uses a linear fit (n=1)
    Use defines which elemenmt of channellist should be used for calibration (2 = first two elements)
         All other data is shown in the plot
    # use
    # returns x column converted to energy
    """
    #roi = config.get('roi',[])
    #colorlst = config.get('colorlst',[])
    isotopelst = config.get('isotopelst',[])
    graphdir = config.get('graphdir',[])
    caliblst = config.get('caliblst',[])
    ch = ch[:len(caliblst)]
    e = e[:len(caliblst)]
    if len(caliblst) > 0:
        usech = [x for x, y in zip(ch, caliblst) if y in [True,'True']]
        usee = [x for x, y in zip(e, caliblst) if y in [True,'True']]
    else:
        usech = ch[:use]
        usee = e[:use]

    if not plotmax:
        plotmax = x[-1]
    # use zero value for fit as well
    if addzero:
        x = np.asarray(x)
        zero = [0]
        zero.extend(usech)
        usech = zero
        zero = [0]
        zero.extend(usee)
        usee = zero
        #use = use+1

    coefs, C_p = np.polyfit(usech, usee, n, cov=True)
    #x_new = np.linspace(0, 500, num=len(x)*10)
    TT = np.vstack([x**(n-i) for i in range(n+1)]).T
    yi = np.dot(TT, coefs)  # matrix multiplication calculates the polynomial values
    C_yi = np.dot(TT, np.dot(C_p, TT.T)) # C_y = TT*C_z*TT.T
    sig_yi = np.sqrt(np.diag(C_yi))  # Standard deviations are sqrt of diagonal

    # allow for linear calibration and more complex
    if plot:
        # Determine the following channel energy relation from each analysis
        fig, ax = plt.subplots(1, 1)
        #fig = plt.figure(4)
        ax.set_xlim([0,plotmax])
        ax.set_ylim([0,3000])
        ax.plot(x, yi, '-',color='black')
        plt.xlabel("channel [number]")
        plt.ylabel("energy [KeV]")
        ax.fill_between(x, yi+sig_yi, yi-sig_yi, alpha=.25)
        #plt.plot(yi+sig_yi, x, '-',color='blue')
        if addzero:
            usee = usee[1:]
            usech = usech[1:]
        ax.plot(usech, usee,'o')
        try:
            ax.plot(usech, usee,'o',color='red')
        except:
            pass
        #isotopelst = ['^{133}Ba','^{137}Cs','^{40}Ka','^{214}Bi']
        for idx, xy in enumerate(zip(usech, usee)):
            ax.annotate('(${}$)'.format(isotopelst[idx]), xy=xy, xytext=(5, -7), textcoords='offset points')
        plt.grid()
        pylab.savefig(os.path.join(graphdir,'calibration.png')) # Speichert den spectra-plot als pdf-Datei
        print ("Graphs created and stored to {}".format(graphdir))
        if debug:
            plt.show()
        plt.close()

    # Interpolate data (using cubic splines) and resample at new index values
    x_new = range(0,3000,1)
    data = count
    func = interp1d(yi, data, kind='linear')
    if plot:
        # Determine the following channel energy relation from each analysis
        fig, ax = plt.subplots(1, 1)
        ax.set_yscale('log')
        ax.set_xlim([0,3000])
        ax.plot(yi, data, '-')
        #ax.plot(x_new, func(x_new),'--', color='red')
        plt.xlabel("energy [KeV]")
        plt.ylabel("counts per hour [1/h]")
        plt.grid()
        if debug:
            plt.show()
        plt.close()

    #print ("Energy range", min(yi), max(yi))
    x_new = range(int(np.ceil(min(yi))),int(np.floor(max(yi))),1)
    return func(x_new), coefs


def length(datadictionary):
    contd = datadictionary.get('DataContent')
    times = contd.get('time')
    return len(times)

def times(datadictionary):
    contd = datadictionary.get('DataContent')
    times = contd.get('time')
    return times

def get_spectraldata(time,datadictionary):
    name = ''
    data = []
    contd = datadictionary.get('DataContent')
    times = contd.get('time')
    specdata = contd.get('spectraldata')
    sensorid = datadictionary.get('SensorName')
    #times = contd.get(time)
    pos = times.index(time)
    specdatadict = specdata[pos]
    data = np.asarray(specdatadict.get('data'))
    name = "{}-{}".format(sensorid,time)
    #name = datetime.timestamp(datetime.strptime(time,"%Y-%m-%dT%H:%M:%S"))
    return name, data


def update_configuration(conf, joblist=None, path=None, export=None):
    """
    DESCRIPTION
        get options and configuration and update config dictionary accordingly
    """
    singleroi = [int(el) for el in conf.get('singleroi',[])]
    rangeroi = [int(el) for el in conf.get('rangeroi',[])]
    singleroi.append(rangeroi)
    conf['roi'] = singleroi
    energylist = [int(el) for el in conf.get('energylist',[])]
    conf['energylist'] = energylist
    if joblist:
        conf['joblist'] = joblist
    if joblist:
        conf['path'] = path
    if joblist:
        conf['export'] = export
    return conf

def extract_paths(path, startdate=(datetime.utcnow()-timedelta(days=1)).date(), enddate=datetime.utcnow().date(),debug=False):
    """
    DESCRIPTION
        extracts file paths if only a directory and a time range is given
    """
    print ("Found a directory ... extracting loading all files between {} and {}".format(startdate,enddate))
    loadlist = []
    filelist = glob.glob(os.path.join(path,'*.json'))
    for f in filelist:
         dd = os.path.basename(f).split('_')[-1]
         if debug:
             print ("Checking", dd)
         filedate = starttime = dparser.parse(dd,fuzzy=True)
         if filedate.date() <= enddate and filedate.date() >= startdate:
             loadlist.append(f)
    return loadlist

def read_data_dict_from_list(loadlist):
    """
    DESCRIPTION
        combines all loaded datadictionaries
    """
    d2 = {}
    for path in loadlist:
        print ("Loading: ", path)
        d1 = read_data_dict(path)
        if d2:
            d2 = joinDataDict(d1, d2)
        else:
            d2 = d1
    return d2
    

def main(argv):
    version = '1.0.0'
    statusmsg = {}
    joblist = ['extract','cleanup']
    debug = False
    conf = {}
    configpath = None
    path = ''
    export = ''
    startdate = (datetime.utcnow()-timedelta(days=1)).date()
    enddate = datetime.utcnow().date()
    debug = False


    try:
        opts, args = getopt.getopt(argv,"hc:p:o:j:s:e:vD",["config=","path=","output=","joblist=","startdate=","enddate="])
    except getopt.GetoptError:
        print ('gamma.py -c <config> -p <path> -o <output> -v <version>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print ('------------------------------------------------------------')
            print ('Description:')
            print ('-- gamma.py extracts/analyses gamma data   --')
            print ('------------------------------------------------------------')
            print ('gamma.py blablabla')
            print ('-------------------------------------')
            print ('Usage:')
            print ('gamma.py -c <config> -j <joblist>')
            print ('-------------------------------------')
            print ('Options:')
            print ('-c (required) : path to a configuration file')
            print ('-p            : path to a data file')
            print ('-o            : path to export json in case of extract from raw')
            print ('-j            : override the joblist in conf')
            print ('-s            : startdate (load)')
            print ('-e            : enddate (load)')
            print ('-v            : print the current version of gamma.py')
            print ('-------------------------------------')
            print ('Application:')
            print ('1) extracting daily files from large source')
            print ('python3 gamma.py -p /home/leon/Cloud/Software/MagPyAnalysis/RadonGammaSpekLinux/data/DIGIBASE_16272059_0001.Chn -j extract,cleanup -o /home/leon/Cloud/Software/MagPyAnalysis/RadonGammaSpekLinux/ -D')
            print ('2) loading and analyzing data')
            print ('python3 gamma.py -p /home/leon/Cloud/Software/MagPyAnalysis/RadonGammaSpekLinux/DIGIBASE_16272059_0001_2021-05-15.json -j load,analyze -D')
            sys.exit()
        elif opt in ("-c", "--config"):
            configpath = arg
        elif opt in ("-p", "--path"):
            path = os.path.abspath(arg)
        elif opt in ("-o", "--output"):
            export = os.path.abspath(arg)
        elif opt in ("-j", "--joblist"):
            joblist = arg.split(',')
        elif opt in ("-s", "--startdate"):
            startdate = dparser.parse(arg,fuzzy=True).date()
        elif opt in ("-e", "--enddate"):
            enddate = dparser.parse(arg,fuzzy=True).date()
        elif opt == "-v":
            print ("gamma.py version: {}".format(version))
        elif opt in ("-D", "--debug"):
            debug = True

    if not debug:
        matplotlib.use('Agg')
    # Testing inputs
    # --------------------------------
    #read config
    addaux = True

    if not configpath:
        pass

    #  extracting configuration
    conf = GetConf2(configpath)
    conf = update_configuration(conf, joblist, path, export)
    joblist = conf.get('joblist')
    path = conf.get('path')
    export = conf.get('export')
    if debug:
        print ("Configuration looks like:")
        print (conf)

    # test inputpath
    # if json then eventually skip extract and use load
    if 'load' in joblist and 'extract' in joblist:
        print (" you need to choose either load (json) or extract (raw) - aborting")
        sys.exit() 

    if 'extract' in joblist:
        if debug:
            print ("Extract job:")
            print ("-----------------")
        datadictionary = read_linux_gamma(path,debug=debug)
        if conf:
            #datadictionary, jobs, export = interpreteConf(datadictionary, conf, jobs, export)
            pass
        if addaux: # defined in config
            # get auxiliary data paths from config file
            pass 
        if export:
            writesuccess = write_data_dict(datadictionary,export,debug=debug)
        if 'cleanup' in joblist and export and writesuccess:
            print (" data extracted and exported to json file - cleaning up old file")
            deldate = datetime(writesuccess.year, writesuccess.month, writesuccess.day)
            print (" deleting everything until {}".format(deldate))
            success = cleanup(path, deldate, debug=debug)

    if 'load' in joblist:
        if debug:
            print ("Loading data:")
            print ("-----------------")
        if os.path.isdir(path):
            loadlist = extract_paths(path,startdate,enddate,debug=debug)
            datadictionary = read_data_dict_from_list(loadlist)
        else:
            datadictionary = read_data_dict(path)
        if debug:
            print (" -> got {} spectral records".format(length(datadictionary)))
            print (datadictionary)

    if 'analyze' in joblist and len(datadictionary) > 0:
        datastream = analyze_gamma_data(datadictionary, config=conf, debug=debug)
        sensid = datastream.header.get('SensorID')
        op = os.path.join(conf.get('streampath','/tmp'),sensid)
        fb = "{}_".format(sensid)
        #print (datastream.ndarray)
        datastream=datastream.sorting()
        #print (num2date(datastream.ndarray[0][-1]))

        datastream.write(op,filenamebegins=fb, format_type=conf.get('dataformat','PYSTR'), mode='replace')
        #mp.plot(datastream)

    if 'merge' in joblist:
        if debug:
             print (" Calling merge ...")
        #mergedstream = merge_data(conf, startdate, enddate)

        def get_list(value):
            if isinstance(value,list):
                return value
            else:
                return [value]

        starttime = datetime(startdate.year, startdate.month, startdate.day)
        endtime = datetime(enddate.year, enddate.month, enddate.day,23,59,59)
        print (starttime, endtime)
        mqttpath = conf.get('streampath')
        sensorid = conf.get('sensorid')
        sourcepath = os.path.join(mqttpath,sensorid,'*')
        digibasestream = read(sourcepath,starttime=starttime,endtime=endtime)
        keylist = digibasestream._get_key_headers()
        for key in keylist:
            col = digibasestream._get_column(key)
            if np.isnan(col).all():
                digibasestream = digibasestream._drop_column(key)
        keylist = digibasestream._get_key_headers()
        sr = digibasestream.samplingrate()
        if debug:
             print ("   obtained ROI stream with {} data points".format(digibasestream.length()[0]))
             print ("   used keys are: {}".format(keylist))
        # Get sensors with current data in 
        sensorlist = get_sensors(mqttpath)
        mcount = 0

        if debug:
            print ("   - folder which eventually contain data:", sensorlist)
        for s in sensorlist:
            sconf = False
            for key in conf:
                if s.find(key) > -1:
                    sconf = conf.get(key)
            if sconf:
                print (" Found {}: merging ...".format(s))
                mcount += 1
                # load auxstream
                auxstream = read(os.path.join(mqttpath,s,'*'),starttime=starttime,endtime=endtime)
                if auxstream.length()[0] > 9:
                    # move every key to the specified new key
                    #  and drop previous keys
                    print (sconf)
                    keys = get_list(sconf.get('keys'))
                    newkeys = get_list(sconf.get('newkeys'))
                    if not len(keys) == len(newkeys):
                        print ("Length of keys and newkeys are not fitting")
                        continue
                    for idx,key in enumerate(keys):
                        newkey = newkeys[idx]
                        #auxstream.header['col-{}'.format(newkey)] = auxstream.header.get('col-{}'.format(key))
                        #auxstream.header['unit-col-{}'.format(newkey)] = auxstream.header.get('unit-col-{}'.format(key))
                        auxstream = auxstream._move_column(key,newkey)
                        auxstream = auxstream._drop_column(key)
                    auxstream.header['SensorKeys'] = ",".join(newkeys)
                    if debug:
                        print (auxstream.length())
                        print (auxstream.header)
                    # evetually despike data
                    if sconf.get('despike',None):
                        print ("    despiking data with threshold {}".format(sconf.get('despike')))
                        mp.plot(auxstream)
                        threshold = float(sconf.get('despike'))
                        auxstream = auxstream.flag_outlier(threshold=threshold)
                        auxstream = auxstream.remove_flagged()
                        mp.plot(auxstream)
                    # eventually smooth data
                    if sconf.get('smooth',None):
                        print ("    smoothing data")
                        print (sr)
                        auxsr = auxstream.samplingrate()
                        print (sr,auxsr)
                        win = int(np.round((sr/auxsr),0))
                        if win > 1:
                            auxstream = auxstream.smooth(window_len=win)
                        mp.plot(auxstream)
                    # merge data
                    mp.plot(digibasestream)
                    digibasestream = mergeStreams(digibasestream,auxstream)
                    mp.plot(digibasestream,outfile="/home/pi/Tmp/figure3.png")
                    pass
            else:
                print ("Sensor {} not found in configuration file".format(s))
        if mcount > 0:
            # write data
            pass

    print ("----------------------------------------------------------------")
    print ("gamma app finished")
    print ("----------------------------------------------------------------")
    print ("SUCCESS")
    if debug:
        return True

if __name__ == "__main__":
   main(sys.argv[1:])



"""
Structure of the JSON 


# EXAMPLE GAMMA CONFIGURATION FILE CONTENT:
# ###########################################

# path to log file (can be overruled by options)
extractpath     :   /var/log/magpy/mm-monitor.log
streampath      :   /srv/mqtt
graphdir        :   /tmp
dataformat      :   PYSTR

# timeranges to extract (can be overruled by options)
# ---------------------------------------------------
# starttime can be begin of file (bof) or any date like 2021-11-22
# endtime can be end-of-file (eof); now; now-1 (last full day); or any date
starttime       :   bof
endtime         :   now

# ROI definitions
# ---------------------------------------------------
# channles
roi             :   169, 338, 447, 541, 807
scarange        :   220,974
energylist      :   [609, 1120, 1460, 1764, 2614, 609]
isotopelst      :   ^{214}Bi,^{214}Bi,^{40}Ka,^{214}Bi,^{208}Tl,^{214}Bi
colorlst        :   orange,orange,blue,orange,red,green,brown


# MERGE definitions
MQ135_xxxx_0001    :   keys:var1;despike:600



# none,mail,telegram
notification   :   telegram

# configuration for notification
notificationconf   :   /etc/martas/telegram.cfg
"""
