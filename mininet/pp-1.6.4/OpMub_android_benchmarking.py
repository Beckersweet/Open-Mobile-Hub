"""
OpMub_android_benchmarking.py
Open Mobile Hub

For use with controller_android.py

Creates a Mininet virtual network that is based on Android devices that the user 
connects to the controller using the MQTT Client and Open Mobile Hub Android
apps, then runs a benchmark for distributed computing on those devices.

Created by Gareth Johnson
Copyright (c) 2014 Beckersweet. All rights reserved.
"""

from commands import getoutput as command
from json import loads as decode
from json import dumps as encode
from mininet.cli import CLI
from mininet.net import Mininet
from mininet.node import Node, RemoteController, CPULimitedHost
from mininet.util import pmonitor
import pexpect
import pp
from re import findall as find

ifconfig = command('ifconfig')
try:
	localIp = find('addr:(192\.168\.56\.\d+) ', ifconfig)[0]
	print 'localIp:', localIp
except:
	print "Network settings not configured. Try running 'sudo dhclient eth1'."

TCP_PORT = 9999
TCP_REQUEST_COMMAND = "python tcpRequest.py " + localIp + " " + \
		str(TCP_PORT) + " "
JOB_SERVER_COMMAND = "python dynamic_ncpus.py "
BENCHMARK_RESULTS_FILE_NAME = "OpMub_benchmarking.out"

hostIPMap = {} # real host IP address => virtual host IP address

virtualNetwork = Mininet(controller=RemoteController,
		host=CPULimitedHost,
		build=False)

controllerName = "c1"
print "Creating controller", controllerName, "..."
virtualNetwork.addController(name=controllerName, controller=RemoteController)

switchName = "s1"
print "Creating switch", switchName, "..."
switch = virtualNetwork.addSwitch(name=switchName)

print "Creating root node ..."
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

print "Linking root namespace to switch ..."
rootLink = virtualNetwork.addLink(rootNode, switch)
rootLink.intf1.setIP("10.254", "8")

print
raw_input("Please connect Android devices now. Press Enter when done: ")
print

print "Getting list of real hosts ..."
realHostRequestJSON = encode({"from": "root", "command": "getRealHosts"})
realHostRequestCommand = TCP_REQUEST_COMMAND + "'" + realHostRequestJSON + "'"
realHostResponse = rootNode.cmd(realHostRequestCommand).strip()
# print "realHostResponse:", realHostResponse
realHosts = decode(realHostResponse)["realHosts"]

print "Adding virtual hosts to Mininet based on real hosts"
i = 0
for host in realHosts:
	i += 1
	hostName = "h" + str(i)
	print " Creating virtual host for", hostName, "..."
	numberOfCpuCores = 1
	cpuUsageFraction = 1.0/len(realHosts)
	virtualIP = "10.0.0." + str(i)
	virtualHost = virtualNetwork.addHost(name=hostName,
			core=numberOfCpuCores,
			cpu=cpuUsageFraction,
			ip=virtualIP)
	virtualNetwork.addLink(node1=virtualHost, node2=switch)
	realIP = host['ip']
	hostIPMap[realIP] = virtualIP

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

    # # Forward virtual-network packets to virtual hosts instead of real devices
    # print "Forwarding real-host IP addresses to their virtual-host " + \
    # 		"counterparts ..."
    # for realIP in hostIPMap:
    # 	forwardCommand = 'sudo iptables -t nat -A OUTPUT -j DNAT -d ' + \
    # 			realIP + ' --to-destination ' + hostIPMap[realIP]
    # 	result = root.cmd(forwardCommand)
    # 	print result
    # 	for host in virtualNetwork.hosts:
    # 		result = host.cmd(forwardCommand)
    # 		print result

print "Starting NAT ..."
startNAT(rootNode)

print "Establishing routes from hosts ..."
for host in virtualNetwork.hosts:
    host.cmd("ip route flush root 0/0")
    host.cmd("route add -net 10.0/8 dev", host.defaultIntf() )
    host.cmd("route add default gw 10.254")

print "Starting network ..."
virtualNetwork.start()

if len(virtualNetwork.hosts) > 1:
	print "Testing network:"
	virtualNetwork.pingAll()
	print "Network test complete."
	print

print "Adding virtual hosts to controller's host list using TCP JSON commands"
for host in virtualNetwork.hosts:
	hostCommand = "addVirtualHost"
	hostName = host.name
	print " Adding", hostName, "..."
	hostNetworkInterface = host.defaultIntf()
	hostIP = hostNetworkInterface.IP()
	hostMAC = hostNetworkInterface.MAC()
	hostTCPRequest = encode({"from": "root",
			"command": hostCommand,
			"name": hostName,
			"ip": hostIP,
			"mac": hostMAC,
			"available": True})
	hostCommand = TCP_REQUEST_COMMAND + "'" + hostTCPRequest + "'"
	hostTCPResponse = rootNode.cmd(hostCommand).strip()
	# print "  Response:", hostTCPResponse

print "Network setup complete."

print
print "Running benchmark:"

# for hostName in hostNames[1:]:
# 	print " Running 'ppserver.py' on", hostName, "..."
# 	host = virtualNetwork.get(hostName)
# 	host.popen("python ppserver.py -d -a -b 10.0.0.1 -w 1")

numberOfAvailableHosts = 0
realHostIpAddresses = []
for realHost in realHosts:
	if realHost['available']:
		numberOfAvailableHosts += 1
		realHostIpAddresses.append(realHost['ip'])

print " Running benchmark on root node ..."
jobServer = rootNode
popens = {}
jobServerCommand = JOB_SERVER_COMMAND + str(numberOfAvailableHosts) + " "
for ipAddress in realHostIpAddresses:
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