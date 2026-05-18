// --- SIGNUP LOGIC ---
const signupForm = document.getElementById('signupForm');
if (signupForm) {
  signupForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const name = document.getElementById('name').value.trim();
    const email = document.getElementById('email').value.trim().toLowerCase();
    const password = document.getElementById('password').value;

    const submitBtn = signupForm.querySelector('.btn-primary');
    submitBtn.textContent = 'Registering...';
    submitBtn.disabled = true;

    try {
      const response = await fetch(`${BASE_URL}/users/signup`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ full_name: name, email, password })
      });

      if (response.ok) {
        // Redirect to verify-email.html with email parameter
        window.location.href = `verify-email.html?email=${encodeURIComponent(email)}`;
      } else {
        const errorData = await response.json();
        alert('Signup failed: ' + (errorData.detail || 'Unknown error'));
      }
    } catch (error) {
      console.error('Error during signup:', error);
      alert('Error connecting to server.');
    } finally {
      submitBtn.textContent = 'Sign Up';
      submitBtn.disabled = false;
    }
  });
}

// --- LOGIN LOGIC ---
const loginForm = document.getElementById('loginForm');
if (loginForm) {
  loginForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    const email = document.getElementById('email').value.trim().toLowerCase();
    const password = document.getElementById('password').value;

    const submitBtn = loginForm.querySelector('.btn-primary');
    submitBtn.textContent = 'Signing in...';
    submitBtn.disabled = true;

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
        const token = data.access_token;
        if (token) {
          localStorage.setItem('token', token);
          console.log("TOKEN ACQUIRED");
          window.location.href = 'home.html';
        } else {
          alert('Login successful but token was not returned.');
        }
      } else {
        const errorData = await response.json();
        alert('Login failed: ' + (errorData.detail || 'Unknown error'));
      }
    } catch (error) {
      console.error('Error during login:', error);
      alert('Error connecting to server.');
    } finally {
      submitBtn.textContent = 'Login';
      submitBtn.disabled = false;
    }
  });
}