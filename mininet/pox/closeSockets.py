"""
closeSockets.py
Open Mobile Hub

Closes sockets opened by OpMub_android_benchmarking.py

Created by Gareth Johnson
Copyright (c) 2014 Beckersweet. All rights reserved.
"""

import re
from subprocess import Popen, PIPE

ports = [8080, 9998, 9999]

process = Popen(['sudo', 'netstat', '-tulpn'], stdout=PIPE)
output = process.communicate()[0]

pids = set()

for line in output.split('\n'):
    for port in ports:
        pid = re.findall('^.*\:' + str(port) + '.*\s(\d+).*$', line)
        if (len(pid) > 0):
            pids.add(pid[0])

for pid in pids:
    Popen(['sudo', 'kill', '-SIGKILL', str(pid)])
