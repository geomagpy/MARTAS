#!/bin/bash

# cp /etc/martas to tmp
# cp /etc/marcos to tmp
# cat crontabs to tmp
# check for SCRIPTS directory and README in home
# cp that to tmp
# compress the temp folder and put it to home
# remove all backups older than a specific date
# could be send via file_upload

# DEFINITIONS
USER="cobs"
DATE=$(date +%Y%m%d)
HOST=$(hostname)

BACKUPNAME="${HOST}_${DATE}_backup"
TMPFOLDER="/tmp/$BACKUPNAME"
HOMEFOLDER="/home/$USER"
MARTASFOLDER="/etc/martas"
MARCOSFOLDER="/etc/marcos"
ETCCRON="$TMPFOLDER/etccrontab.out"
USERCRON="${TMPFOLDER}/${USER}crontab.out"
BACKUPS="$HOMEFOLDER/Backups"
BACKUPFILE="$BACKUPS/${BACKUPNAME}.tar"

# EXECUTION
echo "Running BACKUP of configuration files from $HOST"

mkdir -p $TMPFOLDER
mkdir -p $BACKUPS

# A) copy MARTAS
{
  cp -r $MARTASFOLDER $TMPFOLDER
} || {
  echo "Could not access MARTASFOLDER"
}

# B) copy MARCOS
{
  cp -r $MARCOSFOLDER $TMPFOLDER
} || {
  echo "Could not access MARCOSFOLDER"
}

# C) copy crontab
{
  cat /etc/crontab > $ETCCRON
} || {
  echo "Could not access etc crontab"
}

# D) copy users crontab
{
  crontab -l > $USERCRON
} || {
  echo "Could not access users crontab"
}

# E) copy README
{
  find $HOMEFOLDER -type f -name "README*" -path ${HOMEFOLDER}/RE* -exec cp '{}' $TMPFOLDER \;
  find $HOMEFOLDER -type f -name "Readme*" -path ${HOMEFOLDER}/Re* -exec cp '{}' $TMPFOLDER \;
} || {
  echo "Could not find README"
}

# F) copy SCRIPTS
{
  find $HOMEFOLDER -type d -name "Scripts" -path ${HOMEFOLDER}/Sc* -exec rsync -av --exclude=".*" '{}' $TMPFOLDER \;
  find $HOMEFOLDER -type d -name "SCRIPTS" -path ${HOMEFOLDER}/SC* -exec rsync -av --exclude=".*" '{}' $TMPFOLDER \;
} || {
  echo "Could not access SCRIPTS"
}

# G) copy CONF
{
  find $HOMEFOLDER -type d -name "CONF" -path ${HOMEFOLDER}/CO* -exec cp -r '{}' $TMPFOLDER \;
} || {
  echo "Could not access CONF"
}

# H) copy SYNC
{
  find $HOMEFOLDER -type d -name "Sync" -path ${HOMEFOLDER}/Sy* -exec cp -r '{}' $TMPFOLDER \;
  find $HOMEFOLDER -type d -name "SYNC" -path ${HOMEFOLDER}/SY* -exec cp -r '{}' $TMPFOLDER \;
} || {
  echo "Could not access SYNC"
}

# I) copy credentials
{
  find $HOMEFOLDER -type f -name ".magpycred" -path ${HOMEFOLDER}/.magpyc* -exec cp '{}' $TMPFOLDER/usercred.sys \;
  find /root/ -type f -name ".magpycred" -path /root/.magpyc* -exec cp '{}' $TMPFOLDER/rootcred.sys \;
} || {
  echo "Could not find credential file"
}

# J) other configurations
{
  find /etc/ -type f -name "ntp.conf" -exec cp '{}' $TMPFOLDER/ntp.conf \;
  find /etc/ -type f -name "fstab" -exec cp '{}' $TMPFOLDER/fstab \;
  find /etc/ -type f -name "hosts" -exec cp '{}' $TMPFOLDER/hosts \;
  #cp -r webdirectory $TMPFOLDER
} || {
  echo "Could not find configuration files"
}

# Z) TAR AND ZIP
{
  tar -czf $BACKUPFILE $TMPFOLDER/*
  gzip $BACKUPFILE
} || {
  echo "Could not TAR"
}

# CLEANUP
rm -r $TMPFOLDER
find $BACKUPS -name "*backup.tar.gz" -mtime +30 -exec rm {} \;

echo "BACKUP of $HOST SUCCESSFULLY finished"
