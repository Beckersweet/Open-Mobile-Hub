"""
OpMub_wsh.py
Open Mobile Hub

WebSocket handler for web app

Created by Gareth Johnson
Copyright (c) 2014 Beckersweet. All rights reserved.
"""

import paho.mqtt.client as mqtt


BROKER_PORT = 9998
BROKER_ADDRESS = '127.0.0.1'
TOPIC_PREFIX = 'OpenMobileHub'
CLIENT_NAME = 'web-test'
BROKER_NAME = 'broker'


''' MQTT Client Behaviour '''

def on_connect(client, request, returnCode):
	if returnCode == 0:
		request.ws_stream.send_message('Connection established')
	else:
		request.ws_stream.send_message('Unable to connect to broker')

def on_disconnect(client, request, returnCode):
	if returnCode == 0:
		request.ws_stream.send_message('Connection closed successfully')
	else:
		request.ws_stream.send_message('Disconnected from broker ' + \
				'unexpectedly')

def on_message(client, request, message):
	messageString = str(message.payload)
	request.ws_stream.send_message('Message received: "' +
			messageString + '"')

def on_publish(client, request, messageId):
	request.ws_stream.send_message('Message sent')

def on_subscribe(client, request, messageId, qualityOfServiceList):
	request.ws_stream.send_message('Subscribed to topic "' + CLIENT_NAME + '"')


''' WebSocket Handler Behaviour '''

def web_socket_do_extra_handshake(request):
	pass # Accept all requests

def web_socket_transfer_data(request):

	# Initialize client
	client = mqtt.Client(CLIENT_NAME, True, request)
	client.on_connect = on_connect
	client.on_disconnect = on_disconnect
	client.on_message = on_message
	client.on_publish = on_publish
	client.on_subscribe = on_subscribe

	# Start client
	client.connect(BROKER_ADDRESS, BROKER_PORT)
	client.subscribe(CLIENT_NAME)

	# Publish messages
	message1 = '{"from": "' + CLIENT_NAME + '", "command": "getRealHosts"}'
	message2 = '{"from": "' + CLIENT_NAME + '", "command": "getVirtualHosts"}'
	client.publish(BROKER_NAME, message1)
	client.publish(BROKER_NAME, message2)

	# Keep client running
	client.loop_forever()
