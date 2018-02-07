#! /bin/sh
### BEGIN INIT INFO
# Provides:          martas
# Required-Start:    $remote_fs $syslog
# Required-Stop:     $remote_fs $syslog
# Default-Start:     2 3 4 5
# Default-Stop:      0 1 6
# Short-Description: Starts the MARTAS/acquisition.py script
# Description:       see short
#                    
### END INIT INFO

# /etc/init.d/martas

# Some BASIC definitions  # please edit
# #####################################

# # Define a python path if not using default python
PYTHONPATH='/home/cobs/anaconda2/bin/python'

# # Your Local Martas directory 
MARTASPATH='/home/cobs/MARTAS/'

# # The main acquisition program
# # Please consider the space before options if provided"
ACQU="acquisition.py"
#ACQUOPT=""
ACQUOPT=" -m /home/cobs/martas.cfg"
PIDTEST="[a]cquisition.py$ACQUOPT"
ACQUPROG="$ACQU$ACQUOPT"

# # change delay (necessary for systemstart and proper restart)
DELAY=30

# Some methods
# #####################################
check_process()
{
    # Check if the process is already running. Ignore grep line.
    result=`ps aux | grep "$ACQUPROG" | grep -v grep | wc -l`
}

get_pid()
{
    pid=`ps -ef | awk -v pattern="$PIDTEST" '$0 ~ pattern{print $2}'`
}

# Carry out specific functions when asked to by the system
# #####################################
case "$1" in
  start)
    check_process
    if [ "$result" = "1"  ]; then
       echo "$ACQUPROG is already running"
    else
       echo "Starting MARTAS acquisition script (in $DELAY sec)"
       echo "--------------------"
       sleep $DELAY
       cd $MARTASPATH
       $PYTHONPATH $ACQUPROG &
    fi
    ;;
  stop)
    check_process
    get_pid
    if [ "$result" = "0"  ]; then
       echo "$ACQUPROG is not running"
    else
       echo "Stopping MARTAS acquisition script"
       echo "--------------------"
       kill -9 $pid
       echo "... stopped"
    fi
    ;;
  status)
    check_process
    if [ "$result" = "1"  ]; then
       echo "$ACQUPROG is running"
    else
       echo "$ACQUPROG process is dead"
    fi
    ;;
  restart)
    check_process
    if [ "$result" = "0"  ]; then
       echo "$ACQUPROG is not running"
    else
       get_pid
       echo "Stopping MARTAS acquisition script"
       echo "--------------------"
       kill -9 $pid
       echo "... stopped"
    fi
    echo "Starting acquisition script martas (in $DELAY sec)"
    echo "--------------------"
    sleep $DELAY
    cd $MARTASPATH
    $PYTHONPATH $ACQUPROG &
    ;;
  *)
    echo "Usage: /etc/init.d/martas {start|stop|restart|status}"
    exit 1
    ;;
esac

exit 0
