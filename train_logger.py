import os
import sys
import signal
import threading
import traceback
from datetime import datetime

import git
import yaml

from .global_names import global_names
from .logger import LogWriter, OutputWriter
from .server import http_server
from .server.http_server import HTTPServer
from .server.message_server import MessageLogServer
from .utilities.path_util import mkdir
from .utilities import terminal_color

HAS_NOTI = True
# just in case
try:
    from ..notificator import Notificator
except Exception as e:
    traceback.print_exc()
    print(e)
    print("running without notificator.")
    HAS_NOTI=False

def print_error(e):
    traceback.print_exc()
    print(e)

def color_print(msg, fg, bg):
    print("{}{}{}{}{}".format(bg, fg, msg, terminal_color.fg.END, terminal_color.bg.END))

class TrainLogger(object):
    """
        wrapper of logger.LogWriter
    """

    has_noti = HAS_NOTI
    log_info_file_name = global_names.log_info_file_name
    output_schema_file_name = global_names.output_schema_file_name

    message_timestamp_format = "[{}]"
    message_tag_format = "[{}]"
    message_namespace_format = "{}::"
    message_format = "{}"

    def __init__(self, log_dir="./log", log_name="log_output", namespaces=None, arguments=None, notificate=False, suppress_err=True, visualize_fetch_stride=1):
        """
            log_dir: str
                root directory of saving log.

            log_name: str
                name of the log. the folder named `log_name` will be created
                and logs will be saved in this folder.

            namespaces: dict
                it must be consist of {"namespace1":["header1", "header2", ...], "namespace2":[...], ...}
                for example,
                    {"train":["epoch", "loss"], "val":["epoch", "score1", "score2"]}
                    in this case, there are two `namespace`: "train" and "val", and namespace will separate log.
                    for ["epoch", "loss"] and so on, there are used for headers in csv.
                    parameter at `log` method should be in this header order too.

            arguments: list of tuple, or dict
                if your are using argparse, you can use `_get_kwargs` method to get
                the list of tuple of argument.

            notificate: bool
                use notificator module.

            suppress_err: bool
                suppress the errors. if you want to see the error, set to False.

            visualize_fetch_stride: int
                stride num of visualization with http server.
                only effect on csv logs.
                log graph will print out with this stride at x-axis.
                if you set this to 10, and the x-axis start from 1,
                fetched data's axis value will be like 1, 10, 20, ...
                first row will be always fetched.

            ####################################################################
            file trees
                log_dir/
                    |- log_name_yyyymmdd_hh-mm-ss/
                    |   |- log_info.yaml                            # hold information of the log
                    |   |- name_space1_yyyymmdd_hh-mm-ss.csv        # csv data for the each namespace output
                    |   |- name_space2_yyyymmdd_hh-mm-ss.csv        
                    |   |- ...
                    |   |- log_name_message_yyyymmdd_hh-mm-ss.txt   # if you use msg_server, the log will save in it.
                    |   |...
                    |   |- outputs/
                    |       |- images/
                    |       |   |- img_1                            # the image output when you save with pack_output method
                    |       |   |- ...
                    |       |
                    |       |- output_1.yaml                        # image information and the description which is packed will be
                    |       |- output_2.yaml                        # saved in here
                    |       |- ...
                    |
                    |- ...

            `http_server` will watch all logs in `log_dir`.
        """

        self.log_dir = log_dir
        self.log_name = log_name.replace(" ", "_")
        self.arguments = arguments
        self.suppress_err = suppress_err
        self.visualize_fetch_stride = visualize_fetch_stride
        self.timestamp_for_file = "{}".format(datetime.now().strftime("%Y%m%d_%H-%M-%S"))
        self.timestamp = self.timestamp_for_file.replace("-", ":").replace("_", " ")
        self.log_save_path = os.path.join(self.log_dir, "{}_{}".format(self.log_name, self.timestamp_for_file))
        self.msg_filename = self.log_name+"_message_{}.txt".format(self.timestamp_for_file)

        # making folder for logs
        mkdir(os.path.join(self.log_dir, log_name+"_"+self.timestamp_for_file))

        self.namespace_dict = {}
        self.log_writer = {}
        self.git_info = None
        self.http_server = None
        self.msg_server = None
        self.msg_logger = open(os.path.join(self.log_save_path, self.msg_filename), "w")
        self.output_writer = OutputWriter(schema_list_name=self.output_schema_file_name,
                                          output_root=self.log_save_path,
                                          msg_logger=self.msg_logger,
                                          suppress_err=self.suppress_err)

        # setting up notificator
        if self.has_noti and notificate:
            self.notificator = Notificator(suppress_err=suppress_err)
        else:
            self.notificator = None

        if namespaces is not None:
            self.add_log_namespace(namespaces)
        else:
            self.__make_log_info_file()

        signal.signal(signal.SIGTERM, self.__detect_kill)
        signal.signal(signal.SIGINT, self.__detect_ctrl_c)

    def __detect_kill(self, signal, frame):
        self.log_message("detect signal: SIGTERM, num:{}".format(signal), "INFO", "train_logger")
        sys.exit(0)

    def __detect_ctrl_c(self, signal, frame):
        self.log_message("detect signal: SIGINT, num:{}".format(signal), "INFO", "train_logger")
        sys.exit(0)

    def __make_log_info_file(self):
        self.log_info_data = self.__get_log_info()
        self.log_info_data["fetch_stride"] = self.visualize_fetch_stride

        try:
            if isinstance(self.arguments, dict):
                self.log_info_data["arguments"] = []
                for (key, val) in self.arguments.items():
                    self.log_info_data["arguments"].append({key:val})
            elif isinstance(self.arguments, list) and isinstance(self.arguments[0], tuple):
                self.log_info_data["arguments"] = []
                for (key, val) in self.arguments:
                    self.log_info_data["arguments"].append({key:val})
        except:
            self.log_info_data["arguments"] = []

        self.log_info_writer = open(os.path.join(self.log_save_path, self.log_info_file_name), "w")
        self.log_info_writer.write(yaml.dump(self.log_info_data, default_flow_style=False))
        self.log_info_writer.flush()

    def __get_log_info(self):
        log_info_data = {"log_name":self.log_name,
                         "timestamp":self.timestamp,
                         "log_info":{
                                     "namespaces": list(self.namespace_dict.keys()),
                                     "logs":{}
                                     }
                        }
        for namespace in self.namespace_dict.keys():
            log_info_data["log_info"]["logs"][namespace] = {"file_name":"{}_{}.csv".format(namespace, self.timestamp_for_file)}
        
        log_info_data["git_info"] = self.__get_info()
        
        return log_info_data

    def __get_info(self):
        if self.git_info is None:
            try:
                repo = git.Repo(search_parent_directories=True)
                curr_branch = str(repo.active_branch)
                sha = repo.head.object.hexsha
                self.git_info = {"branch_name":curr_branch, "branch_hash":sha}
            except:
                #print("not in git repository")
                self.git_info = {"branch_name": "no data", "branch_hash": "no data"}

        return self.git_info

    def mkdir(self, path):
        joint_path = os.path.join(self.log_save_path, path)
        mkdir(joint_path)

        return joint_path

    def add_log_namespace(self, namespaces):
        for name, headers in namespaces.items():
            self.log_writer[name] = LogWriter(file_name=name, log_dir=self.log_save_path, log_dict_key="log",
                                              csv=True, header=headers, csv_separator=",",
                                              timestamp=True, flush_always=True, buff_size=1, blocking=False,
                                              suppress_err=self.suppress_err, timestamp_str=self.timestamp_for_file)
            self.namespace_dict[name] = headers
            # this call is not good...
            self.__make_log_info_file()

    def enable_pickle_log(self):
        self.log_writer.enable_pickle_object()

    def start_msg_server(self, bind_host="127.0.0.1", bind_port=8082):
        self.msg_bind_host=bind_host if bind_host != "" else "0.0.0.0"
        self.msg_bind_port=bind_port

        color_print("trying to start message server...", terminal_color.fg.BLACK, terminal_color.bg.GREEN)
        try:
            self.msg_server = MessageLogServer(os.path.join(self.log_save_path, self.msg_filename),
                                               self.msg_bind_host, self.msg_bind_port, 8, blocking=False)
            self.msg_server.start(use_thread=True)
            color_print("message server hosted on {host}:{port}".format(host=self.msg_bind_host, port=self.msg_bind_port),
                        terminal_color.fg.BLACK,
                        terminal_color.bg.GREEN)

        except Exception as e:
            if not self.suppress_err:
                print_error(e)
                color_print("starting with out message server.", terminal_color.fg.WHITE, terminal_color.bg.RED)

    def start_http_server(self, bind_host="127.0.0.1", bind_port=8080):
        if not http_server.SERVER_MODULE_MISSING:
            self.http_bind_host=bind_host if bind_host != "" else "0.0.0.0"
            self.http_bind_port=bind_port

            color_print("trying to start http server...", terminal_color.fg.BLACK, terminal_color.bg.GREEN)
            try:
                self.http_server = HTTPServer(log_dir=self.log_dir, bind_host=self.http_bind_host, bind_port=self.http_bind_port, quiet=True)
                self.http_server.start(use_thread=True)
                color_print("http server hosted on {host}:{port}".format(host=self.http_bind_host, port=self.http_bind_port),
                            terminal_color.fg.BLACK,
                            terminal_color.bg.GREEN)

            except Exception as e:
                if not self.suppress_err:
                    print_error(e)
                    color_print("starting with out http server.", terminal_color.fg.WHITE, terminal_color.bg.RED)
        else:
            color_print("module missing, failed to start http server.", terminal_color.fg.WHITE, terminal_color.bg.RED)

    def set_notificator(self, params=["mail", "slack", "twitter"]):
        try:
            if self.notificator is not None and isinstance(params, list):
                for p in params:
                    if p.lower() == "mail":
                        self.notificator.setMail()

                    elif p.lower() == "slack":
                        self.notificator.setSlack()

                    elif p.lower() == "twitter":
                        self.notificator.setTwitter()
        except Exception as e:
            self.log_message("{}".format(e), "ERROR, INTERNAL", "train_logger::notificate")

    def notify(self, msg, use_thread=True):
        """
            send notification using notification module.
        """
        if self.notificator is not None:
            self.notificator.notify(msg, use_thread)

    def show_header(self, log_namespace):
        self.log_writer[log_namespace].show_header()

    def headers(self, log_namespace):
        self.log_writer[log_namespace].headers()

    def log(self, log_namespace, log_data):
        try:
            self.log_writer[log_namespace].log(log_data)
        except Exception as e:
            if not self.suppress_err:
                print_error(e)

    def log_message(self, message, message_tag, log_namespace, thread=True):
        log_message = "{time}{tag}{namespace}{msg}".format(
                        time=self.message_timestamp_format.format(datetime.now().strftime("%Y%m%d %H:%M:%S")),
                        tag=self.message_tag_format.format(message_tag),
                        namespace=self.message_namespace_format.format(log_namespace),
                        msg=self.message_format.format(message))

        self.msg_logger.write(log_message+"\n")
        self.msg_logger.flush()

        if self.msg_server is not None:
            if thread:
                try:
                    th = threading.Thread(target=self.__log_msg, args=(log_message,))
                    th.start()
                except Exception as e:
                    if not self.suppress_err:
                        import traceback
                        traceback.print_exc()
                        print(e)
            else:
                self.msg_server.log(log_message)

    # for threadding 
    def __log_msg(self, msg):
        self.msg_server.log(msg)

    def setup_output(self, name, desc="", img_name_preffix="_img", img_ext=".png"):
        self.output_writer.setup(name.replace(" ", "_"), desc, img_name_preffix, img_ext)

    def pack_output(self, img=None, desc="", desc_items=[], additional_name="", not_in_schema=False):
        self.output_writer.pack(img, desc, desc_items, additional_name.replace(" ", "_"), not_in_schema)

    def flush_output(self):
        self.output_writer.flush()

    def close(self):
        for logger in self.log_writer.values():
            logger.close()

        self.log_info_writer.close()
        self.msg_logger.close()

        if self.msg_server is not None:
            self.msg_server.stop()
