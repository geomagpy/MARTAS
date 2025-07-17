#!/usr/bin/env python
# coding=utf-8

"""
MagPy - Backup and recover

martas_backup -p backup_path  - will create a zipped backup file containing configuration files, crontab inputs,
including info on python version, environment etc

martas_backup -r -p backup_path (or --recover)   -  will recover (plus init, if necessary) a martas stations after
pip install ... will issue warnining if python versions etc is different

TODO
add fstab and ntp.conf
"""

# Define packages to be used (local refers to test environment)
# ------------------------------------------------------------
import shutil
import os
from datetime import datetime

import getopt
from crontab import CronTab
import sys
import platform
import socket
import pathlib

from martas.version import __version__
from martas.core import methods as mm


def backup_files(source_dir, backup_dir):
    """
    DESCRIPTION
        backup configuration files
    """
    # Get the current date and time for naming the backup folder
    current_time = datetime.now().strftime('%Y-%m-%d')
    host = socket.gethostname()

    backup_folder = os.path.join(backup_dir, f"backup_{host}_{current_time}", ".martas")
    try:
        # Create the backup directory
        if not os.path.exists(backup_folder):
            os.makedirs(backup_folder)
        # Copy all files and subdirectories from source to backup folder
        if os.path.exists(backup_folder):
            shutil.rmtree(backup_folder)
        shutil.copytree(source_dir, backup_folder)
        print(f"Backup: Files have been copied to {backup_folder}")
    except Exception as e:
        print(f"Error: {e}")
    return os.path.join(backup_dir, f"backup_{host}_{current_time}")

def save_crontab(backup_folder, cronname="usercron.bak"):
    cronfile = os.path.join(backup_folder, cronname)
    with CronTab(user=True) as cron:
        cron.write(cronfile)

def create_info(backup_folder, martaspath):
    infofile = os.path.join(backup_folder, "README.txt")
    l = []
    l.append("# MARTAS BACKUP - SYSTEM INFORMATION")
    l.append("")
    l.append("MARTAS path: {}".format(martaspath))
    # add python version and environment here
    l.append("Python version: {}".format(sys.version))
    # add info on MARTAS or MARCOS, and main path
    l.append("MARTAS version: {}".format(__version__))
    # operating system
    l.append("Operating system: {} {}".format(platform.system(),platform.release()))
    with open(infofile, 'w') as f:
        for line in l:
            f.write(f"{line}\n")

def read_info(backup_folder):
    infofile = os.path.join(backup_folder, "README.txt")
    martaspath = ""
    with open(infofile, 'r') as f:
        for line in f:
            if line.startswith("MARTAS path: "):
                martaspath = line.replace("MARTAS path: ","").strip()
                print (" Will recover MARTAS directory: ~{} ".format(martaspath))
            if line.startswith("Python version: "):
                bckvers = line.replace("Python version: ","").strip()
                newvers = sys.version
                if not bckvers == newvers:
                    print(" Backup was running on Python {} ".format(bckvers))
                    print(" New system is running Python {} ".format(newvers))
            if line.startswith("MARTAS version: "):
                bckvers = line.replace("MARTAS version: ","").strip()
                newvers = __version__
                if not bckvers == newvers:
                    print(" Backup was running on MARTAS {} ".format(bckvers))
                    print(" New system is running MARTAS {} ".format(newvers))
            if line.startswith("Operating system: "):
                bckvers = line.replace("Operating system: ","").strip()
                newvers = "{} {}".format(platform.system(),platform.release())
                if not bckvers == newvers:
                    print(" Backup was running on {} ".format(bckvers))
                    print(" New system is running {} ".format(newvers))

    return martaspath.lstrip("/")


def recover_populate(homedir, debug=False):
    # recover main folder and crontab
    unpack = '/tmp/recover'
    if debug:
        print (" Debug mode activated - will not update anything")
    writecred = True
    if os.path.isfile(os.path.join(homedir, ".magpycred")):
        writecred = False
        print (" - credentials already existing!")
        print("   CHECK CAREFULLY - ALL EXISTING CONTENTS WILL BE ERASED")
        answer = input("  Replace existing credentials with backup? (y/n) ")
        if answer in ["yes", "y", "Y"] and not debug:
            writecred = True
    if writecred and not debug:
        shutil.copyfile(os.path.join(unpack, ".magpycred"), os.path.join(homedir, ".magpycred"))
    cronbck = os.path.join(unpack, "usercron.bak")
    file_cron = CronTab(tabfile=cronbck)
    if not debug:
        file_cron.write()
    # Remove README, usercron and .magpycred
    cron_to_rem = pathlib.Path(os.path.join(unpack, "usercron.bak"))
    read_to_rem = pathlib.Path(os.path.join(unpack, "README.txt"))
    cred_to_rem = pathlib.Path(os.path.join(unpack, ".magpycred"))
    cron_to_rem.unlink()
    read_to_rem.unlink()
    cred_to_rem.unlink()
    #if os.path.exists(os.path.join(homedir, ".magpycred")):
    bckfolders = next(os.walk(unpack))[1]
    for bckfolder in bckfolders:
        writefolder = True
        dest = os.path.join(homedir, bckfolder)
        source = os.path.join(unpack, bckfolder)
        if os.path.exists(dest):
            writefolder = False
            print (" - MARTAS main folder already existing!")
            print ("   CHECK CAREFULLY - ALL EXISTING CONTENTS WILL BE ERASED")
            answer = input("  Erase existing MARTAS folder and replace with backup? (y/n) ")
            if answer in ["yes","y", "Y"] and not debug:
                writefolder = True
                shutil.rmtree(dest)
        if writefolder and not debug:
            shutil.copytree(source, dest)
    return True



def main(argv):
    version = __version__
    homedir = os.getenv("HOME")
    backuppath = os.path.join(homedir,".martas")
    destpath = "/tmp"
    recoverpath = ''
    debug = False

    try:
        opts, args = getopt.getopt(argv, "hb:d:r:D",
                                   ["backup=", "destination=", "recover=", "debug="])
    except getopt.GetoptError:
        print('martas_backup.py -b <backup> -d <destination> -r <recover>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('-------------------------------------')
            print('Description:')
            print('-- martas_backup.py will backup a MARTAS/MARCOS machine --')
            print('-----------------------------------------------------------------')
            print('detailed description:')
            print(' martas_backup.py creates a backup of configurations and setup.')
            print(' Creating a backup of MARTAS files and configuartions ')
            print(' ... ')
            print(' Recover from backup:')
            print(' ...')
            print('')
            print('-------------------------------------')
            print('Usage:')
            print('python martas_backup.py -c <config>')
            print('-------------------------------------')
            print('Options:')
            print('-b            : backup - path to main dir, i.e. /home/user/.martas')
            print('-d            : destination to write backup to i.e. /home/user/backups')
            print("-r            : recover from backup")
            print('-------------------------------------')
            print('Application:')
            print('  Backup:  python3 martas_backup.py -b /home/user/.martas -d /home/user/backups')
            print('  Recover: python3 martas_backup.py -r /tmp/backup_theia_2025-06-21.zip')
            sys.exit()
        elif opt in ("-b", "--backup"):
            # delete any / at the end of the string
            backuppath = os.path.abspath(arg)
        elif opt in ("-d", "--destination"):
            # delete any / at the end of the string
            destpath = os.path.abspath(arg)
        elif opt in ("-r", "--recover"):
            recoverpath = os.path.abspath(arg)
        elif opt in ("-D", "--debug"):
            # delete any / at the end of the string
            debug = True

    print("Running martas backup version {}".format(version))
    print("--------------------------------")
    if not os.path.exists(destpath):
        os.makedirs(destpath)

    if backuppath and not recoverpath: # default as backuppath is tmp
        print ("Creating backup")
        if not os.path.exists(backuppath):
            print('!! Specify a valid path to the main MARTAS/MARCOS folder !!')
            sys.exit()
        # create a backup folder in tmp
        # copy main directory into the backup folder
        bpath = backup_files(backuppath, destpath)
        # save credential information in folder
        if os.path.isfile(os.path.join(homedir,".magpycred")):
            shutil.copyfile(os.path.join(homedir,".magpycred"), os.path.join(bpath,".magpycred"))
        # save crontab to folder
        save_crontab(bpath)
        # save pythonpath/info in backup readme
        martaspath = backuppath.replace(homedir,"")
        create_info(bpath, martaspath)
        # zip it and move to destination folder
        destination = os.path.join(destpath,os.path.basename(bpath))
        shutil.make_archive(destination, 'zip', bpath)
        shutil.rmtree(bpath)
        print(" backup saved to {}.zip".format(destination))
    elif recoverpath:
        print ("Recovering from backup")
        if not os.path.exists(recoverpath):
            print('!! Specify a valid path to a existing backup !!')
            sys.exit()
        # unpack zip
        shutil.unpack_archive(recoverpath, '/tmp/recover')
        # extract martaspath, pythonpath and info on main MARTAS/MARCOS folder
        # check validity and eventually send warning
        martaspath = read_info('/tmp/recover')
        # extract main folder, crontab and credentials
        recover_populate(homedir, debug=True)
    else:
        print ("No option selected")

    print("martas_backup successfully finished")


if __name__ == "__main__":
    main(sys.argv[1:])

