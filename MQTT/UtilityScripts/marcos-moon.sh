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

# /etc/init.d/marcos-moon

# Some BASIC definitions  # please edit
# #####################################

# # Define a python path if not using default python
PYTHONPATH="/home/cobs/anaconda2/bin/python"
# # Your Local MARCOS directory 
MARCOSPATH="/home/cobs/MARCOS"
# # IP/address of BROKER
IPBROKER="138.22.188.186"
# # The main acquisition program
COLLECTOR="collector.py"
COLLECTOROPT=" -b $IPBROKER -d db -r cobsdb"
COLLECTORPROG="$COLLECTOR$COLLECTOROPT"
# # change delay (necessary for systemstart and proper restart)
DELAY=5

# Some methods
# #####################################
check_process()
{
    # Check if the process is already running. Ignore grep line.
    result=`ps aux | grep "$COLLECTORPROG" | grep -v grep | wc -l`
}

get_pid()
{
    PIDTEST="[c]ollector.py -b $IPBROKER"
    pid=`ps -ef | awk -v pattern="$PIDTEST" '$0 ~ pattern{print $2}'`
}

# Carry out specific functions when asked to by the system
# #####################################
case "$1" in
  start)
    check_process
    if [ "$result" = "1"  ]; then
       echo "$COLLECTORPROG is already running"
    else
       echo "Starting MARCOS collection script (in $DELAY sec)"
       echo "--------------------"
       sleep $DELAY
       cd $MARCOSPATH
       $PYTHONPATH $COLLECTORPROG &
    fi
    ;;
  stop)
    check_process
    get_pid
    if [ "$result" = "0"  ]; then
       echo "$COLLECTORPROG is not running"
    else
       echo "Stopping MARCOS collection script"
       echo "--------------------"
       kill -9 $pid
       echo "... stopped"
    fi
    ;;
  status)
    check_process
    if [ "$result" = "1"  ]; then
       echo "$COLLECTORPROG is running"
    else
       echo "$COLLECTORPROG process is dead"
    fi
    ;;
  restart)
    check_process
    if [ "$result" = "0"  ]; then
       echo "$COLLECTORPROG is not running"
    else
       get_pid
       echo "Stopping MARCOS acquisition script"
       echo "--------------------"
       kill -9 $pid
       echo "... stopped"
    fi
    echo "Starting collection script marcos (in $DELAY sec)"
    echo "--------------------"
    sleep $DELAY
    cd $MARCOSPATH
    $PYTHONPATH $COLLECTORPROG &
    ;;
  *)
    echo "Usage: /etc/init.d/martas {start|stop|restart|status}"
    exit 1
    ;;
esac

exit 0
