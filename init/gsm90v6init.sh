#!/bin/sh
PYTHONPATH="/home/cobs/anaconda2/bin/python"
MARTASPATH="/home/cobs/MARTAS"

$PYTHONPATH $MARTASPATH/app/serialinit.py -p "/dev/ttyS0" -c S,5,T48,C,datetime,R -k "%y%m%d%w%H%M%S" -i 1024
