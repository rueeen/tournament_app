
window.addEventListener('load', () => {
  const notyf = window.Notyf
    ? new Notyf({
        duration: 3500,
        position: { x: 'right', y: 'top' },
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
