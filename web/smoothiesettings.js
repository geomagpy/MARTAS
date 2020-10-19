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

                            //   minValue: undefined,        // specify to clamp the lower y-axis to a given value
                            //   maxValue: undefined,        // specify to clamp the upper y-axis to a given value
                            //   maxValueScale: 1,           // allows proportional padding to be added above the$
                            //   yRangeFunction: undefined,  // function({min: , max: }) { return {min: , max: };$
                            //   scaleSmoothing: 0.125,      // controls the rate at which y-value zoom animation$
                            //   millisPerPixel: 20         // sets the speed at which the chart pans by
                            //   maxDataSetLength: 2,
                            //   interpolation: 'bezier'     // one of 'bezier', 'linear', or 'step'
                            //   timestampFormatter: null,   // Optional function to format time stamps for botto$
                            //   horizontalLines: [],        // [ { value: 0, color: '#ffffff', lineWidth: 1 } ],
*/
const smoothiesettings = {  yRangeFunction:myYRangeFunction, millisPerPixel: 200 };

const timeseriessettings = { lineWidth:2, strokeStyle:'#fff900' };


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
