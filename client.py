import sys
import socket
import argparse
import time

MAX_RECIEVE_BYTE = 4096

def connect(ip_addr, port, fetch_all=False):
    client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client.connect((ip_addr, port))

    print("### log [{}:{}]".format(ip_addr, port))
    if fetch_all:
        client.send("all".encode('utf-8'))
    else:
        client.send("log".encode('utf-8'))

    while True:
        try:
            try:
                message = client.recv(MAX_RECIEVE_BYTE)
            except socket.error as e:
                err = e.args[0]
                if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
                    continue
                else:
                    print(e)
                    sys.exit(1)

            if not message:
                # Empty string is given on disconnect.
                print("lost connection from server")
                sys.exit(1)
            else:
                print(message.decode('utf-8'), end="")

        except (SystemExit, KeyboardInterrupt):
            break

        time.sleep(0.5)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    # settings
    parser.add_argument('--ip_addr', type=str, default='127.0.0.1', help='directory for train images')
    parser.add_argument('--port', type=int, default=8080, help='directory for train images')

    parser.add_argument('-fetch_all', action="store_true", default=False, help='fetch all log')

    args = parser.parse_args()
    
    connect(args.ip_addr, args.port, args.fetch_all)