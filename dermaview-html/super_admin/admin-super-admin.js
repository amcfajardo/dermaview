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

  window.initRolePermissions = function () {
    const key = 'dermaview.superAdmin.rolePermissions';
    const body = document.getElementById('rolePermissionsBody');
    const save = document.getElementById('saveRolePermissions');

    if (!body) return;

    const allowedRoleIndexes = [0, 1, 4];
    const allowedRoleHeaders = ['Super Admin', 'Admin', 'Staff'];
    const table = body.closest('table');

    if (table) {
      const headerRow = table.querySelector('thead tr');
      if (headerRow) {
        headerRow.innerHTML = `<th>Feature</th>${allowedRoleHeaders.map(role => `<th>${role}</th>`).join('')}`;
      }

      body.querySelectorAll('tr').forEach(row => {
        const cells = Array.from(row.children);
        if (cells.length <= 4) return;

        const featureCell = cells[0];
        const roleCells = allowedRoleIndexes
          .map(index => cells[index + 1])
          .filter(Boolean);
        row.replaceChildren(featureCell, ...roleCells);
      });
    }

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

      const savedValues = saved[row.dataset.feature];
      const values = Array.isArray(savedValues) && savedValues.length === 5
        ? [savedValues[0], savedValues[1], savedValues[4]]
        : savedValues;
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
    const body = document.getElementById('cleanupHistoryBody');
    const count = document.getElementById('cleanupHistoryCount');
    const printButtons = document.querySelectorAll('[data-print-privacy-policy]');

    if (!body) return;

    function endpoint(action) {
      return `admin-privacy-data.php?action=${encodeURIComponent(action)}&v=${Date.now()}`;
    }

    function setBusy(button, busy, label) {
      if (!button) return;
      if (!button.dataset.defaultText) button.dataset.defaultText = button.textContent;
      button.disabled = busy;
      button.textContent = busy ? label : button.dataset.defaultText;
    }

    function render(rows) {
      if (count) count.textContent = rows.length.toLocaleString();
      body.innerHTML = rows.length
        ? rows.map(row => `
            <tr>
              <td>${escapeHtml(row.action)}</td>
              <td>${escapeHtml(row.status === 'Recorded for Super Admin review' || row.status === 'Logged only - no files or records deleted' ? 'Legacy log only - no archive performed' : row.status)}</td>
              <td>${escapeHtml(formatDate(row.date))}</td>
            </tr>
          `).join('')
        : '<tr><td colspan="3" class="accounts-empty-cell">No archive actions recorded.</td></tr>';
    }

    function loadHistory() {
      return fetch(endpoint('list'), { cache: 'no-store' })
        .then(response => response.json())
        .then(payload => {
          if (payload.status !== 'ok') {
            throw new Error(payload.message || 'Unable to load archive history.');
          }
          render(payload.records || []);
        })
        .catch(error => {
          body.innerHTML = `<tr><td colspan="3" class="accounts-empty-cell">${escapeHtml(error.message || 'Unable to load archive history.')}</td></tr>`;
        });
    }

    document.querySelectorAll('[data-archive-action]').forEach(button => {
      button.addEventListener('click', function () {
        if (!confirm(`${button.textContent.trim()}?`)) return;

        const data = new FormData();
        data.append('action', button.dataset.archiveAction);
        setBusy(button, true, 'Archiving...');

        fetch('admin-privacy-data.php', { method: 'POST', body: data })
          .then(response => response.json())
          .then(payload => {
            if (payload.status !== 'ok') {
              throw new Error(payload.message || 'Archive action failed.');
            }
            render(payload.records || []);
            alert(payload.message || 'Archive action completed.');
          })
          .catch(error => alert(error.message || 'Archive action failed.'))
          .finally(() => setBusy(button, false));
      });
    });

    printButtons.forEach(print => {
      print.addEventListener('click', () => {
        const settings = window.DermaViewBranding?.loadSettings?.() || {};
        const clinicName = settings.clinicName || 'DermaView';
        const retention = settings.imageRetentionPeriod || '180 days';
        const printWindow = window.open('', '_blank', 'width=900,height=700');

        if (!printWindow) {
          alert('Please allow popups to print the privacy policy.');
          return;
        }

        printWindow.document.write(`
          <!doctype html>
          <html>
          <head>
            <title>${escapeHtml(clinicName)} Privacy Policy</title>
            <style>
              body { font-family: Arial, sans-serif; color: #111827; line-height: 1.6; padding: 32px; }
              h1 { margin: 0 0 8px; font-size: 28px; }
              h2 { margin-top: 24px; font-size: 18px; }
              p, li { font-size: 14px; }
              .meta { color: #4b5563; margin-bottom: 24px; }
            </style>
          </head>
          <body>
            <h1>${escapeHtml(clinicName)} Privacy Policy</h1>
            <p class="meta">Generated on ${escapeHtml(formatDate(new Date().toISOString()))}</p>
            <h2>Data Collection</h2>
            <p>The clinic stores patient contact details, appointment records, consultation notes, uploaded images, and processed image records needed for consultation and documentation.</p>
            <h2>Image Retention</h2>
            <p>Uploaded and processed images follow the configured retention period: <strong>${escapeHtml(retention)}</strong>.</p>
            <h2>Archiving</h2>
            <p>Old image files and inactive patient records may be archived by the Super Admin. Archiving preserves data for review and audit instead of permanently deleting it.</p>
            <h2>Access Control</h2>
            <p>Administrative privacy, archive, backup, and restore tools are limited to authorized users, with Super Admin access required for archive actions.</p>
            <h2>Restore and Backup</h2>
            <p>Database backups are saved as server files. Restore requests are logged for review and do not automatically replace the active database.</p>
          </body>
          </html>
        `);
        printWindow.document.close();
        printWindow.focus();
        printWindow.print();
      });
    });

    loadHistory();
  };

  window.initBackupRestore = function () {
    const body = document.getElementById('backupHistoryBody');
    const create = document.getElementById('createBackupRecord');
    const download = document.getElementById('downloadBackupRecord');
    const clear = document.getElementById('clearBackupHistory');
    const restoreForm = document.getElementById('restoreDatabaseForm');
    let latestBackupId = null;

    if (!body) return;

    function endpoint(action) {
      return `admin-backup-restore.php?action=${encodeURIComponent(action)}&v=${Date.now()}`;
    }

    function setBusy(button, busy, label) {
      if (!button) return;
      if (!button.dataset.defaultText) button.dataset.defaultText = button.textContent;
      button.disabled = busy;
      button.textContent = busy ? label : button.dataset.defaultText;
    }

    function render(rows) {
      latestBackupId = null;
      const latestBackup = rows.find(row => row.type === 'Backup');
      if (latestBackup) latestBackupId = latestBackup.id;

      if (download) {
        download.disabled = !latestBackupId;
      }

      body.innerHTML = rows.length
        ? rows.map(row => `
            <tr>
              <td>${escapeHtml(row.type)}</td>
              <td>
                <strong>${escapeHtml(row.file_name)}</strong>
                ${row.reason ? `<br><span class="table-muted">${escapeHtml(row.reason)}</span>` : ''}
              </td>
              <td>${escapeHtml(row.status === 'Pending server verification' ? 'Request logged only - database not restored' : row.status)}</td>
              <td>${escapeHtml(formatDate(row.date))}</td>
            </tr>
          `).join('')
        : '<tr><td colspan="4" class="accounts-empty-cell">No backup history recorded.</td></tr>';
    }

    function loadHistory() {
      return fetch(endpoint('list'), { cache: 'no-store' })
        .then(response => response.json())
        .then(payload => {
          if (payload.status !== 'ok') {
            throw new Error(payload.message || 'Unable to load backup history.');
          }
          render(payload.records || []);
        })
        .catch(error => {
          body.innerHTML = `<tr><td colspan="4" class="accounts-empty-cell">${escapeHtml(error.message || 'Unable to load backup history.')}</td></tr>`;
        });
    }

    if (create) {
      create.addEventListener('click', function () {
        const data = new FormData();
        data.append('action', 'create_backup');
        setBusy(create, true, 'Creating...');

        fetch('admin-backup-restore.php', { method: 'POST', body: data })
          .then(response => response.json())
          .then(payload => {
            if (payload.status !== 'ok') {
              throw new Error(payload.message || 'Unable to create backup.');
            }
            render(payload.records || []);
            alert(payload.message || 'Database backup created.');
          })
          .catch(error => alert(error.message || 'Unable to create backup.'))
          .finally(() => setBusy(create, false));
      });
    }

    if (clear) {
      clear.addEventListener('click', function () {
        loadHistory();
      });
    }

    if (download) {
      download.addEventListener('click', function () {
        if (!latestBackupId) {
          alert('No backup file is available to download yet.');
          return;
        }

        window.location.href = endpoint('download') + `&id=${encodeURIComponent(latestBackupId)}`;
      });
    }

    if (restoreForm) {
      restoreForm.addEventListener('submit', function (event) {
        event.preventDefault();
        const file = document.getElementById('restoreFile');
        const reason = document.getElementById('restoreReason');
        const submit = restoreForm.querySelector('button[type="submit"]');

        if (!file?.files?.[0]) {
          alert('Please choose a backup file.');
          return;
        }

        if (!reason?.value?.trim()) {
          alert('Please enter a restore reason.');
          reason?.focus();
          return;
        }

        const data = new FormData();
        data.append('action', 'restore_request');
        data.append('restore_file', file.files[0]);
        data.append('reason', reason.value.trim());
        setBusy(submit, true, 'Recording...');

        fetch('admin-backup-restore.php', { method: 'POST', body: data })
          .then(response => response.json())
          .then(payload => {
            if (payload.status !== 'ok') {
              throw new Error(payload.message || 'Unable to record restore request.');
            }
            restoreForm.reset();
            render(payload.records || []);
            alert(payload.message || 'Restore request recorded.');
          })
          .catch(error => alert(error.message || 'Unable to record restore request.'))
          .finally(() => setBusy(submit, false));
      });
    }

    loadHistory();
  };
})();
