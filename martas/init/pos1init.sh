##!/bin/sh
#PYTHONPATH="/usr/bin/python"
#MARTASPATH="/my/home/MARTAS"

#$PYTHONPATH $MARTASPATH/app/serialinit.py -p "/dev/ttyS0" -b 9600 -c "mode text,time datetime,date 11-22-16,range 48500,auto 5" -k "%H:%M:%S" -x -d 0
PYTHONPATH="/usr/bin/python3"
MARTASPATH="/home/debian/MARTAS"
DAY=$(date +FORMAT=%d |awk -F '=' '{print $2}')
MONTH=$(date +FORMAT=%m |awk -F '=' '{print $2}')
YEAR=$(date +FORMAT=%y |awk -F '=' '{print $2}')
MAINFIELDAWAITING=48900
YOURDEV="/dev/ttyUSB0"
echo 'Starting Pos1init.sh at' 'day=' $DAY 'month=' $MONTH 'year=' $YEAR
DATESET=$MONTH'-'$DAY'-'$YEAR
echo 'DATESET will be:' $DATESET

######## TESTING COM WITH POS1 AND RETURN SET TIMESTAMP ########
$PYTHONPATH $MARTASPATH/app/serialinit.py -p "$YOURDEV" -b 9600 -c "mode text,range $MAINFIELDAWAITING" -x -d 0 -f True
$PYTHONPATH $MARTASPATH/app/serialinit.py -p "$YOURDEV" -b 9600 -c "run" -x -d 0 -f True > returnstring
DATEFOUND=$(more returnstring |grep -a -i 'Response' |awk -F ' ' '{print $7}') # retrieve date from POS1 found by run command return
echo 'DATEFOUND in POS1:' $DATEFOUND
if [ $DATEFOUND = $DATESET ]; then
    echo 'DATESET IS EQUAL TO FOUND IN RUNNING POS1 SYSTEM. USING GPS SYSTEM TIME ONLY.';
    $PYTHONPATH $MARTASPATH/app/serialinit.py -p "$YOURDEV" -b 9600 -c "mode text,range $MAINFIELDAWAITING,auto 5" -x -d 0 -f True;
    echo 'POS1 initilized with GPS.';
else
    echo 'DATESET IS DIFFERENT TO FOUND IN RUNNING POS1 SYSTEM. SETTING TIME MANUALLY TO NTP.';
    $PYTHONPATH $MARTASPATH/app/serialinit.py -p "$YOURDEV" -b 9600 -c "mode text,time datetime,date $MONTH-$DAY-$YEAR,range $MAINFIELDAWAITING,auto 5" -k "%H:%M:%S" -x -d 0 -f True;
    echo 'POS1 initilized with NTP from martas system.';
fi


##### MAYBE remove returnstring file from homefolder after the process ######
