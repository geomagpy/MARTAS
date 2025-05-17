#!/usr/bin/env python
"""
Regularly archive data from a database
use crontab or scheduler to apply archive methods
"""

from magpy.database import *
from magpy.opt import cred as mpcred

try:
    from martas.core.martas import martaslog as ml
except:
    print ("Martas logging service not available")

import getopt


def main(argv):
    shortcut = ''
    path = ''
    depth = 2
    autofilter = 3
    flagging = False
    startdate = ''    
    archiveformat = 'PYCDF'
    flaglist = []
    skip = ''
    samplingrateratio=12 # 12 days * samplingperiod (sec) will be kept from today (e.g. 12 days of seconds data. 720 days of minute data.
    try:
        opts, args = getopt.getopt(argv,"hc:b:s:i:",["cred=","begin=","skip=","sr=",])
    except getopt.GetoptError:
        print ('deleteold.py -c <cred> -b <begin> -s <skip> -i <sr>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print ('-------------------------------------')
            print ('Description:')
            print ('-- deleteold.py gets data from a databank and deletes old data sets  --')
            print ('Old database entries exceding a defined age')
            print ('are deleted.')
            print ('The databank size is automatically restricted ')
            print ('in dependency of the sampling rate of the input data. Only the last ')
            print ('12 days of second data, the last 720 days of minute data and ')
            print ('approximately 118 years of hourly data are kept. To modify these default')
            print ('settings please contact the developers (or learn python and')
            print ('edit the code - its simple and the MagPy cookbook will help you).')
            print ('-------------------------------------')
            print ('Usage:')
            print ('deleteold.py -c <cred> -b <begin> -s <skip> -i <sr> ')
            print ('-------------------------------------')
            print ('Options:')
            print ('-c (required) : provide the shortcut to the data bank credentials as defined by addcred.py')
            print ('-b            : begin: not used so far')
            print ('-s            : list sensor IDs to skip (comma separated list)')
            print ('-i            : samplingrateratio for deleting old db entries - default is 12')
            print ('              : deleting data older than samplingrate(sec)*12 days.')
            print ('              : => i=12 : 1sec data older than 12 days is deleted in DB')
            print ('              :           1min data older than 720 days is deleted in DB')
            print ('              : => i=1  : 1sec data older than 1 day is deleted in DB')
            print ('              :           1min data older than 60 days is deleted in DB')
            print ('-------------------------------------')
            print ('Example:')
            print ('every day cron job: python deleteold.py -c cobsdb')
            print ('creating archive of old db entries: python archive.py -c cobsdb -p /media/Samsung/Observatory/data/ -d 30 -b "2012-06-01" -g -i 100 -a 3')
            sys.exit()
        elif opt in ("-c", "--cred"):
            cred = arg
        elif opt in ("-b", "--begin"):
            startdate = arg
        elif opt in ("-s", "--skip"):
            skip = arg
        elif opt in ("-i", "--samplingrateratio"):
            try:
                samplingrateratio = int(arg)
            except:
                print ("samplingrateratio needs to be an integer")
                sys.exit()

    if cred == '':
        print ('Specify a shortcut to the credential information by the -c option:')
        print ('-- check addcred.py -h for more options and requirements')
        sys.exit()

    print ("Accessing data bank ...")
    try:
        db = mysql.connect (host=mpcred.lc(cred,'host'),user=mpcred.lc(cred,'user'),passwd=mpcred.lc(cred,'passwd'),db =mpcred.lc(cred,'db'))
        print ("success")
    except:
        print ("failure - check your credentials / databank")
        sys.exit()

    # Getting dates
    datelist = []
    if startdate == '':
        current = datetime.utcnow() # make that a variable
    else:
        current = DataStream()._testtime(startdate)

    newcurrent = current
    for elem in range(depth):
        datelist.append(datetime.strftime(newcurrent,"%Y-%m-%d"))
        newcurrent = current-timedelta(days=elem+1)

    print ("Dealing with time range:", datelist)

    testdate = datetime.strftime((datetime.strptime(min(datelist),"%Y-%m-%d")-timedelta(days=1)),"%Y-%m-%d")

    # get a list with all datainfoids covering the selected time range
    if startdate:
        start = (datetime.strftime(DataStream()._testtime(startdate),"%Y-%m-%d")) 
        sql = 'SELECT DataID FROM DATAINFO WHERE DataMaxTime > "'+start+'"'
    else:
        sql = 'SELECT DataID FROM DATAINFO WHERE DataMaxTime > "1900-01-01"'
    print (sql)

    # skip BLV measurements from cleanup 
    sql = sql + ' AND SensorID NOT LIKE "BLV_%"'
    # skip Quakes from cleanup 
    sql = sql + ' AND SensorID NOT LIKE "QUAKES"'

    if len(skip) > 0:
        skipstr = ''
        skiplst = skip.split(',')
        for sensortoskip in skiplst:
            skipstr += ' AND SensorID != "'+sensortoskip+'"'
        sql = sql + skipstr
        print (sql)
 
    cursor = db.cursor ()
    try:
        cursor.execute(sql)
    except:
        print ("Error when reading database")
    datainfoidlist = [elem[0] for elem in cursor.fetchall()]

    print ("Cleaning database contens of:", datainfoidlist)

    for data in datainfoidlist:
        print (" ---------------------------- ")
        print (" ---------------------------- ")
        print ("Loading data files of", data)
        print (" ---------------------------- ")
        print (" ---------------------------- ")
        print ("Starting at: {}".format(datetime.utcnow()))
        # Test of dataid table exists
        try:
            getline = True
            amount = dbgetlines(db,data,10000)
        except:
            print ("Could not get lines from data file")
            getline = False

        if getline:
            sr = amount.samplingrate()
            delete = False
            if amount.length()[0] > 0:
                delete = True
                print (" ---------- Deleting old data for {}".format(data))
            else:
                print (" ---------- Doing nothing for table {}".format(data))
                #sql = 'DELETE FROM DATAINFO WHERE DataID = "{}"'.format(data)
                #print (sql)
                #cursor = db.cursor()
                #cursor.execute(sql)
                #db.commit()
                #cursor.close()

        if not isnan(sr) and delete and getline:
            print ("Now deleting old entries in database older than %s days" % str(int(sr*samplingrateratio)))
            dbdelete(db,data,samplingrateratio=samplingrateratio)
            print (" -> ... success")

if __name__ == "__main__":
   main(sys.argv[1:])



