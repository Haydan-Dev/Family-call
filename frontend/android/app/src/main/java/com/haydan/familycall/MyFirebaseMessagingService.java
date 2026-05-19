package com.haydan.familycall;

import android.app.Notification;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Intent;
import android.media.RingtoneManager;
import android.net.Uri;
import android.os.Build;
import android.os.PowerManager;
import android.util.Log;

import androidx.core.app.NotificationCompat;

import com.google.firebase.messaging.FirebaseMessagingService;
import com.google.firebase.messaging.RemoteMessage;

import java.util.Map;

/**
 * Native FCM Service — catches push notifications even when app is KILLED.
 * 
 * For incoming_call events: builds a HIGH PRIORITY + FULL SCREEN INTENT notification
 * that wakes the device and shows on lock screen (IMO/WhatsApp style).
 * 
 * For new_message events: builds a standard notification (WhatsApp style).
 */
public class MyFirebaseMessagingService extends FirebaseMessagingService {

    private static final String TAG = "FCM_Service";

    @Override
    public void onMessageReceived(RemoteMessage remoteMessage) {
        super.onMessageReceived(remoteMessage);

        Map<String, String> data = remoteMessage.getData();
        String event = data.get("event");

        Log.d(TAG, "FCM Received. Event: " + event);

        if ("incoming_call".equals(event)) {
            showIncomingCallNotification(data);
        } else if ("new_message".equals(event)) {
            showMessageNotification(data);
        } else {
            // Default: let Capacitor's plugin handle it (foreground)
            // For non-custom events, show the notification payload if present
            if (remoteMessage.getNotification() != null) {
                showGenericNotification(remoteMessage.getNotification());
            }
        }
    }

    /**
     * 🚨 INCOMING CALL — Full screen intent, wake device, lock-screen visible
     */
    private void showIncomingCallNotification(Map<String, String> data) {
        String callerName = data.getOrDefault("caller_name", "Family");
        String callType = data.getOrDefault("call_type", "video");
        String roomId = data.getOrDefault("room_id", "");
        String callId = data.getOrDefault("call_id", "");

        // Wake the screen
        wakeScreen();

        // Build the intent that opens the app to the incoming call page
        Intent intent = new Intent(this, MainActivity.class);
        intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        
        // Pass call data as URL fragment so Capacitor WebView can read it
        String targetPage;
        if ("audio".equals(callType)) {
            targetPage = "audio_incommingcall.html";
        } else {
            targetPage = "incoming_call.html";
        }
        
        // Store call data in intent extras — Capacitor will read via App plugin
        intent.putExtra("incoming_call", "true");
        intent.putExtra("call_type", callType);
        intent.putExtra("room_id", roomId);
        intent.putExtra("call_id", callId);
        intent.putExtra("caller_name", callerName);
        intent.putExtra("target_page", targetPage);

        int requestCode = (int) System.currentTimeMillis();

        PendingIntent pendingIntent = PendingIntent.getActivity(
            this, requestCode, intent,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );

        Uri ringtoneUri = RingtoneManager.getDefaultUri(RingtoneManager.TYPE_RINGTONE);

        String callTypeLabel = callType.substring(0, 1).toUpperCase() + callType.substring(1);

        NotificationCompat.Builder builder = new NotificationCompat.Builder(this, "incoming_calls")
            .setSmallIcon(android.R.drawable.ic_menu_call)
            .setContentTitle(callerName + " calling...")
            .setContentText("Incoming " + callTypeLabel + " call. Tap to answer.")
            .setPriority(NotificationCompat.PRIORITY_MAX)
            .setCategory(NotificationCompat.CATEGORY_CALL)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .setAutoCancel(true)
            .setOngoing(true)
            .setSound(ringtoneUri)
            .setVibrate(new long[]{0, 1000, 500, 1000, 500, 1000})
            .setContentIntent(pendingIntent)
            .setFullScreenIntent(pendingIntent, true);  // THIS IS THE KEY — full screen on lock screen

        NotificationManager manager = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
        // Use a fixed ID (1001) so we can cancel it later when call is answered/declined
        manager.notify(1001, builder.build());

        Log.d(TAG, "🚨 Full-screen call notification shown for: " + callerName);
    }

    /**
     * 📩 MESSAGE — WhatsApp-style notification
     */
    private void showMessageNotification(Map<String, String> data) {
        String senderName = data.getOrDefault("sender_name", "Someone");
        String roomId = data.getOrDefault("room_id", "");
        String conversationId = data.getOrDefault("conversation_id", "");

        // Read message preview from data payload (backend sends 'message_body')
        String body = data.getOrDefault("message_body", "You have a new message");

        Intent intent = new Intent(this, MainActivity.class);
        intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        intent.putExtra("new_message", "true");
        intent.putExtra("room_id", roomId);
        intent.putExtra("sender_name", senderName);
        intent.putExtra("target_page", "chat.html");

        int requestCode = (int) System.currentTimeMillis();

        PendingIntent pendingIntent = PendingIntent.getActivity(
            this, requestCode, intent,
            PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );

        NotificationCompat.Builder builder = new NotificationCompat.Builder(this, "messages")
            .setSmallIcon(android.R.drawable.ic_dialog_email)
            .setContentTitle(senderName)
            .setContentText(body)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_MESSAGE)
            .setAutoCancel(true)
            .setContentIntent(pendingIntent);

        NotificationManager manager = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
        // Use unique ID per conversation so multiple chats show separate notifications
        manager.notify(roomId.hashCode(), builder.build());

        Log.d(TAG, "📩 Message notification shown from: " + senderName);
    }

    /**
     * Generic notification fallback
     */
    private void showGenericNotification(RemoteMessage.Notification notification) {
        NotificationCompat.Builder builder = new NotificationCompat.Builder(this, "messages")
            .setSmallIcon(android.R.drawable.ic_dialog_info)
            .setContentTitle(notification.getTitle())
            .setContentText(notification.getBody())
            .setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .setAutoCancel(true);

        NotificationManager manager = (NotificationManager) getSystemService(NOTIFICATION_SERVICE);
        manager.notify((int) System.currentTimeMillis(), builder.build());
    }

    /**
     * Wake the screen using PowerManager WakeLock
     */
    private void wakeScreen() {
        try {
            PowerManager pm = (PowerManager) getSystemService(POWER_SERVICE);
            PowerManager.WakeLock wakeLock = pm.newWakeLock(
                PowerManager.FULL_WAKE_LOCK 
                | PowerManager.ACQUIRE_CAUSES_WAKEUP 
                | PowerManager.ON_AFTER_RELEASE,
                "familycall:incoming_call_wake"
            );
            wakeLock.acquire(30000); // Hold for 30 seconds max
        } catch (Exception e) {
            Log.e(TAG, "WakeLock error: " + e.getMessage());
        }
    }
}
