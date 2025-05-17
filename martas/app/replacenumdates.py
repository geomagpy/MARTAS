#!/usr/bin/env python
"""

Replace datetimes

"""

from __future__ import print_function

from magpy.stream import *
from magpy.absolutes import *
from magpy.database import *
from magpy.opt import cred as mpcred
import getopt


def MatplotlibVersion():
    from pkg_resources import parse_version
    vers = matplotlib.__version__
    print ("Matplotlib version :", vers)
    if parse_version(vers) < parse_version("3.3.0"):
        return False
    return True

def ConnectDB(creddb):
    print("  Accessing data bank ...")
    try:
        db = mysql.connect (host=mpcred.lc(creddb,'host'),user=mpcred.lc(creddb,'user'),passwd=mpcred.lc(creddb,'passwd'),db =mpcred.lc(creddb,'db'))
        print("  ... success")
        return (db)
    except:
        print("  ... failure - check your credentials")
        sys.exit()


def GetAllDeltaString(db):
    val= dbselect(db,'DataDeltaValues','DATAINFO')
    return val


def CreateDBUpdateCall(deltalist, tablename='DATAINFO'):
    updatelist = []
    for el in deltalist:
        if el:
            if el.find("st_") >= 0 or el.find("et_") >= 0:
                #print ("Before", el)
                newel = ReplaceNumDates(el)
                #print ("After", newel)
                updatestr = "UPDATE {} SET DataDeltaValues='{}' WHERE DataDeltaValues='{}'".format(tablename,newel,el)
                updatelist.append(updatestr)
    return list(set(updatelist))


def UpdateDB(db, updatelist):
    if not isinstance(updatelist, list):
        return False
    if not len(updatelist) > 0:
        print ("No data to update")
        return False
    cursor = db.cursor()
    for updatesql in updatelist:
        try:
            cursor.execute(updatesql)
        except mysql.IntegrityError as message:
            return message
        except mysql.Error as message:
            return message
        except:
            return 'dbupdate: unkown error'
    db.commit()
    cursor.close()
    return True


def ReplaceNumDates(str,debug=False):
    ordinal = date2num(np.datetime64('0000-12-31'))
    if debug:
        print (ordinal)
    for el in ['st_','et_']:
        pos=0
        pos2=0
        while pos >= 0:
            if debug:
                print ("Component", el, pos, pos2)
            pos = str.find(el,pos2)
            pos2 = str.find(',',pos)
            pos3 = str.find(';',pos)
            if pos3 > 0 and pos3 < pos2:
                pos2 = pos3
            if debug:
                print (pos,pos2)
            if not pos2 >= 0:
                pos2 = len(str)
            if pos >= 0:
                part = str[pos:pos2]
                partar = part.split('_')
                oldtime = float(partar[1])
                if oldtime > 700000: # if not already replaced by new time - please take care: year 3886 problem coming up
                    newtime = oldtime+ordinal
                    newpart = "{}_{:.1f}".format(partar[0],newtime)
                    str = str.replace(part,newpart)
                pos=pos2

    return str


def main(argv):
    creddb = ''				# c
    debug=False
    teststring = "st_719853.0,x_4274.0,y_-1480.0,z_2192.0,time_timedelta(seconds=-3.0),et_736695.0;st_736695.0,x_4274.0,y_-1571.0,z_2192.0,time_timedelta(seconds=-3.0), et_736951.5;st_736951.5,x_4274.0,y_-1571.0,z_2192.0,time_timedelta(seconds=1.50),et_737060.0;st_737060.0,x_4274.0,y_-1631.0,z_2192.0,time_timedelta(seconds=-0.30)"

    try:
        opts, args = getopt.getopt(argv,"hc:D",["cred=","debug="])
    except getopt.GetoptError:
        print('replacedatetimes.py -c <creddb>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('-------------------------------------')
            print('Description:')
            print('replacenumdates.py finds numerical time and replaces with new (matplotlib >=3.3')
            print('')
            print('-------------------------------------')
            print('Usage:')
            print('replacenumdates.py -c <creddb>')
            print('-------------------------------------')
            print('Options:')
            print('-c            : provide the shortcut to the data bank credentials')
            print('-------------------------------------')
            print('Examples:')
            print('python replacenumdates.py -c wic')
            sys.exit()
        elif opt in ("-c", "--creddb"):
            creddb = arg
        elif opt in ("-D", "--debug"):
           debug=True

    if MatplotlibVersion():
        print ("Conversion necessary ...")
        print ("Starting ...")
        if debug:
            test = ReplaceNumDates(teststring,debug=debug)
            print (test)
        db = ConnectDB(creddb)
        deltalist = GetAllDeltaString(db)
        updatelist = CreateDBUpdateCall(deltalist)
        if not debug:
            val = UpdateDB(db, updatelist)
            if val:
                print ("SUCCESS")
        else:
            print (updatelist)

    else:
        print ("Old matplotlib version ...  everything fine")

if __name__ == "__main__":
   main(sys.argv[1:])

