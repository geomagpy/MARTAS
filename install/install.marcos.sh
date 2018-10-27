#!/bin/bash


## Helper methods
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
PYPATH="/home/leon/Software/anaconda2/bin/python"
PYPATH="/usr/bin/python"
CFGPATH="/etc/marcos"
LOGPATH="/var/log/magpy"
COLLPATH="/home/cobs/MARCOS"
TELEGRAMPATH="/telegram.conf"
BROKER="broker"
BROKERIP="localhost"
STATION="all"
DESTINATION="db"
DETAILS="cobsdb"
MQTTAUTH="no"
MQTTCRED="mqtt"
tvar=""


echo "Helper for adding new collector job "
echo "----------------------------------------"
echo "Each collector job will access a single"
echo "broker, which provides MARTAS mqtt data."
echo "This helper will ask for some PATHS"
echo "and some configuration information of"
echo "the broker and create the startup scripts"
echo "Please also make sure to edit marcos.cfg"
echo "before continuing"
echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
echo "run this job as root"
echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"

read -p "Provide python path (default = $PYPATH): " PYPATHT
read -p "Provide path for broker.conf (default = $CFGPATH): " CFGPATHT
read -p "Provide path to collector.py (default = $COLLPATH): " COLLPATHT
read -p "Provide path for log files (default = $LOGPATH): " LOGPATHT
read -p "Provide the name of the broker (default = $BROKER): " BROKERT
read -p "Provide the address of the broker (default = $BROKER): " BROKERIPT
read -p "Provide a station name/topic (default = $STATION): " STATIONT
read -p "Output destination (stdout, file, db, etc. default = $DESTINATION): " DESTINATIONT
read -p "Destination details (e.g. path if file, or db credentials if db; default = $DETAILS): " DETAILST
read -p "Broker requires authentication? (default = $MQTTAUTH): " MQTTAUTHT
read -p "Want to use telegram notifications? Please provide config path (default = $TELEGRAMPATH): " TELEGRAMPATHT

if [ "$PYPATHT" != "$tvar" ]; then
   PYPATH=$PYPATHT
fi
if [ "$CFGPATHT" != "$tvar" ]; then
   CFGPATH=$CFGPATHT
fi
if [ "$LOGPATHT" != "$tvar" ]; then
   LOGPATH=$LOGPATHT
fi
if [ "$COLLPATHT" != "$tvar" ]; then
   COLLPATH=$COLLPATHT
fi
if [ "$BROKERT" != "$tvar" ]; then
   BROKER=$BROKERT
fi
if [ "$BROKERIPT" != "$tvar" ]; then
   BROKERIP=$BROKERIPT
fi
if [ "$DESTINATIONT" != "$tvar" ]; then
   DESTINATION=$DESTINATIONT
fi
if [ "$STATIONT" != "$tvar" ]; then
   STATION=$STATIONT
fi
if [ "$DETAILST" != "$tvar" ]; then
   DETAILS=$DETAILST
fi
if [ "$MQTTAUTHT" = "yes" ]; then
   read -p "Authentication credentials (check app/addcred.py -h) (default = $MQTTCRED): " MQTTCREDT
   if [ "$MQTTCREDT" != "$tvar" ]; then
      MQTTCRED=$MQTTCREDT
   fi
fi
if [ "$TELEGRAMPATHT" != "$tvar" ]; then
   TELEGRAMPATH=$TELEGRAMPATHT
fi

# create directories if not existing
# log
mkdir -p $LOGPATH

# conf
mkdir -p $CFGPATH

# update configuration
# ------------------
# station
# destination
# address
# storageinfo

CONFFILE=$CFGPATH/$BROKER.cfg

cp marcos.cfg $CONFFILE

DUMMYLOGPATH="/logpath"
DUMMYSTATION="myhome"
DUMMYDEST="outputdestination"
DUMMYIP="brokeraddress"
DUMMYFILE="/tmp"
DUMMYDB="mydb"
DUMMYTELEGRAM="/telegram.conf"
DUMMYCRED="#mqttcredentials  :  broker"
sed -i "s+${DUMMYSTATION}+${STATION}+g" $CONFFILE
sed -i "s+${DUMMYIP}+${BROKERIP}+g" $CONFFILE
sed -i "s+${DUMMYDEST}+${DESTINATION}+g" $CONFFILE
sed -i "s+${DUMMYTELEGRAM}+${TELEGRAMPATH}+g" $CONFFILE
sed -i "s+${DUMMYLOGPATH}+${LOGPATH}/marcos.log+g" $CONFFILE
if [ "$DESTINATION" = "db" ]; then
   sed -i "s+${DUMMYDB}+${DETAILS}+g" $CONFFILE
fi
if [ "$DESTINATION" = "file" ]; then
   sed -i "s+${DUMMYFILE}+${DETAILS}+g" $CONFFILE
fi
if [ "$MQTTAUTHT" = "yes" ]; then
   sed -i "s+${DUMMYCRED}+mqttcredentials  :  ${MQTTCRED}+g" $CONFFILE
fi

# modify logrotate
# ------------------
if [ "$LOGPATH" != "$stdout" ]; then
   cp marcos.logrotate /etc/logrotate.d/marcos
   sed -i "s+${DUMMYLOGPATH}+${LOGPATH}/marcos.log+g" /etc/logrotate.d/marcos
fi



# install as service
# ------------------
cp broker /etc/init.d/collect-$BROKER

# Replace DUMMY values in default file with new values
DUMMYCOLL="/your/collectorpath"
DUMMYPYTHON="/usr/bin/python"
DUMMYNAME="brokername"
DUMMYCONF="optionsline"

sed -i "s+${DUMMYCOLL}+${COLLPATH}+g" /etc/init.d/collect-$BROKER
sed -i "s+${DUMMYPYTHON}+${PYPATH}+g" /etc/init.d/collect-$BROKER
sed -i "s+${DUMMYNAME}+collect-${BROKER}+g" /etc/init.d/collect-$BROKER
sed -i "s+${DUMMYCONF}+ -m ${CONFFILE}+g" /etc/init.d/collect-$BROKER

chmod 755 /etc/init.d/collect-$BROKER
chown root:root /etc/init.d/collect-$BROKER
update-rc.d collect-$BROKER defaults

echo "----------------------------------------"
echo "collect-$BROKER successfully added as service"
echo "----------------------------------------"
echo "usage:"
echo "/etc/init.d/collect-$BROKER {start|stop|restart|status}"
echo "----------------------------------------"
echo "(to remove use: sudo sh removemarcos.sh)"
echo "----------------------------------------"

