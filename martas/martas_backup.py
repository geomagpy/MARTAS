#!/usr/bin/env python
# coding=utf-8

"""
MagPy - Backup and recover

martas_backup -p backup_path  - will create a zipped backup file containing configuration files, crontab inputs,
including info on python version, environment etc

martas_backup -r -p backup_path (or --recover)   -  will recover (plus init, if necessary) a martas stations after
pip install ... will issue warnining if python versions etc is different

"""

# Define packages to be used (local refers to test environment)
# ------------------------------------------------------------
import shutil
import os
from datetime import datetime

import getopt
import socket
import sys

from martas.version import __version__
from martas.core import methods as mm


def backup_files(source_dir, backup_dir):
    """
    DESCRIPTION
        backup configuration files
    """
    # Get the current date and time for naming the backup folder
    current_time = datetime.now().strftime('%Y-%m-%d')
    backup_folder = os.path.join(backup_dir, f"backup_{current_time}", ".martas")
    #try:
    ok = True
    if ok:
        # Create the backup directory
        #os.makedirs(backup_folder)
        # Copy all files and subdirectories from source to backup folder
        shutil.copytree(source_dir, backup_folder)
        print(f"Backup: Files have been copied to {backup_folder}")
    #except Exception as e:
    #    print(f"Error: {e}")


def zip_backup(backup_folder):
    # Get the current date and time for naming the backup folder
    pass


def create_info(backup_folder):
    # add indo on python version and environment here
    # add info on MARTAS or MARCOS, and main path
    pass


def recover_init(backup_folder):
    # run init with main path, type (really necessary?), and defaults
    pass

def recover_populate(backup_folder):
    # recover main folder and crontab
    pass

def main(argv):
    version = __version__
    backuppath = ''
    recoverpath = ''
    debug = False

    try:
        opts, args = getopt.getopt(argv, "hb:r:D",
                                   ["backup=", "recover=", "debug="])
    except getopt.GetoptError:
        print('martas_backup.py -b <backup> -r <recover>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('-------------------------------------')
            print('Description:')
            print('-- martas_backup.py will backup a MARTAS/MARCOS machine --')
            print('-----------------------------------------------------------------')
            print('detailed description:')
            print(' martas_backup.py creates a backup of configurations and setup.')
            print(' Creating a backup:')
            print(' ... ')
            print(' Recover from backup:')
            print(' ...')
            print('')
            print('-------------------------------------')
            print('Usage:')
            print('python martas_backup.py -c <config>')
            print('-------------------------------------')
            print('Options:')
            print('-b            : backup - path to main dir')
            print("-r            : recover from backup")
            print('-------------------------------------')
            print('Application:')
            print(
                'python3 martas_backup.py ')
            sys.exit()
        elif opt in ("-b", "--backup"):
            # delete any / at the end of the string
            backuppath = os.path.abspath(arg)
        elif opt in ("-r", "--recover"):
            recoverpath = os.path.abspath(arg)
        elif opt in ("-D", "--debug"):
            # delete any / at the end of the string
            debug = True

    print("Running martas backup version {}".format(version))
    print("--------------------------------")

    if backuppath:
        if not os.path.exists(backuppath):
            print('!! Specify a valid path to the main MARTAS/MARCOS folder !!')
            sys.exit()
        # create a backup folder in tmp
        # copy main directory into the backup folder
        backup_files(backuppath, "/tmp")
        # save credential information in folder
        # save crontab to folder
        # save pythonpath/info in backup readme

        pass
    elif recoverpath:
        if not os.path.exists(recoverpath):
            print('!! Specify a valid path to a existing backup !!')
            sys.exit()
        # extract pythonpath and info on main MARTAS/MARCOS folder
        # check validity and eventually send warning
        # extract main folder
        # extract crontab
        # extract credentials
        pass
    else:
        print ("No option selected")

    print("martas_backup successfully finished")


if __name__ == "__main__":
    main(sys.argv[1:])

