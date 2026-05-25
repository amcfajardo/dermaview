(function () {
  function escapeHtml(value) {
    const div = document.createElement('div');
    div.textContent = value == null ? '' : String(value);
    return div.innerHTML;
  }

  function formatDate(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '';
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit'
    });
  }

  function downloadTextFile(filename, content) {
    const blob = new Blob([content], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }

  window.initRolePermissions = function () {
    const key = 'dermaview.superAdmin.rolePermissions';
    const body = document.getElementById('rolePermissionsBody');
    const save = document.getElementById('saveRolePermissions');

    if (!body) return;

    const saved = JSON.parse(localStorage.getItem(key) || '{}');
    body.querySelectorAll('tr').forEach(row => {
      const inputs = Array.from(row.querySelectorAll('input[type="checkbox"]'));

      if (row.dataset.superAdminOnly === 'true') {
        inputs.forEach((input, inputIndex) => {
          input.checked = inputIndex === 0;
          input.disabled = true;
        });
        return;
      }

      const values = saved[row.dataset.feature];
      if (!Array.isArray(values)) return;

      inputs.forEach((input, inputIndex) => {
        if (!input.disabled && typeof values[inputIndex] === 'boolean') {
          input.checked = values[inputIndex];
        }
      });
    });

    if (save) {
      save.addEventListener('click', function () {
        const payload = {};
        body.querySelectorAll('tr').forEach(row => {
          payload[row.dataset.feature] = Array.from(row.querySelectorAll('input[type="checkbox"]')).map(input => input.checked);
        });
        localStorage.setItem(key, JSON.stringify(payload));
        alert('Role permissions saved. Super Admin-only controls remain locked.');
      });
    }
  };

  window.initPrivacyDataManagement = function () {
    const key = 'dermaview.superAdmin.cleanupHistory';
    const body = document.getElementById('cleanupHistoryBody');
    const count = document.getElementById('cleanupHistoryCount');
    const print = document.getElementById('printPrivacyPolicy');

    if (!body) return;

    function getRows() {
      return JSON.parse(localStorage.getItem(key) || '[]');
    }

    function saveRows(rows) {
      localStorage.setItem(key, JSON.stringify(rows));
    }

    function render() {
      const rows = getRows();
      if (count) count.textContent = rows.length.toLocaleString();
      body.innerHTML = rows.length
        ? rows.map(row => `
            <tr>
              <td>${escapeHtml(row.action)}</td>
              <td>${escapeHtml(row.status)}</td>
              <td>${escapeHtml(formatDate(row.date))}</td>
            </tr>
          `).join('')
        : '<tr><td colspan="3" class="accounts-empty-cell">No cleanup actions recorded.</td></tr>';
    }

    document.querySelectorAll('[data-cleanup-action]').forEach(button => {
      button.addEventListener('click', function () {
        const rows = getRows();
        rows.unshift({
          action: button.dataset.cleanupAction,
          status: 'Recorded for Super Admin review',
          date: new Date().toISOString()
        });
        saveRows(rows.slice(0, 25));
        render();
      });
    });

    if (print) print.addEventListener('click', () => window.print());
    render();
  };

  window.initBackupRestore = function () {
    const key = 'dermaview.superAdmin.backupHistory';
    const body = document.getElementById('backupHistoryBody');
    const create = document.getElementById('createBackupRecord');
    const download = document.getElementById('downloadBackupRecord');
    const clear = document.getElementById('clearBackupHistory');
    const restoreForm = document.getElementById('restoreDatabaseForm');

    if (!body) return;

    function getRows() {
      return JSON.parse(localStorage.getItem(key) || '[]');
    }

    function saveRows(rows) {
      localStorage.setItem(key, JSON.stringify(rows));
    }

    function render() {
      const rows = getRows();
      body.innerHTML = rows.length
        ? rows.map(row => `
            <tr>
              <td>${escapeHtml(row.type)}</td>
              <td><strong>${escapeHtml(row.name)}</strong></td>
              <td>${escapeHtml(row.status)}</td>
              <td>${escapeHtml(formatDate(row.date))}</td>
            </tr>
          `).join('')
        : '<tr><td colspan="4" class="accounts-empty-cell">No backup history recorded.</td></tr>';
    }

    if (create) {
      create.addEventListener('click', function () {
        const date = new Date();
        const rows = getRows();
        rows.unshift({
          type: 'Backup',
          name: `dermaview-backup-${date.toISOString().slice(0, 10)}.json`,
          status: 'Backup manifest created',
          date: date.toISOString()
        });
        saveRows(rows.slice(0, 25));
        render();
      });
    }

    if (download) {
      download.addEventListener('click', function () {
        downloadTextFile('dermaview-backup-history.json', JSON.stringify(getRows(), null, 2));
      });
    }

    if (clear) {
      clear.addEventListener('click', function () {
        if (!confirm('Clear local backup history?')) return;
        localStorage.removeItem(key);
        render();
      });
    }

    if (restoreForm) {
      restoreForm.addEventListener('submit', function (event) {
        event.preventDefault();
        const file = document.getElementById('restoreFile');
        const reason = document.getElementById('restoreReason');
        const rows = getRows();
        rows.unshift({
          type: 'Restore Request',
          name: `${file?.files?.[0]?.name || 'No file selected'}${reason?.value ? ' - ' + reason.value : ''}`,
          status: 'Pending Super Admin verification',
          date: new Date().toISOString()
        });
        saveRows(rows.slice(0, 25));
        restoreForm.reset();
        render();
      });
    }

    render();
  };
})();
