#!/bin/sh
PYTHONPATH="/usr/bin/python"
MARTASPATH="/my/home/MARTAS"

$PYTHONPATH $MARTASPATH/app/serialinit.py -b 2400 -p "/dev/ttyS1" -c "A00d03000" -d 13
