#!/bin/sh

PYTHON="/usr/bin/python"
MARTASPATH="/home/pi/MARTAS"
APPPATH=$MARTASPATH"/app"

# set PalmAcq into idle mode (command mode)
$PYTHON $APPPATH/palmacq.py -qp
sleep 2
$PYTHON $APPPATH/palmacq.py -qp
sleep 2
# wait for GPS loopseconds=18
$PYTHON $APPPATH/palmacq.py -qg

# set PalmAcq into Transparent mode to access ObsDAQ
$PYTHON $APPPATH/palmacq.py -qt
sleep 2
# stop ObsDAQ's acquisition, if running  
$PYTHON $APPPATH/obsdaq.py -qp
sleep 5
$PYTHON $APPPATH/obsdaq.py -qp
sleep 2
# print serial number
$PYTHON $APPPATH/obsdaq.py -qi
# execute a self calibration resp. load calibration values
$PYTHON $APPPATH/obsdaq.py -qc
sleep 2
# start acquisition
$PYTHON $APPPATH/obsdaq.py -qa
sleep 2
# set PalmAcq into idle mode
$PYTHON $APPPATH/palmacq.py -qp
sleep 2
# set PalmAcq into forward mode
$PYTHON $APPPATH/palmacq.py -q -d R
sleep 2

