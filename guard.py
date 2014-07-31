#!/usr/bin/env python3
# encoding: utf-8
# author: Timo Schmid
# license: GPLv2

import time
import socket
import random
import datetime
import threading
import struct
import subprocess

MIN_PORT = 40000
MAX_PORT = 60000

SECRET = b'Sesam oeffne dich'


class Guard(threading.Thread):
    def __init__(self, ports):
        super(Guard, self).__init__()
        self.ports = ports
        self.stop = False


    def _listen(self, port, first):
        print("Listen on {}".format(port))
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        timeval = struct.pack("2l", 3, 0)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_RCVTIMEO, timeval)
        s.bind(('0.0.0.0', port))
        while True:
            try:
                data, addr = s.recvfrom(1024)
            except BlockingIOError:
                if not first or self.stop: 
                    s.close()
                    return False
                continue
            break
        s.close()
        return data, addr

    def protect(self):
        ports = self.ports[:]
        last_addr = None
        while True:
            try:
                port = ports.pop(0)
            except IndexError:
                return last_addr

            res = self._listen(port, last_addr is None)
            if res is False:
                if self.stop:
                    return False
                else:
                    ports = self.ports[:]
                    last_addr = None
                    continue
            else:
                data, addr = res

            if data.strip() != SECRET:
                print("Invalid secret: {}".format(data))
                ports = self.ports[:]
                last_addr = None
                continue
            print("Valid secret from {}".format(addr))
            if last_addr is None:
                last_addr = addr[0]
            elif last_addr != addr[0]:
                print("Invalid addr: {}".format(addr))
                ports = self.ports[:]
                last_addr = None
                continue

    def run(self):
        while True:
            allowed = self.protect()
            if allowed:
                subprocess.Popen(['iptables', '-I', 'portknocked', 
                                              '-j', 'ACCEPT',
                                              '-s', allowed])
            elif allowed is False and self.stop:
                break



def get_ports(num=5):
    rand = random.Random(to_time())
    
    return [rand.randint(MIN_PORT, MAX_PORT) for i in range(num)]


class Service(object):
    def start(self):
        ports = get_ports()
        self.g = Guard(ports)
        self.g.setDaemon(True)
        self.g.start()
        return self.g

    def stop(self):
        self.g.stop = True
        return self.g

def setup_table():
    subprocess.Popen(['iptables', '-N', 'portknocked']).wait()
    subprocess.Popen(['iptables', '-A', 'INPUT', '-p', 'tcp', '-m', 'conntrack', '--ctstate', 'RELATED,ESTABLISHED', '-j', 'ACCEPT']).wait()
    subprocess.Popen(['iptables', '-A', 'INPUT', '-j', 'portknocked']).wait()

def close_table():
    subprocess.Popen(['iptables', '-D', 'INPUT', '-j', 'portknocked']).wait()
    subprocess.Popen(['iptables', '-F', 'portknocked']).wait()
    subprocess.Popen(['iptables', '-X', 'portknocked']).wait()

def reset_table():
    subprocess.Popen(['iptables', '-F', 'portknocked']).wait()
    subprocess.Popen(['iptables', '-A', 'portknocked', '-p', 'tcp', '-j', 'DROP']).wait()

def to_time(dt=None):
    if not dt:
        dt = datetime.datetime.now()
    return datetime.datetime(year=dt.year,
                             month=dt.month,
                             day=dt.day,
                             hour=dt.hour).timestamp()

if __name__ == '__main__':
    s = Service()
    setup_table()
    try:
        while True:
            reset_table()
            last_date = to_time()
            s.start()
            while True:
                time.sleep(10)
                if to_time() > last_date:
                    print("Time lapse exceeded. Reconfigure")
                    s.stop().join()
                    break

    except:
        print("Stopping")
        s.stop().join()
        close_table()
        raise

