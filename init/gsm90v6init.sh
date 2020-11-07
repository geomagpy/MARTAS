#!/bin/sh
PYTHONPATH="/usr/bin/python"
MARTASPATH="/my/home/MARTAS"

$PYTHONPATH $MARTASPATH/app/serialinit.py -p "/dev/ttyS0" -c S,5,T48,C,datetime,R -k "%y%m%d%w%H%M%S" -i 1024
