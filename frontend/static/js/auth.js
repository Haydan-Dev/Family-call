// --- SIGNUP LOGIC ---
const signupForm = document.getElementById('signupForm');
if(signupForm) signupForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    // WARNING: HTML mein input id="name", id="email", id="password" hi hone chahiye
    const full_name = document.getElementById('name').value;
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;

    try {
      const response = await fetch(`${BASE_URL}/users/signup`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ full_name, email, password })
      });

      if (response.ok) {
        // FIXED: Absolute path for routing
        window.location.href = '/static/login.html';
      } else {
        const errorData = await response.json();
        alert('Signup failed: ' + (errorData.message || 'Unknown error'));
      }
    } catch (error) {
      console.error('Error during signup:', error);
      alert('Error connecting to server.');
    }
});

// --- LOGIN LOGIC ---
const loginForm = document.getElementById('loginForm');
if(loginForm) loginForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    // WARNING: HTML mein input id="email", id="password" hi hone chahiye
    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;

    try {
      const response = await fetch(`${BASE_URL}/users/login`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ email, password })
      });

      if (response.ok) {
        const data = await response.json();
        const token = data.token || data.access_token;
        if (token) {
          localStorage.setItem('token', token);
          console.log("TOKEN ACQUIRED");
          // FIXED: Absolute path for routing
          window.location.href = '/static/home.html';
        } else {
          alert('Login successful but no token found in response.');
        }
      } else {
        const errorData = await response.json();
        alert('Login failed: ' + (errorData.message || 'Unknown error'));
      }
    } catch (error) {
      console.error('Error during login:', error);
      alert('Error connecting to server.');
    }
});