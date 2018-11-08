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
CFGPATH="/etc/martas"
MARTAS="martas"
tvar=""


echo "Helper for removing a collector job "
echo "----------------------------------------"
echo "run this job as root"
echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"

read -p "Provide the name of the MARTAS acquisition process (default = $MARTAS): " MARTAST
read -p "Provide path for martas.cfg (default = $CFGPATH): " CFGPATHT

if [ "$CFGPATHT" != "$tvar" ]; then
   CFGPATH=$CFGPATHT
fi
if [ "$MARTAST" != "$tvar" ]; then
   MARTAS=$MARTAST
fi

CONFFILE=$CFGPATH/martas.cfg
SENSFILE=$CFGPATH/sensors.cfg

/etc/init.d/$MARTAS stop

mv $CONFFILE $CONFFILE.defunc
mv $SENSFILE $SENSFILE.defunc

update-rc.d -f $MARTAS remove

rm /etc/init.d/$MARTAS

echo "----------------------------------------"
echo "$MARTAS successfully removed"
echo "----------------------------------------"
echo "----------------------------------------"
echo "Files in $CFGPATH are still present."
echo "Please delete them manually if not needed anymore."
echo "----------------------------------------"

