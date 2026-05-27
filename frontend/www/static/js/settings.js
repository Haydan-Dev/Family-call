document.addEventListener('DOMContentLoaded', async () => {
  const nameInput = document.getElementById('nameInput');
  const emailDisplay = document.getElementById('emailDisplay');
  const twoFaToggle = document.getElementById('twoFaToggle');
  const logoutBtn = document.getElementById('settingsLogoutBtn');

  // Load user settings
  async function loadSettings() {
    try {
      const res = await authFetch(`${BASE_URL}/api/settings/`);
      if (res.ok) {
        const data = await res.json();
        nameInput.value = data.name || '';
        emailDisplay.textContent = data.email || '';
        if (data.is_2fa_enabled) {
          twoFaToggle.classList.add('active');
        } else {
          twoFaToggle.classList.remove('active');
        }
      }
    } catch (e) {
      console.error("Failed to load settings", e);
    }
  }

  // Handle Name update
  let typingTimer;
  nameInput.addEventListener('input', () => {
    clearTimeout(typingTimer);
    typingTimer = setTimeout(async () => {
      const newName = nameInput.value.trim();
      if (newName) {
        await authFetch(`${BASE_URL}/api/settings/`, {
          method: 'PATCH',
          body: JSON.stringify({ name: newName })
        });
      }
    }, 1000); // Save after 1 second of no typing
  });

  // Handle 2FA Toggle
  twoFaToggle.addEventListener('click', async () => {
    const isCurrentlyActive = twoFaToggle.classList.contains('active');
    const newState = !isCurrentlyActive;
    
    // Optimistic UI update
    twoFaToggle.classList.toggle('active');
    
    try {
      const res = await authFetch(`${BASE_URL}/api/settings/`, {
        method: 'PATCH',
        body: JSON.stringify({ is_2fa_enabled: newState })
      });
      if (!res.ok) {
        // Revert on failure
        twoFaToggle.classList.toggle('active');
        alert("Failed to update 2FA setting.");
      }
    } catch (e) {
      twoFaToggle.classList.toggle('active');
      console.error("Failed to update 2FA", e);
    }
  });

  // Handle Logout
  logoutBtn.addEventListener('click', async () => {
    const confirmLogout = confirm("Are you sure you want to log out?");
    if (confirmLogout) {
      await window.NativeStorage.removeItem('token');
      window.location.href = 'login.html';
    }
  });

  // Initial load
  loadSettings();
});
