"""
controller_android.py
Open Mobile Hub

POX controller that includes a firewall, TCP server, and MQTT broker
Based on l2_learning.py
Edited by Gareth Johnson (comments marked "-G")

TODO: Close MQTT socket on exit
"""

from json import loads as decodeJSON
from json import dumps as encodeJSON
import paho.mqtt.client as mqtt
from pexpect import spawn
from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.revent import *
from pox.lib.util import dpidToStr
from pox.lib.util import str_to_bool
import re
from subprocess import call, Popen
from threading import Thread
from SocketServer import BaseRequestHandler, TCPServer
from urlparse import urlparse as parseURL
import time, os, csv, re

import sys
sys.path.insert(0, '/home/mininet/JsonServer/')
from JsonServer import JsonServer

log = core.getLogger()

# For WebSocket server -G
MQTT_WEBSOCKET_PORT = 8080

# For MQTT broker and subscriber -G
MQTT_BROKER_PORT = 9998
MQTT_BROKER_COMMAND = 'mosquitto -p ' + str(MQTT_BROKER_PORT)
MQTT_BROKER_ADDRESS = '127.0.0.1'
MQTT_BROKER_NAME = 'broker'

# For the contoller-host TCP communicaiton server -G
TCP_HOST = '' # allow any client to connect
TCP_PORT = 9999 # for both client and server

# JSON server used by TCP and MQTT servers -G
jsonServer = JsonServer()

# Dictionaries of name:{ip,mac} for added real and virtual hosts on network -G
realHosts = {}
virtualHosts = {}

# For the firewall -G
policyFile = 'firewall-policies.csv'
rules = []

# We don't want to flood immediately when a switch connects.
FLOOD_DELAY = 5

class FirewallSwitch (EventMixin):

  def __init__ (self, connection, transparent):

    # Reads the firewall rules in the policy file -G
    with open(policyFile, 'rU') as f:
        reader = csv.reader(f)
        header = f.readline()
        for row in reader:
            row.pop(0)
            rules.append(row)

    # Switch we'll be adding L2 switch capabilities to
    self.connection = connection
    self.transparent = transparent

    # Our table
    self.macToPort = {}

    # We want to hear PacketIn messages, so we listen
    self.listenTo(connection)

  def _handle_PacketIn (self, event):
    packet = event.parse()

    def flood ():
      """ Floods the packet """
      if event.ofp.buffer_id == -1:
        log.warning("Not flooding unbuffered packet on %s",
                    dpidToStr(event.dpid))
        return
      msg = of.ofp_packet_out()
      if time.time() - self.connection.connect_time > FLOOD_DELAY:
        # Only flood if we've been connected for a little while...
        msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))
      else:
        pass
      msg.buffer_id = event.ofp.buffer_id
      msg.in_port = event.port
      self.connection.send(msg)

    def drop (duration = None):
      if duration is not None:
        if not isinstance(duration, tuple):
          duration = (duration,duration)
        msg = of.ofp_flow_mod()
        msg.match = of.ofp_match.from_packet(packet)
        msg.idle_timeout = duration[0]
        msg.hard_timeout = duration[1]
        msg.buffer_id = event.ofp.buffer_id
        self.connection.send(msg)
      elif event.ofp.buffer_id != -1:
        msg = of.ofp_packet_out()
        msg.buffer_id = event.ofp.buffer_id
        msg.in_port = event.port
        self.connection.send(msg)

    # Firewall code for single destination -G
    for (mac_0, mac_1) in rules:
        if mac_0 == str(packet.src) and mac_1 == str(packet.dst):
            log.debug("Rule found in firewall: %s -/-> %s" %
                      (packet.src, packet.dst))
            drop()
            return

    self.macToPort[packet.src] = event.port

    if not self.transparent:
      if packet.type == packet.LLDP_TYPE or packet.dst.isBridgeFiltered():
        drop()
        return

    if packet.dst.isMulticast():
      flood()
    else:
      if packet.dst not in self.macToPort:
        log.debug("Port for %s unknown -- flooding" % (packet.dst,))
        flood()
      else:
        port = self.macToPort[packet.dst]
        if port == event.port:
          log.warning("Same port for packet from %s -> %s on %s.  Drop." %
                      (packet.src, packet.dst, port), dpidToStr(event.dpid))
          drop(10)
          return
        log.debug("installing flow for %s.%i -> %s.%i" %
                  (packet.src, event.port, packet.dst, port))
        msg = of.ofp_flow_mod()
        msg.match = of.ofp_match.from_packet(packet)
        msg.idle_timeout = 10
        msg.hard_timeout = 30
        msg.actions.append(of.ofp_action_output(port = port))
        msg.buffer_id = event.ofp.buffer_id # 6a
        self.connection.send(msg)

class l2_firewall (EventMixin):
  def __init__ (self, transparent):
    self.listenTo(core.openflow)
    self.transparent = transparent

  def _handle_ConnectionUp (self, event):
    log.debug("Connection %s" % (event.connection,))
    FirewallSwitch(event.connection, self.transparent)

# Defines behaviour of TCP server -G
class tcpHandler(BaseRequestHandler):
  def handle(self):
    self.data = self.request.recv(1024).strip()
    print "TCP message received:"
    print self.data
    response = jsonServer.request(self.data)
    self.request.sendall(response)
    print "TCP message sent:"
    print response

def runServer():
  server = TCPServer((TCP_HOST, TCP_PORT), tcpHandler)
  server.serve_forever()

def mqttSubscribe(broker=MQTT_BROKER_ADDRESS, port=MQTT_BROKER_PORT,
    topic=MQTT_BROKER_NAME):

  # Defines behaviour of MQTT client -G
  def onConnect(client, server, returnCode):
    if returnCode == 0:
      log.info("MQTT subscription established")
    else:
      log.warning("Unable to connect to MQTT broker")
  def onDisconnect(client, server, returnCode):
    if returnCode == 0:
      log.info("MQTT subscription ended successfully")
    else:
      log.warning("Disconnected from MQTT broker unexpectedly")
  def onMessage(client, server, message):
    messageString = str(message.payload)
    print "MQTT message received:"
    print messageString
    response = server.request(messageString)
    clientName = decodeJSON(response)['to']
    publishTopic = clientName
    client.publish(publishTopic, response)
    print "MQTT message sent:"
    print response

  # Initialize client -G
  client = mqtt.Client(MQTT_BROKER_NAME, True, jsonServer)
  client.on_connect = onConnect
  client.on_disconnect = onDisconnect
  client.on_message = onMessage

  # Connect and subscribe -G
  client.connect(MQTT_BROKER_ADDRESS, MQTT_BROKER_PORT)
  client.subscribe(MQTT_BROKER_NAME)
  client.loop_forever()

def mqttWebServe():
  script = "/home/mininet/pywebsocket/src/mod_pywebsocket/standalone.py"
  port = str(MQTT_WEBSOCKET_PORT)
  pageDirectory = "/home/mininet/public_html/" # absolute -G
  handlerDirectory = "handlers/" # relative to pageDirectory -G
  call([script, "-p", port, "-d", pageDirectory, "-w", handlerDirectory])

def mqttStart(port=MQTT_BROKER_PORT):

  # Wait for POX intro message to disappear -G
  time.sleep(1)

  # Run MQTT broker and wait for it to start or give an error -G
  mqttBrokerProcess = spawn(MQTT_BROKER_COMMAND)
  successMessage = "\d+\: Opening ipv6 listen socket on port " + str(MQTT_BROKER_PORT)
  failureMessage = "\d+\: Error:.*\n"
  returnCode = mqttBrokerProcess.expect([successMessage, failureMessage])
  if returnCode == 0:
    log.info("MQTT broker created")
  if returnCode == 1:
    log.warning("Failed to create MQTT broker:\n " + mqttBrokerProcess.after)

  # Run MQTT subscriber client in separate thread -G
  mqttSubscriberThread = Thread(target=mqttSubscribe)
  mqttSubscriberThread.daemon = True
  mqttSubscriberThread.start()

  # Run MQTT WebSocket server in separate thread -G
  mqttWebServeThread = Thread(target=mqttWebServe)
  mqttWebServeThread.daemon = True
  mqttWebServeThread.start()

  # Keep broker running until thread exits, then close it -G
  try:
    mqttBrokerProcess.wait()
  except:
    mqttBrokerProcess.sendcontrol('c') # send control-c keyboard command
    mqttBrokerProcess.close()

def launch (transparent=False):

  core.registerNew(l2_firewall, str_to_bool(transparent))

  # Start MQTT system in separate thread -G
  mqttThread = Thread(target=mqttStart)
  mqttThread.daemon = True
  mqttThread.start()

  # Run server in separate thread -G
  serverThread = Thread(target=runServer)
  serverThread.daemon = True
  serverThread.start()