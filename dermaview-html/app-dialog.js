(function () {
  let root = null;
  let stylesReady = false;

  function ensureStyles() {
    if (stylesReady) return;

    const style = document.createElement('style');
    style.id = 'dv-dialog-styles';
    style.textContent = `
      .dv-dialog-backdrop {
        position: fixed;
        inset: 0;
        z-index: 10000;
        background: rgba(15, 23, 42, 0.46);
        backdrop-filter: blur(3px);
      }

      .dv-dialog {
        position: fixed;
        inset: 0;
        z-index: 10001;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 24px;
        box-sizing: border-box;
      }

      .dv-dialog[hidden],
      .dv-dialog-backdrop[hidden] {
        display: none !important;
      }

      .dv-dialog-panel {
        width: min(420px, 100%);
        border: 1px solid #e5e7eb;
        border-radius: 18px;
        background: #ffffff;
        color: #111827;
        padding: 24px;
        box-shadow: 0 24px 70px rgba(15, 23, 42, 0.24);
        font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      }

      .dv-dialog-panel h3 {
        margin: 0 0 10px;
        color: #111827;
        font-size: 1.15rem;
        line-height: 1.25;
        font-weight: 800;
      }

      .dv-dialog-panel p {
        margin: 0;
        color: #4b5563;
        font-size: 0.98rem;
        line-height: 1.55;
        white-space: pre-wrap;
      }

      .dv-dialog-input {
        width: 100%;
        min-height: 46px;
        margin-top: 16px;
        padding: 0 12px;
        border: 1px solid #d1d5db;
        border-radius: 10px;
        box-sizing: border-box;
        font: inherit;
      }

      .dv-dialog-input:focus {
        border-color: #2563eb;
        box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.14);
        outline: none;
      }

      .dv-dialog-actions {
        display: flex;
        justify-content: flex-end;
        gap: 10px;
        margin-top: 22px;
      }

      .dv-dialog-actions button {
        min-height: 40px;
        border: 1px solid #d1d5db;
        border-radius: 10px;
        padding: 0 16px;
        background: #ffffff;
        color: #111827;
        font: inherit;
        font-weight: 700;
        cursor: pointer;
      }

      .dv-dialog-actions .dv-dialog-ok {
        border-color: #2563eb;
        background: #2563eb;
        color: #ffffff;
      }
    `;
    document.head.appendChild(style);
    stylesReady = true;
  }

  function ensureRoot() {
    if (root) return root;

    ensureStyles();
    root = document.createElement('div');
    root.className = 'dv-dialog-root';
    root.innerHTML = `
      <div class="dv-dialog-backdrop" data-dialog-backdrop hidden></div>
      <div class="dv-dialog" role="dialog" aria-modal="true" aria-labelledby="dvDialogTitle" hidden>
        <div class="dv-dialog-panel">
          <h3 id="dvDialogTitle">DermaView</h3>
          <p data-dialog-message></p>
          <input data-dialog-input class="dv-dialog-input" hidden>
          <div class="dv-dialog-actions">
            <button type="button" class="dv-dialog-cancel" data-dialog-cancel hidden>Cancel</button>
            <button type="button" class="dv-dialog-ok" data-dialog-ok>OK</button>
          </div>
        </div>
      </div>
    `;
    document.body.appendChild(root);
    return root;
  }

  function showDialog(options) {
    const node = ensureRoot();
    const backdrop = node.querySelector('[data-dialog-backdrop]');
    const dialog = node.querySelector('.dv-dialog');
    const title = node.querySelector('#dvDialogTitle');
    const message = node.querySelector('[data-dialog-message]');
    const input = node.querySelector('[data-dialog-input]');
    const ok = node.querySelector('[data-dialog-ok]');
    const cancel = node.querySelector('[data-dialog-cancel]');

    title.textContent = options.title || 'DermaView';
    message.textContent = options.message || '';
    ok.textContent = options.okText || 'OK';
    cancel.textContent = options.cancelText || 'Cancel';
    cancel.hidden = options.type === 'alert';

    input.hidden = options.type !== 'prompt';
    input.value = options.defaultValue || '';
    input.type = options.inputType || 'text';

    backdrop.hidden = false;
    dialog.hidden = false;

    return new Promise(resolve => {
      function cleanup(value) {
        ok.removeEventListener('click', onOk);
        cancel.removeEventListener('click', onCancel);
        backdrop.removeEventListener('click', onCancel);
        document.removeEventListener('keydown', onKey);
        backdrop.hidden = true;
        dialog.hidden = true;
        resolve(value);
      }

      function onOk() {
        cleanup(options.type === 'prompt' ? input.value : true);
      }

      function onCancel() {
        cleanup(options.type === 'alert' ? true : false);
      }

      function onKey(event) {
        if (event.key === 'Escape') onCancel();
        if (event.key === 'Enter' && (options.type !== 'prompt' || document.activeElement === input)) onOk();
      }

      ok.addEventListener('click', onOk);
      cancel.addEventListener('click', onCancel);
      backdrop.addEventListener('click', onCancel);
      document.addEventListener('keydown', onKey);

      if (options.type === 'prompt') {
        input.focus();
        input.select();
      } else {
        ok.focus();
      }
    });
  }

  window.DermaViewDialog = {
    alert(message, options = {}) {
      return showDialog({ ...options, type: 'alert', message });
    },
    confirm(message, options = {}) {
      return showDialog({ ...options, type: 'confirm', message });
    },
    prompt(message, options = {}) {
      return showDialog({ ...options, type: 'prompt', message });
    }
  };

  window.alert = function (message) {
    window.DermaViewDialog.alert(String(message || ''), { title: 'DermaView' });
  };
})();
