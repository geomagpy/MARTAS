#!/usr/bin/env python
"""
DESCRIPTION
    Checking a MagPy database structure for tables which are not contained in DATAINFO and SENSORS.
    The background/necessity of this method is related to archive.py and deleteold.py, which make
    use of the DATAINFO table for selecting data tables to be archived AND cleaned. Therefore, tables
    not listed in DATAINFO are growing endless until the memory is full.
    
METHOD
    Selects all tables which end with with typical revision numbers (i.e 0001) and check for their
    existance in DATAINFO and SENSORS. 

GROUP
   MARTAS app 

REQUIREMENTS:
   MagPy >= 1.0.0
   Database credentials stored with addcred
"""
from __future__ import print_function

# Define packges to be used (local refers to test environment) 
# ------------------------------------------------------------

from magpy.stream import *
from magpy.database import *
import magpy.opt.cred as mpcred

import getopt
import pwd
import sys
import socket


def add_datainfo(db, tableonly=[], verbose=False, debug=False):

    if debug:
        print (" Adding tableonly to DATAINFO...")
    
    if not len(tableonly) > 0:
        return False
    # get a list with all datainfoids covering the selected time range
    cursor = db.cursor()

    for tab in tableonly:
        sql = 'INSERT INTO DATAINFO (DataID) VALUES ("{}")'.format(tab)
        if not debug:
            try:
                cursor.execute(sql)
            except:
                print ("   Error when sending sql query")
        else:
            print (" if not debug I would execute: {}".format(sql))
    cursor.close()
    return True


def obtain_datainfo(db, blacklist=[], verbose=False, debug=False):

    resultdict = {}
    addstr = ''
    # looks like {'data_1_0001_0001' : {'mintime':xxx, 'maxtime' : xxx }, ...}

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

    cursor = db.cursor()
    try:
        cursor.execute(sql)
    except:
        print ("   Error when sending sql query")
    datainfolist =  cursor.fetchall()
    for el in datainfolist:
        # check whether a data table with this name is existing
        verifytable = "SELECT * FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = '{}'".format(el[0])
        cursor.execute(verifytable)
        test =  cursor.fetchall()
        if test:
            resultdict[el[0]] = {'exists':'BOTH', 'mintime': el[1], 'maxtime': el[2]}
        else:
            resultdict[el[0]] = {'exists':'DATAINFO', 'mintime': el[1], 'maxtime': el[2]}
    cursor.close()
    if debug:
        print ("   -> Obtained the following DataIDs:", resultdict)

    return resultdict


def match(first, second):
    """
    DESCRIPTION
        search string with wildcards in other string
        corrected  in len(first) >= 1
    REFERENCE
        https://www.geeksforgeeks.org/wildcard-character-matching/
    """
 
    # If we reach at the end of both strings, we are done
    if len(first) == 0 and len(second) == 0:
        return True
 
    # Make sure that the characters after '*' are present
    # in second string. This function assumes that the first
    # string will not contain two consecutive '*'
    if len(first) > 1 and first[0] == '*' and  len(second) == 0:
        return False
 
    # If the first string contains '?', or current characters
    # of both strings match
    if (len(first) >= 1 and first[0] == '?') or (len(first) != 0
        and len(second) !=0 and first[0] == second[0]):
        return match(first[1:],second[1:]);
 
    # If there is *, then there are two possibilities
    # a) We consider current character of second string
    # b) We ignore current character of second string.
    if len(first) !=0 and first[0] == '*':
        return match(first[1:],second) or match(first,second[1:])
 
    return False
 

def get_tables(db,identifier="*_00??",verbose=False,debug=False):
    """
    DESCRIPTION
        get all tables which end with the identifier
    RETURN
        list with table names
        (asume table name == DataID, and table name-identifier = SensorId)        
    """
    if verbose or debug:
        print (" Getting all tables ...")
    cursor = db.cursor()

    if debug:
        print (" - Current database information:")
        dbinfo(db,destination='stdout',level='full')

    tablessql = 'SHOW TABLES'
    try:
        cursor.execute(tablessql)
    except mysql.IntegrityError as message:
        if debug:
            print (message)
    except mysql.Error as message:
        if debug:
            print (message)
    except:
        if debug:
            print (' checkdatainfo - get_tables: unkown error')

    tables = cursor.fetchall()
    cursor.close()
    tables = [el[0] for el in tables]

    if debug:
        print (" Found: {}".format(tables))

    if not len(tables) > 0:
        print (' checkdatainfo.py: no tables found in specified database - aborting')
        sys.exit()

        
    # Match tables with identifier
    idtabs = [el for el in tables if match(identifier, el)]
    if debug:
        print (" Found after matching with ID {}: {}".format(identifier, idtabs))

    return idtabs


def matchtest(identifier,string):
    if match(identifier,string):
        print ("Yes")
    else:
        print ("No") 

#matchtest('*_00?1','WIC_adjusted_0001_0001')
#matchtest('*_00*','WIC_adjusted_0001_0001')
#matchtest('*_00??','WIC_adjusted_0001_0001')
#matchtest('*_0001','WIC_adjusted_0001_0001')
#matchtest('*_02??','WIC_adjusted_0001_0001')


def connectDB(cred, exitonfailure=True, verbose=True):
    """
    DESCRIPTION
        connecting to a database using stored credential information
        same method is part of archive.py
    """

    if verbose:
        print ("  Accessing data bank... ")
    try:
        db = mysql.connect (host=mpcred.lc(cred,'host'),user=mpcred.lc(cred,'user'),passwd=mpcred.lc(cred,'passwd'),db =mpcred.lc(cred,'db'))
        if verbose:
            print ("   -> success. Connected to {}".format(mpcred.lc(cred,'db')))
    except:
        if verbose:
            print ("   -> failure - check your credentials / databank")
        if exitonfailure:
            sys.exit()

    return db


def main(argv):
    version = "1.0.0"
    cred = ''
    identifier = ''
    blacklist = []
    checkdatainfo = False
    checksensors = False
    add = False
    verbose = False
    hostname = socket.gethostname().upper()
    debug=False
    
    head = 'checkdatainfo.py -c <cred> -i <id> -d <datainfo> -s <sensors> -a <add>'
    try:
        opts, args = getopt.getopt(argv,"hc:i:dsaD",["credentials=","id=","datainfo=","sensors=","add=","debug=",])
    except getopt.GetoptError:
        print (head)
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print ('-------------------------------------')
            print ('Description:')
            print ('-- checkdatainfo.py checks for missing tables in DATAINFO  --')
            print ('-- and SENOSRS.           --')
            print ('-------------------------------------')
            print ('Usage:')
            print (head)
            print ('-------------------------------------')
            print ('Options:')
            print ('-c (required) : credentials for a database')
            print ('-i            : data table identifiers - end of table name i.e "00??" (? can be numbers from 0-9)')
            print ('-d            : check datainfo')
            print ('-s            : check sensors')
            print ('-a            : add missing data to DATAINFO ( if "-d") and SENSORS (if "-s")')
            print ('-------------------------------------')
            print ('Example:')
            sys.exit()
        elif opt in ("-c", "--credentials"):
            cred = arg
        elif opt in ("-i", "--id"):
            identifier = arg
        elif opt in ("-d", "--datainfo"):
            checkdatainfo = True
        elif opt in ("-s", "--sensors"):
            checksensors = True
        elif opt == "-a":
            add = True
        elif opt == "-v":
            verbose = True
        elif opt in ("-D", "--debug"):
            debug = True

    if verbose or debug:
        print ("Running checkdatainfo.py version {}".format(version))
        print ("-------------------------------")

    if not checkdatainfo and not checksensors:
        print ('Specify either -d and/or -s')
        print ('-- Check checkdatainfo.py -h for more options and requirements')
        sys.exit()

    if cred == '':
        print ('Specify database credentials using the  -c option:')
        print ('-- Database credentials are created by addcred.py')
        print ('-- Check checkdatainfo.py -h for more options and requirements')
        sys.exit()


    # 1. Connect to database
    db = connectDB(cred)

    # 2. Check tables
    tables = get_tables(db,identifier=identifier,verbose=verbose,debug=debug)

    # 3. Check for tables in DATAINFO
    datainfodict = obtain_datainfo(db, blacklist=blacklist, verbose=verbose, debug=debug)
    tableonly = [tab for tab in tables if not tab in datainfodict]
    for tab in tableonly:
        datainfodict[tab]  = {'exists':'TABLE'}
    if verbose or debug:
        for el in datainfodict:
            dd = datainfodict.get(el)
            if dd.get('exists') == 'BOTH':
                print ("Existing in BOTH:  {}".format(el) )
            elif dd.get('exists') == 'TABLE':
                print ("Existing only as TABLE:  {}".format(el) )
            elif dd.get('exists') == 'DATAINFO':
                print ("Existing only in DATAINFO:  {}".format(el) )
    if add:
        print ("Adding DATAINFO information")
        if debug:
            print ("Table only", tableonly) 
        #add_datainfo(db,tableonly=tableonly, verbose=verbose, debug=debug)
        print ("Better choice.. add the missing tables in xMagPy and export the header to the database")
        print (" routinely run this method (at least once per month and report tables")

    # 4. Check for tables in SENSORS


    if verbose or debug:
        print ("----------------------------------------------------------------")
        print ("checking datainfo app finished")
        print ("----------------------------------------------------------------")
        print ("SUCCESS")

if __name__ == "__main__":
   main(sys.argv[1:])



