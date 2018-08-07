import random
import time
from train_logger import TrainLogger

tlog = TrainLogger("test_log", header=["num", "val"], blocking=True)
tlog.set_server(bind_host="", bind_port=8080)
for i in range(5):
	tlog.log([i, random.random()])

time.sleep(5)

# try connecting the server befeore here.

tlog.log_msg("test messgae", "MSG", use_timestamp=True)
tlog.log_msg("3.141592", "LOG", use_timestamp=True)

time.sleep(5)

# try connecting the server befeore here with another client with -fetch_all

for i in range(5):
	tlog.log_msg("{}".format(random.random()), "LOG", use_timestamp=True)
	time.sleep(1)

tlog.close()
