"""
tcpRequest.py
Open Mobile Hub

Sends a simple TCP request to given host and port.

Created by Gareth Johnson
Copyright (c) 2014 Beckersweet. All rights reserved.
"""

from socket import socket
from sys import argv

host = argv[1]
port = int(argv[2])
msg = argv[3]

sock = socket()
addr = (host, port)
sock.connect(addr)
sock.sendall(msg)
data = sock.recv(1024)
sock.close()

print data