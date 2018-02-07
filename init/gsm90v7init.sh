#!/bin/sh
PYTHONPATH="/home/cobs/anaconda2/bin/python"

$PYTHONPATH /home/cobs/MARTAS/MQTT/serialinit.py -p "/dev/ttyS1" -c S,5,T048.5,C,datetime,D,R -k "%y%m%d%w%H%M%S" -r "z-save,z" -i 1024
