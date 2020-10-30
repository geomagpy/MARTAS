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
INITPATH="/etc/martas/init"
LOGPATH="/var/log/magpy"
ACQUISITION="martas"
BROKERIP="localhost"
STATION="wic"
DETAILS="cobsdb"
MQTTAUTH="no"
MQTTCRED="mqtt"
CREDPATH="/home/username/.magpycred"
MQTTUSER="cobs"
tvar=""

current="$(pwd)"
cd ..
ACQUPATH="$(pwd)"
cd ..
CREDPATH="$(pwd)/.magpycred"
cd "$current"

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
read -p "Path for specific sensor initialization files (default = $INITPATH): " INITPATHT
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
if [ "$INITPATHT" != "$tvar" ]; then
   INITPATH=$INITPATHT
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
   read -p "Credentials path (default = $CREDPATH): " CREDPATHT
   if [ "CREDPATHT" != "$tvar" ]; then
      CREDPATH=$CREDPATHT
   fi
   read -p "MQTT username (should be identical as provided in credentials) (default = $MQTTUSER): " MQTTUSERT
   if [ "$MQTTUSERT" != "$tvar" ]; then
      MQTTUSER=$MQTTUSERT
   fi
fi

# create directories if not existing
# log
mkdir -p $LOGPATH

# conf
mkdir -p $CFGPATH

# init
mkdir -p $INITPATH

# check python packages
# ------------------
if $PYPATH -c "import geomagpy" &> /dev/null; then
    echo 'geomagpy package already installed'
else
    echo 'installing geomagpy python package ...'
    $PYPATH -m pip install geomagpy
fi

if $PYPATH -c "import pyserial" &> /dev/null; then
    echo 'pyserial package already installed'
else
    echo 'installing telepot pyserial package ...'
    $PYPATH -m pip install pyserial
fi

if $PYPATH -c "import paho-mqtt" &> /dev/null; then
    echo 'paho-mqtt package already installed'
else
    echo 'installing paho-mqtt python package ...'
    $PYPATH -m pip install paho-mqtt
fi

if $PYPATH -c "import twisted" &> /dev/null; then
    echo 'twisted package already installed'
else
    echo 'installing twisted python package ...'
    $PYPATH -m pip install twisted
fi

# update configuration
# ------------------
# station
# destination
# address
# storageinfo

CONFFILE=$CFGPATH/martas.cfg
SENSFILE=$CFGPATH/sensors.cfg

# copy but not overwrite if existing
cp -n ../conf/martas.cfg $CONFFILE
cp -n ../conf/sensors.cfg $SENSFILE
cp -n ../init/*.sh $INITPATH

DUMMYLOGPATH="/logpath"
DUMMYSENSORPATH="/sensorpath"
DUMMYINIT="/initdir/"
DUMMYSTATION="myhome"
DUMMYIP="brokeraddress"
sed -i "s+${DUMMYSTATION}+${STATION}+g" $CONFFILE
sed -i "s+${DUMMYIP}+${BROKERIP}+g" $CONFFILE
sed -i "s+${DUMMYLOGPATH}+${LOGPATH}/martas.log+g" $CONFFILE
sed -i "s+${DUMMYSENSORPATH}+${SENSFILE}+g" $CONFFILE
sed -i "s+${DUMMYINIT}+${INITPATH}/+g" $CONFFILE

#mqttuser  :  username
#credentialpath  :  /home/username/.magpycred


if [ "$MQTTAUTHT" = "yes" ]; then
   DUMMYCREDPATH="#credentialpath  :  /home/username/.magpycred"
   DUMMYMQTTUSER="#mqttuser  :  username"
   NEWMQTTUSER="mqttuser  :  ${MQTTUSER}"
   NEWCREDPATH="credentialpath  :  ${CREDPATH}"
   sed -i "s+${DUMMYCREDPATH}+${NEWCREDPATH}+g" $CONFFILE
   sed -i "s+${DUMMYMQTTUSER}+${NEWMQTTUSER}+g" $CONFFILE
fi

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
chown root:root /etc/init.d/$ACQUISITION
update-rc.d $ACQUISITION defaults

echo "----------------------------------------"
echo "$ACQUISITION successfully added as service"
echo "----------------------------------------"
echo "usage:"
echo "/etc/init.d/$ACQUISITION {start|stop|restart|status}"
echo "----------------------------------------"
echo "(to remove use: sudo sh removemartas.sh)"
echo "----------------------------------------"
