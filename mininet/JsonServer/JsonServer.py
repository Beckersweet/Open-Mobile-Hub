"""
JsonServer.py
Open Mobile Hub

A local server that gets and gives JSON objects for updating and monitoring both
real and virtual hosts on an Open Mobile Hub network. This server is meant to be
extended for network communication via protocols such as MQTT.

Created by Gareth Johnson
Copyright (c) 2014 Beckersweet. All rights reserved.
"""

from json import loads as decode
from json import dumps as encode

# Pair names
AVAILABLE = 'available'
COMMAND = 'command'
CONFIRMATION = 'confirmation'
DATA = 'data'
ERROR = 'error'
FROM = 'from'
IP = 'ip'
LATITUDE = 'latitude'
LONGITUDE = 'longitude'
MAC = 'mac'
NAME = 'name'
REAL_HOSTS = 'realHosts'
TO = 'to'
VIRTUAL_HOSTS = 'virtualHosts'

class JsonServer:

	def __init__ (self):

		'''
		Dictionary of the form
			{
			    NAME: {
			        IP: string,
			        MAC: string,
			        LATITUDE: float,
			        LONGITUDE: float,
			        AVAILABLE: boolean
			    },
			    ...
			}
		'''
		self.realHosts = {}

		'''
		Dictionary of the form
			{
			    NAME: {
			        IP: string,
			        MAC: string,
			        AVAILABLE: boolean
			    },
			    ...
			}
		'''
		self.virtualHosts = {}

	def request (self, data):

		# Check JSON syntax.
		try: request = decode(data)
		except: return self.makeError('Request is not JSON')

		# Check sender.
		try: client = request[FROM]
		except: return self.makeError('No "' + FROM + '" value')

		# Check command.
		try:
			command = request[COMMAND]

			if command == 'addRealHost':
				name = request[NAME]
				ip = request[IP]
				mac = request[MAC]
				latitude = float(request[LATITUDE])
				longitude = float(request[LONGITUDE])
				available = bool(request[AVAILABLE])
				self.realHosts[name] = {
					IP: ip,
					MAC: mac,
					LATITUDE: latitude,
					LONGITUDE: longitude,
					AVAILABLE: available
				}
				return self.makeConfirmation('Real host added', client)

			elif command == 'addVirtualHost':
				name = request[NAME]
				ip = request[IP]
				mac = request[MAC]
				available = bool(request[AVAILABLE])
				self.virtualHosts[name] = {
					IP: ip,
					MAC: mac,
					AVAILABLE: available
				}
				return self.makeConfirmation('Virtual host added', client)

			elif command == 'removeRealHost':
				name = request[NAME]
				if name not in self.realHosts:
					return self.makeError('Invalid host', client)
				del self.realHosts[name]
				return self.makeConfirmation('Real host removed', client)

			elif command == 'removeVirtualHost':
				name = request[NAME]
				if name not in self.virtualHosts:
					return self.makeError('Invalid host', client)
				del self.virtualHosts[name]
				return self.makeConfirmation('Virtual host removed', client)

			elif command == 'getRealHosts':
				hostList = []
				for host in self.realHosts:
					name = host
					ip = self.realHosts[host][IP]
					mac = self.realHosts[host][MAC]
					latitude = self.realHosts[host][LATITUDE]
					longitude = self.realHosts[host][LONGITUDE]
					available = self.realHosts[host][AVAILABLE]
					hostList.append({
						NAME: name,
						IP: ip,
						MAC: mac,
						LATITUDE: latitude,
						LONGITUDE: longitude,
						AVAILABLE: available
					})
				return encode({TO: client, REAL_HOSTS: hostList})

			elif command == 'getVirtualHosts':
				hostList = []
				for host in self.virtualHosts:
					name = host
					ip = self.virtualHosts[host][IP]
					mac = self.virtualHosts[host][MAC]
					available = self.virtualHosts[host][AVAILABLE]
					hostList.append({
						NAME: name,
						IP: ip,
						MAC: mac,
						AVAILABLE: available
					})
				return encode({TO: client, VIRTUAL_HOSTS: hostList})

			elif command == 'setRealHostAvailability':
				name = request[NAME]
				if name not in self.realHosts:
					return self.makeError('Invalid host', client)
				available = request[AVAILABLE]
				self.realHosts[name][AVAILABLE] = available
				return self.makeConfirmation('Availability set', client)

			elif command == 'setVirtualHostAvailability':
				name = request[NAME]
				if name not in self.virtualHosts:
					return self.makeError('Invalid host', client)
				available = request[AVAILABLE]
				self.virtualHosts[name][AVAILABLE] = available
				return self.makeConfirmation('Availability set', client)

			else:
				raise ValueError

		except (KeyError, ValueError):
			return self.makeError('Invalid command', client)

		except:
			return self.makeError('Unexpected error', client)

	def makeConfirmation(self, confirmation, to):
		confirmationDictionary = {TO: to, CONFIRMATION: confirmation}
		confirmationJson = encode(confirmationDictionary)
		return confirmationJson

	def makeError (self, error, to='null'):
		errorDictionary = {TO: to, ERROR: error}
		errorJson = encode(errorDictionary)
		return errorJson