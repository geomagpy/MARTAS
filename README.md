# MARTAS

**MagPys Automated Real Time Acquisition System**

MARTAS is a collection of python applications and packages supporting data acquisition, collection, storage, monitoring 
and analysis in heterogeneous sensor environments. MARTAS is designed to support professional observatory networks. 
Data acquisition makes use of an instrument library which currently includes many sensors typically used in
observatories around the globe and some development platforms. Basically, incoming sensor data is converted to a 
general purpose data/meta information object which is directly streamed via MQTT (message queue transport) to a data 
broker. Such data broker, called MARCOS (MagPys Automated Realtime Collector and Organization System), can be setup 
within the MARTAS environment. MARCOS collection routines can access MQTT data stream and store/organize such data and 
meta information in files, data banks or forward them to web sockets. All data can directly be analysed using MagPy 
which contains many time domain and frequency domain time series analysis methods.

Developers: R. Leonhardt, R. Mandl, R. Bailey (GeoSphere Austria)

### Table of Contents

1. [About](#1-about)
2. [Installation](#2-installation)
3. [Initialization of MARTAS/MARCOS](#3-initialization-of-martasmarcos)
4. [MARTAS](#4-martas)
5. [MARCOS](#5-marcos)


## 1. About

MARTAS has originally been developed to support realtime geomagnetic data acquisition. The principle idea was providing
a unique platform to obtain data from serial interfaces, and to stream and record this data within a generalized format
to a data archive. Previously any system connected via serial interface to a recording computer was registered by its
own software usually in a company specific format. Intercomparison of such data, extraction of meta information, 
realtime data transport and basically any analysis requiring different sources is significantly hampered.
MARTAS contains a communication library which supports many commonly used instruments as listed below. With these 
libraries, data AND meta information is obtained from connected sensors. This data is then converted to a data stream 
containing essential meta information. This data stream has a general format which can be used for basically every 
imaginable timeseries. The data stream is broadcasted/published on a messaging queue transport type (MQTT) broker, a 
state-of-the-art standard protocol of the Internet-of-Things (IOT). A receiver contained in the MARTAS package 
(MARCOS - MagPy's Automated Realtime Collector and Organization System) subscribes to such data streams and allows to 
store this data in various different archiving types (files (like CDF, CSV, TXT, BIN), databases). Various logging 
methods, comparison functions, threshold tickers, and process communication routines complement the MARTAS package.

Currently supported systems are:

- Lemi025,Lemi036, and most likely all other Lemi systems;
- Geometrics G823 Cs Magnetometers
- GEM Systems GSM-90, GSM-19
- Quantum Magnetometer Systems POS-1, POS-4
- Meteolabs BM35 pressure sensor
- Thiess LaserNiederschlagsMessgerät - Disdrometer
- Ultrasonic Anemometer
- AD7714 general ADC
- Campbell Scientific CR800, CR1000 Data logger
- ENV05 Environment sensors
- MySQL/MariaDB databases
- Dallas OneWire Sensors
- DIGIBASE MCA Gamma sensors
- Mingeo ObsDAQ 24bit-ADC in combination with PalmAcq logger
- all data files readable by MagPy

and basically all I2C Sensors and others connectable to Microcontroller boards like [Arduino]()
(requiring a specific serial output format in the microcontroller program - appendix)


Note: in the following examples we use "USER" as username and "USERS" as group. Replace these names with your 
user:group names. All instructions assume that you have a profound knowledge of debian like linux systems, as such a 
system is the only prerequisite to run MARTAS.


## 2. Installation

### 2.1 Installation requirements

All installation instructions assume a linux (debian-like) system. Although the core methods of MARTAS are platform 
independent, it is currently only tested and supported on debian-like LINUX systems.

    SYSTEM:
    - mosquitto (MQTT client - broker)
        sudo apt-get install mosquitto mosquitto-clients
    - virtualenvironment (python environment)
        sudo apt-get install virtualenv
    - MAROCS only (if MariaDB is used)
        sudo apt-get install mariadb
        sudo apt-get install percona-toolkit

    PYTHON:
    - python >= 3.7
    - all other requirements will be solved during installation

    Optional python packages:
    - pyownet  (one wire support)
        sudo pip install pyownet
        sudo apt-get install owserver


### 2.2 Installing MARTAS/MARCOS

Create a python environment:

        $ virtualenv 

Activate the environement:

        $ source ~/env/martas/bin/activate

Get the MARTAS package:

         download martas-2.x.x.tar.gz

Install the package using pip:

        (martas)$ pip install martas-2.x.x.tar.gz

### 2.3 Configure MQTT

In the following you will find some instructions on
how to get MQTT running on your MARTAS/MAROCS machine.

#### 2.3.1 Enable listener

Starting with Mosquitto version 2.0.0 only localhost can listen to mqtt publications. To enable other listener you can
create a config file as follows:

         sudo nano /etc/mosquitto/conf.d/listener.conf

Create this file if not existing and add the following lines:

         listener 1883
         allow_anonymous true

#### 2.3.2 Enabling authentication

Authentication and secure data communication are supported by MARTAS. In order to enable
authentication and SSL encryption for accessing data streams from your acquisition machine please check mosquitto 
instructions like the following web page:
https://www.digitalocean.com/community/tutorials/how-to-install-and-secure-the-mosquitto-mqtt-messaging-broker-on-ubuntu-16-04

For quickly enabling authentication you can also use the following instructions (without ssl encryption of data transfer):

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

Thats it. How to use credentials in MARTAS is described in section 7.x.


#### 2.3.3 Understanding Quality-of-Service (QOS)

The Quality-of-Service (qos) level is an agreement between the sender of a message and the receiver of a message that 
defines the guarantee of delivery for a specific message. There are three qos levels in MQTT: (0) At most once, (1) At 
least once and (2) Exactly once. (0) sends out data without testing whether it is received or not. (1) sends out data 
and requires an acknowledgement that the data was received. Multiple sendings are possible. (2) makes sure that every 
data is send exactly once. Please refer to MQTT information pages for more details. The amount of messages stored is 
limited, with an upper limit defined by the brokers memory. When using a mosquitto broker the default limit of stored 
messages is 100. In order to change that modify the **max\_queued\_messages** count in mosquitto config.


## 3. Initialization of MARTAS/MARCOS

In the following we are setting up MARTAS to acquire measurement data from any connected system, to store it locally
within a buffer directory and to permanenty stream it to a data broker. In the examples, we will use the same MARTAS 
system as data broker.

### 3.1 Initial setup

Activate the environment if not yet done:

        $ source ~/env/martas/bin/activate

Start the MARTAS/MARCOS initialization routine

        (martas)$ martas_init

This routine will ask you a series of questions to configure the acquisition (MARTAS) or collector (MARCOS) to your 
needs. In case you want to use e-mail, messenger notifications or database support, make sure that you setup these
tool ideally before running martas_init, and provide credential information using [addcred](https://github.com), section 10.6. 
You might want to checkout [section 6.1](#6-1) for details on notifications and [section 5.3.2](#5-3-2) for database support. 
Please also make sure that you have write permissions on the directories to be used.

### 3.2 Inputs during setup

## 4. MARTAS

### 4.1 Configuring sensors

When initialization is finished there is only one further step to do in case of a MARTAS acquisition machine. You need 
to specify the sensors. For this you will have to edit the sensors configuration file.

        $ nano ~/.martas/conf/sensors.cfg

sensors.cfg is the basic configuration file for all sensors connected to the MARTAS system. It contains a line with a 
comma separated list for each sensor which looks like:

        GSM90_6107631_0001,S1,115200,8,1,N,passive,gsm90v7init.sh,-,1,GSM90,GSM90,6107632,0002,-,AS-W-36,GPS,magnetism,GEM Overhauzer v7.0

You will find a number of examples for supported sensors in section 4.6. The following elements are contained in this 
order:

| element      | description | example |
|--------------| -------- | ---------- |
| sensorid     | Unique identification string for sensor. Ideally consisting of  fields "name\_serialnumber\_revision" | GSM90\_6107631\_0001 |
| port         | serial communication port (e.g. tty**S1** or tty**USB0**)  |  S1 |
| baudrate     | Serial communication baudrate | 115200 |
| bytesize     | Serial communication bytesize | 8 |
| stopbits     | Serial communication stopbits | 1 |
| parity       | Parity can be set to none (N), odd (O), even (E), mark (M), or space (S) | N |
| mode         | Can be active (data requests are send) and passive (sensor sends data regularly)  | passive |
| init         | Sensor initialization (see 3.4 and appendix 10.1)  | gsm90v7init.sh |
| rate         | Defines the sampling rate for active threads in seconds (integer). Data will be request with this rate. Active threads with more than 1 Hz are not possible. Not used for passive modes. | - |
| stack        | Amount of data lines to be collected before broadcasting. Default **1**. **1** will broadcast any line as soon it is read. | 1 |
| protocol     | MARTAS protocol to be used with this sensor |  GSM90 |
| name         | Name of the sensors   | GSM90 |
| serialnumber | Serialnumber of the sensor  | 6107632 |
| revision     | Sensors revision number, i.e. can change after maintainance  | 0002 |
| path         | Specific identification path for automatically determined sensors. Used only by the OW protocol. | - |
| pierid       | An identification code of the pier/instrument location  | AS-W-36 |
| ptime        | Primary time originates from NTP (MARTAS clock), GNSS, GPS. If the sensors delivers a timestamp e.g. GPS time, then a generated header input **DataTimesDiff** always contains the average difference to the MARTAS clock, in this case GPS-NTP  | GPS |
| sensorgroup  |  Diszipline or group  | magnetism |
| sensordesc   |  Description of sensor details | GEM Overhauzer v7.0 |


IMPORTANT:
- sensorids should only contain basic characters like 0,1,2,..9,a,b,...,z,A,B,...,Z (no special characters, no underscors, no minus etc)
- sensorids should not contain the phrases "data", "meta" or "dict"

Further details and descriptions are found in the commentary section of the sensors.cfg configuration file.

### 4.2 Running the acquisition system

#### 4.2.1 When installation is finished you can start the system as follows:

        $ sudo /etc/init.d/martas start

    - The following options are now available:
        $ sudo /etc/init.d/martas status
        $ sudo /etc/init.d/martas start
        $ sudo /etc/init.d/martas restart
        $ sudo /etc/init.d/martas stop

#### 4.2.2 Command line

        $ python acquisition.py -m /home/user/martas.cfg

#### 4.2.3 Adding a cleanup for the bufferdirectory

   Principally, all data is buffered in binary files, by default within the /srv/mqtt directory.
   You can mount a SD card or external memory as such a bufferdirectory.
   In order to prevent an overflow of the local file system you can also activate a cleanup job
   to remove old files from the buffer directory.

   Add the following line to /etc/crontab

	15 0 * * * root sh /home/user/MARTAS/app/cleanup.sh

   Edit cleanup.sh to fit your needs. By default it reads (deleting all files older than 100 days):

	find /srv/mqtt -name "*.bin" -ctime +100 -exec rm {} \;

#### 4.2.4 Adding a start option to crontab

   In case that the MARTAS acquisition process hangs up or gets terminated by an unkown reason
   it is advisable to add a start option to crontab, which starts MARTAS in case it is not
   running any more

   Add the following line to /etc/crontab

       10  0  *  *  *  root    /etc/init.d/martas start

### 4.4 Sensors requiring initialization

Several sensors currently supported by MARTAS require an initialization. The initialization process defines e.g. sampling rates, filters, etc. in a way that the sensor systems is automatically sending data to the serial port afterwards. MARTAS supports such initialization routines by sending the respective and necessary command sequence to the system. Initialization commands are stored within the MARTAS configuration directory (Default: /etc/martas/init). The contents of the initialization files for supported instruments is outlined in Appendix 10.1. In order to use such initialization, you need to provide the path within the sensors configuration line in sensors.cfg:

sensors.cfg: line for a GSM90 Overhauzr, the initialzation configuration is taken from gsm90v7init.sh (within the martas config directory)

        GSM90_6107631_0001,S1,115200,8,1,N,passive,gsm90v7init.sh,-,1,GSM90,GSM90,6107632,0002,-,AS-W-36,GPS,magnetism,GEM Overhauzer v7.0


### 4.5 Regular backups of all MARTAS configurations

MARTAS comes with a small backup application to be scheduled using cron, which saves basically all MARTAS configuration files within a zipped archive. The aim of this application is to save all essential information within one single data file so that in case of a system crash (hardware problem, SD card defect, etc) you can easily and quickly setup an identical "new" system. You might also use the backups to setup similar copies of a specific system.

To enable regular monthly backups, first copy the backup_config.sh application to /etc/martas/

          $ (sudo) cp /home/USER/MARTAS/apps/backup_config.sh /etc/martas

Modify backup_config.sh and insert the correct user name in line 13:

          $ (sudo) nano /etc/martas/backup_config.sh

Schedule the script using cron (as root).

          $ sudo nano /etc/crontab

Insert the following line to create backups every 1 day per month.

          10 0   1 * *   root /bin/bash /etc/martas/backup_config.sh


In order to recover a system from an existing backup, MARTAS/install contains a recovery script "recover.martas.sh". In the following example we asume that your system broke down i.e. due to a SD card failure of your beaglebone/raspberry single board PC. You need to recover your system on a newly installed SD card. To apply the recover script you need to perform the following steps:

1. Install a basic debian/ubuntu linux system on your acquisition machine (i.e. see steps 1-3 in section 12.5.2 for beaglebone)

2. login into the new machine as the projected user USER

3. create a directory /home/USER/Backups and copy the backup file you want to apply into this folder

        mkdir /home/USER/Backups
        (s)cp /source/myoldmachine_19990402_backup.tar.gz /home/USER/Backups/

4. get MARTAS (eventually you need to install git - apt install git)

        git clone https://github.com/geomagpy/MARTAS

5. Run the recover script. This script will guide you through the process

        sudo bash /home/USER/MARTAS/install/recover.martas.sh


### 4.6. Typical Sensor definitions in sensors.cfg

#### Geomagetic GSM90 Overhauzer Sensors (GEM Systems)

         GSM90_6107631_0001,S1,115200,8,1,N,passive,gsm90v7init.sh,-,1,GSM90,GSM90,6107632,0002,-,AS-W-36,GPS,magnetism,GEM Overhauzer v7.0

It is suggested to use the sensor name GSM90, the serial number of the electronics unit and a 4 digit revision number of your choice i.e. 0001. The revision number should be changed in case of electronic units maintainance etc. GSM90 sensors require initialization data provided in /etc/martas/init i.e. gsm90v7init.sh, to start continuous recording of the system. I strongly recommend passive recording i.e. at 0.5 Hz (GPS mode) and then filter to 1 Hz to obtain a record with readings centered on the second.

#### Geomagetic GSM19 Overhauzer Sensors (GEM Systems)

        GSM19_7122568_0001,USB0,115200,8,1,N,passive,,-,1,GSM19,GSM19,7122568,0001,-,mobile,GPS,magnetism,GEM Overhauzer v7.0

#### Geoelectric 4point light 10W (Lippmann)  

        4PL_123_0001,ACM0,19200,8,1,N,active,None,60,1,FourPL,4PL,123,0001,-,Home,NTP,geoelectric,wenner-0.65-0-c-o

Provide layout (wenner,schlumberger,half-schlumberger,dipole-dipole,), Distances A and L, as well as current and frequency within the comment part. For currents and frequencies please refer to the following codes:

currdic = {"m":"1uA","n":"10uA","o":"100uA","p":"1mA","q":"5mA","r":"15mA","s":"50mA","t":"100mA"}
freqdic = {"a":"0.26Hz","b":"0.52Hz","c":"1.04Hz","d":"2.08Hz","e":"4.16Hz","f":"8.33Hz","g":"12.5Hz","h":"25Hz"}

wenner-0.65-0-c-o  :  wenner configuration with electrode distance A of 0.65m, L=0 is not used for wenner, current (c) = 100uA, and frequency (o) = 1.04 Hz


#### Meteorology DSP Ultrasonic wind (Meteolab)  

         ULTRASONICDSP_0009009195_0001,S0,115200,8,1,N,active,None,60,1,DSP,ULTRASONICDSP,0009009195,0001,...

#### General Adruino microcontroller (Arduino)  

         ARDUINO1,ACM0,9600,8,1,N,active,None,60,1,ActiveArduino,ARDUINO,-,0001,-,Home,NTP,environment,getO-getU

#### MariaDB/MySQL database access  

         #cobsdb,-,-,-,-,-,passive,None,10,1,MySQL,MySQL,-,0001,-,-,-,magnetism,-

#### Onewire Senors (Dallas)  

         OW,-,-,-,-,-,active,None,10,1,Ow,OW,-,0001,-,A2,NTP,environment,environment: dallas one wire sensors

#### Environment ENV05 T/rh ()

         ENV05_3_0001,USB0,9600,8,1,N,passive,None,-,1,Env,ENV05,3,0001,-,AS-W-20,NTP,environment,temperature and humidity

#### Geomagnetic LEMI025/036 variometer (LEMI LVIV)

         LEMI036_3_0001,USB0,57600,8,1,N,passive,None,-,1,Lemi,LEMI036,3,0001,-,ABS-67,GPS,magnetism,magnetic variometer from Lviv

#### Geomagnetism POS1/POS4 Overhauzer Sensor (Quantum magnetics)

         POS1_N432_0001,S0,9600,8,1,N,passive,pos1init.sh,-,1,POS1,POS1,N432,0001,-,AS-W-36,GPS,magnetism,Quantum magnetics POS1 Overhauzer sensor

#### Datalogger CR1000/CR800 (Campbell Scientific)

         CR1000JC_1_0002,USB0,38400,8,1,N,active,None,2,1,cr1000jc,CR1000JC,02367,0002,-,TEST,NTP,meteorological,snow height

#### Datalogger AD7714 24bit ()

         AD7714_0001_0001,-,-,-,-,-,autonomous,None,-,10,ad7714,AD7714,-,0001,-,-,NTP,environment,24bit analog digital converter

#### Geomagnetic Obsdaq/Palmdaq datalogger together FGE Magnetometer (MINGEO, DTU)

         FGE_S0252_0002,USB0,57600,8,1,N,passive,obsdaqinit.sh,-,1,obsdaq,FGE,S0252,0002,-,ABS-67,GPS,magnetism,magnetic fluxgate from Denmark

### 4.7 Enabling Authentication

If you want to use authentication you should use addcred (MagPy, section 10.6) to obsfuscate user and passwords, which
helps you to avoid plain text passwords directly in scripts. Please note, that these methods do not encrypt passwords. 
They just store it in a different, independent file. To add such information into the credentials list use:

        $ addcred -t transfer -c mqtt -u user -p mypasswd -a localhost

Provide the shortcut (mqtt) and username during the installation process.


### 4.8 Setup of a Broker


A broker defines a system which is permanently receiving data from a MARTAS system via MQTT, i.e. MARTAS publishes data
to the broker. The broker can be the same system as the one running MARTAS (when following the installation
instructions, your system will be ready to act as a broker), but it can also be an external machine. MARTAS makes 
use of a mosquitto brokers. Everything what you need to do to establish a broker is to install mosquitto as outlined
in 1.1. If you want to use authentication on the broker follow the steps outlined in section 1.3. In order to use this 
broker, make sure that MARTAS can reach this broker system via its address (IP/HTTP) on port 1883.


## 5. MARCOS

In the following we are setting up MARCOS to collect measurement data from a broker. MARCOS subscribes to the broker 
and receives any new data published there. All three systems, MARTAS, BROKER, and MARCOS can run on the same machine 
as different processes. You can also have several MARCOS collectors accessing the 
same broker independently.

### 5.1 MARCOS specific configurations

MARCOS subscribes to the data broker and obtains published data depending on the selected "topic". You can select 
whether this data is then stored into files (binary buffer files, supported by MagPy), into a data base (mariadb, mysql)
and/or published on a webserver. You can also select multiple destinations. These selections are done during
initialization. As outlines above it is important to know these destinations already before initializing MARCOS 
and provide credentials using MagPys addcred method. No further configurations are necessary.

### 5.2 Running a collection job

After initialization you will find a bash job with the selected name (i.e. myjon) within your .martas directory.  You 
can start this job manually as follows.:

        $ bash collect-myjob.sh start 

The following options are now available:

        $ bash collect-myjob.sh start 
        $ bash collect-myjob.sh stop 
        $ bash collect-myjob.sh restart 
        $ bash collect-myjob.sh status
        $ bash collect-myjob.sh update #(important for first time usage with database - see below)

Please note: if database output is selected then by default only the data table will be written. If you want to 
create/update DATAINFO and SENSOR information, which usually is the case when running the sensor collection job for the
first time then run the collector with the "update" option, at least for a few seconds/minutes.

        $ bash collect-myjob.sh update 

### 5.3 Data destinations

#### 5.3.1 Saving incoming data as files

Select destination "file" during initialization. You will also have to provide a file path then. Within this file path
a directory named with the SensorID will be created and within this directory daily binary files will be created 
again with SensorId and date as file name. The binary files have a single, ASCII readable header line describing its 
packing formats. These binary files can be read with MagPy and transformed into any MagPy supported format.

#### 5.3.2 Streaming to a database

Checkout the MagPy instructions to setup and initialize a MagPy data base
(see [section 9](https://github.com/geomagpy/magpy/tree/develop?tab=readme-ov-file#9-sql-databases)). 
This is usually done within minutes and then can be readily used for MARCOS data collections or MARTAS dissemination. 
When initializing MARCOS and selecting destination "db" you will need to provide a credential shortcut for the 
database. You can create such credentials using addcred. Use addcred -h for all options.

      $ addcred -d db -c mydb -u user -p secret -h localhost

Please use the "update" option when running a job with a new sensor for the first time to create default inputs into the
database (and not only the data table).

#### 5.3.3 Streaming to a web interface

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


#### 5.3.4 Writing to stdout

When selecting destination "stdout" the ASCII output will be written to the destination defined by logging. This can 
either be sys.stdout or the given log file. 

#### 5.3.5 Selecting diff as destination

Calculates real-time differences between sensors attached to the same MARTAS. This is useful if you want to 
visualize gradients directly.

## 6. Applications and Scripts

### 6.1 Overview of applications

MARTAS comes along with a number of application scripts to support data acquisition, collection of data, access of 
remote data sources and organizations tools for databases. All these scripts can be found within the directory 
MARTAS/apps. Below you will find a comprehensive list of these scripts and their purpose. In the following you will 
find subsections with detailed instructions and example applications for all of these programs.


| Script           | Purpose                                              | Config        | Version | Section |
|------------------|------------------------------------------------------|---------------|---------|---------|
| archive.py       | Read database tables and create archive files        | archive.cfg   | 2.0.0   | 6.2     |
| ardcomm.py       | Communicating with arduino microcontroller           |               | 1.0.0   | 6.3     |
| basevalue.py     | Analyse mag. DI data and create adopted baselines    | basevalue.cfg | 2.0.0*  | 6.4     |
| checkdatainfo.py | List/ad data tables not existing in DATAINFO/SENS    |               | 2.0.0   | 6.5     |
| db_truncate.py   | Delete data from all data tables                     | truncate.cfg  | 2.0.0   | 6.6     |
| file_download.py | Download files, store them and add to archives       | collect.cfg   | 2.0.0*  | 6.7     |
| file_upload.py   | Upload files                                         | upload.json   | 2.0.0*  | 6.8     |
| filter.py        | filter data                                          | filter.cfg    | 2.0.0   | 6.9     |
| gamma.py         | DIGIBASE gamma radiation acquisition and analysis    | gamma.cfg     |         | 6.10    |
| monitor.py       | Monitoring space, data and logfiles                  | monitor.cfg   | 2.0.0   | 6.11    |
| obsdaq.py        | Communicate with ObsDAQ ADC                          | obsdaq.cfg    | 2.0.0*  | 6.12    |
| optimzetables.py | Optimize table disk usages (requires ROOT)           |               | 2.0.0*  | 6,13    |
| palmacq.py       | Communicate with PalmAcq datalogger                  | obsdaq.cfg    | 2.0.0*  | 6.12    |
| serialinit.py    | Sensor initialization uses this method               |               | 2.0.0*  | 6.14    |
| speedtest.py     | Test bandwidth of the internet connection            |               | 2.0.0*  | 6.15    |
| statemachine.py  | Currently under development - will replace threshold |               | 1.0.0   | 6.16    |
| testnote.py      | Send a quick message by mail or telegram             |               | 2.0.0   | 6.17    |
| testserial.py    | test script for serial comm - development tool       |               | 1.0.0   | 6.18    |
| threshold.py     | Tests values and send reports                        | threshold.cfg | 2.0.0   | 6.19    |

Version 2.0.0* means it still needs to be tested

### 6.2 archive

Archive.py gets data from a databank and stores it to any accessible repository (e.g. disk). Old database entries 
exceeding a defined age can be deleted in dependency of data resolution. Archive files can be stored in a user defined 
format. The databank size is automatically restricted in dependency of the sampling rate of the input data. A 
cleanratio of 12  will only keep the last 12 days of second data, the last 720 days of minute data and approximately 
118 years of hourly data are kept. Settings are given in a configuration file.
IMPORTANT: data bank entries are solely identified from DATAINFO table. Make sure that your data tables are contained 
there.
IMPORTANT: take care about depth - needs to be large enough to find data. Any older data set (i.e. you uploaded data 
from a year ago) will NOT be archive and also not be cleaned. Use db_truncate to clean the db in such cases.

        # Automatic application
        python3 archive.py -c ~/.martas/conf/archive.cfg

        # Manual for specific sensors and time range
        python3 archive.py -c ~/.martas/conf/archive.cfg -b 2020-11-22 -s Sensor1,Sensor2 -d 30

The configuration file will be initialized using martas_init. Additional changes and options are available.

        nano ~/.martas/conf/archive.cfg

provides credentials, path, defaultdepth, archiveformat, writearchive, applyflags, cleandb, cleanratio
and lists and dictionaries to modify criteria for specific sensors:
sensordict      :    Sensor1:depth,format,writeDB,writeArchive,applyFlags,cleanratio;
blacklist       :    BLV,QUAKES,Sensor2,Sensor3,


### 6.3 ardcomm

Communication program for microcontrollers (here ARDUINO) e.g. used for remote switching commands


### 6.4 basevalue

Basevalue.py (re)calculates basevalues from DI measurements and provided variation and scalar data. The method can use 
multiple data sources and piers as defined in the configuration file. It further supports different run modes defining
the complexity of baseline fits, application of rotation matricies etc. These run modes are used for the yearly 
definitive data analysis of the Conrad Observatory. It is recommended to use a similar data coverage of approximately one year
particularly with polynomial or spline fits to get comparable fitting parameters. In default mode: if
enddate is set to now and no startdate is given, then startdate will be 380 days before enddate. 

For continuous application throughout the year, i.e. an automatic DI analysis of new input values and a continuous 
calculation of an adopted baseline the following parameters are suggested.

        python basevalue.py -c ~/.martas/conf/basevalue.cfg

For definitive data analysis, verification of baselines, iterative optimization of adopted baselines, and validation of 
multiple pier measurements, you can use very same method with a combination of different run modes (option -j). 
Instructions will be added gradually here. Meanwhile contact the Conrad Observatory team if you have questions.

The basevalue application, in particular its overview plotting method, currently has some limitations as it was developed
for DHZ baselines and might not display XYZ data correctly. 

### 6.5 checkdatainfo

checkdatainfo.py checks for all data tables which are missing in DATAINFO  and SENOSRS. This method helps to 
identify any data tables which are continuously filled, but not available in XMagPy and which are not treated by
archive. This also means that these tables are not frequently trimmed in size. Use db_truncate to trim those tables.

Options:
-c (required) : credentials for a database
-i            : data table identifiers - end of table name i.e "00??" (? can be numbers from 0-9)
-d            : check datainfo
-s            : check sensors
-a            : add missing data to DATAINFO ( if "-d") and SENSORS (if "-s")

Example:

        python checkdatainfo.py -c cobsdb -d -s


### 6.6 db_truncate

db_truncate.py truncates contents of timesseries in a MagPy database. Whereas "archive" also allows for truncating 
the database (based on DATAINO) "db\_truncate" removes contents from all tables of xxx\_xxx\_xxxx\_xxxx structure.
(independent of DATAINFO contents).
The databank size is automatically restricted in dependency of the sampling rate of the input data. A cleanratio of 12
will only keep the last 12 days of second data, the last 720 days of minute data and approximately 118 years of hourly 
data are kept. Settings are given in a configuration file.

Application:

        python3 db_truncate.py -c archive.cfg



### 6.7 file_download

Downloads data by default in to an archive "raw" structure like /srv/archive/STATIONID/SENSORID/raw
Adds data into a MagPy database (if writedatabase is True)
Adds data into a basic archive structure (if writearchive is True)
The application requires credentials of remote source and local database created by addcred

   1) Getting binary data from a FTP Source every, scheduled day
    python3 collectfile-new.py -c ../conf/collect-ftpsource.cfg
    in config "collect-ftpsource.cfg":
             sourcedatapath        :      /remote/data
             filenamestructure     :      *%s.bin

   2) Getting binary data from a FTP Source every, scheduled day, using secondary time column and an offset of 2.3 seconds
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

      
### 6.8 file_upload

Upload data to a destination using various different protocols supported are FTP, SFTP, RSYNC, SCP. Jobs are listed in 
a json structure and read by the upload process. You can have multiple jobs. Each job refers to a local path. Each job
can also have multiple destinations.

Examples:
1. FTP Upload from a directory using files not older than 2 days
{"graphmag" : {"path":"/srv/products/graphs/magnetism/","destinations": {"conradpage": { "type":"ftp", "path" : "images/graphs/magnetism/"} },"log":"/home/leon/Tmp/Upload/testupload.log", "extensions" : ["png"], "namefractions" : ["aut"], "starttime" : 2, "endtime" : "utcnow"}}
2. FTP Upload a single file
{"graphmag" : {"path":"/home/leon/Tmp/Upload/graph/aut.png","destinations": {"conradpage": { "type":"ftp", "path" : "images/graphs/magnetism/"} },"log":"/home/leon/Tmp/Upload/testupload.log"}}
3. FTP Upload all files with extensions
{"mgraphsmag" : {"path":"/home/leon/Tmp/Upload/graph/","destinations": {"conradpage": { "type":"ftp", "path" : "images/graphs/magnetism/"} },"log":"/home/leon/Tmp/Upload/testupload.log", "extensions" : ["png"]} }
4. Test environment
{"TEST" : {"path":"../","destinations": {"homepage": { "type":"test", "path" : "my/remote/path/"} },"log":"/var/log/magpy/testupload.log", "extensions" : ["png"], "starttime" : 2, "endtime" : "utcnow"} }
5. RSYNC upload
{"ganymed" : {"path":"/home/leon/Tmp/Upload/graph/","destinations": {"ganymed": { "type":"rsync", "path" : "/home/cobs/Downloads/"} },"log":"/home/leon/Tmp/Upload/testupload.log"} }
6. JOB on BROKER
{"magnetsim" : {"path":"/home/cobs/SPACE/graphs/","destinations": {"conradpage": { "type":"ftp", "path" : "images/graphs/magnetism/"} },"log":"/home/cobs/Tmp/testupload.log", "extensions" : ["png"], "namefractions" : ["magvar","gic_prediction","solarwind"], "starttime" : 20, "endtime" : "utcnow"}, "supergrad" : {"path":"/home/cobs/SPACE/graphs/","destinations": {"conradpage": { "type":"ftp", "path" : "images/graphs/magnetism/supergrad"} },"log":"/home/cobs/Tmp/testupload.log", "extensions" : ["png"], "namefractions" : ["supergrad"], "starttime" : 20, "endtime" : "utcnow"},"meteo" : {"path":"/home/cobs/SPACE/graphs/","destinations": {"conradpage": { "type":"ftp", "path" : "images/graphs/meteorology/"} },"log":"/home/cobs/Tmp/testupload.log", "extensions" : ["png"], "namefractions" : ["Meteo"], "starttime" : 20, "endtime" : "utcnow"}, "radon" : {"path":"/home/cobs/SPACE/graphs/","destinations": {"conradpage": { "type":"ftp", "path" : "images/graphs/radon/"} },"log":"/home/cobs/Tmp/testupload.log", "extensions" : ["png"], "namefractions" : ["radon"], "starttime" : 20, "endtime" : "utcnow"}, "title" : {"path":"/home/cobs/SPACE/graphs/","destinations": {"conradpage": { "type":"ftp", "path" : "images/slideshow/"} },"log":"/home/cobs/Tmp/testupload.log", "extensions" : ["png"], "namefractions" : ["title"]}, "gic" : {"path":"/home/cobs/SPACE/graphs/","destinations": {"conradpage": { "type":"ftp", "path" : "images/graphs/spaceweather/gic/"} },"log":"/home/cobs/Tmp/testupload.log", "extensions" : ["png","gif"], "namefractions" : ["24hours"]}, "seismo" : {"path":"/home/cobs/SPACE/graphs/","destinations": {"conradpage": { "type":"ftp", "path" : "images/graphs/seismology/"} },"log":"/home/cobs/Tmp/testupload.log", "extensions" : ["png"], "namefractions" : ["quake"]} }

Application:

   python3 file_uploads.py -j /my/path/uploads.json -m /tmp/sendmemory.json

Problem:
 - upload is not performed and stops already at first input. The log file contains "DEALING with ...", "file upload app finished", "SUCCESS"
Solution:
 - this error is typically related to an empty memory file


### 6.9 filter

Use the filter application to smooth and resample data sets. The methods uses the MagPy filter method and allows
for the application of all included filter methods (https://github.com/geomagpy/magpy/tree/develop?tab=readme-ov-file#5-timeseries-methods).
By default only data sets with sampling periods faster than 1 Hz will be filtered. You can change this behavior
you with input options.
The filter method principally supports two run modes using option -j, **realtime** and **archive**, of which realtime 
is the default mode. For the application of the **realtime** mode a MagPy database is mandatory. **archive** requires an
archive structure as obtained by the archive.py application. Both run modes require 
a configuration file. The configuration file is a json structure containing a filter dictionary with the following 
sub items:

| item           | description                                                                        |
|----------------|------------------------------------------------------------------------------------|
| groupparameter | a dictionary with filter characteristics of specific sensors or data groups        |
| permanent      | a list of sensors subjected to *realtime* analysis                                 | 
| blacklist      | a list of SensorIDs which should not be filtered although belonging to data groups |
| basics         | a dictionary with general definition, paths and notification                       |

Groupparameter contains subdictionaries of the following format:

         {...,
         "LEMI036_3_0001_0001" : {"filtertype":"hann", 
                                  "filterwidth":100, 
                                  "missingdata":"conservative",
                                  "resample_period":1, 
                                  "window" : 40000, 
                                  "dayrange":4,
                                  "station" : "WIC",
                                  "revision" : "0002"},
         "LEMI025" : {"filtertype":"gaussian"} 
         }

The groupparameter item can either be a unique DataID, a SensorID or any fraction of those name. "LEMI025" will define
a group and apply the filter parameters to all DataIDs containing "LEMI025". The content of each groupparameter is also
organized as a dictionary. The following items can be defined for each group entry. *station* will limit the application
to data sets from this obs-code/IMO/station. *filtertyp*, *filterwidth* and *missingdata* define
the major filter characteristics. Please check MagPy's help(DataStream().filter) for all available filters and their
parameters. *resample_period* is given in Hz. If you want skip resampling then insert "noresample". *window* defines 
the amount of data on which the filter is applied in 
**realtime** mode. If you want to subject the last 600 seconds of 10Hz data, then window should be 6000. *realtime* is 
deprecated and will be removed. *dayrange* defines the data range to be filtered in **archive** mode. *revision* defines
the DataID revision assigned to the output. Usually this is "0002".
Please note: any parameter defined in groupparameter will override defaults and general values provided as options like
-d dayrange. 

The permanent item defines a list of realtime sensors. Only these DataID's are considered for realtime analysis.

The blacklist item is a list of data sets to be ignored. 

Basics provides a dictionary with general information.

              "basics": {"basepath":"/home/user/MARCOS/archive",
                         "outputformat":"PYCDF",
                         "destination":"db",
                         "credentials":"mydb",
                         "notification":"telegram",
                         "notificationconf":"/home/user/.martas/conf/telegram.cfg",
                         "logpath":"/home/user/.martas/log/filterstatus.log"}


The filter application will firstly scan the database for all DataIDs defined as *grouparameter* items fulfilling the 
sampling rate criteria, below 1 Hz as default, and drop all DataID's as defined in the *blacklist*.
A **realtime** job will then check whether recent data recordings exist, which by default are not older then 7200 sec, 
2 hours. Then it will will perform a filter analysis using the given parameters. 
A **archive** job will use the dayrange parameter, default is 2, and option endtime, default is UTC-now. Endtime can 
only be modified using the general option -e.

        python filter.py -c ~/myconfig.cfg -j archive -e LEMI036_123_0001

The output will be stored within the defined destination. Please note: if a database is your destination then DATAINFO
is NOT updated by default. Data sets are stored within the data table ending with the provided revision, default 
"0002". If you want to update DATAINFO you need to provide the SensorID in option -s.

        python filter.py -c ~/myconfig.cfg -j realtime -s LEMI036_123_0001

Other general optins are -l to define a loggernamse, which is useful if you have several filter jobs running on one
machine. The option -x will enable sending of logging information to the defined notification system. By default 
this is switched of because database contents are usually monitored, which also would report failures with 
specific data sets. 

The filter method should be applied in an overlapping way, as the beginning and end of the filtered sequence are
removed in dependency of the filter width. 

 
### 6.10 gamma

Working with Spectral radiometric data: The gamma script can be used to extract spectral measurements, reorganize the 
data and to analyze such spectral data as obtained by a DIGIBASE RH.

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


### 6.11 monitor

It is possible to monitor most essential aspects of data acquisition and storage. Monitor allows for testing data 
actuality, get changes in log files, and/or get warnings if disk space is getting small. Besides, monitor.py can
be used to trigger external scripts in case of an observed "CRITICAL: execute script." state. This, however, is only
supported for logfile monitoring in case of repeated messages. 
The following jobs are supported, provided usually as joblist within the monitor.cfg configuration file:

1. **space** - testing for disk size of basedirectory (i.e. /srv/mqtt or srv/archive)
2. **martas** - check for latest file updates in basedirectory and subdirs
3. **datafile** - check for latest file updates only in basedirectory, not in subdirs
4. **marcos** - check for latest timestamp in data tables
5. **logfile** - log-test-types are: new or repeat, last, contains; new -> logfile has been changed since last run; repeat -> checks for repeated logsearchmessage in changed logs if more than tolerance then through execute script msg; last -> checks for logsearchmessage in last two lines; contains -> checks for logsearchmessage in full logfile

The monitor configuration file will be initialized by martas_init.

Application:

        python3 monitor.py -c ~/.martas/conf/monitor.cfg

### 6.12 obsdaq and palmacq

Richard, please...


### 6.13 optimizetables

Optimizing tables and free space, the unblocking version. Please note, executing this job requires root privileges

REQUIREMENTS:
 - magpy
 - sudo apt install percona-toolkit
 - main user (user/cobs) needs to be able to use sudo without passwd (add to /etc/sudoers)

### 6.14 serialinit

Serialinit is used by all initialization jobs. See init folder...  


### 6.15 speedtest

Perform a speedtest based on speedtest-cli (https://www.speedtest.net/de/apps/cli)

        sudo apt install speedtest-cli

Application:
        python3 speedtest.py -n speed_starlink01_0001

If you want to run it periodically then add to crontab:

        */5  *  *  *  *  /usr/bin/python3 /path/to/speedtest.py -c /path/to/conf.cfg -n speed_starlink01_0001  > /dev/NULL 2&>1

### 6.16 statemachine

See threshold. Statemaschine is currently developed and may replace threshold in a future version.


### 6.17 testnote

Send notifications via email and telegram. testnote.py will create a log file with a message. Whenever, the logfile 
content (message) is changing, a notification will be send out to the defined receiver. In order to use notifications, 
please install addapps.

OPTIONS:

        -m            : message to be send
        -n            : notification type: email, telegram or log
        -c            : path to configuration file
        -l            : key value of the log dictionary (value will be the message)
        -p            : path to the logfile (will contains a dictionary)

APPLICATION:

        python3 testnote.py -n email -m "Hello World" -c /etc/martas/mail.cfg -l TestMessage -p /home/user/test.log
        python3 testnote.py -n telegram -m "Hello World, I am here" -c /etc/martas/telegram.cfg -l TestMessage -p /home/user/test.log
        python3 testnote.py -n log -m "Hello World again" -l TestMessage -p /home/user/test.log


### 6.18 testserial

Simple test code for serial communication. Not for any productive purpose.

### 6.19 threshold

The threshold application can be used to check your data in realtime and trigger certain action in case a defined 
threshold is met. Among the possible actions are notifications by mail or messenger, switching command to a connected
microcontroller, or execution of bash scripts. This app reads data from a defined source: a MARTAS buffer files, 
MARCOS database or any file supported by [MagPy] (eventually directly from MQTT). Within a configuration file you 
define threshold values for contents in this data sources. Notifications can be triggered if the defined criteria are
met, and even switching commands can be send if thresholds are broken. All threshold processes can be logged and  can 
be monitored independently by mail, nagios, icinga, telegram.
Threshold.py can be scheduled in crontab. 

In case you are using telegram notifications please note that these notification routines are independent of an 
eventually used TelegramBot ([section 7.4]()) for communication with your MARTAS machine. 
You can use the same channel, however.

Threshold requires a configuration file which is setup during the initialization process with [martas_init] 
and the application needs to be scheduled in crontab. In order to test specific data sets you will have to modify the
test parameters in the configuration file by providing a list of sensorid; timerange to check; key to check, value, 
function, state, statusmessage, switchcommand(optional).
SensorID, key:  if sensorid and key of several lines are identical, always the last valid test line defines the message
                 Therefore use warning thresholds before alert thresholds
Function:       can be one of max, min, median, average(mean), stddev
State:          can be one below, above, equal
Statusmessage:  default is replaced by "Current 'function' 'state' 'value', e.g. (1) "Current average below 5"
                 the following words (last occurrence) are replace by datetime.utcnow(): date, month, year, (week), hour, minute
                 "date" is replaced by current date e.g. 2019-11-22
                 "month" is replaced by current month e.g. 2019-11
                 "week" is replaced by current calender week e.g. 56
                 "minute" looks like 2019-11-22 13:10
                 -> "date" changes the statusmessage every day and thus a daily notification is triggered as long a alarm condition is active

IMPORTANT: statusmessage should not contain semicolons, colons and commas; generally avoid special characters


1) Testing whether 1Hz data from column x of sensor "MYSENS_1234_0001" exceeded a certain threshold of 123 in the last 
10 minutes. Send the defined default message to the notification system as defined in the config file. 

1  :  MYSENS_1234_0001;600;x;123;max;above;default

2) Testing whether 1Hz data from column x of sensor "MYSENS_1234_0001" exceeded on average 123 in the last 
10 minutes. Send a message like "warning issued at 2019-11-22".

2  :  MYSENS_1234_0001;600;x;123;average;above;alarm issued at date

3) Testing whether the standard deviation of 1Hz data from column x of sensor "MYSENS_1234_0001" exceeds on 2 in the last 
10 minutes. Send a message like "found flapping states".

3  :  MYSENS_1234_0001;600;x;2;stddev;above;flapping state

4) Testing whether the median 1Hz data from column x of sensor "MYSENS_1234_0001" exceeds a threshold of 123 in the last 
10 minutes. Send the defined default message to the notification system as defined in the config file. Send a "switch"
command to a connected microcontroller if this state is reached.

4  :  MYSENS_1234_0001;600;x;123;median;above;default;swP:1:4



## 7. Logging and notifications

Please note: if you want to use threshold testing or monitoring, then you can use the installer "install.addapps.sh" in
the install directory to set up/initialize these programs.


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

        addcred -t mail -c mymailservice -u info@mailservice.at -p secret -s smtp.mailservice.at -l 25

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

MARTAS can send notifications directly to the [Telegram] messenger. You need either a TelegramBot or a TelegramChannel plus a user id to setup simple notifications. If you just want to receive notificatins you will find some instruction in 7.5.2 on how to use a private TelegramChannel. See section 7.5.1 for some hints of setting up an environment with the possibility of even interacting with your machine.

For sending notifications you then just need to edit the basic configuration files:

        # if not done install addapps
        cd MARTAS/install
        sudo bash install.addapps.sh

        sudo nano /etc/martas/telegram.cfg

Insert your bot_id (token) and the user_id. Thats it. Then you can use testnote.py to for testing whether its working (eventually you must run this command two times with a different message).

        python3 MARTAS/app/testnote.py -n telegram -m "Hello World, I am here" -c /etc/martas/telegram.cfg -l TestMessage -p /home/user/test.log




### 7.4 Support for NAGIOS/ICINGA


### 7.5 Communicating with MARTAS

MARTAS comes with a small communication routine, which allows interaction with the MARTAS server. In principle, you can chat with MARTAS and certain keywords will trigger reports, health stats, data requests, and many more. Communication routines are available for the [Telegram] messenger. In order to use these routines you need to setup a Telegram bot, referring to your MARTAS.

#### 7.5.1 interactive communication with TelegramBot

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

#### 7.5.2 Receiving Telegram notification via TelegramChannel

  a) Preliminary work

Again you need TelegramBotFather to setup a telegram bot (see section 7.5.1) or you are using an existing one (i.e. MyFirstBot).

Then you need to setup a new private TelegramChannel using your Telegram App. Lets asume you the name of your new TelegramChannel is "MyFirstChannel".

Go to your channel overview and add (i.e. MyFirstBot) as administrator to your channel.

  c) Update /etc/martas/telegram.cfg

        $ nano /etc/martas/telegrambot.cfg

      -> you need the BotID, which you obtained when creating the new BOT - put that into "token"

      -> user_id should point to your channel . i.e. @MyFirstChannel for public channels
      -> for private channels send any message within the channel. Then copy the link of this message:
      i.e. https://t.me/c/1123456789/31
      add a preciding -100 and you got your id: "-1001123456789"



## 9. Frequently asked questions

#### During installation of pip packages dependency problems are occuring

If you observe such problems (problems occured in the past with matplotlib, numpy and/or scipy) then it is advisable
to install the recommended packages for your system using apt instead of pip. Please remove the pip packages (pip remove..) and install system
packages using e.g. sudo apt install python3-scipy

#### I want to send out data periodically from a MARTAS acquisition machine using FTP or similar. Is this easily possible?

use app/file_upload.py within crontab (see 8.6)

#### I want download buffer files from the MARTAS machine peridically in order to fill gaps of my qos 0 MQTT stream. How to do that?

use app/file_download.py within crontab (see 8.5)


## 10. Checklist for error analysis

### 10.1 Acquisition

In order to find any issues with data acquisition we recommend to check the following aspects:

    1) acquisition process running?  

              sudo /etc/init.d/martas status

       if not start/restart the process

    2) log file contents?

              tail -30 /var/log/magpy/martas.log

       Check the logfile contents. Typically they might indicate already what is going wrong. For more detailed information within the logfiles please edit "martas.cdf" and set "debug  :  True" before restarting the acquisition process.

    3) buffer file written?

              ls -al /srv/mqtt/YOURSENSOR/

       Check if buffer data written. If buffer file is not written please check acquisition with debug mode (see above). Is your sensor already supported?

### 10.2 Data transfer and MQTT Broker

    1) Can I subscribe to the MQTT data stream?  

              mosquitto_sub -t TOPIC/#

        Above command, issued on the defined data broker (in martas.cfg) will give you some information on published data.

    2) Can I subscribe to the data from elsewhere?

              mosquitto_sub -h BROKER_IP_ADDRESS -t TOPIC/#

         If this one fails check section 1.1 again.

    2) Can I publish data to a broker?

              mosquitto_pub -h BROKER_IP_ADDRESS -t testTOPIC -m "Hello"

              If this one fails check section 1.1 again.

### 10.3. MARCOS collector

1) collector process running?  

          sudo /etc/init.d/collect-MYBROKER status

   if not start/restart the process

2) log file contents

          tail -30 /var/log/magpy/COLLECT.log

   Check the logfile contents. Typically they might indicate already what is going wrong. For more detailed information within the logfiles please edit "martas.cdf" and set "debug  :  True" before restarting the acquisition process.

3) data files/ database  written

          DATABASE:
          mysql -u user -p mydb
          select * from DATATABLE order by time desc limit 10;

          FILE:
          ls -al /my/file/destination/


## 11. Strucure/Files in home directory of MARTAS user

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
app/backup_config.sh    |	Bash scripts wich creates a zipped backup file containing all configuration information - stored in HOME/Backups (apply weekly or monthly, section 3.5)
app/cleanup.sh    |	remove buffer files older than a definite period
app/deleteold.py    |	delete old inputs from a database, using a sampling rate dependent indicator (deleteold.py -h)
app/di.py    |	Routine based on MagPys absoluteAnalysis tool to analyse geomagnetic DI measurements from multiple input sources/observatories.
app/file_upload.py    |	Wrapper to upload files to remote machine using either ssh, rsync, ftp
app/file_download.py    |	Wrapper to download files to remote machine using either ssh, rsync, ftp
app/monitor.py    |	Monitoring application to check buffer files (martas), database actuality (marcos), disk space and log files; can trigger external scripts
app/mpconvert.py    |	converts MARTAS binary buffer files to other formats
app/optimzetables.py    |	application to be used with archive.py or deleteold.py; uses SQL Optimze methods to clear the table space after data has been removed - non-blocking
app/sendip.py    |	Helper for checking and sending public IP  (via ftp) - OLD
app/serialinit.py    |	Load initialization file (in init) to activate continuous serial data delivery (passive mode)
app/telegramnote.py    |	Small program to send notes to a Telegram Messenger BOT. Useful for periodic information as an alternative to e-mail.
app/testnote.py    |	Small routine to test notification sending via email, telegram, etc.
app/testserial.py    |	Small routine to test serial communication.
app/threshold.py    |	Threshold tester (see section 7.1)
app/obsdaq.py        | communicate with ObsDAQ ADC (see section 10.1.5)
app/palmacq.py       | communicate with PalmAcq datalogger (see section 10.1.5)
app/collectfile.py    |	access data locally or via rsync/ssh/ftp and add it to files/DB - OLD - replaced by file_download
app/senddata.py    |	Send data from MARTAS to any other machine using cron/scheduler - OLD - replaced by file_upload
**core**  |  Core methods used by the most runtime scripts and applications
core/martas.py    |	basic logging routines for MARTAS/MARCOS and wrapper for e-mail,logfile,telegram notifications
core/acquisitionsupport.py    |	contains general communication methods and configuration file interpreters
**conf**  | Basic initialization files - used by installer
conf/sensors.cfg    |	skeleton for sensors configuration information
conf/martas.cfg    |	skeleton for basic MARTAS configuration -> acquisition
conf/marcos.cfg    |	skeleton for basic MARCOS configuration -> collector
conf/obsdaq.cfg    |	skeleton for basic obsdaq configuration - enter path in martas.cfg (see 10.1.5)
**init**  | Basic initialization files - used by installer
init/martas.sh    |	Start script to be used in /etc/init.d
init/autostart.sh    |	Run to add and sctivate /etc/init.d/martas
init/martas.logrotate    |	Example script to activate logrotation
init/gsm90v7init.sh    |	Initialization script GEM GSM90 v7
init/gsm90v6init.sh    |	Initialization script GEM GSM90 v6
init/pos1init.sh    |	Initialization script Quantum POS1
init/bm35init.sh    |	Initialization script Meteolab BM35 pressure
init/obsdaqinit.sh  |   Initialization script for PalmAcq and ObsDAQ
**install**  | Installer scripts. Will update configuration and copy job specific information to /etc/martas (default)
install/install.marcos.sh    |	Installer for collector jobs  (section 6.0)
install/install.martas.sh    |	Installer for acquisition jobs  (section 3.0)
install/install.telegram.sh    |	Installer for Telegram messenger communication (section 7.3)
install/install.addapps.sh    |   Installer for threshold testing and monitor
install/recover.martas.sh    |   Recovery script to apply a backup (app/backup_config.sh) to a newly installed system (section 3.5)
**libraries**  |  contain communication libraries for specific systems/protocols/instruments (required by acquisition.py)
libmqtt/...    |			library for supported instruments (mqtt streaming)
libwamp/...    |		library for sup. inst. (wamp streaming) - DISCONTINUED
**web**  |  Webinterface as used by the collector with destination websocket
web/index.html    |		local main page
web/plotws.js    |	  	arranging plots of real time diagrams on html page
web/smoothie.js    |		plotting library/program (http://smoothiecharts.org/)
web/smoothiesettings.js    |        define settings for real time plots
oldstuff/...    |		        Folder for old contents and earlier versions


## 12. Appendix

### 12.1 Libraries

| Instrument          | versions | Inst-type   | Library                  | mode     | init           | requires         |
|---------------------|----------|-------------|--------------------------|----------|----------------|------------------|
| Arduino             |          | multiple    | activearduinoprotocol.py | active   |                |                  |
| AD7714              |          | multiple    | ad7714protocol.py        | active   |                |                  |
| Arduino             |          | multiple    | arduinoprotocol.py       | passive  |                |                  |
| BM35-pressure       |          | pressure    | bm35protocol.py          | passive  | bm35init.sh    |                  |
| BME280              |          | pressure    | bme280i2cprotocol.py     | passive  |                | adafruit_bme280  |
| CR1000/800          |          | multiple    | cr1000jcprotocol.py      | active   |                | pycampbellcr1000 |
| Cesium G823         |          | mag-scalar  | csprotocol.py            | passive  |                |                  |
| Thies LNM           |          | laserdisdro | disdroprotocol.py        | active   |                |                  |
| DSP Ultrasonic wind |          | 2D wind     | dspprotocol.py           | active   |                |                  |
| ENV05               |          | temp-humid  | envprotocol.py           | passive  |                |                  |
| 4PL Lippmann        |          | geoelec     | fourplprotocol.py        | active   |                |                  |
| GIC                 |          | special     | gicprotocol.py           | active   |                |                  |
| GP20S3              |          | mag-scalar  | gp20s3protocol.py        | passive  |                |                  |
| GSM19               |          | mag-scalar  | gsm19protocol.py         |          |                |                  |
| GSM90               |          | mag-scalar  | gsm90protocol.py         | passive  | gsm90v?init.sh |                  |
| DataFiles           |          | multiple    | imfileprotocol.py        | active   |                |                  |
| LEMI025             |          | mag-vario   | lemiprotocol.py          | passive  |                |                  |
| LEMI036             |          | mag-vario   | lemiprotocol.py          | passive  |                |                  |
| Tilt Lippmann       | develop  | tilt        | lmprotocol.py            | active   |                |                  |
| LORAWAN             | develop  | multiple    | lorawanprotocol.py       |          |                |                  |
| MySQL               |          | multiple    | mysqlprotocol.py         | active   |                |                  |
| ObsDaq              |          | multiple    | obsdaqprotocol.py        | active   | obsdaqinit.sh  |                  |
| OneWire             |          | multiple    | owprotocol.py            | passive  |                |                  |
| POS1                |          | mag-scalar  | pos1protocol.py          | passive  | pos1init.sh    |                  |
| Test                | 2.0.0    | special     | testprotocol.py          |          |                |                  |

The library folder further contains publishing.py defining different MQTT topic/payload formats and lorawan stuff. 

### 12.2 Initialization files

#### 12.2.1 GEM Systems Overhauzr GSM90

Using the initialization file of the GSM90 a command will be send towards the system in order to initialize passive data transfer. You need to edit the initialization file within the configuration directory (default is /etc/martas/init/gsm90...). Please adjust the connected serial port (e.g. S1, USB0 etc) and adept the following parameters:

        -b (baudrate) : default is 115400
        -p (port)
        -c (command to send:)
            S
            5          -> filter (5= 50Hz, 6= 60Hz)
            T048.5     -> Tuning field in microT
            C          ->
            datetime   -> initialize time with PC time (see option k)
            h          -> switch to auto-cycle method (sometime necessary)
            D          -> sampling rate: D -> down, U -> up, leave out to keep sampling rate
            R          -> Run

#### 12.2.2 Quantum POS1

#### 12.2.3 Meteolabs BM35 pressure

#### 12.2.4 ObsDAQ / PalmAcq

Having set up MARTAS, but before logging data, make sure to have the right settings for Palmacq and ObsDAQ.
1) Use palmacq.py -h  and obsdaq.py -h for further information. These two scripts can be used to make settings easily by editing, but it is recommended not to edit beyond " # please don't edit beyond this line "
2) This step is optional: use obsdaqinit.sh without config file to test the initialization of PalmAcq and ObsDAQ (edit file). Final settings should be written into obsdaq.cfg.
3) edit obsdaqinit.sh (set MARTAS dir and path to obsdaq.cfg)
4) Edit martas.cfg to tell MARTAS where to find obsdaqinit.sh e.g.
      initdir  :  /etc/martas/init/
5) Add following line to martas.cfg, e.g.:
      obsdaqconfpath  :  /etc/martas/obsdaq.cfg
6) Edit sensors.cfg e.g. like following line:
      FGE\_S0252\_0002,USB0,57600,8,1,N,passive,obsdaqinit.sh,-,1,obsdaq,FGE,S0252,0002,-,ABS-67,GPS,magnetism,magnetic fluxgate from Denmark
7) start acquisition by e.g. /etc/init.d/martas start. Note, that acquisition will not start until Palmacq gets LEAPSECOND (= 18, set in obsdaq.cfg) over the GPS antenna. This guarantees correct GPS time. From now on NTP time will be recorded additionally in the sectime column

#### 12.2.5 LM


### 12.3 Dallas OW (One wire) support

a) modify owfs,conf
        $ sudo nano /etc/owfs.conf

      Modify the following parts as shown below:
        #This part must be changed on real installation
        #server: FAKE = DS18S20,DS2405

        # USB device: DS9490
        server: usb = all

b) start the owserver
        $ sudo etc/init.d/owserver start


### 12.4  Communicating with an Arduino Uno Microcontroller

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


## 13. Installation of a MARTAS Box - recipies

### 13.1 MARTAS minimal installation with root privileges - Debian systems like Raspberry, Ubuntu, Beaglebome, etc

#### 13.1.1 Step 0: Get you Debian system ready (install Ubuntu, Raspberry, Beaglebone, etc)

Please install your preferred debian like system onto your preferred hardware. MARTAS will work with every debian like system. Please follow the installation instructions given for the specific operating system. In the following we will give a quick example of such preparations for a Raspberry installation using debian bullseye:

Install the operating system (i.e. debian bullseye) on a SD card using i.e. Balena Etcher. Do that on your linux working PC, which is NOT the single board computer. Afterwards insert the SD card into the single board computer and boot it. Finish the initial configurations as requested during the boot process. 

Afterwards you might want to change hostname (Raspberry PI configuration or update /etc/hostname and /etc/hosts), partitions on SD card (sudo apt install gparted), proxy configurations (/etc/environment) and in case of raspberry enable ssh (raspberry PI configuration).

#### 13.1.2 Step 1: Install necessary packages for all MARTAS applications

Packages for MARTAS (including NAGIOS and MagPy support):

        sudo apt update
        sudo apt upgrade
        sudo apt-get install ntp arduino ssh mosquitto mosquitto-clients nagios-nrpe-server nagios-plugins fswebcam python3-matplotlib python3-scipy python3-serial python3-twisted python3-wxgtk4.0 python3-pip

After installation you might want to configure ntp servers. You can activate pwd-less ssh access.
To change from local time to UTC time the following command is useful:

        sudo dpkg-reconfigure tzdata

Configure the mosquitto MQTT broker:

        sudo nano /etc/mosquitto/conf.d/listener.conf

Insert the following lines:

        listener 1883
        allow_anonymous true
        # Use the following line and ananymus false for authenicated login
        #password_file /etc/mosquitto/passwd
        max_queued_messages 3000

Restart and check the status of the mosquitto broker

        sudo systemctl restart mosquitto.service
        sudo systemctl status mosquitto.service

#### 13.1.3 Step 2: Install MARTAS

Open a terminal and clone MARTAS into your home directory:

        cd ~
        git clone https://github.com/geomagpy/MARTAS

OPTIONAL: create a special python environment for all MARTAS related packages

        python3 -m menv /path/to/menv

Install MARTAS:

        cd ~/MARTAS/install
        sudo bash install.martas.sh

An initial question will ask for the python path. If you are using an optional environment, then please insert this path. All required packages will then be installed in this environment.
Install monitoring and additional MARTAS applications:

        cd ~/MARTAS/install
        sudo bash install.addapps.sh

Copy some default routines into the configuration path

        sudo cp ~/MARTAS/app/cleanup.sh /etc/martas/
        sudo cp ~/MARTAS/app/backup_config.sh /etc/martas/

and add them into the scheduler:

        sudo nano /etc/crontab

        # Insert these lines into /etc/crontab
        15 0    * * * root /bin/bash /etc/martas/cleanup.sh
        10 0    1 * * root /bin/bash /etc/martas/backup_config.sh
        5  0    * * * root /etc/init.d/martas start

Thats it. MARTAS is now ready to be used. Continue with sensor definitions and tests. Alternatively you can recover configurations from a previously backuped system (continue with 13.1.4).

Useful commands to check ports for sensor definitions are i.e.

        dmesg | grep usb

#### 13.1.4 optional Step 3: recover a previously backuped system

Please also check section 3.5. 

Copy the backup file to the new MARTAS machine i.e. in directory /home/user/Downloads/

Then run the following command and follow the instructions:

        cd ~/MARTAS/install
        sudo bash recover.martas.sh

IMPORTANT: Recovered configuration files will replace all previously exisiting files. Please note: if python paths are changing (i.e. now python3, previously python2) then these paths need to be updated after recovery. Please carefully chech /etc/martas/init/*.sh, /etc/init.d/martas,  as well as all configuration files in /etc/martas. 

#### 13.1.5 optional use of a python environment

##### a) using venv

Create a python environment for all MARTAS related packages using 

        python3 -m venv ~/martasenv

Activate the python environment before installing packages

        source ~/martasenv/bin/activate

Optional: You might want to install the requires packages before installing MARTAS (otherwise MARTAS will install them) 

        pip install geomagpy
        pip install pyserial
        pip install paho-mqtt
        pip install twisted
        pip install python-telegram-bot==13.4
        pip install telegram-send
        pip install psutil
        pip install telepot
        pip install platform

Provide the correct path to the python executable during MARTAS installation (replace USER or the path accordingly):

        python path (default: /usr/bin/python3): /home/USER/martasenv/bin/python


##### b) using conda

Download and install a current mini/anaconda version
Follow the instructions as provided here: 

Create a new conda environment


Activate the conda python environment before installing packages

        conda activate martasenv

Install required conda packages before installing MARTAS ( to be tested )

        conda install numpy
        conda install matplotlib 
        conda install scipy
        conda install twisted
        conda install pyserial
        pip install geomagpy

### 13.2 Full installation on Raspberry - MARCOS/MARTAS


The following example contains a full installation of MARTAS, MARCOS with full database support, XMagPy, Nagios monitoring control, Webinterface, and an archive on an external harddrive.

```
sudo apt-get install curl wget g++ zlibc gv imagemagick gedit gedit-plugins gparted ntp arduino ssh openssl libssl-dev gfortran  libproj-dev proj-data proj-bin git owfs mosquitto mosquitto-clients libncurses-dev build-essential nagios-nrpe-server nagios-plugins apache2 mariadb-server php php-mysql phpmyadmin netcdf-bin curlftpfs fswebcam

# alternative - system python
sudo apt-get install python3-matplotlib python3-scipy cython3 python3-h5py python3-twisted python3-wxgtk4.0 python3-pip

sudo pip3 install pymysql
sudo pip3 install pyproj
sudo pip3 install paho-mqtt
sudo pip3 install pyserial
sudo pip3 install pexpect
sudo pip3 install service_identity
sudo pip3 install pyownet
sudo pip3 install geomagpy


cd ~/Downloads/
git clone git://github.com/SalemHarrache/PyCampbellCR1000.git
cd PyCamp*
sudo python3 setup.py install

####
#### Optional: Setup MARTAS
####

cd ~
git clone https://github.com/geomagpy/MARTAS.git



#Create a desktop entry for MagPy
# -------
#[Desktop Entry]
#Type=Application
#Name=XMagPy
#GenericName=GeoMagPy User Interface
#Exec=xmagpy
#Icon=/usr/local/lib/python3.8/dist-packages/magpy/gui/magpy128.xpm
#Terminal=false
#Categories=Application;Development;

cd ~/Downloads/
sudo cp xmagpy.desktop /usr/share/applications/



### Create a Database: magpy
# -------
# Firstly create a super user
sudo mysql -u root
> CREATE DATABASE magpydb;
> GRANT ALL PRIVILEGES ON magpydb.* TO 'magpy'@'%' IDENTIFIED BY 'magpy' WITH GRANT OPTION;
> FLUSH PRIVILEGES;

# Initialize magpy DB
# -------
python
>>> from magpy.database import *
>>> db=mysql.connect(host="localhost",user="magpy",passwd="magpy",db="magpydb")
>>> dbinit(db)
>>> exit()

# install martas and marcos  (StationName: box)
# -------
cd ~/MARTAS/app
addcred -t db -c magpydb -u magpy -p magpy -d magpydb -o localhost
sudo addcred -t db -c magpydb -u magpy -p magpy -d magpydb -o localhost
cd ~/MARTAS/install
which python
# Station = box
sudo bash install.martas.sh
sudo bash install.marcos.sh

# set background picture of Cobs
# -------
sudo cp ~/Downloads/magpybox.jpg /usr/share/rpd-wallpaper/

# Links to phpmyadmin and Cobs in Browser
# -------
->manual

# Configuration and cleanup
# -------

# telegram and addaps
sudo bash install.telegram.bot
sudo bash install.addapps.sh
#-> us bot farther to create a new bot for the machine, update keys und user_ids

# timeserver
sudo dpkg-reconfigure tzdata

# remote access
anydesk, teamviewer or tmate

# CRONTAB
# check all crontab for $PYTHON and other vaiables

# OWFS
$ sudo nano /etc/owfs.conf

#Modify the following parts as shown below:
#This part must be changed on real installation
#server: FAKE = DS18S20,DS2405

# USB device: DS9490
server: usb = all

#NAGIOS
sudo nano /etc/nagios/nrpe.cfg
# MARTAS/MagPy commands:
# -----------------
command[check_procs_martas]=/usr/lib/nagios/plugins/check_procs -c 1:1 -C python -a acquisition.py
command[check_all_disks]=/usr/lib/nagios/plugins/check_disk -w 20% -c 10% -e -A -i '.gvfs'
command[check_log]=/usr/lib/nagios/plugins/check_log -F /var/log/magpy/martas.log -O /tmp/martas.log -q ?

# NTP check (optional)
#command[check_ntp_time]=/usr/lib/nagios/plugins/check_ntp_time -H your.ntp.server -w 1 -c 2


# CRONTAB
crontab -e
PYTHON=/usr/bin/python3
BASH=/usr/bin/bash

#MARTAS - delete old buffer files
15 0 * * * $BASH /home/pi/MARTAS/app/cleanup.sh
#MARCOS - archive database contents
30 0 * * * $PYTHON /home/pi/MARTAS/app/archive.py -c magpydb -p /srv/archive


# MOUNT external disks
#Get UUID
sudo blkid
sudo nano /etc/fstab

#add a line like
UUID=d46...   /srv   ext4  defaults,auto,users,rw,nofail  0  0

#activate
sudo mount -a


## FINALLY TEST IT!

```
### 13.3 Testing MQTT data transfer

See also in section 10.2 (error analysis). On the collector or any other MQTT machine issue the following subscription command:

        mosquitto_sub -h IPADDRESS_OF_MARTAS -t test/#

On the freshly installed MARTAS machine issue the following command:

        mosquitto_pub -h localhost -m "test message" -t test -d

In case you are using a different MQTT broker: change 'localhost' and 'IPADDRESS_OF_MARTAS' with the IP of the BROKER
In case you are using authenticated access use the following additional options:

        mosquitto_pub -h localhost -m "test message" -t test -u USERNAME -P SECRET -d

As soon as you press return at the mosquitto_pub command you should read "test message" below your subscription command. Checkout the official mosquitto pages for more information.

## 14. Short descriptions and Cookbooks

### 14.1 quick steps to run a new MARTAS with a new sensor for the first time

In this example we use a MARTAS i.e. readily installed beaglebone and connect a GSM19 Overhauzer sensor:

A. GSM19 Sensor

   1. Power on by pressing "B"
   2. go to "C - Info"
   3. go to "B - RS232"
   4. note parameters and then "F - Ok"
   5. switch real-time transfer to yes and then "F - Ok"
   6. "F - Ok"
   7. press "1" and "C" for main menu
   8. start recording - press "A"
   9. if GPS is set to yes wait until GPS is found

B. MARTAS - beaglebone (BB)
   1. connect BB to a DHCP network (if not possible connect a usbhub and screen+keyboard, then login and continue with 4.)
   2. find out its IP
      - option (1): with fully installed telegrambot: just send "getip" to the bot
      - option (2): connect a screen and use ifconfig
      - option (3): from a remote machine in the same network: check router or use nmap
   3. connect to BB via ssh:
      defaultuser: debian
   4. stop MARTAS:
              $ sudo su
              $ /etc/init.d/martas stop
   5. connect your sensor to the usb serial port using a usb to rs232 converter
   6. check "lsusb" to see the name of the converter (e.g. pl2303)
   7. check "dmesg | grep usb" to get the connections port like ttyUSB0
   8. edit /etc/martas/sensors.cfg
      make use of the SENSORID, the parameters of A4 and the port info of B7
      (SENSORID should contain serial number of the system  i.e. GSM19\_123456\_0001)
   9. save /etc/martas/sensors.cfg

A. GSM19 Sensor
   10. final check of sensor configration (i.e. base mode, 1 sec, no AC filter)
   11. start recording

B. MARTAS
   10. start recording:
              $ sudo su
              $ /etc/init.d/martas start
              $ exit
   11. check recording:
              $ cat /var/log/magpy/martas.log (check log file)
              $ ls -al /srv/mqtt/SENSORID  (check buffermemory for new data)

### 14.2 quick steps to setup a fully configured MARTAS with the respective sensor(s)

In this example we use a MARTAS with a GSM19 Overhauzer sensor:

A. Sensor (GSM19)

   1. Connect the sensor to power and MARTAS
   2. Switch on the sensor and start recoding (all A steps in 12.6.1)

B. MARTAS
   1. Connect MARTAS to power

Check whether everything is running. On MARTAS you should check whether the buffer file is increasing and eventually the log file.
Please note: data is written as soon as all sensor specific information is available. When attaching a micro controller (i.e. arduino)
you might need to wait about 10 times the sampling rate (i.e. 10min for 1min sampling rate) until data is written to the buffer.



## 15. Issues and TODO

in some cases, if the recording process terminates, the daily buffer file might be corrupt. In that case you need to delete the daily file and restart the recoding process. The next daily file will be OK in any case.

- add trigger mode for GSM90 (sending f)
- add to #5
- update scp_log to use protected creds
- add in how-to for using senddata and addcreds



[Telegram] : <https://telegram.org/>
[Telegram Botfather] :  <https://core.telegram.org/bots>
[Arduino Microcontroller] : <http://www.arduino.cc/>
