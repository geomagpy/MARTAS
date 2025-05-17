#!/usr/bin/env python3
# coding=utf-8

"""
IMBOT - automatic analysis of one minute data

imbot_init will create folders, setup all configuration files, eventually install dependencies

"""
import sys
sys.path.insert(1, '/home/leon/Software/magpy/')  # should be magpy2
#sys.path.insert(1, '/home/leon/Software/MARTAS/')  # should be magpy2

import shutil
import getopt
import sys
import os

def main(argv):
    debug = False
    dir = ".martas"

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
            print ('- default directory is .martas, change using -d option, i.e. MARTAS')
            print ('- will create a ~/.martas directory')
            print ('- copy skeleton configuration files to .martas/conf/')
            print ('- copy bash scripts to .martas/scripts/')
            print ('- copy python applications to .martas/app/')
            print ('')
            print ('-------------------------------------')
            print ('Application:')
            print ('-------------------------------------')
            print ('python3 martas_init.py')
            sys.exit()
        elif opt in ("-d", "--directory"):
            dir = arg
        elif opt in ("-D", "--debug"):
            debug = True

    # get home directory of current user
    homedir = os.getenv("HOME")

    import martas
    file_path = os.path.dirname(martas.__file__)
    print(file_path)
    if not debug:
        os.makedirs(os.path.join(homedir,dir), exist_ok=True)
        # create sudirs
        os.makedirs(os.path.join(homedir,dir,"log"), exist_ok=True)
    #
    # copy files into subdirs
    if not os.path.isdir(os.path.join(homedir,dir,"conf")):
        shutil.copytree(os.path.join(file_path, "conf"), os.path.join(homedir, dir, "conf"))
    if not os.path.isdir(os.path.join(homedir,dir,"app")):
        shutil.copytree(os.path.join(file_path, "app"), os.path.join(homedir, dir, "app"))
    if not os.path.isdir(os.path.join(homedir,dir,"telegram")):
        shutil.copytree(os.path.join(file_path, "telegram"), os.path.join(homedir, dir, "telegram"))
    if not os.path.isdir(os.path.join(homedir,dir,"doc")):
        shutil.copytree(os.path.join(file_path, "doc"), os.path.join(homedir, dir, "doc"))
    if not os.path.isdir(os.path.join(homedir,dir,"init")):
        shutil.copytree(os.path.join(file_path, "init"), os.path.join(homedir, dir, "init"))
    if not os.path.isdir(os.path.join(homedir,dir,"install")):
        shutil.copytree(os.path.join(file_path, "install"), os.path.join(homedir, dir, "install"))
    if not os.path.isdir(os.path.join(homedir,dir,"web")):
        shutil.copytree(os.path.join(file_path, "web"), os.path.join(homedir, dir, "web"))
    #shutil.copyfile(os.path.join(file_path, "collector.py"), os.path.join(homedir, dir, "collector.py"))
    #shutil.copyfile(os.path.join(file_path, "acquisition.py"), os.path.join(homedir, dir, "acquisition.py"))
    #
    print ("Now update all the configuration files...")



    print("SUCCESS")  # used for monitoring of logfile
    # end of init

if __name__ == "__main__":
   main(sys.argv[1:])
