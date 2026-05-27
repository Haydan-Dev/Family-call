package com.haydan.familycall;

import android.content.Intent;
import android.os.Bundle;
import android.telecom.Connection;
import android.telecom.ConnectionRequest;
import android.telecom.ConnectionService;
import android.telecom.PhoneAccountHandle;
import android.telecom.TelecomManager;
import android.util.Log;

public class CallConnectionService extends ConnectionService {
    private static final String TAG = "CallConnectionService";
    
    // Store active connection to allow cancellation later
    public static CallConnection currentConnection;

    @Override
    public Connection onCreateIncomingConnection(PhoneAccountHandle connectionManagerPhoneAccount, ConnectionRequest request) {
        Log.d(TAG, "onCreateIncomingConnection triggered");
        
        Bundle extras = request.getExtras();
        String roomId = "";
        String callId = "";
        String callerName = "Family Member";
        String callType = "video";
        
        if (extras != null) {
            roomId = extras.getString("room_id", "");
            callId = extras.getString("call_id", "");
            callerName = extras.getString("caller_name", "Family Member");
            callType = extras.getString("call_type", "video");
            
            // Sometimes TelecomManager wraps our extras in another bundle under EXTRA_INCOMING_CALL_EXTRAS
            if (extras.containsKey(TelecomManager.EXTRA_INCOMING_CALL_EXTRAS)) {
                Bundle incomingExtras = extras.getBundle(TelecomManager.EXTRA_INCOMING_CALL_EXTRAS);
                if (incomingExtras != null) {
                    roomId = incomingExtras.getString("room_id", roomId);
                    callId = incomingExtras.getString("call_id", callId);
                    callerName = incomingExtras.getString("caller_name", callerName);
                    callType = incomingExtras.getString("call_type", callType);
                }
            }
        }

        CallConnection connection = new CallConnection(getApplicationContext());
        connection.setCallData(roomId, callId, callerName, callType);
        connection.setInitializing();
        
        // Ringing signals telecom to show UI
        connection.setRinging();

        currentConnection = connection;

        // 🚨 CRITICAL: Launch our custom UI natively.
        // Because we are a bound ConnectionService, OS grants us a VIP exemption
        // to bypass the Android 10+ background activity start restrictions!
        Intent intent = new Intent(this, IncomingCallActivity.class);
        intent.putExtra("room_id", roomId);
        intent.putExtra("call_id", callId);
        intent.putExtra("caller_name", callerName);
        intent.putExtra("call_type", callType);
        intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        try {
            startActivity(intent);
        } catch (Exception e) {
            Log.e(TAG, "Failed to start IncomingCallActivity: " + e.getMessage());
        }

        return connection;
    }

    @Override
    public void onCreateIncomingConnectionFailed(PhoneAccountHandle connectionManagerPhoneAccount, ConnectionRequest request) {
        super.onCreateIncomingConnectionFailed(connectionManagerPhoneAccount, request);
        Log.e(TAG, "onCreateIncomingConnectionFailed");
    }

    @Override
    public Connection onCreateOutgoingConnection(PhoneAccountHandle connectionManagerPhoneAccount, ConnectionRequest request) {
        // Not used right now, but required by ConnectionService
        return super.onCreateOutgoingConnection(connectionManagerPhoneAccount, request);
    }
}
