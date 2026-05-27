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
        root.setBackgroundColor(Color.parseColor("#111111"));
        root.setGravity(Gravity.CENTER);

        TextView nameText = new TextView(this);
        nameText.setText(callerName);
        nameText.setTextColor(Color.WHITE);
        nameText.setTextSize(36);
        nameText.setTypeface(null, Typeface.BOLD);
        nameText.setGravity(Gravity.CENTER);
        
        TextView statusText = new TextView(this);
        statusText.setText("Incoming " + (callType != null ? callType : "video") + " call...");
        statusText.setTextColor(Color.parseColor("#FFC700"));
        statusText.setTextSize(18);
        statusText.setGravity(Gravity.CENTER);
        statusText.setPadding(0, 20, 0, 150);

        LinearLayout buttonLayout = new LinearLayout(this);
        buttonLayout.setOrientation(LinearLayout.HORIZONTAL);
        buttonLayout.setGravity(Gravity.CENTER);

        Button declineButton = new Button(this);
        declineButton.setText("Decline");
        declineButton.setBackgroundColor(Color.parseColor("#F44336")); 
        declineButton.setTextColor(Color.WHITE);
        declineButton.setTextSize(16);
        declineButton.setPadding(60, 40, 60, 40);

        Button acceptButton = new Button(this);
        acceptButton.setText("Answer");
        acceptButton.setBackgroundColor(Color.parseColor("#4CAF50")); 
        acceptButton.setTextColor(Color.WHITE);
        acceptButton.setTextSize(16);
        acceptButton.setPadding(60, 40, 60, 40);

        LinearLayout.LayoutParams btnParams = new LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.WRAP_CONTENT,
            LinearLayout.LayoutParams.WRAP_CONTENT
        );
        btnParams.setMargins(40, 0, 40, 0);
        
        buttonLayout.addView(declineButton, btnParams);
        buttonLayout.addView(acceptButton, btnParams);

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
        
        Intent broadcast = new Intent("com.haydan.familycall.ACTION_CALL_CANCELLED");
        broadcast.putExtra("room_id", roomId);
        sendBroadcast(broadcast);
        
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
