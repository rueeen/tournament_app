window.addEventListener('load', () => {
  const isMobile = window.matchMedia('(max-width: 576px)').matches;
  const notyf = window.Notyf
    ? new Notyf({
        duration: isMobile ? 4500 : 3500,
        dismissible: isMobile,
        position: { x: isMobile ? 'center' : 'right', y: 'top' },
        types: [
          { type: 'info', background: '#5ea2ff' },
          { type: 'warning', background: '#f0ad4e' },
        ],
      })
    : null;

  const mapTag = (tags) => {
    const normalized = (tags || '').toLowerCase();
    if (normalized.includes('error') || normalized.includes('danger')) return 'error';
    if (normalized.includes('success')) return 'success';
    if (normalized.includes('warning')) return 'warning';
    return 'info';
  };

  document.querySelectorAll('#notyf-messages [data-tags]').forEach((message) => {
    if (notyf) {
      notyf.open({
        type: mapTag(message.dataset.tags),
        message: message.textContent.trim(),
      });
    }
  });

  const seenNotificationIds = new Set();
  document.querySelectorAll('#notification-events [data-notification-id]').forEach((item) => {
    const notificationId = item.dataset.notificationId;
    const storageKey = `notification-seen-${notificationId}`;
    if (!notyf || localStorage.getItem(storageKey)) return;
    notyf.open({
      type: 'info',
      message: item.textContent.trim(),
    });
    localStorage.setItem(storageKey, '1');
    seenNotificationIds.add(String(notificationId));
  });

  const feedUrl = document.body.dataset.notificationsFeedUrl;
  const notificationItems = document.getElementById('notifications-items');
  const notificationsBadge = document.getElementById('notifications-badge');

  const updateNotificationBadge = (count) => {
    if (!notificationsBadge) return;
    notificationsBadge.textContent = String(count);
    notificationsBadge.classList.toggle('d-none', count <= 0);
  };

  const renderNotifications = (items) => {
    if (!notificationItems) return;
    if (!items.length) {
      notificationItems.innerHTML = '<p class="text-secondary small mb-0" id="notifications-empty">No hay notificaciones todavía.</p>';
      return;
    }

    const html = items
      .map((item) => {
        const unreadClass = item.is_read ? '' : 'notification-item--unread';
        return `
          <a class="dropdown-item notification-item ${unreadClass}" href="/matches/${item.match_id}/">
            <small class="d-block text-secondary">${item.created_at}</small>
            <span>${item.message}</span>
          </a>
        `;
      })
      .join('');
    notificationItems.innerHTML = html;
  };

  const pollNotifications = async () => {
    if (!feedUrl || !notificationItems) return;
    try {
      const response = await fetch(feedUrl, {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        credentials: 'same-origin',
      });
      if (!response.ok) return;
      const payload = await response.json();
      const items = payload.notifications || [];
      updateNotificationBadge(payload.unread_count || 0);
      renderNotifications(items);

      items.forEach((item) => {
        const notificationId = String(item.id);
        const storageKey = `notification-seen-${notificationId}`;
        if (item.is_read || seenNotificationIds.has(notificationId) || localStorage.getItem(storageKey)) return;
        if (notyf) {
          notyf.open({ type: 'info', message: item.message });
        }
        localStorage.setItem(storageKey, '1');
        seenNotificationIds.add(notificationId);
      });
    } catch (error) {
      console.debug('No se pudo actualizar el feed de notificaciones.', error);
    }
  };

  if (feedUrl && notificationItems) {
    pollNotifications();
    setInterval(pollNotifications, 15000);
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) pollNotifications();
    });
  }

  document.querySelectorAll('form').forEach((form) => {
    form.addEventListener('submit', () => {
      const btn = form.querySelector('button[type="submit"]');
      if (btn) {
        btn.disabled = true;
        if (!btn.dataset.originalText) {
          btn.dataset.originalText = btn.innerText;
        }
        btn.innerText = 'Procesando...';
      }
    });
  });
});
