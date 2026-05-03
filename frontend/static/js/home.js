document.addEventListener('DOMContentLoaded', () => {
  // --- 1. Core Setup & Auth Check ---
  const token = localStorage.getItem('token');
  if (!token) {
    window.location.href = 'login.html';
    return;
  }

  


  // --- 2. Element References ---
  // Layer 1
  const chatsLoading = document.getElementById('chatsLoading');
  const chatsEmpty = document.getElementById('chatsEmpty');
  const chatsList = document.getElementById('chatsList');
  const logoutBtn = document.getElementById('logoutBtn');
  
  // Layer 2
  const contactsSlider = document.getElementById('contactsSlider');
  const openSliderBtn = document.getElementById('openSliderBtn');
  const closeSliderBtn = document.getElementById('closeSliderBtn');
  const contactsLoading = document.getElementById('contactsLoading');
  const contactsEmpty = document.getElementById('contactsEmpty');
  const contactsList = document.getElementById('contactsList');

  // Context Menu Setup
  const roomContextMenu = document.getElementById('roomContextMenu');
  let selectedRoomId = null;

  document.addEventListener('click', (e) => {
    if (roomContextMenu && !roomContextMenu.contains(e.target)) {
      roomContextMenu.style.display = 'none';
    }
  });

  document.querySelectorAll('#roomContextMenu .ctx-item').forEach(item => {
    item.addEventListener('click', async (e) => {
      e.stopPropagation();
      const action = item.getAttribute('data-action');
      roomContextMenu.style.display = 'none';
      if (!selectedRoomId) return;

      try {
        if (action === 'pin') {
          await authFetch(`${BASE_URL}/conversations/pin/${selectedRoomId}`, { method: 'PATCH' });
        } else if (action === 'archive') {
          await authFetch(`${BASE_URL}/conversations/archive/${selectedRoomId}`, { method: 'PATCH' });
        } else if (action === 'delete') {
          if(confirm('Delete this chat permanently?')) {
            await authFetch(`${BASE_URL}/conversations/delete_conversations/${selectedRoomId}`, { method: 'DELETE' });
          }
        }
        fetchChats(); // Refresh UI
      } catch (err) {
        console.error(err);
        alert('Action failed');
      }
    });
  });

  // Fetch logic
  const openAddContactModalBtn = document.getElementById('openAddContactModalBtn');

  // Layer 3
  const contactModal = document.getElementById('contactModal');
  const cancelModalBtn = document.getElementById('cancelModalBtn');
  const addContactForm = document.getElementById('addContactForm');

  // Utility to toggle visibility
  function showState(showEl, hideEls) {
    showEl.classList.remove('hidden');
    hideEls.forEach(el => el.classList.add('hidden'));
  }

  // --- LAYER 1: FETCH CHATS ---
  async function fetchChats() {
    showState(chatsLoading, [chatsEmpty, chatsList]);
    try {
      const res = await authFetch(`${BASE_URL}/conversations/display_conversations`, { method: 'GET' });
      const data = await res.json();
      
      let chats = Array.isArray(data) ? data : (data.data || []);

      if (chats.length === 0) {
        showState(chatsEmpty, [chatsLoading, chatsList]);
      } else {
        renderChats(chats);
        showState(chatsList, [chatsLoading, chatsEmpty]);
      }
    } catch (error) {
      console.error('Error fetching chats:', error);
      showState(chatsEmpty, [chatsLoading, chatsList]);
      chatsEmpty.querySelector('p').textContent = "Failed to load recent chats.";
    }
  }

  function renderChats(chats) {
    chatsList.innerHTML = '';
    chats.forEach((chat, index) => {
      const roomId = chat.room_id || 'Unknown';
      const name = chat.contact_name || chat.name || roomId; 
      const initial = name.charAt(0).toUpperCase();
      
      let badges = '';
      if (chat.is_pinned) {
        badges += `<svg class="badge-icon" fill="currentColor" viewBox="0 0 24 24"><path d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"></path></svg>`;
      }
      if (chat.is_archived) {
        badges += `<svg class="badge-icon" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"></path></svg>`;
      }

      const card = document.createElement('div');
      card.className = 'card-item';
      card.style.animationDelay = `${index * 0.05}s`;
      card.innerHTML = `
        <div class="avatar">${initial}</div>
        <div class="info">
          <div class="name-text">${name} ${badges}</div>
          <div class="sub-text">${chat.last_message || 'Tap to chat'}</div>
        </div>
      `;
      card.addEventListener('click', () => {
        window.location.href = `chat.html?room_id=${roomId}&name=${encodeURIComponent(name)}`;
      });
      
      // Long press / right click logic
      card.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        selectedRoomId = roomId;
        roomContextMenu.style.display = 'flex';
        
        // Prevent menu from going off-screen
        let posX = e.pageX;
        let posY = e.pageY;
        if (posX + 180 > window.innerWidth) posX = window.innerWidth - 190;
        if (posY + 160 > window.innerHeight) posY = window.innerHeight - 170;
        
        roomContextMenu.style.left = `${posX}px`;
        roomContextMenu.style.top = `${posY}px`;
      });
      
      let pressTimer;
      card.addEventListener('touchstart', (e) => {
        pressTimer = window.setTimeout(() => {
          selectedRoomId = roomId;
          roomContextMenu.style.display = 'flex';
          roomContextMenu.style.left = `${e.touches[0].pageX}px`;
          roomContextMenu.style.top = `${e.touches[0].pageY}px`;
        }, 600); // 600ms long press
      });
      card.addEventListener('touchend', () => {
        clearTimeout(pressTimer);
      });
      card.addEventListener('touchmove', () => {
        clearTimeout(pressTimer);
      });

      chatsList.appendChild(card);
    });
  }

  // --- LAYER 2: FETCH CONTACTS & START CHAT ---
  async function fetchContacts() {
    showState(contactsLoading, [contactsEmpty, contactsList]);
    try {
      const res = await authFetch(`${BASE_URL}/contacts/`, { method: 'GET' });
      const data = await res.json();
      
      let contacts = [];
      if (Array.isArray(data)) contacts = data;
      else if (data && Array.isArray(data.contacts)) contacts = data.contacts;
      else if (data && data.data && Array.isArray(data.data)) contacts = data.data;

      if (contacts.length === 0) {
        showState(contactsEmpty, [contactsLoading, contactsList]);
      } else {
        renderContacts(contacts);
        showState(contactsList, [contactsLoading, contactsEmpty]);
      }
    } catch (error) {
      console.error('Error fetching contacts:', error);
      showState(contactsEmpty, [contactsLoading, contactsList]);
      contactsEmpty.querySelector('p').textContent = "Failed to load contacts.";
    }
  }

  function renderContacts(contacts) {
    contactsList.innerHTML = '';
    contacts.forEach((contact, index) => {
      const contactId = contact._id || contact.id;
      const name = contact.contact_nickname || contact.name || 'Unknown';
      const email = contact.contact_email || contact.email || '';
      const initial = name.charAt(0).toUpperCase();

      const card = document.createElement('div');
      card.className = 'card-item';
      card.style.animationDelay = `${index * 0.05}s`;
      card.innerHTML = `
        <div class="avatar">${initial}</div>
        <div class="info">
          <div class="name-text">${name}</div>
          <div class="sub-text">${email}</div>
        </div>
      `;
      
      // Trigger Start Conversation
      card.addEventListener('click', async () => {
        if (!contactId) { alert("Contact ID missing."); return; }
        
        try {
          // Visual feedback
          card.style.opacity = '0.5';
          const res = await authFetch(`${BASE_URL}/conversations/start_conversation/${contactId}`, {
             method: 'POST' 
          });
          const data = await res.json();
          const roomId = data.room_id || data.new_room_id || data.id;
          
          if (roomId) {
            window.location.href = `chat.html?room_id=${roomId}&name=${encodeURIComponent(name)}`;
          } else {
            alert('Failed to get room ID');
            card.style.opacity = '1';
          }
        } catch (error) {
          console.error("Error starting conversation", error);
          alert('Could not start conversation.');
          card.style.opacity = '1';
        }
      });
      
      contactsList.appendChild(card);
    });
  }

  // Slider Interactions
  openSliderBtn.addEventListener('click', () => {
    contactsSlider.classList.add('active');
    fetchContacts(); // Fetch contacts when slider opens
  });

  closeSliderBtn.addEventListener('click', () => {
    contactsSlider.classList.remove('active');
  });

  // --- LAYER 3: ADD CONTACT MODAL ---
  openAddContactModalBtn.addEventListener('click', () => {
    contactModal.classList.add('active');
  });

  cancelModalBtn.addEventListener('click', () => {
    contactModal.classList.remove('active');
    addContactForm.reset();
  });

  contactModal.addEventListener('click', (e) => {
    if (e.target === contactModal) {
      contactModal.classList.remove('active');
      addContactForm.reset();
    }
  });

  addContactForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const nick_val = document.getElementById('contactNickname').value;
    const email_val = document.getElementById('contactEmail').value;
    const submitBtn = addContactForm.querySelector('.btn-save');
    const originalText = submitBtn.textContent;
    
    submitBtn.textContent = 'Saving...';
    submitBtn.disabled = true;

    try {
      const res = await authFetch(`${BASE_URL}/contacts/save`, {
        method: 'POST',
        body: JSON.stringify({ contact_email: email_val, contact_nickname: nick_val })
      });

      if (res.status === 200 || res.ok) {
        contactModal.classList.remove('active');
        addContactForm.reset();
        fetchContacts(); // Refresh slider contacts
      } else if (res.status === 409) {
        alert('Contact already exists');
      } else {
        const errorData = await res.json().catch(() => ({}));
        alert('Failed to save contact: ' + (errorData.detail || 'Unknown error'));
      }
    } catch (error) {
      console.error('Error saving contact:', error);
      alert('Error connecting to server.');
    } finally {
      submitBtn.textContent = originalText;
      submitBtn.disabled = false;
    }
  });

  // Logout
  logoutBtn.addEventListener('click', () => {
    localStorage.removeItem('token');
    window.location.href = 'login.html';
  });

  // Initialize App
  fetchChats();

});