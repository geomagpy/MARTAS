#!/bin/sh
PYTHONPATH="/home/cobs/anaconda2/bin/python"

$PYTHONPATH /home/cobs/MARTAS/MQTT/serialinit.py -p "/dev/ttyUSB0" -c R -i 1024
