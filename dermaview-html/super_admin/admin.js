document.addEventListener('DOMContentLoaded', function () {
  const nav = document.getElementById('adminNav');
  if (!nav) return;

  const links = nav.querySelectorAll('a[data-page]');
  const pageTitle = document.getElementById('pageTitle');
  const pageContent = document.getElementById('pageContent');
  const sessionWelcome = document.getElementById('sessionWelcome');

  const titles = {
    dashboard: 'Super Admin Dashboard',
    adminAccounts: 'Manage Admin Accounts',
    staff: 'Manage Staff / Employee Accounts',
    roles: 'Role and Permission Management',
    appointments: 'Appointments',
    patients: 'Patient Records',
    activity: 'Activity Logs',
    procedures: 'Manage Procedures',
    processing: 'Image Processing Settings',
    system: 'System Settings',
    records: 'Consultation / Image Records',
    reports: 'Reports',
    privacy: 'Privacy / Data Management',
    backup: 'Backup and Restore'
  };

  const pages = {
    dashboard: {
      init: function () {
        window.initAdminDashboard(pageContent);
      }
    },
    staff: {
      url: 'admin-accounts.html',
      init: window.initManageAccounts
    },
    adminAccounts: {
      url: 'admin-admin-accounts.html',
      init: window.initManageAccounts
    },
    roles: {
      url: 'admin-roles-permissions.html',
      init: window.initRolePermissions
    },
    appointments: {
      url: 'admin-appointments.html',
      init: window.initManageAppointments
    },
    patients: {
      url: 'admin-patients.html',
      init: window.initPatientRecords
    },
    activity: {
      url: 'admin-activity.html',
      init: window.initActivityLogs
    },
    procedures: {
      url: 'admin-procedures.html',
      init: window.initManageProcedures
    },
    processing: {
      url: 'admin-processing-settings.html',
      init: window.initProcessingSettings
    },
    system: {
      url: 'admin-system-settings.html',
      init: window.initSystemSettings
    },
    records: {
      url: 'admin-consultation-records.html',
      init: window.initConsultationRecords
    },
    reports: {
      url: 'admin-reports.html',
      init: window.initReports
    },
    privacy: {
      url: 'admin-privacy-data.html',
      init: window.initPrivacyDataManagement
    },
    backup: {
      url: 'admin-backup-restore.html',
      init: window.initBackupRestore
    }
  };

  const descriptions = {
    dashboard: 'Full system summary across users, appointments, patients, images, staff, alerts, and system health.',
    adminAccounts: 'Create, edit, deactivate, reset, and review administrator access.',
    staff: 'Manage staff accounts.',
    roles: 'Control access rules for every user type.',
    appointments: 'View and control clinic appointments across all staff and patient schedules.',
    patients: 'Review patient profiles, histories, images, and exportable records.',
    activity: 'Audit important account, appointment, procedure, image, report, and settings actions.',
    procedures: 'Manage procedure catalog details, pricing, images, availability, and script mapping.',
    processing: 'Configure image processing defaults, folders, quality, disclaimers, and procedure mappings.',
    system: 'Set clinic identity, contact details, hours, notifications, upload rules, and retention.',
    records: 'Inspect uploaded and processed image records, selected procedures, dates, and staff handling.',
    reports: 'Generate appointment, patient, procedure, processed image, staff activity, and monthly reports.',
    privacy: 'Manage retention rules, consent notes, cleanup history, inactive records, and privacy policy printing.',
    backup: 'Create backup manifests, download history, and record restore requests.'
  };

  const pageAliases = {
    accounts: 'staff',
    employees: 'staff',
    'staff-accounts': 'staff',
    'admin-accounts': 'adminAccounts',
    adminaccounts: 'adminAccounts',
    admins: 'adminAccounts',
    permissions: 'roles',
    'roles-permissions': 'roles',
    procedure: 'procedures',
    'procedure-management': 'procedures',
    'image-processing-settings': 'processing',
    settings: 'system',
    'system-settings': 'system',
    'privacy-data': 'privacy',
    restore: 'backup',
    'backup-restore': 'backup',
    logs: 'activity',
    'activity-logs': 'activity',
    consultation: 'records',
    'consultation-records': 'records',
    'image-records': 'records'
  };

  function showLoading() {
    pageContent.innerHTML = '<div class="card placeholder">Loading...</div>';
  }

  function setActiveNav(page) {
    links.forEach(link => {
      link.classList.toggle('active', link.dataset.page === page);
    });
  }

  function normalizePage(value) {
    const key = String(value || '').replace(/^#/, '').trim();
    return pages[key] ? key : (pageAliases[key.toLowerCase()] || 'dashboard');
  }

  function roleLabel(role) {
    const normalized = String(role || '').trim().toLowerCase().replace(/[\s_-]+/g, '');
    if (normalized === 'superadmin') return 'Super Admin';
    if (normalized === 'admin') return 'Admin';
    if (normalized === 'staff') return 'Staff';
    return role || 'User';
  }

  function renderSessionWelcome(session) {
    if (!sessionWelcome) return;

    const firstName = String(session.user_name || '').trim().split(/\s+/)[0] || 'User';
    const employeeNumber = session.employee_number || 'No employee number';
    sessionWelcome.innerHTML = `
      <span>${roleLabel(session.role)}</span>
      <strong>Welcome, ${firstName} - ${employeeNumber}</strong>
    `;
  }

  function guardSuperAdminSession() {
    return fetch('../get-session.php', { cache: 'no-store' })
      .then(response => response.json())
      .then(session => {
        const role = String(session.role || '').trim().toLowerCase().replace(/[\s_-]+/g, '');
        if (session.status !== 'ok') {
          window.location.replace('../index.html');
          return false;
        }

        if (role !== 'superadmin') {
          window.location.replace(role === 'admin' ? '../admin.html' : '../landing.html');
          return false;
        }

        renderSessionWelcome(session);
        return true;
      })
      .catch(() => {
        window.location.replace('../index.html');
        return false;
      });
  }

  function renderPage(page) {
    const config = pages[page] || pages.dashboard;

    setActiveNav(page);
    pageTitle.textContent = titles[page] || titles.dashboard;
    const context = document.querySelector('.super-admin-context');
    if (context) {
      context.textContent = descriptions[page] || descriptions.dashboard;
    }

    if (!config.url) {
      config.init();
      return;
    }

    showLoading();

    fetch(`${config.url}?v=${Date.now()}`, { cache: 'no-store' })
      .then(response => {
        if (!response.ok) throw new Error('Failed to load page');
        return response.text();
      })
      .then(html => {
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        const styles = Array.from(doc.head.querySelectorAll('style'))
          .map(style => style.outerHTML)
          .join('');
        const body = doc.body ? doc.body.innerHTML : html;

        pageContent.innerHTML = styles + body;

        if (typeof config.init === 'function') {
          config.init();
        }
      })
      .catch(error => {
        pageContent.innerHTML = `<div class="card placeholder">Error loading page: ${error.message}</div>`;
      });
  }

  links.forEach(link => {
    link.addEventListener('click', function (event) {
      event.preventDefault();

      const page = this.dataset.page;

      if (location.hash !== `#${page}`) {
        location.hash = page;
      } else {
        renderPage(page);
      }
    });
  });

  pageContent.addEventListener('click', function (event) {
    const link = event.target.closest('[data-admin-page]');
    if (!link) return;

    event.preventDefault();
    const page = normalizePage(link.dataset.adminPage || link.getAttribute('href'));
    if (location.hash !== `#${page}`) {
      location.hash = page;
    } else {
      renderPage(page);
    }
  });

  function runDailyExpiredArchive() {
    const today = new Date().toISOString().slice(0, 10);
    const key = 'dermaview.superAdmin.expiredArchiveRunDate';
    if (localStorage.getItem(key) === today) return;

    const data = new FormData();
    data.append('action', 'archive_expired_all');

    fetch('admin-privacy-data.php', { method: 'POST', body: data, cache: 'no-store' })
      .then(response => response.json())
      .then(payload => {
        if (payload && payload.status === 'ok') {
          localStorage.setItem(key, today);
        }
      })
      .catch(() => {});
  }

  function handleHash() {
    renderPage(normalizePage(location.hash || 'dashboard'));
  }

  window.addEventListener('hashchange', handleHash);
  guardSuperAdminSession().then(isAllowed => {
    if (isAllowed) {
      runDailyExpiredArchive();
      handleHash();
    }
  });
});
