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
  let lastNotificationId = 0;
  let pollTimer = null;

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
          <a class="dropdown-item notification-item ${unreadClass}" href="${item.open_url}" data-notification-id="${item.id}">
            <small class="d-block text-secondary">${item.created_at}</small>
            <span class="d-block fw-semibold">${item.title || 'Notificación'}</span>
            <span>${item.message}</span>
          </a>
        `;
      })
      .join('');
    notificationItems.innerHTML = html;
  };

  const showToastIfNeeded = (item) => {
    const notificationId = String(item.id);
    const storageKey = `notification-seen-${notificationId}`;
    if (item.is_read || seenNotificationIds.has(notificationId) || localStorage.getItem(storageKey)) return;
    if (notyf) {
      notyf.open({ type: 'info', message: `${item.title || 'Notificación'}: ${item.message}` });
    }
    localStorage.setItem(storageKey, '1');
    seenNotificationIds.add(notificationId);
  };

  const pollNotifications = async (fullRefresh = false) => {
    if (!feedUrl || !notificationItems) return;

    try {
      const url = new URL(feedUrl, window.location.origin);

      if (lastNotificationId > 0 && !fullRefresh) {
        url.searchParams.set('since_id', String(lastNotificationId));
      }

      // evita cache del navegador/proxy
      url.searchParams.set('_ts', Date.now().toString());

      const response = await fetch(url.toString(), {
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        credentials: 'same-origin',
        cache: 'no-store',
      });

      if (!response.ok) return;

      const payload = await response.json();
      const items = payload.notifications || [];
      const newItems = payload.new_notifications || [];

      updateNotificationBadge(payload.unread_count || 0);

      if (fullRefresh || newItems.length > 0) {
        renderNotifications(items);
      }

      newItems.forEach(showToastIfNeeded);

      if (payload.last_id) {
        lastNotificationId = payload.last_id;
      }
    } catch (error) {
      console.debug('No se pudo actualizar el feed de notificaciones.', error);
    }
  };

  const startPolling = () => {
    const intervalMs = document.hidden ? 15000 : 3000;
    if (pollTimer) {
      clearInterval(pollTimer);
    }
    pollTimer = setInterval(() => pollNotifications(), intervalMs);
  };

  if (feedUrl && notificationItems) {
    pollNotifications(true);
    startPolling();
    document.addEventListener('visibilitychange', () => {
      startPolling();
      if (!document.hidden) pollNotifications();
    });
  }

  const notificationsTrigger = document.querySelector('.notifications-trigger');

  if (notificationsTrigger) {
    notificationsTrigger.addEventListener('click', () => {
      pollNotifications(true);
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
