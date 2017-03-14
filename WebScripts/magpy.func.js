// ##########################################
// TODO: - Cleanup the event1Cnt variable
//       - Check the remote control functions
// ##########################################
   
         var event1Cnt = 0;
         var event2Cnt = 0;

         // define session variables
         for (var inst in sensors) {
             eval("sess_"+client+" = null;");
             eval("var eventcnt_"+client+"_"+inst+" = null;");
             for (var par in parameters) {
                 eval("var "+par+"_"+client+"_"+inst+" = null;");
                 eval("var line_"+par+"_"+client+"_"+inst+" = new TimeSeries();");
                 eval("var "+par+"_"+client+"_"+inst+"_last = null;");
             }
         }

         // Function for y range in plot
         function myYRangeFunction(range) {
            // TODO implement your calculation using range.min and range.max
            var diff = Math.abs(range.max - range.min); 
            var min = range.min - 3; // - diff*0.05;
            var max = range.max + 3; // + diff*0.05;
            return {min: min, max: max};
            }


         function getClientname(str) {
            var re = str.split("/");
            return re[3];
            }

         function getSensorname(str) {
            var re = str.split("/");
            return re[4].split("#")[1].split("-")[0];
            }


         function createCanvas(sensors) {
             var tab=document.createElement('table');
             tab.setAttribute('id','graphtable');
             tab.className="mytable";
             var tbo=document.createElement('tbody');
             var row, cell, canvastag;
             var nrRows = 4;
             var nrCols = 2;
             for (var inst in sensors) {
                     for (var comp in components) {
                          if (comp == inst) {
                              var str = components[comp];
                              var complst = str.split(",");
                          }
                     };
                     for (var i=0; i<complst.length; i++) {
                         // get the unit:
                         var unit;
                         for (var c in parameters) {
                              if (c == complst[i]) {
                                   unit = parameters[c];
                              };
                         }; 
                         row=document.createElement('tr');
	     	         cell=document.createElement('td');
                         var label = sensors[inst]+": "+complst[i].toUpperCase()+"["+unit+"]";
                         cell.appendChild(document.createTextNode(label));
                         row.appendChild(cell);
  		         cell=document.createElement('td');
              	         canvastag = document.createElement('canvas');
                         if (complst.length < 2) {
		              canvastag.id = "mycanvas_"+inst;
                         } else {
		              canvastag.id = "mycanvas_"+inst+complst[i];
                         };
		         canvastag.width="1000";
                         canvastag.height="150";
		         cell.appendChild(canvastag);
                         row.appendChild(cell);
               	         tbo.appendChild(row);
                     }
             }
             tab.appendChild(tbo);
             return tab;
         }

         function createTable(sensors) {
             var tab=document.createElement('table');
             tab.setAttribute('id','datatable');
             tab.className="mytable";
             var tbo=document.createElement('tbody');
             var row, cell, spantag;
             var nrRows = 4;
             var nrCols = 2;
             row=document.createElement('tr');
             cell=document.createElement('th');
             cell.appendChild(document.createTextNode('SensorID'));
             row.appendChild(cell);
             cell=document.createElement('th');
             cell.appendChild(document.createTextNode('Sensor'));
             row.appendChild(cell);
             //cell=document.createElement('th');
             //cell.appendChild(document.createTextNode('Time'));
             //row.appendChild(cell);
             for (var par in parameters) {
                cell=document.createElement('th');
	        cell.appendChild(document.createTextNode(par));
                row.appendChild(cell);
             	}
             tbo.appendChild(row);
             for(var inst in sensors) {
	         row=document.createElement('tr');
                 cell=document.createElement('td');
		 cell.appendChild(document.createTextNode(inst));
		 row.appendChild(cell);
                 cell=document.createElement('td');
		 cell.appendChild(document.createTextNode(sensors[inst]));
		 row.appendChild(cell);
                 for (var par in parameters) {
                     cell=document.createElement('td');
                     spantag = document.createElement('span');
                     spantag.id = par+"_"+client+"_"+inst;
                     spantag.appendChild(document.createTextNode('-'));
                     cell.appendChild(spantag);
		     row.appendChild(cell);
                 }
	         tbo.appendChild(row);
             }
             tab.appendChild(tbo);
             return tab;
         }

         function hideDetails(divid) {
            document.getElementById(divid).style.display='none';
         }

         function showDetails(divid) {
            document.getElementById(divid).style.display='';
         }

         function controlLed(status) {
            sess.call("rpc:control-led", status).always(ab.log);
         }

         function sendCommand(command) {
            sess.call("rpc:send-command", command).always(ab.log);
         }

         function updateEventCnt() {
            document.getElementById("event1-cnt").innerHTML = Math.round(event1Cnt/eventCntUpdateInterval) + " events/s";
            document.getElementById("event2-cnt").innerHTML = Math.round(event2Cnt/eventCntUpdateInterval) + " events/s";
            event1Cnt = 0;
            event2Cnt = 0;
         }

         function connect() {

            statusline = document.getElementById('statusline');
            
            sess = new ab.Session(wsuri,
               function() {

                  statusline.innerHTML = "Connected to " + wsuri;
                  retryCount = 0;

                  sess.prefix("event", "http://example.com/"+client+"/ow#");
                  for (var inst in sensors) {
                      sess.subscribe("event:"+inst+"-value", onOwValue);
                  }

                  sess.prefix("event", "http://example.com/"+client+"/cs#");
                  for (var inst in sensors) {
                      if (inst.substring(0,3) == "G82") {
                          sess.subscribe("event:"+inst+"-value", onCsValue);
                      }
                  }
                  //sess.subscribe("eventcs:cs2-value", onCsValue);

                  sess.prefix("event", "http://example.com/"+client+"/env#");
                  for (var inst in sensors) {
                      if (inst.substring(0,3) == "ENV") {
                          sess.subscribe("event:"+inst+"-value", onEnvValue);
                      }
                  }

                  sess.prefix("event", "http://example.com/"+client+"/kern#");
                  for (var inst in sensors) {
                      if (inst.substring(0,3) == "KER") {
                          sess.subscribe("event:"+inst+"-value", onKerValue);
                      }
                  }

                  sess.prefix("event", "http://example.com/"+client+"/pal#");
                  for (var inst in sensors) {
                      if (inst.substring(0,3) == "PAL") {
                          sess.subscribe("event:"+inst+"-value", onPalValue);
                      }
                  }

                  sess.prefix("event", "http://example.com/"+client+"/ard#");
                  for (var inst in sensors) {
                      if (inst.substring(0,3) == "ARD") {
                          sess.subscribe("event:"+inst+"-value", onArdValue);
                      }
                  }

                  sess.prefix("event", "http://example.com/"+client+"/lemi#");
                  for (var inst in sensors) {
                      if (inst.substring(0,3) == "LEM") {
                          sess.subscribe("event:"+inst+"-value", onLemiValue);
                      }
                  }

                  sess.prefix("event", "http://example.com/"+client+"/pos1#");
                  for (var inst in sensors) {
                      if (inst.substring(0,3) == "POS") {
                          sess.subscribe("event:"+inst+"-value", onPosValue);
                      }
                  }

                  sess.prefix("event", "http://example.com/"+client+"/gsm#");
                  for (var inst in sensors) {
                      if (inst.substring(0,3) == "GSM") {
                          sess.subscribe("event:"+inst+"-value", onGSMValue);
                      }
                  }

                  sess.prefix("event", "http://example.com/"+client+"/gn#");
                  eval("f_"+client+"_"+inst+".innerHTML = 'hello';");
                  for (var inst in sensors) {
                      if (inst.substring(0,3) == "G19") {
                          sess.subscribe("event:"+inst+"-value", onG19Value);
                      }
                  }
                  
                  sess.prefix("event", "http://example.com/"+client+"/ad7#");
                  for (var inst in sensors) {
                      if (inst.substring(0,3) == "AD7") {
                          sess.subscribe("event:"+inst+"-value", onAD7Value);
                      }
                  }
                  
                  sess.prefix("event", "http://example.com/"+client+"/bm3#");
                  for (var inst in sensors) {
                      if (inst.substring(0,3) == "BM3") {
                          sess.subscribe("event:"+inst+"-value", onBM35Value);
                      }
                  }

                  sess.prefix("event", "http://example.com/"+client+"/sug#");
                  for (var inst in sensors) {
                      if (inst.substring(0,3) == "GP2") {
                          sess.subscribe("event:"+inst+"-value", onGPValue);
                      }
                  }

                  sess.prefix("rpc", "http://example.com/"+client+"/env1-control#");

                  event1Cnt = 0;
                  
                  window.setInterval(updateEventCnt, eventCntUpdateInterval * 1000);
               },
               function() {
                  console.log(retryCount);
                  retryCount = retryCount + 1;
                  statusline.innerHTML = "Connection lost. Reconnecting (" + retryCount + ") in " + retryDelay + " secs ..";
                  window.setTimeout(connect, retryDelay * 1000);
               }
            );

         }


         window.onload = function ()
         {
            document.getElementById('table1div').appendChild(createTable(sensors));
            document.getElementById('table2div').appendChild(createCanvas(sensors));
            document.getElementById('client').innerHTML = client;

            for (var inst in sensors) {
                for (var par in parameters) {
                    eval(par+"_"+client+"_"+inst+" = document.getElementById('"+par+"_"+client+"_"+inst+"');");
                }
            }

            for (var inst in sensors) {
                    for (var comp in components) {
                          var str = components[comp];
                          var complst = str.split(",");
                          if (complst.length < 2) {
                                   eval("var smoothie_"+inst+" = new SmoothieChart({grid: {strokeStyle: '#777777',fillStyle: '#253529',lineWidth: 0.2,millisPerLine: 10000, verticalSections: 10},labels: {fontSize: 15,fontFamily: 'sans-serif',precision: 1},timestampFormatter:SmoothieChart.timeFormatter,yRangeFunction:myYRangeFunction,millisPerPixel: xaxis,resetBounds: false,interpolation: 'bezier'});");
                                   }
                          else {
                                   for (var i=0; i<complst.length; i++) {
                                         eval("var smoothie_"+inst+complst[i]+" = new SmoothieChart({grid: {strokeStyle: '#777777',fillStyle: '#253529',lineWidth: 0.2,millisPerLine: 10000, verticalSections: 10},labels: {fontSize: 15,fontFamily: 'sans-serif',precision: 1},timestampFormatter:SmoothieChart.timeFormatter,yRangeFunction:myYRangeFunction,millisPerPixel: xaxis,resetBounds: false,interpolation: 'bezier'});");
                                         };
                                    }
                           }
		    };

            for (var inst in sensors) {
                if (inst.substring(0,3) == "ENV") {
                    eval("smoothie_"+inst+"t.addTimeSeries(line_ta_"+client+"_"+inst+", { strokeStyle: 'rgb(205,79,57)', fillStyle: 'rgba(205,79,57, 0.1)', lineWidth: 3 });");
                    eval("smoothie_"+inst+"t.addTimeSeries(line_tb_"+client+"_"+inst+", { strokeStyle: 'rgb(205,255,57)', fillStyle: 'rgba(205,255,57, 0.1)', lineWidth: 3 });");
                    eval("smoothie_"+inst+"rh.addTimeSeries(line_vara_"+client+"_"+inst+", { strokeStyle: 'rgb(171,130,255)', fillStyle: 'rgba(171,130,255, 0.3)', lineWidth: 3 });");
                    eval("smoothie_"+inst+"t.streamTo(document.getElementById('mycanvas_"+inst+"t'));");
                    eval("smoothie_"+inst+"rh.streamTo(document.getElementById('mycanvas_"+inst+"rh'));");
                }
                else if (inst.substring(0,3) == "POS") {
                    eval("smoothie_"+inst+".addTimeSeries(line_f_"+client+"_"+inst+", { strokeStyle: '	rgb(179, 68, 108)', fillStyle: 'rgba(179, 68, 108, 0.3)', lineWidth: 3 });");
                    eval("smoothie_"+inst+".streamTo(document.getElementById('mycanvas_"+inst+"'));");
                }
                else if (inst.substring(0,3) == "GSM") {
                    eval("smoothie_"+inst+".addTimeSeries(line_f_"+client+"_"+inst+", { strokeStyle: '	rgb(179, 68, 108)', fillStyle: 'rgba(179, 68, 108, 0.3)', lineWidth: 3 });");
                    eval("smoothie_"+inst+".streamTo(document.getElementById('mycanvas_"+inst+"'));");
                }
                else if (inst.substring(0,3) == "G19") {
                    eval("smoothie_"+inst+".addTimeSeries(line_f_"+client+"_"+inst+", { strokeStyle: '	rgb(179, 68, 108)', fillStyle: 'rgba(179, 68, 108, 0.3)', lineWidth: 3 });");
                    eval("smoothie_"+inst+".streamTo(document.getElementById('mycanvas_"+inst+"'));");
                }
                else if (inst.substring(0,3) == "BM3") {
                    eval("smoothie_"+inst+".addTimeSeries(line_varc_"+client+"_"+inst+", { strokeStyle: 'rgb(179, 68, 108)', fillStyle: 'rgba(179, 68, 108, 0.3)', lineWidth: 3 });");
                    eval("smoothie_"+inst+".streamTo(document.getElementById('mycanvas_"+inst+"'));");
                }
                else if (inst.substring(0,3) == "AD7") {
                    eval("smoothie_"+inst+".addTimeSeries(line_varc_"+client+"_"+inst+", { strokeStyle: 'rgb(179, 68, 108)', fillStyle: 'rgba(179, 68, 108, 0.3)', lineWidth: 3 });");
                    eval("smoothie_"+inst+".streamTo(document.getElementById('mycanvas_"+inst+"'));");
                }
                else if (inst.substring(0,3) == "KER") {
                    eval("smoothie_"+inst+".addTimeSeries(line_w_"+client+"_"+inst+", { strokeStyle: '	rgb(179, 68, 108)', fillStyle: 'rgba(179, 68, 108, 0.3)', lineWidth: 3 });");
                    eval("smoothie_"+inst+".streamTo(document.getElementById('mycanvas_"+inst+"'));");
                }
                else if (inst.substring(0,3) == "G82") {
                    eval("smoothie_"+inst+".addTimeSeries(line_f_"+client+"_"+inst+", { strokeStyle: '	rgb(179, 68, 108)', fillStyle: 'rgba(179, 68, 108, 0.3)', lineWidth: 3 });");
                    eval("smoothie_"+inst+".streamTo(document.getElementById('mycanvas_"+inst+"'));");
                }
                else if (inst.substring(0,3) == "ARD") {
                    eval("smoothie_"+inst+"x.addTimeSeries(line_x_"+client+"_"+inst+", { strokeStyle: 'rgb(205,79,57)', fillStyle: 'rgba(205,79,57, 0.1)', lineWidth: 3 });");
                    eval("smoothie_"+inst+"x.streamTo(document.getElementById('mycanvas_"+inst+"x'));");
                    eval("smoothie_"+inst+"y.addTimeSeries(line_y_"+client+"_"+inst+", { strokeStyle: 'rgb(205,255,57)', fillStyle: 'rgba(205,255,57, 0.1)', lineWidth: 3 });");
                    eval("smoothie_"+inst+"y.streamTo(document.getElementById('mycanvas_"+inst+"y'));");
                    eval("smoothie_"+inst+"z.addTimeSeries(line_z_"+client+"_"+inst+", { strokeStyle: 'rgb(171,130,255)', fillStyle: 'rgba(171,130,255, 0.1)', lineWidth: 3 });");
                    eval("smoothie_"+inst+"z.streamTo(document.getElementById('mycanvas_"+inst+"z'));");
                    eval("smoothie_"+inst+".addTimeSeries(line_t_"+client+"_"+inst+", { strokeStyle: 'rgb(205,79,57)', fillStyle: 'rgba(205,79,57, 0.3)', lineWidth: 3 });");
                    eval("smoothie_"+inst+".streamTo(document.getElementById('mycanvas_"+inst+"'));");
                }
                else if (inst.substring(0,3) == "PAL") {
                    eval("smoothie_"+inst+"x.addTimeSeries(line_x_"+client+"_"+inst+", { strokeStyle: 'rgb(205,79,57)', fillStyle: 'rgba(205,79,57, 0.1)', lineWidth: 3 });");
                    eval("smoothie_"+inst+"x.streamTo(document.getElementById('mycanvas_"+inst+"x'));");
                    eval("smoothie_"+inst+"y.addTimeSeries(line_y_"+client+"_"+inst+", { strokeStyle: 'rgb(205,255,57)', fillStyle: 'rgba(205,255,57, 0.1)', lineWidth: 3 });");
                    eval("smoothie_"+inst+"y.streamTo(document.getElementById('mycanvas_"+inst+"y'));");
                    eval("smoothie_"+inst+"z.addTimeSeries(line_z_"+client+"_"+inst+", { strokeStyle: 'rgb(171,130,255)', fillStyle: 'rgba(171,130,255, 0.1)', lineWidth: 3 });");
                    eval("smoothie_"+inst+"z.streamTo(document.getElementById('mycanvas_"+inst+"z'));");
                }
                else if (inst.substring(0,3) == "LEM") {
                    eval("smoothie_"+inst+"x.addTimeSeries(line_x_"+client+"_"+inst+", { strokeStyle: 'rgb(205,79,57)', fillStyle: 'rgba(205,79,57, 0.1)', lineWidth: 3 });");
                    eval("smoothie_"+inst+"x.streamTo(document.getElementById('mycanvas_"+inst+"x'));");
                    eval("smoothie_"+inst+"y.addTimeSeries(line_y_"+client+"_"+inst+", { strokeStyle: 'rgb(205,255,57)', fillStyle: 'rgba(205,255,57, 0.1)', lineWidth: 3 });");
                    eval("smoothie_"+inst+"y.streamTo(document.getElementById('mycanvas_"+inst+"y'));");
                    eval("smoothie_"+inst+"z.addTimeSeries(line_z_"+client+"_"+inst+", { strokeStyle: 'rgb(171,130,255)', fillStyle: 'rgba(171,130,255, 0.1)', lineWidth: 3 });");
                    eval("smoothie_"+inst+"z.streamTo(document.getElementById('mycanvas_"+inst+"z'));");
                    eval("smoothie_"+inst+"t.addTimeSeries(line_tb_"+client+"_"+inst+", { strokeStyle: 'rgb(255, 127, 80)', fillStyle: 'rgba(255, 127, 80, 0.1)', lineWidth: 3 });");
                    eval("smoothie_"+inst+"t.addTimeSeries(line_ta_"+client+"_"+inst+", { strokeStyle: 'rgb(245, 199, 26)', fillStyle: 'rgba(245, 199, 26, 0.1)', lineWidth: 3 });");
                    eval("smoothie_"+inst+"t.streamTo(document.getElementById('mycanvas_"+inst+"t'));");
                }
                else if (inst.substring(0,3) == "GP2") {
                    eval("smoothie_"+inst+"fa.addTimeSeries(line_fa_"+client+"_"+inst+", { strokeStyle: 'rgb(205,79,57)', fillStyle: 'rgba(205,79,57, 0.1)', lineWidth: 3 });");
                    eval("smoothie_"+inst+"fa.streamTo(document.getElementById('mycanvas_"+inst+"fa'));");
                    eval("smoothie_"+inst+"fb.addTimeSeries(line_fb_"+client+"_"+inst+", { strokeStyle: 'rgb(205,255,57)', fillStyle: 'rgba(205,255,57, 0.1)', lineWidth: 3 });");
                    eval("smoothie_"+inst+"fb.streamTo(document.getElementById('mycanvas_"+inst+"fb'));");
                    eval("smoothie_"+inst+"fc.addTimeSeries(line_fc_"+client+"_"+inst+", { strokeStyle: 'rgb(171,130,255)', fillStyle: 'rgba(171,130,255, 0.1)', lineWidth: 3 });");
                    eval("smoothie_"+inst+"fc.streamTo(document.getElementById('mycanvas_"+inst+"fc'));");
                    eval("smoothie_"+inst+"ga.addTimeSeries(line_ga_"+client+"_"+inst+", { strokeStyle: 'rgb(255, 127, 80)', fillStyle: 'rgba(255, 127, 80, 0.1)', lineWidth: 3 });");
                    eval("smoothie_"+inst+"ga.streamTo(document.getElementById('mycanvas_"+inst+"ga'));");
                    eval("smoothie_"+inst+"gb.addTimeSeries(line_gb_"+client+"_"+inst+", { strokeStyle: 'rgb(245, 199, 26)', fillStyle: 'rgba(245, 199, 26, 0.1)', lineWidth: 3 });");
                    eval("smoothie_"+inst+"gb.streamTo(document.getElementById('mycanvas_"+inst+"gb'));");
                    eval("smoothie_"+inst+"gc.addTimeSeries(line_gc_"+client+"_"+inst+", { strokeStyle: 'rgb(245, 199, 26)', fillStyle: 'rgba(245, 199, 26, 0.1)', lineWidth: 3 });");
                    eval("smoothie_"+inst+"gc.streamTo(document.getElementById('mycanvas_"+inst+"gc'));");
                }
                else if (sensors[inst].substring(0,2) == "DS") {
                    eval("smoothie_"+inst+".addTimeSeries(line_t_"+client+"_"+inst+", { strokeStyle: 'rgb(205,79,57)', fillStyle: 'rgba(205,79,57, 0.3)', lineWidth: 3 });");
                    eval("smoothie_"+inst+".streamTo(document.getElementById('mycanvas_"+inst+"'));");
                }
            }

            connect();

         };

