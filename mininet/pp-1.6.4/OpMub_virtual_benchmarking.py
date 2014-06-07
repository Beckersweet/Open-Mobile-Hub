"""
OpMub_benchmarking.py
Open Mobile Hub

Creates a Mininet virtual network and runs a benchmark on it.

Created by Gareth Johnson
Copyright (c) 2014 Beckersweet. All rights reserved.
"""

from commands import getoutput as command
from json import loads as decodeJSON
from json import dumps as encodeJSON
from mininet.cli import CLI
from mininet.net import Mininet
from mininet.node import Node, RemoteController, CPULimitedHost
from mininet.util import pmonitor
import pp
from re import findall as find

ifconfig = command('ifconfig')
try:
	localIp = find('addr:(192\.168\.56\.\d+) ', ifconfig)[0]
except:
	print "Network settings not configured. Try running 'sudo dhclient eth1'."

NETWORK_CONTROLLER_PORT = 6633
NUMBER_OF_HOSTS = 3
TCP_REQUEST_COMMAND = "python tcpRequest.py " + localIp + " 9999 "
JOB_SERVER_COMMAND = "sudo python dynamic_ncpus.py "
BENCHMARK_RESULTS_FILE_NAME = "OpMub_benchmarking.out"

print
print "Creating network:"

virtualNetwork = Mininet(controller=RemoteController,
							   host=CPULimitedHost,
							  build=False)

controllerName = "c1"
print " Creating controller", controllerName, "..."
virtualNetwork.addController(name=controllerName, controller=RemoteController)

switchName = "s1"
print " Creating switch", switchName, "..."
switch = virtualNetwork.addSwitch(name=switchName)

hostNames = []
for i in range(NUMBER_OF_HOSTS):
    hostName = "h" + str(i+1)
    hostNames.append(hostName)
    print " Creating host", hostName, "..."
    numberOfCpuCores = 1
    cpuUsagePercent = 1/NUMBER_OF_HOSTS
    host = virtualNetwork.addHost(name=hostName,
    							  core=numberOfCpuCores,
    							   cpu=cpuUsagePercent)
    virtualNetwork.addLink(node1=host, node2=switch)

print " Creating root node ..."
rootNode = Node(name="root", inNamespace=False, ip="10.0.3.0")

configFileName = "/etc/network/interfaces"
with open(configFileName, "r") as configFile:
	config = configFile.read()
manualConfigLine = "\niface root-eth0 inet manual\n"
if manualConfigLine not in config:
	print " Adding manual configuration to", configFileName, "..."
	with open(configFileName, "a") as configFile:
		configFile.write(manualConfigLine)
rootNode.cmd("service network-manager restart")

print " Linking root namespace to switch ..."
rootLink = virtualNetwork.addLink(rootNode, switch)
rootLink.intf1.setIP("10.254", "8")

virtualNetwork.start()
print "Network created."
print

print "Testing network:"
virtualNetwork.pingAll()
print "Network test complete."
print

def startNAT( root, inetIntf='eth0', subnet='10.0/8' ):
    """Start NAT/forwarding between Mininet and external network
    root: node to access iptables from
    inetIntf: interface for internet access
    subnet: Mininet subnet (default 10.0/8)="""

    # Identify the interface connecting to the mininet network
    localIntf =  root.defaultIntf()

    # Flush any currently active rules
    root.cmd( 'iptables -F' )
    root.cmd( 'iptables -t nat -F' )

    # Create default entries for unmatched traffic
    root.cmd( 'iptables -P INPUT ACCEPT' )
    root.cmd( 'iptables -P OUTPUT ACCEPT' )
    root.cmd( 'iptables -P FORWARD DROP' )

    # Configure NAT
    root.cmd( 'iptables -I FORWARD -i', localIntf, '-d', subnet, '-j DROP' )
    root.cmd( 'iptables -A FORWARD -i', localIntf, '-s', subnet, '-j ACCEPT' )
    root.cmd( 'iptables -A FORWARD -i', inetIntf, '-d', subnet, '-j ACCEPT' )
    root.cmd( 'iptables -t nat -A POSTROUTING -o ', inetIntf, '-j MASQUERADE' )

    # Instruct the kernel to perform forwarding
    root.cmd( 'sysctl net.ipv4.ip_forward=1' )

print "Starting NAT ..."
startNAT(rootNode)

print "Establishing routes from hosts ..."
for host in virtualNetwork.hosts:
    host.cmd("ip route flush root 0/0")
    host.cmd("route add -net 10.0/8 dev", host.defaultIntf() )
    host.cmd("route add default gw 10.254")

print
print "Adding hosts to controller's host list using TCP JSON commands:"
for host in virtualNetwork.hosts:
	hostCommand = "addVirtualHost"
	hostName = host.name
	print " Adding", hostName, "..."
	hostNetworkInterface = host.defaultIntf()
	hostIP = hostNetworkInterface.IP()
	hostMAC = hostNetworkInterface.MAC()
	hostTCPRequest = encodeJSON({
		"from": hostName,
		"command": hostCommand,
		"name": hostName,
		"ip": hostIP,
		"mac": hostMAC,
		"available": True
	})
	hostCommand = "python tcpRequest.py " + localIp + " 9999 '" + \
				  hostTCPRequest + "'"
	# print "  Request:", hostTCPRequest
	hostTCPResponse = host.cmd(hostCommand).strip()
	# print "  Response:", hostTCPResponse
print "All hosts added to list."
print

print "Running benchmark:"

for hostName in hostNames:
	print " Running 'ppserver.py' on", hostName, "..."
	host = virtualNetwork.get(hostName)
	host.popen("python ppserver.py -d -a -b " + localIp + " -w 1")

print "Getting list of hosts ..."
hostRequestJSON = encodeJSON({"from": "root", "command": "getVirtualHosts"})
hostRequestCommand = TCP_REQUEST_COMMAND + "'" + hostRequestJSON + "'"
hostResponse = rootNode.cmd(hostRequestCommand).strip()
hostList = decodeJSON(hostResponse)["virtualHosts"]
print 'hostList:', hostList

numberOfAvailableHosts = 0
hostIpAddresses = []
for host in hostList:
	if host['available']:
		numberOfAvailableHosts += 1
		hostIpAddresses.append(host['ip'])

print " Running benchmark on root node ..."
jobServer = rootNode
popens = {}
jobServerCommand = JOB_SERVER_COMMAND + str(numberOfAvailableHosts) + " "
for ipAddress in hostIpAddresses:
	jobServerCommand += ipAddress + " "
# print "jobServerCommand = " + jobServerCommand
jobServerCommand = jobServerCommand[:-1] # delete trailing space
popens[jobServer] = jobServer.popen(str(jobServerCommand))
benchmarkResultsFile = open(BENCHMARK_RESULTS_FILE_NAME, "w")
for host, line in pmonitor(popens, timeoutms=500):
	if host:
		benchmarkResultsFile.write(line)
		# print line,
		if len(line) == 0:
			break
print "Benchmark done. Results saved to '" + BENCHMARK_RESULTS_FILE_NAME + "'."
print

print "Stopping network..."
virtualNetwork.stop()
print "Network stopped."
print