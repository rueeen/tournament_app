
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

  document.querySelectorAll('#notification-events [data-notification-id]').forEach((item) => {
    const notificationId = item.dataset.notificationId;
    const storageKey = `notification-seen-${notificationId}`;
    if (!notyf || localStorage.getItem(storageKey)) return;
    notyf.open({
      type: 'info',
      message: item.textContent.trim(),
    });
    localStorage.setItem(storageKey, '1');
  });

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
