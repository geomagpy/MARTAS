#!/usr/bin/env python
"""
Get files from a remote server (to be reached by nfs, samba, ftp, html or local directory) 

file content is directly added to a data bank (or local file if preferred).
"""

import os
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
import traceback
import shlex

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
        cred = {}
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

    COMMAND= "ssh {}@{} -o LogLevel=ERROR -p {} '{}';".format(cred.get("user",''),cred.get("address",''),cred.get("port",22),searchstr)
    if debug:
        print ("Sending command: {}".format(COMMAND))
    child = pexpect.spawn(COMMAND)
    result = ""
    if timeout:
        child.timeout=timeout
    if pwd_required:
        i = child.expect([pexpect.TIMEOUT, 'assword: '])
        child.sendline(cred.get("password",""))
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

    source = ''
    protocol = config.get('protocol')
    if not protocol in ['','ftp','FTP']:
        if not port or port == 21:
            # assume default port for ssh
            port = 22
        source += protocol + "://"
        if user and not user == '' and not password=='':
            source += user + ":" + password + "@"
        else:
            print (" file_download: did not find an appropriate user in credentials")
        if address and not address == '':
            source += address
        else:
            print (" file_download: did not find an appropriate address in credentials")

    config['rmport'] = port
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
    creddict = {}
    creddict['user'] = user
    creddict['password'] = password
    creddict['address'] = address
    creddict['port'] = port

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
        # Check for the remote path prefix
        base_prefix = remotepath.rstrip('/') if remotepath else '/'
        if not dateformat in ['','ctime','mtime']:
            for date in datelist:
                path = ssh_getlist(remotepath, filename, date, dateformat, now, cred=creddict,pwd_required=pwd_required,debug=debug)
                # Only take lines which correspond to the remote path beginning
                clean_path = [p.strip() for p in path if p.strip().startswith(base_prefix)]
                if len(clean_path) > 0:
                    filelist.extend(clean_path)
        else:
            raw_list = ssh_getlist(remotepath, filename, min(datelist), dateformat, max(datelist), cred=creddict,
                                   pwd_required=pwd_required, debug=debug)
            filelist = [p.strip() for p in raw_list if p.strip().startswith(base_prefix)]
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


def obtain_data_files(config=None, filelist=None, debug=False):
    """
    DESCRIPTION
        Download data files and write either to raw directory or tmp (or to specified folder).
        Safely handles local and remote directory paths containing spaces.

    RETURNS
        localfilelist (a list with full paths to all files copied to the local filesystem)
    """
    if not config:
        config = {}
    if not filelist:
        filelist = []

    # Requires (alle String-Parameter sauber trimmen)
    stationid = str(config.get('stationid') or '').strip()
    sensorid = str(config.get('sensorid') or '').strip()
    localpath = str(config.get('archivepath') or '').strip()
    protocol = str(config.get('protocol') or '').strip()
    source = str(config.get('source') or '').strip()
    destination = str(config.get('destination') or '').strip()
    usedatedir = str(config.get('subdirectory') or '').strip()
    deleteremote = config.get('deleteremote', False)
    user = str(config.get('rmuser') or '').strip()
    password = config.get('rmpassword')
    address = str(config.get('rmaddress') or '').strip()
    port = int(config.get('rmport') or 21)
    zipping = mm.get_bool(config.get('zipdata'))
    forcelocal = mm.get_bool(config.get('forcedirectory', False))
    sensid = ""
    ftp = None

    def createdestinationpath(basepath='', stationid='', sensorid='', datedir='', forcelocal=False):
        if (not stationid and not sensorid) or forcelocal:
            destpath = basepath
        elif not stationid:
            destpath = os.path.join(basepath, sensorid, 'raw')
        elif not sensorid:
            destpath = os.path.join(basepath, stationid.upper())
        else:
            destpath = os.path.join(basepath, stationid.upper(), sensorid, 'raw')

        if str(datedir) != '':
            destpath = os.path.join(destpath, str(datedir))
        return os.path.normpath(destpath)

    print("  Writing data to a local directory (or tmp)")

    if deleteremote in [True, 'True']:
        print("  IMPORTANT: deleting remote data has been activated")

    if debug:
        print("   Please Note: files will be copied to local filesystem even when debug is selected")

    localpathlist = []

    if protocol != '' or (protocol == '' and os.path.normpath(destination) != os.path.normpath(tempfile.gettempdir())):
        # Open the specific channel
        if protocol in ['ftp', 'FTP']:
            ftp = ftplib.FTP()
            if port != 21:
                ftp.connect(address, port)
            else:
                ftp.connect(address)
            ftp.login(user, password)
            if source:
                ftp.cwd(source)

        for f in filelist:
            datedir = ''
            if debug:
                print("   Accessing file {}".format(f))

            if usedatedir in ['Y', 'Ym', 'Yj']:
                # get year from filename or ctime/mtime
                tcheck = datetime.fromtimestamp(os.path.getmtime(f))
                fyear = tcheck.year
                fmonth = tcheck.month
                dirdoy = tcheck.strftime('%j')

                if usedatedir == 'Y':
                    datedir = str(fyear)
                elif usedatedir == 'Ym':
                    datedir = os.path.join(str(fyear), '{:02d}'.format(fmonth))
                elif usedatedir == 'Yj':
                    datedir = os.path.join(str(fyear), '{:03d}'.format(dirdoy))
                if debug:
                    print("date related subdirectory:", datedir)

            path = os.path.normpath(f)
            li = path.split(os.sep)

            if not sensorid and protocol not in ['ftp', 'FTP']:
                if len(li) >= 2:
                    sensid = li[-2].strip()
                if sensid == 'raw' and len(li) >= 3:  # in case an archive raw data structure is loaded
                    sensid = li[-3].strip()
            elif not sensorid and protocol in ['ftp', 'FTP']:
                sensid = os.path.basename(f).split('.')[0].rpartition('_')[0].strip()
            else:
                sensid = sensorid

            destpath = createdestinationpath(destination, stationid, sensid, datedir=datedir, forcelocal=forcelocal)
            if debug:
                print("Destinationpath:", destpath)

            filename_only = li[-1]
            destname = os.path.join(destpath, filename_only)

            os.makedirs(destpath, exist_ok=True)
            if debug:
                print("   -> write destination (for raw files): {} , {}".format(destpath, filename_only))

            if protocol in ['ftp', 'FTP']:
                with open(destname, 'wb') as fhandle:
                    ftp.retrbinary('RETR ' + f, fhandle.write)
                if deleteremote in [True, 'True']:
                    ftp.delete(f)

            elif protocol in ['scp', 'SCP']:
                scp_port = 22 if port == 21 else port
                # Workaround für Spaces im lokalen Zielpfad: Kurz in destpath wechseln und '.' nutzen
                prev_cwd = os.getcwd()
                try:
                    os.chdir(destpath)
                    mm.scptransfer(f"{user}@{address}:{f}", '.', password, timeout=600, port=scp_port)
                finally:
                    os.chdir(prev_cwd)

            elif protocol in ['rsync']:
                # Liste statt String.split() verwenden -> lokales destpath mit Leerzeichen funktioniert zuverlässig
                rsync_cmd = ['rsync', '-avz', '-e', 'ssh']
                if deleteremote in [True, 'True']:
                    rsync_cmd.append('--remove-source-files')
                # Remote-Pfad mit shlex.quote schützen, falls dort Leerzeichen enthalten sind
                remote_spec = f"{user}@{address}:{shlex.quote(f)}"
                rsync_cmd.extend([remote_spec, destpath])

                if debug:
                    print("Executing:", rsync_cmd)
                subprocess.run(rsync_cmd, check=False)

            elif protocol in ['html', 'HTML']:
                pass

            elif protocol == '':
                if not os.path.exists(destname) or not filecmp.cmp(f, destname, shallow=False):
                    copyfile(f, destname)
                    if deleteremote in [True, 'True']:
                        os.remove(f)
                else:
                    print("   -> raw file already existing - skipping write")

            if zipping:
                if debug:
                    print(" raw data will be zipped")
                dirname = os.path.dirname(destname)
                oldname = os.path.basename(destname)
                pname = os.path.splitext(oldname)
                if pname[1].lower() not in [".zip", ".gz"]:
                    zipname = pname[0] + '.zip'
                    zip_full_path = os.path.join(dirname, zipname)
                    with zipfile.ZipFile(zip_full_path, 'w') as myzip:
                        myzip.write(destname, oldname, zipfile.ZIP_DEFLATED)
                    os.remove(destname)
                    destname = zip_full_path
                else:
                    if debug:
                        print(" data is zipped already")

            localpathlist.append(destname)

        if protocol in ['ftp', 'FTP'] and ftp:
            ftp.close()
    else:
        localpathlist = [os.path.normpath(elem) for elem in filelist]

    if debug:
        print("   => all files are now on local system: {}".format(localpathlist))

    return localpathlist


def write_data(config=None, localpathlist=None, debug=False):
    """
    DESCRIPTION
        Read local data and write to database and/or archive.
        Handles directory paths containing spaces safely.

    RETURNS
        bool: True if all operations succeeded, False otherwise.
    """
    success = True
    if not config:
        config = {}
    if not localpathlist:
        localpathlist = []
    print("  Writing data to database and/or archive")

    db = config.get('db')
    stationid = str(config.get('stationid', '')).strip()
    sensorid = str(config.get('sensorid', '')).strip()
    force = str(config.get('forcerevision', '')).strip()
    subdirectory = str(config.get('writedirectory', '')).strip()
    writemode = str(config.get('writemode', 'replace')).strip()
    if writemode not in ['replace', 'overwrite']:
        # replace will replace existing data and leave the rest unchanged
        # overwrite will delete the file and write a new one
        writemode = 'replace'

    def merge_two_dicts(x, y):
        z = x.copy()   # start with x's keys and values
        z.update(y)    # modifies z with y's keys and values & returns None
        return z

    for f in localpathlist:
        f_clean = os.path.normpath(str(f).strip())
        data = DataStream()

        # Datei sicher einlesen (mit Workaround für Verzeichnisse mit Leerzeichen)
        try:
            abs_file = os.path.abspath(f_clean)
            file_dir = os.path.dirname(abs_file)
            file_name = os.path.basename(abs_file)

            if os.path.isdir(file_dir):
                prev_cwd = os.getcwd()
                try:
                    os.chdir(file_dir)
                    data = read(file_name)
                finally:
                    os.chdir(prev_cwd)
            else:
                data = read(f_clean)
        except Exception as e:
            print(f" !! Error reading '{f_clean}': {e}")
            if debug:
                traceback.print_exc()
            data = DataStream()

        if data.length()[0] > 0:
            if debug:
                print(" Dealing with {}. Length = {}".format(f_clean, data.length()[0]))
                print(" -------------------------------")
                print(" data looks like: ", data.ndarray)

            # Station ID provided?
            statiddata = str(data.header.get('StationID', '')).strip()

            if stationid != '':
                if statiddata != stationid and statiddata != '':
                    print("   StationID's from file and provided one (or dir) are different!")
                    print("   Using provided value")
                data.header['StationID'] = stationid.upper()
            else:
                if statiddata == '':
                    print("   Could not find station ID in datafile")
                    print("   Please provide by using -t stationid")
                    success = False
                    continue
                data.header['StationID'] = statiddata.upper()

            if debug:
                print("  -> Using StationID", data.header.get('StationID'))

            # Sensor ID extractable?
            sensiddata = str(data.header.get('SensorID', '')).strip()

            if sensorid != '':
                if sensiddata != sensorid and sensiddata != '':
                    print("   SensorID's from file and provided one (or dir) are different!")
                    print("   Using provided value")
                data.header['SensorID'] = sensorid
            else:
                if sensiddata == '':
                    print("   Could not find sensor ID in datafile")
                    print("   Please provide in configuration or by using -s sensorid")
                    success = False
                    continue
                data.header['SensorID'] = sensiddata

            fixsensorid = str(data.header.get('SensorID', '')).strip()

            if debug:
                print("  -> Using SensorID", fixsensorid)

            # Conversions
            if config.get(fixsensorid):
                comments = []
                offdict = {}
                comment = data.header.get('DataComments')
                if comment:
                    comments.append(comment)
                print("  Found modification parameters - applying ...")
                paradict = config.get(fixsensorid)
                if paradict.get('defaulttimecolumn') == 'sectime':
                    print("    -> secondary time column of raw data will be used as primary")
                    data = data.use_sectime()
                    comm1 = "secondary time colum moved to primary"
                    comments.append(comm1)
                keylist = data._get_key_headers()
                keylist.extend(['time', 'sectime'])
                for key in keylist:
                    offset = paradict.get(key)
                    if offset:
                        try:
                            offset = float(offset)
                            if offset and key in ['time', 'sectime']:
                                offdict[key] = timedelta(seconds=offset)
                            elif offset:
                                offdict[key] = offset
                            comm = "applied an offset of {} to column {}".format(offset, key)
                            comments.append(comm)
                            print("    -> offset of {} applied to {}".format(offset, key))
                        except Exception as e:
                            print(f"    -> failure applying offset for {key}: {e}")
                if offdict:
                    if debug:
                        print("    applying offsets: {}".format(offdict))
                    data = data.offset(offdict)

                # extend comment
                if len(comments) > 1:
                    newcomment = ", ".join(comments)
                    data.header['DataComments'] = newcomment
                elif len(comments) > 0:
                    newcomment = comments[0]
                    data.header['DataComments'] = newcomment
                print("  => modifications done")

            datainfoid = str(data.header.get('DataID', '')).strip()
            if force:
                if not datainfoid:
                    datainfoid = "{}_{}".format(fixsensorid, str(force).zfill(4))
                    if debug:
                        print("Using DataID: {}".format(datainfoid))

            # Get existing header information from database and combine with new info
            if datainfoid and db is not None:
                existheader = db.fields_to_dict(datainfoid)
                data.header = merge_two_dicts(existheader, data.header)

            # Writing data to database
            if not debug and mm.get_bool(config.get('writedatabase')):
                print("  {}: Adding {} data points to DB now".format(fixsensorid, data.length()[0]))

                if not len(data.ndarray[0]) > 0:
                    data = data.linestruct2ndarray()  # Dealing with very old formats
                if len(data.ndarray[0]) > 0:
                    try:
                        if force != '':
                            tabname = "{}_{}".format(fixsensorid, str(force).zfill(4))
                            print(" - Force option chosen: forcing data to table {}".format(tabname))
                            print("   IMPORTANT: general database meta information will not be updated")
                            db.write(data, tablename=tabname)
                        else:
                            db.write(data)
                    except Exception as e:
                        print(f" !! Error when writing '{f_clean}' to database: {e}")
                        if debug:
                            traceback.print_exc()
                        success = False
            elif debug:
                print("  DEBUG selected - no database written")

            # Writing data to archive (abgesichert gegen Leerzeichen in Verzeichnisnamen)
            if not debug and mm.get_bool(config.get('writearchive')):
                if force:
                    base_archive = str(config.get('archivepath', '')).strip()
                    if not base_archive:
                        print(" !! Error: archivepath is not configured")
                        success = False
                        continue

                    active_stationid = str(data.header.get('StationID', stationid)).strip().upper()
                    archivepath = os.path.normpath(
                        os.path.join(base_archive, active_stationid, fixsensorid, datainfoid)
                    )

                    if config.get('archiveformat'):
                        print("  {}: Writing {} data points archive".format(fixsensorid, data.length()[0]))
                        if fixsensorid.startswith("LEMI"):
                            # LEMI bin files contains str1 column which cannot be written to PYCDF (TODO) - column contains GPS state
                            data = data._drop_column('str1')

                        if archivepath:
                            try:
                                # Zielverzeichnis inkl. Unterverzeichnis vorab sicher anlegen
                                target_dir = os.path.join(archivepath, subdirectory) if subdirectory else archivepath
                                os.makedirs(target_dir, exist_ok=True)

                                # Kurz in archivepath wechseln, damit C-Bibliotheken (z.B. pycdf)
                                # nur den relativen Pfad '.' ohne Leerzeichen sehen
                                prev_cwd = os.getcwd()
                                try:
                                    os.chdir(archivepath)
                                    data.write(
                                        '.',
                                        filenamebegins=datainfoid + '_',
                                        format_type=config.get('archiveformat'),
                                        mode=writemode,
                                        subdirectory=subdirectory
                                    )
                                finally:
                                    os.chdir(prev_cwd)
                            except Exception as e:
                                print(f" !! Error when writing archive to '{archivepath}': {e}")
                                if debug:
                                    traceback.print_exc()
                                success = False
                else:
                    print("  Writing to archive requires forcerevision")
            elif debug:
                print("  DEBUG selected - no archive written")

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


