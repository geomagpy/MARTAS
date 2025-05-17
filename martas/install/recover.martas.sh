#!/bin/bash

## Helper methods to recover MARTAS
## based on a backup constructed from backup_config.sh
## Recovery can be applied on a fresh ubuntu/debian INSTALLTION
## Only prerequisite is a MARTAS clone within a user directory
## and access to the backup directory
## Recovery needs to be running with root privileges
## Recovery will install all necessary packages and configuartions
## recovery will need access to a backup_config directory and check that first
## - check whether files are backup files
## - check backup version
## - check whether user exists
## - check python paths and recommend minimconda or anaconda installation if necessary
## - check host name and ask whether name should be changed

## Suggested approach on a new installation
## install default ubunutu/debian
## create the same user as used previously
## login as this user, create a directory called "Backups" within home/user,
## and load the backup you want to restore there

USER="debian"
DATE=$(date +%Y%m%d)
BACKUPPATH="/home/${USER}/Backups"
current="$(pwd)"


echo "Helper for MARTAS recovery "
echo "----------------------------------------"
echo "The following job will recover MARTAS"
echo "from backup data created by backup_config.sh. "
echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
echo "run this job as root"
echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"

# 1. Check Backup
read -p "Provide a user name, whos home directory will contain MARTAS and all related configuration data (default = $USER): " USERT
if [ "$USERT" != "$tvar" ]; then
   USER=$USERT
fi
read -p "Provide path where to find a backup zip file (default = $BACKUPPATH). Please note: if more than one zip file is found here then the latest is used: " BACKUPPATHT
if [ "$BACKUPPATHT" != "$tvar" ]; then
   BACKUPPATH=$BACKUPPATHT
fi

# 1.1 extract zipped data to tmp
FILEPATH=$(ls -tp ${BACKUPPATH}/*_backup.tar.gz | grep -v /$ | head -1)
FILENAME=$(basename ${FILEPATH} .tar.gz)
cp ${FILEPATH} /tmp/recover.tar.gz
gunzip /tmp/recover.tar.gz
tar xf /tmp/recover.tar -C /tmp/
TMPBACKPATH="/tmp/tmp/${FILENAME}"

# 1.2 check username
# Get files with ...crontab.out -> get username
cd $TMPBACKPATH
USERN=$(ls -I "etc*" | grep .out | sed "s/crontab.out//")
cd $current
if [[ ! $USERN -eq $USER ]]; then
    echo "Your provided user name (${USER}) differs from the one of the backup (${USERN})"
    echo "We will use the provided one ..."
    echo "If you don't agree you got 10 seconds to abort"
    sleep 10
fi

# 1.3 check if user is existing

# 1.4 check if martas and etccrontab exist (if not abort)
if [[ ! -f "${TMPBACKPATH}/etccrontab.out" || ! -d "${TMPBACKPATH}/martas" ]]; then
    echo "Does not seem to be a MARTAS backup - aborting."
    exit 1
fi
echo " -> backup data extracted and briefly checked for correctness - continuing"
sleep 3
# 2. Check System and eventually install missing packages to run Martas
# extract python version
# try to install python packages if not anaconda. otherwise provide package list
echo "Software requirements"
echo "  ! please note: recovery will always install everything based on system python3 no matter what has been used before - you have 10 sec to cancel in case you dont want that"
sleep 10
echo "- installing some essential linux packages now:"
apt update
apt upgrade
apt-get install ntp arduino ssh mosquitto mosquitto-clients fswebcam python3-matplotlib python3-scipy python3-serial python3-twisted python3-wxgtk4.0 python3-pip

# 3. install martas, marcos, addapps, telegrambot

if [ ! -d "/home/${USER}/MARTAS" ]; then
    echo "- MARTAS not yet existing - getting it as user $USER"
    cd /home/${USER}
    su - {} -c '/usr/bin/git clone https://github.com/geomagpy/MARTAS.git'
fi

if [ -d "${TMPBACKPATH}/martas" ]; then
    echo "-------------------------------------------"
    echo "Dealing with MARTAS part ..."
    echo "-------------------------------------------"
    if [ ! -f "/etc/init.d/martas" ]; then
        echo "- MARTAS not yet installed - doing that now"
        echo "-------------------------------------------"
        cd /home/${USER}/MARTAS/install
        bash install.martas.sh
    fi
    echo "- recovering configuration files"
    echo "-------------------------------------------"
    BACK="/tmp/replaced_by_recovery_${DATE}.tar.gz"
    tar -czf $BACK /etc/martas
    rm -r /etc/martas/*
    cp $BACK /etc/martas/
    cp -r ${TMPBACKPATH}/martas /etc/
    chown -R $USER:$USER /etc/martas
fi

if [ -d "${TMPBACKPATH}/marcos" ]; then
    echo "-------------------------------------------"
    echo "Dealing with MARCOS part ..."
    echo "-------------------------------------------"
    # find collector configurations and go through this list
    # ls /tmp/tmp/endeavour_20230101_backup/martas/ -I mail.cfg -I telegram.cfg -I monitor.cfg -I martas.cfg -I sensors.cfg -I telegrambot.cfg -I threshold.cfg -I "*.sh"
    echo "Marcos is not yet fully supported: you need to perfom install.marcos.sh for all collector jobs"
    echo "- recovering configuration files"
    echo "-------------------------------------------"
    BACK="/tmp/replaced_by_recovery_${DATE}.tar.gz"
    tar -czf $BACK /etc/marcos
    rm -r /etc/marcos/*
    cp $BACK /etc/marcos/
    cp -r ${TMPBACKPATH}/marcos /etc/
    chown -R $USER:$USER /etc/marcos
fi

# find threshold and or monitor scripts in martas/marcos
if [ -f "${TMPBACKPATH}/martas/monitor.cfg" ] || [ -f "${TMPBACKPATH}/martas/threshold.cfg" ]; then
    echo "Installing previously used additional MARTAS applications ..."
    echo "-------------------------------------------"
    cd /home/${USER}/MARTAS/install
    bash install.addapps.sh
fi
if [[ -f "${TMPBACKPATH}/martas/telegrambot.cfg" ]]; then
        echo "Installing previously used telegrambot ..."
        echo "-------------------------------------------"
        cd /home/${USER}/MARTAS/install
        bash install.telegram.bot
fi

# 4. eventually required directories are created
if [[ -d "${TMPBACKPATH}/CONF" ]]; then
    echo "Recovering general configuration data ..."
    cp -r ${TMPBACKPATH}/CONF /home/${USER}/
fi
if [[ -d "${TMPBACKPATH}/SCRIPTS" ]]; then
    echo "Recovering optional scripts ..."
    cp -r ${TMPBACKPATH}/SCRIPTS /home/${USER}/
fi
if [[ -d "${TMPBACKPATH}/SYNC" ]]; then
    echo "Recovering synchronization data ..."
    cp -r ${TMPBACKPATH}/SYNC /home/${USER}/
fi
if [[ -d "${TMPBACKPATH}/Sync" ]]; then
    echo "Recovering synchronization data ..."
    cp -r ${TMPBACKPATH}/Sync /home/${USER}/
fi
if [[ -f "${TMPBACKPATH}/Readme.txt" ]]; then
    echo "Recovering Readme's ..."
    cp ${TMPBACKPATH}/Readme.txt /home/${USER}/README.txt
fi
if [[ -f "${TMPBACKPATH}/README.txt" ]]; then
    echo "Recovering Readme's ..."
    cp ${TMPBACKPATH}/README.txt /home/${USER}/README.txt
fi
if [[ -f "${TMPBACKPATH}/readme.txt" ]]; then
    echo "Recovering Readme's ..."
    cp ${TMPBACKPATH}/readme.txt /home/${USER}/README.txt
fi
if [[ -f "${TMPBACKPATH}/README.TXT" ]]; then
    echo "Recovering Readme's ..."
    cp ${TMPBACKPATH}/README.TXT /home/${USER}/README.txt
fi
if [[ -f "${TMPBACKPATH}/.magpycred" ]]; then
    echo "Recovering users credentials ..."
    cp ${TMPBACKPATH}/usercred.sys /home/${USER}/.magpycred
fi
if [[ -f "${TMPBACKPATH}/.rootcred" ]]; then
    echo "Recovering credentials ..."
    cp ${TMPBACKPATH}/rootcred.sys /root/.magpycred
fi

# append txt to Readme
READMETXT1="Recovered from backup on ${DATE}"
READMETXT2=" -> Backupfile: ${FILEPATH}"
echo $READMETXT1 >> /home/${USER}/README.txt
echo $READMETXT2 >> /home/${USER}/README.txt

# 5. access to logs and config
chown -R $USER:$USER /var/log/magpy

# 6. Summary and suggestions
HOST=$(hostname)
# also check name and IP, suggest to change them
echo "Please note: dont forget to adopt your hostname (current name is ${HOST}),"
echo "the IP configuration and network connection parameters (i.e. proxy)."
echo "This is not done by the recovery job."

# 7. recover crontabs
echo "Replacing /etc/crontab with backup crontab (the previous version is stored in your users homedir):"
cp /etc/crontab /home/${USER}/etccrontab.bck
cp -rf ${TMPBACKPATH}/etccrontab.out /etc/crontab

echo "Checking user crontab: please add changes here manually"
cat ${TMPBACKPATH}/${USER}crontab.out


echo "DONE - reboot when convinient"
