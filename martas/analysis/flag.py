#!/usr/bin/env python

"""
Methods of the former flagging package to be applied to a MARCOS server

| class       |        method      |  version |  tested  |              comment             | manual | *used by |
| ----------- |  ----------------  |  ------- |  ------- |  ------------------------------- | ------ | -------- |
|  MartasFlag |  __init__          |  2.0.0   |      yes |                                  | -      |          |
|  MartasFlag |  _get_data_from_db |  2.0.0   |      yes |                                  | -      |          |
|  MartasFlag |  update_flags_db   |  2.0.0   |      yes |                                  | -      |          |
|  MartasFlag |  periodically      |  2.0.0   |      yes |                                  | -      |          |
|  MartasFlag |  cleanup           |  2.0.0   |          |                                  | -      |          |
|  MartasFlag |  archive           |  2.0.0   |          |                                  | -      |          |
|  MartasFlag |  create_test_set   |  2.0.0   |      yes |                                  | -      |          |
|  MartasFlag |  upload            |  2.0.0   |          |                                  | -      |          |


DESCRIPTION
   This method can be used to flag data regularly, to clean up the
   existing flagging database, to upload new flags from files and
   to archive "old" flags into json file structures. It is also possible
   to delete flags from the database. The delete method will always save
   a backup before removing flag data.

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


from shutil import copyfile
import itertools
import getopt
import pwd
import socket
import sys  # for sys.version_info()

class MartasFlag(object):
    """
    Methods:

    Application:
        from martas.core import methods as mm
        config = mm.get_conf(conf)
        config = mm.check_conf() # see basevalues
        flagdict = READFLAGDICT
        mf = MartasFlag(config=config, flagdict=flagdict)


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
                                 "mode": ['outlier','ultra'],  # outlier, range, ultra, ai,, mode ultra requires 86402 data points
                                 "samplingrate": 1,
                                "min": -59000,
                                 "max": 50000,
                                 "addflag": True,
                                 "threshold": 4,
                                 "window": 60,
                                 "markall": True,
                                 },
                        'FGE': {"coverage": 7200,
                                 "keys": ['x','y','z'],
                                 "mode": ['outlier'],  # outlier, valuerange, ultra, ai,
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
                                 "mode": ['outlier'],  # outlier, valuerange, ultra, ai,
                                "min": 750,
                                 "max": 1000,
                                 "addflag": True,
                                 "threshold": 4,
                                 "window": 60,
                                 "markall": False,
                                 }
                        }
            """
            flagdict = {'LEMI036': [7200, 'x,y,z', 6, 'Default', True, 'None', 'None'],
                        'LEMI025': [7200, 'x,y,z', 6, 'Default', True, 'None', 'None'],
                        'FGE': [7200, 'x,y,z', 5, 'Default', True, 'None', 'None'],
                        'GSM90_14245': [7200, 'f', 5, 'default', False, 'None', 'None'],
                        'GSM90_6': [7200, 'f', 5, 300, False, 'None', 'None'],
                        'GSM90_3': [7200, 'f', 5, 300, False, 'None', 'None'],
                        'GP20S3NSS2': [7200, 'f', 5, 'Default', False, 'None', 'None'],
                        'POS1': [7200, 'f', 4, 100, False, 'None', 'None'],
                        'BM35': [7200, 'var3', 'None', 'None', False, 750, 1000]}
            """

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
                lastdata = self.db.getlines(sensor, namedict.get('coverage',7200))
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
                    ofl = flagging.flag_outlier(data, keys=group.get('keys',['x','y','z']),threshold=group.get('threshold',4),timerange=group.get('window',60), markall=group.get('markall',False))
                    if len(ofl) > 0:
                        print ("  - found ", len(ofl))
                        newfl = newfl.join(ofl)
                if 'range' in flagmode and len(keys) == 1:
                    # validity range
                    rfl = flagging.flag_range(data,group.get('keys',['x','y','z']),above=group.get('min',-100000),below=group.get('max',100000), labelid='060', operator='MARTAS')
                    if len(rfl) > 0:
                        print ("  - found ", len(rfl))
                        newfl = newfl.join(rfl)
                if 'ultra' in flagmode:
                    print (" Running ultra flagging")
                    # probability flags
                    ufl = flagging.flag_ultra(data,keys=group.get('keys',['x','y','z'])) #), factordict={}, mode="xxx")
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


    def cleanup(self, starttime=None, endtime=None, debug=False):
        """
        DESCRIPTION
            Read all flags and clean them up
            - extract all flags
            - apply union
            - remove all flags from db
            - write cleaned data set
        """
        print(" Cleaning up all records")
        cumflag = []
        stream = DataStream()
        flaglist = self.db.flags_from_db()
        if debug:
            print("   -> Found {} flags in database".format(len(flaglist)))
            print(" --------------------------------------")
            flaglist.stats(intensive=True)
            print(" --------------------------------------")
        flaglist = flaglist.union(level=0)
        if debug:
            print("   -> cleaned record contains {} flags".format(len(flaglist)))
            print(" --------------------------------------")
            flaglist.stats(intensive=True)
            print(" --------------------------------------")
        return flaglist


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


    def create_test_set(self, debug=False):
        data = read(example1)
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
        data.header["DataID"] = "TEST001_1234_0001_0001"
        data.header["SensorID"] = "TEST001_1234_0001"
        self.db.write(data)
        if debug:
            print(" successfully written test data TEST001 to database")
        return True


class TestFlagging(unittest.TestCase):

    def test_get_data_from_db(self):
        res = {}
        mf = MartasFlag()
        #mf.db.flags_to_delete(parameter="sensorid", value="TEST001_1234_0001")
        #mf.create_test_set(debug=True)
        for elem in mf.flagdict:
            if elem == "TEST":
                res = mf._get_data_from_db(elem, starttime=datetime.now()-timedelta(days=1), endtime=datetime.now(), debug=True)
        self.assertTrue(res)

    def test_periodically(self):
        mf = MartasFlag()
        fl = mf.periodically(debug=True)
        self.assertGreater(len(fl),1)

    def test_update_flags_db(self):
        mf = MartasFlag()
        fl = mf.periodically(debug=False)
        print ("Writing flags to DB", len(fl))
        suc = mf.update_flags_db(fl, debug=True)
        print(fl.flagdict)
        self.assertTrue(suc)


if __name__ == "__main__":
    unittest.main(verbosity=2)