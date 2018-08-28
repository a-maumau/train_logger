import random
import time
from train_logger import TrainLogger
import argparse

from PIL import Image

def test(args):
    tlog = TrainLogger(log_dir="test_log", log_name="log_output", namespaces={"train":["num", "value", "loss"], "val":["num", "score"], "test":["epoch", "acc"]}, arguments=args._get_kwargs(), notificate=False, suppress_err=False)
    tlog.start_msg_server(bind_port=8082)
    tlog.start_http_server(bind_port=8080)

    img = Image.open("your img")
    img2 = Image.open("your img2")

    s = 0
    for i in range(10):
        r = random.random()
        s += r
        tlog.log("train", [i, r, r*r])
        tlog.setup_output("output_{}".format(i), "test")
        tlog.pack_output(img)
        tlog.pack_output(img, "{}".format(i), ["I", "love", "cat"])
        tlog.pack_output(img, "test image")
        tlog.pack_output(None, "only description", ["and items", "look!"])
        tlog.flush_output()
        print(i)

        time.sleep(10)

    tlog.setup_output("double_cat", "test")
    tlog.pack_output([img, img2])
    tlog.flush_output()

    # try connecting the server befeore here.

    tlog.log_message("test messgae", "MESSAGE", "train")
    tlog.log_message("sum {}".format(s), "LOG", "train")

    time.sleep(5)

    # try connecting the server befeore here with another client with -fetch_all

    for i in range(10):
        r = random.random()
        tlog.log("val", [i, r])
        tlog.log_message("{}".format(r), "LOG", "val")
        time.sleep(0)

    for i in range(1,11):
        r = random.random()
        tlog.log("test", [i*2, r])
        time.sleep(0)

    tlog.close()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    # settings
    parser.add_argument('--args1', type=str, default='this is args1')
    parser.add_argument('--args2', type=str, default='this is args2')
    parser.add_argument('--args3', type=str, default='this is args3')
    parser.add_argument('--args4', type=str, default='this is args4')

    args = parser.parse_args()
    
    test(args)