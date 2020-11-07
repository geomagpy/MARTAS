#!/bin/sh
PYTHONPATH="/usr/bin/python"
MARTASPATH="/my/home/MARTAS"

$PYTHONPATH $MARTASPATH/app/serialinit.py -p "/dev/ttyUSB0" -c R -i 1024
