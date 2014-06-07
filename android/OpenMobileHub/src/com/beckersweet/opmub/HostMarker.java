/*
 * HostMarker.java
 * Open Mobile Hub
 *
 * Created by Gareth Johnson
 * Copyright (c) 2014 Beckersweet. All rights reserved.
 */

package com.beckersweet.opmub;

import android.os.Parcel;
import android.os.Parcelable;

import com.google.android.gms.maps.model.LatLng;
import com.google.android.gms.maps.model.MarkerOptions;

public class HostMarker implements Parcelable {
	
	public String name;
	public String ip;
	public String mac;
	public double latitude;
	public double longitude;
	public boolean available;

	public HostMarker(String newName, String newIp, String newMac,
			double newLatitude, double newLongitude, boolean newAvailable) {
		name = newName;
		ip = newIp;
		mac = newMac;
		latitude = newLatitude;
		longitude = newLongitude;
		available = newAvailable;
	}
	
	public HostMarker(Parcel parcel) {
		String stringData[] = new String[3];
		double doubleData[] = new double[2];
		boolean booleanData[] = new boolean[1];
		
		parcel.readStringArray(stringData);
		name = stringData[0];
		ip = stringData[1];
		mac = stringData[2];
		
		parcel.readDoubleArray(doubleData);
		latitude = doubleData[0];
		longitude = doubleData[1];
		
		parcel.readBooleanArray(booleanData);
		available = booleanData[0];
	}
	
	public static final Parcelable.Creator<HostMarker> CREATOR
			= new Parcelable.Creator<HostMarker>() {
        public HostMarker createFromParcel(Parcel parcel) {
            return new HostMarker(parcel);
        }
        public HostMarker[] newArray(int size) {
            return new HostMarker[size];
        }
	};

	@Override
	public int describeContents() {
		return 0;
	}

	@Override
	public void writeToParcel(Parcel parcel, int flag) {
		String stringData[] = new String[3];
		double doubleData[] = new double[2];
		boolean booleanData[] = new boolean[1];
		
		stringData[0] = name;
		stringData[1] = ip;
		stringData[2] = mac;
		parcel.writeStringArray(stringData);

		doubleData[0] = latitude;
		doubleData[1] = longitude;
		parcel.writeDoubleArray(doubleData);

		booleanData[0] = available;
		parcel.writeBooleanArray(booleanData);
	}
	
	public MarkerOptions getOptions() {
		MarkerOptions options = new MarkerOptions();
		options.title(name);
		LatLng location = new LatLng(latitude, longitude);
		options.position(location);
		return options;
	}
}
