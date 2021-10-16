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
- Geometrics G823 Cs Magnetometers
- GEM Systems GSM-90, GSM-19
- Quantum Magnetometer Systems POS-1, POS-4
- Meteolabs BM35 pressure sensor
- Thiess LaserNiederschlagsMessgerät - Disdrometer
- Ultrasonic Anemometer
- AD7714 general ADC
- MinGeo PalmDac 24 bit data logger (under development)
- Campbell Scientific CR800, CR1000 Data logger
- ENV05 Environment sensors
- MySQL/MariaDB databases
- Dallas OneWire Sensors
- DIGIBASE MCA Gamma sensors

and basically all I2C Sensors and others connectable to a Arduino Microcontroller board
(requiring a specific serial output format in the self written microcontroller program - appendix)


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

#### 3.1.1 Use the MARTAS installation script
        
        $ cd /path/to/MARTAS/install
        $ sudo sh martas.install.sh
      -> follow the instructions

#### 3.1.2 Modify /etc/martas/sensors.cfg

        $ nano /etc/martas/sensors.cfg

sensors.cfg is the basic configuration file for all sensors connected to the MARTAS system. It contains a line with a comma separted list for each sensor which looks like:

        GSM90_6107631_0001,S1,115200,8,1,N,passive,gsm90v7init.sh,-,1,GSM90,GSM90,6107632,0002,-,AS-W-36,GPS,magnetism,GEM Overhauzer v7.0

The following elements are contained in this order:

element  | description | example
-------- | -------- | ----------
sensorid | Unique identification string for sensor. Ideally consisting of  fields "name\_serialnumber\_revision" | GSM90\_6107631\_0001
port | serial communication port (e.g. tty**S1** or tty**USB0**)  |  S1
baudrate | Serial communication baudrate | 115200
bytesize | Serial communication bytesize | 8
stopbits | Serial communication stopbits | 1
parity | Parity can be set to none (N), odd (O), even (E), mark (M), or space (S) | N
mode | Can be active (data requests are send) and passive (sensor sends data regularly)  | passive
init | Sensor initialization (see 3.4 and appendix 10.1)  | gsm90v7init.sh
rate | Defines the sampling rate for active threads in seconds (integer). Data will be request with this rate. Active threads with more than 1 Hz are not possible. Not used for passive modes. | -
stack | Amount of data lines to be collected before broadcasting. Default **1**. **1** will broadcast any line as soon it is read. | 1
protocol | MARTAS protocol to be used with this sensor |  GSM90
name | Name of the sensors   | GSM90
serialnumber | Serialnumber of the sensor  | 6107632
revision | Sensors revision number, i.e. can change after maintainance  | 0002
path | Specific identification path for automatically determined sensors. Used only by the OW protocol. | -
pierid | An identification code of the pier/instrument location  | AS-W-36
ptime | Primary time originates from NTP (MARTAS clock), GNSS, GPS. If the sensors delivers a timestamp e.g. GPS time, then a generated header input **DataTimesDiff** always contains the average difference to the MARTAS clock, in this case GPS-NTP  | GPS
sensorgroup |  Diszipline or group  | magnetism
sensordesc |  Description of sensor details | GEM Overhauzer v7.0


IMPORTANT: 
- sensorids should only contain basic characters like 0,1,2,..9,a,b,...,z,A,B,...,Z (no special characters, no underscors, no minus etc)
- sensorids should not contain the phrases "data", "meta" or "dict" 

Further details and descriptions are found within the created sensors.cfg configuration file. 

#### 3.1.3 Check /etc/martas/martas.cfg 

        $ nano /etc/martas/martas.cfg

martas.cfg contains the basic MARTAS configuration data, definitions for broadcasting and paths. Details and descriptions are found within this file. The file is preconfigured during the installation process and does not beed to be changed. 


### 3.2 Running the acquisition sytem

#### 3.2.1 When installation is finished you can start the system as follows:

        $ sudo /etc/init.d/martas start

    - The following options are now available:
        $ sudo /etc/init.d/martas status
        $ sudo /etc/init.d/martas start
        $ sudo /etc/init.d/martas restart
        $ sudo /etc/init.d/martas stop

#### 3.2.2 Command line

        $ python acquisition.py

    acquisition.py automatically chooses cfg files from the same directory. You can use other parameter
    files using:

        $ python acquisition.py -m /home/user/martas.cfg

#### 3.2.3 Adding a cleanup for the bufferdirectory

   Principally, all data is buffered in binary files, by default within the /srv/mqtt directory.
   You can mount a SD card or external memory as such a bufferdirectory.
   In order to prevent an overflow of the local file system you can also activate a cleanup job
   to remove old files from the buffer directory.

   Add the following line to /etc/crontab

	15 0 * * * root sh /home/user/MARTAS/app/cleanup.sh

   Edit cleanup.sh to fit your needs. By default it reads (deleting all files older than 100 days):

	find /srv/mqtt -name "*.bin" -ctime +100 -exec rm {} \;

#### 3.2.4 Adding a start option to crontab 

   In case that the MARTAS acquisition process hangs up or gets terminated by an unkown reason
   it is advisable to add a start option to crontab, which starts MARTAS in case it is not 
   running any more

   Add the following line to /etc/crontab

       10  0  *  *  *  root    /etc/init.d/martas start

### 3.3 Understanding Quality-of-Service (QOS)

The Quality-of-Service (qos) level is an agreement between the sender of a message and the receiver of a message that defines the guarantee of delivery for a specific message. There are three qos levels in MQTT: (0) At most once, (1) At least once and (2) Exactly once. (0) sends out data without testing whether it is received or not. (1) sends out data and requires an aknowledgment that the data was received. Multiple sendings are possible. (2) makes sure that every data is send exactly once. Please refer to MQTT information pages for more details. The amount of messages stored is limited, with an upper limit defined by the brokers memory. When using a mosquitto broker the default limit of stored messages is 100. In order to change that modify the **max\_queued\_messages** count in mosquitto config.

### 3.4 Sensors requiring initialization 

Several sensors currently supported by MARTAS require an initialization. The initialization process defines e.g. sampling rates, filters, etc. in a way that the sensor systems is automatically sending data to the serial port afterwards. MARTAS supports such initialization routines by sending the respective and necessary command sequence to the system. Initialization commands are stored within the MARTAS configuration directory (Default: /etc/martas/init). The contents of the initialization files for supported instruments is outlined in Appendix 10.1. In order to use such initialization, you need to provide the path within the sensors configuration line in sensors.cfg:

sensors.cfg: line for a GSM90 Overhauzr, the initialzation configuration is taken from gsm90v7init.sh (within the martas config directory)

        GSM90_6107631_0001,S1,115200,8,1,N,passive,gsm90v7init.sh,-,1,GSM90,GSM90,6107632,0002,-,AS-W-36,GPS,magnetism,GEM Overhauzer v7.0

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

c) Adding a start option to crontab 

   In case that the MARCOS collector process hangs up or gets terminated by an unkown reason
   it is advisable to add a start option to crontab, which starts the collector in case it is not 
   running any more

   Add the following line to /etc/crontab

      12  0  *  *  *  root    /etc/init.d/collect-broker start


### 6.2 Running the collection sytem

a) When installation is finished you can start the system as follows:

        $ sudo /etc/init.d/collect-broker start

    - The following options are now available:
        $ sudo /etc/init.d/collect-broker status
        $ sudo /etc/init.d/collect-broker start
        $ sudo /etc/init.d/collect-broker restart
        $ sudo /etc/init.d/collect-broker stop

   Please note: if database outputis selected: on default on the data table will be written. If you want to create/update DATAINFO and SENSOR information, then run the collector with the -v option at least once.
        e.g. python3 collector.py -m /etc/martas/broker.cfg -v


b) Running the collector from the commandline:

        python collector.py -b brokeradress -u myuser -P mypassword


### 6.3 Data destinations


#### 6.3.1 Saving incoming data as files


Select destination "file"


#### 6.3.2 Streaming to a database


Select destination "db"

Stream data to a database requires a preconfigured MagPy conform database structure. That can be done a few steps:

1) Install MariaDB or MySQL (please follow instructions as given here for a proper setup)

        sudo apt-get install mariadb

2) Create an empty database

        $(sudo) mysql -u root -p mysql
        sql> CREATE DATABASE mydb;  # please replace mydb with a name of your choice

3) Grant access to this database for a specific user

        sql> GRANT ALL PRIVILEGES to user ...
        sql> exit;

4) Initialize the database

       $ python3
       >>> import magpy.database
       >>> db = mysql.connect()
       >>> dbinit(db)

5) Eventually add the database credentials with addcred

      $ addcred -d db -c mydb -u user ...


On default, meta information is not considered 

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

Please note: if you want to use threshold testing or monitoring, then you can use the installer "install.addapps.sh" in the install directory to set up/initialize these programs. 

### 7.1 The threshold notifyer threshold.py

MARTAS comes along with a threshold application. This application can be used to check your data in realtime and trigger certain action in case a defined threshold is met. Among the possible actions are notifications by mail or messenger, switching command to a connected microcontroller, or execution of bash scripts. This app reads data from a defined source: a MARTAS buffer files, MARCOS database or any file supported by [MagPy] (eventually directly from MQTT). Within a configuration file you define threshold values for contents in this data sources. Notifications can be triggered if the defined criteria are met, and even switching commands can be send if thresholds are broken. All threshold processes can be logged and  can be monitored independently by mail, nagios, icinga, telegram.
Threshold.py can be scheduled in crontab. You can configure Threshold.py to se

Threshold.py (and monitor.py) can use the Telegram messenager to broadcast notifications. If you want to use that you need to install telegram_send.

        $ sudo pip install telegram_send

        # IMPORTANT: requires Python3.6 !!

Please note that these notification routines are independent of an eventually used TelegramBot (7.4, working also with Python3.5 and smaller) for communication with your MARTAS machine. You can use the same channel, however.


### 7.2 Monitoring MARTAS and MARCOS process with monitor.py

The martas monitoring routine allows for testing data actuality and in MARTAS and MARCOS systems, can check available buffer memory and allows you to trigger bash scripts if a certain condition is found.
For basic initialization, please use the install.addapps.sh script. This will preconfigure the configuration data for you. Monitoring is performend periodically using a crontab input.

The following jobtypes are supported by the monitoring app: martas, marcos, space, logfile

#### 7.2.1 Installation

Use the installation script "install.addapps.sh" to install monitoring support. This script will also create a default monitor configuration file.

#### 7.2.2 logfile monitoring

To apply monitoring to watch contents of specfic log files change the following lines within the monitor.cfg configuration file:

        logfile   :   /var/log/magpy/archive.log
        logtesttype   :   last
        logsearchmessage   :   SUCCESS

The above example will scan the archive.log file for a string "SUCCESS" in the last line. 

To schedule such monitoring use crontab e.g.
        5  *  *  *  *  /usr/bin/python3 /home/cobs/MARTAS/app/monitor.py -c /etc/martas/archivemonitor.cfg -n ARCHIVEMONITOR -j logfile  > /dev/NULL 2&>1

#### 7.2.3 file date monitoring

To apply monitoring to watch for recent files in a directory change the following lines within the monitor.cfg configuration file:

        basedirectory      :   /home/user/datadirectory/*.cdf
        defaultthreshold   :   600

The above example will scan the directory '/home/user/datadirectory' and check if a file '*.cdf' younger then '600' seconds is present. (Ignorelist is not yet working properly as it is not applied to overall file selection)

To schedule such monitoring use crontab e.g.
        5  *  *  *  *  /usr/bin/python3 /home/cobs/MARTAS/app/monitor.py -c /etc/martas/uploadmonitor.cfg -n UPLOADMONITOR -j datafile  > /dev/NULL 2&>1


### 7.3 Sending notifications

### 7.3.1 e-mail notifications


In order to setup e-mail notifications the following steps need to be performed. Firstly, you should use the provided installer to generally setup monitoring and all necessary configuration files:

        cd MARTAS/install
        sudo bash install.addapps.sh

This command will create a number of configuration files for notifications within the default folder /etc/martas.
Secondly, it is necessary to locally save obsfuscated smtp server information on the MARTAS/MARCOS machine:

        python3 addcred.py -t mail -c mymailservice -u info@mailservice.at -p secret -s smtp.mailservice.at -l 25

Now we will need to update the configuration files accordingly.

        sudo nano /etc/martas/mail.cfg
        
You only need to change the input for mailcred, and enter the shortcut for the mailservice defined with option c in the command above. Please also enter the other information as listed below with your correct data:

        mailcred    :     mymailservice

        From        :  info@mailservice.at
        To          :  defaultreceiver@example.com
        smtpserver  :  smtp.mailservice.at
        porrt       :  25


Finally, use the application testnote.py for testing the validity of your configuration (please update the following line with your paths):

        python3 MARTAS/app/testnote.py -n email -m "Hello World" -c /etc/martas/mail.cfg -l TestMessage -p /home/user/test.log

Pleasenote: calling testnote the first time will create the log file but don't send anything. From then on, a message will be send whenever you change the message content.

### 7.3.1 telegram notifications

MARTAS can send notifications directly to the [Telegram] messenger. You need a Telegram Bot and a user id to setup simple notifications. See section 7.5 for some hints of setting up such environment.

For sending notifications yoz then just need to edit the basic configuration files:

        # if not done install addapps
        cd MARTAS/install
        sudo bash install.addapps.sh

        sudo nano /etc/martas/telegram.cfg
        
Insert your bot_id (token) and the user_id. Thats it. Then you can use testnote.py to for testing whether its working.

        python3 MARTAS/app/testnote.py -n telegram -m "Hello World, I am here" -c /etc/martas/telegram.cfg -l TestMessage -p /home/user/test.log


### 7.4 Support for NAGIOS/ICINGA


### 7.5 Communicating with MARTAS

MARTAS comes with a small communication routine, which allows interaction with the MARTAS server. In principle, you can chat with MARTAS and certain keywords will trigger reports, health stats, data requests, and many more. Communication routines are available for the [Telegram] messenger. In order to use these routines you need to setup a Telegram bot, referring to your MARTAS.

To setup [Telegram] communication use the following steps:

  a) Use [Telegram Botfather] to create a new BOT

        /newbot

        /setuserpic

  b) Install Telegram support for MARTAS

        $ cd MARATS/install
        $ sudo bash install.telegram.sh

      The installer will eventually add the following apckages: telepot, psutil and
      platform. For webcam support you shoudl install fswebcam.

        $ sudo apt-get install fswebcam  # optional - transferring webcam pictures


  c) Update /etc/martas/telegrambot.cfg

        $ nano /etc/martas/telegrambot.cfg

      -> you need the BotID, which you obtained when creating the new BOT
      -> you need at least one UserID. Your UserID

  d) Open Telegram on your Mobile/Webclient and access the TelegramBot Channel. 

      You can can now talk to your BOT (here are some examples):

        hello bot

        i need help

        what sensors are connected

        give me some details on sensors DS18B20

        i need further details on sensor 

        please provide your current status

        i would like to get some system information

        get the log of martas, last 20 lines

        please restart the martas process

        please restart the marcos process

        plot data from DS18B20_28616411B2648B6D_0001

        plot data from DS18B20_28616411B2648B6D_0001 between 2020-10-24 and 2020-10-26

      If you have a microcontroller connected programmed with MARTAS specifications (e.g. arduino) you can also send switching commands:

        switch heating on


## 8. Applications and Scripts

### 8.1 Overview of applications 

MARTAS comes along with a number of application scripts to support data acquisition, collection of data, access of remote data sources and organizations tools for databases. All these scripts can be found within the directory MARTAS/apps. Below you will find a comprehensive list of these scripts and their purpose. In the following you will find subsections with detailed instructions and example applications for all of these programs.

Script           |   Purpose                                         | Configuration  | py2/py3   |  Section
---------------- | ------------------------------------------------- | -------------- | --------- | --------
addcred.py       | Create credential information for scripts         |                | py3       | 8.2
archive.py       | Read database tables and create archive files     | archive.cfg    | py3       | 8.3
ardcomm.py       | Communicating with arduino microcontroller        |                | py2/py3   | 8.4
file_download.py | Used to download files, store them in a raw directory amd construct archives/database inputs     |  collect.cfg   |  py3  |  8.5
file_upload.py   | Used to upload files to any specified remote system using a protocol of your choise     |  upload.json   | py3   | 8.6
threshold.py     |      |     |    | 7.1
monitor.py       |      |     |    | 7.2
speedtest.py     | Test the bandwdith of the internet connection. Can be run periodically to write MagPy readable files     |     |    | 8.8
gamma.py         | Dealing with DIGIBASE gamma radiation acquisition and analysis | gamma.cfg | py3  | 8.7

### 8.2 addcred.py

#### DESCRIPTION:
Sending data to a remote host by scp or ftp.
Requires existing credential information (see cred.py).
-------------------------------------
Usage:
addcred.py -v <listexisting> -t <type> -c <credentialshortcut>
 -d <database> -u <user> -p <password> -s <smtp> -a <address> -o <host>
 -l <port>
-------------------------------------
Options:
-v       : view all existing credentials
-t       : define type of data: db, transfer or mail
-c       : shortcut to access stored information
-d       : name of a database for db type
-u       : user name
-p       : password (will be encrypted)
-s       : smtp address for mail types
-a       : address for transfer type
-o       : host of database
-l       : port of transfer protocol
-------------------------------------

#### APPLICATION:
python addcred.py -t transfer -c zamg -u max -p geheim -a "ftp://ftp.remote.ac.at" -l 21
!!!!  please note: put path in quotes !!!!!!


### 8.3 archive.py

#### DESCRIPTION:
Archive.py gets data from a databank and stores it to any accessible repository (e.g. disk). Old database entries exceeding a defined age can be deleted in dependency of data resolution. Archive files can be stored in a user defined format. The databank size is automatically restricted in dependency of the sampling rate of the input data. A cleanratio of 12  will only keep the last 12 days of second data, the last 720 days of minute data and approximately 118 years of hourly data are kept. Settings are given in a configuration file. 
IMPORTANT: take care about depth - needs to be large enough to find data

#### APPLICATION:
        # Auomatic
        python3 archive.py -c config.cfg

        # Manual for specific sensors and time range
        python3 archive.py -c /config.cfg -b 2020-11-22 -s Sensor1,Sensor2 -d 30


#### CONFIGURATION:

        MARTAS/conf/archive.cfg

provides credentials, path, defaultdepth, archiveformat, writearchive, applyflags, cleandb, cleanratio
and lists and dictionaries to modify criteria for specific sensors:
sensordict      :    Sensor1:depth,format,writeDB,writeArchive,applyFlags,cleanratio;
blacklist       :    BLV,QUAKES,Sensor2,Sensor3,


### 8.4 ardcomm

#### DESCRIPTION:
Communication program for microcontrollers (here ARDUINO) e.g. used for reomte switching commands

### 8.5 file_download.py

#### DESCRIPTION:
Downloads data by default in to an archive "raw" structure like /srv/archive/STATIONID/SENSORID/raw
Adds data into a MagPy database (if writedatabase is True)
Adds data into a basic archive structure (if writearchive is True)
The application requires credentials of remote source and local database created by addcred

file_donwload replaces the old collectfile.py routine which is still contained in the package

#### APPLICATION:

   1) Getting binary data from a FTP Source every, scheduled day
    python3 collectfile-new.py -c ../conf/collect-ftpsource.cfg
    in config "collect-ftpsource.cfg":
             sourcedatapath        :      /remote/data
             filenamestructure     :      *%s.bin

   2) Getting binary data from a FTP Source every, scheduled day, using seconday time column and an offset of 2.3 seconds
    python3 collectfile-new.py -c ../conf/collect-ftpsource.cfg
    in config "collect-ftpsource.cfg":
             sourcedatapath        :      /remote/data
             filenamestructure     :      *%s.bin
             LEMI025_28_0002       :      defaulttimecolumn:sectime;time:-2.3

   3) Just download raw data to archive
    python3 collectfile-new.py -c ../conf/collect-ftpsource.cfg
    in config "collect-ftpsource.cfg":
             writedatabase     :      False
             writearchive      :      False

   4) Rsync from a ssh server (passwordless access to remote machine is necessary, cred file does not need to contain a pwd) 
    python3 collectfile-new.py -c ../conf/collect-ftpsource.cfg
    in config "collect-ftpsource.cfg":
             protocol          :      rsync
             writedatabase     :      False
             writearchive      :      False

   5) Uploading raw data from local raw archive
    python3 collectfile-new.py -c ../conf/collect-localsource.cfg
    in config "collect-localsource.cfg":
             protocol          :      
             sourcedatapath    :      /srv/archive/DATA/SENSOR/raw
             writedatabase     :      False
             writearchive      :      True
             forcerevision     :      0001


### 8.6 file_upload.py


### 8.7 gamma.py

#### DESCRIPTION:
Working with Spectral radiometric data: The gamma script can be used to extract spectral measurements, reorganize the data and to analyze such spectral data as obtained by a DIGIBASE RH. 

#### APPLICATION:
Prerequisites are a DIGIBASE MCA and the appropriate linux software to run it.
1) Please install linux drivers as provided and described here:
   https://github.com/kjbilton/libdbaserh
   
2) Use a script to measure spectral data periodically (almost 1h)

        #!/bin/bash
        DATUM=$(date '+%Y-%m-%d')
        SN=$(/home/pi/Software/digibase/dbaserh -l | grep : | cut -f 2)
        NAME="/srv/mqtt/DIGIBASE_16272059_0001/raw/DIGIBASE_"$SN"_0001.Chn"
        /home/pi/Software/digibase/dbaserh -set hvt 710
        /home/pi/Software/digibase/dbaserh -q -hv on -start -i 3590 -t 3590 >> $NAME

3) Use crontab to run this script every hour

        0  *  *  *  *  root  bash /home/pi/Software/gammascript.sh > /var/log/magpy/gamma.log

4) use gamma.py to extract spectral data and store it in daily json structures

        58 5   *  *  *  root  $PYTHON /home/pi/SCRIPTS/gamma.py -p /srv/mqtt/DIGIBASE_16272059_0001/raw/DIGIBASE_16272059_0001.Chn  -c /home/pi/SCRIPTS/gamma.cfg -j extract,cleanup -o /srv/mqtt/DIGIBASE_16272059_0001/raw/ > /var/log/magpy/digiextract.log  2>&1

4) use gamma.py to analyse spectral data and create graphs

        30 6   *  *  *  root  $PYTHON /home/pi/SCRIPTS/gamma.py -p /srv/mqtt/DIGIBASE_16272059_0001/raw/ -j load,analyze -c /home/pi/SCRIPTS/gamma.cfg  > /var/log/magpy/digianalyse.log 2>&1

### 8.8 speedtest.py

#### DESCRIPTION:
Perform a speedtest based on speedtest-cli
(https://www.speedtest.net/de/apps/cli)

#### PREREQUISITES:

        sudo apt install speedtest-cli


#### APPLICATION:
1) Run
        python3 speedtest.py -n speed_starlink01_0001
2) Run periodically
        sudo crontab -e
        
        */5  *  *  *  *  /usr/bin/python3 /path/to/speedtest.py -c /path/to/conf.cfg -n speed_starlink01_0001  > /dev/NULL 2&>1


### 8.9 testnote.py

#### DESCRIPTION:
Send notifications via email and telegram. testnote.py will create a log file with a message. Whenever, the logfile content (message) is changing, a notification will be send out to the defined receiver. In order to use notifications, please install addapps.

#### OPTIONS:

        -m            : message to be send
        -n            : notification type: email, telegram or log
        -c            : path to configuration file
        -l            : key value of the log dictionary (value will be the message)
        -p            : path to the logfile (will contains a dictionary)

#### APPLICATION:

        python3 testnote.py -n email -m "Hello World" -c /etc/martas/mail.cfg -l TestMessage -p /home/user/test.log
        python3 testnote.py -n telegram -m "Hello World, I am here" -c /etc/martas/telegram.cfg -l TestMessage -p /home/user/test.log
        python3 testnote.py -n log -m "Hello World again" -l TestMessage -p /home/user/test.log


## 9. Frequently asked questions

#### During installation of pip packages dependency problems are occuring

If you observe such problems (problems occured in the past with matplotlib, numpy and/or scipy) then it is advisable
to install the recommended packages for your system using apt instead of pip. Please remove the pip packages (pip remove..) and install system
packages using e.g. sudo apt install python3-scipy

#### I want to send out data periodically from a MARTAS acquisition machine using FTP or similar. Is this easily possible?

use app/senddata.py within crontab:

#### I want download buffer files from the MARTAS machine peridically in order to fill gaps of my qos 0 MQTT stream. How to do that?

use app/collectfile.py within crontab:


## 10. Strucure/Files in home directory of MARTAS user

Within the MARTAS directory you will find the following files and programs:

Content |  Description
------- | ------------
acquisition.py    |             accepts options (-h for help)
collector.py    |                   accepts options (-h for help)
README.md    |		You are here.
LICENSE.md    |		GNU GPL 3.0 License
requirements.txt   |    for contiunuous integration test runs
**app**  | 
app/addcred.py    |	run to add protected credentials to be used e.g. by data sending protocol, database connections etc, avoinding the use of plain text passwords in scripts
app/archive.py    |	MARCOS job to periodically archive contents of the data base into archive files (e.g. CDF). Remove information from the data base exceeding a defined age. The latter requires additionally to run sql optimze routines in order to prevent an overflow of the local data base storage files. 
app/ardcomm.py    |	Communication program for microcontrollers (here ARDUINO) e.g. used for reomte switching commands 
app/cleanup.sh    |	remove buffer files older than a definite period
app/collectfile.py    |	access data locally or via rsync/ssh/ftp and add it to files/DB
app/deleteold.py    |	delete old inputs from a database, using a sampling rate dependent indicator (deleteold.py -h)
app/di.py    |	Routine based on MagPys absoluteAnalysis tool to analyse geomagnetic DI measurements from multiple input sources/observatories. 
app/file_upload.py    |	Wrapper to upload files to remote machine using either ssh, rsync, ftp
app/monitor.py    |	Monitoring application to check buffer files (martas), database actuality (marcos), disk space and log files; can trigger external scripts
app/mpconvert.py    |	converts MARTAS binary buffer files to other formats
app/optimzetables.py    |	application to be used with archive.py or deleteold.py; uses SQL Optimze methods to clear the table space after data has been removed - non-blocking
app/senddata.py    |	Send data from MARTAS to any other machine using cron/scheduler - OLD
app/sendip.py    |	Helper for checking and sending public IP  (via ftp) - OLD
app/serialinit.py    |	Load initialization file (in init) to activate continuous serial data delivery (passive mode)
app/telegramnote.py    |	Small program to send notes to a Telegram Messenger BOT. Useful for periodic information as an alternative to e-mail. 
app/testnote.py    |	Small routine to test notification sending via email, telegram, etc. 
app/testserial.py    |	Small routine to test serial communication. 
app/threshold.py    |	Threshold tester (see section 7.1) 
**core**  |  Core methods used by the most runtime scripts and applications 
core/martas.py    |	basic logging routines for MARTAS/MARCOS and wrapper for e-mail,logfile,telegram notifications 
core/acquisitionsupport.py    |	contains general communication methods and configuration file interpreters
**conf**  | Basic initialization files - used by installer 
conf/sensors.cfg    |	skeleton for sensors configuration information
conf/martas.cfg    |	skeleton for basic MARTAS confifuration -> acquisition
conf/marcos.cfg    |	skeleton for basic MARCOS confifuration -> collector
**init**  | Basic initialization files - used by installer 
init/martas.sh    |	Start script to be used in /etc/init.d
init/autostart.sh    |	Run to add and sctivate /etc/init.d/martas
init/martas.logrotate    |	Example script to activate logrotation
init/gsm90v7init.sh    |	Initialization script GEM GSM90 v7
init/gsm90v6init.sh    |	Initialization script GEM GSM90 v6
init/pos1init.sh    |	Initialization script Quantum POS1 
init/bm35init.sh    |	Initialization script Meteolab BM35 pressure
**install**  | Installer scripts. Will update configuration and copy job specific information to /etc/martas (default)
install/install.marcos.sh    |	Installer for collector jobs  (section 6.0)
install/install.martas.sh    |	Installer for acquisition jobs  (section 3.0)
install/install.telegram.sh    |	Installer for Telegram messenger communication (section 7.3)
install/install.addapps.sh    |   Installer for threshold testing and monitor
**libraries**  |  contain communication libraries for specific systems/protocols/instruments (required by acquisition.py)
libmqtt/...    |			library for supported instruments (mqtt streaming)
libwamp/...    |		library for sup. inst. (wamp streaming) - DISCONTINUED
**web**  |  Webinterface as used by the collector with destination websocket
web/index.html    |		local main page 
web/plotws.js    |	  	arranging plots of real time diagrams on html page
web/smoothie.js    |		plotting library/program (http://smoothiecharts.org/)
web/smoothiesettings.js    |        define settings for real time plots
oldstuff/...    |		        Folder for old contents and earlier versions


## 10. Appendix

### 10.1 Initialization files

#### 10.1.1 GEM Systems Overhauzr GSM90

#### 10.1.2 Quantum POS1

#### 10.1.3 Meteolabs BM35 pressure

#### 10.1.4 LM


### 10.2 Dallas OW (One wire) support

a) modify owfs,conf
        $ sudo nano /etc/owfs.conf 

      Modify the following parts as shown below:
        #This part must be changed on real installation
        #server: FAKE = DS18S20,DS2405

        # USB device: DS9490
        server: usb = all

b) start the owserver
        $ sudo etc/init.d/owserver start 


### 10.3  Communicating with an Arduino Uno Microcontroller

An [Arduino Microcontroller] has to be programmed properly with serial outputs, which are interpretable from MARTAS. Such Arduino programs are called sketch.
MARTAS contains a few example scripts, which show, how these sketches need to work, in order to be used with MARTAS. In principle, two basic acquisition modes are supported
for Arduinos:

   - active mode: the active mode sends periodic data requests to the Arduino. This process is non-blocking and supports communication with the Arduino inbetween data requests. E.g. switching commands can be send.

   - passive mode: the arduino ins configured to periodically send data to the serial port. This process is blocking. Passive communication is preferable for high sampling rates.

Within the sensors.cfg configuration file the following line need to be added to communicate with an Arduino:
 
      Active mode (port ttyACM0, data request every 30 sec):
        ARDUINO1,ACM0,9600,8,1,N,active,None,30,1,ActiveArduino,ARDUINO,-,0001,-,M1,NTP,environment,arduino sensors

      Passive mode (port ttyACM0):
        ARDUINO1,ACM0,9600,8,1,N,passive,None,-,1,Arduino,ARDUINO,-,0001,-,M1,NTP,environment,arduino sensors
 
In both cases, all sensors connected to the Arduino (and properly configured within the sketch) will then be automatically detected and added to sensors.cfg
automatically with a leading questionmark. You can edit sensors.cfg and update respective meta information for each sensor.

Within the subdirectory MARTAS/sketchbook you will find a few example sketches for the Arduino Uno Rev3 board. The serial number of the Arduino is hardcoded into those scripts. If you are going to use these scripts then please change the serial number accordingly:

   In all sketches you will find a line like:

        String ASERIALNUMBER="75439313637351A08180"

   Replace the serial number with your Arduion number. To find out your serial number you can use something like

        dmesg | grep usb
 
The following sketches are currently contained:

Sketch name |  version | mode  | job
----------- | ------ | ------ | -------
sketch\_MARTAS\_ac\_ow\_sw  | 1.0.0 |  active | requesting 1-wire sensor data and enabling remote switching of pin 4 (default: off) and pin 5 (default: on)
sketch\_MARTAS\_pa\_ow  | 1.0.0 |  passive | recording 1-wire sensor data


If you change the sensor configuration of the Arduino, then you need to stop martas, eventually delete the existing
arduino block (with the leading questionmark), connect the new sensor configuration and restart MARTAS. 
Make sure to disconnect the Arduino, before manipulating its sensor
configuration. You can check the Arduino independently by looking at Arduino/Tools/SerialMonitor (make sure that MARTAS processes are not running).

**IMPORTANT NOTE**: for active access it is sometimes necessary to start the SerialMonitor from arduino before starting MARTAS. The reason is not clarified yet. This is important after each reboot. If not all sensors are detetcted, you can try to send the RESET command "reS" to the arduino. This will reload available sensors. Such problem might occur if you have several one wire sensors connected to the arduion and remove or replace sensors, or change their configuration. 


### 10.4 Issues and TODO

Sometimes, if the recording process terminates, the daily buffer file might be corrupt. In that case you need to delete the daily file and restart the recoding process. The next daily file will be OK in any case.

- add trigger mode for GSM90 (sending f)
- add to #5
- update scp_log to use protected creds
- add in how-to for using senddata and addcreds



[Telegram] : <https://telegram.org/>
[Telegram Botfather] :  <https://core.telegram.org/bots>
[Arduino Microcontroller] : <http://www.arduino.cc/>

