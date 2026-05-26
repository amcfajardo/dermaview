(function () {
  const storageKey = 'dermaview.admin.systemSettings';
  const defaultClinicName = 'DermaView';

  function escapeHtml(value) {
    const div = document.createElement('div');
    div.textContent = value == null ? '' : String(value);
    return div.innerHTML;
  }

  function loadSettings() {
    try {
      return JSON.parse(localStorage.getItem(storageKey) || '{}');
    } catch (error) {
      return {};
    }
  }

  function saveCachedSettings(settings) {
    localStorage.setItem(storageKey, JSON.stringify(settings || {}));
  }

  function settingsEndpoint() {
    const path = window.location.pathname;
    return path.includes('/pages/') || path.includes('/admin_pages/') || path.includes('/super_admin/')
      ? '../system-settings.php'
      : 'system-settings.php';
  }

  async function refreshSettings(options = {}) {
    try {
      const cachedSettings = loadSettings();
      const response = await fetch(settingsEndpoint(), { cache: 'no-store' });
      const payload = await response.json();
      if (payload.status === 'ok' && payload.settings) {
        const hasCachedSettings = Object.keys(cachedSettings).length > 0;
        const settings = payload.exists === false && hasCachedSettings
          ? cachedSettings
          : payload.settings;

        saveCachedSettings(settings);
        applyThemeFromSettings(settings);
        applyBranding(settings, options);
        return settings;
      }
    } catch (error) {}

    return loadSettings();
  }

  function clinicInitials(name) {
    const words = String(name || defaultClinicName).trim().split(/\s+/).filter(Boolean);
    if (!words.length) return 'D';
    if (words.length === 1) return words[0].charAt(0).toUpperCase();
    return (words[0].charAt(0) + words[1].charAt(0)).toUpperCase();
  }

  function applyBranding(settings = loadSettings(), options = {}) {
    const clinicName = (settings.clinicName || defaultClinicName).trim() || defaultClinicName;
    const logo = settings.logo || '';

    document.querySelectorAll('.brand-name').forEach(brandName => {
      brandName.textContent = clinicName;
    });

    document.querySelectorAll('.brand-mark').forEach(brandMark => {
      brandMark.innerHTML = logo
        ? `<img class="brand-logo" src="${escapeHtml(logo)}" alt="${escapeHtml(clinicName)} logo" style="width:100%;height:100%;max-width:100%;max-height:100%;display:block;object-fit:contain;">`
        : clinicInitials(clinicName);
    });

    if (options.updateTitle !== false) {
      document.title = options.titleSuffix ? `${clinicName} ${options.titleSuffix}` : clinicName;
    }
  }

  function applyThemeFromSettings(settings = loadSettings()) {
    const allowedThemes = new Set(['light', 'clinical', 'dark', 'contrast']);
    const theme = allowedThemes.has(settings.defaultTheme) ? settings.defaultTheme : 'light';
    document.documentElement.dataset.theme = theme;
    return theme;
  }

  window.DermaViewBranding = {
    defaultClinicName,
    storageKey,
    loadSettings,
    saveCachedSettings,
    refreshSettings,
    clinicInitials,
    applyBranding,
    applyThemeFromSettings
  };

  applyThemeFromSettings();
  applyBranding();
  refreshSettings({ updateTitle: false });
})();
