// customize settings for smoothiechart

function myYRangeFunction(range) {
    return {min:range.min-3, max:range.max+3};
};

const streamtosettings = { Delay : 500 }; 
/*
const smoothiesettings = {  interpolation:'linear', 
                            yRangeFunction:myYRangeFunction, 
                            responsive: true};
                            // TODO warum geht das nicht mehr - wie ging es?:
                            //timestampFormatter:SmoothieChart.timeFormatter};
*/
const smoothiesettings = {  yRangeFunction:myYRangeFunction,
                            //timestampFormatter:SmoothieChart.timeFormatter};
                         };

const timeseriessettings = { lineWidth:1, strokeStyle:'#fff900' };


/* optional functions

function makeCanvas(signalid) {
    if (signalid == 'AD7714_0001_0001#0') {
        var someplaceforcanvas = document.getElementById('maindiv');
        var canvas = document.createElement('canvas');
        canvas.width = "1000";
        canvas.height = "500";
        someplaceforcanvas.appendChild(canvas);
        return canvas;
    }else{
        return false;
    }
 }

function makeDescrField(signalid,signals) {
    var someplacefordescription = document.getElementById('debug');
    someplacefordescription.innerHTML = 'some other description '+signals[signalid].unit;
}

*/
