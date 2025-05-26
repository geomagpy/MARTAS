#!/usr/bin/env python
# coding=utf-8

"""
Testing module for methods from apps
"""

import unittest

from martas.app import archive



class TestArchive(unittest.TestCase):
    """
    Test environment for all methods
    """

    def test_create_datelist(self):
        dl = archive.create_datelist(startdate='', depth=10, debug=True)
        print (dl, len(dl))
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

    def test_testbool(self):
        val = archive.testbool("TRUE")
        self.assertTrue(val)

    #def test_validtimerange(self):
    #    archive.validtimerange(timetuple, mintime, maxtime, debug=False)



if __name__ == "__main__":
    unittest.main(verbosity=2)