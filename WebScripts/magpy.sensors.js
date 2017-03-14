         function getClientname(str) {
            var re = str.split("/");
            return re[3];
            }

         function getSensorname(str) {
            var re = str.split("/");
            return re[4].split("#")[1].split("-")[0];
            }

         function onOwValue(topicUri, event) {
            client = getClientname(topicUri)
            inst = getSensorname(topicUri)
            eval("eventcnt_"+client+"_"+inst+" += 1;");             
            event.value = event.value;
            switch (event.id) {
               case 30:
                  event.value = event.value.toFixed(2);
                  eval("t_"+client+"_"+inst+".innerHTML = event.value;");
                  eval("var lastval = t_"+client+"_"+inst+"_last;");
                  if (lastval !== null) {
                     eval("line_t_"+client+"_"+inst+".append(new Date().getTime(), lastval);");
                  }
                  eval("t_"+client+"_"+inst+"_last = event.value;");
                  eval("line_t_"+client+"_"+inst+".append(new Date().getTime(), event.value);");
                  break;
               case 1:
                  eval("time_"+client+"_"+inst+".innerHTML = event.value;");
                  break;
               case 33:
                  eval("rh_"+client+"_"+inst+".innerHTML = event.value;");
                  break;
               case 60:
                  eval("vdd_"+client+"_"+inst+".innerHTML = event.value;");
                  break;
               case 61:
                  eval("vad_"+client+"_"+inst+".innerHTML = event.value;");
                  break;
               case 62:
                  eval("vis_"+client+"_"+inst+".innerHTML = event.value;");
                  break;
               case 10:
                  hostname.innerHTML = event.value;
                  break;
                default:
                  break;
            }
         }

         function onCsValue(topicUri, event) {
            client = getClientname(topicUri);
            inst = getSensorname(topicUri);
            eval("eventcnt_"+client+"_"+inst+" += 1;");             
            event.value = event.value;
            switch (event.id) {
               case 10:
                  event.value = event.value.toFixed(2);
                  eval("f_"+client+"_"+inst+".innerHTML = event.value;");
                  eval("var lastval = f_"+client+"_"+inst+"_last;");
                  if (lastval !== null) {
                     eval("line_f_"+client+"_"+inst+".append(new Date().getTime(), lastval);");
                  }
                  eval("f_"+client+"_"+inst+"_last = event.value;");
                  eval("line_f_"+client+"_"+inst+".append(new Date().getTime(), event.value);");
                  break;
               case 1:
                  eval("time_"+client+"_"+inst+".innerHTML = event.value;");
                  break;
               default:
                  break;
            }
         }

         function onKerValue(topicUri, event) {
            client = getClientname(topicUri);
            inst = getSensorname(topicUri);
            eval("eventcnt_"+client+"_"+inst+" += 1;");             
            event.value = event.value;
            switch (event.id) {
               case 38:
                  event.value = event.value.toFixed(2);
                  eval("w_"+client+"_"+inst+".innerHTML = event.value;");
                  eval("var lastval = w_"+client+"_"+inst+"_last;");
                  if (lastval !== null) {
                     eval("line_w_"+client+"_"+inst+".append(new Date().getTime(), lastval);");
                  }
                  eval("w_"+client+"_"+inst+"_last = event.value;");
                  eval("line_w_"+client+"_"+inst+".append(new Date().getTime(), event.value);");
                  break;
               case 1:
                  eval("time_"+client+"_"+inst+".innerHTML = event.value;");
                  break;
               default:
                  break;
            }
         }

         function onPalValue(topicUri, event) {
            client = getClientname(topicUri);
            inst = getSensorname(topicUri);
            eval("eventcnt_"+client+"_"+inst+" += 1;");            
            event.value = event.value;
            switch (event.id) {
               case 1:
                  eval("time_"+client+"_"+inst+".innerHTML = event.value;");
                  break;
               case 11:
                  event.value = event.value.toFixed(2);
                  eval("x_"+client+"_"+inst+".innerHTML = event.value;");
                  eval("var lastval = x_"+client+"_"+inst+"_last;");
                  if (lastval !== null) {
                     eval("line_x_"+client+"_"+inst+".append(new Date().getTime(), lastval);");
                  }
                  eval("x_"+client+"_"+inst+"_last = event.value;");
                  eval("line_x_"+client+"_"+inst+".append(new Date().getTime(), event.value);");
                  break;
               case 12:
                  event.value = event.value.toFixed(2);
                  eval("y_"+client+"_"+inst+".innerHTML = event.value;");
                  eval("var lastval = y_"+client+"_"+inst+"_last;");
                  if (lastval !== null) {
                     eval("line_y_"+client+"_"+inst+".append(new Date().getTime(), lastval);");
                  }
                  eval("y_"+client+"_"+inst+"_last = event.value;");
                  eval("line_y_"+client+"_"+inst+".append(new Date().getTime(), event.value);");
                  break;
               case 13:
                  event.value = event.value.toFixed(2);
                  eval("z_"+client+"_"+inst+".innerHTML = event.value;");
                  eval("var lastval = z_"+client+"_"+inst+"_last;");
                  if (lastval !== null) {
                     eval("line_z_"+client+"_"+inst+".append(new Date().getTime(), lastval);");
                  }
                  eval("z_"+client+"_"+inst+"_last = event.value;");
                  eval("line_z_"+client+"_"+inst+".append(new Date().getTime(), event.value);");
                  break;
               default:
                  break;
            }
         }


         function onArdValue(topicUri, event) {
            client = getClientname(topicUri);
            inst = getSensorname(topicUri);
            eval("eventcnt_"+client+"_"+inst+" += 1;");            
            event.value = event.value;
            switch (event.id) {
               case 1:
                  eval("time_"+client+"_"+inst+".innerHTML = event.value;");
                  break;
               case 11:
                  event.value = event.value.toFixed(2);
                  eval("x_"+client+"_"+inst+".innerHTML = event.value;");
                  eval("var lastval = x_"+client+"_"+inst+"_last;");
                  if (lastval !== null) {
                     eval("line_x_"+client+"_"+inst+".append(new Date().getTime(), lastval);");
                  }
                  eval("x_"+client+"_"+inst+"_last = event.value;");
                  eval("line_x_"+client+"_"+inst+".append(new Date().getTime(), event.value);");
                  break;
               case 12:
                  event.value = event.value.toFixed(2);
                  eval("y_"+client+"_"+inst+".innerHTML = event.value;");
                  eval("var lastval = y_"+client+"_"+inst+"_last;");
                  if (lastval !== null) {
                     eval("line_y_"+client+"_"+inst+".append(new Date().getTime(), lastval);");
                  }
                  eval("y_"+client+"_"+inst+"_last = event.value;");
                  eval("line_y_"+client+"_"+inst+".append(new Date().getTime(), event.value);");
                  break;
               case 13:
                  event.value = event.value.toFixed(2);
                  eval("z_"+client+"_"+inst+".innerHTML = event.value;");
                  eval("var lastval = z_"+client+"_"+inst+"_last;");
                  if (lastval !== null) {
                     eval("line_z_"+client+"_"+inst+".append(new Date().getTime(), lastval);");
                  }
                  eval("z_"+client+"_"+inst+"_last = event.value;");
                  eval("line_z_"+client+"_"+inst+".append(new Date().getTime(), event.value);");
                  break;
               case 30:
                  event.value = event.value.toFixed(2);
                  eval("t_"+client+"_"+inst+".innerHTML = event.value;");
                  eval("var lastval = t_"+client+"_"+inst+"_last;");
                  if (lastval !== null) {
                     eval("line_t_"+client+"_"+inst+".append(new Date().getTime(), lastval);");
                  }
                  eval("t_"+client+"_"+inst+"_last = event.value;");
                  eval("line_t_"+client+"_"+inst+".append(new Date().getTime(), event.value);");
                  break;
               default:
                  break;
            }
         }


         function onEnvValue(topicUri, event) {
            client = getClientname(topicUri)
            inst = getSensorname(topicUri)
            eval("eventcnt_"+client+"_"+inst+" += 1;");             
            event.value = event.value;
            switch (event.id) {
               case 1: // CHANGED TODO
                  eval("time_"+client+"_"+inst+".innerHTML = event.value;");
                  break;
               case 33:
                  event.value = event.value.toFixed(2);
                  eval("vara_"+client+"_"+inst+".innerHTML = event.value;");
                  eval("var lastval = vara_"+client+"_"+inst+"_last;");
                  if (lastval !== null) {
                     eval("line_vara_"+client+"_"+inst+".append(new Date().getTime(), lastval);");
                  }
                  eval("vara_"+client+"_"+inst+"_last = event.value;");
                  eval("line_vara_"+client+"_"+inst+".append(new Date().getTime(), event.value);");
                  break;
               case 30:
                  event.value = event.value.toFixed(2);
                  eval("ta_"+client+"_"+inst+".innerHTML = event.value;");
                  eval("var lastval = ta_"+client+"_"+inst+"_last;");
                  if (lastval !== null) {
                     eval("line_ta_"+client+"_"+inst+".append(new Date().getTime(), lastval);");
                  }
                  eval("ta_"+client+"_"+inst+"_last = event.value;");
                  eval("line_ta_"+client+"_"+inst+".append(new Date().getTime(), event.value);");
                  break;
               case 34:
                  event.value = event.value.toFixed(2);
                  eval("tb_"+client+"_"+inst+".innerHTML = event.value;");
                  eval("var lastval = tb_"+client+"_"+inst+"_last;");
                  if (lastval !== null) {
                     eval("line_tb_"+".append(new Date().getTime(), lastval);");
                  }
                  eval("tb_"+client+"_"+inst+"_last = event.value;");
                  eval("line_tb_"+client+"_"+inst+".append(new Date().getTime(), event.value);");
                  break;
               case 0:
                  if (inst == "env") {
                      hostname.innerHTML = event.value;
                  };
                  break;
               case 3:
                  eval("date_"+client+"_"+inst+" = event.value;");
                  break;
               default:
                  break;
            }
         }

         function onLemiValue(topicUri, event) {
            client = getClientname(topicUri);
            inst = getSensorname(topicUri);
            eval("eventcnt_"+client+"_"+inst+" += 1;");             
            event.value = event.value;
            switch (event.id) {
               case 1:
                  eval("time_"+client+"_"+inst+".innerHTML = event.value;");
                  break;
               case 11:
                  event.value = event.value.toFixed(2);
                  eval("x_"+client+"_"+inst+".innerHTML = event.value;");
                  eval("var lastval = x_"+client+"_"+inst+"_last;");
                  if (lastval !== null) {
                     eval("line_x_"+client+"_"+inst+".append(new Date().getTime(), lastval);");
                  }
                  eval("x_"+client+"_"+inst+"_last = event.value;");
                  eval("line_x_"+client+"_"+inst+".append(new Date().getTime(), event.value);");
                  break;
               case 12:
                  event.value = event.value.toFixed(2);
                  eval("y_"+client+"_"+inst+".innerHTML = event.value;");
                  eval("var lastval = y_"+client+"_"+inst+"_last;");
                  if (lastval !== null) {
                     eval("line_y_"+client+"_"+inst+".append(new Date().getTime(), lastval);");
                  }
                  eval("y_"+client+"_"+inst+"_last = event.value;");
                  eval("line_y_"+client+"_"+inst+".append(new Date().getTime(), event.value);");
                  break;
               case 13:
                  event.value = event.value.toFixed(2);
                  eval("z_"+client+"_"+inst+".innerHTML = event.value;");
                  eval("var lastval = z_"+client+"_"+inst+"_last;");
                  if (lastval !== null) {
                     eval("line_z_"+client+"_"+inst+".append(new Date().getTime(), lastval);");
                  }
                  eval("z_"+client+"_"+inst+"_last = event.value;");
                  eval("line_z_"+client+"_"+inst+".append(new Date().getTime(), event.value);");
                  break;
               case 31:
                  event.value = event.value.toFixed(2);
                  eval("ta_"+client+"_"+inst+".innerHTML = event.value;");
                  eval("var lastval = ta_"+client+"_"+inst+"_last;");
                  if (lastval !== null) {
                     eval("line_ta_"+client+"_"+inst+".append(new Date().getTime(), lastval);");
                  }
                  eval("ta_"+client+"_"+inst+"_last = event.value;");
                  eval("line_ta_"+client+"_"+inst+".append(new Date().getTime(), event.value);");
                  break;
               case 32:
                  event.value = event.value.toFixed(2);
                  eval("tb_"+client+"_"+inst+".innerHTML = event.value;");
                  eval("var lastval = tb_"+client+"_"+inst+"_last;");
                  if (lastval !== null) {
                     eval("line_tb_"+client+"_"+inst+".append(new Date().getTime(), lastval);");
                  }
                  eval("tb_"+client+"_"+inst+"_last = event.value;");
                  eval("line_tb_"+client+"_"+inst+".append(new Date().getTime(), event.value);");
                  break;
               default:
                  break;
            }
         }

         function onPosValue(topicUri, event) {
            client = getClientname(topicUri);
            inst = getSensorname(topicUri);
            eval("eventcnt_"+client+"_"+inst+" += 1;");             
            event.value = event.value;
            switch (event.id) {
               case 10:   // CHANGED TODO
                  event.value = event.value.toFixed(2);
                  eval("f_"+client+"_"+inst+".innerHTML = event.value;");
                  eval("var lastval = f_"+client+"_"+inst+"_last;");
                  if (lastval !== null) {
                     eval("line_f_"+client+"_"+inst+".append(new Date().getTime(), lastval);");
                  }
                  eval("f_"+client+"_"+inst+"_last = event.value;");
                  eval("line_f_"+client+"_"+inst+".append(new Date().getTime(), event.value);");
                  break;
               case 1:
                  eval("time_"+client+"_"+inst+".innerHTML = event.value;");
                  break;
               default:
                  break;
            }
         }

 
         function onGSMValue(topicUri, event) {
            client = getClientname(topicUri);
            inst = getSensorname(topicUri);
            eval("eventcnt_"+client+"_"+inst+" += 1;");             
            event.value = event.value;
            switch (event.id) {
               case 10:   // CHANGED TODO
                  event.value = event.value.toFixed(2);
                  eval("f_"+client+"_"+inst+".innerHTML = event.value;");
                  eval("var lastval = f_"+client+"_"+inst+"_last;");
                  if (lastval !== null) {
                     eval("line_f_"+client+"_"+inst+".append(new Date().getTime(), lastval);");
                  }
                  eval("f_"+client+"_"+inst+"_last = event.value;");
                  eval("line_f_"+client+"_"+inst+".append(new Date().getTime(), event.value);");
                  break;
               case 1:
                  eval("time_"+client+"_"+inst+".innerHTML = event.value;");
                  break;
               default:
                  break;
            }
         }

         function onG19Value(topicUri, event) {
            client = getClientname(topicUri);
            inst = getSensorname(topicUri);
            eval("eventcnt_"+client+"_"+inst+" += 1;");             
            event.value = event.value;
            switch (event.id) {
               case 10:
                  event.value = event.value.toFixed(2);
                  eval("f_"+client+"_"+inst+".innerHTML = event.value;");
                  eval("var lastval = f_"+client+"_"+inst+"_last;");
                  if (lastval !== null) {
                     eval("line_f_"+client+"_"+inst+".append(new Date().getTime(), lastval);");
                  }
                  eval("f_"+client+"_"+inst+"_last = event.value;");
                  eval("line_f_"+client+"_"+inst+".append(new Date().getTime(), event.value);");
                  break;
               case 1:
                  eval("time_"+client+"_"+inst+".innerHTML = event.value;");
                  break;
               default:
                  break;
            }
         }

         function onGPValue(topicUri, event) {
            client = getClientname(topicUri);
            inst = getSensorname(topicUri);
            eval("eventcnt_"+client+"_"+inst+" += 1;");             
            event.value = event.value;
            switch (event.id) {
               case 1:
                  eval("time_"+client+"_"+inst+".innerHTML = event.value;");
                  break;
               case 20:
                  event.value = event.value.toFixed(2);
                  eval("fa_"+client+"_"+inst+".innerHTML = event.value;");
                  eval("var lastval = fa_"+client+"_"+inst+"_last;");
                  if (lastval !== null) {
                     eval("line_fa_"+client+"_"+inst+".append(new Date().getTime(), lastval);");
                  }
                  eval("fa_"+client+"_"+inst+"_last = event.value;");
                  eval("line_fa_"+client+"_"+inst+".append(new Date().getTime(), event.value);");
                  break;
               case 21:
                  event.value = event.value.toFixed(2);
                  eval("fb_"+client+"_"+inst+".innerHTML = event.value;");
                  eval("var lastval = fb_"+client+"_"+inst+"_last;");
                  if (lastval !== null) {
                     eval("line_fb_"+client+"_"+inst+".append(new Date().getTime(), lastval);");
                  }
                  eval("fb_"+client+"_"+inst+"_last = event.value;");
                  eval("line_fb_"+client+"_"+inst+".append(new Date().getTime(), event.value);");
                  break;
               case 22:
                  event.value = event.value.toFixed(2);
                  eval("fc_"+client+"_"+inst+".innerHTML = event.value;");
                  eval("var lastval = fc_"+client+"_"+inst+"_last;");
                  if (lastval !== null) {
                     eval("line_fc_"+client+"_"+inst+".append(new Date().getTime(), lastval);");
                  }
                  eval("fc_"+client+"_"+inst+"_last = event.value;");
                  eval("line_fc_"+client+"_"+inst+".append(new Date().getTime(), event.value);");
                  break;
               case 23:
                  event.value = event.value.toFixed(2);
                  eval("ga_"+client+"_"+inst+".innerHTML = event.value;");
                  eval("var lastval = ga_"+client+"_"+inst+"_last;");
                  if (lastval !== null) {
                     eval("line_ga_"+client+"_"+inst+".append(new Date().getTime(), lastval);");
                  }
                  eval("ga_"+client+"_"+inst+"_last = event.value;");
                  eval("line_ga_"+client+"_"+inst+".append(new Date().getTime(), event.value);");
                  break;
               case 24:
                  event.value = event.value.toFixed(2);
                  eval("gb_"+client+"_"+inst+".innerHTML = event.value;");
                  eval("var lastval = gb_"+client+"_"+inst+"_last;");
                  if (lastval !== null) {
                     eval("line_gb_"+client+"_"+inst+".append(new Date().getTime(), lastval);");
                  }
                  eval("gb_"+client+"_"+inst+"_last = event.value;");
                  eval("line_gb_"+client+"_"+inst+".append(new Date().getTime(), event.value);");
                  break;
               case 25:
                  event.value = event.value.toFixed(2);
                  eval("gc_"+client+"_"+inst+".innerHTML = event.value;");
                  eval("var lastval = gc_"+client+"_"+inst+"_last;");
                  if (lastval !== null) {
                     eval("line_gc_"+client+"_"+inst+".append(new Date().getTime(), lastval);");
                  }
                  eval("gc_"+client+"_"+inst+"_last = event.value;");
                  eval("line_gc_"+client+"_"+inst+".append(new Date().getTime(), event.value);");
                  break;
               default:
                  break;
            }
         }


         function onBM35Value(topicUri, event) {
            client = getClientname(topicUri);
            inst = getSensorname(topicUri);
            eval("eventcnt_"+client+"_"+inst+" += 1;");
            event.value = event.value;
            switch (event.id) {
               case 35:
                  event.value = event.value.toFixed(2);
                  eval("varc_"+client+"_"+inst+".innerHTML = event.value;");
                  eval("var lastval = varc_"+client+"_"+inst+"_last;");
                  if (lastval !== null) {
                     eval("line_varc_"+client+"_"+inst+".append(new Date().getTime(), lastval);");
                  }
                  eval("varc_"+client+"_"+inst+"_last = event.value;");
                  eval("line_varc_"+client+"_"+inst+".append(new Date().getTime(), event.value);");
                  break;
               case 1:
                  eval("time_"+client+"_"+inst+".innerHTML = event.value;");
                  break;
               default:
                  break;
            }
         }

         function onAD7Value(topicUri, event) {
            client = getClientname(topicUri);
            inst = getSensorname(topicUri);
            eval("eventcnt_"+client+"_"+inst+" += 1;");
            event.value = event.value;
            switch (event.id) {
               case 35:
                  event.value = event.value.toFixed(2);
                  eval("varc_"+client+"_"+inst+".innerHTML = event.value;");
                  eval("var lastval = varc_"+client+"_"+inst+"_last;");
                  if (lastval !== null) {
                     eval("line_varc_"+client+"_"+inst+".append(new Date().getTime(), lastval);");
                  }
                  eval("varc_"+client+"_"+inst+"_last = event.value;");
                  eval("line_varc_"+client+"_"+inst+".append(new Date().getTime(), event.value);");
                  break;
               case 1:
                  eval("time_"+client+"_"+inst+".innerHTML = event.value;");
                  break;
               default:
                  break;
            }
         }

