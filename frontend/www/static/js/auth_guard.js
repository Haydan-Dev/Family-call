// Global Intent Handler to instantly route incoming calls on warm-boot
window.handleAndroidIntent = async function (data) {
  console.log('🚨 [Global handleAndroidIntent] Received custom native intent:', JSON.stringify(data));
  if (!data || !data.event) return;

  const token = await window.NativeStorage.getItem('token');


  const roomId = data.room_id || '';
  const senderName = encodeURIComponent(data.sender_name || 'Family Member');
  console.log(`Global routing to chat room: room=${roomId}`);
  if (roomId) {
    window.location.href = `chat.html?room_id=${roomId}&name=${senderName}`;
  }
};

// Global Authenticated Persistent Native Storage Wrapper
window.NativeStorage = {
  async setItem(key, value) {
    if (window.Capacitor && window.Capacitor.isNativePlatform()) {
      try {
        await window.Capacitor.Plugins.NativeStorage.setItem({ key, value });
      } catch (e) {
        console.error("NativeStorage setItem error:", e);
        localStorage.setItem(key, value);
      }
    } else {
      localStorage.setItem(key, value);
    }
  },
  async getItem(key) {
    if (window.Capacitor && window.Capacitor.isNativePlatform()) {
      try {
        const res = await window.Capacitor.Plugins.NativeStorage.getItem({ key });
        return res.value;
      } catch (e) {
        console.error("NativeStorage getItem error:", e);
        return localStorage.getItem(key);
      }
    } else {
      return localStorage.getItem(key);
    }
  },
  async removeItem(key) {
    if (window.Capacitor && window.Capacitor.isNativePlatform()) {
      try {
        await window.Capacitor.Plugins.NativeStorage.removeItem({ key });
      } catch (e) {
        console.error("NativeStorage removeItem error:", e);
        localStorage.removeItem(key);
      }
    } else {
      localStorage.removeItem(key);
    }
  }
};

(async function () {
  const token = await window.NativeStorage.getItem('token');

  // Check for incoming call intent first (Cold boot from background call notification or action buttons)
  if (window.Capacitor && window.Capacitor.isNativePlatform()) {
    try {
      console.log("🚨 [auth_guard IIFE] Checking for IntentReceiver plugin...");
      let IntentReceiver = window.Capacitor.Plugins.IntentReceiver;

      // Wait up to 1000ms for the plugin to be injected by the Capacitor bridge
      let retries = 0;
      while (!IntentReceiver && retries < 20) {
        await new Promise(r => setTimeout(r, 50));
        IntentReceiver = window.Capacitor.Plugins.IntentReceiver;
        retries++;
      }

      if (IntentReceiver) {
        console.log("🚨 [auth_guard IIFE] IntentReceiver plugin found! Fetching extras...");
        const result = await IntentReceiver.getIntentExtras();
        console.log("🚨 [auth_guard IIFE] getIntentExtras result:", JSON.stringify(result));

        if (result && result.has_extras && result.extras) {
          const callData = result.extras;
          console.log("🚨 [auth_guard IIFE] Parsed callData:", JSON.stringify(callData));
          
          if (callData.event === 'incoming_call' || callData.event === 'answer_call_action') {
            const roomId = callData.room_id || '';
            const senderName = encodeURIComponent(callData.caller_name || 'Family Member');
            const callType = callData.call_type || 'video';
            const autoAnswer = callData.event === 'answer_call_action' ? 'true' : 'false';
            
            console.log(`🚨 [auth_guard IIFE] Routing cold-boot call to chat.html (auto_answer=${autoAnswer})`);
            if (roomId) {
              window.location.href = `chat.html?room_id=${roomId}&name=${senderName}&auto_answer=${autoAnswer}&call_type=${callType}&incoming_call=true`;
              return; // Stop further execution
            }
          } else if (callData.event === 'decline_call_action') {
            const roomId = callData.room_id || '';
            const callId = callData.call_id || '';
            console.log(`🚨 [auth_guard IIFE] Routing cold-boot decline to chat.html`);
            if (roomId) {
              window.location.href = `chat.html?room_id=${roomId}&decline_call=true&call_id=${callId}`;
              return; // Stop further execution
            }
          }
        } else {
          console.log("🚨 [auth_guard IIFE] No pending intent extras found.");
        }
      } else {
        console.error("🚨 [auth_guard IIFE] IntentReceiver plugin still not found after waiting!");
      }
    } catch (e) {
      console.error("VoIP launch intercept failed in IIFE:", e);
    }
  }

  const path = window.location.pathname;

  // Auth Pages: User should not see these if already logged in
  const isAuthPage = path.includes('login.html') ||
    path.includes('signup.html') ||
    path.includes('verify-email.html') ||
    path.includes('forgot-password.html') ||
    path.endsWith('/') ||
    path.endsWith('index.html');

  // Protected Pages: User must be logged in to see these
  const isProtectedPage = path.includes('chat.html') ||
    path.includes('home.html') ||
    path.includes('active_call.html') ||
    path.includes('audio_activecall.html') ||
    path.includes('calls_history.html') ||
    path.includes('blocked_users.html');

  if (token && isAuthPage) {
    // Redirect authenticated users trying to access login/signup/reset
    window.location.href = 'home.html';
  } else if (!token && isProtectedPage) {
    // Redirect unauthenticated users trying to access main app pages
    window.location.href = 'login.html';
  }
})();
