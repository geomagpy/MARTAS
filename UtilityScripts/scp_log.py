#********************************************************************
### DAILY CRONJOB PROTOCOL:
###  - Sends file if has been edited in past day
###  - In cooperation with checklog.sh
#********************************************************************

import time, os, sys
from datetime import datetime
from socket import gethostname

from magpy.transfer import *

station = gethostname()

# Copy files to databank:
# TODO: add the credential function

src = 	"/home/cobs/MARTAS/"+station.upper()
dest = 	"user@adress:/srv/archive/magnetism/wic/StationLogs"
passwd = "secret"
scptransfer(src,dest,passwd)
