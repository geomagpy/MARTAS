# MARTAS 

**MagPys Automated Real Time Acquisition System**

MARTAS is collection of python applications and packages supporting data acquisition,
collection, storage, monitoring and analysis in heterogenuous sensor environments. 
MARTAS is optimzed for professional observatory networks. Data acquisition makes use
of an instrument library which currently supports many sensors typically used in 
observatories arround the globe and some development platforms. Basically, incoming 
sensor data is converted to a general purpose data/meta information object which 
is directly streamed via MQTT (message queue transport) to a data broker (also contained).
The collection routines, coming along with MARTAS, can access such data stream and 
store/organize such data and meta information in files, data banks or forward
them to web sockets etc. All data can directly be analyszed using MagPy which 
contains many time domain and frequency domain time series anaylsis methods.  

Developers: R. Leonhardt, R. Mandl, R. Bailey (ZAMG)

Note: in the folling examples we use "user" as username and "users" as group.
Replace these names with your user:group names.

## 1. INSTALLTION

### 1.1 Installation requirements

All installation instructions assume a linux (debian-like) system.
Although MARTAS is platform independent, it is currently only tested and used
on debian like LINUX systems. 

    PYTHON:
    - tested and running on python 2.7
    - some unicode/string issues open for 3.x compatibility (work in progress)

    Required packages:
    - Geomagpy >= 0.3.97 (and its requirements)
        sudo pip install geomagpy
    - mosquitto (MQTT client - broker)
        sudo apt-get install mosquitto mosquitto-clients
    - paho-mqtt (MQTT python)
        sudo pip install paho-mqtt
    - pyserial 
        sudo pip install pyserial
    - twisted 
        sudo pip install twisted
        sudo pip install service_identity

    Optional packages:
    - pyownet  (one wire support) 
        sudo pip install pyownet


### 1.2 Getting MARTAS

Get all neccessary MARTAS files by one of the following techniques:
a) clone the MARTAS repository to your home folder (requires git)

        $ git clone https://github.com/geomagpy/MARTAS.git

b) download the MARTAS archive and unpack it  

        $ wget ...
        $ tar -zxvf martas.tar.gz
        
### 1.3 INSTALL MQTT

MARTAS makes use of certain IOT protocols for real-time data transfer.
Currently supported are WAMP (decrepated) and MQTT. In the following you will find some instructions
on how to get MQTT running on your acquisition machine.

You only need to install the required packages as listed above. Thats it.


### 1.3 Enabling authentication

Authentication and secure data communication are supported by MARTAS. In order to enable
authentication and SSL encryption for accessing data streams from your acquisition machine please check the following web page:
https://www.digitalocean.com/community/tutorials/how-to-install-and-secure-the-mosquitto-mqtt-messaging-broker-on-ubuntu-16-04

For quickly enabling authentication you can also use the following instructions (without ssl encrytion of data transfer): 

    Adding user/password:
    ---------------------

    Add a user and a password file to the MQTT broker (is encrypted):

        $ sudo mosquitto_passwd -c /etc/mosquitto/passwd user

    Then use command

        $ sudo nano /etc/mosquitto/conf.d/default.conf

    to open an empty file. 

    Paste in the following:
        allow_anonymous false
        password_file /etc/mosquitto/passwd

    Restart mosquitto
Thats it. How to use credentials in MARTAS is described in section 3.4.


## 2. Setting up MARTAS

### 2.1 Basic setup:

a) Use the MARTAS installation script
        
        $ cd /path/to/MARTAS/install
        $ sudo sh martas.install.sh
      -> follow the instructions

b) Modify /etc/martas/sensors.cfg

        $ nano /etc/martas/sensors.cfg


c) Manually: 
      -> Copy configuration files to your home directory
        $ cd /home/user/MARTAS/conf
        $ cp martas.cfg ~ 
        $ cp sensors.cfg ~ 

      -> Modify MARTAS/martas.cfg
      -> Please note that the path to sensors.cfg is defined within this file
        $ nano martas.cfg
        $ nano sensors.cfg

d) Logging to /var/log/magpy/martas.log (recommended)
        $ cd /var/log/ 
        $ sudo mkdir magpy
        $ sudo chown user:users magpy


### 2.2 Running the acquisition sytem

a) Command line

        $ python acquisition.py

    acquisition.py automatically chooses cfg files from the same directory. You can use other parameter
    files using:

        $ python acquisition.py -m /home/user/martas.cfg

b) Autostart (recommended)

    - Go to /home/user/MARTAS/init:
        $ cd /home/user/MARTAS/init
    
    - Modify initialization routine:
      Change Pythonpath and paths to cfg files
        $ nano martas.sh
      If you are going to use authentication you need to add
      option -c credential!

    - Activate autostart:
        $ sudo ./autostart.sh

    - To remove:
        $ sudo update-rc.d -f  martas remove

    - Thef following options are now available:
        $ sudo /etc/init.d/martas status
        $ sudo /etc/init.d/martas start
        $ sudo /etc/init.d/martas restart
        $ sudo /etc/init.d/martas stop

## 3 EXPERTS settings

Edit the Utility scripts (cleanup and logfile applications) according to your needs. Use cron to schedule them.

### 3.1 Remove all data buffer files older then 100 days
    - edit cleanup.sh. It should read:
	find /srv/mqtt -name "*.bin" -ctime +100 -exec rm {} \;
    - edit crontab to schedule this job once a day
	$ sudo crontab -e
	Add this line (don't forget to modify the path):
	15 0 * * * sh /home/user/MARTAS/app/cleanup.sh
	# to run the job every day 15 minutes past midnight

### 3.2 Activate logrotation
    - edit /MARTAS/Logs/martas (check logrotate WIKI)
    - do (on ubuntu and most other Linux versions):
        $ cd ~/MARTAS/app/
    - modify log file paths and critical sizes
        $ nano martas.logrotate
        $ sudo cp martas.logrotate /etc/logrotate.d/martas
        $ sudo chmod 644 /etc/logrotate.d/martas
        $ sudo chown root:root /etc/logrotate.d/martas

### 3.3  Poll for change of public IP (useful for WiFi/UMTS connection):
    - edit paths in UtlityScripts/sendip.py to your own FTP server (if using)
    - Add call into crontab (as often as needed):
	$ crontab -e
	Something like this (for hourly polling):
	1 */1 * * * python ~/MARTAS/UtilityScripts/sendip.py


### 3.4 Enabling Authentication

BROKER:

    Input the user defined in 1.3 into martas.cfg:

        ...
        mqttuser : user
        ...

    a)
    When running acquistion.py you will be asked to provide the mqtt password.

        $ python acquisition_mqtt.py -m /home/cobs/martas.cfg
        MQTT Authentication required for User cobs:
        Password: 

    b)
    or you provide it directly

        $ python acquisition_mqtt.py -m /home/cobs/martas.cfg -P mypasswd

    c)
    Alternative: You can use addcred.py (UtilityScripts) to add user and passwd to the magpy credentials
    is 'user' is found as credential name, the asociated passwd is automatically used 

        $ python addcred.py -t transfer -c mqtt -u user -p mypasswd -a localhost
    for super user:
        $ sudo python addcred.py -t transfer -c mqtt -u user -p mypasswd -a localhost

    When you inserted the same username in martas.cfg as outline above, then everything is working fine.

    Alternatively, you can also use 
        $ python acquisition_mqtt.py -m /home/cobs/martas.cfg -c mqtt
    and avoid plain text usage of passwords anywhere on your system.

    Please note: if you are using autostart/init scripts the alternative technique (c) should be preferred
    IMPORTANT: you have to add  -c mqtt in the martas script.

COLLECTOR:

    Run the collector with user option:

        python collector.py -b brokeradress -u myuser -P mypassword



## 4. Strucure/Files in home directory of MARTAS user

Within the MARTAS directory you will find the following files and programs:

        acquisition.py:                 accepts options (-h for help)
        collector.py:                   accepts options (-h for help)

        README.md:			You are here.
        LICENSE.md:			GNU GPL 3.0 License

        conf/sensors.cfg:		sensors configuration information
        conf/martas.cfg:		basic MARTAS confifuration -> acquisition
        conf/marcos.cfg:		basic MARCOS confifuration -> collector

        init/martas.sh:			Start script to be used in /etc/init.d
        init/autostart.sh:		Run to add and sctivate /etc/init.d/martas
        init/martas.logrotate:		Example script to activate logrotation
        init/gsm90v7init.sh:		Initialization script GEM GSM90 v7
        init/gsm90v6init.sh:		Initialization script GEM GSM90 v6
        init/pos1init.sh:		Initialization script Quantum POS1 
        init/bm35init.sh:		Initialization script Meteolab BM35 pressure
        ...

        install/install.marcos.sh:	Installer for collector jobs 
        install/install.martas.sh:	Installer for acquisition jobs

        app/serialinit.py:		Load initialization file (in init) to activate
                                        continuous serial data delivery (passive mode)
        app/addcred.py:			run to add protected credentials to be used e.g. 
					by data sending protocol
        app/senddata.py:		Send data from MARTAS to any other machine using cron/scheduler
        app/cleanup.sh:			remove buffer files older than a definite period
        app/sendip.py:			Helper for checking and sending public IP  (via ftp)
        app/mpconvert.py:		converts MARTAS binary buffer files to other formats
        app/collectfile.py:		access data locally or via ssh/ftp and add it to files/DB

        libmqtt/...:			library for supported instruments (mqtt streaming)        
        libwamp/...:			library for sup. inst. (wamp streaming) - DISCONTINUED        

        web/index.html:			local main page 
        web/plotws.js:		  	arranging plots of real time diagrams on html page
        web/smoothie.js:		plotting library/program (http://smoothiecharts.org/)
        web/smoothiesettings.js:        define settings for real time plots

        oldstuff/...:		        Folder for old contents and earlier versions


## 5. Using the Webinterface

### 5.1 Starting a WEB interface on the MARTAS client

a) Starting websocket transfer on MARTAS
        $ cd ~/MARTAS
        $ python collector -d websocket -o mystation
      If authentication is used: 
        $ python collector -d websocket -o mystation -u user -P password

b) accessing websocket
      Connect to the MATRTAS machine from remote:
      On any machine which can access defined websocket port you can now open
      the following url in a browser of your choice:
      (Pleas replace "ip_of_martas" with the real IP-address or url name.

        http://ip_of_martas:8080
      
### 5.2 Customizing the WEB interface/ports of the MARTAS client

a) Modifying ports and paths - modify marcos.cfg
        $ python collector -m /path/to/marcos.cfg
      Here you can change default port (8080) and many other parameters.

b) Customizing graphs and layout
      Modify smoothiesettings.js:
        $ nano ~/MARTAS/web/smoothiesettings.js

## 6. protocol specific configurations

### 6.1. OW (One wire) support

a) modify owfs,conf
        $ sudo nano /etc/owfs.conf 

      Modify the following parts as shown below:
        #This part must be changed on real installation
        #server: FAKE = DS18S20,DS2405

        # USB device: DS9490
        server: usb = all

b) start the owserver
        $ sudo etc/init.d/owserver start 


### TODO

- add trigger mode for GSM90 (sending f)
- add to #5
- update scp_log to use protected creds
- add in how-to for using senddata and addcreds




