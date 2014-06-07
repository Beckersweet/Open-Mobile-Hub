/*
 * HostDetailActivity.java
 * Open Mobile Hub
 *
 * Created by Gareth Johnson
 * Copyright (c) 2014 Beckersweet. All rights reserved.
 */

package com.beckersweet.opmub;

import android.app.Activity;
import android.app.AlertDialog;
import android.app.Dialog;
import android.content.ContentResolver;
import android.content.Context;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.IntentSender;
import android.location.Location;
import android.net.wifi.WifiInfo;
import android.net.wifi.WifiManager;
import android.os.Bundle;
import android.provider.Settings.Secure;
import android.text.format.Formatter;
import android.util.Log;
import android.view.View;
import android.widget.EditText;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import com.google.android.gms.common.ConnectionResult;
import com.google.android.gms.common.GooglePlayServicesClient;
import com.google.android.gms.common.GooglePlayServicesUtil;
import com.google.android.gms.location.LocationClient;
import com.google.android.gms.location.LocationListener;

import java.io.File;
import java.io.FileOutputStream;
import java.io.OutputStreamWriter;

import org.json.JSONArray;
import org.json.JSONException;
import org.json.JSONObject;

@SuppressWarnings("deprecation")
public class MainActivity extends Activity implements LocationListener,
		GooglePlayServicesClient.ConnectionCallbacks,
		GooglePlayServicesClient.OnConnectionFailedListener {

	private static final boolean DEBUG = true;
	private static final String DEBUG_TAG = "BeckersweetMqttClient";
	private static final int DEFAULT_PORT = 9998;
	private static int CONNECTION_FAILURE_RESOLUTION_REQUEST = 1; // arbitrary #
	private static String MARKERS = "com.beckersweet.mqttclient.MARKERS";

	private String brokerUrl;
	private int port;
	private String deviceId;
	private String ipAddress;
	private String macAddress;
	private double latitude;
	private double longitude;

	private LocationClient locationClient; // for getting GPS coordinates
	private MqttHelper mqtt; // controls MQTT client for subscribing/publishing
	private JSONArray hosts; // array of host info returned from broker
	private ScrollView logWindow; // contains debug log
	private TextView log; // for debug messages
	private UserMessageHelper messenger; // controls debug messages and alerts
	private WifiManager wifiManager; // for getting IP address and MAC address
	private WifiInfo wifiInfo; // for getting IP address and MAC address
	
	@Override
	protected void onCreate(Bundle savedInstanceState) {
		super.onCreate(savedInstanceState);
		setContentView(R.layout.activity_main);
		
		// Initialize user message stuff.
		log = (TextView) findViewById(R.id.log_text);
		logWindow = (ScrollView) findViewById(R.id.log_window);
		messenger = new UserMessageHelper(this, log, logWindow, DEBUG,
				DEBUG_TAG);
		
		// Initialize MQTT client.
		File cacheDirectory = getCacheDir(); // for MQTT logs
		mqtt = new MqttHelper(messenger, cacheDirectory);
		
		// Check for Google Play services (needed for map).
		int result = GooglePlayServicesUtil.isGooglePlayServicesAvailable(this);
		if (result != ConnectionResult.SUCCESS) {
			Dialog errorDialog = GooglePlayServicesUtil.getErrorDialog(result,
					this, CONNECTION_FAILURE_RESOLUTION_REQUEST);
			errorDialog.show();
		}
		
		// Initialize location stuff.
		locationClient = new LocationClient(this, this, this);
		latitude = 0;
		longitude = 0;
		hosts = new JSONArray();
		
		// Get device ID from Android device.
		ContentResolver contentResolver = this.getContentResolver();
		String contentName = Secure.ANDROID_ID;
		deviceId = Secure.getString(contentResolver, contentName);
		messenger.printDebugMessage("Device ID: " + deviceId);
	}
	
	@Override
	protected void onStart() {
		super.onStart();
		locationClient.connect();
	}
	
	@Override
	protected void onStop() {
		locationClient.disconnect();
		super.onStop();
	}
	
	@Override
    public void onConnected(Bundle dataBundle) {
        // Display the connection status
        Toast.makeText(this, "Connected to Google Play Services",
        		Toast.LENGTH_SHORT).show();
    }
	
    @Override
    public void onDisconnected() {
        // Display the connection status
        Toast.makeText(this, "Disconnected from Google Play Services." +
        		"Please re-connect.", Toast.LENGTH_SHORT).show();
    }
    
    @Override
    public void onConnectionFailed(ConnectionResult connectionResult) {
        if (connectionResult.hasResolution()) {
            try {
                connectionResult.startResolutionForResult(this,
                        CONNECTION_FAILURE_RESOLUTION_REQUEST);
            } catch (IntentSender.SendIntentException e) {
                e.printStackTrace();
            }
        } else {
        	int errorCode = connectionResult.getErrorCode();
        	messenger.showAlert(Integer.toString(errorCode));
        }
    }

	@Override
	public void onLocationChanged(Location location) {
		latitude = location.getLatitude();
		longitude = location.getLongitude();
	}
	
	public int prepareConnection() {
		
		// Get broker URL.
		brokerUrl = getBrokerUrl();
		if (brokerUrl == null)
			return 1;
		
		// Attach port and protocol to broker URL.
		EditText portText = (EditText) findViewById(R.id.port);
		String portString = portText.getText().toString();
		if (portString.isEmpty())
			port = DEFAULT_PORT;
		else
			port = Integer.parseInt(portText.getText().toString());
		brokerUrl = "tcp://" + brokerUrl + ":" + Integer.toString(port);
		messenger.printDebugMessage("Broker URL: " + brokerUrl);
		
		return 0;
	}
	
	private String getBrokerUrl() {
		
		// Verify broker URL.
		try {
			EditText brokerUrlText = (EditText) findViewById(R.id.broker_url);
			String url = brokerUrlText.getText().toString();
			if (url.isEmpty()) throw new Exception("Field is empty.");
			return url;
		} catch (Exception e) {
			messenger.showAlert("Invalid broker ID: " + e.getMessage());
			e.printStackTrace();
			return null;
		}
		
	}
	
	public void addHost(View view) {
		
		if (prepareConnection() == 0) {
			
			if (mqtt.isConnected())
				mqtt.disconnect();

			int connectionResult = mqtt.connect(brokerUrl, deviceId);
			
			if (connectionResult == 0) {
				
				messenger.printDebugMessage("Determining IP and MAC addresses" +
						"...");
				wifiManager = (WifiManager) getSystemService(WIFI_SERVICE);
				wifiInfo = wifiManager.getConnectionInfo();
				int intIpAddress = wifiInfo.getIpAddress();
				ipAddress = Formatter.formatIpAddress(intIpAddress);
				macAddress = wifiInfo.getMacAddress();
				
				messenger.printDebugMessage("Getting current location...");
				Location location = locationClient.getLastLocation();
				latitude = location.getLatitude();
				longitude = location.getLongitude();
				
				messenger.printDebugMessage("Creating message...");
				JSONObject jsonMessage = new JSONObject();
				try {
					jsonMessage.put("from", deviceId);
					jsonMessage.put("command", "addRealHost");
					jsonMessage.put("name", deviceId);
					jsonMessage.put("ip", ipAddress);
					jsonMessage.put("mac", macAddress);
					jsonMessage.put("latitude", latitude);
					jsonMessage.put("longitude", longitude);
					jsonMessage.put("available", true);
				} catch (JSONException e) {
					messenger.showAlert("JSON problem: " + e.getMessage());
					e.printStackTrace();
				}
				String jsonMessageString = jsonMessage.toString();
				
				messenger.printDebugMessage("Message: " + jsonMessageString);

				mqtt.sendMessage(jsonMessageString);

				mqtt.disconnect();
			}
		}
	}
	
	public void getHosts(View view) {
		
		if (prepareConnection() == 0) {
			
			if (mqtt.isConnected())
				mqtt.disconnect();

			int result = mqtt.connect(brokerUrl, deviceId);
			
			if (result == 0) {
				
				mqtt.subscribe(deviceId);
				
				messenger.printDebugMessage("Creating message...");
				JSONObject jsonMessage = new JSONObject();
				try {
					jsonMessage.put("from", deviceId);
					jsonMessage.put("command", "getRealHosts");
				} catch (JSONException e) {
					messenger.showAlert("JSON problem: " + e.getMessage());
					e.printStackTrace();
				}
				String jsonMessageString = jsonMessage.toString();
				
				messenger.printDebugMessage("Message: " + jsonMessageString);

				mqtt.sendMessage(jsonMessageString);

				while (mqtt.isWaiting) {
					// Wait for response
				}
				
				hosts = mqtt.getHosts();

				mqtt.disconnect();
				
			}
			
		}
		
	}
	
	public void startWorker(View view) {

		// Write broadcast address to a file.
		String fileName;
		FileOutputStream stream;
		OutputStreamWriter writer;
		EditText broadcastAddressText;
		String broadcastAddress;
		try {
			broadcastAddress = getBrokerUrl();
			if (broadcastAddress == null)
				return;
			fileName = "broadcast_address.txt";
			stream = this.openFileOutput(fileName, Context.MODE_PRIVATE);
			writer = new OutputStreamWriter(stream);
			writer.write(broadcastAddress);
			writer.close();
			stream.close();
		} catch (Exception e) {
			messenger.showAlert("Error writing file: " + e.getMessage());
			e.printStackTrace();
			return;
		}
		
		// Start Parallel Python activity.
		Intent intent = new Intent(this, ScriptActivity.class);
		startActivity(intent);
		
	}
	
	public void openMap(View view) {
		if (hosts.length() == 0) {
			messenger.showAlert("There are no hosts to show. Try pressing " +
					"'Add Host' and 'Get Hosts' first.");
			return;
		}
		HostMarker[] markers = new HostMarker[hosts.length()];
		for (int i = 0; i < hosts.length(); i++) {
			JSONObject host;
			String name, ip, mac;
			boolean available;
			double latitude, longitude;
			try {
				host = hosts.getJSONObject(i);
				name = host.getString("name");
				ip = host.getString("ip");
				mac = host.getString("mac");
				latitude = host.getDouble("latitude");
				longitude = host.getDouble("longitude");
				available = host.getBoolean("available");
			} catch (Exception e) {
				messenger.showAlert("Invalid host data: " + e.getMessage());
				return;
			}
			HostMarker marker;
			marker = new HostMarker(name, ip, mac, latitude, longitude,
					available);
			markers[i] = marker;
		}
	    Intent intent = new Intent(this, MapActivity.class);
	    intent.putExtra(MARKERS, markers);
	    try {
	    	startActivity(intent);
	    } catch (Exception e) {
	    	Log.e(DEBUG_TAG, e.getMessage());
	    }
	}
	
	public void showAlert(String message) {
		AlertDialog alert = new AlertDialog.Builder(this).create();
		alert.setCancelable(false);
		alert.setMessage(message);
		alert.setButton("OK", new DialogInterface.OnClickListener() {
			@Override
			public void onClick(final DialogInterface dialog, final int which) {
				dialog.dismiss();
			}
		});
		alert.show();
	}
	
}
