#!/usr/bin/env python

"""
Methods of this module

| class           |        method      |  version |  tested  |              comment             | manual | *used by |
| --------------- |  ----------------  |  ------- |  ------- |  ------------------------------- | ------ | -------- |
|  MartasAnalysis |  __init__          |  2.0.0   |      yes |                                  | -      |          |
|  MartasAnalysis |  _get_data_from_db |  2.0.0   |      yes |                                  | -      |          |
|  MartasAnalysis |  update_flags_db   |  2.0.0   |      yes |                                  | -      |          |
|  MartasAnalysis |  periodically      |  2.0.0   |      yes |                                  | -      |          |
|  MartasAnalysis |  cleanup           |  2.0.0   |          |                                  | -      |          |
|  MartasAnalysis |  archive           |  2.0.0   |          |                                  | -      |          |
|  MartasAnalysis |  create_test_set   |  2.0.0   |      yes |                                  | -      |          |
|  MartasAnalysis |  upload            |  2.0.0   |          |                                  | -      |          |
|  MartasAnalysis |  get_primary       |  2.0.0   |      yes |                                  | -      |          |
|  MartasAnalysis |  get_baseline_functions | 2.0.0 |    yes |                                  | -      |          |
|  MartasAnalysis |  adjust_scalar     |  2.0.0   |      yes |                                  | -      |          |
|  MartasAnalysis |  adjust_vario      |  2.0.0   |      yes |                                  | -      |          |
|  MartasAnalysis |  magnetism_products |  2.0.0  |          |                                  | -      |          |
|  MartasStatus   |  __init__          |  2.0.0   |      yes |                                  | -      |          |
|  MartasStatus   |  read_data         |  2.0.0   |      yes |                                  | -      |          |
|  MartasStatus   |  check_highs       |  2.0.0   |      yes |                                  | -      |          |
|  MartasStatus   |  create_sql        |  2.0.0   |      yes |                                  | -      |          |
|  MartasStatus   |  statustableinit   |  2.0.0   |      yes |                                  | -      |          |



PREREQUISITES
   The following packages are required:
      geomagpy >= 2.0.8
      martas >= 2.0.0

APPICATION
   used by the cobsanalysis package, which contains the Observatory specific application

PARAMETERS
    flagdict          :  dict       :  currently hardcoded into the method
            { SensorNamePart : 
              [timerange, keys, threshold, window, markall, lowlimit, highlimit]
    -c configurationfile   :   file    :  too be read from GetConf2 (martas)
    -j joblist             :   list    :  jobs to be performed - default "flag"
                                          (flag, clean, upload, archive, delete)
    -e endtime             :   date    :  date until analysis is performed
                                          default "datetime.utcnow()"
    -p path                :   string  :  upload - path to upload directory
    -s sensor              :   string  :  delete - sensor of which data is deleted 
    -o comment             :   string  :  delete - flag comment for data sets to be deleted

APPLICATION
    PERMANENT with cron:
        python flagging.py -c /etc/marcos/analysis.cfg
    YEARLY with cron:
        python flagging.py -c /etc/marcos/analysis.cfg -j archive
    DAILY with cron:
        python flagging.py -c /etc/marcos/analysis.cfg -j upload,clean -p /srv/archive/flags/uploads/
    REDO:
        python flagging.py -c /etc/marcos/analysis.cfg -e 2020-11-22
    DELETE data with comment:
        python flagging.py -c /etc/marcos/analysis.cfg -j delete -s MYSENSORID -o "my strange comment"
    DELETE data for FlagID Number (e.g. all automatic flags):
        python flagging.py -c /etc/marcos/analysis.cfg -j delete -s MYSENSORID -o "1"
    DELETE data all flags for key "f":
        python flagging.py -c /etc/marcos/analysis.cfg -j delete -s MYSENSORID -o "f"

"""
import sys
sys.path.insert(1,'/home/leon/Software/MARTAS/') # should be magpy2

import unittest

from magpy.stream import *
from magpy.core import database
from magpy.core import methods
from magpy.core import flagging
#import magpy.opt.cred as mpcred

from martas.version import __version__
from martas.core.methods import martaslog as ml
from martas.core import methods as mm
from martas.core import definitive


from shutil import copyfile
import itertools
import getopt
import pwd
import socket
import sys  # for sys.version_info()

class MartasAnalysis(object):
    """
    DESCRIPTION
        This method can be used to flag data regularly, to clean up the
        existing flagging database, to upload new flags from files and
        to archive "old" flags into json file structures. It is also possible
        to delete flags from the database. The delete method will always save
        a backup before removing flag data.

    Methods:

    Application:
        from martas.core import methods as mm
        from martas.core import analysis
        from martas.core import definitive
        config = mm.get_conf(conf)
        config = mm.check_conf() # see basevalues

        mf = analysis.MartasAnalysis(config=config, flagdict=flagdict)

        # flagging
        fl = mf.periodically(debug=True)
        suc = mf.update_flags_db(fl, debug=True)

        # primary
        p = mf.get_primary()

        # adjusted data
        v = mf.get_primary() # vario
        s = mf.get_primary() # scalar
        config['vainstlist'] = [v]
        config['scinstlist'] = [s]
        config['primarypier'] = 'A2'
        config['blvabb'] = 'BLV'
        rot = definitive.variocorr('adjusted', config=config, flagfile=None)

    """
    def __init__(self, config=None, flagdict=None):
        if not config:
            config = {'dbcredentials' : 'cobsdb'}
        if not flagdict:
            flagdict = {'LEMI' :  {"coverage" : 7200,
                                      "keys" : ['x','y','z'],
                                      "samplingrate" : 1,
                                      "mode" : ['ultra'], # outlier, valuerange, ultra, ai,
                                      "min" : 750,
                                      "max" : 1000,
                                      "addflag" : True,
                                      "threshold" : 4,
                                      "window" : 60,
                                      "markall": True,
                                      },
                        'TEST': {"coverage": 86500,
                                 "keys": ['x','y','z'],
                                 #"mode": ['outlier'],  # outlier, range, ultra, ai,
                                 "mode": ['outlier'],  # outlier, range, ultra, ai,, mode ultra requires 86402 data points
                                 "samplingrate": 1,
                                 "groups": {"T001" : ['x','y'], "T002" : ['f']},
                                 "min": -59000,
                                 "max": 50000,
                                 "addflag": True,
                                 "threshold": 4,
                                 "window": 60,
                                 "markall": True,
                                 },
                        'FGE': {"coverage": 7200,
                                 "keys": ['x','y','z'],
                                 "mode": ['outlier'],  # outlier, range, ultra, ai,
                                "samplingrate": 1,
                                "min": 750,
                                 "max": 1000,
                                 "addflag": True,
                                 "threshold": 4,
                                 "window": 60,
                                 "markall": True,
                                 },
                        'GSM': {"coverage": 7200,
                                 "keys": ['f'],
                                 "mode": ['outlier'],  # outlier, range, ultra, ai,
                                "min": 750,
                                 "max": 1000,
                                 "addflag": True,
                                 "threshold": 4,
                                 "window": 60,
                                 "markall": False,
                                 },
                        'GP20S3NS_': {"coverage": 7200,
                                 "keys": ['x,y,z,dx,dy,dz'],
                                 "mode": ['outlier'],  # outlier, range, ultra, ai,
                                 "samplingrate": 1,
                                 "addflag": True,
                                 "groups": {"GP20S3NSS1" : ['f'], "GP20S3NSS2" : ['f'], "GP20S3NSS3" : ['f']},
                                 "threshold": 5,
                                 "window": 60,
                                 "markall": False,
                                 "groups" : {},
                                 },
                        'POS1': {"coverage": 7200,
                                 "keys": ['f'],
                                 "mode": ['outlier'],  # outlier, range, ultra, ai,
                                 "addflag": True,
                                 "threshold": 4,
                                 "window": 60,
                                 "markall": False,
                                 },
                        'BM35': {"coverage": 7200,
                                 "keys": ['var3'],
                                 "mode": ['range'],  # outlier, range, ultra, ai,
                                 "min": 750,
                                 "max": 1000,
                                 "addflag": True,
                                 "markall": False,
                                 }
                        }

        self.config = mm.check_conf(config, debug=True)
        self.flagdict = flagdict

        self.logpath = self.config.get('logpath')
        self.receiver = self.config.get('notification')
        self.receiverconf = self.config.get('notificationconf')
        self.db = self.config.get('primaryDB')
        self.source = 'db' # db, file

    def _get_data_from_db(self, name, starttime=None, endtime=None, debug=False):
        """
        DESCRIPTION
            Extract data sets from database based on name fraction provided in flagdict.
        RETURN
            datadict : dictionary like {"DataID" : {"data": stream, "":"", ...}}
        """
        datadict = {}
        determinesr = []
        namedict = self.flagdict.get(name)
        # First get all existing sensors comaptible with name fraction
        sensorlist = self.db.select('DataID', 'DATAINFO', 'SensorID LIKE "%{}%"'.format(name))
        if debug:
            print("   -> Found {}".format(sensorlist))
            print("   a) select 1 second or highest resolution data")  # should be tested later again
        # Now get corresponding sampling rate
        projected_sr = namedict.get("samplingrate", 0)
        for sensor in sensorlist:
            sr = 0
            res = self.db.select('DataSamplingrate', 'DATAINFO', 'DataID="{}"'.format(sensor))
            try:
                sr = float(res[0])
                if debug:
                    print("    - Sensor: {} -> Samplingrate: {}".format(sensor, sr))
            except:
                if debug:
                    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                    print("Check sampling rate {} of {}".format(res, sensor))
                    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                determinesr.append(sensor)
            if projected_sr and methods.is_number(projected_sr):
                # if sr is similar to projected sr within 0.02 sec
                if np.abs(sr-projected_sr) <= 0.02:
                    cont = {}
                    cont['samplingrate'] = sr
                    datadict[sensor] = cont
            elif projected_sr == "HF":
                if sr < 0.58:
                    cont = {}
                    cont['samplingrate'] = sr
                    datadict[sensor] = cont
            else:
                # if no samplingrate is projected search for sr's above 1 second
                if sr >= 1:
                    cont = {}
                    cont['samplingrate'] = sr
                    datadict[sensor] = cont
        if len(determinesr) > 0:
            if debug:
                print("   b) checking sampling rate of {} }sensors without sampling rate".format(len(determinesr)))
            for sensor in determinesr:
                lastdata = self.db.get_lines(sensor, namedict.get('coverage',7200))
                if len(lastdata) > 0:
                    sr = lastdata.samplingrate()
                    if debug:
                        print("    - Sensor: {} -> Samplingrate: {}".format(sensor, sr))
                    # update samplingrate in db
                    print("    - updating header with determined sampling rate:", lastdata.header)
                    self.db.write(lastdata)
                    if projected_sr and methods.is_number(projected_sr):
                        # if sr is similar to projected sr within 0.02 sec
                        if np.abs(sr - projected_sr) <= 0.02:
                            cont = {}
                            cont['samplingrate'] = sr
                            datadict[sensor] = cont
                    elif projected_sr == "HF":
                        if sr < 0.58:
                            cont = {}
                            cont['samplingrate'] = sr
                            datadict[sensor] = cont
                    else:
                        # if no samplingrate is projected search for sr's above 1 second
                        if sr >= 1:
                            cont = {}
                            cont['samplingrate'] = sr
                            datadict[sensor] = cont
        if debug:
            print ("   -> {} data sets fulfilling search criteria after a and b".format(len(datadict)))
        if starttime or endtime:
            newdatadict = {}
            if debug:
                print("   c) Check for exiting data in requested time frame")
            for dataid in datadict:
                cont = datadict.get(dataid)
                data = self.db.read(dataid, starttime=starttime, endtime=endtime)
                if debug:
                    print ("   Found {} datapoints for {}".format(len(data), dataid))
                if len(data) > 0:
                    cont['data'] = data
                    newdatadict[dataid] = cont
            datadict = newdatadict

        return datadict


    def update_flags_db(self, flags, debug=False):
        success = True
        connectdict = self.config.get('conncetedDB')
        if len(flags) > 0:
            for dbel in connectdict:
                dbt = connectdict[dbel]
                if debug:
                    print("  -- New flags: {}".format(len(flags)))
                    out = flags.stats(level=0, intensive=True, output=None)
                    print(out)
                try:
                    dbt.flags_to_db(flags)
                except:
                    success = False
        return success


    def cleanup(self, splitter=None, part=2, level=0, debug=False):
        """
        DESCRIPTION
            Method which should be called periodically to union the flagging data base.
            This will load all data from the database, split the database by the the given date,
            apply union to one part, recombine, delete all data from the db and upload the new recombined
            data set.
        PARAMETERS:
            splitter : date like "2025-07-01"
            part : which part should be unified, default is the latter
        APPLICATION:
            flag_union()
        """
        success = True
        if not splitter:
            splitter = datetime.strftime(datetime.now(timezone.utc)-timedelta(days=10), "%Y-%m-%d")
        connectdict = self.config.get('conncetedDB')
        if debug:
            print ("Splitting database at ", splitter)
        for dbel in connectdict:
            dbt = connectdict[dbel]
            fl1 = dbt.flags_from_db(endtime=splitter)
            fl2 = dbt.flags_from_db(starttime=splitter)
            if part == 1:
                fl1 = fl1.union(level=level)
            else:
                fl2 = fl2.union(level=level)
            fl = fl1.join(fl2)
            if fl and len(fl)>0:
                dbt.flags_to_delete('all')
                dbt.flags_to_db(fl)
                if debug:
                    out = fl.stats(level=0, intensive=True, output=None)
                    print(out)
            else:
                success = False
        return success


    def periodically(self, debug=False):
        """
        DESCRIPTION
            periodic method to investigate recent data and obtain new flags
        """
        newflags = flagging.Flags()
        for elem in self.flagdict:
            datadict = {}
            dropexist = False
            newfl = flagging.Flags()
            if debug:
                print (" -------------------------------------------")
                print (" Dealing with sensorgroup which starts with {}".format(elem))
                print (" -------------------------------------------")
            # select flagging mode
            group = self.flagdict.get(elem)
            flagmode = group.get('mode')
            coverage = group.get('coverage',7200)
            flaggroup = group.get('groups',{})
            endtime = datetime.now(timezone.utc).replace(tzinfo=None)
            starttime= endtime-timedelta(seconds=coverage)
            # select the corresponding data sources
            if self.source == 'db':
                datadict = self._get_data_from_db(elem, starttime=starttime, endtime=endtime, debug=debug)
            else:
                print ("to be done - get_data_from_files")
                datadict = {}
            # run the flagging procedure
            for dataid in datadict:
                # get existing flags
                cont = datadict.get(dataid)
                data = cont.get('data')
                existfl = self.db.flags_from_db(dataid[:-5], starttime=starttime, endtime=endtime )
                if existfl:
                    print (" Got existing flags:",len(existfl))
                if debug:
                    print (" Running flag mode:", flagmode)
                if dropexist and existfl:
                    data = existfl.apply_flags(data, mode='drop')
                if 'outlier' in flagmode:
                    # simple despiking
                    print (" Running outlier flagging")
                    ofl = flagging.flag_outlier(data, keys=group.get('keys',['x','y','z']),threshold=group.get('threshold',4),timerange=group.get('window',60), markall=group.get('markall',False), groups=flaggroup)
                    if len(ofl) > 0:
                        print ("  - found ", len(ofl))
                        newfl = newfl.join(ofl)
                if 'range' in flagmode:
                    # validity range
                    rfl = flagging.flag_range(data,group.get('keys',['x','y','z']),above=group.get('min',-100000),below=group.get('max',100000), labelid='060', operator='MARTAS', groups=flaggroup)
                    if len(rfl) > 0:
                        print ("  - found ", len(rfl))
                        newfl = newfl.join(rfl)
                if 'ultra' in flagmode:
                    print (" Running ultra flagging")
                    # probability flags
                    ufl = flagging.flag_ultra(data,keys=group.get('keys',['x','y','z'])) #), factordict={}, mode="xxx", group=flaggroup)
                    if len(ufl) > 0:
                        print ("  - found ", len(ufl))
                        newfl = newfl.join(ufl)
                if flagmode == 'ai':
                    # artificial intelligence flags
                    print (" this is not yet included")
                print(" -> RESULT: found {} new flags".format(len(newfl)))
                if debug:
                    print (" Lengths: existing = {}, new = {}".format(len(existfl), len(newfl)))
                if existfl:
                    newfl = existfl.join(newfl)
                newfl = newfl.union(samplingrate=cont.get("samplingrate",0), level=1)
                if debug:
                    print (" Lengths after union: new = {}".format(len(newfl)))
                if newfl:
                    newflags = newflags.join(newfl)

        return newflags


    def archive(self):
        pass


    def upload(self, flagfilepath):
        """
        DESCRIPTION
            Upload flagging lists from files
        """
        filelist = []
        newfl = flagging.Flags()
        print (" Searching for new flagging files")
        for fi in os.listdir(flagfilepath):
            if fi.endswith("flags.json") or fi.endswith("flags.pkl"):
                print ("   -> found: {}".format(os.path.join(flagfilepath, fi)))
                filelist.append(os.path.join(flagfilepath, fi))
        if len(filelist) > 0:
            for fi in filelist:
                fileflaglist = flagging.load(fi)
                if len(fileflaglist) > 0:
                    print(" - Loaded {} flags from file {}".format(len(fileflaglist),fi))
                    # get all flags from DB
                    newfl = fileflaglist.join(newfl)
        return newfl


    def create_test_set(self, dataset=None, sensorid="TEST001_1234_0001", debug=False):
        if not dataset:
            dataset = example1
        data = read(dataset)
        newt = []
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        # replace time column
        if debug:
            print (" create_test:set: length of example file={}".format(len(data)))
        start = now - timedelta(seconds=len(data))
        s = datetime(start.year, start.month, start.day, start.hour, start.minute, start.second)
        for i in range(0,len(data)):
            nt = s + timedelta(seconds=i)
            newt.append(nt)
        newt = np.asarray(newt)
        data = data._put_column(newt,'time')
        if debug:
            print (" replacing timerange with current:", data.timerange())
        data.header["DataID"] = "{}_0001".format(sensorid)
        data.header["SensorID"] = sensorid
        self.db.write(data)
        if debug:
            print(" successfully written test data {} to database".format(sensorid))
        return True


    def get_primary(self, dataids, coverage=86400, endtime=None, starttolerance=3600, endtolerance=82800, valuerange=None, debug=False):
        """
        DESCRIPTION
            Checks all variometers and scalar sensors as defined in a configuration file.
            The first instrument in the list, which fulfills criteria on data availablility
            will be selected as primary instrument. Both primary instruments will be stored
            within a current.data json structure.
            VARIABLES
                instlist : a list with DataIDs from similar instruments of which primary is selected
                coverage : requested data coverage of primary instrument
                endtime : the endtime to be reached by data from the instrument, default = utcnow
                starttolerance : accepted difference from endtime
                endtolerance : accepted difference from start of the sequence
                valuerange : i.e. {'x': [-40,100]} the mean value needs to be within this range
            Identify currently active variometer and f-instrument, which are recording now and have at least one day of data
        """
        if not isinstance(dataids,(list,tuple)) and not len(dataids) > 0:
            return ''
        primaryinst = ''
        if not endtime:
            endtime = datetime.now(timezone.utc).replace(tzinfo=None)
        foundprimary=False
        ## Step 1: checking available data for variometers (need to cover one day and should not be older than one hour
        ##         the first instrument fitting these conditions is selected
        for inst in dataids:
            if not foundprimary:
                if debug:
                    print ("  Primary data set: checking ", inst)
                last = self.db.get_lines(inst,coverage)
                #last = db.select(db,'time',inst,expert="ORDER BY time DESC LIMIT 86400")
                if len(last) > 0:
                    # convert last to datetime
                    firstval, lastval = last.timerange()
                    if debug:
                        print ("    -- Time range check:", firstval, lastval)
                    if lastval > endtime-timedelta(seconds=starttolerance) and firstval < endtime-timedelta(seconds=endtolerance):
                        if debug:
                            print ("    -- Coverage OK of {}".format(inst))
                        if valuerange and isinstance(valuerange, dict):
                            fine = True
                            for key in valuerange:
                                m = last.mean(key)
                                print (key, m)
                                r = valuerange[key]
                                if not r[0] <= m <= r[1]:
                                    fine = False
                            if fine:
                                if debug:
                                    print("    -- Valuerange OK of {}".format(inst))
                                primaryinst = inst
                                foundprimary = True
                        else:
                            primaryinst = inst
                            foundprimary = True
                    else:
                        print ("    -- Coverage not OK")
        if not foundprimary:
            print("    -- none of the instruments fullfills the primary criteria - using first: {}".format(dataids[0]))
            primaryinst = dataids[0]
        print ("  -> Selected: {}".format(primaryinst))

        return primaryinst

    def magnetism_data_product(self, runmode, prim_v, prim_s, starttime=None, endtime=None, debug=False):
        """
        DESCRIPTION
            runmode can be variation, adjusted or quasidefinitive
            Requires config and a primary variometer
        REQUIRED INFO:
            eventually in config:
                flagginginfo - file
                skipsec in case of one-sec res
        PARAMETER:
            prim_v : primary variometer
            prim_s : primary scalar

        APPLICATION
            # adjusted
            get_primary
            merged = magnetism_data_products('adjusted)
            res = merged.get('merge')
            for sr in res:
                export_data


            export_data(merged
            destination: {'file' : path}, or {'db' : cred}
        """
        vario = {}
        scalar = {}
        result = {}
        final = {}
        base = self.config.get("base",'')
        station = self.config.get("obscode",'')
        if not station:
            station = self.config.get("station",'')
        prim_p = self.config.get('primarypier','A2')
        basetype =  self.config.get('blvabb','BLV')
        basename = "{}_{}_{}_{}.txt".format(basetype,prim_v[:-5],prim_s[:-5],prim_p)
        print (" - suggested name of the basevalue file:", basename)
        basefile = os.path.join(os.path.join(base,'archive',station.upper(),'DI','data',basename))
        publevel = 1
        # Obtain pat to baseline data, always use one year of baseline data
        baseend = datetime.now(timezone.utc).replace(tzinfo=None)
        basestart = baseend - timedelta(days=380)
        if debug:
            print (" still need to extract the baseline data")
        if runmode == 'adjusted':
            publevel = 2
            variosource = {'db' : prim_v}
            scalarsource = {'db' : prim_s}
            vario = self.adjust_vario(variosource, basemode='constant', flagfile=None, drop_flagged=True, bc=True,
                                      basefile=basefile, basestart=basestart, baseend=baseend, debug=debug)
            scalar = self.adjust_scalar(scalarsource, flagfile=None, debug=debug)
        elif runmode == 'quasidefinitive':
            # Check if new flags are available since last run (or whether data has been checked by an observer)
            publevel = 3
            variosource = {'file' : os.path.join(base,prim_v[:-5],prim_v)}
            scalarsource = {'file' : os.path.join(base,prim_s[:-5],prim_s)}
            vario = self.adjust_vario(variosource, basemode='function', starttime=starttime, endtime=endtime, flagfile=None, drop_flagged=True, bc=True,
                                      basefile=basefile, basestart=basestart, baseend=baseend, debug=debug)
            scalar = self.adjust_scalar(scalarsource, starttime=starttime, endtime=endtime, flagfile=None, debug=debug)
        elif runmode == 'firstrun':
            # Maybe for the future
            publevel = 4
            variosource = {'file' : os.path.join(base,prim_v[:-5],prim_v)}
            scalarsource = {'file' : os.path.join(base,prim_s[:-5],prim_s)}
            vario = self.adjust_vario(variosource, basemode='constant', flagfile=None, drop_flagged=True, bc=True,
                                      basefile="/tmp/abs.cdf", basestart=basestart, baseend=baseend)
            scalar = self.adjust_scalar(scalarsource, flagfile=None )
            final['vario'] = vario
            final['scalar'] = scalar
            return final

        # merge vario and scalar
        for sr in vario:
            ref = 'sec'
            if sr > 58:
                ref = 'min'
            va = vario.get(sr)
            sc = scalar.get(sr)
            me = merge_streams(va,sc)
            #Rotate into XYZ
            if not va.header.get("DataComponents").startswith("XYZ") and not va.header.get("DataComponents").startswith("xyz"):
                me = me.hdz2xyz()
            me.header['SensorID'] = '{}_{}{}_0001'.format(station.upper(),runmode,ref)
            me.header['DataID'] = '{}_{}{}_0001_0001'.format(station.upper(),runmode,ref)
            me.header['DataPublicationLevel'] = publevel
            result[sr] = me
        final['merge'] = result

        return final

    def get_baseline_functions(self, datastream, absdata, basestart, baseend, mode='constant', debug=False):
        """
        DRESCRIPTION
            Obtain baseline parameters from database and apply. If they don't exist use mean
        """

        funclist = []
        # What about a baseline jump i.e. two or more baseline fits ?
        # get timeranges and baseline fit parameters from database
        absdata = absdata.trim(starttime=basestart, endtime=baseend)
        print(" - getting baseline fit parameter from database")
        ett = methods.testtime(baseend)

        while ett > methods.testtime(basestart):
            print (datastream.header.get('SensorID'), ett)
            basedict = self.db.get_baseline(datastream.header.get('SensorID', ''), date=ett)
            if debug:
                print(" - got baseline boundary conditions from DB:", basedict)
            # get the latest (highest ID) input of the basedictionary
            ids = [int(basein) for basein in basedict]
            if len(ids) > 0:
                latestbaseind = max(ids)
                baseinput = basedict.get(latestbaseind, {})
                bstart = baseinput.get("MinTime", "1777-04-30")
                bend = baseinput.get("MaxTime", "2223-04-30")
                if methods.testtime(bstart) < methods.testtime(basestart):
                    stt = basestart
                else:
                    stt = methods.testtime(bstart).strftime("%Y-%m-%d")
                if methods.testtime(bend) > methods.testtime(baseend):
                    ett = baseend
                else:
                    ett = methods.testtime(bend).strftime("%Y-%m-%d")
                fu = baseinput.get("BaseFunction", 'mean')
                kn = baseinput.get("BaseKnots", '0.3')
                de = baseinput.get("BaseDegree", '1')
            else:
                fu = 'mean'
                kn = 0.3
                de = 1
                stt = basestart
                ett = baseend
                bstart = basestart
            print(" => Adding fit with typ {}, knots {}, degree {} between {} and {}".format(fu, float(kn), float(de),
                                                                                             stt, ett))
            try:
                funclist.append(
                    datastream.baseline(absdata, extradays=0, fitfunc=fu, knotstep=float(kn), fitdegree=float(de), startabs=stt,
                                endabs=ett))
                print(" => Done")
            except:
                print(" => Failed to add baseline parameters")
            ett = methods.testtime(bstart) - timedelta(days=1)

        return datastream, funclist

    def adjust_vario(self, source, basemode='constant', starttime=None, endtime=None, flagfile=None, basefile=None, basestart=None, baseend=None, drop_flagged=False, bc=False, skipsec=False, debug=False):
        """
        DESCRIPTION
            obtain corrected scalar data
            TODO: eventually combine with definitive.scalaracorr
        PARAMETER:
            source: {'file' : pscalar}, or {'db' : pscalar}
            basemode: 'constant' or 'function', function requires an existing baseline table in DB
                      'constant' : determines median baseline for the selected baseline data, flagged data is dropped from vario and basedata
                                   data is returned in baseline corrected state
                      'function' :
            drop_flagged: False - if True flags are dropped before returning
            bs: False - if True baseline correcteion is applied to function mode data
                      for adjusted and QD data drop_flagged and bc should be True
        """
        result = {}
        va = DataStream()
        ff = flagging.Flags()
        fl = flagging.Flags()
        if not endtime:
            endtime = datetime.now(timezone.utc).replace(tzinfo=None)
        else:
            endtime = methods.testtime(endtime)
        if not starttime:
            starttime = endtime -timedelta(days=2)
        else:
            starttime = methods.testtime(starttime)

        addflags_to_header = True

        diflagfile= self.config.get('diflagfile', '')
        year = endtime.year

        rotangledict = {}
        if debug:
            print (" ----------------------------------------- ")
            print (" ------- Adjusting variometer data ------- ")
            print (" ----------------------------------------- ")
            print (" - get data source: {}".format(source))
        for key in source:
            if key == 'db':
                va = self.db.read(source.get(key,''), starttime=starttime, endtime=endtime)
            elif key == 'file':
                # file data will erase db data in case of two sources
                va = read(source.get(key,''), starttime=starttime, endtime=endtime)

        if debug:
            print(" - using {} variometer data from {}".format(len(va), va.header.get("DataID")))
            print(" - dealing with data between {} and {}".format(starttime, endtime))
        if not va or not len(va) > 0:
            print(" - no data found - skipping vario")
            return DataStream()

        if len(va) > 0:
            if debug:
                print (" - MEANS: {},{},{}".format(va.mean("x"),va.mean("y"),va.mean("z")))
            dhead = self.db.fields_to_dict(va.header.get("DataID"))
            if dhead:
                va.header = dhead
            if debug:
                print (" - removing duplicates")
            bef = va.length()[0]
            va = va.removeduplicates()
            aft = va.length()[0]
            if debug:
                print ("   -> dropped {} duplicate values".format(bef-aft))
            if debug:
                print (" - filling gaps")
            va = va.get_gaps()
            if debug:
                print (" - flagging")
            vaflagsdropped = False
            fl = self.db.flags_from_db(va.header['SensorID'], starttime=starttime, endtime=endtime)
            if debug:
                print("    loaded {} flags from DB for this time range".format(len(fl)))
            #  --b. add flaglist from file
            ff = flagging.load(flagfile, begin=starttime, end=endtime)
            if debug:
                print("    loaded {} flags from file in time range {} to {}".format(len(ff), starttime, endtime))
            if len(fl) > 0 and len(ff) > 0:
                fl = fl.join(ff)
            elif not len(fl) > 0:
                fl = ff
            if debug:
                print ("   -> found a sum of {} flags".format(len(fl)))
                print ("   -> applying {} flags".format(len(fl)))
            if addflags_to_header:
                va.header["DataFlags"] = fl # will be kept until second data is saved
            if debug:
                print ("   MEANS: {},{},{}".format(va.mean("x"),va.mean("y"),va.mean("z")))
            if debug:
                print(" - applying compensation values")
            va = va.compensation(skipdelta=True)
            if debug:
                print ("   MEANS: {},{},{}".format(va.mean("x"),va.mean("y"),va.mean("z")))
            if debug:
                print(" - applying delta values")
            va = va.apply_deltas()
            if debug:
                print(" - rotation values ...")   ### should be done after removal of flags....
            rotstring = va.header.get('DataRotationAlpha','')
            rotdict = string2dict(rotstring,typ='oldlist')
            if debug:
                print (" - existing rotation angle alpha for {}: {}".format(str(year), rotdict.get(str(year),'')))
            betastring = va.header.get('DataRotationBeta','')
            betadict = string2dict(betastring,typ='oldlist')
            if debug:
                print (" - existing rotation angle beta for {}: {}".format(str(year), betadict.get(str(year),'')))
            if basemode == 'constant' or rotdict.get(str(year),0) == 0:
                print (" - run with constant baseline: Rotation value will be determined")
                print ("    - need to drop flagged data now...")
                if fl and not vaflagsdropped:
                    va = fl.apply_flags(va, mode='drop')
                    va.header['DataFlags'] = None
                    vaflagsdropped = True
                print (" - getting rotation angle - please note: correct beta determination requires DI data for reference inclination")
                alpha, beta, gamma = va.determine_rotationangles(referenceD=0.0, referenceI=None)
                rotangle = alpha
                print ("    Determined rotation angle alpha for {}: {}".format(va.header.get('SensorID'),rotangle))
                print ("    !!! Please note: These  new rotation angles are not yet applied.")
                print ("                     update DB in order to consider those ")
            ### IMPORTTANT: if BLVcomp is found in BLV file then rotate wit the last existing rotation angles
            if "BLVcomp_" in basefile:
                alpha = 0
                beta = 0
                gamma = 0
                if rotdict:
                    yl = [y for y in rotdict]
                    if len(yl) > 0:
                        maxyear = max(yl)
                        alpha = float(rotdict.get(maxyear, '0.0'))
                        print("  Found BLVcomp in baseline: Using rotation angle alpha={} from last determination in {}".format(alpha, maxyear))
                if betadict:
                    yl = [y for y in betadict]
                    if len(yl) > 0:
                        maxyear = max(yl)
                        beta = float(betadict.get(maxyear,'0.0'))
                        print("  Found BLVcomp in baseline: Using rotation angle beta={} from last determination in {}".format(beta, maxyear))
                if debug:
                    print("  Applying rotation now - please note: gamma is currently ignored")
                # Only apply full year values - as baseline calc uses them as well
                va = va.rotation(alpha=alpha, beta=beta, gamma=gamma)
                if debug:
                    print("  -> Done")
            orgva = va.copy()

            if debug:
                print ("   MEANS: {},{},{}".format(va.mean("x"),va.mean("y"),va.mean("z")))

            basevaluefile = basefile
            if debug:
                print (" - applying baseline file: {}".format(basevaluefile))
            if basefile and os.path.isfile(basefile):
                absr = read(basefile)
                print (" - flagging baseline ...")
                flaglist = absr.header.get("DataFlags")
                if flaglist:
                    print("   -> dropping {} flags in baseline file".format(len(flaglist)))
                    absr = flaglist.apply_flags(absr, mode='drop')
                if debug:
                    print ("   Basevalue SensorID:", absr.header.get('SensorID'))
                    print ("    -- Dropping basedata flags from DB")
                blvflaglist = self.db.flags_from_db(absr.header.get('SensorID'))
                if debug:
                    print ("    -> {} flags".format(len(blvflaglist)))
                if blvflaglist:
                    absr = blvflaglist.apply_flags(absr, mode='drop')
                if debug:
                    print ("    -- Dropping basedata flags from file: {}".format(diflagfile))
                fiflaglist = flagging.load( diflagfile, sensorid=absr.header.get('SensorID'))
                if debug:
                    print ("    -> {} flags".format(len(fiflaglist)))
                if fiflaglist:
                    absr = fiflaglist.apply_flags(absr, mode='drop')

                basestarttime, baseendtime = absr.timerange()
                if basestart:
                    basestarttime = methods.testtime(basestart)
                if baseend:
                    baseendtime = methods.testtime(baseend)

                if debug:
                    print(" - getting baseline fit parameters/jumps from database")
                    print("   and extract all baseline interruptions for the requested baseline timerange")

                if basemode in ['constant']:
                    print (" - constant baseline approach")
                    if fl and not vaflagsdropped:
                        if debug:
                            print("  Baseline adoption: dropping flagged data")
                        va = fl.apply_flags(va, mode='drop')
                        va.header["DataFlags"] = None
                        vaflagsdropped = True
                    va = va.get_gaps()

                    #### GET CONSTANT BASEVALUE
                    #TODO get baseline for one year if no jumps are listed in db
                    absr = absr.trim(starttime=basestarttime,endtime=baseendtime)

                    if debug:
                        print ("  -> remaining DI measurements: ", absr.length())
                    absr = absr._drop_nans('dx')
                    bh, bhstd = absr.mean('dx',meanfunction='median',std=True)
                    bd, bdstd = absr.mean('dy',meanfunction='median',std=True)
                    bz, bzstd = absr.mean('dz',meanfunction='median',std=True)

                    if debug:
                        print ("   Basevalues for {}:".format(year))
                        print ("   Delta H = {a} +/- {b}".format(a=bh, b=bhstd))
                        print ("   Delta D = {a} +/- {b}".format(a=bd, b=bdstd))
                        print ("   Delta Z = {a} +/- {b}".format(a=bz, b=bzstd))

                    print (" - performing constant basevalue correction")
                    va = va.simplebasevalue2stream([bh,bd,bz])
                    hva = va.copy()
                    sr = hva.samplingrate()
                    result[sr] = hva
                    if debug:
                        print("   MEANS: {},{},{}".format(va.mean("x"), va.mean("y"), va.mean("z")))

                    if debug:
                        print (" - filtering variometer data")
                    va = va.filter(missingdata='mean')
                    va = va.get_gaps()
                    if debug:
                        print (" - length after gaps removal (min):", len(va))
                    sr = va.samplingrate()
                    result[sr] = va

                    return result

                else:
                    if debug:
                        print (" - functional baseline approach")
                    va, funclist = self.get_baseline_functions(va, absr, basestarttime, baseendtime, debug=debug)

                    # apply correction?
                    if bc:
                        va = va.bc()
                    print (" - absInfo in stream: {}".format(va.header.get('DataAbsInfo')))
                    if debug:
                        print("   MEANS: {},{},{}".format(va.mean("x"), va.mean("y"), va.mean("z")))

                    sr = va.samplingrate()
                    if 0.8 < sr < 58 and not skipsec:
                        hva = va.copy()
                        #if not basemode in ['constant']:
                        #    print ("  Updating rotation information...")
                        #    update_rot(hva,year,rotangle, beta) ## new 2017
                        if drop_flagged and fl and not vaflagsdropped:
                            hva = fl.apply_flags(hva, mode='drop')
                            vaflagsdropped = True
                            va.header["DataFlags"] = None
                        result[sr] = hva

                    print(" - remove, gaps and filter:", va.length()[0])
                    if fl and not vaflagsdropped:
                        va = fl.apply_flags(va, mode='drop')
                        vaflagsdropped = True
                    if drop_flagged:
                        va.header["DataFlags"] = None
                    va = va.get_gaps()
                    va = va.filter(missingdata='mean')
                    va = va.get_gaps()
                    sr = va.samplingrate()
                    result[sr] = va

                if debug:
                    print ("   -> absolute data has now been loaded and applied")
                    print (" - final step: determining suspected euler rotation")
                    print ("   -> get reference inclination for the specific data from absolute data")
                redabsr = absr.trim(starttime=basestarttime,endtime=baseendtime)
                meanI = redabsr.mean('x')
                if debug:
                    print ("  Mean inclination in abs data = {}".format(meanI))
                alpha, beta, gamma = orgva.determine_rotationangles(referenceI=meanI)

                if rotangledict.get(va.header.get("DataID"),[]) == []:
                    rotangledict[va.header.get("DataID")] = [[alpha,beta]]
                else:
                    rotangledict[va.header.get("DataID")].append([alpha,beta])
                print ("Rotation angle dictionary:", rotangledict)

            else:
                print (" adjust_varion : failed because basevalue file is not existing")

            return result



    def adjust_scalar(self, source, starttime=None, endtime=None, flagfile=None, skipsec=False, debug=False):
        """
        DESCRIPTION
            obtain corrected scalar data
            TODO: eventually combine with definitive.scalaracorr
        PARAMETER:
            source: {'file' : pscalar}, or {'db' : pscalar}
            #destination: {'file' : path}, or {'db' : cred}
        """
        result = {}
        ff = flagging.Flags()
        fl = flagging.Flags()
        if not endtime:
            endtime = datetime.now(timezone.utc).replace(tzinfo=None)
        if not starttime:
            starttime = endtime -timedelta(days=2)
        addflags_to_header = False
        if debug:
            print (" ----------------------------------------- ")
            print (" --- Adjusting scalar data --- ")
            print (" ----------------------------------------- ")
            print (" - get data source: {}".format(source))
        for key in source:
            if key == 'db':
                sc = self.db.read(source.get(key,''), starttime=starttime, endtime=endtime)
            elif key == 'file':
                # file data will erase db data in case of two sources
                sc = read(source.get(key,''), starttime=starttime, endtime=endtime)

        if debug:
            print (" - using {} scalar data from {}".format(len(sc), sc.header.get("DataID")))
            print (" - dealing with data between {} and {}".format(starttime,endtime))
        if not sc or not len(sc) > 0:
            print (" - no data found - skipping scalar")
            return DataStream()
        bef = sc.length()[0]
        sc = sc.removeduplicates()
        aft = sc.length()[0]
        if debug:
            print ("  -> dropped {} duplicate values".format(bef-aft))
        if sc.length()[0] > 1:
            if debug:
                print (" - getting gaps and data base meta info:")
            sc = sc.get_gaps()
            sc.header = self.db.fields_to_dict(sc.header.get('DataID'))
            if debug:
                print (" - flagging with existing flags")
                print ("   a) from DB:")
            fl = self.db.flags_from_db(sc.header.get('SensorID'), starttime=starttime, endtime=endtime) #data.header['SensorID'])
            if debug:
                print ("    -> length of DB flaglist: {}".format(len(fl)))
            if flagfile:
                if debug:
                    print ("   b) from file:")
                if os.path.isfile(flagfile):
                    ff = flagging.load(flagfile, begin=starttime, end=endtime)
                    if debug:
                        print("    -> loaded {} flags from file {} in the time range {} to {}".format(len(ff), flagfile, starttime, endtime))
            if len(fl) > 0 and len(ff) > 0:
                fl = fl.join(ff)
            elif not len(fl) > 0:
                fl = ff
            if debug:
                print("  -> found a sum of {} flags".format(len(fl)))
            if addflags_to_header:
                sc.header["DataFlags"] = fl
            if fl:
                if debug:
                    print(" - removing flagged data before applying deltas and time shifting")
                sc = fl.apply_flags(sc, mode='drop')
                sc.header["DataFlags"] = None
                if debug:
                    print ("   -> done")
            if debug:
                print (" - applying offsets and timeshifts")
            sc = sc.apply_deltas()
            sc = sc.removeduplicates()
            if debug:
                print ("  -> final length: {}".format(sc.length()[0]))
                print(" - dropping all columns except f".format(sc.length()[0]))
            for el in DataStream().KEYLIST:
                if not el in ['time', 'f']:
                    sc = sc._drop_column(el)
            sr = sc.samplingrate()
            if 0.8 < sr < 58 and not skipsec:
                hsc = sc.copy()
                if debug:
                    print (" - adding high resolution data to result")
                result[sr] = hsc
            if 0.8 < sr < 58:
                if debug:
                    print (" - filtering")
                sc = sc.filter(missingdata='mean')
                if debug:
                    print (" - filling gaps with nan")
                sc = sc.get_gaps()
                sr = sc.samplingrate()
                result[sr] = sc
        if debug:
            print("adjust_scalar: done")
        return result


class MartasStatus(object):
    def __init__(self, config=None, statusdict=None, tablename='COBSSTATUS'):
        if not config:
            config = {'dbcredentials' : 'cobsdb'}
        if not statusdict:
            statusdict = {"Average field X": {
                                "source": "TEST001_1234_0001_0001",
                                "key": "x",
                                "type": "temperature",
                                "group": "tunnel condition",
                                "field": "environment",
                                "location": "gmo",
                                "pierid": "",
                                "range": 30,
                                "mode": "mean",
                                "value_unit": "°C",
                                "warning_high": 10,
                                "critical_high": 20
                                }
                        }

        self.config = mm.check_conf(config, debug=True)
        self.statusdict = statusdict
        self.tablename = tablename

        self.logpath = self.config.get('logpath')
        self.receiver = self.config.get('notification')
        self.receiverconf = self.config.get('notificationconf')
        self.db = self.config.get('primaryDB')


    def read_data(self, statuselem=None, endtime=None, debug=False):
        """
        DESCRIPTION
            Read date for a certain table, a given key and timerange from the database.
            Calculate the parameter as defined by mode.
        PARAMETER:
            source
        RETURN
            Returns the calculated parameter and an active bool (0: no data available or problem with calc; 1: everything fine)
        """
        if not statuselem:
            statuselem = {}
        if not endtime:
            endtime = datetime.now(timezone.utc).replace(tzinfo=None)
        ndata = DataStream()
        source = statuselem.get('source','')
        key = statuselem.get('key','x')
        trange = statuselem.get('trange', 30)
        mode = statuselem.get('mode',"mean")
        result = {}
        active = 0
        value = 0
        value_min = 0
        value_max = 0
        uncert = 0
        starttime = endtime - timedelta(minutes=trange)
        newendtime = endtime  # will be changes for mode "last"
        ok = True
        if ok:
            # check what happens if no data is present or no valid data is found
            if source.find('/') > -1:
                if debug:
                    print("Reading data: found path or url:", source, starttime, endtime)
                try:
                    fdata = read(source, starttime=starttime, endtime=endtime)
                except:
                    if debug:
                        print("Just try to load at least the current day")
                    fbdate = endtime.strftime("%Y-%m-%d")
                    source = source.replace("*", "*" + fbdate)
                    fdata = read(source)
                if debug:
                    print(" - found {} datapoints".format(fdata.length()[0]))
                ndata = fdata._drop_nans(key)
                if debug:
                    print(" - dropped nans -> remaining datapoints: {}".format(ndata.length()[0]))
                cleandata = ndata._get_column(key)
                if debug:
                    print(" - got key", key)
                    # print (fdata.ndarray[0])
                if debug:
                    print(" - Done")
            else:
                if debug:
                    print("Reading data: accessing database table")
                ddata = self.db.read(source, starttime=starttime, endtime=endtime)
                if debug and len(ddata) > 0:
                    print(" -> reading done: got {} datapoints for {}".format(len(ddata), key))
                ndata = ddata._drop_nans(key)
                cleandata = ndata._get_column(key)
            newendtime = ndata.end()
            if debug:
                print(" -> {} datapoints remaining after cleaning NaN".format(len(cleandata)))
                #print("Cleandata", cleandata)
            if len(cleandata) > 0 and not isnan(cleandata[0]):
                value_min = np.min(cleandata)
                value_max = np.max(cleandata)
                uncert = np.std(cleandata)
                if mode == "median":
                    value = np.median(cleandata)
                elif mode == "min":
                    value = value_min
                elif mode == "max":
                    value = value_max
                elif mode == "std":
                    value = np.std(cleandata)
                elif mode == "last":  # if mode.startswith(last) allow last1, last2 etc
                    value = cleandata[-1]
                    endtime = newendtime
                else:  # mode == mean
                    value = np.mean(cleandata)
                active = 1

        result['mode'] = mode
        result['value'] = value
        result['min'] = value_min
        result['max'] = value_max
        result['uncert'] = uncert
        result['starttime'] = starttime
        result['endtime'] = endtime
        result['longitude'] = ndata.header.get('DataLocationLongitude',0.0)
        result['latitude'] = ndata.header.get('DataLocationLongitude',0.0)
        result['altitude'] = ndata.header.get('DataElevation',0.0)
        result['active'] = active
        result["type"] = ndata.header.get("SensorType","")
        result["group"] = ndata.header.get("SensorGroup","")
        result["value_unit"] =  ndata.header.get("unit-col-{}".format(key),"")
        result["stationid"] = ndata.header.get("StationID","")
        result["pierid"] = ndata.header.get("PierID","")
        if debug:
            print("DEBUG: returning value={}, starttime={}, endtime={} and active={}".format(value, starttime, endtime,
                                                                                             active))

        return result


    def check_highs(self, value, statuselem=None):
        """
        DESCRIPTION
            test value for warning levels
        """
        if not statuselem:
            statuselem = {}
        value_unit = statuselem.get('value_unit','')
        warning_high = statuselem.get('warning_high',0)
        critical_high = statuselem.get('critical_high',0)
        warning_low = statuselem.get('warning_low',0)
        critical_low = statuselem.get('critical_low',0)
        msg = ''
        if value:
            if critical_high and value >= critical_high:
                msg = "CRITCAL STATUS: value exceeding {} {}".format(critical_high, value_unit)
            elif warning_high and value >= warning_high:
                msg = "WARNING: value exceeding {} {}".format(warning_high, value_unit)
            elif critical_low and value <= critical_low:
                msg = "CRITICAL STATUS: value below {} {}".format(critical_low, value_unit)
            elif warning_low and value <= warning_low:
                msg = "WARNING: value below {} {}".format(warning_low, value_unit)
        return msg


    def create_sql(self, notation, res=None, statuselem=None):
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if not statuselem:
            statuselem = {}
        if not res:
            res = {}
        value = res.get('value')
        value_min = res.get('min')
        value_max = res.get('max')
        uncert = res.get('uncert')
        start = res.get('starttime')
        end = res.get('endtime')
        active = res.get('active')
        long = res.get('longitude')
        lat = res.get('latitude')
        alt = res.get('altitude')
        stype = statuselem.get("type", res.get('typ'))
        group = statuselem.get("group", res.get('group'))
        field = statuselem.get("field", "")
        value_unit = statuselem.get("value_unit", res.get('value_unit'))
        warning_high = statuselem.get("warning_high", 0)
        critical_high = statuselem.get("critical_high", 0)
        warning_low = statuselem.get("warning_low", 0)
        critical_low = statuselem.get("critical_low", 0)
        source = statuselem.get("source", "")
        stationid = statuselem.get("stationid", res.get('stationid'))
        pierid = statuselem.get("pierid", res.get('pierid'))
        comment = statuselem.get("comment", "")
        sql = "INSERT INTO {} (status_notation,status_type,status_group,status_field,status_value,value_min,value_max,value_std,value_unit,warning_high,critical_high,warning_low,critical_low,validity_start,validity_end,source,stationid,pierid,longitude,latitude,altitude,comment,date_added,active) VALUES ('{}','{}','{}','{}',{},{},{},{},'{}',{},{},{},{},'{}','{}','{}','{}','{}',{},{},{},'{}','{}',{}) ON DUPLICATE KEY UPDATE status_type = '{}',status_group = '{}',status_field = '{}',status_value = {},value_min = {},value_max = {},value_std = {},value_unit = '{}',warning_high = {},critical_high = {},warning_low = {},critical_low = {},validity_start = '{}',validity_end = '{}',source = '{}',stationid = '{}',pierid = '{}',longitude = {},latitude = {},altitude = {},comment='{}',date_added = '{}',active = {} ".format(
            self.tablename, notation, stype, group, field, value, value_min, value_max, uncert, value_unit, warning_high, critical_high,
            warning_low, critical_low, start, end, source, stationid, pierid, long, lat, alt, comment, now, active, stype, group, field, value,
            value_min, value_max, uncert, value_unit, warning_high, critical_high, warning_low, critical_low, start,
            end, source, stationid, pierid, long, lat, alt, comment, now, active)
        return sql


    def statustableinit(self, debug=False):
        """
        DESCRIPTION
            creating a STATUS Database table
        """
        columns = ['status_notation', 'status_type', 'status_group', 'status_field', 'status_value', 'value_min',
                   'value_max', 'value_std', 'value_unit', 'warning_high', 'critical_high', 'warning_low',
                   'critical_low', 'validity_start', 'validity_end', 'stationid', 'pierid', 'latitude', 'longitude', 'altitude', 'source',
                   'comment', 'date_added', 'active']
        coldef = ['CHAR(100)', 'TEXT', 'TEXT', 'TEXT', 'FLOAT', 'FLOAT', 'FLOAT', 'FLOAT', 'TEXT', 'FLOAT', 'FLOAT',
                  'FLOAT', 'FLOAT', 'DATETIME', 'DATETIME', 'TEXT', 'TEXT', 'FLOAT', 'FLOAT', 'FLOAT', 'TEXT', 'TEXT', 'DATETIME', 'INT']
        fulllist = []
        for i, elem in enumerate(columns):
            newelem = '{} {}'.format(elem, coldef[i])
            fulllist.append(newelem)
        sqlstr = ', '.join(fulllist)
        sqlstr = sqlstr.replace('status_notation CHAR(100)', 'status_notation CHAR(100) NOT NULL UNIQUE PRIMARY KEY')
        createtablesql = "CREATE TABLE IF NOT EXISTS {} ({})".format(self.tablename, sqlstr)
        return createtablesql


class TestAnalysis(unittest.TestCase):

    def test_aaa(self):
        print ("----------------------------------")
        print ("Creating tests data sets")
        mf = MartasAnalysis()
        # delete any existing flags
        mf.db.flags_to_delete(parameter="sensorid", value="TEST001_1234_0001")
        # create a test data set in DB
        mf.create_test_set(dataset=example1, sensorid="TEST001_1234_0001", debug=True)

    def test_get_data_from_db(self):
        res = {}
        mf = MartasAnalysis()
        for elem in mf.flagdict:
            if elem == "TEST":
                res = mf._get_data_from_db(elem, starttime=datetime.now()-timedelta(days=1), endtime=datetime.now(), debug=True)
        self.assertTrue(res)

    def test_periodically(self):
        mf = MartasAnalysis()
        fl = mf.periodically(debug=True)
        self.assertGreater(len(fl),1)

    def test_update_flags_db(self):
        mf = MartasAnalysis()
        fl = mf.periodically(debug=False)
        print ("Writing flags to DB", len(fl))
        suc = mf.update_flags_db(fl, debug=True)
        #print(fl.flagdict)
        self.assertTrue(suc)

    def test_zcleanup(self):
        mf = MartasAnalysis()
        fl = mf.cleanup(debug=True)
        self.assertGreater(len(fl),1)

    def test_get_primary(self):
        mf = MartasAnalysis()
        mf.create_test_set(dataset=example3, sensorid="TEST002_1234_0001", debug=False)
        dataids = ['TEST002_1234_0001_0001','TEST003_1234_0001_0001','TEST001_1234_0001_0001']
        vr = {'x': [10000,30000], 'y':[-4000,4000]}
        p = mf.get_primary(dataids, coverage=86400, endtime=None, starttolerance=3600, endtolerance=82800, valuerange=vr, debug=True)
        print ("Primary:", p)
        self.assertEqual(p,'TEST001_1234_0001_0001')

    def test_adjust_scalar(self):
        import importlib.resources as importlib_resources
        mf = MartasAnalysis()
        mf.create_test_set(dataset=example2, sensorid="TEST003_1234_0001", debug=True)
        dataids = ['TEST003_1234_0001_0001','TEST001_1234_0001_0001']
        s = mf.get_primary(dataids, valuerange={'f': [40000,50000]}) # scalar
        res = mf.adjust_scalar({'db':s})
        self.assertGreater(len(res.get(1.0)),80000)

    def test_adjust_vario(self):
        import importlib.resources as importlib_resources
        mf = MartasAnalysis()
        d = read(example1)
        st, et = d.timerange()
        a = read(example3)
        d.write("/tmp", filenamebegins="test", format_type='PYCDF', coverage='all')
        a.write("/tmp", filenamebegins="abs", format_type='PYCDF', coverage='all')
        #res = mf.adjust_vario({'file':"/tmp/test.cdf"}, basemode='constant', starttime=st, endtime=et, flagfile=None, drop_flagged=True, bc=True, basefile="/tmp/abs.cdf",
        #             skipsec=False, debug=True)
        res = mf.adjust_vario({'file':"/tmp/test.cdf"}, basemode='functions', starttime=st, endtime=et,
                              flagfile=None, drop_flagged=True, bc=True, basefile="/tmp/abs.cdf", skipsec=False,
                              debug=True)
        print (res)

    def test_get_baseline_functions(self):
        vario = read(example1)
        # test with and without existing baseline table
        #vario.header['SensorID'] = "LEMI036_1_0002"
        #vario.header['DataID'] = "LEMI036_1_0002_0002"
        basedata = read(example3)
        st, et = basedata.timerange()
        mf = MartasAnalysis()
        print("   MEANS: {},{},{}".format(vario.mean("x"), vario.mean("y"), vario.mean("z")))
        vario, func = mf.get_baseline_functions(vario, basedata, st, et, debug=True)
        vario = vario.bc()
        self.assertGreater(len(func), 0)
        print("   MEANS: {},{},{}".format(vario.mean("x"), vario.mean("y"), vario.mean("z")))
        self.assertLess(vario.mean("y"),5)


class TestStatus(unittest.TestCase):

    def test_read_data(self):
        #statusdict = mm.get_json(statusfile)
        #ms = MartasStatus(config=config, statusdict=statusdict,tablename='COBSSTATUS')
        statusdict = {"Average field X": {
            "source": "TEST001_1234_0001_0001",
            "key": "x",
            "type": "temperature",
            "field": "environment",
            "range": 30,
            "mode": "mean",
            "value_unit": "°C",
            "warning_high": 10,
            "critical_high": 20}
        }
        ms = MartasStatus(statusdict=statusdict, tablename='COBSSTATUS')
        initsql = ms.statustableinit(debug=True)
        sqllist = []
        for elem in ms.statusdict:
            statuselem = ms.statusdict.get(elem)
            res = ms.read_data(statuselem=statuselem,debug=True)
            warnmsg = ms.check_highs(res.get('value'), statuselem=statuselem)
            newsql = ms.create_sql(elem, res, statuselem)
            print (warnmsg)
            sqllist.append(newsql)
        #initsql = ms.statustableinit(debug=True)
        sql = "; ".join(sqllist)

        md = ms.db
        cursor = ms.db.db.cursor()
        message = md._executesql(cursor, initsql)
        for el in sqllist:
            message = md._executesql(cursor, el)
        md.db.commit()
        self.assertGreater(len(sqllist), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)