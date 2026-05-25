(function () {
  function escapeHtml(value) {
    const div = document.createElement('div');
    div.textContent = value == null ? '' : String(value);
    return div.innerHTML;
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

  function imageCell(src, label) {
    return src
      ? `<img class="admin-thumb" src="${escapeHtml(src)}" alt="${escapeHtml(label)}" data-preview-image data-preview-title="${escapeHtml(label)}" tabindex="0">`
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
    const csv = rows.map(row => row.map(value => `"${String(value ?? '').replace(/"/g, '""')}"`).join(',')).join('\n');
    const link = document.createElement('a');
    link.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    link.download = filename;
    link.click();
    URL.revokeObjectURL(link.href);
  }

  window.initManageProcedures = function () {
    const body = document.getElementById('procedureTableBody');
    const form = document.getElementById('procedureForm');
    const search = document.getElementById('procedureSearch');
    const show = document.getElementById('showProcedureForm');
    const cancel = document.getElementById('cancelProcedureForm');

    if (!body || !form) return;

    const formHome = {
      parent: form.parentElement,
      nextSibling: form.nextSibling
    };
    let procedures = [];

    function setFormVisible(visible) {
      form.hidden = !visible;
      if (show) show.hidden = visible;
    }

    function restoreFormLocation() {
      if (formHome.parent && form.parentElement !== formHome.parent) {
        formHome.parent.insertBefore(form, formHome.nextSibling);
      }
    }

    function closeProcedureFormModal(reset = true) {
      if (reset) form.reset();
      setFormVisible(false);
      restoreFormLocation();

      const modal = document.getElementById('procedureEditModal');
      if (modal) modal.classList.remove('active');
    }

    function setField(id, value) {
      const field = document.getElementById(id);
      if (field) field.value = value || '';
    }

    function fillForm(item) {
      form.reset();

      const title = document.getElementById('procedureFormTitle');
      if (title) title.textContent = item ? 'Edit Procedure' : 'Add Procedure';

      setField('procedureId', item ? item.id : '');
      setField('procedureName', item ? item.procedure_name : '');
      setField('procedureCategory', item ? item.category : '');
      setField('procedureStatus', item ? item.status : 'Active');
      setField('procedureDescription', item ? item.short_description : '');
      setField('procedureFullDescription', item ? item.full_description : '');
      setField('procedureBenefits', item ? item.benefits : '');
      setField('procedurePreparation', item ? item.preparation_guidelines : '');
      setField('procedureAftercare', item ? item.aftercare_instructions : '');
      setField('procedureDuration', item ? item.session_duration : '');
      setField('procedureSessions', item ? item.recommended_sessions : '');
      setField('procedurePrice', item ? item.procedure_price : '');
      setField('procedureScript', item ? item.processing_script : '');

      setFormVisible(true);
    }

    function render() {
      const query = search ? search.value.trim().toLowerCase() : '';
      const rows = query
        ? procedures.filter(item => `${item.procedure_name} ${item.category} ${item.short_description} ${item.status} ${item.procedure_price} ${item.processing_script}`.toLowerCase().includes(query))
        : procedures;

      body.innerHTML = rows.length ? rows.map(item => `
        <tr draggable="true" data-procedure-row="${escapeHtml(item.id)}" title="Drag row to reorder">
          <td><strong>${escapeHtml(item.procedure_name)}</strong></td>
          <td>${escapeHtml(item.category)}</td>
          <td><div class="procedures-admin-description">${escapeHtml(item.short_description)}</div></td>
          <td>${statusBadge(item.status)}</td>
          <td>${escapeHtml(formatDate(item.updated_at))}</td>
          <td>
            <div class="account-row-actions">
              <button type="button" class="procedure-action-btn procedure-action-edit" data-edit="${escapeHtml(item.id)}">Edit</button>
              <button type="button" class="procedure-action-btn procedure-action-view" data-view="${escapeHtml(item.id)}">View</button>
              <button type="button" class="procedure-action-btn ${item.status === 'Active' ? 'procedure-action-delete' : 'procedure-action-view'}" data-toggle="${escapeHtml(item.id)}">${item.status === 'Active' ? 'Hide' : 'Show'}</button>
              <button type="button" class="procedure-action-btn procedure-action-delete" data-delete="${escapeHtml(item.id)}" aria-label="Delete ${escapeHtml(item.procedure_name)}">Delete</button>
            </div>
          </td>
        </tr>
      `).join('') : '<tr><td colspan="6" class="accounts-empty-cell">No procedures found.</td></tr>';
    }

    function detailValue(value) {
      return escapeHtml(value || 'N/A');
    }

    function toggleInlineProcedureDetails(button, item) {
      const row = button.closest('tr');
      const existing = body.querySelector('.procedure-inline-details-row');

      if (existing && existing.dataset.procedureDetails === String(item.id)) {
        existing.remove();
        return;
      }

      if (existing) {
        existing.remove();
      }

      const detailRow = document.createElement('tr');
      detailRow.className = 'procedure-inline-details-row';
      detailRow.dataset.procedureDetails = String(item.id);
      detailRow.innerHTML = `
        <td colspan="6">
          <div class="procedure-inline-details">
            <div class="procedure-inline-details-header">
              <div>
                <span class="procedure-chip">${escapeHtml(item.category || 'Procedure')}</span>
                <h4>${escapeHtml(item.procedure_name)}</h4>
              </div>
              ${statusBadge(item.status)}
            </div>
            <p>${escapeHtml(item.full_description || item.short_description || '')}</p>
            <div class="procedure-inline-details-grid">
              <div><strong>Benefits</strong><span>${detailValue(item.benefits)}</span></div>
              <div><strong>Preparation</strong><span>${detailValue(item.preparation_guidelines)}</span></div>
              <div><strong>Aftercare</strong><span>${detailValue(item.aftercare_instructions)}</span></div>
              <div><strong>Duration</strong><span>${detailValue(item.session_duration)}</span></div>
              <div><strong>Sessions</strong><span>${detailValue(item.recommended_sessions)}</span></div>
              <div><strong>Price</strong><span>${detailValue(item.procedure_price)}</span></div>
              <div><strong>Processing Script</strong><span>${detailValue(item.processing_script)}</span></div>
              <div><strong>Updated</strong><span>${escapeHtml(formatDate(item.updated_at))}</span></div>
            </div>
          </div>
        </td>
      `;
      row.insertAdjacentElement('afterend', detailRow);
    }

    function saveProcedureOrder() {
      const ids = Array.from(body.querySelectorAll('[data-procedure-row]'))
        .map(row => row.dataset.procedureRow)
        .filter(Boolean);

      if (!ids.length) return;

      const data = new FormData();
      data.append('action', 'reorder');
      data.append('ids', JSON.stringify(ids));

      fetch('admin-procedures.php', { method: 'POST', body: data })
        .then(response => response.json())
        .then(payload => {
          if (!payload || payload.status !== 'ok') throw new Error(payload.message || 'Failed to save procedure order.');
          procedures = ids
            .map(id => procedures.find(item => String(item.id) === String(id)))
            .filter(Boolean);
        })
        .catch(error => alert(error.message || 'Failed to save procedure order.'));
    }

    function bindProcedureReorder() {
      let draggedRow = null;

      body.addEventListener('dragstart', event => {
        const row = event.target.closest('[data-procedure-row]');
        if (!row) return;
        if (event.target.closest('button, a, input, select, textarea')) {
          event.preventDefault();
          return;
        }
        draggedRow = row;
        row.classList.add('is-dragging');
        event.dataTransfer.effectAllowed = 'move';
        event.dataTransfer.setData('text/plain', row.dataset.procedureRow);
      });

      body.addEventListener('dragover', event => {
        const row = event.target.closest('[data-procedure-row]');
        if (!row || !draggedRow || row === draggedRow) return;
        event.preventDefault();

        const rect = row.getBoundingClientRect();
        const shouldPlaceAfter = event.clientY > rect.top + rect.height / 2;
        row.parentNode.insertBefore(draggedRow, shouldPlaceAfter ? row.nextSibling : row);
      });

      body.addEventListener('dragend', () => {
        if (!draggedRow) return;
        draggedRow.classList.remove('is-dragging');
        draggedRow = null;
        saveProcedureOrder();
      });
    }

    function loadProcedures() {
      const data = new FormData();
      data.append('action', 'fetch');

      fetch('admin-procedures.php', { method: 'POST', body: data })
        .then(response => response.json())
        .then(payload => {
          if (!payload || payload.status !== 'ok') throw new Error(payload.message || 'Failed to load procedures.');
          procedures = payload.procedures || [];
          render();
        })
        .catch(error => {
          body.innerHTML = `<tr><td colspan="6" class="accounts-empty-cell">${escapeHtml(error.message || 'Failed to load procedures.')}</td></tr>`;
        });
    }

    function openProcedureDetails(item) {
      let modal = document.getElementById('procedureDetailsModal');

      if (!modal) {
        modal = document.createElement('div');
        modal.id = 'procedureDetailsModal';
        modal.className = 'image-preview-modal admin-details-modal procedure-view-modal';

        modal.innerHTML = `
          <div class="image-preview-dialog admin-details-dialog" role="dialog" aria-modal="true" aria-labelledby="procedureDetailsTitle">
            <div class="image-preview-header">
              <h3 id="procedureDetailsTitle">Procedure Details</h3>
              <button type="button" class="image-preview-close" aria-label="Close procedure details">&times;</button>
            </div>
            <div class="admin-details-body procedure-details-body" id="procedureDetailsBody"></div>
          </div>
        `;

        document.body.appendChild(modal);

        modal.addEventListener('click', event => {
          if (event.target === modal || event.target.classList.contains('image-preview-close')) {
            modal.classList.remove('active');
          }
        });
      }

      document.getElementById('procedureDetailsTitle').textContent =
        item.procedure_name || 'Procedure Details';

      document.getElementById('procedureDetailsBody').innerHTML = `
        <div class="procedure-details-topline">
          <span class="procedure-chip">${escapeHtml(item.category || 'Procedure')}</span>
          ${statusBadge(item.status || 'N/A')}
        </div>

        <section class="procedure-details-section procedure-details-intro">
          <h4>Overview</h4>
          <p>${escapeHtml(item.full_description || item.short_description || 'No overview available.')}</p>
        </section>

        <div class="procedure-details-grid">
          <section class="procedure-details-section">
            <h4>Short Description</h4>
            <p>${escapeHtml(item.short_description || 'N/A')}</p>
          </section>
          <section class="procedure-details-section">
            <h4>Benefits</h4>
            <p>${escapeHtml(item.benefits || 'N/A')}</p>
          </section>
          <section class="procedure-details-section">
            <h4>Preparation Guidelines</h4>
            <p>${escapeHtml(item.preparation_guidelines || 'N/A')}</p>
          </section>
          <section class="procedure-details-section">
            <h4>Aftercare Instructions</h4>
            <p>${escapeHtml(item.aftercare_instructions || 'N/A')}</p>
          </section>
          <section class="procedure-details-section">
            <h4>Session Duration</h4>
            <p>${escapeHtml(item.session_duration || 'N/A')}</p>
          </section>
          <section class="procedure-details-section">
            <h4>Recommended Sessions</h4>
            <p>${escapeHtml(item.recommended_sessions || 'N/A')}</p>
          </section>
          <section class="procedure-details-section">
            <h4>Procedure Price</h4>
            <p>${escapeHtml(item.procedure_price || 'N/A')}</p>
          </section>
          <section class="procedure-details-section">
            <h4>Image Processing Script</h4>
            <p>${escapeHtml(item.processing_script || 'No image processor assigned')}</p>
          </section>
        </div>
      `;

      modal.classList.add('active');
    }

function ensureProcedureEditModal() {
  let modal = document.getElementById('procedureEditModal');

  if (!modal) {
    modal = document.createElement('div');
    modal.id = 'procedureEditModal';
    modal.className = 'image-preview-modal admin-details-modal procedure-edit-modal';
    modal.innerHTML = `
      <div class="image-preview-dialog admin-details-dialog" role="dialog" aria-modal="true">
        <div class="image-preview-header">
          <h3 id="procedureEditModalTitle">Edit Procedure</h3>
          <button type="button" class="image-preview-close" aria-label="Close">&times;</button>
        </div>
        <div id="procedureEditModalBody"></div>
      </div>
    `;
    document.body.appendChild(modal);

    modal.addEventListener('click', event => {
      if (event.target === modal || event.target.classList.contains('image-preview-close')) {
        closeProcedureFormModal(false);
      }
    });
  }

  return modal;
}

    function openProcedureFormModal(item) {
      const modal = ensureProcedureEditModal();
      const modalBody = modal.querySelector('#procedureEditModalBody');

      modal.querySelector('#procedureEditModalTitle').textContent = item ? 'Edit Procedure' : 'Add Procedure';

      modalBody.appendChild(form);
      fillForm(item);

      modal.classList.add('active');
    }

    if (show) show.addEventListener('click', () => openProcedureFormModal(null));
    if (cancel) cancel.addEventListener('click', () => {
      closeProcedureFormModal();
      loadProcedures();
    });
    if (search) search.addEventListener('input', render);

    body.addEventListener('click', event => {
      const button = event.target.closest('button');
      if (!button) return;

      const id = button.dataset.view || button.dataset.edit || button.dataset.toggle || button.dataset.delete;
      const item = procedures.find(row => String(row.id) === String(id));
      if (!item) return;

      if (button.dataset.view) {
        openProcedureDetails(item);
        return;
      }

      if (button.dataset.edit) {
        const modal = ensureProcedureEditModal();
        const modalBody = modal.querySelector('#procedureEditModalBody');

        modal.querySelector('#procedureEditModalTitle').textContent = 'Edit Procedure';

        modalBody.appendChild(form);
        fillForm(item);

        modal.classList.add('active');
        return;
}

      if (button.dataset.toggle) {
        const nextAction = item.status === 'Active' ? 'hide' : 'show';
        const message = item.status === 'Active'
          ? `Hide ${item.procedure_name} from the public Procedures tab?`
          : `Show ${item.procedure_name} on the public Procedures tab?`;

        if (!confirm(message)) return;

        const data = new FormData();
        data.append('id', item.id);
        data.append('action', 'toggle');

        fetch('admin-procedures.php', { method: 'POST', body: data })
          .then(response => response.json())
          .then(payload => {
            if (!payload || payload.status !== 'ok') throw new Error(payload.message || `Failed to ${nextAction} procedure.`);
            loadProcedures();
          })
          .catch(error => alert(error.message || `Failed to ${nextAction} procedure.`));
        return;
      }

      const data = new FormData();
      data.append('id', item.id);
      data.append('action', 'delete');

      if (button.dataset.delete && !confirm(`Delete ${item.procedure_name}?`)) return;

      fetch('admin-procedures.php', { method: 'POST', body: data })
        .then(response => response.json())
        .then(payload => {
          if (!payload || payload.status !== 'ok') throw new Error(payload.message || 'Request failed.');
          loadProcedures();
        })
        .catch(error => alert(error.message || 'Request failed.'));
    });

    form.addEventListener('submit', event => {
      event.preventDefault();

      const procedureName = document.getElementById('procedureName').value;

      if (!confirm(`Save changes for "${procedureName}"?`)) {
        return;
      }

      const data = new FormData();
      data.append('action', 'save');
      data.append('id', document.getElementById('procedureId').value);
      data.append('procedure_name', document.getElementById('procedureName').value);
      data.append('category', document.getElementById('procedureCategory').value);
      data.append('status', document.getElementById('procedureStatus').value);
      data.append('short_description', document.getElementById('procedureDescription').value);
      data.append('full_description', document.getElementById('procedureFullDescription').value);
      data.append('benefits', document.getElementById('procedureBenefits').value);
      data.append('preparation_guidelines', document.getElementById('procedurePreparation').value);
      data.append('aftercare_instructions', document.getElementById('procedureAftercare').value);
      data.append('session_duration', document.getElementById('procedureDuration').value);
      data.append('recommended_sessions', document.getElementById('procedureSessions').value);
      data.append('procedure_price', document.getElementById('procedurePrice').value);
      data.append('processing_script', document.getElementById('procedureScript').value);

      const image = document.getElementById('procedureImage').files[0];
      if (image) data.append('procedure_image', image);

      fetch('admin-procedures.php', { method: 'POST', body: data })
        .then(response => response.json())
        .then(payload => {
          if (!payload || payload.status !== 'ok') throw new Error(payload.message || 'Failed to save procedure.');
          form.reset();
          closeProcedureFormModal(false);

          loadProcedures();
        })
        .catch(error => alert(error.message || 'Failed to save procedure.'));
    });

    loadProcedures();
    bindProcedureReorder();
  };

})();
