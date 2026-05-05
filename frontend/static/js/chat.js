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

  // --- STRANGER DANGER BANNER LOGIC ---
  const strangerBanner = document.getElementById('strangerBanner');
  const isContact      = urlParams.get('is_contact') === 'true';
  const otherEmail     = urlParams.get('email');

  if (strangerBanner && !isContact && roomId && roomId !== 'global') {
    strangerBanner.classList.remove('hidden');
    const infoSpan = strangerBanner.querySelector('.stranger-info span');
    if (infoSpan && otherEmail && otherEmail !== 'Unknown') {
      infoSpan.textContent = `Unknown: ${otherEmail}`;
    }
  }

  const addContactBtn    = document.getElementById('addContactBtn');
  const blockStrangerBtn = document.getElementById('blockStrangerBtn');
  const reportSpamBtn    = document.getElementById('reportSpamBtn');

  if (addContactBtn) {
    addContactBtn.addEventListener('click', async () => {
      try {
        const res = await authFetch(`${BASE_URL}/contacts/save`, {
          method: 'POST',
          body: JSON.stringify({ 
            contact_email: otherEmail, 
            contact_nickname: otherEmail.split('@')[0] 
          })
        });
        if (res.ok) {
          showToast("Contact Added!");
          strangerBanner.classList.add('hidden');
        } else {
          showToast("Failed to add contact");
        }
      } catch (err) {
        console.error("Add contact failed", err);
      }
    });
  }

  if (blockStrangerBtn) {
    blockStrangerBtn.addEventListener('click', async () => {
      if (confirm("Block this sender? They won't be able to message you.")) {
        try {
          const res = await authFetch(`${BASE_URL}/contacts/block/${roomId}`, { method: 'POST' });
          if (res.ok) {
            showToast("User Blocked");
            setTimeout(() => window.location.href = 'home.html', 1000);
          }
        } catch (err) {
          console.error("Block failed", err);
        }
      }
    });
  }

  if (reportSpamBtn) {
    reportSpamBtn.addEventListener('click', () => {
      showToast("Reported as Spam");
      strangerBanner.classList.add('hidden');
    });
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
  let replyingToMsgId = null;
  let currentMediaUrl = null; // Set when context menu opens on a media bubble

  // Utility: Show Custom Toast
  function showToast(message) {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = 'toast-notification';
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
      if (toast.parentElement) toast.remove();
    }, 2000);
  }

  // Setup Reply Banner Close
  const replyBanner = document.getElementById('replyBanner');
  const closeReplyBtn = document.getElementById('closeReplyBtn');
  if (closeReplyBtn) {
    closeReplyBtn.addEventListener('click', () => {
      replyingToMsgId = null;
      replyBanner.classList.add('hidden');
    });
  }



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
    // 1. Pinned Banner Logic
    const pinnedBanner = document.getElementById('pinnedMessageBanner');
    const pinnedText = document.getElementById('pinnedBannerText');
    const pinnedMessage = messages.find(m => m.is_pinned === true);

    if (pinnedBanner && pinnedText) {
      if (pinnedMessage) {
        pinnedText.textContent = pinnedMessage.content || "Pinned message";
        pinnedBanner.classList.remove('hidden');
      } else {
        pinnedBanner.classList.add('hidden');
      }
    }

    if (messages.length === 0 && chatBody.querySelectorAll('.bubble').length === 0) {
      if (loadingState) loadingState.style.display = 'none';
      if (!document.querySelector('.empty-chat')) {
        const emptyDiv = document.createElement('div');
        emptyDiv.className = 'empty-chat';
        emptyDiv.textContent = 'No messages yet. Start the conversation!';
        chatBody.appendChild(emptyDiv);
      }
      return;
    }

    const emptyState = document.querySelector('.empty-chat');
    if (emptyState) emptyState.remove();
    if (loadingState) loadingState.style.display = 'none';

    let addedNew = false;

    messages.forEach((msg, index) => {
      const msgId = msg._id || msg.id;
      if (document.querySelector(`.bubble[data-id="${msgId}"]`)) return;

      addedNew = true;
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

      if (msg.is_pinned) {
        const pinIndicator = document.createElement('div');
        pinIndicator.textContent = '📌';
        pinIndicator.style.fontSize = '12px';
        pinIndicator.style.position = 'absolute';
        pinIndicator.style.top = '-8px';
        pinIndicator.style.right = '-8px';
        bubble.appendChild(pinIndicator);
        bubble.style.position = 'relative';
        bubble.dataset.isPinned = "true";
      } else {
        bubble.dataset.isPinned = "false";
      }

      // Add Forwarded Tag
      if (msg.is_forwarded) {
        const fwdTag = document.createElement('div');
        fwdTag.className = 'forwarded-tag';
        fwdTag.innerHTML = `<span>↪️</span> Forwarded`;
        bubble.appendChild(fwdTag);
      }

      // Add Quote Block if it's a reply
      if (msg.reply_to_message_id) {
        const originalMsg = messages.find(m => String(m._id || m.id) === String(msg.reply_to_message_id));
        let quoteText = 'Original message...';
        let quoteSender = 'Replying to';

        if (originalMsg) {
          quoteText = originalMsg.content || 'Media / Attachment';

          const origSenderId = originalMsg.sender_id || originalMsg.user_id;
          let origIsMine = false;
          if (originalMsg.is_mine !== undefined) origIsMine = originalMsg.is_mine;
          else if (myUserId && origSenderId) origIsMine = String(origSenderId) === String(myUserId);

          let roomTitle = document.getElementById('roomTitle').textContent;
          if (roomTitle.startsWith('Room:')) roomTitle = 'Contact';

          quoteSender = origIsMine ? 'You' : roomTitle;
        }

        // Build the reply quote block using DOM (safe, no innerHTML XSS risk)
        const qBlock = document.createElement('div');
        qBlock.className = 'reply-container';

        const titleEl = document.createElement('div');
        titleEl.className = 'quote-title';
        titleEl.textContent = quoteSender;

        const textEl = document.createElement('div');
        textEl.className = 'quote-text';
        textEl.textContent = quoteText; // CSS handles single-line truncation via ellipsis

        qBlock.appendChild(titleEl);
        qBlock.appendChild(textEl);

        // Step 4 — Click quote block to scroll to the original message with crimson flash
        qBlock.addEventListener('click', () => {
          const targetId = msg.reply_to_message_id;
          const targetBubble = document.querySelector(`.bubble[data-id="${targetId}"]`);
          if (targetBubble) {
            targetBubble.scrollIntoView({ behavior: 'smooth', block: 'center' });
            // Remove class first to re-trigger animation if already flashed
            targetBubble.classList.remove('highlight-flash');
            void targetBubble.offsetWidth; // Force reflow
            targetBubble.classList.add('highlight-flash');
            setTimeout(() => targetBubble.classList.remove('highlight-flash'), 1150);
          }
        });

        bubble.appendChild(qBlock);
      }

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

        // --- Detect media in this bubble → show/hide Download option ---
        currentMediaUrl = null;
        const ctxDownloadEl = document.getElementById('ctxDownload');
        if (ctxDownloadEl) {
          const mediaImg = bubble.querySelector('img[src]');
          const mediaVideo = bubble.querySelector('video[src]');
          const mediaAnchor = bubble.querySelector('a[href*="/uploads/"]');

          if (mediaImg) currentMediaUrl = mediaImg.src;
          else if (mediaVideo) currentMediaUrl = mediaVideo.src;
          else if (mediaAnchor) currentMediaUrl = mediaAnchor.href;

          ctxDownloadEl.style.display = currentMediaUrl ? 'flex' : 'none';
        }

        // Dynamically update Pin/Unpin
        const pinItem = msgContextMenu.querySelector('.ctx-item[data-action="pin"], .ctx-item[data-action="unpin"]');
        if (pinItem) {
          const isPinned = bubble.dataset.isPinned === "true";
          pinItem.setAttribute('data-action', isPinned ? 'unpin' : 'pin');
          pinItem.innerHTML = isPinned ?
            `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="2" y1="2" x2="22" y2="22"></line><line x1="12" y1="17" x2="12" y2="22"></line><path d="M5 17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 11.24V6a3 3 0 0 0-6 0v5.24a2 2 0 0 1-1.11 1.31l-1.78.9A2 2 0 0 0 5 15.24Z"></path></svg> Unpin` :
            `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="17" x2="12" y2="22"></line><path d="M5 17h14v-1.76a2 2 0 0 0-1.11-1.79l-1.78-.9A2 2 0 0 1 15 11.24V6a3 3 0 0 0-6 0v5.24a2 2 0 0 1-1.11 1.31l-1.78.9A2 2 0 0 0 5 15.24Z"></path></svg> Pin`;
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

      // Step 5 — Attach swipe-to-reply gesture
      attachSwipeToReply(bubble, msg, isMine);

      chatBody.appendChild(bubble);
    });

    if (addedNew) {
      scrollToBottom();
    }
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

    const payloadObj = {
      message_type: typeOfMsg,
      content: content
    };
    if (replyingToMsgId) {
      payloadObj.reply_to_message_id = replyingToMsgId;
    }

    try {
      if (window.ws && window.ws.readyState === WebSocket.OPEN) {
        window.ws.send(JSON.stringify(payloadObj));
      } else {
        const res = await authFetch(`${BASE_URL}/messages/send/${roomId}`, {
          method: 'POST',
          body: JSON.stringify(payloadObj)
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
      // Clear reply state after sending
      replyingToMsgId = null;
      if (replyBanner) replyBanner.classList.add('hidden');

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
            return; // zero-API handled by WS
          case 'edit':
            const editBubble = document.querySelector(`.bubble[data-id="${selectedMsgId}"]`);
            if (!editBubble) return;
            const textSpan = editBubble.querySelector('span:not(.message-time)');
            if (!textSpan) return;

            // Prevent multiple inline edits on the same bubble
            if (editBubble.querySelector('.inline-edit-container')) return;

            const originalTextContent = textSpan.textContent;
            textSpan.style.display = 'none';

            const editContainer = document.createElement('div');
            editContainer.className = 'inline-edit-container';
            editContainer.innerHTML = `
              <textarea class="inline-edit-input">${originalTextContent}</textarea>
              <div class="inline-edit-actions">
                <button class="inline-btn cancel">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 6L6 18M6 6l12 12"/></svg> Cancel
                </button>
                <button class="inline-btn save">
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20 6L9 17l-5-5"/></svg> Save
                </button>
              </div>
            `;
            editBubble.appendChild(editContainer);

            const textarea = editContainer.querySelector('.inline-edit-input');
            textarea.focus();
            // Move cursor to end
            textarea.selectionStart = textarea.value.length;

            const cancelBtn = editContainer.querySelector('.cancel');
            const saveBtn = editContainer.querySelector('.save');

            cancelBtn.onclick = (e) => {
              e.stopPropagation();
              editContainer.remove();
              textSpan.style.display = '';
            };

            saveBtn.onclick = async (e) => {
              e.stopPropagation();
              const newText = textarea.value.trim();
              if (newText && newText !== originalTextContent) {
                editContainer.remove();
                textSpan.style.display = '';
                // Optimistic local update (optional, but WS handles it if we just wait)
                textSpan.textContent = newText;
                await authFetch(`${BASE_URL}/messages/edit/${selectedMsgId}`, {
                  method: 'PATCH',
                  body: JSON.stringify({ content: newText })
                });
              } else {
                cancelBtn.click();
              }
            };
            return; // zero-API handled by WS
          case 'pin':
          case 'unpin':
            await authFetch(`${BASE_URL}/messages/pin/${selectedMsgId}`, { method: 'PATCH' });

            // Zero-API DOM Patch
            const msgBubble = document.querySelector(`.bubble[data-id="${selectedMsgId}"]`);
            const isNowPinned = action === 'pin';
            if (msgBubble) {
              msgBubble.dataset.isPinned = isNowPinned ? "true" : "false";
              if (isNowPinned) {
                // Update Banner
                const pinnedBanner = document.getElementById('pinnedMessageBanner');
                const pinnedText = document.getElementById('pinnedBannerText');
                if (pinnedBanner && pinnedText) {
                  let txt = "Pinned message";
                  const span = msgBubble.querySelector('span');
                  if (span) txt = span.textContent;
                  pinnedText.textContent = txt;
                  pinnedBanner.classList.remove('hidden');
                }

                // Unpin other bubbles locally
                document.querySelectorAll('.bubble[data-is-pinned="true"]').forEach(b => {
                  if (b !== msgBubble) {
                    b.dataset.isPinned = "false";
                    // Find and remove the pin emoji element
                    Array.from(b.children).forEach(child => {
                      if (child.textContent === '📌') child.remove();
                    });
                  }
                });

                // Add pin icon to this bubble
                const existingPin = Array.from(msgBubble.children).find(el => el.textContent === '📌');
                if (!existingPin) {
                  const pinIndicator = document.createElement('div');
                  pinIndicator.textContent = '📌';
                  pinIndicator.style.fontSize = '12px';
                  pinIndicator.style.position = 'absolute';
                  pinIndicator.style.top = '-8px';
                  pinIndicator.style.right = '-8px';
                  msgBubble.appendChild(pinIndicator);
                }
              } else {
                // Remove pin icon
                Array.from(msgBubble.children).forEach(child => {
                  if (child.textContent === '📌') child.remove();
                });

                // Hide Banner
                const pinnedBanner = document.getElementById('pinnedMessageBanner');
                if (pinnedBanner) pinnedBanner.classList.add('hidden');
              }
            }
            return; // zero-API handled locally
          case 'forward':
            const fwModal = document.getElementById('forwardModalOverlay');
            const fwList = document.getElementById('forwardList');
            const fwLoad = document.getElementById('forwardLoading');
            if (!fwModal) break;

            fwModal.classList.add('active');
            fwLoad.style.display = 'block';
            fwList.innerHTML = '';

            try {
              const res = await authFetch(`${BASE_URL}/conversations/display_conversations`, { method: 'GET' });
              const data = await res.json();
              let chats = Array.isArray(data) ? data : (data.data || []);
              fwLoad.style.display = 'none';

              if (chats.length === 0) {
                fwList.innerHTML = '<div style="text-align:center; padding:20px; color:#A0A0A0;">No recent chats.</div>';
              } else {
                chats.forEach(chat => {
                  const item = document.createElement('div');
                  item.className = 'forward-item';
                  const initial = (chat.contact_name || 'U').charAt(0).toUpperCase();
                  item.innerHTML = `
                    <div class="avatar" style="background: rgba(255,199,0,0.1); border-radius:50%; display:flex; align-items:center; justify-content:center; color:#FFC700;">${initial}</div>
                    <div style="flex:1; font-weight:500;">${chat.contact_name || 'Unknown'}</div>
                  `;
                  item.onclick = async () => {
                    try {
                      item.style.opacity = '0.5';
                      await authFetch(`${BASE_URL}/messages/forward/${selectedMsgId}`, {
                        method: 'POST',
                        body: JSON.stringify({ target_room_id: chat.room_id })
                      });
                      fwModal.classList.remove('active');
                      showToast('Message forwarded successfully!');
                    } catch (e) {
                      showToast('Forward failed');
                    }
                  };
                  fwList.appendChild(item);
                });
              }
            } catch (e) {
              fwLoad.style.display = 'none';
              fwList.innerHTML = '<div style="color:red; text-align:center;">Failed to load chats.</div>';
            }
            return;
          case 'download': {
            console.log('Media URL:', currentMediaUrl); // DEBUG
            if (!currentMediaUrl) {
              showToast('No media found to download.');
              return;
            }

            const dlFilename = currentMediaUrl.split('/').pop().split('?')[0] || 'download';
            showToast('Downloading...');

            // Use fetch → blob to force download, bypasses browser anchor CORS block
            fetch(currentMediaUrl)
              .then(res => {
                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                return res.blob();
              })
              .then(blob => {
                const blobUrl = URL.createObjectURL(blob);
                const dlAnchor = document.createElement('a');
                dlAnchor.href = blobUrl;
                dlAnchor.download = dlFilename;
                dlAnchor.style.display = 'none';
                document.body.appendChild(dlAnchor);
                dlAnchor.click();
                document.body.removeChild(dlAnchor);
                // Revoke blob URL after short delay so browser can start download
                setTimeout(() => URL.revokeObjectURL(blobUrl), 2000);
                showToast(`Downloaded: ${dlFilename}`);
              })
              .catch(err => {
                console.error('Download failed:', err);
                showToast('Download failed. Check console.');
              });

            // Close menu immediately (download runs async)
            msgContextMenu.classList.remove('active');
            msgContextMenu.style.display = 'none';
            return;
          }
          case 'reply': {
            replyingToMsgId = selectedMsgId;
            const replyBubble = document.querySelector(`.bubble[data-id="${selectedMsgId}"]`);
            let replyTxt = 'Message';
            let replySender = 'You';

            if (replyBubble) {
              // Get the text content — skip quote/forwarded sub-elements
              const span = replyBubble.querySelector('span');
              if (span) replyTxt = span.textContent.trim();

              // Determine sender: msg-right = mine, msg-left = contact
              if (!replyBubble.classList.contains('msg-right')) {
                let roomTitle = document.getElementById('roomTitle').textContent.trim();
                replySender = roomTitle.startsWith('Room:') ? 'Contact' : roomTitle;
              }
            }

            const rbSender = document.getElementById('replyBannerSender');
            const rbText = document.getElementById('replyBannerText');
            if (rbSender) rbSender.textContent = replySender;
            if (rbText) rbText.textContent = replyTxt;

            // Force banner animation replay
            if (replyBanner) {
              replyBanner.classList.remove('hidden');
              replyBanner.style.animation = 'none';
              void replyBanner.offsetWidth; // reflow
              replyBanner.style.animation = '';
            }

            document.getElementById('msgInput').focus();
            return; // No backend fetch needed for UI state
          }
        }
        // Update UI immediately after API hit (for actions like Pin that still need it)
        fetchHistory();
      } catch (err) {
        console.error("Context menu action failed:", err);
      }
    });
  });

  // Setup Forward Modal Close
  const closeForwardBtn = document.getElementById('closeForwardBtn');
  if (closeForwardBtn) {
    closeForwardBtn.addEventListener('click', () => {
      document.getElementById('forwardModalOverlay').classList.remove('active');
    });
  }

  // Setup Quote Block interaction
  document.querySelectorAll('.quote-block').forEach(qBlock => {
    qBlock.onclick = (e) => {
      e.stopPropagation();
      const targetId = qBlock.dataset.replyTo;
      const targetBubble = document.querySelector(`.bubble[data-id="${targetId}"]`);
      if (targetBubble) {
        targetBubble.scrollIntoView({ behavior: 'smooth', block: 'center' });
        targetBubble.classList.add('flash-highlight');
        setTimeout(() => targetBubble.classList.remove('flash-highlight'), 1000);
      }
    };
  });

  // ================================================================
  // Step 5 — attachSwipeToReply
  // WhatsApp-style right-swipe gesture on each bubble.
  // - Swipe right > THRESHOLD px  → triggers the reply UI
  // - Spring animation returns bubble to origin on release
  // - Crimson reply-arrow icon fades in proportionally to drag distance
  // ================================================================
  function attachSwipeToReply(bubble, msg, isMine) {
    const THRESHOLD = 62;   // px to cross before reply triggers
    const MAX_DRAG = 90;   // cap drag distance (px)
    const ICON_START = 20;   // px at which icon starts appearing

    let startX = 0;
    let currentX = 0;
    let swiping = false;
    let triggered = false;

    // Create the swipe icon once and append to bubble
    const icon = document.createElement('div');
    icon.className = 'swipe-reply-icon';
    icon.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none"
      stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
      <polyline points="9 17 4 12 9 7"></polyline>
      <path d="M20 18v-2a4 4 0 0 0-4-4H4"></path>
    </svg>`;
    bubble.appendChild(icon);

    // --- TOUCH START ---
    bubble.addEventListener('touchstart', (e) => {
      startX = e.touches[0].clientX;
      currentX = 0;
      swiping = true;
      triggered = false;
      bubble.classList.add('is-swiping'); // disable CSS transition during drag
    }, { passive: true });

    // --- TOUCH MOVE ---
    bubble.addEventListener('touchmove', (e) => {
      if (!swiping) return;
      const rawDelta = e.touches[0].clientX - startX;

      // Only track RIGHT swipe (positive delta)
      if (rawDelta <= 0) {
        bubble.style.transform = 'translateX(0)';
        icon.classList.remove('visible');
        return;
      }

      // Cap the drag
      currentX = Math.min(rawDelta, MAX_DRAG);
      bubble.style.transform = `translateX(${currentX}px)`;

      // Fade-in icon proportionally after ICON_START px
      if (currentX > ICON_START) {
        icon.classList.add('visible');
      } else {
        icon.classList.remove('visible');
      }

      // Haptic + early trigger feedback at threshold
      if (currentX >= THRESHOLD && !triggered) {
        triggered = true;
        if (navigator.vibrate) navigator.vibrate(35); // gentle haptic
      }
    }, { passive: true });

    // --- TOUCH END ---
    bubble.addEventListener('touchend', () => {
      if (!swiping) return;
      swiping = false;

      // Re-enable CSS spring transition for return animation
      bubble.classList.remove('is-swiping');
      bubble.style.transform = 'translateX(0)';
      icon.classList.remove('visible');

      // If threshold was crossed, fire reply
      if (triggered) {
        triggerReply(msg._id || msg.id, bubble, isMine);
      }

      currentX = 0;
      triggered = false;
    }, { passive: true });
  }

  // Helper called by both context menu AND swipe gesture
  function triggerReply(msgId, bubble, isMine) {
    replyingToMsgId = msgId;

    let replyTxt = 'Message';
    let replySender = 'You';

    if (bubble) {
      const span = bubble.querySelector('span');
      if (span) replyTxt = span.textContent.trim();

      if (!isMine) {
        let roomTitle = document.getElementById('roomTitle').textContent.trim();
        replySender = roomTitle.startsWith('Room:') ? 'Contact' : roomTitle;
      }
    }

    const rbSender = document.getElementById('replyBannerSender');
    const rbText = document.getElementById('replyBannerText');
    if (rbSender) rbSender.textContent = replySender;
    if (rbText) rbText.textContent = replyTxt;

    const banner = document.getElementById('replyBanner');
    if (banner) {
      banner.classList.remove('hidden');
      // Replay slide-in animation
      banner.style.animation = 'none';
      void banner.offsetWidth;
      banner.style.animation = '';
    }

    document.getElementById('msgInput').focus();
  }

});