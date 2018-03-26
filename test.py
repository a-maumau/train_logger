import random
from train_logger import TrainLogger

tlog = TrainLogger("test_log", csv=True)

tlog.set_default_Keys(["num.", "val"])

for i in range(1000):
	tlog.log([i, random.random()])

