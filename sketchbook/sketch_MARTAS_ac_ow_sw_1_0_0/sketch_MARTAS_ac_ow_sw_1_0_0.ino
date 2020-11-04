/***************************************************************************
sketch_MARTAS_active_ow_switch

DESCRIPTION
  MARTAS arduino one wire app.
  Written to be used with MARTAS
  (https://github.com/geomagpy/MARTAS)

CONNECTION
  default ON Switch to 4
  default OFF Switch to 5 
  OW to 2
  GND to ground
  VCC to 5V 

SERIAL OUTPUT
  Each MARTAS output line consists of an identifier and data/meta info.
  (D) for data, (H) for component(s) and unit(s), 
  (M) for meta like SensorID etc

COMMANDS
  commands are identified as follows
  ---------------------------
  owT::     : read temperature from one wire
  swP:1:4   : switch on pin 4
  swS::     : get current switch status
  swD::     : read switch status in MARTAS format
  reS::     : send Reset command
  deS::     : send Sensor Details
***************************************************************************/
#include <Wire.h>
#include <OneWire.h>
#include <DallasTemperature.h>

#define ONE_WIRE_BUS 2
#define ARRAYSIZE 30
String SKETCHVERSION = "1.0.0";

// Name and serial number of Arduino (dmesg | grep usb, lsusb)
String ANAME="UNOR3";
String ASERIALNUMBER="75439313637351A08180";

// Definitions for switches
int swst = LOW;
int sigout = 4;
int signalOut4 = 4; //the pin we connect the LED - off state (signal LOW -> LED off)
int stateSW4 = LOW;
int signalOut5 = 5; //the pin we connect the relais - on state (signal LOW -> relais on)
int stateSW5 = LOW;
long time = 0;
long debounce = 200;
#define ARRAYSIZE 10
String commands[ARRAYSIZE] = { "owT", "swP", "swS", "swD", "reS", "owD"};
/*
Commands:
     owT   :  get temperatures of all connected one wire sensors
     swP   :  switch Pin Y to value X (swP:1:4)
     swS   :  show status of all switch Pins
     swD   :  get switch status data as MARTAS readable data
     owD   :  Get info on all 1-wire sensors
     reS   :  send software reset to Arduino
*/

// Definitions for sensors
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);
String owSensors[ARRAYSIZE] = { "MySensor" };
int numberOfSensors;
int sensorNumber = 3;
float getowseconds = 5.; // sget new one wire data every xx seconds

uint16_t rawData;
float temperature;
float temperatureOW;

// add sensor and current T
String swsensor = "mySens";
float currentT;
float switchT;

// DS18S20 Temperature chip i/o
boolean inarray(String array[ARRAYSIZE], String element);
boolean inarray(String array[ARRAYSIZE], String element) {
 for (int i = 0; i < ARRAYSIZE; i++) {
      if (array[i] == element) {
          return true;
      }
    }
  return false;
 }
 

void setup(void) {
  // start serial port
  Serial.begin(9600);
  // Initialize output pin
  pinMode(signalOut4, OUTPUT);
  pinMode(signalOut5, OUTPUT);
  // OW part
  //Serial.println("Starting OW in 5 secs...");
  //Serial.println("<MARTASEND>");
  delay(5000);  //important on linux as serial port can lock up otherwise
  numberOfSensors = discoverOneWireDevices(0);
  Serial.println();
}

void displaySensorDetails(int n)
{
  Serial.println("------------------------------------");
  Serial.println("Looking for 1-Wire devices...");
  Serial.println("Found \'1-Wire\' device with address: ");
  for (int i = 0; i < n; i++)
  {
    Serial.print("OW:  "); Serial.println(owSensors[i]);
  }
  Serial.println("------------------------------------");
  Serial.println("");
  Serial.println("<MARTASEND>");
  delay(500);
}

int discoverOneWireDevices(int report) {
  // Based on http://www.hacktronics.com/Tutorials/arduino-1-wire-address-finder.html
  oneWire.reset();
  oneWire.reset(); // two resets for good luck
  
  byte i;
  byte present = 0;
  byte data[12];
  byte addr[8];
  int count = 0;
 
  while(oneWire.search(addr)) {
    String owid = "";
    for( i = 0; i < 8; i++) {
      if (addr[i] < 16) {
        owid = owid + '0';
        //owaddr = owaddr +'0';
      }
      owid = owid + String(addr[i], HEX);
    }
    if ( OneWire::crc8( addr, 7) != addr[7]) {
        Serial.println("CRC is not valid!");
        return 0;
    }
    owid.toUpperCase();
    owSensors[count] = owid;
    count++;
  }
  oneWire.reset_search();
  if (getowseconds < count) {
     // update sampling rate if larger then 1 second for each sensor
    getowseconds = count;
  }
  if (report == 1) {
    displaySensorDetails(count);
  }
  return count;
}

void logDataOw(int num)
{
  String dataset =  owSensors[num];
  int val = sensorNumber+num+1;
  String did = 'D'+String(val);
  if (dataset.startsWith("28"))
  {
    temperatureOW = sensors.getTempCByIndex(num);
    Serial.print(did);Serial.print(": "); Serial.println(temperatureOW);
  }
  else if (dataset.startsWith("10"))
  {
    temperatureOW = sensors.getTempCByIndex(num);
    Serial.print(did);Serial.print(": "); Serial.println(temperatureOW);
  }
  else if (dataset.startsWith("26"))
  {
    //temperatureOW = sensors.getTempCByIndex(num);
    //Serial.print(did);Serial.print(": "); Serial.println(temperatureOW);
  }
  else
  {
  }
  Serial.flush();
}

void logMetaOw(int num)
{
  String dataset =  owSensors[num];
  int val = sensorNumber+num+1;
  if (dataset.startsWith("28"))
  {
     Serial.print("H");Serial.print(val);2;Serial.println(": t1_T [degC]");
     Serial.print("M");Serial.print(val);Serial.print(": ");
     Serial.print("SensorName: "); Serial.print("DS18B20");
  }
  else if (dataset.startsWith("10"))
  {
     Serial.print("H");Serial.print(val);2;Serial.println(": t1_T [degC]");
     Serial.print("M");Serial.print(val);Serial.print(": ");
     Serial.print("SensorName: "); Serial.print("DS18S20");
  }
  else
  {
     Serial.print("H");Serial.print(val);2;Serial.println(": x_X [unknown]");
     Serial.print("M");Serial.print(val);Serial.print(": ");
     Serial.print("SensorName: "); Serial.print("UnknownSensor"); Serial.print(dataset.substring(0,1));
  }
  Serial.print(", SensorID:  ");  Serial.println(owSensors[num]);
  Serial.flush();
}

void getOWtemp() {
  // One wire part
  int numprev = numberOfSensors;
  numberOfSensors = discoverOneWireDevices(0);
  if (numberOfSensors == 0) {
    //Serial.println("Lost all sensors: assuming read error"); 
    numberOfSensors = numprev;
  }
  sensors.requestTemperatures(); // Send the command to get temperatures
  for (int i = 0; i<numberOfSensors; i++) 
  {
     logMetaOw(i);
     logDataOw(i);
     //delay(int(numberOfSensors*1000));
  }
  Serial.println("<MARTASEND>");
}

void getSensorDetails() {
  // One wire part
  Serial.println("Please wait...");
  delay(5000);
  numberOfSensors = discoverOneWireDevices(1);
}

void ArduinoReset() {
  asm volatile ("  jmp 0");
}

void interpretecommand(char* comm) {
  while (comm != 0) {
     String command(comm);
     comm = strtok(0, ":");
     String option(comm);
     comm = strtok(0, ":");
     String pin(comm);
     comm = strtok(0, ":");
     //Serial.print("Received Command: " + command);
     //Serial.print("with Option: " + option);
     //Serial.println("; PIN: " + pin);
     if (inarray(commands, command)) {
       if (command == "swP") {
         if (pin.startsWith("4")) {
          sigout = signalOut4;
          swst = stateSW4;
         } else {
           sigout = signalOut5;
           swst = stateSW5;
         }
         if (option == "0") {
           if (swst == HIGH) {
             Serial.println("Switching off pin " + pin);
             Serial.println("<MARTASEND>");
             digitalWrite(sigout, LOW);
             if (pin.startsWith("4")) { stateSW4=LOW;} else { stateSW5=LOW; };
           }
         }
         if (option == "1") {
           if (swst == LOW) {
             Serial.println("Switching on pin " + pin);
             Serial.println("<MARTASEND>");
             digitalWrite(sigout, HIGH);
             if (pin.startsWith("4")) { 
               stateSW4=HIGH;
             } else { 
               stateSW5=HIGH; 
             };
           }
         }
       }
       if (command == "swS") {
         Serial.print("Status: pin4=" + String(stateSW4));
         Serial.println("; pin5=" + String(stateSW5));
         Serial.println("<MARTASEND>");
       }
       if (command == "swD") {
         Serial.print("H");Serial.print(String(sensorNumber));Serial.println(": var4_Pin4 [None], var5_Pin5 [None]");
         Serial.print("M");Serial.print(String(sensorNumber));Serial.print(": ");
         Serial.print("SensorName: "); Serial.print(ANAME);
         Serial.print(", SensorID:  "); Serial.println(ASERIALNUMBER);
         Serial.print("D");Serial.print(sensorNumber);Serial.print(": " + String(stateSW4));
         Serial.println(", " + String(stateSW5));
         Serial.println("<MARTASEND>");
       }
       if (command == "owT") {
         Serial.println("Reading data: onewire temperatures");
         getOWtemp();
       }
       if (command == "owD") {
         Serial.println("Getting onewire sensor details (eventually repeat):");
         getSensorDetails();
       }
       if (command == "reS") {
         Serial.println("Sending reset...");
         delay(100);
         ArduinoReset();
       }
     } else {
       Serial.println("Command not recognized:" + command);
       Serial.println("<MARTASEND>");
     }
     Serial.flush();
  }
}

void handleIncoming() {
  while (Serial.available() > 0) {
    int INPUT_SIZE = 30;
    char input[INPUT_SIZE+1];
    byte size = Serial.readBytes(input, INPUT_SIZE);
    // Add the final 0 to end the C string
    input[size] = 0;
    char* comm = strtok(input, ":");
    interpretecommand(comm);
  }
}
  

void loop(void) {
  // Reading part using basic char operations
  handleIncoming();
  // time break before hanlding the next incoming message
  delay(500);
}
