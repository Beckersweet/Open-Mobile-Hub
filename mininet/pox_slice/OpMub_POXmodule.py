#!/usr/bin/python

"""
OpMub_POXModule.py 
Open Mobile Hub

Phase#1 Allocates mobile resources to a given user.

The FINAL high-level service architecture should be as follows:
Crowdsource | Supercompute | Monitor
The FINAL low-level service architecture should be as follows:
OpMubApp <-> NB API <-> Orchestrator <-> CTRs/SWs <-> Mobile Resources.

The OpMub module acts as a remote controller/orchestrator for OpMub minimal Network.
The firewall rules are replaced with the "Quantum" rules.

After launching OpMub-minimalNetwork_remoteController.py, launch OpMub_POXModule.py in another xterm.  

Created by Barbara Collignon on Sept 9, 2013
Copyright (c) 2013 Beckersweet. All rights reserved. 
"""

from numpy import zeros,matrix 
from pox.openflow.discovery import Discovery # to build adajency map
from pox.core import core
import pox.openflow.libopenflow_01 as of
from pox.lib.revent import *
from pox.lib.util import str_to_bool, dpidToStr
from pox.lib.packet.arp import arp
from pox.lib.packet.ipv4 import ipv4
from pox.lib.addresses import IPAddr,EthAddr
from collections import namedtuple,defaultdict
import os,time,math
import json,urllib2,subprocess,btpeer
#from pox.openflow.discovery import Discovery
from math import *

log = core.getLogger()

packetNb = 0
droppedNb = 0
PhoneAlloc = 0

# Global variables for Layer 2 learning
macToPort = {}
# Gloabal variables for Layer 3 learning
fakeways = []
arpTable = {}
hubTable = {}
arp_for_unknowns = None ;

#Quantum rules replace firewall rules 
#firewall ={}
quantum = {}

# Quantum rules for a 2-switch network :
# SW1 SW1
# (0,0) DROP packets on all SWs
# (0,1) Flood or Drop packets on half of the SWs 
# (1,0) Flood or Drop packets on the other half
# (1,1) FLOOD packets to all SWs
rules = [(1,1)]

#User Rules
# Use REST API to load the rules
NBS=3
NBH=3
moduloSWT=1
moduloHST=1
taskparallel = True
juridiction = 27 # country code
urules =[(NBS,NBH,moduloSWT,moduloHST,taskparallel,juridiction)]

# POX does not support REST
# if REST : Send a REST API request  
# url = "http://%s:6633/opmub/mobile/conections/rules/json" % controllerIP
# rules = json.load(urllib2.urlopen(url))

# MobileAllocRules = [nbSW,PhonesPerSW]
MobileAllocRules = [(3,3)] # = 9 phones
hub = {}
data = {}
result = {}

isHubCompleted = False

# Discovery Global Variables (Copy-pasted from l2_multi.py)
switches = {} # Switches we know of. [dpid] -> Switch
adjacency = defaultdict(lambda:defaultdict(lambda:None)) # Adjacency map. [sw1][sw2] -> port from sw1 to sw2
path_map = defaultdict(lambda:defaultdict(lambda:(None,None))) # [sw1][sw2] -> (distance,intermediate)
#path_hub = defaultdict(lambda:defaultdict(lambda:(None,None))) # [sw1][sw2] -> (distance, intermediate) within a hub
mac_map = {} # ethaddr -> (switch,port)

SWindex = 0
#SWhosts = [] # Host we know of [packet.src] -> Switch

# _calc_paths() is a routine from l2_multi.py
def _calc_paths (nbs,nbh):
   """
   Essentially Floyd-Warshall algorithm
   """

   mapping_completed = True ;

   sws = switches.values()
#   print sws,len(sws),sws[0],sws[1]
   path_map.clear()
   for k in sws:
     for j,port in adjacency[k].iteritems():
       if port is None: continue
       path_map[k][j] = (1,None)
     path_map[k][k] = (0,None) #distance, intermediate
 
   for i in sws:
     for j in sws:
       #a = path_map[i][j][0]
       a = adjacency[i][j]
       if a is None: a = "*"
       print a,
     print

   for k in sws:
     for i in sws:
       for j in sws:
         if path_map[i][k][0] is not None:
           if path_map[k][j][0] is not None:
            # i -> k -> j exists
            ikj_dist = path_map[i][k][0]+path_map[k][j][0]
            if path_map[i][j][0] is None or ikj_dist < path_map[i][j][0]:
              # i -> k -> j is better than existing
              path_map[i][j] = (ikj_dist, k)

   m = 0
   n = 0
   path_hub = matrix(zeros([len(sws),len(sws)]))
   print "MAP--------------------"
   for i in sws:
     #if m < nbs:
       for j in sws:
         if m < nbs and n < nbs:
            path_hub[m,n] = path_map[i][j][0]
            #print m,n,
            #print path_hub[m,n],
         n=n+1
         print path_map[i][j][0],
       print
       n=0
       m=m+1

   print"HUB---------------------"
   for i in range(len(sws)):
     for j in range(len(sws)):
       if math.isnan(path_hub[i,j]) == True or path_hub[i,j] == None:
          mapping_completed = False ;
       print path_hub[i,j],
     print

   return mapping_completed ;

# Routine from l2_multi.py
def _get_raw_path(src,dst):
  if len(path_map) == 0: _calc_paths()
  if src is dst:
    print "We are here !"
    return []
  if path_map[src][dst][0] is None:
    return None
  intermediate = path_map[src][dst][1]
  if intermediate is None:
    print "Directly connected"
    return []
  return _get_raw_path(src, intermediate) + [intermediate] + \
         _get_raw_path(intermediate,dst)  

# Routine from l2_multi.py
def _check_path(p):
   for i in range(len(p) - 1):
     if adjacency[p[i][0]][p[i+1][0]] != p[i][1]:
       return False
   return True

def _get_path(src,dst,final_port):
   print "-----------------"
   print "PATH",src,"TO",dst
   print "-----------------"
   if src == dst:
     path = [src]
   else:
     path = _get_raw_path(src,dst)
     if path is None: return None
     path = [src] + path + [dst]
   r = []
   for s1,s2 in zip(path[:-1],path[1:]):
      port = adjacency[s1][s2]
      r.append((s1,port))
   r.append((dst,final_port))
   print "----------------"
   print "COOKED: ",r
   print "-----------------"

   #assert _check_path(r)
   if _check_path(r) == True:
      print "--------------"
      print "TRUE"
      print "--------------"
      return r
   else:
      print "--------------"
      print "FALSE"
      print "--------------"
      return None

class Hub(object):

    def __init__(self,dpid,mac,hosts=[],malloc=False):
        self.dpid = dpid
        self.mac = mac
        self.hosts = hosts
        self.malloc = malloc
        #self.jurid = jurid

class Switch(object):

    def __init__(self,port,mac):
        self.port = port 
        self.mac = mac 
        #self.jurid = jurid
        #self.rules = rule

def dpid_to_mac(dpid):
    return EthAddr(dpidToStr(dpid)) 

# Service phase#1 is "Allocation of mobile resources for a given user"
class SwitchAlloc (EventMixin): # Should be renamed "SwitchEvents" or "SwitchAlloc"
    '''  
    Handle events at each switch, including mobile resource allocations for a given user
    '''
    def __init__(self,connection,transparent):
        self.connection = connection
        self.transparent = transparent
        self._listeners = self.listenTo(connection)
        #self.path = path
    
    def handle_Computations(mobilealloc,hub,flow): 
        '''
        Nothing yet
        '''       

    def handle_MobileAlloc(self,SWindex,SWhosts):
        '''
        Allocates mobile resources for the user
        '''
        mobilehub = self.buildMobileHub(SWindex,SWhosts)
        print mobilehub
 
    def _handle_PacketIn(self,event):
        #log.debug("Packet number is :#%i",packetNb+1)

        # Time out old packets
        # time.sleep(10)  
        nbh = NBH
        nbs = NBS

        # Check out the current switch map & selected hub
        global isHubCompleted
        if isHubCompleted == False and _calc_paths(nbs,nbh) == True:
          log.debug("=============================================")
          log.debug("MAPping COMPLETED - Handle mobile allocations")
          log.debug("=============================================")
  
          #currentSwitch
          dpid = event.connection.dpid

          SWhosts = []
          for i in range(nbh): # nbPhonePerSW     
              print i+1
              SWhosts.append(i+1)  
         
          currentHub = Hub(dpid,dpid_to_mac(dpid),SWhosts)
         
          #if Switch juridiction == user's juridiction
          if dpid not in hubTable and len(hubTable) < nbs:
             log.debug("-------------------")
             log.debug("BUILDING Mobile Hub")
             log.debug("-------------------")
             print len(hubTable)
             #time.sleep(5)
             hubTable[dpid] = {}
             hubTable[dpid] = currentHub
             if currentHub.malloc == False:
                self.handle_MobileAlloc(currentHub,SWhosts)
          
          if len(hubTable) == nbs:
             isHubCompleted = True
             log.debug("====================")
             log.debug("Mobile Hub COMPLETED")
             log.debug("====================")
             global hub
             print hub 

             #New packets 
             packet = event.parse()
             dpid = event.connection.dpid
             inport = event.port
             buffer_id = event.ofp.buffer_id

             log.debug("Switch entry has PORT:%i and MAC:%s",inport,dpid_to_mac(dpid))
             log.debug("Packet has HOST SRC:%s and HOST DST:%s",packet.src,packet.dst)
             macToPort[packet.src] = event.port
  
             log.debug("Call Flow ORCHESTRATOR")
             ### rules = seld.rulesOrchestrator(nbs,nbh,moduloSWT,moduloSWH)
             self.flowOrchestrator(dpid,inport,packet,buffer_id,moduloSWT,moduloHST) # buffer_id,rules)

        elif isHubCompleted == False and _calc_paths(nbs,nbh) == False :
          log.debug("---------------------")
          log.debug("MAPping still RUNNING")
          log.debug("---------------------")  

        # Time out old packet
        #time.sleep(5)

        elif isHubCompleted == True:
          # New packets
          packet = event.parse()
          dpid = event.connection.dpid
          inport = event.port
          buffer_id = event.ofp.buffer_id
       
          if dpid in hubTable:
            #log.debug("Switch entry has PORT:%i and MAC:%s",inport,dpid_to_mac(dpid))
            #log.debug("Packet has HOST SRC:%s and HOST DST:%s",packet.src,packet.dst)
            macToPort[packet.src] = event.port
   
            #log.debug("Call Flow Orchestrator")
            self.flowOrchestrator(dpid,inport,packet,buffer_id,moduloSWT,moduloHST)

            #if traffic detected
            #log.debug("Traffic DETECTED - Init Peer Connection")
            self.initPeerConnection("0",2,2,2)

        #log.debug("Check our quantum entries")
        #for entry in quantum:
        #    if entry == (dpid,inport):
        #          log.debug("MATCH found")
        #          if buffer_id is not None:
        #             if quantum[(dpid,inport)] == True:
        #                log.debug("FLOOD everything at SWITCH:%s on PORT:%i",dpid_to_mac(dpid),inport)
        #                #self.handle_MobileAlloc(SWindex,SWhosts,packet,isHub=True,isData=False,isComp=False)
        #                
        #                self.forward(inport,buffer_id) # FLOOD everything
        #                log.debug("FORWARD packet at SWITCH: %s on PORT: %i",dpid_to_mac(dpid),inport) 
        #             else:
        #                self.drop(packet,dpid,inport,buffer_id)
        #                log.debug("DROP packet at SWITCH: %s on PORT: %i ",dpid_to_mac(dpid),inport)
        #          else:
        #             log.debug("Time out old packet")
        #             time.sleep(5)
        #print "===========================================================" 
        #log.debug("End of quantum check with nb of packets dropped:%i", droppedNb)
        #print "==========================================================="

    def flowOrchestrator(self,dpid,inport,packet,buffer_id,moduloSWT,moduloHST):
            if dpid in hubTable: # if SWindex % moduloSWT - rule = (moduloSWT,moduloHST)
               #global hub
               #print hub
               # if inport == hubTable[dpid].hosts.index(inport): # if inport % moduloHST
               # Choose the HOST PORT within a SWITCH you want to ping from
               if taskparallel == True:
                 # inport -> ouport works, while outport -> inport don't
                 if inport == 2:
                    self.manageFlow(dpid,inport,packet,buffer_id)
               else:
                 # Allow flow from all ports
                 for inport in hubTable[dpid].hosts:
                    #log.debug("================================================")
                    #log.debug("CHECK OUT the data/packet FLOW for ENTRY PORT:%i",inport)
                    #log.debug("================================================")
                    self.manageFlow(dpid,inport,packet,buffer_id)

                 # Constraint flow to hub
                
    def manageFlow(self,dpid,inport,packet,buffer_id):
        self.isNewL3Switch(dpid,packet)
        self.isTransparentL2Proxy(packet,dpid,inport,buffer_id)
        self.isL2Multicast(packet,dpid,inport,buffer_id)
        self.isNextL3Packet(dpid,inport,packet)

    def orchestrator(self,dpid,inport,rules,packet,buffer_id,moduloSwitch):
            '''
            Low level API that inferfaces between the OpMubApp (Mobile Alloc API) and the controllers/switches as follows:
            OpMubApp <-> NB API <-> Orchestrator <-> CTRs/SWs <-> Mobile resources
            '''
            # Check out the data/packet flow 
            self.isNewL3Switch(dpid,packet)
            self.isTransparentL2Proxy(packet,dpid,inport,buffer_id)
            self.isL2Multicast(packet,dpid,inport,buffer_id)
            self.isNextL3Packet(dpid,inport,packet)
            # Activate / Deactivate controllers
            # Activate / Deactivate switched
            # Drop / Forward packets 
            # Add quantum rules in quantum table
            log.debug("Quantum rules are %s",rules[0])
            for rule in rules:
              if rule == (0,0) :
                 self.AddRule(dpid = dpid,inport = inport,value=False) 
              elif rule == (0,1) :
                 if (inport % moduloSwitch) == 0 :
                     self.AddRule(dpid = dpid, inport = inport, value = True)
              elif rule == (1,0) :
                 if (inport % moduloSwitch) != 0 : 
                     self.AddRule(dpid = dpid, inport = inport, value = True)
              elif rule == (1,1) :
                 self.AddRule(dpid = dpid, inport = inport, value = True) 

            #self.DeleteRule(dpid = dpid, inport = inport)
    
    # Build A hub    
    def buildMobileHub(self,currentSwitch,hosts):
            '''
            Uses a REST interface to query SWITCH addresses that should be in the same computing hub
            '''    
            
            # POX does not support REST
            #if REST : Send a REST API request
            # url = "http://%s:6633/opmub/mobile/connections/json" % controllerIP
            # switches = json.load(urllib2.urlopen(url)) 

            #try REST build command
            #for i in len(switches)
            # params = "{\"dpid\":\"%s\"}" % swicthes[i][dpid]
            # url = "http://%s:6633/opmub/hub/enable/json" % controllerIP
            # connection = httplib.HTTPConnection(url)
            # connection.request("BUILD",command,params)
            # hub = connection.getresponse().read   
            
            keyFound = False ;
 
            #Build a dictionary of switches and hosts
            name = '%s' % currentSwitch.mac
            global hub
            for key in hub.keys():
              if key == name:
                 keyFound = True 
                 hub[key] = hosts
             
            if keyFound == False:
               hub[name] = hosts 

            for key,value in hub.iteritems():
              print key,value
           
            currentSwitch.malloc = True
            hubTable[currentSwitch.dpid].hosts = hosts 
            hubTable[currentSwitch.dpid].malloc = currentSwitch.malloc

            return hub  

    # Crowdsource data
    def Crowdsource(hub,data):
            '''
            Uses a REST interface to crowdsource data from a given hub
            '''
            #for each mobile in hub:
                #dst,src,dstPort,srcPort = data.split(',')
                #install flow from mobile (src) to server (dst) (peer to peer connection)
                #subprocess.call(['sudo','python','./peer_to_peer.py'])
                #send piece of code to src
                #get back result on dst
    
    def initPeerConnection(self,maxpeers,serverport,myid,serverhost): 
            # Routines from btpeer.py

            # Init peer connection
            peerConn = btpeer.__init__(maxpeers,serverport)

            if peerConn != None:
               log.debug("Check live peers/ Ping all currently known peers")
               peerConn.checklivepeers()

               log.debug("Construct server socket listening on the given port")
               clientsock = peerConn.makeserversocket(serverport,backlog=5)
               
               log.debug("Dispatch mess from the socket connection")
               peerConn.__handlpeer(clientsock)
             
               #log.debug("Add next immediate switch/peer")
               #peerConn.addrouter = [(nextpeerid,host,port)]
               #log.debug("Forward message to next immediate switch/peer"
               #peerConn.sendtopeer(peerid,msgtype,msgdata)              

               #log.debug("Add peer in table")
               #peerConn.addpeer(peerid,host,port)
               #log.debug("return host,port for a given peerid")
               #(host,port) = peerConn.getpeer(peerid)
               #log.debug("Forward message to specific (host,port)"
               #peerConn.connectandsemd(host,port,msgtype,msgdata,pid=None,waitreply=True)
             
               #log.debug("Check out size of peer table")
               #nbpeer = peerConn.numberofpeers()
               #isMaxpeerreached = peerConn.maxpeersreached() 

    def disconnect(self):
      if self.connection is not None:
         log.debug("Disconnect %s" % (self.connection,))
         self.connection.removeListeners(self._listeners)
         self.connection = None
         self._listeners = None 

    def connect(self,connection):
      #if self._dps is None:
      #   self._dps = connection.dpid
      #assert self._dps == connection.dpid
      #if self.ports is None:
      #   self.ports = connection.features.ports
      self.disconnect()
      log.debug("Connect %s" % (connection,))
      self.connection = connection
      self._listeners = self.listenTo(connection)

    # Flood packet
    def forward(self,inport,buffer_id):
            msg = of.ofp_flow_mod()
            msg.actions.append(of.ofp_action_output(port = of.OFPP_FLOOD))
            #msg.buffer_id = buffer_id
            msg.in_port = inport
            self.connection.send(msg)            
    
    # Drop packet 
    def drop(self,packet,dpid,inport,buffer_id, duration = None):
        """
        Drop this packet and similar ones 
        """
        global droppedNb
        droppedNb = droppedNb + 1
        if duration is not None:
           if not isinstance(duration,tuple):
             duration = (duration,duration)
           msg = of.ofp_flow_mod()
           msg.match = of.ofp_match.from_packet(packet)
           msg.idle_timeout = duration[0]
           msg.hard_timeout = duration[1] 
           msg.buffer_id = -1 # kill the buffer, Mark is dead
           #self.connection.send(msg)
           #log.debug("drop packet with timeout")
           core.openflow.sendToDPID(dpid,msg)
        elif buffer_id != -1:
           msg = of.ofp_packet_out()
           msg.buffer_id = -1 # kill the buffer, Mark is dead
           msg.in_port = inport
           #self.connection.send(msg)
           #log.debug("drop packet without timeout")
           core.openflow.sendToDPID(dpid,msg)  

    #Layer3 Learning
    def isNewL3Switch(self,dpid,packet):
        if dpid not in arpTable:
           log.debug("Registering new switch -- create an empty arpTable")
           arpTable[dpid] = {}
           log.debug("Traffic DETECTED")
           
           for fake in fakeways:
             arpTable[dpid][IPAddr(fake)] = Switch(of.OFPP_NONE,dpid_to_mac(dpid))
             log.debug("ARP entry created with PORT:%i, MAC:%s and IPAddr(fake):%s",Switch.port,Switch.mac,IPAddr(fake))
        else:
           log.debug("Current ARP entry is Switch with MAC:%s and IPAddr(fake):%s",dpid_to_mac(dpid),arpTable[dpid])           
           #packet.dst = EthAddr(packet.src).toStr()

    # Swicthes/Proxy must not modify the packet
    def isTransparentL2Proxy(self,packet,dpid,inport,buffer_id):
        if not self.transparent:
           # LLDP protocol is a link layer protocol in the Internet Protocol Suite used by Network devices for advertising their identity, capabilities and neighboors on a IEEE 802 LAN, principally wired Ethernet.  
           if packet.type == packet.LLDP_TYPE or packet.dst.isBridgeFiltered():
              self.drop(packet,dpid,inport,buffer_id,10)
              #log.debug("Is not transparent - Packet dropped")
              return

    #Layer2 Learning #Unlike traditional IP Multicast, peercasting can facilitate on-demand content delivery.
    def isL2Multicast(self,packet,dpid,inport,buffer_id): # Must be replaced with "L2PeerCasting" 
        if packet.dst.isMulticast():
           log.debug("isMulticast - FLOOD everything")
           self.forward(inport,buffer_id)
        else:
           if packet.dst not in macToPort:
              log.warning("Port for packet dst not found  - FLOOD everything")
              self.forward(inport,buffer_id) # flood everything
           else:
              destport = macToPort[packet.dst]
              #destport2 = mac_map[packet.dst]
              #print "--------------"
              #log.debug("Src SW is %s .Dst SW is %s",destport2[0],destport2[1])
              #print "--------------"
              if destport == inport:
                 log.warning("Same port for packet from %s -> %s on %s." % (packet.src,packet.dst,destport))
                 self.drop(packet,dpid,inport,buffer_id,10)
                 return
              log.debug("Installing flow path for %s.%i to %s.%i" % (packet.src,inport,packet.dst,destport))
              msg = of.ofp_flow_mod()
              msg.match = of.ofp_match.from_packet(packet)
              msg.actions.append(of.ofp_action_output(port = destport))
              msg.buffer_id = buffer_id
              self.connection.send(msg)  
  
    #Layer3 learning
    def isNextL3Packet(self,dpid,inport,packet):
        if isinstance(packet.next,ipv4):
           log.debug("%i %i IP %s => %s",dpid,inport,packet.next.srcip,packet.next.dstip)
           #Learn or update port/MAC info
           if packet.next.srcip in arpTable[dpid]:
              if arpTable[dpid][packet.next.srcip] != Switch(inport, packet.src):
                 log.info("%i %i learned AGAIN %s", dpid, inport, packet.next.srcip)
           else:
              log.debug("%i %i learned %s", dpid,inport,str(packet.next.srcip))
           arpTable[dpid][packet.next.srcip] = Switch(inport,packet.src) 

        elif isinstance(packet.next,arp):
           a = packet.next
           log.debug("%i %i ARP %s %s => %s",dpid,inport,{arp.REQUEST:"request",arp.REPLY:"reply"}.get(a.opcode,'op:%i' % (a.opcode,)),str(a.protosrc),str(a.protodst))   

    def AddRule(self,dpid,inport,value):
        if(self.CheckRule(dpid,inport,value) == False):
           quantum[(dpid,inport)]=value   
           log.debug("Rule with value:%s installed on Switch with Port %i and Mac: %s",value,inport, dpid_to_mac(dpid))

    def DeleteRule(self,dpid,inport):
        # POX does not support REST
        #if REST
        #try REST del command
        #for i in len(rules)
        #  params = "{\"ruleid\":\"%s\"}" % rules[i][ruleid] 
        #  url = "http://%s:6633/opmub/mobile/connections/rules/json" % controllerIP
        #  connection = httplib.HTTPConnection(url)
        #  connection.request("DELETE",command,params)
        #  row = connection.getresponse().read()
        try:
          del quantum[(dpid,inport)]
          log.debug("Deleting rule on %s.%i",dpid_to_mac(dpid),inport)
        except KeyError:
          log.error("Cannot find in %s.%i",dpid_to_mac(dpid),inport)

    def CheckRule(self,dpid,inport,value):
        try:
          entry = quantum[(dpid,inport)]
          if(entry ==  value):
            log.debug("Rule found in %s.%i",dpid_to_mac(dpid),inport)
            return True
          else:
            log.debug("Rule NOT found in %s.%i",dpid_to_mac(dpid),inport)
            return False
        except KeyError:
            log.debug("Rule NOT found in %s.%i",dpid_to_mac(dpid),inport)
            return False

class OpMubApp (EventMixin):
     '''
     Initial (REST) service : Allocation of Mobile resources for a given user
     The FINAL service architecture should be as follows :
     OpMubApp <-> NB API <-> Orchestrator <-> CTRs/SWs <-> Mobile Resources
     '''

     # Warning : POX does not support REST

     def __init__(self,transparent, fakeways = [],arp_for_unknowns = False):
         self.listenTo(core.openflow)
         self.listenTo(core.openflow_discovery) 
         self.transparent = transparent

     def _handle_LinkEvent(self,event):
         '''
         Copy-pasted routine from l2_multi.py
         '''
         def flip(link):
            return Discovery.Link(link[2],link[3],link[0],link[1])

         l = event.link
         sw1 = switches[l.dpid1]
         sw2 = switches[l.dpid2]

         # Invalidate all flows and path info.
         # For link adds, this makes sure that if a new link leads to an 
         # improved path, we use it.
         # For link removals, this makes sure that we dont use a path that
         # may be broken.
         # NOTE: This could be radically improved (e.g., not *ALL* paths break)
         log.debug("Clear Path Map")
         clear = of.ofp_flow_mod(match=of.ofp_match(),command=of.OFPFC_DELETE)
         for sw in switches.itervalues():
           sw.connection.send(clear)
         path_map.clear()
           
         if event.removed:
           # This link no longer okay
           log.debug("This link no longer okay")
           if sw2 in adjacency[sw1]: del adjacency[sw1][sw2]
           if sw1 in adjacency[sw2]: del adjacency[sw2][sw1]

           log.debug("But maybe there is another way to connect these...")
           for ll in core.openflow_discovery.adjacency:
               if flip(ll) in core.openflow_discovery.adjacency:
                  log.debug("Yup, link goes both ways")
                  adjacency[sw1][sw2] = ll.port1
                  adjacency[sw2][sw1] = ll.port2
                  log.debug("Fixed -- new link chosen to connect these")
                  break
         else:
            # If we already consider these nodes connected, we can
            # ignore this link up.
            # Otherwise, we might be interested...
            if adjacency[sw1][sw2] is None:
              # These previously were not connected. If the link
              # exists in both directions, we condifer them connected now.
              if flip(l) in core.openflow_discovery.adjacency:
                 log.debug("Yup, link goes both ways -- connected !")
                 adjacency[sw1][sw2] = l.port1
                 adjacency[sw2][sw1] = l.port2

            # If we have learned a MAC on this port which we now know to
            # be connected to a switch, unlearn it. 
            bad_macs = set()
            for mac,(sw,port) in mac_map.iteritems():
               # print sw,sw1,port,l.port1
               if sw is sw1 and port == l.port1:
                 if mac not in bad_macs:
                   log.debug("Unlearned %s",mac)
                   bad_macs.add(mac)
               if sw is sw2 and port == l.port2:
                 if mac not in bad_macs:
                   log.debug("Unlearned %s",mac)
                   bad_macs.add(mac)
            for mac in bad_macs:
               del mac_map[mac]  

     def _handle_ConnectionUp(self,event):
         """
         Create a new LLDP packet per port 
         """
         #assert even.dpid in self._dps

         log.debug("Connection %s" % (event.connection,))
         sw = switches.get(event.dpid)
         if sw is None:
            #New Switch
            sw = SwitchAlloc(event.connection,self.transparent)
            switches[event.dpid] = sw
         else:
            sw.connect(event.connection)

         #self._dps.add(event.dpid)

     def _handle_ConnectionDown(self,event):
         """
         Delete all associated links
         """
         #assert event.dpid in self._dps
         #sw = switches.get(event.dpid)
         #if sw is not None:
         #   sw.disconnect()
         #   pass
         #self._dps.remove(event.dpid)

         #must delete links as well
         #deleteme = []
         #l = event.link
         #if l.dpid1 == event.dpid or l.dpid2 == event.dpid:
         #     deleteme.append(l)

         #self._deletlinks(deleteme) 
            
def launch (fakeways="",arp_for_unknowns=None,transparent=False):
    '''
    Starting the OpMub module
    '''
    if 'openflow_discovery' not in core.components:
      import pox.openflow.discovery as discovery
      core.registerNew(discovery.Discovery)
    log.debug("Starting OpMub & Discovery Modules")
    fakeways = fakeways.replace(","," ").split()
    fakeways = [IPAddr(x) for x in fakeways]
    if arp_for_unknowns is None:
      arp_for_unknowns = len(fakeways) > 0
    else:
      arp_for_unknowns = str_to_bool(arp_for_unknowns)
    fakeways = set(fakeways)
    core.registerNew(OpMubApp, str_to_bool(transparent))


