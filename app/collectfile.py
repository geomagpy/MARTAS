#!/usr/bin/env python
"""
Get files from a remote server (to be reached by nfs, samba, ftp, html or local directory) 

file content is directly added to a data bank (or local file if preferred).
"""
from __future__ import print_function

from magpy.stream import *
from magpy.database import *
from magpy.opt import cred as mpcred

import getopt
import fnmatch
import pwd
import zipfile
import tempfile
from dateutil import parser
from shutil import copyfile
import subprocess

try:
    from core.martas import martaslog as ml
except:
    print ("Martas logging service not available")


'''
Changelog:
2014-08-02:   RL removed break when no data was found (could happen if at this selected day not data is available. All other days need to be collected however.
2014-10-22:   RL updated the description
2014-11-04:   RL added the inserttable option to force data upload to a specific table (e.g. for rcs conrad data which has a variable sampling rate)
2015-10-20:   RL changes for fast ndarrays and zip option
2016-10-10:   RL updated imports, improved help and checked for pure file access
2017-03-10:   RL activated force option
2018-10-22:   RL changed all routines considerably
'''

def walk_dir(directory_path, filename, date, dateformat):
    """
    Method to extract filename with wildcards or date patterns by walking through a local directory structure
    """
    # Walk through files in directory_path, including subdirectories
    pathlist = []
    if filename == '':
        filename = '*'
    if dateformat in ['','ctime','mtime']:
        filepat = filename
    else:
        filepat = filename % date
    #print ("Checking directory {} for files with {}".format(directory_path, filepat))
    for root, _, filenames in os.walk(directory_path):
        for filename in filenames:
            if fnmatch.fnmatch(filename, filepat):
                file_path = os.path.join(root,filename)
                if dateformat in ['ctime','mtime']:
                    if dateformat == 'ctime':
                        tcheck = datetime.fromtimestamp(os.path.getctime(file_path))
                    if dateformat == 'mtime':
                        tcheck = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if tcheck.date() == date.date():
                        pathlist.append(file_path)
                else:
                    pathlist.append(file_path)
    return pathlist


def dir_extract(lines, filename, date, dateformat):
    """
    Method to extract filename with wildcards or date patterns from a directory listing
    """
    pathlist = []
    if filename == '':
        filename = '*'
    if dateformat in ['','ctime','mtime']:
        filepat = filename
    else:
        filepat = filename % date
    for line in lines:
        #print ("Checking line {}".format(line))
        tokens = line.split()
        # Not interested in directories
        if not tokens[0][0] == "d":
            time_str = tokens[5] + " " + tokens[6] + " " + tokens[7]
            if dateformat in ['ctime','mtime']:
                # cannot distinguish between mtime and ctime here
                time = parser.parse(time_str)
                #print (time.date())
                if time.date() == date.date():
                    pathlist.append(tokens[8])
            else:
                if fnmatch.fnmatch(tokens[8], filepat):
                    file_path = tokens[8]
                    #print (tokens[8])
                    pathlist.append(file_path)
    return pathlist


def die(child, errstr):
    print (errstr)
    print (child.before, child.after)
    child.terminate()
    exit(1)

def ssh_getlist(source, filename, date, dateformat, maxdate, cred=[], pwd_required=True):
    """
    Method to extract filename with wildcards or date patterns from a directory listing
    """
    pathlist = []
    filename = filename.replace('*','')
    if dateformat in ['','ctime','mtime']:
        filepat = filename
    else:
        filepat = filename % date
    if not dateformat in ['','ctime','mtime']:
        searchstr = 'find %s -type f | grep "%s"' % (source,filepat)
    elif dateformat in ['ctime','mtime']:
        mindate = (datetime.utcnow() - date).days
        maxdate = (datetime.utcnow() - maxdate).days
        if maxdate == 0:
            searchstr = 'find {} -type f -{} -{} | grep "{}"'.format(source,dateformat, mindate,filepat)
        else:
            searchstr = 'find {} -type f -{} -{} -{} +{} | grep "{}"'.format(source,dateformat,mindate,dateformat,(mindate-maxdate),filepat)
    else:
        searchstr = 'find {} -type f | grep "{}"'.format(source,filepat)

    COMMAND= "ssh %s@%s '%s';" % (cred[0],cred[2],searchstr)
    child = pexpect.spawn(COMMAND)
    if pwd_required:
        i = child.expect([pexpect.TIMEOUT, 'assword: '])
        child.sendline(cred[1])
    i = child.expect([pexpect.TIMEOUT, 'Permission denied', pexpect.EOF])
    if i == 0:
        die(child, 'ERROR!\nSSH timed out. Here is what SSH said:')
    elif i == 1:
        die(child, 'ERROR!\nIncorrect password Here is what SSH said:')
    elif i == 2:
        result = child.before
    if sys.version_info.major == 3:
        result = result.decode('ascii')
    pathlist = result.split('\r\n')
    pathlist = [elem for elem in pathlist if not elem == '' and not elem == ' ']
    return pathlist


def main(argv):
    creddb = ''
    credtransfer = ''
    user=''
    password= ''
    address = ''
    port = 21
    protocol = ''
    localpath = ''
    remotepath = ''
    sensorid = ''
    stationid = ''
    startdate = ''
    dateformat = ''
    depth = 1
    filename = ''
    db = False
    disableproxy=False
    zipping = False
    walk=False
    defaultuser = ''
    uppercase=False
    force = ''
    forcelist = ['0001','0002','0003','0004','0005','0006','0007','0008'] 
    debug = False
    try:
        opts, args = getopt.getopt(argv,"hc:e:l:r:p:s:t:b:d:a:f:Uowu:xm:z",["creddb=","credtransfer=","localpath=","remotepath=","protocol=","sensorid=","stationid=","startdate=","depth=","dateformat=", "filefomat=","debug=","disableproxy=","walk=","user=","uppercase=","insert-table=","zip="])
    except getopt.GetoptError:
        print('collectfile.py -c <creddb> -e <credtransfer> -l <localpath> -r <remotepath> -p <protocol> -s <sensorid> -t <stationid> -b <startdate> -d <depth> -a <dateformat> -f <filefomat> -U <debug> -o <disableproxy=True> -w <walk=True> -u <user> -x <uppercase> -m <insert-table> -z <zip>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('-------------------------------------')
            print('Description:')
            print('collectfile.py reads data from various sources ')
            print('and uploads data to a data bank.')
            print('Filtering and archiving is done using "cleanup".')
            print('-------------------------------------')
            print('Usage:')
            print('collectfile.py -c <creddb> -e <credtransfer> -l <localpath> -r <remotepath> -p <protocol> -s <sensorid> -t <stationid> -b <startdate> -d <depth> -a <dateformat> -f <filefomat> -U <debug> -o <disableproxy=True> -w <walk=True> -u <user> -x <uppercase> -m <insert-table> -z <zip>')
            print('-------------------------------------')
            print('Options:')
            print('-c            : provide the shortcut to the data bank credentials')
            print('-e            : credentials for transfer protocol')
            print('-l            : localpath - if provided, raw data will be stored there.')
            print('              : two subdirectories will be created - stationID and sensorID')
            print('-r (required) : remotepath - path to the data to be collected')
            print('-p            : protocol of data access - required for ftp and scp')
            print('-s            : ID of the sensor (required if not contained in the data')
            print('                meta information)')
            print('-t            : ID of the station i.e. the Observatory code (required if')
            print('                not in meta data)')
            print('-b            : date to start with, like 2014-11-22, default is current day')
            print('-d            : depth: 1 means today, 2 today and yesterday, 3 last three days, etc')
            print('-a            : dateformat in files to be read')
            print('                like "%Y-%m-%d" for 2014-02-01')
            print('                     "%Y%m%d" for 20140201')
            print('                     "ctime" or "mtime" for using timestamp of file')
            print('                Check out pythons datetime function for more info')
            print('-f            : filename of data file to be read.') 
            print('                Add %s as placeholder for date')     
            print('                examples: "WIC_%s.bin"')
            print('                          "*%s*"')
            print('                          "WIC_%s.*"')
            print('                          "WIC_2013.all" - no dateformat -> single file will be read')
            print('-o (no input) : if selected any systems proxy settings are disabled')
            print('-w (no input) : if selected all subdirectories below remote path will be searched for')
            print('                filename pattern. Only works for local directories and scp.')     
            print('-u            : perform upload as this user - necessary for cron and other root jobs')
            print('                as root cannot use scp transfer.')     
            print('-x            : use uppercase for dateformat (e.g. NOV2014 instead of Nov2014)')
            print('-m            : force data to the given revision number.') 
            print('-z            : if option l is selected raw data will be zipped within localpath.') 
            print('-------------------------------------')
            print('Examples:')
            print('---------')
            print('1. get data from ftp server and add to database')
            print(' python collectfile.py -r "/data/magnetism/gam" -c cobsdb -e zamg -p ftp -t GAM ') 
            print('      -d 2 -f *%s.zip -a "%Y-%m-%d"')
            print('---------')
            print('2. get data from local directory and add to database')
            print('python collectfile.py -c cobsdb -r "/srv/data/"') 
            print('      -s LEMI036_1_0001 -t WIC -a "%Y-%m-%d" -f "LEMI036_1_0001_%s.bin" ')
            print('---------')
            print('3. get data from local directory and add to database, add raw data to archive')
            print('python collectfile.py -c cobsdb -r "/Observatory/archive/WIK/DIDD_3121331_0002/DIDD_3121331_0002_0001/" -s DIDD_3121331_0002 -t WIK -b "2012-06-01" -d 100 -a "%Y-%m-%d" -f "DIDD_3121331_0002_0001_%s.cdf" -l "/srv/archive"')
            print('---------')
            print('4. get data from remote by ssh and store in local archive')
            print('python collectfile.py -e phobostilt -r "/srv/gwr/" -p scp -s GWRSG_12345_0002 -t SGO -b "2012-06-01" -d 30 -a "%y%m%d" -f "G1%s.025" -l "/srv/archive"')
            print('---------')
            print('5. get recently created files from remote by ssh and store in local archive')
            print('python collectfile.py -e themisto -r "/srv/" -p scp -t SGO -d 2 -a ctime -l "/srv/archive"')
            print('---------')
            sys.exit()
        elif opt in ("-c", "--creddb"):
            creddb = arg
        elif opt in ("-e", "--credtransfer"):
            credtransfer = arg
        elif opt in ("-l", "--localpath"):
            localpath = arg
        elif opt in ("-p", "--protocol"):
            protocol = arg
        elif opt in ("-r", "--remotepath"):
            remotepath = arg
        elif opt in ("-s", "--sensorid"):
            sensorid = arg
        elif opt in ("-t", "--stationid"):
            stationid = arg
        elif opt in ("-d", "--depth"):
            try:
                depth = int(arg)
                if not depth >= 1:
                    print("depth needs to be positve") 
                    sys.exit()
            except:
                print("depth needs to be an integer") 
                sys.exit()
        elif opt in ("-a", "--dateformat"):
            dateformat = arg
        elif opt in ("-b", "--begin"):
            startdate = arg
        elif opt in ("-f", "--filename"):
            filename = arg
        elif opt in ("-o", "--option"):
            disableproxy=True
        elif opt in ("-w", "--walk"):
            walk=True
        elif opt in ("-u", "--user"):
            defaultuser = arg
        elif opt in ("-x", "--uppercase"):
            uppercase=True
        elif opt in ("-z", "--zip"):
            zipping=True
        elif opt in ("-m", "--insert-table"):
            force=arg
            if not force in forcelist:
                print ("-m: provided data revision number is not valid: should be 0001 or similar")
                force = ''
        elif opt in ("-U", "--debug"):
            debug = True

    ### ###############################################################################
    ###   1. Check input variables
    ### ###############################################################################

    if localpath == '' and creddb == '':
        print('Specify either a shortcut to the credential information of the database or a local path:')
        print('-- check collectfile.py -h for more options and requirements')
        sys.exit()
    if localpath == '':
        destination = tempfile.gettempdir()
    else:
        if not os.path.isdir(localpath):
            print ("Destination directory {} not existing. Creating it".format(localpath)) 
            os.makedirs(localpath)
        destination = localpath
    if not credtransfer == '':
        user=mpcred.lc(credtransfer,'user')
        password=mpcred.lc(credtransfer,'passwd')
        address = mpcred.lc(credtransfer,'address')
        try:
            port = int(mpcred.lc(credtransfer,'port'))
        except:
            port = 21
    source = ''
    if not protocol in ['','ftp','FTP']:
        source += protocol + "://"
        if not user == '' and not password=='':
            source += user + ":" + password + "@"
        if not address == '':
            source += address
    if not remotepath == '':
        source += remotepath

    if not protocol in ['','scp','ftp','SCP','FTP','html','rsync']:
        print('Specify a valid protocol:')
        print('-- check collectfile.py -h for more options and requirements')
        sys.exit()
    if walk:
        if not protocol in ['','scp','rsync']: 
            print(' Walk mode only works for local directories and scp access.')
            print(' Switching walk mode off.')
            walk = False
 
    if not creddb == '':
        print("Accessing data bank ...")
        try:
            db = mysql.connect (host=mpcred.lc(creddb,'host'),user=mpcred.lc(creddb,'user'),passwd=mpcred.lc(creddb,'passwd'),db =mpcred.lc(creddb,'db'))
            print("success")
        except:
            print("failure - check your credentials")
            sys.exit()

    # loaded all credential (if started from root rootpermissions are relquired for that)
    # now switch user for scp
    if not defaultuser == '':
        uid=pwd.getpwnam(defaultuser)[2]
        os.setuid(uid)

    if startdate == '':
        current = datetime.utcnow() # make that a variable
    else:
        current = DataStream()._testtime(startdate)

    if dateformat == "" and filename == "":
        print('Specify either a fileformat: -f myformat.dat or a dateformat -d "%Y",ctime !')
        print('-- check collectfile.py -h for more options and requirements')
        sys.exit()
    if not dateformat in ['','ctime','mtime']:
        try:
            newdate = datetime.strftime(current,dateformat)
        except:
            print('Specify a vaild datetime dateformat like "%Y-%m-%d"')
            print('-- check collectfile.py -h for more options and requirements')
            sys.exit()
    if "%s" in filename and dateformat in ['','ctime','mtime']:
        print('Specify a datetime dateformat for given placeholder in fileformat!')
        print('-- check collectfile.py -h for more options and requirements')
        sys.exit()
    elif not "%s" in filename and "*" in filename and not dateformat in ['ctime','mtime']:
        print('Specify either ctime or mtime for dateformat to be used with your give fileformat!')
        print('-- check collectfile.py -h for more options and requirements')
        sys.exit()
    elif not "%s" in filename and not "*" in filename and not dateformat in [""]:
        print('Give dateformat will be ignored!')
        print('-- check collectfile.py -h for more options and requirements')
        print('-- continuing ...')

    if debug:
        print("1.0 finished - Parameters OK")

    ### ###############################################################################
    ###   2. Create download/copy link  
    ### ###############################################################################

    ###  for all files conform with eventually provided datelist


    ###   2.1 Check dates  
    ### -------------------------------------

    ### the following parameters are used here:
    ### dateformat, filename

    ### dateformat:  string like ("%Y-%m-%d"), ("ctime", "mtime") or ""
    ### filename:    string like "*%s.bin" (-> requires dateformat[0] ) 
    ###              string like "*.bin" (-> requires dateformat[1] ) 
    ###              string like "myfile.bin" (-> requires dateformat[2] ) 
    ###              empty "" (-> searches either for dateformat[0] or takes all fitting with dateformat[2] ) 

    ###  -> see 1. check parameter

    ### make use of depth and begin to define timerange

    datelist = []
    newcurrent = current
    if not dateformat in ['','ctime','mtime']:
        for elem in range(depth):
            if dateformat == '%b%d%y': #exception for MAGREC
                newdate = datetime.strftime(newcurrent,dateformat)
                datelist.append(newdate.upper())
            else:
                datelist.append(datetime.strftime(newcurrent,dateformat))
            newcurrent = current-timedelta(days=elem+1)
    elif dateformat in ['ctime','mtime']:
        for elem in range(depth):
            datelist.append(newcurrent)
            newcurrent = current-timedelta(days=elem+1)
    else:
        datelist = ['dummy']

    #if debug:
    print(" - Dealing with time range:\n {}".format(datelist))

    ###   2.2 Select files from source meeting critera 
    ### -------------------------------------

    ### Define source based on 'protocol', 'remotepath', 'walk', 'option' and optionally 'sensorid'

    ### protocols: ''(local disk), 'scp', 'ftp', 'html'

    #filelist = getfilelist(protocol, source, sensorid, filename, datelist, walk=True, option=None)
    if debug:
        print("2.2 Starting - Getting filelists")

    filelist = []
    if protocol in ['ftp','FTP']:
        if debug:
            print (" - Getting filelist - by ftp ") 
        import ftplib
        if debug:
            print (" - connecting to {} on port {}".format(address,port)) 
        if not port == 21:
            ftp = ftplib.FTP()
            ftp.connect(address,port)
        else:
            ftp = ftplib.FTP(address)
        if debug:
            print (" - user: {} ".format(user)) 
        ftp.login(user,password)
        ftp.cwd(source)
        lines = []
        ftp.dir("", lines.append)
        ftp.close()
        for date in datelist:
            path = dir_extract(lines, filename, date, dateformat)
            if len(path) > 0:
                filelist.extend(path)
    elif protocol in ['scp','SCP','rsnyc']:
        if debug:
            print (" - Getting filelist - by ssh ") 
        import pexpect
        if not dateformat in ['','ctime','mtime']: 
            for date in datelist:
                path = ssh_getlist(remotepath, filename, date, dateformat, datetime.utcnow(), cred=[user,password,address])
                if len(path) > 0:
                    filelist.extend(path)
        else:
            filelist = ssh_getlist(remotepath, filename, min(datelist), dateformat, max(datelist), cred=[user,password,address])
    elif protocol == '':
        if debug:
            print (" - Getting filelist - from local directory ") 
        ### Search local directory - Working
        for date in datelist:
            path = walk_dir(source, filename, date, dateformat)
            if len(path) > 0:
                filelist.extend(path)
    elif protocol == 'html':
        print (filelist)
        sys.exit()
     
    if debug:
        print ("Result")
        print ("-----------------------------")
        print (filelist)

    ###   2.3 Get selected files and copy them to destination 
    ### -------------------------------------
    ###
    ### only if not protocol == '' and localpath

    ### update filelist with new filenamens on local harddisk

    if debug:
        print("2.3 Writing data to a local directory (or tmp)")

    localpathlist = []

    if not protocol == '' or (protocol == '' and not destination == tempfile.gettempdir()):
        ### Create a directory by getting sensorid names (from source directory)
        def createdestinationpath(localpath,stationid,sensorid):
            subdir = 'raw'
            if not stationid and not sensorid:
                destpath = os.path.join(localpath)
            elif not stationid:
                destpath = os.path.join(localpath,sensorid,'raw')
            elif not sensorid:
                destpath = os.path.join(localpath,stationid.upper())
            else:
                destpath = os.path.join(localpath,stationid.upper(),sensorid,'raw')
            return destpath

        # Open the specific channel
        if protocol in ['ftp','FTP']:
            if not port == 21:
                ftp = ftplib.FTP()
                ftp.connect(address,port)
            else:
                ftp = ftplib.FTP(address)
            ftp.login(user,password)
            ftp.cwd(source)

        for f in filelist:
            path = os.path.normpath(f)
            li = path.split(os.sep)
            if not sensorid and not protocol in ['ftp','FTP']:
                if len(li) >= 2:
                    sensid = li[-2]
            elif not sensorid and protocol in ['ftp','FTP']:
                sensid = f.split('.')[0].rpartition('_')[0]
            else:
                sensid = sensorid

            destpath = createdestinationpath(destination,stationid,sensid)

            destname = os.path.join(destpath,li[-1])

            if not os.path.isdir(destpath):
                os.makedirs(destpath)
            if debug:
                print ("DESTINATION (for files):", destpath, li[-1])

            if protocol in ['ftp','FTP']:
                fhandle = open(destname, 'wb')
                ftp.retrbinary('RETR ' + f, fhandle.write) 
                fhandle.close()                                                     
            elif protocol in ['scp','SCP']:
                scptransfer(user+'@'+address+':'+f,destpath,password,timeout=600)
            elif protocol in ['rysnc']:
                # create a command line string with rsync ### please note,,, rsync requires password less comminuctaion
                rsyncstring = "rsyn -avz -e ssh {} {}".format(user+'@'+address+':'+f,destpath) 
                print ("Executing:", rsyncstring)
                subprocess.call(rsyncstring)
            elif protocol in ['html','HTML']:
                pass
            elif protocol in ['']:
                copyfile(f, destname)
            if zipping:
                if debug:
                    print (" raw data wil be zipped")
                dirname = os.path.dirname(destname)
                oldname = os.path.basename(destname)
                pname = os.path.splitext(oldname)
                if not pname[1] in [".zip",".gz",".ZIP",".GZ"]:
                    zipname = pname[0]+'.zip'
                    with zipfile.ZipFile(os.path.join(dirname,zipname), 'w') as myzip:
                        myzip.write(destname,oldname, zipfile.ZIP_DEFLATED)
                    os.remove(destname)
                    destname = os.path.join(dirname,zipname)
                else:
                    if debug:
                        print (" data is zipped already")
            localpathlist.append(destname)

        if protocol in ['ftp','FTP']:
            ftp.close()
    else:
        localpathlist = [elem for elem in filelist]


    ### ###############################################################################
    ###   3. Read local data and write to database  
    ### ###############################################################################

    ###  for all files conform with eventually provided datelist


    ###   3.1 Read local data
    ### -------------------------------------

    ###  flagging does not make sense 

    if db:
        if debug:
            print("3.1 Writing data to database")

        for f in localpathlist:
            data = read(f)

            if debug:
                print ("Dealing with {}. Length = {}".format(f,data.length()[0]))
                print ("SensorID in file: {}".format(data.header.get('SensorID')))

            statiddata = data.header.get('StationID','')
            if not stationid == '':
                if not statiddata == stationid and not statiddata == '':
                    print("StationID's from file and provided one (or dir) are different!")
                    print ("Using provided value")
                data.header['StationID'] = stationid
            else:
                if data.header.get('StationID','') == '':
                    print("Could not find station ID in datafile")
                    print("Please provide by using -t stationid")
                    sys.exit()
            if debug:
                print("Using StationID", data.header.get('StationID'))
            sensiddata = data.header.get('SensorID','')
            if not sensorid == '':
                if not sensiddata == sensorid and not sensiddata == '':
                    print("SensorID's from file and provided one (or dir) are different!")
                    print ("Using provided value")
                data.header['SensorID'] = sensorid
            else:
                if data.header.get('SensorID','') == '':
                    print("Could not find sensor ID in datafile")
                    print("Please provide by using -s sensorid")
                    sys.exit()
            if debug:
                print("Using SensorID", data.header.get('SensorID'))

            print("{}: Adding {} data points to DB now".format(data.header.get('SensorID'), data.length()[0]))

            if not len(data.ndarray[0]) > 0:
                data = data.linestruct2ndarray()  # Dealing with very old formats                   
            if len(data.ndarray[0]) > 0:
                if not force == '':
                    tabname = data.header.get('SensorID')+'_'+force
                    print (" - Force option chosen: forcing data to table {}".format(tabname))
                    writeDB(db,data, tablename=tabname)
                else:
                    writeDB(db,data)
                    pass


if __name__ == "__main__":
   main(sys.argv[1:])


