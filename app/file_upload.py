#!/usr/bin/env python
# coding=utf-8

"""
Upload files

DESCRIPTION
   upload data to a destination using various different protocols
   supported are FTP, SFTP, RSYNC, SCP

JOBLIST:
   Jobs are listed in a json structure and read by the upload process.
   You can have multiple jobs. Each job refers to a local path. Each job
   can have multiple destinations.


   {"graphmag" :  {"path":"/home/leon/Tmp/Upload/graph/aut.png",
                    "destinations": {"conradpage": { "type":"ftp", "path" : "/images/graphs/magnetism"} },
                    "log":"/home/leon/Tmp/Upload/testupload.log",
                    "endtime":"utcnow",
                     "starttime":2},
    "wicadjmin" :  {"path":"/home/leon/Tmp/Temp",
                    "destinations": {"gleave": { "type":"sftp", "path" : "/uploads/all-obs"} },
                    "log":"/home/leon/Tmp/wicadjart.log",
                    "endtime":"utcnow",
                     "starttime":2},
   }

## FTP Upload from a directory using files not older than 2 days
{"graphmag" : {"path":"/srv/products/graphs/magnetism/","destinations": {"conradpage": { "type":"ftp", "path" : "images/graphs/magnetism/"} },"log":"/home/leon/Tmp/Upload/testupload.log", "extensions" : ["png"], "namefractions" : ["aut"], "starttime" : 2, "endtime" : "utcnow"}}
## FTP Upload a single file
{"graphmag" : {"path":"/home/leon/Tmp/Upload/graph/aut.png","destinations": {"conradpage": { "type":"ftp", "path" : "images/graphs/magnetism/"} },"log":"/home/leon/Tmp/Upload/testupload.log"}}
## FTP Upload all files with extensions
{"mgraphsmag" : {"path":"/home/leon/Tmp/Upload/graph/","destinations": {"conradpage": { "type":"ftp", "path" : "images/graphs/magnetism/"} },"log":"/home/leon/Tmp/Upload/testupload.log", "extensions" : ["png"]} }
## Test environment
{"TEST" : {"path":"../","destinations": {"homepage": { "type":"test", "path" : "my/remote/path/"} },"log":"/var/log/magpy/testupload.log", "extensions" : ["png"], "starttime" : 2, "endtime" : "utcnow"} }
## RSYNC upload
{"ganymed" : {"path":"/home/leon/Tmp/Upload/graph/","destinations": {"ganymed": { "type":"rsync", "path" : "/home/cobs/Downloads/"} },"log":"/home/leon/Tmp/Upload/testupload.log"} }
## JOB on BROKER
{"magnetsim" : {"path":"/home/cobs/SPACE/graphs/","destinations": {"conradpage": { "type":"ftp", "path" : "images/graphs/magnetism/"} },"log":"/home/cobs/Tmp/testupload.log", "extensions" : ["png"], "namefractions" : ["magvar","gic_prediction","solarwind"], "starttime" : 20, "endtime" : "utcnow"}, "supergrad" : {"path":"/home/cobs/SPACE/graphs/","destinations": {"conradpage": { "type":"ftp", "path" : "images/graphs/magnetism/supergrad"} },"log":"/home/cobs/Tmp/testupload.log", "extensions" : ["png"], "namefractions" : ["supergrad"], "starttime" : 20, "endtime" : "utcnow"},"meteo" : {"path":"/home/cobs/SPACE/graphs/","destinations": {"conradpage": { "type":"ftp", "path" : "images/graphs/meteorology/"} },"log":"/home/cobs/Tmp/testupload.log", "extensions" : ["png"], "namefractions" : ["Meteo"], "starttime" : 20, "endtime" : "utcnow"}, "radon" : {"path":"/home/cobs/SPACE/graphs/","destinations": {"conradpage": { "type":"ftp", "path" : "images/graphs/radon/"} },"log":"/home/cobs/Tmp/testupload.log", "extensions" : ["png"], "namefractions" : ["radon"], "starttime" : 20, "endtime" : "utcnow"}, "title" : {"path":"/home/cobs/SPACE/graphs/","destinations": {"conradpage": { "type":"ftp", "path" : "images/slideshow/"} },"log":"/home/cobs/Tmp/testupload.log", "extensions" : ["png"], "namefractions" : ["title"]}, "gic" : {"path":"/home/cobs/SPACE/graphs/","destinations": {"conradpage": { "type":"ftp", "path" : "images/graphs/spaceweather/gic/"} },"log":"/home/cobs/Tmp/testupload.log", "extensions" : ["png","gif"], "namefractions" : ["24hours"]}, "seismo" : {"path":"/home/cobs/SPACE/graphs/","destinations": {"conradpage": { "type":"ftp", "path" : "images/graphs/seismology/"} },"log":"/home/cobs/Tmp/testupload.log", "extensions" : ["png"], "namefractions" : ["quake"]} }

APPLICTAION:
   python3 file_uploads.py -j /my/path/uploads.json -m /tmp/sendmemory.json
"""


from magpy.stream import *
from magpy.database import *
from magpy.transfer import *
import magpy.mpplot as mp
import magpy.opt.emd as emd
import magpy.opt.cred as mpcred
import io, pickle

import itertools
from threading import Thread
from subprocess import check_output   # used for checking whether send process already finished

import getopt
import pwd
import sys


# ################################################
#             Methods
# ################################################

def getcurrentdata(path):
    """
    usage: getcurrentdata(currentvaluepath)
    example: update kvalue
    >>> fulldict = getcurrentdata(currentvaluepath)
    >>> valdict = fulldict.get('magnetism',{})
    >>> valdict['k'] = [kval,'']
    >>> valdict['k-time'] = [kvaltime,'']
    >>> fulldict[u'magnetism'] = valdict
    >>> writecurrentdata(path, fulldict)
    """
    if os.path.isfile(path):
        with open(path, 'r') as file:
            fulldict = json.load(file)
        return fulldict
    else:
        print ("path not found")

def writecurrentdata(path,dic):
    """
    usage: writecurrentdata(currentvaluepath,fulldict)
    example: update kvalue
    >>> see getcurrentdata
    >>>
    """
    with open(path, 'w',encoding="utf-8") as file:
        file.write(unicode(json.dumps(dic)))


def active_pid(name):
     # Part of Magpy starting with version ??
    try:
        pids = map(int,check_output(["pidof",name]).split())
    except:
        return False
    return True


def uploaddata(localpath, destinationpath, typus='ftp', address='', user='', pwd='', port=None, proxy=None, logfile='stdout'):
    """
    DEFINITION:
        upload data method.
        Supports file upload to servers using the following schemes:
        ftp
        sftp     (requires sftp)
        ftpback (background process)
        scp  (please consider using rsync)  scp transfer requires a established key, therefor connect to the server once using ssh to create it
        gin   (curl based ftp upload to data gins)
    """
    success = True
    print ("Running upload to {} (as {}) via {}: {} -> {}, logging to {}".format(address, user, typus, localpath, destinationpath, logfile)) 
    if typus == 'ftpback':
           Thread(target=ftptransfer, kwargs={'source':localpath,'destination':destinationpath,'host':address,'port':port,'user':user,'password':pwd,'logfile':logfile}).start()
    elif typus == 'ftp':
           success = ftptransfer(source=localpath,destination=destinationpath,host=address,port=port,user=user,password=pwd,logfile=logfile)
    elif typus == 'sftp':
           success = sftptransfer(source=localpath,destination=destinationpath,host=address,user=user,password=pwd,proxy=proxy,logfile=logfile)
    elif typus == 'scp':
           timeout = 60
           destina = "{}@{}:{}".format(user,address,destinationpath)
           scptransfer(localpath,destina,pwd,timeout=timeout)
    elif typus == 'rsync':
           # create a command line string with rsync ### please note,,, rsync requires password less comminuctaion
           rsyncstring = "rsync -avz -e ssh {} {}".format(localpath, user+'@'+address+':'+destinationpath)
           print ("Executing:", rsyncstring)
           subprocess.call(rsyncstring.split())
    elif typus.startswith('gin'):
        if not active_pid('curl'):
            print ("  -- Uploading minute data to GIN - active now")
            stdout = False
            if logfile == 'stdout':
                stdout = True
            print (" -- calling GINUPLOAD")
            stdout = True
            if typus.endswith('basic'):
                success = ginupload(localpath, user, pwd, address, authentication=' ',stdout=stdout)
            else:
                success = ginupload(localpath, user, pwd, address, stdout=stdout)
            print ("   -> Done GINUPLOAD")
        else:
            print ("curl is active")
    elif typus == 'test':
           print ("No file transfer - just a test run")
    else:
        print ("Selected type of transfer is not supported")

    return success


def getchangedfiles(basepath,memory,startdate=datetime(1777,4,30),enddate=datetime.utcnow(), extensions=[], namefractions=[], add="newer"):
    """
    DESCRIPTION
        Will compare contents of basepath and memory and create a list of paths with changed information
        This method will work a bit like rsync without accessing the zieldirectory. It just checks whether
        such data has been uploaded already
    VARIABLES
        basepath  (String)      :  contains the basepath in which all files will be checked
        memory    (list/dict)   :  a dictionary with filepath and last change date (use getcurrentdata)
        startdate (datetime)    :  changes after startdate will be considered
        enddate   (datetime)    :  changes before enddate will be considered
        add       (string)      :  either "all" or "newer" (default)
    RETURNS
        dict1, dict2   : dict1 contains all new data sets to be uploaded, dict2 all analyzed data files for storage
    """

    filelist=[]
    try:
        if os.path.isfile(basepath):
            filelist = [basepath]
        else:
            for file in os.listdir(basepath):
                fullpath=os.path.join(basepath, file)
                filename, file_extension = os.path.splitext(fullpath)
                if os.path.isfile(fullpath):
                    if isinstance(extensions,list) and len(extensions) > 0 and any([file_extension.find(ext)>-1 for ext in extensions]) and len(namefractions) > 0:
                        if isinstance(namefractions,list) and len(namefractions) > 0 and any([filename.find(frac)>-1 for frac in namefractions]):
                            filelist.append(fullpath)
                    elif isinstance(extensions,list) and len(extensions) > 0 and any([file_extension.find(ext)>-1 for ext in extensions]) and len(namefractions) == 0:
                        filelist.append(fullpath)
                    elif isinstance(namefractions,list) and len(namefractions) > 0 and any([filename.find(frac)>-1 for frac in namefractions]) and len(extensions) == 0:
                        filelist.append(fullpath)
                    elif len(extensions) == 0 and len(namefractions) == 0:
                        filelist.append(fullpath)
    except:
        print ("Directory not found")
        return {}, {}

    print (filelist, startdate, enddate)


    retrievedSet={}
    for name in filelist:
        mtime = datetime.fromtimestamp(os.path.getmtime(name))
        stat=os.stat(os.path.join(basepath, name))
        mtime=stat.st_mtime
        #ctime=stat.st_ctime
        #size=stat.st_size
        if datetime.utcfromtimestamp(mtime) > startdate and datetime.utcfromtimestamp(mtime) <= enddate:
            retrievedSet[name] = mtime

    print (retrievedSet)

    print (memory)
    if memory:
        if sys.version_info >= (3,):
            newdict = dict(retrievedSet.items() - memory.items())
        else:
            newdict = dict(filter(lambda x: x not in memory.items(), retrievedSet.items()))
    else:
        newdict = retrievedSet.copy()

    return newdict, retrievedSet


def sftptransfer(source, destination, host="yourserverdomainorip.com", user="root", password="12345", port=22, proxy=None, logfile='stdout'):
    """
    DEFINITION:
        Tranfering data to an sftp server
        (proxy support not tested - please additionally use corkscrew for tranfer through a proxy)

    PARAMETERS:
    Variables:
        - source:       (str) Path within ftp to send file to.
        - destination:  (str) full file path to send to.
        - host:         (str) address of reciever
        - user:
        - password:
        - proxy         (tuple) like ("123.123.123.123",8080)
        - logfile:      (str) not used so far


    RETURNS:
        - success (BOOL) True if succesful.

    EXAMPLE:
        >>> sftptransfer(source='/home/me/file.txt', destination='/data/magnetism/file.txt', host='www.example.com', user='mylogin', password='mypassword', logfile='/home/me/Logs/magpy-transfer.log'
                            )
    """

    import os
    try:
        import paramiko
    except:
        print ("paramiko or pysocks not installed ... aborting")
        return False

    if not os.path.isfile(source):
        print ("source does not exist ... aborting")
        return False

    #if not logfile == 'stdout':
    #    paramiko.util.log_to_file(logfile)


    if not proxy:
        transport = paramiko.Transport((host, port))
    else:
        print ("Using proxy (needs to a tuple (paddr,pport)): {}".format(proxy))  
        import socks
        s = socks.socksocket()
        s.set_proxy(
              proxy_type=socks.SOCKS5,
              addr=proxy[0],
              port=proxy[1]
        )
        s.connect((host,port))
        transport = paramiko.Transport(s)

    transport.connect(username=user,password=password)
    with paramiko.SFTPClient.from_transport(transport) as client:
        destina = os.path.join(destination,os.path.basename(source))
        client.put(source, destina)

    return True


def ftptransfer (source, destination, host="yourserverdomainorip.com", user="root", password="12345", port=22, proxy=None, logfile='stdout', cleanup=False, debug=False):
    """
    DEFINITION:
        Tranfering data to an ftp server

    PARAMETERS:
    Variables:
        - source:       (str) Path within ftp to send file to.
        - destination:  (str) full file path to send to.
        - host:         (str) address of reciever
        - user:
        - password:
        - proxy         (tuple) like ("123.123.123.123",8080)
        - logfile:      (str) not used so far
        - cleanup:      (bool) If True, transfered files are removed from the local directory.

    RETURNS:
        - True/False.

    EXAMPLE:
        >>> ftpdatatransfer(
                localfile='/home/me/file.txt',
                ftppath='/data/magnetism/this',
                myproxy='www.example.com',
                login='mylogin',
                passwd='mypassword',
                logfile='/home/me/Logs/magpy-transfer.log'
                            )

    APPLICATION:
        >>>
    """

    if not source:
        return False
    else:
        try:
            filename = os.path.split(source)[1]
        except:
            print ("Could not determine filename of source")
            return False

    if debug:
        print ("ftptransfer: running ftp transfer")

    def ftpjob(site,source,destination,filename):
        site.set_debuglevel(1)
        site.cwd(destination)
        try:
            site.delete(filename)
        except:
            print ("File not yet existing")
        if debug:
            print ("Uploading file ... {}".format(filename))
        try:
            with open(source, 'rb') as image_file:
                site.storbinary('STOR {}'.format(filename), image_file)
        except:
            image_file = open(source, 'rb')
            site.storbinary('STOR {}'.format(filename), image_file)
            image_file.close()


    transfersuccess = False
    tlsfailed = False
    # First try to connect via TLS
    try:
        with ftplib.FTP_TLS(host, user, password) as ftp:
            print ("FTP TLS connection established...")
            ftpjob(ftp,source,destination,filename)
            transfersuccess = True
    except:
        tlsfailed = True

    # First try to connect without TLS
    if tlsfailed:
        try:
            with ftplib.FTP(host, user, password) as ftp:
                print ("FTP connection established...")
                ftpjob(ftp,source,destination,filename)
                transfersuccess = True
        except:
            try:
                # fallback without with (seems to be problemtic on some old py2 machines
                ftp = ftplib.FTP(host, user, password)
                print ("FTP connection established...")
                ftpjob(ftp,source,destination,filename)
                ftp.close()
                transfersuccess = True                
            except:
                pass

    if cleanup and transfersuccess:
        os.remove(source)

    return transfersuccess

def ginupload(filename, user, password, url, authentication=' --digest ', stdout=True):
    """
    DEFINITION:
        Method to upload data to the Intermagnet GINs using curl
        tries to upload data to the gin - if not succesful ...
    PARAMETERS:
      required:
        filename        (string) filename including path
        user            (string) GIN user
        password        (string) GIN passwd
        url             (string) url address (e.g. http://app.geomag.bgs.ac.uk/GINFileUpload/Cache)
        stdout          (bool) if True the return will be printed
    REQUIRES:
        - a working installation of curl
        - the package subprocess
    """
    print ("  Starting ginupload")
    print ("  ------------------")
    faillog = ''
    logpath = ''
    success = False

    if not logpath:
        logpath = "/tmp/ginupload.log"

    commandlist = []

    print ("Running ginupload")

    curlstring = 'curl -F "File=@'+filename+';type=text/plain" -F "Format=plain" -F "Request=Upload" -u '+user+':'+password+authentication+url
    print ("CURL command looks like {}".format(curlstring))
    if not curlstring in commandlist:
        commandlist.append(curlstring)

    # Process each upload
    # -----------------------------------------------------
    for command in commandlist:
        print ("Running command:", command)
        p = subprocess.Popen(command,stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, error = p.communicate()
        print (" -> Done")
        if sys.version_info.major >= 3:
            out = out.decode('ascii')
            error = error.decode('ascii')
        if stdout:
            print(out, error)
        if "Success" in out:
            success = True

    return success


def main(argv):
    statusmsg = {}
    jobs = ''
    tele = ''
    sendlogpath=''
    try:
        opts, args = getopt.getopt(argv,"hj:m:t:",["jobs=","memory=","telegram=",])
    except getopt.GetoptError:
        print ('file_upload.py -j <jobs> -m <memory> -t <telegram>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print ('-------------------------------------')
            print ('Description:')
            print ('-- file_uploads.py send data to any destination of your choice  --')
            print ('-----------------------------------------------------------------')
            print ('file_uploads is a python wrapper allowing to send either by')
            print ('ftp, scp, sftp using a similar inputs.')
            print ('It can hanlde several different uploads at once.')
            print ('Upload parameters have to be provided in a json structure.')
            print ('file_uploads requires magpy >= 0.9.5.')
            print ('-------------------------------------')
            print ('Usage:')
            print ('file_uploads.py -j <jobs> -m <memory> -t <telegram>')
            print ('-------------------------------------')
            print ('Options:')
            print ('-j (required) : a json structure defining the uplaods')
            print ('-m (required) : a path for "memory"')
            print ('-------------------------------------')
            print ('Example of jobs structure:')
            print ('{"wicadjmin":{"path":"/home/leon/Tmp/Temp","destinations":{"gleave":{"type":"sftp", "path" : "/uploads/all-obs"}},')
            print ('"log":"/home/leon/Tmp/wicadjart.log","endtime":"utcnow","starttime":2}}')
            print ('! please note endtime is usually utcnow')
            print ('! starttime is given as a timedelta in days toward endtime, an integer is required')
            print ('-------------------------------------')
            print ('Application:')
            print ('python3 file_uploads.py -j /my/path/uploads.json -m /tmp/sendmemory.json')
            sys.exit()
        elif opt in ("-j", "--jobs"):
            jobs = arg
        elif opt in ("-m", "--memory"):
            sendlogpath = arg
        elif opt in ("-t", "--telegram"):
            tele = arg

    if tele:
        # ################################################
        #          Telegram Logging
        # ################################################

        ## New Logging features
        coredir = os.path.abspath(os.path.join(scriptpath, '..', 'core'))
        sys.path.insert(0, coredir)
        from martas import martaslog as ml
        # tele needs to provide logpath, and config path ('/home/cobs/SCRIPTS/telegram_notify.conf')
        logpath = '/var/log/magpy/mm-fu-uploads.log'


    if jobs == '':
        print ('Specify a valid path to a jobs dictionary (json):')
        print ('-- check file_uploads.py -h for more options and requirements')
        sys.exit()
    else:
        if os.path.isfile(jobs):
            with open(jobs, 'r') as file:
                workdictionary = json.load(file)
        else:
            print ('Specify a valid path to a jobs dictionary (json):')
            print ('-- check file_uploads.py -h for more options and requirements')
            sys.exit()

    # make fileupload an independent method importing workingdictionary (add to MARTAS?)
    if not sendlogpath:
        sendlogpath = '/tmp/lastupload.json'


    """
    Main Prog
    """
    try:
      for key in workdictionary:
        name = "FileUploads-{}".format(key)
        print ("DEALING with ", key)
        lastfiles = {}
        fulldict = {}
        if os.path.isfile(sendlogpath):
            with open(sendlogpath, 'r') as file:
                fulldict = json.load(file)
                lastfiles = fulldict.get(key)
                # lastfiles looks like: {'/path/to/my/file81698.txt' : '2019-01-01T12:33:12', ...}

        if not lastfiles == {}:
            print ("opened memory")
            pass

        sourcepath = workdictionary.get(key).get('path')
        extensions = workdictionary.get(key).get('extensions',[])
        namefractions = workdictionary.get(key).get('namefractions',[])
        # Test if sourcepath is file
        starttime = workdictionary.get(key).get('starttime',datetime(1777,4,30))
        endtime = workdictionary.get(key).get('endtime',datetime.utcnow())
        if endtime in ["utc","now","utcnow"]:
            endtime = datetime.utcnow()
        if isinstance(starttime, int):
            starttime = datetime.utcnow()-timedelta(days=starttime)
        newfiledict, alldic = getchangedfiles(sourcepath, lastfiles, starttime, endtime, extensions,namefractions)

        print ("Found new: {} and all {}".format(newfiledict, alldic))

        for dest in workdictionary.get(key).get('destinations'):
            print ("  -> Destination: {}".format(dest))
            address=mpcred.lc(dest,'address')
            user=mpcred.lc(dest,'user')
            passwd=mpcred.lc(dest,'passwd')
            port=mpcred.lc(dest,'port')
            destdict = workdictionary.get(key).get('destinations')[dest]
            proxy = destdict.get('proxy',None)
            #print (destdict)
            if address and user and newfiledict:
                for nfile in newfiledict:
                    print ("    -> Uploading {} to dest {}".format(nfile, dest))
                    success = uploaddata(nfile, destdict.get('path'), destdict.get('type'), address, user, passwd, port, proxy=proxy, logfile=destdict.get('logfile','stdout'))
                    print ("    -> Success", success)
                    if not success:
                        #remove nfile from alldic
                        # thus it will be retried again next time
                        print (" !---> upload of {} not successful: keeping it in todo list".format(nfile))
                        del alldic[nfile]

        fulldict[key] = alldic
        writecurrentdata(sendlogpath, fulldict)
      statusmsg[name] = "uploading data succesful"
    except:
      statusmsg[name] = "error when uploading files - please check"

    if tele:
        print (statusmsg)
        martaslog = ml(logfile=logpath,receiver='telegram')
        martaslog.telegram['config'] = '/home/cobs/SCRIPTS/telegram_notify.conf'
        martaslog.msg(statusmsg)

    print ("----------------------------------------------------------------")
    print ("file upload app finished")
    print ("----------------------------------------------------------------")
    print ("SUCCESS")


if __name__ == "__main__":
   main(sys.argv[1:])



