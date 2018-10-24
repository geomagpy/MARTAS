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
PYPATH="/home/leon/Software/anaconda2/bin/python"
PYPATH="/usr/bin/python"
CFGPATH="/etc/martas"
LOGPATH="/var/log/magpy"
ACQUPATH="/home/cobs/MARTAS"
ACQUISITION="martas"
BROKERIP="localhost"
STATION="wic"
DETAILS="cobsdb"
MQTTAUTH="no"
MQTTCRED="mqtt"
tvar=""


echo "Helper for adding new acquisition job "
echo "----------------------------------------"
echo "The following job will install a new acquisition"
echo "job on your machine. "
echo "This helper will ask for some PATHS"
echo "and some configuration information of"
echo "the broker and create startup scripts."
echo "Please also make sure to edit martas.cfg"
echo "and sensor.cfg before continuing!"
echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"
echo "run this job as root"
echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"

read -p "Provide python path (default = $PYPATH): " PYPATHT
read -p "Provide path for martas.cfg and sensors.cfg (default = $CFGPATH): " CFGPATHT
read -p "Provide path to acquisition.py (default = $ACQUPATH): " ACQUPATHT
read -p "Provide path for log files (default = $LOGPATH): " LOGPATHT
read -p "Provide the name of the acquisition job (default = $ACQUISITION): " ACQUISITIONT
read -p "Provide the address of the MQTT broker (default = $BROKERIP): " BROKERIPT
read -p "Provide a station name/topic (default = $STATION): " STATIONT
read -p "Broker requires authentication? (default = $MQTTAUTH): " MQTTAUTHT

if [ "$PYPATHT" != "$tvar" ]; then
   PYPATH=$PYPATHT
fi
if [ "$CFGPATHT" != "$tvar" ]; then
   CFGPATH=$CFGPATHT
fi
if [ "$LOGPATHT" != "$tvar" ]; then
   LOGPATH=$LOGPATHT
fi
if [ "$ACQUPATHT" != "$tvar" ]; then
   ACQUPATH=$ACQUPATHT
fi
if [ "$ACQUISITIONT" != "$tvar" ]; then
   ACQUISITION=$ACQUISITIONT
fi
if [ "$BROKERIPT" != "$tvar" ]; then
   BROKERIP=$BROKERIPT
fi
if [ "$STATIONT" != "$tvar" ]; then
   STATION=$STATIONT
fi
if [ "$MQTTAUTHT" = "yes" ]; then
   read -p "Authentication credentials (check app/addcred.py -h) (default = $MQTTCRED): " MQTTCREDT
   if [ "$MQTTCREDT" != "$tvar" ]; then
      MQTTCRED=$MQTTCREDT
   fi
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

CONFFILE=$CFGPATH/martas.cfg
SENSFILE=$CFGPATH/sensor.cfg

cp martas.cfg $CONFFILE
cp martas.cfg $SENSFILE

DUMMYLOGPATH="/logpath"
DUMMYSENSORPATH="/sensorpath"
DUMMYINIT="/initdir/"
DUMMYSTATION="myhome"
DUMMYIP="brokeraddress"
sed -i "s+${DUMMYSTATION}+${STATION}+g" $CONFFILE
sed -i "s+${DUMMYIP}+${BROKERIP}+g" $CONFFILE
sed -i "s+${DUMMYLOGPATH}+${LOGPATH}/martas.log+g" $CONFFILE
sed -i "s+${DUMMYSENSORPATH}+${SENSFILE}+g" $CONFFILE
sed -i "s+${DUMMYINIT}+${ACQUPATH}/init/+g" $CONFFILE

# modify logrotate
# ------------------
if [ "$LOGPATH" != "$stdout" ]; then
   cp martas.logrotate /etc/logrotate.d/martas
   sed -i "s+${DUMMYLOGPATH}+${LOGPATH}/martas.log+g" /etc/logrotate.d/martas
fi


# install as service
# ------------------
cp martas /etc/init.d/$ACQUISITION

# Replace DUMMY values in default file with new values
DUMMYACQU="/your/acquisitionpath"
DUMMYPYTHON="/usr/bin/python"
DUMMYNAME="acquisitionname"
DUMMYCONF="optionsline"

sed -i "s+${DUMMYACQU}+${ACQUPATH}+g" /etc/init.d/$ACQUISITION
sed -i "s+${DUMMYPYTHON}+${PYPATH}+g" /etc/init.d/$ACQUISITION
sed -i "s+${DUMMYNAME}+${ACQUISITION}+g" /etc/init.d/$ACQUISITION
if [ "$MQTTAUTHT" = "yes" ]; then
   sed -i "s+${DUMMYCONF}+ -m ${CONFFILE} -c ${MQTTCRED}+g" /etc/init.d/$ACQUISITION
else
   sed -i "s+${DUMMYCONF}+ -m ${CONFFILE}+g" /etc/init.d/$ACQUISITION
fi

chmod 755 /etc/init.d/$ACQUISITION
#chown root:root /etc/init.d/$ACQUISITION
#update-rc.d $ACQUISITION defaults

echo "----------------------------------------"
echo "$ACQUISITION successfully added as service"
echo "----------------------------------------"
echo "usage:"
echo "/etc/init.d/$ACQUISITION {start|stop|restart|status}"
echo "----------------------------------------"
echo "(to remove use: )"
echo "----------------------------------------"


