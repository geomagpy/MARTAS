#!/usr/bin/env python
"""
Get files from a remote server (to be reached by nfs, samba, ftp, html or local directory) 

file content is directly added to a data bank (or local file if preferred).
"""

from magpy.stream import *
from magpy.core import database
from magpy.core.methods import testtime
from magpy.opt import cred as mpcred

import getopt
import fnmatch
import pexpect
import ftplib
import pwd
import zipfile
import tempfile
from dateutil import parser
from datetime import datetime, timezone
from shutil import copyfile
import filecmp
import subprocess
import socket

from martas.core.methods import martaslog as ml
from martas.core import methods as mm

"""
DESCRIPTION
    Downloads data by default in to an archive "raw" structure
    like /srv/archive/STATIONID/SENSORID/raw
    Adds data into a MagPy database (if writedatabase is True)
    Adds data into a basic archive structure (if writearchive is True)
    The application requires credentials of remote source and local database created by addcred

APPLICATION

   1) Getting binary data from a FTP Source every, scheduled day
    python3 file_download.py -c ../conf/collect-ftpsource.cfg
    in config "collect-ftpsource.cfg":
             sourcedatapath        :      /remote/data
             filenamestructure     :      *%s.bin

   2) Getting binary data from a FTP Source every, scheduled day, using seconday time column and an offset of 2.3 seconds
    python3 file_download -c ../conf/collect-ftpsource.cfg
    in config "collect-ftpsource.cfg":
             sourcedatapath        :      /remote/data
             filenamestructure     :      *%s.bin
             LEMI025_28_0002       :      defaulttimecolumn:sectime;time:-2.3

   3) Just download raw data to archive
    python3 file_download -c ../conf/collect-ftpsource.cfg
    in config "collect-ftpsource.cfg":
             writedatabase     :      False
             writearchive      :      False

   4) Rsync from a ssh server (passwordless access to remote machine is necessary, cred file does not need to contain a pwd) 
    python3 file_download.py -c ../conf/collect-ftpsource.cfg
    in config "collect-ftpsource.cfg":
             protocol          :      rsync
             writedatabase     :      False
             writearchive      :      False

   5) Uploading raw data from local raw archive
    python3 file_download.py -c ../conf/collect-localsource.cfg
    in config "collect-localsource.cfg":
             protocol          :      
             sourcedatapath    :      /srv/archive/DATA/SENSOR/raw
             writedatabase     :      False
             writearchive      :      True
             forcerevision     :      0001


    python3 file_download.py -c ../conf/collect-source.cfg -d 10 -e 2020-10-20

    Debugging option:
    python3 file_download.py -c ../conf/collect-source.cfg -D




CONFIGURATION FILE
 one for each source e.g. collect-janus.cfg


# Data source
# -----------------
# Credentials
sourcecredentials     :      janus

# Path to the data to be collected
sourcedatapath        :      /srv/mqtt

# Protocol for data access (ftp,rsync,scp)
protocol              :      ftp

# Optional - ID of the sensor (required if not contained in the data')
#sensorid              :      xxx_xxx_0001

# Optional - ID of the station i.e. the Observatory code (required if')
#stationid             :      wic

# Dateformat in files to be read
#   like "%Y-%m-%d" for 2014-02-01
#        "%Y%m%d" for 20140201
#        "ctime" or "mtime" for using timestamp of file
dateformat             :      %Y-%m-%d

# filename of data file to be read.
#    Add %s as placeholder for date
#       examples: "WIC_%s.bin"
#                 "*%s*"
#                 "WIC_%s.*"
                  "*.[bin,asc,cdf]" -> define possible variants within brackets 
                  "CALY*[LFZ,LFY,LFX]*%s*" -> brackets can also be used in filename in combiation with date
#                 "WIC_2013.all" - no dateformat -> single file will be read
filenamestructure      :      *%s*

# Timerange
defaultdepth           :      2

# Sensor specific modifications - defaulttimecolumn, offsets by KEY:value pairs
SENSORID               :      defaulttimecolumn:sectime;sectime:2.3

# Perform as user - uncomment if not used
# necessary for cron and other root jobs 
defaultuser     :      cobs

# Walk through subdirectories
# if selected all subdirectories below remote path will be searched for
# filename pattern. Only works for local directories and scp.
walksubdirs     :      False

# Sensors present in path to be skipped (Begging of Sensorname is enough
#blacklist       :      None


# Collecting server
# -----------------
# Archivepath:
# two subdirectories will be created if not existing - based on stationID and sensorID
# e.g. WIC/LEMI025_22_0003
archivepath            :      /srv/archive
# setting subdirectory will lead to date related subdirectories within raw data folder
# supported are year "Y" i.e. /raw/2024/* or "Ym" i.e. /raw/2024/03/*
#subdirectory    :      Y

# If forcedirectory, then archivepath is used for saving data
forcedirectory     :      False


# Zip data in archive directory
zipdata            :      False


# delete from remote source after successful transfer
# (doesnt work with scp)
deleteremote       :      False

# Force data to the given revision number
#forcerevision      :      0001

# Database (Credentials makes use of addcred)
dbcredentials     :      cobsdb

# Disable proxy settings of the system (seems to be unused - check)
disableproxy       :      False

writedatabase     :      True

# Create a basic archiving file without database if True
# basic path is /STATIONID/SENSORID/SENSORID_0001/
writearchive      :      False
archiveformat     :      PYCDF


# Logging
# -----------------
# Logging parameter
# ################
# path to log file
logpath   :   /var/log/magpy/archivestatus.log
# log,email,telegram
notification    :    telegram
# configuration for notification
notificationconf   :   /myconfpath/mynotificationtype.cfg



Changelog:
2014-08-02:   RL removed break when no data was found (could happen if at this selected day not data is available. All other days need to be collected however.
2014-10-22:   RL updated the description
2014-11-04:   RL added the inserttable option to force data upload to a specific table (e.g. for rcs conrad data which has a variable sampling rate)
2015-10-20:   RL changes for fast ndarrays and zip option
2016-10-10:   RL updated imports, improved help and checked for pure file access
2017-03-10:   RL activated force option
2018-10-22:   RL changed all routines considerably
2020-10-01:   RL included and tested rsync option (not perfect, but well, its working)
2021-02-09:   RL rewriting with config (MARCOS sister script of file_upload) --- file_download with add to MagPy database option, column selectors and header updates (e.g. secondary time + offset option)
   - database writing as option (fixed table or not)
   - simple creation of MagPy archive without database tables (but making use of DB meta info)
   - just download files using ftp, scp, rsync etc
   - use a configuration file
2021-07-17    RL complex placeholders for file identifications

"""


def walk_dir(directory_path, filename, date, dateformat, debug=False):
    """
    Method to extract filename with wildcards or date patterns by walking through a local directory structure
    """
    # Walk through files in directory_path, including subdirectories
    pathlist = []
    tcheck = datetime.now()
    if filename == '':
        filename = '*'
    if dateformat in ['','ctime','mtime']:
        filepat = filename
    else:
        filepat = filename % date
    if debug:
        print ("Checking directory {} for files with {}".format(directory_path, filepat))
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

"""
def list_recursive(ftp, remotedir):
    #""
    Get a recursive file listing on FTP sites
    https://stackoverflow.com/questions/65123271/recursive-file-list-with-ftp
    #""
    ftp.cwd(remotedir)
    for entry in ftp.mlsd():
        if entry[1]['type'] == 'dir':
            remotepath = remotedir + "/" + entry[0]
            print(time.time() - t0, remotepath)
            list_recursive(ftp, remotepath)
        else:
            print(entry)
"""

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
        if not tokens[0][0] == "d" and len(tokens)==9:
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
        elif not tokens[0][0] == "d":
            # exception for Geoelectric (Windows FTP)
            if tokens[2] == '<DIR>':
                # Not interested in directories
                continue
            file_path = tokens[3]
            if len(tokens) == 5:
                # TODO blanks in filenames!!!
                file_path = file_path+' '+tokens[4]
            if fnmatch.fnmatch(file_path, filepat):
                pathlist.append(file_path)
    return pathlist


def die(child, errstr):
    print (errstr)
    print (child.before, child.after)
    child.terminate()
    exit(1)


def ssh_getlist(source, filename, date, dateformat, maxdate, cred=None, pwd_required=True, timeout=60, debug=False):
    """
    Method to extract filename with wildcards or date patterns from a directory listing
    """
    if not cred:
        cred = []
    pathlist = []
    #filename = filename.replace('*','')
    print (filename, date)
    if dateformat in ['','ctime','mtime']:
        filepat = filename
    else:
        filepat = filename % date

    if debug:
        print ("Running ssh_getlist for {}".format(filepat))

    def _obtain_search_criteria(fn):
        # BASIC search string
        # fn = filepat
        #grep = 'grep "%s"'
        #search = 'find %s -type f{}{}'.format(find, grep)
        optstr=""
        grepstr=""
        if fn.find("[") >= 0:
            brack = fn[fn.find("[")+1:fn.find("]")]
            opt = brack.split(',')
            for o in opt:
                if o == opt[-1]:
                    optstr += ' -name "*{}*"'.format(o)
                else:
                    optstr += ' -name "*{}*" -o'.format(o)
            fn = fn.replace(brack,'').replace('[]','*')
        el = fn.split('*')
        el = [e for e in el if len(e) > 0]
        for e in el:
            grepstr += ' | grep "{}"'.format(e)
        return optstr, grepstr

    opt, grep = _obtain_search_criteria(filepat)
    #searchstr = 'find %s -type f{}{}'.format(opt, grep)
    #grep += ' | grep -v "#"' #eventually add this exclude
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    if not dateformat in ['','ctime','mtime']:
        searchstr = 'find {} -type f{}{}'.format(source,opt,grep)
    elif dateformat in ['ctime','mtime']:
        mindate = (now - date).days
        maxdate = (now - maxdate).days
        if maxdate == 0:
            searchstr = 'find {} -type f -{} -{}{}{}'.format(source,dateformat, mindate,opt,grep)
        else:
            searchstr = 'find {} -type f -{} -{} -{} +{}{}{}'.format(source,dateformat,mindate,dateformat,(mindate-maxdate),opt,grep)
    else:
        searchstr = 'find {} -type f{}{}'.format(source,opt,grep)

    if debug:
        print ("Searchstring to indentify files to copy: {}".format(searchstr))

    COMMAND= "ssh %s@%s '%s';" % (cred[0],cred[2],searchstr)
    child = pexpect.spawn(COMMAND)
    result = ""
    if timeout:
        child.timeout=timeout
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


def check_configuration(config=None,debug=False):
    """
    DESCRIPTION
        configuration data will be checked
    """
    if not config:
        config = {}

    user = ''
    password = ''
    address = ''
    destination = ''
    source = ''
    port = 21
    db = None
    success = True

    if debug:
        print ("  Checking configuration data")

    creddb =  config.get('dbcredentials','')

    if config.get('archivepath') == '' and creddb == '':
        print('Specify either a shortcut to the credential information of the database or a local path:')
        print('-- check file_download.py -h for more options and requirements')
        success = False
        #sys.exit()
    if config.get('archivepath') == '' or config.get('archivepath') == '/archivepath':
        destination = tempfile.gettempdir()
    else:
        if not os.path.isdir(config.get('archivepath')):
            print ("Destination directory {} not existing. Creating it".format(config.get('archivepath')))
            os.makedirs(config.get('archivepath'))
        destination = config.get('archivepath')
    config['destination'] = destination

    credtransfer = config.get('sourcecredentials')
    if not credtransfer == '':
        if debug:
            print ("   - checking credentials for remote access")
        user=mpcred.lc(credtransfer,'user')
        password=mpcred.lc(credtransfer,'passwd')
        address = mpcred.lc(credtransfer,'address')
        try:
            port = int(mpcred.lc(credtransfer,'port'))
        except:
            port = 21
        if debug:
            print ("   -> done")
    config['rmuser'] = user
    config['rmpassword'] = password
    config['rmaddress'] = address
    config['rmport'] = port

    source = ''
    protocol = config.get('protocol')
    if not protocol in ['','ftp','FTP']:
        source += protocol + "://"
        if not user == '' and not password=='':
            source += user + ":" + password + "@"
        if not address == '':
            source += address

    remotepath = config.get('sourcedatapath')
    if not remotepath == '':
        s = ""
        # if a colon is contained in path (i.e. ftp access on windows)
        if isinstance(remotepath,dict):
            for i in remotepath:
                s = "{}:{}".format(i,remotepath[i])
            remotepath = s
        source += remotepath
    config['source'] = source

    if not protocol in ['','scp','ftp','SCP','FTP','html','rsync']:
        print('Specify a valid protocol:')
        print('-- check file_download.py -h for more options and requirements')
        success = False
        #sys.exit()

    walk = config.get('walksubdirs')
    if debug:
        print ("   Walk through subdirs: {}".format(walk))
    if mm.get_bool(walk):
        if not protocol in ['','scp','rsync']: 
            print('   -> Walk mode only works for local directories and scp access.')
            print('   -> Switching walk mode off.')
            config['walksubdirs'] = False

    if not creddb == '':
        print("   Accessing local data bank ...")
        # required for either writeing to DB or getting meta in case of writing archive
        try:
            db = mm.connect_db(creddb)
        except:
            db = None
    config['db'] = db

    # loaded all credential (if started from root permissions are required for that)
    # now switch user for scp
    # TODO check whether this is working in a function
    if config.get('defaultuser'):
        try:
            uid=pwd.getpwnam(config.get('defaultuser'))[2]
            os.setuid(uid)
        except:
            print ("  User {} not existing -  moving on".format(config.get('defaultuser')))

    dateformat = config.get('dateformat')
    filename = config.get('filenamestructure')
    if isinstance(filename,list):
        # necessary if brackets with options are contained
        filename = ",".join(filename)
    config['filenamestruc'] = filename

    if dateformat == "" and filename == "":
        print('   Specify either a fileformat: -f myformat.dat or a dateformat -d "%Y",ctime !')
        print('   -- check file_download.py -h for more options and requirements')
        success = False
        #sys.exit()
    if not dateformat in ['','ctime','mtime']:
        current = datetime.now(timezone.utc).replace(tzinfo=None)
        try:
            newdate = current.strftime(dateformat)
        except:
            print('   Specify a vaild datetime dateformat like "%Y-%m-%d"')
            print('   -- check file_download.py -h for more options and requirements')
            success = False
            #sys.exit()
    if "%s" in filename and dateformat in ['','ctime','mtime']:
        print('   Specify a datetime dateformat for given placeholder in fileformat!')
        print('   -- check file_download.py -h for more options and requirements')
        success = False
        #sys.exit()
    elif not "%s" in filename and "*" in filename and not dateformat in ['ctime','mtime']:
        print('   Specify either ctime or mtime for dateformat to be used with your give fileformat!')
        print('   -- check file_download.py -h for more options and requirements')
        success = False
        #sys.exit()
    elif not "%s" in filename and not "*" in filename and not dateformat in [""]:
        print('   Give dateformat will be ignored!')
        print('   -- check file_download.py -h for more options and requirements')
        print('   -- continuing ...')

    if debug:
        print("  => Configuration checked - success")

    return config, success


def get_datelist(config=None,current=None,debug=False):
    if not current:
        current = datetime.now(timezone.utc).replace(tzinfo=None)
    if not config:
        config = {}
    if debug:
        print("   -> Obtaining timerange ...")
    datelist = []
    newcurrent = current
    dateformat = config.get('dateformat')
    depth = int(config.get('defaultdepth'))
    if not dateformat in ['','ctime','mtime']:
        for elem in range(depth):
            if dateformat == '%b%d%y': #exception for MAGREC
                newdate = newcurrent.strftime(dateformat)
                datelist.append(newdate.upper())
            else:
                datelist.append(newcurrent.strftime(dateformat))
            newcurrent = current-timedelta(days=elem+1)
    elif dateformat in ['ctime','mtime']:
        for elem in range(depth):
            datelist.append(newcurrent)
            newcurrent = current-timedelta(days=elem+1)
    else:
        datelist = ['dummy']
    if depth == 0:
        #exception for Geoelectric
        newcurrent = current-timedelta(hours=1)
        datelist = [newcurrent.strftime('%Y-%m-%d %H')]

    #if debug:
    print("   -> Dealing with time range:\n {}".format(datelist))

    return datelist


def create_transfer_list(config=None,datelist=None,debug=False):
    """
    DESCRIPTION
        Create a list of files to be transfered
        Define source based on 'protocol', 'remotepath', 'walk'
        protocols: ''(local disk), 'scp', 'ftp', 'html'

        What about rsync? -> no need to use create list but requires passwd-less connection  

    RETURNS
        filelist (a list of remote filepaths to be transferred)
    """

    #filelist = getfilelist(protocol, source, sensorid, filename, datelist, walk=True, option=None)
    if not config:
        config = {}
    if not datelist:
        datelist = []

    if debug:
        print(" Getting filelists")
        print(" -------------------")

    protocol = config.get('protocol','')
    source = config.get('source','')
    remotepath = config.get('sourcedatapath')
    filename = config.get('filenamestruc')
    user = config.get('rmuser')
    password = config.get('rmpassword')
    address = config.get('rmaddress')
    port = config.get('rmport', 21)

    dateformat = config.get('dateformat')

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    filelist = []
    if protocol in ['ftp','FTP']:
        print ("  Connecting to FTP")
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
    elif protocol in ['scp','SCP','rsync']:
        if debug:
            print (" Connecting for {}".format(protocol))
        pwd_required=True
        if protocol == 'rsync':
            pwd_required=False
            print ("   Rsync requires passwordless ssh connection to remote system")
        import pexpect
        if not dateformat in ['','ctime','mtime']:
            for date in datelist:
                path = ssh_getlist(remotepath, filename, date, dateformat, now, cred=[user,password,address],pwd_required=pwd_required,debug=debug)
                if len(path) > 0:
                    filelist.extend(path)
        else:
            filelist = ssh_getlist(remotepath, filename, min(datelist), dateformat, max(datelist), cred=[user,password,address],pwd_required=pwd_required,debug=debug)
    elif protocol == '':
        if debug:
            print (" Local directory access ") 
        ### Search local directory - Working
        for date in datelist:
            path = walk_dir(source, filename, date, dateformat,debug=debug)
            if len(path) > 0:
                filelist.extend(path)
    elif protocol == 'html':
        print (filelist)
        print ("  HTML access not supported - use MagPy directly to access webservices")

    #if debug:
    print ("Files to be transferred")
    print ("-----------------------------")
    print (filelist)
    print ("-----------------------------")

    return filelist


def obtain_data_files(config=None,filelist=None,debug=False):
    """
    DESCRIPTION
        Download data files ane write either to raw directory ot tmp (or to specified folder)
    ###   2.3 Get selected files and copy them to destination
    ###
    ### only if not protocol == '' and localpath

    ### update filelist with new filenamens on local harddisk

        What about rsync? -> no need to use create list but requires passwd-less connection

    RETURNS
        localfilelist (a list with full paths to all files copied to the localfilesystem)
    """

    if not config:
        config = {}
    if not filelist:
        filelist = []

    # Requires
    stationid = config.get('stationid')
    # if sensorid is not provided it will be extracted from the filelist
    sensorid = config.get('sensorid')
    localpath = config.get('archivepath')
    protocol = config.get('protocol')
    source = config.get('source')
    destination = config.get('destination')
    usedatedir = config.get('subdirectory','')
    deleteremote = config.get('deleteremote',False)
    user = config.get('rmuser')
    password = config.get('rmpassword')
    address = config.get('rmaddress')
    port = config.get('rmport',21)
    zipping = mm.get_bool(config.get('zipdata'))
    forcelocal = mm.get_bool(config.get('forcedirectory',False))
    deleteopt = " "
    sensid = ""
    ftp = None

    #filename = config.get('filenamestructure')
    #dateformat = config.get('dateformat')

    def createdestinationpath(localpath='', stationid='', sensorid='', datedir='', forcelocal=False):
            subdir = 'raw'
            if not stationid and not sensorid or forcelocal:
                destpath = os.path.join(localpath)
            elif not stationid:
                destpath = os.path.join(localpath,sensorid,'raw')
            elif not sensorid:
                destpath = os.path.join(localpath,stationid.upper())
            else:
                destpath = os.path.join(localpath,stationid.upper(),sensorid,'raw')
            if not datedir == '':
                destpath = os.path.join(destpath, str(datedir))
            return destpath


    print("  Writing data to a local directory (or tmp)")

    if deleteremote in [True,'True']:
        print("  IMPORTANT: deleting remote data has been activated")

    if debug:
        print ("   Please Note: files will be copied to local filesystem even when debug is selected")

    localpathlist = []

    if not protocol == '' or (protocol == '' and not destination == tempfile.gettempdir()):
        ### Create a directory by getting sensorid names (from source directory)
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
            datedir = ''
            if debug:
                print ("   Accessing file {}".format(f))
            if usedatedir in ['Y','Ym','Yj']:
                # get year from filename or ctime/mtime
                tcheck = datetime.fromtimestamp(os.path.getmtime(f))
                fyear = tcheck.year
                fmonth = tcheck.month
                dirdoy = tcheck.strftime('%j')

                if usedatedir == 'Y':
                    # get year from filename or ctime/mtime
                    datedir = fyear
                elif usedatedir == 'Ym':
                    datedir = '{}/{:02d}'.format(fyear,fmonth)
                elif usedatedir == 'Yj':
                    datedir = '{}/{:03d}'.format(fyear,dirdoy)
                if debug:
                    print ("date related subdirectory:", datedir)
            path = os.path.normpath(f)
            li = path.split(os.sep)
            if not sensorid and not protocol in ['ftp','FTP']:
                if len(li) >= 2:
                    sensid = li[-2]
                if sensid == 'raw' and len(li) >= 3:  # in case an archive raw data structure is loaded
                    sensid = li[-3]
            elif not sensorid and protocol in ['ftp','FTP']:
                sensid = f.split('.')[0].rpartition('_')[0]
            else:
                sensid = sensorid

            destpath = createdestinationpath(destination, stationid, sensid, datedir=datedir, forcelocal=forcelocal)
            if debug:
                print ("Destinationpath:", destpath)

            destname = os.path.join(destpath,li[-1])

            if not os.path.isdir(destpath):
                os.makedirs(destpath)
            if debug:
                print ("   -> write destination (for raw files): {} , {}".format(destpath, li[-1]))

            if protocol in ['ftp','FTP']:
                fhandle = open(destname, 'wb')
                ftp.retrbinary('RETR ' + f, fhandle.write)
                fhandle.close()
                if deleteremote in [True,'True']:
                    ftp.delete(f)
            elif protocol in ['scp','SCP']:
                mm.scptransfer(user+'@'+address+':'+f,destpath,password,timeout=600)
            elif protocol in ['rsync']:
                # create a command line string with rsync ### please note,,, rsync requires password less comminuctaion
                if deleteremote in [True,'True']:
                    deleteopt = " --remove-source-files "
                else:
                    deleteopt = " "
                rsyncstring = "rsync -avz -e ssh{}{} {}".format(deleteopt, user+'@'+address+':'+f,destpath)
                print ("Executing:", rsyncstring)
                subprocess.call(rsyncstring.split())
            elif protocol in ['html','HTML']:
                pass
            elif protocol in ['']:
                if not os.path.exists(destname) or not filecmp.cmp(f, destname):
                    copyfile(f, destname)
                    if deleteremote in [True,'True']:
                        os.remove(f)
                else:
                    print ("   -> raw file already existing - skipping write")
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

    if debug:
        print ("   => all files are now on local system: {}".format(localpathlist))

    return localpathlist



def write_data(config=None,localpathlist=None,debug=False):
    """
    DESCRIPTION
        Read local data and write to database  

    RETURNS
    """
    success = True
    if not config:
        config={}
    if not localpathlist:
        localpathlist=[]
    print("  Writing data to database and/or archive")

    db = config.get('db')
    stationid = config.get('stationid','')
    sensorid = config.get('sensorid','')
    force = config.get('forcerevision','')
    subdirectory = None
    writemode = config.get('writemode','replace')
    if not writemode in ['replace','overwrite']:
        # replace will replace existing data and leave the rest unchanged
        # overwrite will delete the file and write a new one
        writemode = 'replace'


    for f in localpathlist:
        data = DataStream()

        try:
            data = read(f)
        except:
            data = DataStream()

        if data.length()[0] > 0:
            if debug:
                print (" Dealing with {}. Length = {}".format(f,data.length()[0]))
                print (" -------------------------------")
                print (" data looks like: ", data.ndarray)
                #print ("SensorID in file: {}".format(data.header.get('SensorID')))

            # Station ID provided?
            statiddata = data.header.get('StationID','')

            if not stationid == '':
                if not statiddata == stationid and not statiddata == '':
                    print("   StationID's from file and provided one (or dir) are different!")
                    print ("   Using provided value")
                data.header['StationID'] = stationid.upper()
            else:
                if data.header.get('StationID','') == '':
                    print("   Could not find station ID in datafile")
                    print("   Please provide by using -t stationid")
                    #sys.exit()
                    success = False
                    continue

            if debug:
                print("  -> Using StationID", data.header.get('StationID'))

            # Sensor ID extractable?
            sensiddata = data.header.get('SensorID','')

            if not sensorid == '':
                if not sensiddata == sensorid and not sensiddata == '':
                    print("   SensorID's from file and provided one (or dir) are different!")
                    print ("   Using provided value")
                data.header['SensorID'] = sensorid
            else:
                if data.header.get('SensorID','') == '':
                    print("   Could not find sensor ID in datafile")
                    print("   Please provide in configuration or by using -s sensorid")
                    # Abort try clause
                    success = False
                    continue

            fixsensorid = data.header.get('SensorID')

            if debug:
                print("  -> Using SensorID", data.header.get('SensorID'))

            # Conversions
            if config.get(fixsensorid):
                comments = []
                offdict = {}
                comment = data.header.get('DataComments')
                if comment:
                    comments.append(comment)
                print ("  Found modification parameters - applying ...")
                paradict = config.get(fixsensorid)
                if paradict.get('defaulttimecolumn') == 'sectime':
                    print ("    -> secondary time column of raw data will be used as primary")
                    data = data.use_sectime()
                    comm1 = "secondary time colum moved to primary"
                    comments.append(comm1)
                keylist = data._get_key_headers()
                keylist.extend(['time','sectime'])
                for key in keylist:
                    offset = paradict.get(key)
                    #if debug:
                    #    print ("     offset for key {}: {}".format(key, offset))
                    if offset:
                        #try:
                        offset = float(offset)
                        if offset and key in ['time','sectime']:
                            offdict[key] = timedelta(seconds=offset)
                        elif offset:
                            offdict[key] = offset
                        comm = "applied an offset of {} to column {}".format(offset, key)
                        comments.append(comm)
                        print ("    -> offset of {} applied to {}".format(offset, key))
                        #except:
                        #    print ("    -> failure applying offset")
                if offdict:
                    if debug:
                        print ("    applying offsets: {}".format(offdict))
                    #'time': timedelta(hours=1), 'x': 4.2, 'f': -1.34242
                    data = data.offset(offdict)

                # extend comment
                if len(comments) > 1:
                    newcomment = ", ".join(comments) 
                    data.header['DataComments'] = newcomment
                elif len(comments) > 0:
                    newcomment = comments[0]
                    data.header['DataComments'] = newcomment
                print ("  => modifications done")

                #print ("DATAComments", comments, newcomment, data.header['DataComments'])

            def merge_two_dicts(x, y):
                z = x.copy()   # start with x's keys and values
                z.update(y)    # modifies z with y's keys and values & returns None
                return z

            datainfoid = data.header.get('DataID')
            if force:
                if not datainfoid:
                    datainfoid = "{}_{}".format(fixsensorid,str(force).zfill(4))
                    if debug:
                        print ("Using DataID: {}".format(datainfoid))

            # Get existing header information from database and combine with new info
            if datainfoid:
                existheader = db.fields_to_dict(datainfoid)
                data.header = merge_two_dicts(existheader,data.header)

            # Writing data
            if not debug and mm.get_bool(config.get('writedatabase')):
                print("  {}: Adding {} data points to DB now".format(data.header.get('SensorID'), data.length()[0]))

                if not len(data.ndarray[0]) > 0:
                    data = data.linestruct2ndarray()  # Dealing with very old formats                   
                if len(data.ndarray[0]) > 0:
                    try:
                        if not force == '':
                            tabname = "{}_{}".format(fixsensorid,str(force).zfill(4))
                            print (" - Force option chosen: forcing data to table {}".format(tabname))
                            print ("   IMPORTANT: general database meta information will not be updated")
                            db.write(data, tablename=tabname)
                        else:
                            db.write(data)
                    except:
                        print (" !! Error when writing ", f)
                        success = False
            elif debug:
                print ("  DEBUG selected - no database written")

            # Writing data
            if not debug and mm.get_bool(config.get('writearchive')):
                if force:
                    archivepath = os.path.join(config.get('archivepath'),stationid.upper(),fixsensorid,datainfoid)

                    if config.get('archiveformat'):
                        print("  {}: Writing {} data points archive".format(data.header.get('SensorID'), data.length()[0]))
                        if fixsensorid.startswith("LEMI"):
                            # LEMI bin files contains str1 column which cannot be written to PYCDF (TODO) - column contains GPS state
                            data = data._drop_column('str1')
                        if archivepath:
                            data.write(archivepath,filenamebegins=datainfoid+'_',format_type=config.get('archiveformat'),mode=writemode,subdirectory=subdirectory)
                else:
                    print ("  Writing to archive requires forcerevision")
            elif debug:
                print ("  DEBUG selected - no archive written")
    return success

def main(argv):
    version = "2.0.0"
    conf = ''
    etime = ''
    deptharg = ''
    writedbarg = ''
    writearchivearg = ''
    hostname = socket.gethostname().upper()
    statusmsg = {}
    debug = False
    filelist = []
    localpathlist = []
    proxies = {}

    try:
        opts, args = getopt.getopt(argv,"hc:e:d:w:a:D",["configuration=","endtime=","depth=","writedb=","writearchive=","debug=",])
    except getopt.GetoptError:
        print('file_download.py -c <configuration> -e <endtime> -d <depth>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('-------------------------------------')
            print('Description:')
            print('file_download.py reads data from various sources ')
            print('and uploads data to a data bank.')
            print('Filtering and archiving is done using "cleanup".')
            print('-------------------------------------')
            print('Usage:')
            print('file_download.py -c <configuration> -e <endtime> -d <depth>')
            print('-------------------------------------')
            print('Options:')
            print('-c            : configuration file')
            print('-e            : endtime')
            print('-d            : depth: 1 means today, 2 today and yesterday, 3 last three days, etc')
            print('-w            : write to database')
            print('-a            : write to archive')
            print('-------------------------------------')
            print('Examples:')
            print('---------')
            print('---------')
            sys.exit()
        elif opt in ("-c", "--configuration"):
            conf = arg
        elif opt in ("-e", "--endtime"):
            etime = arg
        elif opt in ("-d", "--depth"):
            try:
                deptharg = int(arg)
                if not deptharg >= 1:
                    print("provided depth needs to be positive")
                    sys.exit()
            except:
                print("depth needs to be an integer") 
                sys.exit()
        elif opt in ("-w", "--writedb"):
            writedbarg = arg
        elif opt in ("-a", "--writearchive"):
            writearchivearg = arg
        elif opt in ("-D", "--debug"):
            debug = True

    # Read configuration file
    # -----------------------
    print ("Running file_download - version {}".format(version))
    print ("-------------------------------")

    name = "{}-file-download-{}".format(hostname, os.path.split(conf)[1].split('.')[0])
    statusmsg[name] = 'file_download successfully finished'

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

    if etime == '':
        current = datetime.now(timezone.utc).replace(tzinfo=None) # make that a variable
    else:
        current = testtime(etime)

    # check configuration information
    # -----------------------
    config, success = check_configuration(config=config, debug=debug)

    if not success:
        statusmsg[name] = 'invalid configuration data - aborting'
    else:
        # Override config data with given inputs
        # -----------------------
        if writearchivearg:
            config['writearchive'] = mm.get_bool(writearchivearg)
        if writedbarg:
            config['writedatabase'] = mm.get_bool(writedbarg)
        if deptharg:
            config['defaultdepth'] = deptharg

        # Create datelist
        # -----------------------
        datelist = get_datelist(config=config,current=current,debug=debug)

        # Obtain list of files to be transferred
        # -----------------------
        try:
            filelist = create_transfer_list(config=config,datelist=datelist,debug=debug)
            moveon = True
        except:
            statusmsg[name] = 'could not obtain remote file list - aborting'
            moveon = False

        if moveon:
            # Obtain list of files to be transferred
            # -----------------------
            try:
                localpathlist = obtain_data_files(config=config,filelist=filelist,debug=debug)
            except:
                statusmsg[name] = 'getting local file list failed - check permission'
                localpathlist = []

            # Write data to specified destinations
            # -----------------------
            #try:
            if config.get('db') and len(localpathlist) > 0 and (mm.get_bool(config.get('writedatabase')) or mm.get_bool(config.get('writearchive'))):
                succ = write_data(config=config,localpathlist=localpathlist,debug=debug)
                if not succ:
                    statusmsg[name] = 'could not write data - check logfile'
            #except:
            #    statusmsg[name] = 'problem when writing data'

    # Send Logging
    # -----------------------
    receiver = config.get('notification')
    receiverconf = config.get('notificationconf')
    logpath = config.get('logpath')

    if config.get('https'):
        proxies['https'] = config.get('https')
    if config.get('http'):
        proxies['http'] = config.get('http')

    if debug:   #No update of statusmessages if only a selected sensor list is analyzed
        print (statusmsg)
    else:
        martaslog = ml(logfile=logpath,receiver=receiver,proxies=proxies)
        martaslog.telegram['config'] = receiverconf
        martaslog.msg(statusmsg)

    print ("----------------------------------------------------------------")
    print ("file_download finished")
    print ("----------------------------------------------------------------")
    if statusmsg[name] == 'file_download successfully finished':
        print ("SUCCESS")
    else:
        print ("FAILURE")

if __name__ == "__main__":
   main(sys.argv[1:])


