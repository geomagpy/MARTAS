/***************************************************************************
sketch_MARTAS_onewire

DESCRIPTION
  MARTAS arduino one wire app.
  Written to be used with MARTAS
  (https://github.com/geomagpy/MARTAS)
  Based on the library example for the HMC5883 magnentometer/compass

CONNECTION
  OW to 2 (dont forget the resistance)
  GND to ground
  VCC to 5V 

SERIAL OUTPUT
  Each output line consists of an identifier and data/meta info.
  (D) for data, (H) for component(s) and unit(s), 
  (M) for meta like SensorID etc

  D1, H1 and M1 -> HMC5883
  
 ***************************************************************************/
#include <Wire.h>
#include <OneWire.h>
#include <DallasTemperature.h>

#define ONE_WIRE_BUS 2
#define ARRAYSIZE 30
String SKETCHVERSION = "1.0.0";

OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature sensors(&oneWire);
String owSensors[ARRAYSIZE] = { "MySensor" };
int numberOfSensors;
int sensorNumber = 3;
float getowseconds = 10.; // sget new one wire data every xx seconds

uint16_t rawData;
float temperature;
float temperatureOW;


// DS18S20 Temperature chip i/o
//OneWire ds(10);  // on pin 10

void setup(void) {
  // start serial port
  Serial.begin(9600);
  // OW part
  Serial.println("Starting OW in 5 secs...");
  delay(5000);  //important on linux as serial port can lock up otherwise
  numberOfSensors = discoverOneWireDevices(1);
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
    if (temperatureOW > -125)
    {
        Serial.print(did);Serial.print(": "); Serial.println(temperatureOW);
    }
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
  
}

void loop(void) {
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
     delay(1000);
  }
  delay(1000);
}
