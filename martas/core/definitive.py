#!/usr/bin/env python
# coding=utf-8

"""
Definitive module contains methods for geomagnetic definitive data analysis. It is currently part of MARTAS2.0
as it uses the same configuration data as basevalue.
Please note that this module was specifically developed for the Conrad Observatory and some of the methods
will only be useful for very similar procedures.

Definitive analysis methods

| class   |      method     |  version |  tested  |              comment             | manual | *used by |
| ------- |  -------------  |  ------- |  ------- |  ------------------------------- | ------ | ---------- |
|         |  create_rotation_sql |  2.0.0 | yes*  | create SQL string for DB update  | -      | yearly_analysis_1 |
|         |  pier_diff      |  2.0.0   |   yes    | pier diff relative to mobilesc   | -      | yearly_analysis_1 |
|         |  scalarcomb     |  2.0.0   |   yes    | merge scalar data (min and sec)  | -      | yearly_analysis_1 |
|         |  scalarcorr     |  2.0.0   |   yes    | clean scalar                     | -      | yearly_analysis_1 |
|         |  variocomb      |  2.0.0   |   yes    | merge minute vario datasets      | -      | yearly_analysis_1 |
|         |  variocorr      |  2.0.0   |   yes    | clean, rotate and adopt baseline | -      | yearly_analysis_1 |


"""
import sys
sys.path.insert(1,'/home/leon/Software/MARTAS/') # should be magpy2
sys.path.insert(1,'/home/leon/Software/magpy/') # should be magpy2

import unittest
from magpy.stream import *
from magpy.core import methods

from martas.core import methods as mm
from martas.app import basevalue
from magpy.core import plot as mp


def create_rotation_sql(rotangledict, config=None, debug=False):

    if not config:
        config = {}
    vainstlist = config.get('vainstlist')
    year = config.get('year')
    db = config.get('primaryDB')
    rotation = False
    meanrotangle = 0.0
    sqlstatement = []
    print ("IMPORTANT: update database with rotation")
    print ("----------------------------------------")
    for vainst in vainstlist:
        # get existing rotangle data
        header = db.fields_to_dict(vainst)
        exist = header.get('DataRotationAlpha','')
        existbeta = header.get('DataRotationBeta','')
        # obtain new
        rotanglelist = rotangledict.get(vainst,[])
        meanrotangle = np.median(rotanglelist,axis=0)

        if not exist == '':
            val = '{},{}_{:.3f}'.format(exist,year,meanrotangle[0])
        else:
            val = '{}_{:.3f}'.format(year,meanrotangle[0])
        updatestr = "UPDATE DATAINFO SET DataRotationAlpha='{}' WHERE SensorID LIKE '{}%';".format(val,vainst[:-5])
        sqlstatement.append(updatestr)
        print (updatestr)
        if not existbeta == '':
            val = '{},{}_{:.3f}'.format(existbeta,year,meanrotangle[1])
        else:
            val = '{}_{:.3f}'.format(year,meanrotangle[1])
        updatestr = "UPDATE DATAINFO SET DataRotationBeta='{}' WHERE SensorID LIKE '{}%';".format(val,vainst[:-5])
        sqlstatement.append(updatestr)
        print (updatestr)
    print ("----------------------------------------")
    return sqlstatement

def pier_diff(runmode, config=None, debug=False):
    """
    REQUIREMENT:
        python3

    DESCRIPTION:
     Check DI differnces for all piers:
     Load definite data for primary instruments (minute resolution is fine)
     Convert to IDF
     Then load DI data for all piers and calculate average diffs relative to definite data
     -> Checks diffs (should be zero for A2)
    """
    if not config:
        config = {}

    sqlstatement = []

    print ("------------------------------------")
    print ("Pier differences")
    print ("------------------------------------")

    vainstlist = config.get('vainstlist')
    scinstlist = config.get('scinstlist')
    pierlist = config.get('pierlist')
    year = int(config.get('year'))
    plot = config.get('plot','False')
    blvabb = config.get('blvabb')
    mobileinst = config.get('mobileinst')
    outpath = config.get('outpath',"/tmp")
    db = config.get('primaryDB')


    prv = vainstlist[0][:-5]  # primary variometer
    prf = scinstlist[0][:-5]  # primary scalar

    # Load definite data dependent on runmode
    if runmode in ['secondrun']:
        # Read one minute definite data
        definitive = read(os.path.join(outpath,'magpy','Definitive_min_mag_{}_{}.cdf'.format(year,runmode)))
        print ("Definitive one minute data with {} data points loaded".format(definitive.length()[0]))
    else:
        print ("Runmode not valid aborting")
        return []
    defi = definitive.hdz2xyz()
    defi = defi.xyz2idf()

    print ("Loading F data from mobile sensor")
    mobilef = read(os.path.join(outpath,'magpy','{}_0001_scalar_oc_min_*'.format(mobileinst)))
    print ("    -> got {} datapoints".format(mobilef.length()[0]))
    print (" - getting standard flags for this sensor")
    #from file
    flagfilename = os.path.join(outpath,'magpy','{}_flags.json'.format(mobileinst))
    mobflaglist = flagging.load(flagfilename, sensorid=mobileinst)
    #from DB
    mobflaglist2 = db.flags_from_db(mobileinst)
    if len(mobflaglist) > 0 and len(mobflaglist2) > 0:
        mobflaglist = mobflaglist.join(mobflaglist2)
    elif len(mobflaglist2) > 0:
        mobflaglist = mobflaglist2
    print (" - found {} flags".format(len(mobflaglist)))
    # Applying all flags
    if mobflaglist:
        mobilef = mobflaglist.apply_flags(mobilef, mode='drop')
    print (" - getting pier flags for this sensor")
    pierfilename = os.path.join(outpath,'magpy','{}_piers.json'.format(mobileinst))
    pierflaglist = flagging.load(pierfilename, sensorid=mobileinst)
    if not len(pierflaglist) > 0:
        print (" --------------------------------------")
        print (" Need to access the pier flaglist to perform this method - aborting")
        print (" --------------------------------------")

    def get(selfi, searchdict, combine='and'):
        """
        DESCRIPTION:
            extract data from flaglist

        EXAMPLE:
            newflaglist = flaglist.get({'comment':'lightning'})
        """

        extractedflaglist = []

        for idx,searchcrit in enumerate(searchdict):
            if combine == 'and' and idx >= 1:
                flaglist = extractedflaglist
            elif combine == 'and' and idx == 0:
                flaglist = selfi
            else: # or
                flaglist = selfi
            #print (searchcrit, searchdict[searchcrit])
            pos = 4 #self.FLAGKEYS.index('comment')
            fl = [el for el in flaglist if searchdict[searchcrit] in el[pos]]
            extractedflaglist.extend(fl)

        return extractedflaglist

    for i in range(1,18):
        pier = 'A{}'.format(i)
        if i == 17:
            pier = 'H1'
        print ("-------------------------------------------")
        print (" Dealing with pier {}".format(pier))
        print ("-------------------------------------------")

        ad, adstd = '',''
        ai, aistd = '',''
        af, afstd = '',''

        print ("############################")
        print (" - Getting existing values from data base")

        # Delta Dictionary in PIERS
        #
        val= db.select('DeltaDictionary','PIERS','PierID like "{}"'.format(pier))[0]
        dic = string2dict(val) #, typ='olddeltadict')
        # Get A2 values
        a2dic = dic['A2']   # append new values here (a2dic[year] = newvaluedict; dic['A2'] = a2dic)
        # get last year for each value
        existdelta = []
        for elem in ['deltaD','deltaI','deltaF']:
            # get years when elem was determined
            years = [int(ye) for ye in a2dic if not a2dic[ye].get(elem,'') == '']
            if len(years) > 0:
                value = a2dic.get(str(max(years))).get(elem,'')
                line = "{} ({}): {}".format(elem,max(years),value)
            else:
                line = "{} ([]): never determined".format(elem)
            existdelta.append(line)

        print ("############################")
        print (" - Extract F values from mobile sensor for pier {}".format(pier))

        currentpier = get(pierflaglist,{'comment':pier})
        if len(currentpier) > 0:
            print (" - found valid data range ... ")
            arsum = [[]]*24
            for el in currentpier:
                ar = mobilef._select_timerange(starttime=el[0], endtime=el[1])
                if debug:
                     print (len(ar[0]), el[0], el[1])
                if not len(arsum[0]) > 0:
                    arsum = ar
                    print (arsum)
                else:
                    for idx,el in enumerate(ar):
                        arsum[idx] = np.concatenate((arsum[idx],ar[idx]))
                    #print (len(arsum[0]))
            print (" - got {} data points".format(len(arsum[0])))
            pierts = DataStream([],mobilef.header,arsum)
            pierts = pierts.get_gaps()
            #mp.plot(pierts)

            fdiff = subtractStreams(definitive, pierts)
            fdiff = fdiff.get_gaps()
            fdiff = fdiff.flag_outlier(threshold=3,timerange=timedelta(seconds=600))
            fdiff = fdiff.remove_flagged()
            if plot == 'True':
                mp.tsplot(fdiff, title=pier)
            fdiff = fdiff._drop_nans('f')

            af,afstd = fdiff.mean('f',meanfunction='median',std=True,percentage=5)
            print (" - F-results:", af,afstd)

        if pier in pierlist:
            print ("############################")
            print (" - Running directional delta analysis for pier {}".format(pier))
            vals1 = defi.copy()

            blvname = '{}_{}_{}_{}_{}_{}.txt'.format(blvabb,prv,prf,pier,year,runmode)
            #delete
            #blvname = '{}-step7.txt'.format(pier)
            print (" - Loading {}".format(blvname))
            try:
                blvdata = read(os.path.join(outpath,'magpy',blvname))
                #delete
                #blvdata = read(os.path.join('/home/leon/Dropbox/Daten/IAGA/DI-files',blvname))
                print (" - Got {} data points in BLV file".format(blvdata.length()[0]))
            except:
                blvdata = DataStream()

            if blvdata.length()[0] > 0:
                print (" - Analyzing {}".format(blvname))
                print (" - Determining dD, dI (and dF) in comparison to Definite_min...cdf file (based on A2):")
                print (" - Trimming original data to overlapping range")
                vals2 = blvdata.copy()
                #vals2 = vals2.idf2xyz()
                #mp.plot(vals1)

                diff = subtract_streams(vals1,vals2, keys=['x','y','z','f'])
                if diff.length()[0] > 2:
                    print (" - difference values: {}".format(diff.length()[0]))
                    fl = flagging.flag_outlier(diff, keys=['x','y','z','f'], timerange=60, threshold=2, markall=True)
                    diff = fl.apply_flags(diff, mode='drop')
                    if plot == 'True':
                        mp.tsplot(diff)
                    print (" - remaining after quick outlier removal: {}".format(diff.length()[0]))
                    ai,aistd = diff.mean('x',meanfunction='median',std=True,percentage=50)
                    ad,adstd = diff.mean('y',meanfunction='median',std=True,percentage=50)
                    az,azstd = diff.mean('z',meanfunction='median',std=True,percentage=50)

        print ("############################")
        print ("Delta values results for pier {}".format(pier))
        valdic = {}
        for idx,elem in enumerate(['deltaD','deltaI','deltaF']):
            print ("{}:".format(elem))
            print (" -> Last determination: {}".format(existdelta[idx]))
            short = elem[-1].lower()
            val = eval("a{}".format(short))
            stdval = eval("a{}std".format(short))
            if short in ['i','d'] and not ad == '' and not ai == '' and np.abs(stdval) > np.abs(val):
                # Significance test
                print (" -> New value (not significant): {} +/- {}".format(val,stdval))
                valdic[elem] = '0.00001'
            else:
                print (" -> New value: {} +/- {}".format(val,stdval))
                if not str(val) == '':
                    if short in ['d','i']:
                        strval = "{:.5f}".format(val)
                    else:
                        strval = "{:.2f}".format(val)
                    valdic[elem] = strval

        if valdic:
            a2dic[str(year)] = valdic
            dic['A2']  = a2dic

        command = dict2string(dic)
        print (command)
        sqlline = "UPDATE PIERS SET DeltaDictionary='{}' WHERE PierID='{}';".format(command,pier)
                #sqlstatement.append(sqlline)
        dic = string2dict(command,typ='dictionary')
        print (dic)
        sqlstatement.append(sqlline)

    print (sqlstatement)
    return sqlstatement

def scalarcomb(runmode, config=None, startmonth=-1, endmonth=13, debug=False):
    """
    DESCRIPTION
        create a merged scalar data file
    """
    if not config:
        config = {}
        return

    outpath = config.get('outpath',"/tmp")

    print (" ----------------------------------------- ")
    print (" --- Combining F measurements --- ")
    print (" ----------------------------------------- ")
    ### !! Run from -1 to 13 to cover the time range of abolutes:
    year = config.get('year')
    scinstlist = config.get('scinstlist')

    f, dt = [],[]
    combminute = False
    combsecond = False
    for i in range(startmonth,endmonth):
        # Extract time range (monthly junks)
        startyear = year
        nextyear = year
        month = str(i+1).zfill(2)
        if i == -1:
           startyear = year-1
           month = str(i+13).zfill(2)
        if i+1 >= 13:
            startyear = year+1
            month = str(i-11).zfill(2)
        nextmonth = str(i+2).zfill(2)
        if i+2 >= 13:
            nextyear = year+1
            nextmonth = str(i-10).zfill(2)

        dstarttime=datetime.strptime(str(startyear)+'-'+month+'-01',"%Y-%m-%d")
        dendtime=datetime.strptime(str(nextyear)+'-'+nextmonth+'-01',"%Y-%m-%d")
        print ("Dealing with data between {} and {}".format(dstarttime,dendtime))
        refmin = DataStream()
        ref = DataStream()

        for idx,scinst in enumerate(scinstlist):
            if idx == 0:
                print ("-------------------------------------")
                print ("Base data: {}".format(scinst))
                print ("-------------------------------------")
                if not combminute:
                    refmin = read(os.path.join(os.path.join(outpath,'magpy','{}_scalar_oc_min_{}_{}.cdf'.format(scinst,runmode,year))))
                    print ("Got {} data points in reference min file".format(refmin.length()[0]))
                    print ("Drop line with nan values")
                    refmin = refmin._drop_nans('f')
                if not combsecond and os.path.isfile(os.path.join(os.path.join(outpath,'magpy','{}_scalar_oc_sec_{}{}{:02d}.cdf'.format(scinst,runmode,dstarttime.year,dstarttime.month)))):
                    ref = read(os.path.join(os.path.join(outpath,'magpy','{}_scalar_oc_sec_{}{}{:02d}.cdf'.format(scinst,runmode,dstarttime.year,dstarttime.month))))
                    print ("Got {} data points in reference sec file".format(ref.length()[0]))
                    # Drop flagged data
                    print ("Drop flagged")
                    print (ref.length(), ref.timerange())
                    ref = ref.remove_flagged()
                    print ("Resampling data")
                    print (ref.length())
                    print (ref.timerange())
                    ref = ref.resample(['f'],period=1)
                    print ("Drop line with nan values")
                    ref = ref._drop_nans('f')
            else:
                print ("-------------------------------------")
                print ("Adding data from {}".format(scinst))
                print ("-------------------------------------")
                if not combminute:
                    if os.path.isfile(os.path.join(outpath,'magpy','{}_scalar_oc_min_{}_{}.cdf'.format(scinst,runmode,year))):
                        addmin = read(os.path.join(outpath,'magpy','{}_scalar_oc_min_{}_{}.cdf'.format(scinst,runmode,year)))
                        print ("Got {} data points in min file".format(addmin.length()[0]))
                        print ("Drop line with nan values")
                        addmin = addmin._drop_nans('f')
                        print ("Merging timeseries")
                        refmin = join_streams(refmin,addmin)
                        print ("Reference now contains {} data points (min)".format(refmin.length()[0]))
                if not combsecond:
                    if os.path.isfile(os.path.join(outpath,'magpy','{}_scalar_oc_sec_{}{}{:02d}.cdf'.format(scinst,runmode,dstarttime.year,dstarttime.month))):
                        add = read(os.path.join(outpath,'magpy','{}_scalar_oc_sec_{}{}{:02d}.cdf'.format(scinst,runmode,dstarttime.year,dstarttime.month)))
                        print ("Got {} data points in sec file".format(add.length()[0]))
                        # Get sampling rate and only continue if sr <= 1
                        sr = add.samplingrate()
                        print ("Sampling rate : {} sec".format(sr))
                        if not sr > 1.01:
                            print ("sampling rate OK - continue")
                            # Drop flagged data
                            print ("Drop flagged")
                            flags = add.header.get("DataFlags")
                            if flags:
                                add = flags.apply_flags(add, mode='drop')
                            print ("Resampling data")
                            add = add.resample(['f'],period=1)
                            print ("Drop line with nan values")
                            add = add._drop_nans('f')
                            #print ("Checking subtract")
                            #subtract = subtractStreams(ref,add)
                            #flaglist = subtract.flag_outlier(threshold=3,returnflaglist=True)
                            print ("Merging timeseries")
                            ref = join_streams(ref,add)
                            print ("Reference now contains {} data points (sec)".format(ref.length()[0]))
                        else:
                            print ("sampling rate too large for second combination")
        if refmin.length()[0] > 0:
            print ("Minute data combined")
            combminute = True
            refmin = refmin.get_gaps()
            refmin.write(os.path.join(outpath,'magpy'),filenamebegins='CobsF_min_{}'.format(runmode),coverage='all',mode='overwrite',format_type='PYCDF')
            #save to file
        if ref.length()[0] > 0:
            ref = ref.get_gaps()
            print ("Second data combined for {}".format(dstarttime.month))
            ref.write(os.path.join(outpath,'magpy'),filenamebegins='CobsF_sec_{}_'.format(runmode),dateformat='%Y%m',coverage='month',mode='replace',format_type='PYCDF')


def scalarcorr(runmode, config=None, startmonth=-1, endmonth=13, flagfile=None, skipsec=False, debug=False):
    if debug:
        print (" ----------------------------------------- ")
        print (" --- Checking and Filtering F --- ")
        print (" ----------------------------------------- ")
    ### !! Run from -1 to 13 to cover the time range of abolutes:
    if not config:
        config = {}
        return
    year = config.get('year')
    scinstlist = config.get('scinstlist')
    testdate = config.get('testdate',"")

    sourcepath = os.path.join(config.get('base'), 'archive', config.get('obscode'))
    db = config.get('primaryDB')
    outpath = config.get('outpath',"/tmp")

    if runmode == 'secondrun':
        scinstlist.append("{}_0001".format(config.get('mobileinst')))

    #### If a testdate is provided (single day)
    tdate = None
    if testdate:
        #extract date and month
        tdate = datetime.strptime(testdate,"%Y-%m-%d")
        if not tdate.year == year:
            print ("Year not fitting - ignoring testdate")
            tdate = None
        else:
            startmonth = tdate.month-1
            endmonth = tdate.month

    f, dt = [],[]
    for i in range(startmonth,endmonth):
        # Extract time range (monthly junks)
        startyear = year
        nextyear = year
        month = str(i+1).zfill(2)
        if i == -1:
           startyear = year-1
           month = str(i+13).zfill(2)
        if i+1 >= 13:
            startyear = year+1
            month = str(i-11).zfill(2)
        nextmonth = str(i+2).zfill(2)
        if i+2 >= 13:
            nextyear = year+1
            nextmonth = str(i-10).zfill(2)

        for scinst in scinstlist:
            if debug:
                print ("-------------------------------------")
                print ("Running analysis for {}".format(scinst))
                print ("-------------------------------------")
                print ("Using Scalar data from path: {}".format(os.path.join(sourcepath,scinst[:-5],scinst,'*')))

            if not tdate:
                dstarttime=datetime.strptime(str(startyear)+'-'+month+'-01',"%Y-%m-%d")
                dendtime=datetime.strptime(str(nextyear)+'-'+nextmonth+'-01',"%Y-%m-%d")
            else:
                dstarttime=tdate
                dendtime=tdate+timedelta(days=1)
            if debug:
                print ("  Dealing with data between {} and {}".format(dstarttime,dendtime))

            try:
                sc = read(os.path.join(sourcepath,scinst[:-5],scinst,'*'),starttime=dstarttime,endtime=dendtime)
                # get header from db
                if debug:
                    print ("  Obtained {} data points".format(sc.length()[0]))
                # 2) Remove duplicates
                if debug:
                    print ("  Removing duplicates")
                bef = sc.length()[0]
                sc = sc.removeduplicates()
                aft = sc.length()[0]
                if debug:
                    print ("  -> dropped {} duplicate values".format(bef-aft))
                if sc.length()[0] > 1:
                    if debug:
                        print ("  Getting gaps and data base meta info:")
                    sc = sc.get_gaps()
                    sc.header = db.fields_to_dict(scinst)
                    # flag it
                    if debug:
                        print ("  Flagging with existing flags:")
                        print ("  a) from DB:")
                    flaglist = db.flags_from_db(scinst[:-5], starttime=dstarttime, endtime=dendtime) #data.header['SensorID'])
                    if debug:
                        print ("     Length of DB flaglist: {}".format(len(flaglist)))
                        print ("  b) from file:")
                    if not flagfile:
                        flagfile = os.path.join(outpath,'magpy',scinst[:-5]+'_flags.json')
                    if os.path.isfile(flagfile):
                        fileflaglist = flagging.load(flagfile, sensorid=sc.header.get('SensorID'), begin=dstarttime, end=dendtime)
                        if debug:
                            print("  Loaded {} flags from file in the time range {} to {}".format(len(fileflaglist),dstarttime, dendtime))
                        if len(flaglist) > 0 and len(fileflaglist) > 0:
                            flaglist = flaglist.join(fileflaglist)
                        elif not len(flaglist) > 0:
                            flaglist = fileflaglist
                    if debug:
                        print("  Found a sum of {} flags".format(len(flaglist)))
                    #sc.header["DataFlags"] = flaglist
                    if debug:
                        print ("  Removing flagged data before applying deltas and time shifting")
                    if flaglist:
                        sc = flaglist.apply_flags(sc, mode='drop')
                        sc.header["DataFlags"] = None
                    if debug:
                        print ("  Applying offsets and timeshifts")
                    sc = sc.apply_deltas()
                    if debug:
                        print ("  -> final length: {}".format(sc.length()[0]))
                    sc = sc.removeduplicates()
                    if debug:
                        print ("  -> final length after dupliacte removal: {}".format(sc.length()[0]))
                    if not runmode=='firstrun' and not skipsec:
                        hsc = sc.copy()
                        if debug:
                            print ("  Drop all columns except f and comments for high resolution storage")
                        for el in KEYLIST:
                            if not el in ['time','f','flag','comment']:
                                hsc = hsc._drop_column(el)
                        #print ("Resample to one second")   # Done in scalarcomb  -> resample deletes flags
                        #hsc = hsc.resample(['f','flag','comment'],period=1)
                        if debug:
                            print ("  Write monthly high resolution file with full info (length {}".format(hsc.length()[0]))
                        fname = '{}_scalar_oc_sec_{}'.format(scinst,runmode)
                        hsc.write(os.path.join(outpath,'magpy'),filenamebegins=fname,dateformat='%Y%m',coverage='month',mode='replace',format_type='PYCDF')
                    if debug:
                        print ("  Filtering")
                    sc = sc.filter(missingdata='mean')
                    if debug:
                        print ("  Fill gaps with nan")
                    sc = sc.get_gaps()
                    if debug:
                        print ("  Keeping only f column")
                    for el in KEYLIST:
                        if not el in ['time','f']:
                            sc = sc._drop_column(el)
                    #mp.plot(sc)
            except:
                pass

            if debug:
                print("  Writing data")
            fminname = '{}_scalar_oc_min_{}_{}'.format(scinst, runmode, year)
            sc.write(os.path.join(outpath, 'magpy'), filenamebegins=fminname, dateformat='%Y', coverage='all', mode='replace', format_type='PYCDF')
            if debug:
                print("Done")
                print("---------------------------")


def variocomb(runmode, config=None, debug=False):
    """
    DESCRIPTION
        create a merged variation file by filling gaps with secondary, teriary etc data sets
    """
    if not config:
        config = {}
        print ("No configuration data existing")
        return

    outpath = config.get('outpath',"/tmp")

    print (" ---------------------------------------------------- ")
    print (" --- Combining Variometer data and merging with F --- ")
    print (" ---------------------------------------------------- ")
    year = config.get('year')
    vainstlist = config.get('vainstlist')

    print ("Dealing with minute data for {}".format(year))
    refmin = DataStream()
    if runmode in ['secondrun','thirdrun']:
        writedefinitive = True
    else:
        writedefinitive = False
    for idx,vainst in enumerate(vainstlist):
        if runmode in ['firstrun']:
            fname = '{}_vario_cbmin_{}.cdf'.format(vainst, year)
        else:
            fname = '{}_vario_blmin_{}_{}.cdf'.format(vainst,runmode,year)
        if idx == 0:
                print ("-------------------------------------")
                print ("Base data: {}".format(vainst))
                print ("-------------------------------------")
                refmin = read(os.path.join(os.path.join(outpath,'magpy',fname)))
                print ("Got {} data points in reference min file".format(refmin.length()[0]))
                refmin = refmin.bc()
                if not refmin.header.get('DataAbsFunctionObject') and runmode == 'firstrun':
                    print ("  Firstrun: baseline has already been applied in simplebaseline adoption")
                print ("Baseline corrected")
                refmin = refmin._drop_column('t1')
                refmin = refmin._drop_column('t2')
                refmin = refmin._drop_column('var1')
                refmin = refmin._drop_column('var2')
                refmin = refmin._drop_column('var5')
                refmin = refmin._drop_column('str1')
                print ("Drop line with nan values")
                refmin = refmin._drop_nans('x')
                refmin = refmin._drop_nans('y')
                refmin = refmin._drop_nans('z')
        else:
                print ("-------------------------------------")
                print ("Adding data from {}".format(vainst))
                print ("-------------------------------------")
                addmin = read(os.path.join(os.path.join(outpath,'magpy',fname)))
                print ("Got {} data points in min file".format(addmin.length()[0]))
                addmin = addmin.bc()
                if not refmin.header.get('DataAbsFunctionObject') and runmode == 'firstrun':
                    print ("  Firstrun: baseline has already been applied in simplebaseline adoption")
                print ("Baseline corrected")
                addmin = addmin._drop_column('t1')
                addmin = addmin._drop_column('t2')
                addmin = addmin._drop_column('var1')
                addmin = addmin._drop_column('var2')
                addmin = addmin._drop_column('var5')
                addmin = addmin._drop_column('str1')
                print ("Drop line with nan values")
                addmin = addmin._drop_nans('x')
                addmin = addmin._drop_nans('y')
                addmin = addmin._drop_nans('z')
                print ("Merging timeseries")
                refmin = join_streams(refmin,addmin)
                print ("Reference now contains {} data points (min)".format(refmin.length()[0]))
    if refmin.length()[0] > 0:
        print ("Minute data combined")
        combminute = True
        refmin = refmin.get_gaps()
        refmin.write(os.path.join(outpath,'magpy'),filenamebegins='CobsV_min_{}_'.format(runmode),coverage='all',mode='overwrite',format_type='PYCDF')
    if writedefinitive:
        #read CobsF data if existing
        reff = read(os.path.join(os.path.join(outpath,'magpy','CobsF_min_{}*'.format(runmode))))
        if reff.length()[0] > 0:
            print ("Writing definitive one minute data")
            definitive = mergeStreams(refmin,reff, keys=['f'])
            #mp.plot(definitive)
            definitive.write(os.path.join(outpath,'magpy'),filenamebegins='Definitive_min_mag_{}_{}'.format(year,runmode),coverage='all',mode='overwrite',format_type='PYCDF')


def variocorr(runmode, config=None, startmonth=0, endmonth=12, skipsec=False, flagfile=None, basefile=None, debug=False):
    """
    DEFININTION:
        calculate variometer files with baseline and flagging information
    PARAMETER:
        runmode:  firstrun  -> xxx
                  secondrun ->
                  thidrun   ->
        skipsec: do not write second data files

    """
    if not config:
        config = {}
        print ("No configuartion data existing")
        return

    sourcepath = os.path.join(config.get('base'), 'archive', config.get('obscode'))
    db = config.get('primaryDB')
    outpath = config.get('outpath',"/tmp")

    if debug:
        print ("##########################################################")
        print (" ----------------------------------------------------------------------- ")
        print (" ----------------  Creating minute filtered variodata  ----------------- ")
        print (" -------------------  apply constant/true baseline       -------------------- ")
        print (" ----------------------------------------------------------------------- ")

    def update_rot(stream,year,alpha,beta=None):
            exist = stream.header.get('DataRotationAlpha','')
            if not exist == '':
                val = '{},{}_{}'.format(exist,year,alpha)
            else:
                val = '{}_{}'.format(year,alpha)
            stream.header['DataRotationAlpha'] = val
            if beta:
                exist = stream.header.get('DataRotationBeta','')
                if not exist == '':
                    val = '{},{}_{}'.format(exist,year,beta)
                else:
                    val = '{}_{}'.format(year,beta)
                stream.header['DataRotationBeta'] = val

    vainstlist = config.get('vainstlist',[])
    year = config.get('year')
    testdate = config.get('testdate',None)
    scinstlist = config.get('scinstlist')
    prf = scinstlist[0]
    rotangledict = {}

    #### If a testdate is provided (single day)
    tdate = None
    if testdate:
        #extract date and month
        tdate = methods.testtime(testdate)
        if not tdate.year == year:
            print ("Year not fitting - ignoring testdate")
            tdate = None
        else:
            startmonth = tdate.month-1
            endmonth = tdate.month

    #### READ MONTHLY ONE SECOND DATA
    for i in range(startmonth,endmonth):   # 0,12
        month = str(i+1).zfill(2)
        nextmonth = str(i+2).zfill(2)
        nextyear = year
        if nextmonth == '13':
            nextyear = year+1
            nextmonth = '01'
        for absidx,inst in enumerate(vainstlist):
            if debug:
                print ("-------------------------------------")
                print ("Running analysis for {}".format(inst))
                print ("  Using Variometer data from path: {}".format(os.path.join(sourcepath, inst[:-5], inst, '*')))

            if not tdate:
                dstarttime=datetime.strptime(str(year)+'-'+month+'-01',"%Y-%m-%d")
                dendtime=datetime.strptime(str(nextyear)+'-'+nextmonth+'-01',"%Y-%m-%d")
            else:
                dstarttime=tdate
                dendtime=tdate+timedelta(days=1)
            dstarttime = dstarttime.replace(tzinfo=None)
            dendtime = dendtime.replace(tzinfo=None)
            if debug:
                print ("  Dealing with data between {} and {}".format(dstarttime,dendtime))

            try:
                va = read(os.path.join(sourcepath, inst[:-5], inst, '*'),starttime=dstarttime,endtime=dendtime)
                # raw data
            except:
                va = DataStream()
            if debug:
                print ("  -> got {} datapoints".format(len(va)))
            if len(va) > 1:
                # 1) get header from db
                # ---------------------
                if debug:
                    print ("MEANS: {},{},{}".format(va.mean("x"),va.mean("y"),va.mean("z")))
                dhead = db.fields_to_dict(inst)
                if dhead:
                    va.header = dhead
                if va.header.get('SensorID','') == '':
                    va.header['SensorID'] = inst[:-5]
                # 2) Remove duplicates
                if debug:
                    print ("  Removing duplicates")
                bef = va.length()[0]
                va = va.removeduplicates()
                aft = va.length()[0]
                if debug:
                    print ("  -> dropped {} duplicate values".format(bef-aft))
                # 3) Fill gaps with nan
                if debug:
                    print ("  Filling gaps")
                va = va.get_gaps()
                # 4) flag data
                # ---------------------
                #  --a. add flaglist from db
                if debug:
                    print ("  Flagging")
                vaflagsdropped = False
                vaflaglist = db.flags_from_db(va.header['SensorID'], starttime=dstarttime, endtime=dendtime)
                if debug:
                    print("  Loaded {} flags from DB for this time range".format(len(vaflaglist)))
                #  --b. add flaglist from file
                if not flagfile:
                    flagfile = os.path.join(outpath,'magpy',inst[:-5]+'_flags.json')
                fileflaglist = flagging.load(flagfile, sensorid=va.header.get('SensorID'), begin=dstarttime, end=dendtime)
                if debug:
                    print("  Loaded {} flags from file in time range {} to {}".format(len(fileflaglist), dstarttime, dendtime))
                if len(vaflaglist) > 0 and len(fileflaglist) > 0:
                    vaflaglist = vaflaglist.join(fileflaglist)
                elif not len(vaflaglist) > 0:
                    vaflaglist = fileflaglist
                if debug:
                    print ("  Found a sum of {} flags".format(len(vaflaglist)))
                    print ("  Applying {} flags".format(len(vaflaglist)))
                va.header["DataFlags"] = vaflaglist
                #va = flaglist.apply_flags(va, mode='drop')
                ## Checkpoint
                #mp.plot(va,variables=['x','y','z'],annotate=True)
                if debug:
                    print ("   MEANS: {},{},{}".format(va.mean("x"),va.mean("y"),va.mean("z")))
                # 5) apply compensation
                # ---------------------
                if debug:
                    print("  Applying compensation values")
                va = va.compensation(skipdelta=True)
                if debug:
                    print ("   MEANS: {},{},{}".format(va.mean("x"),va.mean("y"),va.mean("z")))
                # 6) apply delta values
                # ---------------------
                if debug:
                    print("  Applying delta values")
                va = va.apply_deltas()
                # 7) determine and apply rotation
                # ---------------------
                if debug:
                    print("  Rotation values ...")   ### should be done after removal of flags....
                rotstring = va.header.get('DataRotationAlpha','')
                rotdict = string2dict(rotstring,typ='oldlist')
                if debug:
                    print ("  Existing rotation angle alpha for {}: {}".format(str(year), rotdict.get(str(year),'')))
                betastring = va.header.get('DataRotationBeta','')
                betadict = string2dict(betastring,typ='oldlist')
                if debug:
                    print ("  Existing rotation angle beta for {}: {}".format(str(year), betadict.get(str(year),'')))
                if runmode == 'firstrun' or rotdict.get(str(year),0) == 0:
                    print (" Initial run: Rotation value will be determined")
                    print ("   Need to drop flagged data now...")
                    if vaflaglist and not vaflagsdropped:
                        va = vaflaglist.apply_flags(va, mode='drop')
                        va.header['DataFlags'] = None
                        vaflagsdropped = True
                    print ("   Getting rotation angle - please note: correct beta determination requires DI data for reference inclination")
                    alpha, beta, gamma = va.determine_rotationangles(referenceD=0.0, referenceI=None)
                    rotangle = alpha
                    print ("  Determined rotation angle alpha for {}: {}".format(va.header.get('SensorID'),rotangle))
                    print ("  !!! Please note: These  new rotation angles are not yet applied.")
                    print ("  !!! Please note: They are used for secondrun onwards.")
                    print ("  !!! Please note: update DB with correct rotation angles. ")
                else:
                    rotangle = float(rotdict.get(str(year),'0.0'))
                    beta = float(betadict.get(str(year),'0.0'))
                    print("  Applying rotation (after firstrun): Using rotation angles alpha= {} and beta={}".format(rotangle, beta))
                    # Only apply full year values - as baseline calc uses them as well
                    va = va.rotation(alpha=rotangle, beta=beta)
                orgva = va.copy()

                if debug:
                    print ("   MEANS: {},{},{}".format(va.mean("x"),va.mean("y"),va.mean("z")))
                # 8) calc baseline
                # ---------------------
                # requirement: base value data has been cleaned up
                basename = ""
                ppier = config.get('primarypier','A2')
                blvabb = config.get('blvabb')
                if debug:
                    print ("Getting basevalue data now (primary pier only):", basefile, inst, prf, ppier)
                if runmode in  ['firstrun']:
                    scalar = prf[:-5]
                    basename = "{}_{}_{}_{}_{}.txt".format(blvabb, inst[:-5], scalar, ppier, year)
                elif runmode in ['secondrun','thirdrun']:
                    scalar = prf[:-5]
                    basename = "{}_{}_{}_{}_{}_{}.txt".format(blvabb, inst[:-5], scalar, ppier, year, runmode)
                    #basename = 'BLVcomp_'+inst[:-5]+'_'+scalar+'_A2_'+str(year)+'_'+runmode+'.txt'
                if not basefile:
                    basevaluefile = os.path.join(outpath,'magpy',basename)
                else:
                    basevaluefile = basefile

                if debug:
                    print ("  Applying baseline file: {}".format(basevaluefile))
                if os.path.isfile(basevaluefile):
                    absr = read(basevaluefile)
                    flaglist = absr.header.get("DataFlags")
                    if flaglist:
                        absr = flaglist.apply_flags(absr, mode='drop')
                    if debug:
                        print ("  Basevalue SensorID:", absr.header.get('DataID'))
                        print ("   -- Dropping basedata flags from DB")
                    blvflaglist = db.flags_from_db(absr.header.get('DataID'))
                    if debug:
                        print ("   -> {} flags".format(len(blvflaglist)))
                    if flaglist:
                        absr = flaglist.apply_flags(absr, mode='drop')
                    if debug:
                        print ("   -- Dropping basedata flags from file")
                    flaglist = flagging.load( config.get('diflagfile',''), sensorid=absr.header.get('DataID'))
                    if debug:
                        print ("   -> {} flags".format(len(flaglist)))
                    if flaglist:
                        absr = flaglist.apply_flags(absr, mode='drop')

                    # Checkpoint
                    #mp.plot(absr)
                    if runmode == 'firstrun':
                        if vaflaglist and not vaflagsdropped:
                            print("  Baseline adoption: dropping flagged data")
                            va = vaflaglist.apply_flags(va, mode='drop')
                            vaflagsdropped = True
                        va = va.get_gaps()
                        print ("  Filtering data")
                        va = va.filter(missingdata='mean')
                        # Checkpoint
                        #mp.plot(va,variables=['x','y','z'])
                        va = va.get_gaps()
                        print ("  Length after gaps removal (min):", va.length()[0])
                        #### GET CONSTANT BASEVALUE
                        print ("  Trimming basevalue file to get mean value")
                        bl = 'cbmin'
                        if str(year) == '2021' and inst == 'LEMI036_2_0001_0002' and i >= 6:
                            absr = absr.trim(starttime=str(year)+'-07-08',endtime=str(year+1)+'-01-01')
                        elif str(year) == '2021' and inst == 'LEMI036_2_0001_0002' and i < 6:
                            print ("....here")
                            absr = absr.trim(starttime=str(year)+'-01-01',endtime=str(year+1)+'-06-30')
                        else:
                            absr = absr.trim(starttime=str(year)+'-01-01',endtime=str(year+1)+'-01-01')
                        print (" -> remaining DI measurements: ", absr.length())
                        absr = absr._drop_nans('dx')
                        bh, bhstd = absr.mean('dx',meanfunction='median',std=True)
                        bd, bdstd = absr.mean('dy',meanfunction='median',std=True)
                        bz, bzstd = absr.mean('dz',meanfunction='median',std=True)

                        print (" Basevalues for {}:".format(year))
                        print (" Delta H = {a} +/- {b}".format(a=bh, b=bhstd))
                        print (" Delta D = {a} +/- {b}".format(a=bd, b=bdstd))
                        print (" Delta Z = {a} +/- {b}".format(a=bz, b=bzstd))

                        print ("  Performing constant basevalue correction")
                        va = va.simplebasevalue2stream([bh,bd,bz])
                    else:
                        bl = 'blmin_{}'.format(runmode)
                        ### TODO the steps below require that basevalues are already calculated with a corrected data set
                        print("Determining baseline")
                        starttime = str(year-1)+'-12-01'
                        endtime = str(year+1)+'-02-01'
                        funclist = []
                        # What about a baseline jump i.e. two or more baseline fits ?
                        # get timeranges and baseline fit parameters from database
                        print (" -> getting baseline fit parameter from database")
                        ett = methods.testtime(endtime)

                        while ett > methods.testtime(starttime):
                            baselst = db.get_baseline(va.header.get('SensorID',''),date=ett)
                            if methods.testtime(baselst[1][0]) < methods.testtime(starttime):
                                 stt = starttime
                            else:
                                 stt = datetime.strftime(methods.testtime(baselst[1][0]),"%Y-%m-%d")
                            if methods.testtime(baselst[2][0]) > methods.testtime(endtime):
                                 ett = endtime
                            else:
                                 ett = datetime.strftime(methods.testtime(baselst[2][0]),"%Y-%m-%d")
                            print (" => Adding fit with typ {}, knots {}, degree {} between {} and {}".format(baselst[4][0], float(baselst[6][0]), float(baselst[5][0]),stt, ett))
                            try:
                                funclist.append(va.baseline(absr, extradays=0, fitfunc=baselst[4][0], knotstep=float(baselst[6][0]), fitdegree=float(baselst[5][0]),startabs=stt,endabs=ett))
                                print (" => Done")
                            except:
                                print (" => Failed to add baseline parameters")
                            ett = methods.testtime(baselst[1][0])-timedelta(days=1)

                    print ("  AbsInfo in stream: {}".format(va.header.get('DataAbsInfo')))
                    if debug:
                        print("   MEANS: {},{},{}".format(va.mean("x"), va.mean("y"), va.mean("z")))

                    if runmode in ['secondrun','thirdrun'] and not skipsec: # Save high res data when finishing
                        hva = va.copy()
                        print ("  Updating rotation information...")
                        update_rot(hva,year,rotangle, beta) ## new 2017
                        #hva = hva.resample(keys=['x','y','z','t1','t2','var2','flag','comment'], period=1)
                        print ("  Write monthly high resolution file with full info")
                        fname = '{}_vario_sec_{}_'.format(inst,runmode)
                        hva.write(os.path.join(outpath,'magpy'),filenamebegins=fname,dateformat='%Y%m',coverage='month',mode='replace',format_type='PYCDF')
                    print("  remove, gaps and filter:", va.length()[0])
                    if vaflaglist and not vaflagsdropped:
                        va = vaflaglist.apply_flags(va, mode='drop')
                        vaflagsdropped = True
                    #print(va.length())
                    if not runmode == 'firstrun':
                        va = va.get_gaps()
                        va = va.filter(missingdata='mean')
                    va = va.get_gaps()
                    if debug:
                        print ("  Absolute data has now been loaded and applied - determining true beta now")
                        print ("  Get reference Inclination for the specific month:")
                    redabsr = absr.trim(starttime=dstarttime,endtime=dendtime)
                    meanI = redabsr.mean('x')
                    if debug:
                        print ("  Mean inclination in abs data = {}".format(meanI))
                    alpha, beta, gamma = orgva.determine_rotationangles(referenceI=meanI)

                    if rotangledict.get(inst,[]) == []:
                        rotangledict[inst] = [[alpha,beta]]
                    else:
                        rotangledict[inst].append([alpha,beta])

                    if debug:
                        print ("  Writing")
                    if debug:
                        print("   MEANS: {},{},{}".format(va.mean("x"), va.mean("y"), va.mean("z")))
                    if va.length()[0] > 0:
                        va.write(os.path.join(outpath,'magpy'), filenamebegins=inst+'_vario_'+bl+'_'+str(year),dateformat='%Y',mode='replace',coverage='all',format_type='PYCDF')
                else:
                    print (" !!! Basevalue file not existing")


    print ("----------------------------------------------------------")
    print ("Variometer data analyzed and filtered for months {} until first of {}".format(startmonth+1, endmonth+1))
    print ("Runmode: {}".format(runmode))
    print ("Rotation angles: {}".format(rotangledict))
    for inst in vainstlist:
        print ("Extracting rotation for variometer {}".format(inst))
        rotanglelist = rotangledict.get(inst,[])
        if len(rotanglelist) == 2:
            try:
                meanrotangle = np.nanmean(rotanglelist,axis=0)
            except:
                meanrotangle = np.mean(rotanglelist,axis=0)
            print (" -> Average rotation angle for {}: alpha={}, beta={}".format(inst,meanrotangle[0],meanrotangle[1]))
    print ("----------------------------------------------------------")
    print ("##########################################################")
    return rotangledict



class TestDefinitive(unittest.TestCase):
    """
    Test environment for all methods
    """

    def test_variocorr(self):
        runmode ="firstrun"
        config = mm.get_conf(os.path.join('..', 'conf', 'basevalue.cfg'))
        config['dbcredentials'] = "cobsdb"
        startdate, enddate = None, "2025-12-31"
        varios, scalars, piers = ["LEMI036_1_0002_0002","FGE_S0252_0002_0002"],["GP20S3NSS2_012201_0001_0001"],["A2"]
        config = basevalue.check_conf(config, startdate, enddate, varios=varios, scalars=scalars, piers=piers, debug=True)
        config['blvdatapath'] = "/tmp"
        config['base'] = os.path.abspath("../test")
        config['obscode'] = "WIC"
        config['didatapath'] = os.path.abspath("../test/archive/WIC/DI/analyze")
        config['blvabb'] = "BLV"
        config['testdate'] = "2025-05-14"
        basefile = os.path.join('..', 'test', 'archive', 'WIC', 'DI', 'data', 'BLVcomp_LEMI036_1_0002_GP20S3NSS2_012201_0001_A2.txt')
        rotangledict = variocorr(runmode, config=config, startmonth=0, endmonth=12, skipsec=False, basefile=basefile, debug=True)
        print ("RESULT", rotangledict)
        self.assertTrue(rotangledict)
        us = create_rotation_sql(rotangledict,config=config)
        print ("RESULT", us)
        self.assertTrue(us)

    def test_scalarcorr(self):
        runmode ="firstrun"
        config = mm.get_conf(os.path.join('..', 'conf', 'basevalue.cfg'))
        config['dbcredentials'] = "cobsdb"
        startdate, enddate = None, "2025-12-31"
        varios, scalars, piers = ["LEMI036_1_0002_0002"],["GP20S3NSS2_012201_0001_0001"],["A2"]
        config = basevalue.check_conf(config, startdate, enddate, varios=varios, scalars=scalars, piers=piers, debug=True)
        config['blvdatapath'] = "/tmp"
        config['base'] = os.path.abspath("../test")
        config['obscode'] = "WIC"
        config['didatapath'] = os.path.abspath("../test/archive/WIC/DI/analyze")
        config['blvabb'] = "BLV"
        config['testdate'] = "2025-05-14"
        scalarcorr(runmode, config=config, startmonth=0, endmonth=12, skipsec=False, debug=True)
        t = False
        if os.path.isfile("/tmp/magpy/GP20S3NSS2_012201_0001_0001_scalar_oc_min_firstrun_2025.cdf"):
            t = True
        self.assertTrue(t)

    def test_variocomb(self):
        runmode ="firstrun"
        config = mm.get_conf(os.path.join('..', 'conf', 'basevalue.cfg'))
        config['dbcredentials'] = "cobsdb"
        startdate, enddate = None, "2025-12-31"
        varios, scalars, piers = ["LEMI036_1_0002_0002","FGE_S0252_0002_0002"],["GP20S3NSS2_012201_0001_0001"],["A2"]
        config = basevalue.check_conf(config, startdate, enddate, varios=varios, scalars=scalars, piers=piers, debug=True)
        config['obscode'] = "WIC"
        variocomb(runmode, config=config, debug=True)
        t = False
        if os.path.isfile("/tmp/magpy/CobsV_min_firstrun_.cdf"):
            t = True
        self.assertTrue(t)

    def test_scalarcomb(self):
        runmode ="firstrun"
        config = mm.get_conf(os.path.join('..', 'conf', 'basevalue.cfg'))
        config['dbcredentials'] = "cobsdb"
        startdate, enddate = None, "2025-12-31"
        varios, scalars, piers = ["LEMI036_1_0002_0002","FGE_S0252_0002_0002"],["GP20S3NSS2_012201_0001_0001"],["A2"]
        config = basevalue.check_conf(config, startdate, enddate, varios=varios, scalars=scalars, piers=piers, debug=True)
        config['obscode'] = "WIC"
        scalarcomb(runmode, config=config, debug=True)
        t = False
        if os.path.isfile("/tmp/magpy/CobsF_min_firstrun.cdf"):
            t = True
        self.assertTrue(t)

    def test_pier_diff(self):
        runmode ="firstrun"
        config = mm.get_conf(os.path.join('..', 'conf', 'basevalue.cfg'))
        config['dbcredentials'] = "cobsdb"
        startdate, enddate = None, "2025-12-31"
        varios, scalars, piers = ["LEMI036_1_0002_0002","FGE_S0252_0002_0002"],["GP20S3NSS2_012201_0001_0001"],["A2"]
        config = basevalue.check_conf(config, startdate, enddate, varios=varios, scalars=scalars, piers=piers, debug=True)
        config['obscode'] = "WIC"
        sqllist = pier_diff(runmode, config=config, debug=False)
        print (sqllist)
        #self.assertTrue(sqllist)


if __name__ == "__main__":
    unittest.main(verbosity=2)