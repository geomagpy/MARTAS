#!/bin/sh
PYTHONPATH="/usr/bin/python"
MARTASPATH="/my/home/MARTAS"

$PYTHONPATH $MARTASPATH/app/serialinit.py -p "/dev/ttyS0" -b 9600 -c "mode text,time datetime,date 11-22-16,range 48500,auto 5" -k "%H:%M:%S" -x -d 0
