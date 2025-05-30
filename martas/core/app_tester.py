#!/usr/bin/env python
# coding=utf-8

"""
Testing module for methods from apps
"""

import unittest

import sys
sys.path.insert(1,'/home/leon/Software/MARTAS/') # should be magpy2

import os
import numpy as np
from magpy.stream import DataStream
from magpy.core import database
from magpy.opt import cred as mpcred

from datetime import datetime, timedelta
from martas.core import methods as mameth

from martas.app import archive
from martas.app import checkdatainfo
from martas.app import db_truncate
from martas.app import filter
from martas.app import threshold


def create_teststream(startdate=datetime(2022, 11, 22)):
    teststream = DataStream()
    array = [[] for el in DataStream().KEYLIST]
    array[1] = [20000] * 720
    array[1].extend([22000] * 720)
    array[1] = np.asarray(array[1])
    array[2] = np.asarray([0] * 1440)
    array[3] = np.asarray([20000] * 1440)
    array[6] = np.asarray([np.nan] * 1440)
    # array[4] = np.sqrt((x*x) + (y*y) + (z*z))
    array[0] = np.asarray([startdate + timedelta(minutes=i) for i in range(0, len(array[1]))])
    rain1 = np.arange(1,721,1.0)
    rain2 = np.arange(1,361,0.5)
    rain = np.concatenate((rain1, rain2))
    array[7] = rain
    array[DataStream().KEYLIST.index('sectime')] = np.asarray(
        [startdate + timedelta(minutes=i) for i in range(0, len(array[1]))]) + timedelta(minutes=15)
    teststream = DataStream(header={'SensorID': 'Test_0002_0001'}, ndarray=np.asarray(array, dtype=object))
    teststream.header['col-x'] = 'X'
    teststream.header['col-y'] = 'Y'
    teststream.header['col-z'] = 'Z'
    teststream.header['col-t2'] = 'Text'
    teststream.header['col-var1'] = 'Rain'
    teststream.header['unit-col-x'] = 'nT'
    teststream.header['unit-col-y'] = 'nT'
    teststream.header['unit-col-z'] = 'nT'
    teststream.header['unit-col-t2'] = 'degC'
    teststream.header['unit-col-var1'] = 'mm'
    teststream.header['DataComponents'] = 'XYZ'
    return teststream

class TestArchive(unittest.TestCase):
    """
    Test environment for all methods
    """

    def test_create_datelist(self):
        dl = archive.create_datelist(startdate='', depth=10, debug=True)
        self.assertEqual(len(dl), 10)

    #def test_create_data_selectionlist(self):
    #    dt = archive.create_data_selectionlist(blacklist=None, debug=False)
    #    self.assertEqual(ar[1],11)

    #def test_get_data_dictionary(self):
    #    cfg = archive.get_data_dictionary(db,sql,debug=False)
    #    self.assertEqual(cfg.get("station"),"myhome")

    #def test_get_parameter(self):
    #    sens = archive.get_parameter(plist, debug=False)
    #    self.assertEqual(sens,[])

    #def test_validtimerange(self):
    #    archive.validtimerange(timetuple, mintime, maxtime, debug=False)


class TestCheckdataInfo(unittest.TestCase):
    """
    Test environment for all methods
    """
    def test_add_datainfo(self):
        #add_datainfo(db, tableonly=None, verbose=False, debug=False)
        pass


    def test_obtain_datainfo(self):
        #xxx = obtain_datainfo(db, blacklist=None, verbose=False, debug=False)
        pass

    def test_match(self):
        #match(first, second)
        pass

    def test_match(self):
        #get_tables(db, identifier="*_00??", verbose=False, debug=False)
        pass

    def test_matchtest(self):
        #matchtest(identifier, string)
        pass


class TestDBTrcuncate(unittest.TestCase):

    def test_query_db(self):
        #query_db(db, sql, debug=False)
        pass

    def test_get_table_tist(self):
        #get_table_tist(db, sensorlist=None, blacklist=None, debug=False)
        pass


class TestFilter(unittest.TestCase):
    """
    Test environment for all methods
    """

    def test_read_conf(self):
        cfg = filter.read_conf("config/filter.cfg")
        self.assertNotEqual(cfg,None)

    def test_get_delta(self):
        #self.assertEqual(cmod, "updated but already accepted")
        #self.assertFalse(modres)
        pass

    def test_get_sensors(self):
        recent = True
        dd = filter.read_conf("../conf/filter.cfg")
        groupparameterdict = dd.get('groupparameterdict')
        blacklist = dd.get('blacklist')
        basics = dd.get('basics')
        recentthreshold = int(basics.get('recentthreshold', 7200))
        self.assertEqual(recentthreshold,7200)
        credentials = 'cobsdb'
        db = database.DataBank(host=mpcred.lc(credentials, 'host'), user=mpcred.lc(credentials, 'user'),
                                   password=mpcred.lc(credentials, 'passwd'), database=mpcred.lc(credentials, 'db'))
        highreslst = filter.get_sensors(db=db,groupdict=groupparameterdict,samprate='HF', blacklist=blacklist, recent=recent, recentthreshold=recentthreshold, debug=True)
        print ("Donw:", highreslst)

    def test_one_second_filter(self):
        sensorlist = []
        basepath = '/srv/archive'
        destination = 'db'
        credentials = 'cobsdb'
        dd = filter.read_conf("../conf/filter.cfg")
        groupparameterdict = dd.get('groupparameterdict')
        blacklist = dd.get('blacklist')
        permanent = dd.get('permanent')
        basics = dd.get('basics')
        outputformat = basics.get('outputformat')
        recentthreshold = int(basics.get('recentthreshold', 7200))
        db = database.DataBank(host=mpcred.lc(credentials, 'host'), user=mpcred.lc(credentials, 'user'),
                                   password=mpcred.lc(credentials, 'passwd'), database=mpcred.lc(credentials, 'db'))
        statusmsg = filter.one_second_filter(db, statusmsg={}, groupdict=groupparameterdict, permanent=permanent, blacklist=blacklist, jobtype='realtime', endtime=datetime.now(), dayrange=2, dbinputsensors=sensorlist, basepath=basepath, destination=destination, outputformat=outputformat, recentthreshold=recentthreshold, debug=True)
        print ("HERE")
        statusmsg = filter.one_second_filter(db, statusmsg={}, groupdict=groupparameterdict, permanent=permanent, blacklist=blacklist, jobtype='archive', endtime=datetime.now(), dayrange=2, dbinputsensors=sensorlist, basepath=basepath, destination=destination, outputformat=outputformat, recentthreshold=recentthreshold, debug=True)
        print ("Done")

class TestThreshold(unittest.TestCase):

    def test_assign_parameterlist(self):
        conf = mameth.get_conf(os.path.join('..', 'conf', 'threshold.cfg'))
        para = threshold.assign_parameterlist(threshold.sp.valuenamelist, conf)
        self.assertTrue(para.get('1'))

    def test_get_data(self):
        (dat1,msg1) = threshold.get_data('file', "/tmp/archive/LEMI036_3_0001", "dbcredentials", "LEMI036_3_0001", 1000, startdate=None, debug=True)
        (dat2,msg2) = threshold.get_data('db', "path", "cobsdb", "LEMI036_3_0001", 1000, startdate=None, debug=True)
        self.assertTrue(msg1)

    def test_get_test_value_check_threshold(self):
        data = create_teststream()
        (testvalue, msg2) = threshold.get_test_value(data, key='x', function='average', debug=True)
        self.assertEqual(testvalue, 21000)
        (evaluate, msg) = threshold.check_threshold(testvalue, 20000, "above", debug=True)
        self.assertTrue(evaluate)


    def test_interprete_status(self):
        conf = mameth.get_conf(os.path.join('..', 'conf', 'threshold.cfg'))
        para = threshold.assign_parameterlist(threshold.sp.valuenamelist, conf)
        valuedict = para.get('1', {})
        xxx = threshold.interprete_status(valuedict, debug=True)
        self.assertEqual(xxx, "Current average below 5")


if __name__ == "__main__":
    unittest.main(verbosity=2)