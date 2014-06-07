/*
 * HostDetailActivity.java
 * Open Mobile Hub
 *
 * Created by Gareth Johnson
 * Copyright (c) 2014 Beckersweet. All rights reserved.
 */

package com.beckersweet.opmub;

import java.io.File;

import org.eclipse.paho.client.mqttv3.MqttCallback;
import org.eclipse.paho.client.mqttv3.MqttClient;
import org.eclipse.paho.client.mqttv3.MqttConnectOptions;
import org.eclipse.paho.client.mqttv3.MqttDefaultFilePersistence;
import org.eclipse.paho.client.mqttv3.MqttDeliveryToken;
import org.eclipse.paho.client.mqttv3.MqttException;
import org.eclipse.paho.client.mqttv3.MqttMessage;
import org.eclipse.paho.client.mqttv3.MqttPersistenceException;
import org.eclipse.paho.client.mqttv3.MqttTopic;
import org.json.JSONArray;
import org.json.JSONObject;

import android.os.Handler;
import android.os.HandlerThread;

public class MqttHelper implements MqttCallback {
	
	protected static final boolean DEBUG = true;
	protected static final String DEBUG_TAG = "BeckersweetMqttClient:Helper";
	public static final String BROKER_NAME = "broker";
	protected static final String THREAD_NAME = DEBUG_TAG; // for handler thread
	protected static final boolean CLEAN_SESSION = true;
	
	public boolean isWaiting; // whether client is waiting for a response
	
	private int connectionHandlerReturnCode; // hack for handler return value
	private File cacheDirectory; // for persistenceFile (below)
	private Handler connectionHandler;
	private HandlerThread handlerThread; // background thread that runs client
	private MqttCallback callback; // for receiving messages from broker
	private MqttClient client;
	private MqttConnectOptions connectionOptions;
	private MqttDefaultFilePersistence persistenceFile; // record of messages
	private MqttMessage message; // for outgoing messages
	private MqttTopic brokerTopic;
	private JSONArray hosts;
	private String messageString; // String version of outgoing message
	private String clientTopicName;
	private UserMessageHelper messenger;
	
	public MqttHelper(UserMessageHelper newMessenger, File newCacheDirectory) {
		messenger = newMessenger;
		cacheDirectory = newCacheDirectory;
		
		isWaiting = false;
		callback = this;
	}
	
	public int connect(String url, String deviceId) {
		try {
			messenger.printDebugMessage("Creating persistence file...");
			String directoryPath = cacheDirectory.getAbsolutePath();
			persistenceFile = new MqttDefaultFilePersistence(directoryPath);
		} catch(MqttPersistenceException e) {
			messenger.showAlert("Problem with persistence file: " +
					e.getMessage());
			e.printStackTrace();
			return 1;
		}
		
		messenger.printDebugMessage("Creating handler thread...");
		handlerThread = new HandlerThread(THREAD_NAME);
		handlerThread.start();
		
		messenger.printDebugMessage("Creating connection handler...");
		connectionHandler = new Handler(handlerThread.getLooper());
		
		messenger.printDebugMessage("Setting connection options...");
		connectionOptions = new MqttConnectOptions();
		connectionOptions.setCleanSession(CLEAN_SESSION);
		
		try {
			messenger.printDebugMessage("Creating client...");
			client = new MqttClient(url, deviceId, persistenceFile);
		} catch (MqttException e) {
			messenger.showAlert("Problem with creating client: " +
					e.getMessage());
			e.printStackTrace();
			return 1;
		}
		
		connectionHandlerReturnCode = -1;
		
		connectionHandler.post(new Runnable() {
			@Override
			public void run() {
				try {
					messenger.printDebugMessage("Connecting...");
					client.connect(connectionOptions);
					messenger.printDebugMessage("Connected.");
					connectionHandlerReturnCode = 0;
				} catch (MqttException e) {
					messenger.showAlert("Connection problem: " +
							e.getMessage());
					e.printStackTrace();
					connectionHandlerReturnCode = 1;
				}
			}
		});
		
		while (connectionHandlerReturnCode == -1) {
			// Wait for connection handler thread to finish.
		}
		
		return connectionHandlerReturnCode;
	}
	
	public void disconnect() {
		connectionHandler.post(new Runnable() {
			@Override
			public void run() {
				try {
					messenger.printDebugMessage("Disconnecting...");
					client.disconnect();
				} catch (MqttException e) {
					messenger.showAlert("Disconnection problem: " +
							e.getMessage());
					e.printStackTrace();
					return;
				}
			}
		});
	}

	public boolean isConnected() {
		if (client != null)
			return client.isConnected();
		return false;
	}

	public int sendMessage(String newMessageString) {
		messageString = newMessageString;
		connectionHandlerReturnCode = -1;
		connectionHandler.post(new Runnable() {
			@Override
			public void run() {
				try {
					client.setCallback(callback);
					message = new MqttMessage();
					message.setPayload(messageString.getBytes());
					
					messenger.printDebugMessage("Publishing message...");
					brokerTopic = client.getTopic(BROKER_NAME);
					brokerTopic.publish(message);
				} catch (MqttException e) {
					messenger.showAlert("Publication problem: " +
							e.getMessage());
					e.printStackTrace();
					connectionHandlerReturnCode = 1;
				}
			}
		});
		
		while (connectionHandlerReturnCode == -1) {
			// Wait for connection handler thread to finish.
		}
		
		return connectionHandlerReturnCode;
	}
	
	public void subscribe(String topicFilter) {
		clientTopicName = topicFilter;
		isWaiting = true;
		connectionHandler.post(new Runnable() {
			@Override
			public void run() {
				if (isConnected()) {
					try {
						client.setCallback(callback);
						messenger.printDebugMessage("Subscribing to '" +
								clientTopicName + "'...");
						client.subscribe(clientTopicName);
						messenger.printDebugMessage("Subscribed. Waiting for " +
								"response...");
					} catch (MqttException e) {
						messenger.showAlert("Problem with subscription: " +
								e.getMessage());
						e.printStackTrace();
						isWaiting = false;
					}
				}
			}
		});
	}
	
	@Override
	public void connectionLost(Throwable cause) {
		messenger.printDebugMessage("Connection lost: " + cause.getMessage());
	}

	@Override
	public void deliveryComplete(MqttDeliveryToken token) {
		messenger.printDebugMessage("Message delivered successfully.");
		connectionHandlerReturnCode = 0;
	}

	@Override
	public void messageArrived(MqttTopic topic, MqttMessage message)
			throws MqttException {
		String incomingMessage = message.toString();
		messenger.printDebugMessage("Message received: " + incomingMessage);
		
		JSONObject jsonMessage;
		try {
			jsonMessage = new JSONObject(incomingMessage);
		} catch (Exception e) {
			messenger.printDebugMessage("Incoming message not JSON.");
			isWaiting = false;
			return;
		}
		
		try {
			hosts = new JSONArray(jsonMessage.getString("realHosts"));
		} catch (Exception e) {
			messenger.printDebugMessage("Incoming message has no field " +
					"'realHosts'.");
		}
		
		isWaiting = false;
	}
	
	public JSONArray getHosts() {
		return hosts;
	}

}
