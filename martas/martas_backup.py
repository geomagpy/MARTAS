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


def backup_files(source_dir, backup_dir):
    """
    DESCRIPTION
        backup configuration files
    """
    # Get the current date and time for naming the backup folder
    current_time = datetime.now().strftime('%Y-%m-%d')
    backup_folder = os.path.join(backup_dir, f"backup_{current_time}")
    try:
        # Create the backup directory
        os.makedirs(backup_folder)
        # Copy all files and subdirectories from source to backup folder
        shutil.copytree(source_dir, backup_folder)
        print(f"Backup: Files have been copied to {backup_folder}")
    except Exception as e:
        print(f"Error: {e}")


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
