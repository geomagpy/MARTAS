THISPC=$(echo $(hostname) | tr 'a-z' 'A-Z')
FILENAME="/home/cobs/MARTAS/$THISPC"
FILEMTIME=`stat -c %Y $FILENAME`
CURRTIME=`date +%s`
AGE=$((CURRTIME-FILEMTIME))
DAY=$((60*60*24))

echo $THISPC
echo $FILENAME

# If file has been changed in the last day, upload it...
if [ "$AGE" -lt "$DAY" ]
then
    python /home/cobs/MARTAS/UtilityScripts/scp_log.py
fi
