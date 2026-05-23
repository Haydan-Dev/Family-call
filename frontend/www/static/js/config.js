// Cloudflare Tunnel Testing Configuration
const TUNNEL_DOMAIN = "cheese-robot-rainbow-warranty.trycloudflare.com";

// NO Port numbers here! Cloudflare handles it automatically.
const BASE_URL = `https://${TUNNEL_DOMAIN}`; // Secure Fetch
const WS_URL = `wss://${TUNNEL_DOMAIN}`;     // MUST be wss:// for Cloudflare!

console.log("🚀 Cloudflare Testing via:", WS_URL);


// /// Cloudflare hata diya, Tailscale Funnel Zindabad!
// const TUNNEL_DOMAIN = "abu-hurairah.tail6c8cb6.ts.net";
// const BASE_URL = `https://${TUNNEL_DOMAIN}`; // HTTPS for Secure Fetch
// const WS_URL = `wss://${TUNNEL_DOMAIN}`;     // WSS for Secure WebSockets

// // Ye ensure karta hai ki WebRTC signaling block na ho
// console.log("🚀 Signaling via Tunnel:", WS_URL);

// Global Authenticated Fetch Wrapper
async function authFetch(url, options = {}) {
  const token = await window.NativeStorage.getItem('token');
  if (!options.headers) options.headers = {};
  if (token) options.headers['Authorization'] = `Bearer ${token}`;

  if (!(options.body instanceof FormData)) {
    if (!options.headers['Content-Type']) {
      options.headers['Content-Type'] = 'application/json';
    }
  }

  const res = await fetch(url, options);
  if (res.status === 401) {
    await window.NativeStorage.removeItem('token');
    window.location.href = 'login.html';
  }
  return res;
}
