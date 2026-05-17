(function() {
  const token = localStorage.getItem('token');
  const path = window.location.pathname;
  
  // Auth Pages: User should not see these if already logged in
  const isAuthPage = path.includes('login.html') || 
                     path.includes('signup.html') || 
                     path.includes('verify-email.html') || 
                     path.includes('forgot-password.html');

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
