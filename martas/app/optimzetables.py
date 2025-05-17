#!/usr/bin/env python
"""
MagPy - OPTIMIZING tables and free space
        unblocking version

REQUIREMENTS:
 - magpy
 - sudo apt install percona-toolkit
 - main user (cobs) needs to be able to use sudo without passwd (add to /etc/sudoers)
"""
from __future__ import print_function

# Define packges to be used (local refers to test environment) 
# ------------------------------------------------------------

from magpy.stream import *
from magpy.database import *
import magpy.opt.cred as mpcred

# Get password from cred
# ------------------------------------------------------------
dbpasswd = mpcred.lc('cobsdb','passwd')
dbuser = mpcred.lc('cobsdb','user')
sqluser = mpcred.lc('sql','user')
sqlpwd = mpcred.lc('sql','passwd')

# Use Telegram logging
# ------------------------------------------------------------
logpath = '/var/log/magpy/tg_db.log'
sn = 'ALDEBARAN' # servername
statusmsg = {}
name = "{}-DBopt".format(sn)


# Connect to test database
# ------------------------------------------------------------
try:
    print("Connecting to DATABASE...")
    db = mysql.connect(host="localhost",user=dbuser,passwd=dbpasswd,db="cobsdb")
except:
    print("... failed")
    sys.exit()

# some general initializations
cursor = db.cursor()
step1 = True
step2 = True
step3 = True
optimzesql = []

print ("1. Get initial database information")
print ("-----------------------------------")
dbinfo(db,destination='stdout',level='full')

print ("2. Get all tables")
print ("-----------------------------------")
tablessql = 'SHOW TABLES'
try:
    cursor.execute(tablessql)
except mysql.IntegrityError as message:
    print (message)
    step1 = False
except mysql.Error as message:
    print (message)
    step1 = False
except:
    print ('optimze: unkown error')
    step1 = False

if step1:
    tables = cursor.fetchall()
    tables = [el[0] for el in tables]
    if not len(tables) > 0:
        print ('optimze: no tables found - stopping')
        step2 = False
else:
    print ('optimze: aborting')
    cursor.close()

#tables = [el for el in tables if el.startswith('WIC')]

if step2:
    print ("3. Optimizing tables")
    print ("-----------------------------------")
    for table in tables:
        print (' -> running for {}, user: {}'.format(table, sqluser))
        optbash = 'sudo /usr/bin/pt-online-schema-change --alter "Engine=InnoDB" D=cobsdb,t={} --user={} --password={} --execute'.format(table,sqluser,sqlpwd)
        print (optbash)
        try:
            #print (optbash)
            os.system(optbash)
            print ("Done")
        except:
            print ('------------------------------------------')
            print (' --optimze table: unkown error for {}'.format(table))
            print ('------------------------------------------')

if step3:
    print ("4. Get post-processing information")
    print ("-----------------------------------")
    db.commit()
    cursor.close()
    report = dbinfo(db,destination='stdout',level='full')
    # requires magpy 0.9.7
    statusmsg[name] = report


# Send out a new status
if statusmsg[name] == '':
    martaslog = ml(logfile=logpath,receiver='telegram')
    martaslog.telegram['config'] = '/home/cobs/SCRIPT/telegram_notify.conf'
    martaslog.msg(statusmsg)
