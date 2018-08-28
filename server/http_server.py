import os
import yaml
import json
import re
import threading
import traceback

import base64
from flask import Flask, render_template, redirect, request
from flask_classful import FlaskView, route
from jinja2 import FileSystemLoader

from PIL import Image

from ..utilities.path_util import isdir, isexist
from ..global_names import global_names

print_error = False

def print_error(e):
    traceback.print_exc()
    print(e)

def get_log_folder_names(log_dir):
    """
        get the log folder list
    """

    log_list = []
    folder_list = os.listdir(log_dir)
    for folder in folder_list:
        folder_path = os.path.join(log_dir, folder)
        if isdir(folder_path):
            folder_files = os.listdir(folder_path)
            if global_names.log_info_file_name in folder_files:
                log_list.append(folder)

    return log_list

def fetch_data(fetch_query, exclude_namespace=[]):
    """
        read data from log file and return the parsed data
    """
    if isexist(fetch_query):
        return parse_log(fetch_query, exclude_namespace)
    else:
        return {}

def parse_log(log_folder, exclude_namespace=[]):
    """
        parse log data and convert to dictionary
    """

    parsed_data = {"data":{}}

    with open(os.path.join(log_folder, global_names.log_info_file_name), "r") as f:
        parsed_data["info"] = yaml.load(f)

    for namespace in parsed_data["info"]["log_info"]["namespaces"]:
        if namespace in exclude_namespace:
            continue

        with open(os.path.join(log_folder, parsed_data["info"]["log_info"]["logs"][namespace]["file_name"]), "r") as f:
            parsed_data["data"][namespace] = f.read()

    return parsed_data

def fetch_csv_data(log_name, log_folder, request_dict):
    requested_csv_data = {log_name:{"data":{}}}

    try:
        with open(os.path.join(log_folder, global_names.log_info_file_name), "r") as f:
            yaml_data = yaml.load(f)

        for namespace in request_dict:
            try:
                fetch_request_line = request_dict[namespace]["request"]

                with open(os.path.join(log_folder, yaml_data["log_info"]["logs"][namespace]["file_name"]), "r") as f:
                    csv_data = f.read()

                find_result = re.finditer("\n", csv_data)
                for i, find in enumerate(find_result):
                    if i == fetch_request_line-1:
                        requested_csv_data[log_name]["data"][namespace] = csv_data[0:re.search("\n", csv_data).end()] + csv_data[find.end():]
                        break

            except Exception as e:
                if print_error:
                    print_error(e)

    except Exception as e:
        if print_error:
            print_error(e)

    return requested_csv_data

def fetch_output_data(log_name, log_folder, request_dict):
    requested_csv_data = {log_name:{"data":[]}}

    try:
        # open the schema list file.
        with open(os.path.join(log_folder, global_names.output_schema_file_name), "r") as f:
            schema_list = f.read().split("\n")

        # avoid [''] data for raising up error
        if len(schema_list[0]) < 1:
            return requested_csv_data

        for index in range(request_dict["request"], len(schema_list)):
            if len(schema_list[index]) > 0:
                try:
                    with open(os.path.join(log_folder, schema_list[index]), "r") as f:
                        yaml_data = yaml.load(f)

                    output = {"output_name":yaml_data["output_name"], "output_desc":yaml_data["output_desc"], "outputs":[]}
                    for pack in yaml_data["outputs"]:
                        output["outputs"].append({"images":[]})
                        for i, img_name in enumerate(pack["image"]):
                            img_name = re.search("/[^\n]*\Z", pack["image"][i]).group().replace("/", "")
                            img_type = re.search(".[a-zA-z]*\Z", pack["image"][i]).group().replace(".", "")
                            output["outputs"][-1]["images"].append({"data":base64.encodestring(open(os.path.join(log_folder, pack["image"][i]), "rb").read()).decode("utf-8"),
                                                                    "name":img_name,
                                                                    "type":img_type})

                        output["outputs"][-1]["desc"] = pack["desc"]
                        output["outputs"][-1]["desc_items"] = pack["desc_items"]

                    if len(output) > 0:
                       requested_csv_data[log_name]["data"].append(output)

                except Exception as e:
                    if print_error:
                        print_error(e)
    
    except Exception as e:
        if print_error:
            print_error(e)

    return requested_csv_data

def fetch_new_data(log_dir, known_dict):
    new_data = []

    log_folders = get_log_folder_names(log_dir)

    for log_name in log_folders:
        exclude_names = []
        if log_name in known_dict:
            exclude_names = known_dict[log_name]["namespaces"]

        data_dict = fetch_data(os.path.join(log_dir, log_name), exclude_namespace=exclude_names)
        if len(data_dict["data"]) != 0:
            new_data.append({log_name:data_dict})

    return new_data

def fetch_update(json_data, log_dir):
    """
        reponse json is like

        {
            "log_data":[
                {
                    "log_name":{
                        data": {
                            "namespace": data with header, 
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
    """

    return_data = {"log_data":[], "output_data":[], "new_data":[]}

    print(json_data)

    for log_name in json_data["log"]:
        return_data["log_data"].append(fetch_csv_data(log_name, os.path.join(log_dir, log_name), json_data["log"][log_name]))

    for log_name in json_data["output"]:
        return_data["output_data"].append(fetch_output_data(log_name, os.path.join(log_dir, log_name), json_data["output"][log_name]))

    return_data["new_data"] = fetch_new_data(log_dir, json_data["known"])

    return return_data

class APIView(FlaskView):
    log_dir = "log"
    log_settings = {}

    @classmethod
    def set_log_directory(cls, log_dir_path):
        cls.log_dir = os.path.expanduser(log_dir_path)

    @route('/logs/list')
    def log_list(self):
        return_data = {"logs_list":get_log_folder_names(self.log_dir)}
        return json.dumps(return_data)

    def logs(self):
        return_data = {"log_data":[]}
        log_folders = get_log_folder_names(self.log_dir)

        for log_name in log_folders:
            data_dict = fetch_data(os.path.join(self.log_dir, log_name))
            if len(data_dict) != 0:
                return_data["log_data"].append({log_name:data_dict})

        return json.dumps(return_data)

    @route('/logs/update', methods=["POST"])
    def logs_update(self):
        """
            request.get_json() is like

            {
                'log': {
                    'log_name': {
                        'namespace1': {'read': 10},
                        'namespace2': {'read': 10},
                        ...
                    }
                },

                'output': {
                    'log_name':{'read': 0},
                    ...
                },

                'known': {
                    'log_name': {'namespaces': ['namespace1', 'namespace2', ...]},
                    ...
                }
            }
        """

        client_request = request.get_json()

        return json.dumps(fetch_update(client_request, self.log_dir))

    def log(self, log_name):
        return_data = {"log_data":[]}
        data_dict = fetch_data(os.path.join(self.log_dir, log_name))
        
        if len(data_dict) != 0:
            return_data["log_data"] = {log_name:data_dict}

        return json.dumps(return_data)

    @route('/update_settings', methods=["POST"])
    def update_settings(self):
        # only when POSTed data is valid json, get_json method return the data otherwise None
        #print(request.headers)
        self.log_settings = request.get_json()
        print(self.log_settings)
        return json.dumps({"status":"OK"})

class MainView(FlaskView):
    route_base = "/"

    def index(self):
        return render_template('index.html', title='main')

class HTTPServer(object):
    def __init__(self, log_dir, name="http server for train logger", bind_host="", bind_port=8080, quiet=False):
        # black magic... but we need this module path...
        try:
            raise
        except Exception as e:
            import traceback
            for traceback_line in traceback.format_stack():
                file_line = re.search('\s*File\s[^\n]*/http_server.py', traceback_line)
                if file_line is not None:
                    file_line_str = file_line.group()
                    self.this_module_path = re.sub("http_server.py", "", re.sub('\s*File\s"', "", file_line_str))

        self.log_dir = log_dir
        self.name = name
        self.bind_host = bind_host
        self.bind_port = bind_port

        self.main_thread = None
        self.app = Flask(self.name, static_folder=self.this_module_path+"/static", template_folder=self.this_module_path+"/templates")

        MainView.register(self.app)

        APIView.set_log_directory(self.log_dir)
        APIView.register(self.app)

        if quiet:
            import logging
            log = logging.getLogger("werkzeug")
            log.disabled = True
            self.app.logger.disabled = True

    def start(self, use_thread=False):
        if use_thread:
            self.main_thread = threading.Thread(target=self.app.run, args=(self.bind_host, self.bind_port))
            self.main_thread.daemon = True
            self.main_thread.start()
        else:
            self.app.run(host=self.bind_host, port=self.bind_port)

"""
if __name__ == '__main__':
    app = Flask("only watching")
    log_dir = ""

    APIView.set_log_directory(log_dir)
    APIView.register(app)

    MainView.register(app)

    # stop console log output of flask server
    #import logging
    #log = logging.getLogger("werkzeug")
    #log.setLevel(logging.ERROR)
    # really disable
    #log.disabled = True
    #app.logger.disabled = True

    app.run(host='0.0.0.0', port=8084)
"""
