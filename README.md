# MARTAS 

**MagPys Automated Real Time Acquisition System**

MARTAS is collection of python applications and packages supporting data acquisition,
collection, storage, monitoring and analysis in heterogenuous sensor environments. 
MARTAS is designed to support professional observatory networks. Data acquisition makes use
of an instrument library which currently includes many sensors typically used in 
observatories arround the globe and some development platforms. Basically, incoming 
sensor data is converted to a general purpose data/meta information object which 
is directly streamed via MQTT (message queue transport) to a data broker. Such data broker, called MARCOS (MagPys Automated Realtime Collector and Organization System), can be setup within the MARTAS environment. These collection routines, coming along with MARTAS, can access such data stream and store/organize such data and meta information in files, data banks or forward
them to web sockets. All data can directly be analyszed using MagPy which 
contains many time domain and frequency domain time series anaylsis methods.

Developers: R. Leonhardt, R. Mandl, R. Bailey (ZAMG)

## 1. Introduction

MARTAS has originally been developed to support realtime geomagnetic data acqusition. The principle idea was to provide a unique platform to obtain data from serial interfaces, and to stream and record this data within a generalized format to a data archive. Previously any system connected via serial interface to a recording computer was registered by its own software usually in a company specific format. Intercomparison of such data, extraction of meta information and basically any analysis requiring different sources is significantly hampered. 
MARTAS contains a communication library which supports many commonly used instruments as listed below. With these libraries, data AND meta information is obtained from connected sensors. This data is then converted to a data stream containing essential meta information. This data stream has a general format which can be used for basically every imaginable timeseries. The data stream is broadcasted/published on a messaging queue transport type (MQTT) broker, a state-of-the-art standard protocol of the Internet-of-Things (IOT). A receiver contained in the MARTAS package (MARCOS - MagPys Automated Realtime Collector and Organization System) subscribes to such data streams and allows to store this data in various different archiving types (files, databases). Various logging methods, comparison functions, threshold tickers, and process communication routines complement the MARTAS package.

Currently supported systems are:

- Lemi025,Lemi036, and most likely all other Lemi systems; 
- Geometrics Sytems GSM90, GSM19;
- Quantum Magnetometer Systems POS-1, POS-4
- Meteolabs BM35 pressure
- Thiess LaserNiederschlagsMessgerät - Disdrometer
- AD7714 general ADC
- MinGeo PalmDac 24 bit data logger (under development)
- Campbell Scientific CR800, CR1000 Data loggesr
- ENV05 Environment sensors
- MySQL/MariaDB databases
- Dallas OneWire Sensors

and basically all I2C Sensors and others connectable to a Arduino Microcontroller board
(requiring a specific serial output format in the self writte microcontroller program - appendix)


Note: in the folling examples we use "user" as username and "users" as group.
Replace these names with your user:group names.


## 2. INSTALLTION

### 2.1 Installation requirements

All installation instructions assume a linux (debian-like) system.
Although MARTAS is platform independent, it is currently only tested and used
on debian like LINUX systems. 

    PYTHON:
    - tested and running on python 2.7/3.x (some libraries are currently upgraded to 3.x)
    - any future development will be directed to python 3.x

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
        sudo apt-get install owserver


### 2.2 Getting MARTAS

Get all neccessary MARTAS files by one of the following techniques:
a) clone the MARTAS repository to your home folder (requires git)

        $ git clone https://github.com/geomagpy/MARTAS.git

b) or go to the GITHUB directory and download the MARTAS archive

        https://github.com/geomagpy/MARTAS
        
### 2.3 INSTALL MQTT

MARTAS makes use of certain IOT protocols for real-time data transfer.
Currently fully supported is MQTT. In the following you will find some instructions
on how to get MQTT running on your acquisition machine.

If you dont need authentication you are fine already (continue with section 2). You only need to install the required packages as listed above. Thats it.


### 2.3 Enabling authentication

Authentication and secure data communication are supported by MARTAS. In order to enable
authentication and SSL encryption for accessing data streams from your acquisition machine please check mosqitto instructions like the following web page:
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
Thats it. How to use credentials in MARTAS is described in section 3.1.


## 3. Setting up MARTAS

In the following we are setting up MARTAS to acquire measurement data from any connected system, to store it locally within a buffer directory and to permanenty stream it to a data broker. In the examples, we will use the same MARTAS system as data broker. 

### 3.1 Basic setup:

a) Use the MARTAS installation script
        
        $ cd /path/to/MARTAS/install
        $ sudo sh martas.install.sh
      -> follow the instructions

b) Modify /etc/martas/sensors.cfg

        $ nano /etc/martas/sensors.cfg

      -> IMPORTANT: sensorids should only contain basic characters like 0,1,2,..9,a,b,...,z,A,B,...,Z (no special characters, no underscors, no minus etc)
      -> IMPORTANT: sensorids should not contain the phrases "data", "meta" or "dict" 

c) Check /etc/martas/martas.cfg 

        $ nano /etc/martas/martas.cfg


### 3.2 Running the acquisition sytem

a) When installation is finished you can start the system as follows:

        $ sudo /etc/init.d/martas start

    - The following options are now available:
        $ sudo /etc/init.d/martas status
        $ sudo /etc/init.d/martas start
        $ sudo /etc/init.d/martas restart
        $ sudo /etc/init.d/martas stop

b) Command line

        $ python acquisition.py

    acquisition.py automatically chooses cfg files from the same directory. You can use other parameter
    files using:

        $ python acquisition.py -m /home/user/martas.cfg

c) Adding a cleanup for the bufferdirectory

   Principally, all data is buffered in binary files, by default within the /srv/mqtt directory.
   You can mount a SD card or external memory as such a bufferdirectory.
   In order to prevent an overflow of the local file system you can also activate a cleanup job
   to remove old files from the buffer directory.

   Add the following line to /etc/crontab

	15 0 * * * root sh /home/user/MARTAS/app/cleanup.sh

   Edit cleanup.sh to fit your needs. By default it reads (deleting all files older than 100 days):

	find /srv/mqtt -name "*.bin" -ctime +100 -exec rm {} \;

### 3.3 Understanding Quality-of-Service (QOS)

The Quality-of-Service (qos) level is an agreement between the sender of a message and the receiver of a message that defines the guarantee of delivery for a specific message. There are three qos levels in MQTT: (0) At most once, (1) At least once and (2) Exactly once. (0) sends out data without testing whether it is received or not. (1) sends out data and requires an aknowledgment that the data was received. Multiple sendings are possible. (2) makes sure that every data is send exactly once. Please refer to MQTT information pages for more details.


## 4. Experts settings


### 4.1 Enabling Authentication

    If you want to use authentication you should use addcred.py (UtilityScripts) to obsfuscate user and passwords, which helps you to avoid plain text passwords directly in scripts. Please note, that these methods do not encrypt passwords. They just store it in a different, independent file. To add such information into the credentials list use:

        $ python addcred.py -t transfer -c mqtt -u user -p mypasswd -a localhost

    for super user:
        $ sudo python addcred.py -t transfer -c mqtt -u user -p mypasswd -a localhost

    Provide the shortcut (mqtt) and username during the installation process.


### 4.2  Poll for change of public IP (useful for WiFi/UMTS connection):
    - edit paths in UtlityScripts/sendip.py to your own FTP server (if using)
    - Add call into crontab (as often as needed):
	$ crontab -e
	Something like this (for hourly polling):
	1 */1 * * * python ~/MARTAS/UtilityScripts/sendip.py


### 4.3 Manual instructions and running martas not as a service:

    You can run MARTAS from the command line by changing into the MARTAS directory and
    using the following commands:

        $ python3 acquisition_mqtt.py -m /path/to/martas.cfg -P mypasswd

    Using encryption with credentials created by addcred:

        $ python acquisition_mqtt.py -m /home/cobs/martas.cfg -c mqtt

    Providing authentication directly:

        $ python3 acquisition_mqtt.py -m /path/to/martas.cfg -u mosquittouser -P mosquittopasswd


### 5. Setup of a Broker


A broker defines a system which is permanently receiving data from a MARTAS system via MQTT, i.e. MARTAS publishes data to the broker. The broker can be the same system as the one running MARTAS (when following the installation instructions, your system will be ready to act as a broker), but it can also be an external machine. MARTAS makes use of a mosquitto brokers. Everything what you need to do to establish a broker is to install mosquitto as outlined in 1.1. If you want to use authentication on the broker follow the steps outlined in section 1.3. In order to use this broker, make sure that MARTAS can reach this broker system via its address (IP/HTTP) on port 1883. 


### 6. Setting up MARCOS

In the following we are setting up MARCOS to collect measurement data from a broker. MARCOS subscribes to the broker and receives any new data published there. All three systems, MARTAS, BROKER, and MARCOS can run on the same machine as different processes, but also run on multiple machines. You can also have several MARCOS collectors accessing the same broker independently.

MARCOS subscribes to the data broker and obtains publish data of a defined subject. You can select whether this data is then stored into archive files, into a data base (mariadb, mysql) and/or published on a webserver.

### 6.1 Basic setup:

a) Use the MARTAS installation script
        
        $ cd /path/to/MARTAS/install
        $ sudo sh marcos.install.sh
      -> follow the instructions

b) Check /etc/martas/broker.cfg   ("broker" might be replaced if you use have chosen a different name) 

        $ nano /etc/martas/broker.cfg


### 6.2 Running the collection sytem

a) When installation is finished you can start the system as follows:

        $ sudo /etc/init.d/collect-broker start

    - The following options are now available:
        $ sudo /etc/init.d/collect-broker status
        $ sudo /etc/init.d/collect-broker start
        $ sudo /etc/init.d/collect-broker restart
        $ sudo /etc/init.d/collect-broker stop

b) Running the collector from the commandline:

        python collector.py -b brokeradress -u myuser -P mypassword


### 6.3 Data destinations


#### 6.3.1 Saving incoming data as files


Select destination "file"


#### 6.3.2 Streaming to a database


Select destination "db"


#### 6.3.3 Starting a WEB interface with MARCOS

Select destination "websocket"

Open the following page in a webbrowser 
        http://ip_of_marcos:8080


a) Starting websocket transfer on MARCOS from commandline

      Manually you can also do that as follows:
        $ cd ~/MARTAS
        $ python collector -d websocket -o mystation
      If authentication is used: 
        $ python collector -d websocket -o mystation -u user -P password

b) Accessing websocket
      Connect to the MATRTAS machine from remote:
      On any machine which can access defined websocket port you can now open
      the following url in a browser of your choice:
      (Pleas replace "ip_of_martas" with the real IP-address or url name.

        http://ip_of_martas:8080
      
c) Customizing the WEB interface/ports of MARCOS

   - Modifying ports and paths - modify marcos.cfg
        $ python collector -m /path/to/marcos.cfg
      Here you can change default port (8080) and many other parameters.

   - Customizing graphs and layout (will change in the near future)
      Modify smoothiesettings.js:
        $ nano ~/MARTAS/web/smoothiesettings.js


## 7. Logging and notifications

### 7.1 The threshold notifyer

### 7.2 Support for NAGIOS/ICACLIENT

### 7.3 Communicating with MARTAS

## 8. Frequently asked questions

#### I want to send out data periodically from ma MARTAS acquisition machine using FTP or similar. Is this easily possible?

use app/senddata.py within crontab:

#### I want download buffer files from the MARTAS machine peridically in order to fill gaps of my qos 0 MQTT stream. How to do that?

use app/collectfile.py within crontab:


## 9. Strucure/Files in home directory of MARTAS user

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


## 10. Appendix

### 10.1 Dallas OW (One wire) support

a) modify owfs,conf
        $ sudo nano /etc/owfs.conf 

      Modify the following parts as shown below:
        #This part must be changed on real installation
        #server: FAKE = DS18S20,DS2405

        # USB device: DS9490
        server: usb = all

b) start the owserver
        $ sudo etc/init.d/owserver start 


### 10.2  Communicating with an Arduino Microcontroller


### TODO

- add trigger mode for GSM90 (sending f)
- add to #5
- update scp_log to use protected creds
- add in how-to for using senddata and addcreds




