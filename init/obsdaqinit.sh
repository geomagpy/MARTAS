#!/bin/sh

PYTHON="/usr/bin/python3"
MARTASPATH="/home/pi/MARTAS"
APPPATH=$MARTASPATH"/app"
# run without config file: CONF="" otherwise CONF="-m /config/file"
#CONF=""
CONF="-m /etc/martas/obsdaq.cfg"

# set PalmAcq into idle mode (command mode)
$PYTHON $APPPATH/palmacq.py $CONF -qp
sleep 2
$PYTHON $APPPATH/palmacq.py $CONF -qp
sleep 2
# wait for GPS loopseconds=18
$PYTHON $APPPATH/palmacq.py $CONF -qg

# set PalmAcq into Transparent mode to access ObsDAQ
$PYTHON $APPPATH/palmacq.py $CONF -qt
sleep 2
# stop ObsDAQ's acquisition, if running  
$PYTHON $APPPATH/obsdaq.py $CONF -qp
sleep 5
$PYTHON $APPPATH/obsdaq.py $CONF -qp
sleep 2
# print serial number
$PYTHON $APPPATH/obsdaq.py $CONF -qi
# execute a self calibration resp. load calibration values
$PYTHON $APPPATH/obsdaq.py $CONF -qc
sleep 2
# start acquisition
$PYTHON $APPPATH/obsdaq.py $CONF -qa
sleep 2
# set PalmAcq into idle mode
$PYTHON $APPPATH/palmacq.py $CONF -qp
sleep 2
# set PalmAcq into forward mode
$PYTHON $APPPATH/palmacq.py $CONF -q -d R
sleep 2

