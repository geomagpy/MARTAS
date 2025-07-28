# MARTAS

**MagPys Automated Real Time Acquisition System**

![0.0.0](./martas/web/assets/header.png "MARTAS")


MARTAS is a collection of python applications and packages supporting data acquisition, collection, storage, monitoring 
and analysis in heterogeneous sensor environments. MARTAS is designed to support professional observatory networks and
data sources consisting of timeseries measurements from locally fixed instruments. The package contains two main 
modules: MARTAS for data acquisition and MARCOS for data collection.
**MARTAS**: Data acquisition makes use of an instrument library which currently includes many sensors typically used in
observatories around the globe and some development platforms. Basically, incoming sensor data is converted to a 
general purpose data/meta information object which is directly streamed via IOT protocols, namely MQTT 
(message queue transport) to a data broker. 
**MAROCS**: A data collection system, called MARCOS (MagPys Automated Realtime 
Collector and Organization System), can be setup within the MARTAS environment. MARCOS collection routines can access
MQTT data stream and store/organize such data and meta information in files, data banks or forward them to web sockets.
All data can directly be analysed using [MagPy]() which contains many time domain and frequency domain time series analysis
methods.

Developers: R. Leonhardt, R. Mandl, R. Bailey (GeoSphere Austria)

### Table of Contents

1. [About](#1-about)
2. [Installation](#2-installation)
3. [Initialization of MARTAS/MARCOS](#3-initialization-of-martasmarcos)
4. [MARTAS](#4-martas)
5. [MARCOS](#5-marcos)
6. [Applications](#6-applcations)
7. [Logging and notifications](#7-logging-and-notifications)
8. [Additional tools](#8-additional-tools)


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

A typical installation of a MARTAS data acquisition system with a supported sensor is finished within minutes, the
setup of a MARCOS collection system strongly depends on its complexity and amount of data sources. For both setups 
a single command will guide you through the initialization routine. After installation issue

         $ martas_init

and answer the questions. Then modify the requested configurations and you are done. Nevertheless, please carefully 
read the sections on installation and MARTAS/MARCOS specifics. I also spend some time on describing the basic idea,
additional tools and analysis packages, which might be helpful for one or the other.

Note: in the following examples we use "USER" as username and "USERS" as group. Replace these names with your 
user:group names. All instructions assume that you have a profound knowledge of debian like linux systems, as such a 
system is the only prerequisite to run MARTAS.

### 1.1 The MARTAS/MARCOS naming conventions and data model

MARTAS is focusing on instrument level. Each instrument is characterized by its human readable name and its serial 
number. This information provides an unique reference i.e. a LEMI025 sensor with serial number 56 is typically 
denoted as LEMI025_25. To each instrument a revision number is assigned, providing the possibility to track upgrades,
repairs and maintenance. The combination of instrument name, serial number and revision number is referred to as 
**SensorID**, i.e. LEMI025_56_0001. If you are using a MARCOS collection system with database support, the table SENSORS
will contain all relevant information regarding each SensorID. An instrument like the LEMI025 might record several 
different signals, like three components of geomagnetic field variation, temperatures of electronics and sensor, 
support voltages. These components are referred to as **SensorElements**. For better searchability of the data base it 
is also useful to assign each sensor to a **SensorGroup** (i.e. magnetism), which denotes the primary purpose of the 
instrument and a **SensorType**, which describes the primary physical measurement technique (i.e. fluxgate). The 
individual **SensorElements** however can perform measurements outside the primary group, so each **SensorElement** will
refer to a specific **Field** i.e. temperature probes of LEMI025 will be connected to the field "temperature". An 
instrument is typically setup at a specific location, characterized by its geographical position, a specific 
station name i.e. the observatory, and eventually a specific pier within the station. At this location data is acquired
with the instrument and such data sets are described by the SensorID and a data revision code, referred to as **DataID**
i.e. LEMI025_56_0001_0001. Specific information on each data set is summarized in table DATAINFO referring to the
DataID's. The database will contain pure data tables named by DataID and all acquisition relevant information in 
DATAINFO, including location coordinates and references to station and eventually pier. The station information is 
collected in table STATION, defined by a **StationID** i.e. an observatory defined by its observatory code. Pier 
information might by collected in table PIERS, referring to a specific **PierID**.
 
![1.1.0](./martas/doc/namingconvention.png "Naming convention and database organization")
Figure 1.1.0: An overview about the naming convention. The naming convention is directly used for structuring the 
MARCOS database. Each bold name corresponds to a table within the database. It is strongly recommended to keep the
general structure of the naming convention ( SensorName_SerialNumber_SensorRevision_DataRevision ) even if not using data
base support.

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
        sudo apt-get install owserver
        pip install pyownet


### 2.2 Installing MARTAS/MARCOS

Please make sure that packages as listed in 2.1 are installed. Then create a python environment:

        $ virtualenv ~/env/martas

or virtualenv -p /usr/bin/python3 ~/env/martas 
Then activate the environment:

        $ source ~/env/martas/bin/activate

Get the most recent MARTAS package:

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

        $ sudo nano /etc/mosquitto/conf.d/listener.conf

    to open an empty file.

    Paste in the following:
        listener 1883
        allow_anonymous false
        password_file /etc/mosquitto/passwd

    Restart mosquitto

Thats it. How to use credentials in MARTAS is described in section 7.x. If you have problems restarting mosquitto you 
might want to check the read permissions of the /etc/mosquitto/passwd file.

In order to access such protected MQTT data streams you can use the addcred tool in order to avoid plain passwords in 
your configuration files. Please note, that this method does not encrypt passwords. It just obsfucate it and store it 
in a different, independent file. To add such information into the credentials list use:

        $ addcred -t transfer -c mqtt -u user -p mypasswd -a localhost

Provide the shortcut (mqtt) and username during the installation process.

#### 2.3.3 Testing MQTT data transfer

Issue the following subscription command:

        mosquitto_sub -h IPADDRESS_OF_MARTAS -t test/#

On a freshly installed MARTAS machine issue the following command:

        mosquitto_pub -h localhost -m "test message" -t test -d

In case you are using a different MQTT broker: change 'localhost' and 'IPADDRESS_OF_MARTAS' with the IP of the BROKER
In case you are using authenticated access use the following additional options:

        mosquitto_pub -h localhost -m "test message" -t test -u USERNAME -P SECRET -d

As soon as you press return at the mosquitto_pub command you should read "test message" below your subscription
command. Checkout the official mosquitto pages for more information.
 
#### 2.3.4 Understanding Quality-of-Service (QOS)

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
tools ideally before running martas_init, and provide credential information using [addcred](https://github.com), section 10.6. 
You might want to checkout [section 6.1](#6-1) for details on notifications and [section 5.3.2](#5-3-2) for database 
support. Please also make sure that you have write permissions on the directories to be used and that those directories
exist already.

The martas_init routine will create a .martas folder and copy some applications into this directory. When updating 
the martas python package, these apps remain unaffected. In order to update the apps you should run martas_init again
with the -u option. If you want to replace an existing martas/marcos installation and reset the contents of all 
configuration files then run the martas_init command with the -r option. By default martaa_init will create a .martas
folder in the uses home directory for storing its data and configurations. You can change this directory by providing
another path (relative to the users homedirectory) using -d. I.e. -d MARTAS will use /home/user/MARTAS as default 
directory.

### 3.2 Inputs during setup

The required inputs are self explaining. Please read the comments and suggestions carefully. Before starting the 
initialization routine make sure that you know what to do, i.e. read the manual. If you did anything wrong you can 
restart/redo initialization anytime using option -r. You will need information about paths, storage directories,
database, communication protocols etc. You can modify anything later by editing the configuration files.

### 3.3 Running MARTAS/MAROCS after initialization

Martas_init will update your users crontab and schedule a number of jobs for running the respective module. Typically
the main job will be started shortly after midnight. You might want to issue this command directly after initialization.
Depending on which module (MARTAS or MARCOS) you are installing, you will have a series of scheduled applications.
Please checkout the module specific sections for details.

In order to start your desired module directly after initialization use one of the commands (or check 
crontab -l for the exact name) as listed in section 4.2 or 5.2.

## 4. MARTAS

### 4.1. Quick instructions

Setting up a MARTAS data acquisition system can be accomplished very quickly, if you already have some experience.

**Step 1**: initialize MARTAS using martas_init (details on [martas_init](#3-initialization-of-martasmarcos)) 

        (martas)$ martas_init

**Step 2**: update/insert sensor information in sensors.cfg (details in [section 4.2](#42-defining-and-configuring-sensors)) 
 
        (martas)$ nano ~/.martas/conf/sensors.cfg

**Step 3**: start MARTAS (details in [section 4.5](#45-running-the-acquisition-system)). Actually MARTAS will be 
started automatically after some time.

        (martas)$ cd ~/.martas
        (martas)$ bash -i runmartas.sh start

**Step 4**: view MARTAS acquisition (details in [section 4.6](#46-the-martas-viewer)) 

        (martas)$ cd ~/.martas
        (martas)$ bash martas_view

Open webpage http://127.0.0.1:8050

### 4.2 Defining and configuring sensors

#### 4.2.1 The sensors.cfg configuration file

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
- sensorids should follow the [naming](#11-the-martasmarcos-naming-conventions-and-data-model) convention

Further details and descriptions are found in the commentary section of the sensors.cfg configuration file.

#### 4.2.2 Obtaining parameters for sensors.cfg

Sensors.cfg requires a number of parameters for proper communication. Please consult the sensor specific article in
[section 4.4](#44-examples-for-sensor-definitions-in-sensorscfg) for supported systems and the manual of your sensor.
In addition you will need to provide connection details, in particular the port of the device. The following linux
commands will help you to identify the ports. If you connect you system to a real serial port, the number should be 
written next to the port. In case of USB connections, also when using serial-to-usb converters, you will find out the 
connection as follows. 

The command *lsusb* will give you an overview about USB connections. When issuing this command before and after you 
attach a serial-to-usb device you will find out the name and type of this device.

        $ lsusb

In order to get the corresponding device port (i.e.ttyUSB0) you can use the following command.

        $ dmesg | grep usb

### 4.3 Sensors requiring initialization

Several sensors currently supported by MARTAS require an initialization. The initialization process defines e.g. 
sampling rates, filters, etc. in a way that the sensor systems is automatically sending data to the serial port 
afterwards. MARTAS supports such initialization routines by sending the respective and necessary command sequence to 
the system. Initialization commands are stored within the MARTAS configuration directory (Default: /etc/martas/init).
The contents of the initialization files for supported instruments is outlined in Appendix 10.1. In order to use such
initialization, you need to provide the path within the sensors configuration line in sensors.cfg:

sensors.cfg: line for a GSM90 Overhauzr, the initialzation configuration is taken from gsm90v7init.sh (within the 
martas config directory)

        GSM90_6107631_0001,S1,115200,8,1,N,passive,gsm90v7init.sh,-,1,GSM90,GSM90,6107632,0002,-,AS-W-36,GPS,magnetism,GEM Overhauzer v7.0


### 4.4 Examples for sensor definitions in sensors.cfg

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

         cobsdb,-,-,-,-,-,passive,None,10,1,MySQL,MySQL,-,0001,-,-,-,magnetism,-

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

#### Data files (supported are all data files, readable with MagPy)

         WICadjusted,/home/leon/Cloud/Daten,-,-,-,-,active,None,30,1,IMfile,*.min,-,0001,-,-,-,magnetism,-


### 4.5 Running the acquisition system

Please note: the steps described within this section have already been preconfigured during martas_init. You can 
manually change and re-configure anytime.

#### 4.5.1 Manual start

        (martas)$ cd ~/.martas
        (martas)$ bash -i runmartas.sh start

The following options are now available:

        (martas)$ bash -i runmartas.sh status
        (martas)$ bash -i runmartas.sh start
        (martas)$ bash -i runmartas.sh stop
        (martas)$ bash -i runmartas.sh restart

#### 4.5.2 Automatic schedule

The MARTAS start command is included into the users crontab during the initialization process of martas_init. Therefore
the acquistion job will be started automatically depending on the schedule of the crontab (default is around midnight,
once a day). The process will only be started in case it is not yet running.


### 4.6 The MARTAS viewer

Since MARTAS version 2.0 a MARTAS viewer is included. The viewer will create a local webpage giving you some information
about the MARTAS system, its connected sensors and data. You can start and open the MARTAS viewer as follows: 

        (martas)$ cd ~/.martas
        (martas)$ bash martas_view

Open webpage http://127.0.0.1:8050 will give you something like:

![4.6.1](./martas/doc/martas_viewer.png "The MARTAS viewer")
Figure 4.6.1: The MARTAS viewer provides a quick overview about live data, connected sensors, and some configuration
information. In this example two sensors are connected, one of which is a testing device. The available recorded 
elements are shown on the left side, a "live" image of acquired data is shown on the right side. On the upper right
you can modify the live display.

### 4.7 Additional setups

The initialization process will also schedule a number of additional jobs for your MARTAS maschine, which you can 
modify and/or disable. It also some applications for you eventually might want to enable.

#### 4.7.1 Cleanup of buffer memory

Principally, all data is buffered in binary files, by default within the /home/USER/MARTAS/mqtt directory. 
You can also mount any external storage medium like a SD card or external memory to be used as bufferdirectory. By 
default the buffer memory is handled as some kind of ring-buffer, which only contains data covering a certain timerange. 
Old data is continuously replaced by new data, preventing a buffer overflow. This is done by the configurable cleanup
routine, which has been automatically added and activated in your crontab by the initialization process. 

By default, the cleanup routine will remove local buffer files older than 100 days and local MARTAS backups older then
60 days. You might want to change these values, but at least consider them for remote backups. 


#### 4.7.2 Regular backups of all MARTAS configurations

MARTAS comes with a small [backup application](#64-backup) to be scheduled using cron, which saves basically all MARTAS configuration
files within a zipped archive. The aim of this application is to save all essential information within one single data
file so that in case of a system crash (hardware problem, SD card defect, etc) you can easily and quickly setup an 
identical "new" system. You might also use the backups to setup similar copies of a specific system.
A backup of your MARTAS configuration is automatically scheduled once a week during initialization.

#### 4.7.3 Monitoring MARTAS acquisition

Also scheduled during automatic initialization is a basic [monitoring routine](#612-monitor), which makes use of the given 
notification method, provided that this method is properly configured. The basic monitoring process will watch 
your disk sizes for buffer memory, the martas logfile for errors and the actuality of the buffer files. Changing states
or critical remaining disk sizes will issue messages. The martas logfile, typically to be found in ~/.martas/log, will
be subject to logrotate, in order to prevent an overflow. 

#### 4.7.4 Warning messages with threshold tester

The [threshold](#621-threshold) testing routine is prepared and preconfigured but NOT enabled. In order to do so, adept the parameters
of the configuration file and activate it in crontab.

### 4.8 Checking runtime performance and/or troubleshooting

A few hints in order to test for proper recording and data publication.

1) Check the log files, typically to be found in ~/.martas/log/martas.log

2) Check the buffer file actuality, i.e. ls -al ~/MARTAS/mqtt/YOURSENSORID/

3) Check MQTT publication

           mosquiito_sub -h BROKER -t STATIONID/#

## 5. MARCOS

### 5.1. Quick instructions

In the following we are setting up MARCOS to collect measurement data from a broker. MARCOS subscribes to the broker 
and receives any new data published there. All three systems, MARTAS, BROKER, and MARCOS can run on the same machine 
as different processes. You can also have several MARCOS collectors accessing the 
same broker independently.

**Step 1**: Setup database, create paths for archives and add credentials depending on your projected detsination ([section 5.4](#54-data-destinations))

**Step 2**: initialize a MARCOS collector using martas_init (details on [martas_init](#3-initialization-of-martasmarcos)) 

        (martas)$ martas_init

You will have to provide a name for the collection job. I recommend to use the hostname of the broker/acquisition 
machine. In the following I use MYJOB1 as an example name.

**Step 3**: eventually review/update configurations (details in [section 5.2](#52-marcos-specific-configurations))

The initialization routine will setup a number of scheduled jobs for backup, monitoring, database management, and 
archiving. It will prepare jobs for filtering and threshold testing.

**Step 4**: Run the collection job (details in [section 5.3](#53-running-a-collection-job)) 
 
        $ bash collect-MYJOB1.sh update #(important for first time usage with database - see below)

The collection job will also start automatically around midnight.

**Step 5**: For adding further collection jobs repeat steps 2 and 4

**Step 6**: Eventually setup schedules analyses like flagging, adjusted data preparation and DI analysis ([section 8.1](#81-analysispy-for-continuous-flagging-adjustedquasidefinitive-data-products-and-status-information-))


### 5.2 MARCOS specific configurations

MARCOS subscribes to the data broker and obtains published data depending on the selected "topic". You can select 
whether this data is then stored into files (binary buffer files, supported by MagPy), into a data base (mariadb, mysql)
and/or published on a webserver. You can also select multiple destinations. These selections are done during
initialization. As outlines above it is important to know these destinations already before initializing MARCOS 
and provide credentials using MagPys addcred method. No further configurations are necessary.

#### 5.2.1 archive

see [section 6.10](#610-filter)

#### 5.2.2 monitoring

see [section 6.12](#612-monitor)

#### 5.2.3 database management

see [section 6.7](#67-db_truncate) and [section 6.14](#614-optimizetables) 

#### 5.2.4 backup

see [section 6.4](#64-backup)

#### 5.2.5 optional filter

see [section 6.10](#610-filter)

#### 5.2.6 optional threshold

see [section 6.21](#621-threshold)

### 5.3 Running a collection job

After initialization you will find a bash job with the selected name (i.e. myjon) within your .martas directory.  You 
can start this job manually as follows.:

        $ bash collect-MYJOB1.sh start 

The following options are now available:

        $ bash collect-MYJOB1.sh start 
        $ bash collect-MYJOB1.sh stop 
        $ bash collect-MYJOB1.sh restart 
        $ bash collect-MYJOB1.sh status
        $ bash collect-MYJOB1.sh update #(important for first time usage with database - see below)

Please note: if database output is selected then by default only the data table will be written. If you want to 
create/update DATAINFO and SENSOR information, which usually is the case when running the sensor collection job for the
first time then run the collector with the "update" option, at least for a few seconds/minutes.

        $ bash collect-MYJOB1.sh update 

### 5.4 Data destinations

#### 5.4.1 Saving incoming data as files

Select destination "file" during initialization. You will also have to provide a file path then. Within this file path
a directory named with the SensorID will be created and within this directory daily binary files will be created 
again with SensorId and date as file name. The binary files have a single, ASCII readable header line describing its 
packing formats. These binary files can be read with MagPy and transformed into any MagPy supported format.

#### 5.4.2 Streaming to a database

Checkout the MagPy instructions to setup and initialize a MagPy data base
(see [section 9](https://github.com/geomagpy/magpy/tree/develop?tab=readme-ov-file#9-sql-databases)). 
This is usually done within minutes and then can be readily used for MARCOS data collections or MARTAS dissemination. 
When initializing MARCOS and selecting destination "db" you will need to provide a credential shortcut for the 
database. You can create such credentials using addcred. Use addcred -h for all options.

      $ addcred -d db -c mydb -u user -p secret -h localhost

Please use the "update" option when running a job with a new sensor for the first time to create default inputs into the
database (and not only the data table).

#### 5.4.3 Streaming to a web interface

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


#### 5.4.4 Writing to stdout

When selecting destination "stdout" the ASCII output will be written to the destination defined by logging. This can 
either be sys.stdout or the given log file. 

#### 5.4.5 Selecting diff as destination

Calculates real-time differences between sensors attached to the same MARTAS. This is useful if you want to 
visualize gradients directly.



### 5.5 The MARCOS viewer

Since MARTAS version 2.0 a MARCOS viewer is included. The viewer will create a local webpage giving you some information
about the MARCOS collection system. Please note that this viewer is specifically developed for a datbase based collection
system. You can start and open the MARCOS viewer as follows: 

        (martas)$ cd ~/.martas
        (martas)$ bash marcos_view

Open webpage http://127.0.0.1:8050 will give you something like:

![5.5.1](./martas/doc/marcos_viewer.png "The MARCOS viewer")
Figure 5.5.1: The MARCOS viewer provides a quick overview about collection jobs (top), live data (center right), 
database, archive and monitoring state plus storage consumption (center left), as well as scheduled jobs (bottom left) and
sensors, data records in the database (table right). 


## 6. Applications

### 6.1 Overview of applications

MARTAS comes along with a number of application scripts to support data acquisition, collection of data, access of 
remote data sources and organizations tools for databases. All these scripts can be found within the directory 
MARTAS/apps. Below you will find a comprehensive list of these scripts and their purpose. In the following you will 
find subsections with detailed instructions and example applications for all of these programs.


| Script           | Purpose                                              | Config        | Version | Section |
|------------------|------------------------------------------------------|---------------|---------|---------|
| archive.py       | Read database tables and create archive files        | archive.cfg   | 2.0.0*  | 6.2     |
| ardcomm.py       | Communicating with arduino microcontroller           |               | 1.0.0   | 6.3     |
| backup.py        | Backup configuration                                 |               | 2.0.0   | 6.4     |
| basevalue.py     | Analyse mag. DI data and create adopted baselines    | basevalue.cfg | 2.0.0   | 6.5     |
| checkdatainfo.py | List/ad data tables not existing in DATAINFO/SENS    |               | 2.0.0*  | 6.6     |
| db_truncate.py   | Delete data from all data tables                     | truncate.cfg  | 2.0.0*  | 6.7     |
| file_download.py | Download files, store them and add to archives       | collect.cfg   | 2.0.0*  | 6.8     |
| file_upload.py   | Upload files                                         | upload.json   | 2.0.0*  | 6.9     |
| filter.py        | filter data                                          | filter.cfg    | 2.0.0   | 6.10    |
| gamma.py         | DIGIBASE gamma radiation acquisition and analysis    | gamma.cfg     |         | 6.11    |
| monitor.py       | Monitoring space, data and logfiles                  | monitor.cfg   | 2.0.0*  | 6.12    |
| obsdaq.py        | Communicate with ObsDAQ ADC                          | obsdaq.cfg    | 2.0.0*  | 6.13    |
| optimzetables.py | Optimize table disk usages (requires ROOT)           |               | 2.0.0*  | 6,14    |
| palmacq.py       | Communicate with PalmAcq datalogger                  | obsdaq.cfg    | 2.0.0*  | 6.15    |
| serialinit.py    | Sensor initialization uses this method               |               | 2.0.0*  | 6.16    |
| speedtest.py     | Test bandwidth of the internet connection            |               | 2.0.0*  | 6.17    |
| statemachine.py  | Currently under development - will replace threshold |               | 1.0.0   | 6.18    |
| testnote.py      | Send a quick message by mail or telegram             |               | 2.0.0*  | 6.19    |
| testserial.py    | test script for serial comm - development tool       |               | 1.0.0   | 6.20    |
| threshold.py     | Tests values and send reports                        | threshold.cfg | 2.0.0   | 6.21    |

Version 2.0.0* means it still needs to be tested

### 6.2 archive

Archive.py gets data from a databank and stores it to any accessible repository (e.g. disk). Old database entries 
exceeding a defined age can be deleted in dependency of data resolution. Archive files can be stored in a user defined 
format. The databank size is automatically restricted in dependency of the sampling rate of the input data. A 
cleanratio of 12  will only keep the last 12 days of second data, the last 720 days of minute data and approximately 
118 years of hourly data are kept. Settings are given in a configuration file.
> [!IMPORTANT]  
> data bank entries are solely identified from DATAINFO table. Make sure that your data tables are contained 
there.

> [!IMPORTANT]  
> take care about depth - needs to be large enough to find data. Any older data set (i.e. you uploaded data 
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

### 6.4 backup

The backup routine will be scheduled automatically within the martas_init routine. *backup* creates a 
backup of all configuration files and settings. These backups can be used to recover a MARTAS/MARCOS system quickly.
Recovery is widely independent of hardware and software versions. To recover a broken MARTAS system you would perform
the following steps:

1) Perform all installations steps of section 2
2) Then run: python ...app/backup.py -r /path/to/backup_mymachine_DATE.zip

Thats it... You can also use this routine to clone existing MARTAS installations to new machines.

Backups are created by default on a weekly basis and you might want to store them on a different storage device. 
Eventually use file_upload for this purpose.


### 6.5 basevalue

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

### 6.6 checkdatainfo

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


### 6.7 db_truncate

db_truncate.py truncates contents of timesseries in a MagPy database. Whereas "archive" also allows for truncating 
the database (based on DATAINO) "db\_truncate" removes contents from all tables of xxx\_xxx\_xxxx\_xxxx structure.
(independent of DATAINFO contents).
The databank size is automatically restricted in dependency of the sampling rate of the input data. A cleanratio of 12
will only keep the last 12 days of second data, the last 720 days of minute data and approximately 118 years of hourly 
data are kept. Settings are given in a configuration file.

Application:

        python3 db_truncate.py -c archive.cfg



### 6.8 file_download

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

      
### 6.9 file_upload

Upload data to a destination using various different protocols supported are FTP, SFTP, RSYNC, SCP. Jobs are listed in 
a json structure and read by the upload process. You can have multiple jobs. Each job refers to a local path. Each job
can also have multiple destinations.

Examples:
1. FTP Upload from a directory using files not older than 2 days
```
{"graphmag" : {"path":"/srv/products/graphs/magnetism/","destinations": {"conradpage": { "type":"ftp", "path" : "images/graphs/magnetism/"} },"log":"/home/leon/Tmp/Upload/testupload.log", "extensions" : ["png"], "namefractions" : ["aut"], "starttime" : 2, "endtime" : "utcnow"}}
```
2. FTP Upload a single file
```
{"graphmag" : {"path":"/home/leon/Tmp/Upload/graph/aut.png","destinations": {"conradpage": { "type":"ftp", "path" : "images/graphs/magnetism/"} },"log":"/home/leon/Tmp/Upload/testupload.log"}}
```
3. FTP Upload all files with extensions
```
{"mgraphsmag" : {"path":"/home/leon/Tmp/Upload/graph/","destinations": {"conradpage": { "type":"ftp", "path" : "images/graphs/magnetism/"} },"log":"/home/leon/Tmp/Upload/testupload.log", "extensions" : ["png"]} }
```
4. Test environment
```
{"TEST" : {"path":"../","destinations": {"homepage": { "type":"test", "path" : "my/remote/path/"} },"log":"/var/log/magpy/testupload.log", "extensions" : ["png"], "starttime" : 2, "endtime" : "utcnow"} }
```
5. RSYNC upload
```
{"ganymed" : {"path":"/home/leon/Tmp/Upload/graph/","destinations": {"ganymed": { "type":"rsync", "path" : "/home/cobs/Downloads/"} },"log":"/home/leon/Tmp/Upload/testupload.log"} }
```
6. JOB on BROKER
```
{"magnetsim" : {"path":"/home/cobs/SPACE/graphs/","destinations": {"conradpage": { "type":"ftp", "path" : "images/graphs/magnetism/"} },"log":"/home/cobs/Tmp/testupload.log", "extensions" : ["png"], "namefractions" : ["magvar","gic_prediction","solarwind"], "starttime" : 20, "endtime" : "utcnow"}, "supergrad" : {"path":"/home/cobs/SPACE/graphs/","destinations": {"conradpage": { "type":"ftp", "path" : "images/graphs/magnetism/supergrad"} },"log":"/home/cobs/Tmp/testupload.log", "extensions" : ["png"], "namefractions" : ["supergrad"], "starttime" : 20, "endtime" : "utcnow"},"meteo" : {"path":"/home/cobs/SPACE/graphs/","destinations": {"conradpage": { "type":"ftp", "path" : "images/graphs/meteorology/"} },"log":"/home/cobs/Tmp/testupload.log", "extensions" : ["png"], "namefractions" : ["Meteo"], "starttime" : 20, "endtime" : "utcnow"}, "radon" : {"path":"/home/cobs/SPACE/graphs/","destinations": {"conradpage": { "type":"ftp", "path" : "images/graphs/radon/"} },"log":"/home/cobs/Tmp/testupload.log", "extensions" : ["png"], "namefractions" : ["radon"], "starttime" : 20, "endtime" : "utcnow"}, "title" : {"path":"/home/cobs/SPACE/graphs/","destinations": {"conradpage": { "type":"ftp", "path" : "images/slideshow/"} },"log":"/home/cobs/Tmp/testupload.log", "extensions" : ["png"], "namefractions" : ["title"]}, "gic" : {"path":"/home/cobs/SPACE/graphs/","destinations": {"conradpage": { "type":"ftp", "path" : "images/graphs/spaceweather/gic/"} },"log":"/home/cobs/Tmp/testupload.log", "extensions" : ["png","gif"], "namefractions" : ["24hours"]}, "seismo" : {"path":"/home/cobs/SPACE/graphs/","destinations": {"conradpage": { "type":"ftp", "path" : "images/graphs/seismology/"} },"log":"/home/cobs/Tmp/testupload.log", "extensions" : ["png"], "namefractions" : ["quake"]} }
```

Application:

   python3 file_uploads.py -j /my/path/uploads.json -m /tmp/sendmemory.json

Problem:
 - upload is not performed and stops already at first input. The log file contains "DEALING with ...", "file upload app finished", "SUCCESS"
Solution:
 - this error is typically related to an empty memory file


### 6.10 filter

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

        python filter.py -c ~/myconfig.cfg -j archive -e 2024-11-22

The output will be stored within the defined destination. Please note: if a database is your destination then DATAINFO
is updated. Data sets are stored within the data table ending with the provided revision, default 
"0002". Other general options are -l to define a loggernamse, which is useful if you have several filter jobs running on one
machine. The option -x will enable sending of logging information to the defined notification system. By default 
this is switched of because database contents are usually monitored, which also would report failures with 
specific data sets. 

The filter method should be applied in an overlapping way, as the beginning and end of the filtered sequence are
removed in dependency of the filter width. 

 
### 6.11 gamma

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


### 6.12 monitor

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

### 6.13 obsdaq and palmacq

Richard, please...


### 6.14 optimizetables

Optimizing tables and free space, the unblocking version. Please note, executing this job requires root privileges

REQUIREMENTS:
 - magpy
 - sudo apt install percona-toolkit
 - main user (user/cobs) needs to be able to use sudo without passwd (add to /etc/sudoers)

### 6.16 serialinit

Serialinit is used by all initialization jobs. See init folder...  


### 6.17 speedtest

Perform a speedtest based on speedtest-cli (https://www.speedtest.net/de/apps/cli)

        sudo apt install speedtest-cli

Application:
        python3 speedtest.py -n speed_starlink01_0001

If you want to run it periodically then add to crontab:

        */5  *  *  *  *  /usr/bin/python3 /path/to/speedtest.py -c /path/to/conf.cfg -n speed_starlink01_0001  > /dev/NULL 2&>1

### 6.18 statemachine

See threshold. Statemaschine is currently developed and may replace threshold in a future version.


### 6.19 testnote

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

> [!IMPORTANT]  
> A message is only created if contents are changing. So typically you have to call testnote twice. First, send a message like "Wold", then send "Hello World". This technique is used to report changing states only.

### 6.20 testserial

Simple test code for serial communication. Not for any productive purpose.

### 6.21 threshold

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

> [!IMPORTANT]  
> statusmessage should not contain semicolons, colons and commas; generally avoid special characters


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


## 7. Notifications and advanced monitoring

### 7.1 Setting up e-mail notifications


In order to setup e-mail notifications two steps need to be performed. Firstly, ideally done before running 
martas_init, you should add the credentials for the outgoing mail server using MagPys *addcred* method. For this 
purpose you will need the smtp mailserver details and its port. Supported by MARTAS are the often used ports 25, 465 
and 587.

        addcred -t mail -c webmail -u info@mailservice.at -p secret -s smtp.mailservice.at -l 25

Then you will need to update the mail.cfg configuration file.

        nano ~/.martas/conf/mail.cfg

The mail credential reference has already been updated during configuration. You might want to update the mail 
receivers however. 

Testing your configuration is possible with the application [testnote.py](#619-testnote).

        python ~/.martas/app/testnote.py -n email -m "Hello" -c ~/.martas/conf/mail.cfg -l TestMessage -p /home/user/test.log

Please note: calling testnote the first time will create the log file but don't send anything. From then on, a message
will be send whenever you change the message content.

        python ~/.martas/app/testnote.py -n email -m "Hello World" -c ~/.martas/conf/mail.cfg -l TestMessage -p /home/user/test.log


### 7.2 Setting up Telegram notifications

Notification send with the [Telegram] messenger are supported by MARTAS. For this purpose you will need to setup a 
Telegram BOT and link it to a private message channel, then add the BOTs token and a chat_id into the telegram.cfg 
configuration file. 

Step-by-step instructions:

1) Create a bot: Use BotFather to create a new bot and obtain its token. 

2) Add the bot to your channel: Add your newly created bot as an administrator to the Telegram channel or group. 

3) Send a message: Send a message to the channel from any user. 

4) Get the chat ID:
Open the getUpdates URL in your browser, replacing <YOUR_BOT_TOKEN> with your bot's token: https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates. 

The JSON response will contain an array of updates. Find the update related to your message.
Within that update, locate the chat object. The id field within the chat object is your channel's chat ID. 
Note the chat ID: Remember that for channel chat IDs, you'll often see a negative number, often starting with -100. For
example, the chat ID might look like -1001234567890. 

5) Insert token and chat_id into the telegram.cfg file.


Then you can use [testnote.py](#619-testnote) for testing whether its working (you must run this command two times with 
a different message).

        python ~/.martas/app/testnote.py -n email -m "Hello" -c ~/.martas/conf/mail.cfg -l TestMessage -p /home/user/test.log
        python ~/.martas/app/testnote.py -n email -m "Hello World" -c ~/.martas/conf/mail.cfg -l TestMessage -p /home/user/test.log


### 7.3 Permanent real time visualization

The [martas_viewer](#46-the-martas-viewer) is a nice tool to get a quick picture of data streams. It is however not 
build for permanent realtime visualization. For memory efficient,  long term "real-time" 
graphs, a couple of additional tools is available. These tools require the setup of a MARCOS machine and websocket
communication.

| Content                 | Description                                                      |
| -------------------------|------------------------------------------------------------------|
|  **web**                 | Webinterface as used by the collector with destination websocket |
|  web/index.html          | local main page                                                  |
|  web/plotws.js           | arranging plots of real time diagrams on html page               |
|  web/smoothie.js         | plotting library/program (http://smoothiecharts.org/)            |
|  web/smoothiesettings.js | define settings for real time plots                              |


### 7.4 Monitoring MARTAS and MARCOS

#### 7.4.1. monitor.py

After setup of the communication/notification scheme you can refer to [section 6.x](#612-monitor) for a MARTAS 
monitoring setup. 

### 7.4.2 Support for NAGIOS/ICINGA

Beside the internal monitoring routines you might want to include your MARTAS/MARCOS environment into a high end 
monitoring network. Please checkout Icinga and/or NAGIOS for this purpose. MARTAS can be easily included into such
networks and instructions are available upon request.

### 7.5 Two-way communication with MARTAS

MARTAS comes with a small communication routine, which allows interaction with the MARTAS server. In principle, you can
chat with MARTAS and certain keywords will trigger reports, health stats, data requests, and many more. Communication
routines are available for the [Telegram] messenger. In order to use these routines you need to setup a Telegram bot,
referring to your MARTAS.

#### 7.5.1 interactive communication with TelegramBot

To setup 2-way [Telegram] communication use the following steps:

  a) Use [Telegram Botfather] to create a new BOT

        /newbot

        /setuserpic

  b) Install Telegram support for MARTAS (TODO: needs an update)

        $ cd MARATS/install
        $ sudo bash install.telegram.sh

      The installer will eventually add the following apckages: telepot, psutil and
      platform. For webcam support you shoudl install fswebcam.

        $ sudo apt-get install fswebcam  # optional - transferring webcam pictures


  c) Update /etc/martas/telegrambot.cfg (TODO: needs an update)

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


## 8. Additional tools

### 8.1 analysis.py for continuous flagging, adjusted/quasidefinitive data products and status information 

#### 8.1.1 MartasAnalysis

For continuous flagging of data in a MARCOS environment you can use the MartasAnalysis class as follows. Flagging 
configurations need to be supplied to the method in form of json data. An example of such flagging configuration 
information is given here

```
flagdict = {'TEST': {"coverage": 86400,
                     "keys": ['x','y','z'],
                     "mode": ['outlier'],  # outlier, range, ultra, ai,
                     "samplingrate": 1,
                     "min": -59000,
                     "max": 50000,
                     "addflag": True,
                     "threshold": 4,
                     "window": 60,
                     "markall": True,
                     },
                     ...
            }
```

This dictionary provides details on the Sensor or SensorGroup and the applied flagging method. The "TEST" refers to 
the SensorID of datasets to be flagged. All SensorIDs containing TEST in their name will be flagged with the given
parameters (i.e. TEST_1234_0001, TEST001_XXX_0002, AWSOME_TEST_0001). The last 86400 datapoint will be read and 
outlier flagging (despiking) be performed using threshold and window.

> [!IMPORTANT]  
> the methods of the analysis module are designed to work with a MagPy/MARTAS database. Using the methods on
non-DB architectures will need some work to adjust the methods. Methods and Classes of the analysis module are typically
scheduled using cron.

Typical application for continuous flagging looks as follows. The periodically method will read data, remove already 
existing flags and then apply the flagging method on remaining data.

        from martas.core import methods as mm
        from martas.core.analysis import MartasAnalysis
        config = mm.get_conf('Configuration file like basevalue.cfg')
        config = mm.check_conf()
        flagdict = mm.get_json('Flagdict file like shown above')
        mf = MartasAnalysis(config=config, flagdict=flagdict)
        fl = mf.periodically(debug=False)
        suc = mf.update_flags_db(fl, debug=True)

Other flagging related methods are upload, archive, cleanup.

In order to obtain adjusted or quasidefinitive data, the MartasAnalysis class contains methods specifically designed for 
geomagnetic data analysis. Adjusted data can be obtained hereby.


        from martas.core import methods as mm
        from martas.core.analysis import MartasAnalysis
        config = mm.get_conf('Configuration file like basevalue.cfg')
        config = mm.check_conf()
        mf = MartasAnalysis(config=config)
        primary_vario = mf.get_primary(variometer DataID list)
        primary_scalar = mf.get_primary(scalar DataID list)
        merged = mf.magnetism_data_products('adjusted', primary_vario, primary_scalar)
        results = merged.get('merge')
        for samplingrate in results:
            export_data res.get(samplingrate)

If you have multiple variometers on your site the get_primary method investigates supplied variometer data sets and
selects the first one of the list which contains valid data. The method *magnetim_data_products* will then read data,
eventually remove flags, apply offsets as defined in the database, perform a baseline correction and construct merged 
data sets. If one-second data is supplied it will also create a filtered one-minute record. 


#### 8.1.2 MartasStatus

MartasStatus is used to extract specific values from the data sets. This method can be used to supply status information
and current values to webpages and services. The kind of status information is defined in a dictionary which might be
stored as json file on your system. 

```
statusdict = {"Average Temperature of TEST001": {
                                "source": "TEST001_1234_0001_0001",
                                "key": "x",
                                "type": "temperature",
                                "group": "tunnel condition",
                                "field": "environment",
                                "location": "gmo",
                                "pierid": "",
                                "range": 30,
                                "mode": "mean",
                                "value_unit": "°C",
                                "warning_high": 10,
                                "critical_high": 20
                                },
                     ...
            }
```

THe keys of each status element refer to the following inputs:

| key           | description                          | default                  | example     |
|---------------|--------------------------------------|--------------------------|-------------|
| source        | DataID                               | -                        | -           |
| key           | column of DataID                     | x                        | t1          |
| field         | physical property contained in key   | -                        | temperature |
| group         | primary purpose of Instrument/Sensor | SensorGroup              | magnetism   |
| type          | specific primary sensor type         | SensorType               | fluxgate    |
| pierid        | reference to pier                    | PierID                   | A2          |
| station       | reference to StationID               | StationID                | WIC         |
| longitude     |                                      | DataAcquisitionLongitude | -           |
| latitude      |                                      | DataAcquisitionLatitude  | -           |
| altitude      |                                      | DataElevation            | -           |
| range         | timerange in minutes                 | 30                       | 30          |
| mode          | mean,median,max,min,uncert           | mean                     | fluxgate    |
| value_unit    | unit of key                          | unit-col-KEY             | -           |
| warning_low   | lower warning level                  | 0                        | -5          |
| warning_high  | upper warning level                  | 0                        | 10          |
| critical_low  | lower critical level                 | 0                        | -20         |
| critical_high | upper critical level                 | 0                        | 20          |


The key values of each status element contained in the status dictionary need to be unique and are ideally human 
readable. The subdictionary defines parameters of the data set to be extracted. Typically recent data covering the 
last "range" minutes are extracted and the value as defined by mode (mean, median, max, min, uncert) is obtained. If 
no data is found the "active" value of the return dictionary is set to 0. Most properties are obtained from existing
tables in the database. You can override database contents by providing the corresponding inputs within the status
elements. Please note: the physical property "field" is not contained in the database and can only be supplied here.

As all other methods, the MartasStatus class methods are designed for data base usage. You can extend your MagPy data
base with a status information tables using the following command:

        from martas.core import methods as mm
        from martas.core.analysis import MartasStatus
        config = mm.get_conf('Configuration file like basevalue.cfg')
        config = mm.check_conf()
        statusdict = mm.get_json('Statusdict file like shown above')
        ms = MartasStatus(config=config, statusdict=statusdict,tablename='COBSSTATUS')

        initsql = ms.statustableinit(debug=True)

Status messages in this table can then be updated by scheduling a job like the following

        ms = MartasStatus(config=config, statusdict=statusdict,tablename='COBSSTATUS')
        sqllist = []
        for elem in ms.statusdict:
            statuselem = ms.statusdict.get(elem)
            res = ms.read_data(statuselem=statuselem,debug=True)
            warnmsg = ms.check_highs(res.get('value'), statuselem=statuselem)
            newsql = ms.create_sql(elem, res, statuselem)
            sqllist.extend(newsql)


### 8.2 definitive.py for geomagnetic definitive data production

The definitive module contains a number of methods for geomagnetic definitive data analysis. It is currently part of 
MARTAS2.0 and uses the same configuration data as basevalue. Please note that this module was specifically developed 
for the Conrad Observatory and some of the methods will only be useful for very similar procedures. The module contains
methods for analyzing variometer and scalar data. The methods are designed for an iterative analysis of one-second data,
allowing for optimization of baseline adoption. Filtered one-minute products are generated.
Following the data treatment philosophy of MagPy data from different sensors is treated separately,

Please note: for a general application some of the methods will need to be updated. I included this module anyway, as 
it might turn out to be useful for others, although it can not readily be applied in a general form.

#### 8.2.1 variocorr

Using variocorr one can analyse the variation data of several instruments, apply flagging information, eventually apply 
transformations, rotations and offsets, and perform baseline adoption. Three different application levels are supported 
for an iterative analysis: firstrun, secondrun and thirdrun. Firstrun will use a simple average baseline, whereas 
secondrun and thirdrun support complex baseline fits. The application of bias fields (also called compensation fields), 
rotation angles (Euler rotation) and flagging information can be varied between runs. By default the method requires 
a full year of one second data of one or multiple instruments and baseline data files for each sensor. Data will be 
treated in monthly chunks. The method can also be used for single day analysis by providing the date in 
config['testdate']. The method returns monthly MagPyCDF data files containing raw data, flagging info and 
baseline function, i.e. data files which contain basically every information to review IM variation and produce IM
definitve data.
Variocorr will always return rotation angles between measured field components and a magnetic coordinate system as 
obtained by DI data. In case of an optimal DHZ oriented system these angles are zero. 

#### 8.2.2 variocomb

Variocomb is used to create a merged variation data set from multiple variometer records. The order of instruments in 
the configuration files is used to define primary, secondary, ... systems. Baseline corrected data from variocorr is 
then used to construct a joint record with gaps filled in minute resolution. Variocomb can also read scalar products 
from 8.1.3 and create definitive minute products as requested by INTERMAGNET/IAGA. Definitve second products have to 
be constructed from outputs of variocomb and scalarcomb in a separate step.

#### 8.2.3 scalarcorr and scalarcomb

For scalar data the two methods to the same job as similar methods for variometers, without baseline adoption. Please
note, complex F baseline require a different approach currently not supported by these methods. Currently only constant
offsets are supported. Joint data sets are supported for both minute and second data.

#### 8.2.4 create_rotation

Take the return of variocorr and add rotation data into the database so that average yearly rotations can be considered
for analysis (leading to baseline jumps every year). 

#### 8.2.5 pier_diff

Used to determine F differences of multiple piers provided that a mobile reference sensor is used regularly to measure on 
all these piers. This is very Conrad Observatory specific and you might want to contact the Cobs Team for details.  

#### 8.2.6 dissemination: definitive_min and definitive_sec

Creates geomagnetic dissemination data by producing the corresponding data formats and contents from the MagPy files
obtained by above methods. Created are IAGA, IAF and ImagCDF (in minute and second resolution).

#### 8.2.7 dissemination: activity_analysis

Performs an analysis of geomagnetic activity

#### 8.2.8 dissemination: blv

Creates INTERMAGNET baseline format files and includes all required information into these files.


### 8.3 Useful commands during runtime

acquisition process still running?  

              bash /home/USER/.martas/runmartas status

check log file contents

              tail -30 /home/USER/.martas/log/martas.log

Are buffer files written

              ls -al /home/USER/MARTAS/mqtt/YOURSENSOR/

Can I subscribe to the MQTT data stream (MQTTBROKER might be localhost, etc) 

              mosquitto_sub -h MQTTBROKER -t TOPIC/#

Can I publish data to a broker?

              mosquitto_pub -h MQTTBROKER -t TOPIC -m "Hello"

 collector process running?  

          bash /home/USER/.martas/collect-JOBNAME status

log file contents

          tail -30 /home/USER/.martas/log/collect-JOBNAME.log

data files/ database  written

          DATABASE:
          mysql -u user -p mydb
          select * from DATATABLE order by time desc limit 10;

          FILE:
          ls -al /my/file/destination/


## 9. Instruments and library 

### 9.1 Sensor communication libraries

Principally all libraries should work in version 2.0.0 although only tested libraries contain the new version number.

| Instrument          | versions | Inst-type   | Library                  | mode     | init           | requires         |
|---------------------|----------|-------------|--------------------------|----------|----------------|------------------|
| Arduino             |          | multiple    | activearduinoprotocol.py | active   |                |                  |
| AD7714              |          | multiple    | ad7714protocol.py        | active   |                |                  |
| Arduino             |          | multiple    | arduinoprotocol.py       | passive  |                |                  |
| BM35-pressure       |          | pressure    | bm35protocol.py          | passive  | bm35init.sh    |                  |
| BME280              |          | pressure    | bme280i2cprotocol.py     | passive  |                | adafruit_bme280  |
| CR1000/800          |          | multiple    | cr1000jcprotocol.py      | active   |                | pycampbellcr1000 |
| Cesium G823         |          | opt.pumped  | csprotocol.py            | passive  |                |                  |
| Thies LNM           |          | laserdisdro | disdroprotocol.py        | active   |                |                  |
| DSP Ultrasonic wind |          | wind        | dspprotocol.py           | active   |                |                  |
| ENV05               | 2.0.0    | temperature | envprotocol.py           | passive  |                |                  |
| 4PL Lippmann        |          | geoelec     | fourplprotocol.py        | active   |                |                  |
| GIC                 |          | special     | gicprotocol.py           | active   |                |                  |
| GP20S3              |          | opt.pumped  | gp20s3protocol.py        | passive  |                |                  |
| GSM19               |          | overhauser  | gsm19protocol.py         |          |                |                  |
| GSM90               |          | overhauser  | gsm90protocol.py         | passive  | gsm90v?init.sh |                  |
| DataFiles           |          | multiple    | imfileprotocol.py        | active   |                |                  |
| LEMI025             |          | fluxgate    | lemiprotocol.py          | passive  |                |                  |
| LEMI036             |          | fluxgate    | lemiprotocol.py          | passive  |                |                  |
| Tilt Lippmann       | develop  | tilt        | lmprotocol.py            | active   |                |                  |
| LORAWAN             | develop  | multiple    | lorawanprotocol.py       |          |                |                  |
| MySQL               | 2.0.0    | multiple    | mysqlprotocol.py         | active   |                |                  |
| ObsDaq              |          | multiple    | obsdaqprotocol.py        | active   | obsdaqinit.sh  |                  |
| OneWire             |          | multiple    | owprotocol.py            | passive  |                |                  |
| POS1                |          | overhauser  | pos1protocol.py          | passive  | pos1init.sh    |                  |
| Test                | 2.0.0    | special     | testprotocol.py          |          |                |                  |

The library folder further contains publishing.py defining different MQTT topic/payload formats and lorawan stuff. 

### 9.2 Sensor specific initialization files and settings

#### 9.2.1 GEM Systems Overhauzr GSM90

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

#### 9.2.2 Quantum POS1

#### 9.2.3 Meteolabs BM35 pressure

#### 9.2.4 ObsDAQ / PalmAcq

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

#### 9.2.5 LM - TLippmann tilt meter

To be added

#### 9.2.6 Dallas OW (One wire) support

a) modify owfs,conf
        $ sudo nano /etc/owfs.conf

      Modify the following parts as shown below:
        #This part must be changed on real installation
        #server: FAKE = DS18S20,DS2405

        # USB device: DS9490
        server: usb = all

b) start the owserver
        $ sudo etc/init.d/owserver start


#### 9.2.6  Communicating with an Arduino Uno Microcontroller

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

| Sketch name                |  version | mode  | job |
|----------------------------| ------ | ------ | ------- |
| sketch\_MARTAS\_ac\_ow\_sw | 1.0.0 |  active | requesting 1-wire sensor data and enabling remote switching of pin 4 (default: off) and pin 5 (default: on) |
|  sketch\_MARTAS\_pa\_ow    | 1.0.0 |  passive | recording 1-wire sensor data |


If you change the sensor configuration of the Arduino, then you need to stop martas, eventually delete the existing
arduino block (with the leading questionmark), connect the new sensor configuration and restart MARTAS.
Make sure to disconnect the Arduino, before manipulating its sensor
configuration. You can check the Arduino independently by looking at Arduino/Tools/SerialMonitor (make sure that MARTAS processes are not running).

**IMPORTANT NOTE**: for active access it is sometimes necessary to start the SerialMonitor from arduino before starting MARTAS. The reason is not clarified yet. This is important after each reboot. If not all sensors are detetcted, you can try to send the RESET command "reS" to the arduino. This will reload available sensors. Such problem might occur if you have several one wire sensors connected to the arduion and remove or replace sensors, or change their configuration.


## 10. Appendix

### 10.1. Installation issues and examples

The installation is usually straightforward as described in section 2. For some systems you might however require some
additional packages to fulfill required dependencies. Here we summarise some system specific issues and solutions, as
well as a full installation cookbook.

#### 10.1.1 Installation problems with virtualenv

Such problems might occur and have been experienced while installing scipy on beaglebone blacks. You might want to 
consider search engines to find solutions for that. Alternatively you can also switch to system python for running MARTAS.
As you still require some pip packages this method is not recommended. In order to minimize a potential negative 
influence on system stability it is recommended to install most packages based on apt.

      sudo apt install python3-numpy python3-scipy python3-matplotlib python3-twisted python3-serial python3-plotly python3-numba python3-pandas

Then install the remaining dependencies using pip.

      sudo pip install --break-system-packages martas

You likely will need to update the path variable then in the "runmartas.sh" job. Replace "acquisition" by the full path
"/usr/local/bin/acquisition" to make it available from cron.



#### 10.1.1 Step 0: Get you Debian system ready (install Ubuntu, Raspberry, Beaglebone, etc)

Please install your preferred debian like system onto your preferred hardware. MARTAS will work with every debian 
like system. Please follow the installation instructions given for the specific operating system. In the following we
will give a quick example of such preparations for a Raspberry installation using debian bullseye:

Install the operating system (i.e. debian bullseye) on a SD card using i.e. Balena Etcher. Do that on your linux 
working PC, which is NOT the single board computer. Afterwards insert the SD card into the single board computer and
boot it. Finish the initial configurations as requested during the boot process. 

Afterwards you might want to change hostname (Raspberry PI configuration or update /etc/hostname and /etc/hosts),
partitions on SD card (sudo apt install gparted), proxy configurations (/etc/environment) and in case of raspberry
enable ssh (raspberry PI configuration).

#### 10.1.2 Step 1: Install necessary packages for all MARTAS applications

Packages for MARTAS (including support for all modules including icinga/nagios monitoring):

        sudo apt update
        sudo apt upgrade
        sudo apt-get install ntp arduino owfs ssh mosquitto mosquitto-clients nagios-nrpe-server nagios-plugins fswebcam python3-virtualenv python3-wxgtk4.0 libsdl2-dev

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

#### 10.1.3 Step 2: Install MARTAS

Open a terminal and create a virtual environment:

        cd ~
        virtualenv ~/env/martas

Activate the environment

        source ~/env/martas/bin/activate

Download and install MARTAS:

        pip install martas

Create a bufferdircetory

        mkdir ~/MARTAS

Add credentials for notifications by e-mail (skip this one if not used)

        addcred -t email -c email -u USER -p PASSWD -h -p 

Run initialization

        martas_init

Check crontab (crontab -l):

        crontab -l

Thats it. MARTAS is now ready to be used. Continue with sensor definitions and tests. Alternatively you can recover 
configurations from a martas_backup (see 8.1).

Useful commands to check ports for sensor definitions are i.e.

        dmesg | grep usb


#### 10.1.4 quick steps to run a new MARTAS with a new sensor for the first time (needs to be updated)

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

       
#### 10.1.5 quick steps to setup a fully configured MARTAS with the respective sensor(s) (needs to be updated)

In this example we use a MARTAS with a GSM19 Overhauzer sensor:

A. Sensor (GSM19)

   1. Connect the sensor to power and MARTAS
   2. Switch on the sensor and start recoding (all A steps in 12.6.1)

B. MARTAS
   1. Connect MARTAS to power

Check whether everything is running. On MARTAS you should check whether the buffer file is increasing and eventually the log file.
Please note: data is written as soon as all sensor specific information is available. When attaching a micro controller (i.e. arduino)
you might need to wait about 10 times the sampling rate (i.e. 10min for 1min sampling rate) until data is written to the buffer.

#### 10.1.6 enable remote terminal access (TODO)

tmate instructions

### 10.2 Full installation guide of a MARCOS box

The following example contains a full installation of MARTAS, MARCOS with full database support, XMagPy, Nagios 
monitoring control, Webinterface, and an archive on an external harddrive.

#### 10.2.1  Installation script (needs to be updated)

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

### 10.3 Development tools

#### 10.3.1 Testing modules

Unittest are included in the following modules. app_tester will perform a unittest on applications in the app folder:

       python core/app_tester.py
       python core/methods.py
       python core/definitive.py

#### 10.3.2 Testing acquisition

The main program contains a testing option -T which will create an artificial/random data set published on topic "tst":

       python acquisition.py -m ~/.martas/conf/martas.cfg -T

#### 10.3.3 Testing MARTAS and MARCOS

Run a test acquisition as shown in 9.5.2 to simulate a sensor

       python acquisition.py -m ~/.martas/conf/martas.cfg -T

Run a MARCOS collector to obtain this test data and store it in i.e. a file or db. Configure collect-tst.cfg to access TST

       python collector.py -m ~/.martas/conf/collect-tst.cfg

Run an additional acquisition job without -T using either the imfile library (file) or mysql library (db) to test these
two libraries. Please configure sensors.cfg accordingly and use a stationID different to TST in martas.cfg. 

       nano ~/.martas/conf/sensors.cfg
       python acquisition.py -m ~/.martas/conf/martas.cfg


### 10.4 Issues and TODO

in some cases, if the recording process terminates, the daily buffer file might be corrupt. In that case you need to 
delete the daily file and restart the recoding process. The next daily file will be OK in any case.

- add trigger mode for GSM90 (sending f)
- update scp_log to use protected creds

#### Problem: pip install behind a proxy

       export https_proxy=http://YOUR-PROXY-IP:PORT
       pip install martas

#### Problem pip install - packages do not match the hashes

       pip install --no-cache-dir martas




### 10.5 Example configurations - Conrad Observatory

#### 10.5.1 continuous, automatic DI analysis 

The automatic DI analysis makes use of the basevalue application.
```
#!/bin/sh

### New analysis script
### ###############################
##  Script to download and analyze di data
##  The following sources are accessed:
##  - mounted AUTODIF folder
##  - the /DI/all folder
##    -> file_download -c collect-di-from-broker obtains conrad-observatory homepage: zamg/phocadowload/
##    -> file_download -c collect-di-from-gonggong obtains data from Irene
##    => data ending with WIC.txt is automatically moved into the analysis folder
##       remaining data is kept within "all"
##  Data is downloaded to analysis folder in /srv/archive/WIC/DI
##  Reults are stored in BLVcomp files (not DB) (-f option, no -n option)
##  analyzed data is not moved (no -r option)


# copy files from les from autodif to analyze if they are not yet listed in raw
PYTHON="/usr/bin/python3"
DATE1=$(date +%Y%m%d --date='1 day ago')
DATE2=$(date +%Y%m%d --date='2 days ago')

AUTODIF1="/media/autodif/data/$DATE1.txt"
AUTODIF2="/media/autodif/data/$DATE2.txt"
ARCHIVE1="/srv/archive/WIC/DI/analyze/$DATE1"
ARCHIVE2="/srv/archive/WIC/DI/analyze/$DATE2"
PIER="A16"
STATION="WIC.txt"

ALLDI="/srv/archive/WIC/DI/all/"
ANALYZEDI="/srv/archive/WIC/DI/analyze/"

# activate if AutoDIf data is going to be analyzed
{
  cp $AUTODIF1 ${ARCHIVE1}_${PIER}_${STATION}
  cp $AUTODIF2 ${ARCHIVE2}_${PIER}_${STATION}
} || {
  echo "Could not access AUTODIF"
}

# activate to use new file transmission from broker
{
  find $ALLDI -name "*WIC.txt" -exec mv '{}' $ANALYZEDI \;
} || {
  echo "Could not access ALLDI data from BROKER"
}


echo " ##################################################################"
echo " Running without compensation and rotation - for merritt coil"
echo " ##################################################################"
# ANALYSE WITHOUT ROTATION and Compensation, only ADD BLV TO DB - ONLY A2
$PYTHON /home/cobs/SCRIPTS/basevalue.py -c /home/cobs/CONF/auto-collect/basevalue_blv_merritt.cfg

echo " ##################################################################"
echo " Running without rotation"
echo " ##################################################################"
# ANALYSE WITHOUT ROTATION and ADD TO DB - ONLY A2,A16
$PYTHON /home/cobs/SCRIPTS/basevalue.py -c /home/cobs/CONF/auto-collect/basevalue_blv.cfg

echo " ##################################################################"
echo " Primary piers"
echo " ##################################################################"
# ANALYSE DI data with ROTATION, ADD TO DB, ONLY A2 and move to archive
$PYTHON /home/cobs/SCRIPTS/basevalue.py -c /home/cobs/CONF/auto-collect/basevalue_blvcomp_main.cfg -p A2

echo " ##################################################################"
echo " All other piers"
echo " ##################################################################"
# ANALYSE ALL OTHER DATA FOR ALL PIERS, DI data to DB, movetoarchive
$PYTHON /home/cobs/SCRIPTS/basevalue.py -c /home/cobs/CONF/auto-collect/basevalue_blvcomp.cfg

echo " ##################################################################"
echo " AutoDIF"
echo " ##################################################################"

#Do AUTODIF separate  and check whether data is available and analsis successful
# REASON: If incomplete AutoDIF files are provided then the job might stop
$PYTHON /home/cobs/SCRIPTS/basevalue.py -c /home/cobs/CONF/auto-collect/basevalue_blvcomp.cfg -p A16

echo " ##################################################################"
echo $DATE

# synchronize analysis folder mit remaining, faulty analysis to gonggong
rsync -ave ssh --delete /srv/archive/WIC/DI/analyze/ cobs@138.22.188.192:/home/irene/DIdata/
echo "Success"
```



### References

   [magpy-git]: <https://github.com/geomagpy/magpy>
   [Telegram]: <https://telegram.org/>
   [Telegram Botfather]:  <https://core.telegram.org/bots>
   [Arduino Microcontroller]: <http://www.arduino.cc/>
