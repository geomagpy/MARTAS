#!/usr/bin/env python
"""
Regularly archive data from a database
use crontab or scheduler to apply archive methods
"""

from magpy.stream import *
from magpy.core import database
from magpy.core import methods as magpymeth

from magpy.opt import cred as mpcred


# Relative import of core methods as long as martas is not configured as package
from martas.core.methods import martaslog as ml
from martas.core import methods as mm
from martas.version import __version__


import getopt
from datetime import datetime, timezone
import pwd
import socket


"""
#configuration:

dbcredentials     :      cobsdb

archivepath            :      /srv/archive

# By default all sensors in path will be used with default criteria
defaultdepth    :      2

archiveformat   :      PYCDF

writearchive    :      True
subdirectory    :      Y

applyflags      :      False

cleandb         :      True

# cleanratio = samplingrateratio for deleting old db entries - default is 12')
#                   deleting data older than samplingrate(sec)*12 days.')
#                    cleanratio=12 : 1sec data older than 12 days is deleted in DB')
#                                  :           1min data older than 720 days is deleted in DB')
#                    cleanratio=1  : 1sec data older than 1 day is deleted in DB')
#                                  :           1min data older than 60 days is deleted in DB
cleanratio      :      12


# Modify criteria for specific sensors
sensordict      :    Sensor1:depth,format,writeDB,writeArchive,applyFlags,cleanratio;


# Sensors present in path to be skipped (Begging of Sensorname is enough
blacklist       :    BLV,QUAKES,Sensor2,Sensor3,



DESCRIPTION:
    archive.py gets data from a databank
    to any accessible repository (e.g. disk).
    Old database entries exceding a defined age
    are deleted. Optionally archive files can be stored in a user defined format.
    The databank size is automatically restricted
    in dependency of the sampling rate of the input data. A cleanratio of 12 
    will only keep the last
    12 days of second data, the last 720 days of minute data and
    approximately 118 years of hourly data are kept.
    Settings are given in a configuration file.
    IMPORTANT: take care about depth - needs to be large enough to find data

    For reading raw data and creating archive file please use something else 

APPLICATION:
    # Auomatic
    python3 archive.py -c config.cfg

    # Manual for specific sensors and time range
    python3 archive.py -c /config.cfg -b 2020-11-22 -s Sensor1,Sensor2 -d 30

"""


def create_datelist(startdate='', depth=2, debug=False):

    if debug:
         print ("   Creating datelist...")
    # Getting dates
    datelist = []
    newdatetuple = []
    if startdate == '':
        current = datetime.now(timezone.utc).replace(tzinfo=None)
    else:
        current = magpymeth.testtime(startdate)

    newcurrent = current
    for elem in range(depth):
        datelist.append(newcurrent.strftime("%Y-%m-%d"))
        td = current-timedelta(days=elem+1)
        datetuple = (td.strftime("%Y-%m-%d"), newcurrent.strftime("%Y-%m-%d"))
        newcurrent = current-timedelta(days=elem+1)
        newdatetuple.append(datetuple)
    if debug:
         print ("   -> ", newdatetuple)

    return newdatetuple


def create_data_selectionlist(blacklist=None, debug=False):
    if not blacklist:
        blacklist = []
    addstr = ""
    if debug:
         print ("   Creating sql query...")
    # get a list with all datainfoids covering the selected time range
    sql = 'SELECT DataID,DataMinTime,DataMaxTime FROM DATAINFO'

    if len(blacklist) > 0:
        sql = "{} WHERE".format(sql)
        for el in blacklist:
            addstr += " AND DataID NOT LIKE '{}%'".format(el)
        addstr = addstr.replace(" AND","",1)
    sql = "{}{}".format(sql,addstr)

    if debug:
         print ("   -> query looks like: {}".format(sql))
    return sql


def get_data_dictionary(db,sql,debug=False):

    if debug:
         print ("   Obtaining DataID dict with times...")

    resultdict = {}
    # looks like {'data_1_0001_0001' : {'mintime':xxx, 'maxtime' : xxx }, ...}

    cursor = db.db.cursor()
    try:
        cursor.execute(sql)
    except:
        print ("   Error when sending sql query")
    result =  cursor.fetchall()
    for el in result:
        # check whether a data table with this name is existing
        verifytable = "SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = '{}'".format(el[0])
        cursor.execute(verifytable)
        test =  cursor.fetchall()
        if test:
            resultdict[el[0]] = {'mintime': el[1], 'maxtime': el[2]}
    cursor.close()
    if debug:
        print ("   -> Obtained the following DataIDs:", resultdict)

    return resultdict

def get_parameter(plist, debug=False):
    if debug:
        print ("Found the following parameters: {}".format(plist))
    try:
        depth = int(plist[0])
    except:
        print ("  Depth needs to be an integer")
        sys.exit()
    fo = plist[1]
    wa = mm.get_bool(plist[2])
    af = mm.get_bool(plist[3])
    cdb = mm.get_bool(plist[4])
    try:
        ratio = int(plist[5])
    except:
        print ("  Ratio needs to be an integer")
        sys.exit()
    return depth,fo,wa,af,cdb,ratio


def validtimerange(timetuple, mintime, maxtime, debug=False):
    #timetuple to 1d list unique list
    mintuptime = magpymeth.testtime(min(min(timetuple)))
    maxtuptime = magpymeth.testtime(max(max(timetuple)))
    mintime = magpymeth.testtime(mintime)
    maxtime = magpymeth.testtime(maxtime)
    if mintuptime < maxtime and maxtuptime > mintime:
        if debug:
            print ("  Found valid time range")
        return True
    if debug:
        print ("  Found invalid time range")
    return False

def main(argv):
    version = __version__
    conf = ''
    path = ''
    obsdepth = 0
    obssenslist = []
    startdate = ''
    statusmsg = {}
    proxies = {}
    hostname = socket.gethostname().upper()
    debug=False
    try:
        opts, args = getopt.getopt(argv,"hc:b:d:s:gi:a:D",["config=","begin=","depth=","sensors=","debug=",])
    except getopt.GetoptError:
        print ('archive.py -c <config> -b <begin> -d <depth> -s <sensors>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print ('-------------------------------------')
            print ('Description:')
            print ('-- archive.py gets data from a databank and archives  --')
            print ('-- to any accessible repository (e.g. disk)           --')
            print ('Old database entries exceding a defined age')
            print ('are deleted. Optionally archive files can be stored in a user defined format.')
            print ('The databank size is automatically restricted ')
            print ('in dependency of the sampling rate of the input data. Only the last ')
            print ('12 days of second data, the last 720 days of minute data and ')
            print ('approximately 118 years of hourly data are kept. To modify these default')
            print ('settings please contact the developers (or learn python and')
            print ('edit the code - its simple and the MagPy cookbook will help you).')
            print ('IMPORTANT: data bank entries are solely identified from DATAINFO table.')
            print ('           make sure that your data tables are contained there')
            print ('IMPORTANT: take care about depth - needs to be large enough to find data')
            print ('-------------------------------------')
            print ('Usage:')
            print ('archive.py -c <config> -p <archivepath> -b <begin> -d <depth> -s <sensors>')
            print ('-------------------------------------')
            print ('Options:')
            print ('-c (required) : provide a path to a configuartion file')
            print ('-p            : archivepath like "/home/max/myarchive"')
            print ('              : please note: an asterix requires quotes')
            print ('-d            : depth')
            print ('-b            : begin: end = begin - depth(days)')
            print ('-s            : list sensor to deal with')
            print ('-------------------------------------')
            print ('Example:')
            print ('every day cron job: python archive.py -c cobsdb -p /srv/archive')
            print ('creating archive of old db entries: python archive.py -c cobsdb -p /media/Samsung/Observatory/data/ -d 30 -b "2012-06-01" -g -i 100 -a 3')
            sys.exit()
        elif opt in ("-c", "--config"):
            conf = os.path.abspath(arg)
        elif opt in ("-b", "--begin"):
            startdate = arg
        elif opt in ("-d", "--depth"):
            try:
                obsdepth = int(arg)
                if not obsdepth >= 2:
                    print ("depth needs to be positve and larger or equal than 2")
                    sys.exit()
            except:
                print ("depth needs to be an integer")
                sys.exit()
        elif opt in ("-s", "--sensors"):
            obssenslist = arg.split(",")
        elif opt == "-v":
            print ("archive.py version: {}".format(version))
        elif opt in ("-D", "--debug"):
            debug = True

    print ("Running archive.py")
    print ("-------------------------------")

    if conf == '':
        print ('Specify a path to a configuration file using the  -c option:')
        print ('-- check archive.py -h for more options and requirements')
        sys.exit()
    else:
        if os.path.isfile(conf):
            print ("  Read file with GetConf")
            config = mm.get_conf(conf)
            print ("   -> configuration data extracted")
        else:
            print ('Specify a valid path to a configuration file using the  -c option:')
            print ('-- check archive.py -h for more options and requirements')
            sys.exit()

    ## Logger configuration data
    logpath = config.get('logpath')
    receiver = config.get('notification')
    receiverconf = config.get('notificationconf')
    subdirectory = config.get('subdirectory',None)

    db = mm.connect_db(config.get('dbcredentials'))

    sql = create_data_selectionlist(blacklist=config.get('blacklist',[]), debug=debug)

    datainfoiddict = get_data_dictionary(db,sql,debug=False)

    for data in datainfoiddict:
        sr = 1
        datainfoid = ''
        print (" ---------------------------- ")
        print (" Checking data set {}".format(data))
        name = "{}-archiving-{}".format(hostname,data.replace("_","-"))
        msg = "checking"
        if debug:
            print ("  Times: {}".format(datainfoiddict.get(data)))
        # TODO create a warning if mintime is much younger as it should be after cleaning

        if obssenslist and not data in obssenslist:
            print ("  Not in observers specified dataid list - this DataID will be skipped")
            continue

        if not db: # check whether db is still connected
            print ("    Lost DB - reconnecting ...")
            db = mm.connect_db(config.get('dbcredentials'), exitonfailure=False, report=False)

        para = [config.get('defaultdepth'), config.get('archiveformat'),config.get('writearchive'),config.get('applyflags'), config.get('cleandb'),config.get('cleanratio')]
        # Get default parameter from config
        depth,fo,wa,af,cdb,ratio = get_parameter(para)
        writemode = config.get('writemode','replace')

        # Modify parameters if DataID specifications are give
        for sensd in config.get('sensordict',{}):
            if data.find(sensd) >= 0:
                print ("  Found data specific parameters for sensorgroup {}:".format(sensd)) 
                para = config.get('sensordict').get(sensd)
                depth,fo,wa,af,cdb,ratio = get_parameter(para)
                print ("   -> {}".format(para))

        # Manual specifications
        if obsdepth:
            print ("  Overriding configuration file data with manual specifications - new depth = {}".format(obsdepth)) 
            depth = obsdepth

        # Create datelist (needs to be sorted)
        dateslist = create_datelist(startdate=startdate, depth=depth, debug=debug)

        # check time range
        try:
            # This method might fail if datainfodict does not contain dates - in this case just proceed with normal analysis
            gettrstate = validtimerange(dateslist, datainfoiddict.get(data).get('mintime'), datainfoiddict.get(data).get('maxtime'))
        except:
            print ("   -> Could not extract time ranges from datainfo dictionary")
            gettrstate = True

        if not gettrstate:
            print ("  Apparently no data is existing for the seleceted days - skipping")
            continue

        # run the following in a daily manner? to save memory... check
        for tup in dateslist:
            if debug:
                print ("  Running for range", tup)
            stream = DataStream()
            #tup = (day,nextday)
            if debug:
                print ("  Reading data from DB ...")
            stream = db.read(data,starttime=tup[0],endtime=tup[1])
            if debug:
                print ("    -> Done ({} data points)".format(stream.length()[0]))

            # Data found
            if stream.length()[0] > 0:
                dataidnum = stream.header.get('DataID')
                if not max(stream.ndarray[0]).replace(tzinfo=None) < datetime.now(timezone.utc).replace(tzinfo=None):
                    print ("  Found in-appropriate date in stream - maxdate = {} - cutting off".format(max(stream.ndarray[0])))
                    stream = stream.trim(endtime=datetime.now(timezone.utc).replace(tzinfo=None))
                print ("  Archiving {} data from {} to {}".format(data,tup[0],tup[1]))
                sr = stream.samplingrate()
                print ("   with sampling period {} sec".format(sr))
                if isnan(sr):
                    print ("Please take care - could not extract sampling rate - will assume 60 seconds")
                    sr = 60

                path = config.get('archivepath')
                archivepath = None

                if path:
                    #construct archive path
                    try:
                        sensorid = stream.header['SensorID']
                        stationid = stream.header['StationID']
                        datainfoid = stream.header['DataID']
                        archivepath = os.path.join(path,stationid,sensorid,stream.header['DataID'])
                    except:
                        print ("  Obviously a problem with insufficient header information")
                        print ("  - check StationID, SensorID and DataID in DB")
                        archivepath = None

                if af and sr > 0.9:
                    print ("You selected to apply flags and save them along with the cdf archive.")
                    flaglist = db.flags_from_db(sensorid=stream.header['SensorID'],begin=tup[0],end=tup[1])
                    if len(flaglist) > 0:
                        print ("  Found {} flags in database for the selected time range - adding them to the archive file".format(len(flaglist)))
                        stream = stream.flag(flaglist)

                if not debug and wa and archivepath:
                    stream.write(archivepath,filenamebegins=datainfoid+'_',format_type=fo,mode=writemode,subdirectory=subdirectory)
                else:
                    print ("   Debug: skip writing")
                    print ("    -> without debug a file with {} inputs would be written to {}".format(stream.length()[0],archivepath))
            else:
                print ("No data between {} and {}".format(tup[0],tup[1]))
            msg = "successfully finished"

        if not debug and cdb and not datainfoid == '':
                    print ("Now deleting old entries in database older than {} days".format(sr*ratio))
                    # TODO get coverage before
                    db.delete(datainfoid,samplingrateratio=ratio)
                    # TODO get coverage after
        else:
                    print ("   Debug: skip deleting DB")
                    print ("    -> without debug all entries older than {} days would be deleted".format(sr*ratio))

        statusmsg[name] = msg

    if debug or obssenslist:   #No update of statusmessages if only a selected sensor list is analyzed
        print (statusmsg)
    else:
        if config.get('https'):
            proxies['https'] = config.get('https')
        if config.get('http'):
            proxies['http'] = config.get('http')
        martaslog = ml(logfile=logpath,receiver=receiver,proxies=proxies)
        martaslog.telegram['config'] = receiverconf
        martaslog.msg(statusmsg)

    print ("----------------------------------------------------------------")
    print ("archiving app finished")
    print ("----------------------------------------------------------------")
    print ("SUCCESS")

if __name__ == "__main__":
   main(sys.argv[1:])



