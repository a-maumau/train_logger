import random
from train_logger import TrainLogger

tlog = TrainLogger("test_log", csv=True, use_tensorboradx=True, gspread_credential_path="credential.json", gspread_share_account="your_account@gmail.com", header=True, buff_size=3, notificate=True, suppress_err=False)

# the header of data, it is required
tlog.set_default_Keys(["num.", "val"])

# set witch kind notification
tlog.set_notificator(["slack"])
# send notification using notificator
tlog.notify("test")

for i in range(5):
	tlog.log([i, random.random()])

