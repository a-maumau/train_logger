import sys
import socket
import threading
import errno
import time
from datetime import datetime

class User(object):
    MAX_RECIEVE_BYTE = 4096

    def __init__(self, user_name, ip_addr, port, conn):
        self.user_name = user_name
        self.ip_addr = ip_addr
        self.port = port
        self.conn = conn

    def set_username(self, name):
        self.user_name = name

    def recv(self):
        return self.conn.recv(self.MAX_RECIEVE_BYTE)

    def send(self, msg):
        self.conn.send(msg)

class Server(object):
    MAX_RECIEVE_BYTE = 4096

    def __init__(self, log_file_path, bind_host, bind_port, listen_number=8, blocking=False):
        self.log_file_path = log_file_path
        self.bind_host = bind_host
        self.bind_port = bind_port
        self.listen_number = listen_number
        self.blocking = blocking
        self.connections = []
        self.main_thread = None

        self.log_file = open(log_file_path, "r")

    def start(self, use_thread=True):
        if use_thread:
            self.main_thread = threading.Thread(target=self.__main_loop, args=())
            self.main_thread.daemon = True
            self.main_thread.start()
        else:
            self.__main_loop()

    def stop(self):
        sys.exit(0)

    def __main_loop(self):
        # Set up the server socket.
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.setblocking(self.blocking)
        self.server.bind((self.bind_host, self.bind_port))
        self.server.listen(self.listen_number)

        while True:
            try:
                # Accept new connections.
                while True:
                    try:
                        self.accept()
                    except socket.error:
                        break

                for user in self.connections:
                    try:
                        message = user.recv()
                    except socket.error as e:
                        err = e.args[0]
                        if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
                            continue
                        else:
                            print(e)
                            sys.exit(1)

                    if not message:
                        # Empty string is given on disconnect.
                        self.connections.remove(user)
                time.sleep(.5)
            except (SystemExit, KeyboardInterrupt):
                break

    def log(self, msg):
        for user in self.connections:
            user.send("{}\n".format(msg).encode('utf-8'))

    def accept(self):
        conn, (ip_addr, port_num) = self.server.accept()
        
        accept_thread = threading.Thread(target=self.__thread_accept, args=(conn, ip_addr, port_num))
        accept_thread.start()

    # avoid blocking
    def __thread_accept(self, conn, ip_addr, port_num):
        while True:
            try:
                resp = conn.recv(self.MAX_RECIEVE_BYTE).strip().decode('utf-8')
            except socket.error as e:
                err = e.args[0]
                if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
                    #print('No data available')
                    time.sleep(.5)
                    continue
                else:
                    # a "real" error occurred
                    print(e)
                    sys.exit(1)
            else:
                #if name in users:
                #    conn.send("Name entered is already in use.\n".encode('utf-8'))
                
                conn.setblocking(False)
                self.connections.append(User("anonymous", ip_addr, port_num, conn))
                if "all" in resp:
                    logs = self.log_file.readlines()
                    for line in logs:
                        conn.send("{}".format(line).encode('utf-8'))

                # return to head
                self.log_file.seek(0)

                break

    def __broadcast(self, message):
        """
            Send a message to all users.
        """
        for user in self.connections:
            try:
                user.send((message+"\n").encode('utf-8'))
            except socket.error as e:
                err = e.args[0]
                if err == errno.EAGAIN or err == errno.EWOULDBLOCK:
                    #print('No data available')
                    time.sleep(.2)
                    continue
                else:
                    # a "real" error occurred
                    print(e)
