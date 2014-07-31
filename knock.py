#!/usr/bin/env python3
# encoding: utf-8
# author: Timo Schmid
# license: GPLv2

import socket
import guard
import time
import sys


def knock(addr, ports):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    for port in ports:
        print("Knocking {}:{}".format(addr, port))
        s.sendto(guard.SECRET, (addr, port))
        time.sleep(0.5)
    s.close()

if __name__ == '__main__':
    knock(sys.argv[1], guard.get_ports())
