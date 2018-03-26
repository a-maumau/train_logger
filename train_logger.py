# Setup TensorBoardX summary writer.
import os
import pickle
from datetime import datetime

HAS_TB = True

try:
	from tensorboardX import SummaryWriter
except Exception as e:
	#import traceback
	#traceback.print_exc()
	print("exec. without tensor board.")
	HAS_TB = False


class TrainLogger(object):
	has_tensorboard = HAS_TB

	def __init__(self, file_name, log_dir="./log", default_log_key="log", csv=False, csv_header=False, csv_separator=",", use_tensorboradx=False, time_stamp=True, flush_always=True):
		self.csv_logger = None
		self.tb_logger = None

		self.log_dir = log_dir
		self.file_name = file_name
		self.default_log_key = default_log_key
		
		self.log_dict = {self.default_log_key:[]}

		self.use_csv = csv
		self.csv_header = csv_header
		self.use_tb = use_tensorboradx

		self.csv_separator = csv_separator

		self.dis_pickle_obj = False
		self.set_default_key = False
		self.set_default_tbkey = False

		self.csv_hasHeader = False
		self.flush_always = flush_always
		self.time_stamp = time_stamp

		if not os.path.exists(self.log_dir):
			os.makedirs(self.log_dir)

		if csv:
			self.csv_logger = open(os.path.join(self.log_dir, self.file_name+"{}".format("_{}.csv".format(datetime.now().strftime("%Y%m%d_%H-%M-%S") if time_stamp else ".csv"))), "w")

		if use_tensorboradx and self.has_tensorboard:
			self.tb_logger = SummaryWriter(log_dir=os.path.join(self.log_dir, self.file_name+"{}".format("_{}_tb".format(datetime.now().strftime("%Y%m%d_%H-%M-%S") if time_stamp else "_tb"))))

	def __del__(self):
		self.close()

	def disable_pickle_object(self):
		self.dis_pickle_obj = True

	def set_default_Keys(self, keys):
		self.set_default_key = True
		self.default_dic_key = keys

		if self.use_csv:
			self._csv_header(keys)
			if self.flush_always:
				self.csv_logger.flush()

	def set_default_tbkeys(self, keys):
		if self.has_tensorboard:
			self.set_default_tbkey = True
			self.default_dic_tbkey = keys

	def _csv_header(self, keys):
		_first = True
		for key in keys:
			if _first != True:
				self.csv_logger.write(self.csv_separator)
			self.csv_logger.write(str(key))
		self.csv_logger.write("\n")
		if self.flush_always:
			self.csv_logger.flush()

	def log(self, data):
		if self.dis_pickle_obj != True:
			self._log_dic(data)

		if self.use_csv:
			self._log_csv(data)
		
		if self.use_tb and self.has_tensorboard::
			self._log_tb(data)

	def _log_dic(self, data):
		assert len(self.default_dic_key) == len(data), "keys and data has not same length."
		assert self.set_default_key, "no default keys"

		self.log_dict[self.default_log_key].append({})

		for key, val in zip(self.default_dic_key, data):
			self.log_dict[self.default_log_key][-1][key] = val

	def _log_csv(self, data):
		for key, val in zip(self.default_dic_key, data):
			if key != self.default_dic_key[0]:
				self.csv_logger.write(self.csv_separator)
			self.csv_logger.write(str(val))
		self.csv_logger.write("\n")
		if self.flush_always:
			self.csv_logger.flush()

	def _log_tb(self, data):
		if self.has_tensorboard:
			assert len(self.default_dic_tbkey) == len(data), "keys and data has not same length."
			assert self.set_default_tbkey, "no default keys"

			for key, val in zip(self.default_dic_key, data):
				self.tb_logger.add_scalar(key, val)

	def show_keys(self):
		print(self.default_dic_key)

	def keys(self):
		return self.default_dic_key

	def addAppendLogDic(self, key, value):
		"""
			thiking for adding information like
			how many epochs or starting time and so on.
			not for the sequential data.
		"""
		self.log_dict[key] = value

	# not thinking to use
	def write_log(self, key, value):
		self.log_dict[key] = value

	# not thinking to use
	def write_csvlog(self, data):
		if self.use_csv:
			self.csv_logger.write(data)
			if self.flush_always:
				self.csv_logger.flush()

	def write_tblog(self, name_space, val, iter_num=None):
		if self.has_tensorboard:
			if iter_num is not None:
				self.tb_logger.add_scalar(name_space, val, iter_num)
			else:
				self.tb_logger.add_scalar(name_space, val)

	def close(self):
		if self.dis_pickle_obj != True:	
			with open(os.path.join(self.log_dir, self.file_name+"{}".format("_{}.pkl".format(datetime.now().strftime("%Y%m%d_%H-%M-%S") if self.time_stamp else ".pkl"))), "wb") as f:
				pickle.dump(self.log_dict, f)

		if self.csv_logger is not None:
			self.csv_logger.close()

		if self.tb_logger is not None:
			self.tb_logger.close()
