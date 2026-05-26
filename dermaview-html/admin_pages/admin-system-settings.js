(function () {
  const storageKey = 'dermaview.admin.systemSettings';
  const defaultClinicName = 'DermaView';

  function escapeHtml(value) {
    const div = document.createElement('div');
    div.textContent = value == null ? '' : String(value);
    return div.innerHTML;
  }

  function fileToDataUrl(file) {
    return new Promise(resolve => {
      if (!file) {
        resolve('');
        return;
      }

      const reader = new FileReader();
      reader.onload = () => {
        const image = new Image();
        image.onload = () => {
          const maxSize = 320;
          const scale = Math.min(1, maxSize / Math.max(image.width, image.height));
          const width = Math.max(1, Math.round(image.width * scale));
          const height = Math.max(1, Math.round(image.height * scale));
          const canvas = document.createElement('canvas');
          canvas.width = width;
          canvas.height = height;
          const context = canvas.getContext('2d');
          context.clearRect(0, 0, width, height);
          context.drawImage(image, 0, 0, width, height);
          resolve(canvas.toDataURL('image/webp', 0.82));
        };
        image.onerror = () => resolve(reader.result || '');
        image.src = reader.result || '';
      };
      reader.onerror = () => resolve('');
      reader.readAsDataURL(file);
    });
  }

  function loadSettings() {
    try {
      return JSON.parse(localStorage.getItem(storageKey) || '{}');
    } catch (error) {
      return {};
    }
  }

  function saveSettings(data) {
    localStorage.setItem(storageKey, JSON.stringify(data));
  }

  function settingsEndpoint() {
    return '../system-settings.php';
  }

  async function fetchSavedSettings() {
    try {
      const cachedSettings = loadSettings();
      const response = await fetch(settingsEndpoint(), { cache: 'no-store' });
      const payload = await response.json();
      if (payload.status === 'ok' && payload.settings) {
        const hasCachedSettings = Object.keys(cachedSettings).length > 0;
        const settings = payload.exists === false && hasCachedSettings
          ? cachedSettings
          : payload.settings;

        saveSettings(settings);
        return settings;
      }
    } catch (error) {}

    return loadSettings();
  }

  async function persistSettings(settings) {
    const response = await fetch(settingsEndpoint(), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(settings)
    });
    const text = await response.text();
    let payload = null;
    try {
      payload = JSON.parse(text);
    } catch (error) {
      throw new Error('Unable to save system settings. Please try a smaller logo image.');
    }
    if (!response.ok || payload.status !== 'ok') {
      throw new Error(payload.message || 'Unable to save system settings.');
    }
    saveSettings(payload.settings || settings);
    return payload.settings || settings;
  }

  function clinicInitials(name) {
    const words = String(name || defaultClinicName).trim().split(/\s+/).filter(Boolean);
    if (!words.length) return 'D';
    if (words.length === 1) return words[0].charAt(0).toUpperCase();
    return (words[0].charAt(0) + words[1].charAt(0)).toUpperCase();
  }

  function setValue(id, value) {
    const field = document.getElementById(id);
    if (field) field.value = value || '';
  }

  function renderLogoPreview(src) {
    const preview = document.getElementById('clinicLogoPreview');
    if (!preview) return;

    preview.innerHTML = src
      ? `<img src="${escapeHtml(src)}" alt="Clinic logo preview">`
      : clinicInitials(document.getElementById('clinicName')?.value || defaultClinicName);
  }

  function applySystemSettings(settings = loadSettings()) {
    const clinicName = (settings.clinicName || defaultClinicName).trim() || defaultClinicName;
    const logo = settings.logo || '';
    const brandName = document.querySelector('.brand-name');
    const brandMark = document.querySelector('.brand-mark');

    if (brandName) {
      brandName.textContent = clinicName;
    }

    if (brandMark) {
      brandMark.innerHTML = logo
        ? `<img class="brand-logo" src="${escapeHtml(logo)}" alt="${escapeHtml(clinicName)} logo" style="width:100%;height:100%;max-width:100%;max-height:100%;display:block;object-fit:contain;">`
        : clinicInitials(clinicName);
    }

    document.title = `${clinicName} Admin Dashboard`;
    window.DermaViewBranding?.applyThemeFromSettings(settings);
  }

  window.applySystemSettings = applySystemSettings;
  applySystemSettings();

  window.initSystemSettings = async function () {
    const form = document.getElementById('systemSettingsForm');
    const logoInput = document.getElementById('clinicLogo');

    if (!form) return;

    const settings = await fetchSavedSettings();
    setValue('clinicName', settings.clinicName || 'DermaView');
    setValue('contactInfo', settings.contactInfo || '');
    setValue('clinicEmail', settings.clinicEmail || '');
    setValue('clinicContactNumber', settings.clinicContactNumber || '');
    setValue('businessHours', settings.businessHours || '');
    setValue('appointmentSlots', settings.appointmentSlots || '');
    setValue('sessionTimeout', settings.sessionTimeout || '30');
    setValue('defaultTheme', settings.defaultTheme || 'light');
    setValue('maintenanceMode', settings.maintenanceMode || 'off');
    setValue('emailSender', settings.emailSender || '');
    setValue('emailReplyTo', settings.emailReplyTo || '');
    setValue('reportFooter', settings.reportFooter || 'Generated by DermaView. Results may vary per patient.');
    setValue('uploadSizeLimit', settings.uploadSizeLimit || '10 MB');
    setValue('allowedImageTypes', settings.allowedImageTypes || 'JPG, PNG, WEBP');
    setValue('imageRetentionPeriod', settings.imageRetentionPeriod || '180 days');
    setValue('emailNotifications', settings.emailNotifications || 'enabled');
    renderLogoPreview(settings.logo || '');
    applySystemSettings(settings);

    document.getElementById('clinicName')?.addEventListener('input', () => {
      if (!logoInput || !logoInput.files[0]) {
        renderLogoPreview(settings.logo || '');
      }
    });

    if (logoInput) {
      logoInput.addEventListener('change', async () => {
        renderLogoPreview(await fileToDataUrl(logoInput.files[0]));
      });
    }

    async function handleSave(event) {
      if (event) event.preventDefault();
      try {
        const current = loadSettings();
        const logo = logoInput && logoInput.files[0]
          ? await fileToDataUrl(logoInput.files[0])
          : current.logo || '';

        const nextSettings = {
          clinicName: document.getElementById('clinicName').value.trim() || defaultClinicName,
          contactInfo: document.getElementById('contactInfo').value.trim(),
          clinicEmail: document.getElementById('clinicEmail').value.trim(),
          clinicContactNumber: document.getElementById('clinicContactNumber').value.trim(),
          businessHours: document.getElementById('businessHours').value.trim(),
          appointmentSlots: document.getElementById('appointmentSlots').value.trim(),
          sessionTimeout: document.getElementById('sessionTimeout').value,
          defaultTheme: document.getElementById('defaultTheme').value,
          maintenanceMode: document.getElementById('maintenanceMode').value,
          emailSender: document.getElementById('emailSender').value.trim(),
          emailReplyTo: document.getElementById('emailReplyTo').value.trim(),
          reportFooter: document.getElementById('reportFooter').value.trim(),
          uploadSizeLimit: document.getElementById('uploadSizeLimit').value.trim(),
          allowedImageTypes: document.getElementById('allowedImageTypes').value.trim(),
          imageRetentionPeriod: document.getElementById('imageRetentionPeriod').value.trim(),
          emailNotifications: document.getElementById('emailNotifications').value,
          logo
        };

        const savedSettings = await persistSettings(nextSettings);

        renderLogoPreview(savedSettings.logo || logo);
        applySystemSettings(savedSettings);
        window.DermaViewBranding?.applyBranding(savedSettings, { titleSuffix: 'Admin Dashboard' });
        alert('System settings saved.');
      } catch (error) {
        alert(error.message || 'Unable to save system settings.');
      }
    }

    form.addEventListener('submit', handleSave);
  };
})();
