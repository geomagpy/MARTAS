#!/bin/sh

# INITIALIZATION data
# required for systems like GSM90, POS1, POS4 and BM35
# will send commands to the instrument to initialize data transfer

# GSM90 options
# -b (baudrate) : default is 115400
# -p (port)
# -c (command to send:)
#      S
#      5          -> filter (5= 50Hz, 6= 60Hz)
#      T048.5     -> Tuning field in microT
#      C          ->
#      datetime   -> initialize time with PC time (see option k)
#      D          -> sampling rate: D -> down, U -> up, leave out to keep sampling rate
#      R          -> Run

PYTHONPATH="/home/cobs/anaconda2/bin/python"

$PYTHONPATH /home/cobs/MARTAS/app/serialinit.py -p "/dev/ttyS1" -c S,5,T048.5,C,datetime,D,R -k "%y%m%d%w%H%M%S" -r "z-save,z" -i 1024
