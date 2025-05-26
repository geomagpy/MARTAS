#!/usr/bin/env python
"""
MagPy - OPTIMIZING tables and free space
        unblocking version

REQUIREMENTS:
 - magpy
 - sudo apt install percona-toolkit
 - main user (cobs) needs to be able to use sudo without passwd (add to /etc/sudoers)
"""

# Define packgaes to be used (local refers to test environment)
# ------------------------------------------------------------

from magpy.stream import *
import pymysql as mysql
from magpy.core import database
import magpy.opt.cred as mpcred
from martas.core.methods import martaslog as ml
from martas.core import methods as mm
from martas.version import __version__
import socket
import getopt


def optimize(credentials='cobsdb', sqlcred='sql', debug=False):
    """
    DESCRIPTION
        will run an optimization method on all data tables based
        on the percona toolkit
    REQUIREMENTS
        magpy
        sudo apt install percona-toolkit
        main user (cobs) needs to be able to use sudo without passwd (add to /etc/sudoers)
    APPLICATION
        optimize(credentials='cobsdb', sqlcred='sql', debug=True)
    """
    dbpasswd = mpcred.lc(credentials,'passwd')
    dbuser = mpcred.lc(credentials,'user')
    dbhost = mpcred.lc(credentials,'host')
    dbname = mpcred.lc(credentials,'db')

    sqluser = mpcred.lc(sqlcred, 'user')
    sqlpwd = mpcred.lc(sqlcred, 'passwd')

    report = 'optimization failed'

    # Connect to test database
    # ------------------------------------------------------------
    try:
        if debug:
            print("Connecting to DATABASE...")
        db = database.DataBank(host=dbhost, user=dbuser, password=dbpasswd, database=dbname)
    except:
        if debug:
            print("... failed - aborting")
        sys.exit()

    # some general initializations
    cursor = db.db.cursor()
    step1 = True
    step2 = False
    step3 = False
    optimzesql = []
    tables = []

    print ("1. Get initial database information")
    print ("-----------------------------------")
    db.info(destination='stdout',level='full')

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
        print ('optimize: unknown error')
        step1 = False

    if step1:
        tables = cursor.fetchall()
        tables = [el[0] for el in tables]
        if len(tables) > 0:
            print ('optimize: tables found - continuing')
            step2 = True
            step3 = True
    else:
        print ('optimize: aborting')
        cursor.close()

    if step2 and not debug:
        print ("2. Optimizing tables")
        print ("-----------------------------------")
        for table in tables:
            print (' -> running for {}, user: {}'.format(table, sqluser))
            optbash = 'sudo /usr/bin/pt-online-schema-change --alter "Engine=InnoDB" D=cobsdb,t={} --user={} --password={} --execute'.format(table,sqluser,sqlpwd)
            print (optbash)
            try:
                os.system(optbash)
                print ("Done")
            except:
                print ('------------------------------------------')
                print (' --optimize table: unknown error for {}'.format(table))
                print ('------------------------------------------')

    if step3:
        print ("3. Get post-processing information")
        print ("-----------------------------------")
        db.db.commit()
        cursor.close()
        report = db.info(destination='stdout',level='full')

    return report


def main(argv):
    version = __version__
    sn = socket.gethostname().upper()  # servername
    statusmsg = {}
    name = "{}-DBopt".format(sn)
    credentials = 'cobsdb'
    sql = 'sql'
    configpath = ""
    logpath = "/var/log/magpy/tg_db_opt.log"
    conf = {}
    telegramcfg = ""
    debug=False

    try:
        opts, args = getopt.getopt(argv,"hc:d:s:l:D",["config=","database=","sql=","logpath=","debug=",])
    except getopt.GetoptError:
        print ('cobs_optimizetables.py -c <config>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print ('-------------------------------------')
            print ('Description:')
            print ('-- optimizetables.py will analyse magnetic data --')
            print ('-----------------------------------------------------------------')
            print ('detailed description ..')
            print ('...')
            print ('...')
            print ('-------------------------------------')
            print ('Usage:')
            print ('python optimizetables.py -c <config>')
            print ('-------------------------------------')
            print ('Options:')
            print ('-c (required) : configuration data path')
            print ('-d            : database credentials')
            print ('-s            : sql')
            print ('-l            : logpath')
            print ('-------------------------------------')
            print ('Application:')
            print ('python3 optimzetables.py -d cobsdb -s sql')
            sys.exit()
        elif opt in ("-c", "--config"):
            configpath = os.path.abspath(arg)
        elif opt in ("-d", "--database"):
            credentials = arg
        elif opt in ("-s", "--sql"):
            # define a dayrange for archive jobs - default is 2
            sql = arg
        elif opt in ("-l", "--logpath"):
            logpath = arg
        elif opt in ("-D", "--debug"):
            debug = True

    if configpath:
        conf = mm.get_conf(configpath)
        basepath = os.path.dirname(conf.get("logging"))
        logpath = os.path.join(basepath,"optimize.log")
        telegramcfg = os.path.join(basepath,"..","conf","telegram.cfg")
    print ("Running optimize version", version)
    print ("-------------------------------")
    report = optimize(credentials=credentials, sqlcred=sql, debug=debug)

    # Send out a new status
    statusmsg[name] = report
    print("Status", statusmsg[name])

    if report and telegramcfg and not debug:
        martaslog = ml(logfile=logpath, receiver='telegram')
        martaslog.telegram['config'] = telegramcfg
        martaslog.msg(statusmsg)
    else:
        print("Status", statusmsg[name])


if __name__ == "__main__":
   main(sys.argv[1:])
