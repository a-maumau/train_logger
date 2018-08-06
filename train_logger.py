# Setup TensorBoardX summary writer.
import os
from datetime import datetime
import threading
import random
import pickle

HAS_TB = True
HAS_GS_ENNV = True
HAS_NOTI = True

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

# just in case
try:
    from notificator import Notificator
except Exception as e:
    #import traceback
    #traceback.print_exc()
    #print("exec. without notificator.")
    HAS_NOTI=False

class TrainLogger(object):
    has_tensorboard = HAS_TB
    has_gs = HAS_GS_ENNV
    has_noti = HAS_NOTI

    # api endpoint
    gs_scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive.file']
    
    # google spreadsheet api limitation?
    # actually I think the default worksheet row, col are size of 1000, 26.
    # so this is migth be the limitation.
    row_limit = 1000
    col_limit = 26

    newline_char = "\n"
    newline_char_replace = " "

    def __init__(self, file_name, log_dir="./log", log_dict_key="log", log_dict_msg_key="msg_log", header=None, 
                 csv=False, csv_separator=",",
                 use_tensorboradx=False,
                 gspread_credential_path=None, gspread_share_account="", init_row=1, init_col=1,
                 time_stamp=True, flush_always=True, buff_size=1, notificate=False, blocking=False, suppress_err=True,
                 log_msg_in_one_line=True):
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

            time_stamp: bool
                use time stamp for file name. it's for avoiding overwriting the existing file.
                I know you will think like "Hey please check, Is the file name exist or not, and give a new name."
                yeah, I'll do it someday...

            flush_always: bool
                always flush the log to the file or not.
            
            buff_size: int
                buffer size. I'm not sure this is useful...
                recommend in size 1, but sometimes you want buff it?

            notificate: bool
                use notificator module. you need a setup independently for this.

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

        """

        self.log_dir = log_dir
        self.file_name = file_name
        self.log_dict_key = log_dict_key
        self.log_dict_msg_key = log_dict_msg_key

        self.use_pickle_obj = True
        self.set_tbkey = False

        self.buffer = []
        self.buff_size = buff_size
        self.flush_always = flush_always
        self.time_stamp = time_stamp
        self.blocking = blocking
        self.suppress_err = suppress_err
        
        self.log_dict = {self.log_dict_key:[], self.log_dict_msg_key:[]}

        self.use_csv = csv
        self.csv_separator = csv_separator

        self.use_tb = use_tensorboradx if self.has_tensorboard else False

        # google spread sheet setting
        self.init_row = init_row if init_row > 0 else 1
        self.init_col = init_col if init_col > 0 else 1
        self.count_row = 0
        self.count_col = 0
        self.sheet_count = 1

        self.msg_logger = None
        self.csv_logger = None
        self.tb_logger = None
        self.gs_logger = None
        self.gs = None
        self.notificator = None

        self.msg_filename = None
        self.csv_filename = None
        self.tb_filename = None
        self.gs_filename = None

        self.status_separator = ": "

        if use_tensorboradx and self.has_tensorboard is False:
            if suppress_err == False:
                print("# exec. without tensorboeardX.")

        if self.has_noti and notificate:
            self.notificator = Notificator()

        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)

        self.ts_str = "{}".format(datetime.now().strftime("%Y%m%d_%H-%M-%S"))

        self.msg_filename = self.file_name+"{}".format("_message_{}.txt".format(self.ts_str) if time_stamp else ".txt")
        self.msg_logger = open(os.path.join(self.log_dir, self.msg_filename), "w")

        if self.use_csv:
            self.csv_filename = self.file_name+"{}".format("_{}.csv".format(self.ts_str) if time_stamp else ".csv")
            self.csv_logger = open(os.path.join(self.log_dir, self.csv_filename), "w")

        if self.use_tb:
            self.tb_filename = self.file_name+"{}".format("_{}_tb".format(self.ts_str) if time_stamp else "_tb")
            self.tb_logger = SummaryWriter(log_dir=os.path.join(self.log_dir, self.tb_filename))

        if gspread_credential_path is not None and self.has_gs:
            try:
                credentials = ServiceAccountCredentials.from_json_keyfile_name(gspread_credential_path, self.gs_scope)
                self.gs = gspread.authorize(credentials)
                self.gs_filename = self.file_name+"{}".format("_{}".format(self.ts_str if time_stamp else ""))
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

    def log_msg(self, msg, msg_tag="MSG", use_timestamp=True):
        """
            args:
                msg: str or str castable object

            if self.blocking is False, it will log with another thread
        """

        if self.blocking:
                self._log_msg(msg, msg_tag, use_timestamp)
        else:
            try:
                th = threading.Thread(target=self._thread_log_msg, args=(msg, msg_tag, use_timestamp,))
                th.start()
            except Exception as e:
                # for it's a critical part, I won't suppress here
                import traceback
                traceback.print_exc()
                print(e)

    def notify(self, msg, use_thread=True):
        """
            send notification using notification module.
        """
        if self.notificator is not None:
            self.notificator.notify(msg, use_thread)

    def set_notificator(self, params=["mail", "slack", "twitter"]):
        if self.notificator is not None:
            for p in params:
                if p.lower() == "mail":
                    self.notificator.setMail()

                elif p.lower() == "slack":
                    self.notificator.setSlack()

                elif p.lower() == "twitter":
                    self.notificator.setTwitter()

    def disable_pickle_object(self):
        # if you not want to save dictonary object of log.
        self.use_pickle_obj = False

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
            tensorboeard has different namespace system,
            I separete it.
        """
        if self.use_tb:
            self.set_tbkey = True
            self.default_dic_tbkey = keys

    def show_log_keys(self):
        print(self.header)

    def keys(self):
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
            with open(os.path.join(self.log_dir, self.file_name+"{}".format("_{}.pkl".format(self.ts_str if self.time_stamp else ".pkl"))), "wb") as pickle_file:
                pickle.dump(self.log_dict, pickle_file)

        self.msg_logger.close()

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

    def _log_msg(self, msg, msg_tag="MSG", use_timestamp=True):
        if self.use_pickle_obj:
            self._log_msg_dic(msg, msg_tag, use_timestamp)

        self._log_msg_file(msg, msg_tag, use_timestamp)

    def _thread_log(self, data):
        for d in data:
            self._log(d)

    def _thread_log_msg(self, msg, msg_tag="MSG", use_timestamp=True):
        if self.use_pickle_obj:
            self._log_msg(msg, msg_tag, use_timestamp)

        self._log_msg_file(msg, msg_tag, use_timestamp)

    def _log_dic(self, data, msg_tag="MSG", use_timestamp=True):
        assert len(self.header) == len(data), "keys and data has not same length."
        assert self.header is not None, "no header keys"

        self.log_dict[self.log_dict_key].append({})

        for key, val in zip(self.header, data):
            self.log_dict[self.log_dict_key][-1][key] = val

    def _log_msg_dic(self, msg, msg_tag="MSG", use_timestamp=True):
        logging_message = self._build_log_message("[{}]".format(datetime.now().strftime("%Y%m%d_%H-%M-%S")) if use_timestamp else "", "[{}]".format(msg_tag), msg)
        self.log_dict[self.log_dict_key].append(msg)

    def _log_msg_file(self, msg, msg_tag="MSG", use_timestamp=True):
        logging_message = self._build_log_message("[{}]".format(datetime.now().strftime("%Y%m%d_%H-%M-%S")) if use_timestamp else "", "[{}]".format(msg_tag), msg)
        self.msg_logger.write(logging_message)
        self.msg_logger.write("\n")
        if self.flush_always:
            self.msg_logger.flush()

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

    def _build_log_message(self, timestamp, msg_tag, msg):
        return "{}{}{}{}".format(timestamp, msg_tag, self.status_separator, msg)

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
