#!/bin/sh

MARTASPATH="/home/pi/MARTAS"
APPPATH=$MARTASPATH"/app"

# set PalmAcq into idle mode (command mode)
python $APPPATH/palmacq.py -qp
sleep 2
python $APPPATH/palmacq.py -qp
sleep 2
# wait for GPS loopseconds=18
python $APPPATH/palmacq.py -qg

# set PalmAcq into Transparent mode to access ObsDAQ
python $APPPATH/palmacq.py -qt
sleep 2
# stop ObsDAQ's acquisition, if running  
python $APPPATH/obsdaq.py -qp
sleep 5
python $APPPATH/obsdaq.py -qp
sleep 2
# print serial number
python $APPPATH/obsdaq.py -qi
# execute a self calibration resp. load calibration values
python $APPPATH/obsdaq.py -qc
sleep 2
# start acquisition
python $APPPATH/obsdaq.py -qa
sleep 2
# set PalmAcq into idle mode
python $APPPATH/palmacq.py -qp
sleep 2
# set PalmAcq into forward mode
python $APPPATH/palmacq.py -q -d R
sleep 2

