"""
cr1000jcprotocol written 2017 by richard.mandl@zamg.ac.at
for MQTT protocol by Roman Leonhardt and Rachel Bailey to be used in the Conrad Observatory.
Makes sense only when using a CR1000 data logger with specific set-up
in combination with a Judd JC depth sensor 
to measure snow depth
"""
from __future__ import print_function
from __future__ import absolute_import

# ###################################################################
# Import packages
# ###################################################################

import struct # for binary representation
from datetime import datetime, timedelta
from twisted.python import log
from martas.core import acquisitionsupport as acs
import threading
import time

try:
    from pycampbellcr1000 import CR1000
    cr1000imported = True
except:
    log.msg("pycampbellcr1000 package not available")
    cr1000imported = False

# ###################################################################

# some helpful function
def datetime2array(t):
    return [t.year,t.month,t.day,t.hour,t.minute,t.second,t.microsecond]

# sensor height in cm
# TODO 184 ist fuer die Hohe Warte am Schreibtisch
SENSOR_HEIGHT = 184

if cr1000imported:
    class cr1000jcProtocol:        
        """
        Protocol to read from a campbell datalogger CR1000
        The CR1000's tables are configured to log Judd JC data
        """

        device=None
        reconnect=threading.Event()

        def __init__(self, client, sensordict, confdict):
            self.client = client
            self.sensordict = sensordict 
            self.confdict = confdict
            # variables for broadcasting via mqtt:
            self.count=0
            self.datalst = []
            #self.datacnt = 0
            self.metacnt = 10
            ###
            port = confdict['serialport']+sensordict.get('port')
            baudrate = sensordict.get('baudrate')
            # string should look like that: device = CR1000.from_url('serial:/dev/ttyUSB3:38400')
            #try: 
            log.msg('connecting to device...')
            self.device = CR1000.from_url('serial:{}:{}'.format(port,baudrate))
            #except:
                # TODO no CR1000 present... "Can not access to device"
                #log.msg('Can not access to device')
            tables = self.device.list_tables()
            if not tables == ['Status', 'SamplesEvery2s', 'ValuesEveryMinute', 'Public']:
                # TODO log-Befehl, Abbruch!
                log.msg('CR1000 not configured for Judd JC')
            else:
                self.device.settime(datetime.utcnow())
                # TODO folgende Ausgabe nur fuers Programmieren!!
                log.msg('++++++++ Information von den Konfig-Dateien +++++++++++++')
                log.msg('++ client:')
                log.msg(client)
                log.msg('++ sensordict:')
                log.msg(sensordict)
                log.msg('++ confdict:')
                log.msg(confdict)

        def sendRequest(self):
            # TODO wohin mit debug?
            debug = False
            if self.reconnect.is_set():
                log.msg('exiting, mutex locked!')
                return
            t = datetime.utcnow()
            past = t-timedelta(seconds=3)
            vals = self.device.get_data('SamplesEvery2s',past,t)
            # vals[0] because we grap no older data, there is only one value in 2 seconds
            # timestamp directly from datetime into array
            # TODO Roman fragen, ob oder wie Vergleich mit Computerzeit
            try:
                darray = datetime2array(vals[0]['Datetime'])
                # TODO "again" ist Provisorium
                again = False
            except:
                again = True
            try:
                if again:
                    t = datetime.utcnow()
                    past = t-timedelta(seconds=3)
                    darray = datetime2array(vals[0]['Datetime'])
                    log.msg("IT TOOK A SECOND TIME TO GET DATA PROPERLY!") 
            except:
                # there will be no log messages when the logger is turned off
                return
                # TODO reconnect Loesung, nur wenn sie sauber funktioniert!
                log.msg('NO DATA FROM CR1000 !!! - vals:')
                log.msg(vals)
                port = self.confdict['serialport']+self.sensordict.get('port')
                baudrate = self.sensordict.get('baudrate')
                self.reconnect.set()
                connected=False
                while not connected:
                    self.device.bye()
                    log.msg('reconnecting to device...')
                    time.sleep(5)
                    try:
                        self.device = CR1000.from_url('serial:{}:{}'.format(port,baudrate))
                        tables = self.device.list_tables()
                        if tables == ['Status', 'SamplesEvery2s', 'ValuesEveryMinute', 'Public']:
                            connected=True
                            log.msg('schaut ok aus...')
                            time.sleep(2)
                    except:
                        log.msg('reconnect wohl missglueckt!')
                    try:
                        past = t-timedelta(seconds=3)
                        vals = self.device.get_data('SamplesEvery2s',past,t,debug=True)
                        log.msg(SENSOR_HEIGHT*1000.-vals[0]['DiffVolt']*250.)
                    except:
                        log.msg('...wohl doch nicht!')
                        connected=False
                self.reconnect.clear()
                log.msg('mutex released...')
                return
            if debug:
                log.msg('getting data...')
            # snowheight (1000mV is 250cm) - values from CR1000 in mV, factor 1000 for packing
            snowheight = SENSOR_HEIGHT*1000.-vals[0]['DiffVolt']*250.
            darray.append(int(round(snowheight)))
            # TODO weg
            if debug:
                log.msg(darray)

            # preparations for file save
            # date 6 short microsecond unsigned long snowheight signed long
            # TODO alter packcode!
            packcode = "6hLl"
            #packcode = "<6hLl"
            # header 
            sensorid = self.sensordict['sensorid']
            header = "# MagPyBin %s %s %s %s %s %s %d" % (sensorid,'[f]','[JC]','[cm]','[1000]',packcode,struct.calcsize(packcode))
            data_bin = struct.pack(packcode,*darray)
            # date of dataloggers timestamp
            filedate = datetime.strftime(datetime(darray[0],darray[1],darray[2]), "%Y-%m-%d")
            if not self.confdict.get('bufferdirectory','') == '':
                acs.dataToFile(self.confdict.get('bufferdirectory'), sensorid, filedate, data_bin, header)
                if debug:
                    log.msg('Daten gesichert...')

            # sending via MQTT
            data = ','.join(list(map(str,darray)))
            head = header
            topic = self.confdict.get('station') + '/' + self.sensordict.get('sensorid')
            coll = int(self.sensordict.get('stack'))
            if coll > 1:
                self.metacnt = 1 # send meta data with every block
                if self.datacnt < coll:
                    self.datalst.append(data)
                    self.datacnt += 1
                else:
                    senddata = True
                    data = ';'.join(self.datalst)
                    self.datalst = []
                    self.datacnt = 0
            else:
                senddata = True

            if senddata:
                self.client.publish(topic+"/data", data)
                if self.count == 0:
                    self.client.publish(topic+"/meta", head)
                self.count += 1
                if self.count >= self.metacnt:
                    self.count = 0


            
            # right now auxiliary data only in the log file
            if t.second<2:
                # every minute aux data (battery voltage and logger temperature) will be available
                # going 61s into the past to make sure there are already data
                past=t-timedelta(seconds=61)
                aux=self.device.get_data('ValuesEveryMinute',past,t)
                log.msg('----- aux every minute:')
                # timestamp directly from datetime into array
                try:
                    darray = datetime2array(aux[0]['Datetime'])
                except:
                    # following should never happen...
                    log.msg('AUXILIARY DATA NOT GOT PROPERLY! - aux:')
                    log.msg(aux)
                    log.msg('trying again...')
                    past=t-timedelta(seconds=62)
                    aux=self.device.get_data('ValuesEveryMinute',past,t)
                    try:
                        darray = datetime2array(aux[0]['Datetime'])
                    except:
                        log.msg('giving up...')
                        return

                # battery voltage - factor 1000 for packing
                BattV_Min=int(round(aux[0]['BattV_Min']*1000))
                PTemp_C_Avg=int(round(aux[0]['PTemp_C_Avg']*1000))
                darray.extend([BattV_Min,PTemp_C_Avg])
                # alernative reading:
                #aux = (aux.filter(('Datetime', 'BattV_Min','PTemp_C_Avg')).to_csv(header=False))
                log.msg(darray)
                packcode="<6hLLl"

