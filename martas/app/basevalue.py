#!/usr/bin/env python
# coding=utf-8

"""
MagPy - Baseline recalculation

This method should be able to do:
- recalculate baselines with or without rotation parameters
- can be run during yearly analysis and update all BLV files on Server
- update DIDATA_XXX raw data tables
- update BLV data in database

        This data is then used in the stepwise procedure:
        (firstrun: uncompensated data run: get average basevalues, get an initial
                    constant baseline estimate, delta F and basis for quality checks)
        (secondrun: compensated data run: apply offsets, apply rotation, get baseline,
                    delta F and basis for quality checks)
        IMPORTANT:
                   1. initial baseline for piers other than A2:
                       -> have delta values (delta D, I, F) been considered?
                       -> which one were considered?
                       Answer: yes! deltaD, deltaI and deltaF are already considered
                               in the absolute method, as long as db is active.
                               Therefor BLV db inputs are already corrected.
                               The input of the PIERS table is read, split by komma,
                               and the last line is used.
                       Problem: each DB line needs a reference to the correction values used.
                               Could be done in DataDeltaValues - NO, because it
                               changes from one day to the other
                               Need to be part of the result line -> string5?
                    2. new delta D and delta I:
                       -> where do I get them?
                       -> how are they calculated?
                       -> at which step are those included?
                       -> how do they compare to the previous values?
                       -> are they written to the database?
                    Resulting application scheme:
                       -> check for delta values in PIERS - those have been used for BLV tables


"""

# Define packges to be used (local refers to test environment)
# ------------------------------------------------------------
from magpy.stream import *
import magpy.absolutes as di
from magpy.core import plot as mp
from magpy.core import database
from magpy.core import methods
from magpy.opt import cred as mpcred

from martas.version import __version__

from dateutil.parser import parse
from shutil import copyfile

import itertools
import getopt
import pwd
import socket
import sys  # for sys.version_info()

from martas.core.methods import martaslog as ml
from martas.core import methods as mm

#from cobs_methods import define_logger, connect_databases, get_primary_instruments, get_stringdate, combinelists, \
#    get_conf


## Methods from yearly_analysis_1 -> can later be imported to yearly_analysis
def baseline_overview(runmode='firstrun', config=None, destpath=None, debug=False):
    """
    DESCRIPTION:
        Provide an overview about existing basevalues. The baseline_overview method will read existing basevalue
        data files from DB or file, named like BLV_vario_scalar_pier. BLV corresponds to blvabb, vario and scalar
        contain the SensorID's of variometer and scalar sensor, pier is obvious.
        After reading the BLV data, flagging info is obtained from DB and the given file path in config. Flagged data
        is dropped. Baseline fits are performed using a spline fit with 0.3 knotstep by default. Plotted are daily means
        of the basevalus.
        In case of "thirdrun":
         - only A2 data is plotted
         - a cleaned BLV_..._YEAR.txt file is written to the given blvdatapath directory
         - the graph is stired to the given figurepath

    APPLICATION:
        Step0: we are reviewing source basevalue data (from DB). All existing flags
        are applied and checked. Further flags are added.

    EXAMPLE:

    """

    print(" ----------------------------------------------------------------------- ")
    print(" ----------------  Cleanup and decide on basevalue data----------------- ")
    print(" --------------------------  for each variometer  ---------------------- ")
    print(" ----------------------------------------------------------------------- ")

    if not config:
        config = 'None'
    # Use all scalars only for firstrun - aftwards use average curve
    vainstlist = config.get('vainstlist')
    scinstlist = config.get('scinstlist')
    pierlist = config.get('pierlist')
    primarypier = config.get('primarypier') #,'A2')
    pierdict = config.get('pierdict') #,'A2')
    year = config.get('year')
    blvabb = config.get('blvabb')
    datasource = config.get('datasource')  # db,file
    blvdatapath = config.get('blvdatapath')
    flagfile = config.get('flagfile')
    db = config.get('primaryDB')
    figurepath = config.get('figurepath', '/tmp')
    knotstep = float(config.get('knotstep', 0.3))

    if not config.get('startdate'):
        starttime = str(year - 1) + '-11-01'
        endtime = str(year + 1) + '-02-01'
    else:
        starttime = config.get('startdate')
        endtime = config.get('enddate')
    symbols = ['d', 's', 'o', 'p', '1', '2', '3', '4', '8', '1', '2']
    ttmp = arange(0, 1, 0.0001)
    legendoffset = 2  # shift data of plot 3 so that legend and data are visible

    if debug:
        print(" - you selected {} as blvabb (baseline data file beginning)".format(blvabb))
        print(" - datasource: {} ".format(datasource))
        print(" - starttime: {} ".format(starttime))
        print(" - endtime: {} ".format(endtime))
        print(" - primaryDB: {} ".format(db))

    if not len(vainstlist) > 0:
        print(" baseline requires variometer data: please provide")
    if not len(scinstlist) > 0:
        print(" baseline requires continuous scalar data: please provide")
    # further required are: sourcepath, outpath
    # sourcepath = sourcepath,'DI','data',
    # sourcepath = outpath,'magpy',
    # flagfile = os.path.join(outpath,'magpy','BLV_flags.json')

    for vainst in vainstlist:
        if runmode == 'thirdrun':
            scinstlist = [scinstlist[0]]
        for scinst in scinstlist:
            for idx, pier in enumerate(pierlist):
                basename = "{}_{}_{}_{}".format(blvabb, vainst[:-5], scinst[:-5], pier)
                if runmode in ['secondrun', 'thirdrun'] and methods.is_number(year):
                    filename = "{}_{}_{}.txt".format(basename, year, runmode)
                else:
                    filename = "{}.txt".format(basename)
                    if debug:
                        print ("Checking for {}".format(basename))
                    if not os.path.isfile(os.path.join(blvdatapath, filename)):
                        filename = "{}_{}_{}.txt".format(basename, year, runmode)

                if debug:
                    print ("Path and Filename", blvdatapath, filename)

                if datasource == 'db':
                    print(" Accessing database...")
                    absr = db.read(basename, starttime=starttime, endtime=endtime)
                else:
                    if os.path.isfile(os.path.join(blvdatapath, filename)):
                        print(" Accessing file...", os.path.join(blvdatapath, filename))
                        if debug:
                            print(" Starttime, Endtime:", starttime, endtime)
                        absr = read(os.path.join(blvdatapath, filename), starttime=starttime, endtime=endtime, datecheck=False)
                        if debug:
                            print(" Obtained {} data points".format(len(absr)))
                    else:
                        absr = DataStream()

                print(" Running analysis for {}".format(basename))

                if absr.length()[0] > 0:
                    print("------------------------------")
                    print("Found {} baseline values for {}".format(absr.length()[0], pier))
                    print("------------------------------")
                    absr = absr.removeduplicates()
                    dataid = absr.header.get('DataID')
                    print(" -- Dropping flags contained in data set:")
                    blvflaglistint = absr.header.get("DataFlags")
                    if blvflaglistint:
                        print ("    found {} flags".format(len(blvflaglistint)))
                        absr = blvflaglistint.apply_flags(absr, mode='drop')
                    if db:
                        print(" -- Dropping flags from DB:", dataid)
                        blvflaglist = db.flags_from_db(dataid)
                        print("   -> {} flags".format(len(blvflaglist)))
                        if len(blvflaglist) > 0:
                            absr = blvflaglist.apply_flags(absr, mode='drop')
                    else:
                        if debug:
                            print ("   No DB connected: Could not access flags from DB")
                    if flagfile:
                        print(" -- Dropping flags from File", flagfile)
                        flaglist = flagging.load(flagfile, sensorid=dataid)
                        print("   -> {} flags".format(len(flaglist)))
                        if len(flaglist) > 0:
                            absr = flaglist.apply_flags(absr, mode='drop')
                    absr = absr._drop_nans('dx')
                    absr = absr._drop_nans('dy')
                    absr = absr._drop_nans('dz')
                    if absr.length()[0] > 10:
                        func = absr.fit(['dx', 'dy', 'dz'], knotstep=knotstep)
                    print(" -- Length after removing nan values: {}".format(absr.length()[0]))
                    blvmeans = absr.dailymeans(keys=['dx', 'dy', 'dz'])
                    blvmeans = blvmeans.sorting()
                    ti = blvmeans._get_column('time')
                    basex = blvmeans._get_column('x')
                    basey = blvmeans._get_column('y')
                    basez = blvmeans._get_column('z')
                    sym = symbols[idx]
                    alpha = 1
                    if pierdict.get(pier):
                        if methods.is_number(pierdict.get(pier)):
                            alpha = float(pierdict.get(pier))
                    plt.subplot(311)
                    plt.title('{}'.format(basename[:-3]))
                    plt.ylabel('BASE H')
                    plt.grid(True)
                    plot(ti, basex, color='darkgray', linestyle='', marker=sym, alpha=alpha)
                    if pier == primarypier:
                        x1, x2, y1, y2 = plt.axis()
                        plt.axis((x1, x2, y1 - 4, y2 + 4))
                    if absr.length()[0] > 10:
                        #print (denormalize(ttmp, func[1], func[2]))
                        if not runmode == 'thirdrun' and len(func) > 0:
                            plot(denormalize(ttmp, func[1], func[2]), func[0]['fdx'](ttmp), 'r-')
                        elif pier == primarypier and len(func) > 0:
                            plot(denormalize(ttmp, func[1], func[2]), func[0]['fdx'](ttmp), 'r-', linewidth=2)
                    plt.subplot(312)
                    # plt.tick_params(axis='y', which='both', labelleft='off', labelright='on')
                    plt.ylabel('BASE D')
                    plt.grid(True)
                    plot(ti, basey, color='darkgray', linestyle='', marker=sym, alpha=alpha)
                    if pier == primarypier:
                        x1, x2, y1, y2 = plt.axis()
                        plt.axis((x1, x2, y1 - 0.05, y2 + 0.05))
                    if absr.length()[0] > 10:
                        if not runmode == 'thirdrun' and len(func) > 0:
                            plot(denormalize(ttmp, func[1], func[2]), func[0]['fdy'](ttmp), 'r-')
                        elif pier == primarypier and len(func) > 0:
                            plot(denormalize(ttmp, func[1], func[2]), func[0]['fdy'](ttmp), 'r-', linewidth=2)
                    plt.subplot(313)
                    plt.ylabel('BASE Z')
                    plt.grid(True)
                    # plt.xticks(rotation='vertical')
                    plot(ti, basez, color='darkgray', linestyle='', marker=sym, alpha=alpha, label=pier)
                    if pier == primarypier:
                        x1, x2, y1, y2 = plt.axis()
                        plt.axis((x1, x2, y1 - 4 - legendoffset, y2 + 4 - legendoffset))
                    if absr.length()[0] > 10:
                        if not runmode == 'thirdrun':
                            plot(denormalize(ttmp, func[1], func[2]), func[0]['fdz'](ttmp), 'r-')
                        elif pier == primarypier:
                            plot(denormalize(ttmp, func[1], func[2]), func[0]['fdz'](ttmp), 'r-', linewidth=2)
                    if absr.length()[0] > 0 and destpath and not debug:
                        print("Writing new abs files to {} as {}".format(destpath, basename))
                        absr.write(destpath, filenamebegins=basename, filenameends='_' + str(year) + '.txt',
                                   format_type='PYSTR', coverage='all')
                else:
                    print("No absolutes found for {} - continuing".format(pier))
            plt.legend(loc="lower left", ncol=3, shadow=True)
            if runmode == 'thirdrun' and vainst == vainstlist[0]:
                plotdir = os.path.join(figurepath, 'Yearbook', 'Graphs')
                print("Saving figure to: (defined by figurepath in cfg)", plotdir)
                if not os.path.exists(plotdir):
                    os.makedirs(plotdir)
                plt.savefig(os.path.join(plotdir, 'allbasevalues.png'))
            plt.show()

    return True


def basevalue_recalc(runmode, config=None, startdate=None, enddate=None, debug=False):
    """
    DESCRIPTION
        recalculate basevalues
    """
    if not config:
        config = {}
    vainstlist = config.get('vainstlist')
    scinstlist = config.get('scinstlist')
    pierlist = config.get('pierlist')
    year = config.get('year')
    plot = config.get('plot', 'False')
    blvabb = config.get('blvabb')
    diindent = config.get('diid', '')
    datasource = config.get('datasource')  # db,file
    blvdatapath = config.get('blvdatapath')
    flagfile = config.get('diflagfile')
    db = config.get('primaryDB')
    obscode = config.get('obscode')
    writemode = config.get('writemode')
    writeflags = config.get('writeflags')
    didatapath = config.get('didatapath')
    backup = config.get('backup', False)
    writeblv2file = config.get('writeblv2file', False)
    writeblv2db = config.get('writeblv2db', False)
    writedi2db = config.get('writedi2db', False)
    fixalpha = config.get('usealpha', True)
    fixbeta = config.get('usebeta', True)
    magrotation = config.get('magrotation', True)
    compensation = config.get('compensation', True)
    expectedD = config.get('expectedD', None)
    expectedI = config.get('expectedI', None)
    skipscalardb = config.get('skipscalardb', False)
    movetoarchive = config.get('movetoarchive', False)
    contflagfile = config.get('contflagfile', False) # flagging data for vario and scalar from file
    movetoarchivenow = movetoarchive

    sourcepath = os.path.join(config.get('base'), 'archive', obscode)

    format_type = "PYSTR"

    print("--- RUNNING BASEVALUE CALCULATION ---")

    def _check_db_cond(pier, vario, scalar, conddict):
        if not conddict:
            return True
        # print (conddict)
        boollist = [True]
        vvarios = conddict.get('vario')
        vscalars = conddict.get('scalar')
        vpiers = conddict.get('pier')
        if not isinstance(vvarios, list):
            vvarios = [vvarios]
        if not isinstance(vscalars, list):
            vscalars = [vscalars]
        if not isinstance(vpiers, list):
            vpiers = [vpiers]
        if len(vvarios) > 0 and not vario in vvarios:
            boollist.append(False)
        if len(vpiers) > 0 and not pier in vpiers:
            boollist.append(False)
        if len(vscalars) > 0 and not scalar in vscalars:
            boollist.append(False)

        return np.asarray(boollist).all()

    if not config.get('enddate'):
        startdate = str(year - 1) + '-11-01'
        enddate = str(year + 1) + '-02-01'
    else:
        startdate = config.get('startdate')
        enddate = config.get('enddate')

    if debug:
        print("BLV analysis:")
        print(" blv files will be written to", blvdatapath)

    if runmode in ['thirdrun']:
        if debug:
            print(" Using only primary F as scalar record")
        # it is better to use the primary instrument !!!! -> correct flags are used
        # scinstlist = ['CobsF_sec_0001']
        scinstlist = [scinstlist[0]]

    for scinst in scinstlist:
        if debug:
            print(" Now dealing with scalar {}".format(scinst))
        if scinst:
            if os.path.isdir(scinst):
                print(" scalar instrument provided as full path")
                # directory provided - use this path and get scinst from last layer
                scalarpath = os.path.join(scinst, '*')
                scinst = os.path.basename(os.path.normpath(scinst))
                scalarinst = scinst[:-5]
                print("  -> scalar instrument: {}".format(scinst))
            else:
                scalarinst = scinst[:-5]
                scalarpath = os.path.join(sourcepath, scalarinst, scinst, '*')
            scalarinst = scinst[:-5]
        else:
            scalarpath = None
            scalarinst = "None"
        for vainst in vainstlist:
            if debug:
                print(" Now dealing with vario {}".format(vainst))
            if os.path.isdir(vainst):
                print(" vario instrument provided as full path")
                variopath = os.path.join(vainst, '*')
                vainst = os.path.basename(os.path.normpath(vainst))
                print("  -> vario instrument: {}".format(vainst))
            else:
                variopath = os.path.join(sourcepath, vainst[:-5], vainst, '*')
            if fixalpha and db:
                # IMPORTANT: use alpha for current year
                header = db.fields_to_dict(vainst)
                exist = header.get('DataRotationAlpha', '').split(',')
                rotdic = {}
                for el in exist:
                    cont = el.split('_')
                    try:
                        rotdic[int(cont[0])] = float(cont[1])
                    except:
                        pass
                alpha = rotdic.get(year, 0.0)
                if alpha == 0:
                    print(" - ALPHA is zero - check if last year is existing")
                    alpha = rotdic.get(year - 1, 0.0)
                    if alpha == 0:
                        print(" - ALPHA not existing yet - setting alpha=0")
                    else:
                        print(" - using value for {}: {}".format(year - 1, alpha))
            else:
                alpha = None

            if fixbeta and db:
                # IMPORTANT: use alpha for current year
                header = db.fields_to_dict(vainst)
                exist = header.get('DataRotationBeta', '').split(',')
                rotdic = {}
                for el in exist:
                    cont = el.split('_')
                    try:
                        rotdic[int(cont[0])] = float(cont[1])
                    except:
                        pass
                beta = rotdic.get(year, 0.0)
                if beta == 0:
                    print(" - BETA is zero - check if last year is existing")
                    beta = rotdic.get(year - 1, 0.0)
                    if beta == 0:
                        print("BETA not existing yet - setting beta=0")
                    else:
                        print(" - using value for {}: {}".format(year - 1, beta))
            else:
                beta = None

            if debug:
                print(" rotation data determined")

            if debug:
                # contains a path
                print("MOVETOARCHIVE looks like ", movetoarchive)
            if movetoarchive:
                # movetoarchive = True
                # only activate for last vario and last secular
                lastsc = scinstlist[-1]
                lastva = vainstlist[-1]
                # print (" LAST instruments:", lastsc, lastva)
                # print (" and the insts", scinst, vainst)
                if lastsc.find(scinst) >= 0 and lastva.find(vainst) >= 0:
                    print(" -> activating movetoarchive")
                    movetoarchivenow = movetoarchive
                else:
                    movetoarchivenow = None

            for pier in pierlist:
                if debug:
                    print(" Analyzing for pier {}".format(pier))
                if diindent == 'All':
                    blvid = ".txt"
                else:
                    blvid = "{}_{}.txt".format(pier, obscode)
                skipscalardb = False
                if runmode in ['secondrun', 'firstrun']:
                    deltaD = 0.0000000001
                    deltaI = 0.0000000001
                else:
                    # skipscalardb = True
                    # scalarinst = 'CobsF'
                    # scalarpath = os.path.join(outpath,'magpy','CobsF_sec*')
                    deltaD = None
                    deltaI = None
                if pier == 'A16':
                    abstype = 'autodif'
                    azimuth = 267.36651
                else:
                    abstype = 'manual'
                    azimuth = False
                if debug:
                    print(" di data provided in {}".format(didatapath))
                print("----------------------------------------------------------")
                print("----------------------------------------------------------")
                print("{} absolute analysis for pier {} with {} and {}".format(year, pier, vainst[:-5], scalarinst))
                print("----------------------------------------------------------")
                print("----------------------------------------------------------")
                # absstream = absoluteAnalysis(stationid=stationid, deltaF=deltaF)
                dbadd = False
                if writedi2db and not debug:
                    # writedi2db only supports two write modes: append/insert and fullreplace
                    dbadd = True
                    if writemode == 'fullreplace':
                        prepare_table(db, "DIDATA_{}".format(obscode), startdate, enddate, tcol='StartTime',
                                      cond={'DIID': pier})
                    elif writemode in ['replace', 'overwrite']:
                        print(" writedi2db only supports two write modes: append/insert and fullreplace")

                if debug:
                    print ("Parameter", didatapath, variopath, scalarpath, startdate, enddate)
                absresult = di.absolute_analysis(didatapath, variopath, scalarpath, diid=blvid, pier=pier,
                                                 expD=expectedD, expI=expectedI, starttime=startdate, endtime=enddate,
                                                 db=db, skipscalardb=skipscalardb, compensation=compensation,
                                                 magrotation=magrotation, alpha=alpha, beta=beta, abstype=abstype,
                                                 azimuth=azimuth, deltaD=deltaD, deltaI=deltaI, dbadd=dbadd,
                                                 movetoarchive=movetoarchivenow, flagfile=contflagfile, debug=debug)
                # TODO addDB
                # How is addDB working? -> Append new DI files? Replace existing?
                # How to clean files within the time range?

                if absresult and absresult.length()[0] > 0:
                    absresult = absresult.removeduplicates()
                    # remove all flagged data set (with CobsF)
                    basename = '{}_{}_{}_{}'.format(blvabb, vainst[:-5], scalarinst, pier)  # too save
                    flagname = '{}_{}_{}_{}'.format('BLV', vainst[:-5], scalarinst, pier)  # as flags are stored
                    print(" -------------------------------------")
                    print(" Storing data ")
                    print(" -------------------------------------")
                    print(" - getting flags:")
                    flaglist = []
                    if db:
                        flaglist = db.flags_from_db(flagname)
                        print("   -> {} flags in db".format(len(flaglist)))
                    fllist = flagging.load(flagfile, sensorid=flagname)
                    print("   -> {} flags in file {}".format(len(fllist), flagfile))
                    if len(fllist) > 0 and len(flaglist) > 0:
                        flaglist = flaglist.join(fllist)
                        # flaglist.extend(fllist)
                    elif not len(flaglist) > 0:
                        flaglist = fllist
                    if len(flaglist) > 0:
                        # flaglist = absresult.flaglistclean(flaglist)
                        print("  -> Applying {} flags".format(len(flaglist)))
                        if writeflags:
                            absresult = flaglist.apply_flags(absresult, mode='insert')
                            # TODO or absresult.header['DataFlags'] = flaglist
                            # absresult = absresult.flag(flaglist)
                        else:
                            print("  -> Dropping flagged data")
                            absresult = flaglist.apply_flags(absresult, mode='drop')
                            # absresult = absresult.remove_flagged()
                    if not runmode in ['firstrun', 'secondrun', 'thirdrun']:
                        filenamebegins = "{}".format(basename)
                    else:
                        filenamebegins = "{}_{}_{}".format(basename, year, runmode)

                    extension = '.txt'
                    if format_type == 'PYCDF':
                        extension = '.cdf'

                    if writeblv2file:
                        succ = True
                        if backup:
                            succ = backup_file(os.path.join(blvdatapath, filenamebegins + extension))
                        if succ:
                            print(" - writing data to file using writemode {} ...".format(writemode))
                            wm = writemode
                            if wm in ['append', 'skip']:
                                wm = 'skip'
                            if wm == 'fullreplace':
                                wm = prepare_file(os.path.join(blvdatapath, filenamebegins + extension), startdate,
                                                  enddate, format_type=format_type)
                            print("   -> writing {} data points".format(absresult.length()[0]))
                            absresult.write(blvdatapath, coverage='all', filenamebegins=filenamebegins,
                                            format_type=format_type, mode=wm)
                            print(" ... success")

                    if writeblv2db and _check_db_cond(pier, vainst, scinst, config.get('writedbcond')):
                        print(" - Writing data to DB using writemode {} ...".format(writemode))
                        wm = writemode
                        if wm in ['overwrite', 'delete']:
                            wm = 'delete'
                        if wm in ['append', 'skip']:
                            wm = 'insert'
                        if wm == 'fullreplace':
                            wm = prepare_table(db, filenamebegins, startdate, enddate)
                        # - Replace everything within time range (fullreplace) (not existing in file)
                        # - Replace only existing data (replace) - (replace in file)
                        # - Append data if not existing (append) - (skip in file)
                        # - Delete all and write new file (overwrite) - (overwrite in file)
                        if db:
                            db.write(absresult, tablename=filenamebegins, mode=wm)
                        print(" ... success")

                    if plot == 'True':
                        try:
                            absresult = absresult._drop_nans('dx')
                            absresult = absresult._drop_nans('dy')
                            absresult = absresult._drop_nans('dz')
                            func = absresult.fit(['dx', 'dy', 'dz'], fitfunc='spline', knotstep=0.3)
                            mp.tsplot([absresult], [['dx', 'dy', 'dz']], symbols=[['o', 'o', 'o']],
                                      padding=[5, 0.005, 5], functions=[[func,func,func]], title=pier)
                        except:
                            print(" - Not enough data points for suitable baseline")
                            pass
                    print(" saving (and eventually plotting) successfully finished ")
                    print(" -------------------------------------")
                else:
                    print(" -> obtained an empty abs-result")
                    print(" -------------------------------------")


def check_conf(config, startdate, enddate, varios=None, scalars=None, piers=None, debug=False):
    """
    DESCRIPTION
        this method will extend/modify the configuration data with basevalue analysis specific parameters
    """

    if varios == None:
        varios = []
    if scalars == None:
        scalars = []
    if piers == None:
        piers = []
    if enddate == 'now' or config.get('enddate') == 'now':
        endtime = datetime.now(timezone.utc).replace(tzinfo=None)
        config['enddate'] = endtime.strftime("%Y-%m-%d")
        if not startdate:
            starttime = endtime - timedelta(days=380)
            config['startdate'] = starttime.strftime("%Y-%m-%d")
    elif enddate == 'file':
        # determine startdate and enddate from the available files in the directory
        pass
    elif enddate:
        endtime = parse(enddate)
        config['enddate'] = endtime.strftime("%Y-%m-%d")
        if not startdate:
            starttime = endtime - timedelta(days=380)
            config['startdate'] = starttime.strftime("%Y-%m-%d")
    else:
        enddate = config.get('enddate', None)
        if enddate in ['None', 'False', None, 0]:
            config['enddate'] = None
    if startdate:
        starttime = parse(startdate)
        config['startdate'] = starttime.strftime("%Y-%m-%d")
    else:
        startdate = config.get('startdate', None)
        if startdate in ['None', 'False', None, 0]:
            config['startdate'] = None

    if varios and len(varios) > 0:
        print(" Setting variometers to {}".format(varios))
        config['vainstlist'] = varios
    if scalars and len(scalars) > 0:
        print(" Setting scalars to {}".format(scalars))
        config['scinstlist'] = scalars
    if piers and len(piers) > 0:
        print(" Setting piers to {}".format(piers))
        config['pierlist'] = piers
    pl = config.get('pierlist')
    if not isinstance(pl, (list, tuple)):
        config['pierlist'] = [pl]
    if not config.get('primarypier'):
        if len(config.get('pierlist')) > 0:
            config['primarypier'] = config.get('pierlist')[0]

    if config.get('year') in ['None', 'False', None, 0]:
        config['year'] = None
    elif config.get('year') in ['current', 'now']:
        config['year'] = datetime.now(timezone.utc).replace(tzinfo=None).year

    if config.get('blvdatapath', '') in ['None', 'False', '', None]:
        config['blvdatapath'] = os.path.join(config.get('base', ''), 'archive', config.get('obscode', ''), 'DI', 'data')

    if not isinstance(config.get('dbcredentials'), list):
        config['dbcredentials'] = [config.get('dbcredentials')]
    if not isinstance(config.get('vainstlist'), list):
        config['vainstlist'] = [config.get('vainstlist')]
    if not isinstance(config.get('scinstlist'), list):
        config['scinstlist'] = [config.get('scinstlist')]
    if not isinstance(config.get('pierlist'), list):
        config['pierlist'] = [config.get('pierlist')]

    credentials = config.get('dbcredentials')
    credential = None
    if len(credentials) > 0:
        credential = credentials[0]
    if debug:
        print("- Connecting to database {}".format(credential))
    try:
        db = mm.connect_db(credential)
        print (" ... success")
        config['primaryDB'] = db
    except:
        config['primaryDB'] = None

    sourcepath = os.path.join(config.get('base', ''), 'archive', config.get('obscode', ''))

    if config.get('didatapath') == 'raw':
        config['didatapath'] = os.path.join(sourcepath, 'DI', 'raw')
    elif config.get('didatapath') == 'analyze':
        config['didatapath'] = os.path.join(sourcepath, 'DI', 'analyze')
        if config.get('movetoarchive') in ['True', 'true', True]:
            config['movetoarchive'] = os.path.join(sourcepath, 'DI', 'raw')
    elif config.get('didatapath') == '':
        config['didatapath'] = os.path.join(sourcepath, 'DI', 'raw')

    for key in config:
        if config.get(key) in ['False', 'false']:
            config[key] = False
        if config.get(key) in ['True', 'true']:
            config[key] = True

    return config


def get_runmode(joblist):
    if 'firstrun' in joblist:
        runmode = 'firstrun'
        if not 'overview' in joblist:
            joblist.append('default')
    elif 'secondrun' in joblist:
        runmode = 'secondrun'
        if not 'overview' in joblist:
            joblist.append('default')
    elif 'thirdrun' in joblist:
        runmode = 'thirdrun'
        if not 'overview' in joblist:
            joblist.append('default')
    else:
        runmode = 'upload'
        if not 'overview' in joblist:
            joblist.append('default')
    return list(set(joblist)), runmode


def backup_file(path):
    ret = False
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    agecode = now.strftime("%Y%m%d%H")
    print(" Backing up {}".format(path))
    if os.path.isfile(path):
        directory, finame = os.path.split(path)
        newfilename = "{}.{}.bak".format(finame, agecode)
        newpath = os.path.join(directory, newfilename)
        try:
            shutil.copyfile(path, newpath)
            print(" Backup file saved as {}".format(newpath))
            ret = True
        except:
            pass
    else:
        print("File not yet existing")
        ret = True
    return ret


def prepare_file(path, starttime, endtime, format_type='PYSTR'):
    """
    DESCRIPTION
        Prepare file will remove all contents from the file within the selected timerange
    """
    print(" -> fullreplace: preparing file")
    try:
        # read data
        data = read(path)
        # remove time range
        data1 = data.trim(endtime=starttime)
        data2 = data.trim(starttime=endtime)
        newdata = join_streams(data1, data2)
        # write data
        directory, finame = os.path.split(path)
        fname = finame.split('.')
        newdata.write(directory, filenamebegins=fname[0], coverage='all', format_type=format_type, mode='overwrite')
    except:
        print("File not yet existing?")
    # set wm to replace
    return 'replace'


def prepare_table(db, tablename, starttime, endtime, tcol='time', cond=None):
    # starttime and endtime need to be strings
    if not cond:
        cond = {}
    print(" -> fullreplace: preparing table")
    condition = ''
    if cond:
        for key in cond:
            condstr = "{} LIKE '{}%' AND ".format(key, cond[key])
            condition += condstr
    try:
        delstring = "DELETE FROM {} WHERE {}DATE({}) BETWEEN DATE('{}') AND DATE('{}')".format(tablename, condition,
                                                                                               tcol, starttime, endtime)
        cursor = db.db.cursor()
        cursor.execute(delstring)
        cursor.close()
    except:
        print(" PrepareTable: removing time range failed - table not yet existing?")
    return 'replace'


def main(argv):
    version = __version__
    configpath = ''
    statusmsg = {}
    debug = False
    joblist = ['default']
    startdate = None
    enddate = None
    scalars = []
    varios = []
    piers = []

    # supported jobs are:
    #   (1) calculate basevalues from DI data and write BLV files/DB
    #           -> caluclate BLV files from DI data - daily basis
    #                 (two confs: one for comp with archive, one without comp)
    #           -> redo any BLV analsysis for a specified time range with
    #                 given instruments
    #   (2) homogenize DB contents and files
    #   (3) create overview plots

    try:
        opts, args = getopt.getopt(argv, "hc:j:s:e:v:f:p:D",
                                   ["config=", "joblist=", "startdate=", "enddate=", "variometers=", "scalars=",
                                    "piers=", "debug="])
    except getopt.GetoptError:
        print('basevalue.py -c <config>')
        sys.exit(2)
    for opt, arg in opts:
        if opt == '-h':
            print('-------------------------------------')
            print('Description:')
            print('-- basevalue.py will obtain baseline plots --')
            print('-----------------------------------------------------------------')
            print('detailed description:')
            print(' basevalue.py recalculates basevalues from DI measurements and provided variation and scalar data.')
            print(' The method can use multiple data sources and piers as defined in the configuration file. It')
            print(' further supports different run modes defining the complexity of baseline fits, application of ')
            print(' rotation matricies etc. These run modes are used for the yearly definitive data analysis of the')
            print(' Conrad Obs. It is recommended to use a similar data coverage of approximately one year when using')
            print(' this technique with polynomial or spline fits to get comparable fitting parameters.')
            print(' In default mode: if enddate is set to now and no startdate is given, then startdate')
            print(' is set to now-380days')
            print('')
            print('-------------------------------------')
            print('Usage:')
            print('python basevalue.py -c <config>')
            print('-------------------------------------')
            print('Options:')
            print('-c (required) : configuration data path')
            print("-j            : list of jobs - one of 'firstrun','seconrun','thirdrun','upload'")
            print("              : plus 'default' or 'overview'")
            print("              : -j firstrun,overview will create overview plots using firstrun fits")
            print('-e            : enddate (e.g. now, 2020-11-22)')
            print('-s            : startdate')
            print('-v            : variometer')
            print('-f            : scalar')
            print('-p            : piers')
            print('-------------------------------------')
            print('Application:')
            print(
                'python3 basevalue.py -c /media/leon/Images/products/data/magnetism/definitive/wic2020/basevalue.cfg -j upload -s 2019-01-01 -e 2021-02-01')
            sys.exit()
        elif opt in ("-c", "--config"):
            # delete any / at the end of the string
            configpath = os.path.abspath(arg)
        elif opt in ("-e", "--enddate"):
            enddate = arg
        elif opt in ("-s", "--startdate"):
            startdate = arg
        elif opt in ("-j", "--joblist"):
            joblist = arg.split(',')
        elif opt in ("-v", "--variometers"):
            varios = arg.split(',')
        elif opt in ("-f", "--scalars"):
            scalars = arg.split(',')
        elif opt in ("-p", "--piers"):
            piers = arg.split(',')
        elif opt in ("-D", "--debug"):
            # delete any / at the end of the string
            debug = True

    print("Running basevalue version {}".format(version))
    print("--------------------------------")

    if not os.path.exists(configpath):
        print('!! Specify a valid path to configuration information !!')
        print('-- check basevalue.py -h for more options and requirements')
        sys.exit()

    if debug:
        print("- Read and check validity of configuration data")
    config = mm.get_conf(configpath)
    config = check_conf(config, startdate, enddate, varios=varios, scalars=scalars, piers=piers, debug=debug)
    if debug:
        print("  Configuration data:", config)

    #print("2. Activate logging scheme as selected in config")
    #config = define_logger(config=config, category="Info", job=os.path.basename(__file__),
    #                       newname='mm-basevalue-tool.log', debug=debug)
    # Use the logfile from config
    name1 = "{}".format(os.path.basename(config.get('logfile')))
    name1 = name1.replace(".log","")
    statusmsg[name1] = 'Baseline notification successful'
    if not config.get('primaryDB'):
        statusmsg[name1] = 'database failed'

    if debug:
        print("- Running data analysis")
    joblist, runmode = get_runmode(joblist)
    if debug:
        print("  -> you selected the following jobs ({}) and runmode {}".format(joblist, runmode))

    if 'default' in joblist:
        print("Running default job")
        if debug:
            print("Selected parameters:")
            print(runmode, config.get('usealpha'), config.get('magrotation'), config.get('compensation'), startdate,
                  enddate, config.get('year'))
        basevalue_recalc(runmode, config=config, debug=debug)

    if 'overview' in joblist:
        print("Creating plots and overview")
        if debug:
            print("Selected parameters:")
            print(runmode, startdate, enddate, config.get('year'))
        baseline_overview(runmode=runmode, config=config, debug=debug)

    print("basevalue successfully finished")

    # 6. Logging section
    # ###########################
    if not debug:
        receiver = config.get('notification')
        notificationcfg = config.get('notificationconfig')
        martaslog = ml(logfile=config.get('logfile'), receiver=receiver)
        if receiver == 'telegram':
            martaslog.telegram['config'] = notificationcfg
        elif receiver == 'email':
            martaslog.email['config'] = notificationcfg
        martaslog.msg(statusmsg)
    else:
        print("Debug selected - statusmsg looks like:")
        print(statusmsg)


if __name__ == "__main__":
    main(sys.argv[1:])

"""
### Configuration file for DI and Basevalue analysis

### Some general hints for parameter settings:
### (1) update yearly analysis data in server tables and DB
###   -> update raw file directory with current files
###   -> writemode=fullreplace,writeblv=True,writedi=True
### (2) local yearly analysis
###   -> writemode=fullreplace,writeblv2db=False,writedi2db=False
### (3) permanenty running with rotation
###   -> writemode=replace,didatapath=analyze,backup=False
### (4) permanenty running without rotation
###   -> writemode=replace,didatapath=analyze,backup=False
###   -> fixalpha=False,compensation=True,magrotation=False
###   -> pierlist=A2

### Basically run several jobs: 
### 1) A2, all instruments save DB and file
### 2) other piers, all instr, save file (eventually only primaryinst)
### 3) A2, all instr, no rotation, save file (eventually only primaryinst)


# Timerange
# --------------------------------------------------------------
#  - if a year is provided (e.g. 2020), then start and time will 
     be set to 1.11.2019 prev year and 1.2.2021 
#    -> can be overruled by startdate and enddate as options
# --------------------------------------------------------------
year           :      current
#startdate      :      None
#enddate        :      None


# Instruments
# --------------------------------------------------------------
#  - IMPORTANT: Lists need to be provided. If only one instrument
#             or pier then end with comma
#  - reference is a single instrument - provide SensorID
# --------------------------------------------------------------
#vainstlist     :      LEMI036_1_0002_0002,LEMI025_22_0003_0002
#scinstlist     :      GP20S3NSS2_012201_0001_0001,GSM90_14245_0002_0002,GP20S3NSS3_012201_0001_0001
vainstlist     :      LEMI036_1_0002_0002
scinstlist     :      GP20S3NSS2_012201_0001_0001
#pierlist       :      A2,A7,H1,A16,A4,A8,A10,A5,A1
pierlist       :      A5
mobileinst     :      GSM90_31968_0002


# Databases
# --------------------------------------------------------------
dbcredentials  :      cobsdb


# Analysis parameters
# --------------------------------------------------------------
# - magrotation = True will activate compensation and rotation 
# - compensation = True will activate compensation and rotation 
# - usealpha will handle rotation parameter
# - skipscalardb True will not use offsets from database
#    -> use only if your scalar source is fully corrected for 
#       pier diffs already TODO OR TOGETHER WITH F-ADOPTION
# - movetoarchive: if True and didatapath = analyze then
#      successfully analyzed DI data is moved to raw
# --------------------------------------------------------------
magrotation    :      True
compensation   :      True
usealpha       :      True
expectedD      :      4
expectedI      :      64
skipscalardb   :      False
movetoarchive  :      False


# Paths and data sources
# --------------------------------------------------------------
#  - basepath expects a "magpy" directory structure below
#    like /srv    -> /srv/archive/WIC/Di; /srv/archive/WIC/
#  - if blvdatapath = None: /srv/archive/obscode/DI/data 
#  - didata path can be either analyze, raw or a full path
#  - backup = True will create a backup of BLV data before saving
#  - writemode supports:
#          -> replace: Replace only existing data
#          -> overwrite: Delete all and write new
#          -> append: Append data if not existing
#          -> fullreplace: Replace everything within time range
# --------------------------------------------------------------
obscode        :      WIC
datasource     :      file
ext            :      cdf
base           :      /media/leon/Images
plot           :      False
blvabb         :      BLVcomp
#blvdatapath    :      /media/leon/Images/products/data/magnetism/definitive/wic2020/magpy
flagfile       :      /media/leon/Images/products/data/magnetism/definitive/wic2020/magpy/BLV_flags.json
#saveplotpath   :      xxx
didatapath     :      raw
writemode      :      fullreplace
backup         :      True


# Data receivers
# --------------------------------------------------------------
#  - writeflags: write flags within the DataStream structure
# --------------------------------------------------------------
writeraw       :      False
writeblv2db    :      True
writeblv2file  :      False
writedi2db     :      True
writeflags     :      False
writedbcond    :      vario:LEMI036_1_0002_0002;scalar:GP20S3NSS2_012201_0001_0001;pier:A5

# Monitoring
# --------------------------------------------------------------
#  - Logfile (a json style dictionary, which contains statusmessages) 
#  - Notifaction (uses martaslog class, one of email, telegram, mqtt, log) 
# --------------------------------------------------------------
loggingdirectory       :   /var/log/magpy
notification         :   telegram
notificationconfig   :   /myconfpath/mynotificationtype.cfg

"""


