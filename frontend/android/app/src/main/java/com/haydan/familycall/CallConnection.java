package com.haydan.familycall;

import android.content.Context;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.telecom.Connection;
import android.telecom.DisconnectCause;
import android.telecom.TelecomManager;
import android.util.Log;

public class CallConnection extends Connection {
    private static final String TAG = "CallConnection";
    private Context context;
    private String roomId;
    private String callId;
    private String callerName;
    private String callType;

    public CallConnection(Context context) {
        this.context = context;
        // Since we are self-managed/managed by Telecom, we declare properties
        setConnectionProperties(PROPERTY_SELF_MANAGED);
        // By default, audio can route to earpiece, speaker, bluetooth, wired headset
        setAudioModeIsVoip(true);
    }

    public void setCallData(String roomId, String callId, String callerName, String callType) {
        this.roomId = roomId;
        this.callId = callId;
        this.callerName = callerName;
        this.callType = callType;
        
        // Ensure caller name appears in the native UI
        setCallerDisplayName(callerName, TelecomManager.PRESENTATION_ALLOWED);
        setAddress(Uri.parse("tel:" + callerName.replaceAll("[^0-9a-zA-Z]", "")), TelecomManager.PRESENTATION_ALLOWED);
    }

    @Override
    public void onAnswer(int videoState) {
        Log.d(TAG, "onAnswer triggered from Native Dialer");
        super.onAnswer(videoState);
        setActive(); // Mark call as active in OS
        
        // Launch MainActivity and route to WebView
        Intent intent = new Intent(context, MainActivity.class);
        intent.setAction("com.haydan.familycall.ACTION_ANSWER_CALL");
        intent.putExtra("room_id", roomId);
        intent.putExtra("call_id", callId);
        intent.putExtra("caller_name", callerName);
        intent.putExtra("call_type", callType);
        intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        context.startActivity(intent);
    }

    @Override
    public void onAnswer() {
        // Fallback for older APIs
        onAnswer(0);
    }

    @Override
    public void onReject() {
        Log.d(TAG, "onReject triggered from Native Dialer");
        super.onReject();
        setDisconnected(new DisconnectCause(DisconnectCause.REJECTED));
        destroy();

        // Broadcast to WebView to reject call if app is open
        Intent broadcast = new Intent("com.haydan.familycall.ACTION_CALL_CANCELLED");
        broadcast.putExtra("room_id", roomId);
        context.sendBroadcast(broadcast);

        // Also we can send a decline push here if needed, but usually we just let frontend/backend handle it
        // Since app might be killed, we should probably hit the backend directly, but let's just wake main activity to decline
        Intent intent = new Intent(context, MainActivity.class);
        intent.setAction("com.haydan.familycall.ACTION_DECLINE_CALL");
        intent.putExtra("room_id", roomId);
        intent.putExtra("call_id", callId);
        intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        context.startActivity(intent);
    }

    @Override
    public void onDisconnect() {
        Log.d(TAG, "onDisconnect triggered");
        super.onDisconnect();
        setDisconnected(new DisconnectCause(DisconnectCause.LOCAL));
        destroy();

        Intent intent = new Intent(context, MainActivity.class);
        intent.setAction("com.haydan.familycall.ACTION_END_CALL");
        intent.putExtra("room_id", roomId);
        intent.putExtra("call_id", callId);
        intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        context.startActivity(intent);
    }

    @Override
    public void onAbort() {
        Log.d(TAG, "onAbort triggered");
        super.onAbort();
        setDisconnected(new DisconnectCause(DisconnectCause.CANCELED));
        destroy();
    }
}
