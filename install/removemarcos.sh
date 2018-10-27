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
CFGPATH="/etc/marcos"
BROKER="broker"
tvar=""


echo "Helper for removing a collector job "
echo "----------------------------------------"
echo "run this job as root"
echo "!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!"

read -p "Provide the name of the broker (default = $BROKER): " BROKERT
read -p "Provide path for broker.conf (default = $CFGPATH): " CFGPATHT

if [ "$CFGPATHT" != "$tvar" ]; then
   CFGPATH=$CFGPATHT
fi
if [ "$BROKERT" != "$tvar" ]; then
   BROKER=$BROKERT
fi

CONFFILE=$CFGPATH/$BROKER.cfg

/etc/init.d/collect-$BROKER stop

mv $CONFFILE $CONFFILE.defunc

update-rc.d -f collect-$BROKER remove

rm /etc/init.d/collect-$BROKER

echo "----------------------------------------"
echo "collect-$BROKER successfully removed"
echo "----------------------------------------"
echo "----------------------------------------"
echo "Files in $CFGPATH are still present."
echo "Please delete them manually if not needed anymore."
echo "----------------------------------------"

