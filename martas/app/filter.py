#!/usr/bin/env python
# coding=utf-8
"""

DESCRIPTION
    Filtering data files. By default all results are written to table '0002'. A DATAINFO input is not created. To do that add option -s and specify the sensor(s).


PARAMETER:
    sensors:

APPLICATION
    filter.py -j archive for daily jobs (read HF cdf archive files)
    filter.py -j realtime for permanent jobs (read HF database data)

filter.py -c singlefilter.cfg -j archive,second -d 5 -e 2021-02-01


# Better read a json stucture
a

filter.py requires a file called realtime.py within the same directory. realtime.py looks like:


filter.cfg

{"filter": {
              "groupparameterdict":{ "LEMI" : {"station" : "WIC", "filtertype":"default", "realtime" : "True", "window" : 40000},
                                     "LEMI036_3_0001_0001" : {"filtertype":"hann", "filterwidth":100, "resample_period":1, "realtime":"False", "window" : 40000},
                                     "LEMI025_28_0002_0001" : {"filtertype":"default", "realtime":"False", "window" : 40000},
                                     "GSM90_14245_0002_0001" : {"filtertype":"gaussian", "filterwidth":3.33333333, "resample_period":1, "realtime":"True", "window" : 10000},
                                     "IWT_TILT01_0001_0003" : {"filtertype": "default", "realtime" : "False", "window" : 40000},
                                     "BM35" : {"filtertype":"gaussian", "filterwidth":3.33333333, "resample_period":1, "realtime":"True", "window" : 10000},
                                     "G823A" : {"filtertype": "default", "realtime" : "False", "window" : 40000}
                                    },
              "scalardict":{"GP20S3NS_012201_0001_0001": {"type" : "GP20S3", "components" : ["x","y","z"]},
                             "GP20S3V_911005_0001_0001" :  {"type" : "GP20S3", "components" : ["x","y","z"]},
                             "GP20S3EW_111201_0001_0001" :  {"type" : "GP20S3", "components" : ["x","y","z"]}
                                    },
              "realtime": ["LEMI025_22_0003_0001","LEMI036_1_0002_0001","LEMI036_3_0001_0001","GSM90_14245_0002_0001","BM35_029_0001_0001","BM35_033_0001_0001"],
              "blacklist": ["LEMI025_28_0002_0001"],
              "basics": {"basepath":"/srv/archive","outputformat":"PYCDF","destination":"db"}
            }
}


# If you just want to filter data for archiving directly to disk only of a single sensor use
singlefilter.cfg
{"filter": {
              "groupparameterdict":{ "LEMI025_28_0002_0001" : {"filtertype":"default", "realtime":"False", "window" : 40000}},
              "scalardict":{},
              "realtime": [],
              "blacklist": [],
              "basics": {"basepath":"/srv/archive","outputformat":"PYCDF","destination":"disk"}
            }
}

and use:
filter.py -c singlefilter.cfg -j archive,second -d 5 -e 2021-02-01

Please note that filtering always reads the complete timerange..thus for long time ranges construct a bash job like:
filter.py -c singlefilter.cfg -j archive,second -d 2 -e 2021-02-01
filter.py -c singlefilter.cfg -j archive,second -d 2 -e 2021-01-30
filter.py -c singlefilter.cfg -j archive,second -d 2 -e 2021-02-28
filter.py -c singlefilter.cfg -j archive,second -d 2 -e 2021-02-26


| class  |    method     | since vers |  validation   |  comment    | manual  |  *used by |
| ------ |  -----------  | ---------- | ------------- | ----------  | ------- | --------- |
|        |               |            |               |             |         |           |
|        |  read_conf    |      2.0.0 |  yes          |             |         |           |
|        |  get_sensors  |      2.0.0 |  yes          |             |         |           |


"""

from magpy.stream import *
from magpy.core import database
from magpy.core import methods
import magpy.opt.cred as mpcred

import getopt
import socket
import json

from martas.version import __version__
from martas.core.methods import martaslog as ml
from martas.core import methods as mm


def read_conf(path):
    """
    DESCRIPTION
    Read a dictionary structure from a text file
    """
    filterdict = {}
    if os.path.isfile(path):
        with open(path, "r") as f:
             contents = f.read()
             c = contents.replace(" ","").replace("\n","")
             d = json.loads(c)
             filterdict = d.get('filter')
    return filterdict



def get_sensors(db=None,groupdict=None,samprate=None,recent=False,recentthreshold=7200,blacklist=None, debug=False):
    """
    DESCRIPTION
      extracts Sensors with names similar a the one in groupdict
      You can also select for sampling rates and recent data

    REQUIREMENTS
      an input in DATAINFO is required
        -> check G823 on Aldebaran
        -> highest res always to 0001 -> why are there so many LEMI028 inputs in table
    """

    if not groupdict:
        groupdict = {}
    if not blacklist:
        blacklist = []
    returndict = {}
    timerange = recentthreshold # used for sampling rate determination
    dbdateformat = "%Y-%m-%d %H:%M:%S.%f"

    for key in groupdict:
        print ("Get-senors: Dealing with group", key)
        # Checking all available sensors
        # ##############################
        samprate = groupdict[key].get('samplingrate',samprate)
        srlist = []
        stationid = groupdict[key].get('station',None)
        stationstr = ''
        if stationid:
            stationstr = ' AND StationID LIKE "{}"'.format(stationid)
        sensorlist = db.select('DataID', 'DATAINFO','DataID LIKE "{}%"{}'.format(key,stationstr))
        if debug:
            print ("   -> Found {}".format(sensorlist))

        # Apply black list
        # ##############################
        sensorlist = [sens for sens in sensorlist if not sens in blacklist]

        # If sampling rate criteria is given then subselect all sensors
        # ##############################
        if samprate:
            if debug:
                print ("- Limiting selection to sensors with sampling rate {}".format(samprate))
            validsensors1 = []  # add sensors for which the sampling rate is given in DATAINFO
            determinesr = [] # add senors for which the sampling rate needs to be determined
            srlist = []
            if debug:
                print (" * Selecting sensors with appropriate sampling rate in DATAINFO")
            for sensor in sensorlist:
                res = db.select('DataSamplingrate','DATAINFO','DataID="{}"'.format(sensor))
                try:
                    sr = float(res[0])
                    if debug:
                        print ("    Sensor (DATAINFO): {} -> Samplingrate: {}".format(sensor,sr))
                    if samprate == 'HF':
                        if sr < 0.98:
                            validsensors1.append(sensor)
                            srlist.append(sr)
                    else:
                        try:
                            samprate = float(samprate)
                        except:
                            samprate = 1.0
                        if samprate*0.98 <= sr and sr <= samprate*1.02:
                            validsensors1.append(sensor)
                            srlist.append(sr)
                except:
                    print ("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                    print ("Check sampling rate {} of {}".format(res,sensor))
                    print ("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                    determinesr.append(sensor)

            if len(determinesr) > 0 and debug:
                print (" * checking sampling rate of sensors with no sampling rate given in DATAINFO")
            for sensor in determinesr:
                lastdata = db.get_lines(sensor,timerange)
                if lastdata.length()[0] > 0:
                    sr = lastdata.samplingrate()
                    if debug:
                        print ("    Sensor (TESTING DATA): {} -> Samplingrate: {}".format(sensor,sr))
                    if samprate == 'HF':
                        if sr < 0.98:
                            validsensors1.append(sensor)
                            srlist.append(sr)
                    else:
                        try:
                            samprate = float(samprate)
                        except:
                            samprate = 1.0
                        if samprate*0.98 <= sr and sr <= samprate*1.02:
                            validsensors1.append(sensor)
                            srlist.append(sr)
                    # update data of these sensors in db
                    if debug:
                        print("new header of sensor without samplingrate:", lastdata.header)
                    if db and not debug:
                        # This will only be done once for a new sensor without sampling rate in DATAINFO
                        print("updating header with determined sampling rate:", lastdata.header)
                        db.write(lastdata)
            sensorlist = validsensors1
            if debug:
                print (" -> got {} sensors".format(len(sensorlist)))
        # If only sensors with current data should be used
        # ##############################
        if recent:
            currentthreshold = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(seconds=recentthreshold)
            if debug:
                print ("- Limiting selection to sensors with current data")
            validsensors = []
            validsr = []
            for idx,sensor in enumerate(sensorlist):
                last = db.select('time',sensor,expert="ORDER BY time DESC LIMIT 10")
                if len(last) > 0:
                    dbdate = last[0]
                    if dbdate > currentthreshold:
                        if debug:
                            print ("   current data for {}".format(sensor))
                        validsensors.append(sensor)
                        validsr.append(srlist[idx])
            sensorlist = validsensors

        if debug:
            print(" -> finally got {} sensors for filtering".format(len(sensorlist)))
        # join all obtained sensors into a new dictionary
        # ##############################
        for sensor in sensorlist:
            returndict[sensor] = groupdict.get(key)

    return returndict


def apply_filter(db, statusmsg=None, groupdict=None, permanent=None, blacklist=None, jobtype='realtime', endtime=datetime.now(timezone.utc).replace(tzinfo=None), dayrange=2, basepath='', dbinputsensors=None, destination='db', outputformat='PYCDF', recentthreshold=7200, debug=False):
    """
    DESCRIPTION
        Create one-second records by filtering data sets

    PARAMETER
        jobtype  : 'realtime' or 'archive'
        destination : 'db' or 'disk' -> if db (for realtime), disk archiving is done by archive; disk should only be used to convert old files 
    """
    # Allow to define groups in highreslist (e.g. LEMI036*)
    # Then firstly extract all instruments which fit to the appropriate group
    # and assign the parameters to each instrument.
    # Later list positions need to overwrite previous inputs: e.g.
    #   LEMI036*, par1, par2
    #   LEMI036_3, par4, par5
    if not statusmsg:
        statusmsg = {}
    if not groupdict:
        groupdict = {}
    if not permanent:
        permanent = []
    if not blacklist:
        blacklist = []
    if not dbinputsensors:
        dbinputsensors = []
    stationid = ''
    sensor = ''

    if debug:
        print ("Selected options are: Destination = {}; outputformat = {}; path = {}".format(destination, outputformat, basepath))

    dayrangedefault = dayrange
    sn = socket.gethostname()
    recent = True
    if jobtype == 'archive':
        recent = False

    highreslst = get_sensors(db=db,groupdict=groupdict,samprate='HF',blacklist=blacklist,recent=recent,recentthreshold=recentthreshold,debug=debug)
    if debug:
        print ("  Obtained HF list (sampling rate higher then 1 Hz):", highreslst)
        print ("  Starting one second data filtering:  (Filtering high resolution data sets)")
    p1start = datetime.now()
    for inst in highreslst:
        if debug:
            print ("  ----------------------------")
            print ("  Dealing with instrument {}".format(inst))
        name = '{}-filter-{}-{}'.format(sn,jobtype,inst.replace('_',''))
        last = DataStream()
        dataexpected = True
        try:
            noresample = None
            resample_period = None
            options = highreslst[inst]
            if debug:
                print ("     -> Selected options:", options)
                print ("  Obtaining projected data amount")
            if jobtype == 'realtime' and inst in permanent:
                if debug:
                    print ("     Realtime job selected -> getting data from database")
                amount = options.get('window',40000)
                rt = options.get('realtime',True)
                # amount * sampling rate defines coverage in seconds -> 10Hz (0.1 sec * 40000 -> 4000 sec or 0.5 sec * 10000 -> 5000 sec)
                if not mm.get_bool(rt):
                    amount = amount*3                # triple the amount of expected data if only hourly uploads are existing
                last = db.get_lines(inst,amount)
                try:
                    test = len(last)
                except:
                    statusmsg[name] = 'db access - data not existing'
                if debug:
                    print ("     -> Extracting {} data points".format(amount))
                if len(last) > 0:
                    sr = last.samplingrate()
                    expectedcoverage_in_sec = amount*sr
                    now = datetime.now(timezone.utc).replace(tzinfo=None)
                    last = last.trim(starttime=now-timedelta(seconds=expectedcoverage_in_sec),endtime=now) # remove all timesteps exceeding current time (typical IWT error)
                    if debug:
                        print ("     -> Extracted {} data points in reality after slicing".format(len(last)))
                        print ("     -> Done")
            elif jobtype == 'realtime' and not inst in permanent:
                dataexpected = False
            elif not jobtype == 'realtime':
                dayrange = options.get('dayrange',dayrangedefault)
                if debug:
                    print ("     Archive job selected -> getting data from archive")
                stationid = db.select('StationID', 'DATAINFO', 'DataID LIKE "{}"'.format(inst))[0]
                sensor = "_".join(inst.split('_')[:-1])
                datapath = os.path.join(basepath,stationid,sensor,inst,'*')
                print (datapath)
                begin = endtime-timedelta(days=dayrange)
                if debug:
                    print ("    Reading data between {} and {}".format(begin, endtime))
                last = read(datapath,starttime=begin,endtime=endtime)
                if debug:
                    print ("     -> found data between {}".format(last.timerange()))
                    print ("         corresponding to {} datapoints".format(len(last)))
                    print ("     -> Done")

            if debug:
                print ("    Got {} datapoints".format(last.length()[0]))

            if last.length()[0] > 0:
                if options.get('filtertype') == 'default':
                    filtertype = 'gaussian'
                    filterwidth = None # use default of 3.3333333 seconds
                else:
                    filtertype = options.get('filtertype','gaussian')
                    fwin = options.get('filterwidth',None)
                    filterwidth = timedelta(seconds=fwin)
                    resamp = options.get('resample_period',None)
                    if resamp == 'noresample':
                        noresample = True
                    else:
                        try:
                            resample_period=int(resamp)
                        except:
                            resample_period=1.0
                            pass
                missingdata = options.get('missingdata', 'conservative')
                destrevision = options.get('revision', '0002')
                if debug:
                    print ("    Default analysis parameter (may be re-specified for individual sensors): {}, filter type: {}, filter width: {}, resample period: {}, {}".format(inst, filtertype, filterwidth, resample_period, noresample))
                filtstream = last.filter(filter_type=filtertype, filter_width=filterwidth, missingdata=missingdata,resample_period=resample_period,noresample=noresample)
                # cut out the last 90% to reduce boundary filter effects # after 0.4.6
                try:
                    if debug:
                        print ("    Cutting out two lines (seconds) from start and two from beginning ..")
                    am = len(filtstream)
                    print (len(filtstream))
                    filtstream = filtstream.cut(am-2, 1, 0)
                    filtstream = filtstream.cut(am-4, 1, 1)
                    print ("Should be length -4", len(filtstream))
                    if debug:
                        print ("     Filtstream coverage: length={}, {}".format(len(filtstream), filtstream.timerange()) )
                        print ("     -> Done")
                except:
                    pass

                #### ALWAYS write to 0002 table
                newtab = "{}_{}".format(inst[:-5],destrevision)

                if not destination == 'disk':
                    # Write to database
                    try:
                        if not debug:
                            if newtab in dbinputsensors:
                                # if the sensor is already contained in DATAINFO then solely write data contents
                                db.write(filtstream,tablename=newtab)
                            else:
                                #print ("   Sensor contained in DBlist - adding Metainformation to DATAINFO")
                                db.write(filtstream)
                            #print ("    Writing to DB successful")
                        else:
                            print ("    !! Debug selected - skipping writing to DB")
                    except:
                        """db.write errors currently not captured - 
                           only general DB connection failures.
                           it happens once in a while that DB connection
                           is lost before writing (on sol at 3:00 and 4:00 UTC)
                           eventually connected to other DB access e.g.di analyses
                        """
                        pass
                else:
                    if debug:
                        print ("   Writing data directly to disk...")
                    archivepath = os.path.join(basepath,stationid,sensor,newtab)
                    if debug:
                        print ("   Destinationpath: {}".format(archivepath))
                    if not debug and outputformat and archivepath:
                        #print ("     valid write conditions")
                        filtstream.write(archivepath,filenamebegins=newtab+'_',format_type=outputformat)
                        #print ("    -> Done")
                    else:
                        print ("   Debug: skip writing")
                        print ("    -> without debug a file with {} inputs would be written to {}".format(filtstream.length()[0],archivepath))

                statusmsg[name] = 'fine'
            else:
                # send no data monitor
                if dataexpected:
                    statusmsg[name] = 'no data found'
        except:
            # send failed message to monitor
            statusmsg[name] = 'one second filter: general failure'

    if debug:
        p1end = datetime.now()
        print ("   One second job needed {}".format(p1end-p1start))
    return statusmsg


def main(argv):
    version = __version__
    configpath = ''
    statusmsg = {}
    debug=False
    jobtype = 'realtime'
    process = 'all'
    basepath = '/srv/archive'
    dayrange = 2
    destination='db'
    joblist = [] # jobtype can be realtime,second; archive;supergrad; etc
    newloggername = ''
    recentthreshold=7200
    sensorlist = []
    sendlog = False
    db = None
    telegramconfig = '/etc/martas/telegram.cfg'
    endtime = datetime.now(timezone.utc).replace(tzinfo=None)

    try:
        opts, args = getopt.getopt(argv,"hc:j:e:d:p:l:xD",["config=","joblist=","endtime=","dayrange=","path=","loggername","sendlog","debug=",])
    except getopt.GetoptError:
        print ('filter.py -c <config>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print ('-------------------------------------')
            print ('Description:')
            print ('-- filter.py to smooth and resample data --')
            print ('-----------------------------------------------------------------')
            print ('detailed description ..')
            print ('...')
            print ('...')
            print ('-------------------------------------')
            print ('Usage:')
            print ('python filter.py -c <config>')
            print ('-------------------------------------')
            print ('Options:')
            print ('-c (required) : configuration data path')
            print ('-j            : define jobtype i.e. realtime or archive')
            print ('-e            : endtime, default is now')
            print ('-d            : (int) dayrange, amount of days to analyze before endtime')
            print ('-p            : basepath - default is in config file')
            print ('-l            : loggername')
            print ('-------------------------------------')
            print ('Application:')
            print ('python3 filter.py -c ../conf/filter.cfg -j archive,second -d 3 -s LEMI025_28_0002_0001')
            sys.exit()
        elif opt in ("-c", "--config"):
            # delete any / at the end of the string
            configpath = os.path.abspath(arg)
        elif opt in ("-j", "--jobtype"):
            # define a jobtype (realtime,archive)
            joblist = arg.split(",")
            jobtype = joblist[0]
        elif opt in ("-d", "--dayrange"):
            # define a dayrange for archive jobs - default is 2
            dayrange = int(arg)
        elif opt in ("-e", "--endtime"):
            # define an endtime, default is now
            try:
                endtime = methods.testtime(arg)
            except:
                print (" Endtime could not be interpreted")
                endtime = datetime.now(timezone.utc).replace(tzinfo=None)
        elif opt in ("-p", "--path"):
            basepath = os.path.abspath(arg)
        elif opt in ("-l", "--loggername"):
            newloggername = arg
        elif opt in ("-x", "--sendlog"):
            sendlog = True
        elif opt in ("-D", "--debug"):
            print ("Debug activated ...")
            debug = True

    print ("Running filter.py version {} for {} job".format(version,jobtype))

    if not os.path.exists(configpath):
        print ('Specify a valid path to configuration information')
        print ('-- check filter.py -h for more options and requirements')
        sys.exit()

    if not jobtype == 'realtime':
        jobtype = "archive"

    if endtime:
        try:
            endtime = methods.testtime(endtime)
        except:
            print ("Endtime could not be interpreted - Aborting")
            sys.exit(1)


    print ("1. Read and check validity of configuration data")
    dd = read_conf(configpath)
    if not dd:
        print ("filter: empty configuration file - aborting")
        sys.exit(0)

    if debug:
        print ("Configuration:", dd)
    groupparameter = dd.get('groupparameter',{})
    permanent = dd.get('permanent',[])
    blacklist = dd.get('blacklist',[])
    basics = dd.get('basics',{})
    # By default the last 2 hours are filtered for realtime data
    try:
        recentthreshold=int(basics.get('recentthreshold',7200))
    except:
        recentthreshold=7200
    destination = basics.get('destination')
    basepath = basics.get('basepath', "/srv/archive")
    receiver  = basics.get('notification',"")
    notificationcfg  = basics.get('notificationcfg',"")
    logpath = basics.get('logpath',"/tmp/filterstatus.log")
    if newloggername:
        logpath = os.path.join(os.path.dirname(logpath),newloggername)
    outputformat = basics.get('outputformat')
    credentials = basics.get('credentials',"cobsdb")

    print ("2. Activate logging scheme as selected in config")
    #sn = 'ALDEBARAN' # servername  get name from machine ...
    sn = socket.gethostname()
    statusmsg = {}
    name = "{}-FILTER".format(sn)

    try:
        print ("Connecting to database")
        db = mm.connect_db(credentials)
        print ("... success")
        statusmsg[name] = 'DB on {} connected'.format(sn)
        # get existing Data IDs from data base
        sensorlist = db.select("DataID","DATAINFO")
    except:
        print ("... failed")
        statusmsg[name] = '{}: DB connection failed'.format(sn)

    statusmsg = apply_filter(db, statusmsg=statusmsg, groupdict=groupparameter, permanent=permanent, blacklist=blacklist, jobtype=jobtype, endtime=endtime, dayrange=dayrange, dbinputsensors=sensorlist, basepath=basepath, destination=destination, outputformat=outputformat, recentthreshold=recentthreshold, debug=debug)

    if not debug and sendlog:
        martaslog = ml(logfile=logpath,receiver=receiver)
        if receiver == 'telegram':
            martaslog.telegram['config'] = notificationcfg
        elif receiver == 'email':
            martaslog.email['config'] = notificationcfg
        martaslog.msg(statusmsg)
    elif debug:
        print ("Debug selected - statusmsg looks like:")
        print (statusmsg)

if __name__ == "__main__":
   main(sys.argv[1:])




"""
groupparameterdict   :   'LEMI' : {'station' : 'WIC', 'filtertype':'default', 'realtime' : True, 'window' : 40000},
                         'GSM90_14245_0002_0001' : {'filtertype':'gaussian', 'filterwidth':3.33333333, 'resample_period':1, 'realtime':True, 'window' : 10000},
                         'IWT_TILT01_0001_0003' : {'filtertype': 'default', 'realtime' : False, 'window' : 40000},
                         'BM35' : {'filtertype':'gaussian', 'filterwidth':3.33333333, 'resample_period':1, 'realtime':True, 'window' : 10000},
                         'G823A' : {'filtertype': 'default', 'realtime' : False, 'window' : 40000}}


# Realtime list is used for time slicing to avoid linearly filled gaps
realtime     :    LEMI025_22_0003_0001,LEMI036_1_0002_0001,LEMI036_3_0001_0001,GSM90_14245_0002_0001,BM35_029_0001_0001,BM35_033_0001_0001

blacklist    :    LEMI025_28_0002_0001,

scalardict   :    GP20S3NS_012201_0001_0001 : {'type' : 'GP20S3', 'components' : ['x','y','z']},
                  'GP20S3V_911005_0001_0001' :  {'type' : 'GP20S3', 'components' : ['x','y','z']},
                  'GP20S3EW_111201_0001_0001' :  {'type' : 'GP20S3', 'components' : ['x','y','z']}}
"""

