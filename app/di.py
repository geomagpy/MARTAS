#!/usr/bin/env python
"""

DI.PY 
Applictaion to analysze di data from different sources
######################################################

di.py can analyze data from various sources by considering data from 
several different variometers and scalar systems. It further supports 
data from multiple piers with different characteristics. Please note:
directional pier differences (dD and dI) are not considered.
 

How does it work:

1. - Needs access to all available variometers
   - Needs access to all available scalar sensors (first is primary)
   -> Primary access is database 
   -> if not present or no data available there go to archive
   -> no success in archive: test for reported files on ftp accout 
        (fallback in case the process is not running with servers access) 
   => Test access and report any errors

   Parameters: -dbcred, id-list-vario, id-list-scalar, path-to-archive, link-to-fallback, fallback-cred

Get files from a remote server (to be reached by nfs, samba, ftp, html or local directory) 
File content is directly added to a data bank (or local file if preferred).
"""
from __future__ import print_function

from magpy.stream import *
from magpy.absolutes import *
import magpy.mpplot as mp
from magpy.database import *
from magpy.opt import cred as mpcred

import getopt
import fnmatch
import pwd, grp  # for changing ownership of web files


def walkdir(filepat,top):
    for path, dirlist, filelist in os.walk(top):
        for name in fnmatch.filter(filelist,filepat):
            yield os.path.join(path,name)


def main(argv):
    creddb = ''				# c
    dipath = ''				# a
    variolist = ''			# v
    variodataidlist = ''		# j
    scalarlist = ''			# s
    scalardataidlist = ''		# k
    pierlist = ''			# p
    abstypelist = ''			# y
    azimuthlist = ''			# z
    archive = ''			# w   (e.g. /srv/archive)
    identifier = 'BLV'                 # f
    stationid = 'wic'			# t
    fallbackvariopath = ''		# o
    fallbackscalarpath = ''		# l
    begin = '1900-01-01'		  		  # b
    end = datetime.strftime(datetime.utcnow(),"%Y-%m-%d") # e
    expD = 3				# d
    expI = 64				# i
    compensation=False                  # m
    rotation=False                      # q
    dbadd = False			# n
    addBLVdb = False			# n
    flagging=False			# g
    createarchive=False			# r
    webdir = '/var/www/joomla/images/didaten/' # TODO add option
    webuser = 'www-data'
    webgroup = 'www-data'
    defaultuser = 'cobs'
    defaultgroup = 'cobs'

    keepremote = False
    getremote = False
    remotecred = ''
    remotepath = ''
    variopath = ''			# 
    scalarpath = ''			# 

    try:
        opts, args = getopt.getopt(argv,"hc:a:v:j:s:k:o:mql:b:e:t:z:d:i:p:y:w:f:ngrx:u:",["cred=","dipath=","variolist=","variodataidlist=","scalarlist=","scalardataidlist=","variopath=","compensation=","rotation=","scalarpath=","begin=","end=","stationid=","pierlist=","abstypelist=","azimuthlist=","expD=","expI=","write=","identifier=","add2DB=","flag=","createarchive=","webdir=","keepremote"])
    except getopt.GetoptError:
        print('di.py -c <creddb> -a <dipath> -v <variolist>  -j <variodataidlist> -s <scalarlist> -o <variopath> -m <compensation> -q <rotation> -l <scalarpath> -b <startdate>  -e <enddate> -t <stationid>  -p <pierlist> -z <azimuthlist> -y <abstypelist> -d <expectedD> -i <expectedI> -w <writepath> -f<identifier> -n <add2DB>  -g  <flag> -r <createarchive> -x <webdir> -u <user> --keepremote')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('-------------------------------------')
            print('Description:')
            print('dianalysis.py reads DI measurements and calculates DI values.')
            print('Provide variometer and scalar data for correction.')
            print('Returns di values, f and collimation angles.')
            print('A number of additional option allow for archiving, validity tests,')
            print('and output redirection. If variometer data is provided, base values')
            print('are calculated. ')
            print('')
            print('-------------------------------------')
            print('Usage:')
            print('di.py -c <creddb> -a <dipath> -v <variolist>  -j <variodataidlist> -s <scalarlist> -o <variopath> -l <scalarpath> -m <compensation> -q <rotation> -b <startdate>  -e <enddate> -t <stationid>  -p <pierlist> -z <azimuthlist> -y <abstypelist> -d <expectedD> -i <expectedI> -w <writepath> -n <add2DB>  -g  <flag> -r <createarchive> -x <webdir> -u <user> --keepremote')
            print('-------------------------------------')
            print('Options:')
            print('-c            : provide the shortcut to the data bank credentials')
            print('-a (required) : path to DI data - can be either a real path to a local directory')
            print('                    or a credential shortcut for a remote connection ')
            print('-w (required) : archivepath for writing results and eventually accessing data.')
            print('                e.g. /srv/archive. or /tmp') 
            print('                below this folder the following structure will be implemented:') 
            print('                -/srv/archive/"StationID"/DI/analyse : ')
            print('                                 folder with raw data to be analyzed') 
            print('                -/srv/archive/"StationID"/DI/data : ')
            print('                                 folder with calculated di results') 
            print('                                 Name will be set to "BLV_" + variometerID + pier.')
            print('                                 This plain text file can be opend and') 
            print('                                 analyzed with the MagPy stream package.') 
            print('                -/srv/archive/"StationID"/DI/raw : ')
            print('                             archivefolder with successfully analyzed raw data') 
            print('-f            : idetifier for BLV data (in database and filename) - default is BLV')
            print('-v            : variolist - comma separated list of variometer ids')
            print('-j            : variodataidlist - specify the dataids to be used fro each vario')
            print('                Default: 0002 for each variometer sensor')
            print('-o            : path to variometer data')
            print('-m (no input) : apply compensation field values to variometer data')
            print('-q (no input) : apply rotation to variometer data')
            print('-s            : scalarpath - path to scalar data')
            print('-k            : scalardataidlist - specify the dataids to be used fro each scalar')
            print('                Default: 0002 for each scalar sensor')
            print('-b            : startdate - begin of analysis  (not yet active)')
            print('-e            : enddate - default is today (not yet active)')
            print('-t (required) : ID of the station i.e. the Observatory code (required if')
            print('                not in meta data of DI measurements)')
            print('-z            : list of astronomic azimuths of the mark from the measurement pier')
            print('              : Azimuthlist needs either to be empty or to have the same order ')
            print('                and length of the pierlist.')
            print('                use "False" if the specific value should be taken from the')
            print('                originalfile/database')
            print('                e.g. -p D3,H6  -z False,156.678')
            print('-y            : comma separated list of absolute data types for each pier')
            print('              : "di" for standard theodolite or "autodif" ')
            print('              : e.g. -p D3,H6 -m di,autodif ')
            print('-d            : expected declination')
            print('-i            : expected inclination')
            print('-p (required) : name/number of the pier, comma separated list') 
            print('-n (no input) : add di and basevalues to data base')
            print('-g (no input) : read flaglist from DB if db is opened and add flags')
            print('-r            : move successfully analyzed files to raw archive')
            print('-x            : directory to copy non-analyzed files to.')
            print('              : can be a www directory at which PHP-scripts are used to edit data.')
            print('-u            : define user for which jobs are performed')
            print('              : e.g. cobs:cobsgroup')
            print('--keepremote  : Don t delete remote files after dowloading them')
            print('-------------------------------------')
            print('Examples:')
            print('1. Running on MARCOS servers:') 
            print('python di.py -c wic -a cobshome,cobenzlabs -v "FGE_S0252_0001"')
            print('      -s "POS1_N432_0001" -j 0002 -b 2014-01-01') 
            print('      -w /media/DAE2-4808/archive -d 3 -i 64 -t wic -p H1,A7,A2,A16')
            print('      -y di,di,di,autodif -z False,179.8978,180.1391,267.3982')
            print('2. Running it with manually provided data links:') 
            print('python di.py -c wic -a /media/DAE2-4808/archive/WIC/DI/analyze') 
            print('      -v "FGE_S0252_0001" -s "POS1_N432_0001" -j 0002 -b 2014-02-01')
            print('      -e 2014-05-01 -w /media/DAE2-4808/archive -d 3 -i 64 -t wic')
            print('      -p H1,A7,A2,A16 -y di,di,di,autodif -r') 
            print('      -z False,179.8978,180.1391,267.3982 -u user:group')
            print('python di.py -c cobs -a cobshomepage,cobenzlabs ')
            print('      -v DIDD_3121331_0002,LEMI025_1_0002 -s DIDD_3121331_0002')
            print('      -j 0001,0001 -b 2014-10-01 -e 2014-10-07')
            print('      -w /srv/archive -d 3 -i 64 -t wik -p D -n -r')
            sys.exit()
        elif opt in ("-c", "--creddb"):
            creddb = arg
        elif opt in ("-a", "--dipath"):
            dipath = arg
        elif opt in ("-w", "--archive"):
            archive=arg
        elif opt in ("-f", "--identifier"):
            identifier=arg
        elif opt in ("-v", "--variolist"):
            variolist = arg.split(',')
        elif opt in ("-j", "--variodataidlist"):
            variodataidlist = arg.split(',')
        elif opt in ("-s", "--scalarlist"):
            scalarlist = arg.split(',')
        elif opt in ("-k", "--scalardataidlist"):
            scalardataidlist = arg.split(',')
        elif opt in ("-o", "--variopath"):
            fallbackvariopath = arg
        elif opt in ("-m", "--compensation"):
            compensation=True
        elif opt in ("-q", "--rotation"):
            rotation=True
        elif opt in ("-l", "--scalarpath"):
            fallbackscalarpath = arg
        elif opt in ("-b", "--begin"):
            begin = arg
        elif opt in ("-e", "--end"):
            end = arg
        elif opt in ("-t", "--stationid"):
            stationid = arg
        elif opt in ("-p", "--pierlist"):
            pierlist = arg.split(',')
        elif opt in ("-z", "--azimuthlist"):
            azimuthlist = arg.split(',')
        elif opt in ("-y", "--abstypelist"):
            abstypelist = arg.split(',')
        elif opt in ("-x", "--webdir"):
            webdir = arg
        elif opt in ("-u", "--user"):
            user = arg.split(':')
            if len(user) > 1:
                defaultuser = user[0]
                defaultgroup = user[1]
        elif opt in ("-d", "--expectedD"):
            try:
                expD = float(arg)
            except:
                print("expected declination needs to be a float") 
                sys.exit()
        elif opt in ("-i", "--expectedI"):
            try:
                expI = float(arg)
            except:
                print("expected inclination needs to be a float") 
                sys.exit()
        elif opt in ("-n", "--add2db"):
            dbadd = True
            addBLVdb = True
        elif opt in ("-g", "--flag"):
            flagging=True
        elif opt in ("--keepremote"):
            keepremote=True
        elif opt in ("-r", "--createarchive"):
           createarchive=True

    if dipath == '':
        print('Specify the path to the DI data: -a /path/to/my/data !')
        print('-- check dianalysis.py -h for more options and requirements')
        sys.exit()

    if archive == '':
        print('Specify an Archive path for writing results: -w /path/to/my/archive !')
        print('-- check dianalysis.py -h for more options and requirements')
        sys.exit()

    if variolist == '':
        variolist = []
    if scalarlist == '':
        scalarlist = []
    if azimuthlist == '':
        azimuthlist = []
    if abstypelist == '' or len(abstypelist) == 0:
        abstypelist = ['di' for elem in pierlist]
    if variodataidlist == '':
        variodataidlist = []
    if scalardataidlist == '':
        scalardataidlist = []
    if len(variodataidlist) == 0:
        variodataidlist = ['0002' for elem in variolist]
    else:
        if not len(variolist) == len(variodataidlist):
            print('You need to specify a specific DataID for each variometer: e.g. -j 0002,0001')
            print('-- check dianalysis.py -h for more options and requirements')
            sys.exit()
    if len(scalardataidlist) == 0:
        scalardataidlist = ['0002' for elem in scalarlist]
    else:
        if not len(scalarlist) == len(scalardataidlist):
            print('You need to specify a specific DataID for each variometer: e.g. -j 0002,0001')
            print('-- check dianalysis.py -h for more options and requirements')
            sys.exit()


    if not len(abstypelist) == 0:
        if not len(abstypelist) == len(pierlist):
            print('Abstypelist needs to have the same order and length of the pierlist')
            print('-- check dianalysis.py -h for more options and requirements')
            sys.exit()

    try:
        test = datetime.strptime(begin,"%Y-%m-%d")
        print(test)
    except:
        print('Date format for begin seems to be wrong: -b 2013-11-22')
        print('-- check dianalysis.py -h for more options and requirements')
        sys.exit()

    try:
        datetime.strptime(end,"%Y-%m-%d")
    except:
        print('Date format for end seems to be wrong: -e 2013-11-22')
        print('-- check dianalysis.py -h for more options and requirements')
        sys.exit()
  
    if pierlist == []:
        print('Specify a list of the measurement piers containing at list one element: -p [Pier2]')
        print('-- check dianalysis.py -h for more options and requirements')
        sys.exit()

    if not len(azimuthlist) == 0:
        if not len(azimuthlist) == len(pierlist):
            print('Azimuthlist needs to have the same order and length of the pierlist')
            print('-- check dianalysis.py -h for more options and requirements')
            sys.exit()

    if stationid == '':
        print('Specify a station name e.g. your observatory code')
        print('-- check dianalysis.py -h for more options and requirements')
        sys.exit()
    else:
        stationid = stationid.upper()

    if not creddb == '':
        print("Accessing data bank ...")
        try:
            db = mysql.connect (host=mpcred.lc(creddb,'host'),user=mpcred.lc(creddb,'user'),passwd=mpcred.lc(creddb,'passwd'),db =mpcred.lc(creddb,'db'))
            print("success")
        except:
            print("failure - check your credentials")
            sys.exit()
    else:
        db = False

    if not fallbackvariopath == '':
        if not fallbackvariopath.endswith('*'):
            fallbackvariopath = os.path.join(fallbackvariopath,'*')
        variopath = fallbackvariopath

    if not fallbackscalarpath == '':
        if not fallbackscalarpath.endswith('*'):
            fallbackscalarpath = os.path.join(fallbackscalarpath,'*')
        scalarpath = fallbackscalarpath

    if variolist == []:
        if fallbackvariopath == '':
            print('You have not provided any variometer information at all')
 
    if scalarlist == []:
        if fallbackscalarpath == '':
            print('You have not provided any independent scalar information')
            print('-- I guess this data is provided along with the DI files') 

    # -----------------------------------------------------
    # a) Basic information
    # -----------------------------------------------------
    print(archive)
    print(variolist)
    print(abstypelist)
    print(dipath)

    # -----------------------------------------------------
    # b) Getting new raw data from the input server
    # -----------------------------------------------------
    if not os.path.exists(dipath):
        print("No local dipath found")
        try:
            credlist = mpcred.sc()
            credshort = [elem[0] for elem in credlist] 
            print(credshort)
        except:
            print("dipath %s not existing - credentials not accessible - aborting" % dipath)
            sys.exit()
        try:
            dic = dipath.split(',')
            print(dic)
            print(len(dic))
            if len(dic) == 2:
                remotecred = dic[0]
                remotepath = dic[1]
            elif len(dic) == 1:
                remotecred = dic[0]
                remotepath = ''
            else:
                print("could not interprete dipath in terms of credential information")
                sys.exit()            
            if remotecred in credshort:
                getremote = True
            else:
                print("dipath %s not existing - credentials not existing - aborting" % dipath)
        except:
            print("dipath %s not existing - credentials not existing - aborting" % dipath)
            sys.exit()
        if getremote == False:
            sys.exit()
    else:
        print("Found directory with specified dipath")

    # Getting data from the webdir (eventually edited and corrected)
    if createarchive and not webdir == '':
        dipath = os.path.join(archive,stationid,'DI','analyze')
        for pier in pierlist:
            diid = pier + '_' + stationid + '.txt'
            for infile in iglob(os.path.join(webdir,'*'+diid)):
                # Testing whether file exists:
                if os.path.exists(os.path.join(dipath,os.path.split(infile)[1])):
                    print("Deleting:", os.path.join(dipath,os.path.split(infile)[1]))
                    os.remove(os.path.join(dipath,os.path.split(infile)[1]))
                print("Retrieving from webdir: ", infile)
                shutil.copy(infile,dipath)
                # Setting permission to defaultuser even if started the job                
                uid = pwd.getpwnam(defaultuser)[2]
                gid = grp.getgrnam(defaultgroup)[2]
                os.chown(os.path.join(dipath,os.path.split(infile)[1]),uid,gid)
                # Deleting file from web dir
                try:
                    os.remove(os.path.join(webdir,os.path.split(infile)[1]))
                except:
                    print("No persmissions to modify webdirectory")
                    pass


    if getremote:
        delete = True
        if keepremote:
            delete = False
        dipath = os.path.join(archive,stationid,'DI','analyze')
        for pier in pierlist:
            if not os.path.exists(dipath):
                os.makedirs(dipath)
            diid = pier + '_' + stationid + '.txt'
            try:
                port = mpcred.lc(remotecred,'port')
            except:
                port = 21
            ftpget(mpcred.lc(remotecred,'address'),mpcred.lc(remotecred,'user'),mpcred.lc(remotecred,'passwd'),remotepath,os.path.join(archive,stationid,'DI','analyze'),diid,port= port, delete=delete)

    print("Variolist", variolist)

    # copy all files from web directory to the analysis folder    

    # -----------------------------------------------------
    # c) analyze all files in the local analysis directory and put successfully analyzed data to raw
    # -----------------------------------------------------
    for pier in pierlist:
        print("######################################################")
        print("Starting analysis for pier ", pier)
        print("######################################################")
        abspath = dipath
        diid = pier + '_' + stationid + '.txt'
        for vario in variolist:
            dataid = variodataidlist[variolist.index(vario)]
            if os.path.exists(os.path.join(archive,stationid,vario,vario+'_'+dataid)):
                variopath = os.path.join(archive,stationid,vario,vario+'_'+dataid,vario+'*')
            else:
                variopath = vario
                if not os.path.exists(variopath):
                    print("No variometerdata found in the specified paths/IDs - using dummy path")
                    variopath = '/tmp/*'
            print("Using Variometerdata at:", variopath)
            for scalar in scalarlist:
                # Define paths for variometer and scalar data
                scalarid = scalardataidlist[scalarlist.index(scalar)]
                if os.path.exists(os.path.join(archive,stationid,scalar,scalar+'_'+scalarid)):
                    scalarpath = os.path.join(archive,stationid,scalar,scalar+'_'+scalarid,scalar+'*')
                else:
                    scalarpath = scalar
                    if not os.path.exists(scalarpath):
                        print("No scalar data found in the specified paths/IDs - using dummy path")
                        scalarpath = '/tmp/*'
                print("Using Scalar data at:", scalarpath)
                # ALPHA and delta needs to be provided with the database
                if db:
                    print("Getting parameter:")
                    alpha =  dbgetfloat(db, 'DATAINFO', vario, 'DataSensorAzimuth')
                    if not isNumber(alpha):
                        alpha = 0.0
                    beta =  dbgetfloat(db, 'DATAINFO', vario, 'DataSensorTilt')
                    if not isNumber(beta):
                        beta = 0.0
                    deltaF =  dbgetfloat(db, 'DATAINFO', scalar, 'DataDeltaF')
                    if not isNumber(deltaF):
                        deltaF = 0.0                    
                else:
                    # eventually add an input option
                    # load a scalar file from path and get delta F from header
                    try:
                        scal = read(scalarpath,starttime=begin,endtime=begin)
                        try:
                            scal = applyDeltas(db,scal)
                            deltaF = 0.0
                        except:
                            deltaF = scal.header['DataDeltaF']
                    except:
                        deltaF = 0.0
                    try:
                        var = read(variopath,starttime=begin,endtime=begin)
                        try:
                            var = applyDeltas(db,var)
                        except:
                            pass
                        alpha = scal.header['DataSensorAzimuth']
                        beta = scal.header['DataSensorTilt']
                    except:
                        alpha = 0.0
                        beta = 0.0
                print("using alpha, beta, deltaF:", alpha, beta, deltaF)
                # Azimuths are usually contained in the DI files
                ## Eventually overriding azimuths in DI files
                if len(azimuthlist) > 0:
                    azimuth = azimuthlist[pierlist.index(pier)]
                    if azimuth == 'False' or azimuth == 'false':
                        azimuth = False
                else:
                    azimuth = False
                if len(abstypelist) > 0:
                    abstype = abstypelist[pierlist.index(pier)]
                    if abstype == 'False' or abstype == 'false':
                        abstype = False
                else:
                    abstype = False
                print("Abolute type:", abstype, abstypelist)


                if createarchive and variolist.index(vario) == len(variolist)-1  and scalarlist.index(scalar) == len(scalarlist)-1:
                    print("adding to archive")
                    absstream = absoluteAnalysis(abspath,variopath,scalarpath,expD=expD,expI=expI, diid=diid,stationid=stationid,abstype=abstype,azimuth=azimuth,pier=pier, alpha=alpha,deltaF=deltaF, starttime=begin,endtime=end, db=db,dbadd=dbadd,compensation=compensation,magrotation=rotation,movetoarchive=os.path.join(archive,stationid,'DI','raw'),deltaD=0.0000000001,deltaI=0.0000000001)
                else:
                    print("just analyzing")
                    absstream = absoluteAnalysis(abspath,variopath,scalarpath,expD=expD,expI=expI, diid=diid,stationid=stationid,abstype=abstype,azimuth=azimuth,pier=pier, alpha=alpha,deltaF=deltaF, starttime=begin,endtime=end, db=db,dbadd=dbadd,compensation=compensation,deltaD=0.0000000001,deltaI=0.0000000001)

		# -----------------------------------------------------
    		# d) write data to a file and sort it, write it again 
                #          (workaround to get sorting correctly)
    		# -----------------------------------------------------
                if absstream and absstream.length()[0] > 0:
                    print("Writing data", absstream.length())
                    absstream.write(os.path.join(archive,stationid,'DI','data'),coverage='all', mode='replace',filenamebegins=identifier+'_'+vario+'_'+scalar+'_'+pier)
                    try:
                        # Reload all data, delete old file and write again to get correct ordering
                        newabsstream = read(os.path.join(archive,stationid,'DI','data',identifier+'_'+vario+'_'+scalar+'_'+pier+'*'))
                        os.remove(os.path.join(archive,stationid,'DI','data',identifier+'_'+vario+'_'+scalar+'_'+pier+'.txt'))# delete file from hd
                        newabsstream.write(os.path.join(archive,stationid,'DI','data'),coverage='all',mode='replace',filenamebegins=identifier+'_'+vario+'_'+scalar+'_'+pier)
                    except:
                        print (" Stream apparently not existing...")
                    print("Stream written - checking for DB")
                    if addBLVdb:
                        # SensorID necessary....
                        print("Now adding data to the data bank")
                        #newabsstream.header["SensorID"] = vario
                        writeDB(db,absstream,tablename=identifier+'_'+vario+'_'+scalar+'_'+pier)
                        #stream2db(db,newabsstream,mode='force',tablename=identifier+'_'+vario+'_'+scalar+'_'+pier) 

        	    # -----------------------------------------------------
        	    # f) get flags and apply them to data
        	    # -----------------------------------------------------
                    if db and flagging:
                        newabsstream = readDB(db,identifier+'_'+vario+'_'+scalar+'_'+pier)
       	                flaglist = db2flaglist(db,identifier+'_'+vario+'_'+scalar+'_'+pier)
                    else:
                        newabsstream = readDB(db,identifier+'_'+vario+'_'+scalar+'_'+pier)
                        flaglist = []
        	    if len(flaglist) > 0:
                        flabsstream = newabsstream.flag(flaglist)
        	        #for i in range(len(flaglist)):
        	        #    flabsstream = newabsstream.flag_stream(flaglist[i][2],flaglist[i][3],flaglist[i][4],flaglist[i][0],flaglist[i][1])
                        flabsstream.write(os.path.join(archive,stationid,'DI','data'),coverage='all',filenamebegins=identifier+'_'+vario+'_'+scalar+'_'+pier)
                        pltabsstream = flabsstream.remove_flagged()

        	    # -----------------------------------------------------
        	    # h) fit baseline and plot
        	    # -----------------------------------------------------
                    try:
                        #pltabsstream = read(os.path.join(archive,stationid,'DI','data',identifier+'_'+vario+'_'+scalar+'_'+pier+'*'))
               	        pltabsstream.trim(starttime=datetime.utcnow()-timedelta(days=380))
        	        # fit baseline using the parameters defined in db (if parameters not available then skip fitting)
        	        #absstream = absstream.fit(['dx','dy','dz'],poly,4)
          	        savename = identifier+'_'+vario+'_'+scalar+'_'+pier+ '.png'
                        #absstream = absstream.extract('f',98999,'<')
        	        mp.plot(pltabsstream,['dx','dy','dz'],symbollist=['o','o','o'],plottitle=vario+'_'+scalar+'_'+pier,outfile=os.path.join(archive,stationid,'DI','graphs',savename))
        	        #absstream.plot(['dx','dy','dz'],symbollist=['o','o','o'],plottitle=vario+'_'+scalar+'_'+pier,outfile=os.path.join(archive,stationid,'DI','graphs',savename))
                    except:
                        pass

    # -----------------------------------------------------
    # j) move files from analyze folder to web folder 
    # -----------------------------------------------------
    # move only if createarchive is selected
    if createarchive:
        print("Dont mind the error message - works only if su at cron is running this job")
        filelst = []
        for infile in iglob(os.path.join(archive,stationid,'DI','analyze','*.txt')):
            print("Processing ", infile)
            filelst.append(infile)
            destination = '/var/www/joomla/images/didaten/'
            infilename = os.path.split(infile)
            print(infilename)
            try:
                shutil.copy(infile, destination)
                #perform changes to privs
                if not webuser == '':
                    uid = pwd.getpwnam(webuser)[2]
                    gid = grp.getgrnam(webgroup)[2]
                    os.chown(os.path.join(destination,infilename[1]),uid,gid)
            except:
                print("Webdir not accesible - finishing")
                pass


    print ("----------------------------------------------------------------")
    print ("di app finished")
    print ("----------------------------------------------------------------")
    print ("SUCCESS")

if __name__ == "__main__":
   main(sys.argv[1:])


