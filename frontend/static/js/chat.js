document.addEventListener('DOMContentLoaded', () => {
  // 1. Core Setup & Authentication
  const token = localStorage.getItem('token');
  if (!token) {
    window.location.href = 'login.html';
    return;
  }


  const urlParams = new URLSearchParams(window.location.search);
  const roomId = urlParams.get('room_id');
  const contactName = urlParams.get('name');

  if (!roomId) {
    alert("Invalid Room ID");
    window.location.href = 'home.html';
    return;
  }

  // Set header title
  if (contactName) {
    document.getElementById('roomTitle').textContent = contactName;
  } else {
    document.getElementById('roomTitle').textContent = `Room: ${roomId.substring(0, 8)}...`;
  }

  // Parse JWT to find user ID for distinguishing sender/receiver
  let myUserId = null;
  try {
    const payload = JSON.parse(atob(token.split('.')[1]));
    myUserId = payload.sub || payload.id || payload.user_id || payload.owner_id || null;
  } catch (e) {
    console.warn("Could not parse JWT token for user ID");
  }

  // DOM Elements
  const chatBody = document.getElementById('chatBody');
  const msgInput = document.getElementById('msgInput');
  const sendBtn = document.getElementById('sendBtn');
  const mediaBtn = document.getElementById('mediaBtn');
  const mediaInput = document.getElementById('mediaInput');
  const loadingState = document.getElementById('loadingState');

  let currentMsgCount = 0;
  let isFetching = false;
  let isFirstLoad = true;



  // Helper 2: Scroll to Bottom
  function scrollToBottom() {
    chatBody.scrollTop = chatBody.scrollHeight;
  }

  // 2. Load History
  async function fetchHistory() {
    if (isFetching) return;
    isFetching = true;

    try {
      const res = await authFetch(`${BASE_URL}/messages/history/${roomId}`, { method: 'GET' });
      if (res.ok) {
        const data = await res.json();
        // Priority to 'Chat', then standard fallback arrays
        const messages = Array.isArray(data) ? data : (data.Chat || data.messages || data.data || []);
        renderMessages(messages);
      }
    } catch (error) {
      console.error("Error fetching history:", error);
    } finally {
      isFetching = false;
      if (isFirstLoad) {
        if (loadingState) loadingState.style.display = 'none';
        isFirstLoad = false;
      }
    }
  }

  function renderMessages(messages) {
    // If no messages at all
    if (messages.length === 0 && currentMsgCount === 0) {
      if (loadingState) loadingState.style.display = 'none';
      if (!document.querySelector('.empty-chat')) {
        const emptyDiv = document.createElement('div');
        emptyDiv.className = 'empty-chat';
        emptyDiv.textContent = 'No messages yet. Start the conversation!';
        chatBody.appendChild(emptyDiv);
      }
      return;
    }

    // Optimization: Only process new messages
    if (messages.length === currentMsgCount) return;

    // Remove empty state message if it exists
    const emptyState = document.querySelector('.empty-chat');
    if (emptyState) emptyState.remove();
    if (loadingState) loadingState.style.display = 'none';

    // Append only NEW messages to avoid full re-render
    const newMessages = messages.slice(currentMsgCount);

    newMessages.forEach((msg, index) => {
      const isDeleted = msg.is_deleted === true;
      const senderId = msg.sender_id || msg.user_id;

      let isMine = false;
      if (msg.is_mine !== undefined) {
        isMine = msg.is_mine;
      } else if (myUserId && senderId) {
        isMine = String(senderId) === String(myUserId);
      }

      const bubble = document.createElement('div');
      bubble.className = `bubble ${isMine ? 'msg-right' : 'msg-left'}`;
      bubble.dataset.id = msg._id || msg.id;

      // Small animation stagger for smooth entry
      bubble.style.animationDelay = `${Math.min(index * 0.05, 0.3)}s`;

      // Context Menu Event
      bubble.oncontextmenu = (e) => {
        e.preventDefault();
        selectedMsgId = msg._id || msg.id;

        if (isMine) {
          document.getElementById('ctxEdit').style.display = 'flex';
          document.getElementById('ctxDelete').style.display = 'flex';
        } else {
          document.getElementById('ctxEdit').style.display = 'none';
          document.getElementById('ctxDelete').style.display = 'none';
        }

        // Display to calculate space
        msgContextMenu.style.display = 'flex';
        msgContextMenu.style.visibility = 'hidden';

        const menuWidth = 180;
        const menuHeight = isMine ? 210 : 130;

        let x = e.pageX;
        let y = e.pageY;

        if (x + menuWidth > window.innerWidth) x = window.innerWidth - menuWidth - 10;
        if (y + menuHeight > window.innerHeight) y = window.innerHeight - menuHeight - 10;

        msgContextMenu.style.visibility = 'visible';
        msgContextMenu.style.left = `${x}px`;
        msgContextMenu.style.top = `${y}px`;
        msgContextMenu.classList.add('active');
      };

      if (isDeleted) {
        bubble.classList.add('msg-deleted');
        bubble.innerHTML = `<span>This message was deleted</span>`;
      } else {
        const content = msg.content || '';

        if (content.startsWith('http://') || content.startsWith('https://')) {
          try {
            const urlObj = new URL(content);
            const pathname = urlObj.pathname.toLowerCase();

            if (pathname.match(/\.(jpeg|jpg|gif|png|webp)$/i)) {
              const img = document.createElement('img');
              img.src = content;
              img.alt = "Image";
              img.onload = scrollToBottom;
              bubble.appendChild(img);
            }
            else if (pathname.match(/\.(mp4|webm|mov)$/i)) {
              const video = document.createElement('video');
              video.src = content;
              video.controls = true;
              video.style.maxWidth = '100%';
              video.style.borderRadius = '8px';
              video.onloadeddata = scrollToBottom;
              bubble.appendChild(video);
            }
            else if (pathname.match(/\.(mp3|wav|ogg)$/i)) {
              const audio = document.createElement('audio');
              audio.src = content;
              audio.controls = true;
              audio.style.maxWidth = '100%';
              bubble.appendChild(audio);
            }
            else if (pathname.match(/\.(pdf|doc|docx|txt|csv)$/i)) {
              const a = document.createElement('a');
              a.href = content;
              a.target = "_blank";
              a.style.color = "#FFC700";
              a.style.textDecoration = "underline";
              a.textContent = "📄 View Document";
              bubble.appendChild(a);
            }
            else {
              const a = document.createElement('a');
              a.href = content;
              a.target = "_blank";
              a.style.color = "#FFC700";
              a.style.textDecoration = "underline";
              a.textContent = content;
              a.style.wordBreak = "break-all";
              bubble.appendChild(a);
            }
          } catch (e) {
            const textSpan = document.createElement('span');
            textSpan.textContent = content;
            bubble.appendChild(textSpan);
          }
        } else {
          const textSpan = document.createElement('span');
          textSpan.textContent = content;
          bubble.appendChild(textSpan);
        }
      }

      // Time formatter
      if (msg.timestamp || msg.created_at) {
        const date = new Date(msg.timestamp || msg.created_at);
        if (!isNaN(date)) {
          const timeSpan = document.createElement('div');
          timeSpan.className = 'bubble-time';

          let statusHtml = '';
          if (isMine && !isDeleted) {
            const status = msg.status || 'sent';
            if (status === 'seen') {
              statusHtml = '<span class="msg-status seen-status" style="margin-left:5px; color:#4facfe;">✓✓</span>';
            } else if (status === 'delivered') {
              statusHtml = '<span class="msg-status delivered-status" style="margin-left:5px; opacity:0.7;">✓✓</span>';
            } else {
              statusHtml = '<span class="msg-status" style="margin-left:5px; opacity:0.7;">✓</span>';
            }
          }

          timeSpan.innerHTML = date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) + statusHtml;
          bubble.appendChild(timeSpan);
        }
      }

      chatBody.appendChild(bubble);
    });

    scrollToBottom();
    currentMsgCount = messages.length;
  }

  // Helper 3: Determine Message Type
  function getMessageType(content) {
    const text = content.toLowerCase();

    // 1. Location check
    if (text.includes('google.com/maps') || text.match(/lat.*lng/i) || text.match(/latitude.*longitude/i)) {
      return 'location';
    }

    // 2. Extension mapping for URLs
    if (text.startsWith('http://') || text.startsWith('https://')) {
      try {
        const urlObj = new URL(content);
        const pathname = urlObj.pathname.toLowerCase();

        const imageExts = ['.jpg', '.jpeg', '.png', '.gif', '.webp'];
        const videoExts = ['.mp4', '.mov', '.webm', '.avi'];
        const audioExts = ['.mp3', '.wav', '.ogg', '.m4a'];
        const docExts = ['.pdf', '.doc', '.docx', '.xls', '.txt'];

        if (imageExts.some(ext => pathname.endsWith(ext))) return 'image';
        if (videoExts.some(ext => pathname.endsWith(ext))) return 'video';
        if (audioExts.some(ext => pathname.endsWith(ext))) return 'audio';
        if (docExts.some(ext => pathname.endsWith(ext))) return 'doc';

      } catch (e) {
        // Ignore URL parsing errors
      }
    }

    // 3. Fallback
    return 'text';
  }

  // 3. Sending Logic
  async function sendMessage(content) {
    if (!content.trim()) return;

    const originalText = msgInput.value;
    msgInput.value = '';
    sendBtn.disabled = true;

    // Use robust helper function
    const typeOfMsg = getMessageType(content);

    try {
      if (window.ws && window.ws.readyState === WebSocket.OPEN) {
        window.ws.send(JSON.stringify({ message_type: typeOfMsg, content: content }));
      } else {
        const res = await authFetch(`${BASE_URL}/messages/send/${roomId}`, {
          method: 'POST',
          body: JSON.stringify({ message_type: typeOfMsg, content: content })
        });
        if (res.ok) await fetchHistory();
        else {
          msgInput.value = originalText;
          alert("Failed to send message.");
        }
      }
    } catch (err) {
      console.error(err);
      msgInput.value = originalText;
    } finally {
      checkInput();
      msgInput.focus();
    }
  }

  // Send via Button
  sendBtn.addEventListener('click', () => {
    sendMessage(msgInput.value);
  });

  // Send via Enter Key
  msgInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter' && !sendBtn.disabled) {
      sendMessage(msgInput.value);
    }
  });

  // Toggle Send Button State
  function checkInput() {
    sendBtn.disabled = msgInput.value.trim().length === 0;
  }
  msgInput.addEventListener('input', checkInput);

  // 4. Media Integration & Attachment Menu
  const attachMenu = document.getElementById('attachMenu');

  mediaBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    attachMenu.classList.toggle('active');
  });

  document.addEventListener('click', (e) => {
    if (!attachMenu.contains(e.target) && e.target !== mediaBtn) {
      attachMenu.classList.remove('active');
    }
  });

  const attachItems = document.querySelectorAll('.attach-item');
  attachItems.forEach(item => {
    item.addEventListener('click', (e) => {
      e.stopPropagation();
      attachMenu.classList.remove('active');
      const type = item.getAttribute('data-type');

      if (type === 'photo') {
        mediaInput.removeAttribute('capture');
        mediaInput.accept = 'image/*,video/*';
        mediaInput.click();
      } else if (type === 'camera') {
        mediaInput.accept = 'image/*,video/*';
        mediaInput.setAttribute('capture', 'environment');
        mediaInput.click();
      } else if (type === 'document') {
        mediaInput.removeAttribute('capture');
        mediaInput.accept = '.pdf,.doc,.docx,.txt';
        mediaInput.click();
      } else if (type === 'audio') {
        mediaInput.removeAttribute('capture');
        mediaInput.accept = 'audio/*';
        mediaInput.click();
      } else if (type === 'contact' || type === 'poll') {
        alert('Feature coming soon in Alpha Update!');
      }
    });
  });

  mediaInput.addEventListener('change', async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Show loading state on media button
    mediaBtn.style.opacity = '0.5';
    mediaBtn.style.pointerEvents = 'none';

    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await authFetch(`${BASE_URL}/media/upload`, {
        method: 'POST',
        body: formData
      });

      if (res.ok) {
        const data = await res.json();
        const url = data.url || data.file_url || data.media_url;
        if (url) {
          // Send the URL as a message immediately
          await sendMessage(url);
        } else {
          alert('Upload succeeded but no URL returned from backend.');
        }
      } else {
        alert('Media upload failed.');
      }
    } catch (err) {
      console.error(err);
      alert('Error uploading media. Check console.');
    } finally {
      mediaBtn.style.opacity = '1';
      mediaBtn.style.pointerEvents = 'auto';
      mediaInput.value = ''; // Reset file input
    }
  });

  // 5. Start App & WebSockets
  fetchHistory();

  function connectWebSocket() {
    const token = localStorage.getItem('token');
    if (!token) return;

    window.ws = new WebSocket(`${WS_URL}/ws/chat/${roomId}?token=${token}`);

    window.ws.onopen = () => {
      console.log('WebSocket Connected to room', roomId);
    };

    window.ws.onmessage = (event) => {
      console.log('WebSocket Msg:', event.data);
      try {
        const payload = JSON.parse(event.data);
        if (payload.event === 'MESSAGE_EDITED') {
          const bubble = document.querySelector(`.bubble[data-id="${payload.message_id}"]`);
          if (bubble && !bubble.classList.contains('msg-deleted')) {
            const spans = bubble.querySelectorAll('span');
            if (spans.length > 0) {
              spans[0].textContent = payload.new_content;
              let editedTag = bubble.querySelector('.edited-tag');
              if (!editedTag) {
                editedTag = document.createElement('small');
                editedTag.className = 'edited-tag';
                editedTag.style.fontSize = '10px';
                editedTag.style.opacity = '0.6';
                editedTag.style.marginLeft = '6px';
                editedTag.textContent = '(edited)';
                bubble.appendChild(editedTag);
              }
            }
          }
          return; // Prevent full re-fetch for just an edit
        }

        if (payload.event === 'MESSAGE_DELETED') {
          const bubble = document.querySelector(`.bubble[data-id="${payload.message_id}"]`);
          if (bubble) {
            bubble.remove();
          }
          return; // Prevent full re-fetch for just a delete
        }

        if (payload.event === 'STATUS_UPDATE') {
          if (payload.message_ids && Array.isArray(payload.message_ids)) {
            payload.message_ids.forEach(id => {
              const bubble = document.querySelector(`.bubble[data-id="${id}"]`);
              if (bubble) {
                const statusSpan = bubble.querySelector('.msg-status');
                if (statusSpan) {
                  if (payload.new_status === 'seen') {
                    statusSpan.textContent = '✓✓';
                    statusSpan.style.color = '#4facfe'; // Blue ticks
                    statusSpan.classList.add('seen-status');
                    statusSpan.classList.remove('delivered-status');
                    statusSpan.style.opacity = '1';
                  } else if (payload.new_status === 'delivered' && !statusSpan.classList.contains('seen-status')) {
                    statusSpan.textContent = '✓✓';
                    statusSpan.style.color = 'inherit';
                    statusSpan.classList.add('delivered-status');
                    statusSpan.style.opacity = '0.7';
                  }
                }
              }
            });
          }
          return;
        }
        if (payload.event === 'new_message' || payload.event === 'new_message_sent') {
            if (payload.room_id && payload.room_id !== roomId) {
                authFetch(`${BASE_URL}/messages/mark_delivered`, { method: 'PUT' });
            } else {
                fetchHistory();
            }
        }

      } catch (e) {
        console.error("WS Parse Error:", e);
      }
    };

    window.ws.onclose = () => {
      console.log('WebSocket Disconnected. Reconnecting in 3s...');
      setTimeout(connectWebSocket, 3000);
    };
  }

  connectWebSocket();

  // 6. Context Menu Logic
  let selectedMsgId = null;
  const msgContextMenu = document.getElementById('msgContextMenu');

  document.addEventListener('click', (e) => {
    if (msgContextMenu && !msgContextMenu.contains(e.target)) {
      msgContextMenu.classList.remove('active');
      msgContextMenu.style.display = 'none';
    }
  });

  const ctxItems = document.querySelectorAll('.ctx-item');
  ctxItems.forEach(item => {
    item.addEventListener('click', async () => {
      const action = item.getAttribute('data-action');
      msgContextMenu.classList.remove('active');
      msgContextMenu.style.display = 'none';

      if (!selectedMsgId) return;

      try {
        switch (action) {
          case 'delete':
            await authFetch(`${BASE_URL}/messages/delete/${selectedMsgId}`, { method: 'DELETE' });
            break;
          case 'edit':
            const newText = prompt('Enter new message text:');
            if (newText && newText.trim() !== '') {
              await authFetch(`${BASE_URL}/messages/edit/${selectedMsgId}`, {
                method: 'PATCH',
                body: JSON.stringify({ content: newText.trim() })
              });
            }
            break;
          case 'pin':
            await authFetch(`${BASE_URL}/messages/pin/${selectedMsgId}`, { method: 'PATCH' });
            break;
          case 'forward':
            alert('Forward logic: Select a room first!');
            break;
          case 'reply':
            console.log("Reply action triggered for:", selectedMsgId);
            break;
        }
        // Update UI immediately after API hit
        fetchHistory();
      } catch (err) {
        console.error("Context menu action failed:", err);
      }
    });
  });

});