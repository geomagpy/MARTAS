MARTAS - new (October 2017)

MARTAS now uses MQTT as main protocol
Developers: R. Leonhardt (ZAMG)

MARTAS = Magpy Automated Real Time Acquisition System

########
Changes:
########

version 0.1 (October 2017)
   * imported existing MARTAS 0012 


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

All installation instructions assume a linux (debian-like) system.
Although MARTAS is platform independent, it is currently only tested and used
on debian like LINUX systems. 

    Required packages:
    - Geomagpy >= 0.3.97 (and its requirements)
        sudo pip install geomagpy
    - mosquitto (MQTT client)
        sudo apt-get install mosquitto mosquitto-clients
    - paho-mqtt (MQTT python)
        sudo pip install paho-mqtt

1.1 Cloning MARTAS:
###########################

Get all neccessary MARTAS files by one of the following techniques:
a) clone the MARTAS repository to your local hard disk (requires git)

        user@home:~$ git clone https://github.com/geomagpy/MARTAS.git

b) download the MARTAS archive and unpack it  

        user@home:~$ wget ...
        user@home:~$ tar -zxvf martas.tar.gz
        

1.2 MQTT installation:
###########################

MARTAS makes use of certain IOT protocols for real-time data transfer.
Currently supported are WAMP (decrepated) and MQTT. In the following you will find some instructions
on how to get MQTT running on your acquisition machine.

You only need to install the required packages as listed above. Thats it.


1.3 Authentication:
###########################

Authentication and secure data communication are supported by MARTAS. In order to enable
authentication and SSL encryption for accessing data streams from your acquisition machine please check the following web page:
https://www.digitalocean.com/community/tutorials/how-to-install-and-secure-the-mosquitto-mqtt-messaging-broker-on-ubuntu-16-04

For quickly enabling authentication you can also use the following instructions (without ssl encrytion of data transfer): 

    Adding user/password:
    ---------------------

    Add a user and a password file to the MQTT broker (is encrypted):

        user@home:~$ sudo mosquitto_passwd -c /etc/mosquitto/passwd myuser

    Then use command

        user@home:~$ sudo nano /etc/mosquitto/conf.d/default.conf

    to open an empty file. 

    Paste in the following:
        allow_anonymous false
        password_file /etc/mosquitto/passwd

Thats it. How to use credentials in MARTAS is described in section 3.4.

# -------------------------------------------------------------------
2. Strucure/Files in home directory of MARTAS user
# -------------------------------------------------------------------

All necessary files are found within the MARTAS directory 
	SYSTEMNAME:  			(e.g. RASPBERRYONE, CERES) contains a description of the system and a history of changes made to it
        acquisition_mqtt.py:		the main program

        index.html:			HTML script for visualization - accessed by localhost:8080

        README.md:			You are here.
        sensors.cfg:			sensors configuration information
        martas.cfg:			basic MARTAS confifuration

        acquisition.py:                 should accept options (-s sensors.cfg, -m martas.cfg, -c cred)
        collector.py:                   should accept options (-s sensors.cfg, -m martas.cfg, -c cred)

	DataScripts/convert.py:		converts MARTAS binary buffer files to ascii
	DataScripts/senddata.py:	Send data from MARTAS to any other machine using cron/scheduler


	DataScripts/palmacq-init.py:	Necessary for initiating PALMAQ/OBSDAC 
                                               - specifications in commands.txt
	DataScripts/commands.txt:	Commands for initiating PALMAQ/OBSDAC 

	Logs/martas.log:		MARTAS standard logging file for acquisition
	Logs/martas:			sceleton file to be modified and copied to /etc/logrotate.d

	Nagios/add2nrpe.cfg:		command to check for martas process for nagios (client side, requires nrpe)
	Nagios/add2server.cfg:		service description to add on the cfg file (server side)

	OldVersions/...:		Folder for storage of old SYSTEMNAME log files

	UtilityScripts/addcred.py:	run to add protected credentials to be used e.g. by data sending protocol
	UtilityScripts/cleanup.sh:      remove buffer files older than a definite period
	UtilityScripts/martas.sh:	to be run at boot time for starting the acquisition
	UtilityScripts/sendip.py:	Helper for checking and sending (via ftp) public IP

 	WebScripts/autobahn.min.js:	required for index.html 
 	WebScripts/autobahn.sensors.js:	required for index.html 
        WebScripts/magpy.func.js:       required for index.html
        WebScripts/magpy.sensors.js:    required for index.html
	WebScripts/smoothie.js:		required for index.html

	examples/...:			contains some examples for above mentioned files
	

# -------------------------------------------------------------------
3. Running the acquisition module
# -------------------------------------------------------------------

3.1 Basic setup:
###########################

a) Modify MARTAS/martas.cfg

   - please note that the path to sensors.cfg is defined within this file

b) Modify MARTAS/sensors.cfg


3.2 Running the acquisition sytem
##################################


a) Command line

        user@home:~$ python acquisition.py

    acquisition.py automatically chooses cfg files from the same directory. You can use other parameter
    files using:

        user@home:~$ python acquisition.py -m /home/myuser/MARTAS/martas.cfg

b) Autostart

    check out the example startscript 'martas.sh' in folder UtilityScripts

OPTION 1 - recommended - Using a bootscript (e.g. debian, rasbian, ubuntu etc)
	$ sudo cp martas.sh /etc/init.d/martas
	$ sudo chmod 755 /etc/init.d/martas
	$ sudo chown root:root /etc/init.d/martas
	$ sudo update-rc.d martas defaults

To remove:
	$ sudo update-rc.d -f  martas remove

Starting up MARTAS:
within ~/MARTAS do:
sudo /etc/init.d/martas start

3.3 OPTIONAL modifications
##########################

Edit the Utility scripts (cleanup and logfile applications) according to your needs. Use cron to schedule them.

a) Remove all data buffer files older then 100 days:
    - edit cleanup.sh. It should read:
	find /srv/mqtt -name "*.bin" -ctime +100 -exec rm {} \;
    - edit crontab to schedule this job once a day
	$ sudo crontab -e
	Add this line (don't forget to modify the path):
	15 0 * * * sh /home/mydir/MARTAS/UtilityScripts/cleanup.sh
	# to run the job every day 15 minutes past midnight

b) Get human readable data out of files:
    - OPTION 1: Use MagPy (see examples)
    - OPTION 2: Use the included convert.py routine. convert.py -h for a description of usage

c) Poll for change of public IP (useful for WiFi/UMTS connection):
    - edit paths in UtlityScripts/sendip.py to your own FTP server (if using)
    - Add call into crontab (as often as needed):
	$ crontab -e
	Something like this (for hourly polling):
	1 */1 * * * python ~/MARTAS/UtilityScripts/sendip.py

d) Activate logrotation
    - edit /MARTAS/Logs/martas (check logrotate WIKI)
    - do (on ubuntu and most other Linux versions):
        sudo cp martas /etc/logrotate.d/
        sudo chmod 644 /etc/logrotate.d/martas
        sudo chown root:root /etc/logrotate.d/martas


3.4 Enabling Authentication
##########################

BROKER:

    Input the user defined in 1.3 into martas.cfg:

        ...
        mqttuser : myuser
        ...

    a)
    When running acquistion.py you will be asked to provide the mqtt password.

        user@home:~$ python acquisition_mqtt.py -m /home/cobs/martas.cfg
        MQTT Authentication required for User cobs:
        Password: 

    b)
    or you provide it directly

        user@home:~$ python acquisition_mqtt.py -m /home/cobs/martas.cfg -P mypasswd

    c)
    Alternative: You can use addcred.py (UtilityScripts) to add user and passwd to the magpy credentials
    is 'myuser' is found as credential name, the asociated passwd is automatically used 

        user@home:~$ python addcred.py -t transfer -c mqtt -u myuser -p mypasswd -a localhost
    for super user:
        user@home:~$ sudo python addcred.py -t transfer -c mqtt -u myuser -p mypasswd -a localhost

    Then you can use 
        user@home:~$ python acquisition_mqtt.py -m /home/cobs/martas.cfg -c mqtt
    and avoid plain text usage of passwords anywhere on your system.

    Please note: if you are using autostart/init scripts the alternative technqiue should be preferred

COLLECTOR:

    Run the collector with user option:

        python collector.py -b brokeradress -u myuser -P mypassword

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



# -------------------------------------------------------------------
6. protocol specific configurations
# -------------------------------------------------------------------

6.1. OW (One wire) support

a) modify owfs,conf
cobs@xxx$ sudo nano /etc/owfs.conf 

# ...and owserver uses the real hardware, by default fake devices
# This part must be changed on real installation
#server: FAKE = DS18S20,DS2405
#
# USB device: DS9490
server: usb = all
#

b) start the owserver
cobs@xxx$ sudo etc/init.d/owserver start 


