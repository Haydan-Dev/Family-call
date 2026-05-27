package com.haydan.familycall;

import android.app.KeyguardManager;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Build;
import android.os.Bundle;
import android.util.Log;
import android.view.WindowManager;
import android.net.Uri;

import com.getcapacitor.BridgeActivity;
import com.getcapacitor.JSObject;
import com.getcapacitor.Plugin;
import com.getcapacitor.PluginCall;
import com.getcapacitor.PluginMethod;
import com.getcapacitor.annotation.CapacitorPlugin;

public class MainActivity extends BridgeActivity {

    private static final String TAG = "MainActivity";
    private static JSObject pendingIntentExtras = null;
    public static boolean isAppRunning = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        // 🚨 CRITICAL: Extract intent data BEFORE super.onCreate()!
        // super.onCreate() starts loading the WebView immediately.
        // If we set pendingIntentExtras AFTER that, auth_guard.js may
        // run getIntentExtras() and find null — causing redirect to home.html
        // instead of active_call.html. This was the KILLED STATE bug.
        preExtractIntentData(getIntent());
        
        // Register custom native plugins BEFORE super.onCreate()
        registerPlugin(IntentReceiverPlugin.class);
        registerPlugin(NativeStoragePlugin.class);
        registerPlugin(AppPermissionsPlugin.class);
        registerPlugin(TelecomManagerPlugin.class);
        
        super.onCreate(savedInstanceState);
        isAppRunning = true;
        
        createNotificationChannels();
        
        // Apply UI flags (window flags, clear notifications) — data already extracted above
        applyIntentUiEffects(getIntent());
    }

    @Override
    public void onDestroy() {
        super.onDestroy();
        isAppRunning = false;
    }

    @Override
    public void onStart() {
        super.onStart();
        // Unblock audio autoplay without user interaction (Fixes silent ringtone on incoming call cold boot)
        if (getBridge() != null && getBridge().getWebView() != null) {
            getBridge().getWebView().getSettings().setMediaPlaybackRequiresUserGesture(false);
        }
    }

    public void requestOverlayPermissionNative() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            if (!android.provider.Settings.canDrawOverlays(this)) {
                // If it is a Xiaomi/MIUI device, try opening their custom App Permission Editor directly
                if ("xiaomi".equalsIgnoreCase(Build.MANUFACTURER)) {
                    try {
                        Intent intent = new Intent("miui.intent.action.APP_PERM_EDITOR");
                        intent.setClassName("com.miui.securitycenter", "com.miui.permalink.action.APP_PERM_EDITOR");
                        intent.putExtra("extra_pkgname", getPackageName());
                        startActivity(intent);
                        return;
                    } catch (Exception e) {
                        try {
                            Intent intent = new Intent("miui.intent.action.APP_PERM_EDITOR");
                            intent.setPackage("com.miui.securitycenter");
                            intent.putExtra("extra_pkgname", getPackageName());
                            startActivity(intent);
                            return;
                        } catch (Exception e2) {
                            // Fallback to standard overlay settings
                        }
                    }
                }

                // Standard Android overlay settings redirect (makes it 1-tap setup)
                Intent intent = new Intent(
                    android.provider.Settings.ACTION_MANAGE_OVERLAY_PERMISSION,
                    Uri.parse("package:" + getPackageName())
                );
                startActivity(intent);
            }
        }
    }

    public void checkAndRequestAutoStartNative() {
        SharedPreferences prefs = getSharedPreferences("FamilyCallPrefs", Context.MODE_PRIVATE);
        boolean autoStartRequested = prefs.getBoolean("auto_start_requested_v1", false);
        if (!autoStartRequested) {
            requestAutoStartPermission();
            prefs.edit().putBoolean("auto_start_requested_v1", true).apply();
        }
    }

    private void requestAutoStartPermission() {
        String manufacturer = Build.MANUFACTURER.toLowerCase();
        Intent intent = new Intent();
        boolean found = false;

        if (manufacturer.contains("xiaomi")) {
            intent.setComponent(new android.content.ComponentName("com.miui.securitycenter", "com.miui.permcenter.autostart.AutoStartManagementActivity"));
            found = true;
        } else if (manufacturer.contains("oppo") || manufacturer.contains("realme") || manufacturer.contains("oneplus")) {
            try {
                intent.setComponent(new android.content.ComponentName("com.coloros.safecenter", "com.coloros.safecenter.startupapp.StartupAppListActivity"));
                found = true;
            } catch (Exception e) {
                try {
                    intent.setComponent(new android.content.ComponentName("com.oppo.safe", "com.oppo.safe.permission.startup.StartupAppListActivity"));
                    found = true;
                } catch (Exception e2) {
                    try {
                        intent.setComponent(new android.content.ComponentName("com.coloros.safecenter", "com.coloros.safecenter.permission.startup.StartupAppListActivity"));
                        found = true;
                    } catch (Exception e3) {}
                }
            }
        } else if (manufacturer.contains("vivo")) {
            try {
                intent.setComponent(new android.content.ComponentName("com.iqoo.secure", "com.iqoo.secure.ui.phoneoptimize.AddWhiteListActivity"));
                found = true;
            } catch (Exception e) {
                try {
                    intent.setComponent(new android.content.ComponentName("com.vivo.permissionmanager", "com.vivo.permissionmanager.activity.BgStartUpManagerActivity"));
                    found = true;
                } catch (Exception e2) {
                    try {
                        intent.setComponent(new android.content.ComponentName("com.iqoo.secure", "com.iqoo.secure.ui.phoneoptimize.BgStartUpManager"));
                        found = true;
                    } catch (Exception e3) {}
                }
            }
        } else if (manufacturer.contains("huawei")) {
            intent.setComponent(new android.content.ComponentName("com.huawei.systemmanager", "com.huawei.systemmanager.optimize.process.ProtectActivity"));
            found = true;
        }

        if (found) {
            try {
                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                startActivity(intent);
                Log.d(TAG, "Auto-start settings launched for: " + manufacturer);
            } catch (Exception e) {
                Log.e(TAG, "Failed to launch native auto-start settings: " + e.getMessage());
            }
        }
    }

    private void clearCallingNotification() {
        // Clear telecom notification if needed, but TelecomManager usually handles it.
        // We also clear fallback notification directly as a safety fallback.
        try {
            NotificationManager manager = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
            if (manager != null) {
                manager.cancel(1001);
                Log.d(TAG, "🚨 Fallback calling notifications cleared natively!");
            }
        } catch (Exception e) {
            Log.e(TAG, "Error clearing notification: " + e.getMessage());
        }
    }

    /**
     * 🚨 CRITICAL: This runs BEFORE super.onCreate() — before WebView loads.
     * It populates pendingIntentExtras so that auth_guard.js can read them
     * immediately when the IIFE executes. This fixes the killed-state bug
     * where the race condition caused pendingIntentExtras to be null.
     */
    private void preExtractIntentData(Intent intent) {
        if (intent == null) return;
        
        String action = intent.getAction();
        Log.d(TAG, "preExtractIntentData: action=" + action);

        if ("com.haydan.familycall.ACTION_DECLINE_CALL".equals(action)) {
            JSObject data = new JSObject();
            data.put("event", "decline_call_action");
            data.put("call_id", intent.getStringExtra("call_id") != null ? intent.getStringExtra("call_id") : "");
            data.put("room_id", intent.getStringExtra("room_id") != null ? intent.getStringExtra("room_id") : "");
            pendingIntentExtras = data;
            Log.d(TAG, "✅ preExtract: pendingIntentExtras SET for decline_call_action");
            return;
        }

        if ("com.haydan.familycall.ACTION_ANSWER_CALL".equals(action)) {
            JSObject data = new JSObject();
            data.put("event", "answer_call_action");
            data.put("call_id", intent.getStringExtra("call_id") != null ? intent.getStringExtra("call_id") : "");
            data.put("room_id", intent.getStringExtra("room_id") != null ? intent.getStringExtra("room_id") : "");
            data.put("call_type", intent.getStringExtra("call_type") != null ? intent.getStringExtra("call_type") : "video");
            data.put("caller_name", intent.getStringExtra("caller_name") != null ? intent.getStringExtra("caller_name") : "Family");
            pendingIntentExtras = data;
            Log.d(TAG, "✅ preExtract: pendingIntentExtras SET for answer_call_action, room=" + intent.getStringExtra("room_id"));
            return;
        }

        if (intent.hasExtra("finish_call")) {
            JSObject data = new JSObject();
            data.put("event", "call_cancelled");
            data.put("room_id", intent.getStringExtra("room_id") != null ? intent.getStringExtra("room_id") : "");
            pendingIntentExtras = data;
            Log.d(TAG, "✅ preExtract: pendingIntentExtras SET for call_cancelled");
            return;
        }

        if ("com.haydan.familycall.ACTION_END_CALL".equals(action)) {
            JSObject data = new JSObject();
            data.put("event", "end_call_action");
            data.put("room_id", intent.getStringExtra("room_id") != null ? intent.getStringExtra("room_id") : "");
            pendingIntentExtras = data;
            Log.d(TAG, "✅ preExtract: pendingIntentExtras SET for end_call_action");
            return;
        }

        if (intent.hasExtra("incoming_call") || intent.hasExtra("new_message")) {
            String eventType = intent.hasExtra("incoming_call") ? "incoming_call" : "new_message";
            JSObject data = new JSObject();
            data.put("event", eventType);
            data.put("room_id", intent.getStringExtra("room_id") != null ? intent.getStringExtra("room_id") : "");
            data.put("caller_name", intent.getStringExtra("caller_name") != null ? intent.getStringExtra("caller_name") : "");
            data.put("sender_name", intent.getStringExtra("sender_name") != null ? intent.getStringExtra("sender_name") : "");
            data.put("call_id", intent.getStringExtra("call_id") != null ? intent.getStringExtra("call_id") : "");
            data.put("call_type", intent.getStringExtra("call_type") != null ? intent.getStringExtra("call_type") : "");
            data.put("message_body", intent.getStringExtra("message_body") != null ? intent.getStringExtra("message_body") : "");
            pendingIntentExtras = data;
            Log.d(TAG, "✅ preExtract: pendingIntentExtras SET for " + eventType);
        }
    }

    /**
     * Apply UI side-effects (window flags, clear notifications) AFTER super.onCreate().
     * Called only during cold launch. The data extraction already happened in preExtractIntentData().
     */
    private void applyIntentUiEffects(Intent intent) {
        if (intent == null) return;
        String action = intent.getAction();

        if ("com.haydan.familycall.ACTION_DECLINE_CALL".equals(action) || "com.haydan.familycall.ACTION_END_CALL".equals(action)) {
            clearCallingNotification();
            return;
        }

        if ("com.haydan.familycall.ACTION_ANSWER_CALL".equals(action)) {
            clearCallingNotification();
            runOnUiThread(() -> {
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
                        keyguardManager.requestDismissKeyguard(MainActivity.this, null);
                    }
                }
            });
            return;
        }

        if (intent.hasExtra("finish_call")) {
            clearCallingNotification();
            runOnUiThread(() -> {
                getWindow().clearFlags(
                    WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED
                    | WindowManager.LayoutParams.FLAG_DISMISS_KEYGUARD
                    | WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON
                    | WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON
                );
            });
            return;
        }

        if (intent.hasExtra("incoming_call") || intent.hasExtra("new_message")) {
            runOnUiThread(() -> {
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
                        keyguardManager.requestDismissKeyguard(MainActivity.this, null);
                    }
                }
            });
            clearCallingNotification();
        }
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        
        // Handle intent from background/warm resume — app is already running, inject directly
        handleIntent(intent);
    }

    /**
     * Handles intents when app is ALREADY RUNNING (background/warm boot).
     * For cold launch, preExtractIntentData() + applyIntentUiEffects() are used instead.
     */
    private void handleIntent(Intent intent) {
        if (intent == null) return;
        
        String action = intent.getAction();
        Log.d(TAG, "handleIntent (warm): action=" + action);

        if ("com.haydan.familycall.ACTION_DECLINE_CALL".equals(action)) {
            clearCallingNotification();
            JSObject data = new JSObject();
            data.put("event", "decline_call_action");
            data.put("call_id", intent.getStringExtra("call_id") != null ? intent.getStringExtra("call_id") : "");
            data.put("room_id", intent.getStringExtra("room_id") != null ? intent.getStringExtra("room_id") : "");
            final String jsonStr = data.toString();
            runOnUiThread(() -> {
                getBridge().getWebView().evaluateJavascript(
                    "if (window.handleAndroidIntent) { window.handleAndroidIntent(" + jsonStr + "); }",
                    null
                );
            });
            return;
        }

        if ("com.haydan.familycall.ACTION_ANSWER_CALL".equals(action)) {
            clearCallingNotification();
            runOnUiThread(() -> {
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
                        keyguardManager.requestDismissKeyguard(MainActivity.this, null);
                    }
                }
            });
            JSObject data = new JSObject();
            data.put("event", "answer_call_action");
            data.put("call_id", intent.getStringExtra("call_id") != null ? intent.getStringExtra("call_id") : "");
            data.put("room_id", intent.getStringExtra("room_id") != null ? intent.getStringExtra("room_id") : "");
            data.put("call_type", intent.getStringExtra("call_type") != null ? intent.getStringExtra("call_type") : "video");
            data.put("caller_name", intent.getStringExtra("caller_name") != null ? intent.getStringExtra("caller_name") : "Family");
            
            pendingIntentExtras = data; // Store it just in case WebView reloads
            
            final String jsonStr = data.toString();
            runOnUiThread(() -> {
                getBridge().getWebView().evaluateJavascript(
                    "if (window.handleAndroidIntent) { window.handleAndroidIntent(" + jsonStr + "); }",
                    null
                );
            });
            return;
        }

        if (intent.hasExtra("finish_call")) {
            clearCallingNotification();
            runOnUiThread(() -> {
                getWindow().clearFlags(
                    WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED
                    | WindowManager.LayoutParams.FLAG_DISMISS_KEYGUARD
                    | WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON
                    | WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON
                );
            });
            JSObject data = new JSObject();
            data.put("event", "call_cancelled");
            data.put("room_id", intent.getStringExtra("room_id") != null ? intent.getStringExtra("room_id") : "");
            final String jsonStr = data.toString();
            runOnUiThread(() -> {
                getBridge().getWebView().evaluateJavascript(
                    "if (window.handleAndroidIntent) { window.handleAndroidIntent(" + jsonStr + "); }",
                    null
                );
            });
            return;
        }

        if ("com.haydan.familycall.ACTION_END_CALL".equals(action)) {
            clearCallingNotification();
            JSObject data = new JSObject();
            data.put("event", "end_call_action");
            data.put("room_id", intent.getStringExtra("room_id") != null ? intent.getStringExtra("room_id") : "");
            final String jsonStr = data.toString();
            runOnUiThread(() -> {
                getBridge().getWebView().evaluateJavascript(
                    "if (window.handleAndroidIntent) { window.handleAndroidIntent(" + jsonStr + "); }",
                    null
                );
            });
            return;
        }

        if (intent.hasExtra("incoming_call") || intent.hasExtra("new_message")) {
            runOnUiThread(() -> {
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
                        keyguardManager.requestDismissKeyguard(MainActivity.this, null);
                    }
                }
            });
            clearCallingNotification();

            String eventType = intent.hasExtra("incoming_call") ? "incoming_call" : "new_message";
            JSObject data = new JSObject();
            data.put("event", eventType);
            data.put("room_id", intent.getStringExtra("room_id") != null ? intent.getStringExtra("room_id") : "");
            data.put("caller_name", intent.getStringExtra("caller_name") != null ? intent.getStringExtra("caller_name") : "");
            data.put("sender_name", intent.getStringExtra("sender_name") != null ? intent.getStringExtra("sender_name") : "");
            data.put("call_id", intent.getStringExtra("call_id") != null ? intent.getStringExtra("call_id") : "");
            data.put("call_type", intent.getStringExtra("call_type") != null ? intent.getStringExtra("call_type") : "");
            data.put("message_body", intent.getStringExtra("message_body") != null ? intent.getStringExtra("message_body") : "");
            final String jsonStr = data.toString();
            runOnUiThread(() -> {
                getBridge().getWebView().evaluateJavascript(
                    "if (window.handleAndroidIntent) { window.handleAndroidIntent(" + jsonStr + "); }",
                    null
                );
            });
        }
    }

    private void createNotificationChannels() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            NotificationManager manager = getSystemService(NotificationManager.class);

            // Create Audio Attributes for notification sound customization
            android.media.AudioAttributes audioAttributes = new android.media.AudioAttributes.Builder()
                .setContentType(android.media.AudioAttributes.CONTENT_TYPE_SONIFICATION)
                .setUsage(android.media.AudioAttributes.USAGE_NOTIFICATION_RINGTONE)
                .build();

            // RINGTONE URI pointing to 'res/raw/ringtone.mp3'
            Uri ringtoneSoundUri = Uri.parse("android.resource://" + getPackageName() + "/" + R.raw.ringtone);

    // Channel 1: Incoming Calls (HIGH PRIORITY)
            // NOTE: Sound is set to null because IncomingCallService plays ringtone via MediaPlayer
            // This prevents double-sound and guarantees ringtone works in ALL states
            NotificationChannel callChannel = new NotificationChannel(
                "incoming_calls_channel_v5",
                "Incoming Calls",
                NotificationManager.IMPORTANCE_HIGH
            );
            callChannel.setDescription("Notifications for incoming voice and video calls");
            callChannel.enableVibration(false); // Service handles vibration too
            callChannel.setLockscreenVisibility(android.app.Notification.VISIBILITY_PUBLIC);
            callChannel.setBypassDnd(true);
            callChannel.setSound(null, null); // NO sound from notification, MediaPlayer handles it
            manager.createNotificationChannel(callChannel);

            // NOTIFICATION URI pointing to 'res/raw/notification.mp3'
            Uri msgSoundUri = Uri.parse("android.resource://" + getPackageName() + "/" + R.raw.notification);

            // Channel 2: Messages (HIGH PRIORITY)
            NotificationChannel msgChannel = new NotificationChannel(
                "messages_channel_v4",
                "Messages",
                NotificationManager.IMPORTANCE_HIGH
            );
            msgChannel.setDescription("Notifications for new chat messages");
            msgChannel.enableVibration(true);
            msgChannel.setSound(msgSoundUri, audioAttributes);
            manager.createNotificationChannel(msgChannel);
        }
    }

    // --- Custom capacitor plugin for receiving deep-intent details on cold launch ---
    // --- Custom capacitor plugin to expose cold launch intent data to JS ---
    @CapacitorPlugin(name = "IntentReceiver")
    public static class IntentReceiverPlugin extends Plugin {
        @PluginMethod
        public void getIntentExtras(PluginCall call) {
            JSObject data = new JSObject();
            if (pendingIntentExtras != null) {
                data.put("has_extras", true);
                data.put("extras", pendingIntentExtras);
                pendingIntentExtras = null; // Clear so it only triggers once
            } else {
                data.put("has_extras", false);
            }
            call.resolve(data);
        }
    }

    // --- Custom capacitor plugin for fully persistent key-value native storage ---
    @CapacitorPlugin(name = "NativeStorage")
    public static class NativeStoragePlugin extends Plugin {
        private SharedPreferences getPrefs() {
            return getContext().getSharedPreferences("FamilyCallPrefs", Context.MODE_PRIVATE);
        }

        @PluginMethod
        public void setItem(PluginCall call) {
            String key = call.getString("key");
            String value = call.getString("value");
            if (key == null) {
                call.reject("Key is required");
                return;
            }
            getPrefs().edit().putString(key, value).apply();
            call.resolve();
        }

        @PluginMethod
        public void getItem(PluginCall call) {
            String key = call.getString("key");
            if (key == null) {
                call.reject("Key is required");
                return;
            }
            String value = getPrefs().getString(key, null);
            JSObject result = new JSObject();
            result.put("value", value);
            call.resolve(result);
        }

        @PluginMethod
        public void removeItem(PluginCall call) {
            String key = call.getString("key");
            if (key == null) {
                call.reject("Key is required");
                return;
            }
            getPrefs().edit().remove(key).apply();
            call.resolve();
        }
    }

    // --- Custom capacitor plugin for managing overlay & autostart permissions ---
    @CapacitorPlugin(name = "AppPermissions")
    public static class AppPermissionsPlugin extends Plugin {
        @PluginMethod
        public void checkOverlayPermission(PluginCall call) {
            JSObject data = new JSObject();
            boolean granted = true;
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                granted = android.provider.Settings.canDrawOverlays(getContext());
            }
            data.put("granted", granted);
            call.resolve(data);
        }

        @PluginMethod
        public void requestOverlayPermission(PluginCall call) {
            MainActivity activity = (MainActivity) getActivity();
            if (activity != null) {
                activity.runOnUiThread(new Runnable() {
                    @Override
                    public void run() {
                        activity.requestOverlayPermissionNative();
                    }
                });
            }
            call.resolve();
        }

        @PluginMethod
        public void checkAndRequestAutoStart(PluginCall call) {
            MainActivity activity = (MainActivity) getActivity();
            if (activity != null) {
                activity.runOnUiThread(new Runnable() {
                    @Override
                    public void run() {
                        activity.checkAndRequestAutoStartNative();
                    }
                });
            }
            call.resolve();
        }

        @PluginMethod
        public void openAppInfo(PluginCall call) {
            MainActivity activity = (MainActivity) getActivity();
            if (activity != null) {
                activity.runOnUiThread(new Runnable() {
                    @Override
                    public void run() {
                        try {
                            Intent intent = new Intent(android.provider.Settings.ACTION_APPLICATION_DETAILS_SETTINGS);
                            intent.setData(Uri.parse("package:" + activity.getPackageName()));
                            intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                            activity.startActivity(intent);
                        } catch (Exception e) {
                            Log.e("AppPermissions", "Failed to open App Info: " + e.getMessage());
                        }
                    }
                });
            }
            call.resolve();
        }

        @PluginMethod
        public void openAutoStartSettings(PluginCall call) {
            MainActivity activity = (MainActivity) getActivity();
            if (activity != null) {
                activity.runOnUiThread(new Runnable() {
                    @Override
                    public void run() {
                        activity.requestAutoStartPermission();
                    }
                });
            }
            call.resolve();
        }

        @PluginMethod
        public void checkFullScreenIntentPermission(PluginCall call) {
            JSObject data = new JSObject();
            boolean granted = true;
            if (Build.VERSION.SDK_INT >= 34) { // Build.VERSION_CODES.UPSIDE_DOWN_CAKE
                android.app.NotificationManager manager = (android.app.NotificationManager) getContext().getSystemService(Context.NOTIFICATION_SERVICE);
                if (manager != null) {
                    granted = manager.canUseFullScreenIntent();
                }
            }
            data.put("granted", granted);
            call.resolve(data);
        }

        @PluginMethod
        public void requestFullScreenIntentPermission(PluginCall call) {
            MainActivity activity = (MainActivity) getActivity();
            if (activity != null) {
                activity.runOnUiThread(new Runnable() {
                    @Override
                    public void run() {
                        if (Build.VERSION.SDK_INT >= 34) {
                            try {
                                Intent intent = new Intent("android.settings.MANAGE_APP_USE_FULL_SCREEN_INTENT");
                                intent.setData(Uri.parse("package:" + activity.getPackageName()));
                                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                                activity.startActivity(intent);
                            } catch (Exception e) {
                                try {
                                    Intent intent = new Intent("android.settings.MANAGE_APP_USE_FULL_SCREEN_INTENT");
                                    intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                                    activity.startActivity(intent);
                                } catch (Exception ex) {
                                    Log.e("AppPermissions", "Failed to open Full Screen Intent settings: " + ex.getMessage());
                                }
                            }
                        }
                    }
                });
            }
            call.resolve();
        }

        @PluginMethod
        public void getDeviceManufacturer(PluginCall call) {
            JSObject data = new JSObject();
            data.put("manufacturer", Build.MANUFACTURER);
            call.resolve(data);
        }
    }

    // --- Custom capacitor plugin for TelecomManager (call end) ---
    @CapacitorPlugin(name = "TelecomManager")
    public static class TelecomManagerPlugin extends Plugin {
        @PluginMethod
        public void endCall(PluginCall call) {
            if (CallConnectionService.currentConnection != null) {
                CallConnectionService.currentConnection.onDisconnect();
                CallConnectionService.currentConnection = null;
            }
            call.resolve();
        }
    }
}
