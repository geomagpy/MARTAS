MARTAS - new (October 2017)

MARTAS now uses MQTT as main protocol
Developers: R. Leonhardt (ZAMG)

MARTAS = Magpy Automated Real Time Acquisition System

########
Changes:
########

version 0012 (March 2017)
   * added support for BM35
   * serial-init script supports BM35, POS1 and GSM90

version 0011 (May 2015)
   * added logrotate script for martas.log

version 0010 (March 2015)
   * added Mingeo PALMAQ/OBSDAC support
   * adding preliminary GSM19 support 
               (not yet finished and not contained in the maypy acquisition folder)

version 0009 (February 2015)
   * corrected GSM shortcut to gsm#... Testing GSM19 
   * added Arduino support 

version 0008 (November 2014)
   * added GSM initialization script to DataScripts and links to martas.sh

version 0007 (October 2014)
   * added scripts and input for kern balance. modified acquisition (by adding parity and bytesize option), index, and magpy.xx webscripts for that reason
   * changed ctime in cleanup to mtime because this is more relevant for data content

version 0006 (September 2014)
   * modified senddata.py app: dateformat and extension now freely choseable, zipping is possible
                               corrected wrong amount of days option

version 0005 (July 2014):
   ...


##########################
MINI TO-DO:
- add trigger mode for GSM90 (sending f)
- add to #5
- update scp_log to use protected creds
- add in how-to for using senddata and addcreds
##########################


#####################################################################
         Setup and Structure of Acquisition Units (MARTAS)
#####################################################################

# -------------------------------------------------------------------
1. Installation requirements
# -------------------------------------------------------------------
	Required packages:
	- Geomagpy >= 0.3.97 (and its requirements)
		python = 2.7.x, Matplotlib >= 1.0.0, SciPy, NumPy
                optional: spacepy >= 1.3


# -------------------------------------------------------------------
2. Strucure/Files in home directory of MARTAS user
# -------------------------------------------------------------------

All necessary files are found within the MARTAS directory 
	SYSTEMNAME:  			(e.g. RASPBERRYONE, CERES) contains a description of the system and a history of changes made to it
        acquisition_mqtt.py:			the main program for data aquisition (please open and modify user specific variables according to your requirements)
        index.html:			HTML script for visualization - accessed by localhost:8080 
	README.md:			You are here.
	sensors.cfg:			sensors confifuration information
	martas.cfg:			basic MARTAS confifuration

	DataScripts/convert.py:		converts MARTAS binary buffer files to ascii
	DataScripts/POS1-Start.py:	Necessary for initiating POS-1 Overhauzer sensors
	DataScripts/senddata.py:	Send data from MARTAS to any other machine using cron/scheduler
	DataScripts/gsm-init.py:	Necessary for initiating GSM90 Overhauzer sensors
	DataScripts/palmacq-init.py:	Necessary for initiating PALMAQ/OBSDAC 
                                               - specifications in commands.txt
	DataScripts/commands.txt:	Commands for initiating PALMAQ/OBSDAC 

	Logs/martas.log:		MARTAS standard logging file for acquisition
	Logs/martas:			sceleton file to be modified and copied to /etc/logrotate.d

	Nagios/add2nrpe.cfg:		command to check for martas process for nagios (client side, requires nrpe)
	Nagios/add2server.cfg:		service description to add on the cfg file (server side)

	OldVersions/...:		Folder for storage of old SYSTEMNAME log files

	UtilityScripts/addcred.py:	run to add protected credentials to be used e.g. by data sending protocol
	UtilityScripts/checklog.sh:     check for changes to log files and send them to server
	UtilityScripts/cleanup.sh:      remove buffer files older than a definite period
	UtilityScripts/martas.conf:     to be run at boot time using upstart (alternative to martas.sh)
	UtilityScripts/martas.sh:	to be run at boot time for starting the acquisition
	UtilityScripts/scp_log.py:      helper method for checklog
	UtilityScripts/sendip.py:	Helper for checking and sending (via ftp) public IP

 	WebScripts/autobahn.min.js:	required for index.html 
 	WebScripts/autobahn.sensors.js:	required for index.html 
        WebScripts/magpy.func.js:       required for index.html
        WebScripts/magpy.sensors.js:    required for index.html
	WebScripts/smoothie.js:		required for index.html

	examples/...:			contains some examples for above mentioned files
	

# -------------------------------------------------------------------
3. Setting up the system
# -------------------------------------------------------------------

3.1 REQUIRED modifications:
###########################

a) Edit MARTAS/sensors.txt to contain all required sensor info.
The SENSORPORT code will be found under /dev/tty***.
Use following format (data separated by TABS):

# -------------------------------------------------------------
# Read data of sensors attached to PC:
# 
# "Sensors.txt" should have the following format:
# SENSORNAME	SENSORPORT	SENSORBAUDRATE
# e.g:
# LEMI036_1_0001	USB0	57600
# POS1_N432_0001	S0	9600
# ARDUINO		ACM0	9600
# OW			-	-
#
# Notes: OneWire devices do not need this data, all others do.
# -------------------------------------------------------------

b) Edit the SYSTEMNAME file and rename to own system name:
Insert system information and keep it.

c) Edit acquisition.py:
Edit the user specific information and paths (beginning at line 53)

d) Edit index.html:
Insert the name of your martas client in:
	var client = 'my_martas_name' 

e) Edit martas.conf (and/or martas.sh):
Paths need to be adjusted.


3.2 STARTING the acquisition sytem
##################################

OPTION 1 - recommended - Using a bootscript (e.g. debian, rasbian, ubuntu etc)
	$ sudo cp martas.sh /etc/init.d/martas
	$ sudo chmod 755 /etc/init.d/martas
	$ sudo chown root:root /etc/init.d/martas
	$ sudo update-rc.d martas defaults

To remove:
	$ sudo update-rc.d -f  martas remove

OPTION 2 - Using startup (e.g. ubuntu)
	$ sudo cp martas.conf /etc/init/
	$ sudo chmod 755 /etc/init/martas.conf
	$ sudo chown root:root /etc/init.d/martas.conf
	$ sudo service martas start  (restart, stop) (please note the sleep interval)

To remove:
	$ sudo rm /etc/init/martas.conf


Starting up MARTAS:
within ~/MARTAS do:
sudo /etc/init.d/martas start

3.3 OPTIONAL modifications
##########################

Edit the Utility scripts (cleanup and logfile applications) according to your needs. Use cron to schedule them.

a) Remove all data buffer files older then 100 days:
    - edit cleanup.sh. It should read:
	find /srv/ws -name "*.bin" -ctime +100 -exec rm {} \;
    - edit crontab to schedule this job once a day
	$ sudo crontab -e
	Add this line (don't forget to modify the path):
	15 0 * * * sh /home/mydir/MARTAS/UtilityScripts/cleanup.sh
	# to run the job every day 15 minutes past midnight

b) Upload log file to defined destination whenever it changes:
    - change the paths in checklog.sh
    - change the destination path and credentials in scp_log.py

c) Get human readable data out of files:
    - OPTION 1: Use MagPy (see examples)
    - OPTION 2: Use the included convert.py routine. convert.py -h for a description of usage

d) Poll for change of public IP (useful for WiFi/UMTS connection):
    - edit paths in UtlityScripts/sendip.py to your own FTP server (if using)
    - Add call into crontab (as often as needed):
	$ crontab -e
	Something like this (for hourly polling):
	1 */1 * * * python ~/MARTAS/UtilityScripts/sendip.py

e) Activate logrotation
    - edit /MARTAS/Logs/martas (check logrotate WIKI)
    - do (on ubuntu and most other Linux versions):
        sudo cp martas /etc/logrotate.d/
        sudo chmod 644 /etc/logrotate.d/martas
        sudo chown root:root /etc/logrotate.d/martas


# -------------------------------------------------------------------
4. Customizing the WEB interface of the MARTAS client
# -------------------------------------------------------------------

a) Edit index.html and put in the correct client name ... that's it.
    var client = 'name_of_my_martas'

b) Open a browser, e.g. firefox.

c) Enter this address: localhost:8080
     (if you are on a remote machine use ipnumber:8080 e.g. 192.168.0.100:8080 )

d) Be astonished. 
	(if not check whether you started the script within the MARTAS homedirectory.
	And is apache installed and running?)


# -------------------------------------------------------------------
5. For those who read to the end before doing any changes
# -------------------------------------------------------------------

Just modify the code below and copy it to a terminal window - within your martas homedirectory to make all necessary parameter changes in all files. 

# TODO: write a small install script which sets paths and names correctly

