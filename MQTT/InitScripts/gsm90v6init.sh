#!/bin/sh
python serial-init.py -p "/dev/ttyUSB0" -c S,5,T048,C,datetime,R -k "%y%m%d%w%H%M%S" -i 1024
