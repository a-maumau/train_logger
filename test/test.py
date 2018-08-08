import random
from train_logger import TrainLogger

#tlog = TrainLogger("test_log", csv=True, use_tensorboradx=True, gspread_credential_path="credential.json", gspread_share_account="your_account@gmail.com", header=True, buff_size=3, notificate=True, suppress_err=False)
tlog = TrainLogger("test_log", csv=True, use_tensorboradx=True, header=["num", "val"], buff_size=3, notificate=True, blocking=True, suppress_err=False)
for i in range(5):
	tlog.log([i, random.random()])

tlog.log_msg("test messgae", "MSG", use_timestamp=True)
tlog.log_msg("3.141592", "LOG", use_timestamp=True)

# need notificator module
# set witch kind notification
tlog.set_notificator(["slack"])
# send notification using notificator
tlog.notify("test")

tlog.close()

tlog2 = TrainLogger("test_log2", csv=True, use_tensorboradx=True, buff_size=3, notificate=True, blocking=True, suppress_err=False)
# you can set header after
tlog2.set_header(["num.", "val"])
for i in range(5):
	tlog2.log([i, random.random()])
tlog2.close()

tlog3 = TrainLogger("only_csv", csv=True, use_tensorboradx=False, buff_size=3, notificate=True, blocking=True, suppress_err=False)
tlog3.disable_pickle_object()
for i in range(5):
	tlog3.log([i, random.random()])
tlog3.close()