// Configuration
const SERVER_IP = "192.168.1.4"; // Default to localhost, easily changeable
const PORT = 8000;
const BASE_URL = `http://${SERVER_IP}:${PORT}`;
const WS_URL = `ws://${SERVER_IP}:${PORT}`;

// Global Authenticated Fetch Wrapper
async function authFetch(url, options = {}) {
  const token = localStorage.getItem('token');
  if (!options.headers) options.headers = {};
  if (token) options.headers['Authorization'] = `Bearer ${token}`;
  
  if (!(options.body instanceof FormData)) {
      if (!options.headers['Content-Type']) {
          options.headers['Content-Type'] = 'application/json';
      }
  }
  
  const res = await fetch(url, options);
  if (res.status === 401) {
    localStorage.removeItem('token');
    window.location.href = 'login.html';
  }
  return res;
}
