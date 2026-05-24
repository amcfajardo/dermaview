(function () {
  const keys = {
    procedures: 'dermaview.admin.procedures',
    references: 'dermaview.admin.references',
    settings: 'dermaview.admin.processingSettings',
    records: 'dermaview.admin.records'
  };

  const scripts = {
    'CO2 Fractional Laser + Dermapen': 'process_co2_dermapen.py',
    'Face Slimming Package': 'process_face_slimming.py',
    'Diamond Peel with Facial': 'process_diamond_peel.py',
    'Undereye and Lip Filler': 'process_undereye_lip_filler.py',
    'PICO Carbon Laser Facial': 'process_pico_carbon_laser.py',
    'Lip Filler, Chin Filler, and Jawtox': 'process_lip_chin_jawtox.py',
    'General Skin Assessment': 'process_general_skin_assessment.py'
  };

  const seedProcedures = [
    ['CO2 Fractional Laser + Dermapen', 'Laser', 'Combined resurfacing and microneedling for texture, scars, and rejuvenation.'],
    ['Face Slimming Package', 'Contouring', 'Non-surgical contouring plan for facial definition and balance.'],
    ['Diamond Peel with Facial', 'Facial', 'Gentle exfoliation with cleansing facial care for smoother-looking skin.'],
    ['Undereye and Lip Filler', 'Filler', 'Targeted filler service for undereye support and lip enhancement.'],
    ['PICO Carbon Laser Facial', 'Skin Rejuvenation', 'Carbon-assisted laser facial for tone, pores, and brightness.'],
    ['Lip Filler, Chin Filler, and Jawtox', 'Filler', 'Profile-balancing injectables for lips, chin, and jawline tension.'],
    ['General Skin Assessment', 'Acne Treatment', 'Consultation-based assessment for personalized treatment planning.']
  ].map((item, index) => ({
    id: `proc-${index + 1}`,
    name: item[0],
    category: item[1],
    description: item[2],
    fullDescription: `${item[0]} includes consultation, skin review, and treatment planning based on patient needs.`,
    benefits: 'Improves patient awareness, supports treatment planning, and documents expected care steps.',
    preparation: 'Arrive with clean skin and disclose recent procedures, medication, and allergies.',
    aftercare: 'Follow staff instructions, avoid harsh actives when advised, and use sun protection.',
    duration: index === 6 ? '30 minutes' : '45-90 minutes',
    sessions: index === 6 ? '1 session' : '3-5 sessions',
    status: 'Active',
    image: '',
    updatedAt: new Date(Date.now() - index * 86400000).toISOString()
  }));

  function escapeHtml(value) {
    const div = document.createElement('div');
    div.textContent = value == null ? '' : String(value);
    return div.innerHTML;
  }

  function load(key, fallback) {
    try {
      const raw = localStorage.getItem(key);
      return raw ? JSON.parse(raw) : fallback;
    } catch (error) {
      return fallback;
    }
  }

  function save(key, value) {
    localStorage.setItem(key, JSON.stringify(value));
  }

  function procedures() {
    const items = load(keys.procedures, null);
    if (items) return items;
    save(keys.procedures, seedProcedures);
    return seedProcedures.slice();
  }

  function references() {
    const items = load(keys.references, null);
    if (items) return items;
    const seeded = procedures().slice(0, 3).map((procedure, index) => ({
      id: `ref-${index + 1}`,
      procedureId: procedure.id,
      procedureName: procedure.name,
      type: index === 1 ? 'Reference image' : 'Before-and-after sample',
      beforeImage: '',
      afterImage: '',
      caption: `${procedure.name} awareness sample. Results may vary per patient.`,
      consent: 'Clinic-owned sample with consent note on file.',
      disclaimer: 'Results may vary per patient.',
      status: 'Active',
      uploadedAt: new Date(Date.now() - index * 172800000).toISOString()
    }));
    save(keys.references, seeded);
    return seeded;
  }

  function records() {
    const items = load(keys.records, null);
    if (items) return items;
    const seeded = procedures().slice(0, 5).map((procedure, index) => ({
      id: `REC-${String(index + 1).padStart(4, '0')}`,
      date: new Date(Date.now() - index * 7200000).toISOString(),
      procedure: procedure.name,
      originalImage: '',
      processedImage: '',
      status: ['Completed', 'Pending', 'Failed', 'Completed', 'Deleted'][index],
      handledBy: index % 2 ? 'Staff User' : 'Admin User',
      notes: index === 2 ? 'Processing attempt failed; image quality was too low.' : 'Consultation record reviewed.'
    }));
    save(keys.records, seeded);
    return seeded;
  }

  function settings() {
    const current = load(keys.settings, null);
    if (current) return current;
    const initial = {
      enabled: 'Yes',
      brightness: 100,
      contrast: 105,
      sharpness: 110,
      smoothing: 20,
      quality: 90,
      maxSize: '10 MB',
      types: 'JPG, PNG, JPEG',
      outputFolder: 'processed_uploads/',
      resizeLimit: '1600 px',
      retention: '90 days',
      showDisclaimer: 'Yes',
      disclaimer: 'Image processing previews are for awareness and documentation only. Results may vary per patient.',
      mappings: Object.entries(scripts).map(([name, script]) => `${name}: ${script}`).join('\n'),
      moduleStatus: {}
    };
    procedures().forEach(item => {
      initial.moduleStatus[item.id] = true;
    });
    save(keys.settings, initial);
    return initial;
  }

  function shortDate(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '';
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  }

  function fileToDataUrl(file) {
    return new Promise(resolve => {
      if (!file) {
        resolve('');
        return;
      }
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result || '');
      reader.onerror = () => resolve('');
      reader.readAsDataURL(file);
    });
  }

  function statusBadge(status) {
    const name = String(status || '').toLowerCase().replace(/\s+/g, '-');
    return `<span class="account-status account-status-${escapeHtml(name)}">${escapeHtml(status)}</span>`;
  }

  function placeholderImage(label) {
    return `<div class="admin-image-placeholder">${escapeHtml(label)}</div>`;
  }

  function imageCell(src, label) {
    return src
      ? `<img class="admin-thumb" src="${escapeHtml(src)}" alt="${escapeHtml(label)}" data-preview-image data-preview-title="${escapeHtml(label)}" tabindex="0">`
      : placeholderImage(label);
  }

  function bindPreview(root) {
    root.querySelectorAll('[data-preview-image]').forEach(image => {
      image.addEventListener('click', () => openPreview(image.src, image.dataset.previewTitle || image.alt));
      image.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          openPreview(image.src, image.dataset.previewTitle || image.alt);
        }
      });
    });
  }

  function openPreview(src, title) {
    let modal = document.getElementById('processedImagePreviewModal');
    if (!modal) {
      modal = document.createElement('div');
      modal.id = 'processedImagePreviewModal';
      modal.className = 'image-preview-modal';
      modal.innerHTML = `<div class="image-preview-dialog" role="dialog" aria-modal="true">
        <div class="image-preview-header"><h3>${escapeHtml(title || 'Image Preview')}</h3><button type="button" class="image-preview-close">&times;</button></div>
        <img src="" alt="">
      </div>`;
      document.body.appendChild(modal);
      modal.addEventListener('click', event => {
        if (event.target === modal || event.target.classList.contains('image-preview-close')) {
          modal.classList.remove('active');
        }
      });
    }
    modal.querySelector('h3').textContent = title || 'Image Preview';
    modal.querySelector('img').src = src;
    modal.classList.add('active');
  }

  function downloadCsv(filename, rows) {
    const csv = rows.map(row => row.map(value => `"${String(value ?? '').replace(/"/g, '""')}"`).join(',')).join('\n');
    const link = document.createElement('a');
    link.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv' }));
    link.download = filename;
    link.click();
    URL.revokeObjectURL(link.href);
  }

  function ensureProcedureDetailsModal() {
    let modal = document.getElementById('procedureDetailsModal');

    if (modal) {
      return modal;
    }

    modal = document.createElement('div');
    modal.id = 'procedureDetailsModal';
    modal.className = 'image-preview-modal admin-details-modal procedure-edit-modal';
    modal.innerHTML = `
      <div class="image-preview-dialog admin-details-dialog" role="dialog" aria-modal="true" aria-labelledby="procedureDetailsTitle">
        <div class="image-preview-header">
          <h3 id="procedureDetailsTitle">Procedure Details</h3>
          <button type="button" class="image-preview-close" aria-label="Close procedure details">&times;</button>
        </div>
        <div class="admin-details-body" id="procedureDetailsBody"></div>
      </div>
    `;
    document.body.appendChild(modal);

    modal.addEventListener('click', event => {
      if (event.target === modal || event.target.classList.contains('image-preview-close')) {
        modal.classList.remove('active');
      }
    });

    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && modal.classList.contains('active')) {
        modal.classList.remove('active');
      }
    });

    return modal;
  }

  function openProcedureDetails(item) {
    const modal = ensureProcedureDetailsModal();
    modal.querySelector('#procedureDetailsTitle').textContent = item.procedure_name || 'Procedure Details';

    // Add an Edit button inside the popup
    modal.querySelector('#procedureDetailsBody').innerHTML = `
      <div class="admin-details-summary">
        <span class="procedure-chip">${escapeHtml(item.category || 'Procedure')}</span>
        ${statusBadge(item.status)}
      </div>

      <p>${escapeHtml(item.full_description || item.short_description || '')}</p>

      <div class="admin-button-row" style="margin-top: 10px; margin-bottom: 6px;">
        <button type="button" class="accounts-create-btn" id="editProcedureFromPopup">Edit This Procedure</button>
      </div>

      <dl class="admin-details-list">
        <div><dt>Short Description</dt><dd>${escapeHtml(item.short_description || 'N/A')}</dd></div>
        <div><dt>Benefits</dt><dd>${escapeHtml(item.benefits || 'N/A')}</dd></div>
        <div><dt>Preparation</dt><dd>${escapeHtml(item.preparation_guidelines || 'N/A')}</dd></div>
        <div><dt>Aftercare</dt><dd>${escapeHtml(item.aftercare_instructions || 'N/A')}</dd></div>
        <div><dt>Session Duration</dt><dd>${escapeHtml(item.session_duration || 'N/A')}</dd></div>
        <div><dt>Recommended Sessions</dt><dd>${escapeHtml(item.recommended_sessions || 'N/A')}</dd></div>
        <div><dt>Date Updated</dt><dd>${escapeHtml(formatDate(item.updated_at))}</dd></div>
      </dl>
    `;

    modal.classList.add('active');

    // Wire Edit from popup to in-page edit form
    const editBtn = modal.querySelector('#editProcedureFromPopup');
    if (editBtn) {
      editBtn.addEventListener('click', () => {
        // close popup and show edit form
        try { modal.classList.remove('active'); } catch (e) {}

        // Prefer current initManageProcedures popup edit helper
        if (typeof window.__procedureFillFormFromPopup === 'function') {
          window.__procedureFillFormFromPopup(item);
          return;
        }

        // Fallback: open the form and populate fields from whatever shape we have
        const form = document.getElementById('procedureForm');
        if (form) form.hidden = false;
      });
    }

    modal.querySelector('.image-preview-close').focus();
  }



  window.initProcessingSettings = function () {
    const form = document.getElementById('visualizationSettingsForm');
    const body = document.getElementById('visualizationProcedureBody');
    const saveTop = document.getElementById('saveVisualizationSettingsTop');

    if (!form || !body) return;

    const storageKey = 'dermaview.admin.visualizationSettings';
    const fallbackCounts = [12, 8, 5, 7, 4, 6, 3];

    function loadSettings() {
      try {
        return JSON.parse(localStorage.getItem(storageKey)) || {};
      } catch (error) {
        return {};
      }
    }

    function saveSettings(data) {
      localStorage.setItem(storageKey, JSON.stringify(data));
    }

    function collectSettings() {
      const procedureStatus = {};
      body.querySelectorAll('[data-visualization-status]').forEach(input => {
        procedureStatus[input.dataset.visualizationStatus] = input.checked;
      });

      return {
        enableTreatmentVisualization: document.getElementById('enableTreatmentVisualization').checked,
        enableBeforeAfterComparison: document.getElementById('enableBeforeAfterComparison').checked,
        showSideBySideComparison: document.getElementById('showSideBySideComparison').checked,
        showTreatmentDisclaimer: document.getElementById('showTreatmentDisclaimer').checked,
        disclaimer: document.getElementById('visualizationDisclaimer').value,
        allowedTypes: document.getElementById('visualizationAllowedTypes').value,
        maxUpload: document.getElementById('visualizationMaxUpload').value,
        procedureStatus
      };
    }

    function applySettings(data) {
      document.getElementById('enableTreatmentVisualization').checked = data.enableTreatmentVisualization !== false;
      document.getElementById('enableBeforeAfterComparison').checked = data.enableBeforeAfterComparison !== false;
      document.getElementById('showSideBySideComparison').checked = data.showSideBySideComparison !== false;
      document.getElementById('showTreatmentDisclaimer').checked = data.showTreatmentDisclaimer !== false;
      document.getElementById('visualizationDisclaimer').value = data.disclaimer || 'These visualizations are for consultation support and treatment awareness only.\nActual results may vary per patient.';
      document.getElementById('visualizationAllowedTypes').value = data.allowedTypes || 'JPG, PNG';
      document.getElementById('visualizationMaxUpload').value = data.maxUpload || '10 MB';
    }

    function renderProcedures(items, data) {
      const procedureStatus = data.procedureStatus || {};

      body.innerHTML = items.length ? items.map((item, index) => {
        const id = item.id || item.databaseId || `procedure-${index}`;
        const enabled = procedureStatus[id] !== false;
        const count = fallbackCounts[index % fallbackCounts.length];

        return `
          <tr>
            <td><strong>${escapeHtml(item.name || item.procedure_name)}</strong></td>
            <td>
              <label class="visualization-status-toggle">
                <input type="checkbox" data-visualization-status="${escapeHtml(id)}" ${enabled ? 'checked' : ''}>
                <span>${enabled ? 'Enabled' : 'Disabled'}</span>
              </label>
            </td>
            <td>${count} Images</td>
            <td>
              <div class="visualization-row-actions">
                <button type="button" data-visualization-edit="${escapeHtml(id)}">Edit</button>
                <button type="button" data-visualization-preview="${escapeHtml(id)}">Preview</button>
                <button type="button" data-visualization-disable="${escapeHtml(id)}">${enabled ? 'Disable' : 'Enable'}</button>
              </div>
            </td>
          </tr>
        `;
      }).join('') : '<tr><td colspan="4" class="accounts-empty-cell">No procedures found.</td></tr>';
    }

    function loadProcedureRows(data) {
      const formData = new FormData();
      formData.append('action', 'fetch');

      fetch('admin-procedures.php', { method: 'POST', body: formData })
        .then(response => response.json())
        .then(payload => {
          const items = payload && payload.status === 'ok'
            ? payload.procedures.map(item => ({
                id: item.id,
                name: item.procedure_name
              }))
            : procedures();
          renderProcedures(items, data);
        })
        .catch(() => {
          renderProcedures(procedures(), data);
        });
    }

    function persistAndNotify() {
      saveSettings(collectSettings());
      alert('Visualization settings saved.');
    }

    const data = loadSettings();
    applySettings(data);
    loadProcedureRows(data);

    body.addEventListener('change', event => {
      if (!event.target.matches('[data-visualization-status]')) return;
      const label = event.target.closest('.visualization-status-toggle');
      const text = label ? label.querySelector('span') : null;
      if (text) text.textContent = event.target.checked ? 'Enabled' : 'Disabled';
    });

    body.addEventListener('click', event => {
      const button = event.target.closest('button');
      if (!button) return;

      const id = button.dataset.visualizationDisable || button.dataset.visualizationEdit || button.dataset.visualizationPreview;
      const row = button.closest('tr');
      const name = row ? row.querySelector('td strong')?.textContent || 'this procedure' : 'this procedure';
      const toggle = row ? row.querySelector('[data-visualization-status]') : null;

      if (button.dataset.visualizationDisable && toggle) {
        toggle.checked = !toggle.checked;
        toggle.dispatchEvent(new Event('change', { bubbles: true }));
        button.textContent = toggle.checked ? 'Disable' : 'Enable';
        return;
      }

      if (button.dataset.visualizationPreview) {
        alert(`${name}\n\nPreview opens the patient-facing visualization workflow for review.`);
        return;
      }

      if (button.dataset.visualizationEdit) {
        alert(`${name}\n\nUse the procedure management page to edit details and comparison images.`);
      }
    });

    form.addEventListener('submit', event => {
      event.preventDefault();
      persistAndNotify();
    });

    if (saveTop) {
      saveTop.addEventListener('click', persistAndNotify);
    }
  };

})();
