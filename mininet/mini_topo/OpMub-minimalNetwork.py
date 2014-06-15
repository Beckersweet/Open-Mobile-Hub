#!/usr/bin/python

"""
OpMub-minimalNetwork.py
Open Mobile Hub

Create a minimal network of NC controllers, NC switches and NH hosts per switch.

Created by Barbara Collignon on Sept 8, 2013
Copyright (c) 2013 Beckersweet. All rights reserved.
"""

from mininet.link import TCLink
from mininet.node import CPULimitedHost
from mininet.net import Mininet
from mininet.node import Controller, OVSKernelSwitch
from mininet.cli import CLI
from mininet.log import setLogLevel

Switch = OVSKernelSwitch

def addHost( net, N ):
    "Add host hN to net"
    name = 'h%d' % N
    ip = '10.0.0.%d' % N
    # cpu = desired overall system CPU fraction
    cpu = 0.5/N
    # cores = (real) core(s) this host can run on
    core = 1
    return net.addHost( name, ip=ip, cpu=cpu , core = core )

def addController(net, N, gateID):
    "Add controller cN to net"
    name = 'c%d' % N
    return net.addController(name,port=gateID)

def addSwitch(net,N):
    "Add switch sN to net"
    name = 's%d' % N
    return net.addSwitch(name)

def multiSwitchNet(NS,NH):
    "Add 1 controller, NS switches & NH hosts per switch"
    
    port = 6633
    net = Mininet( controller=Controller, switch=Switch, host=CPULimitedHost, link=TCLink)
    
    k=NS;
    
    c = addController(net,N=1,gateID=port);
    
    lastSwitch = None
    for i in range(1,NS+1) :
#        name = 'c%d' % i
#        c = addController(net,N=i,gateID=port)
        s = addSwitch(net,N=i)
        host = [addHost(net,n) for n in range(k,k+NH)]
        for h in host :
            net.addLink(h,s,bw=10,delay='5ms',loss=1,max_queue_size=1000,use_htb=True)
        if lastSwitch :
            net.addLink(s,lastSwitch,bw=10,delay='5ms',loss=1,max_queue_size=1000,use_htb=True)
        lastSwitch = s
        port = port + 1
        k=k+NH
    
    print "Starting network"
    net.start()
    
    print "Testing network"
    net.pingAll()
    
    print "Running CLI"
    CLI( net )
    
    print "Stopping network"
    net.stop()

if __name__ == '__main__':
    setLogLevel( 'info' )  # for CLI output
    multiSwitchNet(NS=4,NH=2)