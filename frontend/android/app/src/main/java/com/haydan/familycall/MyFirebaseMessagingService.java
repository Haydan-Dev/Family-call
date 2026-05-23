package com.haydan.familycall;

import android.app.Notification;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.Context;
import android.content.Intent;
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
        } else if ("call_cancelled".equals(event) || "call_ended".equals(event) || "call_declined".equals(event) || "call_rejected".equals(event)) {
            cancelIncomingCallNotification(data);
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
     * 🚨 CALL CANCELLED / TERMINATED — dismiss ringing notification immediately
     */
    private void cancelIncomingCallNotification(Map<String, String> data) {
        Log.d(TAG, "🚨 cancelIncomingCallNotification: Cancelling ringing notification 1001");
        try {
            android.app.NotificationManager manager = (android.app.NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
            if (manager != null) {
                manager.cancel(1001);
            }
        } catch (Exception e) {
            Log.e(TAG, "Error cancelling notification 1001: " + e.getMessage());
        }

        // Broadcast to close IncomingCallActivity if open
        Intent broadcast = new Intent("com.haydan.familycall.ACTION_CALL_CANCELLED");
        broadcast.putExtra("room_id", data.getOrDefault("room_id", ""));
        sendBroadcast(broadcast);

        // Also tell Capacitor to finish if active_call is open
        Intent intent = new Intent(this, MainActivity.class);
        intent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        intent.putExtra("finish_call", "true");
        intent.putExtra("room_id", data.getOrDefault("room_id", ""));
        try {
            startActivity(intent);
        } catch (Exception e) {
            Log.e(TAG, "Failed to start MainActivity for finish_call: " + e.getMessage());
        }
    }

    /**
     * 🚨 INCOMING CALL — Start Native Lock Screen UI and Ringtone
     */
    private void showIncomingCallNotification(Map<String, String> data) {
        String callerName = data.getOrDefault("caller_name", "Family Member");
        if (callerName.trim().isEmpty()) callerName = "Family Member";
        String callType = data.getOrDefault("call_type", "video");
        String roomId = data.getOrDefault("room_id", "");
        String callId = data.getOrDefault("call_id", "");

        wakeScreen();

        // 1. Intent for Full Screen UI (When screen is locked) - Now routing directly to MainActivity
        Intent fullScreenIntent = new Intent(this, MainActivity.class);
        fullScreenIntent.putExtra("incoming_call", "true");
        fullScreenIntent.putExtra("call_id", callId);
        fullScreenIntent.putExtra("room_id", roomId);
        fullScreenIntent.putExtra("caller_name", callerName);
        fullScreenIntent.putExtra("call_type", callType);
        fullScreenIntent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);

        int requestCode = (int) System.currentTimeMillis();
        PendingIntent fullScreenPendingIntent = PendingIntent.getActivity(
                this, requestCode, fullScreenIntent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );

        // 2. Intent for Answer Button (Heads-up notification)
        Intent answerIntent = new Intent(this, MainActivity.class);
        answerIntent.setAction("com.haydan.familycall.ACTION_ANSWER_CALL");
        answerIntent.putExtra("call_id", callId);
        answerIntent.putExtra("room_id", roomId);
        answerIntent.putExtra("call_type", callType);
        answerIntent.putExtra("caller_name", callerName);
        answerIntent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        PendingIntent answerPendingIntent = PendingIntent.getActivity(
                this, requestCode + 1, answerIntent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );

        // 3. Intent for Decline Button (Heads-up notification) - Now routing directly to MainActivity
        Intent declineIntent = new Intent(this, MainActivity.class);
        declineIntent.setAction("com.haydan.familycall.ACTION_DECLINE_CALL");
        declineIntent.putExtra("call_id", callId);
        declineIntent.putExtra("room_id", roomId);
        declineIntent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        PendingIntent declinePendingIntent = PendingIntent.getActivity(
                this, requestCode + 2, declineIntent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );

        Uri ringtoneUri = Uri.parse("android.resource://" + getPackageName() + "/" + R.raw.ringtone);
        String callTypeLabel = callType.substring(0, 1).toUpperCase() + callType.substring(1);

        NotificationCompat.Builder builder = new NotificationCompat.Builder(this, "incoming_calls_channel_v4")
                .setSmallIcon(android.R.drawable.ic_menu_call)
                .setContentTitle(callerName + " is calling...")
                .setContentText("Incoming " + callTypeLabel + " Call")
                .setPriority(NotificationCompat.PRIORITY_MAX)
                .setCategory(NotificationCompat.CATEGORY_CALL)
                .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
                .setOngoing(true)
                .setAutoCancel(true)
                .setSound(ringtoneUri)
                .setVibrate(new long[]{0, 1000, 500, 1000, 500, 1000})
                .setFullScreenIntent(fullScreenPendingIntent, true)
                .addAction(android.R.drawable.ic_menu_close_clear_cancel, "Decline", declinePendingIntent)
                .addAction(android.R.drawable.ic_menu_call, "Answer", answerPendingIntent);

        Notification notification = builder.build();
        notification.flags |= Notification.FLAG_INSISTENT; // Loops the native ringtone!

        NotificationManager manager = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        if (manager != null) {
            manager.notify(1001, notification);
        }

        Log.d(TAG, "🚨 Native Notification with Full Screen Intent Triggered!");
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

        Uri msgSoundUri = Uri.parse("android.resource://" + getPackageName() + "/" + R.raw.notification);

        NotificationCompat.Builder builder = new NotificationCompat.Builder(this, "messages_channel_v3")
            .setSmallIcon(android.R.drawable.ic_dialog_email)
            .setContentTitle(senderName)
            .setContentText(body)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_MESSAGE)
            .setAutoCancel(true)
            .setSound(msgSoundUri)
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
