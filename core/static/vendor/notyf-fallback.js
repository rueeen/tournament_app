(function setupNotyfFallback() {
  if (window.Notyf) return;

  const TYPE_CLASS = {
    success: 'notyf-fallback-toast--success',
    error: 'notyf-fallback-toast--error',
    warning: 'notyf-fallback-toast--warning',
    info: 'notyf-fallback-toast--info',
  };

  class NotyfFallback {
    constructor(options = {}) {
      this.options = options;
      this.duration = Number(options.duration || 3000);
      this.container = document.createElement('div');
      this.container.className = 'notyf-fallback-container';
      document.body.appendChild(this.container);
    }

    open(payload = {}) {
      const type = (payload.type || 'info').toLowerCase();
      const message = payload.message || '';
      const timeout = Number(payload.duration || this.duration);

      const toast = document.createElement('div');
      toast.className = `notyf-fallback-toast ${TYPE_CLASS[type] || TYPE_CLASS.info}`;
      toast.textContent = message;
      this.container.appendChild(toast);

      window.setTimeout(() => {
        toast.remove();
      }, timeout);
    }

    success(message) {
      this.open({ type: 'success', message });
    }

    error(message) {
      this.open({ type: 'error', message });
    }
  }

  window.Notyf = NotyfFallback;
})();
