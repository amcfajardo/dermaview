// Super Admin module: full-system control surface.
(function () {
  function escapeHtml(value) {
    const div = document.createElement('div');
    div.textContent = value == null ? '' : String(value);
    return div.innerHTML;
  }

  function processedByLabel(value) {
    const label = String(value || '').trim();
    return label && label.toLowerCase() !== 'system' ? label : 'Not recorded';
  }

  function formatDate(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '';
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  }

  function statusBadge(status) {
    const normalized = String(status || '').toLowerCase().replace(/\s+/g, '-');
    return `<span class="account-status account-status-${escapeHtml(normalized)}">${escapeHtml(status)}</span>`;
  }

  function displayPath(src) {
    if (!src) return '';
    if (/^(https?:|data:|blob:|\/|\.{1,2}\/)/i.test(src)) return src;
    return `../${src}`;
  }

  function imageCell(src, label) {
    const path = displayPath(src);
    return path
      ? `<img class="admin-thumb" src="${escapeHtml(path)}" alt="${escapeHtml(label)}" data-preview-image data-preview-title="${escapeHtml(label)}" tabindex="0">`
      : `<div class="admin-image-placeholder">${escapeHtml(label)}</div>`;
  }

  function bindPreview(root) {
    root.querySelectorAll('[data-preview-image]').forEach(image => {
      if (image.dataset.previewBound === 'true') return;
      image.dataset.previewBound = 'true';
      image.addEventListener('click', () => {
        let modal = document.getElementById('processedImagePreviewModal');
        if (!modal) {
          modal = document.createElement('div');
          modal.id = 'processedImagePreviewModal';
          modal.className = 'image-preview-modal';
          modal.innerHTML = `
            <div class="image-preview-dialog" role="dialog" aria-modal="true">
              <div class="image-preview-header">
                <h3>Image Preview</h3>
                <button type="button" class="image-preview-close">&times;</button>
              </div>
              <img src="" alt="">
            </div>
          `;
          document.body.appendChild(modal);
          modal.addEventListener('click', event => {
            if (event.target === modal || event.target.classList.contains('image-preview-close')) {
              modal.classList.remove('active');
            }
          });
        }

        modal.querySelector('h3').textContent = image.dataset.previewTitle || image.alt || 'Image Preview';
        modal.querySelector('img').src = image.src;
        modal.classList.add('active');
      });
    });
  }

  function downloadCsv(filename, rows) {
    const csv = rows.map(row => row.map(value => `"${String(value ?? '').replace(/"/g, '""')}"`).join(',')).join('\r\n');
    const link = document.createElement('a');
    link.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    link.download = filename;
    link.click();
    URL.revokeObjectURL(link.href);
  }

  function recordDisplayId(item) {
    return item.source === 'processed_images' ? `PI-${item.id}` : `REC-${item.id}`;
  }

  function ensureRecordDetailsModal() {
    let modal = document.getElementById('recordDetailsModal');
    if (modal) return modal;

    modal = document.createElement('div');
    modal.id = 'recordDetailsModal';
    modal.className = 'image-preview-modal admin-details-modal record-details-modal';
    modal.innerHTML = `
      <div class="image-preview-dialog admin-details-dialog" role="dialog" aria-modal="true" aria-labelledby="recordDetailsTitle">
        <div class="image-preview-header">
          <h3 id="recordDetailsTitle">Consultation Record</h3>
          <button type="button" class="image-preview-close" aria-label="Close record details">&times;</button>
        </div>
        <div class="admin-details-body" id="recordDetailsBody"></div>
      </div>
    `;
    document.body.appendChild(modal);

    modal.addEventListener('click', event => {
      if (event.target === modal || event.target.classList.contains('image-preview-close')) {
        modal.classList.remove('active');
      }
    });

    return modal;
  }

  function printRecordPdf(item) {
    const beforePath = displayPath(item.original_image_path);
    const afterPath = displayPath(item.processed_image_path);
    const beforePrintPath = beforePath ? new URL(beforePath, window.location.href).href : '';
    const afterPrintPath = afterPath ? new URL(afterPath, window.location.href).href : '';
    const printWindow = window.open('', '_blank', 'width=900,height=700');

    if (!printWindow) {
      alert('Please allow popups to export this consultation PDF.');
      return;
    }

    printWindow.document.write(`
      <!doctype html>
      <html>
      <head>
        <meta charset="utf-8">
        <title>${escapeHtml(recordDisplayId(item))} Consultation Record</title>
        <style>
          body { font-family: Arial, sans-serif; color: #111827; margin: 32px; }
          h1 { margin: 0 0 6px; font-size: 24px; }
          .muted { color: #64748b; margin: 0 0 24px; }
          .grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 14px; margin-bottom: 22px; }
          .field { border: 1px solid #e5e7eb; border-radius: 8px; padding: 12px; }
          .field span { display: block; color: #64748b; font-size: 12px; font-weight: 700; text-transform: uppercase; }
          .field strong { display: block; margin-top: 5px; font-size: 15px; }
          .images { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; margin: 24px 0; }
          figure { margin: 0; border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden; }
          img { display: block; width: 100%; aspect-ratio: 4 / 3; object-fit: contain; background: #f8fafc; }
          figcaption { padding: 8px 10px; font-weight: 700; font-size: 13px; }
          .notes { white-space: pre-wrap; line-height: 1.55; }
        </style>
      </head>
      <body>
        <h1>Consultation / Image Record</h1>
        <p class="muted">${escapeHtml(recordDisplayId(item))}</p>
        <div class="grid">
          <div class="field"><span>Procedure Used</span><strong>${escapeHtml(item.procedure_name || 'N/A')}</strong></div>
          <div class="field"><span>Processing Status</span><strong>${escapeHtml(item.processing_status || 'N/A')}</strong></div>
          <div class="field"><span>Staff Who Processed It</span><strong>${escapeHtml(processedByLabel(item.handled_by))}</strong></div>
          <div class="field"><span>Timestamp</span><strong>${escapeHtml(item.date_processed || 'N/A')}</strong></div>
        </div>
        <div class="images">
          <figure>
            ${beforePrintPath ? `<img src="${escapeHtml(beforePrintPath)}" alt="Before image">` : '<div class="field">No before image</div>'}
            <figcaption>Before Image</figcaption>
          </figure>
          <figure>
            ${afterPrintPath ? `<img src="${escapeHtml(afterPrintPath)}" alt="After image">` : '<div class="field">No after image</div>'}
            <figcaption>After Image</figcaption>
          </figure>
        </div>
        <h2>Notes</h2>
        <p class="notes">${escapeHtml(item.notes || 'No notes recorded.')}</p>
      </body>
      </html>
    `);
    printWindow.document.close();
    printWindow.focus();
    setTimeout(() => printWindow.print(), 400);
  }

  function openRecordDetails(item) {
    const modal = ensureRecordDetailsModal();
    const beforePath = displayPath(item.original_image_path);
    const afterPath = displayPath(item.processed_image_path);

    modal.querySelector('#recordDetailsTitle').textContent = `Record ${recordDisplayId(item)}`;
    modal.querySelector('#recordDetailsBody').innerHTML = `
      <div class="record-details-header">
        <div>
          <span class="table-muted">View Full Record</span>
          <h4>${escapeHtml(item.procedure_name || 'Consultation Record')}</h4>
        </div>
        <button type="button" class="accounts-create-btn" id="exportSingleRecordPdf">Export PDF</button>
      </div>

      <div class="record-image-compare">
        <figure>
          ${beforePath ? `<img src="${escapeHtml(beforePath)}" alt="Before image" data-preview-image data-preview-title="Before Image" tabindex="0">` : '<div class="admin-image-placeholder">Before Image</div>'}
          <figcaption>Before Image</figcaption>
        </figure>
        <figure>
          ${afterPath ? `<img src="${escapeHtml(afterPath)}" alt="After image" data-preview-image data-preview-title="After Image" tabindex="0">` : '<div class="admin-image-placeholder">After Image</div>'}
          <figcaption>After Image</figcaption>
        </figure>
      </div>

      <dl class="admin-details-list">
        <div><dt>Record ID</dt><dd>${escapeHtml(recordDisplayId(item))}</dd></div>
        <div><dt>Procedure Used</dt><dd>${escapeHtml(item.procedure_name || 'N/A')}</dd></div>
        <div><dt>Staff Processed By</dt><dd>${escapeHtml(processedByLabel(item.handled_by))}</dd></div>
        <div><dt>Timestamp</dt><dd>${escapeHtml(item.date_processed || 'N/A')}</dd></div>
        <div><dt>Status</dt><dd>${statusBadge(item.processing_status || 'N/A')}</dd></div>
        <div><dt>Notes</dt><dd>${escapeHtml(item.notes || 'No notes recorded.')}</dd></div>
      </dl>
    `;

    modal.querySelector('#exportSingleRecordPdf')?.addEventListener('click', () => printRecordPdf(item));
    bindPreview(modal);
    modal.classList.add('active');
  }

  window.initConsultationRecords = function () {
    const body = document.getElementById('recordsTableBody');
    if (!body) return;

    const search = document.getElementById('recordsSearch');
    const procedureFilter = document.getElementById('recordsProcedureFilter');
    const statusFilter = document.getElementById('recordsStatusFilter');
    const dateFilter = document.getElementById('recordsDateFilter');
    const exportBtn = document.getElementById('exportRecordsCsv');
    const clearBtn = document.getElementById('clearOldRecords');

    let records = [];

    function populateProcedures() {
      if (!procedureFilter) return;
      const current = procedureFilter.value;
      const names = Array.from(new Set(records.map(item => item.procedure_name).filter(Boolean))).sort();
      procedureFilter.innerHTML = '<option value="">All procedures</option>' + names.map(name => `<option>${escapeHtml(name)}</option>`).join('');
      procedureFilter.value = current;
    }

    function filteredRecords() {
      const query = search ? search.value.trim().toLowerCase() : '';
      return records.filter(item => {
        const dateOnly = item.date_processed ? item.date_processed.slice(0, 10) : '';
        return (!query || `${item.procedure_name} ${item.processing_status} ${item.handled_by} ${item.notes}`.toLowerCase().includes(query)) &&
          (!procedureFilter || !procedureFilter.value || item.procedure_name === procedureFilter.value) &&
          (!statusFilter || !statusFilter.value || item.processing_status === statusFilter.value) &&
          (!dateFilter || !dateFilter.value || dateOnly === dateFilter.value);
      });
    }

    function render() {
      const rows = filteredRecords();
      body.innerHTML = rows.length ? rows.map(item => `
        <tr>
          <td>${escapeHtml(recordDisplayId(item))}</td>
          <td>${escapeHtml(formatDate(item.date_processed))}</td>
          <td>${escapeHtml(item.procedure_name)}</td>
          <td>${imageCell(item.original_image_path, 'Original image')}</td>
          <td>${imageCell(item.processed_image_path, 'Processed image')}</td>
          <td>${statusBadge(item.processing_status)}</td>
          <td>${escapeHtml(processedByLabel(item.handled_by))}</td>
          <td>${escapeHtml(item.notes || '')}</td>
          <td>
            <div class="account-row-actions">
              <button type="button" class="account-action-btn reactivate-btn" data-view="${escapeHtml(item.source)}:${escapeHtml(item.id)}">View</button>
              <button type="button" class="account-action-btn deactivate-btn" data-delete="${escapeHtml(item.source)}:${escapeHtml(item.id)}">Delete</button>
            </div>
          </td>
        </tr>
      `).join('') : '<tr><td colspan="9" class="accounts-empty-cell">No records found.</td></tr>';
      bindPreview(body);
    }

    function loadRecords() {
      const data = new FormData();
      data.append('action', 'fetch');

      fetch('admin-consultation-records.php', { method: 'POST', body: data })
        .then(response => response.json())
        .then(payload => {
          if (!payload || payload.status !== 'ok') throw new Error(payload.message || 'Failed to load records.');
          records = payload.records || [];
          populateProcedures();
          render();
        })
        .catch(error => {
          body.innerHTML = `<tr><td colspan="9" class="accounts-empty-cell">${escapeHtml(error.message || 'Failed to load records.')}</td></tr>`;
        });
    }

    [search, procedureFilter, statusFilter, dateFilter].forEach(input => {
      if (input) input.addEventListener('input', render);
      if (input) input.addEventListener('change', render);
    });

    body.addEventListener('click', event => {
      const button = event.target.closest('button');
      if (!button) return;

      const raw = button.dataset.view || button.dataset.delete || '';
      const [source, id] = raw.split(':');
      const item = records.find(record => String(record.id) === String(id) && record.source === source);
      if (!item) return;

      if (button.dataset.view) {
        openRecordDetails(item);
        return;
      }

      if (!confirm('Delete this record?')) return;

      const data = new FormData();
      data.append('action', 'delete');
      data.append('id', id);
      data.append('source', source);

      fetch('admin-consultation-records.php', { method: 'POST', body: data })
        .then(response => response.json())
        .then(payload => {
          if (!payload || payload.status !== 'ok') throw new Error(payload.message || 'Failed to delete record.');
          loadRecords();
        })
        .catch(error => alert(error.message || 'Failed to delete record.'));
    });

    if (exportBtn) {
      exportBtn.addEventListener('click', () => {
        downloadCsv('consultation-image-records.csv', [
          ['Record ID', 'Date Processed', 'Procedure', 'Status', 'Handled By', 'Notes'],
          ...filteredRecords().map(item => [item.id, item.date_processed, item.procedure_name, item.processing_status, processedByLabel(item.handled_by), item.notes || ''])
        ]);
      });
    }

    if (clearBtn) {
      clearBtn.addEventListener('click', () => {
        if (!confirm('Clear records older than 90 days?')) return;
        const data = new FormData();
        data.append('action', 'clear_old');
        fetch('admin-consultation-records.php', { method: 'POST', body: data })
          .then(response => response.json())
          .then(() => loadRecords())
          .catch(error => alert(error.message || 'Failed to clear old records.'));
      });
    }

    loadRecords();
  };
})();
