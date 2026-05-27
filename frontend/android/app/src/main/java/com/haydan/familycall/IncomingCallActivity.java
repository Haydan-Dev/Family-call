package com.haydan.familycall;

import android.app.Activity;
import android.app.KeyguardManager;
import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.Typeface;
import android.media.AudioAttributes;
import android.media.MediaPlayer;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.util.Log;
import android.view.Gravity;
import android.view.WindowManager;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.graphics.drawable.GradientDrawable;

import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;

public class IncomingCallActivity extends Activity {

    private static final String TAG = "IncomingCallActivity";
    private MediaPlayer mediaPlayer;
    private String roomId;
    private String callId;
    private String callerName;
    private String callType;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        
        getWindow().addFlags(
            WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED |
            WindowManager.LayoutParams.FLAG_DISMISS_KEYGUARD |
            WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON |
            WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON |
            WindowManager.LayoutParams.FLAG_ALLOW_LOCK_WHILE_SCREEN_ON
        );

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1) {
            setShowWhenLocked(true);
            setTurnScreenOn(true);
        }

        roomId = getIntent().getStringExtra("room_id");
        callId = getIntent().getStringExtra("call_id");
        callerName = getIntent().getStringExtra("caller_name");
        if (callerName == null) callerName = "Family Member";
        callType = getIntent().getStringExtra("call_type");
        
        setupUI();
        playRingtone();
    }

    private void setupUI() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(Color.parseColor("#1a1a1a"));
        root.setGravity(Gravity.CENTER);

        // Circular avatar placeholder
        TextView avatarText = new TextView(this);
        avatarText.setText(callerName.substring(0, 1).toUpperCase());
        avatarText.setTextColor(Color.WHITE);
        avatarText.setTextSize(48);
        avatarText.setGravity(Gravity.CENTER);
        avatarText.setTypeface(null, Typeface.BOLD);
        
        GradientDrawable avatarBg = new GradientDrawable();
        avatarBg.setShape(GradientDrawable.OVAL);
        avatarBg.setColor(Color.parseColor("#2196F3"));
        avatarText.setBackground(avatarBg);
        
        LinearLayout.LayoutParams avatarParams = new LinearLayout.LayoutParams(250, 250);
        avatarParams.setMargins(0, 0, 0, 60);

        TextView nameText = new TextView(this);
        nameText.setText(callerName);
        nameText.setTextColor(Color.WHITE);
        nameText.setTextSize(32);
        nameText.setTypeface(null, Typeface.BOLD);
        nameText.setGravity(Gravity.CENTER);
        
        TextView statusText = new TextView(this);
        statusText.setText("Family Call • " + (callType != null ? callType.substring(0,1).toUpperCase() + callType.substring(1) : "Video"));
        statusText.setTextColor(Color.parseColor("#AAAAAA"));
        statusText.setTextSize(18);
        statusText.setGravity(Gravity.CENTER);
        statusText.setPadding(0, 20, 0, 180);

        LinearLayout buttonLayout = new LinearLayout(this);
        buttonLayout.setOrientation(LinearLayout.HORIZONTAL);
        buttonLayout.setGravity(Gravity.CENTER);

        // Decline Button
        Button declineButton = new Button(this);
        declineButton.setText("DECLINE");
        declineButton.setTextColor(Color.WHITE);
        declineButton.setTextSize(16);
        declineButton.setTypeface(null, Typeface.BOLD);
        GradientDrawable declineBg = new GradientDrawable();
        declineBg.setCornerRadius(60);
        declineBg.setColor(Color.parseColor("#FF3B30"));
        declineButton.setBackground(declineBg);
        declineButton.setElevation(8);

        // Accept Button
        Button acceptButton = new Button(this);
        acceptButton.setText("ANSWER");
        acceptButton.setTextColor(Color.WHITE);
        acceptButton.setTextSize(16);
        acceptButton.setTypeface(null, Typeface.BOLD);
        GradientDrawable acceptBg = new GradientDrawable();
        acceptBg.setCornerRadius(60);
        acceptBg.setColor(Color.parseColor("#34C759"));
        acceptButton.setBackground(acceptBg);
        acceptButton.setElevation(8);

        LinearLayout.LayoutParams btnParams = new LinearLayout.LayoutParams(320, 140);
        btnParams.setMargins(40, 0, 40, 0);
        
        buttonLayout.addView(declineButton, btnParams);
        buttonLayout.addView(acceptButton, btnParams);

        root.addView(avatarText, avatarParams);
        root.addView(nameText);
        root.addView(statusText);
        root.addView(buttonLayout);

        setContentView(root);

        acceptButton.setOnClickListener(v -> onAcceptCall());
        declineButton.setOnClickListener(v -> onDeclineCall());
    }

    private void playRingtone() {
        try {
            Uri ringtoneUri = Uri.parse("android.resource://" + getPackageName() + "/" + R.raw.ringtone);
            mediaPlayer = new MediaPlayer();
            mediaPlayer.setDataSource(getApplicationContext(), ringtoneUri);
            mediaPlayer.setAudioAttributes(new AudioAttributes.Builder()
                .setUsage(AudioAttributes.USAGE_NOTIFICATION_RINGTONE)
                .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                .build());
            mediaPlayer.setLooping(true);
            mediaPlayer.prepare();
            mediaPlayer.start();
        } catch (Exception e) {
            Log.e(TAG, "Failed to play ringtone: " + e.getMessage());
        }
    }

    private void stopRingtone() {
        if (mediaPlayer != null) {
            try {
                mediaPlayer.stop();
                mediaPlayer.release();
            } catch (Exception e) {}
            mediaPlayer = null;
        }
    }

    private void onAcceptCall() {
        stopRingtone();
        Log.d(TAG, "Call accepted. Requesting keyguard dismiss...");
        
        if (CallConnectionService.currentConnection != null) {
            CallConnectionService.currentConnection.setActive();
        }

        KeyguardManager keyguardManager = (KeyguardManager) getSystemService(Context.KEYGUARD_SERVICE);
        if (keyguardManager != null && keyguardManager.isKeyguardLocked()) {
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                keyguardManager.requestDismissKeyguard(this, new KeyguardManager.KeyguardDismissCallback() {
                    @Override
                    public void onDismissSucceeded() {
                        super.onDismissSucceeded();
                        launchMainActivity();
                    }
                    @Override
                    public void onDismissCancelled() {
                        super.onDismissCancelled();
                        launchMainActivity();
                    }
                });
            } else {
                launchMainActivity();
            }
        } else {
            launchMainActivity();
        }
    }

    private void launchMainActivity() {
        Intent intent = new Intent(this, MainActivity.class);
        intent.setAction("com.haydan.familycall.ACTION_ANSWER_CALL");
        intent.putExtra("room_id", roomId);
        intent.putExtra("call_id", callId);
        intent.putExtra("caller_name", callerName);
        intent.putExtra("call_type", callType);
        intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        startActivity(intent);
        finish();
    }

    private void onDeclineCall() {
        stopRingtone();
        
        if (CallConnectionService.currentConnection != null) {
            CallConnectionService.currentConnection.onDisconnect();
            CallConnectionService.currentConnection = null;
        }
        
        // 1. Send Native Intent (if app is warm)
        Intent broadcast = new Intent("com.haydan.familycall.ACTION_CALL_CANCELLED");
        broadcast.putExtra("room_id", roomId);
        sendBroadcast(broadcast);
        
        // 2. Fire direct HTTP sync to backend so caller drops instantly
        new Thread(() -> {
            try {
                // IMPORTANT: Update this if your tunnel domain changes, or keep it synced!
                URL url = new URL("https://lowest-antiques-ceremony-formerly.trycloudflare.com/ws/decline");
                HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                conn.setRequestMethod("POST");
                conn.setRequestProperty("Content-Type", "application/json");
                conn.setDoOutput(true);
                
                String jsonInputString = "{\"room_id\": \"" + roomId + "\", \"call_id\": \"" + callId + "\"}";
                
                try (OutputStream os = conn.getOutputStream()) {
                    byte[] input = jsonInputString.getBytes("utf-8");
                    os.write(input, 0, input.length);
                }
                
                int code = conn.getResponseCode();
                Log.d(TAG, "Native HTTP decline fired! Response code: " + code);
            } catch (Exception e) {
                Log.e(TAG, "Native HTTP decline failed: " + e.getMessage());
            }
        }).start();

        // 3. Fallback Intent for cold boot intercept via auth_guard.js
        Intent intent = new Intent(this, MainActivity.class);
        intent.setAction("com.haydan.familycall.ACTION_DECLINE_CALL");
        intent.putExtra("room_id", roomId);
        intent.putExtra("call_id", callId);
        intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        startActivity(intent);
        finish();
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        stopRingtone();
    }
}
