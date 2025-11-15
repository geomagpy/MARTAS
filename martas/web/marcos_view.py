#!/usr/bin/env python

from magpy.stream import *
from martas.core import methods as mm
from martas.version import __version__
from dash import Dash, html, dash_table, dcc, Output, Input
import dash_daq as daq
from plotly.subplots import make_subplots
from martas.app.monitor import _latestfile
import random
from crontab import CronTab
import psutil
from pathlib import Path
import numpy as np

"""
DESCRIPTION:
a visual summary of a MARCOS server contains:
- table of sensorIDs plus datatables and actuality
  i.e. LEMI025_22_0004   |     | _0001 (green), _0002(green) |  location: StationID, PierID
- collect processes (list of collector processes) and health state
  i.e. PROMETHEUS |  status  | sensorA (green), sensorB (green) | location: StationID, PierID 
- collect external data source data actuality (list of collector processes) and health state
  i.e. GOES17 |  green |  dataset  | source location 
- a general health state section
  i.e. MARCOS on, essential jobs on green, secondary jobs on green, SUCCESS in all scheduled jobs
  accessibility of Hohe Warte
- status of scheduler and time to next job running
- Status Lamps for important thresholds
- local storage space (gauge)
- selection of three timeseries live plots with component selection
- group, type, element selector with current values (LED) and activity status


Required packages
dash
plotly
pip install dash_daq
"""
# Configuration information
mainpath = os.path.dirname(os.path.realpath(__file__))
configpath = os.path.join(mainpath,"..","conf","archive.cfg")

statusdict = {"archive" : {"space" : 400, "used": 150, "cronenabled": False, "active": False, "logstatus":False },
              "monitor" : {"space" : 100, "used": 100, "cronenabled": False, "active": False, "logstatus":False },
              "database" : {"space" : 300, "used": 250, "cronenabled": False, "active": False, "logstatus":False }
              }


def get_datainfo_from_db(cred='cobsdb', debug=False):
    """
    DESCRIPTION
        select all datatables from database, check DATAINFO, check contents
    RETURNS
        dictionary with DataID, SensorID, datatable ok, DATAINFO ok, last input, first input, StationID, PierID
    """

    db = mm.connect_db(cred, False, False)
    if db:
        dbd = statusdict.get('database')
        dbd['active'] = True
        statusdict['database'] = dbd

    def _analyse_columns(colsstr,unitsstr):
        usedkeys, components, counits = [],[],[]
        cols, units = [], []
        if colsstr:
            cols = colsstr.split(",")
        if unitsstr:
            units = unitsstr.split(",")
        allkeys = DataStream().KEYLIST
        for i,co in enumerate(cols):
            if co:
                components.append(co)
                if len(units)>=i:
                   counits.append(units[i])
                usedkeys.append(allkeys[i+1])
        return usedkeys, components, counits

    def _get_column_names(tablename):
        keys = []
        sql = "SELECT * FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = '{}'".format(tablename)
        cursor = db.db.cursor()
        msg = db._executesql(cursor, sql)
        n = cursor.fetchall()
        for l in n:
            keys.append(l[3])
        # drop time column and only return keys with more then time
        if len(keys) > 1:
            return keys[1:]
        else:
            return []

    # Check whether DB still available
    result = {}
    missingdatainfo = []
    now = datetime.now(timezone.utc).replace(tzinfo=None)

    if db:
        output = db.select('DataID,SensorID,StationID,ColumnContents,ColumnUnits,DataPier', 'DATAINFO')
        for elem in output:
            #print ("Columns", elem[3],elem[4])
            usedkeys, components, units = _analyse_columns(elem[3],elem[4])
            result[elem[0]] = {"SensorID":elem[1],"StationID":elem[2],"PierID":elem[5],"DataKeys":usedkeys,"DataElements":components,"DataUnits":units,"TableExists":False,"DataInfoExists":True,"FirstInput":None,"LastInput":None,"Actual":0}
        sql = "SHOW TABLES"
        cursor = db.db.cursor()
        msg = db._executesql(cursor, sql)
        n = cursor.fetchall()
        for elem in n:
            tablename = elem[0]
            if tablename.count("_") == 3:
                #follows the naming convention of MagPy
                cont = result.get(tablename, None)
                if cont:
                    cont["TableExists"] = True
                    result[tablename] = cont
                else:
                    missingdatainfo.append(tablename)
        for elem in missingdatainfo:
            # Get columns of existing data
            keys = _get_column_names(elem)
            if len(keys) > 0:
                result[elem] = {"SensorID":elem[:-5],"StationID":"","PierID":"","DataKeys":keys,"TableExists":True,"DataInfoExists":False,"FirstInput":None,"LastInput":None,"Actual":0}
            else:
                if debug:
                    print("ERROR with table {}: no data keys".format(elem))

        # Update start and enddate for all DataID
        for elem in result:
            cont = result.get(elem)
            #print (elem)
            if cont.get("TableExists"):
                try:
                    l = db.get_lines(elem, 1)
                    cont['LastInput'] = l.end()
                    diff = (now - l.end()).total_seconds()
                    if diff < 3600: # Threshold corresponds to maximal graph range - only those can be plotted
                        cont["Actual"] = 2
                    elif diff < 87000: # data younger then 1 day
                        cont["Actual"] = 1
                    cont['TimeDiff'] = diff
                    result[elem] = cont
                except:
                    if debug:
                        print ("ERROR with get_lines in table {}".format(elem))
                    pass

        if debug:
            print ("Summary", result)
        return result


def convert_datainfo_to_datatable(result, debug=False):
    """
    DESCRIPTION
        converts results dictionary into a Table for display
    """
    if not result:
        result = {}
    table = []
    dtable = []
    sidtab = []
    for elem in result:
        cont = result.get(elem)
        sid = cont.get("SensorID")
        did = elem[-5:]
        if sid in sidtab:
            line = [s for s in table if s[0] == sid][0]
            if debug:
                print ("found existing line", line)
            if cont.get("Actual") > line[1]:
                line[1] = cont.get("Actual")
            line[2].append(did)
        else:
            table.append([sid, cont.get("Actual"), [did], cont.get("StationID"), cont.get("PierID")])
        sidtab.append(sid)

    for line in table:
        dtable.append({"SensorID" : line[0], "Actual" : line[1], "DataIDs" : ",".join(line[2]), "StationID" : line[3], "PierID" : line[4]})
    dcols = ["SensorID", "Actual", "DataIDs", "StationID", "PierID"]
    return dtable, dcols


def convert_datainfo_to_idtable(result, debug=False):
    """
    DESCRIPTION
        converts results dictionary into a Table for display
    """
    dtable = []
    for elem in result:
        cont = result.get(elem)
        comps = cont.get("DataElements",[])
        if len(comps) > 8:
            comps = comps[:8]
            comps.append("...")
        comps = ",".join(comps)
        dtable.append({"DataID" : elem, "in DATAINFO" : str(cont.get("DataInfoExists")), "Data table" : str(cont.get("TableExists")), "Actual" : cont.get("Actual"), "Components" : comps})
    dcols = ["DataID", "in DATAINFO", "Data table", "Actual", "Components"]
    return dtable, dcols


def get_graph_options(result, actualcrit=1):
    """
    DESCRIPTION
        get a list of actual sensors for dropdown and available keys/elements for plotting
    """
    if not result:
        result = {}
    dataoptions = []
    datavalue = None
    for elem in result:
        cont = result.get(elem)
        actual = cont.get("Actual")
        if actual >= actualcrit:
            dataoptions.append(elem)
    if len(dataoptions) > 0:
        datavalue = random.choice(dataoptions)
    return dataoptions, datavalue


def get_graph_keys(tablename, result):
    """
    DESCRIPTION
        get a list of keys for dropdown selection
    """
    keyoptions = [] # for datavalue
    keyvalue = None # for datavalue
    if not tablename:
        return [],""

    cont = result.get(tablename)
    opt = []
    keys = cont.get("DataKeys",[])
    choice = random.choice(keys)
    units = cont.get("DataUnits",[])
    comps = cont.get("DataElements",[])
    for i,key in enumerate(keys):
        if len(comps) > 0 and len(comps) >= i and len(units) >= i and units[i]:
            label = "{} [{}]".format(comps[i], units[i])
        elif len(comps) > 0 and len(comps) >= i:
            label = "{}".format(comps[i])
        else:
            label = "{}".format(key)
        opt.append({'label': label, "value":key })
    keyoptions = opt
    keyvalue = choice

    return keyoptions, keyvalue


def get_data(datatable, keys, datainfo=None, duration=60, cred="cobsdb"):
    mydata = {}
    names = []
    db = mm.connect_db(cred, False, False)
    # This job needs including trim needs about 1 sec on my comp
    stream = db.get_lines(datatable, 36000)
    endtime = stream.timerange()[1]
    stream = stream.trim(starttime=endtime-timedelta(minutes=duration), endtime=endtime)
    mydata['time'] = stream.ndarray[0]
    for key in keys:
        name = key
        #name = stream.get_key_name(key) # get name from results
        mydata[name] = stream._get_column(key)
        names.append(name)
    return mydata, names


# slow methods
def getspace(path="/srv"): # path = '/srv'
    """
    DESCRIPTION
        get space from monitor
    """
    statvfs = os.statvfs(path)
    total = (statvfs.f_frsize * statvfs.f_blocks / (1024.*1024.))     # Size of filesystem in bytes
    remain = (statvfs.f_frsize * statvfs.f_bavail / (1024.*1024.))     # Number of free bytes that ordinary users
    usedper=100-(remain/total*100.)
    used = total-remain
    return total, used


def get_storage_usage(statusdict=None, cred="cobsdb", archivepath="", logpath="", debug=False):
    if not statusdict:
        statusdict = {}
    txt = ""
    dbused = 0
    db = mm.connect_db(cred, False, False)
    if db:
        txt = db.info(destination='stdout', level='full')
    if txt:
        dbused = txt.split()[-1]
    dbmax = 30.0 # should be smaller than 30GB
    atotal, aused = 0, 0
    mtotal, mused = 0, 0
    if archivepath:
        if os.path.exists(archivepath):
            atotal, aused = getspace(path=archivepath)
    if logpath:
        logpath = os.path.dirname(logpath)
        if os.path.exists(logpath):
            mtotal, mused = getspace(path=logpath)
    ad = statusdict.get('archive',{})
    if ad:
        ad["space"] = np.round(atotal/1000.,0)
        ad["used"] = np.round(aused/1000.,0)
    md = statusdict.get('monitor',{})
    if md:
        md["space"] = np.round(mtotal/1000.,0)
        md["used"] = np.round(mused/1000.,0)
    if debug:
        print ("SPACE", atotal, aused)
        print("SPACE", mtotal, mused)
    dd = statusdict.get('database',{})
    if dd:
        dd["space"] = dbmax
        dd["used"] = float(dbused)
    return statusdict


def get_pid(name):
    pid = 0
    for proc in psutil.process_iter(attrs=["pid", "name", "exe", "cmdline"]):
        if isinstance(proc.info.get('cmdline'), (list,tuple)):
            for cmd in proc.info.get('cmdline'):
                if name in cmd:
                    pid = proc.pid
                    break
            if pid:
                break
    return pid


def get_cron_jobs(statusdict=None,cred="cobsdb", archivepath="", logpath="",debug=False):
    """
    DESCRIPTION
        get active Cron jobs once per minute
    """
    if not statusdict:
        statusdict = {}

    statusdict = get_storage_usage(statusdict, cred=cred, archivepath=archivepath, logpath=logpath, debug=False)
    crontable = []
    marcoslist = []

    mycron = CronTab(user=True)
    for job in mycron:
        if debug:
            print ("Testing job:", job)
        comm = job.comment
        cand = job.command
        en = job.is_enabled()
        cl = cand.split()
        if comm.find("Running MARCOS") >= 0:
            logstatus = False
            active = False
            k = comm.replace("Running MARCOS process ","")
            pidname = Path(cl[2]).stem
            if debug:
                print ("Testing pid", pidname)
            p = get_pid(pidname)
            if debug:
                print (" - got pid", p)
            if p > 0:
                active = True
            for el in cl:
                if el.find(".log") >= 0:
                    te = el.split("/")
                    if debug:
                        print ("Found MARCOS job", te)
                    try:
                        ctime = os.path.getctime(el)
                        ctime = datetime.fromtimestamp(ctime)
                        logstatus = True
                    except:
                        pass
            statusdict[k] = {"cronenabled": en, "active": active, "logstatus": logstatus}
            marcoslist.append(k)
        else:
            logstatus = False
            active = False
            jobcommand = cl[1]
            lf = ""
            ctime = ""
            if len(jobcommand) < 3:
                jobcommand = cl[2]
            jc = jobcommand.split("/")[-1]
            for el in cl:
                if el.find(".log") >= 0:
                    te = el.split("/")
                    if debug:
                        print ("Found basic cron job", te)
                    try:
                        ctime = os.path.getctime(el)
                        ctime = datetime.fromtimestamp(ctime)
                        logstatus = True
                        if ctime > datetime.now()-timedelta(days=8):
                            active = True
                        ctime = ctime.strftime("%Y-%m-%dT%H:%M:%S")
                        jn = jc.split(".")[0]
                        if jn in ["archive", "monitor"]:
                            jnstat = statusdict.get(jn,{})
                            jnstat["cronenabled"] = en
                            jnstat["active"] = active
                            jnstat["logstatus"] = logstatus
                            statusdict[jn] = jnstat
                        elif jn in ["db_truncate"]:
                            dbstat = statusdict.get("database",{})
                            dbstat["cronenabled"] = en
                            dbstat["logstatus"] = logstatus
                            statusdict["database"] = dbstat
                    except:
                        pass
                    lf = te[-1]
            resd = {"job" : jc, "enabled":str(en), "logfile":lf, "last log":ctime}
            crontable.append(resd)
    croncols = ["job", "enabled", "logfile", "last log"]

    return crontable, croncols, marcoslist


def get_marcos_html(marcos,i):
    htmllist = []
    oncolor = '#008003'
    offcolor = '#FF5E5E'
    acolor = offcolor
    ecolor = offcolor
    lcolor = offcolor
    if statusdict[marcos].get('active'):
        acolor = oncolor
    if statusdict[marcos].get('cronenabled'):
        ecolor = oncolor
    if statusdict[marcos].get('logstatus'):
        lcolor = oncolor
    htmllist.append(html.Div([
        daq.Indicator(id='marcos{}active'.format(i), value=True, color=acolor,
                      style={"float": "left", "margin-right": "10px"}),
        html.B("{}".format(marcos)),
    ]))
    htmllist.append(html.Div([
        daq.Indicator(id='marcos{}enabled'.format(i), value=True, color=ecolor,
                      style={"float": "left", "margin-right": "10px"}),
        html.P("cron enabled"),
    ]))
    htmllist.append(html.Div([
        daq.Indicator(id='marcos{}log'.format(i), value=True, color=lcolor,
                      style={"float": "left", "margin-right": "10px"}),
        html.P("log status"),
    ]))
    return htmllist

# Read configuration data and initialize amount of plots
cfg = mm.get_conf(configpath)
archivepath = cfg.get('archivepath')
logpath = cfg.get('logpath')
dbcred = cfg.get('dbcredentials')

test = False
if test:
    print(cfg)
    archivepath = "/srv"
    logpath = "/home/leon/.martas/log"
    dbcred = 'cobsdb'

# Initialize basic result dictionary (fast interval, graph and table)
result = get_datainfo_from_db(cred=dbcred)
dtable, dcols = convert_datainfo_to_datatable(result)
dataoptions, datavalue = get_graph_options(result)
keyoptions, keyvalue = get_graph_keys(datavalue, result)

# Initialize status dictionary (slow interval, diskspace, cron and processes)
crontable, croncols, marcoslist = get_cron_jobs(statusdict=statusdict, cred=dbcred, archivepath=archivepath, logpath=logpath,debug=False)

app = Dash(__name__, assets_ignore='martas.css')

app.layout = (html.Div(
                 className="mwrap",
                 children=[
                              html.Div(
                                  className="mbox ma",
                                  children=html.Div([
                                      html.Img(src='/assets/header.png',style={'width': '60%'}),
                                      ])
                              ),
                              html.Div(
                                  className="mbox mb",
                                  children=html.Div([
                                      html.Div(id='live-update-marcos1')
                                      ])
                              ),
                              html.Div(
                                  className="mbox mc",
                                  children=html.Div([
                                      html.Div(id='live-update-marcos2')
                                      ])
                              ),
                              html.Div(
                                  className="mbox md",
                                  children=html.Div([
                                      html.Div(id='live-update-marcos3')
                                      ])
                              ),
                              html.Div(
                                  className="mbox me",
                                  children=html.Div([
                                      html.Div(id='live-update-marcos4')
                                      ])
                              ),
                              html.Div(
                                  className="mbox mf",
                                  children=html.Div([
                                      html.Div(id='live-update-marcos5')
                                      ])
                              ),
                              html.Div(
                                  className="mbox mg",
                                  children=html.Div([
                                      html.Div(id='live-update-marcos6')
                                      ])
                              ),
                              html.Div(
                                  className="mbox mh",
                                  children=html.Div([
                                      html.Div(id='live-update-marcos7')
                                      ])
                              ),
                             html.Div(
                                 className="mbox mi",
                                 children=html.Div([
                                     html.P('Time coverage (minutes):'),
                                     dcc.Slider(id='durationslider', min=5, max=60, step=5, value=10,
                                                marks={x: str(x) for x in [10, 20, 30, 40, 50, 60]}),
                                     html.P('Height of the graph display (px):'),
                                     dcc.Slider(id='heightslider', min=200, max=1000, step=25, value=450,
                                                marks={x: str(x) for x in [200, 400, 600, 800, 1000]}),
                                 ])
                             ),
                             html.Div(
                                  className="mbox mj",
                                  children=html.Div([
                                      html.Div(id='live-update-dbstatus')
                                      ])
                              ),
                              html.Div(
                                  className="mbox mk",
                                  children=html.Div([
                                      html.Div(id='live-update-monitorstatus')
                                      ])
                              ),
                              html.Div(
                                  className="mbox ml",
                                  children=html.Div([
                                      html.Div(id='live-update-archivestatus')
                                      ])
                              ),
                              html.Div(
                                  className="mbox mm",
                                  children=html.Div([
                                      daq.Gauge(
                                          id='db-gauge',
                                          units="GB",
                                          size=120,
                                          color={"gradient": True,
                                                 "ranges": {"green": [0, statusdict['database'].get('space')*0.6], "yellow": [statusdict['database'].get('space')*0.6, statusdict['database'].get('space')*0.8], "red": [statusdict['database'].get('space')*0.8, statusdict['database'].get('space')]}},
                                          value=statusdict['database'].get('used'),
                                          label='DB storage',
                                          max=statusdict['database'].get('space'),
                                          min=0,
                                      ),
                                      dcc.Interval(
                                          id='gauge-update',
                                          interval=60 * 1000,  # in milliseconds
                                          n_intervals=0
                                      )
                                  ])
                              ),
                              html.Div(
                                  className="mbox mn",
                                  children=html.Div([
                                    daq.Gauge(
                                        id='base-gauge',
                                        size=120,
                                        color={"gradient": True,
                                               "ranges": {"green": [0, statusdict['monitor'].get('space') * 0.8],
                                                          "yellow": [statusdict['monitor'].get('space') * 0.8,
                                                                     statusdict['monitor'].get('space') * 0.9],
                                                          "red": [statusdict['monitor'].get('space') * 0.9,
                                                                  statusdict['monitor'].get('space')]}},
                                        value=statusdict['monitor'].get('used'),
                                        label='Base',
                                        max=statusdict['monitor'].get('space'),
                                        min=0,
                                    )
                                      ])
                              ),
                              html.Div(
                                  className="mbox mo",
                                  children=html.Div([
                                      daq.Gauge(
                                          id='archive-gauge',
                                          size=120,
                                          color={"gradient": True,
                                                 "ranges": {"green": [0, statusdict['archive'].get('space') * 0.8],
                                                            "yellow": [statusdict['archive'].get('space') * 0.8,
                                                                       statusdict['archive'].get('space') * 0.9],
                                                            "red": [statusdict['archive'].get('space') * 0.9,
                                                                    statusdict['archive'].get('space')]}},
                                          value=statusdict['archive'].get('used'),
                                          label='Archive',
                                          max=statusdict['archive'].get('space'),
                                          min=0,
                                      )
                                      ])
                              ),
                              html.Div(
                                  className='mbox mp',
                                  children=html.Div([
                                      html.Div([dcc.Dropdown(dataoptions, datavalue, id='data-dropdown'),
                                                dcc.Dropdown(keyoptions, keyvalue, id='key-dropdown')], style={"width": "50%"}),
                                      dcc.Graph(id='live-graph', animate=False),
                                      dcc.Interval(
                                          id='graph-update',
                                          interval=5 * 1000,  # in milliseconds
                                          n_intervals=0
                                      )
                                  ])
                              ),
                              html.Div(
                                  className="mbox mq",
                                  children=html.Div([
                                      dash_table.DataTable(crontable,
                                                           columns=[{'id': c, 'name': c} for c in croncols],
                                                           sort_action='native',
                                                           fixed_rows={'headers': True},
                                                           style_cell={'minWidth': 95, 'width': 95, 'maxWidth': 95, 'padding': '5px'},
                                                           style_table={'height': 300},  # default is 500
                                                           style_cell_conditional=[
                                                               {
                                                                   'if': {'column_id': c},
                                                                   'textAlign': 'left'
                                                               } for c in ['job','enabled']
                                                           ],
                                                           style_data={
                                                               'whiteSpace': 'normal',
                                                               'color': 'rgb(230, 230, 250)',
                                                               'fontSize': '14px',
                                                               'backgroundColor': 'rgb(112, 128, 144)'
                                                           },
                                                           style_data_conditional=[
                                                               {
                                                                   'if': {'row_index': 'odd'},
                                                                   'backgroundColor': 'rgb(119, 149, 163)',
                                                               },
                                                               {
                                                                   'if': {
                                                                       'filter_query': '{enabled} = False',
                                                                       'column_id': 'enabled'
                                                                   },
                                                                   'backgroundColor': '#eaf044',
                                                                   'color': 'black'
                                                               },
                                                           ],
                                                           style_header={
                                                               'backgroundColor': '#4D4D4D',
                                                               'color': 'rgb(230, 230, 250)',
                                                               'fontWeight': 'bold',
                                                               'fontSize': '16px',
                                                               'border': '1px solid black'
                                                           },
                                                           ),

                                  ])
                              ),
                             html.Div(
                                 className="mbox mr",
                                 children=html.Div([
                                     dcc.Dropdown(['Sensors', 'Data records'], 'Sensors', id='sensor-dropdown' , style={"width": "50%"}),
                                     dash_table.DataTable(data=dtable,
                                                          id='sensors-table',
                                                          sort_action='native',
                                                          columns=[{'id': c, 'name': c} for c in dcols],
                                                          fixed_rows={'headers': True},
                                                          style_cell={'minWidth': 95, 'width': 95, 'maxWidth': 95, 'padding': '5px'},
                                                          style_table={'height': 150},  # default is 500
                                                          style_cell_conditional=[
                                                                {
                                                                    'if': {'column_id': c},
                                                                    'textAlign': 'left'
                                                                } for c in ['DataID', 'SensorID', 'Actual']
                                                          ],
                                                          style_data={
                                                              'color': 'rgb(230, 230, 250)',
                                                              'fontSize': '14px',
                                                              'backgroundColor': 'rgb(112, 128, 144)'
                                                          },
                                                          style_data_conditional=[
                                                              {
                                                                  'if': {'row_index': 'odd'},
                                                                  'backgroundColor': 'rgb(119, 149, 163)',
                                                              },
                                                              {
                                                                  'if': {
                                                                      'filter_query': '{Data table} = False',
                                                                      'column_id': 'Data table'
                                                                  },
                                                                  'backgroundColor': '#eaf044',
                                                                  'color': 'black'
                                                              },
                                                              {
                                                                  'if': {
                                                                      'filter_query': '{Actual} < 1',
                                                                      'column_id': 'Actual'
                                                                  },
                                                                  'backgroundColor': 'tomato'
                                                              },
                                                              {
                                                                  'if': {
                                                                      'filter_query': '{in DATAINFO} = False',
                                                                      'column_id': 'in DATAINFO'
                                                                  },
                                                                  'backgroundColor': 'tomato'
                                                              },
                                                          ],
                                                          style_header={
                                                              'backgroundColor': '#4D4D4D',
                                                              'color': 'rgb(230, 230, 250)',
                                                              'fontWeight': 'bold',
                                                              'fontSize': '16px',
                                                              'border': '1px solid black'
                                                          }
                                                          ),
                                 ])
                             ),
                             html.Div(
                                 className="mbox mt",
                                 children=html.Div([
                                     html.H4('Configuration'),
                                     html.Div(id='live-update-config')
                                 ])
                             ),
                             html.Div(
                                 className="mbox mu",
                                 children=html.Div([
                                     html.B('MARCOS (MagPys automatic real-time collection and organization system)'),
                                     html.P('Version {}'.format(__version__)),
                                     html.P('written by R. Leonhardt, R. Bailey, R. Mandl'),
                                     html.P(['MARTAS on GitHUB:', html.A('click here', href='https://github.com/geomagpy/MARTAS')]),
                                     html.P(['MagPY on GitHUB:',
                                                 html.A('click here', href='https://github.com/geomagpy/geomagpy')]),
                                 ])
                             ),
                 ]
            )
)


@app.callback(Output('live-update-config', 'children'),
              Input('gauge-update', 'n_intervals'))
def update_config(n):
    style = {'padding': '5px', 'fontSize': '16px'}
    crontable, croncols, marcoslist = get_cron_jobs(cred=dbcred, archivepath=archivepath,
                                                     logpath=logpath, debug=False)
    pos = {}
    htmllist = []
    cfg = mm.get_conf(configpath)
    #print (cfg)
    htmllist.append(html.P(['Amount of MARCOS jobs: {}'.format(len(marcoslist))]))
    htmllist.append(html.P(['Archivepath: {}'.format(archivepath)]))
    htmllist.append(html.P(['Download jobs: ']))
    return htmllist


@app.callback(Output('live-update-archivestatus', 'children'),
              Input('gauge-update', 'n_intervals'))
def update_archive_status(n):
    htmllist = []
    oncolor = '#008003'
    offcolor = '#FF5E5E'
    acolor = offcolor
    ecolor = offcolor
    lcolor = offcolor
    if statusdict['archive'].get('active'):
        acolor = oncolor
    if statusdict['archive'].get('cronenabled'):
        ecolor = oncolor
    if statusdict['archive'].get('logstatus'):
        lcolor = oncolor
    htmllist.append(html.Div([
        daq.Indicator(id='archiveactive', value=True, color=acolor,
                      style={"float": "left", "margin-right": "10px"}),
        html.P("archive active"),
    ]))
    htmllist.append(html.Div([
        daq.Indicator(id='archiveenabled', value=True, color=ecolor,
                      style={"float": "left", "margin-right": "10px"}),
        html.P("cron enabled"),
    ]))
    htmllist.append(html.Div([
        daq.Indicator(id='archivelog', value=True, color=lcolor,
                      style={"float": "left", "margin-right": "10px"}),
        html.P("log status"),
    ]))
    return htmllist


@app.callback(Output('live-update-monitorstatus', 'children'),
              Input('gauge-update', 'n_intervals'))
def update_monitor_status(n):
    htmllist = []
    oncolor = '#008003'
    offcolor = '#FF5E5E'
    acolor = offcolor
    ecolor = offcolor
    lcolor = offcolor
    if statusdict['monitor'].get('active'):
        acolor = oncolor
    if statusdict['monitor'].get('cronenabled'):
        ecolor = oncolor
    if statusdict['monitor'].get('logstatus'):
        lcolor = oncolor
    htmllist.append(html.Div([
        daq.Indicator(id='monitoractive', value=True, color=acolor,
                      style={"float": "left", "margin-right": "10px"}),
        html.P("monitor active"),
    ]))
    htmllist.append(html.Div([
        daq.Indicator(id='monitorenabled', value=True, color=ecolor,
                      style={"float": "left", "margin-right": "10px"}),
        html.P("cron enabled"),
    ]))
    htmllist.append(html.Div([
        daq.Indicator(id='monitorlog', value=True, color=lcolor,
                      style={"float": "left", "margin-right": "10px"}),
        html.P("log status"),
    ]))
    return htmllist


@app.callback(Output('live-update-dbstatus', 'children'),
              Input('gauge-update', 'n_intervals'))
def update_db_status(n):
    htmllist = []
    oncolor = '#008003'
    offcolor = '#FF5E5E'
    acolor = offcolor
    ecolor = offcolor
    lcolor = offcolor
    if statusdict['database'].get('active'):
        acolor = oncolor
    if statusdict['database'].get('cronenabled'):
        ecolor = oncolor
    if statusdict['database'].get('logstatus'):
        lcolor = oncolor
    htmllist.append(html.Div([
        daq.Indicator(id='dbactive', value=True, color=acolor,
                      style={"float": "left", "margin-right": "10px"}),
        html.P("database active"),
    ]))
    htmllist.append(html.Div([
        daq.Indicator(id='dbenabled', value=True, color=ecolor,
                      style={"float": "left", "margin-right": "10px"}),
        html.P("cron enabled"),
    ]))
    htmllist.append(html.Div([
        daq.Indicator(id='dblog', value=True, color=lcolor,
                      style={"float": "left", "margin-right": "10px"}),
        html.P("log status"),
    ]))
    return htmllist


@app.callback(Output('live-update-marcos1', 'children'),
              Input('gauge-update', 'n_intervals'))
def update_marcos1_status(n):
    htmllist=[]
    if len(marcoslist) > 0:
        m = marcoslist[0]
        htmllist = get_marcos_html(m, 1)
    else:
        htmllist.append(html.P(['empty MARCOS slot']))
    return htmllist

@app.callback(Output('live-update-marcos2', 'children'),
              Input('gauge-update', 'n_intervals'))
def update_marcos2_status(n):
    htmllist=[]
    if len(marcoslist) > 1:
        m = marcoslist[1]
        htmllist = get_marcos_html(m, 2)
    else:
        htmllist.append(html.P(['empty slot']))
    return htmllist

@app.callback(Output('live-update-marcos3', 'children'),
              Input('gauge-update', 'n_intervals'))
def update_marcos3_status(n):
    htmllist=[]
    if len(marcoslist) > 2:
        m = marcoslist[2]
        htmllist = get_marcos_html(m, 3)
    else:
        htmllist.append(html.P(['empty slot']))
    return htmllist

@app.callback(Output('live-update-marcos4', 'children'),
              Input('gauge-update', 'n_intervals'))
def update_marcos4_status(n):
    htmllist=[]
    if len(marcoslist) > 3:
        m = marcoslist[3]
        htmllist = get_marcos_html(m, 4)
    else:
        htmllist.append(html.P(['empty slot']))
    return htmllist

@app.callback(Output('live-update-marcos5', 'children'),
              Input('gauge-update', 'n_intervals'))
def update_marcos5_status(n):
    htmllist=[]
    # get_cron...
    if len(marcoslist) > 4:
        m = marcoslist[4]
        htmllist = get_marcos_html(m, 5)
    else:
        htmllist.append(html.P(['empty slot']))
    return htmllist

@app.callback(Output('live-update-marcos6', 'children'),
              Input('gauge-update', 'n_intervals'))
def update_marcos6_status(n):
    htmllist=[]
    if len(marcoslist) > 5:
        m = marcoslist[5]
        htmllist = get_marcos_html(m, 6)
    else:
        htmllist.append(html.P(['empty slot']))
    return htmllist

@app.callback(Output('live-update-marcos7', 'children'),
              Input('gauge-update', 'n_intervals'))
def update_marcos7_status(n):
    htmllist=[]
    if len(marcoslist) > 6:
        m = marcoslist[6]
        htmllist = get_marcos_html(m, 7)
    else:
        htmllist.append(html.P(['empty slot']))
    return htmllist


@app.callback(Output('key-dropdown', 'options'),
              Output('key-dropdown', 'value'),
              Input('data-dropdown', 'value'))
def update_keydrop(datavalue):
    result = get_datainfo_from_db(cred=dbcred)
    keyoptions, keyvalue = get_graph_keys(datavalue, result)
    return keyoptions, keyvalue


@app.callback(Output('sensors-table', 'data'),Output('sensors-table', 'columns'),
              Input('sensor-dropdown', 'value'))
def update_table_update(datavalue):
    if datavalue.startswith("Sensor"):
        dtable, dcols = convert_datainfo_to_datatable(result)
    else:
        dtable, dcols = convert_datainfo_to_idtable(result)
    cols = [{'id': c, 'name': c} for c in dcols]
    return dtable, cols


@app.callback(
    Output('live-graph', 'figure'),
    Input('graph-update', 'n_intervals'),
    Input('heightslider', 'value'),
    Input('durationslider', 'value'),
    Input('data-dropdown', 'value'),
    Input('key-dropdown', 'value'),
    prevent_initial_call=True
)
def update_graph(n, hvalue, duration, datavalue, keyvalue):
    # read data
    #print ("Get available data sets")
    result = get_datainfo_from_db(cred=dbcred)

    data, names = get_data(datavalue, [keyvalue], datainfo=result, duration=duration, cred=dbcred)
    fig = make_subplots(rows=len(names), cols=1, vertical_spacing=0.1)
    fig.update_layout(
        plot_bgcolor='#4D4D4D',
        paper_bgcolor='#EDE9E8',
    )
    fig.update_xaxes(
        mirror=True,
        ticks='outside',
        showline=True,
        linecolor='black',
        gridcolor='lightgrey'
    )
    fig.update_yaxes(
        mirror=True,
        ticks='outside',
        showline=True,
        linecolor='black',
        gridcolor='lightgrey'
    )
    fig['layout']['margin'] = {
        'l': 20, 'r': 10, 'b': 10, 't': 10
    }
    fig['layout']['legend'] = {'x': 0, 'y': 1, 'xanchor': 'left'}
    fig.update_layout(height=int(hvalue))

    i = 0
    for name in names:
            i += 1
            fig.add_trace({
                'x': data['time'],
                'y': data[name],
                'name': name,
                'mode': 'lines+markers',
                'type': 'scatter'
            }, i, 1)

    return fig

if __name__ == '__main__':
    app.run(host="0.0.0.0", debug=True)
