// TODO make a class out of it , use jquery...
// plot magpy data coming over websocket from collector

    var serveraddr= location.host.split(':')[0];
    console.log(serveraddr);
    var wsconnection = new WebSocket('ws://' +serveraddr+ ':5000/');
    var signals = {};
    var descrFields = {};
    var table;
    var smoothieloaded = 0;

    console.log("plotws.js started");

// "import" smoothiechart javascripts
//    var importsmoothie = document.createElement('script');
//    importsmoothie.src = 'smoothie.js';
//    document.head.appendChild(importsmoothie);
//    var importsmoothiesettings = document.createElement('script');
//    importsmoothiesettings.src = 'smoothiesettings.js';
//    document.head.appendChild(importsmoothiesettings);

// Modidied import by leon May 2018
// https://stackoverflow.com/questions/950087/how-do-i-include-a-javascript-file-in-another-javascript-file
// Modified import my rmandl Sept 2018, importJs launches the nextFunction, when a js-File is loaded
// smoothieloaded will be 1, when both files are loaded

    function jsImport(toBeLoaded, nextFunction) {
        var importJs = document.createElement('script');
        importJs.src = toBeLoaded;
        // bind the event to callback (nextFunction)
        //importJs.onreadystatechange = nextFunction; // don't need that here(?)
        importJs.onload = nextFunction;
        // Fire loading
        document.head.appendChild(importJs);
    }

    var smoothieLoaded = function () {
        smoothieloaded = 1;
    }

    var loadSmoothie = function () {
        jsImport('smoothie.js', smoothieLoaded);
    }

    jsImport('smoothiesettings.js',loadSmoothie);

    function getCanvas(signalid) {
        try {
            canvas = makeCanvas(signalid);
            row = null;
        }
        catch (e) {
            canvas = null;
        }
        // default is table in maindiv, or we get a canvas from somewhere else
        if (canvas == null) {
            var row = document.createElement('tr');
            table.appendChild(row);
            var cell = document.createElement('td');
            row.appendChild(cell);
            var canvas = document.createElement('canvas');
            // TODO replace arbitrary number by settings or derive from screen width etc.
            canvas.width = "1000";
            cell.appendChild(canvas);
        }
        return [canvas,row];
    }

    function getDescrField(signalid,row) {
        try {
            descrField = makeDescrField(signalid,signals);
        }
        catch (e) {
            // only if canvas was created by default
            if (row) {
                // a new cell in the table
                var descrField = document.createElement('td');
                row.appendChild(descrField);
                descrFields[signalid] = descrField;
                iH = signals[signalid];
                descrField.innerHTML = iH.sensorid +'<BR>'+ iH.key +' : '+ iH.elem +' ['+ signals[signalid].unit +']';
            }
        }
        return descrField;
    }


    function addChart(signalid) {
        var [canvas,row] = getCanvas(signalid);
        // if there is a non default selection, other signals are not shown
        if (canvas) {
            var descrField = getDescrField(signalid,row);
            var chart = {};
            chart.smoothie = new SmoothieChart(smoothiesettings);
            chart.timeSeries = new TimeSeries();
            chart.smoothie.addTimeSeries(chart.timeSeries,timeseriessettings);
            chart.smoothie.streamTo(canvas,streamtosettings.Delay);
            return chart;
        }
    };


    wsconnection.onmessage = function (e) {
        if (e.data[0] == '#') {
            // header
            // # json
            var data = e.data.split('# ')[1];
            var head = JSON.parse(data);
            signalid = head.sensorid + '#' + head.nr;
            if (signals[signalid] == null && smoothieloaded == 1) {
                // new header
                signals[signalid] = head;
                signals[signalid].chart = addChart(signalid);
                // result might look like:
                // { sensorid: "AD7714_0001_0001", nr: 0, unit: "mV", elem: "U", key: "var1", chart: Object }
                console.log('new header: sensor ' + signals[signalid].sensorid);
                //debug.innerHTML = 'new header: sensor ' + signals[signalid].sensorid;
            }
        } else {
            // data
            // sensorid: timestamp,data0,data1...
            var data = e.data.split(': ');
            var sensor = data[0];
            if (signals[sensor+'#0'] == null) {
                // no header yet
            } else {
                var data_arr = data[1].split(',');
                for (i=0; i < data_arr.length-1; i++) {
                    var signalid = sensor +'#'+ i.toString();
                    // catch not selected signals in non default mode
                    try {
                        signals[signalid].chart.timeSeries.append((data_arr[0]),Number(data_arr[i+1]));
                        var mydate = new Date(Number(data_arr[0]));
                        debug.innerHTML = mydate.toString()+'  '+data_arr.slice(1);
			iH = signals[signalid];
			text = iH.sensorid +'<BR>'+ iH.key +' : '+ iH.elem +' ['+ signals[signalid].unit +']<BR>';
			text = text + data_arr[1+i] + ' ' + signals[signalid].unit;
                        descrFields[signalid].innerHTML = text;

                    }
                    catch (e) {}
                    //debug.innerHTML = data_arr[i+1];
                }
            }
        }
        // console.log('data from collector: ' + e.data);
    };
    wsconnection.onopen = function (){
        console.log('websocket connection open');
    };
    wsconnection.onerror = function (error){
        console.log('error: ' + error);
        connection.close();
    };

window.onload = function() {

    var maindiv = document.getElementById('maindiv');
    // TODO no need for a table, when no default
    table = document.createElement('table');
    maindiv.appendChild(table);

    debug1 = document.getElementById('debug');
}
