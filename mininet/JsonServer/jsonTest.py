"""
jsonTest.py
Open Mobile Hub

A quick and dirty testing script for JsonServer.py

Created by Gareth Johnson
Copyright (c) 2014 Beckersweet. All rights reserved.
"""

from JsonServer import JsonServer

j = JsonServer()

print 'not json'
print j.request('hi')
print
print 'no "from" attribute'
print j.request('{"command":"getRealHosts"}')
print
print 'bad command'
print j.request('{"from":"test", "command":"hi"}')
print
print 'get empty hosts'
print j.request('{"from": "test", "command":"getRealHosts"}')
print j.request('{"from": "test", "command":"getVirtualHosts"}')
print
print 'set availability of nonexistent hosts'
print j.request('{"from": "test", "command":"setRealHostAvailability", "name":"h1", "available":false}')
print j.request('{"from": "test", "command":"setVirtualHostAvailability", "name":"h2", "available":true}')
print
print 'remove nonexistent hosts'
print j.request('{"from": "test", "command":"removeRealHost", "name":"h1"}')
print j.request('{"from": "test", "command":"removeVirtualHost", "name":"h2"}')
print
print 'add hosts'
print j.request('{"from": "test", "command":"addRealHost", "name":"h1", "ip":"1.1.1.1", "mac":"11-11-11-11-11-11", "latitude":11.1111, "longitude":11.1111, "available":true}')
print j.request('{"from": "test", "command":"addVirtualHost", "name":"h2", "ip":"1.1.1.1", "mac":"11-11-11-11-11-11", "available":false}')
print
print 'get nonempty hosts'
print j.request('{"from": "test", "command":"getRealHosts"}')
print j.request('{"from": "test", "command":"getVirtualHosts"}')
print
print 'set availability of existing hosts'
print j.request('{"from": "test", "command":"setRealHostAvailability", "name":"h1", "available":false}')
print j.request('{"from": "test", "command":"setVirtualHostAvailability", "name":"h2", "available":true}')
print
print 'check availability of hosts'
print j.request('{"from": "test", "command":"getRealHosts"}')
print j.request('{"from": "test", "command":"getVirtualHosts"}')
print
print 'remove existing hosts'
print j.request('{"from": "test", "command":"removeRealHost", "name":"h1"}')
print j.request('{"from": "test", "command":"removeVirtualHost", "name":"h2"}')
print
print 'get empty hosts'
print j.request('{"from": "test", "command":"getRealHosts"}')
print j.request('{"from": "test", "command":"getVirtualHosts"}')
