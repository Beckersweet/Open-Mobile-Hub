/*
 * HostDetailActivity.java
 * Open Mobile Hub
 *
 * Created by Gareth Johnson
 * Copyright (c) 2014 Beckersweet. All rights reserved.
 */

package com.beckersweet.opmub;

import android.app.Activity;
import android.content.Intent;
import android.os.Bundle;
import android.os.Parcelable;
import android.widget.TextView;

public class HostDetailActivity extends Activity {
	
	private static String MARKER = "com.beckersweet.mqttclient.MARKER";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_host_detail);
    	
        // Get host marker from previous activity.
        Intent intent = getIntent();
        Parcelable extra = intent.getParcelableExtra(MARKER);
    	HostMarker hostMarker = (HostMarker) extra;
    	
    	// Get data from host marker.
    	String nameString = hostMarker.name;
    	String ipString = hostMarker.ip;
    	String macString = hostMarker.mac;
    	String latitudeString = String.valueOf(hostMarker.latitude);
    	String longitudeString = String.valueOf(hostMarker.longitude);
    	String statusString;
    	if (hostMarker.available)
    		statusString = "Available";
    	else
    		statusString = "Not available";
    	
    	// Get text views from layout.
    	TextView nameView = (TextView) findViewById(R.id.host_detail_name);
    	TextView ipView = (TextView) findViewById(R.id.host_detail_ip);
    	TextView macView = (TextView) findViewById(R.id.host_detail_mac);
    	TextView latitudeView =
    			(TextView) findViewById(R.id.host_detail_latitude);
    	TextView longitudeView =
    			(TextView) findViewById(R.id.host_detail_longitude);
    	TextView statusView = (TextView) findViewById(R.id.host_detail_status);
    	
    	// Update text views with data;
    	nameView.setText(nameString);
    	ipView.setText(ipString);
    	macView.setText(macString);
    	latitudeView.setText(latitudeString);
    	longitudeView.setText(longitudeString);
    	statusView.setText(statusString);
    }

}
