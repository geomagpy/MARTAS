#!/bin/sh


## Helper methods for MARTAS
## the helper creates
## 1. a startupscript for /etc/init.d
##    calling the collector method
## 2. a configuration file for the broker
##    which contains all necessary info for
##    the collector.py job
## Requirements:
## Python2.7.12 or later
## packages paho, etc

# Get the paths for python and config directory
PYPATH="/usr/bin/python3"
CFGPATH="/etc/martas"
LOGPATH="/var/log/magpy"
DATAPATH="/srv"
DBCRED="cobsdb"
RUNTYPE="MARTAS"
CREDPATH="/home/username/.magpycred"
DATASOURCE="file"
EMAILCRED="smtp"
tvar=""

MONITORQ="yes"
THRESHOLDQ="yes"
SERIALSWITCH="no"
NOTIFICATIONQ="l"
NOTIFICATIONTYPE="log"

current="$(pwd)"
cd ..
MARTASPATH="$(pwd)"
cd app
MARTASAPPPATH="$(pwd)"
cd ../..
CREDPATH="$(pwd)/.magpycred"
cd "$current"

echo "Installer for adding applications to MARTAS/MARCOS"
echo "----------------------------------------"
echo "In the following you can add some applications"
echo "to support your MARTAS/MARCOS machine."
echo "This helper will ask for basic information"
echo "on methods and configuration of apps."
echo "It will create basic startup scripts."
echo "Jobs details however still need to be"
echo "added manually later in the configuration"
echo "files."
echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
echo "run this job as root"
echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"

echo "${whoami}"

read -p "Provide python path (default = $PYPATH): " PYPATHT
read -p "Provide path for configuration files (default = $CFGPATH): " CFGPATHT
read -p "Path to the MARTAS applications directory (default = $MARTASAPPPATH): " MARTASAPPPATHT
read -p "Basepath to archive and data (default = $DATAPATH): " DATAPATHT
read -p "Add monitoring scripts (monitor.py) (default = $MONITORQ): " MONITORQT
read -p "Add threshold testing (default = $THRESHOLDQ): " THRESHOLDQT

# if both N then break
if [ "$MONITORQT" != "$tvar" ]; then
   MONITORQ="no"
fi
if [ "$THRESHOLDQT" != "$tvar" ]; then
   THRESHOLDQ="no"
fi
if [ "$MONITORQ" = "no"  ] && [ "$THRESHOLDQ" = "no" ]; then
   exit 0
fi

read -p "Running on MARTAS or MARCOS (default = $RUNTYPE): " RUNTYPET
read -p "Preferred notification option [email (e), messenger (m), only log (l)] (default = $NOTIFICATIONQ): " NOTIFICATIONQT
read -p "Provide path for logs (default = $LOGPATH): " LOGPATHT


if [ "$PYPATHT" != "$tvar" ]; then
   PYPATH=$PYPATHT
fi
if [ "$CFGPATHT" != "$tvar" ]; then
   CFGPATH=$CFGPATHT
fi
if [ "$MARTASAPPPATHT" != "$tvar" ]; then
   MARTASAPPPATH=$MARTASAPPPATHT
fi
if [ "$DATAPATHT" != "$tvar" ]; then
   DATAPATH=$DATAPATHT
fi
if [ "$LOGPATHT" != "$tvar" ]; then
   LOGPATH=$LOGPATHT
fi
if [ "$NOTIFICATIONQT" != "$tvar" ]; then
   NOTIFICATIONQ=$NOTIFICATIONQT
fi

if [ "$RUNTYPET" = "MARCOS" ]; then
   RUNTYPE=$RUNTYPET
   DATASOURCE="db"
   read -p "Database credentials (check app/addcred.py -h) (default = $DBCRED): " DBCREDT
   if [ "DBCREDT" != "$tvar" ]; then
      DBCRED=$DBCREDT
   fi
   read -p "Credentials path (default = $CREDPATH): " CREDPATHT
   if [ "CREDPATHT" != "$tvar" ]; then
      CREDPATH=$CREDPATHT
   fi
fi

if [ "$NOTIFICATIONQ" = "e" ]; then
   NOTIFICATIONTYPE="mail"
   read -p "e-mail authentication credentials (check app/addcred.py -h) (default = $EMAILCRED): " EMAILCREDT
   if [ "$EMAILCREDT" != "$tvar" ]; then
      EMAILCRED=$EMAILCREDT
   fi
   if [ "$RUNTYPE" = "MARTAS" ]; then
       read -p "Credentials path (default = $CREDPATH): " CREDPATHT
       if [ "CREDPATHT" != "$tvar" ]; then
          CREDPATH=$CREDPATHT
       fi
   fi
elif [ "$NOTIFICATIONQ" = "m" ]; then
   NOTIFICATIONTYPE="telegram"
   echo "Messenger selected - will check for required python packages after selection is finished"
else
   NOTIFICATIONTYPE="log"
   NOTIFICATIONQ="l"
   echo "Neither mail nor messenger selected - continuing with log file notification"
fi

if [ "$RUNTYPE" = "MARTAS" ] && [ "$THRESHOLDQ" = "yes" ]; then
   read -p "Use microcontroller switch commands with threshold tester (default = $SERIALSWITCH): " SERIALSWITCHT
fi

# create directories if not existing
# log
mkdir -p $LOGPATH

# conf
mkdir -p $CFGPATH


# check python packages
# ------------------
if [ "$NOTIFICATIONQ" = "m" ]; then
    if $PYPATH -c "import telegram_send" &> /dev/null; then
        echo 'telegram_send package already installed'
    else
        echo 'installing telegram_send python package ...'
        echo '(please note: for python > 3.6 required)'
        $PYPATH -m pip install python-telegram-bot==13.4
        $PYPATH -m pip install telegram-send
    fi
fi


# update configuration
# ------------------

MONITORCFG=$CFGPATH/monitor.cfg
THRESHOLDCFG=$CFGPATH/threshold.cfg
MAILCFG=$CFGPATH/mail.cfg
TELEGRAMCFG=$CFGPATH/telegram.cfg
ALLCFG=$CFGPATH/*.cfg

# copy but not overwrite if existing
cp -n ../conf/monitor.cfg $MONITORCFG
cp -n ../conf/threshold.cfg $THRESHOLDCFG
cp -n ../conf/mail.cfg $MAILCFG
cp -n ../conf/telegram.cfg $TELEGRAMCFG

DUMMYLOGPATH="/mylogpath"
DUMMYBASEDIR="/mybasedir"
DUMMYMARTAS="/my/home/MARTAS"
DUMMYNOTIFICATION="mynotificationtype"
DUMMYCONFPATH="/myconfpath"
DUMMYDBCRED="mydbcred"
DUMMYCREDPATH="/home/username"
DUMMYDATASOURCE="mydatasource"
DUMMYMAILCRED="mysmtp"

sed -i "s+${DUMMYNOTIFICATION}+${NOTIFICATIONTYPE}+g" $MONITORCFG
sed -i "s+${DUMMYBASEDIR}+${DATAPATH}+g" $MONITORCFG
sed -i "s+${DUMMYCONFPATH}+${CFGPATH}+g" $MONITORCFG
sed -i "s+${DUMMYLOGPATH}+${LOGPATH}+g" $MONITORCFG
sed -i "s+${DUMMYMARTAS}+${MARTASPATH}+g" $MONITORCFG
sed -i "s+${DUMMYDBCRED}+${DBCRED}+g" $MONITORCFG
sed -i "s+${DUMMYCREDPATH}+${CREDPATH}+g" $MONITORCFG

sed -i "s+${DUMMYNOTIFICATION}+${NOTIFICATIONTYPE}+g" $THRESHOLDCFG
sed -i "s+${DUMMYBASEDIR}+${DATAPATH}+g" $THRESHOLDCFG
sed -i "s+${DUMMYCONFPATH}+${CFGPATH}+g" $THRESHOLDCFG
sed -i "s+${DUMMYLOGPATH}+${LOGPATH}+g" $THRESHOLDCFG
sed -i "s+${DUMMYMARTAS}+${MARTASPATH}+g" $THRESHOLDCFG
sed -i "s+${DUMMYDBCRED}+${DBCRED}+g" $THRESHOLDCFG
sed -i "s+${DUMMYCREDPATH}+${CREDPATH}+g" $THRESHOLDCFG
sed -i "s+${DUMMYDATASOURCE}+${DATASOURCE}+g" $THRESHOLDCFG

sed -i "s+${DUMMYMAILCRED}+${EMAILCRED}+g" $MAILCFG

#mqttuser  :  username
#credentialpath  :  /home/username/.magpycred

if [ "$SERIALSWITCHT" = "yes" ]; then
   echo "Please update the serial communication parameters in the threshold.cfg file"
   #DUMMYCREDPATH="#credentialpath  :  /home/username/.magpycred"
   #DUMMYMQTTUSER="#mqttuser  :  username"
   #NEWMQTTUSER="mqttuser  :  ${MQTTUSER}"
   #NEWCREDPATH="credentialpath  :  ${CREDPATH}"
   #sed -i "s+${DUMMYCREDPATH}+${NEWCREDPATH}+g" $CONFFILE
   #sed -i "s+${DUMMYMQTTUSER}+${NEWMQTTUSER}+g" $CONFFILE
fi

# modify logrotate
# ------------------
# monitor an threshold to logrotate?
#if [ "$LOGPATH" != "$stdout" ]; then
#   cp -n martas.logrotate /etc/logrotate.d/martas
#   sed -i "s+${DUMMYLOGPATH}+${LOGPATH}/martas.log+g" /etc/logrotate.d/martas
#fi


# add line to cron
# ----------------
MONITORLINE="30  *  *  *  *   ${PYTHONPATH} ${MARTASAPPPATH}/monitor.py -c ${CFGPATH}/monitor.cfg"
THRESHOLDLINE="1,11,21,31,41,51  *  *  *  *   ${PYTHONPATH} ${MARTASAPPPATH}/threshold.py -m ${CFGPATH}/threshold.cfg"

echo "----------------------------------------"
echo "APPLICATIONS successfully added "
echo "----------------------------------------"
echo "add the following lines to your crontab:"
if [ "$THRESHOLDQ" = "yes" ]; then
    echo "# Periodically testing threshold every 10 min"
    echo "$THRESHOLDLINE"
fi
if [ "$MONITORQ" = "yes" ]; then
    echo "# Periodical process monitoring"
    echo "$MONITORLINE"
fi
echo "----------------------------------------"
