package com.beckersweet.opmub;

import android.util.Log;
import android.view.View;
import android.widget.ScrollView;
import android.widget.TextView;

public class UserMessageHelper {
	
	private static boolean DEFAULT_DEBUG = true;
	private static String DEFAULT_DEBUG_TAG = "UserMessageHelper";
	
	boolean debug;
	String debugTag;
	
	MainActivity activity;
	TextView log;
	ScrollView logWindow;
	
	public UserMessageHelper(MainActivity newActivity, TextView newLog,
			ScrollView newLogWindow) {
		activity = newActivity;
		log = newLog;
		logWindow = newLogWindow;
		debug = DEFAULT_DEBUG;
		debugTag = DEFAULT_DEBUG_TAG;
	}
	
	public UserMessageHelper(MainActivity newActivity, TextView newLog,
			ScrollView newLogWindow, boolean newDebug) {
		this(newActivity, newLog, newLogWindow);
		debug = newDebug;
	}
	
	public UserMessageHelper(MainActivity newActivity, TextView newLog,
			ScrollView newLogWindow, boolean newDebug, String newDebugTag) {
		this(newActivity, newLog, newLogWindow, newDebug);
		debugTag = newDebugTag;
	}
	
	public void printDebugMessage(String message) {
		if (debug) {
			Log.i(debugTag, message);
			printToLog(message);
		}
	}
	
	public void showAlert(String message) {
		activity.showAlert(message);
		printDebugMessage(message);
	}
	
	private void printToLog(final String message) {
		activity.runOnUiThread(new Runnable() {
			@Override
			public void run() {
				log.append(message + "\n");
			}
		});
		scrollLogWindowToBottom();
	}
	
	private void scrollLogWindowToBottom() {
		logWindow.fullScroll(View.FOCUS_DOWN);
	}

}
