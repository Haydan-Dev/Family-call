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
        
        if (data.requires_2fa) {
            loginForm.classList.add('hidden');
            const twoFaForm = document.getElementById('twoFaForm');
            if (twoFaForm) {
                twoFaForm.classList.remove('hidden');
                twoFaForm.dataset.email = email;
            }
        } else {
            const token = data.access_token;
            if (token) {
              await window.NativeStorage.setItem('token', token);
              console.log("TOKEN ACQUIRED");
              window.location.href = 'home.html';
            } else {
              alert('Login successful but token was not returned.');
            }
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

// --- 2FA LOGIC ---
const twoFaForm = document.getElementById('twoFaForm');
if (twoFaForm) {
  twoFaForm.addEventListener('submit', async function(e) {
    e.preventDefault();
    const email = twoFaForm.dataset.email;
    const code = document.getElementById('twoFaCode').value.trim();
    
    const submitBtn = twoFaForm.querySelector('.btn-primary');
    submitBtn.textContent = 'Verifying...';
    submitBtn.disabled = true;
    
    try {
      const response = await fetch(`${BASE_URL}/users/login/verify-2fa`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ email, code })
      });
      
      if (response.ok) {
        const data = await response.json();
        const token = data.access_token;
        if (token) {
          await window.NativeStorage.setItem('token', token);
          window.location.href = 'home.html';
        }
      } else {
        const errorData = await response.json();
        alert('Verification failed: ' + (errorData.detail || 'Unknown error'));
      }
    } catch (error) {
      console.error('Error during 2FA:', error);
      alert('Error connecting to server.');
    } finally {
      submitBtn.textContent = 'Verify Code';
      submitBtn.disabled = false;
    }
  });

  const backBtn = document.getElementById('backToLogin');
  if (backBtn) {
    backBtn.addEventListener('click', (e) => {
      e.preventDefault();
      twoFaForm.classList.add('hidden');
      document.getElementById('loginForm').classList.remove('hidden');
    });
  }
}