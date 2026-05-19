package com.haydan.familycall;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.os.Build;
import android.os.Bundle;
import com.getcapacitor.BridgeActivity;

public class MainActivity extends BridgeActivity {

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        createNotificationChannels();
    }

    /**
     * Create notification channels for Android 8.0+ (API 26+)
     * - incoming_calls: HIGH importance = heads-up notification + lock-screen + sound
     * - messages: DEFAULT importance = standard notification
     */
    private void createNotificationChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationManager manager = getSystemService(NotificationManager.class);

            // ── Channel 1: Incoming Calls (HIGH PRIORITY) ──
            NotificationChannel callChannel = new NotificationChannel(
                "incoming_calls",
                "Incoming Calls",
                NotificationManager.IMPORTANCE_HIGH
            );
            callChannel.setDescription("Notifications for incoming voice and video calls");
            callChannel.enableVibration(true);
            callChannel.setVibrationPattern(new long[]{0, 1000, 500, 1000, 500, 1000});
            callChannel.setLockscreenVisibility(android.app.Notification.VISIBILITY_PUBLIC);
            callChannel.setBypassDnd(true);
            manager.createNotificationChannel(callChannel);

            // ── Channel 2: Messages (DEFAULT) ──
            NotificationChannel msgChannel = new NotificationChannel(
                "messages",
                "Messages",
                NotificationManager.IMPORTANCE_HIGH
            );
            msgChannel.setDescription("Notifications for new chat messages");
            msgChannel.enableVibration(true);
            manager.createNotificationChannel(msgChannel);
        }
    }
}
