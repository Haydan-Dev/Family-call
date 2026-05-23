package com.haydan.familycall;

import android.app.Activity;
import android.app.KeyguardManager;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.SharedPreferences;
import android.os.Build;
import android.os.Bundle;
import android.util.Log;
import android.view.WindowManager;
import android.widget.ImageButton;
import android.widget.TextView;

import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;

public class IncomingCallActivity extends Activity {

    private static final String TAG = "IncomingCallActivity";
    private String callId;
    private String roomId;
    private String callerName;
    private String callType;

    private BroadcastReceiver cancelReceiver = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            if ("com.haydan.familycall.ACTION_CALL_CANCELLED".equals(intent.getAction())) {
                String cancelledRoomId = intent.getStringExtra("room_id");
                if (roomId != null && roomId.equals(cancelledRoomId)) {
                    Log.d(TAG, "Call cancelled by remote, finishing activity.");
                    clearRingingNotification();
                    finish();
                }
            }
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        // Turn on screen and show over lock screen
        getWindow().addFlags(
                WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED
                | WindowManager.LayoutParams.FLAG_DISMISS_KEYGUARD
                | WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON
                | WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON
        );
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1) {
            setShowWhenLocked(true);
            setTurnScreenOn(true);
            KeyguardManager keyguardManager = (KeyguardManager) getSystemService(KEYGUARD_SERVICE);
            if (keyguardManager != null) {
                keyguardManager.requestDismissKeyguard(this, null);
            }
        }

        setContentView(R.layout.activity_incoming_call);

        Intent intent = getIntent();
        callId = intent.getStringExtra("call_id");
        roomId = intent.getStringExtra("room_id");

        if ("DECLINE_FROM_NOTIF".equals(intent.getAction())) {
            declineCall();
            return;
        }

        callerName = intent.getStringExtra("caller_name");
        if (callerName == null || callerName.trim().isEmpty()) callerName = "Family Member";
        callType = intent.getStringExtra("call_type");
        if (callType == null) callType = "video";

        TextView nameText = findViewById(R.id.callerNameText);
        TextView typeText = findViewById(R.id.callTypeText);
        TextView avatarText = findViewById(R.id.callerAvatarInitial);
        
        nameText.setText(callerName);
        typeText.setText("Incoming " + callType.substring(0,1).toUpperCase() + callType.substring(1) + " Call");
        avatarText.setText(callerName.substring(0,1).toUpperCase());

        ImageButton btnAccept = findViewById(R.id.btnAccept);
        ImageButton btnDecline = findViewById(R.id.btnDecline);

        btnAccept.setOnClickListener(v -> acceptCall());
        btnDecline.setOnClickListener(v -> declineCall());

        // Register receiver for cancellation
        IntentFilter filter = new IntentFilter("com.haydan.familycall.ACTION_CALL_CANCELLED");
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            registerReceiver(cancelReceiver, filter, Context.RECEIVER_NOT_EXPORTED);
        } else {
            registerReceiver(cancelReceiver, filter);
        }
    }

    private void acceptCall() {
        Log.d(TAG, "Call accepted natively");
        clearRingingNotification();
        
        // Launch MainActivity and tell it to answer the call
        Intent answerIntent = new Intent(this, MainActivity.class);
        answerIntent.setAction("com.haydan.familycall.ACTION_ANSWER_CALL");
        answerIntent.putExtra("call_id", callId);
        answerIntent.putExtra("room_id", roomId);
        answerIntent.putExtra("call_type", callType);
        answerIntent.putExtra("caller_name", callerName);
        answerIntent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        startActivity(answerIntent);
        
        finish();
    }

    private void declineCall() {
        Log.d(TAG, "Call declined natively");
        clearRingingNotification();

        // Run HTTP request in background thread
        new Thread(() -> {
            try {
                SharedPreferences prefs = getSharedPreferences("FamilyCallPrefs", Context.MODE_PRIVATE);
                String token = prefs.getString("token", null);
                if (token != null && callId != null && !callId.isEmpty()) {
                    // Update this if BASE_URL changes!
                    String baseUrl = "https://returns-means-cocktail-meetup.trycloudflare.com"; 
                    URL url = new URL(baseUrl + "/calls/status_update/" + callId);
                    HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                    conn.setRequestMethod("PATCH");
                    conn.setRequestProperty("Content-Type", "application/json");
                    conn.setRequestProperty("Authorization", "Bearer " + token);
                    conn.setDoOutput(true);

                    String jsonInputString = "{\"call_status\": \"rejected\"}";
                    try(OutputStream os = conn.getOutputStream()) {
                        byte[] input = jsonInputString.getBytes("utf-8");
                        os.write(input, 0, input.length);
                    }
                    
                    int code = conn.getResponseCode();
                    Log.d(TAG, "Decline API Response Code: " + code);
                }
            } catch (Exception e) {
                Log.e(TAG, "Failed to decline call via API", e);
            }
        }).start();

        finish();
    }

    private void clearRingingNotification() {
        try {
            android.app.NotificationManager manager = (android.app.NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
            if (manager != null) {
                manager.cancel(1001);
            }
        } catch (Exception e) {
            Log.e(TAG, "Error clearing notification", e);
        }
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        try {
            unregisterReceiver(cancelReceiver);
        } catch (Exception e) {
            // Ignored
        }
    }
    
    // Prevent back button from destroying the ringing screen by doing nothing
    @Override
    public void onBackPressed() {
        // Do nothing to enforce explicit accept/decline
    }
}
