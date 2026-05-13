document.addEventListener('DOMContentLoaded', () => {
  const token = localStorage.getItem('token');
  if (!token) { window.location.href = 'login.html'; return; }

  const loadingState = document.getElementById('loadingState');
  const emptyState   = document.getElementById('emptyState');
  const blockedList  = document.getElementById('blockedList');
  const backBtn      = document.getElementById('backBtn');
  const toastCont    = document.getElementById('toastContainer');

  // ── Back button ─────────────────────────────────────────────────────────────
  backBtn.addEventListener('click', () => window.history.back());

  // ── Toast helper ────────────────────────────────────────────────────────────
  function showToast(msg) {
    const t = document.createElement('div');
    t.className = 'toast-notification';
    t.textContent = msg;
    toastCont.appendChild(t);
    setTimeout(() => t.remove(), 3000);
  }

  // ── authFetch helper (mirrors home.js / config.js pattern) ──────────────────
  async function authFetch(url, options = {}) {
    return fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
        ...(options.headers || {})
      }
    });
  }

  // ── Show / hide states ───────────────────────────────────────────────────────
  function show(el)  { el.classList.remove('hidden'); }
  function hide(el)  { el.classList.add('hidden'); }

  // ── Fetch and render blocked users ───────────────────────────────────────────
  async function fetchBlocked() {
    show(loadingState);
    hide(emptyState);
    hide(blockedList);

    try {
      const res  = await authFetch(`${BASE_URL}/contacts/blocked`);
      const data = await res.json();
      const list = data.data || [];

      hide(loadingState);

      if (list.length === 0) {
        show(emptyState);
        return;
      }

      blockedList.innerHTML = '';
      list.forEach((contact, i) => renderCard(contact, i));
      show(blockedList);
    } catch (err) {
      console.error('Failed to fetch blocked users:', err);
      hide(loadingState);
      show(emptyState);
    }
  }

  // ── Render a single blocked contact card ─────────────────────────────────────
  function renderCard(contact, index) {
    const name    = contact.contact_nickname || contact.contact_email?.split('@')[0] || 'Unknown';
    const email   = contact.contact_email || '';
    const initial = name.charAt(0).toUpperCase();
    // contact._id is the MongoDB contact document ID (not room_id)
    const contactId = contact._id;

    const card = document.createElement('div');
    card.className = 'blocked-card';
    card.style.animationDelay = `${index * 0.06}s`;
    card.dataset.contactId = contactId;
    card.innerHTML = `
      <div class="avatar">${initial}</div>
      <div class="blocked-info">
        <div class="blocked-name">${name}</div>
        <div class="blocked-email">${email}</div>
      </div>
      <button class="unblock-btn" data-id="${contactId}">Unblock</button>
    `;

    card.querySelector('.unblock-btn').addEventListener('click', () => unblock(contactId, card));
    blockedList.appendChild(card);
  }

  // ── Unblock action ───────────────────────────────────────────────────────────
  // NOTE: The unblock endpoint in contactroutes.py expects a room_id.
  // However, the blocked-users page only has the contact document _id.
  // We use a dedicated contact-level unblock endpoint here.
  async function unblock(contactId, cardEl) {
    // Optimistic removal
    cardEl.style.opacity = '0.4';
    cardEl.style.pointerEvents = 'none';

    try {
      // Direct contact-level unblock (by contact _id, not room_id)
      const res = await authFetch(`${BASE_URL}/contacts/unblock_by_id/${contactId}`, {
        method: 'POST'
      });

      if (res.ok) {
        // Animate out then remove
        cardEl.style.transition = 'opacity 0.25s, transform 0.25s';
        cardEl.style.transform  = 'translateX(30px)';
        cardEl.style.opacity    = '0';
        setTimeout(() => {
          cardEl.remove();
          if (blockedList.children.length === 0) {
            hide(blockedList);
            show(emptyState);
          }
        }, 280);
        showToast('User unblocked successfully.');
      } else {
        throw new Error(`HTTP ${res.status}`);
      }
    } catch (err) {
      console.error('Unblock failed:', err);
      cardEl.style.opacity = '1';
      cardEl.style.pointerEvents = 'auto';
      showToast('Failed to unblock. Please try again.');
    }
  }

  // ── Init ─────────────────────────────────────────────────────────────────────
  fetchBlocked();
});
