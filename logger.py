import os
import threading
import random
from datetime import datetime

import pickle
import yaml
import numpy as np
from PIL import Image

from .utilities.path_util import mkdir
from .global_names import global_names

HAS_TB = True
HAS_GS_ENNV = True

# It's not a major libraries that are in anaconda, so I will check them for you.
try:
    from tensorboardX import SummaryWriter
except Exception as e:
    #import traceback
    #traceback.print_exc()
    #print("exec. without tensor board.")
    HAS_TB = False

try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
except Exception as e:
    #import traceback
    #traceback.print_exc()
    #print("exec. without google spreadsheet.")
    HAS_GS_ENNV = False

class LogWriter(object):
    has_tensorboard = HAS_TB
    has_gs = HAS_GS_ENNV

    # api endpoint
    gs_scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive.file']
    
    # google spreadsheet api limitation?
    # actually I think the default worksheet row, col are size of 1000, 26.
    # so this is migth be the limitation.
    row_limit = 1000
    col_limit = 26

    newline_char = "\n"
    newline_char_replace = " "

    def __init__(self, file_name, log_dir="./log", log_dict_key="log", header=None, 
                 csv=False, csv_separator=",",
                 use_tensorboradx=False,
                 gspread_credential_path=None, gspread_share_account="", init_row=1, init_col=1,
                 timestamp=True, flush_always=True, buff_size=1, blocking=False, suppress_err=True,
                 log_msg_in_one_line=True, timestamp_str=None):
        """
            file_name: str
                the file name which you want to use.
                should be without extension, otherwise it would be like "hoge.csv.csv"
            
            log_dir: str
                the saving directory of the log.
                it would be saved like log_dir/file_name.

            log_dict_key: str
                key of the log in the dictionary self.log_dict.

                    self.log_dict = {self.log_dict_key:[], self.log_dict_msg_key:[]}

            log_dict_msg_key: str
                key of the message log of dictionary self.log_dict.

            header: list of str
                header name, and also recored in this order.

            csv: bool
                save the log in .csv file or not.
            
            csv_separator: str
                separating charactor of csv file.

            use_tensorboradx: bool
                use tensorboadX or not.

            gspread_cred_path: str
                the paht of google API's credentials json file.
                if you set the json file path it enable the logging to the google spreadsheet.
            
            gspread_share_account: str
                the sharing account string.
                you need set your google account to access to the spreadsheet.
                because the created spreadsheet allows the access from API account for initial.
            
            init_row: int
                starting row.

            init_col: int
                starting col.

            timestamp: bool
                use time stamp for file name. it's for avoiding overwriting the existing file.
                I know you will think like "Hey please check, Is the file name exist or not, and give a new name."
                yeah, I'll do it someday...

            flush_always: bool
                always flush the log to the file or not.
            
            buff_size: int
                buffer size. I'm not sure this is useful...
                recommend in size 1, but sometimes you want buff it?

            blocking: bool
                block until the logging finishes.
                sometimes google spreadsheed or other things take time,
                so if you don't want to get disturb, set this False.
                using thread, for a short interval to write a log, it might cause some trouble of order,
                I recommend to set a order number to log output.

            suppress_err: bool
                suppress the error logs.

            log_msg_in_one_line: bool
                if this is True, "\n" will be replace to " " in default setting.
                actually, it is not implemented yet.

        """

        self.log_dir = log_dir
        self.file_name = file_name
        self.log_dict_key = log_dict_key

        self.use_pickle_obj = False
        self.set_tbkey = False

        self.buffer = []
        self.buff_size = buff_size
        self.flush_always = flush_always
        self.timestamp = timestamp
        self.blocking = blocking
        self.suppress_err = suppress_err
        
        self.log_dict = {self.log_dict_key:[]}

        self.use_csv = csv
        self.csv_separator = csv_separator

        self.use_tb = use_tensorboradx if self.has_tensorboard else False

        # google spread sheet setting
        self.init_row = init_row if init_row > 0 else 1
        self.init_col = init_col if init_col > 0 else 1
        self.count_row = 0
        self.count_col = 0
        self.sheet_count = 1

        self.csv_logger = None
        self.tb_logger = None
        self.gs_logger = None
        self.gs = None

        self.csv_filename = None
        self.tb_filename = None
        self.gs_filename = None

        self.status_separator = ": "

        if use_tensorboradx and self.has_tensorboard is False:
            if suppress_err == False:
                print("# exec. without tensorboeardX.")

        mkdir(self.log_dir)

        if timestamp_str is not None and isinstance(timestamp_str, str):
            self.ts_str = timestamp_str
        else:
            self.ts_str = "{}".format(datetime.now().strftime("%Y%m%d_%H-%M-%S"))

        if self.use_csv:
            self.csv_filename = self.file_name+"{}".format("_{}.csv".format(self.ts_str) if timestamp else ".csv")
            self.csv_logger = open(os.path.join(self.log_dir, self.csv_filename), "w")

        if self.use_tb:
            self.tb_filename = self.file_name+"{}".format("_{}_tb".format(self.ts_str) if timestamp else "_tb")
            self.tb_logger = SummaryWriter(log_dir=os.path.join(self.log_dir, self.tb_filename))

        if gspread_credential_path is not None and self.has_gs:
            try:
                credentials = ServiceAccountCredentials.from_json_keyfile_name(gspread_credential_path, self.gs_scope)
                self.gs = gspread.authorize(credentials)
                self.gs_filename = self.file_name+"{}".format("_{}".format(self.ts_str if timestamp else ""))
                self.gs_sh = self.gs.create(self.gs_filename)

                # without shareing, we can't access to the spread sheet.
                self.gs_sh.share(gspread_share_account, perm_type='user', role='writer')

                # somehow, I can't rename the title of the sheet, so I append new one and delete the default sheet
                self.gs_logger = self.gs_sh.add_worksheet(title=self.file_name, rows="{}".format(self.row_limit), cols="{}".format(self.col_limit))
                wks = self.gs_sh.get_worksheet(0)
                self.gs_sh.del_worksheet(wks)

            except Exception as e:
                if suppress_err == False:
                    import traceback
                    traceback.print_exc()
                    print("exec. without google spreadsheet.")
                HAS_GS_ENNV = False

        if header is not None:
            self.set_header(header)
        else:
            self.header = None

    def log(self, data):
        """
            args:
                data: list
                    it must be a list of data what you want to log,
                    and the length of the lsit must be same as self.log_dict_key

            if self.blocking is False, it will log with another thread
        """

        self.buffer.append(data)

        if len(self.buffer) >= self.buff_size:
            if self.blocking:
                for i in range(len(self.buffer)):
                    self._log(self.buffer.pop(0))
            else:
                try:
                    th = threading.Thread(target=self._thread_log, args=(self.buffer,))
                    th.start()
                    self.buffer = []
                except Exception as e:
                    # for it's a critical part, I won't suppress here
                    import traceback
                    traceback.print_exc()
                    print(e)

    def enable_pickle_object(self):
        # if you want to save dictonary object of log.
        self.use_pickle_obj = True

    def set_header(self, keys):
        """
            because of default logging is dictonary, we need a key.
            this might be not good way for default.
            I might fix it someday.
        """
        assert isinstance(keys, list), "header key is not a list"

        self.header = keys

        if self.use_csv:
            self._csv_header(keys)
            if self.flush_always:
                self.csv_logger.flush()
        if self.gs is not None:
            self._gs_header(keys)

    def set_default_tbkeys(self, keys):
        """
            tensorboeard has different namespace system
        """
        if self.use_tb:
            self.set_tbkey = True
            self.default_dic_tbkey = keys

    def show_header(self):
        print(self.header)

    def headers(self):
        return self.header

    def addAppendLogDic(self, key, value):
        """
            thiking for adding information like
            how many epochs or starting time and so on.
            not for the sequential data.
        """
        if key in log_dict:
            hash = random.getrandbits(32)
            key = "{:x}_".format(hash)+key
            if suppress_err == False:
                print("key conflict, change to {}".format(key))

        self.log_dict[key] = value

    def close(self):
        """
            in some case, it might cause a messing log order beecause of using threads
            I am not waiting other threads to be finished now.
            for avoiding this case, I recommend using buffer size to be 1.
        """

        for i in range(len(self.buffer)):
            self._log(self.buffer.pop(0))

        if self.use_pickle_obj:
            with open(os.path.join(self.log_dir, self.file_name+"{}".format("_{}.pkl".format(self.ts_str if self.timestamp else ".pkl"))), "wb") as pickle_file:
                pickle.dump(self.log_dict, pickle_file)

        if self.csv_logger is not None:
            self.csv_logger.close()

        if self.tb_logger is not None:
            self.tb_logger.close()

    def _csv_header(self, keys):
        for key in keys:
            if key != keys[0]:
                self.csv_logger.write(self.csv_separator)
            self.csv_logger.write(str(key))
        self.csv_logger.write("\n")
        if self.flush_always:
            self.csv_logger.flush()

    def _gs_header(self, keys):
        self.count_col = 0
        for key in keys:
            self.gs_logger.update_cell(self.init_row+self.count_row, self.init_col+self.count_col, str(key))
            self.count_col += 1

        self.count_row += 1

    def _log(self, data):
        if self.use_pickle_obj:
            self._log_dic(data)

        if self.use_csv:
            self._log_csv(data)
        
        if self.use_tb:
            self._log_tb(data)

        if self.gs is not None:
            self._log_gs(data)

    def _thread_log(self, data):
        for d in data:
            self._log(d)

    def _log_dic(self, data):
        assert len(self.header) == len(data), "keys and data has not same length."
        assert self.header is not None, "no header keys"

        self.log_dict[self.log_dict_key].append({})

        for key, val in zip(self.header, data):
            self.log_dict[self.log_dict_key][-1][key] = val

    def _log_csv(self, data):
        if self.header is None:
            for i, val in enumerate(data):
                if i != 0:
                    self.csv_logger.write(self.csv_separator)
                self.csv_logger.write(str(val))
            self.csv_logger.write("\n")
        else:
            for key, val in zip(self.header, data):
                if key != self.header[0]:
                    self.csv_logger.write(self.csv_separator)
                self.csv_logger.write(str(val))
            self.csv_logger.write("\n")
        
        if self.flush_always:
            self.csv_logger.flush()

    def _log_tb(self, data):
        assert len(self.default_dic_tbkey) == len(data), "keys and data has not same length."
        assert self.set_tbkey, "no default keys"

        for key, val in zip(self.header, data):
            self.tb_logger.add_scalar(key, val)

    def _log_gs(self, data):
        """
            cell is
                A B C
               ------>
            1 |
            2 |
            3 v

            which is ('B1') -> (1, 2)
        """
        self.count_col = 0
        for d in data:
            self.gs_logger.update_cell(self.init_row+self.count_row, self.init_col+self.count_col, d)
            self.count_col += 1
            if self.count_col >= self.row_limit:
                self.sheet_count += 1
                self.gs_logger = self.gs_sh.add_worksheet(title=self.file_name+"_{}".format(self.sheet_count), rows="{}".format(self.row_limit), cols="{}".format(self.col_limit))

        self.count_row += 1

    # not thinking to use
    def _write_log(self, key, value):
        self.log_dict[key] = value

    # not thinking to use
    def _write_csvlog(self, data):
        if self.use_csv:
            self.csv_logger.write(data)
            if self.flush_always:
                self.csv_logger.flush()

    def _write_tblog(self, name_space, val, iter_num=None):
        if self.use_tb:
            if iter_num is not None:
                self.tb_logger.add_scalar(name_space, val, iter_num)
            else:
                self.tb_logger.add_scalar(name_space, val)

class OutputWriter(object):
    output_folder = global_names.output_folder
    output_image_folder = global_names.output_image_folder

    def __init__(self, schema_list_name="output_schema_list.txt", output_root="./log", blocking=False, suppress_err=True, msg_logger=None):
        """ 
            args:
                schema_list_name: str
                    file name of schema list file.
                    all the path of schema file will be written in here.

                output_root: str
                    the saving directory of the log.
                    output folder which containing schema file will be created in here 

                blocking: bool
                    block until the logging finishes.

                suppress_err: bool
                    suppress the error logs.
                    actually, it doesn't have any function yet.

                msg_logger: message_server.MessageLogServer
                    it will write out the error log through this.
        """

        self.schema_list_name = schema_list_name
        self.output_root = output_root
        self.output_schema_dir = os.path.join(self.output_root, self.output_folder)
        self.output_image_dir = os.path.join(self.output_schema_dir, self.output_image_folder)
        self.schema_base = self.output_folder
        self.output_image_base = os.path.join(self.schema_base, self.output_image_folder)

        self.blocking = blocking
        self.suppress_err = suppress_err
        self.msg_logger = msg_logger

        self.output_name = None
        self.output_desc = None
        self.schema_list_logger = open(os.path.join(self.output_root, self.schema_list_name), "w")
        self.schema_writer = None

        mkdir(self.output_root)
        mkdir(self.output_schema_dir)
        mkdir(self.output_image_dir)

    def setup(self, name, desc, img_name_preffix="_img", img_ext=".png"):
        """
            args:
                data: list
                    it must be a list of data what you want to log,
                    and the length of the lsit must be same as self.log_dict_key

            if self.blocking is False, it will log with another thread

                    name     |  ________
                        desc | |        |
                             | |  img   |
                             | |        |
                             | |________|
                             |  pack:desc
                             |  - pack:desc_items[0]
                             |  - pack:desc_items[1]
                             |  - pack:desc_items[2]

                pack:~ is value of pack function
        """

        self.output_name = name
        self.output_desc = desc
        self.img_name_preffix = img_name_preffix
        self.img_ext = img_ext

        self.img_count = 0

        self.schema_writer = open(os.path.join(self.output_schema_dir, self.output_name+".yaml"), "w")

        self.schema = {"output_name":self.output_name, "output_desc":self.output_desc, "outputs":[]}

    def pack(self, img=None, desc="", desc_items=[]):
        """
            img:
                for image

            desc: str
            desc_items: list of str

            on the output tab on web browser, it show up like

                setup_output:name     |  ________
                    setup_output:desc | |        |
                                      | |  img   |
                                      | |        |
                                      | |________|
                                      |  desc
                                      |  - desc_items[0]
                                      |  - desc_items[1]
                                      |  - desc_items[2]

                setup_output:~ is value of setup_output function

            if you don't set any desc and desc_items,
            you can line up the images.
            when you call twice, it will look like

            setup_output:name         |  ________   ________
                    setup_output:desc | |        | |        |
                                      | |  img1  | |  img2  |
                                      | |        | |        |
                                      | |________| |________|
                                      |  

            also multiple img of argument will do the same thing.

            setup_output:name         |  ________   ________
                    setup_output:desc | |        | |        |
                                      | |  img1  | |  img2  |
                                      | |        | |        |
                                      | |________| |________|
                                      |  desc
                                      |  - desc_items1[0]
                                      |  - desc_items2[1]
                                      |  - desc_items3[2]
        """

        if self.schema_writer is not None:
            self.schema["outputs"].append({"image":self.__save_image(img), "desc":desc, "desc_items":desc_items})

    def flush(self):
        self.schema_list_logger.write(os.path.join(self.schema_base, self.output_name+".yaml")+"\n")
        self.schema_list_logger.flush()

        if self.schema_writer is not None:
            if self.blocking:
                self.schema_writer.write(yaml.dump(self.schema, default_flow_style=False))
                self.schema_writer.close()
                self.schema_writer = None
            else:
                try:
                    th = threading.Thread(target=self.__thread_flush)
                    th.start()
                except Exception as e:
                    # for it's a critical part, I won't suppress here
                    import traceback
                    traceback.print_exc()
                    print(e)

    def __thread_flush(self):
        self.schema_writer.write(yaml.dump(self.schema, default_flow_style=False))
        self.schema_writer = None

    def write(self):
        self.flush()

    def __save_image(self, img):
        """
            args:
                img
             
            return:
                list of saved file names
        """

        if img is not None:
            img_path_list = []

            try:
                if isinstance(img, Image.Image):
                    save_path = os.path.join(self.output_image_dir, "{}{}_{}{}".format(
                                                                      self.output_name,
                                                                      self.img_name_preffix,
                                                                      self.img_count,
                                                                      self.img_ext))
                    log_path = os.path.join(self.output_image_base, "{}{}_{}{}".format(
                                                                    self.output_name,
                                                                    self.img_name_preffix,
                                                                    self.img_count,
                                                                    self.img_ext))
                    img.save(save_path)
                    img_path_list.append(log_path)
                    self.img_count += 1

                elif isinstance(img, list):
                    if isinstance(img[0], Image.Image):
                        for _img in img:
                            save_path = os.path.join(self.output_image_dir, "{}{}_{}{}".format(
                                                                              self.output_name,
                                                                              self.img_name_preffix,
                                                                              self.img_count,
                                                                              self.img_ext))
                            log_path = os.path.join(self.output_image_base, "{}{}_{}{}".format(
                                                                            self.output_name,
                                                                            self.img_name_preffix,
                                                                            self.img_count,
                                                                            self.img_ext))
                            _img.save(save_path)
                            img_path_list.append(log_path)
                            self.img_count += 1

                else:
                    raise

            except Exception as e:
                if self.msg_logger is not None:
                    log_message = "{time}{tag}{namespace}{msg}".format(
                                time="[{}]".format(datetime.now().strftime("%Y%m%d %H:%M:%S")),
                                tag="[ERROR, INTERNAL]",
                                namespace="OutputWriter::{}::".format(self.output_name),
                                msg="cannot save image, {}".format(e))

                    self.msg_logger.write(log_message+"\n")
                    self.msg_logger.flush()

            finally:
                return img_path_list

        return []

    def close(self):
        if self.schema_writer is not None:
            self.schema_writer.write(yaml.dump(self.schema, default_flow_style=False))
            self.schema_writer = None

        if self.schema_writer is not None:
            self.schema_writer.close()

        self.schema_list_logger.close()
