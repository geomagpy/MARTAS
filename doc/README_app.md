# MARTAS 

**MagPys Automated Real Time Acquisition System**

**app - application directory**

Developers: R. Leonhardt, R. Mandl, R. Bailey (ZAMG)

Note: in the folling examples we use "user" as username and "users" as group.
Replace these names with your user:group names.

## 1. Overview

The following apps are contained:
(sorted firstly accordinng primary affiliation to MARTAS/MARCOS)

### 1.1 MARTAS apps (acquisition system)

        serialinit.py:		Load initialization file (in init) to activate
                                continuous serial data delivery (passive mode)
        senddata.py:		Send data by ftp/scp from MARTAS to any other machine using cron/scheduler
        sendip.py:		Helper for checking and sending public IP  (via ftp)

        cleanup.sh:		Bash script, remove buffer files older than a definite period

        ardcomm.py:		Small program to check serial communication
        testserial.py:		Small program to check serial communication


### 1.2 MARCOS apps (collector system)

        collectfile.py:		Download files from local/remote machines using various protocols
                                like cp/ftp/scp. Usually called by cron jobs.


### 1.3 MARTAS and MARCOS

        addcred.py:		Run to add encrypted credentials to be used e.g. 
				by data sending protocol

        mpconvert.py (decrapted):	converts MARTAS binary buffer files to other formats
                                (please use MagPy's mpconvert (since 0.4.0))


## 2 Detailed description of each app

Sorted alphabetically:

