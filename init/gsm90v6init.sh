#!/bin/sh
PYTHONPATH="/home/cobs/anaconda2/bin/python"

$PYTHONPATH /home/cobs/MARTAS/MQTT/serialinit.py -p "/dev/ttyS0" -c S,5,T48,C,datetime,R -k "%y%m%d%w%H%M%S" -i 1024
