#!/usr/bin/env python
"""
Regularly truncate contents of timesseries in a MagPy database
whereas "archive" also allows for truncating the database (based on DATAINO)
"db_truncate" removes contents from all tables of xxx_xxx_xxxx_xxxx structures
(independent of DATAINFO contents)
"""
from magpy.stream import *
from magpy.core import database
from magpy.opt import cred as mpcred

from martas.core.methods import martaslog as ml
from martas.core import methods as mm

from datetime import datetime, timezone
import getopt
import pwd
import socket


"""
#configuration:

credentials     :      cobsdb

# cleanratio = samplingrateratio for deleting old db entries - default is 12')
#                   deleting data older than samplingrate(sec)*12 days.')
#                    cleanratio=12 : 1sec data older than 12 days is deleted in DB')
#                                  :           1min data older than 720 days is deleted in DB')
#                    cleanratio=1  : 1sec data older than 1 day is deleted in DB')
#                                  :           1min data older than 60 days is deleted in DB
cleanratio      :      12

# Sensors present in path to be skipped (Begging of Sensorname is enough
blacklist       :    BLV,QUAKES,Sensor2,Sensor3,

# If sensorlist is provided only these sensors are considered
#sensorlist      :    Sensor1,Sensor4,



DESCRIPTION:
    db_truncate.py truncates contents of timesseries in a MagPy database.
    Whereas "archive" also allows for truncating the database (based on DATAINO)
    "db_truncate" removes contents from all tables of xxx_xxx_xxxx_xxxx structure.
    (independent of DATAINFO contents).
    The databank size is automatically restricted
    in dependency of the sampling rate of the input data. A cleanratio of 12
    will only keep the last
    12 days of second data, the last 720 days of minute data and
    approximately 118 years of hourly data are kept.
    Settings are given in a configuration file.

APPLICATION:
    # Automatic
    python3 db_truncate.py -c truncate.cfg

    # Manual for specific sensors and time range
    python3 db_truncate.py -c config.cfg -s Sensor1,Sensor2 -i 12

"""

def query_db(db, sql, debug=False):
    if not db:
        return []
    if debug:
         print ("   Sending sql query: {}".format(sql))
    cursor = db.db.cursor()
    message = db._executesql(cursor, sql)
    if message:
        print(message)
        return []
    return cursor.fetchall()

def get_table_tist(db, sensorlist=None, blacklist=None, debug=False):

    if not sensorlist:
        sensorlist=[]
    if not blacklist:
        blacklist=[]
    if debug:
         print ("   Creating sql query for selecting tables...")
    # get a list with all datainfoids covering the selected time range
    sql = 'SELECT table_name FROM information_schema.tables'
    fulllist = query_db(db,sql,debug=debug)
    if debug:
        print ("got fulllist", fulllist)
    table1list = [el[0] for el in fulllist]
    if debug:
        print ("got tables:", table1list)

    # only select tables with the correct schema
    table2list = [tab for tab in table1list if tab.count("_") == 3]
    if debug:
        print ("got tables:", table2list)

    # remove tables from blacklist
    blacklist.append("INNODB")
    blacklist.append("COLLATION")
    if len(blacklist) > 0:
        table3list = []
        for tab in table2list:
            add = True
            for bl in blacklist:
                if tab.find(bl) > -1:
                    add = False
            if add:
                table3list.append(tab)
    else:
        table3list = table2list

    # select only desired tables
    if len(sensorlist) > 0:
        table4list = []
        for tab in table3list:
            add = False
            for se in sensorlist:
                if tab.find(se) > -1:
                    add = True
            if add:
                table4list.append(tab)
    else:
        table4list = table3list

    if debug:
         print ("   -> tables to be treated: {}".format(table4list))
    return table4list


def main(argv):
    version = "1.0.0"
    conf = ''
    path = ''
    ratio = None
    sensorlist = []
    blacklist = []
    config={}
    sr = np.nan
    startdate = ''
    hostname = socket.gethostname().upper()
    debug=False
    try:
        opts, args = getopt.getopt(argv,"hc:i:s:b:vD",["config=","ratio=","sensorlist=","blacklist=","version=","debug=",])
    except getopt.GetoptError:
        print ('db_truncate.py -c <config> -i <ratio> -s <sensorlist> -b <blacklist> -v <version>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print ('-------------------------------------')
            print ('Description:')
            print ('-- db_truncate.py removes old data from a databank  --')
            print ('db_truncate.py truncates contents of time series in a MagPy database. ')
            print ('Whereas "archive" also allows for truncating the database (based on DATAINO) ')
            print ('"db_truncate" removes contents from all tables of xxx_xxx_xxxx_xxxx structure. ')
            print ('(independent of DATAINFO contents). ')
            print ('The databank size is automatically restricted ')
            print ('in dependency of the sampling rate of the input data. Only the last ')
            print ('12 days of second data, the last 720 days of minute data and ')
            print ('approximately 118 years of hourly data are kept.')
            print ('-------------------------------------')
            print ('Usage:')
            print ('db_truncate.py -c <config> -i <ratio> -s <sensorlist> -b <blacklist>')
            print ('-------------------------------------')
            print ('Options:')
            print ('-c (required) : provide a path to a configuration file')
            print ('-i            : ratio')
            print ('-b            : blacklist (tables to skip)')
            print ('-s            : sensorlist (use only these tables)')
            print (' given options will override config data')
            print ('-------------------------------------')
            print ('Example:')
            print ('python db_truncate.py -c config')
            sys.exit()
        elif opt in ("-c", "--config"):
            conf = os.path.abspath(arg)
        elif opt in ("-i", "--ratio"):
            ratio = int(arg)
        elif opt in ("-s", "--sensorlist"):
            sensorlist = arg.split(",")
        elif opt in ("-b", "--blacklist"):
            blacklist = arg.split(",")
        elif opt in ("-v", "--version"):
            print ("db_truncate.py version: {}".format(version))
        elif opt in ("-D", "--debug"):
            debug = True

    if debug:
        print ("Running db_truncate.py")
        print ("-------------------------------")

    if os.path.isfile(conf):
        print ("  Read configuration data:")
        config = mm.get_conf(conf)
        print ("   -> configuration data extracted")

    ## Logger configuration data
    logpath = config.get('logpath')
    receiver = config.get('notification')
    receiverconf = config.get('notificationconf')
    ## Analysis configuration data
    cratio = int(config.get('cleanratio',12))
    if not ratio:
        ratio = cratio
    csensorlist = config.get('sensorlist',[])
    if not sensorlist:
        sensorlist = csensorlist
    cblacklist = config.get('blacklist',[])
    if not blacklist:
        blacklist = cblacklist

    if debug:
        print ("Parameters:")
        print ("Ratio:", ratio)
        print ("Sensorlist:", sensorlist)
        print ("Blacklist:", blacklist)

    db = mm.connect_db(config.get('dbcredentials','cobsdb'))

    tables = get_table_tist(db, sensorlist=sensorlist, blacklist=blacklist, debug=debug)

    if debug:
        print ("Cleaning database contents of:", tables)

    for data in tables:
        sr = np.nan
        st = datetime.now(timezone.utc).replace(tzinfo=None)
        amount = DataStream()
        delete = False
        print (" ---------------------------- ")
        print ("Cleaning contents:", data)
        # Test of dataid table exists
        try:
            getline = True
            amount = db.get_lines(data,10000)
        except:
            print ("Could not get lines from data file")
            getline = False

        if getline:
            sr = amount.samplingrate()
            delete = False
            if amount.length()[0] > 0:
                delete = True
                print ("   Deleting old data for {}".format(data))
            else:
                print ("   Doing nothing for table {}".format(data))

        if not isnan(sr) and delete and getline:
            print ("  - Deleting entries in database older than {} days".format(int(sr*ratio)))
            if not debug:
                try:
                    db.delete(data,samplingrateratio=ratio)
                    et = datetime.now(timezone.utc).replace(tzinfo=None)
                    print (" -> ... success: needed {} minutes".format((et-st).total_seconds()/60.))
                except:
                    print (" -> ... failure")
            else:
                print (" DEBUG selected: will not delete anything")
        print (" ---------------------------- ")

if __name__ == "__main__":
   main(sys.argv[1:])
