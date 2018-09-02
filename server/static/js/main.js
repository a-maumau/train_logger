/*
    variables
*/
var global_log_data = {};
var global_log_lut = {};
var global_settings = {"chart_number":0, "chart_current_id":null, "chart_log_pair":{"not_on_chart":[]}};

// chart instance will be save like {"chart0":chart_obj, "chart1":... }
var global_charts = {};


var global_known_log = {};

// for witch data to featch from server, in this array means fetch data
var global_watch_list = [];
var global_load_output_list = [];

var global_loaded_history = {"log":{}, "output":{}};
var global_fetch_update_go = true;
var global_update_re_request = false;

// sec
const base_time_interval = 5;
const namespace_separator = "::";

function set_accordion(){
    $(function() {
        var Accordion = function(el, multiple) {
            this.el = el || {};
            this.multiple = multiple || false;

            // Variables privadas
            var links = this.el.find('.link, .sublink, .sub-sublink, .side-menu-link');
            // Evento
            links.on('click', {el: this.el, multiple: this.multiple}, this.dropdown)
        }

        Accordion.prototype.dropdown = function(e) {
            var $el = e.data.el;
                $this = $(this),
                $next = $this.next();

            $next.slideToggle();
            $this.parent().toggleClass('open');

            /*
            // close other accordions
            if (!e.data.multiple) {
                $el.find('.submenu').not($next).slideUp().parent().removeClass('open');
            };
            */
        }   

        var accordion = new Accordion($('#accordion, #side-menu-accordion, #sub-sub-accordion'), false);
    });
}

/*
    for side menu button action.
*/
$(function () {
  var $body = $('body');
  $('#js__sideMenuBtn').on('click', function () {
    $body.toggleClass('side-open');
    var $side_menu = $('.side-menu');
    if($side_menu.hasClass('visible')){
        $side_menu.removeClass('visible');  
    }else{
        $side_menu.addClass('visible')
    }
    $('#js__overlay').on('click', function () {
      $body.removeClass('side-open');
    });
  });
});

function parse_namespaces_to_html_element(namespace_array){
    ns_str = ""
    for(let index in namespace_array){
        ns_str = ns_str+"<option value=\""+index+"\">"+namespace_array[index]+"</option>"
    }

    return ns_str
}

function parse_info_to_html_element(info_json){
    info_str = ""
    info_str = info_str+"<li><div class=\"second-indent\"><a href=\"#\">"+"log name"+":<p>"+info_json["log_name"]+"</p></a></div></li>"
    info_str = info_str+"<li><div class=\"second-indent\"><a href=\"#\">"+"timestamp"+":<p>"+info_json["timestamp"]+"</p></a></div></li>"
    info_str = info_str+"<li><div class=\"second-indent\"><a href=\"#\">"+"namespaces"+":<p>"
    for(let index in info_json["log_info"]["namespaces"]){
        if(index != 0){
            info_str = info_str+", "
        }
        info_str = info_str+info_json["log_info"]["namespaces"][index]
    }
    info_str = info_str+"</p></a></div></li>"

    for(let key in info_json["log_info"]["logs"]){
        info_str = info_str+"<li><div class=\"second-indent\"><a href=\"#\">"+key+" file name:"+"<p>"+info_json["log_info"]["logs"][key]["file_name"]+"</p></a></div></li>"
    }

    return info_str
}

function parse_gitinfo_to_html_element(gitinfo_json){
    ginfo_str = ""
    for(let key in gitinfo_json){
        ginfo_str = ginfo_str+"<li><div class=\"second-indent\"><a href=\"#\">"+key+":<p>"+gitinfo_json[key]+"</p></a></div></li>"
    }

    return ginfo_str
}

function parse_arguments_to_html_element(argument_array){
    arg_str = ""
    for(let index in argument_array){
        for(let key in argument_array[index]){
            arg_str = arg_str+"<li><div class=\"second-indent\"><a href=\"#\">"+key+":<p>"+argument_array[index][key]+"</p></a></div></li>"
        }
    }

    return arg_str
}

function create_html_element(json_data){
    for(let index in json_data["log_data"]){
        for(let key_log_name in json_data["log_data"][index]){
            data_dict = json_data["log_data"][index][key_log_name];
            log_name = key_log_name;
            namespace_box_option_element = parse_namespaces_to_html_element(data_dict["info"]["log_info"]["namespaces"]);
            info_element = parse_info_to_html_element(data_dict["info"]);
            gitinfo_element = parse_gitinfo_to_html_element(data_dict["info"]["git_info"]);
            arguments_element = parse_arguments_to_html_element(data_dict["info"]["arguments"]);

            // fuckin code, but I think it's most fast...
            $(function() {
                $("#log_list").append("<li class=\"sub-accordion\"><div class=\"sublink\" id=\""+log_name+"\">"+log_name+"<i class=\"fa fa-chevron-down\"></i></div><ul class=\"sub-submenu\"><li><a href=\"#\">watch<input type=\"checkbox\" class=\"toggle_button\" id=\""+log_name+"_watch_toggle\" onclick=\"update_watch_list('"+log_name+"',this.checked)\"></a></li><li><a href=\"#\">load outputs<input type=\"checkbox\" class=\"toggle_button\" id=\""+log_name+"_load_outputs_toggle"+"\" onclick=\"update_load_output_list('"+log_name+"',this.checked)\"></a></li><li><a href=\"#\">color<div class=\"custom_select_box namespace_box\"><select required>"+namespace_box_option_element+"</select></div><input type=\"color\" class=\"color_input\" value=\"#ff6622\" id=\"colorWell "+log_name+"\"></a></li>"+"<li id=\"sub-sub-accordion\" class=\"sub-sub-accordion\"><div class=\"sub-sublink\">log info<i class=\"fa fa-chevron-down\"></i></div><ul class=\"sub-sub-submenu\">"+info_element+"</ul></li><li id=\"sub-sub-accordion\" class=\"sub-sub-accordion\"><div class=\"sub-sublink\">git info<i class=\"fa fa-chevron-down\"></i></div><ul class=\"sub-sub-submenu\">"+gitinfo_element+"</ul></li><li id=\"sub-sub-accordion\" class=\"sub-sub-accordion\"><div class=\"sub-sublink\">arguments<i class=\"fa fa-chevron-down\"></i></div><ul class=\"sub-sub-submenu\">"+arguments_element+"</ul></li></ul></li>");
            });
        }
    }
    set_accordion();
}

/*
"log_data":[
    "log_output_20180819_03-40-24":{
        "data": {
            "train": "num,value\n0,0.6642626949058058\n1,0.15790458550463182\n2,0.5962026553982934\n3,0.6003983213629899\n4,0.8684492810064259\n5,0.465069529542406\n6,0.8245318462802421\n7,0.5157306781871831\n8,0.08771873084482451\n9,0.016051337888839723\n",
            "val": "num,score\n0,0.5026417259952136\n1,0.9878552214303242\n2,0.4635398949983144\n3,0.9668898641012703\n4,0.06986499185359096\n5,0.6759377369183559\n6,0.7118023555867911\n7,0.2832029023651267\n8,0.6596488885843175\n9,0.018762206401513493\n"
        },
{
    "log_name":{"namesapce":{"header":[], "header":[], "header":[]}, "namesapce2":{"header":[], "header":[],"header":[]}}.
    "log_name":{"namesapce":{"header":[], "header":[], "header":[]}, "namesapce2":{"header":[], "header":[],"header":[]}}.
}
*/

function init_charts(){
    for(let n = 0; n < global_settings["chart_current_id"]+1; n++){
        var tmp_chart = c3.generate({bindto:"#chart"+n,data:{xs:{},columns:[]},color:{},axis:{x:{label: 'X Label'},y:{label:'Y Label'},y2:{show: true,label: 'Y2 Label'}},zoom:{enabled:true},title: {show: false,text: "chart"+n, position: 'top-center',padding: {top: 0,right: 0,bottom: 0,left: 0}}});
        for(let index in global_settings["chart_log_pair"]["chart"+n]){
            log_data_name = global_settings["chart_log_pair"]["chart"+n][index];

            if(global_log_lut[log_data_name]["is_axis"] == true){
                continue;
            }else{
                tmp_chart.load({
                    xs: {[log_data_name]: global_log_lut[log_data_name]["x_axis"]},
                    columns: [
                        global_log_data[global_log_lut[log_data_name]["x_axis"]],
                        global_log_data[log_data_name]
                    ],
                    color: { pattern: ['#ff7700']},
                });
                //d3.select('#chart'+n+' .c3-title').style('font-size', '4em');
                
                // https://stackoverflow.com/questions/45142519/c3-js-chart-title-overlapped-if-i-change-the-size-of-title
                //d3.select('#chart'+n+' .c3-title').style('font-size', '2em').style("dominant-baseline", "central");
            }
        }
        global_charts["chart"+n] = tmp_chart;
    }
}

function add_chart(){
    if(global_settings["chart_current_id"] == null){
        global_settings["chart_current_id"] = 0;
    }else{
        global_settings["chart_current_id"] = global_settings["chart_current_id"]+1;
    }

    $(function() {
        $(".chart_area").append("<div id=\"chart"+global_settings["chart_current_id"]+"\" class=\"chart_figure\"></div>");
    });
}

function parse_log_data(json_data, header_exist) {
    var csv_lines = null;
    var headers = null;
    var csv_per_line = null;

    for(let index in json_data["log_data"]){
        add_chart();
        // for which chart to be written 
        global_settings["chart_log_pair"]["chart"+global_settings["chart_current_id"]] = [];
        // log name scope
        for(let key_log_name in json_data["log_data"][index]){
            log_data = json_data["log_data"][index][key_log_name]["data"];
            global_known_log[key_log_name] = {"namespaces":[]};
            global_loaded_history["log"][key_log_name] = {};

            for(let key_namespace in log_data){
                // add to known list
                global_known_log[key_log_name]["namespaces"].push(key_namespace);

                csv_lines = log_data[key_namespace].split("\n").filter(c => c != "");

                headers = csv_lines[0].split(","); 
                // prepare for ["x1", 1, 2, 3, 4, ...]
                global_log_data[key_log_name+namespace_separator+key_namespace+namespace_separator+headers[0]] = [key_log_name+namespace_separator+key_namespace+namespace_separator+headers[0]];
                global_log_lut[key_log_name+namespace_separator+key_namespace+namespace_separator+headers[0]] = {"x_axis":"", "is_axis":true};
                for(let i = 1; i < headers.length; i++){
                    // prepare for ["data1", 1, 10, 55, 34, ...]
                    global_log_data[key_log_name+namespace_separator+key_namespace+namespace_separator+headers[i]] = [key_log_name+namespace_separator+key_namespace+namespace_separator+headers[i]];
                    // look up table for data and axis
                    global_log_lut[key_log_name+namespace_separator+key_namespace+namespace_separator+headers[i]] = {"x_axis":key_log_name+namespace_separator+key_namespace+namespace_separator+headers[0], "is_axis":false, "chart":"chart"+global_settings["chart_current_id"]};
                    // assign in chart#
                    global_settings["chart_log_pair"]["chart"+global_settings["chart_current_id"]].push(key_log_name+namespace_separator+key_namespace+namespace_separator+headers[i]);
                }
                for(let i = 1; i < csv_lines.length; i++) {
                    csv_per_line = csv_lines[i].split(",");
                    // exclude only \n line
                    if(csv_per_line.length == headers.length){
                        for(let col = 0; col < csv_per_line.length; col++){
                            global_log_data[key_log_name+namespace_separator+key_namespace+namespace_separator+headers[col]].push(csv_per_line[col]);
                        }
                    }
                }
                global_loaded_history["log"][key_log_name][key_namespace] = {"read_csv":csv_lines.length};
                global_loaded_history["output"][key_log_name] = {"read_output":0};
            }
        }
    }
}

var update_interval_slider = document.getElementById("update_interval_slider");
var update_interval_output = document.getElementById("update_interval_val");
var update_checker = setInterval(update_log, update_interval_slider.value*base_time_interval*1000);

update_interval_output.innerHTML = update_interval_slider.value*base_time_interval;
update_interval_slider.oninput = function() {
    update_interval_output.innerHTML = this.value*base_time_interval;
    clear_interval(update_checker);
    update_checker = setInterval(update_log, this.value*base_time_interval*1000);
}

/*
example:

    csv file on the server:
    0: headers
    1: data1
    2: data2
    3: data3 served,       read
    ---------------------------
    4: data4 not served, unread
    .
    .
    .

    global_loaded_history::"read_line" -> 4
    so at server, it should read out csv file from 4:
    not thinking of none header csv file...
*/
function create_update_query_json(){
    var request_json = {"log":{}, "output":{}, "known":global_known_log};
    var log_name = null;

    for(let watch_list_index in global_watch_list){
        log_name = global_watch_list[watch_list_index];
        request_json["log"][log_name] = {};
        for(let namespace_key in global_loaded_history["log"][log_name]){
            request_json["log"][log_name][namespace_key] = {"request":global_loaded_history["log"][log_name][namespace_key]["read_csv"]};
        }

        if(global_load_output_list.indexOf(log_name) >= 0){
            request_json["output"][log_name] = {"request":global_loaded_history["output"][log_name]["read_output"]};
        }
    }

    return request_json;
}
/*
{
    "log_data":[
        {
            "log_name":{
                data": {
                    "namespace": data, 
                    ...
                },
        },
        ...
    ]

    "output_data":[
        "log_name":{
            "data":
                # array of each output name
                [
                    {
                        "output_name": output name
                        "output_desc": output description
                        "output":
                            # this array is same output name
                            [
                                {
                                    "images": [
                                        {
                                            "data": base64 encoded image data
                                            "name"; image name
                                            "type": image extension
                                        },
                                        ...
                                    ],
                                    "desc": description
                                    "desc_items": itemized description
                                },
                                ...
                            ],
                            ...
                    }
                ],
                ...
            }
        },
        ...
    ],

    "new_data":[
        {
            "log_name":{
                data": {
                    "namespace": data, 
                    ...
                },
            }
        },
        ...
    ]
}
*/
function update_csv_data(log_json_data){
    var csv_lines = null;
    var headers = null;
    var csv_per_line = null;

    for(let index in log_json_data){
        for(let key_log_name in log_json_data[index]){
            log_data = log_json_data[index][key_log_name]["data"];

            for(let key_namespace in log_data){
                csv_lines = log_data[key_namespace].split("\n").filter(c => c != "");

                headers = csv_lines[0].split(","); 
                for(let i = 1; i < csv_lines.length; i++) {
                    csv_per_line = csv_lines[i].split(",");

                    // exclude only \n line
                    //if(csv_per_line.length == headers.length){
                    for(let col = 0; col < csv_per_line.length; col++){
                        global_log_data[key_log_name+namespace_separator+key_namespace+namespace_separator+headers[col]].push(csv_per_line[col]);
                    }
                    //}
                }
                global_loaded_history["log"][key_log_name][key_namespace]["read_csv"] += csv_lines.length-1; // -1, because header is included.
                
                if(csv_lines.length > 1){
                    for(let i = 1; i < headers.length; i++) {
                        log_data_name = key_log_name+namespace_separator+key_namespace+namespace_separator+headers[i]
                        global_charts[global_log_lut[log_data_name]["chart"]].load({
                            xs: {[log_data_name]: global_log_lut[log_data_name]["x_axis"]},
                            columns: [
                                global_log_data[global_log_lut[log_data_name]["x_axis"]],
                                global_log_data[log_data_name]
                            ],
                        });
                    }
                }
            }
        }
    }
}

function update_output(output_json_data){
    var html_element = null;

    for(let index in output_json_data){
        html_element = ""

        for(let key_log_name in output_json_data[index]){
            output_data_array = output_json_data[index][key_log_name]["data"];

            if($(".timeline-wrapper#"+key_log_name).size() == false){
                $(function() {
                    $("#content2").append("<div class=\"timeline-wrapper\" id=\""+key_log_name+"\"><div class=\"timeline-ac-container\"><input id=\""+key_log_name+"_ac\" type=\"checkbox\" checked /><label for=\""+key_log_name+"_ac\"><h2>"+key_log_name+"</h2></label><div class=\"timeline-ac-content\"><div class=\"timeline-box\"><div class=\"timeline\"><div class=\"timeline-entry\"><div class=\"timeline-title\"><h3>Output Name</h3><p>description/tag</p></div><div class=\"timeline-body\"><p>Output Contents</p><ul><li>image/text</li></ul></div></div></div></div></div></div></div>");
                });
            }

            for(let output_data_index in output_data_array){
                output_data = output_data_array[output_data_index];

                html_element = "<div class=\"timeline-entry\"><div class=\"timeline-title\"><h3>"+output_data["output_name"]+"</h3><p>"+output_data["output_desc"]+"</p></div><div class=\"timeline-body\"><div class=\"luminous-imgbox\">";

                add_image_ids = [];

                for(let each_output_index in output_data["outputs"]){
                    each_output = output_data["outputs"][each_output_index];

                    for(let img_index in each_output["images"]){
                        img = each_output["images"][img_index];
                        add_image_ids.push(key_log_name+namespace_separator+img["name"]);
                        // it is possible to embed img at <a> tag href like href=\"data:image/"+img["type"]+";base64,"+img["data"]+"\", but it is redundant,
                        // and also for implementing thumbnail resizing, and improving UX
                        html_element = html_element + "<a id=\""+key_log_name+namespace_separator+img["name"]+"\" class=\"luminous luminous-img zoom-in\" href=\"api/log/"+key_log_name+"/output/image/"+img["name"]+"\" title=\""+img["name"]+"\"><img class=\"thumbnail\" src=\"data:image/"+img["type"]+";base64,"+img["data"]+"\" alt=\""+img["name"]+"\"></a>";
                    }

                    if(each_output["desc"].length > 0){
                        html_element = html_element+ "<p>"+each_output["desc"]+"</p>";
                    }

                    if(each_output["desc_items"].length > 0){
                        html_element = html_element + "<ul>";
                        for(let items_index in each_output["desc_items"]){
                            html_element = html_element + "<li>"+each_output["desc_items"][items_index]+"</li>";
                        }
                        html_element = html_element + "</ul>";
                    }
                }
                html_element = html_element + "</div></div></div>";

                $(function() {
                    $("#content2").find(".timeline-wrapper#"+key_log_name+" .timeline").append(html_element);
                });
                for(let i in add_image_ids){
                    set_luminous(add_image_ids[i])
                }
            }
            global_loaded_history["output"][key_log_name]["read_output"] += output_json_data[index][key_log_name]["data"].length;
        }
    }
}

function update_data(json_data){
    update_csv_data(json_data["log_data"])
    update_output(json_data["output_data"])
    //update_new_data()
    //set_luminous()
}

/*
    in the case of,
    when the first update_log is called,
    and waiting the .onload to start.
    then, a new call of update_log has been occured.
    the passing parameter might be contradicted.

    is it possible to rewrite this function with
    promise, async and await?
*/ 
function update_log(){
    if(global_fetch_update_go){
        var req_update_log = new XMLHttpRequest();
        req_update_log.open("POST", '/api/logs/update', true);
        req_update_log.setRequestHeader("Content-Type", "application/json");
        // async
        req_update_log.onload = function(){
            //parse_update();
            //console.log(req_update_log.responseText);
            update_data(JSON.parse(req_update_log.responseText));
            if(global_update_re_request){
                global_update_re_request = false;
                update_log();
            }else{
                global_fetch_update_go = true;
            }
        }
        req_update_log.send(JSON.stringify(create_update_query_json()));
        global_fetch_update_go = false;
        console.log("update called");
    }else{
        console.log("now calling, wait.");
    }
}

function clear_interval(interval_id){
    clearInterval(interval_id);
}

function update_watch_list(log_id, assign){
    if(assign){
        if(global_watch_list.indexOf(log_id) < 0){
            global_watch_list.push(log_id);
        }
    }else{
        global_watch_list = global_watch_list.filter(log_name => log_name != log_id);
    }
}

function update_load_output_list(log_id, assign){
    if(assign){
        if(global_load_output_list.indexOf(log_id) < 0){
            global_load_output_list.push(log_id);
        }
        update_log();
        update_checker = setInterval(update_log, update_interval_slider.value*base_time_interval*1000);
    }else{
        global_load_output_list = global_load_output_list.filter(log_name => log_name != log_id);
    }
}

function update_graph_smoothing(smooth){
    console.log("smooth")
    if(smooth){
        ;
    }else{
        ;
    }
}

function set_luminous(img_id){
    var luminousTrigger = document.getElementById(img_id);
    new LuminousGallery([luminousTrigger], {}, {
        caption: function (trigger) {
        return trigger.querySelector('img').getAttribute('alt');}
    });
    /*
    var luminousTrigger = document.getElementById(img_id);
    new Luminous(luminousTrigger, {}, {
        caption: function (trigger) {
        return trigger.querySelector('img').getAttribute('alt');}
    });
    */
}

function init_load() {
    var req = new XMLHttpRequest();
    req.open("GET", '/api/logs', true);
    req.onload = function() {
        json_data = JSON.parse(req.responseText);
        create_html_element(json_data)
        parse_log_data(json_data, true);
        init_charts()
    }
    req.send(null);
    
    var req_update_settings = new XMLHttpRequest();
    req_update_settings.open("POST", '/api/update_settings', true);
    req_update_settings.setRequestHeader("Content-Type", "application/json");
    // async
    req_update_settings.onload = function() {
        console.log(req_update_settings.responseText)
    }
    var data = JSON.stringify(global_settings);
    req_update_settings.send(data);
    // then if onload req_update_settings.onload will be exec
}

init_load();
