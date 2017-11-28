#!/bin/sh
python serial-init.py -p "/dev/ttyUSB0" -c S,5,T048.5,C,datetime,D,R -k "%y%m%d%w%H%M%S" -r "z-save,z" -i 1024
