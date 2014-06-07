/*
 * HostDetailActivity.java
 * Open Mobile Hub
 *
 * Created by Gareth Johnson
 * Copyright (c) 2014 Beckersweet. All rights reserved.
 */

package com.beckersweet.opmub;

import android.content.Intent;
import android.os.Bundle;
import android.os.Parcelable;
import android.support.v4.app.Fragment;
import android.support.v4.app.FragmentActivity;
import android.support.v4.app.FragmentManager;
import android.view.Display;
import android.view.WindowManager;
import android.widget.Toast;

import com.google.android.gms.maps.CameraUpdate;
import com.google.android.gms.maps.CameraUpdateFactory;
import com.google.android.gms.maps.GoogleMap;
import com.google.android.gms.maps.GoogleMap.OnMarkerClickListener;
import com.google.android.gms.maps.SupportMapFragment;
import com.google.android.gms.maps.model.LatLng;
import com.google.android.gms.maps.model.LatLngBounds;
import com.google.android.gms.maps.model.Marker;
import com.google.android.gms.maps.model.MarkerOptions;

@SuppressWarnings("deprecation")
public class MapActivity extends FragmentActivity
		implements OnMarkerClickListener{

	private static String MARKER = "com.beckersweet.mqttclient.MARKER";
	private static String MARKERS = "com.beckersweet.mqttclient.MARKERS";
	
	HostMarker[] hostMarkers;
	MarkerOptions[] markerOptions;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_map);
        
        // Get host markers from previous activity.
        Intent intent = getIntent();
        Parcelable[] extra = intent.getParcelableArrayExtra(MARKERS);
    	markerOptions = new MarkerOptions[extra.length];
    	hostMarkers = new HostMarker[extra.length];
        for (int i = 0; i < extra.length; i++) {
        	hostMarkers[i] = (HostMarker) extra[i];
        	markerOptions[i] = hostMarkers[i].getOptions();
        }

        // Get map.
    	FragmentManager fragmentManager = getSupportFragmentManager();
    	Fragment fragment = fragmentManager.findFragmentById(R.id.map);
    	SupportMapFragment mapFragment = (SupportMapFragment) fragment;
    	GoogleMap map = mapFragment.getMap();
    	
    	// Set map's initial bounds.
    	CameraUpdate cameraUpdate = null;
    	if (markerOptions.length == 1) {
    		MarkerOptions marker = markerOptions[0];
    		LatLng markerPosition = marker.getPosition();
    		float zoom = 14;
    		cameraUpdate = CameraUpdateFactory.newLatLngZoom(markerPosition,
    				zoom);
    	} else if (markerOptions.length > 1) {
	    	LatLngBounds.Builder boundBuilder = new LatLngBounds.Builder();
	    	for (int i = 0; i < markerOptions.length; i++) {
	    		MarkerOptions marker = markerOptions[i];
	    		LatLng markerPosition = marker.getPosition();
	    		boundBuilder.include(markerPosition);
	    	}
	    	LatLngBounds bounds = boundBuilder.build();
	    	WindowManager windowManager = getWindowManager();
	    	Display screen = windowManager.getDefaultDisplay();
	    	int boundWidth = screen.getWidth(); // pixels
	    	int boundHeight = screen.getHeight(); // pixels
	    	int boundPadding = 200; // pixels
	    	cameraUpdate = CameraUpdateFactory.newLatLngBounds(bounds,
	    			boundWidth, boundHeight, boundPadding);
    	}
    	if (cameraUpdate != null) {
    		try {
    			map.moveCamera(cameraUpdate);
    		} catch (Exception e) {
    			e.printStackTrace();
    		}
    	}
    	
    	// Add markers an marker click listener.
    	if (map != null) {
    		for (int i = 0; i < markerOptions.length; i++) {
    			MarkerOptions marker = markerOptions[i];
	    		map.addMarker(marker);
    		}
    		map.setOnMarkerClickListener(this);
    	}
    }

	@Override
	public boolean onMarkerClick(Marker clickedMarker) {
		HostMarker hostMarker = null;
		for (int i = 0; i < hostMarkers.length; i++) {
			if (clickedMarker.getTitle().equals(hostMarkers[i].name)) {
				hostMarker = hostMarkers[i];
			}
		}
		
		if (hostMarker == null)
			return false;
		
		Intent intent = new Intent(this, HostDetailActivity.class);
		intent.putExtra(MARKER, hostMarker);
		startActivity(intent);
		return true;
	}
}
