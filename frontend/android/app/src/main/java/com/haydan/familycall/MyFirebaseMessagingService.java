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
     * 🚨 CALL CANCELLED / TERMINATED — stop ringing service and dismiss everything
     */
    private void cancelIncomingCallNotification(Map<String, String> data) {
        Log.d(TAG, "🚨 cancelIncomingCallNotification: Stopping ringing service");
        
        if (CallConnectionService.currentConnection != null) {
            CallConnectionService.currentConnection.onDisconnect();
            CallConnectionService.currentConnection = null;
        }

        // Broadcast to close UI if open
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

    private void showIncomingCallNotification(Map<String, String> data) {
        String callerName = data.getOrDefault("caller_name", "Family Member");
        if (callerName.trim().isEmpty()) callerName = "Family Member";
        String callType = data.getOrDefault("call_type", "video");
        String roomId = data.getOrDefault("room_id", "");
        String callId = data.getOrDefault("call_id", "");

        wakeScreen();

        try {
            android.telecom.TelecomManager telecomManager = (android.telecom.TelecomManager) getSystemService(Context.TELECOM_SERVICE);
            android.content.ComponentName componentName = new android.content.ComponentName(this, CallConnectionService.class);
            android.telecom.PhoneAccountHandle phoneAccountHandle = new android.telecom.PhoneAccountHandle(componentName, "FamilyCallAccount");
            
            // Register PhoneAccount
            android.telecom.PhoneAccount phoneAccount = android.telecom.PhoneAccount.builder(phoneAccountHandle, "Family Call")
                .setCapabilities(android.telecom.PhoneAccount.CAPABILITY_SELF_MANAGED)
                .setShortDescription("Family Call")
                .build();
            telecomManager.registerPhoneAccount(phoneAccount);

            android.os.Bundle extras = new android.os.Bundle();
            android.os.Bundle callExtras = new android.os.Bundle();
            callExtras.putString("room_id", roomId);
            callExtras.putString("call_id", callId);
            callExtras.putString("caller_name", callerName);
            callExtras.putString("call_type", callType);
            
            extras.putBundle(android.telecom.TelecomManager.EXTRA_INCOMING_CALL_EXTRAS, callExtras);
            
            telecomManager.addNewIncomingCall(phoneAccountHandle, extras);
            Log.d(TAG, "📞 TelecomManager.addNewIncomingCall invoked successfully!");

            // FORTIFICATION: Chinese OEMs (Xiaomi, Realme, Vivo) often block TelecomManager from waking the screen
            // when the app is in the killed state. We ALWAYS post the FullScreenIntent notification to force the screen ON.
            showFallbackNotification(callId, roomId, callerName, callType);

        } catch (SecurityException se) {
            Log.e(TAG, "🚨 SecurityException: Missing MANAGE_OWN_CALLS permission or account not enabled: " + se.getMessage());
            showFallbackNotification(callId, roomId, callerName, callType);
        } catch (Exception e) {
            Log.e(TAG, "🚨 Failed to use TelecomManager: " + e.getMessage());
            showFallbackNotification(callId, roomId, callerName, callType);
        }
    }

    /**
     * 🚨 FALLBACK NOTIFICATION — for when Foreground Service can't start (Realme/ColorOS)
     * This creates its OWN notification channel with sound+vibration so ringtone always plays.
     */
    private void showFallbackNotification(String callId, String roomId, String callerName, String callType) {
        Log.d(TAG, "🚨 Posting FALLBACK notification directly!");

        // Create fallback channel WITH sound (the main channel has no sound since service uses MediaPlayer)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            Uri ringtoneUri = Uri.parse("android.resource://" + getPackageName() + "/" + R.raw.ringtone);
            android.media.AudioAttributes audioAttributes = new android.media.AudioAttributes.Builder()
                    .setContentType(android.media.AudioAttributes.CONTENT_TYPE_SONIFICATION)
                    .setUsage(android.media.AudioAttributes.USAGE_NOTIFICATION_RINGTONE)
                    .build();

            android.app.NotificationChannel fallbackChannel = new android.app.NotificationChannel(
                    "incoming_calls_fallback_v1",
                    "Incoming Calls (Fallback)",
                    NotificationManager.IMPORTANCE_HIGH
            );
            fallbackChannel.setDescription("Fallback call notifications with sound");
            fallbackChannel.enableVibration(true);
            fallbackChannel.setVibrationPattern(new long[]{0, 1000, 500, 1000, 500, 1000});
            fallbackChannel.setLockscreenVisibility(android.app.Notification.VISIBILITY_PUBLIC);
            fallbackChannel.setBypassDnd(true);
            fallbackChannel.setSound(ringtoneUri, audioAttributes);

            NotificationManager mgr = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
            if (mgr != null) mgr.createNotificationChannel(fallbackChannel);
        }

        // Build intents — all go DIRECTLY to MainActivity
        Intent mainIntent = new Intent(this, MainActivity.class);
        mainIntent.putExtra("incoming_call", "true");
        mainIntent.putExtra("call_id", callId);
        mainIntent.putExtra("room_id", roomId);
        mainIntent.putExtra("caller_name", callerName);
        mainIntent.putExtra("call_type", callType);
        mainIntent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);

        int requestCode = (int) System.currentTimeMillis();
        PendingIntent fullScreenPendingIntent = PendingIntent.getActivity(
                this, requestCode, mainIntent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );

        // Accept
        Intent acceptIntent = new Intent(this, MainActivity.class);
        acceptIntent.setAction("com.haydan.familycall.ACTION_ANSWER_CALL");
        acceptIntent.putExtra("call_id", callId);
        acceptIntent.putExtra("room_id", roomId);
        acceptIntent.putExtra("caller_name", callerName);
        acceptIntent.putExtra("call_type", callType);
        acceptIntent.setFlags(Intent.FLAG_ACTIVITY_NEW_TASK | Intent.FLAG_ACTIVITY_CLEAR_TOP | Intent.FLAG_ACTIVITY_SINGLE_TOP);
        PendingIntent acceptPendingIntent = PendingIntent.getActivity(
                this, requestCode + 1, acceptIntent,
                PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE
        );

        // Decline
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

        // Fallback channel HAS sound, so notification will ring even without service
        NotificationCompat.Builder builder = new NotificationCompat.Builder(this, "incoming_calls_fallback_v1")
                .setSmallIcon(android.R.drawable.ic_menu_call)
                .setContentTitle(callerName)
                .setContentText("Incoming " + callTypeLabel + " Call")
                .setPriority(NotificationCompat.PRIORITY_MAX)
                .setCategory(NotificationCompat.CATEGORY_CALL)
                .setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
                .setOngoing(true)
                .setAutoCancel(true)
                .setSound(ringtoneUri)
                .setVibrate(new long[]{0, 1000, 500, 1000, 500, 1000})
                .setFullScreenIntent(fullScreenPendingIntent, true)
                .setContentIntent(fullScreenPendingIntent)
                .addAction(android.R.drawable.ic_menu_close_clear_cancel, "Decline", declinePendingIntent)
                .addAction(android.R.drawable.ic_menu_call, "Accept", acceptPendingIntent);

        Notification notification = builder.build();
        notification.flags |= Notification.FLAG_INSISTENT;

        NotificationManager manager = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        if (manager != null) {
            manager.notify(1001, notification);
        }

        Log.d(TAG, "🚨 Fallback notification posted with sound!");
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

        NotificationCompat.Builder builder = new NotificationCompat.Builder(this, "messages_channel_v4")
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
