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

# Some things that run always
touch /var/lock/martas

# Carry out specific functions when asked to by the system
case "$1" in
  start)
    echo "Starting acquisition script martas (in 20sec)"
    echo "--------------------"
    sleep 20
    echo "initializing GSM90"
    python /home/cobs/MARTAS/DataScripts/serial-init.py -p "/dev/ttyUSB0" -c S,5,T048.5,C,datetime,D,R -k "%y%m%d%w%H%M%S" -r "z-save,z" -i 1024
    #echo "initiating POS1"
    #python /home/cobs/MARTAS/DataScripts/POS1-Start.py &
    #sleep 5
    #ps -ef | grep 'POS1-Start.py' | awk '{print $2}' | xargs kill -9
    #python /home/cobs/MARTAS/DataScripts/POS1-Start.py &
    sleep 30
    echo "initiating MARTAS"
    cd /home/cobs/MARTAS
    python acquisition.py &
    ;;
  stop)
    echo "Stopping acquisition script martas"
    echo "--------------------"
    #ps -ef | grep 'POS1-Start.py' | awk '{print $2}' | xargs kill -9
    ps -ef | grep 'acquisition.py' | awk '{print $2}' | xargs kill -9
    ;;
  restart)
    echo "Stopping acquisition script martas"
    echo "--------------------"
    #ps -ef | grep 'POS1-Start.py' | awk '{print $2}' | xargs kill -9
    ps -ef | grep 'acquisition.py' | awk '{print $2}' | xargs kill -9
    echo "Restarting acquisition script martas"
    echo "--------------------"
    sleep 5
    echo "initializing GSM90"
    python /home/cobs/MARTAS/DataScripts/serial-init.py -p "/dev/ttyUSB0" -c S,5,T048.5,C,datetime,D,R -k "%y%m%d%w%H%M%S" -r "z-save,z" -i 1024
    #echo "initializing POS1"
    #python /home/cobs/MARTAS/DataScripts/POS1-Start.py &
    #sleep 5
    #ps -ef | grep 'POS1-Start.py' | awk '{print $2}' | xargs kill -9
    #python /home/cobs/MARTAS/DataScripts/POS1-Start.py &
    sleep 30
    echo "initiating MARTAS"
    cd /home/cobs/MARTAS
    python acquisition.py &
    ;;
  *)
    echo "Usage: /etc/init.d/martas {start|stop}"
    exit 1
    ;;
esac

exit 0
