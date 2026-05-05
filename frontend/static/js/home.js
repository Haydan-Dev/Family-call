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

  // Layer 4
  const archivedSlider = document.getElementById('archivedSlider');
  const closeArchivedSliderBtn = document.getElementById('closeArchivedSliderBtn');
  const archivedLoading = document.getElementById('archivedLoading');
  const archivedEmpty = document.getElementById('archivedEmpty');
  const archivedList = document.getElementById('archivedList');

  // Context Menu Setup
  const roomContextMenu = document.getElementById('roomContextMenu');
  let selectedRoomId = null;
  let unreadArchivedCount = 0; // Tracks aggregate unread count for archived chats

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
      if (action === 'pin' || action === 'unpin') {
          await authFetch(`${BASE_URL}/conversations/pin/${selectedRoomId}`, { method: 'PATCH' });
        } else if (action === 'archive' || action === 'unarchive') {
          // Optimistic UI Update: Instantly hide the card
          const cards = document.querySelectorAll(`.card-item[data-room-id="${selectedRoomId}"]`);
          cards.forEach(c => c.style.display = 'none');

          // The backend /archive endpoint automatically toggles between archive and unarchive
          await authFetch(`${BASE_URL}/conversations/archive/${selectedRoomId}`, { method: 'PATCH' });
        } else if (action === 'rename') {
          // Pre-fill modal with current name and open it
          const card = document.querySelector(`.card-item[data-room-id="${selectedRoomId}"]`);
          const currentName = card?.querySelector('.name-text')?.firstChild?.textContent?.trim() || '';
          const renameInput = document.getElementById('renameInput');
          const renameModal = document.getElementById('renameModal');
          if (renameInput) renameInput.value = currentName;
          if (renameModal) renameModal.classList.add('active');
          setTimeout(() => renameInput?.focus(), 150); // Wait for transition
          return; // Modal buttons handle the rest
        } else if (action === 'block') {
          // Open custom glassmorphic block confirmation modal
          const blockModal = document.getElementById('blockModal');
          if (blockModal) blockModal.classList.add('active');
          return;
        } else if (action === 'unblock') {
          // Immediately flip DOM state — no modal needed for unblock
          const card = document.querySelector(`.card-item[data-room-id="${selectedRoomId}"]`);
          if (card) card.dataset.isBlocked = 'false';
          try {
            await authFetch(`${BASE_URL}/contacts/unblock/${selectedRoomId}`, { method: 'POST' });
          } catch (err) {
            // Rollback DOM on failure
            if (card) card.dataset.isBlocked = 'true';
            console.error('Unblock API failed:', err);
          }
          return;
        } else if (action === 'delete') {
          if (confirm('Delete this chat permanently?')) {
            const cards = document.querySelectorAll(`.card-item[data-room-id="${selectedRoomId}"]`);
            cards.forEach(c => c.style.display = 'none');
            await authFetch(`${BASE_URL}/conversations/delete_conversations/${selectedRoomId}`, { method: 'DELETE' });
          }
        }
        fetchChats(true); // Silent refresh
        if (archivedSlider && archivedSlider.classList.contains('active')) {
          fetchArchivedChats(true);
        }
      } catch (err) {
        console.error(err);
        alert('Action failed');
      }
    });
  });

  // ── RENAME MODAL LOGIC ───────────────────────────────────────────────────
  const renameModal  = document.getElementById('renameModal');
  const renameInput  = document.getElementById('renameInput');
  const saveRenameBtn   = document.getElementById('saveRenameBtn');
  const cancelRenameBtn = document.getElementById('cancelRenameBtn');

  function closeRenameModal() {
    if (renameModal) renameModal.classList.remove('active');
  }

  // Cancel button & backdrop click both close without saving
  if (cancelRenameBtn) cancelRenameBtn.addEventListener('click', closeRenameModal);
  if (renameModal) {
    renameModal.addEventListener('click', (e) => {
      if (e.target === renameModal) closeRenameModal();
    });
  }

  // Enter key inside input triggers save
  if (renameInput) {
    renameInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') saveRenameBtn?.click();
    });
  }

  if (saveRenameBtn) {
    saveRenameBtn.addEventListener('click', async () => {
      const newName = renameInput?.value?.trim();
      if (!newName || !selectedRoomId) { closeRenameModal(); return; }

      // Optimistic DOM update — name updates instantly
      const card = document.querySelector(`.card-item[data-room-id="${selectedRoomId}"]`);
      const oldName = card?.querySelector('.name-text')?.firstChild?.textContent?.trim() || '';
      if (card) {
        const nameEl = card.querySelector('.name-text');
        if (nameEl && nameEl.firstChild) nameEl.firstChild.textContent = newName + ' ';
      }

      closeRenameModal();

      // Persist to backend — /contacts/rename/{room_id}
      try {
        const res = await authFetch(`${BASE_URL}/contacts/rename/${selectedRoomId}`, {
          method: 'PATCH',
          body: JSON.stringify({ name: newName })
        });
        if (res.ok) {
          console.log('Rename API: 200 OK — persisted for room', selectedRoomId);
        } else {
          const err = await res.json().catch(() => ({}));
          console.error('Rename API failed:', res.status, err);
          alert('Rename failed: ' + (err.detail || `HTTP ${res.status}`));
          // Rollback optimistic update
          if (card) {
            const nameEl = card.querySelector('.name-text');
            if (nameEl && nameEl.firstChild) nameEl.firstChild.textContent = oldName + ' ';
          }
        }
      } catch (err) {
        console.error('Rename API network error:', err);
        alert('Rename failed — network error.');
      }
    });
  }

  // ── BLOCK MODAL LOGIC ────────────────────────────────────────────────────
  const blockModal      = document.getElementById('blockModal');
  const cancelBlockBtn  = document.getElementById('cancelBlockBtn');
  const confirmBlockBtn = document.getElementById('confirmBlockBtn');

  function closeBlockModal() {
    if (blockModal) blockModal.classList.remove('active');
  }

  // Cancel + backdrop close
  if (cancelBlockBtn) cancelBlockBtn.addEventListener('click', closeBlockModal);
  if (blockModal) {
    blockModal.addEventListener('click', (e) => {
      if (e.target === blockModal) closeBlockModal();
    });
  }

  if (confirmBlockBtn) {
    confirmBlockBtn.addEventListener('click', async () => {
      closeBlockModal();

      // Optimistic: stamp blocked state immediately so toggle is correct on re-open
      const card = document.querySelector(`.card-item[data-room-id="${selectedRoomId}"]`);
      if (card) card.dataset.isBlocked = 'true';

      // Instant DOM removal
      const cards = document.querySelectorAll(`.card-item[data-room-id="${selectedRoomId}"]`);
      cards.forEach(c => c.remove());

      // Real API call — persists to MongoDB via FastAPI
      try {
        await authFetch(`${BASE_URL}/contacts/block/${selectedRoomId}`, { method: 'POST' });
      } catch (err) {
        console.error('Block API failed:', err);
        // Silent fail — card is already removed from DOM, refresh will restore if backend rejected
      }
    });
  }

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
  async function fetchChats(silent = false) {
    if (!silent) showState(chatsLoading, [chatsEmpty, chatsList]);
    try {
      const res = await authFetch(`${BASE_URL}/conversations/display_conversations`, { method: 'GET' });
      const data = await res.json();

      if (data.total_archived_unread !== undefined) {
        unreadArchivedCount = data.total_archived_unread;
      }

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

  function renderChats(chats, isArchivedView = false) {
    const listEl = isArchivedView ? archivedList : chatsList;
    listEl.innerHTML = '';

    if (!isArchivedView) {
      const archivedBtn = document.createElement('div');
      archivedBtn.className = 'card-item';
      archivedBtn.style.background = 'rgba(255, 255, 255, 0.05)';
      archivedBtn.innerHTML = `
        <div class="avatar" style="background: transparent; color: #fff;">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" width="24" height="24"><path d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"></path></svg>
        </div>
        <div class="info" style="flex:1; display:flex; align-items:center;">
          <div class="name-text">Archived</div>
        </div>
        ${unreadArchivedCount > 0 ? `<div class="unread-badge" style="background: #ff9800; color: white; border-radius: 50%; padding: 2px 6px; font-size: 12px; font-weight: bold; margin-left: auto;">${unreadArchivedCount}</div>` : ''}
      `;
      archivedBtn.addEventListener('click', () => {
        archivedSlider.classList.add('active');
        fetchArchivedChats();
      });
      listEl.appendChild(archivedBtn);
    }

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

      let unreadBadge = chat.unread_count > 0 ? `<div class="unread-badge" style="background: red; color: white; border-radius: 50%; padding: 2px 6px; font-size: 12px; font-weight: bold; margin-left: auto;">${chat.unread_count}</div>` : '';
      const card = document.createElement('div');
      card.className = 'card-item';
      card.dataset.roomId = roomId;
      card.dataset.isPinned = chat.is_pinned ? 'true' : 'false';
      card.dataset.isBlocked = chat.is_blocked ? 'true' : 'false'; // persist block state
      card.style.animationDelay = `${index * 0.05}s`;
      card.innerHTML = `
        <div class="avatar">${initial}</div>
        <div class="info" style="flex:1;">
          <div class="name-text">${name} ${badges}</div>
          <div class="sub-text">${chat.last_message || 'Tap to chat'}</div>
        </div>
        ${unreadBadge}
      `;
      card.addEventListener('click', () => {
        window.location.href = `chat.html?room_id=${roomId}&name=${encodeURIComponent(name)}`;
      });

      // Long press / right click logic
      card.addEventListener('contextmenu', (e) => {
        e.preventDefault();
        selectedRoomId = roomId;

        // Dynamically update Pin/Unpin action
        const pinItem = roomContextMenu.querySelector('.ctx-item[data-action="pin"], .ctx-item[data-action="unpin"]');
        const isPinned = card.dataset.isPinned === 'true';
        if (pinItem) {
          pinItem.setAttribute('data-action', isPinned ? 'unpin' : 'pin');
          pinItem.querySelector('span').textContent = isPinned ? 'Unpin' : 'Pin';
        }

        // Dynamically update context menu action
        const archiveItem = roomContextMenu.querySelector('.ctx-item[data-action="archive"], .ctx-item[data-action="unarchive"]');
        if (archiveItem) {
          archiveItem.setAttribute('data-action', isArchivedView ? 'unarchive' : 'archive');
          archiveItem.querySelector('span').textContent = isArchivedView ? 'Unarchive' : 'Archive';
        }

        // Dynamically toggle Block / Unblock based on card's current state
        const isBlocked = card.dataset.isBlocked === 'true';
        const ctxBlockItem   = document.getElementById('ctxBlockItem');
        const ctxUnblockItem = document.getElementById('ctxUnblockItem');
        if (ctxBlockItem)   ctxBlockItem.style.display   = isBlocked ? 'none' : 'flex';
        if (ctxUnblockItem) ctxUnblockItem.style.display = isBlocked ? 'flex' : 'none';

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

          // Dynamically update Pin/Unpin action
          const pinItem = roomContextMenu.querySelector('.ctx-item[data-action="pin"], .ctx-item[data-action="unpin"]');
          const isPinned = card.dataset.isPinned === 'true';
          if (pinItem) {
            pinItem.setAttribute('data-action', isPinned ? 'unpin' : 'pin');
            pinItem.querySelector('span').textContent = isPinned ? 'Unpin' : 'Pin';
          }

          // Dynamically update context menu action
          const archiveItem = roomContextMenu.querySelector('.ctx-item[data-action="archive"], .ctx-item[data-action="unarchive"]');
          if (archiveItem) {
            archiveItem.setAttribute('data-action', isArchivedView ? 'unarchive' : 'archive');
            archiveItem.querySelector('span').textContent = isArchivedView ? 'Unarchive' : 'Archive';
          }

          // Dynamically toggle Block / Unblock based on card's current state
          const isBlocked = card.dataset.isBlocked === 'true';
          const ctxBlockItem   = document.getElementById('ctxBlockItem');
          const ctxUnblockItem = document.getElementById('ctxUnblockItem');
          if (ctxBlockItem)   ctxBlockItem.style.display   = isBlocked ? 'none' : 'flex';
          if (ctxUnblockItem) ctxUnblockItem.style.display = isBlocked ? 'flex' : 'none';

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

      listEl.appendChild(card);
    });
  }

  async function fetchArchivedChats(silent = false) {
    if (!silent) showState(archivedLoading, [archivedEmpty, archivedList]);
    try {
      const res = await authFetch(`${BASE_URL}/conversations/archived_conversations`, { method: 'GET' });
      const data = await res.json();
      let chats = Array.isArray(data) ? data : (data.data || []);

      if (chats.length === 0) {
        showState(archivedEmpty, [archivedLoading, archivedList]);
      } else {
        renderChats(chats, true);
        showState(archivedList, [archivedLoading, archivedEmpty]);
      }
    } catch (error) {
      console.error('Error fetching archived chats:', error);
      showState(archivedEmpty, [archivedLoading, archivedList]);
      if (archivedEmpty.querySelector('p')) archivedEmpty.querySelector('p').textContent = "Failed to load archived chats.";
    }
  }

  if (closeArchivedSliderBtn) {
    closeArchivedSliderBtn.addEventListener('click', () => {
      archivedSlider.classList.remove('active');
      fetchChats();
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

  // Mark all incoming messages as delivered globally on app load
  authFetch(`${BASE_URL}/messages/mark_delivered`, { method: 'PUT' })
    .catch(err => console.error('Error marking messages as delivered:', err));

  // Global listener for socket events to update unread badge without refresh
  function connectGlobalWebSocket() {
    const token = localStorage.getItem('token');
    if (!token) return;

    window.ws = new WebSocket(`${WS_URL}/ws/global?token=${token}`);

    window.ws.onopen = () => {
      console.log('Global WebSocket Connected');
    };

    window.ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        if (payload.event === 'STATUS_UPDATE' && payload.new_status === 'seen' && payload.room_id) {
          const card = document.querySelector(`.card-item[data-room-id="${payload.room_id}"]`);
          if (card) {
            const badge = card.querySelector('.unread-badge');
            if (badge) badge.remove();
          }
        }

        if (payload.event === 'new_message') {
          // Instantly acknowledge delivery and update UI
          authFetch(`${BASE_URL}/messages/mark_delivered`, { method: 'PUT' });

          const archivedCard = document.querySelector(`#archivedList .card-item[data-room-id="${payload.room_id}"]`);
          const activeCard = document.querySelector(`#chatsList .card-item[data-room-id="${payload.room_id}"]`);

          if (archivedCard) {
            // It's loaded in the slider, bump the badge via DOM
            let badge = archivedCard.querySelector('.unread-badge');
            if (!badge) {
              badge = document.createElement('div');
              badge.className = 'unread-badge';
              badge.style.cssText = 'background: red; color: white; border-radius: 50%; padding: 2px 6px; font-size: 12px; font-weight: bold; margin-left: auto;';
              badge.textContent = '0';
              archivedCard.appendChild(badge);
            }
            badge.textContent = parseInt(badge.textContent) + 1;
            archivedList.prepend(archivedCard); // bump to top

            unreadArchivedCount++;
            updateArchivedBadgeDOM();
            return; // Zero API call execution for loaded archived chats!
          } else if (!activeCard) {
            // It's not loaded in archived, and not active. 
            // We assume it's an unloaded archived chat (or new).
            // Increment aggregate and purely update DOM.
            unreadArchivedCount++;
            updateArchivedBadgeDOM();
          }

          fetchChats(true); // Refresh main list for active chat updates
        }
      } catch (e) { }
    };

    function updateArchivedBadgeDOM() {
      const archivedBtn = document.querySelector('#chatsList .card-item'); // It's always the first item if rendered
      if (archivedBtn && archivedBtn.querySelector('.name-text') && archivedBtn.querySelector('.name-text').textContent.includes('Archived')) {
        let badge = archivedBtn.querySelector('.unread-badge');
        if (unreadArchivedCount > 0) {
          if (!badge) {
            badge = document.createElement('div');
            badge.className = 'unread-badge';
            badge.style.cssText = 'background: #ff9800; color: white; border-radius: 50%; padding: 2px 6px; font-size: 12px; font-weight: bold; margin-left: auto;';
            archivedBtn.appendChild(badge);
          }
          badge.textContent = unreadArchivedCount;
        } else if (badge) {
          badge.remove();
        }
      }
    }

    window.ws.onclose = () => {
      console.log('Global WS Disconnected. Reconnecting...');
      setTimeout(connectGlobalWebSocket, 3000);
    };
  }

  connectGlobalWebSocket();

});