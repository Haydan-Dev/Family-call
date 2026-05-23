// Global Intent Handler to instantly route incoming calls on warm-boot
window.handleAndroidIntent = async function(data) {
  console.log('🚨 [Global handleAndroidIntent] Received custom native intent:', JSON.stringify(data));
  if (!data || !data.event) return;

  const token = await window.NativeStorage.getItem('token');

  if (data.event === 'decline_call_action') {
    const callId = data.call_id || '';
    console.log('🚨 [Global handleAndroidIntent] Native DECLINE button clicked for call:', callId);
    if (callId && token) {
      try {
        const res = await fetch(`${BASE_URL}/calls/status_update/${callId}`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
          },
          body: JSON.stringify({ call_status: 'rejected' })
        });
        console.log('✅ Call successfully declined natively. Status:', res.status);
      } catch (err) {
        console.error('❌ Native call decline fetch failed:', err);
      }
    }
    return;
  }

  if (data.event === 'answer_call_action') {
    const callId = data.call_id || '';
    const roomId = data.room_id || '';
    const callType = data.call_type || 'video';
    const callerName = encodeURIComponent(data.caller_name || 'Family');
    console.log('🚨 [Global handleAndroidIntent] Native ANSWER button clicked. Launching room:', roomId);

    let target = `active_call.html?room_id=${roomId}&call_id=${callId}&mode=receiver&call_type=${callType}&name=${callerName}`;
    if (callType === 'audio') {
      target = `audio_activecall.html?room_id=${roomId}&call_id=${callId}&mode=receiver&call_type=${callType}&name=${callerName}`;
    }
    console.log("Global routing to active call room directly:", target);
    window.location.href = target;
    return;
  }

  if (data.event === 'incoming_call') {
    const callType = data.call_type || 'video';
    const roomId = data.room_id || '';
    const callId = data.call_id || '';
    const callerName = encodeURIComponent(data.caller_name || 'Family');

    let target = `incoming_call.html?room_id=${roomId}&call_id=${callId}&caller_name=${callerName}`;
    if (callType === 'audio') {
      target = `audio_incommingcall.html?room_id=${roomId}&call_id=${callId}&caller_name=${callerName}`;
    }
    console.log("Global routing to call screen:", target);
    window.location.href = target;
  } else if (data.event === 'call_cancelled' || data.event === 'call_ended' || data.event === 'call_declined' || data.event === 'call_rejected') {
    console.log('🚨 [Global handleAndroidIntent] Call cancelled/ended natively. Redirecting to chat...');
    const roomId = data.room_id || '';
    if (roomId) {
      window.location.href = `chat.html?room_id=${roomId}`;
    } else {
      window.location.href = 'home.html';
    }
  } else if (data.event === 'new_message') {
    const roomId = data.room_id || '';
    const senderName = encodeURIComponent(data.sender_name || 'Family Member');
    console.log(`Global routing to chat room: room=${roomId}`);
    if (roomId) {
      window.location.href = `chat.html?room_id=${roomId}&name=${senderName}`;
    }
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

(async function() {
  const token = await window.NativeStorage.getItem('token');

  // Check for incoming call intent first (Cold boot from background call notification or action buttons)
  if (window.Capacitor && window.Capacitor.isNativePlatform()) {
    try {
      const IntentReceiver = window.Capacitor.Plugins.IntentReceiver;
      if (IntentReceiver) {
        const result = await IntentReceiver.getIntentExtras();
        if (result && result.has_extras && result.extras) {
          const callData = result.extras;
          
          if (callData.event === 'decline_call_action') {
            const callId = callData.call_id || '';
            console.log('🚨 [auth_guard IIFE] Cold Decline clicked for call:', callId);
            if (callId && token) {
              try {
                await fetch(`${BASE_URL}/calls/status_update/${callId}`, {
                  method: 'PATCH',
                  headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                  },
                  body: JSON.stringify({ call_status: 'rejected' })
                });
                console.log('✅ Call declined successfully during cold boot!');
              } catch (err) {
                console.error('❌ Cold call decline fetch failed:', err);
              }
            }
            // Do not redirect to any call screen, just let it proceed to normal authentication routing below!
          }
          else if (callData.event === 'answer_call_action') {
            const callId = callData.call_id || '';
            const roomId = callData.room_id || '';
            const callType = callData.call_type || 'video';
            const callerName = encodeURIComponent(callData.caller_name || 'Family');
            console.log('🚨 [auth_guard IIFE] Cold Answer clicked. Launching room:', roomId);
            
            let target = `active_call.html?room_id=${roomId}&call_id=${callId}&mode=receiver&call_type=${callType}&name=${callerName}`;
            if (callType === 'audio') {
              target = `audio_activecall.html?room_id=${roomId}&call_id=${callId}&mode=receiver&call_type=${callType}&name=${callerName}`;
            }
            window.location.href = target;
            return;
          }
          else if (callData.event === 'incoming_call') {
            const callType = callData.call_type || 'video';
            const roomId = callData.room_id || '';
            const callId = callData.call_id || '';
            const callerName = encodeURIComponent(callData.caller_name || 'Family');
            console.log('🚨 [auth_guard IIFE] Cold Incoming call. Launching screen:', roomId);
            
            let target = `incoming_call.html?room_id=${roomId}&call_id=${callId}&caller_name=${callerName}`;
            if (callType === 'audio') {
              target = `audio_incommingcall.html?room_id=${roomId}&call_id=${callId}&caller_name=${callerName}`;
            }
            window.location.href = target;
            return;
          }
        }
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
