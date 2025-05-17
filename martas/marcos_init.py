#!/usr/bin/env python3
# coding=utf-8

"""
IMBOT - automatic analysis of one minute data

imbot_init will create folders, setup all configuration files, eventually install dependencies

"""
import sys
sys.path.insert(1, '/home/leon/Software/magpy/')  # should be magpy2
sys.path.insert(1, '/')  # should be magpy2

import shutil
import getopt
import sys
import os

def main(argv):
    debug = False

    try:
        opts, args = getopt.getopt(argv,"hD",["debug=",])
    except getopt.GetoptError:
        print ('martas_init.py')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print ('-------------------------------------')
            print ('Description:')
            print ('-- martas_init.py will initialize imbot configuration --')
            print ('-----------------------------------------------------------------')
            print ('martas_init.py will perform the following tasks:')
            print ('- create a ~/.martas directory')
            print ('- copy skeleton configuration files to .martas/conf/')
            print ('- copy bash scripts to .martas/scripts/')
            print ('- copy python applications to .martas/app/')
            print ('')
            print ('-------------------------------------')
            print ('Application:')
            print ('-------------------------------------')
            print ('python3 martas_init.py')
            sys.exit()
        elif opt in ("-D", "--debug"):
            debug = True

    # get home directory of current user
    homedir = os.getenv("HOME")
    #print(homedir)
    # create .imbot
    import MARTAS
    file_path = os.path.dirname(MARTAS.__file__)
    #print(file_path)
    if not debug:
        os.makedirs(os.path.join(homedir,".martas"), exist_ok=True)
        # create sudirs
        os.makedirs(os.path.join(homedir,".martas","log"), exist_ok=True)
    #
    # copy files into subdirs
    if not os.path.isdir(os.path.join(homedir,".martas","conf")):
        shutil.copytree(os.path.join(file_path, "conf"), os.path.join(homedir, ".martas", "conf"))
    if not os.path.isdir(os.path.join(homedir,".martas","app")):
        shutil.copytree(os.path.join(file_path, "app"), os.path.join(homedir, ".martas", "app"))
    if not os.path.isdir(os.path.join(homedir,".martas","doc")):
        shutil.copytree(os.path.join(file_path, "doc"), os.path.join(homedir, ".martas", "doc"))
    if not os.path.isdir(os.path.join(homedir,".martas","init")):
        shutil.copytree(os.path.join(file_path, "init"), os.path.join(homedir, ".martas", "init"))
    if not os.path.isdir(os.path.join(homedir,".martas","web")):
        shutil.copytree(os.path.join(file_path, "web"), os.path.join(homedir, ".martas", "web"))
    #
    print ("Now update all the configuration files...")




    print("SUCCESS")  # used for monitoring of logfile
    # end of init

if __name__ == "__main__":
   main(sys.argv[1:])
