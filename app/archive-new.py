#!/usr/bin/env python
"""
Regularly archive data from a database
use crontab or scheduler to apply archive methods
"""

from magpy.stream import *
from magpy.database import *
from magpy.opt import cred as mpcred


# Relative import of core methods as long as martas is not configured as package
scriptpath = os.path.dirname(os.path.realpath(__file__))
coredir = os.path.abspath(os.path.join(scriptpath, '..', 'core'))
sys.path.insert(0, coredir)
from martas import martaslog as ml
from acquisitionsupport import GetConf2 as GetConf2

import getopt
import pwd
import socket


"""
#configuration:

cred            :      cobsdb

path            :      /srv/archive

# By default all sensors in path will be used with default criteria
defaultdepth    :      2

archiveformat   :      PYCDF

writearchive    :      True

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

def connectDB(cred, exitonfailure=True, report=True):

    if report:
        print ("  Accessing data bank... ")
    try:
        db = mysql.connect (host=mpcred.lc(cred,'host'),user=mpcred.lc(cred,'user'),passwd=mpcred.lc(cred,'passwd'),db =mpcred.lc(cred,'db'))
        if report:
            print ("   -> success. Connected to {}".format(mpcred.lc(cred,'db')))
    except:
        if report:
            print ("   -> failure - check your credentials / databank")
        if exitonfailure:
            sys.exit()

    return db


def createDatelist(startdate='', depth=2, debug=False):

    if debug:
         print ("   Creating datelist...")
    # Getting dates
    datelist = []
    newdatetuple = []
    if startdate == '':
        current = datetime.utcnow()
    else:
        current = DataStream()._testtime(startdate)

    newcurrent = current
    for elem in range(depth):
        datelist.append(datetime.strftime(newcurrent,"%Y-%m-%d"))
        datetuple = (datetime.strftime((current-timedelta(days=elem+1)),"%Y-%m-%d"), datetime.strftime(newcurrent,"%Y-%m-%d"))
        newcurrent = current-timedelta(days=elem+1)
        newdatetuple.append(datetuple)
    if debug:
         print ("   -> ", newdatetuple)

    return newdatetuple


def createDataSelectionList(blacklist=[], debug=False):

    if debug:
         print ("   Creating sql query...")
    # get a list with all datainfoids covering the selected time range
    sql = 'SELECT DataID,DataMinTime,DataMaxTime FROM DATAINFO'

    if len(blacklist) > 0:
        sql = "{} WHERE".format(sql)
        addstr = ''
        for el in blacklist:
            addstr += " AND DataID NOT LIKE '{}%'".format(el)
        addstr = addstr.replace(" AND","",1)
    sql = "{}{}".format(sql,addstr)

    if debug:
         print ("   -> query looks like: {}".format(sql))
    return sql


def gettingDataDictionary(db,sql,debug=False):

    if debug:
         print ("   Obtaining DataID dict with times...")

    resultdict = {}
    # looks like {'data_1_0001_0001' : {'mintime':xxx, 'maxtime' : xxx }, ...}

    cursor = db.cursor()
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

def getparameter(plist):
    try:
        depth = int(plist[0])
    except:
        print ("  Depth needs to be an integer")
        sys.exit()
    fo = plist[1]
    wa = testbool(plist[2])
    af = testbool(plist[3])
    cdb = testbool(plist[4])
    try:
        ratio = int(plist[5])
    except:
        print ("  Ratio needs to be an integer")
        sys.exit()
    return depth,fo,wa,af,cdb,ratio


def testbool(string):
    if string in ['True','true','TRUE','Yes','yes','ja','Ja']:
        return True
    else:
        return False


def validtimerange(timetuple, mintime, maxtime, debug=False):
    #timetuple to 1d list unique list
    mintuptime = DataStream()._testtime(min(min(timetuple)))
    maxtuptime = DataStream()._testtime(max(max(timetuple)))
    mintime = DataStream()._testtime(mintime)
    maxtime = DataStream()._testtime(maxtime)
    if mintuptime < maxtime and maxtuptime > mintime:
        if debug:
            print ("  Found valid time range")
        return True
    if debug:
        print ("  Found invalid time range")
    return False

def main(argv):
    version = "1.0.0"
    conf = ''
    path = ''
    obsdepth = 0
    obssenslist = []
    startdate = ''
    statusmsg = {}
    hostname = socket.gethostname().upper()
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
            config = GetConf2(conf)
            print ("   -> configuration data extracted")
        else:
            print ('Specify a valid path to a configuration file using the  -c option:')
            print ('-- check archive.py -h for more options and requirements')
            sys.exit()

    ## Logger configuration data
    logpath = config.get('logpath')
    receiver = config.get('notification')
    receiverconf = config.get('notificationconf')


    db = connectDB(config.get('credentials'))

    sql = createDataSelectionList(blacklist=config.get('blacklist',[]), debug=debug)

    datainfoiddict = gettingDataDictionary(db,sql,debug=False)

    for data in datainfoiddict:
        print (" ---------------------------- ")
        print (" Checking data set {}".format(data))
        name = "{}-archiving-{}".format(hostname,data.replace("_","-"))
        msg = "checking"
        if debug:
            print ("  Times: {}".format(datainfoiddict.get(data)))

        if obssenslist and not data in obssenslist:
            print ("  Not in observers specified dataid list - this DataID will be skipped")
            continue

        if not db: # check whether db is still connected
            print ("    Lost DB - reconnecting ...")
            db = connectDB(config.get('credentials'), exitonfailure=False, report=False)

        para = [config.get('defaultdepth'), config.get('archiveformat'),config.get('writearchive'),config.get('applyflags'), config.get('cleandb'),config.get('cleanratio')]
        # Get default parameter from config
        depth,fo,wa,af,cdb,ratio = getparameter(para)

        # Modify parameters if DataID specifications are give
        for sensd in config.get('sensordict',{}): 
            if data.find(sensd) >= 0:
                print ("  Found data specific parameters for sensorgroup {}:".format(sensd)) 
                para = config.get('sensordict').get(data)
                depth,fo,wa,af,cdb,ratio = getparameter(para)
                print ("   -> {}".format(para))

        # Manual specifications
        if obsdepth:
            print ("  Overriding configuration file data with manual specifications - new depth = {}".format(obsdepth)) 
            depth = obsdepth

        # Create datelist (needs to be sorted)
        dateslist = createDatelist(startdate=startdate, depth=depth, debug=debug)

        # check time range
        if not validtimerange(dateslist, datainfoiddict.get(data).get('mintime'), datainfoiddict.get(data).get('maxtime')):
            print ("  Apparently no data is existing for the seleceted days - skipping")
            continue

        # run the following in a daily manner? to save memory... check
        for tup in dateslist:
            stream = DataStream()
            #tup = (day,nextday)
            stream = readDB(db,data,starttime=tup[0],endtime=tup[1])

            # Data found
            if stream.length()[0] > 0:
                if not num2date(max(stream.ndarray[0])).replace(tzinfo=None) < datetime.utcnow().replace(tzinfo=None):
                    print ("  Found in-appropriate date in stream - maxdate = {} - cutting off".format(num2date(max(stream.ndarray[0]))))
                    stream = stream.trim(endtime=datetime.utcnow())
                print ("  Archiving {} data from {} to {}".format(data,tup[0],tup[1]))
                sr = stream.samplingrate()
                print ("   with sampling period {} sec".format(sr))
                if isnan(sr):
                    print ("Please take care - could not extract sampling rate - will assume 60 seconds")
                    sr = 60

                path = config.get('path')

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
                    print ("Please note: flags are by default not contained in the cdf archive. They are stored separately in the database.")
                    flaglist = db2flaglist(db,sensorid=stream.header['SensorID'],begin=tup[0],end=tup[1])
                    if len(flaglist) > 0:
                        print ("  Found {} flags in database for the selected time range - adding them to the archive file".format(len(flaglist)))
                        stream = stream.flag(flaglist)

                if not debug and wf and archivepath and af:
                    stream.write(archivepath,filenamebegins=datainfoid+'_',format_type=fo)
                else:
                    print ("   Debug: skip writing")

                if not debug and cdb:
                    print ("Now deleting old entries in database older than {} days".format(sr*ratio))
                    dbdelete(db,stream.header['DataID'],samplingrateratio=ratio)
                else:
                    print ("   Debug: skip deleting DB")
                msg = "successfully finished"

        statusmsg[name] = msg

    if debug:
        print (statusmsg)
    else:
        martaslog = ml(logfile=logpath,receiver=receiver)
        martaslog.telegram['config'] = receiverconf
        martaslog.msg(statusmsg)

    print ("----------------------------------------------------------------")
    print ("archiving app finished")
    print ("----------------------------------------------------------------")
    print ("SUCCESS")

if __name__ == "__main__":
   main(sys.argv[1:])



