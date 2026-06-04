// Super Admin module: full-system control surface.
(function () {
  function escapeHtml(value) {
    const div = document.createElement('div');
    div.textContent = value == null ? '' : String(value);
    return div.innerHTML;
  }

  function displayPath(src) {
    if (!src) return '';
    if (/^(https?:|data:|blob:|\/|\.{1,2}\/)/i.test(src)) return src;
    return `../${src}`;
  }

  function shortDate(value) {
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '';
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
  }

  function downloadCsv(filename, rows) {
    const csv = rows.map(row => row.map(value => `"${String(value ?? '').replace(/"/g, '""')}"`).join(',')).join('\r\n');
    const link = document.createElement('a');
    link.href = URL.createObjectURL(new Blob([csv], { type: 'text/csv;charset=utf-8' }));
    link.download = filename;
    link.click();
    URL.revokeObjectURL(link.href);
  }

  function ensurePatientModal() {
    let modal = document.getElementById('patientRecordModal');
    if (modal) return modal;

    modal = document.createElement('div');
    modal.id = 'patientRecordModal';
    modal.className = 'image-preview-modal admin-details-modal patient-record-modal';
    modal.innerHTML = `
      <div class="image-preview-dialog admin-details-dialog" role="dialog" aria-modal="true" aria-labelledby="patientRecordTitle">
        <div class="image-preview-header">
          <h3 id="patientRecordTitle">Patient Record</h3>
          <button type="button" class="image-preview-close" aria-label="Close patient record">&times;</button>
        </div>
        <div class="admin-details-body" id="patientRecordBody"></div>
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

  window.initPatientRecords = function () {
    const body = document.getElementById('patientsTableBody');
    const search = document.getElementById('patientsSearch');
    const procedureFilter = document.getElementById('patientsProcedureFilter');
    const activityFilter = document.getElementById('patientsActivityFilter');
    const exportBtn = document.getElementById('exportPatientsCsv');

    if (!body) return;

    let patients = [];

    function populateProcedureFilter() {
      if (!procedureFilter) return;
      const current = procedureFilter.value;
      const procedures = Array.from(new Set(patients.flatMap(patient => patient.treatment_history || []))).filter(Boolean).sort();
      procedureFilter.innerHTML = '<option value="">All treatments</option>' + procedures.map(name => `<option>${escapeHtml(name)}</option>`).join('');
      procedureFilter.value = current;
    }

    function filteredPatients() {
      const query = search ? search.value.trim().toLowerCase() : '';
      const procedure = procedureFilter ? procedureFilter.value : '';
      const activity = activityFilter ? activityFilter.value : '';

      return patients.filter(patient => {
        const haystack = `${patient.patient_name} ${patient.email} ${patient.phone} ${(patient.treatment_history || []).join(' ')} ${patient.notes}`.toLowerCase();
        return (!query || haystack.includes(query)) &&
          (!procedure || (patient.treatment_history || []).includes(procedure)) &&
          (!activity ||
            (activity === 'appointments' && patient.consultations.length) ||
            (activity === 'images' && patient.uploaded_images.length) ||
            (activity === 'notes' && patient.notes));
      });
    }

    function render() {
      const rows = filteredPatients();
      body.innerHTML = rows.length ? rows.map(patient => `
        <tr>
          <td><strong>${escapeHtml(patient.patient_name)}</strong></td>
          <td>${escapeHtml(patient.phone || 'N/A')}<br><span class="table-muted">${escapeHtml(patient.email || '')}</span></td>
          <td>${escapeHtml(patient.consultations.length)}</td>
          <td>${escapeHtml(patient.uploaded_images.length)}</td>
          <td>${escapeHtml((patient.treatment_history || []).slice(0, 3).join(', ') || 'N/A')}</td>
          <td>${escapeHtml(shortDate(patient.last_activity))}</td>
          <td><button type="button" class="account-action-btn reactivate-btn" data-patient="${escapeHtml(patient.patient_key)}">View</button></td>
        </tr>
      `).join('') : '<tr><td colspan="7" class="accounts-empty-cell">No patient records found.</td></tr>';
    }

    function openPatient(patient) {
      const modal = ensurePatientModal();
      modal.querySelector('#patientRecordTitle').textContent = patient.patient_name;

      const images = (patient.uploaded_images || []).slice(0, 6).map(image => `
        <figure>
          ${image.before ? `<img src="${escapeHtml(displayPath(image.before))}" alt="Uploaded before image">` : '<div class="admin-image-placeholder">No image</div>'}
          <figcaption>${escapeHtml(image.procedure || 'Uploaded image')}<br><span class="table-muted">${escapeHtml(shortDate(image.date))}</span></figcaption>
        </figure>
      `).join('');

      modal.querySelector('#patientRecordBody').innerHTML = `
        <dl class="admin-details-list">
          <div><dt>Patient Name</dt><dd>${escapeHtml(patient.patient_name)}</dd></div>
          <div><dt>Contact</dt><dd>${escapeHtml(patient.phone || 'N/A')} ${patient.email ? `<br>${escapeHtml(patient.email)}` : ''}</dd></div>
          <div><dt>Consultation History</dt><dd>${patient.consultations.map(item => `${escapeHtml(shortDate(item.date))} - ${escapeHtml(item.procedure)} (${escapeHtml(item.status)})`).join('<br>') || 'No consultations recorded.'}</dd></div>
          <div><dt>Treatment History</dt><dd>${escapeHtml((patient.treatment_history || []).join(', ') || 'No treatments recorded.')}</dd></div>
        </dl>
        <div class="patient-image-grid">${images || '<p class="table-muted">No uploaded images recorded.</p>'}</div>
        <label class="accounts-field accounts-field-full patient-notes-field">
          <span>Patient Notes</span>
          <textarea id="patientNotesInput" class="accounts-input">${escapeHtml(patient.notes || '')}</textarea>
        </label>
        <div class="admin-button-row">
          <button type="button" class="accounts-submit" id="savePatientNotes">Save Notes</button>
        </div>
      `;

      modal.querySelector('#savePatientNotes')?.addEventListener('click', () => {
        const data = new FormData();
        data.append('action', 'save_note');
        data.append('patient_key', patient.patient_key);
        data.append('notes', modal.querySelector('#patientNotesInput').value);

        fetch('admin-patients.php', { method: 'POST', body: data })
          .then(response => response.json())
          .then(payload => {
            if (!payload || payload.status !== 'ok') throw new Error(payload.message || 'Failed to save notes.');
            patient.notes = modal.querySelector('#patientNotesInput').value;
            render();
            alert('Patient notes saved.');
          })
          .catch(error => alert(error.message || 'Failed to save notes.'));
      });

      modal.classList.add('active');
    }

    function loadPatients() {
      const data = new FormData();
      data.append('action', 'fetch');

      fetch('admin-patients.php', { method: 'POST', body: data })
        .then(response => response.json())
        .then(payload => {
          if (!payload || payload.status !== 'ok') throw new Error(payload.message || 'Failed to load patients.');
          patients = payload.patients || [];
          populateProcedureFilter();
          render();
        })
        .catch(error => {
          body.innerHTML = `<tr><td colspan="7" class="accounts-empty-cell">${escapeHtml(error.message || 'Failed to load patients.')}</td></tr>`;
        });
    }

    [search, procedureFilter, activityFilter].forEach(input => {
      if (input) input.addEventListener('input', render);
      if (input) input.addEventListener('change', render);
    });

    body.addEventListener('click', event => {
      const button = event.target.closest('[data-patient]');
      if (!button) return;
      const patient = patients.find(item => item.patient_key === button.dataset.patient);
      if (patient) openPatient(patient);
    });

    if (exportBtn) {
      exportBtn.addEventListener('click', () => {
        downloadCsv('patient_records.csv', [
          ['Patient Name', 'Email', 'Phone', 'Consultations', 'Uploaded Images', 'Treatments', 'Last Activity', 'Notes'],
          ...filteredPatients().map(patient => [
            patient.patient_name,
            patient.email,
            patient.phone,
            patient.consultations.length,
            patient.uploaded_images.length,
            (patient.treatment_history || []).join('; '),
            patient.last_activity,
            patient.notes
          ])
        ]);
      });
    }

    loadPatients();
  };
})();
